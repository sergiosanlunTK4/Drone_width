# PROJECT_MASTER_PLAN_V1.md

> **Documento único de operación** del proyecto *Downwash, transporte de gotas y deposición de UAV agrícolas DJI Agras*.
> Consolida: `CONTEXT.md` (57 secciones), `RESEARCH_ARCHITECTURE_V1.md` (24 secciones) y el Plan de Investigación v1. Una vez aprobado, es el referente operativo; los otros documentos quedan como detalle técnico de referencia.
>
> **Estado de capacidades confirmadas por el investigador (2026-09):**
> - ✔ Acceso físico a los 4 modelos (T25P, T55, T70P, T100) → mediciones (M) viables.
> - ✔ Especificaciones oficiales disponibles → categoría P con fuente.
> - ⏳ Hardware CFD y permisos de telemetría: a confirmar.

---

## Índice

1. Visión y filosofía
2. Pregunta científica, hipótesis y criterios de falsación
3. Alcance y fuera de alcance
4. Plataformas y especificaciones
5. Arquitectura técnica única (CFD, turbulencia, gotas, DOE, surrogate)
6. Plan experimental unificado
7. Roadmap de fases y gates
8. Arquitectura de datos y software
9. Gestión de riesgos (actualizada)
10. Ética, conflicto de interés, propiedad intelectual, autoría
11. Papers y difusión
12. Hitos y próximas acciones concretas

---

## 1. Visión y filosofía

Filosofía central (§57): **PHYSICS → NUMERICAL VERIFICATION → EXPERIMENTAL VALIDATION → DATASET → SURROGATE MODEL → OPTIMIZATION → APPLICATION.**

La app móvil es un **producto derivado**; el paper y el dataset conservan valor científico incluso si la app nunca se publica.

Principios no negociables:
- Cada UAV (T25P, T55, T70P, T100) es una plataforma independiente. No hay ecuación universal ni extrapolación automática entre modelos (T25P≠T25≠T20P; T55≠T40≠T50) sin análisis formal de semejanza (§30).
- Ningún dato crítico se inventa: cada uno lleva etiqueta P (público/oficial), M (medido), I (inferido), E (estimado-planning) o D (desconocido) con fuente exacta (§7 contexto).
- Los resultados negativos son válidos y se documentan (§54).
- Toda conclusión pasa por sanity check, verificación, independencia de malla/timestep, validación experimental y estadística (§40).
- Gate por fase: no se avanza si el gate no se cumple (§53).

---

## 2. Pregunta científica, hipótesis y criterios de falsación

### 2.1 Pregunta principal
> ¿Cómo modifican la arquitectura específica del UAV, la masa transportada, la velocidad de avance, la altura de pulverización, el tamaño de gota y la configuración espacial de atomizadores el campo aerodinámico y la distribución espacial de deposición D(x,y)?

### 2.2 Preguntas secundarias (mapa a entregables)
u(x,y,z), v, w, presión, turbulencia; efecto masa; efecto velocidad; efecto altura; comportamiento por d de gota; deposición transversal y 2D; 2 vs 4 atomizadores y posición espacial; efecto operacional de la carga (vaciado); viabilidad de surrogate e interpolador para app.

### 2.3 Hipótesis y criterios explícitos de falsación

| Hipótesis (§6) | Criterio de aceptación | Criterio de falsación |
|---|---|---|
| H1: Un ancho nominal no describe la distribución real | Perfil D(x) con múltiples extremos/asimetría/curvas de overlap no planas documentado | D(x) consistentemente unimodal y plano (poco probable) |
| H2: D(x,y) depende de interacción V×H×d | Términos de interacción significativos en el modelo estadístico (p<0.05 y tamaño de efecto definido) | Interacción no significativa; efectos aditivos |
| H3: N.º y posición de atomizadores afectan D | Diferencias entre config. 2/4 y posiciones superan el presupuesto de incertidumbre | Sin diferencia ≥ umbral |
| H4: La arquitectura de cada UAV exige modelos independientes | Diferencias inter-plataforma ≥ umbral en patrones a condiciones análogas | Curvas estadísticamente indistinguibles ⇒ se revisa (posible semejanza formal) |
| H5: La carga modifica downwash | Dif. de deposición entre 100% y 0% de carga supera umbral | Efecto < umbral ⇒ se excluye y se justifica (§10) |
| H6: Gotas pequeñas siguen más el flujo | Tendencia St ↓ ⇒ seguimiento ↑ demostrada en trayectoria/deriva/deposición | Comportamiento sin correlación con St |
| H7: Existe región operacional que optimiza uniformidad+productividad+eficiencia | Región convexa de Pareto encontrada con restricción de uniformidad | Conflictos irreconciliables entre metas |

