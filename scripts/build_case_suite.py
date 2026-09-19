"""
ESPECIFICACION DE CASOS + DOE por plataforma + GENERACION DE CASOS OpenFOAM.

ARQUITECTURA CFD (decidida en Entry 010/011; ver geometry/coaxial_thrust_split.md):
  C  ->  suma de empujes + peso = 0     restriccion fisica global
  C  ->  reparto de empuje por disco    a partir de masa, CG y actitud
  B  ->  actuator disk que materializa ese empuje en cada disco
  A  ->  RPM prescrita solo en casos selectos (no implementado aqui)

  Se implementa con `fvOptions/actuationDiskSource` (OpenFOAM 2412) sobre una cellZone
  cilindrica por rotor. El reparto de empuje superior/inferior es un PARAMETRO, no una
  suposicion: se barre 0.5 / 0.6 / 0.7.

DOE POR PLATAFORMA, no comun: cada UAV tiene su envolvente. Los limites salen de:
  - velocidad de aplicacion: 2-13 m/s (DJI Academy compara 3/5/7/10/13 m/s; context.md)
  - altura sobre cultivo: 1.5-6 m (rango operativo Agras; Academy T40/T50 da 3-4 m)
  - DV0.5: 100-500 um (ficha oficial 50-500; se recorta para evitar gota ultrafina)
  - carga de tanque: 0-1 con RESTRICCION de bateria por plataforma
  - atomizadores: 2 o 4 (configuracion, no variable continua)

REGLA DE HONESTIDAD DE ESTE SCRIPT:
  Genera CASOS, no resultados. No hay ningun campo de resultado de CFD aqui.
  Todo lo que se calcula (empuje por disco, area de disco, v inducida) es fisica
  ANALITICA derivada de masa y geometria, y se etiqueta como tal.

Uso:
  python scripts/build_case_suite.py --out data/processed --cfd cfd/cases
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

G = 9.81
RHO = 1.1716          # 28 C, nivel del mar
P_ATM = 101325.0
NU = 1.5e-5           # m2/s, aire a ~28 C
MU_W = 0.000836       # Pa.s, agua a 28 C
RHO_W = 996.2         # kg/m3, agua a 28 C
SIGMA_W = 0.0719      # N/m, agua a 28 C

# --------------------------------------------------------------------------------------
# PLATAFORMAS — datos con su clase de fuente (P/Academy/S/O/I)
# --------------------------------------------------------------------------------------
PLAT = {
    "T25P": dict(
        nombre="DJI Agras T25P",
        rotor_d=1.270, n_brazos=4, coaxial=False,
        m_bat=33.0, tanque=20.0, mtow=53.0,
        bateria="DB800",
        wheelbase=1.970, span=(2.650, 2.700),
        atom_std=2, atom_opt=4, atom_sep=1420, atom_x=None,
        v_range=(2.0, 13.0), h_range=(1.5, 6.0), d_range=(100.0, 500.0),
        carga_max_por_bateria=True,
        bomba_2=16.0, bomba_4=24.0,
    ),
    "T55": dict(
        nombre="DJI Agras T55",
        rotor_d=1.575, n_brazos=4, coaxial=True,
        m_bat=45.0, tanque=50.0, mtow=95.0,
        bateria="DB1050",
        wheelbase=2.415, span=(3.190, 3.570),
        atom_std=2, atom_opt=4, atom_sep=1800, atom_x=None,
        v_range=(2.0, 13.0), h_range=(1.5, 6.0), d_range=(100.0, 500.0),
        carga_max_por_bateria=True,
        bomba_2=None, bomba_4=None,   # D: no capturado
    ),
    "T70P": dict(
        nombre="DJI Agras T70P",
        rotor_d=1.574, n_brazos=4, coaxial=True,
        m_bat=56.0, tanque=70.0, mtow=126.0,
        bateria="DB2160",
        wheelbase=2.440, span=(3.200, 3.520),
        atom_std=2, atom_opt=4, atom_sep=1874, atom_x=None,
        v_range=(2.0, 13.0), h_range=(1.5, 6.0), d_range=(100.0, 500.0),
        # RESTRICCION: a 70 L solo con DB2160. Con DB1580 (52 kg) el MTOW (102) no cierra.
        carga_max_por_bateria=True,
        bomba_2=30.0, bomba_4=40.0,
    ),
    "T100": dict(
        nombre="DJI Agras T100",
        rotor_d=1.574, n_brazos=4, coaxial=True,
        m_bat=75.0, tanque=100.0, mtow=175.0,
        bateria="DB2160",
        wheelbase=2.330, span=(3.220, 3.224),
        atom_std=2, atom_opt=4, atom_sep=1834,
        atom_x=[-0.9, -0.8, -0.8, -0.9],   # clase O (propietario)
        v_range=(2.0, 13.0), h_range=(1.5, 6.0), d_range=(100.0, 500.0),
        carga_max_por_bateria=True,
        bomba_2=30.0, bomba_4=40.0,
    ),
}

# reparto de empuje del par coaxial: PARAMETRO, no supuesto (coaxial_thrust_split.md)
SPLIT_COAXIAL = [0.5, 0.6, 0.7]


def rot_centers(p: dict) -> list[dict]:
    """Centros de rotor en planta regular X (hipotesis I). Devuelve upper y lower si coaxial."""
    R = p["wheelbase"] / 2.0
    out = []
    for i, (ang, rol) in enumerate([(45, "FL"), (135, "RL"), (225, "RR"), (315, "FR")], start=1):
        x = R * math.cos(math.radians(ang))
        y = R * math.sin(math.radians(ang))
        if p["coaxial"]:
            out.append({"id": f"R{i}_upper", "role": rol, "x": x, "y": y, "z": 0.18})
            out.append({"id": f"R{i}_lower", "role": rol, "x": x, "y": y, "z": -0.02})
        else:
            out.append({"id": f"R{i}", "role": rol, "x": x, "y": y, "z": 0.08})
    return out


def n_rotores(p: dict) -> int:
    return len(rot_centers(p))


def disco(p: dict) -> dict:
    n = n_rotores(p)
    r = p["rotor_d"] / 2
    A = n * math.pi * r ** 2
    return {"n_rotores": n, "r_rotor": r, "A_total": A}


def reparto_empuje(p: dict, masa: float, split: float) -> list[float]:
    """Empuje por disco (N). Coaxial: reparto asimetrico parametrizado; simple: uniforme."""
    T = masa * G
    centros = rot_centers(p)
    if not p["coaxial"]:
        return [T / len(centros)] * len(centros)
    n_brazos = len(centros) // 2
    T_brazo = T / n_brazos
    # split = fraccion del empuje del brazo que va al rotor SUPERIOR
    out = []
    for c in centros:
        out.append(T_brazo * split if c["id"].endswith("upper") else T_brazo * (1 - split))
    return out


# --------------------------------------------------------------------------------------
# DOE POR PLATAFORMA
# --------------------------------------------------------------------------------------
def latin_hypercube(n: int, dims: int, rng: random.Random) -> list[list[float]]:
    """LHS estratificado correcto: una muestra por estrato en cada dimension."""
    cols = []
    for _ in range(dims):
        puntos = [(i + rng.random()) / n for i in range(n)]
        rng.shuffle(puntos)
        cols.append(puntos)
    return [[cols[d][i] for d in range(dims)] for i in range(n)]


def escala(u: float, lo: float, hi: float) -> float:
    return lo + u * (hi - lo)


def build_doe(n_por_plataforma: int, seed: int = 42) -> list[dict]:
    rng = random.Random(seed)
    filas = []
    for clave, p in PLAT.items():
        # 5 dimensiones: V, H, d, carga, split
        muestras = latin_hypercube(n_por_plataforma, 5, rng)
        for i, (uv, uh, ud, uc, us) in enumerate(muestras, start=1):
            V = escala(uv, *p["v_range"])
            H = escala(uh, *p["h_range"])
            d = escala(ud, *p["d_range"])
            f = uc                                 # fraccion de tanque 0..1
            masa = p["m_bat"] + p["tanque"] * f
            # atomizadores: alternar 2/4 de forma balanceada
            atom = 2 if i % 2 else 4
            # split: solo relevante en coaxial; en simple va fijo a 0.5
            split = escala(us, SPLIT_COAXIAL[0], SPLIT_COAXIAL[-1]) if p["coaxial"] else 0.5
            case_id = f"{clave}_V{V:.1f}_H{H:.1f}_d{d:.0f}_f{f:.2f}_a{atom}"
            filas.append({
                "case_id": case_id,
                "plataforma": clave,
                "V_inf_ms": round(V, 3),
                "H_m": round(H, 3),
                "DV05_um": round(d, 1),
                "carga_fraccion": round(f, 4),
                "masa_total_kg": round(masa, 2),
                "atomizadores": atom,
                "split_coaxial_superior": round(split, 3),
                "coaxial": p["coaxial"],
                "fuente_geometria": "P/S/O/I (ver presupuesto_hipotesis.md)",
                "estado": "especificado_no_ejecutado",
            })
    return filas


# --------------------------------------------------------------------------------------
# GENERACION DE CASOS OpenFOAM
# --------------------------------------------------------------------------------------
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


def write_case(case_dir: Path, row: dict, p: dict) -> None:
    """Escribe un caso OpenFOAM completo para actuator disk con empuje prescrito."""
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "system").mkdir(exist_ok=True)
    (case_dir / "constant").mkdir(exist_ok=True)
    (case_dir / "0").mkdir(exist_ok=True)

    H = row["H_m"]
    V = row["V_inf_ms"]
    masa = row["masa_total_kg"]
    split = row["split_coaxial_superior"]
    centros = rot_centers(p)
    empujes = reparto_empuje(p, masa, split)
    d = disco(p)
    r_rot = d["r_rotor"]

    # dominio: el dron en z=0; suelo a -H (altura de aplicacion REAL, no 6 m fijos)
    x0, x1 = -6.0, 14.0
    y0, y1 = -6.0, 6.0
    z0, z1 = -H, 4.0

    # ---- blockMeshDict
    (case_dir / "system" / "blockMeshDict").write_text(
        foam_header("dictionary", "blockMeshDict") + f"""
