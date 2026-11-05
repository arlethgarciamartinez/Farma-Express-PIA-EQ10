"""RN-10 / US-27: las respuestas se entienden sin conocer el proyecto."""
import re
from decimal import Decimal

import pytest

from farmaexpress.application import mensajes as m
from farmaexpress.domain.exceptions import (
    CantidadInvalida,
    ConflictoDeEstado,
    ErrorDeValidacion,
    ImporteInvalido,
    PedidoDuplicado,
    PedidoNoEditable,
    RecursoNoEncontrado,
    ReglaDeNegocioIncumplida,
    StockInsuficiente,
    TransicionInvalida,
)
from farmaexpress.domain.state_machine import EstadoPedido
from farmaexpress.infrastructure.ejecutor_casos import (
    construir_servicio,
    ejecutar_casos,
    ejecutar_transiciones,
)
from tests.conftest import DATOS

JERGA = re.compile(
    r"\b[a-z]+_[a-z_]+\b"  # nombres_de_reglas_en_snake_case
    r"|Input should|Exception|Specification|CONFLICTO_DE_ESTADO|REGLA_DE_NEGOCIO|NO_ENCONTRADO|DATOS_INVALIDOS"
    r"|TransicionInvalida|ReglaDeNegocio|null|undefined"
)


def sin_jerga(*textos: str) -> None:
    for t in textos:
        assert t.strip(), "mensaje vacío"
        assert not JERGA.search(t), f"jerga técnica en el mensaje: {t!r}"


def aplanar(cuerpo: dict, claves: tuple[str, ...]) -> list[str]:
    salida: list[str] = []
    for k in claves:
        v = cuerpo[k]
        salida += v if isinstance(v, list) else [v]
    return salida


# ----------------------------------------------------------------- unitarias
class TestTextos:
    def test_dinero(self):
        assert m.dinero(Decimal("7559")) == "$7,559.00 MXN"
        assert m.dinero("1500") == "$1,500.00 MXN"

    @pytest.mark.parametrize("estado", list(EstadoPedido))
    def test_cada_estado_tiene_descripcion_y_siguiente_paso(self, estado):
        sin_jerga(m.siguiente_paso(estado))
        assert estado.value in m.describir_estado(estado)
        assert "(" in m.describir_estado(estado)

    def test_siguiente_paso_en_estados_finales(self):
        assert "cerrado" in m.siguiente_paso(EstadoPedido.ENTREGADO)
        assert "cerrado" in m.siguiente_paso(EstadoPedido.CANCELADO)
        assert "validarlo" in m.siguiente_paso(EstadoPedido.CREADO)
        assert "cancelarlo" in m.siguiente_paso("CREADO")

    def test_motivos_traducen_dedupican_y_quitan_ruido(self):
        reglas = ["NOT contiene_controlado", "receta_vigente", "receta_vigente", "autorizacion"]
        r = m.motivos(reglas)
        assert len(r) == 2 and "receta" in r[0] and "autorización" in r[1]
        sin_jerga(*r)

    def test_todas_las_reglas_conocidas_tienen_texto_claro(self):
        conocidas = list(m._MOTIVOS)
        assert len(conocidas) == 10
        sin_jerga(*m.motivos(conocidas))

    def test_regla_desconocida_no_rompe(self):
        assert "regla_rara" in m.motivos(["regla_rara"])[0]

    def test_conclusiones(self):
        assert m.conclusion_procesamiento(True, []).startswith("Sí se puede procesar")
        no = m.conclusion_procesamiento(False, ["cliente_activo", "autorizacion"])
        assert no.startswith("Todavía no") and "inactivo" in no and "autorización" in no
        assert m.conclusion_beneficio(True, []).startswith("Sí aplica")
        sin = m.conclusion_beneficio(False, ["cliente_preferente", "total>=1500", "NOT promocion_activa"])
        assert "preferente" in sin and "$1,500.00" in sin and "promoción" in sin
        sin_jerga(no, sin)

    @pytest.mark.parametrize(
        ("nombre", "datos", "fragmento"),
        [
            ("PedidoCreado", {"total": "100"}, "$100.00 MXN"),
            ("PedidoValidado", {}, "cumple las reglas"),
            ("PedidoPreparado", {}, "existencia"),
            ("PedidoEntregado", {"total": "7559.00", "beneficio_referencia": True}, "recibe el beneficio"),
            ("PedidoEntregado", {"total": "10", "beneficio_referencia": False}, "No aplica"),
            ("PedidoCancelado", {}, "canceló"),
            ("Otro", {}, "Otro"),
        ],
    )
    def test_describir_evento(self, nombre, datos, fragmento):
        texto = m.describir_evento(nombre, datos)
        assert fragmento in texto
        if nombre.startswith("Pedido"):
            sin_jerga(texto)


