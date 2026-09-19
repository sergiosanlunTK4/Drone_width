"""
Genera la HOJA DE CAMPO imprimible para los cuatro modelos.

QUE ES:
  un documento de campo, en papel o tablet, para ejecutar el BLOQUE 1 (metrologia estatica)
  y opcionalmente el BLOQUE 2 (estado operativo) sobre T25P, T55, T70P y T100.

COMO ESTA ORGANIZADO:
  - Seccion 0: sistema de referencia (se hace UNA vez, antes de tocar ningun dron).
  - Seccion 1-4: una seccion por plataforma, con TODAS las mediciones y su casilla.
  - Seccion 5: bloque operativo (opcional, requiere volar).
  - Seccion 6: reglas de captura y de campo.

  Las casillas estan pensadas para escribirse a mano y luego transcribirse al CSV
  (data/raw/mediciones_geometria.csv). Cada linea de la hoja corresponde a UNA fila del CSV.

REGLA DE ORO (acordada): si una medicion parece rara, NO se reemplaza la fila anterior.
Se anade una repeticion con otro setup_id y se anota la incidencia. Asi despues se puede
distinguir error de captura / repetibilidad / asimetria real.

Uso:
  python scripts/generate_field_sheets.py
"""
from __future__ import annotations

import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "geometry" / "hoja_de_campo.md"

G = 9.81
RHO = 1.1716

# Datos publicos verificados (docs/specs, specs_master.csv, capturas oficiales)
PLAT = {
    "T25P": dict(
        nombre="DJI Agras T25P", wheelbase=1970, dims=(2650, 2700, 820),
        rotor_d=1.270, coaxial=False, rotores_hip=4,
        m_bat=33.0, tanque=20.0, mtow=53.0,
        atom_std=2, atom_opt=4, atom_sep=1420,
        nota_rotor="Evidencia S (deck 01 slide 12): 4 brazos SIN par coaxial. Motor rotulado 10028/59KV."),
    "T55": dict(
        nombre="DJI Agras T55", wheelbase=2415, dims=(3190, 3570, 934),
        rotor_d=1.575, coaxial=True, rotores_hip=8,
        m_bat=45.0, tanque=50.0, mtow=95.0,
        atom_std=2, atom_opt=4, atom_sep=1800,
        nota_rotor="Topologia NO confirmada. Ficha oficial: 'Cantidad = 4 pares'. Contar "
                   "brazos y rotores: es el dato que cierra GATE 1A del T55."),
    "T70P": dict(
        nombre="DJI Agras T70P", wheelbase=2440, dims=(3200, 3520, 960),
        rotor_d=1.574, coaxial=True, rotores_hip=8,
        m_bat=56.0, tanque=70.0, mtow=126.0,
        atom_std=2, atom_opt=4, atom_sep=1874,
        nota_rotor="Evidencia S (slide 11): par coaxial en cada brazo. A6 (separacion axial del "
                   "par) es PARAMETRO DEL MODELO de empuje, no una cota decorativa."),
    "T100": dict(
        nombre="DJI Agras T100", wheelbase=2330, dims=(3220, 3224, 975),
        rotor_d=1.574, coaxial=True, rotores_hip=8,
        m_bat=75.0, tanque=100.0, mtow=175.0,
        atom_std=2, atom_opt=4, atom_sep=1834,
        nota_rotor="CONFLICTO ABIERTO: ficha oficial dice 'Cantidad = 8 pares'; el material "
                   "Academy indica 4 brazos con un par cada uno. ESTE CONTEO ES A9: hacerlo con "
                   "foto cenital y contando fisicamente, no interpretando la tabla."),
}

ROLES = [("R1", "FL", "delantero izquierdo"), ("R2", "RL", "trasero izquierdo"),
         ("R3", "RR", "trasero derecho"), ("R4", "FR", "delantero derecho")]


