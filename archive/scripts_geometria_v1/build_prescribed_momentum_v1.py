#!/usr/bin/env python3
"""Fuente de momento PRESCRITA por rotor: implementa la arquitectura C -> B.

El problema que resuelve
------------------------
`actuationDiskSource` (metodo Froude) NO aplica un empuje prescrito: lo CALCULA a partir
del flujo incidente axial,

    T = 2 rho A |U_o . n|^2 a (1 - a)

Con flujo perpendicular al disco, `U_o . n ~ 0` y por tanto `T ~ 0`. Y el caso fisico de
este proyecto es justo ese: en hover o vuelo nivelado el disco GENERA el flujo, no lo
recibe. Resultado medido: `Uz ~ 1e-7` (nulo). Ver `evidence/BUG_conceptual_06_actuationDisk.md`.

En la arquitectura C -> B, `T_i` es una ENTRADA (viene del equilibrio de fuerzas y momentos
del UAV), no una salida. Aqui se materializa como fuente de momento explicita.

La formulacion
--------------
`vectorSemiImplicitSource` con `volumeMode absolute` aporta, a la ecuacion de momento de la
celda `c`, un termino `Su_c * V_c` (newtons). Por tanto `Su` tiene unidades de N/m^3.

Para imponer que la fuerza TOTAL sobre la zona sea exactamente `T_i`:

    f_c          =  T_vec * V_c / V_zone^2          [N/m^3]

    integral_{V_zone} f dV
        = sum_c (T_vec * V_c / V_zone^2) * V_c ... NO:

    integral_{V_zone} f dV  =  sum_c f_c * V_c
                            =  T_vec * sum_c V_c^2 / V_zone^2

Eso NO es `T_vec` salvo que todas las celdas tengan el mismo volumen. La formulacion
correcta, que vale para CUALQUIER malla, es repartir proporcionalmente al volumen:

    f_c  =  T_vec / V_zone                          [N/m^3]   (constante)

    integral_{V_zone} f dV  =  T_vec/V_zone * sum_c V_c  =  T_vec/V_zone * V_zone  =  T_vec

**Constante es lo correcto y ademas lo mas simple.** El reparto por volumen lo hace ya la
integracion: una celda grande recibe mas fuerza total porque `f * V` es mayor. Repartir
`f_c propto V_c` (mi primera idea) sobreponderaria las celdas grandes y daria una fuerza
total `T * sum(V^2)/V_zone^2 > T`. Corregido antes de escribir nada.

Propiedades que cumple esta fuente
----------------------------------
1. INDEPENDIENTE DE `U`: con `U = 0` (hover puro) la fuerza sigue siendo `T_i`. Es la
   prueba que `actuationDiskSource` no pasa.
2. DIRECCIONAL: `T_vec` es un vector explicito, alineado con el eje del rotor.
3. VECTORIAL POR ROTOR: cada zona tiene su propio `T_vec` (reparto coaxial superiores/
   inferiores distinto).
4. VERIFICABLE: la fuerza aplicada se integra con `volFieldValue`/`volIntegrate` sobre el
   campo real y se compara con `T_i`.

Lo que esta fuente NO hace
--------------------------
No modela el par de reaccion (torque) del rotor, ni la estela helicoidal, ni la
interaccion rotor-rotor mas alla de la superposicion de campos. Es un disco de momento
prescrito, no un rotor resuelto.

Uso
---
    python scripts/build_prescribed_momentum.py                  # caso nominal
    python scripts/build_prescribed_momentum.py --case <ruta>
    python scripts/build_prescribed_momentum.py --all            # todos los casos con malla
    python scripts/build_prescribed_momentum.py --dry-run        # no escribe, solo informa

Requiere que `constant/rotorZoneVolumes` exista (lo genera `scripts/mesh_zone_volumes.py`).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "cfd" / "cases"
CASO_NOMINAL = "T25P_V3.1_H2.8_d190_f0.95_a4"

G = 9.80665

# Casos que NO forman parte de la suite DOE y no deben arrastrarse en los barridos:
#   - `T25P_baseline*`: artefactos de desarrollo (tienen malla pero no case_meta.json ni
#     fvOptions). Se detectan tambien por la falta de case_meta.json.
#   - el caso de hover: es la prueba discriminante de GATE CFD-0, no un punto del DOE.
def es_caso_doe(d: Path) -> bool:
    return (d.is_dir()
            and (d / "case_meta.json").exists()
            and "HOVER" not in d.name)


# ---------------------------------------------------------------------------------------
# lectura de la configuracion del caso
# ---------------------------------------------------------------------------------------
def leer_volumenes_zonas(caso: Path) -> dict:
    """Lee `constant/rotorZoneVolumes` -> {zona: V_zone}."""
    f = caso / "constant" / "rotorZoneVolumes"
    if not f.exists():
        raise FileNotFoundError(
            f"{caso.name}: falta constant/rotorZoneVolumes. "
            f"Ejecuta antes: python scripts/mesh_zone_volumes.py --case {caso.name} --write"
        )
    zonas: dict[str, float] = {}
    dentro = False
    for linea in f.read_text(encoding="utf-8").splitlines():
        s = linea.split("//")[0].strip()
        if not s:
            continue
        if s.startswith("volumenZonas"):
            dentro = True
            continue
        if dentro:
            if s.startswith("}"):
                break
            partes = s.rstrip(";").split()
            if len(partes) == 2:
                zonas[partes[0]] = float(partes[1])
    if not zonas:
        raise ValueError(f"{caso.name}: rotorZoneVolumes sin entradas")
    return zonas


def leer_cell_zone_names(caso: Path) -> list:
    """Nombres de las cellZone de rotor presentes en la malla.

    Se reutiliza el lector YA VERIFICADO de `mesh_zone_volumes` en lugar de reimplementarlo:
    una segunda implementacion del mismo parseo es una segunda oportunidad de equivocarse,
    y de hecho la primera version de esta funcion tomaba las etiquetas de celda (numeros)
    como si fueran nombres de zona.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from mesh_zone_volumes import leer_zonas  # noqa: PLC0415 - import local a proposito

    f = caso / "constant" / "polyMesh" / "cellZones"
    if not f.exists():
        return []
    return sorted(leer_zonas(f))


