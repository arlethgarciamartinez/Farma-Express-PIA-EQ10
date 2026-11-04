"""Composition root. Arranque: uvicorn --factory farmaexpress.api.main:crear_app"""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from farmaexpress.application.consultas import ServicioCatalogo
from farmaexpress.application.servicios import ServicioPedidos
from farmaexpress.config import Settings
from farmaexpress.infrastructure.bus import BusDeEventosEnMemoria
from farmaexpress.infrastructure.carga_csv import cargar_datos
from farmaexpress.infrastructure.db import Base, crear_engine
from farmaexpress.infrastructure.repositorios import SqlUnidadDeTrabajo

from .errores import registrar_manejadores
from .routers import catalogo, pedidos, router

DESCRIPCION = """
API de **FarmaExpress** (Equipo 10, FIME-UANL). Flujo del pedido:
`CREADO → VALIDADO → PREPARADO → ENTREGADO` y `CREADO → CANCELADO`.

Contrato de errores: **400** datos inválidos · **404** no existe ·
**409** transición inválida · **422** regla de negocio incumplida.
"""


def crear_app(settings: Settings | None = None, engine: Engine | None = None) -> FastAPI:
    settings = settings or Settings()
    logging.basicConfig(level=settings.log_level)
    engine = engine or crear_engine(settings.database_url)
    fabrica = sessionmaker(engine, expire_on_commit=False)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if settings.auto_create_schema:
            Base.metadata.create_all(engine)
        if settings.seed_on_startup:
            with fabrica() as s:
                cargar_datos(s, settings.data_dir)
        yield
        engine.dispose()

    app = FastAPI(
        title="FarmaExpress API",
        version="1.0.0",
        description=DESCRIPCION,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    uow = lambda: SqlUnidadDeTrabajo(fabrica)  # noqa: E731
    app.state.bus = BusDeEventosEnMemoria()
    app.state.servicio_pedidos = ServicioPedidos(uow, app.state.bus)
    app.state.servicio_catalogo = ServicioCatalogo(uow)
    registrar_manejadores(app)
    app.include_router(router)
    app.include_router(pedidos)
    app.include_router(catalogo)
    return app
