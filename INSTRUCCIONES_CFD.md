# Instrucciones para la siguiente conversación — CFD de aspersión con la geometría v2

> **Para empezar:** abre Claude Code en `D:\AUTOMATIONS\DRONEWITH` (la raíz del proyecto) y escribe:
> *"Lee `INSTRUCCIONES_CFD.md` y continúa con el paso 1 del plan."*
> Este archivo resume el estado al 2026-11-22. **Objetivo: base de datos de escenarios para un paper (§5).** Lo que dice aquí manda sobre las guías antiguas cuando se contradigan, sobre todo en geometría y rutas.

---

## 1. Qué hay hecho

### Geometría v2 de las 4 plataformas (lista para CFD)

Visión general: `geometry/models/README_MODELOS_CFD.md`. Código: `scripts/agras_model/`.
Para regenerar: `python scripts/agras_model/run.py all` (~6 min, usa `freecadcmd` de FreeCAD 1.1).

| | T25P | T55 | T70P | T100 |
|---|---|---|---|---|
| Rotores | 4 simples, 50 in | 4 simples, 62 in | 4 simples, 62 in | 8 = 4 pares coaxiales |
| Inclinación del motor (a lo largo del brazo, parte alta hacia dentro) | −2.2° | −2.2° | −2.2° | −3.3° |
| Suelo (Z del modelo) | −0.565 | −0.514 | −0.500 | −0.730 |

Por plataforma, en `geometry/models/<P>_CFD/` (prefijo `<p>_`):
- `<p>_airframe.stl`: pared no-slip, un sólido estanco, en metros.
- `<p>_rotor_disks.stl`: discos actuadores **inclinados**, con **una región por rotor** (`rotor_M1_FR`…; en el T100, `_upper` / `_lower`).
- `<p>_spray_nozzles.stl`: discos de los atomizadores, una región por boquilla.
- `<p>_cfd_coordinates.json`: **la fuente de verdad para los casos**.
  - Rotores: `center_xyz_m`, `disk_normal` (no es (0, 0, 1)), `angular_velocity_unit_vector`, `rotation_seen_from_above`, `swept_area_m2`.
  - Boquillas: `disc_center_xyz_m`, `disc_axis`, `height_above_ground_m`.
  - Además: `ground_plane_z_m`, masas y referencia de momentum theory.
- `<p>_rotor_blades.stl`: palas (solo para MRF o malla deslizante).

Terna: **+X adelante, +Y izquierda (babor), +Z arriba**, dextrógira. Origen XY en el centroide de los bujes; Z = 0 en el plano de los brazos.

### Hechos que cambian lo que dicen los documentos antiguos

- **El T70P y el T55 NO son coaxiales** (4 rotores). `geometry/manifests/t70p_geometry_manifest.json`, `docs/specs/T55.md` y `scripts/build_case_suite.py` todavía los tratan como coaxiales. Hay que corregirlo.
- **El T100 antiguo tenía la terna levógira.** El modelo anterior está guardado en `geometry/models/T100_CFD/_anterior_v1/`.
- Los rotores **no** están en una "planta regular X": el T70P y el T55 tienen la vía delantera más ancha que la trasera.

---

## 2. Entorno de cálculo (verificado el 2026-11-22)

- **OpenFOAM v2412** dentro de WSL Ubuntu: `/usr/lib/openfoam/openfoam2412`. Hay `python3` y `mpirun`.
- Proyecto visto desde WSL: **`/mnt/d/AUTOMATIONS/DRONEWITH`**. Las guías antiguas dicen `/mnt/c/Users/Dimasur/Downloads/...`: **esa ruta ya no vale**.
- El agente **sí** puede ejecutar en WSL desde Bash:
  ```bash
  wsl.exe -d Ubuntu -- bash -lc 'cd /mnt/d/AUTOMATIONS/DRONEWITH && python3 scripts/foam_run.py check'
  ```
