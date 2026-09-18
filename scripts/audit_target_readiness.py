"""
Auditoría de preparación de datos -> responde: ¿qué de lo necesario para el
dataset objetivo existe realmente en el repo?

Solo lee. No modifica casos CFD ni geometrías.
Uso:  python scripts/audit_target_readiness.py
"""
from __future__ import annotations

import csv
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------- STL / geometría
def stl_stats(path: Path) -> dict:
    """Bounding box y nº de facetas de un STL ASCII (los 'control' son ASCII)."""
    xs, ys, zs = [], [], []
    nfacet = 0
    with path.open("r", errors="ignore") as fh:
        for line in fh:
            s = line.strip()
            if s.startswith("facet"):
                nfacet += 1
            elif s.startswith("vertex"):
                _, a, b, c = s.split()
                xs.append(float(a)); ys.append(float(b)); zs.append(float(c))
    if not xs:
        return {"facets": nfacet, "empty": True}
    return {
        "facets": nfacet,
        "x": (round(min(xs), 3), round(max(xs), 3)),
        "y": (round(min(ys), 3), round(max(ys), 3)),
        "z": (round(min(zs), 3), round(max(zs), 3)),
        "bbox_m": (round(max(xs) - min(xs), 3),
                   round(max(ys) - min(ys), 3),
                   round(max(zs) - min(zs), 3)),
        "empty": False,
    }


def audit_geometry() -> None:
    print("=" * 78)
    print("1) GEOMETRÍA DE CONTROL (lo que realmente mallaría snappyHexMesh)")
    print("=" * 78)
    models = sorted((ROOT / "geometry" / "models").glob("*.stl"))
    for stl in models:
        st = stl_stats(stl)
        print(f"  {stl.name:18s} facets={st['facets']:4d}  bbox(xyz m)={st.get('bbox_m')}")
    # ¿son todos iguales? -> la geometría no distingue plataformas
    sigs = {stl_stats(p)["bbox_m"] for p in models}
    print(f"  -> bbox distintos entre los 4 modelos: {len(sigs)} (1 = idénticos)")

    # --- Manifiestos auditables (geometry/manifests/*) + relacion candidata
    print("\n  Manifiestos auditables (geometry/manifests/) y prueba de consistencia:")
    man_dir = ROOT / "geometry" / "manifests"
    total_d = {}
    for f in sorted(man_dir.glob("*_geometry_manifest.json")):
        m = json.loads(f.read_text(encoding="utf-8"))
        mg = m["modelo_geometrico"]
        d_rot = m["dimensiones"]["rotor_diameter_m"]["valor"]
        rc = m["topologia_rotores"]["rotor_count"]
        err = m["validaciones"]["errores"]
        avs = m["validaciones"]["avisos"]
        # contar campos clasificados D (desconocidos) de forma recursiva
        n_d = 0
        n_por_clase = {}

        def contar(v):
            nonlocal n_d
            if isinstance(v, dict):
                c = v.get("clasificacion")
                if c:
                    base = c.split(" ")[0].split("(")[0].strip()
                    n_por_clase[base] = n_por_clase.get(base, 0) + 1
                if c == "D" or (isinstance(c, str) and c.startswith("D")):
                    n_d += 1
                for x in v.values():
                    contar(x)
            elif isinstance(v, list):
                for x in v:
                    contar(x)

        contar(m)
        uav = f.name.split("_")[0].upper()
        total_d[uav] = n_d
        span = mg.get("span_candidato_mm", mg.get("span_predicho_mm"))
        rc_txt = (f"{rc.get('valor')} ({rc.get('clasificacion')})" if rc.get("valor")
                  else f"hipotesis {rc.get('hipotesis_trabajo', rc.get('hipotesis_previa'))} (D)")
        clases = ", ".join(f"{k.split(' ')[0]}={v}" for k, v in sorted(n_por_clase.items()))
        print(f"    {uav:5s} rotor={d_rot} m  lado_ejes={mg['lado_entre_ejes_adyacentes_m']} m"
              f"  span_cand={span} vs {mg['span_oficial_mm'][0]} mm ({mg['error_vs_ancho_pct']:+.2f} %)"
              f"{'' if mg.get('coincide_con_el_sobre') else '  <-- NO cierra'}")
        print(f"          rot_count={rc_txt}  errores={len(err)} avisos={len(avs)}  conteo por clase: {clases}")

    # --- consistencia del caso CFD con la geometria vigente
    print("\n  Coherencia del caso CFD con la geometria vigente:")
    stl_case = ROOT / "cfd" / "cases" / "T25P_baseline" / "constant" / "triSurface" / "T25P_control.stl"
    stl_geo = ROOT / "geometry" / "models" / "T25P_control.stl"
    if stl_case.exists() and stl_geo.exists():
        a, b = stl_stats(stl_case), stl_stats(stl_geo)
        igual = a["bbox_m"] == b["bbox_m"] and a["facets"] == b["facets"]
        print(f"    STL del caso : {a['facets']} facetas bbox={a['bbox_m']}")
        print(f"    STL vigente  : {b['facets']} facetas bbox={b['bbox_m']}")
        print(f"    -> {'COINCIDE' if igual else 'OBSOLETO: la malla del caso NO corresponde a la geometria corregida'}")
    else:
        print("    falta alguno de los STL")


