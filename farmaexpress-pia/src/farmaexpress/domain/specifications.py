"""Patrón Specification (ADR-002).

Cada regla de negocio es una clase pequeña con una sola responsabilidad
(SRP) y se combina con los operadores ``&`` (AND), ``|`` (OR) y ``~`` (NOT)
sin modificar las existentes (OCP).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # evita ciclo: el agregado importa las reglas
    from .entities import Comprador, Producto
    from .pedido import Pedido


@dataclass(frozen=True)
class ContextoPedido:
    """Lo que las reglas necesitan ver: el pedido, su comprador y los productos."""

    pedido: Pedido
    comprador: Comprador
    productos: dict[str, Producto] = field(default_factory=dict)
    hoy: date = field(default_factory=date.today)


class Specification(ABC):
    nombre: str = ""

    @abstractmethod
    def is_satisfied_by(self, c: ContextoPedido) -> bool: ...

    def fallos(self, c: ContextoPedido) -> list[str]:
        """Nombres de las reglas hoja que explican por qué NO se cumple."""
        return [] if self.is_satisfied_by(c) else [self.nombre or type(self).__name__]

    def __and__(self, otra: Specification) -> Specification:
        return AndSpecification(self, otra)

    def __or__(self, otra: Specification) -> Specification:
        return OrSpecification(self, otra)

    def __invert__(self) -> Specification:
        return NotSpecification(self)


class AndSpecification(Specification):
    def __init__(self, izq: Specification, der: Specification) -> None:
        self.izq, self.der = izq, der
        self.nombre = f"({izq.nombre} AND {der.nombre})"

    def is_satisfied_by(self, c: ContextoPedido) -> bool:
        return self.izq.is_satisfied_by(c) and self.der.is_satisfied_by(c)

    def fallos(self, c: ContextoPedido) -> list[str]:
        return self.izq.fallos(c) + self.der.fallos(c)


class OrSpecification(Specification):
    def __init__(self, izq: Specification, der: Specification) -> None:
        self.izq, self.der = izq, der
        self.nombre = f"({izq.nombre} OR {der.nombre})"

    def is_satisfied_by(self, c: ContextoPedido) -> bool:
        return self.izq.is_satisfied_by(c) or self.der.is_satisfied_by(c)

    def fallos(self, c: ContextoPedido) -> list[str]:
        return [] if self.is_satisfied_by(c) else self.izq.fallos(c) + self.der.fallos(c)


class NotSpecification(Specification):
    def __init__(self, interna: Specification) -> None:
        self.interna = interna
        self.nombre = f"NOT {interna.nombre}"

    def is_satisfied_by(self, c: ContextoPedido) -> bool:
        return not self.interna.is_satisfied_by(c)


# ---------------------------------------------------------------- reglas hoja
class ActorActivo(Specification):
    nombre = "cliente_activo"

    def is_satisfied_by(self, c: ContextoPedido) -> bool:
        return c.comprador.activo


class ActorPreferente(Specification):
    nombre = "cliente_preferente"

    def is_satisfied_by(self, c: ContextoPedido) -> bool:
        return c.comprador.es_preferente


class DetalleNoVacio(Specification):
    nombre = "detalle_no_vacio"

    def is_satisfied_by(self, c: ContextoPedido) -> bool:
        return len(c.pedido.lineas) > 0


class Autorizado(Specification):
    nombre = "autorizacion"

    def is_satisfied_by(self, c: ContextoPedido) -> bool:
        return c.pedido.autorizado


class PromocionActiva(Specification):
    nombre = "promocion_activa"

    def is_satisfied_by(self, c: ContextoPedido) -> bool:
        return c.pedido.promocion_activa


class TotalMinimo(Specification):
    """total >= minimo (inclusivo)."""

    def __init__(self, minimo: Decimal) -> None:
        self.minimo = minimo
        self.nombre = f"total>={minimo}"

    def is_satisfied_by(self, c: ContextoPedido) -> bool:
        return c.pedido.total.monto >= self.minimo


class ProductosHabilitados(Specification):
    nombre = "producto_habilitado"

    def is_satisfied_by(self, c: ContextoPedido) -> bool:
        return all(
            (p := c.productos.get(ln.recurso_id)) is not None and p.habilitado
            for ln in c.pedido.lineas
        )


class StockSuficiente(Specification):
    nombre = "stock_suficiente"

    def is_satisfied_by(self, c: ContextoPedido) -> bool:
        return all(
            (p := c.productos.get(ln.recurso_id)) is not None and p.tiene_stock_para(ln.cantidad)
            for ln in c.pedido.lineas
        )


class ContieneControlado(Specification):
    nombre = "contiene_controlado"

    def is_satisfied_by(self, c: ContextoPedido) -> bool:
        return any(
            (p := c.productos.get(ln.recurso_id)) is not None and p.controlado
            for ln in c.pedido.lineas
        )


class RecetaVigente(Specification):
    """BRD US-03: receta presente y con antigüedad <= 30 días."""

    nombre = "receta_vigente"

    def __init__(self, dias: int = 30) -> None:
        self.dias = dias

    def is_satisfied_by(self, c: ContextoPedido) -> bool:
        r = c.pedido.receta_fecha
        return r is not None and 0 <= (c.hoy - r).days <= self.dias


class ExcedeLimiteControlado(Specification):
    """BRD US-04: más de 10 piezas o más de $3,000 MXN."""

    nombre = "excede_limite_controlado"

    def __init__(self, piezas: int = 10, monto: Decimal = Decimal("3000")) -> None:
        self.piezas, self.monto = piezas, monto

    def is_satisfied_by(self, c: ContextoPedido) -> bool:
        return c.pedido.piezas > self.piezas or c.pedido.total.monto > self.monto
