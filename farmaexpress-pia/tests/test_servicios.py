"""Integración: servicio de aplicación + repositorios SQLAlchemy + bus de eventos."""
import pytest

from farmaexpress.application.consultas import ServicioCatalogo
from farmaexpress.application.servicios import CrearPedido, LineaSolicitada
from farmaexpress.domain import events as ev
from farmaexpress.domain.exceptions import (
    CantidadInvalida,
    PedidoDuplicado,
    RecursoNoEncontrado,
    ReglaDeNegocioIncumplida,
    TransicionInvalida,
)
from farmaexpress.infrastructure.repositorios import SqlUnidadDeTrabajo


def _crear(servicio, comprador="FAR-C001", lineas=(("FAR-P009", 3),), **kw):
    return servicio.crear_pedido(
        CrearPedido(comprador, [LineaSolicitada(r, q) for r, q in lineas], **kw)
    )


def test_flujo_completo_persiste_estado_stock_y_eventos(servicio, bus, datos_cargados):
    p = _crear(servicio, autorizado=True)
    assert p.total.monto == 3057  # 3 x 1019
    for paso in ("validar", "preparar", "entregar"):
        getattr(servicio, paso)(p.id)
    assert servicio.obtener(p.id).estado.value == "ENTREGADO"
    with SqlUnidadDeTrabajo(datos_cargados) as uow:
        assert uow.productos.obtener("FAR-P009").stock == 34  # 37 - 3
    nombres = [e["evento"] for e in servicio.eventos_de(p.id)]
    assert nombres == ["PedidoCreado", "PedidoValidado", "PedidoPreparado", "PedidoEntregado"]
    assert [type(e) for e in bus.publicados] == [
        ev.PedidoCreado, ev.PedidoValidado, ev.PedidoPreparado, ev.PedidoEntregado,
    ]


def test_eventos_no_se_publican_si_la_operacion_falla(servicio, bus):
    p = _crear(servicio, autorizado=False)
    antes = len(bus.publicados)
    with pytest.raises(ReglaDeNegocioIncumplida):
        servicio.validar(p.id)
    assert len(bus.publicados) == antes
    assert servicio.obtener(p.id).estado.value == "CREADO"


def test_suscriptor_roto_no_revierte_la_operacion(servicio, bus):
    def roto(_):
        raise RuntimeError("boom")

    bus.suscribir(ev.PedidoCreado, roto)
    p = _crear(servicio)
    assert servicio.obtener(p.id).id == p.id


def test_errores_de_referencia_y_duplicados(servicio):
    with pytest.raises(RecursoNoEncontrado):
        _crear(servicio, comprador="NOPE")
    with pytest.raises(RecursoNoEncontrado):
        _crear(servicio, lineas=(("NOPE", 1),))
    with pytest.raises(RecursoNoEncontrado):
        servicio.obtener("NOPE")
    with pytest.raises(RecursoNoEncontrado):
        servicio.agregar_linea("NOPE", "FAR-P001", 1)
    p = _crear(servicio)
    with pytest.raises(RecursoNoEncontrado):
        servicio.agregar_linea(p.id, "NOPE", 1)
    with pytest.raises(PedidoDuplicado):
        servicio.crear_pedido(CrearPedido("FAR-C001", pedido_id=p.id))


@pytest.mark.parametrize("cantidad", [0, -1])
def test_cantidad_invalida(servicio, cantidad):
    with pytest.raises(CantidadInvalida):
        _crear(servicio, lineas=(("FAR-P001", cantidad),))


def test_stock_insuficiente_impide_validar(servicio):
    p = _crear(servicio, lineas=(("FAR-P015", 11),), autorizado=True)  # stock 10
    with pytest.raises(ReglaDeNegocioIncumplida) as exc:
        servicio.validar(p.id)
    assert "stock_suficiente" in exc.value.fallos


def test_producto_deshabilitado_impide_validar(servicio):
    p = _crear(servicio, lineas=(("FAR-P011", 1),), autorizado=True)
    with pytest.raises(ReglaDeNegocioIncumplida) as exc:
        servicio.validar(p.id)
    assert exc.value.fallos == ["producto_habilitado"]


def test_cancelar_y_transiciones_invalidas(servicio):
    p = _crear(servicio, autorizado=True)
    servicio.cancelar(p.id)
    for accion in ("validar", "preparar", "entregar", "cancelar"):
        with pytest.raises(TransicionInvalida):
            getattr(servicio, accion)(p.id)


def test_agregar_linea_y_listar_por_estado(servicio):
    p = servicio.crear_pedido(CrearPedido("FAR-C001", autorizado=True))
    assert servicio.evaluar(p.id).puede_procesarse is False  # detalle vacío
    servicio.agregar_linea(p.id, "FAR-P001", 2)
    servicio.agregar_linea(p.id, "FAR-P001", 1)
    actualizado = servicio.obtener(p.id)
    assert actualizado.lineas[0].cantidad.valor == 3
    assert servicio.evaluar(p.id).puede_procesarse is True
    assert p.id in [x.id for x in servicio.listar("CREADO")]
    assert servicio.listar("ENTREGADO") == []


def test_catalogo(datos_cargados):
    cat = ServicioCatalogo(lambda: SqlUnidadDeTrabajo(datos_cargados))
    assert len(cat.compradores()) == 40 and len(cat.productos()) == 20
    assert cat.comprador("FAR-C001").ciudad == "Monterrey"
    assert str(cat.producto("FAR-P001").precio.monto) == "451.00"
    with pytest.raises(RecursoNoEncontrado):
        cat.comprador("X")
    with pytest.raises(RecursoNoEncontrado):
        cat.producto("X")


def test_carga_csv_es_idempotente_y_respeta_conteos(datos_cargados):
    from farmaexpress.infrastructure.carga_csv import cargar_datos
    from tests.conftest import DATOS

    with datos_cargados() as s:
        assert cargar_datos(s, DATOS) == {}  # ya había datos


def test_carga_csv_conteos(fabrica):
    from farmaexpress.infrastructure.carga_csv import cargar_datos
    from tests.conftest import DATOS

    with fabrica() as s:
        assert cargar_datos(s, DATOS) == {
            "compradores": 40, "productos": 20, "pedidos": 60, "lineas": 117,
        }


def test_rollback_si_falla_a_mitad(datos_cargados):
    with SqlUnidadDeTrabajo(datos_cargados) as uow:
        producto = uow.productos.obtener("FAR-P001")
        producto.stock = 0
        uow.productos.guardar(producto)
        # sin commit -> se descarta
    with SqlUnidadDeTrabajo(datos_cargados) as uow:
        assert uow.productos.obtener("FAR-P001").stock == 13
