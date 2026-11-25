#!/usr/bin/env python3
"""Construye el/los caso(s) de HOVER de GATE CFD-0 — geometria v2.

Por que hover (sin cambios respecto de v1; ver Entry 016/017)
--------------------------------------------------------------
Con `U_inf = 0` la fuerza prescrita no puede venir del flujo incidente: si aparece downwash,
la fuente implementa C -> B. `actuationDiskSource` daba T ~ 0 aqui (bug #6).

Condiciones de contorno: por defecto `abierto` (decision del propietario 2026-11-23, Entry 023:
"no se fumiga en hover cerrados"). `cerrado` (Entry 016/017) queda solo como referencia: es una
caja sellada, recircula y no converge (Entry 021)
--------------------------------------------------------------------
    U: inlet, outlet, sides, top -> slip ; ground, airframe -> noSlip
    p: top -> fixedValue 0 (unica salida de presion) ; resto zeroGradient
Un par de parches de presion fija enfrentados produjo un flujo de canal espurio (media Ux =
13 m/s) y se descarto. Dominio simetrico en x e y (+-10 m), por el mismo motivo.
Opcion `--hover-bc abierto`: totalPressure + pressureInletOutletVelocity en todo el contorno
salvo el suelo (aire libre). Se compara con `cerrado` dentro de CFD-0, no se supone.

Que cambia en v2
----------------
Ya no se copia un caso nominal y se parchea: el generador v2 (`build_case_suite.py`) escribe
el caso de hover directamente desde `air_cases` (rol `cfd0` / `cfd0_malla`), con la geometria
real (`<p>_cfd_coordinates.json`), el fuselaje `<p>_airframe.stl`, zonas de rotor inclinadas
y fuerza F_i = -T_i n_i. La version v1 esta en `archive/scripts_geometria_v1/`.

Uso
---
    python scripts/build_hover_case.py                 # CFD-0: T25P hover H 2.5 f 1, malla gruesa
    python scripts/build_hover_case.py --mallas        # + media y fina (independencia de malla)
    python scripts/build_hover_case.py --hover-bc abierto --nombre <carpeta>
Despues: `python scripts/run_queue.py --rol cfd0` (o Allrun.sh del caso).
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_case_suite import CASES, DB, escribir_caso_aire  # noqa: E402

ROLES = ("cfd0",)
ROLES_MALLA = ("cfd0", "cfd0_malla")


def casos_cfd0(con: sqlite3.Connection, con_mallas: bool) -> list[dict]:
    roles = ROLES_MALLA if con_mallas else ROLES
    con.row_factory = sqlite3.Row
    return [dict(r) for r in con.execute(
        f"SELECT * FROM air_cases WHERE rol IN ({','.join('?' * len(roles))}) ORDER BY prioridad, air_id",
        roles)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mallas", action="store_true")
    ap.add_argument("--hover-bc", choices=("cerrado", "abierto"), default="abierto")
    ap.add_argument("--nombre", default=None, help="carpeta alternativa (p. ej. para BC abierto)")
    a = ap.parse_args()
    con = sqlite3.connect(DB)
    filas = casos_cfd0(con, a.mallas)
    con.close()
    if not filas:
        print("no hay casos cfd0 en air_cases: ejecuta scripts/build_scenario_db.py")
        return 1
    for f in filas:
        destino = CASES / (a.nombre if a.nombre and len(filas) == 1 else f["air_id"])
        if (destino / "constant" / "polyMesh").exists():
            print(f"  [existe, no se toca] {destino.relative_to(ROOT)}")
            continue
        meta = escribir_caso_aire(destino, f, f["malla"], a.hover_bc)
        print(f"  {destino.relative_to(ROOT)}  malla={f['malla']}  bloque={meta['malla']['n_bloque']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