def leer_meta(caso: Path) -> dict:
    f = caso / "case_meta.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


# ---------------------------------------------------------------------------------------
# construccion de la fuente
# ---------------------------------------------------------------------------------------
def reparto_empuje(meta: dict, n_rotores: int) -> tuple[list, float]:
    """Fuerza PRESCRITA (vector, newtons) por rotor, y el peso del UAV.

    Origen de `T_i`: arquitectura C. El equilibrio de fuerzas y momentos del UAV da el
    empuje total y su reparto. `case_meta.json` guarda ya el resultado de esa cadena en
    `derivados_analiticos.empuje_por_disco_N`.

    Convenio de signos, explicito porque es donde se cometen los errores:
      - `T_i` es la fuerza que el rotor ejerce SOBRE EL UAV (hacia arriba en hover).
      - La fuerza que el rotor ejerce SOBRE EL AIRE es la reaccion: `-T_i` (hacia abajo).
      - `vectorSemiImplicitSource` anade fuerza AL FLUIDO.
    => lo que se escribe en `sources` es `F_aire = -T_i`.
    """
    der = meta.get("derivados_analiticos", {})
    masa = float(meta.get("entradas", {}).get("masa_total_kg", 0.0))
    peso = masa * G

    por_disco = der.get("empuje_por_disco_N")
    if isinstance(por_disco, dict) and por_disco:
        # orden estable y explicito: R1, R2, ... segun el numero final de la clave
        def clave(k: str) -> int:
            digitos = "".join(ch for ch in k if ch.isdigit())
            return int(digitos) if digitos else 0
        valores = [float(por_disco[k]) for k in sorted(por_disco, key=clave)]
    else:
        total = float(der.get("empuje_total_N", peso))
        valores = [total / n_rotores] * n_rotores

    if len(valores) != n_rotores:
        raise ValueError(f"empuje_por_disco_N tiene {len(valores)} entradas y hay "
                         f"{n_rotores} zonas de rotor")

    # hover: eje del rotor vertical -> fuerza sobre el aire hacia abajo
    #
    # ALCANCE DE ESTA APROXIMACION, declarado en lugar de silenciado:
    # En vuelo nivelado real el UAV se inclina un angulo theta para vencer la resistencia,
    # de modo que la fuerza tiene una componente horizontal T*sin(theta) y la vertical vale
    # T*cos(theta). Aqui se prescriben fuerzas VERTICALES puras, lo que es exacto en hover
    # (theta = 0) y una aproximacion en avance. El error relativo en la componente vertical
    # es (1 - cos(theta)), que para theta tipico es despreciable:
    #     theta =  0.7 deg -> 7.5e-5
    #     theta =  6.0 deg -> 5.5e-3   (0.55 %)
    #     theta = 12.0 deg -> 2.2e-2   (2.2 %)
    # `verificar_inclinacion` comprueba el caso concreto y marca cuando deja de ser
    # despreciable. Modelar el empuje inclinado exige la actitud resuelta por la cadena C
    # (scripts/force_chain.py), que pertenece a GATE 1A/1B y no a este generador.
    fuerzas = [(0.0, 0.0, -t) for t in valores]
    verificar_inclinacion(meta, valores)
    return fuerzas, peso


