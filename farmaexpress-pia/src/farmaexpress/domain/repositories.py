"""Puertos de persistencia (interfaces). Las implementaciones viven en infrastructure."""
from __future__ import annotations

from abc import ABC, abstractmethod

from .entities import Comprador, Producto
from .events import EventoDeDominio
from .pedido import Pedido


class RepositorioCompradores(ABC):
    @abstractmethod
    def obtener(self, actor_id: str) -> Comprador | None: ...

    @abstractmethod
    def listar(self) -> list[Comprador]: ...


class RepositorioProductos(ABC):
    @abstractmethod
    def obtener(self, recurso_id: str) -> Producto | None: ...

    @abstractmethod
    def obtener_varios(self, ids: list[str]) -> dict[str, Producto]: ...

    @abstractmethod
    def listar(self) -> list[Producto]: ...

    @abstractmethod
    def guardar(self, producto: Producto) -> None: ...


class RepositorioPedidos(ABC):
    @abstractmethod
    def obtener(self, pedido_id: str) -> Pedido | None: ...

    @abstractmethod
    def listar(self, estado: str | None = None) -> list[Pedido]: ...

    @abstractmethod
    def guardar(self, pedido: Pedido) -> None: ...


class RepositorioEventos(ABC):
    @abstractmethod
    def registrar(self, eventos: list[EventoDeDominio]) -> None: ...

    @abstractmethod
    def de_pedido(self, pedido_id: str) -> list[dict]: ...
