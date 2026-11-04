"""Composición de Specifications = reglas de negocio con nombre propio.

Aquí sólo se *componen* reglas; la lógica de cada una vive en
``specifications.py``.
"""
from decimal import Decimal

from .specifications import (
    ActorActivo,
    ActorPreferente,
    Autorizado,
    ContieneControlado,
    DetalleNoVacio,
    ExcedeLimiteControlado,
    ProductosHabilitados,
    PromocionActiva,
    RecetaVigente,
    Specification,
    StockSuficiente,
    TotalMinimo,
)

UMBRAL_BENEFICIO = Decimal("1500")

# Regla 1 del paquete: actor activo AND detalle no vacío AND autorización
PUEDE_PROCESARSE: Specification = ActorActivo() & DetalleNoVacio() & Autorizado()

# Regla 2 del paquete: preferente AND total >= 1500 AND NOT promoción
BENEFICIO_REFERENCIA: Specification = (
    ActorPreferente() & TotalMinimo(UMBRAL_BENEFICIO) & ~PromocionActiva()
)

# Extensiones del BRD (US-03, US-04): sólo aplican a medicamentos controlados.
VENTA_CONTROLADA_CON_RECETA: Specification = ~ContieneControlado() | RecetaVigente()
LIMITE_CONTROLADO_AUTORIZADO: Specification = (
    ~(ContieneControlado() & ExcedeLimiteControlado()) | Autorizado()
)

EXISTENCIA_Y_CATALOGO: Specification = ProductosHabilitados() & StockSuficiente()

# Guarda de la transición CREADO -> VALIDADO
PUEDE_VALIDARSE: Specification = (
    PUEDE_PROCESARSE
    & EXISTENCIA_Y_CATALOGO
    & VENTA_CONTROLADA_CON_RECETA
    & LIMITE_CONTROLADO_AUTORIZADO
)

# Guarda de la transición VALIDADO -> PREPARADO (el stock pudo cambiar)
PUEDE_PREPARARSE: Specification = EXISTENCIA_Y_CATALOGO