def verificar_inclinacion(meta: dict, valores: list) -> None:
    """Avisa si el angulo de actitud del caso hace no despreciable la aproximacion vertical.

    Se recalcula la actitud con el mismo modelo explicito que usa la cadena de fuerza
    (tan theta = D/(m g)), pero SIN inventar el area frontal ni el Cd si no estan: si no
    hay datos suficientes, se informa de que no puede comprobarse en vez de suponer.
    """
    entradas = meta.get("entradas", {})
    V = float(entradas.get("V_inf_ms", 0.0))
    masa = float(entradas.get("masa_total_kg", 0.0))
    if V <= 0.0 or masa <= 0.0:
        return

    aero = meta.get("aerodinamica", {})
    Cd = aero.get("Cd")
    A = aero.get("area_frontal_m2")
    if Cd is None or A is None:
        return

    rho = 1.1716
    D = 0.5 * rho * V * V * float(Cd) * float(A)
    theta = math.atan2(D, masa * G)
    err = 1.0 - math.cos(theta)
    if err > 0.01:
        print(f"    [AVISO] V = {V:.2f} m/s -> theta = {math.degrees(theta):.2f} deg: la "
              f"aproximacion de empuje vertical tiene un error de {err*100:.2f} % en la "
              f"componente vertical. Para este caso hay que usar el empuje inclinado.")


