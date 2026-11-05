"""Traducción excepción de dominio -> código HTTP + mensaje claro (ADR-006, ADR-008)."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from farmaexpress.application.mensajes import Explicacion, explicar_error, explicar_validacion
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


def _respuesta(
    status: int, codigo: str, explicacion: Explicacion, detalle: str, reglas: list[str] | None = None
) -> JSONResponse:
    # Primero lo que entiende cualquier persona; después los campos técnicos para desarrolladores.
    return JSONResponse(
        status_code=status,
        content={
            "mensaje": explicacion.mensaje,
            "que_hacer": explicacion.que_hacer,
            "motivos": explicacion.motivos,
            "codigo": codigo,
            "detalle": detalle,
            "reglas_incumplidas": reglas or [],
        },
    )


def registrar_manejadores(app: FastAPI) -> None:
    @app.exception_handler(ErrorDeDominio)
    async def _dominio(_: Request, exc: ErrorDeDominio) -> JSONResponse:
        for tipo, status, codigo in _MAPA:
            if isinstance(exc, tipo):
                return _respuesta(status, codigo, explicar_error(exc), str(exc), getattr(exc, "fallos", None))
        return _respuesta(500, "ERROR_INTERNO", explicar_error(exc), str(exc))

    @app.exception_handler(RequestValidationError)
    async def _validacion(_: Request, exc: RequestValidationError) -> JSONResponse:
        tecnico = "; ".join(f"{'.'.join(map(str, e['loc'][1:]))}: {e['msg']}" for e in exc.errors())
        return _respuesta(400, "DATOS_INVALIDOS", explicar_validacion(list(exc.errors())), tecnico)
