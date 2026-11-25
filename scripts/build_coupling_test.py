"""
PRUEBA DE ACOPLAMIENTO AIRE/GOTAS (INSTRUCCIONES_CFD.md §5.1 y §5.5.4) sobre el caso CFD-0.

Pregunta: las gotas alteran el campo de aire? Si no, la simulacion se parte en nivel A (aire)
y nivel B (gotas sobre aire congelado) y la dosis escala linealmente.

Metodo: dos corridas TRANSITORIAS identicas con kinematicParcelFoam (mismo solver de U que
simpleFoam: ecuacion cinematica + la misma fuente vectorSemiImplicitSource en m/s2), que
arrancan del campo RANS convergido del CFD-0 oficial:
    C_<air>_uno   coupled no    (las gotas ven el aire; el aire no ve las gotas)
    C_<air>_dos   coupled yes   (fuente de momento de las parcelas en la ecuacion de U)
La diferencia entre ambas (promedios temporales en la ventana estadistica) es el efecto del
acoplamiento. La variabilidad temporal de `uno` da el ruido contra el que se compara.

PEOR CASO declarado (todo sesga hacia MAS acoplamiento):
    Q          24 L/min (Q_max con 4 atomizadores, P) por los 2 atomizadores ESTANDAR (12 c/u):
               1.5x el maximo real de la configuracion de 2 (16 L/min). En hover: toda la
               masa queda en la columna de downwash (en avance se reparte en la estela).
    rpm        14 000 (P-A, maximo) -> v_borde = w R = 44 m/s, R_disco = 0.03 m (meta)
    gotas      Rosin-Rammler d 100 um, n 3, 20-400 um (I: sin espectro medido; D)
    lamina     radial, cono 85-90 grados respecto a -eje del atomizador (I)
Sin dispersion turbulenta estocastica (no cambia el balance de momento medio; declarado).
Suelo y fuselaje: stick (la gota se deposita); contornos abiertos: escape.

Uso:
    python scripts/build_coupling_test.py                      # escribe los 2 casos
    bash cfd/cases/_acoplamiento/run_acoplamiento.sh           # (en WSL, via foam_run.py)
"""
from __future__ import annotations

import json
import math
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FUENTE = ROOT / "cfd" / "cases" / "A_T25P_V00.0_H2.5_f1.00_g2"
DEST = ROOT / "cfd" / "cases" / "_acoplamiento"

Q_TOTAL_LMIN = 24.0
RHO_L = 996.2               # agua 28 C (build_lagrangian_spec)
RPM = 14000.0
D_RR_M, N_RR, DMIN, DMAX = 100e-6, 3.0, 20e-6, 400e-6
END_T = 2.0                 # s fisicos
VENTANA = (1.0, 2.0)        # ventana estadistica (la estela se renueva en ~0.3 s)
PARCELAS_S = 20000          # por atomizador
# El centro del disco (meta) queda DENTRO del cuerpo del atomizador en el STL (el cuerpo baja
# hasta z = -0.291 en r < 5 cm). Se inyecta 3 cm mas abajo a lo largo de -eje, ya en el aire
# (clase I, declarado): la gota sale del borde del disco y cruza ese tramo en < 1 ms.
DESPLAZ_M = 0.03

CAB = """FoamFile
{{
    version     2.0;
    format      ascii;
    class       {cls};
    object      {obj};
}}
// generado por scripts/build_coupling_test.py
"""


def _ultimo_tiempo(caso: Path) -> Path:
    ts = [d for d in caso.iterdir() if d.is_dir() and d.name.replace(".", "").isdigit() and d.name != "0"]
    return max(ts, key=lambda d: float(d.name))


