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

---