**Umbrales numéricos se fijan formalmente en PHASE_07 (presupuesto de incertidumbre (§41) y tamaño de efecto mínimo operacionalmente relevante).**

---

## 3. Alcance y fuera de alcance

**Dentro (paper 1):** campo de aire por UAV (hover + traslación uniforme), transporte y deposición de gotas (agua, 28 °C, 70 % RH, 0 m/s viento), variables V/H/d/carga/config. de atomizadores, DOE, validación (viento + pulverización), surrogate por dron, interlineado derivado del patrón.

**Fuera (fase actual):** fitosanitarios/adjuvantes/mezclas; cultivos/canopia/terreno; viento exterior/atmósfera real; aplicación móvil (producto derivado); dosis por etiqueta (no recomendar "mínimo consumo" por debajo de etiqueta, §23).

---

## 4. Plataformas y especificaciones

### 4.1 Bloqueo de decisiones — matriz maestra por UAV

| Parámetro | T25P | T55 | T70P | T100 | Fuente | Est. |
|---|---|---|---|---|---|---|
| Geometría (L×A×H, wheelbase) | ⬜ | ⬜ | ⬜ | ⬜ | Docs oficiales (P) + medición (M) | P/M |
| N.º rotores y posición XYZ | ⬜ | ⬜ | ⬜ | ⬜ | Docs (P) + medición (M) | P/M |
| Diámetro rotor, palas, paso | ⬜ | ⬜ | ⬜ | ⬜ | Medición directa + foto alta velocidad | M |
| Masas (vacío, MTOW, tanque) | ⬜ | ⬜ | ⬜ | ⬜ | Docs (P) + pesaje (M) | P/M |
| Motor/KV/RPM/empuje/torque | ⬜ | ⬜ | ⬜ | ⬜ | Docs (P); RPM/empuje: telemetría aut. + tachómetro/cámara + estimación inversa (M/I) | P/M/I |
| Atomizadores: tipo, n.º, XYZ, orientación | ⬜ | ⬜ | ⬜ | ⬜ | Docs (P) + medición (M) — **crítico** para H3 | P/M |
| Caudal, presión, VMD/espectro | ⬜ | ⬜ | ⬜ | ⬜ | Docs (P) + bancada + caracterización (M) | P/M |
| Velocidad y altura de operación | ⬜ | ⬜ | ⬜ | ⬜ | Docs (P) | P |

⬜ = pendiente de completar con los documentos oficiales que el investigador tiene a mano.

**Clasificación de datos:** P público (a citar con fuente+fecha), M medido (protocolo propio), I inferido, E estimado, D desconocido. Resultado: ficha maestra por UAV en `docs/specs/`.

### 4.2 Prioridad de medición (acceso físico confirmado)
1. Diámetro real de rotores y posición XYZ de rotores y atomizadores (es decisivo para la geometría CFD).
2. Masas reales (vacío, baterías, tanque a 100/75/50/25/0 %).
3. Tipo/número de atomizadores y su configuración real 2 vs 4 (± posición delantera/trasera/lateral).
4. RPM en hover (tachómetro óptico/cámara) y momento de empuje (curva peso vs RPM) — **riesgo principal R1**.
5. Caudal por atomizador y espectro de gota (bancada; PDI/Sympatec si hay acceso, si no, hidrosensibles como ordinal).

**Regla de integridad:** no se usará información confidencial interna sin permiso escrito (§31). Datos de la empresa del investigador se etiquetan y verifican su independencia.

---

## 5. Arquitectura técnica única

*(Detalle en RESEARCH_ARCHITECTURE_V1.md §9–§17; aquí queda el resumen ejecutivo vinculante.)*

### 5.1 Métodos CFD (jerarquía)
- **Nivel 0 Momentum theory:** sanity checks (v_inducida, empuje, flujo).
- **Nivel 1 Actuator Disk:** screening rápido del campo.
- **Nivel 2 Actuator Line:** solución intermedia (tip vortices).
- **Nivel 3 MRF:** **candidato para dataset principal** — geom. de rotor real en región rotatoria.
- **Nivel 4 Sliding Mesh:** casos selectos de alta fidelidad; **comparación MRF vs Sliding antes de fijar el nivel del dataset**.
- **Nivel 5 Experimento:** validación.

