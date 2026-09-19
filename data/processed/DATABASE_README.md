# Base de datos del proyecto — `data/processed/dronewith.sqlite`

Generada por `scripts/build_database.py`. Inspeccionable con `scripts/check_database.py`.

---

## ⚠ Qué contiene y qué NO contiene

| Capa | Estado | Origen |
|---|---|---|
| Plataformas (4) | ✅ poblada | ficha oficial + Academy + propietario |
| Casos especificados (128) | ✅ poblada | DOE por plataforma, LHS estratificado |
| **Métricas analíticas (128)** | ✅ poblada | **física analítica calculada de verdad** |
| Resultados de CFD de aire | ❌ **vacía a propósito** | requiere ejecutar OpenFOAM |
| Resultados de CFD de deposición | ❌ **vacía a propósito** | requiere CFD + seguimiento Lagrangiano |
| Métricas de franja CFD | ❌ **vacía a propósito** | requiere CFD |
| Validación experimental | ❌ vacía | requiere la campaña de medición |
| Surrogates | ❌ vacía | requiere CFD validado (GATE 4) |

**La capa analítica NO es CFD y no se etiqueta como tal.** Cada fila lleva
`origen_dato = "ANALITICO (...). NO ES CFD. Requiere validacion."`.

**Las tablas `cfd_*` están vacías por diseño.** Ningún resultado de simulación se ha
inventado: rellenarlas sin ejecutar OpenFOAM invalidaría el proyecto entero (context.md §7, §51).

---

## Esquema

```
platforms            4 filas   geometría y masas de cada UAV, con clasificación de fuente
cases              128 filas   DOE: V, H, DV0.5, carga, atomizadores, split coaxial
analytic_metrics   128 filas   física analítica (momentum theory + difusión + solape)
cfd_airflow          0 filas   campos de aire por caso y malla          [se puebla con CFD]
cfd_deposition       0 filas   D(x,y) por caso                          [se puebla con CFD]
cfd_swath_metrics    0 filas   W_eff, CV, interlineado por caso         [se puebla con CFD]
experiments          0 filas   validación experimental                  [se puebla midiendo]
surrogate_models     0 filas   modelos reducidos                        [GATE 4]
provenance           4 filas   trazabilidad: qué es dato y qué no
v_estado             vista     conteo global de ocupación
```

---

## Qué calcula la capa analítica (y con qué modelo)

| Métrica | Modelo | Validez |
|---|---|---|
| `area_disco_total_m2` | geometría | exacta si la geometría es correcta |
| `carga_disco_N_m2` | `T/A` | exacta |
| `v_inducida_hover_ms` | momentum theory, disco ideal | orden de magnitud (§12 nivel 0) |
| `v_downwash_nucleo_ms` | `2·v_ind` | orden de magnitud |
| `potencia_ideal_W` / `potencia_estimada_W` | `P = T·v_i` con FM = 0,70 | estimación |
| `v_terminal_gota_ms` | Stokes + iteración de arrastre (Schiller-Naumann) | **validada contra valores canónicos** |
| `Stokes_number` | `τ_p/τ_f` | exacta dada la geometría |
| `dominancia_estela` | integración numérica de `dz/dt = v_term + v_estela(z)` | modelo declarado |
| `sigma_y_m`, `ancho_efectivo_analitico_m` | difusión turbulenta `√(σ₀² + 2u'L·t)` con `u' = 0,15·v_ind` | **modelo grueso: requiere validación CFD** |
| `interlineado_recomendado_m` | solape de gaussianas, criterio CV ≤ 20 % | depende del modelo de σ_y |

Uso previsto: **planificación y contraste**, nunca como resultado del estudio.

---

## Hallazgo físico relevante

El número de Stokes separa dos regímenes, y la frontera cae **dentro** del rango operativo:

| d (µm) | St | Régimen | Implicación |
|---|---|---|---|
| 100 | **0,55** | sigue las líneas de flujo | alta exposición a la estela, sensible a deriva |
| 200 | 1,74 | transición | comportamiento mixto |
| 300 | 3,73 | inercial | penetra la estela |
| 500 | **11,4** | balístico | apenas lo desvía el downwash |

Esto es el fundamento cuantitativo de **H6** (regímenes de Stokes) y explica por qué el tamaño de
gota es una variable de primer orden: no cambia el resultado un poco, **cambia el régimen**.

---

## Cómo se pueblan el resto de capas

```powershell
# 1. verificar que los casos están estructuralmente completos
bash scripts/run_cfd_suite.sh --dry-run

# 2. ejecutar (requiere OpenFOAM; NO disponible en el entorno de desarrollo actual)
bash scripts/run_cfd_suite.sh all 8

# 3. el runner llama a postprocess_case.py por caso, que escribe en cfd_airflow
#    (solo si el caso CONVERGIÓ; si no, registra el fallo y no escribe métricas)

# 4. revisar
python scripts/check_database.py
```

Los pasos de **deposición** (`cfd_deposition`) requieren además el seguimiento Lagrangiano de gotas,
que se implementa sobre los campos de aire ya validados.

---

## Advertencia de uso

- `analytic_metrics` **no** es resultado del estudio. Es planificación.
- La geometría de sus entradas es `P/S/O/I` — **no `M`**. Ver `geometry/presupuesto_hipotesis.md`.
- **No** alimentar la app ni el surrogate con esta capa.
- Cuando existan mediciones (`M`) y CFD ejecutado, esta capa se recalcula y se contrasta: ahí es
  donde empieza el resultado científico.
