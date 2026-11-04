"""Consultas de lectura (lado 'Query' del CQRS básico, ADR-004)."""
from __future__ import annotations

from collections.abc import Callable

from farmaexpress.domain.entities import Comprador, Producto
from farmaexpress.domain.exceptions import RecursoNoEncontrado

from .puertos import UnidadDeTrabajo


class ServicioCatalogo:
    def __init__(self, uow_factory: Callable[[], UnidadDeTrabajo]) -> None:
        self._uow = uow_factory

    def compradores(self) -> list[Comprador]:
        with self._uow() as uow:
            return uow.compradores.listar()

    def comprador(self, actor_id: str) -> Comprador:
        with self._uow() as uow:
            c = uow.compradores.obtener(actor_id)
            if c is None:
                raise RecursoNoEncontrado("Comprador", actor_id)
            return c

    def productos(self) -> list[Producto]:
        with self._uow() as uow:
            return uow.productos.listar()

    def producto(self, recurso_id: str) -> Producto:
        with self._uow() as uow:
            p = uow.productos.obtener(recurso_id)
            if p is None:
                raise RecursoNoEncontrado("Producto", recurso_id)
            return p
