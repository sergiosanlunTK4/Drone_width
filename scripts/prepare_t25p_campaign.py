"""
Prepara (NO ejecuta) la hoja de campaña fisica del T25P y la plantilla CSV de mediciones.

POR QUE T25P ES LA PLATAFORMA PILOTO (y algo mas que "la primera que se puede cerrar"):
  el T25P elimina de la primera iteracion toda la incertidumbre coaxial (no tiene par
  coaxial), asi que sirve para ENSAYAR EL PROPIO METODO EXPERIMENTAL de punta a punta:
      documentacion -> medicion M -> incertidumbre -> manifest -> GATE 1A -> freeze -> SHA256
  Si aparecen problemas de sistema de referencia, repetibilidad, instrumentos, nomenclatura
  o incertidumbre, se corrigen antes de enfrentar los coaxiales.

Este script:
  - deriva los puntos de carga del T25P de los datos publicos (33 kg + 20 kg * f)
  - calcula referencias de nivel 0 (momentum theory) para contrastar lo que se mida
  - escribe data/raw/mediciones_geometria.csv con SOLO la cabecera (cero filas)
  - escribe geometry/campana_T25P.md con la hoja de campaña

NO mide nada. NO inventa valores. Las filas del CSV las llena la campaña de campo.

Uso:
  python scripts/prepare_t25p_campaign.py
"""
from __future__ import annotations

import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "data" / "raw" / "mediciones_geometria.csv"
DOC = ROOT / "geometry" / "campana_T25P.md"

# --- datos publicos del T25P (docs/specs/T25P.md, clasificacion P) -----------------
M_SIN_BATERIA = 26.0
M_BATERIA_DB800 = 6.6
M_CON_BATERIA = 33.0
TANQUE = 20.0
MTOW_SPRAY = 53.0
ROTOR_D = 1.270
N_ROTORES = 4                 # evidencia S (deck 01, slide 12): 4 brazos sin coaxial
WHEELBASE = 1.970
G = 9.81
RHO = 1.1716                  # 28 C, nivel del mar

CSV_COLS = [
    "uav", "block", "element_id", "parameter", "value", "unit", "uncertainty",
    "method", "instrument", "timestamp", "operator", "source_class",
    "reference_frame", "configuracion", "repetitions", "raw_file", "notes",
]


def nivel0() -> dict:
    r = ROTOR_D / 2
    A = N_ROTORES * math.pi * r ** 2
    T = MTOW_SPRAY * G
    return {
        "area_disco_m2": round(A, 3),
        "carga_disco_N_m2": round(T / A, 1),
        "empuje_por_rotor_N": round(T / N_ROTORES, 1),
        "empuje_por_rotor_kg": round(T / N_ROTORES / G, 1),
        "v_inducida_hover_ms": round(math.sqrt(T / (2 * RHO * A)), 2),
        "lado_entre_ejes_m": round(WHEELBASE / math.sqrt(2), 4),
    }


