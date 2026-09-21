#!/usr/bin/env python3
"""Volumen de las zonas de rotor, calculado desde la malla REAL.

Por que existe este script
--------------------------
La fuente de momento prescrita impone una densidad de fuerza volumetrica

    f_cell  =  T_i * V_cell / V_zone           [N/m^3]

de modo que, por construccion,

    integral_{V_zone} f dV  =  T_i * (sum_cell V_cell) / V_zone  =  T_i

Esa construccion solo es correcta si `V_zone` es el volumen REAL de la zona en la malla
que se va a correr. Si `V_zone` se toma de una estimacion geometrica (pi r^2 h) y la malla
no la reproduce exactamente, la fuerza integrada NO es `T_i` y el error es silencioso:
el solver converge igual y nadie lo nota.

Por eso `V_zone` se calcula aqui directamente de `constant/polyMesh/{points,faces,owner,
neighbour,cellZones}`, con el teorema de la divergencia, y no se estima.

Esto es una comprobacion GEOMETRICA, no un resultado de CFD. No sustituye a GATE CFD-0:
CFD-0 debe demostrar que la fuerza que el SOLVER aplica integra `T_i`, lo cual es una
afirmacion distinta y se verifica con `volFieldValue`/`volIntegrate` sobre el campo real.

Uso
---
    python scripts/mesh_zone_volumes.py                       # un caso (el nominal)
    python scripts/mesh_zone_volumes.py --case <ruta>         # un caso concreto
    python scripts/mesh_zone_volumes.py --all                 # los 128 casos
    python scripts/mesh_zone_volumes.py --json                # salida legible por maquina

El resultado se escribe en `constant/rotorZoneVolumes` dentro de cada caso, que es el
fichero que consume `scripts/build_prescribed_momentum.py`.
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


# ---------------------------------------------------------------------------------------
# lectura de ficheros OpenFOAM
# ---------------------------------------------------------------------------------------
def _sin_comentarios(texto: str) -> str:
    """Quita comentarios // y /* */ de un fichero OpenFOAM."""
    fuera = []
    i, n = 0, len(texto)
    while i < n:
        if texto.startswith("/*", i):
            fin = texto.find("*/", i + 2)
            i = n if fin < 0 else fin + 2
        elif texto.startswith("//", i):
            fin = texto.find("\n", i)
            i = n if fin < 0 else fin
        else:
            fuera.append(texto[i])
            i += 1
    return "".join(fuera)


def _cuerpo_tras_cabecera(txt: str) -> str:
    """Devuelve el texto despues del diccionario FoamFile de cabecera.

    Necesario porque la cabecera `FoamFile { ... }` va precedida de un banner de comentario
    que contiene parentesis, y buscar el primer '(' del fichero entero lo encontraria ahi.

    El emparejamiento de llaves IGNORA las cadenas entrecomilladas: la cabecera contiene
    `arch "LSB;label=32;scalar=64";` y no debe confundirse con estructura de diccionario.
    """
    marca = txt.find("FoamFile")
    if marca < 0:
        return txt
    abre = txt.find("{", marca)
    if abre < 0:
        return txt
    prof, i, n = 0, abre, len(txt)
    en_cadena = False
    while i < n:
        c = txt[i]
        if c == '"':
            en_cadena = not en_cadena
        elif not en_cadena:
            if c == "{":
                prof += 1
            elif c == "}":
                prof -= 1
                if prof == 0:
                    return txt[i + 1:]
        i += 1
    return txt


def leer_lista_numeros(ruta: Path, n_esperado: int | None = None) -> list:
    """Lee `N ( v1 v2 ... vN )` de un fichero de lista OpenFOAM."""
    txt = _escalares_tras_cabecera(ruta)
    ini = txt.find("(")
    if ini < 0:
        raise ValueError(f"{ruta.name}: no se encontro '(' de la lista")
    cuerpo = txt[ini + 1:]
    fin = cuerpo.rfind(")")
    if fin >= 0:
        cuerpo = cuerpo[:fin]
    vals = [float(t) for t in cuerpo.replace("\n", " ").split()]
    if n_esperado is not None and len(vals) != n_esperado:
        raise ValueError(f"{ruta.name}: esperaba {n_esperado} valores, hay {len(vals)}")
    return vals


def _escalares_tras_cabecera(ruta: Path) -> str:
    """Texto del fichero sin cabecera FoamFile ni comentarios: el cuerpo de la lista."""
    txt = _sin_comentarios(ruta.read_text(encoding="utf-8", errors="replace"))
    return _cuerpo_tras_cabecera(txt)


