# Research Log: Aerodynamics, Downwash, and Spray Deposition of DJI Agras Agricultural UAVs

## Project Metadata
- **Project Title:** Comprehensive Aerodynamic, Downwash, and Spray Deposition Modeling of DJI Agras Agricultural Multirotor Platforms (T25P, T55, T70P, T100)
- **Principal Investigation Role:** Principal Scientific Research Agent
- **Target Deliverables:** High-impact peer-reviewed scientific publications, open-access validated datasets, and high-fidelity reduced-order surrogate models for operational decision support.
- **Repository Standard:** Open Science / Full Reproducibility Framework (OpenFOAM, Python, ParaView, Open Data).

---

## State Tracker
- **Current Phase:** `PHASE_01_SPECIFICATIONS` (en corrección). **GATE 1A ABIERTO** y **GATE 1B ABIERTO** (partidos en Entry 009).
- **Active Goal / próximo hito:** **cerrar GATE 1A — geometry validated**, no ejecutar OpenFOAM.
  Requiere la campaña de medición física (bloques A/B del protocolo) sobre las 4 plataformas.
- **Transition Gates:** criterios de cierre en `geometry/protocolo_geometria.md` §8.
  - **1A** bloquea mallado, geometría CFD y dominio. Al cerrar: congelar `geometry-v1` con hash.
  - **1B** bloquea CFD cuantitativo y toda afirmación de magnitud de downwash; **no** bloquea
    topología, dominio, refinamientos ni comparaciones relativas.
- **Regla vigente:** con 1B abierto, todo CFD es **exploratorio** y no entra al dataset ni al paper
  como dato de la plataforma real. El DOE no se rehace hasta tener los rangos medidos.

### Orden de ejecución acordado (2026-09-14, vinculante)

```
recaptura T55/T70P/T100 ✅  →  auditoría A9/A10 ✅  →  campaña T25P 🔄 EN CURSO (investigador)
   →  post-mortem metodológico  →  campaña v2  →  generar T55/T70P/T100
```

**En paralelo (Entry 015):** el **estudio paramétrico está habilitado** con geometría declarada
(clases `P`/`P-A`/`S`/`O`/`I`/`E`) y presupuesto de hipótesis explícito
(`geometry/presupuesto_hipotesis.md`). La medición **no es prerrequisito para empezar**: es una
mejora de retorno alto y coste bajo que avanza en paralelo, y los valores `O`/`I`/`E` se **promueven**
a `M` cuando lleguen las filas.

**Por qué este orden:** las hojas de campaña de T55/T70P/T100 **no se preparan todavía**.
El piloto T25P existe para descubrir qué falta en la plantilla (campos, repeticiones,
definición de incertidumbre); generarlas antes produciría cuatro documentos a corregir.
Y preparar campañas con incertidumbre documental abierta arriesga **medir lo innecesario**.

- **Regla de actualización de evidencia:** ante nueva evidencia documental se actualiza
  **únicamente `evidence/CONFLICTS.md`**. Ningún manifiesto ni `rotor_count` cambia
  automáticamente, aunque una captura parezca resolverlo. Promover a `M` exige **convergencia
  entre tabla + fotografía/diagrama + inspección física**.

---

## Log Entries

### Entry 001 | Initialization & Scaffolding
- **Date:** 2026-09-13
- **Action:** Initialized standardized research repository structure:
  - `/research`: Problem statements, theoretical derivations, methodology blueprints.
  - `/docs`: Project architecture, meeting notes, guidelines.
  - `/literature`: Systematic literature review database, bibtex, literature synthesis matrices.
  - `/data/raw` & `/data/processed`: Experimental anemometry, spray deposition collector data, CFD mesh outputs.
  - `/geometry`: Parametric CAD models, rotor airfoils, hub assemblies, atomizer placement coordinates.
  - `/cfd`: OpenFOAM cases (`cases/`), base templates (`templates/`), post-processed simulation results (`results/`).
  - `/experiments`: Protocols, instrumentation calibration curves, sampling grids, field trial logs.
  - `/surrogate`: Gaussian Process Regressors, Polynomial Chaos, XGBoost / neural surrogates, optimization algorithms.
  - `/notebooks` & `/scripts`: Reproducible analysis pipelines, automated post-processing, validation scripts.
  - `/figures`: Publication-quality vector graphics (SVG, PDF, high-res PNG).
  - `/paper` & `/supplementary`: LaTeX manuscript, supplementary material, response to reviewers.
  - `/logs`: Execution logs, convergence monitors, mesh independence metrics.
- **Decision:** Establish strict gatekeeping protocol. No CFD simulations will be executed until physics formulation, geometry boundaries, mesh independence metrics, and experimental validation protocols are formally established and approved.

### Entry 002 | Methodological & Scientific Scrutiny
- **Hypotheses Under Review:**
  - *H1 (Swath non-universality):* Rejection of single nominal swath across variable flight envelopes.
  - *H2 (Three-way interaction):* Deposition distribution $D(x,y)$ exhibits strong non-linear coupling among forward velocity ($V_\infty$), flight altitude ($H$), and droplet diameter spectrum ($d_{10}, d_{50}, d_{90}$).
  - *H3 (Atomizer positioning & rotor wake ingestion):* Front vs. rear vs. outboard atomizer placement alters droplet wake ingestion, rotor tip vortex entrainment, and ground spray widening.
  - *H4 (Platform aerodynamic specificity):* Different airframe geometries, coaxial rotor wake contractions, and disc loadings require independent CFD and surrogate modeling rather than simple scaling laws.
  - *H5 (Dynamic payload effect):* Tank depletion (100% to 0%) alters thrust demand, downwash velocity magnitude, and wake contraction angle, modifying deposition profiles over time $m(t)$.
  - *H6 (Stokes number regime & droplet drift susceptibility):* Droplets with $St \ll 1$ follow rotor wake streamlines into peripheral vortex rings, while $St \ge 1$ droplets ballistic penetrate the downwash core.
  - *H7 (Pareto operational optimization):* Existence of a Pareto-optimal operating front reconciling high swath width (productivity), low coefficient of variation ($CV \le 15-20\%$), and minimal off-target drift.
- **Engineering Data Audit:** Classification of all platform parameters into `public`, `measured`, `inferred`, `estimated`, and `unknown` to eliminate unverified assumptions.

### Entry 003 | Delivery of RESEARCH_ARCHITECTURE_V1.md
- **Date:** 2026-09-13
- **Action:** Completed and stored `research/RESEARCH_ARCHITECTURE_V1.md` containing the comprehensive 24-point research architecture, governing equations, multi-fidelity CFD comparison, DOE, surrogate strategy, and explicit Gate 1 stop/go criteria.
- **Status:** Pending Principal Investigator review prior to transitioning to `PHASE_01_SPECIFICATIONS` and `PHASE_02_GEOMETRY`.

### Entry 004 | Completion of Engineering Specifications (Phase 1)
- **Date:** 2026-09-13
- **Action:** Created detailed engineering specifications matrix (`research/specifications/dji_agras_engineering_specs.md`) for DJI Agras T25P, T55, T70P, and T100 platforms, classifying all physical dimensions, masses, rotor properties, and atomizer configurations into public, measured, inferred, and estimated categories.
- **Status:** Gate 1 satisfied. Transitioning to CFD template preparation (`PHASE_03_BASELINE_CFD`).

### Entry 005 | Computational Framework Scaffolding & DOE Generation
- **Date:** 2026-09-13
- **Action:** 
  - Established OpenFOAM case dictionary template (`cfd/templates/openfoam_case_template.dict`) incorporating SST $k-\omega$ turbulence closure, water fluid properties at $28\ ^\circ\text{C}$, and PISO pressure-velocity coupling schemes.
  - Developed and executed Latin Hypercube Sampling (LHS) script (`scripts/generate_doe.py`) generating a 100-run master DOE matrix across all four platforms (`data/processed/doe_master_plan.csv`) spanning forward velocity, flight altitude, droplet median diameter, payload fraction, and atomizer configurations.
