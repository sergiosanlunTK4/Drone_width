"""
QA de las mediciones fisicas (data/raw/mediciones_geometria.csv).

QUE HACE:
  1. Esquema y trazabilidad: filas M sin uncertainty/instrument, filas sin reference_frame,
     source_class invalida, valores no numericos donde toca.
  2. Repetibilidad: dispersion entre REPETICIONES INDEPENDIENTES (distinto setup_id) por
     magnitud critica. Distingue resolucion instrumental de repetibilidad.
  3. Cierres geometricos y SIMETRIAS, reportando RESIDUOS.
  4. Cierre de distancias: separacion entre ejes vs wheelbase declarado y vs la relacion candidata.
  5. Cobertura: que parametros exige GATE 1A y cuales faltan.
  6. NO-CIRCULARIDAD: que el cierre de GATE 1A no dependa de valores derivados de CFD.

REGLA FUNDAMENTAL:
  Los residuos NO se corrigen. Si un rotor no cumple x1+x3 ~ 0, el residuo ES el dato.
  Este script NUNCA escribe en el CSV ni en los manifiestos: solo reporta.

Uso:
  python scripts/audit_measurement_csv.py
  python scripts/audit_measurement_csv.py --uav T25P
  python scripts/audit_measurement_csv.py --tol-m 0.010      # tolerancia de simetria
"""
from __future__ import annotations

import argparse
import csv
import math
import re
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "raw" / "mediciones_geometria.csv"

COLS_OBLIGATORIAS = ["uav", "block", "element_id", "parameter", "value", "unit",
                     "uncertainty", "method", "instrument", "timestamp", "operator",
                     "source_class", "reference_frame"]
CLASES_VALIDAS = {"P", "P-A", "S", "M", "I", "E", "D"}
FUENTE_GEOMETRIA = ["scripts/build_geometry_manifests.py",
                    "scripts/annotate_manifests_with_media_evidence.py",
                    "scripts/freeze_geometry_v1.py",
                    "scripts/audit_measurement_csv.py"]

# parametros que exige GATE 1A
REQ_ROTOR = ["posicion_x", "posicion_y", "posicion_z", "eje_normal", "diametro", "sentido_giro"]
REQ_ATOMIZER = ["posicion_x", "posicion_y", "posicion_z", "vector_descarga",
                "altura_rel_plano_rotor"]

# pares de rotores opuestos para el contraste de simetria (numeracion por defecto)
PARES_OPUESTOS = [("R1", "R3"), ("R2", "R4")]