def nube(meta: dict, acoplado: bool) -> str:
    boq = [b for b in meta["boquillas"] if b["configuracion"] == "estandar"]
    q_kg_s = Q_TOTAL_LMIN / 60000.0 * RHO_L / len(boq)
    R = boq[0]["radio_disco_m"]
    umag = RPM * 2 * math.pi / 60 * R
    iny = []
    for b in boq:
        e = b["eje"]
        c = [b["centro_m"][k] - DESPLAZ_M * e[k] for k in range(3)]
        iny.append(f"""        {b['nozzle_id']}
        {{
            type            coneNozzleInjection;
            SOI             0;
            duration        {END_T};
            massTotal       {q_kg_s * END_T:.6g};
            parcelBasisType mass;
            injectionMethod disc;
            flowType        constantVelocity;
            UMag            {umag:.4g};
            outerDiameter   {2 * R:.4g};
            innerDiameter   {2 * R * 0.9:.4g};
            position        ({c[0]:.5f} {c[1]:.5f} {c[2]:.5f});
            direction       ({-e[0]} {-e[1]} {-e[2]});
            parcelsPerSecond {PARCELAS_S};
            flowRateProfile constant 1;
            thetaInner      constant 85;
            thetaOuter      constant 90;
            sizeDistribution
            {{
                type        RosinRammler;
                RosinRammlerDistribution {{ lambda {D_RR_M}; n {N_RR}; minValue {DMIN}; maxValue {DMAX}; }}
            }}
        }}""")
    return CAB.format(cls="dictionary", obj="kinematicCloudProperties") + f"""
solution
{{
    active          true;
    coupled         {'yes' if acoplado else 'no'};
    transient       yes;
    cellValueSourceCorrection no;
    maxCo           0.3;
    sourceTerms {{ schemes {{ U semiImplicit 1; }} }}
    interpolationSchemes {{ rho cell; U cellPoint; muc cell; p cell; }}
    integrationSchemes {{ U Euler; }}
}}

constantProperties {{ rho0 {RHO_L}; }}

subModels
{{
    particleForces {{ sphereDrag; gravity; }}
    injectionModels
    {{
{chr(10).join(iny)}
    }}
    dispersionModel none;
    patchInteractionModel localInteraction;
    localInteractionCoeffs
    {{
        patches
        (
            "(ground|airframe)" {{ type stick; }}
            "(inlet|outlet|sides|top)" {{ type escape; }}
        );
    }}
    stochasticCollisionModel none;
    surfaceFilmModel none;
}}

cloudFunctions
{{
    impactos_suelo {{ type particlePostProcessing; maxStoredParcels 2000000; patches (ground); }}
}}
"""


def control_dict(src: str) -> str:
    """El de simpleFoam con tiempo transitorio; se conservan TODAS las function objects."""
    rep = {"application": "kinematicParcelFoam", "startFrom": "startTime", "endTime": f"{END_T}",
           "deltaT": "2e-4", "writeControl": "adjustable", "writeInterval": "0.25", "purgeWrite": "0",
           "writeFormat": "binary"}
    out = []
    for l in src.splitlines():
        k = l.split()[0] if l.split() else ""
        if k in rep and not l.startswith(" "):
            l = f"{k:<16}{rep.pop(k)};"
        out.append(l)
        if k == "runTimeModifiable":
            out += ["adjustTimeStep  yes;", "maxCo           0.8;", "maxDeltaT       2e-3;"]
    txt = "\n".join(out)
    # function objects por paso de tiempo: en transitorio cada 20 pasos esta bien (~10-40 ms)
    return txt


FVSCHEMES = CAB.format(cls="dictionary", obj="fvSchemes") + """
ddtSchemes      { default Euler; }
gradSchemes     { default Gauss linear; limited cellLimited Gauss linear 1; grad(U) cellLimited Gauss linear 1; }
divSchemes
{
    default                         none;
    div(phi,U)                      bounded Gauss linearUpwind limited;
    div(phi,k)                      bounded Gauss upwind;
    div(phi,omega)                  bounded Gauss upwind;
    div((nuEff*dev2(T(grad(U)))))   Gauss linear;
}
laplacianSchemes { default Gauss linear limited corrected 0.5; }
interpolationSchemes { default linear; }
snGradSchemes   { default limited corrected 0.5; }
wallDist        { method meshWave; }
"""

FVSOLUTION = CAB.format(cls="dictionary", obj="fvSolution") + """
solvers
{
    p      { solver GAMG; tolerance 1e-7; relTol 0.01; smoother GaussSeidel; }
    pFinal { $p; relTol 0; }
    "(U|k|omega)"      { solver smoothSolver; smoother symGaussSeidel; tolerance 1e-8; relTol 0.05; }
    "(U|k|omega)Final" { $U; relTol 0; }
}
PIMPLE
{
    momentumPredictor   yes;
    nOuterCorrectors    1;
    nCorrectors         2;
    nNonOrthogonalCorrectors 1;
    pRefCell 0; pRefValue 0;
}
relaxationFactors { equations { ".*" 1; } }
"""


