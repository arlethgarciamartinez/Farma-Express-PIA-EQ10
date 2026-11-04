"""Modelo relacional (SQLAlchemy 2.x) y fábrica de engine."""
from __future__ import annotations

import warnings
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    create_engine,
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SAWarning
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.pool import StaticPool

# SQLite (sólo para pruebas locales) no tiene Decimal nativo; en Postgres no aplica.
warnings.filterwarnings("ignore", message="Dialect sqlite.*Decimal", category=SAWarning)


class Base(DeclarativeBase):
    pass


class CompradorRow(Base):
    __tablename__ = "compradores"
    actor_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    es_preferente: Mapped[bool] = mapped_column(Boolean, default=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    ciudad: Mapped[str] = mapped_column(String(60), default="")


class ProductoRow(Base):
    __tablename__ = "productos"
    recurso_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    descripcion: Mapped[str] = mapped_column(String(150))
    precio_mxn: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    stock: Mapped[int] = mapped_column(Integer)
    habilitado: Mapped[bool] = mapped_column(Boolean, default=True)
    controlado: Mapped[bool] = mapped_column(Boolean, default=False)


class PedidoRow(Base):
    __tablename__ = "pedidos"
    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    comprador_id: Mapped[str] = mapped_column(ForeignKey("compradores.actor_id"), index=True)
    estado: Mapped[str] = mapped_column(String(20), index=True)
    fecha_solicitud: Mapped[date] = mapped_column(Date)
    promocion_activa: Mapped[bool] = mapped_column(Boolean, default=False)
    autorizado: Mapped[bool] = mapped_column(Boolean, default=False)
    referencia: Mapped[str] = mapped_column(String(60), default="")
    receta_fecha: Mapped[date | None] = mapped_column(Date, nullable=True)
    lineas: Mapped[list[LineaRow]] = relationship(
        back_populates="pedido", cascade="all, delete-orphan", lazy="selectin"
    )


class LineaRow(Base):
    __tablename__ = "lineas_pedido"
    pedido_id: Mapped[str] = mapped_column(ForeignKey("pedidos.id"), primary_key=True)
    recurso_id: Mapped[str] = mapped_column(ForeignKey("productos.recurso_id"), primary_key=True)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    cantidad: Mapped[int] = mapped_column(Integer)
    pedido: Mapped[PedidoRow] = relationship(back_populates="lineas")


class EventoRow(Base):
    __tablename__ = "eventos_dominio"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pedido_id: Mapped[str] = mapped_column(String(30), index=True)
    nombre: Mapped[str] = mapped_column(String(60))
    ocurrido_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    payload: Mapped[dict] = mapped_column(JSON)


def crear_engine(url: str) -> Engine:
    if url.startswith("sqlite"):
        kwargs: dict = {"connect_args": {"check_same_thread": False}}
        if ":memory:" in url or url in ("sqlite://", "sqlite:///"):
            kwargs["poolclass"] = StaticPool
        return create_engine(url, **kwargs)
    return create_engine(url, pool_pre_ping=True)