def leer_puntos(ruta: Path) -> list:
    """Devuelve [(x,y,z), ...].

    `points` NO es una lista plana de escalares: es `N ( (x y z) (x y z) ... )`, es decir
    cada entrada lleva sus propios parentesis. Por eso no se puede usar el lector de lista
    plana (que corta en el primer '(' y el ultimo ')'), sino que hay que tomar los
    parentesis INTERNOS.
    """
    txt = _escalares_tras_cabecera(ruta)

    # contar valores declarado por la cabecera de la lista: el primer entero antes de '('
    abre = txt.find("(")
    if abre < 0:
        raise ValueError(f"{ruta.name}: no se encontro '(' de la lista")
    declarado = txt[:abre].split()
    n_esperado = int(declarado[-1]) if declarado else None

    # parentesis internos: el caracter siguiente al '(' que abre la lista, hasta el ultimo ')'
    cuerpo = txt[abre + 1:]
    fin = cuerpo.rfind(")")
    if fin >= 0:
        cuerpo = cuerpo[:fin]

    vals = []
    i, n = 0, len(cuerpo)
    while i < n:
        if cuerpo[i] == "(":
            cierra = cuerpo.find(")", i)
            if cierra < 0:
                raise ValueError(f"{ruta.name}: parentesis sin cerrar")
            campos = cuerpo[i + 1:cierra].split()
            if len(campos) != 3:
                raise ValueError(f"{ruta.name}: entrada con {len(campos)} componentes, "
                                 f"se esperaban 3")
            vals.append((float(campos[0]), float(campos[1]), float(campos[2])))
            i = cierra + 1
        else:
            i += 1

    if n_esperado is not None and len(vals) != n_esperado:
        raise ValueError(f"{ruta.name}: la lista declara {n_esperado} puntos, "
                         f"se leyeron {len(vals)}")
    return vals


def leer_caras(ruta: Path) -> list:
    """Devuelve [[i0,i1,...], ...] desde el formato `n(i0 i1 ... in)`."""
    txt = _escalares_tras_cabecera(ruta)
    ini = txt.find("(")
    if ini < 0:
        raise ValueError(f"{ruta.name}: no se encontro '(' de la lista")
    cuerpo = txt[ini + 1:]
    fin = cuerpo.rfind(")")
    if fin >= 0:
        cuerpo = cuerpo[:fin]

    caras, i, n = [], 0, len(cuerpo)
    while i < n:
        while i < n and not cuerpo[i].isdigit():
            i += 1
        if i >= n:
            break
        j = i
        while j < n and cuerpo[j].isdigit():
            j += 1
        k = int(cuerpo[i:j])
        abre = cuerpo.find("(", j)
        cierra = cuerpo.find(")", abre)
        caras.append([int(t) for t in cuerpo[abre + 1:cierra].split()])
        if len(caras[-1]) != k:
            raise ValueError(f"{ruta.name}: cara {len(caras)-1} declara {k} puntos, "
                             f"tiene {len(caras[-1])}")
        i = cierra + 1
    return caras


def leer_zonas(ruta: Path) -> dict:
    """Lee `constant/polyMesh/cellZones` -> {nombre: [cellLabels]}.

    Estructura del fichero:

        N
        (
        rotor1
        {
            type            cellZone;
            cellLabels      List<label> 60 ( 74906 ... );
        }
        rotor2
        { ... }
        )

    El nombre de la zona esta en la linea ANTERIOR a su '{'. Se localiza el '{' de cada
    bloque y se toma la ultima palabra no vacia del texto que lo precede, ignorando las
    llaves de cierre de los bloques previos (de ahi el `replace("}", " ")`): sin eso, el
    primer bloque heredaria la llave del diccionario FoamFile de la cabecera y el nombre
    saldria contaminado.
    """
    txt = _escalares_tras_cabecera(ruta)
    zonas: dict[str, list[int]] = {}
    i = 0
    while True:
        marca = txt.find("cellLabels", i)
        if marca < 0:
            break
        abre_bloque = txt.rfind("{", 0, marca)
        if abre_bloque < 0:
            raise ValueError(f"{ruta.name}: 'cellLabels' sin llave de bloque antes")
        previo = txt[:abre_bloque].replace("}", " ").replace("{", " ").replace("(", " ")
        campos = previo.split()
        if not campos:
            raise ValueError(f"{ruta.name}: no se pudo determinar el nombre de la zona")
        nombre = campos[-1]

        abre_lista = txt.find("(", marca)
        cierra_lista = txt.find(")", abre_lista)
        if abre_lista < 0 or cierra_lista < 0:
            raise ValueError(f"{ruta.name}: lista de cellLabels mal formada en '{nombre}'")
        etiquetas = [int(t) for t in txt[abre_lista + 1:cierra_lista].split()]

        declarado = txt[marca:abre_lista].split()
        n_declarado = None
        for tok in declarado:
            if tok.isdigit():
                n_declarado = int(tok)
        if n_declarado is not None and n_declarado != len(etiquetas):
            raise ValueError(f"{ruta.name}: zona '{nombre}' declara {n_declarado} celdas, "
                             f"se leyeron {len(etiquetas)}")

        zonas[nombre] = etiquetas
        i = cierra_lista + 1
    return zonas


