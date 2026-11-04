"""Puertos de la capa de aplicación (los implementa infrastructure)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from types import TracebackType

from farmaexpress.domain.events import EventoDeDominio
from farmaexpress.domain.repositories import (
    RepositorioCompradores,
    RepositorioEventos,
    RepositorioPedidos,
    RepositorioProductos,
)


class UnidadDeTrabajo(ABC):
    """Una transacción: o se persiste todo o nada."""

    pedidos: RepositorioPedidos
    compradores: RepositorioCompradores
    productos: RepositorioProductos
    eventos: RepositorioEventos

    def __enter__(self) -> UnidadDeTrabajo:
        return self

    def __exit__(
        self, tipo: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> None:
        self.rollback()  # no-op si ya se hizo commit

    @abstractmethod
    def commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...


class PublicadorDeEventos(ABC):
    @abstractmethod
    def publicar(self, eventos: list[EventoDeDominio]) -> None: ...