def main() -> int:
    # 1) cabecera del CSV (sin filas: la campana no se ha ejecutado)
    CSV.parent.mkdir(parents=True, exist_ok=True)
    if not CSV.exists():
        CSV.write_text(",".join(CSV_COLS) + "\n", encoding="utf-8")
        print(f"creado {CSV.relative_to(ROOT)} (solo cabecera, 0 filas)")
    else:
        print(f"{CSV.relative_to(ROOT)} ya existe: NO se sobrescribe")

    # 2) puntos de carga
    puntos = []
    for f in (1.00, 0.75, 0.50, 0.25, 0.00):
        m = M_CON_BATERIA + TANQUE * f
        puntos.append((f, m, round(m * G / N_ROTORES, 1)))

    n0 = nivel0()

    doc = f"""# Hoja de campaña física — DJI Agras T25P (plataforma piloto)

> ⚠ **ESTADO: PREPARADA, NO EJECUTADA.** Este documento es el plan de medición.
> No contiene ningún valor medido. Las filas se registran en
> `data/raw/mediciones_geometria.csv` durante el trabajo de campo.

## 0. Por qué el T25P es la plataforma piloto

No es solo "la primera que se puede cerrar". El T25P **elimina de la primera iteración toda la
incertidumbre coaxial** (no tiene par coaxial), así que sirve para **ensayar el propio método
experimental** de punta a punta antes de enfrentar los coaxiales:

```
documentación → medición M → incertidumbre → manifest → GATE 1A → freeze → SHA256 → malla
```

Si aparecen problemas de **sistema de referencia, repetibilidad, instrumentos, nomenclatura o
incertidumbre**, se corrigen aquí y no en T55/T70P/T100.

## 1. Estado de partida (todo público, clasificación P)

| Parámetro | Valor | Clase |
|---|---|---|
| Masa sin batería | {M_SIN_BATERIA} kg | P |
| Batería DB800 | {M_BATERIA_DB800} kg | P |
| Masa con batería | {M_CON_BATERIA} kg | P |
| Tanque | {TANQUE} kg (20 L) | P |
| MTOW pulverización | {MTOW_SPRAY} kg | P |
| Diámetro de rotor | {ROTOR_D} m (50 in) | P |
| Nº de rotores | {N_ROTORES} | **S** (deck 01, slide 12: 4 brazos sin coaxial) |
| Palas por rotor | 2 | **S** |
| Distancia diagonal entre ejes | {WHEELBASE*1000:.0f} mm | P |
| Motor | estator 100 × 28 mm, KV 59 | P-A + S (imagen rotulada "10028/59KV") |
| Atomizadores | 2 estándar / 4 opcional, separación 1420 mm | P |
| Gota | 50–500 µm | P |

### 1.1 Referencias de nivel 0 (momentum theory) — para CONTRASTAR, no para sustituir

> Solo órdenes de magnitud (context.md §12 nivel 0), calculados con `scripts/prepare_t25p_campaign.py`.
> **Nunca** se reportan como resultado del estudio.

| Derivado | Valor |
|---|---|
| Área de disco total (4 rotores) | {n0['area_disco_m2']} m² |
| Carga de disco a MTOW | {n0['carga_disco_N_m2']} N/m² |
| Empuje por rotor a MTOW (si reparto uniforme) | {n0['empuje_por_rotor_N']} N = {n0['empuje_por_rotor_kg']} kg |
| Velocidad inducida en hover a MTOW | {n0['v_inducida_hover_ms']} m/s |
| Lado entre ejes (D_axis/√2) | {n0['lado_entre_ejes_m']} m |

**Uso:** si la RPM medida implica una velocidad inducida que se aparta mucho de
{n0['v_inducida_hover_ms']} m/s, hay que revisar antes de construir el modelo — no ajustar el
modelo para que encaje.

## 2. Puntos de carga a caracterizar (bloque C)

Masa total = {M_CON_BATERIA} + {TANQUE} · f (kg). Sanity check: f = 1 → {M_CON_BATERIA + TANQUE:.1f} kg ≈ MTOW {MTOW_SPRAY} kg ✓

| f (tanque) | Masa total (kg) | Empuje por rotor si reparto uniforme (N) |
|---|---|---|
""" + "\n".join(
        f"| {f:.2f} | {m:.1f} | {t} |" for f, m, t in puntos
    ) + f"""

> ⚠ El reparto uniforme de la última columna es **hipótesis de partida**, no verdad experimental.
> El T25P no es coaxial, así que `mg/N` es una aproximación razonable — **pero se contrasta con el
> CG medido (C5)**: si el CG está desplazado (tanque, batería, atomizadores), el reparto real no
> será uniforme y hay que declararlo.

## 3. Sistema de referencia (se declara UNA vez)

```
origen  = CG en configuración de pulverización con tanque al 50 %
X       = hacia adelante (dirección de vuelo)
Y       = hacia la izquierda
Z       = hacia arriba
nombre  = CG_tank50
```

Toda fila del CSV lleva `reference_frame = CG_tank50`. **Determinar la posición del CG (C5) antes
de fijar el origen**; si el CG se mide después, hay que anotar el desplazamiento.

## 4. Bloques a ejecutar

### Bloque A — sistema propulsivo (bloquea GATE 1A)

| # | Medición | Método | Objetivo |
|---|---|---|---|
| A1 | Nº de brazos y rotores; verificar ausencia de coaxial | inspección + foto cenital | exacto (confirma la evidencia `S`) |
| A2 | **Centro XYZ de los 4 discos de rotor** | cinta/calibre desde referencias del cuerpo; plomada para XY | ±5 mm |
| A3 | **Vector normal del disco** de cada rotor | nivel digital | ±1° |
| A4 | Diámetro de barrido real | cinta punta a punta | ±5 mm |
| A5 | Sentido de giro de cada rotor | manual / arranque controlado | binario |
| A7 | Nº de palas (confirmar 2) y geometría de pala | medición + fotos ortogonales | ±2 mm |
| A8 | **Separación entre ejes**, X e Y | cinta entre centros de buje | ±5 mm |

**A6 (separación axial del par) y A10/A11 no aplican al T25P**: no hay par coaxial.
Eso es exactamente lo que lo hace buen piloto.

### Bloque B — atomizadores (bloquea H3)

| # | Medición | Método |
|---|---|---|
| B1 | Nº real por configuración (2 y 4) | inspección |
| B2 | **Centro XYZ de cada atomizador**, en config. 2 y 4 | cinta desde referencias |
| B3 | **Vector de descarga** | foto ortogonal con referencia angular |
| B4 | **Δz al plano de rotor más próximo** y rotor cuya estela recibe | derivado de A2 + B2 |
| B5 | Punto efectivo de emisión, si es determinable | foto macro / patrón en banco |
| B6 | Geometría de soporte (brazo), cota al eje | cinta |

### Bloque C — masas y CG (bloquea GATE 1A)

| # | Medición | Método |
|---|---|---|
| C1 | Masa sin batería | báscula |
| C2 | Masa de la batería DB800 | báscula |
| C3 | Masa total en los 5 puntos de carga de §2 | báscula + agua medida |
| C5 | **Posición del CG** en cada estado de carga | punto de equilibrio / 4 células de carga |

### Bloque D — bancada y vuelo (GATE 1B; puede ir después)

| # | Medición | Método |
|---|---|---|
| D1 | Caudal por atomizador a cada ajuste | caudalímetro / báscula + cronómetro |
| D2 | Presión de pulverización | manómetro |
| D3 | Espectro real (D10/D50/D90) | PDI/Sympatec o hidrosensibles (ordinal) |
| D4 | RPM del motor del atomizador | tacómetro óptico |
| D5 | Curva empuje–RPM–torque–corriente **por rotor** | bancada |
| — | **RPM en hover real** en los 5 puntos de carga (medir ANTES de la bancada) | tacómetro óptico / cámara de alta velocidad |

## 5. Requisitos previos a la ejecución

- [ ] Instrumentos disponibles y **calibrados**, con su certificado o fecha de calibración.
- [ ] Báscula con resolución declarada; cinta con clase de exactitud; nivel digital.
- [ ] Definir el **número de repeticiones** (mínimo 3 en los puntos críticos) y el criterio de
      repetibilidad (p. ej. dispersión ≤ incertidumbre instrumental declarada).
- [ ] Condiciones ambientales registradas (T, HR, presión) para poder referir ρ.
- [ ] **Protocolo de seguridad**: hélices retiradas o bloqueadas en toda medición con el dron
      energizado; bancada de RPM solo si el fabricante lo permite. Riesgo R11 (garantía).
- [ ] Dron sobre caballete o superficie plana nivelada, para que Z sea reproducible.

## 6. Entregable de la campaña

`data/raw/mediciones_geometria.csv` (cabecera ya creada, **0 filas**) con los campos:

```
{", ".join(CSV_COLS)}
```

Reglas:
- Ninguna fila `M` sin `uncertainty` e `instrument`.
- Ninguna fila sin `reference_frame`.
- Si una medición contradice la ficha oficial, **gana la medición** y la discrepancia se anota
  en `notes`.
- Guardar las fotos y hojas de banco en `raw_file`.

## 7. Criterio de cierre y congelación

Al completar los bloques A, B y C:

```powershell
python scripts/freeze_geometry_v1.py --uav T25P --dry-run     # debe salir sin bloqueantes
python scripts/freeze_geometry_v1.py --uav T25P --by "<quien>"
python scripts/freeze_geometry_v1.py --uav T25P --verify
```

Si el dry-run sigue dando bloqueantes, **no se congela**: el script no tiene flag de forzado.
"""
    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text(doc, encoding="utf-8")
    print(f"escrito {DOC.relative_to(ROOT)}")
    print(f"\nnivel 0 T25P: A_disco={n0['area_disco_m2']} m2, DL={n0['carga_disco_N_m2']} N/m2, "
          f"v_ind={n0['v_inducida_hover_ms']} m/s")
    print("NO se ha medido nada. La hoja esta preparada para ejecucion.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
