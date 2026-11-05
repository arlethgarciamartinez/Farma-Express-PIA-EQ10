"""Agregado Pedido (raíz) y su entidad interna LineaPedido."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from . import events as ev
from .entities import Comprador, Producto
from .exceptions import PedidoNoEditable, ReglaDeNegocioIncumplida
from .reglas import BENEFICIO_REFERENCIA, PUEDE_PREPARARSE, PUEDE_PROCESARSE, PUEDE_VALIDARSE
from .specifications import ContextoPedido, Specification
from .state_machine import MAQUINA_PEDIDO, Accion, EstadoPedido, MaquinaDeEstados
from .value_objects import Cantidad, Dinero


@dataclass(frozen=True)
class LineaPedido:
    recurso_id: str
    precio_unitario: Dinero
    cantidad: Cantidad

    @property
    def subtotal(self) -> Dinero:
        return self.precio_unitario.por(self.cantidad)


class Pedido:
    def __init__(
        self,
        pedido_id: str,
        comprador_id: str,
        fecha_solicitud: date,
        lineas: list[LineaPedido] | None = None,
        estado: EstadoPedido = EstadoPedido.CREADO,
        promocion_activa: bool = False,
        autorizado: bool = False,
        referencia: str = "",
        receta_fecha: date | None = None,
        maquina: MaquinaDeEstados = MAQUINA_PEDIDO,
    ) -> None:
        self.id = pedido_id
        self.comprador_id = comprador_id
        self.fecha_solicitud = fecha_solicitud
        self.lineas: list[LineaPedido] = list(lineas or [])
        self.estado = estado
        self.promocion_activa = promocion_activa
        self.autorizado = autorizado
        self.referencia = referencia
        self.receta_fecha = receta_fecha
        self._maquina = maquina
        self._eventos: list[ev.EventoDeDominio] = []

    # ------------------------------------------------------------ fábrica
    @classmethod
    def crear(cls, *args: object, **kwargs: object) -> Pedido:
        """Alta de un pedido nuevo: emite PedidoCreado (a diferencia de reconstituir)."""
        pedido = cls(*args, **kwargs)  # type: ignore[arg-type]
        pedido._eventos.append(
            ev.PedidoCreado(
                pedido_id=pedido.id, comprador_id=pedido.comprador_id, total=pedido.total.monto
            )
        )
        return pedido

    # ----------------------------------------------------------- consultas
    @property
    def total(self) -> Dinero:
        resultado = Dinero.cero()
        for ln in self.lineas:
            resultado = resultado + ln.subtotal
        return resultado

    @property
    def piezas(self) -> int:
        return sum(ln.cantidad.valor for ln in self.lineas)

    def _contexto(
        self, comprador: Comprador, productos: dict[str, Producto] | None, hoy: date | None
    ) -> ContextoPedido:
        return ContextoPedido(self, comprador, productos or {}, hoy or date.today())

    def puede_procesarse(self, comprador: Comprador) -> bool:
        return PUEDE_PROCESARSE.is_satisfied_by(self._contexto(comprador, None, None))

    def beneficio_referencia(self, comprador: Comprador) -> bool:
        return BENEFICIO_REFERENCIA.is_satisfied_by(self._contexto(comprador, None, None))

    def fallos(self, regla: Specification, comprador: Comprador) -> list[str]:
        return regla.fallos(self._contexto(comprador, None, None))

    # ------------------------------------------------------------- comandos
    def agregar_linea(self, producto: Producto, cantidad: Cantidad) -> None:
        if self.estado is not EstadoPedido.CREADO:
            raise PedidoNoEditable(self.estado.value)
        previa = next((ln for ln in self.lineas if ln.recurso_id == producto.recurso_id), None)
        if previa:
            self.lineas.remove(previa)
            cantidad = Cantidad(previa.cantidad.valor + cantidad.valor)
        self.lineas.append(LineaPedido(producto.recurso_id, producto.precio, cantidad))

    def _exigir(self, regla: Specification, ctx: ContextoPedido, mensaje: str) -> None:
        if not regla.is_satisfied_by(ctx):
            raise ReglaDeNegocioIncumplida(mensaje, regla.fallos(ctx))

    def validar(
        self, comprador: Comprador, productos: dict[str, Producto], hoy: date | None = None
    ) -> None:
        # 1º transición legal (409), 2º reglas de negocio (422)
        destino = self._maquina.siguiente(self.estado, Accion.VALIDAR)
        self._exigir(
            PUEDE_VALIDARSE, self._contexto(comprador, productos, hoy), "El pedido no cumple las precondiciones"
        )
        self.estado = destino
        self._eventos.append(ev.PedidoValidado(pedido_id=self.id))

    def preparar(
        self, comprador: Comprador, productos: dict[str, Producto], hoy: date | None = None
    ) -> None:
        destino = self._maquina.siguiente(self.estado, Accion.PREPARAR)
        self._exigir(
            PUEDE_PREPARARSE, self._contexto(comprador, productos, hoy), "No hay existencia suficiente"
        )
        for ln in self.lineas:
            productos[ln.recurso_id].descontar(ln.cantidad)
        self.estado = destino
        self._eventos.append(ev.PedidoPreparado(pedido_id=self.id))

    def entregar(self, comprador: Comprador) -> None:
        destino = self._maquina.siguiente(self.estado, Accion.ENTREGAR)
        self.estado = destino
        self._eventos.append(
            ev.PedidoEntregado(
                pedido_id=self.id,
                total=self.total.monto,
                beneficio_referencia=self.beneficio_referencia(comprador),
            )
        )

    def cancelar(self) -> None:
        self.estado = self._maquina.siguiente(self.estado, Accion.CANCELAR)
        self._eventos.append(ev.PedidoCancelado(pedido_id=self.id))

    # -------------------------------------------------------------- eventos
    def extraer_eventos(self) -> list[ev.EventoDeDominio]:
        eventos, self._eventos = self._eventos, []
        return eventos
