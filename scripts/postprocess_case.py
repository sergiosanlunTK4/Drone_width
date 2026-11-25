"""
POST-PROCESO v2 de un caso de aire (nivel A): extrae metricas REALES de OpenFOAM y las escribe
en `cfd_airflow` (clave air_id, mesh_id). Version v1 (clave case_id) en
`archive/scripts_geometria_v1/postprocess_case_v1.py`.

Es el UNICO camino legitimo para poblar cfd_airflow (regla 2 del proyecto). Si falta una
salida, ese campo queda NULL y se dice; nunca se rellena con un valor plausible.

QUE EXTRAE (todo de salidas del solver del propio caso):
  - log.simpleFoam : ultima iteracion, residuales iniciales finales de U y p, convergencia
                     de residuales (residualControl) y si el solver termino ("End").
  - log.checkMesh  : celdas.
  - postProcessing/fuerza_{suelo,fuselaje,contorno} : F_z total (presion + viscosa), ultimo valor.
  - case_meta.json : fuerza prescrita sobre el aire (entrada, no resultado) -> cierre del
                     balance (igual que la condicion 2 de CFD-0, con el flujo de momento M_out
                     por los contornos abiertos):
                     cierre_momento_pct = 100 * ((-sum F_paredes_z - M_out) / T - 1)
  - postProcessing/U_rotorN : Uz media en cada zona de rotor -> asimetria izquierda/derecha
                     asimetria_LR_pct = 100 * (Uz_izq - Uz_der) / |media|   (izq = y > 0)
  - postProcessing/downwash : perfiles Uz(z) bajo cada rotor y su minimo (downwash maximo).
  - postProcessing/yPlus    : y+ medio en el suelo (ground), ultimo tiempo.

REGLA DE ESCRITURA: solo se escribe si el solver termino sin error. Si los residuales NO
alcanzaron residualControl, por defecto NO se escribe; con `--registrar-no-convergido` se
escribe con convergido = 0 (queda marcado, no se oculta). La convergencia de MAGNITUDES (no
solo residuales) es la condicion 3 de CFD-0 y la evalua check_cfd0_conditions.py.

Uso:
    python scripts/postprocess_case.py --air-id A_T25P_V00.0_H2.5_f1.00_g2
    python scripts/postprocess_case.py --case cfd/cases/<carpeta> [--dry-run]
    python scripts/postprocess_case.py --hechos      # todos los air_cases 'hecho' sin fila
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
DB = ROOT / "data" / "processed" / "dronewith.sqlite"
CASES = ROOT / "cfd" / "cases"

from check_cfd0_conditions import flujo_momento_z, leer_fuerza_final  # noqa: E402

VEC = re.compile(r"\(\s*([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s*\)")


def _ultimo_dir(base: Path) -> Path | None:
    ds = [d for d in base.iterdir() if d.is_dir()] if base.exists() else []
    return max(ds, key=lambda d: float(d.name)) if ds else None


def leer_log(caso: Path) -> dict:
    out = {"iteraciones": None, "res_U": None, "res_p": None, "convergido": 0, "termino": False,
           "error": None}
    lg = caso / "log.simpleFoam"
    if not lg.exists():
        out["error"] = "sin log.simpleFoam"
        return out
    t = lg.read_text(errors="replace")
    its = re.findall(r"^Time = (\d+)", t, re.M)
    out["iteraciones"] = int(its[-1]) if its else None
    ux = [float(v) for v in re.findall(r"Solving for Ux, Initial residual = ([0-9.eE+-]+)", t)]
    uy = [float(v) for v in re.findall(r"Solving for Uy, Initial residual = ([0-9.eE+-]+)", t)]
    uz = [float(v) for v in re.findall(r"Solving for Uz, Initial residual = ([0-9.eE+-]+)", t)]
    ps = [float(v) for v in re.findall(r"Solving for p, Initial residual = ([0-9.eE+-]+)", t)]
    if ux:
        out["res_U"] = max(x[-1] for x in (ux, uy, uz) if x)
    if ps:
        out["res_p"] = ps[-1]
    out["convergido"] = int("solution converged in" in t or "reached convergence" in t)
    out["termino"] = bool(re.search(r"^End\s*$", t, re.M))
    # ojo: la cabecera dice "Floating point exception trapping enabled" -> no vale buscar la frase
    if "FOAM FATAL" in t or re.search(r"Floating point exception(?! trapping)", t) or "sigFpe" in t:
        out["error"] = "error del solver (ver log.simpleFoam)"
    return out


def leer_celdas(caso: Path) -> int | None:
    cm = caso / "log.checkMesh"
    if not cm.exists():
        return None
    m = re.search(r"^\s*cells:\s+(\d+)", cm.read_text(errors="replace"), re.M)
    return int(m.group(1)) if m else None


def uz_zonas(caso: Path, n: int) -> dict:
    out = {}
    for i in range(1, n + 1):
        d = _ultimo_dir(caso / "postProcessing" / f"U_rotor{i}")
        if d is None or not (d / "volFieldValue.dat").exists():
            continue
        filas = [l for l in (d / "volFieldValue.dat").read_text(errors="replace").splitlines()
                 if l.strip() and not l.startswith("#")]
        if filas:
            m = VEC.search(filas[-1])
            if m:
                out[i] = float(m.group(3))
    return out


def perfiles_downwash(caso: Path) -> dict:
    d = _ultimo_dir(caso / "postProcessing" / "downwash")
    out = {}
    if d is None:
        return out
    for f in sorted(d.glob("bajo_rotor*_k_U.xy")):
        i = int(re.search(r"bajo_rotor(\d+)_", f.name).group(1))
        zs, uz = [], []
        for l in f.read_text(errors="replace").splitlines():   # z  k  Ux Uy Uz
            c = l.split()
            if len(c) >= 5:
                zs.append(float(c[0]))
                uz.append(float(c[4]))
        if zs:
            out[f"rotor{i}"] = {"t": float(d.name), "z": zs, "Uz": uz}
    return out


def yplus_suelo(caso: Path) -> float | None:
    d = _ultimo_dir(caso / "postProcessing" / "yPlus")
    if d is None or not (d / "yPlus.dat").exists():
        return None
    filas = [l.split() for l in (d / "yPlus.dat").read_text(errors="replace").splitlines()
             if l.strip() and not l.startswith("#")]
    suelo = [f for f in filas if len(f) >= 5 and f[1] == "ground"]
    return float(suelo[-1][4]) if suelo else None


def procesar(caso: Path, registrar_no_conv: bool, dry: bool) -> int:
    meta_p = caso / "case_meta.json"
    if not meta_p.exists():
        print(f"  {caso.name}: sin case_meta.json — no es un caso v2, no se escribe nada")
        return 1
    meta = json.loads(meta_p.read_text(encoding="utf-8"))
    aid = meta["air_id"]
    lg = leer_log(caso)
    if lg["error"] or not lg["termino"]:
        print(f"  {aid}: solver no terminado ({lg['error'] or 'sin End en log'}) — no se escribe")
        return 1
    if not lg["convergido"] and not registrar_no_conv:
        print(f"  {aid}: residuales NO alcanzaron residualControl (U {lg['res_U']}, p {lg['res_p']}, "
              f"iter {lg['iteraciones']}) — no se escribe (usa --registrar-no-convergido para "
              "dejarlo marcado convergido=0)")
        return 1

    zonas = meta["zonas_rotor"]
    zl = list(zonas.values()) if isinstance(zonas, dict) else zonas
    F_aire_z = sum(z["F_aire_N"][2] for z in zl)
    Fs = leer_fuerza_final(caso, "fuerza_suelo")
    Ff = leer_fuerza_final(caso, "fuerza_fuselaje")
    Fc = leer_fuerza_final(caso, "fuerza_contorno")
    cierre = None
    if None not in (Fs, Ff, Fc) and F_aire_z:
        M_out, _ = flujo_momento_z(caso)       # flujo de momento z por contornos abiertos
        cierre = 100.0 * ((-(Fs + Ff + Fc) - M_out) / -F_aire_z - 1.0)

    uz = uz_zonas(caso, len(zl))
    asim = None
    if len(uz) == len(zl):
        izq = [uz[i + 1] for i, z in enumerate(zl) if z["centro_m"][1] > 0]
        der = [uz[i + 1] for i, z in enumerate(zl) if z["centro_m"][1] < 0]
        if izq and der:
            mi, md = sum(izq) / len(izq), sum(der) / len(der)
            asim = 100.0 * (mi - md) / abs(0.5 * (mi + md))

    perf = perfiles_downwash(caso)
    dw_max = min(min(p["Uz"]) for p in perf.values()) if perf else None
    celdas = leer_celdas(caso)
    malla = meta.get("entradas", {}).get("malla", "?")
    mesh_id = f"{malla}_{celdas}" if celdas else f"{malla}_?"
    fila = dict(air_id=aid, mesh_id=mesh_id, solver="simpleFoam", solver_version="v2412",
                turb_model="kOmegaSST", celdas=celdas, y_plus_medio=yplus_suelo(caso),
                residual_final_U=lg["res_U"], residual_final_p=lg["res_p"],
                iteraciones=lg["iteraciones"], F_suelo_z_N=Fs, F_fuselaje_z_N=Ff, F_contorno_z_N=Fc,
                suma_T_N=sum(z["T_N"] for z in zl), cierre_momento_pct=cierre, asimetria_LR_pct=asim,
                v_downwash_max_ms=dw_max, v_downwash_perfil_json=json.dumps(perf) if perf else None,
                convergido=lg["convergido"], fecha_ejecucion=datetime.now(timezone.utc).isoformat(
                    timespec="seconds"), origen_dato="CFD")
    faltan = [k for k, v in fila.items() if v is None]
    resumen = (f"celdas={celdas} iter={lg['iteraciones']} conv={lg['convergido']} "
               f"cierre={cierre if cierre is None else round(cierre, 3)} % "
               f"asimLR={asim if asim is None else round(asim, 3)} % dw_max={dw_max} "
               f"y+suelo={fila['y_plus_medio']}")
    if dry:
        print(f"  [dry-run] {aid}: {resumen}  NULL: {faltan or '-'}")
        return 0
    con = sqlite3.connect(DB, timeout=60)
    cols = list(fila)
    con.execute(f"INSERT OR REPLACE INTO cfd_airflow ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                [fila[c] for c in cols])
    con.commit()
    con.close()
    print(f"  {aid}: escrito  {resumen}  NULL: {faltan or '-'}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--air-id")
    g.add_argument("--case")
    g.add_argument("--hechos", action="store_true")
    ap.add_argument("--registrar-no-convergido", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.hechos:
        con = sqlite3.connect(DB)
        ids = [r[0] for r in con.execute("SELECT air_id FROM air_cases WHERE estado='hecho' AND air_id "
                                         "NOT IN (SELECT air_id FROM cfd_airflow)")]
        con.close()
        rcs = [procesar(CASES / i, a.registrar_no_convergido, a.dry_run) for i in ids]
        print(f"{len(ids)} caso(s); {rcs.count(0)} escritos")
        return 0
    caso = CASES / a.air_id if a.air_id else Path(a.case)
    return procesar(caso, a.registrar_no_convergido, a.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
