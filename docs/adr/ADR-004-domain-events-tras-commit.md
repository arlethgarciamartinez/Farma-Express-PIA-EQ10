# ADR-004 — Domain Events: registro transaccional, publicación tras commit

**Estado:** Aceptada · Continúa el ADR-003 de `farmaexpress-arquitectura` ("eventos tras commit").

## Decisión
1. El agregado acumula eventos (`PedidoCreado`, `PedidoValidado`, `PedidoPreparado`, `PedidoEntregado`, `PedidoCancelado`)
   y los entrega con `extraer_eventos()` (vacía la lista, evitando doble publicación).
2. El servicio **persiste** pedido + eventos (`eventos_dominio`, con `payload` JSON) en la **misma transacción**.
3. Sólo después del `commit` llama a `PublicadorDeEventos.publicar()`. Si algo falla antes, no se publica nada
   (`test_eventos_no_se_publican_si_la_operacion_falla`).
4. `BusDeEventosEnMemoria` aísla fallos de suscriptores (se loguean; no revierten la venta).

La tabla `eventos_dominio` sirve de bitácora de auditoría (`GET /pedidos/{id}/eventos`) y es un paso hacia un
*outbox* si en el futuro se publican a un broker.

## Consecuencias
Entrega *at-most-once* hacia suscriptores en memoria (si el proceso muere entre commit y publicar, el evento queda
en la tabla pero no se despacha). Aceptable para el alcance; el outbox lo resolvería.
