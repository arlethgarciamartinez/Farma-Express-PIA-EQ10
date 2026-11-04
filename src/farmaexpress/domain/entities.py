"""Entidades de referencia: Comprador (actor) y Producto farmacéutico."""
from __future__ import annotations

from dataclasses import dataclass

from .exceptions import CantidadInvalida, StockInsuficiente
from .value_objects import Cantidad, Dinero


@dataclass
class Comprador:
    actor_id: str
    nombre: str
    activo: bool = True
    es_preferente: bool = False
    ciudad: str = ""


@dataclass
class Producto:
    recurso_id: str
    descripcion: str
    precio: Dinero
    stock: int
    habilitado: bool = True
    controlado: bool = False  # extensión BRD: medicamento controlado (requiere receta)

    def __post_init__(self) -> None:
        if self.stock < 0:
            raise CantidadInvalida("El stock no puede ser negativo")

    def tiene_stock_para(self, cantidad: Cantidad | int) -> bool:
        n = cantidad.valor if isinstance(cantidad, Cantidad) else cantidad
        return self.stock >= n

    def descontar(self, cantidad: Cantidad) -> None:
        if not self.tiene_stock_para(cantidad):
            raise StockInsuficiente(
                f"{self.recurso_id}: stock {self.stock} < solicitado {cantidad.valor}",
                ["stock_suficiente"],
            )
        self.stock -= cantidad.valor
