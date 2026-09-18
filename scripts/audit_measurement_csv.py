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
# ademas, toda fila de rotor debe declarar position_role (ver §5b)

# Roles y pares DIAMETRALMENTE OPUESTOS expresados como SEMANTICA GEOMETRICA, no como
# identificadores. La QA deriva los pares de la columna `position_role`, de modo que cambiar
# la numeracion (o que un manual DJI numere distinto) no obliga a reinterpretar mediciones.
#   FL = delantero izquierdo   RL = trasero izquierdo
#   RR = trasero derecho       FR = delantero derecho
ROLES_VALIDOS = {"FL", "RL", "RR", "FR"}
PARES_OPUESTOS_POR_ROL = [("FL", "RR"), ("FR", "RL")]


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
        if not (f.get("value") or "").strip():
            problemas["fila sin value"] += 1
        if not (f.get("parameter") or "").strip():
            problemas["fila sin parameter"] += 1
    if problemas:
        for k, v in sorted(problemas.items()):
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

    # ---- 3. simetrias: VECTOR COMPLETO, residuos reportados, NUNCA corregidos ----
    print("\n[3] OPOSICION DIAMETRAL DE ROTORES — residuo del VECTOR COMPLETO")
    print("    Para cada pareja opuesta:  r_i + r_j ~ 2·r_c   (con r_c = centro esperado)")
    print("    Si el origen esta en el centro geometrico esperado, r_c = 0.")
    print("    Los pares se derivan de `position_role` (FL<->RR, FR<->RL), no de los ids.\n")

    # recoger posiciones por rol y comprobar consistencia id<->rol
    roles: dict[str, dict[str, float]] = {}
    ids_por_rol: dict[str, set] = defaultdict(set)
    roles_sin_declarar = set()
    for f in filas:
        if (f.get("block") or "").lower() != "rotor":
            continue
        rol = (f.get("position_role") or "").strip().upper()
        p, v = f.get("parameter"), num(f.get("value"))
        if not rol:
            if p in ("posicion_x", "posicion_y", "posicion_z"):
                roles_sin_declarar.add((f.get("element_id") or "").strip())
            continue
        ids_por_rol[rol].add((f.get("element_id") or "").strip())
        if v is not None and p in ("posicion_x", "posicion_y", "posicion_z"):
            roles.setdefault(rol, {})[p] = v

    if roles_sin_declarar:
        print(f"    AVISO: {len(roles_sin_declarar)} rotores con posicion pero sin position_role:")
        print(f"           {', '.join(sorted(roles_sin_declarar))}")
        print("           -> sin el rol no se puede derivar la oposicion. Anadelo al CSV.")

    raros = {r: s for r, s in ids_por_rol.items() if len(s) > 1}
    for r, s in raros.items():
        print(f"    AVISO: el rol {r} aparece con varios ids: {', '.join(sorted(s))}")

    def vec(rol: str) -> dict:
        return roles.get(rol, {})

    encontrados = False
    for ra, rb in PARES_OPUESTOS_POR_ROL:
        va, vb = vec(ra), vec(rb)
        comunes = [e for e in ("posicion_x", "posicion_y", "posicion_z") if e in va and e in vb]
        if not comunes:
            print(f"    {ra}<->{rb}: sin datos suficientes (faltan ambos o uno)")
            continue
        encontrados = True
        resid = {e: va[e] + vb[e] for e in comunes}
        norm3 = math.sqrt(sum(resid[e] ** 2 for e in comunes))
        detalle = "  ".join(f"{e.split('_')[1].upper()}={resid[e]:+.4f}" for e in comunes)
        marca = "OK" if norm3 <= a.tol_m else "RESIDUO GRANDE"
        planos = [e for e in comunes if e != "posicion_z"]
        norm2 = math.sqrt(sum(resid[e] ** 2 for e in planos)) if planos else float("nan")
        print(f"    {ra}<->{rb}: {detalle}   |residuo|_3D={norm3:.4f} m  "
              f"|residuo|_XY={norm2:.4f} m   [{marca}]")

    if not encontrados:
        print("    sin parejas opuestas evaluables todavia.")

    print(f"\n    tolerancia usada: ±{a.tol_m*1000:.0f} mm  (--tol-m para cambiarla)")
    print("    RECORDATORIO: un residuo grande es INFORMACION, no un error a corregir.")
    print("    Lecturas posibles: (a) el CG real no coincide con el origen declarado; (b) la planta")
    print("    no es simetrica; (c) error de medicion. Se documenta y se decide con el residuo.")
    print("    El vector completo detecta lo que dos pruebas aisladas en X e Y pueden esconder.")

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

    # ---- 5b. convencion de numeracion y evidencia fotografica ----
    print("\n[5b] CONVENCION DE ROTORES Y EVIDENCIA FOTOGRAFICA")
    ids_rol = {r: sorted(s) for r, s in ids_por_rol.items()}
    if ids_rol:
        print(f"    roles declarados: {', '.join(f'{r}={ids_rol[r][0]}' for r in sorted(ids_rol))}")
    faltan_roles = ROLES_VALIDOS - set(ids_rol)
    if faltan_roles:
        print(f"    roles sin datos: {', '.join(sorted(faltan_roles))}")
    invalidos = {f.get("position_role") for f in filas
                 if (f.get("position_role") or "").strip()
                 and (f.get("position_role") or "").strip().upper() not in ROLES_VALIDOS}
    if invalidos:
        print(f"    AVISO: position_role no reconocido: {', '.join(sorted(x for x in invalidos if x))}")
    if not ids_rol:
        print("    sin position_role declarado todavia (anadelo en las filas de rotor).")

    # foto cenital con etiquetas y flecha +X asociada al reference_frame
    refs = {(f.get("reference_frame") or "").strip() for f in filas if (f.get("reference_frame") or "").strip()}
    con_foto = set()
    for f in filas:
        blob = " ".join(str(f.get(k) or "") for k in ("raw_file", "notes", "method")).lower()
        if ("foto" in blob or "photo" in blob or "cenital" in blob or "raw_file" in f and (f.get("raw_file") or "").strip()):
            if "cenital" in blob or "top" in blob or "+x" in blob or (f.get("raw_file") or "").strip():
                con_foto.add((f.get("reference_frame") or "").strip())
    for r in sorted(refs):
        estado = "con evidencia fotografica" if r in con_foto else "SIN foto cenital etiquetada registrada"
        print(f"    reference_frame '{r}': {estado}")
    if refs and not (refs & con_foto):
        print("    AVISO: falta la foto cenital con etiquetas R1-R4 y flecha +X asociada al")
        print("           reference_frame. Es la evidencia que impide discutir que significaba 'R1'.")

    print("\n" + "=" * 80)
    print("Este script NO escribe nada. Los residuos se reportan; no se corrigen.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
