"""
EVALUA LA PRUEBA DE ACOPLAMIENTO (build_coupling_test.py) y escribe evidence/cfd0_acoplamiento.json.

CRITERIO, FIJADO ANTES DE VER RESULTADOS (2026-11-24). Promedios temporales en la ventana
estadistica [1.0, 2.0] s de las corridas `uno` (coupled no) y `dos` (coupled yes):

  C1  fuerza del aire sobre el suelo:    |dF_suelo_z| / T_total            <= 1 %
  C2  Uz medio en cada zona de rotor:    max_i |dUz_i| / |Uz_i|            <= 1 %
  C3  perfiles de downwash bajo rotor:   max_i RMS(dUz_i(z)) / max|Uz_i|   <= 2 %
      (media de los perfiles escritos en la ventana: t = 1.0, 1.25, ..., 2.0)

Ademas se informa (no decide) el RUIDO temporal de `uno` en la ventana (desviacion tipica
de F_suelo_z y de Uz_i): si una diferencia supera el umbral pero no el ruido, se dice asi.
Pasa = C1 y C2 y C3. Si no pasa, INSTRUCCIONES §5.5.4: la dosis pasa a variable del nivel A
en ese extremo (no se fuerza el resultado).

Tambien guarda la estimacion A PRIORI (clase I) de la carga masica y del intercambio de momento.

Uso:  python scripts/compare_coupling.py [--sin-escribir]
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from check_cfd0_conditions import serie_fuerza  # noqa: E402

DEST = ROOT / "cfd" / "cases" / "_acoplamiento"
SALIDA = ROOT / "evidence" / "cfd0_acoplamiento.json"
VENTANA = (1.0, 2.0)
UMBRAL = {"C1_suelo_pct": 1.0, "C2_Uz_zona_pct": 1.0, "C3_downwash_rms_pct": 2.0}
VEC = re.compile(r"\(\s*([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s*\)")


def en_ventana(serie):
    return [v for t, v in serie if VENTANA[0] - 1e-9 <= t <= VENTANA[1] + 1e-9]


def serie_uz(caso: Path, i: int) -> list:
    out = []
    for d in sorted((caso / "postProcessing" / f"U_rotor{i}").glob("*")):
        f = d / "volFieldValue.dat"
        if not f.exists():
            continue
        for l in f.read_text(errors="replace").splitlines():
            if l.startswith("#") or not l.strip():
                continue
            m = VEC.search(l)
            if m:
                out.append((float(l.split()[0]), float(m.group(3))))
    return out


def perfiles(caso: Path) -> dict:
    """{rotor: [(t, z[], Uz[])]} en los tiempos escritos dentro de la ventana."""
    out = {}
    base = caso / "postProcessing" / "downwash"
    for d in sorted(base.glob("*")) if base.exists() else []:
        t = float(d.name)
        if not (VENTANA[0] - 1e-9 <= t <= VENTANA[1] + 1e-9):
            continue
        for f in d.glob("bajo_rotor*_k_U.xy"):
            r = re.search(r"bajo_rotor(\d+)_", f.name).group(1)
            z, uz = [], []
            for l in f.read_text(errors="replace").splitlines():
                c = l.split()
                if len(c) >= 5:
                    z.append(float(c[0]))
                    uz.append(float(c[4]))
            out.setdefault(r, []).append((t, z, uz))
    return out


def perfil_medio(lst):
    z = lst[0][1]
    return z, [mean(p[2][k] for p in lst) for k in range(len(z))]


def a_priori(meta_c: dict, meta_a: dict) -> dict:
    T = -sum(z["F_aire_N"][2] for z in meta_a["zonas_rotor"].values()) if isinstance(
        meta_a["zonas_rotor"], dict) else -sum(z["F_aire_N"][2] for z in meta_a["zonas_rotor"])
    rho, A = meta_a["propiedades_fluido"]["rho"], 0.0
    zl = meta_a["zonas_rotor"].values() if isinstance(meta_a["zonas_rotor"], dict) else meta_a["zonas_rotor"]
    A = sum(math.pi * z["radio_m"] ** 2 for z in zl)
    v_i = math.sqrt(T / (2 * rho * A))                  # teoria de momento: T = 2 rho A v_i^2
    mdot_a = rho * A * v_i                              # caudal por el disco
    mdot_l = meta_c["Q_total_Lmin"] / 60000 * meta_c["rho_liquido"]
    w = 2 * v_i                                         # velocidad de estela lejana (= T / mdot)
    return {"clase": "I", "T_N": round(T, 2), "A_discos_m2": round(A, 4),
            "v_i_ms": round(v_i, 3), "mdot_aire_kg_s": round(mdot_a, 2), "mdot_liquido_kg_s": round(mdot_l, 4),
            "carga_masica": round(mdot_l / mdot_a, 5),
            "fraccion_volumetrica": float(f"{(mdot_l / meta_c['rho_liquido']) / (mdot_a / rho):.3g}"),
            "momento_arrastre_vertical_N": round(mdot_l * w, 2),
            "momento_arrastre_vertical_pct_T": round(100 * mdot_l * w / T, 2),
            "nota": "cota: el aire acelera todo el liquido hasta la velocidad de estela w = T/mdot_aire; "
                    "Elghobashi (1994): fraccion vol. 1e-6..1e-3 = zona de acoplamiento en dos sentidos "
                    "-> por eso se mide y no se supone"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sin-escribir", action="store_true")
    a = ap.parse_args()
    uno = next(DEST.glob("C_*_uno"))
    dos = next(DEST.glob("C_*_dos"))
    meta_c = json.loads((dos / "coupling_meta.json").read_text(encoding="utf-8"))
    meta_a = json.loads((ROOT / "cfd" / "cases" / meta_c["caso_aire"] / "case_meta.json").read_text(encoding="utf-8"))
    ap_ = a_priori(meta_c, meta_a)
    T = ap_["T_N"]
    res = {"criterio": UMBRAL, "ventana_s": VENTANA, "casos": [uno.name, dos.name], "a_priori": ap_}
    for c in (uno, dos):
        lg = c / "log.kinematicParcelFoam"
        if not lg.exists() or not re.search(r"^End\s*$", lg.read_text(errors="replace"), re.M):
            print(f"{c.name}: sin terminar — no se evalua")
            res["pasa"] = False
            res["motivo"] = f"{c.name} sin terminar"
            if not a.sin_escribir:
                SALIDA.write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            return 1

    fs = {c: en_ventana(serie_fuerza(c, "fuerza_suelo")) for c in (uno, dos)}
    d1 = 100 * abs(mean(fs[dos]) - mean(fs[uno])) / T
    ruido1 = 100 * pstdev(fs[uno]) / T
    n = len(meta_a["zonas_rotor"])
    d2, ruido2 = [], []
    for i in range(1, n + 1):
        su, sd = en_ventana(serie_uz(uno, i)), en_ventana(serie_uz(dos, i))
        d2.append(100 * abs(mean(sd) - mean(su)) / abs(mean(su)))
        ruido2.append(100 * pstdev(su) / abs(mean(su)))
    pu, pd = perfiles(uno), perfiles(dos)
    d3 = []
    for r in sorted(pu):
        z, a1 = perfil_medio(pu[r])
        _, a2 = perfil_medio(pd[r])
        rms = math.sqrt(mean((x - y) ** 2 for x, y in zip(a1, a2)))
        d3.append(100 * rms / max(abs(v) for v in a1))
    res["resultados"] = {
        "C1_suelo_pct": round(d1, 3), "F_suelo_z_medio_N": {"uno": round(mean(fs[uno]), 3), "dos": round(mean(fs[dos]), 3)},
        "C1_ruido_temporal_pct": round(ruido1, 3), "n_muestras": len(fs[uno]),
        "C2_Uz_zona_pct": round(max(d2), 3), "C2_por_rotor_pct": [round(x, 3) for x in d2],
        "C2_ruido_temporal_pct": [round(x, 3) for x in ruido2],
        "C3_downwash_rms_pct": round(max(d3), 3) if d3 else None, "C3_por_rotor_pct": [round(x, 3) for x in d3],
        "n_perfiles": {r: len(v) for r, v in pu.items()}}
    ok = {k: (res["resultados"][k] is not None and res["resultados"][k] <= u) for k, u in UMBRAL.items()}
    res["condiciones"] = ok
    res["pasa"] = all(ok.values())
    res["consecuencia"] = ("acoplamiento en un sentido valido a la dosis maxima: nivel A / nivel B y escalado "
                           "lineal en dosis" if res["pasa"] else
                           "NO se cumple: la dosis pasa a variable del nivel A en este extremo (§5.5.4)")
    res["generado"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(json.dumps(res, indent=2, ensure_ascii=False))
    if not a.sin_escribir:
        SALIDA.write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"-> {SALIDA.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