class TestErrores:
    def test_404_por_tipo_con_pista(self):
        e = m.explicar_error(RecursoNoEncontrado("Pedido", "NOPE"))
        assert "No encontramos el pedido" in e.mensaje and "/pedidos" in e.que_hacer
        assert "el comprador" in m.explicar_error(RecursoNoEncontrado("Comprador", "X")).mensaje
        assert "el producto" in m.explicar_error(RecursoNoEncontrado("Producto", "X")).mensaje
        assert "xyz" in m.explicar_error(RecursoNoEncontrado("Xyz", "1")).mensaje
        sin_jerga(e.mensaje, e.que_hacer)

    def test_409_saltar_estado(self):
        e = m.explicar_error(TransicionInvalida("CREADO", "entregar"))
        assert "validarse y prepararse" in e.mensaje and "validarlo" in e.que_hacer
        sin_jerga(e.mensaje, e.que_hacer)

    def test_409_paso_repetido(self):
        e = m.explicar_error(TransicionInvalida("VALIDADO", "validar"))
        assert "ya se hizo" in e.mensaje and "prepararlo" in e.que_hacer

    def test_409_cancelar_tarde(self):
        e = m.explicar_error(TransicionInvalida("VALIDADO", "cancelar"))
        assert "recién registrado" in e.mensaje

    def test_409_valores_desconocidos_no_rompen(self):
        e = m.explicar_error(TransicionInvalida("RARO", "bailar"))
        assert e.mensaje and e.que_hacer

    def test_409_otros_conflictos(self):
        assert "ya no se pueden agregar" in m.explicar_error(PedidoNoEditable("ENTREGADO")).mensaje.lower()
        assert "Ya existe" in m.explicar_error(PedidoDuplicado("x")).mensaje
        assert "no se puede hacer" in m.explicar_error(ConflictoDeEstado("algo")).mensaje

    def test_422_lista_motivos_y_dice_que_no_cambio(self):
        e = m.explicar_error(ReglaDeNegocioIncumplida("x", ["cliente_activo", "stock_suficiente"]))
        assert len(e.motivos) == 2 and "no cambió" in e.que_hacer
        sin_jerga(e.mensaje, e.que_hacer, *e.motivos)
        assert m.explicar_error(StockInsuficiente("P1: stock 1 < 5", ["stock_suficiente"])).motivos
        assert m.explicar_error(ReglaDeNegocioIncumplida("sin lista")).mensaje.endswith("sin lista")

    def test_400_de_dominio(self):
        for exc in (CantidadInvalida("x"), ImporteInvalido("x"), ErrorDeValidacion("x")):
            e = m.explicar_error(exc)
            sin_jerga(e.mensaje, e.que_hacer)

    def test_error_desconocido(self):
        from farmaexpress.domain.exceptions import ErrorDeDominio

        assert "inesperado" in m.explicar_error(ErrorDeDominio("x")).mensaje

    @pytest.mark.parametrize(
        ("tipo", "loc", "fragmento"),
        [
            ("greater_than", ("body", "lineas", 0, "cantidad"), "mayor que cero"),
            ("int_from_float", ("body", "lineas", 0, "cantidad"), "número entero"),
            ("int_parsing", ("body", "lineas", 0, "cantidad"), "número entero"),
            ("missing", ("body", "comprador_id"), "Falta indicar el comprador"),
            ("string_too_short", ("body", "comprador_id"), "no puede ir vacío"),
            ("json_invalid", ("body", 1), "formato válido"),
            ("date_from_datetime_parsing", ("body", "receta_fecha"), "año-mes-día"),
            ("list_type", ("body", "lineas"), "la lista de productos"),
            ("otro", ("body", "zzz"), "uno de los datos"),
        ],
    )
    def test_validacion_en_espanol(self, tipo, loc, fragmento):
        e = m.explicar_validacion([{"type": tipo, "loc": loc, "msg": "Input should be ..."}])
        assert fragmento.lower() in e.mensaje.lower()
        sin_jerga(e.mensaje, e.que_hacer)

    def test_validacion_no_repite_frases(self):
        err = {"type": "greater_than", "loc": ("body", "lineas", 0, "cantidad"), "msg": "x"}
        assert len(m.explicar_validacion([err, err]).motivos) == 1