scale 1;

vertices
(
    ({x0} {y0} {z0})
    ({x1} {y0} {z0})
    ({x1} {y1} {z0})
    ({x0} {y1} {z0})
    ({x0} {y0} {z1})
    ({x1} {y0} {z1})
    ({x1} {y1} {z1})
    ({x0} {y1} {z1})
);

blocks
(
    hex (0 1 2 3 4 5 6 7) (80 48 48) simpleGrading (1 1 1)
);

edges ();

boundary
(
    inlet  {{ type patch; faces ((0 4 7 3)); }}
    outlet {{ type patch; faces ((1 2 6 5)); }}
    sides  {{ type patch; faces ((0 1 5 4) (3 7 6 2)); }}
    top    {{ type patch; faces ((4 5 6 7)); }}
    ground {{ type wall;  faces ((0 3 2 1)); }}
);

mergePatchPairs ();
""", encoding="utf-8")
    # ---- controlDict con extraccion de datos (function objects)
    probe_lines = "\n".join(
        f"        ({c['x']:.4f} {c['y']:.4f} {c['z']:.4f})" for c in centros[:2]
    )
    (case_dir / "system" / "controlDict").write_text(
        foam_header("dictionary", "controlDict") + f"""
application     simpleFoam;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         2000;
deltaT          1;
writeControl    timeStep;
writeInterval   100;
purgeWrite      3;
writeFormat     ascii;
writePrecision  8;
writeCompression off;
timeFormat      general;
timePrecision   6;
runTimeModifiable true;

