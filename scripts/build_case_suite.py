"""
GENERADOR DE CASOS OpenFOAM — GEOMETRIA v2 (nivel A: campo de aire).

Version 2 (2026-11-22). La version 1 (planta "regular X", T55/T70P coaxiales, `diskDir (0 0 -1)`,
cajas de control) esta en `archive/scripts_geometria_v1/build_case_suite_v1.py` y sus 131 casos en
`cfd/cases/_obsoletos_geometria_v1/`. NO se mezclan.

QUE CAMBIA RESPECTO DE v1 (cada punto con su evidencia):
  1. Rotores: centros, normales inclinadas, areas y sentido de giro salen de
     `geometry/models/<P>_CFD/<p>_cfd_coordinates.json` via `scripts/agras_model/cfd_geometry.py`.
     T25P/T55/T70P = 4 rotores simples; T100 = 8 (4 pares coaxiales).
  2. Fuerza sobre el aire de cada rotor: F_i = -T_i * n_i (vectorial, inclinada), no (0,0,-T).
     La magnitud se escala para que sum(F_z) = -m g exactamente (con el cant, n_z = 0.99926:
     un 0.07 % del empuje es lateral/longitudinal y se cancela por simetria).
  3. Suelo: z_suelo = ground_plane_z_m - H. H se mide desde el CONTACTO DE LOS PATINES
     (INSTRUCCIONES_CFD §6 paso 1; clase I: el radar de DJI mide desde el cuerpo, no se sabe
     el punto exacto -> la diferencia, ~0.1 m, se declara).
  4. Pared no-slip: `<p>_airframe.stl` con snappyHexMesh (v1 usaba cajas de control).
  5. SENTIDO DEL FLUJO (error de v1 encontrado al migrar): v1 ponia el inlet en x_min con
     U = (+V 0 0), es decir aire hacia +X = dron volando hacia -X (marcha atras en la terna v2,
     +X adelante). Ahora, en ejes del dron: inlet en x_max, U = (-V 0 0), y el SUELO SE MUEVE
     a (-V 0 0) (INSTRUCCIONES §5.5: no inventar una capa limite en un suelo fijo).
  6. Actitud: si theta != 0, se gira el modelo entero (STL, rotores, boquillas) un angulo de
     cabeceo theta (morro abajo) alrededor del origen. El CG es clase D: se declara.
  7. `actuationDiskSource` retirado (bug #6). La fuente prescrita la escribe
     `build_prescribed_momentum.py` DESPUES de mallar, con el volumen real de cada zona.
     `Allrun` se niega a resolver si `constant/fvOptions` no contiene esa fuente.

REGLA: genera CASOS, no resultados. Nada de este archivo es salida de CFD.

Uso:
  python scripts/build_case_suite.py --air-id <air_id>            # un caso desde la BD
  python scripts/build_case_suite.py --plataforma T25P --V 0 --H 2.5 --f 1.0 [--malla gruesa]
  python scripts/build_case_suite.py --pendientes [--max N]       # todos los air_cases pendientes
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import sqlite3
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "agras_model"))
sys.path.insert(0, str(ROOT / "scripts"))

import cfd_geometry as cg  # noqa: E402

DB = ROOT / "data" / "processed" / "dronewith.sqlite"
CASES = ROOT / "cfd" / "cases"
GEOMETRIA_VERSION = "2.0"

# Gravedad estandar. DEBE coincidir con `scripts/force_chain.py` (Entry 016).
G = 9.80665
RHO = 1.1716          # 28 C, nivel del mar (E; deberia ser f(P,T,HR), ver force_chain [F])
NU = 1.5e-5           # m2/s, aire a ~28 C
P_ATM = 101325.0
RHO_W = 996.2
MU_W = 0.000836
SIGMA_W = 0.0719

# Niveles de malla para el estudio de independencia (factor ~1.4 entre niveles).
MALLAS = {
    "gruesa": {"dx": 0.25, "lv_cerca": 1, "lv_disco": 2, "lv_cuerpo": (2, 3)},
    "media":  {"dx": 0.18, "lv_cerca": 1, "lv_disco": 2, "lv_cuerpo": (2, 3)},
    "fina":   {"dx": 0.125, "lv_cerca": 1, "lv_disco": 2, "lv_cuerpo": (2, 3)},
}

# Turbulencia de entrada: intensidad y escala de longitud (clase I, declaradas).
TU_ENTRADA = 0.05
L_TURB_M = 0.10

# --------------------------------------------------------------------------------------
# Compatibilidad con scripts que importaban la API v1 (fix_case_meta_gravity.py, etc.)
# --------------------------------------------------------------------------------------
_PLATS = cg.cargar_todas()
PLAT = {k: {"nombre": p.nombre, "coaxial": p.coaxial, "m_bat": p.masa_vacio_kg,
            "tanque": p.tanque_kg, "mtow": p.mtow_kg} for k, p in _PLATS.items()}
SPLIT_COAXIAL = [0.5, 0.6, 0.7]


def rot_centers(p) -> list[dict]:
    """Centros de rotor v2 (antes: planta regular X). Acepta clave o dict de PLAT."""
    clave = p if isinstance(p, str) else next(k for k, v in PLAT.items() if v is p)
    return [{"id": r.rotor_id, "role": r.brazo, "x": r.centro[0], "y": r.centro[1],
             "z": r.centro[2], "normal": r.normal, "nivel": r.nivel}
            for r in _PLATS[clave].rotores]


# --------------------------------------------------------------------------------------
# geometria: giro de cabeceo
# --------------------------------------------------------------------------------------
def rot_cabeceo(v, theta_deg: float) -> tuple:
    """Cabeceo MORRO ABAJO de theta (>0): la normal vertical se inclina hacia +X (adelante).
    Giro alrededor de +Y: x' = x cos + z sin ; z' = -x sin + z cos."""
    t = math.radians(theta_deg)
    c, s = math.cos(t), math.sin(t)
    return (v[0] * c + v[2] * s, v[1], -v[0] * s + v[2] * c)


def stl_girado(origen: Path, destino: Path, theta_deg: float, nombre: str) -> int:
    """Copia un STL binario girado theta (cabeceo). Devuelve el numero de facetas."""
    datos = origen.read_bytes()
    n = struct.unpack("<I", datos[80:84])[0]
    if len(datos) != 84 + 50 * n:
        raise ValueError(f"{origen.name}: no es un STL binario valido")
    cab = (nombre.encode() + b" " * 80)[:80]
    out = bytearray(cab + struct.pack("<I", n))
    for i in range(n):
        reg = struct.unpack("<12fH", datos[84 + 50 * i: 84 + 50 * (i + 1)])
        vs = [rot_cabeceo(reg[3 * k: 3 * k + 3], theta_deg) for k in range(4)]
        out += struct.pack("<12fH", *[c for v in vs for c in v], reg[12])
    destino.write_bytes(bytes(out))
    return n


# --------------------------------------------------------------------------------------
# fisica del caso (analitica, declarada)
# --------------------------------------------------------------------------------------
def empujes_y_fuerzas(p: cg.Plataforma, masa: float, theta_deg: float, split: float) -> dict:
    """Empuje por rotor y fuerza sobre el aire, con sum(F_aire,z) = -m g exactamente."""
    pesos = p.reparto_empuje(1.0, split)                      # reparto relativo (suma 1)
    normales = [rot_cabeceo(r.normal, theta_deg) for r in p.rotores]
    nz = sum(w * n[2] for w, n in zip(pesos, normales))
    W = masa * G
    escala = W / nz                                           # empuje total |T|
    T = [escala * w for w in pesos]
    F = [tuple(-t * c for c in n) for t, n in zip(T, normales)]
    return {"T": T, "F_aire": F, "normales": normales, "W": W, "T_total": escala,
            "F_suma": tuple(sum(f[i] for f in F) for i in range(3))}


def foam_header(cls: str, obj: str) -> str:
    return f"""/*--------------------------------*- C++ -*----------------------------------*\\
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
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //
"""


def _v(t, fmt=".5f") -> str:
    return "(" + " ".join(format(c, fmt) for c in t) + ")"


# --------------------------------------------------------------------------------------
# escritura del caso
# --------------------------------------------------------------------------------------
def escribir_caso_aire(case_dir: Path, air: dict, malla: str = "gruesa",
                       hover_bc: str = "abierto") -> dict:
    """Escribe un caso de aire completo. `air` = fila de air_cases (o equivalente)."""
    p = cg.cargar(air["plataforma"])
    V = float(air["V_ms"])
    H = float(air["H_m"])
    f = float(air["f"])
    split = float(air.get("split_coax") or 0.5)
    theta = air.get("theta_actitud_deg")
    if V > 0 and theta is None:
        raise ValueError(f"{air.get('air_id')}: V = {V} m/s sin actitud theta. La actitud "
                         "en avance es clase D hasta tener telemetria o Cd*A; no se inventa.")
    theta = float(theta or 0.0)
    masa = p.masa(f)
    m = MALLAS[malla]
    dx = m["dx"]
    hover = V == 0.0

    fz = empujes_y_fuerzas(p, masa, theta, split)
    centros = [rot_cabeceo(r.centro, theta) for r in p.rotores]
    boq = [(b, rot_cabeceo(b.centro, theta), rot_cabeceo(b.eje, theta)) for b in p.boquillas]

    # ---- dominio (ejes del dron)
    z_suelo = p.z_suelo_modelo - H
    z_top = 5.0
    if hover:
        x0, x1, y0, y1 = -10.0, 10.0, -10.0, 10.0      # simetrico (Entry 017: remallado)
    else:
        x0, x1, y0, y1 = -16.0, 8.0, -8.0, 8.0         # estela aguas abajo (-X)
    nx, ny, nz = (round((x1 - x0) / dx), round((y1 - y0) / dx), round((z_top - z_suelo) / dx))
    # celda en el disco y espesor de la zona: un cilindro mas fino que ~1.5 celdas sale vacio
    dx_disco = dx / 2 ** m["lv_disco"]
    h_zona = max(max(r.espesor_m for r in p.rotores), 1.5 * dx_disco)

    for sub in ("system", "constant/triSurface", "0"):
        (case_dir / sub).mkdir(parents=True, exist_ok=True)

    n_fac = stl_girado(p.stl_airframe, case_dir / "constant" / "triSurface" / "airframe.stl",
                       theta, f"{p.clave} airframe v{p.version_modelo} theta={theta}")

    # ---- blockMeshDict
    (case_dir / "system" / "blockMeshDict").write_text(foam_header("dictionary", "blockMeshDict") + f"""
scale 1;
vertices
(
    ({x0} {y0} {z_suelo:.5f}) ({x1} {y0} {z_suelo:.5f}) ({x1} {y1} {z_suelo:.5f}) ({x0} {y1} {z_suelo:.5f})
    ({x0} {y0} {z_top}) ({x1} {y0} {z_top}) ({x1} {y1} {z_top}) ({x0} {y1} {z_top})
);
blocks ( hex (0 1 2 3 4 5 6 7) ({nx} {ny} {nz}) simpleGrading (1 1 1) );
edges ();
boundary
(
    // ejes del dron: +X adelante. En avance el aire ENTRA por x_max (inlet) y sale por x_min.
    inlet  {{ type patch; faces ((1 2 6 5)); }}
    outlet {{ type patch; faces ((0 4 7 3)); }}
    sides  {{ type patch; faces ((0 1 5 4) (3 7 6 2)); }}
    top    {{ type patch; faces ((4 5 6 7)); }}
    ground {{ type wall;  faces ((0 3 2 1)); }}
);
mergePatchPairs ();
""", encoding="utf-8")

    # ---- surfaceFeatureExtract + snappyHexMesh
    (case_dir / "system" / "surfaceFeatureExtractDict").write_text(
        foam_header("dictionary", "surfaceFeatureExtractDict") + """
airframe.stl
{
    extractionMethod    extractFromSurface;
    includedAngle       150;
    subsetFeatures { nonManifoldEdges no; openEdges yes; }
    writeObj            no;
}
""", encoding="utf-8")

    R = max(r.radio_m for r in p.rotores)
    xs = [c[0] for c in centros]
    ys = [c[1] for c in centros]
    zs = [c[2] for c in centros]
    # caja "cerca": rotores + estela hasta el suelo; en avance se alarga aguas abajo el
    # recorrido de la estela en el tiempo de caida ~ (H+1)/v_i  (orden de magnitud)
    vi = p.v_inducida_hover(masa)
    arrastre = 0.0 if hover else min(V * (H + 1.0) / vi, 12.0)
    cerca_min = (min(xs) - R - 0.5 - arrastre, min(ys) - R - 0.5, z_suelo - 1.0)
    cerca_max = (max(xs) + R + 0.5, max(ys) + R + 0.5, max(zs) + 0.8)
    regiones = [f"""        cerca
        {{
            type searchableBox; min {_v(cerca_min, '.3f')}; max {_v(cerca_max, '.3f')};
        }}"""]
    niveles = [f"        cerca {{ mode inside; levels ((1e15 {m['lv_cerca']})); }}"]
    for i, (r, c, n) in enumerate(zip(p.rotores, centros, fz["normales"]), 1):
        a = tuple(c[k] - 0.15 * n[k] for k in range(3))
        b = tuple(c[k] + 0.15 * n[k] for k in range(3))
        regiones.append(f"""        disco{i}   // {r.rotor_id}
        {{
            type searchableCylinder; point1 {_v(a)}; point2 {_v(b)}; radius {1.08 * r.radio_m:.4f};
        }}""")
        niveles.append(f"        disco{i} {{ mode inside; levels ((1e15 {m['lv_disco']})); }}")
    for j, (b, c, e) in enumerate(boq, 1):
        regiones.append(f"""        boquilla{j}   // {b.nozzle_id}
        {{
            type searchableSphere; centre {_v(c)}; radius 0.30;
        }}""")
        niveles.append(f"        boquilla{j} {{ mode inside; levels ((1e15 {m['lv_disco']})); }}")
    lv0, lv1 = m["lv_cuerpo"]
    loc = (x1 - 0.371, y1 - 0.413, z_top - 0.437)
    (case_dir / "system" / "snappyHexMeshDict").write_text(foam_header("dictionary", "snappyHexMeshDict") + f"""
castellatedMesh true;
snap            true;
addLayers       false;   // capas: se activan tras el estudio de y+ de CFD-0

geometry
{{
    airframe.stl {{ type triSurfaceMesh; name airframe; }}
{chr(10).join(regiones)}
}}

castellatedMeshControls
{{
    maxLocalCells       4000000;
    maxGlobalCells      8000000;
    minRefinementCells  10;
    maxLoadUnbalance    0.10;
    nCellsBetweenLevels 3;
    features ( {{ file "airframe.eMesh"; level {lv1}; }} );
    refinementSurfaces {{ airframe {{ level ({lv0} {lv1}); patchInfo {{ type wall; }} }} }}
    resolveFeatureAngle 30;
    refinementRegions
    {{
{chr(10).join(niveles)}
    }}
    locationInMesh {_v(loc, '.3f')};
    allowFreeStandingZoneFaces true;
}}

snapControls
{{
    nSmoothPatch 3; tolerance 2.0; nSolveIter 50; nRelaxIter 5;
    nFeatureSnapIter 10; implicitFeatureSnap false; explicitFeatureSnap true;
    multiRegionFeatureSnap false;
}}

addLayersControls
{{
    relativeSizes true; layers {{ airframe {{ nSurfaceLayers 3; }} }}
    expansionRatio 1.2; finalLayerThickness 0.4; minThickness 0.1; nGrow 0;
    featureAngle 60; nRelaxIter 5; nSmoothSurfaceNormals 1; nSmoothNormals 3;
    nSmoothThickness 10; maxFaceThicknessRatio 0.5; maxThicknessToMedialRatio 0.3;
    minMedialAxisAngle 90; nBufferCellsNoExtrude 0; nLayerIter 50;
}}

meshQualityControls
{{
    maxNonOrtho 65; maxBoundarySkewness 20; maxInternalSkewness 4; maxConcave 80;
    minVol 1e-13; minTetQuality 1e-15; minArea -1; minTwist 0.02; minDeterminant 0.001;
    minFaceWeight 0.05; minVolRatio 0.01; minTriangleTwist -1; nSmoothScale 4;
    errorReduction 0.75;
}}
mergeTolerance 1e-6;
""", encoding="utf-8")

    # ---- topoSet: cellZone cilindrica INCLINADA por rotor (centro +- h/2 * normal)
    acciones = []
    zonas_meta = {}
    for i, (r, c, n, T, F) in enumerate(zip(p.rotores, centros, fz["normales"], fz["T"], fz["F_aire"]), 1):
        a = tuple(c[k] - 0.5 * h_zona * n[k] for k in range(3))
        b = tuple(c[k] + 0.5 * h_zona * n[k] for k in range(3))
        acciones.append(f"""    // rotor{i} = {r.rotor_id} ({r.nivel}, {r.giro_desde_arriba}); espesor de zona {h_zona:.4f} m
    {{ name rotorSet{i}; type cellSet; action new; source cylinderToCell;
      p1 {_v(a)}; p2 {_v(b)}; radius {r.radio_m:.5f}; }}
    {{ name rotor{i}; type cellZoneSet; action new; source setToCellZone; set rotorSet{i}; }}""")
        zonas_meta[f"rotor{i}"] = {
            "rotor_id": r.rotor_id, "nivel": r.nivel, "giro_desde_arriba": r.giro_desde_arriba,
            "centro_m": [round(x, 6) for x in c], "normal": [round(x, 7) for x in n],
            "radio_m": r.radio_m, "espesor_zona_m": round(h_zona, 5),
            "V_teorico_m3": round(math.pi * r.radio_m ** 2 * h_zona, 7),
            "T_N": round(T, 6), "F_aire_N": [round(x, 6) for x in F],
        }
    (case_dir / "system" / "topoSetDict").write_text(foam_header("dictionary", "topoSetDict") + f"""
// Una cellZone cilindrica por rotor, ALINEADA con disk_normal (geometria v2, inclinada).
actions
(
{chr(10).join(acciones)}
);
""", encoding="utf-8")

    # ---- controlDict + function objects de verificacion (CFD-0) y extraccion
    lineas_dw = []
    for i, (c, n) in enumerate(zip(centros, fz["normales"]), 1):
        lineas_dw.append(f"""            bajo_rotor{i} {{ type uniform; axis z; start ({c[0]:.4f} {c[1]:.4f} {z_suelo + 0.02:.4f});
                           end ({c[0]:.4f} {c[1]:.4f} {c[2] + 1.0:.4f}); nPoints 80; }}""")
    zonas_vff = []
    for i in range(1, len(p.rotores) + 1):
        zonas_vff.append(f"""    U_rotor{i}
    {{
        type volFieldValue; libs (fieldFunctionObjects); writeControl timeStep; writeInterval 20;
        regionType cellZone; name rotor{i}; operation volAverage; fields (U); writeFields false;
    }}""")
    z_boq = min(c[2] for _, c, _ in boq)
    (case_dir / "system" / "controlDict").write_text(foam_header("dictionary", "controlDict") + f"""
application     simpleFoam;
startFrom       latestTime;
startTime       0;
stopAt          endTime;
endTime         3000;
deltaT          1;
writeControl    timeStep;
writeInterval   500;
purgeWrite      2;
writeFormat     ascii;
writePrecision  8;
writeCompression off;
timeFormat      general;
timePrecision   6;
runTimeModifiable true;

functions
{{
    residuales {{ type solverInfo; libs (utilityFunctionObjects); fields (U p k omega); writeResidualFields no; }}
    minmax     {{ type fieldMinMax; libs (fieldFunctionObjects); fields (U p); writeControl timeStep; writeInterval 20; }}

    // balance global de momento (CFD-0, condicion 2): fuerza sobre suelo y sobre el fuselaje
    fuerza_suelo
    {{
        type forces; libs (forces); writeControl timeStep; writeInterval 20;
        patches (ground); rho rhoInf; rhoInf {RHO}; CofR (0 0 0);
    }}
    fuerza_fuselaje
    {{
        type forces; libs (forces); writeControl timeStep; writeInterval 20;
        patches (airframe); rho rhoInf; rhoInf {RHO}; CofR (0 0 0);
    }}
    fuerza_contorno
    {{
        type forces; libs (forces); writeControl timeStep; writeInterval 20;
        patches (inlet outlet sides top); rho rhoInf; rhoInf {RHO}; CofR (0 0 0);
    }}

{chr(10).join(zonas_vff)}

    downwash
    {{
        type sets; libs (sampling); writeControl writeTime; interpolationScheme cellPoint;
        setFormat raw; fields (U k);
        sets
        {{
{chr(10).join(lineas_dw)}
        }}
    }}

    planos
    {{
        type surfaces; libs (sampling); writeControl writeTime; surfaceFormat raw;
        interpolationScheme cellPoint; fields (U p k);
        surfaces
        {{
            suelo     {{ type plane; point (0 0 {z_suelo + 0.02:.4f}); normal (0 0 1); triangulate false; }}
            boquillas {{ type plane; point (0 0 {z_boq - 0.05:.4f}); normal (0 0 1); triangulate false; }}
            simetria  {{ type plane; point (0 0 0); normal (0 1 0); triangulate false; }}
        }}
    }}

    yPlus {{ type yPlus; libs (fieldFunctionObjects); writeControl writeTime; }}
}}
""", encoding="utf-8")

    (case_dir / "system" / "fvSchemes").write_text(foam_header("dictionary", "fvSchemes") + """
ddtSchemes      { default steadyState; }
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
""", encoding="utf-8")

    (case_dir / "system" / "fvSolution").write_text(foam_header("dictionary", "fvSolution") + """
solvers
{
    p { solver GAMG; tolerance 1e-8; relTol 0.01; smoother GaussSeidel; }
    "(U|k|omega)" { solver smoothSolver; smoother symGaussSeidel; tolerance 1e-9; relTol 0.05; }
}
SIMPLE
{
    nNonOrthogonalCorrectors 1;
    consistent      yes;
    residualControl { p 1e-5; U 1e-6; "(k|omega)" 1e-6; }
}
relaxationFactors
{
    fields      { p 0.3; }
    equations   { U 0.7; k 0.7; omega 0.7; }
}
""", encoding="utf-8")

    (case_dir / "system" / "decomposeParDict").write_text(foam_header("dictionary", "decomposeParDict") + """
numberOfSubdomains 8;
method          scotch;
""", encoding="utf-8")

    (case_dir / "constant" / "turbulenceProperties").write_text(foam_header("dictionary", "turbulenceProperties") + """
simulationType  RAS;
RAS { model kOmegaSST; turbulence on; printCoeffs on; }
""", encoding="utf-8")
    (case_dir / "constant" / "transportProperties").write_text(foam_header("dictionary", "transportProperties") + f"""
transportModel  Newtonian;
nu              [0 2 -1 0 0 0 0] {NU};
""", encoding="utf-8")

    # ---- condiciones de contorno
    U_ref = max(V, vi)
    k_val = 1.5 * (U_ref * TU_ENTRADA) ** 2
    om_val = math.sqrt(k_val) / (0.09 ** 0.25 * L_TURB_M)
    Uv = f"({-V:g} 0 0)"
    if hover and hover_bc == "cerrado":
        # Entry 016/017: dominio cerrado slip + una unica salida de presion en el techo.
        bcU = {"inlet": "type slip;", "outlet": "type slip;", "sides": "type slip;",
               "top": "type slip;", "ground": "type noSlip;"}
        bcp = {"inlet": "type zeroGradient;", "outlet": "type zeroGradient;",
               "sides": "type zeroGradient;", "top": "type fixedValue; value uniform 0;",
               "ground": "type zeroGradient;"}
        bct = {k: "type slip;" for k in ("inlet", "outlet", "sides", "top")}
    elif hover:
        # aire libre: entrada/salida por presion total en todos los contornos laterales y techo
        abierto_U = "type pressureInletOutletVelocity; value uniform (0 0 0);"
        bcU = {k: abierto_U for k in ("inlet", "outlet", "sides", "top")}
        bcU["ground"] = "type noSlip;"
        bcp = {k: "type totalPressure; p0 uniform 0; value uniform 0;" for k in ("inlet", "outlet", "sides", "top")}
        bcp["ground"] = "type zeroGradient;"
        bct = None
    else:
        bcU = {"inlet": f"type fixedValue; value uniform {Uv};",
               "outlet": f"type inletOutlet; inletValue uniform (0 0 0); value uniform {Uv};",
               "sides": "type slip;", "top": "type slip;",
               "ground": f"type fixedValue; value uniform {Uv};   // suelo movil (ejes del dron)"}
        bcp = {"inlet": "type zeroGradient;", "outlet": "type fixedValue; value uniform 0;",
               "sides": "type zeroGradient;", "top": "type zeroGradient;", "ground": "type zeroGradient;"}
        bct = {"sides": "type slip;", "top": "type slip;"}
    bcU["airframe"] = "type noSlip;"
    bcp["airframe"] = "type zeroGradient;"

    def campo(nombre, clase, dims, interno, bc):
        cuerpo = "\n".join(f"    {k:9s}{{ {v} }}" for k, v in bc.items())
        (case_dir / "0" / nombre).write_text(foam_header(clase, nombre) + f"""
dimensions      {dims};
internalField   uniform {interno};
boundaryField
{{
{cuerpo}
}}
""", encoding="utf-8")

    campo("U", "volVectorField", "[0 1 -1 0 0 0 0]", Uv if not hover else "(0 0 0)", bcU)
    campo("p", "volScalarField", "[0 2 -2 0 0 0 0]", "0", bcp)
    for nombre, val, dims, wf in (("k", k_val, "[0 2 -2 0 0 0 0]", "kqRWallFunction"),
                                  ("omega", om_val, "[0 0 -1 0 0 0 0]", "omegaWallFunction")):
        bc = {}
        for pat in ("inlet", "outlet", "sides", "top"):
            if bct and pat in bct:
                bc[pat] = bct[pat]
            elif pat == "inlet" and not hover:
                bc[pat] = f"type fixedValue; value uniform {val:.6g};"
            else:
                bc[pat] = f"type inletOutlet; inletValue uniform {val:.6g}; value uniform {val:.6g};"
        bc["ground"] = f"type {wf}; value uniform {val:.6g};"
        bc["airframe"] = f"type {wf}; value uniform {val:.6g};"
        campo(nombre, "volScalarField", dims, f"{val:.6g}", bc)
    bc_nut = {k: "type calculated; value uniform 0;" for k in ("inlet", "outlet", "sides", "top")}
    bc_nut["ground"] = "type nutkWallFunction; value uniform 0;"
    bc_nut["airframe"] = "type nutkWallFunction; value uniform 0;"
    campo("nut", "volScalarField", "[0 2 -1 0 0 0 0]", "0", bc_nut)

    # ---- Allrun (WSL, via scripts/foam_run.py)
    (case_dir / "Allrun.sh").write_text(f"""#!/usr/bin/env bash
# Generado por scripts/build_case_suite.py (geometria v{GEOMETRIA_VERSION}).
# Uso: python3 scripts/foam_run.py bash cfd/cases/<air_id>/Allrun.sh   (desde la raiz)
set -euo pipefail
CASO="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
RAIZ="$(cd "$CASO/../../.." && pwd)"
cd "$CASO"
NP=${{NP:-8}}
paso() {{ echo "== $(date -Is) $*"; }}
# marcador propio: snappyHexMesh ya crea un cellZones vacio, asi que no sirve de indicador
if [[ ! -f constant/polyMesh/.malla_v2_ok ]]; then
  paso blockMesh;               blockMesh > log.blockMesh 2>&1
  paso surfaceFeatureExtract;   surfaceFeatureExtract > log.surfaceFeatureExtract 2>&1
  paso snappyHexMesh;           snappyHexMesh -overwrite > log.snappyHexMesh 2>&1
  paso topoSet;                 topoSet > log.topoSet 2>&1
  date -Is > constant/polyMesh/.malla_v2_ok
fi
paso checkMesh
checkMesh -constant > log.checkMesh 2>&1 || true
if ! grep -q "Mesh OK" log.checkMesh; then echo "[FALLO] checkMesh no da 'Mesh OK'"; exit 2; fi
paso volumenes de zona y fuente prescrita
python3 "$RAIZ/scripts/mesh_zone_volumes.py" --case "$CASO" --write > log.zoneVolumes 2>&1
python3 "$RAIZ/scripts/build_prescribed_momentum.py" --case "$CASO" > log.prescribedMomentum 2>&1
grep -q vectorSemiImplicitSource constant/fvOptions || {{ echo "[FALLO] sin fuente prescrita"; exit 3; }}
# reanudacion: si una ejecucion previa se corto, recuperar su ultimo tiempo escrito
ULT=$(ls -d processor0/[0-9]* 2>/dev/null | xargs -n1 basename 2>/dev/null | sort -g | tail -1 || true)
if [[ -n "${{ULT:-}}" && "$ULT" != "0" ]]; then
  paso "reanudacion desde t=$ULT (reconstructPar)"
  reconstructPar -latestTime > log.reconstructPar.reanudar 2>&1
  [[ -f log.simpleFoam ]] && mv log.simpleFoam "log.simpleFoam.hasta_t$ULT"   # conservar la historia previa
fi
paso decomposePar
rm -rf processor*
foamDictionary -entry numberOfSubdomains -set $NP system/decomposeParDict > /dev/null
decomposePar -force -latestTime > log.decomposePar 2>&1
paso simpleFoam x$NP
mpirun --oversubscribe -np $NP simpleFoam -parallel > log.simpleFoam 2>&1
paso reconstructPar
reconstructPar -latestTime > log.reconstructPar 2>&1
rm -rf processor*
paso fin
""", encoding="utf-8", newline="\n")

    # ---- ficha del caso
    meta = {
        "air_id": air.get("air_id"),
        "case_id": air.get("air_id"),
        "plataforma": p.clave,
        "nombre_plataforma": p.nombre,
        "geometria_version": GEOMETRIA_VERSION,
        "fuente_geometria": str(p.dir_modelo.relative_to(ROOT)).replace("\\", "/")
                            + f"/{p.prefijo}_cfd_coordinates.json",
        "arquitectura_cfd": "C (equilibrio) -> B (fuente de momento prescrita vectorSemiImplicitSource)",
        "entradas": {
            "V_inf_ms": V, "H_m": H, "carga_fraccion": f, "masa_total_kg": round(masa, 4),
            "split_coaxial_superior": split if p.coaxial else None,
            "theta_actitud_deg": theta, "malla": malla, "hover_bc": hover_bc if hover else None,
            "cuerpos_atom_opcionales": int(air.get("cuerpos_opcionales") or 0),
        },
        "derivados_analiticos": {
            "n_rotores_modelados": len(p.rotores),
            "peso_N": round(fz["W"], 6),
            "empuje_total_N": round(fz["T_total"], 6),
            "suma_F_aire_N": [round(x, 6) for x in fz["F_suma"]],
            "empuje_por_disco_N": {z: d["T_N"] for z, d in zonas_meta.items()},
            "fuerza_sobre_aire_N": {z: d["F_aire_N"] for z, d in zonas_meta.items()},
            "v_inducida_hover_ms": round(vi, 4),
            "nota": "analitico (momentum theory solo orden de magnitud); NO es CFD",
        },
        "zonas_rotor": zonas_meta,
        "boquillas": [{"nozzle_id": b.nozzle_id, "configuracion": b.configuracion,
                       "centro_m": [round(x, 6) for x in c], "eje": [round(x, 7) for x in e],
                       "radio_disco_m": b.radio_disco_m, "clasificacion": b.clasificacion}
                      for b, c, e in boq],
        "dominio": {"x": [x0, x1], "y": [y0, y1], "z": [round(z_suelo, 5), z_top],
                    "z_suelo_modelo": p.z_suelo_modelo,
                    "nota": "z_suelo = ground_plane_z_m - H (H desde el contacto de los patines, I)"},
        "malla": {"nivel": malla, "dx_base_m": dx, "dx_disco_m": dx_disco,
                  "n_bloque": [nx, ny, nz], "facetas_airframe": n_fac},
        "turbulencia_entrada": {"modelo": "kOmegaSST", "Tu": TU_ENTRADA, "L_m": L_TURB_M,
                                "U_ref_ms": round(U_ref, 4), "clase": "I"},
        "propiedades_fluido": {"rho": RHO, "nu": NU, "g": G},
        "supuestos_declarados": [
            "H medido desde el contacto de los patines (I)",
            "pivote del cabeceo en el origen del modelo; CG real D",
            "reparto de empuje igual por brazo (sin trim de momentos; force_chain.py)",
            "fuente uniforme en el disco; rotorDiskSource (elemento de pala) pendiente de CFD-0",
        ],
        "estado": "generado_no_ejecutado",
        "no_contiene": "ningun resultado de CFD: este archivo describe el caso, no su salida",
    }
    (case_dir / "case_meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return meta


# --------------------------------------------------------------------------------------
def _filas_bd(where: str, args: tuple) -> list[dict]:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    filas = [dict(r) for r in con.execute(f"SELECT * FROM air_cases WHERE {where}", args)]
    con.close()
    return filas


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--air-id")
    ap.add_argument("--pendientes", action="store_true")
    ap.add_argument("--max", type=int, default=0)
    ap.add_argument("--plataforma")
    ap.add_argument("--V", type=float, default=0.0)
    ap.add_argument("--H", type=float, default=2.5)
    ap.add_argument("--f", type=float, default=1.0)
    ap.add_argument("--split", type=float, default=0.5)
    ap.add_argument("--theta", type=float, default=None)
    ap.add_argument("--malla", choices=list(MALLAS), default=None)
    ap.add_argument("--hover-bc", choices=("cerrado", "abierto"), default="abierto")
    ap.add_argument("--out", default=str(CASES))
    ap.add_argument("--nombre", default=None, help="nombre de carpeta (por defecto, air_id)")
    a = ap.parse_args()

    if a.air_id:
        filas = _filas_bd("air_id = ?", (a.air_id,))
    elif a.pendientes:
        filas = _filas_bd("estado = 'pendiente' ORDER BY prioridad, air_id", ())
    elif a.plataforma:
        filas = [{"air_id": a.nombre or f"manual_{a.plataforma}_V{a.V:g}_H{a.H:g}_f{a.f:g}",
                  "plataforma": a.plataforma.upper(), "V_ms": a.V, "H_m": a.H, "f": a.f,
                  "split_coax": a.split, "theta_actitud_deg": a.theta, "malla": a.malla or "gruesa"}]
    else:
        ap.error("indica --air-id, --pendientes o --plataforma")
    if a.max:
        filas = filas[: a.max]
    if not filas:
        print("nada que generar")
        return 1

    ok = 0
    for fila in filas:
        destino = Path(a.out) / (a.nombre or fila["air_id"])
        try:
            meta = escribir_caso_aire(destino, fila, a.malla or fila.get("malla") or "gruesa", a.hover_bc)
        except ValueError as exc:
            print(f"  [OMITIDO] {fila['air_id']}: {exc}")
            continue
        d = meta["derivados_analiticos"]
        print(f"  {destino}  m={meta['entradas']['masa_total_kg']} kg  "
              f"|T|={d['empuje_total_N']:.2f} N  sumF=({', '.join(f'{x:+.4f}' for x in d['suma_F_aire_N'])}) N  "
              f"bloque={meta['malla']['n_bloque']}")
        ok += 1
    print(f"\n{ok} caso(s) escritos. Son CASOS, no resultados.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
