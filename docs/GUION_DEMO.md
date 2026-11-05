# Guion de demostración y defensa (≈ 8 minutos)

Los pedidos de ejemplo vienen de `datos/` y los resultados de cada paso fueron verificados contra la API real.
Prepara todo **antes** de la clase: `cp .env.example .env` · `docker compose up --build -d` · abrir `http://localhost:8000/docs`.

## Parte 1 — Arquitectura y requisitos (2 min)
1. **Trazabilidad:** abrir `docs/trazabilidad.md`: "cada regla del BRD (BN → US → RN) apunta a un componente y a una prueba; un script en el CI falla si una referencia se rompe".
2. **Capas:** mostrar `docs/diagramas.md` (clases + capas). "El dominio no importa a nadie; un test lo verifica."
3. **ADRs:** `docs/adr/` — mencionar ADR-005 (por qué pedido + extensiones del BRD).

## Parte 2 — API en vivo (4 min, Swagger en `/docs`)
| # | Acción | Resultado esperado | Qué decir |
|---|---|---|---|
| 1 | `GET /pedidos/FAR-O002/evaluacion` | `puede_procesarse: true`, `beneficio_referencia: true` (total 7,559.00) | Specifications AND/NOT: preferente ∧ total ≥ 1500 ∧ ¬promoción |
| 2 | `POST /pedidos/FAR-O002/validar` | 200 · `VALIDADO` | Guarda = `PUEDE_VALIDARSE` |
| 3 | `POST /pedidos/FAR-O002/preparar` | 200 · `PREPARADO` | Descuenta existencia (ver `GET /productos`) |
| 4 | `POST /pedidos/FAR-O002/entregar` | 200 · `ENTREGADO` | Cierra la venta |
| 5 | `GET /pedidos/FAR-O002/eventos` | `PedidoValidado`, `PedidoPreparado`, `PedidoEntregado` (`beneficio_referencia: true`) | Domain Events persistidos. Los pedidos importados de CSV no traen `PedidoCreado`; uno creado con `POST /pedidos` sí. |
| 6 | `POST /pedidos/FAR-O004/entregar` | **409** | Saltar de CREADO a ENTREGADO: máquina de estados |
| 7 | `POST /pedidos/FAR-O028/validar` | **422** · `["cliente_activo"]` | La regla incumplida se explica |
| 8 | `POST /pedidos/FAR-O005/validar` | **422** · `["producto_habilitado"]` | El catálogo bloquea FAR-P011 |
| 9 | `POST /pedidos/FAR-O013/validar` | **422** · `["detalle_no_vacio"]` | Pedido sin líneas |
| 10 | `POST /pedidos` con `cantidad: 0` | **400** | Validación de datos (≠ regla de negocio) |
| 11 | `GET /pedidos/NOPE` | **404** | Contrato 400/404/409/422 (ADR-006) |

Si prefieres terminal: `curl -X POST http://localhost:8000/pedidos/FAR-O002/validar` (y análogos).

## Parte 3 — Calidad y despliegue (2 min)
1. **GitHub → Actions → último CI en verde:** lint, 97 pruebas sobre PostgreSQL, cobertura 97.96 % (mínimo 80 %), trazabilidad, casos CSV, job de Docker Compose.
2. `docker compose --profile test run --rm tests` (opcional en vivo) — pruebas dentro de Compose.
3. `resultados/casos_prueba_resultado.csv` y `transiciones_resultado.csv`: los 120 casos y 20 transiciones del paquete.

## Preguntas probables y cómo responder
| Pregunta | Respuesta corta |
|---|---|
| ¿Dónde está el patrón Specification? | `domain/specifications.py` (11 reglas hoja + And/Or/Not); composiciones con nombre en `domain/reglas.py`. |
| ¿Cómo combinan AND/OR/NOT? | Operadores `&`, `\|`, `~`. Ej.: `BENEFICIO_REFERENCIA = ActorPreferente() & TotalMinimo(1500) & ~PromocionActiva()`. Test de De Morgan. |
| ¿Por qué la máquina de estados es una tabla? | 5 estados × 4 acciones se verifican exhaustivamente; la guarda de negocio va aparte (ADR-003). |
| ¿Diferencia entre 409 y 422? | 409: el estado no admite la acción. 422: el estado sí, pero una regla de negocio falla. 400: dato mal formado. |
| ¿Por qué publican eventos después del commit? | Para no avisar de algo que luego se revierte (ADR-004); hay test que lo demuestra. |
| ¿Cómo garantizan que el dominio no depende de la BD? | `tests/test_arquitectura.py` analiza los imports y falla si `domain` importa SQLAlchemy/FastAPI. |
| Su BRD habla de venta con lotes; ¿por qué pedidos? | El paquete del PIA define el modelo de pedidos. El BRD v2.0 lo formaliza como la venta en mostrador (BN-11…14) y deja lotes/resurtido como backlog priorizado (§9.6, ADR-005). |
| ¿Qué NO implementaron? | Lotes/caducidad, resurtido, sustitución, transferencias, conteo y reportes; receta completa (sólo vigencia) y roles (autorización como bandera). Está en `trazabilidad.md` §3. |
| ¿Por qué `Decimal`? | Importes en MXN sin error de `float`; `Dinero` redondea a centavos. |
| ¿Cómo prueban contra Postgres y SQLite? | Misma suite; con `TEST_DATABASE_URL` corre en Postgres (CI y Compose). |
| ¿Cómo se aplica 12-Factor? | Configuración por variables (`.env.example`, `config.py`); el `.env` real no se versiona. |
| ¿Qué mejorarían primero? | Value Object `Receta` completa (US-02/03), luego agregado `Lote`; los eventos ya permiten colgar el resurtido. |
| Limitaciones honestas | Sin migraciones Alembic (usa `create_all`); sin concurrencia optimista en el stock; bus de eventos en memoria. |
