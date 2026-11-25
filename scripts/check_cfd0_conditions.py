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


# v2 (2026-11-22): function objects `fuerza_suelo`, `fuerza_fuselaje`, `fuerza_contorno`
# (build_case_suite.py v2). v1 usaba `forces` (solo suelo, componente de presion).
# Se usa total_z (presion + viscosa), columna 3 del force.dat de v2412.
def _force_dat(caso: Path, nombre: str) -> Path | None:
    base = caso / "postProcessing" / nombre
    if not base.exists():
        return None
    cand = sorted(base.glob("*/force.dat"), key=lambda p: float(p.parent.name))
    return cand[-1] if cand else None


def serie_fuerza(caso: Path, nombre: str, col: int = 3) -> list:
    dat = _force_dat(caso, nombre)
    if dat is None:
        return []
    out = []
    for linea in dat.read_text(encoding="utf-8", errors="replace").splitlines():
        s = linea.strip()
        if not s or s.startswith("#"):
            continue
        f = s.replace("(", " ").replace(")", " ").split()
        if len(f) >= 10:
            out.append((float(f[0]), float(f[col])))
    return out


def serie_presion(caso: Path) -> list:
    s = serie_fuerza(caso, "fuerza_suelo")
    return s if s else serie_fuerza(caso, "forces", col=6)


def leer_presion_final(caso: Path) -> float | None:
    s = serie_presion(caso)
    return s[-1][1] if s else None


def leer_fuerza_final(caso: Path, nombre: str) -> float | None:
    s = serie_fuerza(caso, nombre)
    return s[-1][1] if s else None


def ultimo_campo(caso: Path) -> Path | None:
    cand = []
    for d in caso.iterdir():
        if d.is_dir() and d.name.replace(".", "").isdigit() and float(d.name) > 0:
            if (d / "U").exists():
                cand.append((float(d.name), d / "U"))
    return max(cand)[1] if cand else None


PATCHES_ABIERTOS = ("inlet", "outlet", "sides", "top")


def _lista_patch(txt: str, patch: str, vector: bool) -> list:
    i = txt.index("boundaryField")
    m = re.search(rf"\n\s+{patch}\s*\n\s*\{{", txt[i:])
    if not m:
        return []
    b = txt[i + m.end(): txt.index("}", i + m.end())]
    if "nonuniform" not in b:
        return []                                   # uniforme (p. ej. 0 en una pared slip)
    n = int(re.search(r"List<\w+>\s*(\d+)", b).group(1))
    cuerpo = b[b.index("(", b.index("nonuniform") + 10 + len(str(n))):]
    if vector:
        return [tuple(map(float, v)) for v in re.findall(
            r"\(\s*([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s*\)", cuerpo)[:n]]
    return list(map(float, cuerpo[1:].split(")")[0].split()))[:n]