- **Status:** Advancing toward surrogate modeling and deposition post-processing scripts.

### Entry 006 | Phase 2 Geometry & Phase 3 CFD Mesh Setup
- **Date:** 2026-09-13
- **Action:**
  - Created parametric geometry manifest generator (`scripts/generate_geometry_manifest.py`) defining the 3D spatial coordinates, rotor rotation directions, and dual/quad atomizer configurations for the DJI Agras T25P platform (`geometry/t25p_geometry_manifest.json`).
  - Developed OpenFOAM `snappyHexMeshDict` template (`cfd/templates/snappyHexMeshDict.template`) featuring multi-level refinement boxes around rotor wake zones and surface feature mesh controls for automated boundary layer generation.
- **Status:** Transitioning to baseline CFD automated run scripts and particle tracking setup.

### Entry 007 | Auditoría de preparación y corrección del eslabón físico (GATE 1 reabierto)
- **Date:** 2026-09-14
- **Hipótesis evaluada:** "PHASE_01 está cerrado y GATE 1 satisfecho" (declarado en Entry 004).
- **Decisión:** Reabrir GATE 1. La auditoría reproducible demuestra que el cierre declarado **no se sostiene**.
- **Herramienta:** `scripts/audit_target_readiness.py` (solo lectura, reejecutable).

**Errores detectados y documentados (context.md §39: no se borran, se documentan):**

1. **Geometría de control inválida.** `scripts/generate_control_geometry.py` generaba una caja de
   0,5 m + 4 discos + 2 cajas, con radio de rotor fijo (0,5 m T25P / 0,6 m resto) e igual para todos
   los modelos. El rotor oficial es 1270 mm (T25P) o 1575 mm (resto) ⇒ error de −21 % a −24 % en radio.
   Sin palas: solo un disco plano de 8 lados. Todas las plataformas compartían el mismo cuerpo.
2. **Manifiestos de geometría con datos inventados.** `scripts/generate_geometry_manifest.py` declaraba
   cuadricópteros de 4 rotores para T25P/T55/T70P cuando el número de rotores es **D** en las propias
   fichas; wheelbase 2135/2800/3300/3800 mm frente a los oficiales 1970/2415/2440/2330 mm; diámetros
   1,35/1,45/1,55/1,65 m frente a 1,270/1,575/1,575/1,574 m; y **max_rpm 3400/2900/2600/2200 sin
   ninguna fuente**, que viola directamente §42 ("no inferir RPM") y el riesgo R1 declarado.
   Error geométrico adicional: división del wheelbase por √2 **dos veces** (rotores a 1,51 m del centro
   para un wheelbase de 2135 mm). El docstring afirmaba "based on exact DJI Agras architecture".
   → Script marcado como OBSOLETO con los defectos listados. Manifiestos antiguos eliminados.
3. **Caso CFD sin física de rotor.** `simpleFoam` estacionario sin actuator disk ni MRF ⇒ no puede
   producir downwash. Ninguno de los niveles CFD 1–4 del plan está implementado.
4. **Contornos no físicos.** `inlet` y `outlet` ambos `fixedValue (0 0 0)` (caja cerrada, sin caudal);
   `sides` como `symmetry` en vez de dominio semi-infinito.
5. **Dominio incoherente con el caso base.** z ∈ [−6, 4] con el cuerpo en z ≈ 0 ⇒ el dron queda a 6 m
   del suelo, no a los 3 m de §45. Además el `log.snappyHexMesh` dice `(-5 -5 0)(5 5 10)`: **el log no
   corresponde al `blockMeshDict` actual** ⇒ la malla es anterior al diccionario (no se regeneró).
6. **Resolución insuficiente.** Celda base 0,20 m frente a rotores de 1,27 m; `level (1 2)` y el log
   confirma que la superficie no disparó refinamiento ("Selected for refinement: 0 cells").
7. **Sin extracción de datos.** No hay `functions` en `controlDict` (ni forces, ni probes, ni surfaces,
   ni muestreo en plano receptor) ⇒ aunque corriera, no produciría una sola fila del dataset objetivo.
8. **Turbulencia incompleta.** `kOmegaSST` declarado, pero `0/` solo tiene `p` y `U`: faltan `k`, `omega`, `nut`.
9. **DOE prematuro y fuera de especificación.** 100 corridas LHS generadas antes de validar nada
   (viola GATE 2 y el orden de §24/§13); rangos idénticos para las 4 plataformas (§9 exige rangos por UAV);
   `Atomizers` y `Platform` asignados al azar en vez de por diseño; y **T70P a carga 1,0 solo es válido
   con batería DB2160** (con DB1580: 52+70 = 122 kg > MTOW 102 kg) sin filtrar.
10. **Sin replicabilidad de software.** No hay repositorio Git; `.venv` vacío creado desde WSL.
    OpenFOAM 2412 corrió por WSL, pero WSL devuelve **acceso denegado** en esta sesión ⇒ el pipeline
    CFD no es reproducible aquí (puede ser restricción del harness; registrado, no concluido).

**Correcciones aplicadas:**

- `scripts/build_geometry_manifests.py` → manifiestos con **procedencia por campo**
  (P / P-A / I / E / D) en `geometry/manifests/`. Los campos desconocidos quedan en `null`, no inventados.
- **Relación geométrica candidata (I) — prueba de consistencia, NO identidad demostrada:**
  `lado entre ejes = D_axis/√2` y `span_candidato = lado + diámetro de rotor`.
  Contraste con el sobre oficial: **T25P +0,49 %**, **T100 +0,05 %** (coinciden) y
  T55 +2,90 %, T70P +3,92 % (**no coinciden**). Con 4 plataformas, 2 coincidencias y 2 desviaciones,
  la evidencia **no alcanza para elevarla a ley** y un 2,9–3,9 % es demasiado grande para tratarlo
  como redondeo — pero tampoco demuestra que la especificación esté mal. Se mantiene como **prueba de
  consistencia** hasta que las mediciones A2/A8 expliquen o descarten la desviación
  (hipótesis alternativas en `geometry/protocolo_geometria.md` §7.1).
  La invariante de no-solape de rotores sí se cumple en las 4 (margen mínimo T100: +0,074 m).
  > **Corrección de rigor (2026-09-14, tras revisión del investigador):** en la primera redacción
  > esto se registró como "modelo geométrico *validado*" y como "relación no documentada descubierta".
  > Ambas etiquetas eran **excesivas** y se retiran: era una inferencia con dos coincidencias
  > favorables, no una validación.
- Derivados de nivel 0 (momentum theory) calculados y marcados como orden de magnitud:
  v_inducida en hover 6,62 / 5,05 / 5,82 / 6,86 m/s y carga de disco 102,6 / 59,8 / 79,4 / 110,3 N/m².
- `scripts/generate_control_geometry_v2.py` → geometría correcta: diámetro de rotor real, 4 u 8 rotores
  según hipótesis declarada, par coaxial modelado como 2 planos, normales STL reales, y sidecar
  `.meta.json` con la clasificación de cada cota. Bounding boxes: 2,663 / 3,283 / 3,299 / 3,222 m.
- `geometry/protocolo_geometria.md` reescrito como protocolo de medición ejecutable (bloques A–D),
  con criterios de cierre de GATE 1 y el plan del riesgo R1.
- `scripts/extract_pptx_text.py` + `data/raw/dji_academy_01_conocimiento_basico.txt` +
  `data/raw/dji_academy_01_FUENTE.md` → nueva fuente **P-A** (DJI Academy) registrada y auditada.

**Aportes de la fuente P-A (DJI Academy) que resuelven campos que estaban en D:**
hélice **6223 = 62 × 23 in** (paso de pala), **coaxialidad del T100**, rango de gota **10–500 µm** de la
boquilla de niebla, **V máx de traslado 20 m/s**, ascenso 3 m/s y descenso 2–3 m/s, **rotación del T70P
opuesta a un cuadricóptero tradicional (1/3 CW, 2/4 CCW)**, ESC 370 A pico, y **4 boquillas TRASERAS**
sobre barra en el T100 (corrige la premisa "delanteras+traseras").
Discrepancias registradas sin resolver: dimensiones del T70P (3200×3520×960 specs vs 3175×3490×960 Academy)
y masa del T100 (75 kg specs vs 73 kg Academy).