def nivel0(p: dict) -> dict:
    r = p["rotor_d"] / 2
    n = p["rotores_hip"]
    A = n * math.pi * r ** 2
    T = p["mtow"] * G
    return {
        "A": round(A, 3),
        "DL": round(T / A, 1),
        "T_rotor_kg": round(T / n / G, 1),
        "v_ind": round(math.sqrt(T / (2 * RHO * A)), 2),
    }


def tabla_rotor(p: dict, plataforma: str) -> str:
    """Bloque de medicion de rotores: una tabla por plataforma."""
    filas_hi = []
    filas_lo = []
    for rid, rol, desc in ROLES:
        filas_hi.append(
            f"| `{rid}` | `{rol}` | {desc} |  |  |  |  |  |")
    if p["coaxial"]:
        for rid, rol, desc in ROLES:
            filas_lo.append(
                f"| `{rid}_lower` | `{rol}` | {desc} (inferior) |  |  |  |  |  |")
    cab = ("| id | rol | posición | X (m) | Y (m) | Z (m) | normal (x,y,z) | Ø (m) |\n"
           "|---|---|---|---|---|---|---|---|")
    out = [f"### A. Centros de rotor — {plataforma}", "",
           "> **Convención interna** (vista cenital, +X adelante, +Y izquierda, +Z arriba).",
           "> No es numeración DJI. Toda fila lleva su `position_role`.", "",
           "*Origen de medida (marcar uno):* ☐ buje R1 ☐ centro del cuerpo ☐ plomada al suelo",
           "*Referencia vertical:* ☐ base del depósito ☐ plano de aterrizaje ☐ otro: __________", "",
           cab]
    out += filas_hi
    if filas_lo:
        out += ["", "**Rotores inferiores del par coaxial** (si aplica):", "", cab]
        out += filas_lo
    out += ["", f"*Nota de esta plataforma:* {p['nota_rotor']}", "",
            "**Separaciones** (cinta entre centros de buje, dron desplegado):", "",
            "| magnitud | valor (m) | rep. 2 | rep. 3 | setup |",
            "|---|---|---|---|---|",
            "| separación ejes adyacentes, dirección X | | | | |",
            "| separación ejes adyacentes, dirección Y | | | | |",
            "| separación ejes opuestos, dirección X | | | | |",
            "| separación ejes opuestos, dirección Y | | | | |",
            "| alcance desplegado total, X | | | | |",
            "| alcance desplegado total, Y | | | | |",
            "| cota del disco al cuerpo (por si el 'desplegado' incluye guardas) | | | | |", ""]
    if p["coaxial"]:
        out += ["**Par coaxial — A6 (parámetro del modelo de empuje):**", "",
                "| magnitud | valor (m) | rep. 2 | rep. 3 | setup |",
                "|---|---|---|---|---|",
                "| separación axial del par, brazo FL | | | | |",
                "| separación axial del par, brazo FR | | | | |",
                "| separación axial del par, brazo RL | | | | |",
                "| separación axial del par, brazo RR | | | | |", ""]
    return "\n".join(out)


def tabla_atomizadores(p: dict, plataforma: str) -> str:
    filas = []
    for i in range(1, p["atom_opt"] + 1):
        filas.append(f"| `A{i}` |  |  |  |  |  |  |  |")
    return "\n".join([
        f"### B. Atomizadores — {plataforma}", "",
        "> Medir en **configuración de 2** y repetir en **configuración de 4** (anotar en `configuracion`).",
        "> `altura_rel_plano_rotor` es el Δz al plano de rotor **más próximo**: es lo crítico para H3.",
        "",
        "| id | X (m) | Y (m) | Z (m) | vector descarga (x,y,z) | Δz al rotor (m) | rotor más cercano | soporte / cota al eje |",
        "|---|---|---|---|---|---|---|---|",
        *filas, "",
        f"*Separación entre boquillas declarada por el fabricante:* {p['atom_sep']} mm.",
        "Comprobar en campo si coincide y anotar la diferencia.",
        "",
        "**Punto efectivo de emisión** (si es determinable, foto macro): ☐ sí ☐ no",
        "Descripción: ______________________________________________",
        "",
        "**Rotor(es) cuya estela recibe cada atomizador** (derivado de A + B):",
        "A1 → ______   A2 → ______   A3 → ______   A4 → ______", "",
    ])


