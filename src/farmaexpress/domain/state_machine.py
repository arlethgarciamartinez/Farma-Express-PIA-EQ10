"""Máquina de estados del pedido, dirigida por tabla (ADR-003).

CREADO -> VALIDADO -> PREPARADO -> ENTREGADO
CREADO -> CANCELADO

La máquina sólo responde "¿es legal esta transición?"; las precondiciones de
negocio (Specifications) las evalúa el agregado antes de invocarla.
"""
from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum

from .exceptions import TransicionInvalida


class EstadoPedido(StrEnum):
    CREADO = "CREADO"
    VALIDADO = "VALIDADO"
    PREPARADO = "PREPARADO"
    ENTREGADO = "ENTREGADO"
    CANCELADO = "CANCELADO"


class Accion(StrEnum):
    VALIDAR = "validar"
    PREPARAR = "preparar"
    ENTREGAR = "entregar"
    CANCELAR = "cancelar"


TRANSICIONES_PEDIDO: Mapping[tuple[EstadoPedido, Accion], EstadoPedido] = {
    (EstadoPedido.CREADO, Accion.VALIDAR): EstadoPedido.VALIDADO,
    (EstadoPedido.VALIDADO, Accion.PREPARAR): EstadoPedido.PREPARADO,
    (EstadoPedido.PREPARADO, Accion.ENTREGAR): EstadoPedido.ENTREGADO,
    (EstadoPedido.CREADO, Accion.CANCELAR): EstadoPedido.CANCELADO,
}


class MaquinaDeEstados:
    def __init__(self, transiciones: Mapping[tuple[EstadoPedido, Accion], EstadoPedido]) -> None:
        self._transiciones = dict(transiciones)

    def siguiente(self, estado: EstadoPedido, accion: Accion) -> EstadoPedido:
        try:
            return self._transiciones[(estado, accion)]
        except KeyError:
            raise TransicionInvalida(estado.value, accion.value) from None

    def acciones_permitidas(self, estado: EstadoPedido) -> list[Accion]:
        return [a for (e, a) in self._transiciones if e == estado]

    def es_final(self, estado: EstadoPedido) -> bool:
        return not self.acciones_permitidas(estado)


MAQUINA_PEDIDO = MaquinaDeEstados(TRANSICIONES_PEDIDO)