### 5.2 Turbulencia
- **Primario: SST k-ω** (justificación vía literatura verificada en PHASE_00). 
- Comparación contra **realizable k-ε** en subconjunto de casos.
- **LES:** solo si hay pregunta abierta de interacción estela-dispersión y recursos.

### 5.3 Gotas
- Euler-Lagrange (parcelas); monodisperso primero (d ∈ {100–500} µm a confirmar), luego D10/D50/D90/espectro medido.
- Fuerzas: drag Schiller-Naumann, gravedad, dispersión turbulenta (eddy lifetime). Lift Saffman/Magnus solo si sensibilidad lo justifica.
- **Acoplamiento:** one-way como hipótesis (razón de carga ~10⁻³), **demostrado** con caso comparativo two-way antes del dataset (no asumido).

### 5.4 DOE
- LHS/Sobol para continuas (V, H, d, L) + factores discretos (UAV, config. atomizadores) cruzados por UAV.
- Central Composite / Box-Behnken evaluados como alternativa; **adaptive sampling** con GP para nuevas CFD donde incertidumbre/gradiente sea alta.
- Réplicas ≥3 en puntos de validación críticos. Rangos operativos por UAV según ficha maestra (no comunes a los 4).

### 5.5 Surrogate
- Salida funcional D(x) reducida por PCA/FPCA; **Gaussian Process** primario (incertidumbre, active learning); comparar RSM/XGBoost/RF; NN solo si se justifican.
- Validación out-of-sample con CFD nuevo y experimento. Por dron: D̂_T25P, D̂_T55, D̂_T70P, D̂_T100. Sin extrapolación fuera del dominio DOE.

### 5.6 Software (todo open-source)
OpenFOAM + ParaView + Gmsh + snappyHexMesh + FreeCAD/Blender + Python (NumPy/SciPy/pandas/matplotlib/scikit-learn; XGBoost si aplica). Versiones congeladas para reproducibilidad.

---

## 6. Plan experimental unificado

**(Detalle y métricas en ARCHITECTURE §15.)**

| Línea | Objeto | Instrumento | Grid/producto | Métricas CFD-vs-exp |
|---|---|---|---|---|
| A | Campo de viento | Anemometría sónica 3D (u,v,w) en mástil/rejilla; hot-wire opcional; cámara para RPM | V_z(x,y,H) + perfil vertical, ≥3 alturas, ≥3 repeticiones | RMSE, MAE, R², bias, error relativo |
| B | Pulverización | Línea transversal de colectores 0.25/0.50 m + trazador fluorescente cuantitativo + hidrosensibles | D_exp(x); D_exp(x,y) si el terreno lo permite; ≥3 repeticiones | RMSE, MAE, R², bias, CV, asimetría |
| C | Bancada de atomizador | Medición caudal + VMD/espectro | Q(VMD-presión), espectro por config. | Alimenta inyección de parcelas |
| D | Bancada de motor/hélice | Empuje vs RPM, corriente, potencia | Curva T(RPM), torque | Alimenta nivel CFD 3/4 |

**Puente a datos reales:** con acceso físico confirmado, el plan de medición puede ejecutarse de inmediato en paralelo con la revisión de literatura.

---

## 7. Roadmap de fases y gates

| Fase | Contenido | Output | Gate de salida |
|---|---|---|---|
| **PHASE_00_LITERATURE** | Revisión sistemática; matriz de literatura verificada; matriz de novedad | `literature/` | ≥20–60 refs verificadas; gap confirmado |
| **PHASE_01_SPECIFICATIONS** | Fichas maestras P/M por UAV (con docs a mano + mediciones) | `docs/specs/*`, `data/raw/specs_*` | **GATE 1**: dimensiones principales revisadas; plan RPM/empuje definido |
| **PHASE_02_GEOMETRY** | CAD simplificado por UAV + dominios de cálculo | `geometry/` | **GATE 1**: revisión dimensional; apto para mallado |
| **PHASE_03_BASELINE_CFD** | Fase A (T25P, aire); mesh independence c/m/f; timestep para transitorios | `cfd/results/` | **GATE 2**: convergencia + independencia de malla demostrada |
| **PHASE_04_AIRFLOW_VALIDATION** | Campaña anemométrica vs CFD | `experiments/` | **GATE 3**: downwash concuerda razonablemente |
| **PHASE_05_DROPLETS** | Gotas mono + distribuidas; one-way vs two-way | `cfd/results/` | Acoplamiento decidido |
| **PHASE_06_SPRAY_VALIDATION** | Línea de colectores vs CFD | `experiments/`, `figures/` | Validación cuantitativa |
| **PHASE_07_DOE** | DOE por UAV/config. (LHS/Sobol/adaptive) | `data/processed/` | Cobertura + calidad |
| **PHASE_08_DATASET** | Base completa con metadatos/incertidumbre | `data/processed/`, `cfd/results/` | Integridad/reproducibilidad |
| **PHASE_09_SURROGATE** | GP (+ comparativos) por dron; validación out-of-sample | `surrogate/` | **GATE 5** |
| **PHASE_10_OPTIMIZATION** | Interlineado óptimo por patrón; CV vs spacing; modos | `figures/`, `data/processed/` | Métricas cerradas |
| **PHASE_11_PAPER** | Manuscrito + suplementario + declaraciones | `paper/` | Revisión interna/CC |

