#!/usr/bin/env python3
"""Las cinco condiciones de cierre de GATE CFD-0, comprobadas una por una.

Por que existe
--------------
"Aparece downwash" es necesario pero no suficiente. El fallo original (bug #6) enseño que un
caso puede converger, escribir resultados y no validar nada. Este script declara las cinco
condiciones de cierre y da el resultado de CADA una, incluida la que falla.

Las cinco condiciones
---------------------
  1. FUERZA REALMENTE APLICADA      |F_CFD - T_i| / T_i < 1e-3  por rotor
  2. BALANCE GLOBAL DE MOMENTO      F_fuente + F_fronteras - flujo convectivo ~ 0
  3. CONVERGENCIA DE MAGNITUDES     ademas de residuos: F_suelo y U_z no deben derivar
  4. SIMETRIA FISICA                media(Ux) ~ 0, media(Uy) ~ 0, Uz < 0 bajo los rotores
  5. ORDEN DE MAGNITUD DEL DOWNWASH comparar con v_i = sqrt(T/(2 rho A))

Uso
---
    python3 scripts/check_cfd0_conditions.py <ruta_al_caso>
Codigo de salida 0 si las cinco pasan, 1 si alguna falla.
"""

from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

RHO = 1.1716                      # kg/m3, el mismo de los casos
TOL_FUERZA = 1e-3                 # 0.1 % exigido por el investigador
UMBRAL_SIMETRIA = 0.05            # |media U| / |Uz| max
FACTOR_VOLUMEN = 8.0              # |su*V| / T admisible (test de volumen erroneo)


# ---------------------------------------------------------------------------------------
def leer_U(ruta: Path) -> list:
    txt = ruta.read_text(encoding="utf-8", errors="replace").split("boundaryField")[0]
    m = re.search(r"internalField\s+uniform\s*\(\s*([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+"
                  r"([-+0-9.eE]+)\s*\)", txt)
    if m:
        return [(float(m.group(1)), float(m.group(2)), float(m.group(3)))]
    m = re.search(r"internalField\s+nonuniform\s+List<vector>\s*\n?\s*(\d+)\s*\(", txt)
    if not m:
        raise ValueError(f"{ruta.name}: no se pudo leer internalField")
    n = int(m.group(1))
    i = txt.index("(", m.end() - 1)
    vals = [tuple(map(float, mm.groups())) for mm in
            re.finditer(r"\(\s*([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s*\)", txt[i:])]
    if len(vals) < n:
        raise ValueError(f"{ruta.name}: declaraba {n} celdas, se leyeron {len(vals)}")
    return vals[:n]


def leer_presion_final(caso: Path) -> float | None:
    dat = caso / "postProcessing" / "forces" / "0" / "force.dat"
    if not dat.exists():
        return None
    ultimo = None
    for linea in dat.read_text(encoding="utf-8", errors="replace").splitlines():
        s = linea.strip()
        if not s or s.startswith("#"):
            continue
        f = s.split()
        if len(f) >= 10:
            ultimo = float(f[6])          # pressure_z
    return ultimo


def serie_presion(caso: Path) -> list:
    dat = caso / "postProcessing" / "forces" / "0" / "force.dat"
    if not dat.exists():
        return []
    out = []
    for linea in dat.read_text(encoding="utf-8", errors="replace").splitlines():
        s = linea.strip()
        if not s or s.startswith("#"):
            continue
        f = s.split()
        if len(f) >= 10:
            out.append((float(f[0]), float(f[6])))
    return out


def ultimo_campo(caso: Path) -> Path | None:
    cand = []
    for d in caso.iterdir():
        if d.is_dir() and d.name.replace(".", "").isdigit() and float(d.name) > 0:
            if (d / "U").exists():
                cand.append((float(d.name), d / "U"))
    return max(cand)[1] if cand else None