functions
{{
    // plano receptor a la altura del suelo: D(x,y) se integra aqui
    receptorPlane
    {{
        type            surfaces;
        libs            ("libsampling.so");
        surfaceFormat   raw;
        fields          (U p k omega);
        interpolationScheme cellPoint;
        surfaces
        {{
            ground
            {{
                type        plane;
                planeType   pointAndNormal;
                pointAndNormalDict
                {{
                    point   (0 0 {z0 + 0.01});
                    normal  (0 0 1);
                }}
                triangulate false;
            }}
        }}
    }}

    // lineas verticales: perfil de downwash u(z) bajo cada rotor
    downwashLines
    {{
        type            sets;
        libs            ("libsampling.so");
        writeControl    timeStep;
        writeInterval   100;
        interpolationScheme cellPoint;
        setFormat       raw;
        fields          (U k omega);
        sets
        {{
            line_under_rotor1
            {{
                type        uniform;
                axis        z;
                start       ({centros[0]['x']:.4f} {centros[0]['y']:.4f} {z0 + 0.02});
                end         ({centros[0]['x']:.4f} {centros[0]['y']:.4f} 1.0);
                nPoints     60;
            }}
        }}
    }}

    // residuos y fuerzas en el disco
    forces
    {{
        type            forces;
        libs            ("libforces.so");
        writeControl    timeStep;
        writeInterval   20;
        patches         (ground);
        rho             rhoInf;
        rhoInf          {RHO};
        CofR            (0 0 0);
    }}
}}
""", encoding="utf-8")

    # ---- fvSchemes
    (case_dir / "system" / "fvSchemes").write_text(
        foam_header("dictionary", "fvSchemes") + """
