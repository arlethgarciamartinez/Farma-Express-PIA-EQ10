# FarmaExpress — PIA Componentes de Lógica de Negocios (Equipo 10)

[![CI](https://github.com/arlethgarciamartinez/Farma-Express-PIA-EQ10/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/arlethgarciamartinez/Farma-Express-PIA-EQ10/actions/workflows/ci.yml)

FIME-UANL · Arleth García Martínez, Ángel Mauricio Castruita Márquez, Carlos Patricio Lozano Treviño.
Sistema de pedidos de farmacia con **DDD + Specification + State Machine + Domain Events**, API REST documentada (OpenAPI),
PostgreSQL, Docker Compose y CI en GitHub Actions.

> **Requerimientos:** [BRD final v2.0](docs/BRD_final.md) (26 historias con Gherkin, reglas RN-01…RN-09) ·
> **Trazabilidad:** [BRD → regla → componente → prueba](docs/trazabilidad.md) ·
> **Alcance y diferencias:** [ADR-005](docs/adr/ADR-005-reconciliacion-modelo-pedido-vs-brd.md) · **Backlog:** BRD §9.6.

## Arquitectura
```
src/farmaexpress/
  domain/          Value Objects, entidades, agregado Pedido, Specifications, state machine, eventos, puertos
  application/     ServicioPedidos (casos de uso), ServicioCatalogo (consultas), puertos UoW / eventos
  infrastructure/  SQLAlchemy, repositorios, UoW, bus de eventos, carga CSV, ejecutor de casos
  api/             FastAPI: routers, schemas, traducción de errores, composition root
tests/             unit (dominio) · integración (servicios, API, CSV) · arquitectura
docs/              BRD_final.md · trazabilidad.md · adr/ADR-001…007
scripts/           verificar_trazabilidad.py (referencias de la matriz)
datos/             CSV del paquete    resultados/            salida del ejecutor de casos
```
Flujo del pedido: `CREADO → VALIDADO → PREPARADO → ENTREGADO` · `CREADO → CANCELADO`.

## Ejecutar con Docker Compose (DB + App + Tests)
```bash
cp .env.example .env                 # ajusta la contraseña
docker compose up --build -d         # db + app (carga los CSV al arrancar)
open http://localhost:8000/docs      # Swagger UI  (también /redoc, /openapi.json)
docker compose --profile test run --rm tests    # pruebas + cobertura sobre PostgreSQL
docker compose down -v
```

## Ejecutar localmente (sin Docker)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env                 # DATABASE_URL apunta a SQLite
uvicorn --factory farmaexpress.api.main:crear_app --reload
pytest                               # SQLite en memoria; falla si cobertura < 80 %
TEST_DATABASE_URL=postgresql+psycopg://user:pass@localhost/farmaexpress_test pytest   # contra PostgreSQL
ruff check .
```

## Casos de prueba del paquete (120 + 20)
```bash
python -m farmaexpress.infrastructure.ejecutor_casos --datos datos --salida resultados
```
Genera `resultados/casos_prueba_resultado.csv` y `transiciones_resultado.csv` con `resultado_alumno` y `evidencia`.
`tests/test_casos_csv.py` compara los 120 resultados contra un oráculo calculado con Python plano desde los CSV.

## API (resumen)
| Método y ruta | Resultado |
|---|---|
| `POST /pedidos` | 201 pedido `CREADO` |
| `GET /pedidos`, `GET /pedidos/{id}` | 200 / 404 |
| `POST /pedidos/{id}/lineas` | agrega línea (sólo `CREADO`) |
| `POST /pedidos/{id}/validar \| preparar \| entregar \| cancelar` | 200 / 404 / 409 / 422 |
| `GET /pedidos/{id}/evaluacion` | resultado de las Specifications + reglas incumplidas |
| `GET /pedidos/{id}/eventos` | Domain Events persistidos |
| `GET /compradores`, `/productos` (+ `/{id}`) | catálogo |

Errores: 400 datos inválidos · 404 no existe · 409 transición inválida · 422 regla de negocio ([ADR-006](docs/adr/ADR-006-contrato-http-de-errores.md)).

## Calidad
Cobertura actual ≈ 98 % (mínimo exigido 80 %, forzado en `pyproject.toml` y en CI). CI: `.github/workflows/ci.yml`.