- **No** hagas `source .../etc/bashrc` dentro de scripts: corta la ejecución. Usa `scripts/foam_run.py` (ver `geometry/COMO_EJECUTAR_CFD0.md`).
- Recursos de WSL: **8 núcleos y ~7 GB de RAM**. Eso alcanza para unos **3–5 M celdas** con `simpleFoam` en paralelo. Si hace falta más, el propietario puede ampliar la memoria en `%UserProfile%\.wslconfig` (`memory=…`); pídeselo, no lo cambies tú.

---

## 3. Reglas del proyecto (obligatorias)

1. **Clasificación de cada dato:** P (ficha DJI) · P-A (DJI Academy) · M/O (medido por el propietario) · S (medido en imagen) · I (inferido) · E (estimado) · D (desconocido). No se rellena un D con supuestos.
2. **Ningún resultado inventado.** Las tablas `cfd_*` solo se pueblan desde salidas reales de OpenFOAM, mediante `scripts/postprocess_case.py`.
3. **Orden de gates** (`Metodología de cálculo.md`, §10): **CFD-0 → suite → Lagrangiano**. No se escala sin cerrar el gate anterior. *Un caso que corre sin errores no es un caso correcto.*
4. Cada avance va como una nueva *Entry* en `research_log.md`, con lo verificado, lo que no y por qué.
5. Todo dentro del proyecto. Nada importante solo en carpetas temporales.
6. Idioma de trabajo: español.

---

## 4. Estado del pipeline CFD existente

Lee en este orden:
1. `Metodología de cálculo.md` §10 (gates y fuente prescrita).
2. `evidence/BUG_conceptual_06_actuationDisk.md`.
3. `evidence/BUG_07_normalizacion_fvOptions.md`.
4. `geometry/coaxial_thrust_split.md`.
5. `geometry/COMO_EJECUTAR_CFD0.md`.
6. Las últimas entradas de `research_log.md` (Entry 016–018).