Fases experimentales del contexto (A–H): A=T25P aire → B=gotas → C=tamaños → D=carga → E=2/4 atomizadores → F/G/H=T55, T70P, T100. Carga y atomizadores se resuelven en T25P antes de escalar.

---

## 8. Arquitectura de datos y software

Estructura de directorios (CONTEXT §38): docs, literature, data/{raw,processed}, geometry, cfd/{cases,templates,results}, experiments, surrogate, notebooks, scripts, figures, paper, supplementary, logs.

Esquema de base con tablas: `cases/simulations`, `deposition`, `airflow`, `experiments`, `surrogate`, `metrics_swath` (resumen). Cada fila con incertidumbre y metadatos de procedencia (P/P-A/S/M/I/E/D), mesh_id, solver_version, modelo_turbulencia, fecha, estado_validacion (§28, §18 ARCHITECTURE).

**Categoría `S` (2026-09-14):** evidencia documental visual — imagen de una fuente oficial con pie
inequívoco. Vale para hechos **discretos** (nº de brazos, coaxialidad, nº de palas, posición relativa).
**De una fotografía sin escala o cota no se derivan dimensiones.**

Entrada de specs: los PDFs/manuales/catálogos oficiales del investigador se importan a `data/raw/`, se extraen los valores a `docs/specs/<UAV>.md` (con cita de fuente y página) y a CSV en `data/processed/specs_master.csv`. La matriz §4 se completa a partir de ahí.

Versionado Git desde el inicio; raw inmutable.

### 8.1 Entrada de fuentes del investigador (actualizado 2026-09-14)

Además de los PDF de especificaciones, el investigador aportó el material **DJI Academy**
(carpeta `DJI ACADEMY COMPLETO`). Se registra como fuente **P-A** (público de formación de
distribuidor, jerarquía distinta a las fichas oficiales):

- Extracción con `scripts/extract_pptx_text.py` → `data/raw/dji_academy_*.txt`
- Registro y auditoría de aportes, discrepancias y límites → `data/raw/dji_academy_01_FUENTE.md`
- Resumen en `research_log.md` Entries 007 y 008.

**Aportes que resuelven campos antes `D`:** paso de pala (hélice 6223 = 62 × 23 in), coaxialidad
del T100, rango de gota 10–500 µm de la boquilla de niebla, V máx de traslado 20 m/s, ascenso
3 m/s y descenso 2–3 m/s, rotación del T70P opuesta a un cuadricóptero tradicional, ESC 370 A pico,
y **4 boquillas traseras** sobre barra en el T100.

> ⚠ **Restricción vinculante:** las tablas de parámetros operativos del material oficial están
> etiquetadas **únicamente para T40/T50**. **No pueden usarse como entradas del DOE** para T25P,
> T55, T70P ni T100 (§30 prohíbe extrapolar entre plataformas). Su uso se limita a referencia
> cualitativa y a punto de partida de los rangos a medir.

> 📌 **Dato relevante para §2 (hipótesis):** el material oficial atribuye la *cobertura* a la
> combinación **ancho + velocidad + altura** y plantea el compromiso ancho ↔ uniformidad en la
> *eficiencia*. Es respaldo cualitativo de **H2** y **H7** desde la práctica industrial; **no**
> sustituye la demostración estadística, que sigue siendo el aporte del estudio.

> 📌 **Terminología:** DJI llama **"separación de rutas"** al interlineado. El entregable del
> proyecto es directamente un parámetro configurable en el control remoto Agras.