# ---------------------------------------------------------------- malla CFD
def audit_mesh() -> None:
    print("\n" + "=" * 78)
    print("2) MALLA CFD EXISTENTE")
    print("=" * 78)
    case = ROOT / "cfd" / "cases" / "T25P_baseline"
    pm = case / "constant" / "polyMesh"
    owner = pm / "owner"
    nfaces = npoints = ncells = None
    if owner.exists():
        with owner.open("r", errors="ignore") as fh:
            for _ in range(60):
                line = fh.readline()
                if not line:
                    break
                if "nPoints:" in line:
                    npoints = int(line.split("nPoints:")[1].split()[0].rstrip(","))
                if "nCells:" in line:
                    ncells = int(line.split("nCells:")[1].split()[0].rstrip(","))
                if "nFaces:" in line:
                    nfaces = int(line.split("nFaces:")[1].split()[0].rstrip(","))
    print(f"  caso: cfd/cases/T25P_baseline")
    print(f"  celdas={ncells}  caras={nfaces}  puntos={npoints}")
    # tamaño de celda base del blockMesh
    for bmd in [case / "system" / "blockMeshDict"]:
        txt = bmd.read_text()
        verts = [l.strip(" ()\n") for l in txt.splitlines() if l.strip().startswith("(")]
        print(f"  blockMeshDict vértices: {verts}")
        for line in txt.splitlines():
            if line.strip().startswith("hex"):
                print(f"  división base: {line.strip()}")
    # campos iniciales presentes
    present = sorted(p.name for p in (case / "0").iterdir() if p.is_file())
    print(f"  campos en 0/: {present}")
    print("  campos requeridos por kOmegaSST: p, U, k, omega, nut")
    faltan = [f for f in ["k", "omega", "nut"] if f not in present]
    print(f"  -> FALTAN: {faltan}")
    # ¿se ejecutó el solver?
    times = [p.name for p in case.iterdir() if p.is_dir() and p.name.replace('.', '').isdigit()]
    print(f"  directorios de tiempo de solución: {times}")
    # dominios
    for tag, d in [("activo", case), ("backup", ROOT / "cfd" / "cases" / "T25P_baseline_backup_20260914_091336")]:
        lf = d / "log.snappyHexMesh"
        if lf.exists():
            for line in lf.read_text(errors="ignore").splitlines():
                if "Overall mesh bounding box" in line:
                    print(f"  dominio ({tag}) según log.snappyHexMesh: {line.split(':', 1)[1].strip()}")
                    break


# ---------------------------------------------------------------- DOE
def audit_doe() -> None:
    print("\n" + "=" * 78)
    print("3) DOE GENERADO")
    print("=" * 78)
    f = ROOT / "data" / "processed" / "doe_master_plan.csv"
    rows = list(csv.DictReader(f.open()))
    print(f"  filas={len(rows)}  columnas={list(rows[0].keys())}")
    plat = {}
    for r in rows:
        plat[r["Platform"]] = plat.get(r["Platform"], 0) + 1
    print(f"  reparto por plataforma: {plat}")
    v = [float(r["V_inf_ms"]) for r in rows]
    h = [float(r["Height_m"]) for r in rows]
    d = [float(r["DV0.5_um"]) for r in rows]
    l = [float(r["Payload_Fraction"]) for r in rows]
    print(f"  V  in [{min(v):.2f}, {max(v):.2f}] m/s   (cita de limites: ninguna)")
    print(f"  H  in [{min(h):.2f}, {max(h):.2f}] m")
    print(f"  d  in [{min(d):.1f}, {max(d):.1f}] um")
    print(f"  L  in [{min(l):.3f}, {max(l):.3f}] fraccion")
    # cobertura LHS real: 1 punto por estrato
    bins = {}
    for x in v:
        b = int((x - 2.0) / (10.0 - 2.0) * 10)
        bins[b] = bins.get(b, 0) + 1
    print(f"  ocupacion de 10 estratos de V: {[bins.get(i, 0) for i in range(10)]} (ideal ~10 por estrato)")
    print("  -> muestreo usado: permutación aleatoria uniforme (NO LHS estratificado)")
    # límites de masa por plataforma (H5 / §10)
    print("\n  Capacidad de carga por plataforma vs 'Payload_Fraction'=1.0:")
    datos = {
        "T25P": ("Carga 20 kg; masa con batería 33 kg; MTOW 53", True),
        "T55":  ("Carga 50 kg; masa con batería 45 kg (DB1050) / 48.4 (DB1580); MTOW 95/99", True),
        "T70P": ("Carga 70 kg; 52 kg (DB1580) / 56 kg (DB2160); MTOW 102 (DB1580,2boq)", None),
        "T100": ("Carga 100 kg; 75 kg (2 boq); MTOW 175", True),
    }
    for k, (txt, ok) in datos.items():
        flag = "OK" if ok else "REQUIERE DB2160: 52+70=122 > MTOW 102 con DB1580"
        print(f"    {k:5s} {txt}  -> {flag}")

    print("  -> los rangos del DOE son COMUNES a las 4 plataformas; context.md SS9 exige rangos por UAV")


