"""Excepciones del dominio.

Cada excepción lleva el código HTTP que la capa API le asigna (ADR-006), pero
el dominio no depende de HTTP: sólo expresa *qué* tipo de fallo es.
"""
from __future__ import annotations


class ErrorDeDominio(Exception):
    """Raíz de todas las excepciones del dominio."""


class ErrorDeValidacion(ErrorDeDominio):
    """Dato mal formado (cantidad <= 0, importe negativo...). -> 400"""


class CantidadInvalida(ErrorDeValidacion):
    pass


class ImporteInvalido(ErrorDeValidacion):
    pass


class RecursoNoEncontrado(ErrorDeDominio):
    """Entidad inexistente. -> 404"""

    def __init__(self, tipo: str, identificador: str) -> None:
        super().__init__(f"{tipo} '{identificador}' no existe")
        self.tipo = tipo
        self.identificador = identificador


class ConflictoDeEstado(ErrorDeDominio):
    """El estado actual no admite la operación. -> 409"""


class TransicionInvalida(ConflictoDeEstado):
    def __init__(self, estado: str, accion: str) -> None:
        super().__init__(f"No se puede '{accion}' un pedido en estado {estado}")
        self.estado = estado
        self.accion = accion


class PedidoDuplicado(ConflictoDeEstado):
    pass


class PedidoNoEditable(ConflictoDeEstado):
    def __init__(self, estado: str) -> None:
        super().__init__(f"Sólo se editan pedidos CREADO (actual: {estado})")
        self.estado = estado


class ReglaDeNegocioIncumplida(ErrorDeDominio):
    """Se cumplen los datos y el estado, pero no una regla de negocio. -> 422"""

    def __init__(self, mensaje: str, fallos: list[str] | None = None) -> None:
        super().__init__(mensaje)
        self.fallos = fallos or []


class StockInsuficiente(ReglaDeNegocioIncumplida):
    pass