# ---------------------------------------------------------------------------------------
# volumenes
# ---------------------------------------------------------------------------------------
def volumenes_celdas(puntos, caras, owner, neighbour, n_celdas) -> list:
    """Volumen de cada celda por el teorema de la divergencia.

    Para una cara plana con vertices v0..v(k-1), el tetraedro (origen, v0, v_{j}, v_{j+1})
    aporta  (v0 . (v_j x v_{j+1})) / 6  al volumen encerrado por la superficie orientada.
    La suma sobre las caras de la celda, con la orientacion owner->neighbour, da V_cell.
    Es exacto para caras planas y no exige convexidad de la celda.
    """
    vol = [0.0] * n_celdas

    # recorrido explicito (sin crear listas gigantes de tuplas)
    for fid in range(len(owner)):
        c = owner[fid]
        vs = caras[fid]
        x0, y0, z0 = puntos[vs[0]]
        acc = 0.0
        for j in range(1, len(vs) - 1):
            xa, ya, za = puntos[vs[j]]
            xb, yb, zb = puntos[vs[j + 1]]
            acc += (xa * (yb * z0 - zb * y0)
                    - ya * (xb * z0 - zb * x0)
                    + za * (xb * y0 - yb * x0))
        vol[c] += acc / 6.0

    for fid in range(len(neighbour)):
        c = neighbour[fid]
        vs = caras[fid]
        x0, y0, z0 = puntos[vs[0]]
        acc = 0.0
        for j in range(1, len(vs) - 1):
            xa, ya, za = puntos[vs[j]]
            xb, yb, zb = puntos[vs[j + 1]]
            acc += (xa * (yb * z0 - zb * y0)
                    - ya * (xb * z0 - zb * x0)
                    + za * (xb * y0 - yb * x0))
        vol[c] -= acc / 6.0

    return vol


def analizar_caso(caso: Path) -> dict:
    pm = caso / "constant" / "polyMesh"
    faltan = [f for f in ("points", "faces", "owner", "neighbour") if not (pm / f).exists()]
    if faltan:
        return {"caso": caso.name, "estado": "sin_malla", "faltan": faltan}

    puntos = leer_puntos(pm / "points")
    caras = leer_caras(pm / "faces")
    owner = [int(t) for t in leer_lista_numeros(pm / "owner")]
    neighbour = [int(t) for t in leer_lista_numeros(pm / "neighbour")]

    fz = pm / "cellZones"
    if not fz.exists():
        return {"caso": caso.name, "estado": "sin_cellZones"}
    zonas = leer_zonas(fz)
    if not zonas:
        return {"caso": caso.name, "estado": "cellZones_vacio"}

    n_celdas = max(max(owner), max(neighbour)) + 1
    vol = volumenes_celdas(puntos, caras, owner, neighbour, n_celdas)

    negativos = sum(1 for v in vol if v <= 0.0)
    total = math.fsum(vol)

    caja = [max(p[0] for p in puntos) - min(p[0] for p in puntos),
            max(p[1] for p in puntos) - min(p[1] for p in puntos),
            max(p[2] for p in puntos) - min(p[2] for p in puntos)]
    caja_vol = caja[0] * caja[1] * caja[2]

    por_zona = {z: math.fsum(vol[c] for c in etqs) for z, etqs in zonas.items()}
    n_por_zona = {z: len(etqs) for z, etqs in zonas.items()}

    return {
        "caso": caso.name,
        "estado": "ok",
        "n_puntos": len(puntos),
        "n_caras": len(caras),
        "n_celdas": n_celdas,
        "volumen_total_m3": total,
        "volumen_caja_m3": caja_vol,
        "error_cierre_caja_pct": 100.0 * (total - caja_vol) / caja_vol if caja_vol else None,
        "celdas_volumen_no_positivo": negativos,
        "zonas": por_zona,
        "celdas_por_zona": n_por_zona,
    }


