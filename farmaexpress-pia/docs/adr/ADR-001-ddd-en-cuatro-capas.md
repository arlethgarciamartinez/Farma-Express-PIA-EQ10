# ADR-001 — DDD en cuatro capas

**Estado:** Aceptada · **Contexto U3:** continúa el ADR-001 (Domain Model) del repo `farmaexpress-arquitectura`.

## Contexto
Las reglas (precondiciones, estados, límites) cambian con el negocio y deben poder probarse sin BD ni HTTP.

## Decisión
`src/farmaexpress/` se divide en:

| Capa | Contenido | Puede importar |
|---|---|---|
| `domain` | Value Objects (`Dinero`, `Cantidad`), entidades, agregado `Pedido`, Specifications, máquina de estados, Domain Events, puertos de repositorio | nada externo |
| `application` | `ServicioPedidos` (un método por caso de uso), `ServicioCatalogo` (consultas), puertos `UnidadDeTrabajo` y `PublicadorDeEventos` | `domain` |
| `infrastructure` | SQLAlchemy, repositorios, UoW, bus en memoria, carga CSV | `domain`, `application` |
| `api` | Controllers FastAPI, DTOs Pydantic, traducción de errores | `application`, `domain` |

`Pedido` es la raíz del agregado; `LineaPedido` sólo se modifica a través de ella. El precio de la línea es
un *snapshot* del catálogo al momento de crear/agregar.

## SOLID
- **S**: cada Specification una regla; el servicio sólo orquesta; los controllers sólo traducen.
- **O**: nuevas reglas = nuevas clases/composiciones, sin tocar las existentes (p. ej. `RecetaVigente`).
- **L**: cualquier `Specification` es intercambiable en una composición.
- **I**: puertos de repositorio pequeños por agregado.
- **D**: `application` depende de abstracciones (`UnidadDeTrabajo`); la implementación SQL se inyecta en `api/main.py` (composition root).

## Consecuencias
`tests/test_arquitectura.py` analiza los imports (AST) y falla si `domain` importa `sqlalchemy`/`fastapi`/`pydantic`
o si una capa interna importa una externa.

**Compromiso consciente:** `Pedido.preparar()` descuenta stock de `Producto` (otro agregado) dentro de una misma
transacción. Es aceptable aquí porque el descuento es una invariante de la misma operación; con concurrencia alta
habría que añadir bloqueo optimista (`version`) en `Producto`.