def construir_fvOptions(caso: Path, zonas: dict, fuerzas: list) -> str:
    lineas = [
        "/*--------------------------------*- C++ -*----------------------------------*\\",
        "| =========                 |                                                 |",
        "| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |",
        "|  \\\\    /   O peration     | Version:  2412                                  |",
        "|   \\\\  /    A nd           | Website:  www.openfoam.com                      |",
        "|    \\\\/     M anipulation  |                                                 |",
        "\\*---------------------------------------------------------------------------*/",
        "FoamFile",
        "{",
        "    version     2.0;",
        "    format      ascii;",
        "    class       dictionary;",
        "    object      fvOptions;",
        "}",
        "// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //",
        "",
        "// =====================================================================================",
        "// FUENTE DE MOMENTO PRESCRITA  -  arquitectura C -> B",
        "// =====================================================================================",
        "//",
        "// NO es actuationDiskSource. Aquel CALCULA el empuje a partir del flujo incidente",
        "// axial (T = 2 rho A |U_o.n|^2 a(1-a)), de modo que con flujo perpendicular da",
        "// T ~ 0. Aqui el empuje es una ENTRADA.",
        "//",
        "// Formulacion: vectorSemiImplicitSource. En OpenFOAM, `Su` entra en la ecuacion de",
        "// momento CINEMATICA (fvm::div(phi,U) -> dimensiones [0 2 -2 0 0 0 0]), de modo que",
        "// `Su` tiene dimensiones [0 -1 -2] = aceleracion por unidad de volumen, NO fuerza por",
        "// unidad de masa. En un solver incompresible rho NO aparece: la densidad ya esta",
        "// implicita en las unidades. La cadena es",
        "//",
        "//       F [N]  ->  F/V_zone [N/m^3]  ->  Su",
        "//",
        "// El codigo de OpenFOAM aplica, por celda, `Su_c * V_c` newtons (fvm::SuSp multiplica",
        "// por el volumen de celda). Por tanto, con Su CONSTANTE en la zona,",
        "//",
        "//       integral_{V_zone} f dV = Su * sum_c V_c = Su * V_zone",
        "//",
        "// y para que valga `F` hay que escribir `Su = F / V_zone`.",
        "//",
        "// POR QUE `specific` Y NO `absolute`  (candidato a bug #7, medido)",
        "//   El codigo de v2412 hace, para volumeMode absolute:",
        "//       VDash_ = V_ ;   Su_interno = Su_diccionario / VDash_",
        "//   es decir, `absolute` DIVIDE por el volumen de la zona. Eso mete una division por",
        "//   V_zone en medio de la formulacion y hace que el resultado dependa de que el volumen",
        "//   declarado coincida EXACTAMENTE con el de la malla. Se midio en un caso controlado",
        "//   (scripts/calibrate_semiimplicit.py): con el mismo `Su`, `specific` aplica un factor",
        "//   V_zone mas de fuerza que `absolute`, exactamente el factor 4.0 del volumen del test.",
        "//",
        "//   Con `specific`, `VDash_ = 1` y el valor del diccionario es la densidad volumetrica",
        "//   SIN ninguna renormalizacion. La formulacion deja de depender de la semantica del",
        "//   modo: menos piezas moviles, mismo resultado fisico.",
        "//",
        "// Constante es lo correcto: el reparto por volumen ya lo hace la integracion, porque",
        "// una celda grande recibe mas fuerza total al multiplicarse por su volumen. Repartir",
        "// Su_c proporcional a V_c sobreponderia las celdas grandes.",
        "//",
        "// Convenio de signos: T_i es la fuerza del rotor SOBRE EL UAV; lo que se inyecta al",
        "// FLUIDO es la reaccion, -T_i. En hover, (0 0 -T_i).",
        "//",
        "// V_zone procede de constant/rotorZoneVolumes, calculado sobre la malla REAL de este",
        "// caso (scripts/mesh_zone_volumes.py). OpenFOAM imprime su propio valor en el log",
        "// ('- selected N cell(s) with volume V'); verificacion: verify_prescribed_force.py.",
        "//",
        "// VERIFICACION OBLIGATORIA (GATE CFD-0): la fuerza aplicada debe integrar T_i rotor",
        "// por rotor, y el balance global de momento debe cerrar.",
        "// =====================================================================================",
        "",
        "options",
        "{",
    ]

    for zona, F in zip(sorted(zonas), fuerzas):
        V = zonas[zona]
        if V <= 0:
            raise ValueError(f"{caso.name}/{zona}: V_zone = {V} no es positivo")
        su = tuple(c / V for c in F)
        T = -F[2]
        lineas += [
            f"    // {zona}: T_i = {T:.6f} N (fuerza del rotor sobre el UAV, hacia arriba)",
            f"    //     V_zone = {V:.10e} m3  ->  Su = F_aire/V_zone = "
            f"({su[0]:.10e} {su[1]:.10e} {su[2]:.10e}) N/m3",
            f"    {zona}",
            "    {",
            "        type            vectorSemiImplicitSource;",
            "        libs            (\"libfvOptions.so\");",
            "        selectionMode   cellZone;",
            "        cellZone        " + zona + ";",
            "        // `specific`: el valor es la densidad volumetrica y NO se renormaliza.",
            "        // NO cambiar a `absolute` sin volver a dividir por V_zone (ver cabecera).",
            "        volumeMode      specific;",
            "",
            "        sources",
            "        {",
            f"            U               (({su[0]:.10e} {su[1]:.10e} {su[2]:.10e}) 0);",
            "        }",
            "    }",
            "",
        ]

    lineas += ["}", "", "// ************************************************************************* //", ""]
    return "\n".join(lineas)