# ---------------------------------------------------------------- jerarquia de fuentes
def audit_sources() -> None:
    print("\n" + "=" * 78)
    print("5) JERARQUIA DE FUENTES Y COBERTURA DEL ESLABON FISICO")
    print("=" * 78)
    apl = ROOT / "data" / "raw" / "dji_academy_01_FUENTE.md"
    txt = ROOT / "data" / "raw" / "dji_academy_01_conocimiento_basico.txt"
    print(f"  fuente P-A (DJI Academy) registrada : {'si' if apl.exists() else 'NO'}")
    if txt.exists():
        print(f"  extraccion de texto                 : si ({len(txt.read_text(encoding='utf-8').splitlines())} lineas)")

    print("\n  Datos criticos que exigen medicion fisica (plan maestro 4.2):")
    for c in ["numero real de rotores y pares coaxiales",
              "posicion XYZ de rotores",
              "posicion XYZ y orientacion de atomizadores",
              "RPM real en hover/traslacion (R1)",
              "presion de pulverizacion y espectro de gota"]:
        print(f"    - {c:46s} -> D   (ver geometry/protocolo_geometria.md)")

    print("\n  Entregables del eslabon fisico:")
    for rel in ["geometry/manifests/", "data/processed/geometry_master.csv",
                "geometry/protocolo_geometria.md", "geometry/models/"]:
        p = ROOT / rel.rstrip("/")
        if not p.exists():
            print(f"    {rel:38s} AUSENTE")
            continue
        n = sum(1 for _ in p.rglob("*")) if p.is_dir() else 1
        print(f"    {rel:38s} {'OK (' + str(n) + ')' if n else 'VACIO'}")

    # conteo de campos clasificados D en los manifiestos
    print("\n  Campos pendientes de medicion (clasificacion D) por plataforma:")
    man_dir = ROOT / "geometry" / "manifests"
    for f in sorted(man_dir.glob("*_geometry_manifest.json")):
        m = json.loads(f.read_text(encoding="utf-8"))
        n_d = 0

        def contar(v):
            nonlocal n_d
            if isinstance(v, dict):
                if v.get("clasificacion") == "D":
                    n_d += 1
                for x in v.values():
                    contar(x)
            elif isinstance(v, list):
                for x in v:
                    contar(x)

        contar(m)
        print(f"    {f.name.split('_')[0].upper():5s} {n_d} campos D")
    print("\n  -> GATE 1A NO se cierra mientras el bloque A/B del protocolo siga en D")
    print("  -> GATE 1B (estado operativo del rotor) es independiente: ver protocolo SS6.1")


# ---------------------------------------------------------------- arquitectura de datos
def audit_data_arch() -> None:
    print("\n" + "=" * 78)
    print("4) ARQUITECTURA DE DATOS OBJETIVO (¿existe?)")
    print("=" * 78)
    esperados = {
        "cfd/results/": "campos de aire + gotas por caso",
        "data/processed/dataset_*.csv|parquet": "tabla maestra (casos, deposition, airflow, metrics_swath)",
        "surrogate/": "D̂ por dron (GP/XGB) + validación out-of-sample",
        "experiments/": "datos de anemometría y colectores",
        "literature/": "matriz de literatura verificada",
        "figures/": "D(x), D(x,y), CV vs spacing, W_eff vs V/H/d",
        "paper/": "manuscrito",
        "logs/": "convergencia, mesh/timestep independence",
    }
    for rel, desc in esperados.items():
        base = rel.split("*")[0].rstrip("/")
        p = ROOT / base
        n = sum(1 for _ in p.rglob("*")) if p.exists() else 0
        estado = "vacío" if n == 0 else f"{n} entradas"
        print(f"  {rel:38s} {estado:12s} -> {desc}")
    print("  .git/ (control de versiones, §38): "
          f"{'presente' if (ROOT / '.git').exists() else 'AUSENTE'}")


if __name__ == "__main__":
    print(f"Auditoría de: {ROOT}\n")
    audit_geometry()
    audit_mesh()
    audit_doe()
    audit_data_arch()
    audit_sources()
