"""Fixtures. Por defecto SQLite en memoria; con TEST_DATABASE_URL usa PostgreSQL (CI / Docker)."""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from farmaexpress.api.main import crear_app
from farmaexpress.application.servicios import ServicioPedidos
from farmaexpress.config import Settings
from farmaexpress.infrastructure.bus import BusDeEventosEnMemoria
from farmaexpress.infrastructure.carga_csv import cargar_datos
from farmaexpress.infrastructure.db import Base, crear_engine
from farmaexpress.infrastructure.repositorios import SqlUnidadDeTrabajo

DATOS = Path(__file__).resolve().parent.parent / "datos"


@pytest.fixture
def engine():
    eng = crear_engine(os.environ.get("TEST_DATABASE_URL", "sqlite://"))
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def fabrica(engine):
    return sessionmaker(engine, expire_on_commit=False)


@pytest.fixture
def datos_cargados(fabrica):
    with fabrica() as s:
        cargar_datos(s, DATOS)
    return fabrica


@pytest.fixture
def bus():
    return BusDeEventosEnMemoria()


@pytest.fixture
def servicio(datos_cargados, bus):
    return ServicioPedidos(lambda: SqlUnidadDeTrabajo(datos_cargados), bus)


@pytest.fixture
def client(engine, datos_cargados):
    app = crear_app(Settings(database_url="sqlite://", seed_on_startup=False), engine=engine)
    with TestClient(app) as c:
        yield c
