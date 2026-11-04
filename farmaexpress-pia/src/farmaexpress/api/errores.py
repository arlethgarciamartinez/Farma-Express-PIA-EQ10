"""Traducción excepción de dominio -> código HTTP (ADR-006)."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from farmaexpress.domain.exceptions import (
    ConflictoDeEstado,
    ErrorDeDominio,
    ErrorDeValidacion,
    RecursoNoEncontrado,
    ReglaDeNegocioIncumplida,
)

_MAPA: list[tuple[type[ErrorDeDominio], int, str]] = [
    (ErrorDeValidacion, 400, "DATOS_INVALIDOS"),
    (RecursoNoEncontrado, 404, "NO_ENCONTRADO"),
    (ConflictoDeEstado, 409, "CONFLICTO_DE_ESTADO"),
    (ReglaDeNegocioIncumplida, 422, "REGLA_DE_NEGOCIO"),
]


def _respuesta(status: int, codigo: str, detalle: str, reglas: list[str] | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"codigo": codigo, "detalle": detalle, "reglas_incumplidas": reglas or []},
    )


def registrar_manejadores(app: FastAPI) -> None:
    @app.exception_handler(ErrorDeDominio)
    async def _dominio(_: Request, exc: ErrorDeDominio) -> JSONResponse:
        for tipo, status, codigo in _MAPA:
            if isinstance(exc, tipo):
                return _respuesta(status, codigo, str(exc), getattr(exc, "fallos", None))
        return _respuesta(500, "ERROR_INTERNO", str(exc))

    @app.exception_handler(RequestValidationError)
    async def _validacion(_: Request, exc: RequestValidationError) -> JSONResponse:
        detalle = "; ".join(f"{'.'.join(map(str, e['loc'][1:]))}: {e['msg']}" for e in exc.errors())
        return _respuesta(400, "DATOS_INVALIDOS", detalle)