**Decisiones vigentes:**
- **`actuationDiskSource` está retirado** (bug #6): con flujo perpendicular al disco da T ≈ 0. Se usa una **fuente de momento prescrita** (`vectorSemiImplicitSource`) por rotor, con ∫f dV = T_i. Arquitectura C→B: los empujes salen del equilibrio de fuerzas y momentos (`scripts/force_chain.py`), y el reparto coaxial es un **parámetro barrido** (0.5 / 0.6 / 0.7).
- **Bug #7 abierto:** la normalización de `vectorSemiImplicitSource` en v2412 divide por el volumen seleccionado con `volumeMode absolute`. Verifica la formulación (`specific` frente a `absolute`) contra `verify_prescribed_force.py` antes de fiarte de la magnitud.

**CFD-0** (un caso T25P de hover, `scripts/build_hover_case.py` + `scripts/gate_cfd0_hover.sh`): **ABIERTO**. En `evidence/cfd0_conditions.json`:
- Condición 1 (fuerza aplicada por rotor): pasa.
- Condiciones 2–5 (balance de momento, convergencia, simetría, orden de magnitud del downwash): sin evaluar, porque falta una ejecución convergida.

**⚠️ Los 131 casos de `cfd/cases/` están OBSOLETOS**, generados con la geometría antigua:
- planta regular X;
- T55 y T70P coaxiales;
- `diskDir (0 0 -1)`, sin inclinación;
- cuerpo mallado desde `geometry/models/<UAV>_control.stl` (cajas de control).

No los ejecutes ni los postproceses. Muévelos a `cfd/cases/_obsoletos_geometria_v1/` (pregunta antes de borrar nada).

Scripts relevantes: `build_case_suite.py` (DOE + casos), `build_hover_case.py`, `build_prescribed_momentum.py`, `mesh_zone_volumes.py`, `verify_prescribed_force.py`, `force_chain.py`, `tilt_model.py` (actitud en avance), `lagrangian_injection.py`, `build_lagrangian_spec.py`, `postprocess_case.py`, `foam_run.py`, y las plantillas en `cfd/templates/`.

---

## 5. Objetivo del propietario (2026-11-22) y diseño de la base de datos

**Objetivo:** un paper basado en una **base de datos de muchos escenarios**. Cada escenario se define por las **variables programables** del dron y guarda:
- el **mapa de deposición D(x,y)**;
- el **ancho efectivo real W_eff**;
- el **coeficiente de variación CV**.

Además hay que determinar si la **variación de la masa en el tiempo** (el vaciado del tanque según la programación) es significativa o despreciable (H5 y H8).

**Variables programables (app DJI):**
- altura H;
- velocidad V;
- tamaño de gota d. Los atomizadores son **centrífugos, no presurizados**: d lo fija la RPM del disco, no la presión;
- configuración de aspersores, 2 o 4;
- dosis (L/ha) e interlineado de ruta, que juntos fijan el caudal Q.

### 5.1 Clave de eficiencia: desacoplar el aire de las gotas

La fracción volumétrica de líquido en el aire es del orden de 10⁻⁶, así que **las gotas no alteran el campo de aire** (acoplamiento en un sentido). Hay que verificarlo **una vez** en CFD-0, comparando acoplamiento en un sentido y en dos.

Si se confirma, la simulación se parte en dos niveles:

| Nivel | Qué depende de él | Coste | Clave |
|---|---|---|---|
| **A. Campo de aire** (RANS estacionario) | plataforma, V, H, **fracción de carga f** (empuje = m·g, actitud θ(V, f) en avance) y reparto coaxial (solo T100) | **caro** (horas) | `air_id` |
| **B. Gotas sobre un campo A congelado** (Lagrangiano) | d (RPM del atomizador), configuración 2/4, caudal Q | **barato** (minutos), **muchos por cada A** | `spray_id` → `air_id` |

**Configuración 2/4 frente al aire:**
- **T55:** los 4 atomizadores van **atrás**, dos por brazo trasero en la misma barra (confirmado por el propietario el 2026-11-22). La barra y los 4 cuerpos están en el fuselaje en ambas configuraciones, así que 2/4 es siempre nivel B.
- **T100:** la barra LS100 lleva los 4 cuerpos, así que también es siempre nivel B.
- **T25P y T70P:** los atomizadores opcionales van **bajo los motores delanteros** (confirmado por el propietario el 2026-11-22). En la configuración de 4 añaden cuerpos bajo los rotores delanteros, así que hay que **medir su efecto sobre el aire** en uno o dos casos (con y sin cuerpos). Si es despreciable, 2/4 es nivel B; si no, la configuración pasa al nivel A en estas dos plataformas.

Con esto, cada simulación de aire alimenta decenas de escenarios de gotas, y la base de datos crece sobre todo por el nivel B, que es barato.

### 5.2 Masa en función del tiempo (vaciado)

- **Caudal:** Q [L/min] = dosis [L/ha] × V [m/s] × interlineado [m] × 60 / 10⁴.
- **Masa:** m(t) = m_vacío + ρ·(V_tanque − Q·t). La fracción de carga es f(t) = 1 − Q·t / V_tanque.
- **Hipótesis cuasi-estacionaria:** el tanque se vacía en minutos (el T70P, con 70 L a 30 L/min, en unos 2.3 min). La estela se renueva en ~D/v_i ≈ 0.2–0.3 s. Por tanto cada instante equivale al caso estacionario con f(t), y el vaciado se modela con **niveles discretos de f** (p. ej. 1.0 / 0.5 / 0.0, o 5 niveles si resulta significativo) e interpolación. **Hay que declarar esta hipótesis en el paper.**
- **Efectos de f:**
  - empuje y downwash: v_i ∝ √(m·g); del T70P lleno al vacío, v_i cae ~1.5×;
  - actitud en avance, más inclinación con el tanque vacío (H8): ya está en `scripts/tilt_model.py` / `force_chain.py`;
  - el abanico centrífugo se inclina con el dron.
- **Criterio de significancia (H5):** a igual (V, H, d, configuración), comparar W_eff, CV y D(x,y) entre f = 1 y f = 0. Si la diferencia queda por debajo del presupuesto de incertidumbre (CV numérico + independencia de malla), el efecto es **no significativo** y se documenta así, **sin asumirlo de antemano**.
- **Resultado derivado:** una tabla por escenario programado de **cómo evoluciona W_eff(t) y CV(t) a lo largo de una pasada**, es decir, si el operador debería ajustar el interlineado según el tanque se vacía.

### 5.3 Esquema de base de datos (ampliar `scripts/build_database.py` y `dronewith.sqlite`, sin borrar lo que ya existe)

- `air_cases(air_id, plataforma, V, H, f, masa_kg, theta_actitud_deg, split_coax, geometria_version, estado, ...)`
- `spray_cases(spray_id, air_id, d_um, rpm_atomizador, config_atom (2|4), Q_Lmin, dosis_Lha, interlineado_m, estado, ...)`
- `cfd_airflow(air_id, ...)`: la tabla actual, ahora con clave `air_id`.
- `deposition_maps(spray_id, archivo_mapa, nx, ny, dx, dy, n_particulas, ...)`. El mapa D(x,y) se guarda como archivo (`results/maps/<spray_id>.npz`), no como JSON gigante dentro de SQLite.
- `swath_metrics(spray_id, W_eff_m, CV_pct, interlineado_recomendado_m, asimetria_pct, deriva_fuera_pct, p10/p50/p90, ...)`
- `run_log(id, tipo (air|spray), ref_id, inicio, fin, horas_cpu, celdas, convergido, host)`: medir el coste real sirve para planificar.
- Mantener `origen_dato` y `provenance`. Los casos antiguos `cases` (geometría v1) se marcan como obsoletos, no se borran.
- **Cola reanudable:** un script `scripts/run_queue.py` que tome los casos `pendiente` de la base de datos, los ejecute en WSL, marque `hecho` o `fallido` y continúe tras una interrupción. Sirve para correr de noche durante días.

### 5.4 Volumen de trabajo

Estimación **a confirmar con el tiempo real de CFD-0**, que se registra en `run_log`:
- 5 V × 4 H × 3 f = 60 casos de aire por plataforma, unos 240 en total. A ~1–3 h cada uno con 8 núcleos, son **10–30 días de cálculo continuo** solo para el aire.
- 5 d × 2 configuraciones ≈ 10 escenarios de gotas por cada caso de aire, unos 2400 en total, a minutos cada uno.
- Si no alcanza: usar un DOE de llenado de espacio (hipercubo latino) en lugar de una malla completa, más un surrogate por plataforma (ya previsto en el plan maestro), o cómputo externo. **Que decida el propietario con los tiempos reales de CFD-0 sobre la mesa.**

### 5.5 Realismo máximo y rejilla de escenarios (indicaciones del propietario, 2026-11-22)

**El propietario quiere la simulación más real posible.** Lo que sigue lo hace realista **sin** multiplicar el coste.

**Superposición exacta (acoplamiento en un sentido, sin coalescencia):** sobre un campo de aire congelado, las gotas no interactúan entre sí. Por tanto, para cada caso de aire:
1. **Una ejecución Lagrangiana por boquilla y por clase de tamaño** (10, 50, 100, …, 500 µm), registrando los impactos de cada clase por separado. Cada clase evoluciona con su propia evaporación y dispersión turbulenta.
2. **Cualquier espectro real** (los atomizadores no producen gotas de un solo tamaño: Rosin-Rammler o log-normal alrededor del VMD programado) = **suma ponderada de las clases**. El "tamaño de gota" de la app es el VMD (Dv50), y la dispersión del espectro se fija por modelo de atomizador (de bancada o literatura; declarar la clase). Referencia aportada por el propietario: Guo et al. (2025), ficha en `literature/guo2025_downwash_crosswind/FICHA.md`. **No contiene el espectro de atomizadores centrífugos** (usa boquillas de abanico a presión): sirve como antecedente y como referencia de error de validación (~27–30 %). **El espectro de los atomizadores DJI sigue en D**: buscar otra referencia o pedir una medición de bancada.
3. **Configuración 2 o 4** = suma de las boquillas activas, cada una con Q/2 o Q/4.
4. **Caudal / dosis (L/ha):** con acoplamiento en un sentido, D(x,y) es **lineal** en Q, así que el W_eff y el CV normalizados **no dependen de la dosis**. La rejilla de 5 a 120 L/ha cada 5 (24 valores) cuesta **cero simulaciones extra**: es un escalado exacto en el postproceso. La dosis solo influye en (a) la masa absoluta depositada y (b) **la velocidad de vaciado** (§5.2), que vincula la dosis con la carga f(t).
   - **Restricción física:** Q = dosis × V × interlineado / 10⁴ no puede superar el caudal máximo de la bomba (con 2 / 4 aspersores): **T25P 16 / 24 L/min · T55 40 / 50 · T70P 30 / 40 · T100 30 / 40** (P; T55 del propietario). Las combinaciones imposibles se marcan como *no realizables* y no se reportan.
   - Verificar en CFD-0 que el acoplamiento en un sentido se cumple también a la dosis máxima (120 L/ha a velocidad alta). Si no, la dosis pasa a ser variable del nivel A en ese extremo.

**Rejillas:**

| Variable | Rejilla | Nivel | Simulaciones |
|---|---|---|---|
| Tamaño de gota | 10, 50, 100, 150, …, 500 µm (11 clases) | B | 11 por boquilla y caso de aire. **10 µm solo con la boquilla de niebla opcional** (P-A: estándar 50–500, niebla 10–500) |
| Dosis | 5–120 L/ha cada 5 | postproceso | 0 |
| Configuración | 2 / 4 | postproceso (superposición) | 0 |
| Altura H | 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, **6.0 m (máximo, propietario)** | A | — |
| Velocidad V | 0 (hover) a V_max cada 1 m/s. **T25P: 0–10 m/s (36 km/h); T55, T70P y T100: 0–20 m/s (72 km/h)** (propietario) | A | — |
| Carga f | 1.0 / 0.5 / 0.0, ampliar si H5 sale significativa | A | — |

**El cuello de botella es el nivel A.** Con la malla completa salen 8 H × 21 V × 3 f = 504 casos para el T55, el T70P y el T100, y 264 para el T25P: **~1 800 simulaciones de aire**, inviable en un portátil con RANS de calidad. Estrategia propuesta, que debe aprobar el propietario:
1. **Etapa 1, malla gruesa:** H = {1.5, 2.5, 3.5, 5} × V = {0, 2, 5, 8, 12, 16, 20} (T25P: {0, 2, 4, 6, 8, 10}) × f = {1, 0}.
2. **Validación de la interpolación:** simular puntos intermedios **no usados** para interpolar y medir el error de W_eff, CV y D(x,y). Así se cumple que *no queden datos demasiado alejados*: el error se mide, no se supone.
3. **Refinamiento adaptativo:** añadir casos solo donde el error supere el umbral (p. ej. > 5 % en W_eff o > 2 puntos de CV), típicamente en la transición hover → avance (V bajas) y a alturas bajas (efecto suelo).
4. Registrar el error de interpolación en la base de datos y en el paper.

**Realismo del aire** (decidir en CFD-0 comparando con la fuente uniforme actual):
- **Rotor:** sustituir el disco de empuje uniforme por un **disco de elemento de pala** (`rotorDiskSource` de OpenFOAM) con la geometría de pala del modelo v2 (cuerda y torsión), la **RPM de la telemetría** del propietario y un **trim al empuje objetivo** (`targetCoeffTrim`). Da la distribución radial de carga y el **giro de la estela** (swirl), que afectan al abanico. Polares del perfil: I, declararlas.
- **Inclinación del motor** (ya en la geometría) y **actitud del dron** θ(V, f) del trim en avance.
- **Suelo:** en avance, referencia del dron con el suelo **móvil** a −V (no pared fija) para no inventar una capa límite; efecto suelo completo.
- **Turbulencia:** k-ω SST, malla refinada en estelas y en la zona de atomizadores; independencia de malla en CFD-0. Las simulaciones transitorias (URANS/LES) quedan para un subconjunto de validación, no para la suite.
- **Gotas:** arrastre dependiente de Re, gravedad, **dispersión turbulenta estocástica**, **evaporación a 28 °C y 70 % HR** (decisiva para 10–100 µm), inyección desde el borde del disco centrífugo (velocidad tangencial ω·R_disco, plano inclinado según `disc_axis`).
- **Validación experimental:** la hará **otro equipo** (propietario, 2026-11-22). Nuestro trabajo: (a) acordar con ellos los escenarios y las condiciones exactas de ensayo (altura, velocidad, dosis, gota, configuración, carga, condiciones ambientales) **antes** de que midan; (b) entregar las predicciones en el mismo formato y la misma rejilla que sus colectores (D(x,y) en los puntos de los papeles hidrosensibles, W_eff, CV); (c) comparar con métricas definidas de antemano. Sin esa comparación, el paper no puede afirmar que el modelo es real.

---

## 6. Plan

### Paso 0 — Base de datos y cola de escenarios (§5.3), antes de lanzar nada masivo
Implementa el esquema de dos niveles y la cola reanudable, y genera la matriz de escenarios v2. Los casos de aire quedan `pendiente`; nada se ejecuta todavía.

### Paso 1 — Conectar la geometría v2 al generador de casos

Crea `scripts/agras_model/cfd_geometry.py`, un adaptador que lea `<p>_cfd_coordinates.json` y devuelva para cada rotor: centro, normal, área, sentido de giro y si es superior o inferior. Después:

- En `build_case_suite.py` y `build_hover_case.py`, sustituye la planta "regular X" y la bandera `coaxial` codificada a mano por el adaptador (T25P/T55/T70P = 4 rotores; T100 = 8).
- En snappyHexMesh, la pared es `<p>_airframe.stl`. Las `cellZone` de los rotores salen de `<p>_rotor_disks.stl` (regiones por rotor, `cellZoneInside inside`) o, como alternativa, de un `topoSet` con `cylinderToCell` usando centro ± (espesor/2)·normal. En ambos casos comprueba los volúmenes con `mesh_zone_volumes.py`, que deben salir ≈ π r² h.
- En `build_prescribed_momentum.py`, la fuerza sobre el aire de cada rotor es **F_i = −T_i · disk_normal_i**, vectorial e inclinada, no (0, 0, −T).
- El dominio usa como suelo el `ground_plane_z_m` del modelo más la altura de vuelo H del DOE. Ojo: el suelo del modelo está en el contacto de los patines, no en el plano de los rotores.
- Corrige el manifiesto del T70P y `docs/specs/T55.md` (4 rotores, no coaxiales), citando la evidencia.

### Paso 2 — Cerrar CFD-0 con la geometría v2

Caso T25P en hover, `U_inf = 0`, a la altura del DOE típica. Además: **medir el tiempo de cálculo** (`run_log`) y **verificar el desacoplamiento aire/gotas** (§5.1) en este mismo caso.
1. Malla gruesa primero (< 1.5 M celdas); `checkMesh` sin errores.
2. Ejecuta y comprueba las 5 condiciones de `gate_cfd0_hover.sh` / `verify_prescribed_force.py`:
   - fuerza integrada = T_i por rotor;
   - balance global (fuerza en el suelo ≈ ΣT);
   - residuales y magnitudes estables;
   - simetría izquierda/derecha;
   - downwash del orden de momentum theory (T25P en MTOW: v_i ≈ 6–7 m/s; ver el JSON).
3. Estudio de independencia de malla en 2–3 niveles.
4. Registra la Entry y actualiza `evidence/cfd0_conditions.json`.

### Paso 3 — Suite DOE (nivel A: aire)

Corre la cola de casos de aire (§5.3), primero la comparación f = 1 frente a f = 0 para decidir pronto si el vaciado importa (H5). Regenera los casos con el paso 1. Ejecuta primero un subconjunto representativo por plataforma (el presupuesto de cómputo es limitado), y luego el resto. Usa `postprocess_case.py` para poblar `cfd_*`.

### Paso 4 — Lagrangiano (nivel B: deposición D(x, y), W_eff, CV)

Muchos escenarios de gotas por cada campo de aire congelado; los resultados van a `deposition_maps` y `swath_metrics`.

Ver `build_lagrangian_spec.py` y `lagrangian_injection.py`.
- Inyección desde `disc_center_xyz_m` de cada boquilla, como lámina radial en el plano **perpendicular a `disc_axis`** (inclinado). La velocidad de borde es ω·R_disco, hasta 14 000 rpm (P-A).
- Respeta la configuración: el T55 usa los atomizadores exteriores como estándar; el T100, la barra LS100.
- D(x, y) se obtiene contando impactos en el plano receptor, nunca con una fórmula analítica.

---

## 7. Preguntas abiertas para el propietario (hazlas cuando afecten al paso en curso)

1. **T100, X de los atomizadores.** Su medida: −0.875 / −0.775 m. Las fotos dan −0.58 (cenital) y −0.68 m (lateral). Hoy se usa su medida. Es crítica para la deposición; ver `geometry/models/T100_CFD/t100_overlay_top.png`.
   - **Geometría real de la barra (propietario, 2026-11-23):** son **dos barras rectas**, una por lado, que **salen del tren de aterrizaje**. Cada una es un solo eje, sin cambios de ángulo, y lleva los dos atomizadores de su lado. El modelo actual la dibuja con quiebros y anclada al cuerpo: **hay que corregirlo**.
   - **Conflicto pendiente:** una barra recta por los dos atomizadores medidos (X −0.775 y −0.875) cruza la anchura del tren en X ≈ −0.75, pero la pata trasera del tren (fotos) está a esa altura en X ≈ −0.27. **El propietario volverá a medir** la distancia a lo largo del eje X entre la pata trasera, donde nace la barra, y cada atomizador. Hasta entonces **no se cambia** la geometría (`scripts/agras_model/platforms/t100.py`, `NOZZLES` y `_boom`). Con la medida: barra recta = tubo desde el punto de anclaje en la pata hasta 5 cm más allá del atomizador exterior, con los atomizadores colgando sobre ella.
2. **T55:** el ángulo de la V de los atomizadores (hoy ±10°, I) y la planta (inferida de la familia T70P).
3. **T25P y T55:** sentido de giro de cada motor (hoy se asume la convención DJI tradicional, I).
4. RPM y reparto de empuje coaxial: el propietario tiene **telemetría** (RPM por motor, del atomizador, de las bombas y caudal; Metodología §11). Pídela para la fase 1B.

5. ~~Altura máxima~~ → **6 m** (respondido el 2026-11-22).
6. ~~Atomizadores opcionales del T25P y el T70P~~ → **delante** (respondido).
7. **Espectro de gota real:** el propietario no lo conoce; sugiere Guo et al. 2025 (ver §5.5). Falta el PDF en `literature/`. Preguntar también si dispone de la boquilla de niebla (la única que llega a 10 µm).
8. ~~Caudal máximo de la bomba del T55~~ → **40 / 50 L/min** (respondido).
9. ~~Campaña de validación~~ → **la hace otro equipo**: coordinar escenarios y formato (§5.5).

Para cambiar cualquier cota: `scripts/agras_model/platforms/<p>.py`, luego `python scripts/agras_model/run.py <p>`, y después regenerar los casos.
