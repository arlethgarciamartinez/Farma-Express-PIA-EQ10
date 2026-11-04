# ADR-002 — Patrón Specification

**Estado:** Aceptada

## Contexto
El paquete exige ≥3 Specifications combinadas con AND/OR/NOT. Las reglas del BRD (receta ≤30 días, límite
10 piezas / $3,000) cambian con la regulación.

## Decisión
`Specification` (clase base abstracta) define `is_satisfied_by(contexto)` y los operadores `&`, `|`, `~`, que
devuelven `AndSpecification`, `OrSpecification` y `NotSpecification`. Además `fallos(contexto)` devuelve los nombres de las
reglas hoja que explican un rechazo (se expone en la API como `reglas_incumplidas`).

Reglas hoja (`domain/specifications.py`): `ActorActivo`, `ActorPreferente`, `DetalleNoVacio`, `Autorizado`,
`PromocionActiva`, `TotalMinimo`, `ProductosHabilitados`, `StockSuficiente`, `ContieneControlado`,
`RecetaVigente`, `ExcedeLimiteControlado`.

Composiciones con nombre (`domain/reglas.py`):

```python
PUEDE_PROCESARSE     = ActorActivo() & DetalleNoVacio() & Autorizado()
BENEFICIO_REFERENCIA = ActorPreferente() & TotalMinimo(1500) & ~PromocionActiva()
VENTA_CONTROLADA_CON_RECETA   = ~ContieneControlado() | RecetaVigente()
LIMITE_CONTROLADO_AUTORIZADO  = ~(ContieneControlado() & ExcedeLimiteControlado()) | Autorizado()
PUEDE_VALIDARSE = PUEDE_PROCESARSE & ProductosHabilitados() & StockSuficiente()
                  & VENTA_CONTROLADA_CON_RECETA & LIMITE_CONTROLADO_AUTORIZADO
```

Las reglas reciben un `ContextoPedido` (pedido + comprador + productos + fecha) para no acoplar la regla a repositorios.
`hoy` se inyecta, así que las reglas de fecha son deterministas en pruebas.

## Alternativas descartadas
- `if` anidados en el servicio (Transaction Script): duplica reglas y no explica el rechazo.
- Reglas en SQL: oculta el negocio en la BD y dificulta las pruebas unitarias.

## Consecuencias
Las reglas de controlados sólo afectan pedidos con productos `controlado=True`; los datos del paquete no los
tienen, así que los oráculos de `puede_procesarse` / `beneficio_referencia` no cambian (ver ADR-005).