def escribir(acoplado: bool) -> Path:
    meta = json.loads((FUENTE / "case_meta.json").read_text(encoding="utf-8"))
    nombre = f"C_{meta['air_id']}_{'dos' if acoplado else 'uno'}"
    caso = DEST / nombre
    if caso.exists():
        raise SystemExit(f"{caso} ya existe: no se sobrescribe (borrarlo es decision del propietario)")
    (caso / "0").mkdir(parents=True)
    shutil.copytree(FUENTE / "constant", caso / "constant")
    shutil.copytree(FUENTE / "system", caso / "system")
    ult = _ultimo_tiempo(FUENTE)
    for f in ("U", "p", "k", "omega", "nut", "phi"):
        if (ult / f).exists():
            shutil.copy2(ult / f, caso / "0" / f)
    rho = meta["propiedades_fluido"]["rho"]
    (caso / "constant" / "transportProperties").write_text(
        CAB.format(cls="dictionary", obj="transportProperties")
        + f"\ntransportModel  Newtonian;\nnu              {meta['propiedades_fluido']['nu']};\nrhoInf          {rho};\n",
        encoding="utf-8")
    g = meta["propiedades_fluido"]["g"]
    (caso / "constant" / "g").write_text(
        CAB.format(cls="uniformDimensionedVectorField", obj="g")
        + f"\ndimensions      [0 1 -2 0 0 0 0];\nvalue           (0 0 {-g});\n", encoding="utf-8")
    (caso / "constant" / "kinematicCloudProperties").write_text(nube(meta, acoplado), encoding="utf-8")
    cd = caso / "system" / "controlDict"
    cd.write_text(control_dict(cd.read_text(encoding="utf-8")), encoding="utf-8")
    (caso / "system" / "fvSchemes").write_text(FVSCHEMES, encoding="utf-8")
    (caso / "system" / "fvSolution").write_text(FVSOLUTION, encoding="utf-8")
    ficha = {"proposito": "verificacion del acoplamiento en un sentido (INSTRUCCIONES §5.1)",
             "caso_aire": meta["air_id"], "campo_inicial": f"{FUENTE.name}/{ult.name} (RANS convergido)",
             "acoplado": acoplado, "Q_total_Lmin": Q_TOTAL_LMIN, "atomizadores": "estandar (2)",
             "rpm": RPM, "desplazamiento_inyeccion_m": DESPLAZ_M, "UMag_ms": round(RPM * 2 * math.pi / 60 * meta["boquillas"][0]["radio_disco_m"], 3),
             "gotas": {"modelo": "RosinRammler", "lambda_m": D_RR_M, "n": N_RR, "min_m": DMIN, "max_m": DMAX,
                       "clase": "I"},
             "endTime_s": END_T, "ventana_estadistica_s": VENTANA, "rho_aire": rho, "rho_liquido": RHO_L,
             "peor_caso": "24 L/min por 2 atomizadores (1.5x el maximo real de 2), hover, rpm maxima",
             "sin": ["dispersion turbulenta estocastica", "evaporacion", "rotura secundaria"]}
    (caso / "coupling_meta.json").write_text(json.dumps(ficha, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"  escrito {caso.relative_to(ROOT)}  (campo inicial t={ult.name})")
    return caso


RUN_SH = """#!/bin/bash
# Ejecuta las dos corridas de acoplamiento (uno, dos). Llamar via scripts/foam_run.py.
set -euo pipefail
NP=${NP:-6}
cd "$(dirname "$0")"
for c in C_*_uno C_*_dos; do
  [[ -f $c/log.kinematicParcelFoam && -n "$(grep -E '^End' $c/log.kinematicParcelFoam || true)" ]] && { echo "$c ya hecho"; continue; }
  ( cd $c
    rm -rf processor*
    foamDictionary -entry numberOfSubdomains -set $NP system/decomposeParDict > /dev/null
    decomposePar -force > log.decomposePar 2>&1
    echo "== $(date -Iseconds) $c kinematicParcelFoam x$NP"
    mpirun --oversubscribe -np $NP kinematicParcelFoam -parallel > log.kinematicParcelFoam 2>&1
    reconstructPar -latestTime > log.reconstructPar 2>&1
    rm -rf processor*
    echo "== $(date -Iseconds) $c fin" )
done
"""


def main() -> int:
    DEST.mkdir(parents=True, exist_ok=True)
    for acop in (False, True):
        escribir(acop)
    (DEST / "run_acoplamiento.sh").write_text(RUN_SH, encoding="utf-8", newline="\n")
    print(f"  -> {(DEST / 'run_acoplamiento.sh').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