def tabla_masas(p: dict, plataforma: str) -> str:
    filas = []
    for f in (1.00, 0.75, 0.50, 0.25, 0.00):
        nom = p["m_bat"] + p["tanque"] * f
        filas.append(f"| {f:.2f} | {nom:.1f} |  |  |  |  |")
    return "\n".join([
        f"### C. Masas y CG — {plataforma}", "",
        "> 🔴 **`nominal` ≠ `measured`.** La columna nominal es un valor **derivado** del planning",
        "> (clase `E`). Antes de cada pesada hay que **pesar la configuración efectiva** y anotarla",
        "> en `measured`. **La diferencia entre ambas es un resultado**, no un detalle.",
        "",
        "| f (tanque) | nominal (kg) | **medido (kg)** | incert. | CG X (m) | CG Y (m) | CG Z (m) |",
        "|---|---|---|---|---|---|---|",
        *filas, "",
        "| elemento | masa (kg) | incertidumbre | instrumento |",
        "|---|---|---|---|",
        "| batería instalada (indicar modelo) | | | |",
        "| tanque vacío | | | |",
        "| dron sin batería | | | |",
        "| atomizadores instalados (2 o 4) | | | |",
        "",
        f"*Restricción a verificar:* el T70P a {p['tanque']:.0f} L exige batería **DB2160**.",
        "Con DB1580 no cierra contra el MTOW. Anotar qué batería se usó realmente.", "",
    ])


def bloque_plataforma(clave: str, p: dict) -> str:
    n0 = nivel0(p)
    return "\n".join([
        "", "---", "",
        f"# {clave} — {p['nombre']}", "",
        f"**Datos públicos de partida:** wheelbase {p['wheelbase']} mm · "
        f"sobre desplegado {p['dims'][0]} × {p['dims'][1]} × {p['dims'][2]} mm · "
        f"Ø rotor {p['rotor_d']*1000:.0f} mm · tanque {p['tanque']:.0f} kg · MTOW {p['mtow']:.0f} kg",
        "",
        f"**Referencias de nivel 0 para CONTRASTAR** (momentum theory, no son resultado): "
        f"área de disco {n0['A']} m² · carga de disco {n0['DL']} N/m² · "
        f"empuje/rotor si reparto uniforme {n0['T_rotor_kg']} kg · v_inducida {n0['v_ind']} m/s",
        "",
        "*Fecha:* __________  *Operador:* __________  *Lugar:* ____________________",
        "*Condiciones:* T ___ °C  HR ___ %  P ___ hPa  viento ___ m/s",
        "*Dron:* ☐ sobre caballete ☐ superficie plana ☐ otro: __________  *Nivelado:* ☐ sí",
        "",
        tabla_rotor(p, clave),
        tabla_atomizadores(p, clave),
        tabla_masas(p, clave),
    ])


