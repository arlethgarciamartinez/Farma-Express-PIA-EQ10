# ADR-006 — Contrato de códigos HTTP

**Estado:** Aceptada

| Código | Cuándo | Excepción de dominio | `codigo` en el cuerpo |
|---|---|---|---|
| 200 | Consulta o acción de estado exitosa | — | — |
| 201 | `POST /pedidos` crea el pedido | — | — |
| 400 | Dato mal formado: cantidad ≤ 0 o no entera, JSON inválido, importe negativo | `ErrorDeValidacion` / validación Pydantic | `DATOS_INVALIDOS` |
| 404 | Pedido, comprador o producto inexistente (también si el cuerpo referencia uno inexistente) | `RecursoNoEncontrado` | `NO_ENCONTRADO` |
| 409 | Transición ilegal (saltar estado, repetir aprobación, cancelar tras validar), editar pedido no `CREADO`, ID duplicado | `ConflictoDeEstado` | `CONFLICTO_DE_ESTADO` |
| 422 | Datos y estado correctos pero una regla de negocio falla (inactivo, sin autorización, sin stock, producto deshabilitado, receta vencida) | `ReglaDeNegocioIncumplida` | `REGLA_DE_NEGOCIO` + `reglas_incumplidas[]` |

Precedencia: **400 → 404 → 409 → 422**. FastAPI devuelve 422 por defecto en validación de esquema; se sobreescribe a
400 para reservar 422 a las reglas de negocio. El cuerpo de error siempre es `{mensaje, que_hacer, motivos, codigo, detalle, reglas_incumplidas}`
(`ErrorOut`), documentado en OpenAPI para cada endpoint. `mensaje`, `que_hacer` y `motivos` están en lenguaje claro
(ADR-008); `codigo`, `detalle` y `reglas_incumplidas` son técnicos y estables.
