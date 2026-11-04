"""Controllers REST. Sin lógica de negocio: traducen HTTP <-> casos de uso."""
from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from farmaexpress.application.consultas import ServicioCatalogo
from farmaexpress.application.servicios import CrearPedido, LineaSolicitada, ServicioPedidos

from .schemas import (
    CompradorOut,
    ErrorOut,
    EvaluacionOut,
    EventoOut,
    LineaIn,
    PedidoIn,
    PedidoOut,
    ProductoOut,
)


def _servicio(request: Request) -> ServicioPedidos:
    return request.app.state.servicio_pedidos


def _catalogo(request: Request) -> ServicioCatalogo:
    return request.app.state.servicio_catalogo


Pedidos = Annotated[ServicioPedidos, Depends(_servicio)]
Catalogo = Annotated[ServicioCatalogo, Depends(_catalogo)]

_ERRORES = {
    400: {"model": ErrorOut, "description": "Datos inválidos (p. ej. cantidad <= 0)"},
    404: {"model": ErrorOut, "description": "Recurso inexistente"},
    409: {"model": ErrorOut, "description": "Transición de estado inválida"},
    422: {"model": ErrorOut, "description": "Regla de negocio incumplida"},
}

router = APIRouter()
pedidos = APIRouter(prefix="/pedidos", tags=["Pedidos"], responses=_ERRORES)
catalogo = APIRouter(tags=["Catálogo"], responses={404: _ERRORES[404]})


@router.get("/health", tags=["Operación"])
def health() -> dict[str, str]:
    return {"status": "ok"}


# ---------------------------------------------------------------- pedidos
@pedidos.post("", status_code=201, response_model=PedidoOut, summary="Crear pedido (estado CREADO)")
def crear(body: PedidoIn, svc: Pedidos) -> PedidoOut:
    cmd = CrearPedido(
        comprador_id=body.comprador_id,
        lineas=[LineaSolicitada(ln.recurso_id, ln.cantidad) for ln in body.lineas],
        promocion_activa=body.promocion_activa,
        autorizado=body.autorizado,
        referencia=body.referencia,
        receta_fecha=body.receta_fecha,
    )
    return PedidoOut.desde(svc.crear_pedido(cmd))


@pedidos.get("", response_model=list[PedidoOut], summary="Listar pedidos")
def listar(svc: Pedidos, estado: Annotated[str | None, Query(examples=["CREADO"])] = None) -> list[PedidoOut]:
    return [PedidoOut.desde(p) for p in svc.listar(estado)]


@pedidos.get("/{pedido_id}", response_model=PedidoOut, summary="Consultar pedido")
def obtener(pedido_id: str, svc: Pedidos) -> PedidoOut:
    return PedidoOut.desde(svc.obtener(pedido_id))


@pedidos.post("/{pedido_id}/lineas", response_model=PedidoOut, summary="Agregar línea (sólo CREADO)")
def agregar_linea(pedido_id: str, body: LineaIn, svc: Pedidos) -> PedidoOut:
    return PedidoOut.desde(svc.agregar_linea(pedido_id, body.recurso_id, body.cantidad))


def _accion(nombre: str, resumen: str) -> Callable:
    def endpoint(pedido_id: str, svc: Pedidos) -> PedidoOut:
        return PedidoOut.desde(getattr(svc, nombre)(pedido_id))

    endpoint.__name__ = nombre
    pedidos.post(f"/{{pedido_id}}/{nombre}", response_model=PedidoOut, summary=resumen)(endpoint)
    return endpoint


_accion("validar", "CREADO -> VALIDADO (evalúa precondiciones)")
_accion("preparar", "VALIDADO -> PREPARADO (descuenta stock)")
_accion("entregar", "PREPARADO -> ENTREGADO")
_accion("cancelar", "CREADO -> CANCELADO")


@pedidos.get("/{pedido_id}/evaluacion", response_model=EvaluacionOut, summary="Evalúa las Specifications")
def evaluacion(pedido_id: str, svc: Pedidos) -> EvaluacionOut:
    return EvaluacionOut(**svc.evaluar(pedido_id).__dict__)


@pedidos.get("/{pedido_id}/eventos", response_model=list[EventoOut], summary="Domain Events del pedido")
def eventos(pedido_id: str, svc: Pedidos) -> list[EventoOut]:
    return [EventoOut(**e) for e in svc.eventos_de(pedido_id)]


# --------------------------------------------------------------- catálogo
@catalogo.get("/compradores", response_model=list[CompradorOut])
def compradores(svc: Catalogo) -> list[CompradorOut]:
    return [CompradorOut.desde(c) for c in svc.compradores()]


@catalogo.get("/compradores/{actor_id}", response_model=CompradorOut)
def comprador(actor_id: str, svc: Catalogo) -> CompradorOut:
    return CompradorOut.desde(svc.comprador(actor_id))


@catalogo.get("/productos", response_model=list[ProductoOut])
def productos(svc: Catalogo) -> list[ProductoOut]:
    return [ProductoOut.desde(p) for p in svc.productos()]


@catalogo.get("/productos/{recurso_id}", response_model=ProductoOut)
def producto(recurso_id: str, svc: Catalogo) -> ProductoOut:
    return ProductoOut.desde(svc.producto(recurso_id))
