"""Mensajes en lenguaje claro para personas que no conocen el proyecto (ADR-008, RN-10).

Cada respuesta debe contestar tres preguntas: ¿qué pasó?, ¿por qué? y ¿qué puedo hacer ahora?
El dominio sólo conoce *nombres de regla* (``cliente_activo``); aquí se traducen a oraciones.
Lo usan la API y el ejecutor de casos, por eso vive en la capa de aplicación.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from farmaexpress.domain.exceptions import (
    CantidadInvalida,
    ConflictoDeEstado,
    ErrorDeDominio,
    ErrorDeValidacion,
    ImporteInvalido,
    PedidoDuplicado,
    PedidoNoEditable,
    RecursoNoEncontrado,
    ReglaDeNegocioIncumplida,
    TransicionInvalida,
)
from farmaexpress.domain.pedido import Pedido
from farmaexpress.domain.state_machine import MAQUINA_PEDIDO, Accion, EstadoPedido


@dataclass(frozen=True)
class Explicacion:
    mensaje: str
    que_hacer: str
    motivos: list[str] = field(default_factory=list)


def dinero(monto: Decimal | str | float) -> str:
    return f"${Decimal(str(monto)):,.2f} MXN"


# ------------------------------------------------------------------ estados
_ESTADOS = {
    EstadoPedido.CREADO: "recién registrado, aún sin revisar",
    EstadoPedido.VALIDADO: "cumple las reglas y falta surtirlo",
    EstadoPedido.PREPARADO: "productos separados y existencia descontada; listo para entregar",
    EstadoPedido.ENTREGADO: "venta cerrada",
    EstadoPedido.CANCELADO: "anulado antes de validarse",
}
_ACCIONES_VERBO = {
    Accion.VALIDAR: "validarlo (comprobar que cumple las reglas)",
    Accion.PREPARAR: "prepararlo (separar los productos y descontar la existencia)",
    Accion.ENTREGAR: "entregarlo al comprador",
    Accion.CANCELAR: "cancelarlo",
}
_ACCION_INFINITIVO = {
    Accion.VALIDAR: "validar",
    Accion.PREPARAR: "preparar",
    Accion.ENTREGAR: "entregar",
    Accion.CANCELAR: "cancelar",
}
_ACCION_RESULTA_EN = {
    Accion.VALIDAR: EstadoPedido.VALIDADO,
    Accion.PREPARAR: EstadoPedido.PREPARADO,
    Accion.ENTREGAR: EstadoPedido.ENTREGADO,
    Accion.CANCELAR: EstadoPedido.CANCELADO,
}


def describir_estado(estado: EstadoPedido | str) -> str:
    e = EstadoPedido(estado)
    return f"{e.value} ({_ESTADOS[e]})"


def siguiente_paso(estado: EstadoPedido | str) -> str:
    e = EstadoPedido(estado)
    acciones = MAQUINA_PEDIDO.acciones_permitidas(e)
    if not acciones:
        return "Ninguno: el pedido ya está cerrado y no admite más cambios."
    return "Lo siguiente que se puede hacer es " + " o ".join(_ACCIONES_VERBO[a] for a in acciones) + "."


def resumen_pedido(p: Pedido) -> str:
    n = len(p.lineas)
    contenido = (
        "no tiene productos todavía"
        if n == 0
        else f"incluye {n} producto{'s' if n != 1 else ''} ({p.piezas} pieza{'s' if p.piezas != 1 else ''})"
    )
    detalle = contenido[0].upper() + contenido[1:]
    return f"El pedido {p.id} está {describir_estado(p.estado)}. {detalle}; total {dinero(p.total.monto)}."


# ------------------------------------------------------------------ reglas
_MOTIVOS = {
    "cliente_activo": "El comprador está dado de baja (inactivo), por eso no se le puede procesar un pedido.",
    "detalle_no_vacio": "El pedido no tiene ningún producto. Agrega al menos uno.",
    "autorizacion": "El pedido no tiene la autorización del responsable de farmacia.",
    "producto_habilitado": (
        "Uno de los productos no está disponible para la venta (está deshabilitado o no existe en el catálogo)."
    ),
    "stock_suficiente": "No hay existencia suficiente de alguno de los productos para surtir la cantidad pedida.",
    "receta_vigente": "El pedido incluye un medicamento controlado y la receta falta o tiene más de 30 días.",
    "NOT (contiene_controlado AND excede_limite_controlado)": (
        "Un medicamento controlado pasa el límite permitido (más de 10 piezas o más de $3,000.00 MXN) "
        "y necesita autorización."
    ),
    "cliente_preferente": "El comprador no es cliente preferente.",
    "total>=1500": "El total del pedido es menor a $1,500.00 MXN, el mínimo para el beneficio.",
    "NOT promocion_activa": "El pedido ya tiene una promoción activa, y no se acumula con el beneficio.",
}
_RUIDO = {"NOT contiene_controlado"}  # parte interna de una regla; no aporta nada al usuario


def motivos(reglas: list[str]) -> list[str]:
    """Traduce nombres de reglas a oraciones, sin repetir y respetando el orden."""
    salida: list[str] = []
    for r in reglas:
        if r in _RUIDO:
            continue
        texto = _MOTIVOS.get(r, f"No se cumple una condición del negocio («{r}»).")
        if texto not in salida:
            salida.append(texto)
    return salida


def conclusion_procesamiento(ok: bool, fallos: list[str]) -> str:
    if ok:
        return "Sí se puede procesar: el comprador está activo, el pedido tiene productos y cuenta con autorización."
    return "Todavía no se puede procesar. " + " ".join(motivos(fallos))


def conclusion_beneficio(ok: bool, fallos: list[str]) -> str:
    if ok:
        return (
            "Sí aplica el beneficio de cliente preferente: el comprador es preferente, "
            "el total llega a $1,500.00 MXN y no hay promoción activa."
        )
    return "No aplica el beneficio de cliente preferente. " + " ".join(motivos(fallos))


# ------------------------------------------------------------------ eventos
def describir_evento(nombre: str, datos: dict) -> str:
    if nombre == "PedidoCreado":
        return f"Se registró el pedido por un total de {dinero(datos.get('total', 0))}."
    if nombre == "PedidoValidado":
        return "Se confirmó que el pedido cumple las reglas y puede surtirse."
    if nombre == "PedidoPreparado":
        return "Se separaron los productos y se descontó la existencia del inventario."
    if nombre == "PedidoEntregado":
        beneficio = (
            "El comprador recibe el beneficio de cliente preferente."
            if datos.get("beneficio_referencia")
            else "No aplica el beneficio de cliente preferente."
        )
        return f"El pedido se entregó y la venta quedó cerrada (total {dinero(datos.get('total', 0))}). {beneficio}"
    if nombre == "PedidoCancelado":
        return "El pedido se canceló antes de validarse."
    return f"Ocurrió el evento «{nombre}»."


# ------------------------------------------------------------------ errores
_ENTIDAD = {
    "Pedido": ("el pedido", "/pedidos"),
    "Comprador": ("el comprador", "/compradores"),
    "Producto": ("el producto", "/productos"),
}
_CAMPOS = {
    "comprador_id": "el comprador",
    "recurso_id": "el producto",
    "cantidad": "la cantidad",
    "lineas": "la lista de productos",
    "receta_fecha": "la fecha de la receta",
    "promocion_activa": "si hay promoción activa",
    "autorizado": "si el pedido está autorizado",
    "referencia": "la referencia",
}


def explicar_error(exc: ErrorDeDominio) -> Explicacion:
    if isinstance(exc, TransicionInvalida):
        return _explicar_transicion(exc)
    if isinstance(exc, PedidoNoEditable):
        return Explicacion(
            f"Ya no se pueden agregar productos: el pedido está {describir_estado(exc.estado)}.",
            "Solo se puede editar un pedido recién registrado. Si hace falta, crea un pedido nuevo.",
        )
    if isinstance(exc, PedidoDuplicado):
        return Explicacion(
            "Ya existe un pedido con ese número.",
            "Usa otro número o deja que el sistema genere uno automáticamente.",
        )
    if isinstance(exc, ConflictoDeEstado):
        return Explicacion(
            f"Esa operación no se puede hacer en este momento. {exc}",
            "Revisa el estado del pedido e inténtalo de nuevo.",
        )
    if isinstance(exc, RecursoNoEncontrado):
        nombre, listado = _ENTIDAD.get(exc.tipo, (exc.tipo.lower(), ""))
        pista = f" Consulta el listado en «{listado}» para ver los números válidos." if listado else ""
        return Explicacion(
            f"No encontramos {nombre} con el número «{exc.identificador}».",
            "Revisa que esté bien escrito (se distingue entre mayúsculas y minúsculas)." + pista,
        )
    if isinstance(exc, ReglaDeNegocioIncumplida):
        lista = motivos(exc.fallos)
        cuerpo = " ".join(lista) if lista else str(exc)
        return Explicacion(
            f"No se puede continuar con el pedido. {cuerpo}",
            "Corrige lo indicado y vuelve a intentarlo. El pedido no cambió.",
            lista,
        )
    if isinstance(exc, CantidadInvalida):
        return Explicacion(
            "La cantidad no es válida: debe ser un número entero mayor que cero (por ejemplo, 1, 2 o 3).",
            "Corrige la cantidad e inténtalo otra vez.",
        )
    if isinstance(exc, ImporteInvalido):
        return Explicacion(
            "El importe no es válido: debe ser un número positivo.", "Revisa el precio e inténtalo otra vez."
        )
    if isinstance(exc, ErrorDeValidacion):
        return Explicacion(f"Algún dato no es válido. {exc}", "Revisa los datos enviados e inténtalo otra vez.")
    return Explicacion("Ocurrió un problema inesperado.", "Inténtalo de nuevo; si continúa, avisa al equipo técnico.")


def _explicar_transicion(exc: TransicionInvalida) -> Explicacion:
    try:
        estado, accion = EstadoPedido(exc.estado), Accion(exc.accion)
    except ValueError:
        return Explicacion(f"Esa acción no se puede hacer ahora ({exc}).", "Revisa el estado del pedido.")
    if _ACCION_RESULTA_EN[accion] == estado:
        return Explicacion(
            f"Ese paso ya se hizo: el pedido está {describir_estado(estado)}. No hace falta (ni se puede) repetirlo.",
            siguiente_paso(estado),
        )
    extra = ""
    if accion is Accion.ENTREGAR and estado is EstadoPedido.CREADO:
        extra = " Antes de entregarlo debe validarse y prepararse, en ese orden."
    elif accion is Accion.CANCELAR:
        extra = " Un pedido solo se puede cancelar mientras está recién registrado."
    return Explicacion(
        f"No se puede {_ACCION_INFINITIVO[accion]} el pedido ahora: está {describir_estado(estado)}.{extra}",
        siguiente_paso(estado),
    )


def explicar_validacion(errores: list[dict]) -> Explicacion:
    """Traduce los errores de formato (Pydantic, en inglés) a frases claras en español."""
    frases: list[str] = []
    for e in errores:
        tipo = e.get("type", "")
        loc = [str(x) for x in e.get("loc", []) if x not in ("body", "query", "path")]
        campo = next((_CAMPOS[x] for x in reversed(loc) if x in _CAMPOS), "uno de los datos")
        if tipo == "json_invalid":
            frase = "Los datos enviados no tienen un formato válido (revisa llaves, comas y comillas)."
        elif tipo == "greater_than":
            frase = "La cantidad de cada producto debe ser un número entero mayor que cero."
        elif tipo in ("int_parsing", "int_from_float", "int_type"):
            frase = f"{campo.capitalize()} debe ser un número entero, sin decimales."
        elif tipo == "missing":
            frase = f"Falta indicar {campo}."
        elif tipo in ("string_too_short", "string_type"):
            frase = f"{campo.capitalize()} no puede ir vacío."
        elif tipo.startswith("date") or tipo == "datetime_from_date_parsing":
            frase = "La fecha debe escribirse como año-mes-día (por ejemplo, 2026-11-05)."
        else:
            frase = f"{campo.capitalize()} no tiene un valor válido."
        if frase not in frases:
            frases.append(frase)
    return Explicacion(
        "No pudimos procesar la solicitud porque hay datos incorrectos. " + " ".join(frases),
        "Corrige lo indicado y vuelve a enviar la solicitud.",
        frases,
    )