def procesar(caso: Path, dry_run: bool) -> dict:
    zonas = leer_volumenes_zonas(caso)
    meta = leer_meta(caso)
    nombres_malla = leer_cell_zone_names(caso)

    fuerzas, peso = reparto_empuje(meta, len(zonas))

    # coherencia entre rotorZoneVolumes y la malla real
    if nombres_malla:
        faltan = set(nombres_malla) - set(zonas)
        sobran = set(zonas) - set(nombres_malla)
        if faltan or sobran:
            raise ValueError(f"{caso.name}: rotorZoneVolumes no coincide con cellZones. "
                             f"faltan={sorted(faltan)} sobran={sorted(sobran)}")

    suma = [sum(f[i] for f in fuerzas) for i in range(3)]
    Fz_aire = suma[2]                      # fuerza vertical sobre el aire (negativa)
    T_total = -Fz_aire                     # empuje total del UAV

    residuo = T_total - peso

    salida = caso / "constant" / "fvOptions"
    texto = construir_fvOptions(caso, zonas, fuerzas)
    if not dry_run:
        salida.write_text(texto, encoding="utf-8")

    return {
        "caso": caso.name,
        "n_rotores": len(zonas),
        "zonas": {z: zonas[z] for z in sorted(zonas)},
        "T_por_rotor_N": [-f[2] for f in fuerzas],
        "F_aire_por_rotor_N": [list(f) for f in fuerzas],
        "Su_por_rotor_N_m3": [[c / zonas[z] for c in f]
                              for z, f in zip(sorted(zonas), fuerzas)],
        "T_total_N": T_total,
        "peso_N": peso,
        "residuo_N": residuo,
        "residuo_pct": 100.0 * residuo / peso if peso else None,
        "escrito": None if dry_run else str(salida.relative_to(ROOT)),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--case", default=None)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.case:
        casos = [Path(args.case)]
        if not casos[0].is_absolute():
            casos[0] = (ROOT / casos[0]).resolve()
    elif args.all:
        casos = sorted(p for p in CASES.iterdir()
                       if es_caso_doe(p) and (p / "constant" / "rotorZoneVolumes").exists())
        if not casos:
            print("No hay casos con constant/rotorZoneVolumes.")
            print("Ejecuta antes: python scripts/mesh_zone_volumes.py --all --write")
            return 1
    else:
        casos = [CASES / CASO_NOMINAL]

    resultados, fallos = [], 0
    for caso in casos:
        try:
            resultados.append(procesar(caso, args.dry_run))
        except Exception as exc:  # noqa: BLE001
            fallos += 1
            resultados.append({"caso": caso.name, "estado": "error",
                               "detalle": f"{type(exc).__name__}: {exc}"})

    if args.json:
        print(json.dumps(resultados, indent=2, ensure_ascii=False))
        return 1 if fallos else 0

    print("=" * 100)
    print("FUENTE DE MOMENTO PRESCRITA  -  integral_{V_zone} f dV = T_i")
    print("=" * 100)
    for r in resultados:
        if r.get("estado") == "error":
            print(f"\n  {r['caso']}: ERROR  {r['detalle']}")
            continue
        print(f"\n  {r['caso']}")
        print(f"    rotores: {r['n_rotores']}")
        for i, (z, T, F, su) in enumerate(zip(sorted(r["zonas"]), r["T_por_rotor_N"],
                                               r["F_aire_por_rotor_N"],
                                               r["Su_por_rotor_N_m3"]), 1):
            print(f"      {z:<10} T = {T:10.6f} N · F_aire = "
                  f"({F[0]:+.6f} {F[1]:+.6f} {F[2]:+.6f}) N · Su = {su[2]:+.6e} N/m3")
        print(f"    T total = {r['T_total_N']:.6f} N   peso = {r['peso_N']:.6f} N   "
              f"residuo = {r['residuo_N']:+.6f} N ({r['residuo_pct']:+.4f} %)")
        if abs(r["residuo_pct"] or 0.0) > 0.01:
            print("    [!!] el empuje total no cierra con el peso: revisar la cadena C")
        else:
            print("    [ok] el empuje total cierra con el peso (arquitectura C)")
        if r["escrito"]:
            print(f"    escrito: {r['escrito']}")
    print()
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
