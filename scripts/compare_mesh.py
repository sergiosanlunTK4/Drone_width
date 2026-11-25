"""
INDEPENDENCIA DE MALLA de CFD-0 (INSTRUCCIONES_CFD.md Paso 2.3) -> evidence/cfd0_independencia_malla.json

Casos: gruesa  A_T25P_V00.0_H2.5_f1.00_g2   (oficial)
       media   A_T25P_V00.0_H2.5_f1.00_mmedia_g2
       fina    A_T25P_V00.0_H2.5_f1.00_mfina_g2
Valores = ultimo tiempo de cada corrida (RANS estacionario; la estabilidad de magnitudes es la
condicion 3 de CFD-0, evaluada aparte con check_cfd0_conditions.py).

MAGNITUDES (las que alimentan el nivel B y el paper):
  Uz_zona_i       Uz medio en la zona de cada rotor (postProcessing/U_rotorN)
  dw_max_i        minimo de Uz en el perfil bajo cada rotor (downwash maximo)
  F_fuselaje_z    carga del downwash sobre el fuselaje (sensible a la resolucion cerca del cuerpo)
  perfil_i(z)     perfil Uz(z) bajo cada rotor (80 puntos, mismas lineas en las 3 mallas)
(F_suelo no se usa: la fija el balance de momento y es insensible a la malla por construccion.)

CRITERIO, FIJADO ANTES DE VER LA MEDIA Y LA FINA (2026-11-24):
  M1  |phi_media - phi_fina| / |phi_fina| <= 2 %   para Uz_zona_i y dw_max_i (todos los rotores)
  M2  RMS(perfil_media - perfil_fina) / max|perfil_fina| <= 3 %   (todos los rotores)
  M3  GCI_fina (Roache, Fs = 1.25, orden p observado) <= 3 % para la media de Uz_zona y de dw_max,
      si la convergencia es monotona; si es oscilante se informa y decide M1/M2.
  F_fuselaje_z se informa (no decide): es pequena y su error relativo no es representativo.
Pasa = M1 y M2 y M3.  Consecuencia si pasa: la suite usa la GRUESA si M1/M2 tambien se cumplen entre gruesa y
fina; si no, la MEDIA (decision documentada, no supuesta).

Uso: python scripts/compare_mesh.py [--sin-escribir]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from check_cfd0_conditions import leer_fuerza_final  # noqa: E402
from postprocess_case import leer_celdas, leer_log, perfiles_downwash, uz_zonas, yplus_suelo  # noqa: E402

CASES = ROOT / "cfd" / "cases"
NIVELES = {"gruesa": "A_T25P_V00.0_H2.5_f1.00_g2", "media": "A_T25P_V00.0_H2.5_f1.00_mmedia_g2",
           "fina": "A_T25P_V00.0_H2.5_f1.00_mfina_g2"}
SALIDA = ROOT / "evidence" / "cfd0_independencia_malla.json"
U_M1, U_M2, U_M3 = 2.0, 3.0, 3.0


def leer(nivel: str) -> dict | None:
    c = CASES / NIVELES[nivel]
    lg = leer_log(c) if c.exists() else {"termino": False}
    if not lg.get("termino") or lg.get("error"):
        return None
    perf = perfiles_downwash(c)
    n = len(json.loads((c / "case_meta.json").read_text(encoding="utf-8"))["zonas_rotor"])
    uz = uz_zonas(c, n)
    return {"celdas": leer_celdas(c), "iter": lg["iteraciones"], "conv_residuales": lg["convergido"],
            "Uz_zona": [uz.get(i) for i in range(1, n + 1)],
            "dw_max": [min(perf[f"rotor{i}"]["Uz"]) for i in range(1, n + 1)],
            "perfiles": {k: v["Uz"] for k, v in perf.items()},
            "F_fuselaje_z": leer_fuerza_final(c, "fuerza_fuselaje"), "y_plus_suelo": yplus_suelo(c)}


def rel(a, b):
    return 100 * abs(a - b) / abs(b)


def rms_rel(p, q):
    return 100 * math.sqrt(sum((x - y) ** 2 for x, y in zip(p, q)) / len(q)) / max(abs(y) for y in q)


def gci(f1, f2, f3, N1, N2, N3):
    """Roache/Celik (2008). 1 = fina. Devuelve dict con p, GCI_fina_pct, tipo de convergencia."""
    r21, r32 = (N1 / N2) ** (1 / 3), (N2 / N3) ** (1 / 3)
    e21, e32 = f2 - f1, f3 - f2
    if e21 == 0 or e32 == 0:
        return {"tipo": "sin cambio", "GCI_fina_pct": 0.0}
    s = e32 / e21
    if s < 0:
        return {"tipo": "oscilante", "r21": round(r21, 3), "r32": round(r32, 3)}
    sg = 1 if s > 0 else -1
    p = 1.0
    for _ in range(100):                       # iteracion de punto fijo (Celik et al. 2008)
        q = math.log((r21 ** p - sg) / (r32 ** p - sg))
        p = abs(math.log(abs(e32 / e21)) + q) / math.log(r21)
    ea21 = abs((f1 - f2) / f1)
    g = 1.25 * ea21 / (r21 ** p - 1)
    ext = (r21 ** p * f1 - f2) / (r21 ** p - 1)
    return {"tipo": "monotona", "p": round(p, 3), "r21": round(r21, 3), "r32": round(r32, 3),
            "GCI_fina_pct": round(100 * g, 3), "extrapolado": round(ext, 4)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sin-escribir", action="store_true")
    a = ap.parse_args()
    d = {k: leer(k) for k in NIVELES}
    faltan = [k for k, v in d.items() if v is None]
    res = {"criterio": {"M1_pct": U_M1, "M2_pct": U_M2, "M3_GCI_pct": U_M3}, "casos": NIVELES,
           "celdas": {k: (v or {}).get("celdas") for k, v in d.items()}}
    if "media" in faltan or "fina" in faltan:
        res.update(pasa=False, motivo=f"faltan corridas terminadas: {faltan}")
        print(json.dumps(res, indent=2, ensure_ascii=False))
        if not a.sin_escribir:
            SALIDA.write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return 1
    m, f = d["media"], d["fina"]
    m1 = {"Uz_zona_pct": [round(rel(x, y), 3) for x, y in zip(m["Uz_zona"], f["Uz_zona"])],
          "dw_max_pct": [round(rel(x, y), 3) for x, y in zip(m["dw_max"], f["dw_max"])]}
    m2 = {k: round(rms_rel(m["perfiles"][k], f["perfiles"][k]), 3) for k in sorted(f["perfiles"])}
    res["M1_media_vs_fina"] = m1
    res["M2_media_vs_fina_rms_pct"] = m2
    ok1 = max(m1["Uz_zona_pct"] + m1["dw_max_pct"]) <= U_M1
    ok2 = max(m2.values()) <= U_M2
    if d["gruesa"]:
        g = d["gruesa"]
        res["gruesa_vs_fina"] = {
            "Uz_zona_pct": [round(rel(x, y), 3) for x, y in zip(g["Uz_zona"], f["Uz_zona"])],
            "dw_max_pct": [round(rel(x, y), 3) for x, y in zip(g["dw_max"], f["dw_max"])],
            "perfil_rms_pct": {k: round(rms_rel(g["perfiles"][k], f["perfiles"][k]), 3) for k in sorted(f["perfiles"])}}
        res["gruesa_vs_media"] = {
            "Uz_zona_pct": [round(rel(x, y), 3) for x, y in zip(g["Uz_zona"], m["Uz_zona"])],
            "dw_max_pct": [round(rel(x, y), 3) for x, y in zip(g["dw_max"], m["dw_max"])],
            "perfil_rms_pct": {k: round(rms_rel(g["perfiles"][k], m["perfiles"][k]), 3) for k in sorted(m["perfiles"])}}
        N = (f["celdas"], m["celdas"], g["celdas"])
        media = lambda xs: sum(xs) / len(xs)  # noqa: E731
        res["M3_GCI"] = {"Uz_zona_media": gci(media(f["Uz_zona"]), media(m["Uz_zona"]), media(g["Uz_zona"]), *N),
                         "dw_max_media": gci(media(f["dw_max"]), media(m["dw_max"]), media(g["dw_max"]), *N),
                         "F_fuselaje_z (informativo)": gci(f["F_fuselaje_z"], m["F_fuselaje_z"], g["F_fuselaje_z"], *N)}
        gs = [res["M3_GCI"][k] for k in ("Uz_zona_media", "dw_max_media")]
        ok3 = all(x.get("GCI_fina_pct", 0) <= U_M3 for x in gs if x["tipo"] != "oscilante")
        osc = [k for k, x in zip(("Uz_zona_media", "dw_max_media"), gs) if x["tipo"] == "oscilante"]
        if osc:
            res["M3_nota"] = f"convergencia oscilante en {osc}: decide M1/M2"
    else:
        ok3 = False
        res["M3_nota"] = "sin malla gruesa terminada: no hay GCI"
    res["valores"] = {k: {kk: vv for kk, vv in v.items() if kk != "perfiles"} for k, v in d.items() if v}
    res["condiciones"] = {"M1": ok1, "M2": ok2, "M3": ok3}
    res["pasa"] = ok1 and ok2 and ok3
    if d["gruesa"]:
        gm = res["gruesa_vs_fina"]   # la gruesa basta solo si ya esta cerca de la fina
        gm_ok = max(gm["Uz_zona_pct"] + gm["dw_max_pct"]) <= U_M1 and max(gm["perfil_rms_pct"].values()) <= U_M2
        res["malla_para_la_suite"] = "gruesa" if gm_ok and res["pasa"] else ("media" if res["pasa"] else None)
    yp = {k: v["y_plus_suelo"] for k, v in d.items() if v and v.get("y_plus_suelo") is not None}
    fuera = [k for k, y in yp.items() if not 30 <= y <= 300]
    res["y_plus_suelo"] = yp
    res["y_plus_nota"] = (f"y+ medio del suelo fuera de 30-300 (funciones de pared) en {fuera}: el suelo esta "
                          "infra-resuelto en la direccion normal; decidir capa de prismas" if fuera else "y+ del suelo en 30-300")
    res["generado"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(json.dumps(res, indent=2, ensure_ascii=False))
    if not a.sin_escribir:
        SALIDA.write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"-> {SALIDA.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