ddtSchemes      { default steadyState; }
gradSchemes     { default Gauss linear; limited cellLimited Gauss linear 1; }
divSchemes
{
    default                         none;
    div(phi,U)                      bounded Gauss linearUpwind grad(U);
    div(phi,k)                      bounded Gauss upwind;
    div(phi,omega)                  bounded Gauss upwind;
    div((nuEff*dev2(T(grad(U)))))   Gauss linear;
}
laplacianSchemes { default Gauss linear limited corrected 0.5; }
interpolationSchemes { default linear; }
snGradSchemes   { default limited corrected 0.5; }
wallDist        { method meshWave; }
""", encoding="utf-8")

    # ---- fvSolution
    (case_dir / "system" / "fvSolution").write_text(
        foam_header("dictionary", "fvSolution") + """
solvers
{
    p
    {
        solver          GAMG;
        tolerance       1e-8;
        relTol          0.01;
        smoother        GaussSeidel;
    }
    "(U|k|omega)"
    {
        solver          smoothSolver;
        smoother        symGaussSeidel;
        tolerance       1e-9;
        relTol          0.01;
    }
}
SIMPLE
{
    nNonOrthogonalCorrectors 2;
    consistent      yes;
    residualControl
    {
        p               1e-5;
        U               1e-6;
        "(k|omega)"     1e-6;
    }
}
relaxationFactors
{
    fields      { p 0.3; }
    equations   { U 0.7; k 0.7; omega 0.7; }
}
""", encoding="utf-8")

    # ---- turbulenceProperties
    (case_dir / "constant" / "turbulenceProperties").write_text(
        foam_header("IOdictionary", "turbulenceProperties") + """
simulationType  RAS;
RAS
{
    model           kOmegaSST;
    turbulence      on;
    printCoeffs     on;
}
""", encoding="utf-8")

    (case_dir / "constant" / "transportProperties").write_text(
        foam_header("IOdictionary", "transportProperties") + f"""
transportModel  Newtonian;
nu              [0 2 -1 0 0 0 0] {NU};
""", encoding="utf-8")

    # ---- condiciones de contorno REALES (con traslacion)
    tint = 0.05   # intensidad turbulenta (numero, no string)
    k_val = 1.5 * (V * tint) ** 2
    omega_val = k_val ** 0.5 / (0.09 ** 0.25 * 0.01)   # l ~ 1 cm
    (case_dir / "0" / "U").write_text(
        foam_header("volVectorField", "U") + f"""
dimensions      [0 1 -1 0 0 0 0];
internalField   uniform ({V} 0 0);
boundaryField
{{
    inlet   {{ type fixedValue;  value uniform ({V} 0 0); }}
    outlet  {{ type inletOutlet; inletValue uniform ({V} 0 0); value uniform ({V} 0 0); }}
    sides   {{ type slip; }}
    top     {{ type slip; }}
    ground  {{ type noSlip; }}
}}
""", encoding="utf-8")

    (case_dir / "0" / "p").write_text(
        foam_header("volScalarField", "p") + """
dimensions      [0 2 -2 0 0 0 0];
internalField   uniform 0;
boundaryField
{
    inlet   { type zeroGradient; }
    outlet  { type fixedValue; value uniform 0; }
    sides   { type zeroGradient; }
    top     { type zeroGradient; }
    ground  { type zeroGradient; }
}
""", encoding="utf-8")

    for fld, val, dims in (("k", k_val, "[0 2 -2 0 0 0 0]"), ("omega", omega_val, "[0 0 -1 0 0 0 0]")):
        (case_dir / "0" / fld).write_text(
            foam_header("volScalarField", fld) + f"""
dimensions      {dims};
internalField   uniform {val:.8g};
boundaryField
{{
    inlet   {{ type fixedValue;  value uniform {val:.8g}; }}
    outlet  {{ type inletOutlet; inletValue uniform {val:.8g}; value uniform {val:.8g}; }}
    sides   {{ type slip; }}
    top     {{ type slip; }}
    ground  {{ type kqRWallFunction; value uniform {val:.8g}; }}
}}
""", encoding="utf-8")

    (case_dir / "0" / "nut").write_text(
        foam_header("volScalarField", "nut") + f"""
