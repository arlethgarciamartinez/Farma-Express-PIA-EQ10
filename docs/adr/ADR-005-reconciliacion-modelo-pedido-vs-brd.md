# ADR-005 — Reconciliar el modelo de pedidos del paquete con el BRD del equipo

**Estado:** Aceptada y **resuelta por el BRD final v2.0** (`docs/BRD_final.md`, §9) · Reemplaza la versión previa de este ADR.

## Contexto (diferencia detectada)
El PIA exige derivar la implementación del BRD/BPMN/Gherkin del equipo (U2/U3) y advierte que el modelo de los CSV es
"propuesto; si difieren, documentar las diferencias y adaptar fixtures y oráculos". Comparados:

| Tema | BRD v1 / BPMN / U3 | Paquete de datos (CSV) |
|---|---|---|
| Proceso | Venta en mostrador (cajero) con receta, lote, caducidad y resurtido | Pedido de comprador |
| Estados | Venta cobrada / rechazada / retenida | CREADO→VALIDADO→PREPARADO→ENTREGADO / CANCELADO |
| Reglas | Receta ≤ 30 días, límite 10 pzas / $3,000 con autorización | activo, detalle no vacío, autorización, preferente ≥ $1,500 sin promoción |
| Inventario | Por lote y sucursal | `capacidad_o_stock` por producto |

## Decisión
**El BRD se refina (no se reemplaza):** el BRD v2.0 conserva íntegros BN-01…BN-10 y US-01…US-18 y agrega, en su §9,
el **pedido de farmacia como formalización de la venta en mostrador**: BN-11…BN-15, US-19…US-27 con Gherkin,
reglas RN-01…RN-10 y supuestos S-1…S-4. Con esto el código **sí se deriva del BRD**: cada regla implementada tiene un ID
en el documento y cada ID tiene prueba (`docs/trazabilidad.md`, verificada por `scripts/verificar_trazabilidad.py`).

1. El agregado `Pedido` implementa el flujo y reglas del paquete → ejecuta los 120 casos y 20 transiciones.
2. Las reglas del BRD v1 que caben en este modelo se implementan como Specifications que sólo aplican a productos
   `controlado=True`: `RecetaVigente` (US-03, RN-04) y `ExcedeLimiteControlado` + `Autorizado` (US-04, RN-05).
3. Lo que no cabe sin rediseñar el dominio queda **declarado como backlog priorizado** (BRD §9.6), no omitido en silencio:
   lotes y caducidad, resurtido, sustitución, transferencias, conteo y reportes.
4. Interpretación de roles: "Autorizado" del CSV = autorización del Responsable de farmacia (supuesto S-2).
   El umbral de $1,500 del beneficio es una política tomada del paquete (supuesto S-1).

## Alternativas descartadas
- *Sólo CSV*: ignora que el BRD es base obligatoria.
- *Sólo BRD v1*: los CSV (oráculos del docente) no podrían ejecutarse sin adaptadores artificiales.
- *Implementar todo el BRD v1*: lotes, sucursales y resurtido exceden el tiempo del PIA; se prioriza un corte vertical completo y probado.

## Consecuencias
- Los oráculos de los CSV no se alteran (no hay controlados en los datos).
- **Riesgo residual:** la cobertura del BRD v1 es parcial (BN-01 y BN-10 parciales). Se mitiga con el backlog explícito; el
  siguiente incremento de menor costo es el Value Object `Receta` completa (US-02, US-03).
- La extensión a lotes reemplazaría `stock` de `Producto` por un agregado `Lote` (ver ADR-002 de `farmaexpress-arquitectura`).
