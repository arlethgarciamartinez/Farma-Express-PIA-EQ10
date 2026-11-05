"""Ejecuta casos_prueba.csv y transiciones_prueba.csv contra el código del equipo.

    python -m farmaexpress.infrastructure.ejecutor_casos --datos datos --salida resultados

Genera los mismos CSV con ``resultado_alumno`` y una columna ``evidencia``.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from sqlalchemy.orm import sessionmaker

from farmaexpress.application.mensajes import (
    conclusion_beneficio,
    conclusion_procesamiento,
    describir_estado,
    dinero,
    explicar_error,
)
from farmaexpress.application.servicios import ServicioPedidos
from farmaexpress.domain.exceptions import (
    ConflictoDeEstado,
    ErrorDeDominio,
    ErrorDeValidacion,
    ReglaDeNegocioIncumplida,
)

from .bus import BusDeEventosEnMemoria
from .carga_csv import cargar_datos, leer_csv
from .db import Base, crear_engine
from .repositorios import SqlUnidadDeTrabajo

SECUENCIAS = {
    "aprobar": ["validar"],
    "completar": ["validar", "preparar", "entregar"],
    "cancelar": ["cancelar"],
    "repetir_aprobacion": ["validar", "validar"],
    "saltar_estado": ["entregar"],  # CREADO -> ENTREGADO sin pasar por VALIDADO/PREPARADO
}


def _codigo_http(exc: ErrorDeDominio) -> int:
    if isinstance(exc, ConflictoDeEstado):
        return 409
    if isinstance(exc, ReglaDeNegocioIncumplida):
        return 422
    if isinstance(exc, ErrorDeValidacion):
        return 400
    return 404


def construir_servicio(database_url: str = "sqlite://", datos: str = "datos") -> ServicioPedidos:
    engine = crear_engine(database_url)
    Base.metadata.create_all(engine)
    fabrica = sessionmaker(engine, expire_on_commit=False)
    with fabrica() as s:
        cargar_datos(s, datos)
    return ServicioPedidos(lambda: SqlUnidadDeTrabajo(fabrica), BusDeEventosEnMemoria())


def _escribir(ruta: Path, filas: list[dict[str, str]]) -> None:
    with open(ruta, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)


def ejecutar_casos(servicio: ServicioPedidos, datos: Path) -> list[dict[str, str]]:
    salida = []
    for caso in leer_csv(datos / "casos_prueba.csv"):
        ev = servicio.evaluar(caso["operacion_id"])
        if caso["tipo_prueba"] == "validar_operacion":
            ok, fallos = ev.puede_procesarse, ev.fallos_procesamiento
            conclusion = conclusion_procesamiento(ok, fallos)
        else:
            ok, fallos = ev.beneficio_referencia, ev.fallos_beneficio
            conclusion = conclusion_beneficio(ok, fallos)
        caso["resultado_alumno"] = "TRUE" if ok else "FALSE"
        caso["evidencia"] = f"total={ev.total} MXN; reglas_incumplidas={fallos or 'ninguna'}"
        caso["explicacion"] = f"Pedido {ev.pedido_id} (total {dinero(ev.total)}). {conclusion}"
        salida.append(caso)
    return salida


def ejecutar_transiciones(servicio: ServicioPedidos, datos: Path) -> list[dict[str, str]]:
    salida = []
    for caso in leer_csv(datos / "transiciones_prueba.csv"):
        pid, accion = caso["operacion_id"], caso["accion_sugerida"]
        inicial = servicio.obtener(pid).estado
        try:
            for paso in SECUENCIAS[accion]:
                getattr(servicio, paso)(pid)
            final = servicio.obtener(pid).estado
            caso["resultado_alumno"] = f"OK estado_final={final.value}"
            caso["evidencia"] = f"eventos={[e['evento'] for e in servicio.eventos_de(pid)]}"
            caso["explicacion"] = f"Todo salió bien con el pedido {pid}: ahora está {describir_estado(final)}."
        except ErrorDeDominio as exc:
            final = servicio.obtener(pid).estado
            caso["resultado_alumno"] = f"EXCEPCION {type(exc).__name__} ({_codigo_http(exc)}) estado_final={final.value}"
            detalle = f"{exc}" + (f" reglas={exc.fallos}" if getattr(exc, "fallos", None) else "")
            caso["evidencia"] = f"{detalle}; eventos={[e['evento'] for e in servicio.eventos_de(pid)]}"
            ex = explicar_error(exc)
            avance = (
                f" El pedido avanzó hasta {describir_estado(final)} y ahí se detuvo." if final != inicial else ""
            )
            caso["explicacion"] = (
                f"No se pudo completar la acción en el pedido {pid}. {ex.mensaje}{avance} {ex.que_hacer}"
            )
        salida.append(caso)
    return salida


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--datos", default="datos")
    p.add_argument("--salida", default="resultados")
    a = p.parse_args()
    datos, out = Path(a.datos), Path(a.salida)
    out.mkdir(parents=True, exist_ok=True)
    servicio = construir_servicio(datos=a.datos)
    casos = ejecutar_casos(servicio, datos)
    trans = ejecutar_transiciones(servicio, datos)
    _escribir(out / "casos_prueba_resultado.csv", casos)
    _escribir(out / "transiciones_resultado.csv", trans)
    print(f"{len(casos)} casos y {len(trans)} transiciones ejecutados -> {out}/")


if __name__ == "__main__":
    main()
