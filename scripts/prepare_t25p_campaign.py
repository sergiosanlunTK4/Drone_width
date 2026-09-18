"""
Prepara (NO ejecuta) la campana fisica del T25P en DOS JORNADAS con parada obligatoria.

CAMBIO DE ESTRUCTURA respecto de la version anterior, por indicacion del investigador:
  El piloto no debe intentar medir todo de una vez. Se parte en dos bloques para que un error
  metodologico no contamine toda la campana.

  BLOQUE 1 — METROLOGIA ESTATICA (UAV apagado):
      fijar el sistema CG_tank50, documentar como se materializa el origen, fotografiar cada
      punto, identificar R1-R4 y A1-A2, medir centros XYZ, normales, diametro efectivo,
      posiciones/vectores de atomizadores y las cotas para contrastar wheelbase/alcance.
      REPETICION: independiente, con RECOLOCACION del instrumento entre lecturas. Asi se estima
      repetibilidad ademas de resolucion.
      >> PARADA OBLIGATORIA: procesar filas, calcular cierres, simetrias y residuos. <<

  BLOQUE 2 — ESTADO OPERATIVO (solo si el bloque 1 pasa el post-mortem):
      masa real por estado de carga, CG/actitud, ambiente y RPM en hover.

CORRECCIONES CONCRETAS INCORPORADAS:
  1. Masa nominal != masa medida. 33/38/43/48/53 kg son PUNTOS NOMINALES DERIVADOS
     (33 + 20*f). Antes de cada vuelo hay que PESAR la configuracion efectiva. En el CSV deben
     existir como variables distintas: `nominal_total_mass_kg` y `measured_total_mass_kg`.
  2. RPM INDIVIDUAL POR ROTOR (R1-R4), no una sola RPM del T25P. Diferencias entre rotores son
     justamente lo que puede falsar el supuesto de reparto uniforme mg/4.
  3. Criterio de aceptacion expresado como RESIDUOS que NO se corrigen. Si un residuo es grande,
     se documenta; no se ajustan coordenadas para forzar la simetria.

Este script:
  - deriva los puntos nominales de carga de los datos publicos
  - calcula las referencias de nivel 0 (para contrastar, no para sustituir)
  - escribe data/raw/mediciones_geometria.csv con SOLO la cabecera (cero filas)
  - NO toca el CSV si ya tiene filas capturadas
  - escribe geometry/campana_T25P.md

NO mide nada. NO inventa valores.

Uso:
  python scripts/prepare_t25p_campaign.py
"""
from __future__ import annotations

import csv
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
    "reference_frame", "configuracion", "repetitions", "setup_id", "raw_file", "notes",
]

