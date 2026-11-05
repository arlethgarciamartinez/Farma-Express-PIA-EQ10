"""Verifica que la matriz de trazabilidad no cite pruebas ni IDs inexistentes.

    python scripts/verificar_trazabilidad.py     (código de salida 1 si hay referencias rotas)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
TRAZA = (RAIZ / "docs" / "trazabilidad.md").read_text(encoding="utf-8")
BRD = (RAIZ / "docs" / "BRD_final.md").read_text(encoding="utf-8")


def pruebas_citadas() -> set[tuple[str, str]]:
    return set(re.findall(r"`(test_\w+)::(\w+)", TRAZA))


def ids(texto: str, prefijo: str) -> set[str]:
    return set(re.findall(rf"\b{prefijo}-\d{{2}}\b", texto))


def main() -> int:
    errores: list[str] = []
    for archivo, prueba in sorted(pruebas_citadas()):
        ruta = RAIZ / "tests" / f"{archivo}.py"
        if not ruta.exists():
            errores.append(f"archivo de prueba inexistente: {archivo}")
        elif not re.search(rf"def {re.escape(prueba)}\b", ruta.read_text(encoding="utf-8")):
            errores.append(f"prueba inexistente: {archivo}::{prueba}")
    for prefijo in ("BN", "US", "RN"):
        for ident in sorted(ids(TRAZA, prefijo) - ids(BRD, prefijo)):
            errores.append(f"{ident} aparece en la trazabilidad pero no en el BRD final")
    # cada BN y US del BRD debe aparecer en la matriz
    for prefijo in ("BN", "US"):
        for ident in sorted(ids(BRD, prefijo) - ids(TRAZA, prefijo)):
            errores.append(f"{ident} está en el BRD pero no en la trazabilidad")
    for e in errores:
        print("ERROR:", e)
    print(f"{len(pruebas_citadas())} pruebas citadas, {len(errores)} errores")
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
