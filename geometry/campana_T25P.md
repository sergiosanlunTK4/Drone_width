# Hoja de campaña física — DJI Agras T25P (plataforma piloto)

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
| Masa sin batería | 26.0 kg | P |
| Batería DB800 | 6.6 kg | P |
| Masa con batería | 33.0 kg | P |
| Tanque | 20.0 kg (20 L) | P |
| MTOW pulverización | 53.0 kg | P |
| Diámetro de rotor | 1.27 m (50 in) | P |
| Nº de rotores | 4 | **S** (deck 01, slide 12: 4 brazos sin coaxial) |
| Palas por rotor | 2 | **S** |
| Distancia diagonal entre ejes | 1970 mm | P |
| Motor | estator 100 × 28 mm, KV 59 | P-A + S (imagen rotulada "10028/59KV") |
| Atomizadores | 2 estándar / 4 opcional, separación 1420 mm | P |
| Gota | 50–500 µm | P |

### 1.1 Referencias de nivel 0 (momentum theory) — para CONTRASTAR, no para sustituir

> Solo órdenes de magnitud (context.md §12 nivel 0), calculados con `scripts/prepare_t25p_campaign.py`.
> **Nunca** se reportan como resultado del estudio.

| Derivado | Valor |
|---|---|
| Área de disco total (4 rotores) | 5.067 m² |
| Carga de disco a MTOW | 102.6 N/m² |
| Empuje por rotor a MTOW (si reparto uniforme) | 130.0 N = 13.3 kg |
| Velocidad inducida en hover a MTOW | 6.62 m/s |
| Lado entre ejes (D_axis/√2) | 1.393 m |

**Uso:** si la RPM medida implica una velocidad inducida que se aparta mucho de
6.62 m/s, hay que revisar antes de construir el modelo — no ajustar el
modelo para que encaje.

## 2. Puntos de carga a caracterizar (bloque C)

Masa total = 33.0 + 20.0 · f (kg). Sanity check: f = 1 → 53.0 kg ≈ MTOW 53.0 kg ✓

| f (tanque) | Masa total (kg) | Empuje por rotor si reparto uniforme (N) |
|---|---|---|
| 1.00 | 53.0 | 130.0 |
| 0.75 | 48.0 | 117.7 |
| 0.50 | 43.0 | 105.5 |
| 0.25 | 38.0 | 93.2 |
| 0.00 | 33.0 | 80.9 |

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
uav, block, element_id, parameter, value, unit, uncertainty, method, instrument, timestamp, operator, source_class, reference_frame, configuracion, repetitions, raw_file, notes
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