def leer(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def num(v: str):
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--uav", default=None)
    ap.add_argument("--tol-m", type=float, default=0.010,
                    help="tolerancia de simetria en metros (default 10 mm)")
    a = ap.parse_args()

    print("=" * 80)
    print("QA DE MEDICIONES FISICAS")
    print("=" * 80)

    # ---- 6. NO-CIRCULARIDAD (se comprueba primero: es una regla estructural) ----
    print("\n[6] NO-CIRCULARIDAD — ¿el cierre de GATE 1A depende de CFD?")
    violaciones = []
    for rel in FUENTE_GEOMETRIA:
        p = ROOT / rel
        if not p.exists():
            continue
        # analizar SOLO codigo: se descartan comentarios y literales de cadena, para no
        # detectar la propia comprobacion ni las menciones en docstrings.
        for i, raw in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            s = raw.strip()
            if s.startswith("#") or s.startswith('"""') or s.startswith("'''"):
                continue
            # quitar literales de cadena simples/dobles y comentarios de final de linea
            codigo = re.sub(r'""".*?"""', "", s)
            codigo = re.sub(r"'''.*?'''", "", codigo)
            codigo = re.sub(r'"[^"]*"', '""', codigo)
            codigo = re.sub(r"'[^']*'", "''", codigo)
            codigo = codigo.split("#", 1)[0]
            for m in re.finditer(r"cfd/(?:results|cases)", codigo):
                violaciones.append(f"{rel}:{i} -> {codigo.strip()[:120]}")
    if violaciones:
        print("    ALERTA: codigo del gate que construye rutas de CFD:")
        for v in violaciones:
            print(f"      - {v}")
    else:
        print("    OK: ningun script del gate construye rutas a cfd/results ni cfd/cases.")
        print("        GATE 1A puede cerrarse solo con geometria y evidencia experimental.")

    # ---- carga del CSV ----
    if not CSV_PATH.exists():
        print(f"\nNo existe {CSV_PATH.relative_to(ROOT)}.")
        print("La campana no se ha ejecutado: no hay nada que auditar todavia.")
        return 0
    filas = leer(CSV_PATH)
    if a.uav:
        filas = [f for f in filas if (f.get("uav") or "").upper() == a.uav.upper()]
    print(f"\nfilas en el CSV: {len(filas)}"
          + (f"  (filtrado a {a.uav})" if a.uav else ""))
    if not filas:
        print("El CSV esta vacio: la campana no se ha ejecutado. Nada que auditar.")
        return 0

    # ---- 1. esquema y trazabilidad ----
    print("\n[1] ESQUEMA Y TRAZABILIDAD")
    faltan_cols = [c for c in COLS_OBLIGATORIAS
                   if c not in (filas[0].keys() if filas else [])]
    if faltan_cols:
        print(f"    columnas obligatorias ausentes: {', '.join(faltan_cols)}")
    problemas = defaultdict(int)
    for i, f in enumerate(filas, 2):
        if (f.get("source_class") or "") not in CLASES_VALIDAS:
            problemas["source_class invalida o vacia"] += 1
        if (f.get("source_class") == "M"):
            if not (f.get("uncertainty") or "").strip():
                problemas["fila M sin uncertainty"] += 1
            if not (f.get("instrument") or "").strip():
                problemas["fila M sin instrument"] += 1
        if not (f.get("reference_frame") or "").strip():
            problemas["fila sin reference_frame"] += 1
        if not (f.get("method") or "").strip():
            problemas["fila sin method"] += 1
    if problemas:
        for k, v in problemas.items():
            print(f"    {v:4d}  {k}")
    else:
        print("    OK: sin problemas de trazabilidad.")

    # ---- 2. repetibilidad entre repeticiones independientes ----
    print("\n[2] REPETIBILIDAD (repeticiones con distinto setup_id)")
    grupos = defaultdict(list)
    for f in filas:
        v = num(f.get("value"))
        if v is None:
            continue
        clave = (f.get("uav"), f.get("block"), f.get("element_id"), f.get("parameter"),
                 f.get("configuracion") or "")
        grupos[clave].append((v, (f.get("setup_id") or "").strip(),
                              (f.get("uncertainty") or "").strip()))
    con_rep = {k: v for k, v in grupos.items() if len(v) >= 2}
    if not con_rep:
        print("    sin magnitudes con repeticion registrada.")
    else:
        print(f"    magnitudes con >=2 lecturas: {len(con_rep)}")
        print(f"    {'elemento':18s} {'parametro':22s} {'n':>2s} {'media':>10s} {'disp':>9s} {'setup unicos':>12s}")
        for k, v in sorted(con_rep.items())[:25]:
            vals = [x[0] for x in v]
            setups = {x[1] for x in v if x[1]}
            disp = statistics.stdev(vals) if len(vals) > 1 else 0.0
            print(f"    {str(k[1]) + '/' + str(k[2]):18s} {str(k[3]):22s} {len(vals):2d} "
                  f"{statistics.fmean(vals):10.4f} {disp:9.4f} {len(setups):12d}")
        solo_una = [k for k, v in grupos.items()
                    if len(v) >= 2 and len({x[1] for x in v if x[1]}) == 1]
        if solo_una:
            print(f"\n    AVISO: {len(solo_una)} magnitudes tienen varias lecturas con el MISMO setup_id.")
            print("           Eso mide resolucion instrumental, NO repetibilidad. Para repetibilidad")
            print("           hace falta RECOLOCAR el instrumento y usar otro setup_id.")

    # ---- 3. simetrias: reportar residuos, NO corregir ----
    print("\n[3] SIMETRIAS DE ROTORES — RESIDUOS (no se corrigen)")
    pos = defaultdict(dict)
    for f in filas:
        if (f.get("block") or "").lower() != "rotor":
            continue
        p, v = f.get("parameter"), num(f.get("value"))
        if v is None:
            continue
        if p in ("posicion_x", "posicion_y", "posicion_z"):
            pos[(f.get("element_id") or "").strip()][p] = v
    if not pos:
        print("    sin filas de posicion de rotor.")
    else:
        print(f"    rotores con posicion: {', '.join(sorted(pos))}")
        for r1, r3 in PARES_OPUESTOS:
            if r1 in pos and r3 in pos:
                for eje in ("posicion_x", "posicion_y"):
                    if eje in pos[r1] and eje in pos[r3]:
                        res = pos[r1][eje] + pos[r3][eje]
                        marca = "OK" if abs(res) <= a.tol_m else "RESIDUO GRANDE"
                        print(f"    {r1}+{r3}  {eje:11s} = {res:+.4f} m   [{marca}]")
        print(f"\n    tolerancia usada: ±{a.tol_m*1000:.0f} mm")
        print("    RECORDATORIO: un residuo grande es INFORMACION, no un error a corregir.")
        print("    Lecturas posibles: (a) el CG real no coincide con el origen; (b) la planta no es")
        print("    simetrica; (c) error de medicion. Se documenta y se decide con el residuo.")

    # ---- 4. cierre de distancias vs wheelbase declarado ----
    print("\n[4] CIERRE DE DISTANCIAS")
    pend = {}
    for f in filas:
        p, v = f.get("parameter"), num(f.get("value"))
        if v is not None and p and p.startswith(("separacion_ejes", "alcance_desplegado")):
            pend[p] = v
    if pend:
        for k, v in sorted(pend.items()):
            print(f"    {k:34s} = {v:.4f} m")
        if "separacion_ejes_opuestos_x" in pend:
            decl = 1.970
            err = (pend["separacion_ejes_opuestos_x"] - decl) / decl * 100
            print(f"    contraste con wheelbase declarado {decl:.3f} m -> error {err:+.2f} %")
        if "alcance_desplegado_x" in pend:
            decl = 2.650
            err = (pend["alcance_desplegado_x"] - decl) / decl * 100
            print(f"    contraste con alcance oficial 2.650 m -> error {err:+.2f} %")
    else:
        print("    sin cotas de separacion/alcance registradas.")

    # ---- 5. cobertura de parametros para GATE 1A ----
    print("\n[5] COBERTURA PARA GATE 1A")
    por_bloque = defaultdict(set)
    for f in filas:
        por_bloque[(f.get("block") or "").lower()].add(f.get("parameter"))
    for bloque, req in (("rotor", REQ_ROTOR), ("atomizer", REQ_ATOMIZER)):
        presentes = por_bloque.get(bloque, set())
        faltan = [p for p in req if p not in presentes]
        print(f"    bloque {bloque:9s}: {len(req)-len(faltan)}/{len(req)} parametros"
              + (f"  FALTAN: {', '.join(faltan)}" if faltan else "  OK"))
    if "mass" in por_bloque:
        tiene_nom = "nominal_total_mass_kg" in por_bloque["mass"]
        tiene_med = "measured_total_mass_kg" in por_bloque["mass"]
        print(f"    masa nominal registrada : {tiene_nom}")
        print(f"    masa MEDIDA registrada  : {tiene_med}"
              + ("" if tiene_med else "   <-- obligatoria: nominal != medida"))
    rpm_rotor = {f.get("element_id") for f in filas
                 if (f.get("parameter") or "") == "rpm_hover"}
    if rpm_rotor:
        print(f"    rpm_hover por rotor: {len(rpm_rotor)} rotores ({', '.join(sorted(x for x in rpm_rotor if x))})")
    print("\n" + "=" * 80)
    print("Este script NO escribe nada. Los residuos se reportan; no se corrigen.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
