"""Pruebas unitarias del dominio (sin BD ni HTTP)."""
from datetime import date, timedelta
from decimal import Decimal

import pytest

from farmaexpress.domain import events as ev
from farmaexpress.domain.entities import Comprador, Producto
from farmaexpress.domain.exceptions import (
    CantidadInvalida,
    ConflictoDeEstado,
    ImporteInvalido,
    ReglaDeNegocioIncumplida,
    StockInsuficiente,
    TransicionInvalida,
)
from farmaexpress.domain.pedido import LineaPedido, Pedido
from farmaexpress.domain.reglas import BENEFICIO_REFERENCIA, PUEDE_PROCESARSE, PUEDE_VALIDARSE
from farmaexpress.domain.specifications import (
    ContextoPedido,
    ContieneControlado,
    ExcedeLimiteControlado,
    RecetaVigente,
    Specification,
)
from farmaexpress.domain.state_machine import MAQUINA_PEDIDO, Accion, EstadoPedido
from farmaexpress.domain.value_objects import Cantidad, Dinero

HOY = date(2026, 11, 4)


def dinero(x) -> Dinero:
    return Dinero(Decimal(str(x)))


def prod(rid="P1", precio="100", stock=10, habilitado=True, controlado=False) -> Producto:
    return Producto(rid, rid, dinero(precio), stock, habilitado, controlado)


def pedido(lineas=(("P1", "100", 1),), **kw) -> Pedido:
    return Pedido(
        "O1",
        "C1",
        HOY,
        [LineaPedido(r, dinero(p), Cantidad(q)) for r, p, q in lineas],
        **kw,
    )


def comprador(activo=True, preferente=False) -> Comprador:
    return Comprador("C1", "Ana", activo, preferente, "Monterrey")


def ctx(p: Pedido, c: Comprador | None = None, productos=None) -> ContextoPedido:
    return ContextoPedido(p, c or comprador(), productos or {}, HOY)


# ------------------------------------------------------------ value objects
class TestValueObjects:
    def test_dinero_redondea_a_centavos(self):
        assert Dinero(Decimal("10.005")).monto == Decimal("10.01")

    def test_dinero_suma_y_multiplica_sin_error_de_float(self):
        total = dinero("0.10") + dinero("0.20")
        assert total.monto == Decimal("0.30")
        assert dinero("451.00").por(Cantidad(3)).monto == Decimal("1353.00")

    @pytest.mark.parametrize("malo", [Decimal("-1"), "abc", Decimal("NaN"), Decimal("Infinity")])
    def test_dinero_rechaza_invalidos(self, malo):
        with pytest.raises(ImporteInvalido):
            Dinero(malo)

    def test_dinero_acepta_cadena_numerica_y_str(self):
        assert Dinero("5").monto == Decimal("5.00")
        assert str(Dinero("5")) == "5.00 MXN"

    @pytest.mark.parametrize("malo", [0, -3, 1.5, "2", True, None])
    def test_cantidad_rechaza_no_positivos_o_no_enteros(self, malo):
        with pytest.raises(CantidadInvalida):
            Cantidad(malo)

    def test_cantidad_valida(self):
        assert Cantidad(4).valor == 4


