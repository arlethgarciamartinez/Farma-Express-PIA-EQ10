# ADR-007 — Persistencia y configuración

**Estado:** Aceptada

- **PostgreSQL 16** en Docker Compose; **SQLAlchemy 2.x** como ORM, aislado en `infrastructure` (el dominio no lo conoce).
- Los repositorios traducen filas ↔ objetos de dominio; el ORM nunca sale de la capa.
- **SQLite en memoria** sólo para pruebas rápidas locales; con `TEST_DATABASE_URL` las mismas pruebas corren contra
  PostgreSQL (CI y servicio `tests` de Compose, BD `farmaexpress_test` separada de la de la app).
- Importes `Numeric(12,2)` ↔ `Decimal` (nunca `float`).
- **12-Factor:** toda configuración viene del entorno (`config.Settings`, `.env.example`); el `.env` real no se versiona.
  Compose inyecta `DATABASE_URL` hacia el servicio `db`.
- **Esquema:** `create_all` al arrancar (`AUTO_CREATE_SCHEMA`). Para producción se recomienda Alembic (no incluido por alcance).
- Carga de datos: `SEED_ON_STARTUP=true` importa `datos/*.csv` sólo si la BD está vacía (idempotente).
