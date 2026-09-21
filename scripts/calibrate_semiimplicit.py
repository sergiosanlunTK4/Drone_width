#!/usr/bin/env python3
"""BUG #7 (candidato) — calibracion de la normalizacion de `vectorSemiImplicitSource`.

LA OBJECION
-----------
En v2412 el codigo hace, para `volumeMode absolute`:

    VDash_ = V_;                                   // V_ = volumen de las celdas seleccionadas
    Su_interno = Su_diccionario / VDash_           // divide por el volumen

Entonces, si `Su_interno` se aplicase como densidad de fuerza uniforme, la fuerza total seria

    F = Su_interno * V_zone = (Su_diccionario / V_zone) * V_zone = Su_diccionario

es decir: **el valor del diccionario SERIA la fuerza total**. Y mi generador escribe
`Su = F/V_zone`, con lo que la fuerza aplicada seria `F/V_zone` = 127.27/0.3134 = 406 N por
rotor en vez de 127.27 N: **un factor 1/V_zone = 3.19 de mas**.

Eso es exactamente lo que hay que medir, no razonar.

EL TEST: ACELERACION INICIAL
----------------------------
Primer intento, descartado, y conviene registrar por que. Se probo un conducto cerrado con
fuerza uniforme en todo el dominio esperando medir la presion en las paredes. **No funciona
por construccion**: en un dominio cerrado la fuerza se equilibra contra un gradiente de
presion, y ese equilibrio exige que la fuerza este AUSENTE en alguna parte del circuito
cerrado. Con `f` uniforme en TODO el dominio no existe tal circuito, la presion queda
constante y el fluido acelera indefinidamente; los residuos bajan a ~1e-16 porque el campo
es trivial (presion uniforme), no porque haya convergencia. Un test mal planteado tambien
converge.

Test correcto, sin presiones: **la aceleracion en el primer instante**. Partiendo de fluido
en reposo y con presion uniforme, la ecuacion de momento es exactamente

    dU/dt = F_aplicada / (rho * V)

porque no hay conveccion, no hay gradiente de presion y no hay viscoso (campo uniforme). Por
tanto, midiendo `U(T)` tras un tiempo T se obtiene la fuerza aplicada SIN interpretar nada:

    F_aplicada = rho * V * U(T) / T

Se usa un valor de `su` PEQUENO para que la aceleracion sea moderada y no haya efectos de
borde ni no linealidades: el test mide una conversion, no simula un flujo.

Se corren varias formulaciones y se comparan. La que devuelva `F_aplicada = F_prescrita`
queda determinada por la medida, no por la lectura del codigo.

Uso
---
    python3 scripts/foam_run.py python3 scripts/calibrate_semiimplicit.py
"""

from __future__ import annotations

import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "cfd" / "calibration"

L, S, F_TOTAL = 4.0, 1.0, 0.04        # 0.04 N sobre 4 m3 -> a = 0.01 m/s2 con rho = 1
F_VOL = F_TOTAL / (S * L)             # 0.01 N/m3
T_FIN = 1.0                           # un solo paso de tiempo de 1 s

HEADER = """/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  2412                                  |
|   \\\\  /    A nd           | Website:  www.openfoam.com                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       {cls};
    object      {obj};
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //
"""