# ---------------------------------------------------------------------------------------
def escribir_rotorZoneVolumes(caso: Path, zonas: dict) -> Path:
    destino = caso / "constant" / "rotorZoneVolumes"
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
        "    object      rotorZoneVolumes;",
        "}",
        "// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //",
        "",
        "// Volumen REAL de cada cellZone de rotor, calculado sobre la malla de ESTE caso",
        "// con scripts/mesh_zone_volumes.py (teorema de la divergencia).",
        "// Lo consume scripts/build_prescribed_momentum.py para imponer",
        "//     integral_{V_zone} f dV = T_i      con   f = T_i * V_cell / V_zone^2",
        "// NO es una estimacion geometrica: si la malla cambia, hay que recalcularlo.",
        "//",
        "// Aviso: el volumen es una propiedad de la MALLA, no un resultado de CFD.",
        "// GATE CFD-0 exige ademas comprobar que la fuerza que aplica el SOLVER integra T_i.",
        "",
        "volumenZonas",
        "{",
    ]
    for z in sorted(zonas):
        lineas.append(f"    {z:<12} {zonas[z]:.10e};")
    lineas += ["}", "", "// ************************************************************************* //", ""]
    destino.write_text("\n".join(lineas), encoding="utf-8")
    return destino


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--case", default=None, help="ruta a un caso concreto")
    ap.add_argument("--all", action="store_true", help="todos los casos con malla")
    ap.add_argument("--json", action="store_true", help="salida JSON")
    ap.add_argument("--write", action="store_true",
                    help="escribir constant/rotorZoneVolumes en cada caso")
    args = ap.parse_args()

    if args.case:
        casos = [Path(args.case)]
        if not casos[0].is_absolute():
            casos[0] = (ROOT / casos[0]).resolve()
    elif args.all:
        # Solo casos reales de la suite: los artefactos de desarrollo (`T25P_baseline*`)
        # tienen malla pero no case_meta.json, y el caso de hover es la prueba de
        # GATE CFD-0, no un punto del DOE.
        casos = sorted(p for p in CASES.iterdir()
                       if p.is_dir() and (p / "case_meta.json").exists()
                       and "HOVER" not in p.name)
    else:
        casos = [CASES / CASO_NOMINAL]

    resultados = []
    for caso in casos:
        try:
            r = analizar_caso(caso)
        except Exception as exc:  # noqa: BLE001 - se reporta, no se oculta
            r = {"caso": caso.name, "estado": "error", "detalle": f"{type(exc).__name__}: {exc}"}
        resultados.append(r)
        if r.get("estado") == "ok" and args.write:
            escribir_rotorZoneVolumes(caso, r["zonas"])

    if args.json:
        print(json.dumps(resultados, indent=2, ensure_ascii=False))
        return 0

    print("=" * 100)
    print("VOLUMEN DE ZONAS DE ROTOR  -  calculado desde la malla real, no estimado")
    print("=" * 100)
    for r in resultados:
        if r.get("estado") != "ok":
            print(f"\n  {r['caso']}: {r['estado']}  {r.get('detalle', '')}")
            continue
        print(f"\n  {r['caso']}")
        print(f"    malla: {r['n_puntos']} puntos · {r['n_caras']} caras · {r['n_celdas']} celdas")
        print(f"    V total       = {r['volumen_total_m3']:.6f} m3")
        print(f"    V caja dominio= {r['volumen_caja_m3']:.6f} m3")
        print(f"    cierre        = {r['error_cierre_caja_pct']:+.6f} %  "
              f"(debe ser ~0 en una malla estructurada)")
        if r["celdas_volumen_no_positivo"]:
            print(f"    [!!] {r['celdas_volumen_no_positivo']} celdas con V <= 0  -> malla no valida")
        else:
            print("    [ok] ninguna celda con V <= 0")
        for z in sorted(r["zonas"]):
            print(f"      {z:<10} V = {r['zonas'][z]:.10e} m3   "
                  f"({r['celdas_por_zona'][z]} celdas)")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
