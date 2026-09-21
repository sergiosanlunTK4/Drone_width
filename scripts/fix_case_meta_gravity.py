#!/usr/bin/env python3
"""Recalcula los derivados analiticos de `case_meta.json` con la gravedad correcta.

El defecto que corrige
----------------------
`scripts/build_case_suite.py` definia `G = 9.81` mientras `scripts/force_chain.py` —la
cadena de fuerza autoritativa del proyecto— usa `G = 9.80665`. Consecuencia:

    case_meta.json decia   empuje_total_N        = 509.24      (= 51.91 * 9.81)
    y a la vez             v_inducida_hover_ms   = 6.549       (= sqrt(509.063/(2*rho*A)))

Es decir, **el propio fichero era internamente incoherente**: el empuje total implicito en
`v_inducida_hover_ms` (509.063 N) no era el `empuje_total_N` declarado (509.24 N). El error
es de 0.0347 % — pequeno, pero es un error, y ademas silencioso.

Lo detecto la comprobacion de coherencia de `scripts/build_prescribed_momentum.py`, que
compara el empuje total prescrito contra el peso `m*g` de la cadena C.

Que hace este script
--------------------
Reescribe UNICAMENTE el bloque `derivados_analiticos` de cada `case_meta.json`, dejando
intactas las entradas, el dominio, las propiedades del fluido y el estado. No toca la malla,
ni `fvOptions`, ni los campos.

Es preferible a reejecutar `build_case_suite.py` completo porque aquel reescribe los 128
arboles de caso y borraria evidencias ya producidas (mallas, `log.checkMesh`, postProcessing).
Aqui la reparacion es minima y auditable.

Uso
---
    python scripts/fix_case_meta_gravity.py --dry-run     # muestra que cambiaria
    python scripts/fix_case_meta_gravity.py               # aplica
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

CASES = ROOT / "cfd" / "cases"

# Se importan los calculos del generador para garantizar que los derivados se recalculan
# con EXACTAMENTE su misma logica, en lugar de reimplementarla aqui (una segunda
# implementacion es una segunda oportunidad de divergir).
from build_case_suite import (  # noqa: E402
    G, PLAT, RHO, disco, reparto_empuje, rot_centers,
)


def derivados_correctos(meta: dict) -> dict:
    clave = meta.get("plataforma")
    if clave not in PLAT:
        raise KeyError(f"plataforma desconocida en case_meta.json: {clave!r}")
    p = PLAT[clave]

    masa = float(meta["entradas"]["masa_total_kg"])
    split = float(meta["entradas"].get("split_coaxial_superior", 0.5))

    centros = rot_centers(p)
    empujes = reparto_empuje(p, masa, split)
    d = disco(p)

    return {
        "n_rotores_modelados": d["n_rotores"],
        "r_rotor_m": round(d["r_rotor"], 4),
        "area_disco_total_m2": round(d["A_total"], 4),
        "empuje_total_N": round(masa * G, 2),
        "empuje_por_disco_N": {c["id"]: round(T, 2) for c, T in zip(centros, empujes)},
        "v_inducida_hover_ms": round(math.sqrt(masa * G / (2 * RHO * d["A_total"])), 3),
        "nota_derivados": (
            "Recalculado por scripts/fix_case_meta_gravity.py. Se corrigio la incoherencia "
            "interna que dejaba G=9.81 en build_case_suite.py frente a G=9.80665 en "
            "force_chain.py: empuje_total_N y v_inducida_hover_ms procedian de gravedades "
            "distintas. Ahora ambos usan 9.80665 y cierran con el peso de la cadena C."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    casos = sorted(p for p in CASES.iterdir() if p.is_dir()
                   and (p / "case_meta.json").exists())
    if not casos:
        print(f"No hay case_meta.json en {CASES}")
        return 1

    cambiados, iguales, errores = 0, 0, 0
    ejemplos = []

    for caso in casos:
        f = caso / "case_meta.json"
        try:
            meta = json.loads(f.read_text(encoding="utf-8"))
            nuevos = derivados_correctos(meta)
        except Exception as exc:  # noqa: BLE001
            errores += 1
            print(f"  {caso.name}: ERROR {type(exc).__name__}: {exc}")
            continue

        viejos = meta.get("derivados_analiticos", {})
        difiere = any(viejos.get(k) != v for k, v in nuevos.items() if k != "nota_derivados")

        if not difiere:
            iguales += 1
            continue

        if len(ejemplos) < 3:
            ejemplos.append((caso.name, viejos.get("empuje_total_N"),
                             nuevos["empuje_total_N"],
                             viejos.get("v_inducida_hover_ms"),
                             nuevos["v_inducida_hover_ms"]))

        meta["derivados_analiticos"] = nuevos
        if not args.dry_run:
            f.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8")
        cambiados += 1

    modo = "DRY-RUN (no se escribio nada)" if args.dry_run else "APLICADO"
    print("=" * 100)
    print(f"RECALCULO DE DERIVADOS EN case_meta.json  -  {modo}")
    print("=" * 100)
    print(f"  casos revisados : {len(casos)}")
    print(f"  modificados     : {cambiados}")
    print(f"  ya correctos    : {iguales}")
    print(f"  errores         : {errores}")
    if ejemplos:
        print("\n  ejemplos (empuje_total_N / v_inducida_hover_ms):")
        for nombre, ea, eb, va, vb in ejemplos:
            print(f"    {nombre}")
            print(f"      T: {ea} -> {eb}   v_i: {va} -> {vb}")
    print(f"\n  G usada: {G}  (= la de scripts/force_chain.py)")
    print()
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