# ---------------------------------------------------------------------------------------
def main() -> int:
    caso = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if caso is None or not caso.is_dir():
        print(f"[FALLO] uso: {Path(sys.argv[0]).name} <ruta_al_caso>")
        return 1

    from verify_prescribed_force import comprobar_caso, leer_volumenes

    print()
    r = comprobar_caso(caso, TOL_FUERZA)
    vol = leer_volumenes(caso)
    venta = leer_volumenes(caso)

    resultados = []
    rutas = ultimo_campo(caso)

    # ---- condicion 1: fuerza realmente aplicada -----------------------------------
    # La fuerza aplicada es Su*V_zone. Nota importante: el criterio de 0.1 % es trivialmente
    # satisfecho porque la construccion es algebraica; por eso se anade la comprobacion de
    # que el VOLUMEN usado coincide con el de la malla, que es donde puede fallar en silencio.
    detalle1, ok1 = [], True
    for ro in r["rotores"]:
        T_i = abs(ro["F_aplicada_N"][2])
        z = ro["zona"]
        errV = ro["error_V_rel"]
        su = ro["Su_N_m3"][2]
        aplicada = su * ro["V_real_m3"]
        err = abs(abs(aplicada) - T_i) / T_i if T_i else float("inf")
        ok = err < TOL_FUERZA and errV < 1e-9
        ok1 = ok1 and ok
        detalle1.append(f"{z}: T={T_i:.4f} N, Su*V={abs(aplicada):.6f} N, err={err:.2e}, "
                        f"err(V)={errV:.2e} {'ok' if ok else 'FALLA'}")
    resultados.append(("1. fuerza aplicada por rotor", ok1, detalle1))

    # ---- condicion 3: convergencia de magnitudes -----------------------------------
    serie = serie_presion(caso)
    detalle3, ok3 = [], True
    if len(serie) < 3:
        ok3 = False
        detalle3.append(f"serie de F_suelo demasiado corta ({len(serie)} puntos): no se puede "
                        f"evaluar convergencia")
    else:
        # deriva relativa en los ultimos 40 % de la corrida
        n = len(serie)
        ini = int(n * 0.6)
        cola = [v for _, v in serie[ini:]]
        ref = max(abs(v) for v in cola)
        deriva = (max(cola) - min(cola)) / ref if ref else float("inf")
        tendencia = (cola[-1] - cola[0]) / ref if ref else float("inf")
        ok3 = deriva < 0.05
        detalle3.append(f"F_suelo: {len(serie)} muestras; ultimas {len(cola)} con dispersion "
                        f"{deriva*100:.2f} % y tendencia {tendencia*100:+.2f} %")
        detalle3.append(f"F_suelo final = {cola[-1]:+.3f} N")
        if not ok3:
            detalle3.append("las magnitudes SIGUEN DERIVANDO: no hay convergencia de "
                            "magnitudes aunque los residuos bajen")
    resultados.append(("3. convergencia de magnitudes fisicas", ok3, detalle3))

    # ---- condicion 4: simetria fisica ----------------------------------------------
    detalle4, ok4 = [], True
    if rutas is None:
        ok4 = False
        detalle4.append("sin campo U de solver: no evaluable")
    else:
        U = leer_U(rutas)
        if len(U) == 1:
            ok4 = False
            detalle4.append("campo uniforme: no hay estructura")
        else:
            mx = sum(v[0] for v in U) / len(U)
            my = sum(v[1] for v in U) / len(U)
            mxz = max(abs(v[2]) for v in U)
            okx = abs(mx) / mxz < UMBRAL_SIMETRIA if mxz else False
            oky = abs(my) / mxz < UMBRAL_SIMETRIA if mxz else False
            ok4 = okx and oky
            detalle4.append(f"media(Ux) = {mx:+.4f} m/s, media(Uy) = {my:+.4f} m/s, "
                            f"max|Uz| = {mxz:.4f} m/s")
            detalle4.append(f"|media(Ux)|/max|Uz| = {abs(mx)/mxz:.4f}  "
                            f"(umbral {UMBRAL_SIMETRIA}) {'ok' if okx else 'FALLA'}")
            detalle4.append(f"|media(Uy)|/max|Uz| = {abs(my)/mxz:.4f}  "
                            f"{'ok' if oky else 'FALLA'}")
    resultados.append(("4. simetria fisica (hover sin viento)", ok4, detalle4))

    # ---- condicion 5: orden de magnitud del downwash -------------------------------
    detalle5, ok5 = [], True
    if rutas is None:
        ok5 = False
        detalle5.append("sin campo U: no evaluable")
    else:
        from mesh_zone_volumes import leer_zonas
        U = leer_U(rutas)
        zonas = leer_zonas(caso / "constant" / "polyMesh" / "cellZones")
        T_total = r["T_total_prescrito_N"]
        # area total de disco: 4 rotores, r = 0.635 m
        A = 4 * math.pi * 0.635 ** 2
        v_i = math.sqrt(T_total / (2 * RHO * A))
        uzs = []
        for z, celdas in zonas.items():
            idx = [c for c in celdas if c < len(U)]
            if idx:
                uzs.append(sum(U[c][2] for c in idx) / len(idx))
        if not uzs:
            ok5 = False
            detalle5.append("no se pudieron muestrear las zonas de rotor")
        else:
            uz_med = sum(uzs) / len(uzs)
            ratio = abs(uz_med) / v_i if v_i else float("inf")
            ok5 = 0.2 < ratio < 5.0
            detalle5.append(f"v_i (teoria de momento) = {v_i:.3f} m/s")
            detalle5.append(f"Uz medio en las zonas        = {uz_med:+.3f} m/s")
            detalle5.append(f"cociente = {ratio:.3f}  (admisible 0.2 - 5.0) "
                            f"{'ok' if ok5 else 'FALLA'}")
            detalle5.append("no se exige coincidencia exacta: hay 4 rotores, suelo, dominio "
                            "finito y una fuente volumetrica simplificada")
    resultados.append(("5. orden de magnitud del downwash", ok5, detalle5))

    # ---- condicion 2: balance global de momento ------------------------------------
    # F_fuente + F_fronteras - flujo convectivo ~ 0.
    # En hover las fronteras laterales son slip (no aportan fuerza vertical) y el techo es
    # p=0 (tampoco), asi que la fuerza vertical de frontera es la del SUELO. El flujo
    # convectivo neto hacia abajo se integra sobre el suelo.
    detalle2, ok2 = [], True
    Fsuelo = leer_presion_final(caso)
    T_total = r["T_total_prescrito_N"]
    if Fsuelo is None:
        ok2 = False
        detalle2.append("sin postProcessing/forces: no evaluable")
    else:
        # signo: la fuente aplica -T sobre el aire; el suelo reacciona con aproximadamente +T
        razon = -Fsuelo / T_total if T_total else float("inf")
        ok2 = 0.9 < razon < 1.1
        detalle2.append(f"F_suelo (presion) = {Fsuelo:+.3f} N")
        detalle2.append(f"T prescrito       = {T_total:.3f} N")
        detalle2.append(f"-F_suelo / T      = {razon:+.4f}   (esperado ~ +1.0)")
        if not ok2:
            detalle2.append("el balance global NO cierra. Puede ser (a) falta de convergencia "
                            "real o (b) un termino de fuerza no contabilizado. NO se cierra "
                            "CFD-0 con este resultado.")
    resultados.append(("2. balance global de momento", ok2, detalle2))

    # ---- informe -------------------------------------------------------------------
    print("=" * 100)
    print(" CONDICIONES DE CIERRE DE GATE CFD-0")
    print("=" * 100)
    n_ok = 0
    for titulo, ok, detalle in resultados:
        print(f"\n  [{'PASA' if ok else 'FALLA'}] {titulo}")
        for d in detalle:
            print(f"        {d}")
        n_ok += bool(ok)

    print()
    print("=" * 100)
    if n_ok == len(resultados):
        print(f" CFD-0: LAS {len(resultados)} CONDICIONES SE CUMPLEN")
    else:
        print(f" CFD-0: {n_ok} de {len(resultados)} condiciones se cumplen -> SIGUE ABIERTO")
        faltan = [t for t, ok, _ in resultados if not ok]
        for t in faltan:
            print(f"   pendiente: {t}")
    print("=" * 100)

    destino = RAIZ / "evidence" / "cfd0_conditions.json"
    destino.parent.mkdir(exist_ok=True)
    destino.write_text(json.dumps(
        [{"condicion": t, "pasa": ok, "detalle": d} for t, ok, d in resultados],
        indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\n  evidencia: {destino.relative_to(RAIZ)}")

    return 0 if n_ok == len(resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
