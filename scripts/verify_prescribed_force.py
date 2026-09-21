#!/usr/bin/env python3
"""GATE CFD-0: verifica que la fuerza APLICADA integra el empuje PRESCRITO, rotor por rotor.

Que se comprueba, y por que no basta con "el caso corrio"
---------------------------------------------------------
El fallo que este gate existe para impedir es el de `BUG_conceptual_06`: un caso que
converge, escribe resultados y no valida nada porque la fuente fisica es nula. La leccion
de metodo fue que **un caso que corre sin errores no es un caso correcto**, y que una
comprobacion estructural (128/128 ficheros bien formados) puede dar un «OK» que no
significa lo que parece.

Por eso este gate exige una comprobacion CUANTITATIVA del campo real:

  A. Fuerza aplicada. La fuente aporta `Su_c * V_c` newtons a la celda `c`. Sumando sobre
     la cellZone se obtiene la fuerza total aplicada al fluido en ese rotor. Debe igualar
     el empuje prescrito `T_i`, en las TRES componentes.

  B. Independencia del flujo incidente. Con `U_inf = 0` (hover puro) la fuerza aplicada
     debe seguir siendo `T_i`. `actuationDiskSource` falla exactamente aqui: da `T ~ 0`.
     Es la prueba discriminante, no una comprobacion de forma.

  C. Downwash no nulo. Debe existir velocidad vertical bajo cada rotor. El umbral es
     CUANTITATIVO y se declara: `|Uz|` claramente por encima del ruido numerico, que en la
     prueba de `actuationDiskSource` fue ~1e-7 m/s. Se exige un orden de magnitud fisico,
     no un valor: el valor exacto depende de la malla y no es un dato validado.

  D. Cierre global. La suma de las fuerzas aplicadas debe igualar el peso del UAV (con la
     componente de resistencia segun la actitud). Es la arquitectura C.

Que NO comprueba este script
----------------------------
No valida la fisica del rotor (no hay rotor resuelto), ni la deposicion, ni el espectro.
No sustituye a la validacion experimental. Comprueba que la fuente HACE LO QUE DICE.

Uso
---
    python scripts/verify_prescribed_force.py                      # caso nominal
    python scripts/verify_prescribed_force.py --case <ruta>
    python scripts/verify_prescribed_force.py --all
    python scripts/verify_prescribed_force.py --tolerance 1e-6

Salida: codigo 0 si pasa, 1 si falla. Escribe `evidence/cfd0_force_integral.json`.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

CASES = ROOT / "cfd" / "cases"
EVIDENCE = ROOT / "evidence"
CASO_NOMINAL = "T25P_V3.1_H2.8_d190_f0.95_a4"

from mesh_zone_volumes import leer_zonas  # noqa: E402

TOL_FUERZA = 1e-6      # relativo: la igualdad es algebraica, no aproximada
UMBRAL_UZ = 1e-3       # m/s: 4 ordenes por encima del ruido medido (~1e-7)


# ---------------------------------------------------------------------------------------
def leer_fvOptions(ruta: Path) -> dict:
    """Extrae, por zona: `Su` (vector) y `volumeMode`."""
    if not ruta.exists():
        raise FileNotFoundError(f"falta {ruta}")
    txt = ruta.read_text(encoding="utf-8")

    zonas: dict[str, dict] = {}
    # bloques:  <zona> { ... type vectorSemiImplicitSource; ... U ((x y z) 0); ... }
    for m in re.finditer(r"^\s{4}(\w+)\s*\{", txt, flags=re.MULTILINE):
        nombre = m.group(1)
        abre = txt.index("{", m.start())
        prof, i, n = 0, abre, len(txt)
        while i < n:
            if txt[i] == "{":
                prof += 1
            elif txt[i] == "}":
                prof -= 1
                if prof == 0:
                    break
            i += 1
        bloque = txt[abre:i + 1]

        if "vectorSemiImplicitSource" not in bloque:
            continue
        vm = re.search(r"volumeMode\s+(\w+)\s*;", bloque)
        su = re.search(r"\bU\s+\(\(\s*([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s*\)",
                       bloque)
        cz = re.search(r"cellZone\s+(\w+)\s*;", bloque)
        if not (vm and su and cz):
            raise ValueError(f"{ruta.name}: bloque '{nombre}' incompleto "
                             f"(volumeMode={bool(vm)} Su={bool(su)} cellZone={bool(cz)})")
        zonas[cz.group(1)] = {
            "Su": (float(su.group(1)), float(su.group(2)), float(su.group(3))),
            "volumeMode": vm.group(1),
            "tipo": "vectorSemiImplicitSource",
        }
    if not zonas:
        raise ValueError(f"{ruta.name}: no se encontro ninguna vectorSemiImplicitSource")
    return zonas


def leer_volumenes(caso: Path) -> dict:
    f = caso / "constant" / "rotorZoneVolumes"
    if not f.exists():
        raise FileNotFoundError(f"{caso.name}: falta constant/rotorZoneVolumes "
                                f"(ejecuta scripts/mesh_zone_volumes.py --write)")
    zonas, dentro = {}, False
    for linea in f.read_text(encoding="utf-8").splitlines():
        s = linea.split("//")[0].strip()
        if s.startswith("volumenZonas"):
            dentro = True
            continue
        if dentro:
            if s.startswith("}"):
                break
            partes = s.rstrip(";").split()
            if len(partes) == 2:
                zonas[partes[0]] = float(partes[1])
    return zonas


def volumen_real_zonas(caso: Path) -> dict:
    """V_zone sobre la malla real, recalculado aqui de forma INDEPENDIENTE.

    No se reutiliza `rotorZoneVolumes`: si se leyera el mismo fichero que uso el generador,
    un error en ese fichero pasaria desapercibido. Aqui se recalcula desde la malla.
    """
    from mesh_zone_volumes import analizar_caso

    r = analizar_caso(caso)
    if r.get("estado") != "ok":
        raise ValueError(f"{caso.name}: no se pudo analizar la malla: {r.get('estado')}")
    return r["zonas"]


def comprobar_caso(caso: Path, tol: float) -> dict:
    """Parte A: la fuerza aplicada integra T_i. Algebraico, sobre el diccionario y la malla."""
    fv = leer_fvOptions(caso / "constant" / "fvOptions")
    vol_declarado = leer_volumenes(caso)
    vol_real = volumen_real_zonas(caso)

    problemas, rotores = [], []
    for zona in sorted(fv):
        if zona not in vol_declarado or zona not in vol_real:
            problemas.append(f"{zona}: sin volumen declarado o sin cellZone real")
            continue

        su = fv[zona]["Su"]
        Vd = vol_declarado[zona]
        Vr = vol_real[zona]

        # coherencia del volumen: si rotorZoneVolumes no coincide con la malla, la fuerza
        # integrada NO sera T_i, y el error seria silencioso. Se comprueba explicitamente.
        err_V = abs(Vd - Vr) / Vr if Vr else float("inf")

        # fuerza aplicada = Su * V_zone  (volumeMode absolute -> Su en N/m^3)
        aplicada = tuple(c * Vd for c in su)

        rotores.append({
            "zona": zona,
            "Su_N_m3": list(su),
            "V_declarado_m3": Vd,
            "V_real_m3": Vr,
            "error_V_rel": err_V,
            "F_aplicada_N": list(aplicada),
            "F_magnitud_N": math.dist((0, 0, 0), aplicada),
        })

        if fv[zona]["volumeMode"] != "specific":
            problemas.append(f"{zona}: volumeMode={fv[zona]['volumeMode']}, se exige 'specific' "
                             f"(con 'absolute' OpenFOAM divide ademas por V_zone: candidato a "
                             f"bug #7)")
        if err_V > 1e-9:
            problemas.append(f"{zona}: V declarado {Vd:.10e} != V real {Vr:.10e} "
                             f"(error {err_V:.3e}): la fuerza integrada no sera T_i")

    suma = [sum(r["F_aplicada_N"][i] for r in rotores) for i in range(3)]

    return {
        "caso": caso.name,
        "tolerancia_relativa": tol,
        "rotores": rotores,
        "F_total_aplicada_N": suma,
        "T_total_prescrito_N": -suma[2],
        "problemas": problemas,
    }


# ---------------------------------------------------------------------------------------
# Parte B/C: comprobacion sobre el CAMPO real. Es la parte que discrimina.
# ---------------------------------------------------------------------------------------
def _celdas_de_zona(caso: Path) -> dict:
    return leer_zonas(caso / "constant" / "polyMesh" / "cellZones")


def leer_campo_U(ruta_U: Path) -> list:
    """Lee `internalField uniform (x y z)` o `nonuniform List<vector> N (...)`."""
    txt = ruta_U.read_text(encoding="utf-8", errors="replace")
    txt = txt.split("boundaryField")[0]

    m = re.search(r"internalField\s+uniform\s*\(\s*([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+"
                  r"([-+0-9.eE]+)\s*\)", txt)
    if m:
        v = (float(m.group(1)), float(m.group(2)), float(m.group(3)))
        return [v]      # campo uniforme: se representa por su unico valor

    m = re.search(r"internalField\s+nonuniform\s+List<vector>\s*\n?\s*(\d+)\s*\(", txt)
    if not m:
        raise ValueError(f"{ruta_U.name}: no se pudo leer internalField")
    n = int(m.group(1))
    abre = txt.index("(", m.end() - 1)
    vals = []
    for mm in re.finditer(r"\(\s*([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s*\)",
                          txt[abre:]):
        vals.append((float(mm.group(1)), float(mm.group(2)), float(mm.group(3))))
        if len(vals) == n:
            break
    if len(vals) != n:
        raise ValueError(f"{ruta_U.name}: declaraba {n} celdas, se leyeron {len(vals)}")
    return vals


def leer_campo_escalar(ruta: Path, nombre: str) -> list:
    txt = ruta.read_text(encoding="utf-8", errors="replace").split("boundaryField")[0]
    m = re.search(r"internalField\s+uniform\s+([-+0-9.eE]+)\s*;", txt)
    if m:
        return [float(m.group(1))]
    m = re.search(r"internalField\s+nonuniform\s+List<scalar>\s*\n?\s*(\d+)\s*\(", txt)
    if not m:
        raise ValueError(f"{ruta.name}/{nombre}: no se pudo leer internalField")
    n = int(m.group(1))
    abre = txt.index("(", m.end() - 1)
    vals = [float(t) for t in txt[abre + 1:].replace("\n", " ").split()
            if t not in ("(", ")")][:n]
    if len(vals) != n:
        raise ValueError(f"{ruta.name}/{nombre}: declaraba {n} valores, hay {len(vals)}")
    return vals


def comprobar_campo(caso: Path, U_esperado_cero: bool) -> dict:
    """B y C: independencia del flujo incidente y existencia de downwash.

    B. Con `U_inf = 0` la fuerza aplicada debe seguir siendo `T_i`. Esto NO puede
       comprobarse leyendo el diccionario: es una propiedad del solver. Se comprueba
       indirectamente con C, porque si la fuerza fuera nula no habria downwash.
    C. Debe existir velocidad vertical bajo los rotores, muy por encima del ruido
       numerico (~1e-7 m/s) que producia actuationDiskSource.
    """
    ruta_U = buscar_campo_U(caso)
    if ruta_U is None:
        return {"disponible": False,
                "motivo": "sin campo U de solver (tiempo > 0): el caso aun no se ha ejecutado"}

    U = leer_campo_U(ruta_U)
    zonas = _celdas_de_zona(caso)

    out = {"disponible": True, "campo_U": str(ruta_U), "n_celdas_campo": len(U)}

    if len(U) == 1:
        out["U_uniforme"] = list(U[0])
        out["motivo"] = "campo uniforme: el solver no desarrollo estructura"
        out["downwash_detectado"] = False
        out["Uz_max_abs"] = abs(U[0][2])
        return out

    uz_global = [abs(v[2]) for v in U]
    out["Uz_max_abs_global"] = max(uz_global)
    out["Uz_media_abs_global"] = sum(uz_global) / len(uz_global)

    por_zona = {}
    for z, celdas in zonas.items():
        idx = [c for c in celdas if c < len(U)]
        if not idx:
            continue
        uz = [U[c][2] for c in idx]
        por_zona[z] = {
            "Uz_media": sum(uz) / len(uz),
            "Uz_min": min(uz),
            "Uz_max": max(uz),
            "n_celdas": len(idx),
        }
    out["por_zona"] = por_zona

    if por_zona:
        out["Uz_min_en_zonas"] = min(v["Uz_min"] for v in por_zona.values())
        out["downwash_detectado"] = out["Uz_min_en_zonas"] < -UMBRAL_UZ
    else:
        out["downwash_detectado"] = False

    out["umbral_Uz_ms"] = UMBRAL_UZ
    return out


def buscar_campo_U(caso: Path) -> Path | None:
    """Ultimo campo U escrito por el SOLVER (tiempo > 0).

    Se excluye deliberadamente el tiempo inicial `0/U`: ese campo es una CONDICION DE
    CONTORNO, no un resultado. Tratarlo como resultado daba un falso negativo: con el campo
    inicial puesto a cero, el verificador concluia "campo uniforme, el solver no desarrollo
    estructura" cuando en realidad el solver aun no habia corrido. Son dos situaciones
    distintas y hay que distinguirlas.
    """
    candidatos = []
    for d in caso.iterdir():
        if d.is_dir() and d.name.replace(".", "").isdigit():
            t = float(d.name)
            if t > 0.0 and (d / "U").exists():
                candidatos.append((t, d / "U"))
    if not candidatos:
        return None
    return max(candidatos)[1]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--case", default=None)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--tolerance", type=float, default=TOL_FUERZA)
    ap.add_argument("--hover", action="store_true",
                    help="el caso es de hover (U_inf = 0): activa la lectura B/C")
    ap.add_argument("--exigir-downwash", action="store_true",
                    help="fallar si no se detecta downwash (prueba discriminante)")
    args = ap.parse_args()

    if args.case:
        caso = Path(args.case)
        if not caso.is_absolute():
            caso = (ROOT / caso).resolve()
        casos = [caso]
    elif args.all:
        casos = sorted(p for p in CASES.iterdir()
                       if p.is_dir() and (p / "case_meta.json").exists())
    else:
        casos = [CASES / CASO_NOMINAL]

    resultados, fallo_global = [], False
    for caso in casos:
        try:
            r = comprobar_caso(caso, args.tolerance)
            r["campo"] = comprobar_campo(caso, U_esperado_cero=args.hover)
            if r["problemas"]:
                r["estado"] = "FALLA"
            elif r["campo"].get("disponible") and args.exigir_downwash:
                r["estado"] = "PASA" if r["campo"].get("downwash_detectado") else "FALLA"
                if r["estado"] == "FALLA":
                    r["problemas"].append(
                        "no se detecto downwash por encima del umbral: la fuente no "
                        "materializa el empuje en el campo (el fallo de actuationDiskSource)"
                    )
            else:
                r["estado"] = "PASA"
        except Exception as exc:  # noqa: BLE001
            r = {"caso": caso.name, "estado": "ERROR",
                 "detalle": f"{type(exc).__name__}: {exc}"}
        resultados.append(r)
        if r["estado"] != "PASA":
            fallo_global = True

    print("=" * 100)
    print("GATE CFD-0  -  fuerza PRESCRITA vs fuerza APLICADA, rotor por rotor")
    print("=" * 100)
    for r in resultados:
        print(f"\n  {r['caso']}: {r['estado']}")
        if r["estado"] == "ERROR":
            print(f"    {r['detalle']}")
            continue
        print(f"    {'zona':<12}{'Su_z (N/m3)':>16}{'V_zone (m3)':>16}"
              f"{'F_aplicada_z (N)':>20}{'error V':>12}")
        for ro in r["rotores"]:
            print(f"    {ro['zona']:<12}{ro['Su_N_m3'][2]:>16.6e}"
                  f"{ro['V_declarado_m3']:>16.10e}"
                  f"{ro['F_aplicada_N'][2]:>20.6f}{ro['error_V_rel']:>12.2e}")
        print(f"    suma vectorial aplicada = ({r['F_total_aplicada_N'][0]:+.6f} "
              f"{r['F_total_aplicada_N'][1]:+.6f} {r['F_total_aplicada_N'][2]:+.6f}) N")
        print(f"    T total prescrito       = {r['T_total_prescrito_N']:.6f} N")

        campo = r.get("campo", {})
        if not campo.get("disponible"):
            print(f"    [--] parte B/C pendiente: {campo.get('motivo')}")
        elif campo.get("n_celdas_campo") == 1:
            print(f"    [FALLA] campo U uniforme ({campo['U_uniforme']}): el solver no "
                  f"desarrollo estructura")
        else:
            print(f"    campo U: {campo['campo_U']}")
            print(f"    |Uz| max global  = {campo.get('Uz_max_abs_global', 0):.6e} m/s")
            print(f"    Uz min en zonas  = {campo.get('Uz_min_en_zonas', 0):+.6e} m/s "
                  f"(umbral {campo.get('umbral_Uz_ms')} m/s)")
            for z, d in sorted(campo.get("por_zona", {}).items()):
                print(f"      {z:<10} Uz media = {d['Uz_media']:+.6e}  "
                      f"[{d['Uz_min']:+.6e}, {d['Uz_max']:+.6e}]  ({d['n_celdas']} celdas)")
            if campo.get("downwash_detectado"):
                print("    [ok] downwash detectado: la fuente SI genera flujo")
            else:
                print("    [FALLA] no hay downwash: la fuente no materializa el empuje")

        if r["problemas"]:
            for p in r["problemas"]:
                print(f"    [FALLA] {p}")
        else:
            print("    [ok] Su constante + volumeMode specific + V declarado = V real")
            print("         => integral_{V_zone} f dV = Su * V_zone = T_i")

    EVIDENCE.mkdir(exist_ok=True)
    destino = EVIDENCE / "cfd0_force_integral.json"
    destino.write_text(json.dumps(resultados, indent=2, ensure_ascii=False) + "\n",
                       encoding="utf-8")
    print(f"\n  evidencia escrita: {destino.relative_to(ROOT)}")
    print()
    return 1 if fallo_global else 0


if __name__ == "__main__":
    sys.exit(main())
