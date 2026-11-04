"""Servicio de aplicación: un método por caso de uso, sólo orquesta (sin reglas)."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from uuid import uuid4

from farmaexpress.domain.entities import Comprador
from farmaexpress.domain.events import EventoDeDominio
from farmaexpress.domain.exceptions import PedidoDuplicado, RecursoNoEncontrado
from farmaexpress.domain.pedido import LineaPedido, Pedido
from farmaexpress.domain.reglas import BENEFICIO_REFERENCIA, PUEDE_PROCESARSE
from farmaexpress.domain.value_objects import Cantidad

from .puertos import PublicadorDeEventos, UnidadDeTrabajo


@dataclass(frozen=True)
class LineaSolicitada:
    recurso_id: str
    cantidad: int


@dataclass(frozen=True)
class CrearPedido:
    comprador_id: str
    lineas: list[LineaSolicitada] = field(default_factory=list)
    promocion_activa: bool = False
    autorizado: bool = False
    referencia: str = ""
    receta_fecha: date | None = None
    pedido_id: str | None = None


@dataclass(frozen=True)
class Evaluacion:
    pedido_id: str
    total: str
    puede_procesarse: bool
    beneficio_referencia: bool
    fallos_procesamiento: list[str]
    fallos_beneficio: list[str]


def _nuevo_id() -> str:
    return f"FAR-O{uuid4().hex[:8].upper()}"


class ServicioPedidos:
    def __init__(
        self,
        uow_factory: Callable[[], UnidadDeTrabajo],
        publicador: PublicadorDeEventos,
        reloj: Callable[[], date] = date.today,
    ) -> None:
        self._uow = uow_factory
        self._publicador = publicador
        self._reloj = reloj

    # ------------------------------------------------------------ comandos
    def crear_pedido(self, cmd: CrearPedido) -> Pedido:
        with self._uow() as uow:
            comprador = self._comprador(uow, cmd.comprador_id)
            pedido_id = cmd.pedido_id or _nuevo_id()
            if uow.pedidos.obtener(pedido_id):
                raise PedidoDuplicado(f"El pedido '{pedido_id}' ya existe")
            productos = uow.productos.obtener_varios([ln.recurso_id for ln in cmd.lineas])
            lineas: list[LineaPedido] = []
            for sol in cmd.lineas:
                producto = productos.get(sol.recurso_id)
                if producto is None:
                    raise RecursoNoEncontrado("Producto", sol.recurso_id)
                lineas.append(LineaPedido(producto.recurso_id, producto.precio, Cantidad(sol.cantidad)))
            pedido = Pedido.crear(
                pedido_id,
                comprador.actor_id,
                self._reloj(),
                lineas,
                promocion_activa=cmd.promocion_activa,
                autorizado=cmd.autorizado,
                referencia=cmd.referencia,
                receta_fecha=cmd.receta_fecha,
            )
            return self._persistir(uow, pedido)

    def agregar_linea(self, pedido_id: str, recurso_id: str, cantidad: int) -> Pedido:
        with self._uow() as uow:
            pedido = self._pedido(uow, pedido_id)
            producto = uow.productos.obtener(recurso_id)
            if producto is None:
                raise RecursoNoEncontrado("Producto", recurso_id)
            pedido.agregar_linea(producto, Cantidad(cantidad))
            return self._persistir(uow, pedido)

    def validar(self, pedido_id: str) -> Pedido:
        with self._uow() as uow:
            pedido = self._pedido(uow, pedido_id)
            comprador = self._comprador(uow, pedido.comprador_id)
            productos = uow.productos.obtener_varios([ln.recurso_id for ln in pedido.lineas])
            pedido.validar(comprador, productos, self._reloj())
            return self._persistir(uow, pedido)

    def preparar(self, pedido_id: str) -> Pedido:
        with self._uow() as uow:
            pedido = self._pedido(uow, pedido_id)
            comprador = self._comprador(uow, pedido.comprador_id)
            productos = uow.productos.obtener_varios([ln.recurso_id for ln in pedido.lineas])
            pedido.preparar(comprador, productos, self._reloj())
            for producto in productos.values():  # el stock descontado se persiste
                uow.productos.guardar(producto)
            return self._persistir(uow, pedido)

    def entregar(self, pedido_id: str) -> Pedido:
        with self._uow() as uow:
            pedido = self._pedido(uow, pedido_id)
            pedido.entregar(self._comprador(uow, pedido.comprador_id))
            return self._persistir(uow, pedido)

    def cancelar(self, pedido_id: str) -> Pedido:
        with self._uow() as uow:
            pedido = self._pedido(uow, pedido_id)
            pedido.cancelar()
            return self._persistir(uow, pedido)

    # ------------------------------------------------------------ consultas
    def obtener(self, pedido_id: str) -> Pedido:
        with self._uow() as uow:
            return self._pedido(uow, pedido_id)

    def listar(self, estado: str | None = None) -> list[Pedido]:
        with self._uow() as uow:
            return uow.pedidos.listar(estado)

    def evaluar(self, pedido_id: str) -> Evaluacion:
        with self._uow() as uow:
            pedido = self._pedido(uow, pedido_id)
            comprador = self._comprador(uow, pedido.comprador_id)
            return Evaluacion(
                pedido_id=pedido.id,
                total=str(pedido.total.monto),
                puede_procesarse=pedido.puede_procesarse(comprador),
                beneficio_referencia=pedido.beneficio_referencia(comprador),
                fallos_procesamiento=pedido.fallos(PUEDE_PROCESARSE, comprador),
                fallos_beneficio=pedido.fallos(BENEFICIO_REFERENCIA, comprador),
            )

    def eventos_de(self, pedido_id: str) -> list[dict]:
        with self._uow() as uow:
            self._pedido(uow, pedido_id)
            return uow.eventos.de_pedido(pedido_id)

    # -------------------------------------------------------------- helpers
    @staticmethod
    def _pedido(uow: UnidadDeTrabajo, pedido_id: str) -> Pedido:
        pedido = uow.pedidos.obtener(pedido_id)
        if pedido is None:
            raise RecursoNoEncontrado("Pedido", pedido_id)
        return pedido

    @staticmethod
    def _comprador(uow: UnidadDeTrabajo, actor_id: str) -> Comprador:
        comprador = uow.compradores.obtener(actor_id)
        if comprador is None:
            raise RecursoNoEncontrado("Comprador", actor_id)
        return comprador

    def _persistir(self, uow: UnidadDeTrabajo, pedido: Pedido) -> Pedido:
        eventos: list[EventoDeDominio] = pedido.extraer_eventos()
        uow.pedidos.guardar(pedido)
        uow.eventos.registrar(eventos)
        uow.commit()
        self._publicador.publicar(eventos)  # sólo tras commit exitoso (ADR-004)
        return pedido