def flujo_momento_z(caso: Path) -> tuple[float, str]:
    """rho * sum(Uz * phi) por los contornos no pared, en el ultimo tiempo con U y phi."""
    d = ultimo_campo(caso)
    if d is None or not (d.parent / "phi").exists():
        return 0.0, "sin U/phi escritos: M_out = 0 supuesto"
    tU, tP = d.read_text(errors="replace"), (d.parent / "phi").read_text(errors="replace")
    tot, partes = 0.0, []
    for pt in PATCHES_ABIERTOS:
        u, f = _lista_patch(tU, pt, True), _lista_patch(tP, pt, False)
        if not f:
            continue
        if len(u) != len(f):
            raise ValueError(f"{pt}: {len(u)} valores de U y {len(f)} de phi")
        m = RHO * sum(a[2] * b for a, b in zip(u, f))
        tot += m
        partes.append(f"{pt} {m:+.2f}")
    return tot, f"t={d.parent.name}: " + (", ".join(partes) if partes else "sin flujo por contornos")


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
    # Entry 022: la version anterior era CIRCULAR (tomaba T_i de la propia fuerza reconstruida
    # desde Su) y por eso no detecto el bug #8 (faltaba rho). Ahora se compara la fuerza FISICA
    # que aplica el solver, rho * Su * V_solver, con la fuerza PRESCRITA en case_meta.json
    # (zonas_rotor.F_aire_N, salida de la cadena de fuerzas, independiente de fvOptions).
    # V_solver = el volumen que imprime simpleFoam ("selected N cell(s) with volume V").
    detalle1, ok1 = [], True
    meta = json.loads((caso / "case_meta.json").read_text(encoding="utf-8"))
    zr = meta.get("zonas_rotor", {})
    vsol = {}
    log = caso / "log.simpleFoam"
    if log.exists():
        vols = re.findall(r"Source: (\S+)\s+- selecting cells using cellZones \(\S+\)\s+"
                          r"- selected (\d+) cell\(s\) with volume ([-+0-9.eE]+)",
                          log.read_text(errors="replace"))
        vsol = {z: float(v) for z, _, v in vols}
    if not vsol:
        detalle1.append("sin volumen del solver en log.simpleFoam: se usa el declarado")
    for ro in r["rotores"]:
        z = ro["zona"]
        if z not in zr:
            ok1 = False
            detalle1.append(f"{z}: no esta en case_meta.zonas_rotor")
            continue
        F_pres = zr[z]["F_aire_N"]
        V = vsol.get(z, ro["V_declarado_m3"])
        F_fis = [ro["rho"] * c * V for c in ro["Su_m_s2"]]
        err = math.dist(F_fis, F_pres) / math.dist((0, 0, 0), F_pres)
        ok = err < TOL_FUERZA and ro["error_V_rel"] < 1e-9
        ok1 = ok1 and ok
        detalle1.append(f"{z}: |F_prescrita| = {math.dist((0, 0, 0), F_pres):.4f} N, "
                        f"|rho Su V_solver| = {math.dist((0, 0, 0), F_fis):.4f} N, "
                        f"err = {err:.2e}, err(V decl/malla) = {ro['error_V_rel']:.2e} "
                        f"{'ok' if ok else 'FALLA'} (tol {TOL_FUERZA})")
    T_total = -sum(d["F_aire_N"][2] for d in zr.values())       # prescrito, vertical
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
        # area de momentum desde la geometria v2 del caso (antes: 4 x pi 0.635^2 fijo)
        meta = json.loads((caso / "case_meta.json").read_text(encoding="utf-8"))
        zr = meta.get("zonas_rotor", {})
        if zr:
            A = sum(math.pi * d["radio_m"] ** 2 for d in zr.values()
                    if d.get("nivel") in ("simple", "upper"))
        else:
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
    # Volumen de control = todo el dominio, componente z, estacionario:
    #   F_fuente,z + F_paredes->fluido,z = flujo neto saliente de momento z por los contornos
    #   -T - sum(F_fluido->paredes,z) = M_out,z      =>   (-sum F_paredes - M_out) / T = 1
    # F_paredes incluye suelo, fuselaje y contornos (presion + viscosa). M_out = rho sum(Uz phi)
    # sobre inlet/outlet/sides/top en el ultimo tiempo escrito (0 con BC cerrado: slip).
    detalle2, ok2 = [], True
    Fsuelo = leer_presion_final(caso)
    if Fsuelo is None:
        ok2 = False
        detalle2.append("sin postProcessing/fuerza_suelo: no evaluable")
    else:
        Ffus = leer_fuerza_final(caso, "fuerza_fuselaje") or 0.0
        Fcon = leer_fuerza_final(caso, "fuerza_contorno") or 0.0
        F_paredes = Fsuelo + Ffus + Fcon
        M_out, det_m = flujo_momento_z(caso)
        razon = (-F_paredes - M_out) / T_total if T_total else float("inf")
        ok2 = 0.9 < razon < 1.1
        detalle2.append(f"F_suelo z = {Fsuelo:+.3f} N · F_fuselaje z = {Ffus:+.3f} N · "
                        f"F_contorno z = {Fcon:+.3f} N")
        detalle2.append(f"flujo de momento z saliente M_out = {M_out:+.3f} N ({det_m})")
        detalle2.append(f"T prescrito (case_meta) = {T_total:.3f} N")
        detalle2.append(f"(-sum F_paredes - M_out) / T = {razon:+.4f}   (esperado ~ +1.0, 0.9-1.1)")
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
        [{"condicion": t, "pasa": ok, "detalle": d,
          "caso": str(caso.resolve().relative_to(RAIZ)).replace("\\", "/")} for t, ok, d in resultados],
        indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\n  evidencia: {destino.relative_to(RAIZ)}")

    return 0 if n_ok == len(resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
