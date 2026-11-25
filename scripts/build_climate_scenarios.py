"""
ESCENARIOS CLIMATICOS DE VERACRUZ para la evaporacion de gotas (nivel B), derivados de datos.

Fuente: METAR horarios de MMVR (Aeropuerto Gral. Heriberto Jara, Veracruz), 2010-2025, descargados
del archivo ASOS/METAR del Iowa Environmental Mesonet (IEM). Clase M (instrumental de la estacion),
con el SHA-256 del archivo bruto. `Metodologia de calculo.md` §7.3 pedia exactamente esto.

Que hace
--------
1. Filtra las horas de aplicacion, hora local (America/Mexico_City): por defecto 06:00-09:59 Y
   16:00-18:59 (manana y tarde; §7.3 solo pedia la manana, pero tambien se fumiga por la tarde y
   las mananas de Veracruz estan casi saturadas: con solo la manana P5 y P10 salen ambos dT = 0).
2. Calcula por observacion:
     P_estacion  desde el altimetro QNH y la elevacion (12 m), atmosfera estandar
     rho         aire humedo (Magnus + gas ideal de dos componentes, igual que §7.1)
     T_bh        temperatura de bulbo humedo: psicrometria iterativa a la P de la estacion
     dT_bh       T - T_bh: el motor de la evaporacion (lo que se usa en deriva de pulverizacion)
3. Escenarios = cuantiles de dT_bh: {P10, P25, P50, P75, P90, P95, P99} (7). En cada uno, T es la
   MEDIA de las observaciones reales en una banda de +-2.5 puntos de percentil (P99: +-1) y P la
   mediana; la HR se RESUELVE para que T - T_bh sea exactamente el cuantil. Asi T y HR son una
   combinacion que de verdad ocurre (no se cruzan percentiles de T y de HR, que daria climas
   inexistentes) y el motor de la evaporacion queda fijado. El METAR da T en grados enteros:
   por eso T es media y no mediana.
4. Escribe `data/processed/clima_MMVR_escenarios.json` y la tabla `climate_scenarios`.

Uso:
    python scripts/build_climate_scenarios.py [--horas 6-9] [--escribir-db]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
CRUDO = ROOT / "data" / "raw" / "clima_MMVR" / "MMVR_2010_2025_metar.csv"
SALIDA = ROOT / "data" / "processed" / "clima_MMVR_escenarios.json"
DB = ROOT / "data" / "processed" / "dronewith.sqlite"
URL = ("https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?station=MMVR&data=tmpf&data=dwpf"
       "&data=relh&data=alti&data=sknt&data=drct&tz=America/Mexico_City&format=onlycomma&latlon=no"
       "&missing=M&report_type=3&report_type=4&year1=2010&month1=1&day1=1&year2=2025&month2=12&day2=31")
ELEV_M = 12.0          # elevacion de MMVR (aprox., AIP); el efecto sobre P es ~0.15 %
CUANTILES = (10, 25, 50, 75, 90, 95, 99)
BANDA = 2.5
RHO_CASOS = 1.1716     # la de los casos de aire (Entry 023: se mantiene y se declara)


def p_sat(Tc: float) -> float:
    return 610.94 * math.exp(17.625 * Tc / (Tc + 243.04))          # Pa, Magnus (§7.1)


def rho_humedo(Tc: float, rh: float, P: float) -> float:
    pv = rh * p_sat(Tc)
    T = Tc + 273.15
    return (P - pv) / (287.058 * T) + pv / (461.495 * T)


def bulbo_humedo(Tc: float, rh: float, P: float) -> float:
    """Psicrometria: e = e_s(Tw) - gamma*P*(T - Tw), gamma = 6.62e-4 /K (psicrometro ventilado)."""
    e = rh * p_sat(Tc)
    lo, hi = -10.0, Tc
    for _ in range(60):
        tw = 0.5 * (lo + hi)
        if p_sat(tw) - 6.62e-4 * P * (Tc - tw) > e:
            hi = tw
        else:
            lo = tw
    return 0.5 * (lo + hi)


def p_estacion(alti_inhg: float) -> float:
    qnh = alti_inhg * 3386.389
    return qnh * (1 - 2.25577e-5 * ELEV_M) ** 5.25588


def hr_para_dT(Tc: float, P: float, dT: float) -> float:
    lo, hi = 0.05, 1.0
    for _ in range(60):
        rh = 0.5 * (lo + hi)
        if Tc - bulbo_humedo(Tc, rh, P) > dT:
            lo = rh
        else:
            hi = rh
    return 0.5 * (lo + hi)


def leer(ventanas: list[tuple[int, int]]) -> tuple[list[dict], dict]:
    obs, desc = [], {"total": 0, "sin_dato": 0, "fuera_de_hora": 0, "fuera_de_rango": 0}
    with open(CRUDO, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            desc["total"] += 1
            if "M" in (r["tmpf"], r["dwpf"], r["alti"]):
                desc["sin_dato"] += 1
                continue
            t = datetime.strptime(r["valid"], "%Y-%m-%d %H:%M")
            if not any(a <= t.hour <= b for a, b in ventanas):
                desc["fuera_de_hora"] += 1
                continue
            Tc = (float(r["tmpf"]) - 32) / 1.8
            Td = (float(r["dwpf"]) - 32) / 1.8
            rh = min(1.0, p_sat(Td) / p_sat(Tc))         # de T y Td (mas preciso que relh redondeada)
            alti = float(r["alti"])
            if not (5 < Tc < 45 and 0.05 < rh <= 1 and 28.5 < alti < 31.0):
                desc["fuera_de_rango"] += 1
                continue
            P = p_estacion(alti)
            tw = bulbo_humedo(Tc, rh, P)
            obs.append({"t": t, "T": Tc, "RH": rh, "P": P, "rho": rho_humedo(Tc, rh, P),
                        "Tw": tw, "dT": Tc - tw, "viento_ms": float(r["sknt"]) * 0.514444
                        if r["sknt"] not in ("M", "") else None})
    return obs, desc


def cuantil(xs: list[float], q: float) -> float:
    s = sorted(xs)
    k = (len(s) - 1) * q / 100.0
    i = int(k)
    return s[i] + (s[min(i + 1, len(s) - 1)] - s[i]) * (k - i)


def escenarios(obs: list[dict]) -> list[dict]:
    dts = [o["dT"] for o in obs]
    out = []
    for q in CUANTILES:
        b = min(BANDA, 100 - q, q)
        b = 1.0 if q >= 99 else b
        lo, hi = cuantil(dts, q - b), cuantil(dts, q + b)
        sel = [o for o in obs if lo <= o["dT"] <= hi]
        dT = cuantil(dts, q)
        T, P = sum(o["T"] for o in sel) / len(sel), median(o["P"] for o in sel)
        RH = hr_para_dT(T, P, dT)
        tw = bulbo_humedo(T, RH, P)
        meses = {}
        for o in sel:
            meses[o["t"].month] = meses.get(o["t"].month, 0) + 1
        out.append({"clima_id": f"VER_P{q:02d}", "cuantil_dT": q, "dT_bh_K": round(T - tw, 3),
                    "T_C": round(T, 2), "HR": round(RH, 4), "P_Pa": round(P, 1),
                    "rho_kg_m3": round(rho_humedo(T, RH, P), 4),
                    "rho_vs_casos_pct": round(100 * (rho_humedo(T, RH, P) / RHO_CASOS - 1), 2),
                    "T_bh_C": round(tw, 2), "n_obs_banda": len(sel),
                    "meses_mas_frecuentes": sorted(meses, key=meses.get, reverse=True)[:3]})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--horas", default="6-9,16-18")
    ap.add_argument("--escribir-db", action="store_true")
    a = ap.parse_args()
    vent = [tuple(int(x) for x in w.split("-")) for w in a.horas.split(",")]
    sha = hashlib.sha256(CRUDO.read_bytes()).hexdigest()
    obs, desc = leer(vent)
    hs = ", ".join(f"{x:02d}:00-{y:02d}:59" for x, y in vent)
    esc = escenarios(obs)
    anios = sorted({o["t"].year for o in obs})
    print(f"MMVR {anios[0]}-{anios[-1]}  horas {hs}  obs validas {len(obs)}  {desc}")
    print(f"sha256 {sha[:16]}...")
    print(f"\n  {'id':8s} {'dT_bh':>6s} {'T':>6s} {'HR':>6s} {'P kPa':>7s} {'rho':>7s} {'vs 1.1716':>9s}  meses")
    for e in esc:
        print(f"  {e['clima_id']:8s} {e['dT_bh_K']:6.2f} {e['T_C']:6.2f} {100*e['HR']:6.1f} {e['P_Pa']/1000:7.2f} "
              f"{e['rho_kg_m3']:7.4f} {e['rho_vs_casos_pct']:+8.2f}%  {e['meses_mas_frecuentes']}")
    rhos = [o["rho"] for o in obs]
    print(f"\n  rho en horas de aplicacion: P1 {cuantil(rhos, 1):.4f}  P50 {cuantil(rhos, 50):.4f}  "
          f"P99 {cuantil(rhos, 99):.4f} kg/m3")
    vs = [o["viento_ms"] for o in obs if o["viento_ms"] is not None]
    print(f"  viento (referencia, no se usa): P50 {cuantil(vs, 50):.1f}  P90 {cuantil(vs, 90):.1f} m/s")
    res = {"fuente": "METAR MMVR via IEM ASOS", "url": URL, "archivo": str(CRUDO.relative_to(ROOT)).replace("\\", "/"),
           "sha256": sha, "clase": "M", "horas_locales": hs, "anios": [anios[0], anios[-1]],
           "n_obs": len(obs), "descartes": desc, "metodo": "cuantiles de T - T_bh; T, HR, P = medianas en banda +-2.5",
           "rho_P1_P50_P99": [round(cuantil(rhos, q), 4) for q in (1, 50, 99)],
           "escenarios": esc, "generado": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    SALIDA.write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\n  -> {SALIDA.relative_to(ROOT)}")
    if a.escribir_db:
        con = sqlite3.connect(DB)
        con.execute("""CREATE TABLE IF NOT EXISTS climate_scenarios (
            clima_id TEXT PRIMARY KEY, cuantil_dT INTEGER, dT_bh_K REAL, T_C REAL, HR REAL, P_Pa REAL,
            rho_kg_m3 REAL, T_bh_C REAL, n_obs_banda INTEGER, horas TEXT, clase TEXT, fuente TEXT)""")
        for e in esc:
            con.execute("INSERT OR REPLACE INTO climate_scenarios VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                        (e["clima_id"], e["cuantil_dT"], e["dT_bh_K"], e["T_C"], e["HR"], e["P_Pa"],
                         e["rho_kg_m3"], e["T_bh_C"], e["n_obs_banda"], res["horas_locales"], "M",
                         f"METAR MMVR {anios[0]}-{anios[-1]} (IEM), sha256 {sha[:16]}"))
        con.commit()
        con.close()
        print("  -> tabla climate_scenarios")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