dimensions      [0 2 -1 0 0 0 0];
internalField   uniform 0;
boundaryField
{{
    inlet   {{ type calculated; value uniform 0; }}
    outlet  {{ type calculated; value uniform 0; }}
    sides   {{ type calculated; value uniform 0; }}
    top     {{ type calculated; value uniform 0; }}
    ground  {{ type nutkWallFunction; value uniform 0; }}
}}
""", encoding="utf-8")

    # ---- topoSet: una cellZone cilindrica por rotor
    sets = []
    for i, (c, T) in enumerate(zip(centros, empujes), start=1):
        sets.append(f"""    rotor{i}
    {{
        type    cylinderToCell;
        p1      ({c['x']:.4f} {c['y']:.4f} {c['z'] - 0.01:.4f});
        p2      ({c['x']:.4f} {c['y']:.4f} {c['z'] + 0.01:.4f});
        radius  {r_rot:.4f};
        cellZone rotor{i};
    }}""")
    (case_dir / "system" / "topoSetDict").write_text(
        foam_header("dictionary", "topoSetDict") + f"""
actions
(
{chr(10).join(sets)}
);
""", encoding="utf-8")

    # ---- fvOptions: actuationDiskSource por rotor con empuje PRESCRITO
    opts = []
    for i, (c, T) in enumerate(zip(centros, empujes), start=1):
        A_disk = math.pi * r_rot ** 2
        ct = T / (0.5 * RHO * A_disk * 1.0 ** 2)
        opts.append(f"""    rotor{i}
    {{
        type            actuationDiskSource;
        libs            ("libfvOptions.so");
        selectionMode   cellZone;
        cellZone        rotor{i};
        fields          (U);

        // empuje PRESCRITO por disco (arquitectura C -> B)
        // T = {T:.3f} N   masa = {masa:.2f} kg   split = {split:.3f}   rotor = {c['id']}
        // El empuje debe actuar en la direccion del eje del rotor.
        // En vuelo nivelado el disco empuja el aire hacia ABAJO: diskDir = (0 0 -1).
        diskDir         (0 0 -1);
        diskArea        {A_disk:.6f};
        thrustCoeff     constant {ct:.8g};
        writeMultiVal   false;
        U               U;
        Uref            30;
        Cp              constant 0.0;
        Ct              constant {ct:.8g};
    }}""")
    (case_dir / "constant" / "fvOptions").write_text(
        foam_header("dictionary", "fvOptions") + f"""
// Empuje PRESCRITO por disco (arquitectura C -> B de geometry/coaxial_thrust_split.md).
// `diskDir (0 0 -1)`: en vuelo nivelado el rotor empuja el aire hacia abajo.
// El reparto superior/inferior en coaxiales es un PARAMETRO barrido, no una suposicion.
options
(
{chr(10).join(opts)}
);
""", encoding="utf-8")

    # ---- snappyHexMeshDict (mallado del cuerpo, opcional)
    (case_dir / "system" / "snappyHexMeshDict").write_text(
        foam_header("dictionary", "snappyHexMeshDict") + """
castellatedMesh true;
snap            true;
addLayers       true;

geometry
{
    // el cuerpo del dron se malla desde geometry/models/<UAV>_control.stl
    // si el STL no esta, snappyHexMesh no se ejecuta y se corre sobre el blockMesh
}

castellatedMeshControls
{
    maxLocalCells       2000000;
    maxGlobalCells      8000000;
    minRefinementCells  10;
    nCellsBetweenLevels 3;
    features ();
    refinementSurfaces {}
    refinementRegions
    {
        // refinamiento del tubo de estela bajo los rotores
        wake
        {
            mode        inside;
            levels      ((0.0 2));
            // se define en la plantilla con searchableCylinder por rotor
        }
    }
    resolveFeatureAngle 30;
    allowFreeStandingZoneFaces false;
    locationInMesh (3 0 2);
}