### 8.2 GATE 1 partido en dos (actualizado 2026-09-14)

La versión anterior de GATE 1 acoplaba la topología geométrica con el estado operativo del rotor.
Son problemas con dependencias distintas: acoplarlos bloquea trabajo que sí se puede hacer.

| Gate | Contenido | Bloquea | NO bloquea |
|---|---|---|---|
| **GATE 1A** | *geometry validated*: topología, centros/ejes de cada disco, coaxialidad, **separación axial del par**, geometría de hélice, posición y orientación de atomizadores, sin `D` críticos | mallado de estudio, geometría CFD, dominio | estructura del DOE, arquitectura de datos, elección de turbulencia, estrategias de mallado |
| **GATE 1B** | *rotor operating state*: relación **RPM ↔ masa ↔ empuje ↔ configuración de rotor ↔ atmósfera** | CFD **cuantitativo**, afirmaciones de magnitud de downwash | topología, dominio, refinamientos, comparaciones **relativas** a igualdad de hipótesis de empuje |

**Al cerrar 1A:** congelar `geometry-v1` y registrar hashes para que la geometría no cambie en
silencio durante el DOE. Criterios completos en `geometry/protocolo_geometria.md` §8.

> **Regla vigente:** con 1B abierto, todo CFD es **exploratorio** y no puede entrar al dataset ni al
> paper como dato de la plataforma real.

### 8.3 Decisión pendiente: frontera CFD por RPM o por empuje

Pregunta **previa** a la campaña de medición, porque determina qué dato es necesario:

| Estrategia | Frontera | Dato experimental necesario |
|---|---|---|
| **A. RPM prescrita** (MRF / sliding mesh / ALM) | ω + geometría de pala | RPM en condición real **y** geometría de pala fiable |
| **B. Empuje prescrito** (actuator disk) | Δp o distribución de fuerza | empuje por rotor en la condición de vuelo |
| **C. Sustentación impuesta** (empuje = peso) | reparto de carga | masa total + reparto de empuje (CG y ángulos) |

Recomendación provisional: **B/C para el dataset principal** y **A en casos selectos**, para que el
cuello de botella no dependa de la geometría de pala (el dato más caro). Requiere decisión del
investigador. Detalle en `geometry/protocolo_geometria.md` §6.1.

### 8.4 Relación geométrica candidata (no elevada a ley)

`span_candidato = D_axis/√2 + diámetro de rotor` coincide con el sobre desplegado en T25P (+0,49 %)
y T100 (+0,05 %), y **no** en T55 (+2,90 %) ni T70P (+3,92 %).
Es una **prueba de consistencia**: con 2 coincidencias y 2 desviaciones no alcanza para tratarla como
identidad geométrica, y la desviación tampoco demuestra error de la especificación.
Hipótesis alternativas y cómo discriminarlas: `geometry/protocolo_geometria.md` §7.1.

---

## 9. Gestión de riesgos (actualizada tras confirmaciones)

| ID | Riesgo | Tras confirmaciones | Gravedad | Mitigación |
|---|---|---|---|---|
| R1 | RPM/empuje desconocidos | **Resoluble**: acceso físico + docs; telemetría pendiente de permiso | Alta (técnico principal) | **RPM en hover real primero** (tacómetro/cámara), bancada después; estimación inversa solo como contraste; incertidumbre ± objetivo 10 % |
| R2 | Geometría no fiel | **Resoluble**: medición directa | Alta→Media | Protocolo de medición; GATE 1A; sensibilidad |
| R3 | Mesh independence no alcanzable | Depende del hardware | Media | Presupuesto previo; AD para screening, MRF para selección |
| R4 | Modelo de turbulencia insuficiente | Pregunta abierta | Media | SST vs k-ε; LES selectivo |
| R5 | Evaporación/deriva en gotas finas | — | Media | Sanity check; reportar límite |
| R6 | Variabilidad experimental | Instrumentos a confirmar | Media | Ventanas de calma; repeticiones; estadística |
| R7 | Acceso físico a drones | **Resuelto** | — | — |
| R8 | Falta de literatura / novedad falsa | Pendiente PHASE_00 | Media | Revisión sistemática pre-publicación |
| R9 | One-way coupling inválido a caudales altos | — | Baja-media | Comparación two-way antes de dataset |
| R10 | Reproducibilidad | — | Media | Versiones congeladas; casos completos; hash de `geometry-v1` |
| R11 | Daños/garantía de drones en pruebas | Acceso físico confirmado ⇒ gestión | Media | Protocolo de prueba no invasivo; permisos de operador; insured/estacionario |
| R12 | Instrumentos de anemometría/espectro no disponibles | A confirmar | Media | Priorizar colectores+trazador; hidrosensibles; colaboraciones |
| R13 | **Nuevo:** conflicto de fuentes oficiales sobre el nº de rotores del T100 (8 vs 16) | Detectado 2026-09-14 | Media | Conteo directo (A9) **antes de mallar**; error si no se resuelve: área de disco al doble, v≈√2 |
| R14 | **Nuevo:** el T55 carece de evidencia visual y de sección propia en el material Academy | Detectado 2026-09-14 | Media | Medición directa; extraer decks 04–09; buscar documentación específica del T55 |
| R15 | **Nuevo:** WSL/OpenFOAM no accesible desde el entorno actual | Detectado 2026-09-14 | Media | Confirmar disponibilidad de OpenFOAM antes de comprometer el plan CFD |