def escribir_caso(destino: Path, su: float, volume_mode: str) -> None:
    if destino.exists():
        shutil.rmtree(destino)
    (destino / "system").mkdir(parents=True)
    (destino / "constant").mkdir(parents=True)
    (destino / "0").mkdir(parents=True)

    n = (20, 1, 1)
    (destino / "system" / "blockMeshDict").write_text(
        HEADER.format(cls="dictionary", obj="blockMeshDict") + f"""
scale 1;
vertices
(
    (0 0 0) ({L} 0 0) ({L} 1 0) (0 1 0)
    (0 0 1) ({L} 0 1) ({L} 1 1) (0 1 1)
);
blocks ( hex (0 1 2 3 4 5 6 7) ({n[0]} {n[1]} {n[2]}) simpleGrading (1 1 1) );
edges ();
boundary
(
    xmin {{ type patch; faces ((0 3 2 1)); }}
    xmax {{ type patch; faces ((4 5 6 7)); }}
    walls {{ type patch; faces ((0 1 5 4) (3 7 6 2) (0 4 7 3) (1 2 6 5)); }}
);
mergePatchPairs ();
""", encoding="utf-8")

    (destino / "system" / "controlDict").write_text(
        HEADER.format(cls="dictionary", obj="controlDict") + """
// ** pimpleFoam, NO simpleFoam. **
// Primer intento con simpleFoam, descartado: con `consistent yes` el solver resuelve la
// ecuacion ESTACIONARIA, no acumula dU/dt, de modo que la "aceleracion" que se medía no era
// F/(rho V) sino la respuesta amortiguada del solver. El unico solver donde
//     dU/dt = F_aplicada/(rho V)
// es literalmente la ecuacion es el TRANSITORIO.
application     pimpleFoam;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         1.0;
deltaT          0.05;
writeControl    timeStep;
writeInterval   1;
purgeWrite      0;
writeFormat     ascii;
writePrecision  12;
runTimeModifiable true;
""", encoding="utf-8")

    # Los esquemas se copian LITERALMENTE de los que ya funcionan en los 128 casos
    # (`cfd/cases/*/system/fvSchemes`). Escribirlos de nuevo "a mano" fallo dos veces:
    # con `default none` OpenFOAM aborta en cuanto aparece un termino no listado, y el
    # termino que aparece en v2412 es `div((nuEff*dev2(T(grad(U)))))`.
    (destino / "system" / "fvSchemes").write_text(
        HEADER.format(cls="dictionary", obj="fvSchemes") + """
// `ddtSchemes` pasa a Euler: el test es TRANSITORIO y mide dU/dt. Con `steadyState` no
// existiria el termino temporal y la medida no tendria sentido.
ddtSchemes      { default Euler; }
gradSchemes     { default Gauss linear; limited cellLimited Gauss linear 1; }
divSchemes
{
    default                         none;
    div(phi,U)                      Gauss linearUpwind grad(U);
    div(phi,k)                      Gauss upwind;
    div(phi,omega)                  Gauss upwind;
    div((nuEff*dev2(T(grad(U)))))   Gauss linear;
}
laplacianSchemes { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes   { default corrected; }
wallDist        { method meshWave; }
""", encoding="utf-8")

    (destino / "system" / "fvSolution").write_text(
        HEADER.format(cls="dictionary", obj="fvSolution") + """
solvers
{
    p       { solver PCG; preconditioner DIC; tolerance 1e-14; relTol 0; }
    pFinal  { $p; relTol 0; }
    U       { solver smoothSolver; smoother symGaussSeidel; tolerance 1e-14; relTol 0; }
    UFinal  { $U; relTol 0; }
}
PIMPLE
{
    nOuterCorrectors    1;
    nCorrectors         2;
    nNonOrthogonalCorrectors 0;
    pRefPoint           (2 0.5 0.5);
    pRefValue           0;
}
// SIN relajacion: la medida es la aceleracion exacta dU/dt = F/(rho V).
relaxationFactors
{
    equations { ".*" 1; }
    fields    { ".*" 1; }
}
""", encoding="utf-8")

    (destino / "constant" / "transportProperties").write_text(
        HEADER.format(cls="dictionary", obj="transportProperties") + """
// simpleFoam (v2412) exige `transportModel` de forma explicita; sin el aborta con
// "Entry 'transportModel' not found". Es un requisito del solver, no una eleccion fisica.
transportModel  Newtonian;

// nu = 1, rho = 1: el unico objetivo es medir la conversion fuerza -> fuente.
nu              [0 2 -1 0 0 0 0] 1.0;
""", encoding="utf-8")

    (destino / "constant" / "turbulenceProperties").write_text(
        HEADER.format(cls="dictionary", obj="turbulenceProperties") + """
simulationType  laminar;
""", encoding="utf-8")

    (destino / "0" / "U").write_text(
        HEADER.format(cls="volVectorField", obj="U") + """
dimensions      [0 1 -1 0 0 0 0];
internalField   uniform (0 0 0);
boundaryField
{
    xmin  { type zeroGradient; }
    xmax  { type zeroGradient; }
    walls { type slip; }
}
""", encoding="utf-8")

    (destino / "0" / "p").write_text(
        HEADER.format(cls="volScalarField", obj="p") + """
dimensions      [0 2 -2 0 0 0 0];
internalField   uniform 0;
boundaryField
{
    xmin  { type zeroGradient; }
    xmax  { type zeroGradient; }
    walls { type zeroGradient; }
}
""", encoding="utf-8")

    # LA FUENTE: `su` es lo que se escribe en el diccionario. Ni mas ni menos.
    (destino / "constant" / "fvOptions").write_text(
        HEADER.format(cls="dictionary", obj="fvOptions") + f"""
// Calibracion: fuerza volumetrica uniforme en TODO el dominio.
// F_total prescrita = {F_TOTAL} N  (f = {F_VOL} N/m3 sobre V = {S*L} m3)
// Lo escrito en `sources` es `su` = {su:.10e}
// volumeMode = {volume_mode}
//
// Si la normalizacion fuese "el diccionario ES la fuerza total", la fuerza medida seria
// `su` cualquiera que sea el modo. Si fuese "densidad volumetrica", seria `su * V`.
// La medida decide.
calibracion
{{
    type            vectorSemiImplicitSource;
    libs            ("libfvOptions.so");
    selectionMode   all;
    volumeMode      {volume_mode};
    sources
    {{
        U           (({su:.10e} 0 0) 0);
    }}
}}
""", encoding="utf-8")


