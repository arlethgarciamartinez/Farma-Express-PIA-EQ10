"""Fitness functions: la regla de dependencia se verifica automáticamente (ADR-001)."""
import ast
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src" / "farmaexpress"

# capa -> paquetes que NO puede importar
PROHIBIDO = {
    "domain": {"application", "infrastructure", "api", "sqlalchemy", "fastapi", "pydantic"},
    "application": {"infrastructure", "api", "sqlalchemy", "fastapi"},
    "infrastructure": {"api"},
}


def _imports(archivo: Path) -> set[str]:
    arbol = ast.parse(archivo.read_text(encoding="utf-8"))
    salida: set[str] = set()
    for n in ast.walk(arbol):
        if isinstance(n, ast.Import):
            salida |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module:
            salida.add(n.module)
    return salida


def test_regla_de_dependencia():
    violaciones = []
    for capa, prohibidos in PROHIBIDO.items():
        for f in (SRC / capa).glob("*.py"):
            for imp in _imports(f):
                partes = imp.split(".")
                destino = partes[1] if partes[0] == "farmaexpress" and len(partes) > 1 else partes[0]
                if destino in prohibidos:
                    violaciones.append(f"{capa}/{f.name} importa {imp}")
    assert violaciones == []


def test_hay_al_menos_tres_specifications_hoja():
    from farmaexpress.domain import specifications as sp

    hojas = [
        c for c in vars(sp).values()
        if isinstance(c, type) and issubclass(c, sp.Specification)
        and c not in (sp.Specification, sp.AndSpecification, sp.OrSpecification, sp.NotSpecification)
    ]
    assert len(hojas) >= 3
