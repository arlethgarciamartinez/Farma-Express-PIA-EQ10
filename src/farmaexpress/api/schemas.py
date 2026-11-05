"""DTOs HTTP (Pydantic). Nunca se expone una entidad de dominio directamente."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from farmaexpress.application.mensajes import resumen_pedido, siguiente_paso
from farmaexpress.domain.entities import Comprador, Producto
from farmaexpress.domain.pedido import Pedido
from farmaexpress.domain.state_machine import MAQUINA_PEDIDO


class LineaIn(BaseModel):
    recurso_id: str = Field(min_length=1, examples=["FAR-P001"])
    cantidad: int = Field(gt=0, examples=[2], description="Entero > 0")


class PedidoIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "comprador_id": "FAR-C001",
            "lineas": [{"recurso_id": "FAR-P009", "cantidad": 3}],
            "autorizado": True,
        }
    })
    comprador_id: str = Field(min_length=1)
    lineas: list[LineaIn] = Field(default_factory=list)
    promocion_activa: bool = False
    autorizado: bool = False
    referencia: str = ""
    receta_fecha: date | None = None


class LineaOut(BaseModel):
    recurso_id: str
    precio_unitario: Decimal
    cantidad: int
    subtotal: Decimal


class PedidoOut(BaseModel):
    resumen: str = Field(description="Explicación en lenguaje claro del estado del pedido")
    siguiente_paso: str = Field(description="Qué se puede hacer ahora con este pedido")
    id: str
    comprador_id: str
    estado: str
    fecha_solicitud: date
    promocion_activa: bool
    autorizado: bool
    referencia: str
    receta_fecha: date | None
    lineas: list[LineaOut]
    total: Decimal
    acciones_permitidas: list[str]

    @classmethod
    def desde(cls, p: Pedido) -> PedidoOut:
        return cls(
            resumen=resumen_pedido(p),
            siguiente_paso=siguiente_paso(p.estado),
            id=p.id,
            comprador_id=p.comprador_id,
            estado=p.estado.value,
            fecha_solicitud=p.fecha_solicitud,
            promocion_activa=p.promocion_activa,
            autorizado=p.autorizado,
            referencia=p.referencia,
            receta_fecha=p.receta_fecha,
            lineas=[
                LineaOut(
                    recurso_id=ln.recurso_id,
                    precio_unitario=ln.precio_unitario.monto,
                    cantidad=ln.cantidad.valor,
                    subtotal=ln.subtotal.monto,
                )
                for ln in p.lineas
            ],
            total=p.total.monto,
            acciones_permitidas=[a.value for a in MAQUINA_PEDIDO.acciones_permitidas(p.estado)],
        )


class EvaluacionOut(BaseModel):
    conclusion_procesamiento: str = Field(description="¿Se puede procesar el pedido? Con el porqué")
    conclusion_beneficio: str = Field(description="¿Aplica el beneficio de cliente preferente? Con el porqué")
    motivos_no_procesable: list[str]
    motivos_sin_beneficio: list[str]
    pedido_id: str
    total: Decimal
    puede_procesarse: bool
    beneficio_referencia: bool
    fallos_procesamiento: list[str]
    fallos_beneficio: list[str]


class EventoOut(BaseModel):
    descripcion: str = Field(description="Qué ocurrió, en lenguaje claro")
    evento: str
    ocurrido_en: str
    datos: dict


class CompradorOut(BaseModel):
    actor_id: str
    nombre: str
    activo: bool
    es_preferente: bool
    ciudad: str

    @classmethod
    def desde(cls, c: Comprador) -> CompradorOut:
        return cls(**c.__dict__)


class ProductoOut(BaseModel):
    recurso_id: str
    descripcion: str
    precio_mxn: Decimal
    stock: int
    habilitado: bool
    controlado: bool

    @classmethod
    def desde(cls, p: Producto) -> ProductoOut:
        return cls(
            recurso_id=p.recurso_id,
            descripcion=p.descripcion,
            precio_mxn=p.precio.monto,
            stock=p.stock,
            habilitado=p.habilitado,
            controlado=p.controlado,
        )


class ErrorOut(BaseModel):
    mensaje: str = Field(description="Qué pasó y por qué, en lenguaje claro")
    que_hacer: str = Field(description="Qué puede hacer la persona para resolverlo")
    motivos: list[str] = Field(default_factory=list, description="Cada motivo del rechazo, en una frase")
    codigo: str = Field(description="Código técnico estable (para programadores)")
    detalle: str = Field(description="Detalle técnico (para programadores)")
    reglas_incumplidas: list[str] = Field(default_factory=list, description="Nombres técnicos de las reglas")