snapControls    { nSmoothPatch 3; tolerance 2.0; nSolveIter 100; nRelaxIter 5; }
addLayersControls
{
    relativeSizes true;
    layers {}
    expansionRatio          1.2;
    finalLayerThickness     0.3;
    minThickness            0.1;
    nGrow                   0;
    featureAngle            60;
    nRelaxIter              5;
    nSmoothSurfaceNormals   1;
    nSmoothNormals          3;
    nSmoothThickness        10;
    maxFaceThicknessRatio   0.5;
    maxThicknessToMedialRatio 0.3;
    minMedialAxisAngle      90;
    nBufferCellsNoExtrude   0;
    nLayerIter              50;
}
meshQualityControls
{
    maxNonOrtho 65; maxBoundarySkewness 20; maxInternalSkewness 4;
    maxConcave 80; minVol 1e-13; minTetQuality 1e-30; minArea -1;
    minTwist 0.02; minTriangleTwist -1; minDeterminant 0.001;
    minFaceWeight 0.02; minVolRatio 0.01; nSmoothScale 4; errorReduction 0.75;
}
debug 0;
mergeTolerance 1e-6;
""", encoding="utf-8")

    # ---- ficha del caso (trazabilidad)
    meta = {
        "case_id": row["case_id"],
        "plataforma": row["plataforma"],
        "nombre_plataforma": p["nombre"],
        "arquitectura_cfd": "C (equilibrio fisico) -> B (actuator disk con empuje prescrito)",
        "entradas": {
            "V_inf_ms": row["V_inf_ms"],
            "H_m": row["H_m"],
            "DV05_um": row["DV05_um"],
            "carga_fraccion": row["carga_fraccion"],
            "masa_total_kg": row["masa_total_kg"],
            "atomizadores": row["atomizadores"],
            "split_coaxial_superior": row["split_coaxial_superior"],
        },
        "derivados_analiticos": {
            "n_rotores_modelados": d["n_rotores"],
            "r_rotor_m": round(r_rot, 4),
            "area_disco_total_m2": round(d["A_total"], 4),
            "empuje_total_N": round(masa * G, 2),
            "empuje_por_disco_N": {c["id"]: round(T, 2) for c, T in zip(centros, empujes)},
            "v_inducida_hover_ms": round(math.sqrt(masa * G / (2 * RHO * d["A_total"])), 3),
        },
        "dominio": {"x": [x0, x1], "y": [y0, y1], "z": [z0, z1], "nota": "suelo a -H (altura real)"},
        "propiedades_fluido": {"rho": RHO, "nu": NU, "p_atm": P_ATM,
                               "agua_rho": RHO_W, "agua_mu": MU_W, "agua_sigma": SIGMA_W},
        "clasificacion_geometria": "P/S/O/I — NO M. Ver geometry/presupuesto_hipotesis.md",
        "estado": "generado_no_ejecutado",
        "no_contiene": "ningun resultado de CFD: este archivo describe el caso, no su salida",
    }
    (case_dir / "case_meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")


# --------------------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/processed")
    ap.add_argument("--cfd", default="cfd/cases")
    ap.add_argument("--n", type=int, default=32, help="casos por plataforma")
    ap.add_argument("--no-cases", action="store_true", help="solo el DOE, sin escribir casos")
    a = ap.parse_args()

    out = ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)

    filas = build_doe(a.n)
    doe_path = out / "doe_by_platform.csv"
    with doe_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0].keys()))
        w.writeheader()
        w.writerows(filas)
    print(f"DOE por plataforma -> {doe_path.relative_to(ROOT)}  ({len(filas)} casos)")

    # resumen por plataforma
    print(f"\n  {'plataforma':10s} {'casos':>6s} {'V (m/s)':>14s} {'H (m)':>12s} "
          f"{'d (um)':>13s} {'masa (kg)':>16s} {'rotores':>8s} {'A_disco':>9s}")
    for clave, p in PLAT.items():
        sub = [f for f in filas if f["plataforma"] == clave]
        d = disco(p)
        print(f"  {clave:10s} {len(sub):6d} "
              f"{min(f['V_inf_ms'] for f in sub):6.1f}-{max(f['V_inf_ms'] for f in sub):<7.1f} "
              f"{min(f['H_m'] for f in sub):5.1f}-{max(f['H_m'] for f in sub):<6.1f} "
              f"{min(f['DV05_um'] for f in sub):5.0f}-{max(f['DV05_um'] for f in sub):<7.0f} "
              f"{min(f['masa_total_kg'] for f in sub):6.1f}-{max(f['masa_total_kg'] for f in sub):<9.1f} "
              f"{d['n_rotores']:8d} {d['A_total']:9.3f}")

    if not a.no_cases:
        casos_dir = ROOT / a.cfd
        n_escritos = 0
        for row in filas:
            p = PLAT[row["plataforma"]]
            write_case(casos_dir / row["case_id"], row, p)
            n_escritos += 1
        print(f"\ncasos OpenFOAM escritos: {n_escritos} en {casos_dir.relative_to(ROOT)}/")

    print("\nREGLA: esto son CASOS, no resultados. Ningun campo de salida de CFD se ha")
    print("inventado. Para poblarlos hace falta ejecutar OpenFOAM (no disponible aqui).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
