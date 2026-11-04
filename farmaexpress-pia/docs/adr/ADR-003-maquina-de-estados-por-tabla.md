# ADR-003 — Máquina de estados dirigida por tabla

**Estado:** Aceptada

## Decisión
```
CREADO ──validar──▶ VALIDADO ──preparar──▶ PREPARADO ──entregar──▶ ENTREGADO
  └─────cancelar──▶ CANCELADO
```
`state_machine.py` contiene únicamente la tabla `(estado, acción) → estado` y `MaquinaDeEstados.siguiente()`,
que lanza `TransicionInvalida` (→ 409). `ENTREGADO` y `CANCELADO` son finales (sin salidas).

Las **guardas** (Specifications) no viven en la máquina sino en el agregado, y se evalúan **después** de comprobar
que la transición es legal. Orden de precedencia: *transición legal (409) → reglas de negocio (422) → efectos*.

Efectos: `validar` registra `PedidoValidado`; `preparar` descuenta stock y registra `PedidoPreparado`;
`entregar` registra `PedidoEntregado` (con `beneficio_referencia`); `cancelar` registra `PedidoCancelado`.

## Por qué tabla y no `State` pattern
Con 5 estados y 4 acciones, una tabla es verificable exhaustivamente: `test_matriz_completa_solo_4_transiciones_legales`
recorre las 5×4 combinaciones y comprueba que sólo 4 son legales.

## Supuesto a validar con el docente
La cancelación sólo se permite desde `CREADO` (flujo de referencia del paquete). Si el BRD pide cancelar un pedido
`VALIDADO`, basta añadir una fila a la tabla (y liberar stock si ya estuviera `PREPARADO`).
