"""Implementaciones SQLAlchemy de los repositorios y de la Unidad de Trabajo."""
from __future__ import annotations

from collections.abc import Callable
from types import TracebackType

from sqlalchemy import select
from sqlalchemy.orm import Session

from farmaexpress.application.puertos import UnidadDeTrabajo
from farmaexpress.domain.entities import Comprador, Producto
from farmaexpress.domain.events import EventoDeDominio
from farmaexpress.domain.pedido import LineaPedido, Pedido
from farmaexpress.domain.repositories import (
    RepositorioCompradores,
    RepositorioEventos,
    RepositorioPedidos,
    RepositorioProductos,
)
from farmaexpress.domain.state_machine import EstadoPedido
from farmaexpress.domain.value_objects import Cantidad, Dinero

from .db import CompradorRow, EventoRow, LineaRow, PedidoRow, ProductoRow


class SqlCompradores(RepositorioCompradores):
    def __init__(self, s: Session) -> None:
        self.s = s

    @staticmethod
    def _a_dominio(r: CompradorRow) -> Comprador:
        return Comprador(r.actor_id, r.nombre, r.activo, r.es_preferente, r.ciudad)

    def obtener(self, actor_id: str) -> Comprador | None:
        r = self.s.get(CompradorRow, actor_id)
        return self._a_dominio(r) if r else None

    def listar(self) -> list[Comprador]:
        rows = self.s.scalars(select(CompradorRow).order_by(CompradorRow.actor_id))
        return [self._a_dominio(r) for r in rows]


class SqlProductos(RepositorioProductos):
    def __init__(self, s: Session) -> None:
        self.s = s

    @staticmethod
    def _a_dominio(r: ProductoRow) -> Producto:
        return Producto(
            r.recurso_id, r.descripcion, Dinero(r.precio_mxn), r.stock, r.habilitado, r.controlado
        )

    def obtener(self, recurso_id: str) -> Producto | None:
        r = self.s.get(ProductoRow, recurso_id)
        return self._a_dominio(r) if r else None

    def obtener_varios(self, ids: list[str]) -> dict[str, Producto]:
        if not ids:
            return {}
        rows = self.s.scalars(select(ProductoRow).where(ProductoRow.recurso_id.in_(ids)))
        return {r.recurso_id: self._a_dominio(r) for r in rows}

    def listar(self) -> list[Producto]:
        rows = self.s.scalars(select(ProductoRow).order_by(ProductoRow.recurso_id))
        return [self._a_dominio(r) for r in rows]

    def guardar(self, producto: Producto) -> None:
        r = self.s.get(ProductoRow, producto.recurso_id)
        if r is None:
            r = ProductoRow(recurso_id=producto.recurso_id)
            self.s.add(r)
        r.descripcion = producto.descripcion
        r.precio_mxn = producto.precio.monto
        r.stock = producto.stock
        r.habilitado = producto.habilitado
        r.controlado = producto.controlado
        self.s.flush()


class SqlPedidos(RepositorioPedidos):
    def __init__(self, s: Session) -> None:
        self.s = s

    @staticmethod
    def _a_dominio(r: PedidoRow) -> Pedido:
        lineas = [
            LineaPedido(ln.recurso_id, Dinero(ln.precio_unitario), Cantidad(ln.cantidad))
            for ln in sorted(r.lineas, key=lambda x: x.recurso_id)
        ]
        return Pedido(
            r.id,
            r.comprador_id,
            r.fecha_solicitud,
            lineas,
            EstadoPedido(r.estado),
            r.promocion_activa,
            r.autorizado,
            r.referencia,
            r.receta_fecha,
        )

    def obtener(self, pedido_id: str) -> Pedido | None:
        r = self.s.get(PedidoRow, pedido_id)
        return self._a_dominio(r) if r else None

    def listar(self, estado: str | None = None) -> list[Pedido]:
        q = select(PedidoRow).order_by(PedidoRow.id)
        if estado:
            q = q.where(PedidoRow.estado == estado)
        return [self._a_dominio(r) for r in self.s.scalars(q)]

    def guardar(self, pedido: Pedido) -> None:
        r = self.s.get(PedidoRow, pedido.id)
        if r is None:
            r = PedidoRow(id=pedido.id)
            self.s.add(r)
        r.comprador_id = pedido.comprador_id
        r.estado = pedido.estado.value
        r.fecha_solicitud = pedido.fecha_solicitud
        r.promocion_activa = pedido.promocion_activa
        r.autorizado = pedido.autorizado
        r.referencia = pedido.referencia
        r.receta_fecha = pedido.receta_fecha
        existentes = {ln.recurso_id: ln for ln in r.lineas}
        nuevas = {ln.recurso_id: ln for ln in pedido.lineas}
        for rid in set(existentes) - set(nuevas):
            r.lineas.remove(existentes[rid])
        for rid, ln in nuevas.items():
            if rid in existentes:
                existentes[rid].precio_unitario = ln.precio_unitario.monto
                existentes[rid].cantidad = ln.cantidad.valor
            else:
                r.lineas.append(
                    LineaRow(
                        recurso_id=rid,
                        precio_unitario=ln.precio_unitario.monto,
                        cantidad=ln.cantidad.valor,
                    )
                )
        self.s.flush()


class SqlEventos(RepositorioEventos):
    def __init__(self, s: Session) -> None:
        self.s = s

    def registrar(self, eventos: list[EventoDeDominio]) -> None:
        for e in eventos:
            self.s.add(
                EventoRow(
                    pedido_id=e.pedido_id, nombre=e.nombre, ocurrido_en=e.ocurrido_en, payload=e.payload()
                )
            )
        self.s.flush()

    def de_pedido(self, pedido_id: str) -> list[dict]:
        rows = self.s.scalars(
            select(EventoRow).where(EventoRow.pedido_id == pedido_id).order_by(EventoRow.id)
        )
        return [
            {"evento": r.nombre, "ocurrido_en": r.ocurrido_en.isoformat(), "datos": r.payload}
            for r in rows
        ]


class SqlUnidadDeTrabajo(UnidadDeTrabajo):
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self.session = session_factory()
        self.pedidos = SqlPedidos(self.session)
        self.compradores = SqlCompradores(self.session)
        self.productos = SqlProductos(self.session)
        self.eventos = SqlEventos(self.session)

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()

    def __exit__(
        self, tipo: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> None:
        try:
            self.rollback()
        finally:
            self.session.close()
