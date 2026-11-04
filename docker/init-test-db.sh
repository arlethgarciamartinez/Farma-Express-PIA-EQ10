#!/bin/sh
# Crea una BD aparte para las pruebas de integración (no toca los datos de la app).
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-SQL
  CREATE DATABASE ${POSTGRES_TEST_DB:-farmaexpress_test};
SQL
