#!/usr/bin/env python3
"""Construye el caso de HOVER: la prueba discriminante de GATE CFD-0.

Por que hover y no el caso nominal
----------------------------------
El fallo de `actuationDiskSource` era `T = 2 rho A |U_o.n|^2 a(1-a)`: con flujo perpendicular
al disco, `T ~ 0`. Las dos medidas que lo demuestran son

    flujo horizontal (caso nominal)  ->  Uz ~ 1e-7 m/s   (nulo)
    flujo vertical   (test axial)    ->  Uz = -0.289 m/s

Pero el caso FISICO de este proyecto es hover o vuelo nivelado, donde el disco GENERA el
flujo y no lo recibe. Con la fuente de momento prescrita, el caso decisivo es `U_inf = 0`:

    si con flujo incidente NULO sigue apareciendo downwash,
    entonces la fuerza NO depende del flujo  ->  la fuente implementa C -> B.

Es la misma logica que la prueba axial, aplicada al caso peor. Si este caso da downwash,
`actuationDiskSource` no puede replicarlo y la sustitucion queda justificada con evidencia.

Que cambia respecto del caso base
---------------------------------
Solo las condiciones de contorno, mas function objects de verificacion. **La malla,
`constant/fvOptions` y `constant/rotorZoneVolumes` se COPIAN intactos**, de modo que la
prueba mide el efecto de la fuente y nada mas.

Condiciones de contorno, y por que son estas
--------------------------------------------
    U:  inlet, outlet, sides, top -> `slip`      (paredes no penetrables)
        ground                     -> `noSlip`   (se conserva: el suelo importa para D(x,y))
    p:  top                        -> `fixedValue 0`   (unica salida de presion)
        resto                      -> `zeroGradient`

**Un primer intento fallo y conviene dejar constancia de por que.** Se pusieron `inlet` y
`outlet` como `inletOutlet` con `p = 0` en ambos. Resultado medido tras 286 iteraciones:

    Ux: min = -20.5   max = +37.4   MEDIA = +13.1 m/s      <- flujo de canal espurio

Con dos parches de presion fija enfrentados en x, el dominio admite un caudal de paso
arbitrario; la fuente de momento lo arrastra y el resultado es un canal, no un hover. La
media de `Ux` deberia ser 0 por simetria y era 13 m/s: el caso estaba mal planteado, no mal
resuelto, y por eso se descarta en lugar de ajustarlo.

La configuracion corregida cierra el dominio en x e y con paredes slip (preservando la
simetria que el canal rompia) y deja **una sola** salida de presion en el techo. El aire que
el disco empuja hacia abajo sale por arriba y la recirculacion se cierra sola. No hay par de
parches enfrentados y por tanto no hay direccion privilegiada.

Uso
---
    # Orden correcto en tres pasos. El orden IMPORTA:
    #   1. copiar desde el caso base (trae malla del caso base, asimetrica)
    python scripts/build_hover_case.py
    #   2. remallar el dominio simetrico (rehace malla, cellZones, V_zone y la fuente)
    python3 scripts/foam_run.py bash scripts/remesh_hover_symmetric.sh
    #   3. parchear las BC SIN recopiar, para no perder el remallado
    python scripts/build_hover_case.py --no-copy

    # Sin el paso --no-copy, el paso 3 restauraria la malla asimetrica del caso base: el
    # `copytree` sobrescribe todo el arbol, incluido `system/blockMeshDict`.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

CASES = ROOT / "cfd" / "cases"
CASO_NOMINAL = "T25P_V3.1_H2.8_d190_f0.95_a4"
SUFIJO = "_HOVER_U0"

from build_case_suite import PLAT, rot_centers  # noqa: E402


def centros_plataforma(meta: dict) -> list:
    """Centros de rotor (x, y, z) de la plataforma del caso."""
    clave = meta.get("plataforma")
    if clave not in PLAT:
        raise KeyError(f"plataforma desconocida: {clave!r}")
    return [(c["x"], c["y"], c["z"]) for c in rot_centers(PLAT[clave])]


def zonas_y_empujes(meta: dict) -> dict:
    """{nombre_de_zona: T_i (N)} en el MISMO orden en que se generaron las cellZone."""
    der = meta.get("derivados_analiticos", {})
    por_disco = der.get("empuje_por_disco_N", {})
    if not por_disco:
        return {}
    return {f"rotor{i+1}": float(v) for i, v in enumerate(por_disco.values())}


# ---------------------------------------------------------------------------------------
# parcheo de los campos
# ---------------------------------------------------------------------------------------
def campo_U_hover(texto: str) -> str:
    """Dominio cerrado y en reposo: todo slip salvo el suelo, que sigue noSlip.

    Se usa `slip` en lugar de `inletOutlet` a proposito: un par de parches con velocidad
    libre enfrentados admite un caudal de paso arbitrario y produce un flujo de canal. Con
    paredes slip y una unica salida de presion en el techo, el unico flujo posible es el que
    genera la fuente.
    """
    t = re.sub(r"internalField\s+uniform\s*\([^)]*\)",
               "internalField   uniform (0 0 0)", texto)
    for parche in ("inlet", "outlet", "sides", "top"):
        t = re.sub(rf"{parche}\s*\{{[^}}]*\}}", f"{parche}   {{ type slip; }}", t)
    t = re.sub(r"ground\s*\{[^}]*\}", "ground  { type noSlip; }", t)
    return t


def campo_p_hover(texto: str) -> str:
    """Una UNICA salida de presion, en el techo.

    Dos parches de presion fija enfrentados (inlet/outlet) crean el flujo de canal descrito
    en el docstring del modulo. Con el techo como unica referencia, la presion queda anclada
    una sola vez y no hay direccion privilegiada.
    """
    t = re.sub(r"inlet\s*\{[^}]*\}", "inlet   { type zeroGradient; }", texto)
    t = re.sub(r"outlet\s*\{[^}]*\}", "outlet  { type zeroGradient; }", texto)
    t = re.sub(r"top\s*\{[^}]*\}", "top     { type fixedValue; value uniform 0; }", t)
    return t


CONTROLDICT_BASE = """/*--------------------------------*- C++ -*----------------------------------*\\
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
    class       dictionary;
    object      controlDict;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

application     simpleFoam;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         {endTime};
deltaT          1;
writeControl    timeStep;
writeInterval   {writeInterval};
purgeWrite      0;
writeFormat     ascii;
writePrecision  8;
writeCompression off;
timeFormat      general;
timePrecision   6;
runTimeModifiable true;
"""


def escribir_controlDict(destino: Path, z_suelo: float, centros: list, zonas: dict,
                         end_time: int = 2000, write_interval: int = 100) -> None:
    """REGENERA `system/controlDict` completo a partir de la plantilla base.

    Por que se regenera y no se parchea. Se intento dos veces parchear el fichero
    existente y las dos fallo, por la misma razon de fondo: manipular texto con llaves
    anidadas es fragil.

      1. Insertar antes de `rfind("}")` metia las funciones dentro de otro bloque y al
         reejecutar dejaba las de la ejecucion anterior:
             Entry 'writeFields' not found in .../functions/momInlet
      2. Reemplazar el intervalo [inicio, cierre] del bloque `functions` dejaba el fichero
         DESBALANCEADO en la segunda pasada:
             Unexpected EOF while reading dictionary entry

    Regenerar elimina la clase entera de fallo: el resultado no depende del estado previo
    del fichero, es balanceado por construccion y es reproducible.
    """
    texto = CONTROLDICT_BASE.format(endTime=end_time, writeInterval=write_interval)
    texto += anadir_funciones(z_suelo, centros, zonas)
    (destino / "system" / "controlDict").write_text(texto, encoding="utf-8")


def _fin_bloque_functions(texto: str) -> int | None:
    """Indice del `}` que cierra el diccionario `functions` (contador de profundidad)."""
    marca = texto.find("functions")
    if marca < 0:
        return None
    abre = texto.find("{", marca)
    if abre < 0:
        return None
    prof, i, n = 0, abre, len(texto)
    en_cadena = False
    while i < n:
        c = texto[i]
        if c == '"':
            en_cadena = not en_cadena
        elif not en_cadena:
            if c == "{":
                prof += 1
            elif c == "}":
                prof -= 1
                if prof == 0:
                    return i
        i += 1
    return None


def anadir_funciones(z_suelo: float, centros: list, zonas: dict) -> str:
    """Genera el bloque `functions` completo, como texto, con llaves balanceadas."""
    lineas = [
        "",
        "functions",
        "{",
        "    // ------------------------------------------------------------------",
        "    // VERIFICACION GATE CFD-0  -  generado por scripts/build_hover_case.py",
        "    // Este controlDict se REGENERA entero en cada ejecucion; no se parchea.",
        "    // ------------------------------------------------------------------",
        "",
        "    // Integral volumetrica de U sobre cada cellZone de rotor.",
        "    //",
        "    // Que comprueba y que NO comprueba, dicho sin ambiguedad:",
        "    //   - SI: que existe flujo atravesando la zona del disco, y su magnitud.",
        "    //   - NO: no mide la fuerza. La fuerza aplicada se verifica en el lado Python con",
        "    //     `Su * V_zone`, porque Su no es un campo que OpenFOAM escriba.",
        "    //     Ver scripts/verify_prescribed_force.py.",
    ]
    for zona, T in zonas.items():
        lineas += [
            f"    flujo_{zona}   // T_i prescrito = {T:.4f} N",
            "    {",
            "        type            volFieldValue;",
            "        libs            (\"libfieldFunctionObjects.so\");",
            "        writeFields     false;",
            "        regionType      cellZone;",
            f"        name            {zona};",
            "        operation       volIntegrate;",
            "        fields          (U);",
            "    }",
            "",
        ]

    lineas += [
        "    // Perfil vertical de downwash en el eje de cada rotor.",
        "    // El suelo esta en z = z_suelo y el dron en z = 0.",
        "    downwashRotor",
        "    {",
        "        type            sets;",
        "        libs            (\"libsampling.so\");",
        "        writeControl    writeTime;",
        "        interpolationScheme cellPoint;",
        "        setFormat       raw;",
        "        fields          (U);",
        "        sets",
        "        {",
    ]
    for i, (x, y, _) in enumerate(centros, start=1):
        lineas += [
            f"            eje_rotor{i}",
            "            {",
            "                type        uniform;",
            "                axis        z;",
            f"                start       ({x:.6f} {y:.6f} {z_suelo:.6f});",
            f"                end         ({x:.6f} {y:.6f} 0.500000);",
            "                nPoints     80;",
            "            }",
        ]
    lineas += ["        }", "    }"]

    # --- convergencia de MAGNITUDES FISICAS, no solo de residuos ----------------
    # Condicion 3 de GATE CFD-0: los residuos pueden bajar mientras las magnitudes siguen
    # derivando. Estas integrales permiten verlo. Sin ellas no hay forma de saber si la
    # corrida convergio de verdad.
    lineas += [
        "",
        "    // --- convergencia de magnitudes fisicas (GATE CFD-0) ---",
        "",
        "    // Caudal volumetrico NETO en cada parche abierto. Con todos los parches cerrados",
        "    // debe ser ~0; si no lo es, hay un problema de conservacion.",
        "    masaInlet  { type surfaceFieldValue; libs (\"libfieldFunctionObjects.so\");",
        "                 writeFields false;",
        "                 regionType patch; name inlet; operation sum;",
        "                 fields (phi); }",
        "    masaOutlet { type surfaceFieldValue; libs (\"libfieldFunctionObjects.so\");",
        "                 writeFields false;",
        "                 regionType patch; name outlet; operation sum;",
        "                 fields (phi); }",
        "",
        "    // Presion integrada sobre las fronteras: es el termino que cierra el balance",
        "    // global de momento. En estado estacionario F_suelo debe valer +T (el chorro",
        "    // empuja el aire hacia abajo y el suelo reacciona).",
        "    pSuelo     { type surfaceFieldValue; libs (\"libfieldFunctionObjects.so\");",
        "                 writeFields false;",
        "                 regionType patch; name ground; operation areaIntegrate;",
        "                 fields (p); }",
        "    pTecho     { type surfaceFieldValue; libs (\"libfieldFunctionObjects.so\");",
        "                 writeFields false;",
        "                 regionType patch; name top; operation areaIntegrate;",
        "                 fields (p); }",
        "",
        "    // Integral de U sobre las zonas de rotor: si deriva, no hay convergencia de",
        "    // magnitudes aunque los residuos bajen.",
        "    uDom       { type volFieldValue; libs (\"libfieldFunctionObjects.so\");",
        "                 writeFields false;",
        "                 regionType all; operation volIntegrate; fields (U); }",
        "}",
    ]
    return "\n".join(lineas) + "\n"


# ---------------------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="origen", default=CASO_NOMINAL)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--no-copy", action="store_true",
                    help="no recopiar el caso base: parchear el caso existente. Necesario "
                         "cuando el caso ya fue remallado (p.ej. dominio simetrico), porque "
                         "recopiar restauraria la malla del caso base y borraria el remallado.")
    args = ap.parse_args()

    if args.list:
        for d in sorted(p.name for p in CASES.iterdir() if p.is_dir()):
            print(d)
        return 0

    base = CASES / args.origen
    if not base.is_dir():
        print(f"no existe el caso base: {base}")
        return 1

    destino = CASES / (args.origen + SUFIJO)
    if args.no_copy:
        if not destino.is_dir():
            print(f"[FALLO] --no-copy pero no existe el caso destino: {destino}")
            return 1
        print("  [modo] --no-copy: se conserva la malla y la fuente del caso existente")
    else:
        if destino.exists():
            shutil.rmtree(destino)
        shutil.copytree(base, destino)

    meta = json.loads((destino / "case_meta.json").read_text(encoding="utf-8"))
    centros = centros_plataforma(meta)
    zonas = zonas_y_empujes(meta)

    # --- 1. U a cero --------------------------------------------------------------
    fU = destino / "0" / "U"
    fU.write_text(campo_U_hover(fU.read_text(encoding="utf-8")), encoding="utf-8")

    # --- 2. p con salida tambien en inlet -----------------------------------------
    fp = destino / "0" / "p"
    fp.write_text(campo_p_hover(fp.read_text(encoding="utf-8")), encoding="utf-8")

    # --- 3. quitar tiempos anteriores (se recalcularan) ---------------------------
    for d in sorted(destino.iterdir()):
        if d.is_dir() and d.name.replace(".", "").isdigit() and d.name != "0":
            shutil.rmtree(d)
    for d in ("postProcessing",):
        if (destino / d).exists():
            shutil.rmtree(destino / d)
    for lg in destino.glob("log.*"):
        lg.unlink()

    # --- 4. controlDict regenerado con los function objects de verificacion -------
    # La altura del suelo se toma del caso base, no se inventa.
    puntos = re.findall(r"\(\s*[-0-9.eE]+\s+[-0-9.eE]+\s+([-0-9.eE]+)\s*\)",
                        (destino / "system" / "blockMeshDict").read_text(encoding="utf-8"))
    z_suelo = float(puntos[0]) if puntos else -3.0
    escribir_controlDict(destino, z_suelo, centros, zonas)

    # --- 5. ficha del caso --------------------------------------------------------
    meta["case_id"] = destino.name
    meta["entradas"]["V_inf_ms"] = 0.0
    meta["proposito"] = (
        "PRUEBA DISCRIMINANTE DE GATE CFD-0. U_inf = 0 (hover puro). Con la fuente de momento "
        "prescrita debe aparecer downwash. actuationDiskSource daba T ~ 0 en esta "
        "configuracion (medido: Uz ~ 1e-7 m/s) y por tanto no puede reproducir este caso. Si "
        "aqui hay downwash, la fuerza no depende del flujo incidente y C -> B esta "
        "implementada."
    )
    meta["no_contiene"] = ("ningun resultado de CFD: es la configuracion del caso, no su "
                           "salida")
    meta["derivado_de"] = args.origen
    (destino / "case_meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # --- 6. comprobaciones de la propia generacion --------------------------------
    problemas = []
    fu = fU.read_text(encoding="utf-8")
    if "internalField   uniform (0 0 0)" not in fu:
        problemas.append("internalField de U no quedo a cero")
    if re.search(r"uniform\s*\(\s*3\.\d", fu):
        problemas.append("U conserva el valor de vuelo")
    if fu.count("type slip") < 4:
        problemas.append("U: no todos los parches cerrados son slip "
                         "(riesgo de flujo de canal)")
    if "type noSlip" not in fu:
        problemas.append("U: el suelo perdio noSlip")
    fp_txt = fp.read_text(encoding="utf-8")
    if fp_txt.count("fixedValue") != 1:
        problemas.append(f"p: hay {fp_txt.count('fixedValue')} salidas de presion, "
                         f"se exige exactamente 1 (mas de una crea flujo de canal)")
    if not (destino / "constant" / "fvOptions").exists():
        problemas.append("falta constant/fvOptions (la fuente prescrita)")
    if not (destino / "constant" / "rotorZoneVolumes").exists():
        problemas.append("falta constant/rotorZoneVolumes")
    if not (destino / "constant" / "polyMesh" / "cellZones").exists():
        problemas.append("falta la malla o las cellZones")
    if not zonas:
        problemas.append("no se pudieron leer los empujes por disco del case_meta.json")

    print("=" * 100)
    print("CASO DE HOVER  -  prueba discriminante de GATE CFD-0")
    print("=" * 100)
    print(f"  base    : {args.origen}")
    print(f"  destino : {destino.name}")
    print(f"  suelo   : z = {z_suelo:.6f} m  (el dron esta en z = 0)")
    print(f"  rotores : {len(centros)}")
    print(f"  zonas   : {', '.join(zonas) if zonas else '(ninguna)'}")
    print("  U_inf   : 0 m/s  (dominio cerrado, en reposo)")
    print("  BC      : inlet/outlet/sides/top = slip, ground = noSlip")
    print("  p       : UNA salida de presion en el techo")
    print("  fuente  : copiada intacta de constant/fvOptions")
    if problemas:
        print("\n  [FALLO] problemas en la generacion:")
        for p_ in problemas:
            print(f"    - {p_}")
    else:
        print("\n  [ok] el caso de hover quedo bien formado")
        print("       siguiente paso: ejecutar el solver y verificar")
        print("       python3 scripts/foam_run.py bash scripts/gate_cfd0_hover.sh")
    print()
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())