# ----------------------------------------------------------------------- API
class TestApiEnLenguajeClaro:
    def test_error_404(self, client):
        r = client.get("/pedidos/NOPE")
        c = r.json()
        assert r.status_code == 404 and c["mensaje"].startswith("No encontramos el pedido")
        sin_jerga(*aplanar(c, ("mensaje", "que_hacer", "motivos")))
        assert c["codigo"] == "NO_ENCONTRADO"  # el código técnico se conserva para programadores

    def test_error_409_saltar_estado(self, client):
        c = client.post("/pedidos/FAR-O004/entregar").json()
        assert "validarse y prepararse" in c["mensaje"] and "validarlo" in c["que_hacer"]
        sin_jerga(*aplanar(c, ("mensaje", "que_hacer")))

    def test_error_409_repetir_validacion(self, client):
        client.post("/pedidos/FAR-O002/validar")
        c = client.post("/pedidos/FAR-O002/validar").json()
        assert "ya se hizo" in c["mensaje"]

    def test_error_422_explica_cada_motivo(self, client):
        r = client.post("/pedidos/FAR-O028/validar")
        c = r.json()
        assert r.status_code == 422 and "dado de baja" in c["mensaje"]
        assert c["reglas_incumplidas"] == ["cliente_activo"]
        sin_jerga(*aplanar(c, ("mensaje", "que_hacer", "motivos")))

    @pytest.mark.parametrize(("pedido", "fragmento"), [
        ("FAR-O005", "no está disponible para la venta"),
        ("FAR-O013", "no tiene ningún producto"),
    ])
    def test_error_422_otros_motivos(self, client, pedido, fragmento):
        c = client.post(f"/pedidos/{pedido}/validar").json()
        assert fragmento in c["mensaje"]

    @pytest.mark.parametrize("cuerpo", [
        {"comprador_id": "FAR-C001", "lineas": [{"recurso_id": "FAR-P001", "cantidad": 0}]},
        {"comprador_id": "FAR-C001", "lineas": [{"recurso_id": "FAR-P001", "cantidad": 1.5}]},
        {"lineas": []},
        {"comprador_id": "FAR-C001", "receta_fecha": "no-es-fecha"},
    ])
    def test_error_400_en_espanol(self, client, cuerpo):
        r = client.post("/pedidos", json=cuerpo)
        c = r.json()
        assert r.status_code == 400
        assert c["mensaje"].startswith("No pudimos procesar la solicitud")
        sin_jerga(*aplanar(c, ("mensaje", "que_hacer", "motivos")))

    def test_json_mal_escrito(self, client):
        r = client.post("/pedidos", content="{mal", headers={"content-type": "application/json"})
        assert r.status_code == 400 and "formato válido" in r.json()["mensaje"]

    def test_pedido_trae_resumen_y_siguiente_paso(self, client):
        c = client.post("/pedidos/FAR-O002/validar").json()
        assert "VALIDADO (cumple las reglas" in c["resumen"] and "$7,559.00 MXN" in c["resumen"]
        assert "prepararlo" in c["siguiente_paso"]
        sin_jerga(c["resumen"], c["siguiente_paso"])
        nuevo = client.post("/pedidos", json={"comprador_id": "FAR-C001"}).json()
        assert "No tiene productos todavía" in nuevo["resumen"]

    def test_evaluacion_explica_ambas_reglas(self, client):
        ok = client.get("/pedidos/FAR-O002/evaluacion").json()
        assert ok["conclusion_procesamiento"].startswith("Sí se puede procesar")
        assert ok["conclusion_beneficio"].startswith("Sí aplica")
        no = client.get("/pedidos/FAR-O028/evaluacion").json()
        assert "dado de baja" in no["conclusion_procesamiento"]
        assert "no es cliente preferente" in no["conclusion_beneficio"]
        assert no["motivos_no_procesable"] and no["motivos_sin_beneficio"]
        for c in (ok, no):
            sin_jerga(*aplanar(c, ("conclusion_procesamiento", "conclusion_beneficio",
                                   "motivos_no_procesable", "motivos_sin_beneficio")))

    def test_eventos_con_descripcion(self, client):
        for a in ("validar", "preparar", "entregar"):
            client.post(f"/pedidos/FAR-O002/{a}")
        eventos = client.get("/pedidos/FAR-O002/eventos").json()
        assert [e["evento"] for e in eventos] == ["PedidoValidado", "PedidoPreparado", "PedidoEntregado"]
        assert "recibe el beneficio" in eventos[-1]["descripcion"]
        sin_jerga(*[e["descripcion"] for e in eventos])

    def test_openapi_documenta_los_campos_claros(self, client):
        esquema = client.get("/openapi.json").json()["components"]["schemas"]
        assert {"mensaje", "que_hacer", "motivos"} <= set(esquema["ErrorOut"]["properties"])
        assert "resumen" in esquema["PedidoOut"]["properties"]
        assert "conclusion_procesamiento" in esquema["EvaluacionOut"]["properties"]


# ------------------------------------------------------- casos del paquete (CSV)
@pytest.fixture(scope="module")
def resultados():
    s = construir_servicio("sqlite://", str(DATOS))
    return ejecutar_casos(s, DATOS), ejecutar_transiciones(s, DATOS)


def test_los_140_resultados_traen_explicacion_clara(resultados):
    casos, trans = resultados
    assert len(casos) + len(trans) == 140
    for fila in casos + trans:
        sin_jerga(fila["explicacion"])
        assert fila["operacion_id"] in fila["explicacion"]


def test_explicaciones_de_ejemplo(resultados):
    casos, trans = resultados
    assert any("Sí se puede procesar" in c["explicacion"] for c in casos)
    assert any("Todavía no se puede procesar" in c["explicacion"] for c in casos)
    assert any("Sí aplica el beneficio" in c["explicacion"] for c in casos)
    assert any("No aplica el beneficio" in c["explicacion"] for c in casos)
    assert any("Todo salió bien" in t["explicacion"] for t in trans)
    assert any("No se pudo completar la acción" in t["explicacion"] for t in trans)