# parametros que la QA exige para cerrar GATE 1A (ver scripts/audit_measurement_csv.py)
REQUERIDOS_ROTOR = ["posicion_x", "posicion_y", "posicion_z", "eje_normal", "diametro", "sentido_giro"]
REQUERIDOS_ATOMIZER = ["posicion_x", "posicion_y", "posicion_z", "vector_descarga",
                       "altura_rel_plano_rotor"]


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
    # 1) cabecera del CSV — NUNCA sobrescribe datos capturados
    CSV.parent.mkdir(parents=True, exist_ok=True)
    if not CSV.exists():
        CSV.write_text(",".join(CSV_COLS) + "\n", encoding="utf-8")
        print(f"creado {CSV.relative_to(ROOT)} (solo cabecera, 0 filas)")
    else:
        filas = sum(1 for _ in CSV.open(encoding="utf-8")) - 1
        if filas > 0:
            print(f"ATENCION: {CSV.relative_to(ROOT)} ya tiene {filas} filas capturadas.")
            print("           Si falta alguna columna nueva, anadela a mano; no se sobrescribe.")
        else:
            CSV.write_text(",".join(CSV_COLS) + "\n", encoding="utf-8")
            print(f"{CSV.relative_to(ROOT)} reescrito con la cabecera ampliada (0 filas)")

    puntos = []
    for f in (1.00, 0.75, 0.50, 0.25, 0.00):
        nominal = M_CON_BATERIA + TANQUE * f
        puntos.append((f, nominal, round(nominal * G / N_ROTORES, 1)))

    n0 = nivel0()

    doc = f"""# Campaña física — DJI Agras T25P (plataforma piloto)

> ⚠ **ESTADO: PREPARADA, NO EJECUTADA.** Plan de medición. No contiene ningún valor medido.
> Las filas se registran en `data/raw/mediciones_geometria.csv` durante el trabajo de campo.

## 0. Qué debe demostrar este piloto

**No** una curva aerodinámica. Debe demostrar que esta cadena funciona **sin intervención manual
oportunista**:

```
medición cruda → CSV (clase M) → incertidumbre → QA → manifest → GATE 1A → freeze → SHA256 → --verify
```

Si esto funciona en el T25P, queda probado que **el método** —no solo el código— es reproducible,
y recién entonces se clona a los coaxiales.

**Regla de no-circularidad:** el cierre de GATE 1A **no puede depender de ningún valor derivado de
CFD**. Ese gate debe poder cerrarse exclusivamente con geometría y evidencia experimental; de lo
contrario se introduce circularidad antes de empezar a simular. Verificado: los manifiestos y el
congelador no leen `cfd/` (ver `scripts/audit_measurement_csv.py`, comprobación de no-circularidad).

## 1. Dos jornadas, con parada obligatoria

El piloto **no mide todo de una vez**. Un error metodológico en la metrología contaminaría toda la
campaña, así que se parte en dos bloques y **se procesa el primero antes de volar**.

| | Bloque 1 — Metrología estática | Bloque 2 — Estado operativo |
|---|---|---|
| UAV | **apagado**, sobre caballete/superficie nivelada | energizado / en vuelo estacionario |
| Mide | sistema de referencia, rotores, atomizadores, cotas | masas reales, CG, actitud, ambiente, RPM |
| Salida | filas `block=rotor|atomizer|geometry` | filas `block=mass|operation` |
| Cierra | **GATE 1A** | **GATE 1B** |
| Siguiente | **PARADA: post-mortem de residuos** | solo si el bloque 1 pasó |

---

# BLOQUE 1 — METROLOGÍA ESTÁTICA (UAV apagado)

## 1.1 Fijar el sistema de referencia (lo primero, antes de medir nada)

```
nombre  = CG_tank50
origen  = CG en configuración de pulverización con tanque al 50 %
X       = hacia adelante (dirección de vuelo)
Y       = hacia la izquierda
Z       = hacia arriba
```

**Documentar cómo se materializa el origen**, no solo declararlo:

- [ ] Registrar **cómo** se ubicó el origen: punto físico elegido, referencias del cuerpo usadas,
      marcas con cinta, plantilla o trípode.
- [ ] **Fotografiar la materialización del origen** (ingresar la ruta en `raw_file`).
- [ ] Registrar si el origen se fijó **antes o después** de conocer el CG medido. Si se fijó antes,
      anotar el desplazamiento posterior y **no re-medir todo** sin dejarlo documentado.
- [ ] Dejar el dron **nivelado y bloqueado**; registrar la nivelación (burbuja digital o similar).

> Un error aquí invalida todo el bloque. Ninguna cota por debajo de esta sección es interpretable
> si el origen no está documentado.

## 1.2 Identificación de elementos

- [ ] Rotores **R1–R4** identificados de forma inequívoca y **fotografiados** (vista cenital con
      los rótulos visibles). Definir el criterio: p. ej. R1 = delantero izquierdo, y el sentido
      de numeración (horario/antihorario).
- [ ] Atomizadores **A1–A2** (configuración estándar) y **A3–A4** (opcional) identificados igual.
- [ ] Registrar en `notes` el criterio de numeración elegido. **Sin esto, las coordenadas no son
      comparables ni siquiera consigo mismas entre jornadas.**

## 1.3 Medición de rotores (una fila por campo y por rotor)

| parámetro | descripción | objetivo |
|---|---|---|
| `posicion_x` `posicion_y` `posicion_z` | centro del disco de cada rotor en `CG_tank50` | ±5 mm |
| `eje_normal` | vector normal del disco (dirección de empuje), normalizado | ±1° |
| `diametro` | diámetro de barrido efectivo | ±5 mm |
| `sentido_giro` | CW / CCW | binario |
| `n_palas` | confirmar 2 (evidencia `S`) | exacto |

**Método:** cinta/calibre desde las referencias del cuerpo; plomada al suelo para XY; nivel digital
para la normal. **Fotografiar cada punto medido.**

## 1.4 Medición de atomizadores (una fila por campo y por atomizador)

| parámetro | descripción |
|---|---|
| `posicion_x` `posicion_y` `posicion_z` | centro del disco de atomización, en `CG_tank50` |
| `vector_descarga` | orientación del eje del cono de pulverización |
| `altura_rel_plano_rotor` | **Δz respecto al plano de rotor más próximo** |
| `rotor_mas_cercano` | a qué rotor(es) cae su estela (derivado de 1.3 + 1.4) |
| `punto_efectivo_emision` | si es determinable (foto macro) |
| `soporte_cota_eje` | cota del soporte al eje del brazo |

## 1.5 Cotas para contrastar la relación candidata

Medir lo necesario para **discriminar** las hipótesis alternativas de
`geometry/protocolo_geometria.md` §7.1, no solo para "cuadrar un número":

| parámetro | para qué |
|---|---|
| `separacion_ejes_adyacentes_x`, `_y` | ¿la planta es cuadrada? |
| `separacion_ejes_opuestos_x`, `_y` | contraste directo con el wheelbase declarado (1970 mm) |
| `posicion_longitudinal_brazo` | ¿algún brazo desplazado hacia delante/atrás? |
| `alcance_desplegado_x`, `_y` | contraste con 2650 × 2700 mm oficiales |
| `cota_disco_a_cuerpo` | por si el "desplegado" se mide con/sin guardas |

## 1.6 Repetibilidad: repeticiones INDEPENDIENTES

**No** tres lecturas consecutivas sin moverse: eso mide resolución instrumental, no repetibilidad.

- [ ] Cada magnitud crítica se mide **≥3 veces con RECOLOCACIÓN del instrumento** entre lecturas
      (soltar y volver a montar el útil, volver a plomar, volver a nivelar).
- [ ] Cada repetición es **una fila propia** del CSV, con distinto `setup_id`.
- [ ] Registrar **resolución instrumental** (una vez) y **dispersión entre repeticiones**
      (calculada en la QA). Son cosas distintas y se reportan por separado.

---

# ⛔ PARADA OBLIGATORIA — post-mortem del bloque 1

**No se pasa al bloque 2 sin procesar estas filas.** Ejecutar:

```powershell
python scripts/audit_measurement_csv.py --uav T25P
```

La QA calcula y reporta, **sin corregir**:

1. **Esquema y trazabilidad:** filas `M` sin `uncertainty`/`instrument`; filas sin
   `reference_frame`; `source_class` faltante.
2. **Repetibilidad:** dispersión entre repeticiones independientes por magnitud crítica.
3. **Cierres geométricos y simetrías.** Para rotores opuestos, si el sistema de referencia es
   simétrico respecto del CG cabe esperar:

   ```
   x1 + x3 ≈ 0        y1 + y3 ≈ 0
   x2 + x4 ≈ 0        y2 + y4 ≈ 0
   ```

   > ⚠ **El residuo es información, no un error a corregir.** Si sale grande, las lecturas
   > posibles son: (a) el CG real no coincide con el origen elegido; (b) la planta no es simétrica;
   > (c) error de medición. **Está prohibido ajustar las coordenadas para forzar la simetría.**
   > Se documenta el residuo y se decide con él.

4. **Cierre de distancias:** separación entre ejes adyacentes/opuestos medida vs el wheelbase
   declarado (1970 mm) y vs la relación candidata de §7 del protocolo.
5. **Criterio de paso al bloque 2:** dispersión repetible dentro de lo declarado, sin residuos de
   simetría inexplicados, y sistema de referencia documentado con fotografías.

**Si el bloque 1 no pasa:** se corrige el método y se repite el bloque 1. **No se vuela.**

---

# BLOQUE 2 — ESTADO OPERATIVO

*(Solo si el bloque 1 pasó el post-mortem.)*

## 2.1 Masas: nominal ≠ medida

Los puntos de carga son **nominales derivados** de datos públicos:

| f (tanque) | `nominal_total_mass_kg` | Empuje por rotor **si** reparto uniforme (N) |
|---|---|---|
""" + "\n".join(
        f"| {f:.2f} | {m:.1f} | {t} |" for f, m, t in puntos
    ) + f"""

> 🔴 **Estos valores NO se tratan como masas experimentales reales.**
> Antes de **cada** vuelo hay que **pesar la configuración efectiva** (batería concreta, agua
> realmente cargada, atomizadores instalados). En el CSV deben existir **como variables distintas**:

```
nominal_total_mass_kg    ← el valor de la tabla de arriba (derivado, clase E)
measured_total_mass_kg   ← lo que marca la báscula ese día   (clase M, con incertidumbre)
```

La diferencia entre ambas **es un resultado**, no un detalle: es la primera cuantificación de
cuánto se desvía el planning de la realidad.

## 2.2 CG y actitud

- [ ] `cg_x`, `cg_y`, `cg_z` medidos en cada estado de carga (punto de equilibrio / 4 células).
- [ ] Actitud (cabeceo/alabeo) en hover si es registrable.
- [ ] Contraste: el reparto `mg/4` es **hipótesis**, y el CG medido es lo que puede refutarla.

## 2.3 Ambiente

- [ ] `temp_ambiente_C`, `humedad_relativa_pct`, `presion_hPa`: para poder referir ρ.
- [ ] `viento_ms` (debe ser ~0 para el caso base).

## 2.4 RPM en hover — INDIVIDUAL POR ROTOR

| parámetro | descripción |
|---|---|
| `rpm_hover` | **una fila por rotor** (`element_id` = R1, R2, R3, R4), simultáneas, con `configuracion` = estado de carga |
| `rpm_hover_metodo` | tacómetro óptico de 2 canales / cámara de alta velocidad |

> 🔴 **No registrar una sola "RPM del T25P".** El T25P no es coaxial, pero **diferencias de RPM
> entre R1–R4 son precisamente una de las cosas que pueden falsar el supuesto de reparto uniforme
> `mg/4`**. Es evidencia directa contra una de las hipótesis del modelo, y se pierde si se promedia.

**Orden:** RPM en hover real **primero**; bancada después (context.md §42).

## 2.5 Instrumentos y condiciones

- [ ] Instrumentos **calibrados**, con certificado o fecha de calibración registrada.
- [ ] Resolución de cada instrumento declarada.
- [ ] **Seguridad (R11):** hélices retiradas o bloqueadas en toda medición con el dron energizado;
      bancada de RPM solo si el fabricante lo permite; protocolo de prueba no invasivo.

---

# Criterio de cierre

| Gate | Se cierra con | Artefacto |
|---|---|---|
| **GATE 1A** | bloques 1.1–1.6 con `M`, sin residuos inexplicados | `geometry-v1/T25P/` |
| **GATE 1B** | masas medidas, CG, ambiente y RPM por rotor | se documenta en el log |

```powershell
# QA del CSV (sin corregir nada)
python scripts/audit_measurement_csv.py --uav T25P

# el gate debe salir sin bloqueantes
python scripts/freeze_geometry_v1.py --uav T25P --dry-run
python scripts/freeze_geometry_v1.py --uav T25P --by "<quien>"
python scripts/freeze_geometry_v1.py --uav T25P --verify
```

Si el dry-run sigue dando bloqueantes, **no se congela**: el congelador no tiene flag de forzado.

## Referencias de nivel 0 (momentum theory) — para CONTRASTAR

> Órdenes de magnitud (context.md §12 nivel 0). **Nunca** se reportan como resultado del estudio.

| Derivado | Valor |
|---|---|
| Área de disco total (4 rotores) | {n0['area_disco_m2']} m² |
| Carga de disco a MTOW | {n0['carga_disco_N_m2']} N/m² |
| Empuje por rotor a MTOW si reparto uniforme | {n0['empuje_por_rotor_N']} N = {n0['empuje_por_rotor_kg']} kg |
| Velocidad inducida en hover a MTOW | {n0['v_inducida_hover_ms']} m/s |
| Lado entre ejes (D_axis/√2) | {n0['lado_entre_ejes_m']} m |

Si la RPM medida implica una velocidad inducida muy alejada de {n0['v_inducida_hover_ms']} m/s,
**se revisa antes de construir el modelo** — no se ajusta el modelo para que encaje.
"""
    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text(doc, encoding="utf-8")
    print(f"escrito {DOC.relative_to(ROOT)}")
    print(f"nivel 0 T25P: A_disco={n0['area_disco_m2']} m2, DL={n0['carga_disco_N_m2']} N/m2, "
          f"v_ind={n0['v_inducida_hover_ms']} m/s")
    print("NO se ha medido nada. Campana en dos jornadas con parada obligatoria.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