**Resultado:** GATE 1 queda **ABIERTO**. El cuello de botella pasa a ser la campaña de medición física
(bloques A y B del protocolo): número real de rotores, posición XYZ de rotores y de atomizadores, y RPM real.
- **Estado:** `PHASE_01_SPECIFICATIONS` en corrección. No se avanza a CFD de estudio hasta cerrar GATE 1.

### Entry 008 | Ampliación de la fuente DJI Academy y hallazgo sobre el hueco de novedad
- **Date:** 2026-09-14
- **Acción:** Se extrajeron 3 presentaciones más de la carpeta DJI Academy con
  `scripts/extract_pptx_text.py`: intro al flujo de trabajo, planificación de misión y
  **configuración de parámetros de aplicación**.
- **Hallazgos relevantes:**
  1. **Estructura de variables confirmada oficialmente.** DJI define los parámetros de vuelo que
     ajusta el usuario como: tasa de aplicación, **tamaño de gota**, **velocidad de vuelo**,
     **altura sobre el cultivo** y **separación de rutas**. Coincide con las variables independientes
     del proyecto (§9) y confirma que el entregable (interlineado recomendado) es directamente un
     parámetro del control remoto Agras ("separación de rutas").
  2. **H2 y H7 tienen respaldo cualitativo industrial.** La tabla oficial de DJI atribuye la
     *cobertura* a la combinación **ancho + velocidad + altura**, y la *eficiencia* a un compromiso
     ancho ↔ uniformidad. Es la formulación de H2 (interacción triple) y de H7 (compromiso
     productividad/uniformidad) en la práctica comercial. **Sigue siendo evidencia cualitativa,
     no demostración:** la cuantificación es el aporte científico del estudio.
  3. **Rango de velocidad de aplicación más amplio de lo asumido:** DJI compara 3/5/7/10/**13 m/s**
     a 140 µm, mientras `doe_master_plan.csv` solo cubre 2,01–9,93 m/s.
  4. **HALLAZGO CRÍTICO — el material oficial NO tiene tablas para T25P, T55, T70P ni T100.**
     Las cinco tablas de recomendación de parámetros del deck 03 están etiquetadas **solo para
     T40/T50** (tasas 15–30 L/ha, gota 150–500 µm, V 5–10 m/s, ancho 4,5–9 m, altura 3–4 m).
     Esto **refuerza el hueco de novedad** declarado en `RESEARCH_ARCHITECTURE_V1.md` §3 (la práctica
     industrial está anclada a plataformas anteriores) y a la vez impone una **restricción**:
     esas tablas **no pueden usarse como entradas del DOE** para las 4 plataformas del estudio —
     sería la extrapolación entre modelos que §30 prohíbe. Solo valen como referencia cualitativa
     y como punto de partida de los rangos a medir.
  5. Prácticas antideriva: viento ≤ 2 m/s, V ≤ 6 m/s, gota gruesa, zona de amortiguamiento 9–20 m.
     (El límite del aparato declarado en fichas es viento ≤ 6 m/s: son dos cifras distintas.)
  6. Distancia de seguridad a obstáculos: ≥ 2,5 m entre punta de hélice y objeto.
- **Decisiones:** registrar todo en `data/raw/dji_academy_01_FUENTE.md` §6–§7 y anotar la restricción
  antes de rehacer el DOE. **El DOE no se rehace todavía:** depende de los rangos medidos (GATE 1A).
- **Estado:** sigue en `PHASE_01_SPECIFICATIONS`.

### Entry 009 | Multimedia, gate partido y decisión de frontera CFD
- **Date:** 2026-09-14
- **Disparador:** revisión del investigador principal, que objeta correctamente tres puntos:
  (a) no confundir geometría paramétrica trazable con geometría **físicamente validada**;
  (b) no describir la relación geométrica como "descubierta";
  (c) no dejar que la RPM bloquee toda la geometría.
- **Acciones:**
  1. **Extracción de los objetos multimedia ANTES del commit** (el investigador pidió no crear un
     checkpoint artificial antes de saber si las imágenes cambian el protocolo).
     `scripts/extract_pptx_media.py` → 178 objetos de 4 decks, `data/processed/media_inventory.csv`,
     hojas de contactos en `figures/contact_sheets/`.
  2. **Nueva categoría de datos `S`** = evidencia documental visual (imagen oficial con pie
     inequívoco). Regla: **de una foto sin escala o cota NO se derivan dimensiones**; solo hechos
     discretos (nº de brazos, coaxialidad, nº de palas, posición relativa). Registrada en la
     jerarquía de fuentes del protocolo §1.
  3. **GATE 1 partido en 1A y 1B** (protocolo §0):
     - **1A — geometry validated:** bloquea mallado, geometría CFD y dominio. Al cerrar: congelar
       `geometry-v1` con hash.
     - **1B — rotor operating state:** bloquea CFD cuantitativo; **no** bloquea topología, dominio,
       refinamientos ni comparaciones relativas.
  4. **Decisión de frontera CFD planteada explícitamente** (protocolo §6.1.1): RPM prescrita vs
     empuje prescrito vs sustentación impuesta. Recomendación: B/C para el dataset principal y A en
     casos selectos, para que el cuello de botella no dependa de la geometría de pala.
     Orden de medición corregido: **RPM en hover real primero, bancada después.**
  5. **Terminología corregida** en manifiestos, README, log y este documento: "modelo validado" →
     **"relación geométrica candidata / prueba de consistencia"**.
- **Hallazgos de la evidencia visual (categoría S):**
  - **T25P:** 4 brazos **sin** par coaxial → 4 rotores. Motor rotulado **10028/59KV** en la imagen
    (coincide con estator 100×28 y KV 59 oficiales). **2 palas.** Atomizador montado por debajo del
    plano del brazo. → `rotor_count` sube de `I` a `S`.
  - **T70P:** **par coaxial en cada uno de los 4 brazos** → 8 rotores, con separación axial visible.
    Detalle de rotor con **2 palas** y abrazadera oscilante. → `rotor_count` y `coaxial` suben de `I` a `S`.
  - **T100:** par coaxial por brazo; atomizadores por debajo y por fuera, en la parte trasera.
  - **T55: sin evidencia visual** en el deck 01 — sigue sin dato.
  - ⚠ **Conflicto abierto T100:** specs DJI "Cantidad: 8 pares" (16 hélices) vs deck 01
    (texto + imagen: 4 pares = 8 hélices). Ambas oficiales. Si se elige mal, el área de disco total
    se duplica y v≈√2. **Medir y resolver antes de mallar** (A9). Registrado como campo propio
    `CONFLICTO_ABIERTO_rotor_count` en el manifiesto.
  - **Medición del modelo de datos corregida:** el protocolo ya no pide "número de rotores" sino
    **centro XYZ, vector normal del disco, diámetro, sentido de giro, rol coaxial y separación axial
    del par** por rotor; y para atomizadores **posición + vector de descarga + Δz al plano de rotor +
    rotor cuya estela recibe + punto efectivo de emisión** (§3 y §4 del protocolo).
- **Pendiente identificado:** `p09_0a7ec705d2dc.emf` (16 MB, **vectorial**) es un diagrama rotulado de
  la aeronave; un vectorial se escala sin pérdida y es el mejor candidato para leer **posiciones
  relativas**. Requiere conversión EMF (Inkscape/ImageMagick no instalados en esta sesión).
  Quedan los decks 04–09 por extraer; pueden contener material del T55.
- **Estado:** `PHASE_01_SPECIFICATIONS`. **El hito siguiente NO es ejecutar OpenFOAM**, sino cerrar
  **GATE 1A**.

### Entry 010 | Arquitectura CFD compuesta, reparto coaxial y multimedia resuelto
- **Date:** 2026-09-14
- **Disparador:** segunda revisión del investigador, que corrige la disyuntiva B/C y señala el
  punto ciego del reparto de empuje en coaxiales.
- **Correcciones aceptadas:**
  1. **B y C NO son alternativas excluyentes.** Arquitectura adoptada:
     **C como restricción física global** (`Σ T_i + W ≈ 0`) **+ B como representación CFD local**
     (actuator disk materializa el empuje en cada disco). **A (RPM prescrita)** queda como
     **modelo secundario** para casos selectos, cuya finalidad es cuantificar si la simplificación
     por disco reproduce la **estructura de estela relevante para los atomizadores** (H3), no la
     fidelidad aerodinámica en abstracto.
  2. **`mg/N` NO se adopta como verdad experimental.** Para T25P (no coaxial) es una primera
     aproximación aceptable, contrastada con el CG medido. Para T55/T70P/T100 (coaxiales) **no**.
  3. **GATE 1A se cierra POR PLATAFORMA**, no globalmente: un conflicto del T100 no debe bloquear
     al T25P. Cada plataforma congela su propia `geometry-v1/<uav>/`.
  4. **Esquema del CSV ampliado** (protocolo §5): `value`, `unit`, `uncertainty`, `method`,
     `instrument`, `timestamp`, `operator`, `source_class`, `reference_frame`, `notes` — la
     trazabilidad experimental se captura en el momento, no se reconstruye después.
- **Punto ciego atacado — reparto de empuje del par coaxial** (`geometry/coaxial_thrust_split.md`):
  - La restricción física real **no es `T_u = T_l`** sino el equilibrio de momento angular:
    `Q_u(ω_u) = Q_l(ω_l)`.
  - De teoría de elemento de pala: `ω_l/ω_u = sqrt(C_Qu/C_Ql)` y
    `T_l/T_u = (C_Tl/C_Tu)·(C_Qu/C_Ql)`.
  - **Consecuencia:** el rotor **superior gira más rápido** que el inferior para par neto nulo.
    El reparto **depende del grado de interferencia**, no de una simetría.
  - **Incógnita de accionamiento (nueva, ítem A10):** si el par es **solidario** (ω_u = ω_l forzado)
    o **independiente** (dos motores/ESC por brazo). El material DJI **no lo declara**.
    Sin esto el modelo de empuje del coaxial no está definido.
  - **La separación axial del par (A6) deja de ser una cota decorativa:** es parámetro del modelo
    de empuje.
- **Multimedia resuelto:**
  - Se intentó Inkscape primero: **no instalado y `winget` bloqueado** en este entorno (exit
    -1978335231); sin ImageMagick ni LibreOffice. Se resolvió con **Pillow/GDI**, que sí rasteriza
    WMF/EMF en Windows. Script nuevo `scripts/convert_vector_media.py`.
  - **Hallazgo que refuta la premisa:** el EMF de 16 MB **no es vectorial útil** — es un **mapa de
    bits envuelto en un metafile**. Renderizado a 5174×2558 px no hay trazados que escalar.
    La idea de "escalar sin pérdida para leer posiciones" **no era viable por esa vía**.
  - **Vía correcta:** los rótulos son **cuadros de texto superpuestos**, así que la geometría se
    lee del **XML de la diapositiva** en EMU (dato exacto, no estimación de píxeles).
    Script nuevo `scripts/extract_pptx_shape_geometry.py` → `data/processed/shape_geometry/`
    (285 formas + extremos de los 17 conectores de la slide 09).
  - **Limitación declarada:** el mapeo rótulo→componente por cercanía de línea guía es **ambiguo**
    (17 conectores vs 22 rótulos; "Motor" y "ESC" colapsan). Lo exacto son las posiciones de las
    formas; los pares rótulo–componente **no se citan como hechos**.
- **Nuevo artefacto:** `scripts/freeze_geometry_v1.py` — valida el cierre de GATE 1A por plataforma
  y congela `geometry-v1/<uav>/` con manifiesto, STL, `SOURCES.md`, `README.md` y `SHA256SUMS`.
  **No existe flag de forzado**: para congelar hay que cerrar el gate de verdad.
  Verificación con `--verify` (recalcula hashes y detecta alteraciones).
- **Resultado de la validación (dry-run, estado real):**
  | Plataforma | Bloqueantes |
  |---|---|
  | T25P | 1 — falta la campaña de medición (**es el candidato natural a cerrar primero**) |
  | T55 | 3 — `blades_per_rotor` y `rotor_count` en D + medición |
  | T70P | 1 — medición (coaxial: exige A6/A11 y reparto) |
  | T100 | 2 — **conflicto 8 vs 16 rotores abierto** + medición |
- **Estado:** `PHASE_01_SPECIFICATIONS`. Próximo hito sin cambios: **cerrar GATE 1A por plataforma**,
  empezando por T25P.

### Entry 011 | Corrección del reparto coaxial, barrido documental 04–09 y hoja de campaña T25P
- **Date:** 2026-09-14
- **Disparador:** tercera revisión del investigador. Objeción aceptada: la restricción
  `Q_u(ω_u) = Q_l(ω_l)` **no es una restricción universal**.

**1. Corrección de física en `geometry/coaxial_thrust_split.md`**

Lo que exige un UAV en hover sin aceleración de guiñada es la **suma algebraica global**:

```
Σ_i  s_i · Q_i  ≈  0          (s_i = ±1 según el sentido de giro)
```

**No** que cada pareja coaxial tenga par neto nulo: el controlador puede compensar desequilibrios
entre brazos. Por tanto **se retiran** como resultados:
- `ω_l/ω_u = √(C_Qu/C_Ql)`;
- la afirmación de que el rotor superior *debe* girar más rápido;
- toda partición `T_l/T_u` por defecto.

Lo que queda es una **hipótesis condicional explícita** (accionamiento independiente **y** par neto
nulo por pareja), útil solo como **modelo candidato falsable** con A11 y D5a–D5c.
Lo único robusto es aerodinámico: el rotor inferior opera en la estela del superior
(`v_in,l = v_u + δ·v_i`) y eso degrada su `C_T` y encarece su `C_Q`. **Cómo se reparte esa
degradación en `T` y `ω` es asignación de control, no aerodinámica: no se puede afirmar sin medir.**

→ `A10` (accionamiento del par) queda confirmado como **más importante de lo que parecía**: sin él
no se sabe ni qué restricción aplica. El CFD correrá con la partición **como parámetro**, con
análisis de sensibilidad.

**2. Barrido documental de los decks 04–09** (`scripts/audit_documentary_evidence.py`)

Extraídos los 6 decks restantes (10 decks en total, ~1 600 líneas). Auditor con criterios
explícitos: alias de identidad por modelo + 13 términos técnicos, reportando archivo y línea.
**El script reporta; no concluye** (regla del encargo).

- **RESULTADO NEGATIVO — el T55 no existe en la carpeta.** Cero coincidencias de identidad en los
  10 decks, ni por alias. Los decks 04–09 tratan de energía/generador, agroquímicos, seguridad,
  instructor, mantenimiento y operación práctica. El material formativo cubre **T100, T70P, T25P y
  la generación T40/T50**. → el T55 queda **enteramente dependiente de medición física**; no hay
  más evidencia documental que explotar aquí.
- **A9 — origen del "8 pares" LOCALIZADO.** No era lectura ambigua: es un valor de tabla explícito
  de la ficha oficial. `data/raw/T100_ocr.txt` líneas 56–67 (`Sistema de propulsion - Hélices` →
  `62 pulgadas` → `Cantidad` → **`8 pares`**). Contraste: `T55_ocr.txt` líneas 60–66 dice
  **`4 pares`** con la misma hélice de 62 in. `T70P_ocr.txt` líneas 58–68 tiene el campo
  `Cantidad` **vacío**.
  → Lecturas posibles registradas (16 hélices / nomenclatura que cuenta hélices / otra versión).
  **No se resuelve por interpretación**: se resuelve por conteo físico. Añadida la hipótesis de
  **ambigüedad de traducción** (el original probablemente usa 对, "par").
  → **Subproducto:** el `Cantidad` vacío del T70P es un **hueco recuperable recapturando la página
  oficial** — vía barata identificada, no incógnita de medición.
- **A10 — sigue sin resolverse.** El deck 08 menciona la categoría "Motores y ESC" en una lista de
  limpieza, sin contar unidades ni describir el accionamiento. El deck 04 trata del **generador**,
  no de la propulsión. **No hay atajo documental: exige inspección física o manual de servicio.**

**3. Hoja de campaña T25P preparada, NO ejecutada** (`geometry/campana_T25P.md`)

El T25P pasa de "el primero que se puede cerrar" a **ensayo del propio método experimental**: al no
tener par coaxial, permite depurar de punta a punta
`documentación → M → incertidumbre → manifest → GATE 1A → freeze → SHA256` y corregir problemas de
sistema de referencia, repetibilidad, instrumentos o nomenclatura **antes** de los coaxiales.

- Generada por `scripts/prepare_t25p_campaign.py`: puntos de carga derivados de datos públicos
  (33 + 20·f → 33 / 38 / 43 / 48 / 53 kg, coherente con MTOW 53 kg ✓), referencias de nivel 0
  (A_disco = 5,067 m², DL = 102,6 N/m², v_ind = 6,62 m/s) **para contrastar, no para sustituir**,
  bloques A/B/C/D con métodos y precisiones objetivo, checklist de instrumentos calibrados,
  repeticiones, seguridad (R11) y criterio de cierre con `freeze_geometry_v1.py`.
- **A6, A10 y A11 no aplican al T25P** (no hay par coaxial): precisamente lo que lo hace buen piloto.
- `data/raw/mediciones_geometria.csv` creado **solo con cabecera y 0 filas**.
  Verificado que el gate **sigue bloqueando**: el script de congelación no tiene flag de forzado.

- **Estado:** `PHASE_01_SPECIFICATIONS`. Nada medido, ningún gate cerrado, CFD no ejecutado.

### Entry 012 | Recaptura forense de fichas oficiales: A9 gana precisión, A10 no se resuelve
- **Date:** 2026-09-14
- **Disparador:** cuarta revisión del investigador. Orden vinculante registrado:
  **`recaptura T55/T70P/T100 → auditoría A9/A10 → campaña T25P → post-mortem metodológico →
  campaña v2 → generar T55/T70P/T100`**. Acordado: **no preparar las otras tres campañas ahora**,
  porque el piloto T25P existe precisamente para descubrir qué está mal en la plantilla.

**1. Recaptura forense** — `scripts/capture_official_specs.py`

- Vía de red: **PowerShell y `curl.exe` fallan** (schannel `SEC_E_NO_CREDENTIALS`), pero
  **Python/urllib funciona**. Registrado para futuras sesiones.
- 6 capturas (T100/T70P/T55 × es/zh), con URL, fecha UTC, user-agent, cabeceras, HTML crudo y
  **sha256**. Manifiesto en `data/raw/specs_captures/capturas_manifest.json`.
- **Hallazgo forense:** `/es/` y `/cn/` devuelven **bytes idénticos** (mismo sha256), `lang="es"` y
  el payload **en español**. El contenido se hidrata por JavaScript (0 tablas HTML). Se intentó
  además `Accept-Language: zh-CN`, cookie de locale y `www.dji.com/cn/...` (404):
  **el texto chino original no es accesible por HTTP**. El punto 3 del encargo (conservar 对 sin
  traducir) **queda sin satisfacer por esta vía**, y así queda registrado en
  `data/raw/specs_captures/intentos_chino.json`.
- **Vía que sí funcionó:** extraer el **payload JSON embebido**
  (`scripts/extract_spec_payload.py` → `spec_tables.json`). Da la **fila completa con sus
  encabezados** (`key`/`value`) y el texto literal, sin OCR ni maquetación.

**2. A9 — el conflicto cambia de naturaleza (y empeora de forma útil)**

La recaptura confirma que **el OCR era correcto** y la cifra es literal:

| Plataforma | `Cantidad` en la fila de hélices |
|---|---|
| T100 | **`8 pares`** |
| T55 | **`4 pares`** |
| T70P | **`4`** ← ¡sin la palabra "pares"! |

**Corrección:** el `Cantidad` del T70P **no estaba vacío** — dice `4` a secas. El hueco era del PDF
capturado, no de la ficha. **Vía barata cerrada** (era uno de los objetivos de la recaptura).

**Por qué sigue abierto y ahora es más interesante:** los tres UAV tienen la **misma arquitectura
de 4 brazos con par coaxial**, y sin embargo DJI escribe `8 pares` / `4 pares` / `4`. Esa
**inconsistencia de unidad dentro de la misma casa** demuestra que el campo **no se puede leer como
conteo físico** sin más. Hipótesis registradas, ninguna adoptada (ver `evidence/CONFLICTS.md` C-01):
"pares" cuenta hélices (16 hélices en T100); "pares" es criterio comercial de suministro; el `4`
pelado del T70P cuenta otra cosa; o versión distinta.

→ **Refuerza exactamente la advertencia del investigador**: "8 pares" quizá **no** sea un conflicto
8-vs-16 rotores. Ya no es una sospecha: es una ambigüedad **demostrada en la fuente oficial**.

**3. A10 — sigue sin resolverse, sin atajo documental**

Las fichas oficiales **no declaran** número de motores ni de ESC por brazo: el grupo
`Sistema de propulsión - Motores` solo da estátor y KV. Combinado con el barrido negativo de los
10 decks, **A10 exige inspección física o manual de servicio**. Confirmado como el punto ciego
central del modelo coaxial.

**4. Artefacto nuevo: `evidence/CONFLICTS.md`**

Registro único de los conflictos, con evidencia citada (archivo + línea + hash). Se crea siguiendo
la instrucción de que **ese es el único documento que se actualiza** ante evidencia documental.
`rotor_count` y compañía **no se tocan automáticamente**.

**5. Un conflicto SÍ se cerró, y con el criterio correcto**

**C-05 resuelto:** la ficha oficial vigente da T70P **3200 × 3520 × 960 mm** (coincide con el PDF del
investigador); el deck de Academy decía 3175 × 3490 × 960 y **se descarta**. Es convergencia entre
dos fuentes independientes del mismo emisor, que es el criterio exigido → manifiesto del T70P
actualizado, y su prueba de consistencia pasa de +3,92 % a **+3,10 %** (sigue sin cerrar: C-04).

**6. Conflictos nuevos detectados por la recaptura:** C-06 (masa de pulverización del T100: la ficha
dice 75 kg y cierra con el MTOW; Academy 73 kg no cierra) y C-07 (MTOW de **esparcido** discrepante
en T55/T70P — **fuera de alcance** de este paper, se registra y no se corrige).

**7. Lo que la propia investigación se lleva de método:** la recaptura **no promovió nada a `M`**.
Sirvió para (a) cerrar una vía barata, (b) convertir una duda de digitalización en una ambigüedad
semántica demostrada, y (c) refutar la expectativa de que la web resolvería A9. Ningún gate cambió
de estado.

- **Estado:** `PHASE_01_SPECIFICATIONS`. **Siguiente paso acordado: campaña física del T25P.**

### Entry 013 | Piloto T25P: campaña en dos jornadas, reglas de medición y QA con no-circularidad
- **Date:** 2026-09-14
- **Disparador:** quinta revisión del investigador. Decisión aceptada: **se deja de investigar
  documentación** (rendimiento decreciente) y **se arranca el piloto T25P**. Antes de tocar el
  dron, dos correcciones estructurales a la hoja de campaña.

**1. El piloto se parte en DOS jornadas con parada obligatoria forzando la división por bloques**

| | Bloque 1 — Metrología estática | Bloque 2 — Estado operativo |
|---|---|---|
| UAV | **apagado** | energizado / hover |
| Mide | sistema de referencia, rotores, atomizadores, cotas | masas reales, CG, ambiente, RPM |
| Cierra | **GATE 1A** | **GATE 1B** |

**Parada obligatoria** entre bloques: procesar las filas, calcular cierres y residuos, y **solo si
el bloque 1 pasa el post-mortem se vuela**. El motivo es evitar que un error metodológico
contamine toda la campaña.

**2. Reglas de medición incorporadas**

- **Repetibilidad ≠ resolución.** Cada magnitud crítica con **≥3 mediciones con RECOLOCACIÓN del
  instrumento** y **distinto `setup_id`**. Tres lecturas consecutivas sin moverse solo miden
  resolución instrumental; la QA detecta ese caso y lo marca.
- **Los residuos no se corrigen.** Contraste de simetría para rotores opuestos
  (`x1+x3 ≈ 0`, `y1+y3 ≈ 0`) **reportando el residuo como información**. Lecturas posibles si sale
  grande: el CG real no coincide con el origen, la planta no es simétrica, o error de medición.
  **Prohibido ajustar coordenadas para forzar la simetría** — queda escrito en la hoja y en la QA.
- **Masa nominal ≠ masa medida.** Los puntos 33/38/43/48/53 kg son **nominales derivados**
  (33 + 20·f, clase `E`), **no** masas experimentales. Antes de cada vuelo se pesa la configuración
  efectiva. El CSV incorpora **dos variables distintas**: `nominal_total_mass_kg` y
  `measured_total_mass_kg`. **La diferencia entre ambas es un resultado.**
- **RPM individual por rotor (R1–R4)**, no una sola "RPM del T25P": diferencias entre rotores son
  evidencia directa contra el supuesto de reparto uniforme `mg/4`, y se pierden al promediar.
- **Sistema de referencia documentado, no solo declarado:** registrar **cómo** se materializa el
  origen y **fotografiarlo**. Un origen no documentado invalida todas las cotas del bloque.

**3. Regla de no-circularidad (nueva)**

**GATE 1A debe poder cerrarse exclusivamente con geometría y evidencia experimental.** Si el script
que decide el gate usara valores derivados de CFD, se introduciría circularidad antes de empezar a
simular. Implementado como comprobación automática en la QA, que inspecciona **solo código**
(descartando comentarios y literales, para no detectarse a sí misma) y verifica que ningún script
del gate construya rutas a `cfd/results` ni `cfd/cases`. **Resultado: OK.**

> Aclaración de alcance: los manifiestos incluyen `derivados_nivel0` (momentum theory). Es **física
> analítica**, no CFD, y está marcada como orden de magnitud. No rompe la no-circularidad, pero
> **no** es criterio de cierre del gate: solo contraste.

**4. QA implementada y verificada** — `scripts/audit_measurement_csv.py`

Reporta, **sin escribir nunca en el CSV ni en los manifiestos**:
1. esquema y trazabilidad (filas `M` sin `uncertainty`/`instrument`, sin `reference_frame`, sin `method`);
2. repetibilidad entre repeticiones independientes, distinguiendo del caso "mismo `setup_id`";
3. **residuos de simetría**, con recordatorio explícito de que no se corrigen;
4. cierre de distancias vs wheelbase (1970 mm) y alcance (2650 mm) declarados;
5. cobertura de parámetros exigidos por GATE 1A, y obligación de que exista masa **medida**;
6. no-circularidad del gate.

**Verificación de que la QA sirve:** `scripts/selftest_measurement_qa.py` inyecta 8 problemas
conocidos en un CSV desechable (par simétrico correcto, par con residuo de 30 mm, fila `M` sin
trazabilidad, fila sin `reference_frame`, repeticiones con el mismo `setup_id`, repeticiones
correctas, cota de separación de ejes) y comprueba que **todos** se detectan. Resultado: detecta
los 6 grupos, incluido el residuo de −0,030 m marcado como `RESIDUO GRANDE` y el error de cierre
del +0,56 % frente al wheelbase. El CSV real se restaura tras la prueba.

**5. Estado:** la documentación se cierra. **El cuello de botella es ahora físico, no documental.**
La hoja `geometry/campana_T25P.md` está lista para ejecutar el bloque 1; el CSV
(`data/raw/mediciones_geometria.csv`) tiene la cabecera ampliada (`setup_id` incluido) y **0 filas**.

### Entry 014 | Convención de rotores desacoplada y residuo del vector completo
- **Date:** 2026-09-14
- **Disparador:** sexta revisión del investigador, con el corte metodológico explícito:
  **"ya no tocaría el protocolo antes de medir"** — el riesgo es diseñar metodología alrededor de
  problemas imaginarios. Se implementan sus tres correcciones y **se deja de refinar** hasta tener
  datos reales.

**1. La numeración deja de pretenderse "de DJI"**

No se fija `PARES_OPUESTOS` sobre una numeración DJI no demostrada. Se adopta una **convención
geométrica interna** (vista cenital, `+X` adelante, `+Y` izquierda, `+Z` arriba):
`R1=FL`, `R2=RL`, `R3=RR`, `R4=FR`, y **`position_role` pasa a ser columna obligatoria** del CSV.

Razón registrada: **`R1…R4` son identificadores; `FL/RL/RR/FR` contienen la semántica geométrica.**
Si un manual DJI numera los motores de otra forma, no habrá que reinterpretar mediciones antiguas.
Es exactamente la clase de decisión que, tomada tarde, obliga a rehacer una campaña.

**2. La QA deja de estar hardcodeada**

Los pares opuestos se **derivan de `position_role`** (`FL↔RR`, `FR↔RL`), no de una lista de
identificadores. Se elimina así una fuente de error humano.

**3. Corrección de fondo: el residuo se comprueba como VECTOR COMPLETO**

Tenías razón: comprobar solo `x₁+x₃ ≈ 0` **no demuestra oposición**. Ahora se comprueba
`r_i + r_j ≈ 2·r_c` para cada pareja (con `r_c = 0` si el origen está en el centro geométrico
esperado) y se reportan **residuos X, Y, Z, norma 3D y norma XY**, sin usarlos para corregir.
En la prueba: una pareja con residuo puramente en Z (`X=Y=0`, `Z=+10 mm`) **habría pasado
desapercibida** con las dos pruebas aisladas en X e Y, y ahora aparece.

**4. Evidencia fotográfica obligatoria**

Foto cenital con etiquetas físicas `R1`–`R4` y flecha `+X`, **asociada al `reference_frame`**.
Queda como checklist del bloque 1 y como comprobación en la QA.

**5. Autotest corregido — y una lección**

El autotest pasó de 7 a **8 comprobaciones**. Al ejecutarlo, una falló: yo esperaba la marca
"fila M sin uncertainty" y no salía. **La QA era correcta; mi caso de prueba estaba mal
construido**: había puesto `instrument = "-"` (no vacío), así que solo debía dispararse la marca de
`instrument`. Se corrigió el caso (ambos campos vacíos) y ahora **las 8 se detectan**.

> Lección de método: el fallo apareció **porque el autotest comparaba marcas concretas**, no porque
> "la QA pareciera funcionar". Es el argumento a favor de haber probado la QA antes de usarla.

**6. Límite conocido de la comprobación [5b], para la próxima iteración**

La detección de "foto cenital registrada" da un **falso positivo** cuando el CSV tiene filas
malformadas o vacías (aparece un `reference_frame` espurio con valor `M`). **No se corrige ahora**:
no hay datos reales todavía y refinar contra un CSV vacío es diseñar para un problema imaginario
—exactamente lo que el investigador advirtió—. Se anota para corregirlo **cuando existan las
primeras filas reales**, que es cuando se sabrá qué forma tienen de verdad.

**7. Decisión de parada:** **no se añade ningún control preventivo más.** El siguiente paso es
ejecutar el bloque 1 del T25P.

- **Estado:** `PHASE_01_SPECIFICATIONS`. **La metodología queda congelada hasta tener datos.**

### Entry 015 | Datos del propietario (clase `O`) y presupuesto de hipótesis con sensibilidad
- **Date:** 2026-09-14
- **Contexto:** el investigador pregunta si se puede seguir con lo declarado en la web, y aporta
  datos nuevos. Su campaña de medición **está en curso** (prevista para hoy o mañana).

**1. Datos aportados por el propietario — clase nueva `O`**

> T100: **8 motores**; T25P, T55 y T70P: **4 motores**.
> Atomizadores del T100: x = **−0,9 / −0,8 / −0,8 / −0,9 m** (izq. a der.), siendo **la 2ª y la 3ª
> las extras** de la configuración de 4.

Se introduce la clase **`O` = aportado por el propietario** en la jerarquía de fuentes, entre `S` y
`M`. Razón: el propietario es la fuente más cercana al objeto físico, así que **es mejor que una
inferencia**, pero **no es `M`** —sin instrumento, sin incertidumbre, sin repetición—. Confundir `O`
con `M` sería el mismo error que confundir `I` con `P`.

**Regla añadida:** un dato `O` **nunca se cita como si fuera de DJI**. Hacerlo no es idealizar:
es una cita falsa.

**2. Efecto sobre C-01 (T100, 8 vs 16 rotores)**

"8 motores" con 4 brazos coaxiales corresponde a **8 rotores** (2 por brazo) ⇒ **respalda la lectura
"4 pares"** y contradice la lectura literal "8 pares = 16 hélices". Convergencia por **dos fuentes
independientes**: imagen oficial (8 hélices) + propietario (8 motores).
**Falta la tercera pata** (inspección física fotografiada) para promover a `M`. **C-01 no se cierra
todavía**, ni automáticamente ni por mayoría de fuentes.

**3. Geometría de atomizadores regularizada y validada**

`scripts/derive_atomizer_geometry.py` → nomenclatura `A1..A4` con rol `L_out/L_in/R_in/R_out`.
Hipótesis explícita para la Y: la separación declarada (T100: 1834 mm) es el **par extremo**, y el
par interior queda cerrado a la mitad → ±0,917 m y ±0,459 m.

**Validación superada:** la boquilla exterior (±0,917 m) cae **dentro** de la barra LS100 (±0,965 m)
con margen de solo **+48 mm** — ajuste muy justo, consistente con que DJI especifique 1834 mm.

**Hallazgo útil para H3:** las cuatro boquillas caen **dentro de la proyección horizontal** de un
disco de rotor (0,248 m del eje las exteriores, 0,707 m las interiores, frente a r_rotor = 0,787 m).
No es colisión —van por debajo del plano— pero **es exactamente la configuración que hace relevante
H3**: las gotas se emiten **dentro** de la estela.

**4. Presupuesto de hipótesis — respuesta fundamentada a "¿podemos seguir con la web?"**

`geometry/presupuesto_hipotesis.md` + `scripts/assumption_budget.py`. **Sí se puede**, como
**estudio paramétrico con idealizaciones declaradas**, cumpliendo tres condiciones:
**(1)** declararlas en su propia sección y tabla; **(2)** justificarlas; **(3)** **cuantificar su
impacto** con análisis de sensibilidad. Incluye **borrador del texto para el paper**
(*Model assumptions and uncertainty budget*) que declara, justifica y acota sin reclamar validación.

**5. Ranking de sensibilidad — y el hallazgo que cambia la estrategia**

| # | Incógnita | Efecto | Coste de resolverla |
|---|---|---|---|
| 1 | Nº de rotores del T100 (8 vs 16) | **−29 %** en v_inducida (√2) | **minutos: contar y fotografiar** |
| 2 | Reparto de empuje superior/inferior | **±20 %** por disco (si 60/40) | RPM por rotor + bancada |
| 3 | Posición Z de atomizadores | **±6,7 %** en altura de caída en estela | **minutos: cinta métrica** |
| 4 | Posición XYZ de rotores | **±3,5–4,3 %** en separación entre ejes | **minutos: cinta métrica** |
| 5 | Separación axial del par | **±3,3 %** en longitud de estela | **minutos: cinta métrica** |
| 6 | RPM real | no cuantificable | tacómetro en hover |

> **Hallazgo:** **cuatro de las seis incógnitas se resuelven con cinta métrica y conteo**, sin
> instrumentos especiales ni volar. Solo el reparto de empuje y la RPM exigen equipamiento o vuelo.

Consecuencia: el estudio paramétrico **es viable hoy** y la medición no es un prerrequisito para
empezar, sino una **mejora de retorno alto y coste bajo**. Los valores `O`/`I`/`E` se **promueven**
a `M` cuando lleguen las filas; el trabajo no se tira.

**6. Sigue prohibido:** llamar validado a cualquier resultado con esta base; cerrar gates con
`O`/`I`/`E`; citar valores `O` como de DJI; alimentar la app con geometría supuesta.

- **Estado:** `PHASE_01_SPECIFICATIONS`. Estudio paramétrico **habilitado**; medición **en curso**.

### Entry 016 | GATE CFD-0, corrección del número de Stokes y módulo Lagrangiano especificado
- **Date:** 2026-09-14
- **Disparador:** séptima revisión del investigador. Tres objeciones, las tres aceptadas.

**1. Objeción aceptada: "128/128 estructuralmente verificados" NO es "128 casos CFD validados"**

Es correcto y era una afirmación mía que no se sostenía. `actuationDiskSource`, las `cellZone`,
el **signo del empuje**, las BC de traslación y los `function objects` son **hipótesis de
implementación** hasta que un caso corra de punta a punta.

→ Creado **GATE CFD-0** (protocolo §0), bloqueante, con alcance de **un solo caso T25P nominal**:

```
blockMesh → checkMesh → topoSet → solver 100-500 iter
          → confirmar actuationDiskSource → function objects → postprocess
```

Criterios verificables: `checkMesh` sin errores; una `cellZone` por rotor con el número correcto;
≥100 iteraciones sin divergir; **evidencia cuantitativa de que el disco actúa**; **signo del
downwash verificado** (el error más probable y más silencioso, porque el solver converge igual);
`function objects` con ficheros no vacíos; `postprocess_case.py` que los lea; y coste medido.

Artefactos: `scripts/gate_cfd0.sh` (secuencia completa con criterios) y
`scripts/check_cfd0_evidence.py` (comprueba que el perfil de downwash **no sea constante**, que el
signo sea correcto y que la magnitud esté dentro de un factor 5 de `√(T/2ρA)`).

> **CFD-0 NO se ha podido ejecutar.** Verificado: no hay `blockMesh`, `checkMesh`, `simpleFoam`
> ni `topoSet` en el PATH, no hay instalación en rutas típicas, y **WSL devuelve acceso denegado**.
> Además, `bash` **también está bloqueado** en este entorno, así que los tres `.sh`
> (`run_cfd_suite.sh`, `gate_cfd0.sh`) **no se han podido ejecutar ni verificar aquí** y se
> declaran como no probados.
> **Consecuencia:** los 128 casos son **casos generados, no casos CFD validados**, y así deben
> citarse. Escalar la suite queda bloqueado hasta cerrar CFD-0.

**2. Objeción aceptada: el número de Stokes no existe sin declarar la escala temporal**

Corregido en el código, no solo matizado. `analytic_metrics` ahora guarda **tres definiciones**
con su escala explícita y un campo `St_definicion` que declara cuál es la principal:

| Definición | τ_f | 100 µm | 500 µm |
|---|---|---|---|
| `St_rotor` | `r_rotor / v_dw` (escala global) | 0,519 | 12,97 |
| `St_estela` | `H / v_dw` | 0,136 | 3,40 |
| `St_turbulento` | `L_turb / u'` | 0,039 | **0,973** |

**Y la afirmación sobre H6 estaba mal, no solo mal formulada.** Se retira:

> ~~"St = 11,4 ⇒ balístico, el downwash apenas lo desvía"~~

Es **falso** en este rango. Añadido el criterio correcto (que el St **no** informa): el cociente
entre arrastre del campo medio y peso neto, `F_arrastre/F_gravedad`, que va de **198** (100 µm) a
**20** (500 µm). **Donde hay downwash, el arrastre supera al peso en más de un orden de magnitud
para todos los tamaños del rango operativo.** Un St alto implica menor seguimiento de
*fluctuaciones* y de la curvatura de líneas de flujo, **no** ausencia de aceleración por el campo
medio.

**Reformulación de H6 con lo que sí se sostiene:** el tamaño de gota **no** separa limpiamente
"sigue la estela" de "penetra balísticamente". Lo que cambia con el tamaño es (a) el seguimiento
de las **fluctuaciones** (St_turb de 0,039 a 0,973, cruza 1 dentro del rango) y (b) el **tiempo de
residencia** en la estela, porque la velocidad terminal crece mucho más rápido que el arrastre.
Artefacto: `scripts/report_stokes.py`.

**3. Objeción aceptada: separación conceptual del módulo Lagrangiano**

Regla incorporada al código y a la especificación:

```
flujo de aire → trayectorias de gotas → D(x,y) → ancho efectivo / uniformidad
```

- **`sigma_y` analítico NO alimenta la deposición CFD.** Queda como **baseline independiente**
  contra el cual comparar. Si se usara, se construiría en la simulación aquello que luego se
  pretende descubrir.
- **D(x,y) sale de contar impactos**, no de una fórmula.

`scripts/build_lagrangian_spec.py` → `lagrangian_spec.json` + `constant/cloudProperties` por caso.
**Especificado y validado estructuralmente, NO ejecutado.** Contiene lo que el investigador pidió:

- inyección desde la **posición y orientación real** del atomizador (con la **Z como parámetro**,
  porque sigue en `D`: se barre −0,10 / −0,20 / −0,30 m);
- **distribución de diámetros** Rosin-Rammler discretizada en 12 bins (no una sola gota), con
  `q = 2.0` marcado como **supuesto declarado**;
- velocidad inicial, gravedad y **arrastre dependiente de Re_p** (`sphereDrag`,
  Cd = 24/Re·(1+0,15Re^0,687)); se documenta explícitamente que **no** se usa ley lineal de Stokes
  porque Re_p va de ~1 a ~30 en el rango 100–500 µm;
- **evaporación, breakup y turbulencia estocástica declarados y desactivados por defecto**, con su
  razón escrita, activables por caso para análisis de sensibilidad — **no introducidos en silencio
  como "realismo"**;
- detección de impacto en el patch `ground`, con `stick` declarado.

**4. Orden de ejecución actualizado (vinculante)**

```
Stokes explícito ✅ → Lagrangiano diseñado ✅ sin ejecutar → esperar mediciones
   → cerrar T25P GATE 1A → UN smoke case (CFD-0) → recién entonces escalar a los 128
```

- **Estado:** `PHASE_01_SPECIFICATIONS`. Nada medido, ningún gate cerrado, CFD no ejecutado.

### Entry 017 | Diagnóstico corregido: OpenFOAM SÍ está instalado — es el acceso del agente a WSL
- **Date:** 2026-09-14
- **Disparador:** octava revisión del investigador, que objeta correctamente mi diagnóstico de
  Entry 016 ("este entorno no tiene OpenFOAM"). **Su objeción es correcta y la mía era errónea.**

**1. Corrección del diagnóstico**

Afirmé: *"no hay `blockMesh`/`checkMesh`/`simpleFoam`/`topoSet`, no hay instalación en rutas
típicas ⇒ este entorno no tiene OpenFOAM"*. **Conclusión inválida.** La verificación desde la
terminal del investigador demuestra:

```text
WSL Ubuntu 2 disponible (wsl -l -v)
Instalación:  /usr/lib/openfoam/openfoam2412        ← NO en /opt (ese camino no existe)
Comando:      openfoam2412                           → abre shell de sesión OpenFOAM
Build:        _b8cf4d35-20260127 (patch=260127), linux64GccDPInt32Opt, mpi=sys-openmpi
```

**La prueba decisiva:** ese build **coincide exactamente** con el que figura en
`cfd/cases/T25P_baseline/log.snappyHexMesh` (`Build: _b8cf4d35-20260127 OPENFOAM=2412
patch=260127`). Es la **misma instalación** que ya generó esa malla. **OpenFOAM funcionaba.**

**Tabla de lo verdadero y lo falso — la distinción que hay que sostener:**

| Afirmación | Veredicto |
|---|---|
| "OpenFOAM no está instalado" | ❌ **FALSO** |
| "El agente no puede alcanzar WSL desde esta sesión" | ✅ cierto |
| "`wsl -l -v` desde la sesión del agente → `E_ACCESSDENIED`" | ✅ cierto |
| "`bash` desde la sesión del agente también falla" | ✅ cierto |

**Lección de método:** busqué en rutas típicas de Linux (`/opt/openfoam*`), no encontré nada y
**concluí ausencia de instalación**. El error fue saltar de "no lo encuentro desde aquí" a
"no existe". La distinción entre *no accesible* y *no existente* es exactamente el mismo tipo de
error que este proyecto lleva quince revisiones evitando en el terreno de los datos. Aplicable a
mí mismo: **no accesible ≠ inexistente.**

**2. Bug real encontrado en las herramientas .sh (por el diagnóstico correcto)**

En **shell no interactiva** el entorno de OpenFOAM **no está cargado** (`foamVersion: command not
found`), aunque esté instalado. Mis tres `.sh` comprobaban `command -v blockMesh` y abortaban:
habrían fallado en tu terminal aunque OpenFOAM estuviera perfectamente instalado.

→ Añadida función `cargar_openfoam()` con **autodetección** en `gate_cfd0.sh`,
`run_cfd_suite.sh` y `verify_cfd_prereqs.sh`, que prueba, en orden:
`/usr/lib/openfoam/openfoam*/etc/bashrc`, `/opt/openfoam*/etc/bashrc`,
`$HOME/OpenFOAM/OpenFOAM-*/etc/bashrc`.
Los mensajes de ayuda ahora citan la ruta **correcta** (`/usr/lib/openfoam/openfoam2412`).

**3. Segundo bug corregido: elección del caso CFD-0**

El selector usaba `head -1` sobre el orden alfabético, que daba un T25P arbitrario (y el comentario
prometía "el más cercano a operación típica"). Reescrito con **parseo explícito de campos** y
minimización de la distancia relativa a `V=5 m/s, H=3 m, d=200 µm`. Verificado sobre el sistema de
ficheros real: selecciona **`T25P_V3.1_H2.8_d190_f0.95_a4`** (score 0,151).
Implementado **sin depender de Python**, porque `which python3` no apareció en tu verificación y
puede no estar instalado en el WSL.

**4. Prerequisito nuevo detectado: `python3`**

`postprocess_case.py` y `check_cfd0_evidence.py` lo necesitan. Nuevo
`scripts/verify_cfd_prereqs.sh` que lo comprueba y falla con instrucción de instalación
(`sudo apt install -y python3`) en lugar de romper a mitad del smoke test.

**5. Guía operativa** — `geometry/COMO_EJECUTAR_CFD0.md`: secuencia exacta desde PowerShell →
WSL → `openfoam2412` → proyecto → `verify_cfd_prereqs.sh` → `gate_cfd0.sh`, con la tabla de qué
significa cada fallo y qué traer de vuelta.

**6. Lo que sigue sin estar verificado, y se declara:** los `.sh` **no se han podido ejecutar ni
probar desde el agente** (WSL y `bash` bloqueados en esa sesión). Están escritos para funcionar en
tu terminal; **hasta que los corras no están verificados**. Es la misma honestidad que aplico a los
datos, aplicada al software.

- **Estado:** `PHASE_01_SPECIFICATIONS`. **CFD-0 es ejecutable hoy desde tu terminal.**

---