# ----------------------------------------------------------- specifications
class TestSpecifications:
    def test_puede_procesarse_requiere_las_tres_condiciones(self):
        ok = pedido(autorizado=True)
        assert PUEDE_PROCESARSE.is_satisfied_by(ctx(ok))
        assert not PUEDE_PROCESARSE.is_satisfied_by(ctx(ok, comprador(activo=False)))
        assert not PUEDE_PROCESARSE.is_satisfied_by(ctx(pedido(autorizado=False)))
        assert not PUEDE_PROCESARSE.is_satisfied_by(ctx(pedido(lineas=(), autorizado=True)))

    def test_fallos_explican_que_regla_no_se_cumple(self):
        p = pedido(lineas=(), autorizado=False)
        assert PUEDE_PROCESARSE.fallos(ctx(p, comprador(activo=False))) == [
            "cliente_activo",
            "detalle_no_vacio",
            "autorizacion",
        ]
        assert PUEDE_PROCESARSE.fallos(ctx(pedido(autorizado=True))) == []

    @pytest.mark.parametrize(
        ("precio", "pref", "promo", "esperado"),
        [
            ("1500", True, False, True),  # límite inclusivo
            ("1499.99", True, False, False),
            ("1500", False, False, False),
            ("1500", True, True, False),
            ("2000", True, True, False),
        ],
    )
    def test_beneficio_referencia(self, precio, pref, promo, esperado):
        p = pedido(lineas=(("P1", precio, 1),), promocion_activa=promo)
        assert BENEFICIO_REFERENCIA.is_satisfied_by(ctx(p, comprador(preferente=pref))) is esperado

    def test_not_fallos_se_nombran(self):
        p = pedido(promocion_activa=True)
        assert "NOT promocion_activa" in BENEFICIO_REFERENCIA.fallos(ctx(p, comprador(preferente=True), None))[-1]

    def test_operadores_and_or_not_son_composables(self):
        class Siempre(Specification):
            nombre = "T"

            def is_satisfied_by(self, c):
                return True

        class Nunca(Specification):
            nombre = "F"

            def is_satisfied_by(self, c):
                return False

        c = ctx(pedido())
        t, f = Siempre(), Nunca()
        assert (t & t).is_satisfied_by(c) and not (t & f).is_satisfied_by(c)
        assert (t | f).is_satisfied_by(c) and not (f | f).is_satisfied_by(c)
        assert (~f).is_satisfied_by(c) and not (~t).is_satisfied_by(c)
        # De Morgan: NOT(a AND b) == NOT a OR NOT b
        for a in (t, f):
            for b in (t, f):
                assert (~(a & b)).is_satisfied_by(c) == ((~a) | (~b)).is_satisfied_by(c)
        assert (f | f).fallos(c) == ["F", "F"]
        assert (f | t).fallos(c) == []
        assert (f & t).nombre == "(F AND T)"

    def test_receta_vigente_30_dias(self):
        assert RecetaVigente().is_satisfied_by(ctx(pedido(receta_fecha=HOY - timedelta(days=30))))
        assert not RecetaVigente().is_satisfied_by(ctx(pedido(receta_fecha=HOY - timedelta(days=31))))
        assert not RecetaVigente().is_satisfied_by(ctx(pedido(receta_fecha=HOY + timedelta(days=1))))
        assert not RecetaVigente().is_satisfied_by(ctx(pedido()))

    def test_limite_controlado_10_piezas_o_3000(self):
        s = ExcedeLimiteControlado()
        assert not s.is_satisfied_by(ctx(pedido(lineas=(("P1", "300", 10),))))
        assert s.is_satisfied_by(ctx(pedido(lineas=(("P1", "10", 11),))))
        assert s.is_satisfied_by(ctx(pedido(lineas=(("P1", "3000.01", 1),))))

    def test_contiene_controlado(self):
        p = pedido()
        assert ContieneControlado().is_satisfied_by(ctx(p, productos={"P1": prod(controlado=True)}))
        assert not ContieneControlado().is_satisfied_by(ctx(p, productos={"P1": prod()}))

    def test_precondiciones_de_validacion(self):
        p = pedido(autorizado=True)
        buenos = {"P1": prod()}
        assert PUEDE_VALIDARSE.is_satisfied_by(ctx(p, productos=buenos))
        assert not PUEDE_VALIDARSE.is_satisfied_by(ctx(p, productos={"P1": prod(habilitado=False)}))
        assert not PUEDE_VALIDARSE.is_satisfied_by(ctx(p, productos={"P1": prod(stock=0)}))
        assert not PUEDE_VALIDARSE.is_satisfied_by(ctx(p, productos={}))  # producto desconocido

    def test_controlado_exige_receta_y_autorizacion_por_limite(self):
        ctrl = {"P1": prod(controlado=True)}
        sin_receta = pedido(autorizado=True)
        assert not PUEDE_VALIDARSE.is_satisfied_by(ctx(sin_receta, productos=ctrl))
        con_receta = pedido(autorizado=True, receta_fecha=HOY - timedelta(days=5))
        assert PUEDE_VALIDARSE.is_satisfied_by(ctx(con_receta, productos=ctrl))
        excede_sin_auth = pedido(lineas=(("P1", "400", 11),), autorizado=False, receta_fecha=HOY)
        # sin autorización ya falla PUEDE_PROCESARSE; se comprueba la regla de límite sola:
        from farmaexpress.domain.reglas import LIMITE_CONTROLADO_AUTORIZADO

        assert not LIMITE_CONTROLADO_AUTORIZADO.is_satisfied_by(ctx(excede_sin_auth, productos=ctrl))
        assert LIMITE_CONTROLADO_AUTORIZADO.is_satisfied_by(ctx(excede_sin_auth, productos={"P1": prod()}))


# ----------------------------------------------------------- state machine
class TestMaquinaDeEstados:
    def test_flujo_feliz(self):
        e = EstadoPedido.CREADO
        for a, esperado in [
            (Accion.VALIDAR, EstadoPedido.VALIDADO),
            (Accion.PREPARAR, EstadoPedido.PREPARADO),
            (Accion.ENTREGAR, EstadoPedido.ENTREGADO),
        ]:
            e = MAQUINA_PEDIDO.siguiente(e, a)
            assert e is esperado

    def test_cancelacion_solo_desde_creado(self):
        assert MAQUINA_PEDIDO.siguiente(EstadoPedido.CREADO, Accion.CANCELAR) is EstadoPedido.CANCELADO
        for e in (EstadoPedido.VALIDADO, EstadoPedido.PREPARADO, EstadoPedido.ENTREGADO):
            with pytest.raises(TransicionInvalida):
                MAQUINA_PEDIDO.siguiente(e, Accion.CANCELAR)

    @pytest.mark.parametrize("estado", list(EstadoPedido))
    @pytest.mark.parametrize("accion", list(Accion))
    def test_matriz_completa_solo_4_transiciones_legales(self, estado, accion):
        legales = {
            (EstadoPedido.CREADO, Accion.VALIDAR),
            (EstadoPedido.VALIDADO, Accion.PREPARAR),
            (EstadoPedido.PREPARADO, Accion.ENTREGAR),
            (EstadoPedido.CREADO, Accion.CANCELAR),
        }
        if (estado, accion) in legales:
            MAQUINA_PEDIDO.siguiente(estado, accion)
        else:
            with pytest.raises(TransicionInvalida) as exc:
                MAQUINA_PEDIDO.siguiente(estado, accion)
            assert estado.value in str(exc.value)

    def test_estados_finales_y_acciones(self):
        assert MAQUINA_PEDIDO.es_final(EstadoPedido.ENTREGADO)
        assert MAQUINA_PEDIDO.es_final(EstadoPedido.CANCELADO)
        assert not MAQUINA_PEDIDO.es_final(EstadoPedido.CREADO)
        assert set(MAQUINA_PEDIDO.acciones_permitidas(EstadoPedido.CREADO)) == {
            Accion.VALIDAR,
            Accion.CANCELAR,
        }