def main() -> int:
    doc = []
    doc.append("# HOJA DE CAMPO — Bloque 1: metrología estática")
    doc.append("")
    doc.append("**Plataformas:** T25P · T55 · T70P · T100  ")
    doc.append("**Generado por:** `scripts/generate_field_sheets.py`  ")
    doc.append("**Protocolo de referencia:** `geometry/protocolo_geometria.md` §10")
    doc.append("")
    doc.append("---")
    doc.append("")
    doc.append("## 0. ANTES DE TOCAR NINGÚN DRON — sistema de referencia")
    doc.append("")
    doc.append("Se hace **una vez** y vale para los cuatro. Si esto queda mal, **ninguna cota**")
    doc.append("posterior es interpretable.")
    doc.append("")
    doc.append("```")
    doc.append("nombre  = CG_tank50")
    doc.append("origen  = CG en configuración de pulverización con tanque al 50 %")
    doc.append("X       = hacia adelante (dirección de vuelo)")
    doc.append("Y       = hacia la izquierda")
    doc.append("Z       = hacia arriba")
    doc.append("```")
    doc.append("")
    doc.append("| # | paso | hecho |")
    doc.append("|---|---|---|")
    doc.append("| 0.1 | Elegir y **marcar físicamente** el origen (punto, cintas, plantilla) | ☐ |")
    doc.append("| 0.2 | Describir **cómo** se materializó: ________________________________ | ☐ |")
    doc.append("| 0.3 | **FOTO CENITAL** con etiquetas físicas `R1`–`R4` y **flecha `+X`** | ☐ |")
    doc.append("| 0.4 | Anotar el nombre del archivo de esa foto: ____________________ | ☐ |")
    doc.append("| 0.5 | Nivelar el dron y registrar el método de nivelación | ☐ |")
    doc.append("| 0.6 | Anotar si el origen se fijó **antes o después** de conocer el CG medido | ☐ |")
    doc.append("")
    doc.append("> La foto de 0.3 es la que dentro de meses impedirá discutir qué significaba «R1».")
    doc.append("> Es obligatoria, no opcional.")
    doc.append("")
    doc.append("### 0.1 Convención de numeración (interna, NO de DJI)")
    doc.append("")
    doc.append("| id | `position_role` | posición |")
    doc.append("|---|---|---|")
    for rid, rol, desc in ROLES:
        doc.append(f"| `{rid}` | `{rol}` | {desc} |")
    doc.append("")
    doc.append("`R1…R4` son **identificadores**; `FL/RL/RR/FR` contienen la **semántica**.")
    doc.append("Los pares diametralmente opuestos son `FL↔RR` y `FR↔RL`.")
    doc.append("")
    doc.append("### 0.2 Material mínimo")
    doc.append("")
    doc.append("- [ ] Cinta métrica (clase de exactitud anotada) y regla/calibre")
    doc.append("- [ ] Plomada o nivel láser para proyectar centros al suelo")
    doc.append("- [ ] Nivel digital (para la normal del disco)")
    doc.append("- [ ] Báscula con resolución conocida")
    doc.append("- [ ] Cámara o móvil (fotos de **cada** punto medido)")
    doc.append("- [ ] Cintas de etiquetar para marcar `R1`–`R4`, `A1`–`A4` y el origen")
    doc.append("- [ ] Esta hoja impresa y bolígrafo (o tablet)")
    doc.append("")
    doc.append("### 0.3 Seguridad")
    doc.append("")
    doc.append("- [ ] **Hélices retiradas o bloqueadas** en toda medición con el dron energizado")
    doc.append("- [ ] Ninguna medición se hace con motores armados")
    doc.append("- [ ] Dron sobre caballete o superficie estable antes de inclinarse sobre él")
    doc.append("")

    for clave, p in PLAT.items():
        doc.append(bloque_plataforma(clave, p))

    doc += [
        "", "---", "",
        "# 5. BLOQUE OPERATIVO (opcional — requiere volar)",
        "",
        "> Solo si el Bloque 1 pasó el post-mortem. **No se vuela antes de auditar las filas",
        "> estáticas.** Aquí se cierra GATE 1B.",
        "",
        "## 5.1 RPM en hover — INDIVIDUAL POR ROTOR",
        "",
        "> 🔴 **No registrar una sola «RPM del dron».** Diferencias entre rotores son evidencia",
        "> directa contra el supuesto de reparto uniforme `mg/N`, y **se pierden si se promedian**.",
        "",
        "| plataforma | estado de carga | R1 (rpm) | R2 | R3 | R4 | R1_low | R2_low | R3_low | R4_low |",
        "|---|---|---|---|---|---|---|---|---|---|",
        "|  |  |  |  |  |  |  |  |  |  |",
        "",
        "*Método:* ☐ tacómetro óptico de 2 canales ☐ cámara alta velocidad  *Instrumento:* ______________",
        "*Medir RPM en hover ANTES que en bancada* (context.md §42).",
        "",
        "## 5.2 Orden recomendado",
        "",
        "1. RPM en hover real con **masa medida** (no nominal), en los 5 estados de carga.",
        "2. Bancada de empuje **por rotor**, no por brazo: D5a/D5b/D5c de `coaxial_thrust_split.md`.",
        "3. Comprobar A10 (¿un motor o dos por brazo? ¿ESC compartido o independiente?).",
        "",
        "---",
        "",
        "# 6. Reglas de captura",
        "",
        "1. **Si una medición parece rara: NO se reemplaza la fila anterior.** Se añade una",
        "   repetición con **otro `setup_id`** y se anota la incidencia. Así después se distingue",
        "   **error de captura / repetibilidad / asimetría real** — hoy son indistinguibles.",
        "2. **Repeticiones independientes:** para repetibilidad hay que **soltar y volver a montar**",
        "   el instrumento entre lecturas (≥3, con distinto `setup_id`). Tres lecturas seguidas sin",
        "   moverse miden **resolución**, no repetibilidad.",
        "3. **Los residuos no se corrigen.** Si `r_i + r_j ≠ 0`, ese residuo **es el dato**.",
        "   Nunca se ajustan coordenadas para forzar la simetría.",
        "4. **`nominal` ≠ `measured`** en masa. Son variables distintas, ambas en el CSV.",
        "5. Toda fila `M` necesita `uncertainty` e `instrument`. Toda fila necesita `reference_frame`.",
        "6. **Fotografiar cada punto medido** y anotar el nombre del archivo.",
        "7. Si una medición **contradice la ficha oficial, gana la medición** — y la discrepancia",
        "   se anota en `notes`.",
        "",
        "---",
        "",
        "# 7. Cómo entregar los datos",
        "",
        "Transcribir la hoja a `data/raw/mediciones_geometria.csv` con estas columnas:",
        "",
        "```",
        "uav,block,element_id,position_role,parameter,value,unit,uncertainty,method,",
        "instrument,timestamp,operator,source_class,reference_frame,configuracion,",
        "repetitions,setup_id,raw_file,notes",
        "```",
        "",
        "Ejemplo de tres filas reales:",
        "",
        "```csv",
        "T25P,rotor,R1,FL,posicion_x,0.6965,m,±0.005 (k=2),cinta desde centro de buje,",
        "\"cinta Stanley 5 m\",2026-09-20T10:35:00-03:00,D.M.,M,CG_tank50,2atm,3,S1,",
        "foto_R1_xy.jpg,origen marcado con cinta",
        "```",
        "",
        "**Entregar:** el CSV + las fotografías + notas de campo. Con eso corro la QA, calculo",
        "incertidumbres, residuos 3D y consistencia geométrica, y decidimos GATE 1A.",
        "",
        "*Recordatorio del orden acordado:* primero se ve **lo que dicen las mediciones**, y",
        "**después** se buscan explicaciones. No se ajusta la geometría para hacerla coincidir",
        "ni con DJI ni con la relación geométrica candidata.",
    ]

    OUT.write_text("\n".join(doc), encoding="utf-8")
    print(f"escrito {OUT.relative_to(ROOT)}")
    print(f"plataformas incluidas: {', '.join(PLAT)}")
    for k, p in PLAT.items():
        n0 = nivel0(p)
        print(f"  {k:5s} coaxial={str(p['coaxial']):5s} rotores_hip={p['rotores_hip']} "
              f"atom_std/opt={p['atom_std']}/{p['atom_opt']} v_ind={n0['v_ind']} m/s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
