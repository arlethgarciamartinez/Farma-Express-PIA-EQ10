"""Domain Events: hechos inmutables ocurridos en el dominio (nombrados en pasado)."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any


def _ahora() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, kw_only=True)
class EventoDeDominio:
    pedido_id: str
    ocurrido_en: datetime = field(default_factory=_ahora)

    @property
    def nombre(self) -> str:
        return type(self).__name__

    def payload(self) -> dict[str, Any]:
        datos = asdict(self)
        datos.pop("ocurrido_en")
        return {k: (str(v) if isinstance(v, Decimal) else v) for k, v in datos.items()}


@dataclass(frozen=True, kw_only=True)
class PedidoCreado(EventoDeDominio):
    comprador_id: str
    total: Decimal


@dataclass(frozen=True, kw_only=True)
class PedidoValidado(EventoDeDominio):
    pass


@dataclass(frozen=True, kw_only=True)
class PedidoPreparado(EventoDeDominio):
    pass


@dataclass(frozen=True, kw_only=True)
class PedidoEntregado(EventoDeDominio):
    total: Decimal
    beneficio_referencia: bool


@dataclass(frozen=True, kw_only=True)
class PedidoCancelado(EventoDeDominio):
    pass
