"""Value Objects: inmutables, se comparan por valor y validan su invariante."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from .exceptions import CantidadInvalida, ImporteInvalido

_CENTAVOS = Decimal("0.01")


@dataclass(frozen=True, order=True)
class Dinero:
    """Importe en MXN con precisión de centavos (nunca float)."""

    monto: Decimal
    moneda: str = "MXN"

    def __post_init__(self) -> None:
        try:
            valor = self.monto if isinstance(self.monto, Decimal) else Decimal(str(self.monto))
        except InvalidOperation as exc:
            raise ImporteInvalido(f"Importe no numérico: {self.monto!r}") from exc
        if not valor.is_finite() or valor < 0:
            raise ImporteInvalido(f"Importe inválido: {valor}")
        object.__setattr__(self, "monto", valor.quantize(_CENTAVOS, ROUND_HALF_UP))

    @classmethod
    def cero(cls) -> Dinero:
        return cls(Decimal("0"))

    def __add__(self, otro: Dinero) -> Dinero:
        return Dinero(self.monto + otro.monto, self.moneda)

    def por(self, cantidad: Cantidad) -> Dinero:
        return Dinero(self.monto * cantidad.valor, self.moneda)

    def __str__(self) -> str:
        return f"{self.monto} {self.moneda}"


@dataclass(frozen=True, order=True)
class Cantidad:
    """Número entero de piezas, estrictamente positivo."""

    valor: int

    def __post_init__(self) -> None:
        if isinstance(self.valor, bool) or not isinstance(self.valor, int) or self.valor <= 0:
            raise CantidadInvalida(f"La cantidad debe ser un entero > 0, se recibió {self.valor!r}")
