# ADR-005 — Reconciliar el modelo de pedidos del paquete con el BRD del equipo

**Estado:** Aceptada · **Requiere validación del docente**

## Contexto (diferencia detectada)
El PIA exige derivar la implementación del BRD/BPMN/Gherkin del equipo (U2/U3) y advierte que el modelo de los CSV es
"propuesto". Comparados:

| Tema | BRD / BPMN / U3 (equipo) | Paquete de datos (CSV) |
|---|---|---|
| Proceso | Venta en mostrador (cajero) con receta, lote, caducidad y resurtido | Pedido de comprador |
| Estados | Venta cobrada / rechazada / retenida por autorización | CREADO→VALIDADO→PREPARADO→ENTREGADO / CANCELADO |
| Reglas | Receta ≤30 días, límite 10 pzas / $3,000 con autorización del Responsable, lote vigente | cliente activo, detalle no vacío, autorización, preferente ≥$1,500 sin promoción |
| Inventario | Por lote y sucursal | `capacidad_o_stock` por producto |

## Decisión
**Pedido como núcleo + extensiones del BRD.**
1. El agregado `Pedido` implementa el flujo y las reglas del paquete (permite ejecutar los 120 casos y 20 transiciones).
2. Las reglas propias del BRD que caben en este modelo se implementan como Specifications adicionales y se activan sólo
   con productos `controlado=True`: `RecetaVigente` (US-03), `ExcedeLimiteControlado` + `Autorizado` (US-04).
3. Lo que **no** cabe sin rediseñar el dominio queda **fuera de este incremento** y documentado en
   `docs/trazabilidad.md`: lotes/caducidad por sucursal (US-07/08/09), resurtido y órdenes de compra (US-12/13),
   sustitución (US-05/06), transferencias y reportes.
4. Reinterpretación de roles: "Autorizado" del CSV equivale a la autorización del Responsable de farmacia del BRD.

## Alternativas descartadas
- *Sólo CSV*: ignora la regla del PIA de que el BRD es base obligatoria.
- *Sólo BRD*: los CSV (oráculos del docente) no podrían ejecutarse sin adaptadores artificiales.

## Consecuencias
Los oráculos de los CSV no se alteran (sin productos controlados en los datos). La extensión a lotes/resurtido sería un
agregado `Lote` (ya diseñado en `farmaexpress-arquitectura`, ADR-002) que reemplaza `stock` en `Producto`.