def leer_U_media(directorio: Path, n_celdas: int) -> float:
    """Media de Ux sobre TODO el dominio en un tiempo escrito."""
    f = directorio / "U"
    if not f.exists():
        return float("nan")
    txt = f.read_text(encoding="utf-8", errors="replace").split("boundaryField")[0]
    m = re.search(r"internalField\s+uniform\s*\(\s*([-+0-9.eE]+)", txt)
    if m:
        return float(m.group(1))
    m = re.search(r"internalField\s+nonuniform\s+List<vector>\s*\n?\s*(\d+)\s*\(", txt)
    if not m:
        return float("nan")
    i = txt.index("(", m.end() - 1)
    vals = [float(mm.group(1)) for mm in
            re.finditer(r"\(\s*([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s*\)", txt[i:])]
    return sum(vals) / len(vals) if vals else float("nan")


def main() -> int:
    print("=" * 100)
    print("CALIBRACION de vectorSemiImplicitSource  -  candidato a BUG #7")
    print("=" * 100)
    print(f"  dominio: {L} x 1 x 1 m  ->  V = {S*L} m3   (malla 20x1x1)")
    print(f"  fuerza PRESCRITA  F = {F_TOTAL} N   (densidad f = {F_VOL} N/m3)")
    print(f"  con rho = 1 y sin relajacion: dU/dt = F/(rho V) = {F_TOTAL/(S*L)} m/s2")
    print(f"  tras T = {T_FIN} s debe medirse Ux = {F_TOTAL/(S*L)*T_FIN} m/s")
    print()

    # Cuatro formulaciones. Se distingue "densidad" de "fuerza total" y absolute de specific.
    casos = [
        ("A_dens_abs", F_VOL, "absolute"),
        ("B_dens_spec", F_VOL, "specific"),
        ("C_fuerza_abs", F_TOTAL, "absolute"),
        ("D_fuerza_spec", F_TOTAL, "specific"),
    ]

    resultados = []
    for nombre, su, modo in casos:
        destino = BASE / nombre
        escribir_caso(destino, su, modo)
        print(f"-- {nombre}: su = {su:.6e}, volumeMode = {modo}")

        rb = subprocess.run(["blockMesh", "-case", str(destino)],
                            cwd=destino, capture_output=True, text=True, timeout=300)
        if rb.returncode != 0:
            print(f"   [FALLO] blockMesh rc={rb.returncode}")
            resultados.append((nombre, su, modo, None))
            continue

        r = subprocess.run(["pimpleFoam", "-case", str(destino)],
                           cwd=destino, capture_output=True, text=True, timeout=1800)
        if r.returncode != 0:
            print(f"   [FALLO] pimpleFoam rc={r.returncode}")
            print("   " + "\n   ".join(r.stdout.splitlines()[-8:]))
            resultados.append((nombre, su, modo, None))
            continue

        tiempos = sorted((float(d.name), d) for d in destino.iterdir()
                         if d.is_dir() and d.name.replace(".", "").isdigit()
                         and float(d.name) > 0)
        serie = [(t, leer_U_media(d, 20)) for t, d in tiempos]
        if not serie:
            print("   [FALLO] no se escribio ningun tiempo")
            resultados.append((nombre, su, modo, None))
            continue

        # F_aplicada = rho * V * U/T  con rho = 1
        t_fin, u_fin = serie[-1]
        F_medida = S * L * u_fin / t_fin

        print(f"   Ux(t): " + "  ".join(f"t={t:.0f}:{u:+.6e}" for t, u in serie))
        print(f"   F_aplicada medida = rho*V*U/T = {F_medida:.8e} N")
        print(f"   respecto a la prescrita {F_TOTAL} N  ->  factor {F_medida/F_TOTAL:.6f}")
        print(f"   respecto a su*V = {su*S*L:.6e}      ->  factor {F_medida/(su*S*L):.6f}")
        print(f"   respecto a su   = {su:.6e}           ->  factor {F_medida/su:.6f}")
        resultados.append((nombre, su, modo, F_medida))
        print()

    print("=" * 100)
    print(" LECTURA")
    print("=" * 100)
    print(f"  fuerza PRESCRITA en el test: {F_TOTAL} N")
    print()
    print(f"  {'caso':<16}{'modo':<10}{'su':>12}{'F medida':>16}{'F/su':>12}{'F/(su*V)':>12}")
    for nombre, su, modo, fx in resultados:
        if fx is None:
            print(f"  {nombre:<16}{modo:<10}{su:>12.4e}   sin resultado")
            continue
        ok = "OK" if abs(fx - F_TOTAL) / F_TOTAL < 0.02 else "  "
        print(f"  {nombre:<16}{modo:<10}{su:>12.4e}{fx:>16.8e}{fx/su:>12.4f}"
              f"{fx/(su*S*L):>12.4f}  {ok}")
    print()
    print("  Interpretacion del factor F/su:")
    print(f"     = 1        -> el valor del diccionario ES la fuerza total aplicada")
    print(f"     = {S*L:.1f}      -> el valor del diccionario es una DENSIDAD, se integra por V")
    print(f"     = 1/{S*L:.1f}    -> se divide por V DOS veces (el fallo que se investiga)")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
