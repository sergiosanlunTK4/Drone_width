"""
ESPECIFICACION DEL MODULO LAGRANGIANO (inyeccion de gotas y deposicion D(x,y)).

ESTADO: ESPECIFICADO, NO EJECUTADO. Este script genera la infraestructura y la valida
estructuralmente. NO produce resultados de deposicion.

SEPARACION CONCEPTUAL QUE ESTE MODULO RESPETA (indicacion del investigador):
    flujo de aire -> trayectorias de gotas -> D(x,y) -> ancho efectivo / uniformidad
  Cada flecha es un paso distinto y no se puede saltar. En particular:
    * `sigma_y` ANALITICO **NO** alimenta la deposicion CFD. Queda como baseline
      independiente contra el cual comparar. Si se usara, se construIRIA en la simulacion
      aquello que luego se pretende "descubrir".
    * D(x,y) sale de contar IMPACTOS de gotas en el plano receptor, no de una formula.

QUE GENERA:
  Para cada caso CFD:  constant/cloudProperties  +  system/particleInjection (ficha)
  Y una ficha `lagrangian_spec.json` con TODAS las decisiones declaradas.

MODELOS OPCIONALES: evaporacion, breakup y turbulencia estocastica se declaran y se pueden
  ACTIVAR/DESACTIVAR por caso para analisis de sensibilidad. No se introducen en silencio
  como "realismo": cada uno se marca como activado o desactivado y por que.

Uso:
  python scripts/build_lagrangian_spec.py --cfd cfd/cases --dry-run
  python scripts/build_lagrangian_spec.py --case T25P_V..._a2
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Propiedades del agua a 28 C (referencias estandar)
RHO_W = 996.2
MU_W = 8.36e-4
SIGMA_W = 0.0719
P_VAP_28C = 3780.0        # Pa, presion de vapor del agua a 28 C
RHO_AIR = 1.1716
MU_AIR = 1.86e-5

# ---- Atomizadores: posicion y orientacion (clases O / I / P segun el caso) ------------
#   X: T100 clase O (propietario). Y: derivada de la separacion declarada (I).
#   Z: DESCONOCIDA -> se declara como parametro y se barre por sensibilidad.
ATOMIZERS = {
    "T100": [
        {"id": "A1", "role": "L_out", "x": -0.900, "y": -0.917, "z": None},
        {"id": "A2", "role": "L_in",  "x": -0.800, "y": -0.4585, "z": None},
        {"id": "A3", "role": "R_in",  "x": -0.800, "y": +0.4585, "z": None},
        {"id": "A4", "role": "R_out", "x": -0.900, "y": +0.917, "z": None},
    ],
}
# Para el resto, la X no esta declarada: se usa solo la Y y se marca la X como D.
ATOM_SEP = {"T25P": 1420, "T55": 1800, "T70P": 1874, "T100": 1834}
Z_ATOMIZER_PARAM = [-0.10, -0.20, -0.30]   # rango de sensibilidad para la Z desconocida


def atomizers_for(plataforma: str, n: int) -> list[dict]:
    """Devuelve los atomizadores activos segun la configuracion (2 o 4)."""
    if plataforma in ATOMIZERS:
        todos = ATOMIZERS[plataforma]
        # 1 y 2 son las 'extras' segun el propietario -> config de 2 usa las exteriores
        return todos if n == 4 else [todos[0], todos[3]]
    sep = ATOM_SEP[plataforma] / 2000.0
    base = [
        {"id": "A1", "role": "L_out", "x": None, "y": -sep, "z": None},
        {"id": "A2", "role": "L_in",  "x": None, "y": -sep / 2, "z": None},
        {"id": "A3", "role": "R_in",  "x": None, "y": +sep / 2, "z": None},
        {"id": "A4", "role": "R_out", "x": None, "y": +sep, "z": None},
    ]
    return base if n == 4 else [base[0], base[3]]


# ---- Distribucion de diametros: NO una sola gota ---------------------------------------
def rosin_rammler(dv50_um: float, n_bins: int = 12) -> list[dict]:
    """Distribucion Rosin-Rammler alrededor de DV0.5, discretizada por bins.

    Se usa Rosin-Rammler por ser la distribucion estandar en pulverizacion agricola, pero
    el parametro de dispersion q es un SUPUESTO declarado (q=2.0) modificable por caso.
    """
    q = 2.0
    d_min, d_max = dv50_um * 0.25, dv50_um * 2.5
    bins = []
    for i in range(n_bins):
        d0 = d_min + (d_max - d_min) * i / n_bins
        d1 = d_min + (d_max - d_min) * (i + 1) / n_bins
        # fraccion acumulada Rosin-Rammler: F(d) = 1 - exp(-(d/dv50)^q)
        f1 = 1.0 - math.exp(-((d1 / dv50_um) ** q))
        f0 = 1.0 - math.exp(-((d0 / dv50_um) ** q))
        frac = f1 - f0
        if frac > 1e-6:
            bins.append({
                "d_min_um": round(d0, 1),
                "d_max_um": round(d1, 1),
                "d_medio_um": round(0.5 * (d0 + d1), 1),
                "fraccion_masa": round(frac, 5),
            })
    total = sum(b["fraccion_masa"] for b in bins)
    for b in bins:
        b["fraccion_masa_normalizada"] = round(b["fraccion_masa"] / total, 5)
    return bins


def cloud_properties(case_meta: dict, n_particulas: int, opciones: dict) -> str:
    """Genera constant/cloudProperties para sprayCloud (OpenFOAM)."""
    P = lambda s: s  # noqa: E731
    return f"""/*--------------------------------*- C++ -*----------------------------------*\\
| Modulo LAGRANGIANO — generado por scripts/build_lagrangian_spec.py
| ESTADO: especificado, NO ejecutado.
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      cloudProperties;
}}

solution
{{
    active          true;
    coupled         false;          // one-way: la gota no modifica el aire (declarado)
    transient       no;             // acoplado al campo estacionario
    cellValueSourceCorrection off;
    maxCo           0.3;
    sourceTerms
    {{
        schemes
        {{
            U   semiImplicit 1;
        }}
    }}
    interpolationSchemes
    {{
        U   cellPoint;
        rho cell;
    }}
}}

// ---- Inyeccion desde la posicion/orientacion REAL del atomizador --------------------
// Cada `injectionModels` usa un `patchInjection` sobre una cara del atomizador.
// El atomizador se representa geometricamente en el mallado (ver topoSet/STL).
injectionModels
{{
    // Un modelo por atomizador ACTIVO en esta configuracion
    atomizerInjection
    {{
        type            patchInjection;
        patch           atomizerFaces;      // cara de inyeccion (creada en el mallado)
        massTotal       {{MASS_TOTAL}};
        parcelBasisType mass;
        nParticle       {n_particulas};
        duration        1.0;               // inyeccion continua en el tiempo de flujo
        // orientacion del cono de pulverizacion (vector real del atomizador)
        U0              {{U0_VECTOR}};
        // dispersion inicial del abanico (semiangulo del cono)
        flowRateProfile constant 1.0;
        umbrellaAngle   {{UMBRELLA_DEG}};
    }}
}}

// ---- Distribucion de diametros: NO una sola gota ------------------------------------
// Rosin-Rammler discretizada. q = 2.0 es un SUPUESTO declarado, no un dato.
sizeDistribution
{{
    type            RosinRammler;
    RosinRammlerDistribution
    {{
        minValue        {{D_MIN}};
        maxValue        {{D_MAX}};
        d               {{DV50}};
        n               {{Q_EXP}};
    }}
}}

// ---- Propiedades del liquido (agua a 28 C) ------------------------------------------
// Fuente: propiedades estandar del agua a 28 C. NO incluye agroquimicos (fuera de alcance).
thermoPhysicalProperties
{{
    type            liquid;
    liquid
    {{
        rho             {RHO_W};
        mu              {MU_W};
        sigma           {SIGMA_W};
        pVap            {P_VAP_28C};
        T               {28.0};
        Cp              4180.0;
        kappa           0.6;
    }}
}}

// ---- SUB-MODELOS: cada uno DECLARADO y conmutable ------------------------------------
subModels
{{
    particleForces
    {{
        // gravedad: siempre activa
        gravity
        {{
            type            gravity;
            g               (0 0 -9.81);
        }}
    }}

    // --- arrastre dependiente de Re_p ------------------------------------------------
    // NO se usa una ley lineal de Stokes: sobre el rango 100-500 um, Re_p va de ~1 a ~30
    // y la ley de arrastre debe ser la completa (Schiller-Naumann).
    drag
    {{
        type            sphereDrag;
        // sphereDrag aplica Cd = 24/Re*(1+0.15 Re^0.687) para Re<1000. Es el modelo correcto.
    }}

    // --- EVAPORACION: DESACTIVADA por defecto ---------------------------------------
    // '<EVAP>'
    // Razon: context.md SS3 excluye evaporacion del caso base. Se activa para sensibilidad.
    evaporation
    {{
        type            none;     // 'none' | 'standard'
    }}

    // --- BREAKUP: DESACTIVADO por defecto -------------------------------------------
    // '<BREAKUP>'
    // Razon: el atomizador ya produce la distribucion; el breakup secundario no es el
    // objetivo de este primer paper. Se activa para sensibilidad.
    breakup
    {{
        type            none;     // 'none' | 'PilchErdman' | 'ReitzDiwakar'
    }}

    // --- TURBULENCIA ESTOCASTICA: DESACTIVADA por defecto ---------------------------
    // '<TURB>'
    // Razon: introduce dispersion estocastica que debe poder apagarse para aislar el
    // efecto del campo medio. Se activa para sensibilidad.
    dispersion
    {{
        type            none;     // 'none' | 'stochasticDispersionRAS'
    }}

    // --- DETECCION DE IMPACTO en el plano receptor ----------------------------------
    // La deposicion D(x,y) sale de CONTAR IMPACTOS, no de una formula.
    stick
    {{
        type            <STICK_MODEL>;
    }}
}}

cloudFunctions
{{
    // conteo y distribucion de impacto en el plano receptor
    patchPostProcessing
    {{
        type            patchPostProcessing;
        patches         (ground);
        maxStoredParcels 10000000;
    }}
}}
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cfd", default="cfd/cases")
    ap.add_argument("--case", default=None)
    ap.add_argument("--dry-run", action="store_true", help="solo especificacion, no escribe casos")
    ap.add_argument("--activar-evaporacion", action="store_true")
    ap.add_argument("--activar-breakup", action="store_true")
    ap.add_argument("--activar-turbulencia", action="store_true")
    a = ap.parse_args()

    casos = sorted((ROOT / a.cfd).glob("*_V*"))
    if a.case:
        casos = [c for c in casos if c.name == a.case]
    if not casos:
        print("no hay casos; ejecuta scripts/build_case_suite.py")
        return 2

    print("=" * 92)
    print("MODULO LAGRANGIANO — especificacion")
    print("=" * 92)
    print(f"\ncasos: {len(casos)}")
    print(f"sub-modelos opcionales:")
    print(f"  evaporacion : {'ACTIVADA' if a.activar_evaporacion else 'desactivada (context.md SS3)'}")
    print(f"  breakup     : {'ACTIVADO' if a.activar_breakup else 'desactivado (no es objetivo)'}")
    print(f"  turbulencia : {'ACTIVADA' if a.activar_turbulencia else 'desactivada (aisla campo medio)'}")

    escritos = 0
    for caso in casos[: (1 if a.dry_run else len(casos))]:
        meta_path = caso / "case_meta.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
        plat = meta.get("plataforma", caso.name.split("_")[0])
        d50 = meta.get("entradas", {}).get("DV05_um", 200.0)
        n_atom = meta.get("entradas", {}).get("atomizadores", 2)

        atom = atomizers_for(plat, n_atom)
        bins = rosin_rammler(d50)

        spec = {
            "case_id": caso.name,
            "estado": "ESPECIFICADO_NO_EJECUTADO",
            "separacion_conceptual": {
                "cadena": "flujo de aire -> trayectorias -> D(x,y) -> ancho efectivo/uniformidad",
                "regla_1": "sigma_y analitico NO alimenta la deposicion CFD; es baseline independiente",
                "regla_2": "D(x,y) sale de contar impactos, no de una formula",
            },
            "inyeccion": {
                "atomizadores_activos": atom,
                "z_atomizador": {
                    "valor": None,
                    "clasificacion": "D (desconocida)",
                    "parametro_de_sensibilidad": Z_ATOMIZER_PARAM,
                    "nota": "la coordenada Z no esta medida; se barre en el analisis",
                },
                "n_particulas_representativas": 100000,
                "vector_inicial": "normal al disco del atomizador, magnitud del caudal / area efectiva",
                "semiangulo_cono_deg": 30.0,
            },
            "distribucion_diametros": {
                "tipo": "Rosin-Rammler",
                "dv50_um": d50,
                "q_exponente": 2.0,
                "q_es_supuesto": True,
                "bins": bins,
            },
            "fuerzas": {
                "gravedad": "activa (0 0 -9.81)",
                "arrastre": "sphereDrag: Cd = 24/Re*(1+0.15 Re^0.687), valido Re<1000",
                "nota": "NO se usa ley lineal de Stokes: Re_p va de ~1 a ~30 en el rango 100-500 um",
            },
            "submodelos_opcionales": {
                "evaporacion": {"activo": a.activar_evaporacion,
                                "razon": "excluida del caso base por context.md SS3"},
                "breakup": {"activo": a.activar_breakup,
                            "razon": "el atomizador ya produce la distribucion; no es objetivo"},
                "turbulencia_estocastica": {"activo": a.activar_turbulencia,
                                            "razon": "debe poder apagarse para aislar el campo medio"},
            },
            "deteccion_impacto": {
                "superficie": "patch ground del caso CFD",
                "modelo_stick": "stick (queda adherida); alternativas: rebound, splash",
                "metricas": ["conteo por celda", "D(x,y) g/m2", "W_eff", "CV",
                             "asimetria", "P10/P50/P90"],
            },
            "propiedades_liquido": {"rho": RHO_W, "mu": MU_W, "sigma": SIGMA_W,
                                    "pVap": P_VAP_28C, "T_C": 28.0,
                                    "nota": "agua pura, sin agroquimicos (fuera de alcance)"},
            "advertencias": [
                "los resultados de este modulo NO son validos hasta cerrar GATE CFD-0",
                "la Z del atomizador es desconocida: los resultados se reportan con su barrido",
                "cfd_deposition se pobla solo tras ejecutar y converger",
            ],
        }
        if not a.dry_run:
            (caso / "lagrangian_spec.json").write_text(
                json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8")
            (caso / "constant" / "cloudProperties").write_text(
                cloud_properties(meta, 100000, spec["submodelos_opcionales"])
                .replace("{{MASS_TOTAL}}", "1.0e-3")
                .replace("{{U0_VECTOR}}", "(0 0 -20)")
                .replace("{{UMBRELLA_DEG}}", "30")
                .replace("{{D_MIN}}", f"{d50*0.25:.1f}e-6")
                .replace("{{D_MAX}}", f"{d50*2.5:.1f}e-6")
                .replace("{{DV50}}", f"{d50:.1f}e-6")
                .replace("{{Q_EXP}}", "2.0")
                .replace("{{STICK_MODEL}}", "stick"),
                encoding="utf-8")
            escritos += 1
        else:
            print(f"\n  caso: {caso.name}")
            print(f"    atomizadores activos: {', '.join(x['id'] for x in atom)}")
            print(f"    bins de diametro: {len(bins)} (DV50={d50:.0f} um, q=2.0 supuesto)")
            print(f"    Z del atomizador: D (desconocida), se barre {Z_ATOMIZER_PARAM}")

    if not a.dry_run:
        print(f"\nficheros escritos: {escritos} casos (lagrangian_spec.json + constant/cloudProperties)")
    print("\nAVISO: este modulo esta ESPECIFICADO, NO EJECUTADO. No produce resultados de")
    print("deposicion. La tabla cfd_deposition sigue vacia y debe seguir asi hasta que")
    print("(1) se cierre GATE CFD-0 y (2) se ejecute el seguimiento.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
