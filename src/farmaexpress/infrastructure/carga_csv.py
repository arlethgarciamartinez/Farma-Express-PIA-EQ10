"""Importa los CSV del paquete (UTF-8 con BOM) respetando claves foráneas."""
from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .db import CompradorRow, LineaRow, PedidoRow, ProductoRow


def leer_csv(ruta: Path) -> list[dict[str, str]]:
    with open(ruta, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def cargar_datos(session: Session, directorio: str | Path) -> dict[str, int]:
    """Carga idempotente: si ya hay compradores no hace nada."""
    d = Path(directorio)
    if session.scalar(select(func.count()).select_from(CompradorRow)):
        return {}
    n_compradores = 0
    for r in leer_csv(d / "actores.csv"):
        n_compradores += 1
        session.add(
            CompradorRow(
                actor_id=r["actor_id"],
                nombre=r["nombre"],
                es_preferente=r["es_preferente"] == "1",
                activo=r["activo"] == "1",
                ciudad=r["ciudad"],
            )
        )
    precios: dict[str, Decimal] = {}
    for r in leer_csv(d / "catalogo.csv"):
        precios[r["recurso_id"]] = Decimal(r["precio_mxn"])
        session.add(
            ProductoRow(
                recurso_id=r["recurso_id"],
                descripcion=r["descripcion"],
                precio_mxn=precios[r["recurso_id"]],
                stock=int(r["capacidad_o_stock"]),
                habilitado=r["habilitado"] == "1",
            )
        )
    session.flush()
    pedidos: dict[str, PedidoRow] = {}
    for r in leer_csv(d / "operaciones.csv"):
        pedidos[r["operacion_id"]] = PedidoRow(
            id=r["operacion_id"],
            comprador_id=r["actor_id"],
            estado=r["estado_inicial"],
            fecha_solicitud=date.fromisoformat(r["fecha_solicitud"]),
            promocion_activa=r["promocion_activa"] == "1",
            autorizado=r["autorizado"] == "1",
            referencia=r["referencia"],
        )
        session.add(pedidos[r["operacion_id"]])
    session.flush()
    n_lineas = 0
    for r in leer_csv(d / "detalle_operaciones.csv"):
        session.add(
            LineaRow(
                pedido_id=r["operacion_id"],
                recurso_id=r["recurso_id"],
                precio_unitario=precios[r["recurso_id"]],
                cantidad=int(r["cantidad"]),
            )
        )
        n_lineas += 1
    session.commit()
    return {"compradores": n_compradores, "productos": len(precios), "pedidos": len(pedidos), "lineas": n_lineas}
