"""Ejecuta los 120 casos y las 20 transiciones del paquete contra un oráculo independiente.

El oráculo se calcula directamente de los CSV con Python plano (sin usar el dominio),
de modo que una regresión en las Specifications haría fallar estas pruebas.
"""
from decimal import Decimal

import pytest

from farmaexpress.infrastructure.carga_csv import leer_csv
from farmaexpress.infrastructure.ejecutor_casos import (
    SECUENCIAS,
    construir_servicio,
    ejecutar_casos,
    ejecutar_transiciones,
    main,
)
from tests.conftest import DATOS


def _oraculo():
    actores = {r["actor_id"]: r for r in leer_csv(DATOS / "actores.csv")}
    precios = {r["recurso_id"]: Decimal(r["precio_mxn"]) for r in leer_csv(DATOS / "catalogo.csv")}
    lineas: dict[str, list] = {}
    for r in leer_csv(DATOS / "detalle_operaciones.csv"):
        lineas.setdefault(r["operacion_id"], []).append((r["recurso_id"], int(r["cantidad"])))
    ops = {r["operacion_id"]: r for r in leer_csv(DATOS / "operaciones.csv")}
    esperado = {}
    for oid, op in ops.items():
        a = actores[op["actor_id"]]
        total = sum((precios[rid] * q for rid, q in lineas.get(oid, [])), Decimal("0"))
        esperado[oid] = {
            "validar_operacion": a["activo"] == "1" and len(lineas.get(oid, [])) > 0 and op["autorizado"] == "1",
            "evaluar_beneficio": a["es_preferente"] == "1" and total >= 1500 and op["promocion_activa"] == "0",
        }
    return esperado


@pytest.fixture(scope="module")
def resultados(tmp_path_factory):
    servicio = construir_servicio("sqlite://", str(DATOS))
    return ejecutar_casos(servicio, DATOS), ejecutar_transiciones(servicio, DATOS)


def test_120_casos_coinciden_con_el_oraculo(resultados):
    casos, _ = resultados
    esperado = _oraculo()
    assert len(casos) == 120
    errores = [
        c["caso_id"]
        for c in casos
        if (c["resultado_alumno"] == "TRUE") != esperado[c["operacion_id"]][c["tipo_prueba"]]
    ]
    assert errores == []
    assert {c["resultado_alumno"] for c in casos} <= {"TRUE", "FALSE"}
    assert all(c["evidencia"] for c in casos)


def test_los_casos_cubren_ambos_resultados(resultados):
    casos, _ = resultados
    for tipo in ("validar_operacion", "evaluar_beneficio"):
        assert {c["resultado_alumno"] for c in casos if c["tipo_prueba"] == tipo} == {"TRUE", "FALSE"}


def test_20_transiciones_con_estado_final_o_excepcion(resultados):
    _, trans = resultados
    assert len(trans) == 20
    por_accion = {}
    for t in trans:
        por_accion.setdefault(t["accion_sugerida"], []).append(t["resultado_alumno"])
    # saltar_estado y repetir_aprobacion NUNCA pueden terminar bien
    assert all(r.startswith("EXCEPCION") for r in por_accion["saltar_estado"])
    assert all(r.startswith("EXCEPCION") for r in por_accion["repetir_aprobacion"])
    assert all("(409)" in r or "(422)" in r for r in por_accion["saltar_estado"] + por_accion["repetir_aprobacion"])
    # cancelar siempre es legal desde CREADO
    assert all(r == "OK estado_final=CANCELADO" for r in por_accion["cancelar"])
    # aprobar / completar: OK o 422 por reglas (cliente inactivo, no autorizado, producto deshabilitado)
    for r in por_accion["aprobar"] + por_accion["completar"]:
        assert r.startswith("OK") or "(422)" in r


def test_transicion_coincide_con_oraculo_de_reglas(resultados):
    """aprobar sólo funciona si se cumplen precondiciones; si no, el estado sigue CREADO."""
    _, trans = resultados
    esperado = _oraculo()
    actores = {r["actor_id"]: r for r in leer_csv(DATOS / "actores.csv")}
    ops = {r["operacion_id"]: r for r in leer_csv(DATOS / "operaciones.csv")}
    det = {r["operacion_id"]: r["recurso_id"] for r in leer_csv(DATOS / "detalle_operaciones.csv")}
    for t in trans:
        if t["accion_sugerida"] != "aprobar":
            continue
        base = esperado[t["operacion_id"]]["validar_operacion"]
        lineas_p011 = any(
            r["operacion_id"] == t["operacion_id"] and r["recurso_id"] == "FAR-P011"
            for r in leer_csv(DATOS / "detalle_operaciones.csv")
        )
        debe_pasar = base and not lineas_p011
        assert t["resultado_alumno"].startswith("OK") == debe_pasar, t
    assert actores and ops and det  # datos presentes


def test_secuencias_cubren_todas_las_acciones_del_csv():
    acciones = {r["accion_sugerida"] for r in leer_csv(DATOS / "transiciones_prueba.csv")}
    assert acciones <= set(SECUENCIAS)


def test_cli_genera_csv_de_resultados(tmp_path, monkeypatch):
    monkeypatch.setattr("sys.argv", ["x", "--datos", str(DATOS), "--salida", str(tmp_path)])
    main()
    for nombre in ("casos_prueba_resultado.csv", "transiciones_resultado.csv"):
        filas = leer_csv(tmp_path / nombre)
        assert filas and "evidencia" in filas[0] and "PENDIENTE" not in {f["resultado_alumno"] for f in filas}