**Presupuesto de incertidumbre (§41):** se asignan contribuciones (geometría, RPM, malla, turbulencia, gotas, instrumentos, surrogate) con objetivos numéricos y se documenta que no se reporta precisión falsa.

---

## 10. Ética, conflicto de interés, propiedad intelectual, autoría

- **COI (§31):** investigador en empresa distribuidora de Agras. Declaración explícita desde diseño y manuscrito. El estudio es independiente salvo participación formal de DJI.
- **IP (§32):** checklist de propiedad (equipo, financiación, datos, CAD, software, resultados) a completar antes de PHASE_02.
- **Autoría (§33):** CRediT, basada en contribución real.
- **Permisos:** telemetría/firmware/info interna solo con autorización escrita.

---

## 11. Papers y difusión

- Evaluar 1–3 papers (§34): (1) aerodinámica/downwash; (2) gotas y deposición; (3) surrogate + optimización de interlineado. No fragmentar artificialmente.
- Candidatos M: revistas de ingeniería agrícola/drones (p. ej. Computers & Electronics in Agriculture, Biosystems Engineering, Drones, Precisión Agriculture, Agronomy, Journal of Applied Fluid Mechanics) — lista a refinar con la revisión de literatura y el perfil del equipo.
- Dataset abierto/parcialmente abierto como valor científico independiente de la app.

---

## 12. Hitos y próximas acciones concretas

**Próximo hito (no es "ejecutar OpenFOAM"):** **CERRAR GATE 1A — geometry validated**
(`geometry/protocolo_geometria.md` §8). Al cerrarlo: congelar `geometry-v1` con hash.

**Inmediatas:**
1. **Convocar la campaña de medición** con acceso físico, siguiendo los bloques A–D del protocolo.
   Mínimo bloqueante: bloques **A** (sistema propulsivo) y **B** (atomizadores) para GATE 1A.
2. **Resolver el conflicto del T100 (8 vs 16 rotores)** por conteo directo antes de mallar. [R13]
3. **Buscar evidencia del T55**: extraer los decks 04–09 y localizar documentación específica. [R14]
4. **Decidir la estrategia de frontera CFD** (§8.3): RPM prescrita vs empuje prescrito vs sustentación.
   Es decisión previa a la medición porque define qué dato hay que capturar.
5. **Convertir el EMF vectorial de la slide 09** (16 MB, diagrama rotulado) — requiere Inkscape o
   ImageMagick. Es el mejor candidato para leer posiciones relativas sin escala externa.
6. **Confirmar disponibilidad de OpenFOAM/WSL** en el entorno de trabajo. [R15]
7. **PHASE_00 literatura** en paralelo: búsquedas, matriz de literatura verificada y actualización de
   la declaración de novedad. El hallazgo del deck 03 (tablas solo de T40/T50) refuerza el hueco.
8. Repositorio Git ya inicializado y `.gitignore` configurado.

**Decisiones que el investigador debe tomar:** (a) aprobar la partición de GATE 1 en 1A/1B;
(b) estrategia de frontera CFD (§8.3); (c) ejecutar la campaña de medición y entregar
`data/raw/mediciones_geometria.csv`; (d) indicar hardware e instrumentos disponibles;
(e) permisos para telemetría (R1).

---

*Documento que unifica CONTEXT.md + RESEARCH_ARCHITECTURE_V1.md + Research Plan v1. Sometido a aprobación del investigador principal; tras aprobación empieza PHASE_00/PHASE_01.*