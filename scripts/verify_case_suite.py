"""
Verificacion ESTRUCTURAL de los casos CFD generados.

POR QUE EXISTE:
  GATE CFD-0 ejecuto el primer caso real y encontro un bug SISTEMICO que afectaba a los 128:
  mis ficheros `transportProperties` y `turbulenceProperties` declaraban `class IOdictionary`
  y OpenFOAM 2412 exige `class dictionary`:

      FOAM FATAL IO ERROR: unexpected class name IOdictionary expected dictionary

  Este script comprueba, para TODOS los casos, las invariantes que ya conocemos. Su objetivo
  es que un error de generacion se detecte SIN necesidad de lanzar el solver caso por caso.

QUE COMPRUEBA (cada una nace de un fallo real o de una regla del protocolo):
  1. los ficheros requeridos existen
  2. `class` correcta en cada fichero (transportProperties y turbulenceProperties = dictionary)
  3. `topoSetDict` define una cellZone por rotor, y el numero coincide con los rotores modelados
  4. `fvOptions` tiene un actuationDiskSource por rotor, con cellZone existente
  5. `diskDir` es (0 0 -1)  -> el empuje debe ir hacia ABAJO en vuelo nivelado
  6. las condiciones de contorno NO son todas cero (el caso antiguo tenia inlet y outlet a 0)
  7. `sides` y `top` son slip/freestream, no symmetry
  8. los campos de turbulencia (k, omega, nut) existen
  9. el suelo esta a -H (altura de aplicacion real), no a un valor fijo

Uso:
  python scripts/verify_case_suite.py
  python scripts/verify_case_suite.py --verbose
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUERIDOS = [
    "system/blockMeshDict", "system/controlDict", "system/fvSchemes", "system/fvSolution",
    "system/topoSetDict", "system/snappyHexMeshDict",
    "0/U", "0/p", "0/k", "0/omega", "0/nut",
    "constant/turbulenceProperties", "constant/transportProperties",
    "constant/fvOptions", "case_meta.json",
]
# ficheros que DEBEN declarar `class dictionary` en OpenFOAM 2412
CLASE_DICTIONARY = ["constant/transportProperties", "constant/turbulenceProperties",
                    "system/fvSchemes", "system/fvSolution", "system/blockMeshDict",
                    "system/controlDict", "system/topoSetDict", "constant/fvOptions"]


def clase_de(p: Path) -> str | None:
    txt = p.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r"^\s*class\s+(\w+)\s*;", txt, re.M)
    return m.group(1) if m else None


def revisar_caso(caso: Path) -> list[str]:
    fallos: list[str] = []

    # 1. ficheros requeridos
    for f in REQUERIDOS:
        if not (caso / f).exists():
            fallos.append(f"falta {f}")

    # 2. clase correcta
    for f in CLASE_DICTIONARY:
        p = caso / f
        if p.exists():
            c = clase_de(p)
            if c != "dictionary":
                fallos.append(f"{f}: class={c} (debe ser dictionary)")

    # meta
    meta = {}
    mp = caso / "case_meta.json"
    if mp.exists():
        meta = json.loads(mp.read_text(encoding="utf-8"))
    n_rot = meta.get("derivados_analiticos", {}).get("n_rotores_modelados", 0)

    # 3. cellZones de rotor en topoSetDict
    #    Estructura correcta en OpenFOAM 2412 (dos bugs reales encontrados ejecutando):
    #      rotorSetN  { type cellSet ; action new ; source cylinderToCell ; ... }
    #      rotorZoneN { type cellZoneSet ; action new ; source setToCellZone ; set rotorSetN }
    #    Errores historicos:
    #      - `type cylinderToCell`  -> "Unknown set type cylinderToCell" (es una FUENTE)
    #      - falta `action`         -> "Entry 'action' not found"
    #      - `cellZone rotorN`      -> "Entry 'name' not found"
    ts = caso / "system" / "topoSetDict"
    if ts.exists():
        t = ts.read_text(errors="ignore")
        n_sets = len(re.findall(r"type\s+cellSet\s*;", t))
        n_source_cyl = len(re.findall(r"source\s+cylinderToCell\s*;", t))
        n_zonas = len(re.findall(r"type\s+cellZoneSet\s*;", t))
        n_set2zone = len(re.findall(r"source\s+setToCellZone\s*;", t))
        n_action = len(re.findall(r"\baction\s+\w+\s*;", t))
        if n_rot and n_sets != n_rot:
            fallos.append(f"topoSetDict: {n_sets} cellSet vs {n_rot} rotores")
        if n_rot and n_source_cyl != n_rot:
            fallos.append(f"topoSetDict: {n_source_cyl} source cylinderToCell vs {n_rot} rotores")
        if n_rot and n_zonas != n_rot:
            fallos.append(f"topoSetDict: {n_zonas} cellZoneSet vs {n_rot} rotores")
        if n_rot and n_set2zone != n_rot:
            fallos.append(f"topoSetDict: {n_set2zone} setToCellZone vs {n_rot} rotores")
        if n_action < 2 * n_rot:
            fallos.append(f"topoSetDict: {n_action} entradas 'action' para {2*n_rot} acciones")
        # errores historicos que no deben reaparecer
        if re.search(r"type\s+cylinderToCell\s*;", t):
            fallos.append("topoSetDict: 'type cylinderToCell' (es una FUENTE, debe ser 'source')")
        if re.search(r"cellZone\s+rotor\d", t):
            fallos.append("topoSetDict: 'cellZone rotorN' dentro de la accion (sintaxis invalida)")
        for i in range(1, n_rot + 1):
            if f"rotorSet{i}" not in t:
                fallos.append(f"topoSetDict: falta rotorSet{i}")
            if f"name    rotor{i};" not in t:
                fallos.append(f"topoSetDict: falta la cellZone rotor{i}")

    # 4/5. fvOptions: un disco por rotor y diskDir hacia abajo
    #    OJO: `options` debe ser SUB-DICCIONARIO (llaves) y no lista (parentesis).
    #    Bug historico: `options ( rotor1 {...} )` -> fvOptions no cargaba y el EMPUJE
    #    NUNCA se aplicaba (solver converge a campo sin discos, residuales ~1e-10).
    fo = caso / "constant" / "fvOptions"
    if fo.exists():
        t = fo.read_text(errors="ignore")
        n_discos = len(re.findall(r"type\s+actuationDiskSource\s*;", t))
        if n_rot and n_discos != n_rot:
            fallos.append(f"fvOptions: {n_discos} discos vs {n_rot} rotores")
        if re.search(r"^\s*options\s*\(", t, re.M):
            fallos.append("fvOptions: 'options' es una LISTA; debe ser SUB-DICCIONARIO (llaves)")
        if not re.search(r"^\s*options\s*\{", t, re.M):
            fallos.append("fvOptions: falta el sub-diccionario 'options { ... }'")
        for i in range(1, n_rot + 1):
            if f"cellZone        rotor{i};" not in t:
                fallos.append(f"fvOptions: falta la referencia a la cellZone rotor{i}")
        for m in re.finditer(r"diskDir\s+\(([^)]*)\)", t):
            comps = [float(x) for x in m.group(1).split()]
            if not (len(comps) == 3 and comps[2] < 0):
                fallos.append(f"fvOptions: diskDir=({m.group(1)}) no apunta hacia abajo")
        # Cp > 0 es OBLIGATORIO: OpenFOAM aborta con "Cp and Ct must be greater than zero"
        for m in re.finditer(r"^\s*Cp\s+([-\d.eE+]+)\s*;", t, re.M):
            if float(m.group(1)) <= 0:
                fallos.append(f"fvOptions: Cp={m.group(1)} (debe ser > 0)")
        for m in re.finditer(r"^\s*Ct\s+([-\d.eE+]+)\s*;", t, re.M):
            if float(m.group(1)) <= 0:
                fallos.append(f"fvOptions: Ct={m.group(1)} (debe ser > 0)")
        if "upstreamPoint" not in t:
            fallos.append("fvOptions: falta upstreamPoint (obligatorio en 2412)")

    # 6/7. condiciones de contorno
    up = caso / "0" / "U"
    if up.exists():
        t = up.read_text(errors="ignore")
        if re.search(r"inlet\s*\{\s*type\s+fixedValue;\s*value\s+uniform\s+\(0 0 0\)", t):
            fallos.append("0/U: inlet a (0 0 0) -> no hay traslacion")
        if "symmetry" in t:
            fallos.append("0/U: usa symmetry en sides/top (deberia ser slip)")

    # 9. suelo a -H
    bm = caso / "system" / "blockMeshDict"
    if bm.exists():
        t = bm.read_text(errors="ignore")
        m = re.search(r"\(([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\)", t)
        H = meta.get("entradas", {}).get("H_m")
        if m and H:
            z0 = float(m.group(3))
            if abs(z0 + float(H)) > 0.01:
                fallos.append(f"suelo en z={z0} pero H={H} (deberia ser -{H})")

    return fallos


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()

    casos = sorted([d for d in (ROOT / "cfd" / "cases").glob("*_V*") if d.is_dir()])
    if not casos:
        print("no hay casos; ejecuta scripts/build_case_suite.py")
        return 2

    print("=" * 88)
    print(f"VERIFICACION ESTRUCTURAL DE LA SUITE — {len(casos)} casos")
    print("=" * 88)

    contador: Counter = Counter()
    con_fallos = 0
    for c in casos:
        f = revisar_caso(c)
        if f:
            con_fallos += 1
            for x in f:
                contador[x.split(":")[0]] += 1
            if a.verbose:
                print(f"\n  {c.name}")
                for x in f:
                    print(f"     - {x}")

    print(f"\n  casos SIN fallos : {len(casos) - con_fallos}/{len(casos)}")
    print(f"  casos con fallos : {con_fallos}")

    if contador:
        print("\n  fallos agrupados (causa -> cuantos casos):")
        for k, v in contador.most_common():
            print(f"    {v:4d}  {k}")
    else:
        print("\n  [OK] todas las invariantes se cumplen en TODOS los casos.")

    print("\nNOTA: esto es verificacion ESTRUCTURAL, no fisica. Que los ficheros sean")
    print("correctos no garantiza que el solver corra ni que el resultado tenga sentido:")
    print("eso lo decide GATE CFD-0 ejecutando un caso de punta a punta.")
    return 1 if con_fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