# ------------------------------------------------------------ agregado
class TestPedido:
    def test_total_con_decimal(self):
        p = pedido(lineas=(("A", "451.00", 3), ("B", "1019.00", 4)))
        assert p.total.monto == Decimal("5429.00")
        assert p.piezas == 7

    def test_crear_emite_evento_y_reconstituir_no(self):
        p = Pedido.crear("O9", "C1", HOY, [])
        assert [type(e) for e in p.extraer_eventos()] == [ev.PedidoCreado]
        assert p.extraer_eventos() == []
        assert pedido().extraer_eventos() == []

    def test_flujo_completo_emite_eventos_en_orden_y_descuenta_stock(self):
        p = pedido(lineas=(("P1", "1000", 2),), autorizado=True)
        c = comprador(preferente=True)
        productos = {"P1": prod(stock=5)}
        p.validar(c, productos, HOY)
        p.preparar(c, productos, HOY)
        p.entregar(c)
        assert p.estado is EstadoPedido.ENTREGADO
        assert productos["P1"].stock == 3
        eventos = p.extraer_eventos()
        assert [type(e) for e in eventos] == [ev.PedidoValidado, ev.PedidoPreparado, ev.PedidoEntregado]
        assert eventos[-1].beneficio_referencia is True
        assert eventos[-1].payload()["total"] == "2000.00"

    def test_validar_con_regla_incumplida_es_422_y_no_cambia_estado(self):
        p = pedido(autorizado=False)
        with pytest.raises(ReglaDeNegocioIncumplida) as exc:
            p.validar(comprador(), {"P1": prod()}, HOY)
        assert exc.value.fallos == ["autorizacion"]
        assert p.estado is EstadoPedido.CREADO
        assert p.extraer_eventos() == []

    def test_transicion_ilegal_tiene_prioridad_sobre_reglas(self):
        p = pedido(autorizado=False)  # también incumpliría reglas
        with pytest.raises(TransicionInvalida):
            p.entregar(comprador())
        with pytest.raises(TransicionInvalida):
            p.preparar(comprador(), {"P1": prod()}, HOY)

    def test_no_se_valida_dos_veces(self):
        p = pedido(autorizado=True)
        p.validar(comprador(), {"P1": prod()}, HOY)
        with pytest.raises(TransicionInvalida):
            p.validar(comprador(), {"P1": prod()}, HOY)

    def test_preparar_sin_stock_falla_y_no_descuenta(self):
        p = pedido(lineas=(("P1", "10", 3),), autorizado=True)
        c = comprador()
        p.validar(c, {"P1": prod(stock=5)}, HOY)
        agotado = {"P1": prod(stock=1)}
        with pytest.raises(ReglaDeNegocioIncumplida):
            p.preparar(c, agotado, HOY)
        assert agotado["P1"].stock == 1 and p.estado is EstadoPedido.VALIDADO

    def test_cancelar_emite_evento(self):
        p = pedido()
        p.cancelar()
        assert p.estado is EstadoPedido.CANCELADO
        assert [type(e) for e in p.extraer_eventos()] == [ev.PedidoCancelado]

    def test_agregar_linea_acumula_cantidad_y_solo_en_creado(self):
        p = pedido(lineas=())
        p.agregar_linea(prod("P1", "50"), Cantidad(2))
        p.agregar_linea(prod("P1", "50"), Cantidad(3))
        assert len(p.lineas) == 1 and p.lineas[0].cantidad.valor == 5
        p.cancelar()
        with pytest.raises(ConflictoDeEstado):
            p.agregar_linea(prod("P1"), Cantidad(1))


class TestProducto:
    def test_descontar(self):
        x = prod(stock=3)
        x.descontar(Cantidad(2))
        assert x.stock == 1
        with pytest.raises(StockInsuficiente):
            x.descontar(Cantidad(2))

    def test_stock_negativo_invalido(self):
        with pytest.raises(CantidadInvalida):
            prod(stock=-1)
