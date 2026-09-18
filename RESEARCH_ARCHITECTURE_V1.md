# RESEARCH_ARCHITECTURE_V1.md

> **Estado:** Aprobado conceptualmente (2026-09). Consolidado en `PROJECT_MASTER_PLAN_V1.md` como documento de operación único; este archivo conserva el detalle técnico de referencia.
> **Hipótesis, cifras de especificación y costos computacionales contenidos aquí son provisionales.** Ningún valor de ficha técnica presentado como "estimado"/"desconocido" debe tratarse como dato medido.
> **Regla que rige este documento:** no se fabrican especificaciones ni referencias. Todo dato crítico lleva una etiqueta de procedencia: P (público), M (medido), I (inferido), E (estimado), D (desconocido).

---

## Índice

1. Problem definition
2. Scientific relevance
3. Literature gap
4. Novelty hypothesis
5. Scope
6. Out-of-scope variables
7. Four UAV comparison matrix
8. Missing engineering information
9. Governing equations
10. CFD approach comparison
11. Recommended initial solver
12. Turbulence model recommendation
13. Droplet model recommendation
14. Coupling recommendation
15. Validation experiment
16. DOE proposal
17. Surrogate proposal
18. Data schema
19. Computational estimate
20. Scientific risks
21. Publication risks
22. Conflict-of-interest considerations
23. Recommended order of execution
24. Explicit stop/go criteria for the next phase

---

## 1. Problem definition

Se busca caracterizar y predecir, para cuatro plataformas agrícolas DJI Agras independientes (T25P, T55, T70P, T100), el campo aerodinámico tridimensional generado por sus rotores (downwash, estelas, interacción rotor-rotor, turbulencia) y su influencia sobre el transporte de gotas de agua y la deposición espacial D(x,y) sobre un plano receptor.

**No** se define como objetivo primario calcular un "ancho de trabajo nominal". El ancho efectivo, la uniformidad y el interlineado recomendado son **resultados derivados** del campo completo de deposición.

Pregunta científica principal:

> ¿Cómo modifican la arquitectura específica del UAV, la masa transportada, la velocidad de avance, la altura de pulverización, el tamaño de gota y la configuración espacial de atomizadores el campo aerodinámico y la distribución espacial de deposición de una pulverización agrícola?

Preguntas secundarias (sección 5 del contexto): campo de velocidades u,v,w; cambios con masa, velocidad, altura; comportamiento de gotas por diámetro; deposición transversal y bidimensional; 2 vs 4 atomizadores; posición espacial de atomizadores; efecto operacional del vaciado del tanque; viabilidad de surrogate model y de interpolador reducido para app móvil.

**Restricción de diseño:** cada UAV se modela por separado. No se construye una ecuación universal multi-modelo. Cualquier aproximación futura entre modelos debe demostrarse formalmente (semejanza geométrica/aerodinámica), no asumirse.

**Marco operativo de referencia (aislar variables propias del UAV):**

| Variable | Valor de referencia |
|---|---|
| Temperatura del aire | 28 °C |
| Humedad relativa | 70 % |
| Viento | 0 m/s (calma) |
| Altitud | 0 m s. n. m. |
| Presión | 1013.25 ± variación por 28 °C y humedad |
| Fluido pulverizado | Agua pura (sin adjuvantes) |
| Cultivo / canopia / terreno | Ninguno (plano receptor horizontal rígido) |

Propiedades del agua a ≈28 °C: densidad ≈996 kg/m³, viscosidad dinámica ≈0.83–0.84 mPa·s, tensión superficial ≈71.5–72.0 mN/m, presión de vapor ≈3.8 kPa (valores de referencia a verificar contra fuentes primarias, p. ej. tablas IAPWS/CRC; [E]).

---

## 2. Scientific relevance

1. **Seguridad y eficacia de aplicación:** la deposición desigual (sobre/sub-aplicación) compromete eficacia fitosanitaria, deriva y residuos. Conocer D(x,y) y su variabilidad permite interlineados basados en física.
2. **Economía operacional y ambiental:** reducir solapamiento innecesario y deriva tiene impacto directo en costos y contaminación.
3. **Decisión de compra/operación:** comparar plataformas con métricas consistentes (no folletos) da criterios objetivos.
4. **Diseño de futuras plataformas:** la relación posición-atomizador/estela es información de ingeniería reutilizable por fabricantes.
5. **Producto derivado reproducible:** el dataset y el surrogate pueden servir a apps de operadores sin ejecutar CFD (sección 2 del contexto), conservando valor científico incluso sin la app.

---

## 3. Literature gap

**Gap formal (provisional, a confirmar en PHASE_00).**

La literatura publicada sobre downdraft/pulverización de UAV agrícolas (CFD + experimentos) está dominada por:
- plataformas de generación anterior o de pequeño tamaño (octocópteros 8–25 L);
- estudios en un solo modelo o con geometrías simplificadas (disco actuador sin aeronave);
- análisis de un único atomizador central o distribuciones transversales 1D;
- ausencia de comparación controlada entre plataformas actuales con geometría realista;
- escasez de validación experimental sistemática del campo de viento *y* de deposición sobre el mismo banco.

La comparación simultánea de **cuatro plataformas Agras actuales (T25P, T55, T70P, T100)**, con modelos independientes, posición real de atomizadores (2 vs 4), efecto de carga y un surrogate validado fuera de muestra, constituye un hueco razonable si la revisión sistemática lo confirma. **La afirmación de novedad quedará subordinada a la revisión.** (Matriz de literatura: plantilla en sección 3.1; celdas a completar con referencias verificadas, no fabricadas.)

### 3.1 Plantilla de matriz de literatura (a completar en PHASE_00)

| Autor | Año | UAV | Método CFD | Modelo de turbulencia | Modelo de gota | Variables | Validación | Hallazgos | Limitaciones | Relevancia |
|---|---|---|---|---|---|---|---|---|---|---|
| (a rellenar con refs verificadas) | | | | | | | | | | |

**Estrategia de búsqueda:** Scopus/Web of Science/Google Scholar + literatura gris (DJI, congresos ASABE). Queries (inglés/español): "agricultural UAV spraying", "rotor downwash", "spray deposition drone", "actuator disk multirotor CFD", "MRF rotor simulation", "Lagrangian particle tracking droplet UAV", "effective swath", "transverse distribution", "water sensitive paper drone", "T25/T40/T50/T55/T70P/T100". Criterios de inclusión/exclusión explícitos a definir; tabla de 20–60 referencias.

**Importante:** no se incluirá ninguna referencia que no haya sido localizada y verificada.

---

## 4. Novelty hypothesis

**Novelty provisional (dependiente de GATE de literatura):**

1. Comparación directa de cuatro plataformas Agras actuales con geometría realista y modelos independientes (no extrapolación entre modelos).
2. Cuantificación de la interacción posición-de-atomizador/estela-rotor (delante/detrás/lateral) para configuraciones de 2 y 4 atomizadores.
3. Evaluación experimental del efecto de carga del tanque sobre downwash y sobre deposición integrada D̄(x,y) = ∫D(x,y,m(t))dt — sin asumir a priori su significancia (H5).
4. Métricas de deposición 2D completas (D(x,y)), no solo perfil transversal.
5. Surrogate model por dron (D̂_T25P, D̂_T55, D̂_T70P, D̂_T100) con salida funcional D(x) y estimación de incertidumbre, validado fuera de muestra con CFD nuevo y con experimento.
6. Dataset/artefactos reproducible (configuración CFD completa, scripts, versionado).

La hipótesis de novedad será **falsada o matizada** por la revisión sistemática; el documento final declarará la novedad real demostrada.

---

## 5. Scope

**Entra en el estudio (primer paper):**
- Campo de aire (a u,v,w, presión, turbulencia) de cada UAV en vuelo estacionario y en traslación rectilínea uniforme (agua, condiciones estándar).
- Transporte y deposición de gotas monodispersas y, posteriormente, distribuciones (D10/D50/D90) sobre plano receptor.
- Variables: modelo UAV; masa/carga (100/75/50/25/0 %); velocidad de avance; altura; tamaño de gota; número y posición de atomizadores; caudal.
- Estrategias CFD niveles 0–5, con decidir qué nivel es suficiente para el dataset principal.
- Validación experimental (viento + pulverización con agua).
- DOE, surrogate, métricas de uniformidad, interlineado óptimo por patrón.
- Mecánica conceptual para modos futuros (máxima productividad/cobertura/eficiencia).

**Fuera de alcance (primer paper):**
- Pesticidas, fertilizantes, surfactantes, adjuvantes, mezclas con densidad/viscosidad no estándar.
- Cultivos, canopia, dosel, terreno irregular.
- Viento exterior, cizalladura atmosférica, turbulencia ambiente, efecto de atmósfera real.
- Evaporación como mecanismo de pérdida dominante (se incorpora solo como check de magnitud; el presupuesto deposición-vs-evaporación podrá ser objeto futuro).
- Validación con producto fitosanitario real.
- Optimización de dosis por etiqueta de producto (no se recomienda "mínimo consumo" por debajo de etiqueta).
- Aplicación móvil (producto derivado posterior; fuera del manuscrito central aunque el esquema de datos lo habilite).

---

## 6. Out-of-scope variables

| Variable | Motivo de exclusión (fase actual) | ¿Fase futura? |
|---|---|---|
| Viento horizontal exterior | Confunde efecto UAV con transporte por viento | Sí (paper 2/3) |
| Cultivo / canopia / terreno | Añade capa de incertidumbre; primero banco neutro | Sí |
| Productos fitosanitarios / adjuvantes | Cambian tensión superficial, viscosidad, deriva | Sí |
| Sombra de viento por vegetación | Ídem | Sí |
| Evaporación (criterio de pérdida) | Se computa solo como sanity check | Sí |
| Vuelo con virajes / aceleraciones | Primero vuelo estabilizado | Sí |
| Vuelo multi-UAV / formación | Fuera de alcance | Futuro |
| Ausencia de obstáculos/estructuras | Banco ideal | — |

---

## 7. Four UAV comparison matrix

**Regla de integridad:** esta matriz NO está completa. Solo se incluyen celdas con procedencia conocida; el resto queda "D – desconocido, pendiente de fuente oficial o medición". Ningún número se inventa. Cuando el agente disponga de un valor de conocimiento general razonable pero no verificable al escribir este documento, se anota como **[E]** (estimado) en el cuerpo y **se marcará para verificación** antes de usarse en geometría.

La fecha de escritura (2026-09) implica que T25P, T55, T70P y T100 pueden ser plataformas cuya ficha pública detallada está fuera de los datos confiables del agente. Por tanto, el plan asigna **obtención de fichas oficiales (P)** como tarea de entrada de PHASE_01, con respaldo de medición física (**M**) para parámetros críticos si DJI no publica (p. ej., RPM y curvas de empuje — ver sección 8 y riesgo R1).

Estados de procedencia: **P** público (fuente oficial), **M** medido (protocolo propio), **I** inferido (de publicaciones de modelo cercano + argumento explícito), **E** estimado (planning only), **D** desconocido.

| Parámetro | T25P | T55 | T70P | T100 | Procedencia / fuente requerida |
|---|---|---|---|---|---|
| **A. Geometría** | | | | | |
| Longitud / anchura / altura | D | D | D | D | Manual del usuario, página DJI, catálogo distribuidor |
| Wheelbase / disposición | D | D | D | D | Ídem + fotogrametría |
| N.º de rotores | D | D | D | D | Ficha oficial / imagen de alta resolución |
| Posición XYZ de cada rotor | D | D | D | D | CAD publico/medido o fotogrametría calibrada |
| Diámetro de rotor | D | D | D | D | Ficha/medición física |
| N.º de palas por rotor | D | D | D | D | Fotografía de alta velocidad / ficha |
| Brazos / cuerpo / tanque | D | D | D | D | CAD simplificado propio |
| Tren de aterrizaje relevante al flujo | D | D | D | D | Foto/medición |
| **B. Masa** | | | | | |
| Masa vacía (sin líquido/baterías) | D | D | D | D | Manual/especificaciones oficiales |
| Masa máxima de despegue | D | D | D | D | Ídem |
| Carga líquida máxima | D | D | D | D | Ídem |
| Masa total a 100/75/50/25/0 % | D | D | D | D | Derivado (suma directa) |
| **C. Propulsión** | | | | | |
| Motor (modelo, KV) | D | D | D | D | Ficha oficial / medición |
| RPM nominal por régimen | D | D | D | D | **Telemetría autorizada / tachómetro óptico** (R1) |
| Empuje total y por rotor | D | D | D | D | Curva empuje vs RPM (fuente o banco propio) |
| Torque / potencia | D | D | D | D | Ídem |
| **D. Pulverización** | | | | | |
| Tipo de atomizador (rotativo/centrífugo/hidráulico) | D | D | D | D | Ficha oficial / catalogación |
| Cantidad de atomizadores (2 y 4) | D | D | D | D | Ídem |
| Posición XYZ de cada atomizador | D | D | D | D | CAD/medición (crítico: delante/detrás/lateral, §8) |
| Orientación / ángulo de descarga | D | D | D | D | Ídem |
| Caudal max / típico por config | D | D | D | D | Ficha oficial + prueba de bancada |
| Presión de pulverización | D | D | D | D | Ídem |
| Rango de diámetro de gota (VMD/d33) | D | D | D | D | Ficha/medición con láser (p. ej. Sympatec/PDI) |
| **E. Operación** | | | | | |
| Velocidad min / max de aplicación | D | D | D | D | Manual/guías oficiales |
| Altura típica de pulverización | D | D | D | D | Ídem |
| Límites (pendiente, viento) | D | D | D | D | Ídem |

**Nota metodológica:** la plantilla se completa con fuentes listadas en *Fuentes candidatas de PHASE_01* (sección 8). Hasta completar la ficha, NO se inicia PHASE_02 (geometría) — ver GATE 1.

---

## 8. Missing engineering information

Lista priorizada de datos faltantes con estrategia de obtención y dificultad:

### R1 — RPM real y curva de empuje/torque (RIESGO PRINCIPAL, sección 42 del contexto)
- Sin RPM real el empuje y el downwash son arbitrarios. **No se infiere RPM de KV.**
- Fuentes: (a) telemetría autorizada del flight controller (con permiso); (b) tachómetro óptico / cámara de alta velocidad sobre hélice; (c) banco de empuje de motor+hélice real; (d) estimación inversa: medir empuje en hover = peso total (balanza integrada o pesaje) y ajustar RPM del rotor modelado hasta igualar empuje (método de calibración cruzada CFD-experimento).
- Clasificación objetivo: M (medido) o P (publicado oficial). Incertidumbre documentada; si no se puede medir, se usa la estimación inversa con propagación explícita de incertidumbre.

### R2 — Diámetro y geometría de hélice
- Medir diámetro/plano de barrido real (regla/cinta) y palas (paso, twist, perfil: fotografía + aproximación BEMT o CAD). Si no hay CAD, reconstrucción aproximada con tratamiento como hélice de paso/distribución conocida genérica **[I/E]**.

### R3 — Posición exacta de atomizadores (XYZ y orientación)
- Es determinante para H3 (efecto configuración de atomizadores). Medición física con cinta/láser y fotogrametría sencilla; registrar sistema de coordenadas (cuerpo). Si hay versión 4-atomizadores, ¿los adicionales van delante/detrás/lateral? Esto se verifica de forma empírica por plataforma.

### R4 — Caudales y tamaño de gota real
- Bancada de pulverización estática: recolectar caudal por atomizador; obtener VMD y espectro con laboratorio de caracterización (PDI/Sympatec) o, en su defecto, tarjetas hidrosensibles (calidad ordinal). El valor de VMD nominal de catálogo se contrasta con medición.

### R5 — Masa y centros de gravedad
- Pesar por componente; MTOW; masa con tanque al 100/75/50/25/0 %. Para CFD lo relevante es el empuje requerido (tiene que equilibrar peso en hover) → se propaga a RPM.

### R6 — Configuración propulsiva por modelo
- N.º rotores, coaxialidad real (¿rotores en tándem coaxial superior/inferior o en planta plana?), sentido de giro, RPM relativa. Determinar con fotos y documentación oficial.

### R7 — Procedencia de "P" (públicos) verificable
- Páginas oficiales DJI, manuales de usuario PDF, páginas de distribuidores autorizados, informes de homologación/FCC si existen. **Todo P se cita con URL capturada y fecha de acceso.**

### Plan de prioridad (PHASE_01 → GATE 1)
1. Obtener fichas oficiales (P) de los 4 modelos.
2. Medir (M): diámetro rotor, posiciones atomizadores, masas, caudales, espectro de gota.
3. Establecer RPM (M o I) con plan de telemetría autorizada o estimación inversa.
4. Consolidar ficha maestra por UAV en `docs/specs/` con metadatos de procedencia por celda.

---

## 9. Governing equations

### 9.1 Flujo (aire, fase continua)
Se asume aire incompresible (Ma << 0.3 en la zona de interés fuera del plano de rotor) y flujo newtoniano. Ecuaciones RANS (también aplicables URANS):

- Continuidad: ∇·u = 0
- Momento:
  ρ (∂u/∂t + u·∇u) = −∇p + ∇·[μ (∇u + ∇uᵀ)] − ρ∇·(u'⊗u') + f_body  (con f_body = fuerzas de actuación rotor/gravedad donde corresponda)

donde el tensor de Reynolds u'⊗u' se cierra con el modelo de turbulencia. Para LES (solo si se justifica): ecuaciones FNS filtradas con modelo sub-rejilla (p. ej. WALE/Smagorinsky dinámico).

### 9.2 Turbulencia (candidatos)
- **SST k-ω** (Menter, 1994): dos ecuaciones para k y ω; mejora comportamiento en gradientes adversos y propagación de estelas; ampliamente usado en literatura de multirotor. **Candidato primario.**
- **Realizable k-ε** (Shih et al., 1995): robusto en regiones libres; se comparará contra SST en un subconjunto de casos.
- **LES**: solo si se justifica por física de interacción estela-estela / dispersión turbulenta de gotas y se dispone de recursos (ver §19).

### 9.3 Gotas (fase dispersa, enfoque Lagrangiano)
Partículas de agua (ρ_d ≈ 996 kg/m³), esféricas a presión/sin gas, con:

- Ecuación de traslación (pasante en flujo con Re_p y corrección de Schiller–Naumann):
  du_p/dt = (u − u_p)/τ_p · f_Re + g (1 − ρ/ρ_d)  [+ F_Saffman, F_Magnus opcional]
  con τ_p = ρ_d d²/(18 μ) y f_Re = 1 + 0.15 Re_p^0.687.
- Número de Stokes: St = τ_p · U_ref / L_ref (definir U_ref = velocidad inducida característica, L_ref = longitud característica de estela/diámetro rotor).
- Número de Reynolds de partícula: Re_p = ρ |u−u_p| d / μ.
- Dispersión turbulenta: eddy lifetime / random walk; comparar con modelo de difusión turbulenta de partículas.
- Evaporación: útil solo como sanity check de pérdida de masa en gotas VMD < 150 µm a 70 % RH; se documenta y se decide si se incluye.
- Diámetros: inicial monodisperso (aislar física); luego D10/D50/D90 o distribución (Rosin–Rammler/lognormal) por configuración.

### 9.4 Acoplamiento gas/gota
- One-way coupling si la carga de masa/impulso es despreciable; two-way coupling si es significativa.
- Estimación a priori (¿two-way?): con caudal representativo Q ≈ 0.1–0.2 kg/s de líquido y flujo másico de aire del conjunto de rotores O(10²) kg/s, la razón de carga de masa se estima en el orden de 10⁻³. **Con este orden de magnitud, one-way coupling es la hipótesis de partida**, pero se verifica con un caso comparativo two-way vs one-way (GATE interno Fase B/C). No se asume; se demuestra.

---

## 10. CFD approach comparison

| Nivel | Método | Representación del rotor | Costo relativo | Uso propuesto | Ventajas | Limitaciones |
|---|---|---|---|---|---|---|
| 0 | Momentum theory (glauert) | Ninguna (disco ideal) | ~0 | Sanity checks de v_inf, empuje, flujo | Rápido, cierra órdenes de magnitud | No da campo espacial real |
| 1 | Actuator Disk (AD) | Salto de presión / fuente de momento en disco delgado | Bajo | Exploración rápida del campo dentro/fuera de estelas; screening DOE | Simple, robusto | Sin dinámica de palas ni tip vortices resueltos |
| 2 | Actuator Line (ALM) | Fuerzas distribuidas en líneas que representan palas (BEMT) | Medio | Solución intermedia; captura tip vortices y carga radial | Mejor física que AD a costo moderado | Requiere regularización y calibración de parámetros |
| 3 | MRF | Geometría de rotor completa en región rotatoria estacionaria | Medio-alto | **Candidato para dataset principal** si pasa verificación | Captura efectos 3D de pala con bajo costo por caso | Estado estacionario aproximado; no resuelve transitorio absoluto |
| 4 | Sliding Mesh | Malla rotativa transitoria | Alto | Casos selectos de alta fidelidad + validación MRF | Máxima fidelidad rotacional-resuelta | Costoso; requiere timestep independence |
| 5 | Experimento | — | Alto (humano+instrumento) | Validación final (aire y pulverización) | Verdad de referencia | Costo, repetibilidad, condiciones reales |

**Decisión preliminar (a confirmar tras Fase A/B):** jerarquía nivel 0 → 1 → 3, con nivel 4 como referencia puntual y nivel 2 opcional intermedio. Se evalúa si MRF (nivel 3) es suficiente para el dataset principal comparándolo con un caso sliding mesh (nivel 4). **No se decide el nivel del dataset principal sin esa comparación.**

---

## 11. Recommended initial solver

**OpenFOAM** (open-source, reproducible). Candidatos específicos:
- **Líquido en versión estable de OpenFOAM** (público/build reproducible, p. ej. `openfoam.com/org` 23xx/24xx) con solvers:
  - RANS estacionario: `simpleFoam` / `buoyantSimpleFoam` (con densidad constante y opción de flotabilidad) — con adición de fuerzas de actuador (AD: `fvOptions` momentumSource; ALM: `fvOptions`/código propio).
  - MRF: `MRFSimpleFoam` / `simpleFoam` con `MRFProperties`.
  - Sliding mesh / transitorio: `pimpleFoam` + `dynamicMesh` (AMI) para caso selecto.
  - Dispersión de gotas: `foamDiscretePhase`/`kinematicCloud` (Lagrangian) — verificar disponibilidad en la versión elegida; alternativa: solvers lagrangiano estándar de la distribución (para gotas no reactivas es suficiente `kinematicCloud` con `dispersionModel`, `dragModel` SchillerNaumann, `gravity`).
- **Mallado:** Gmsh (externo, paramétrico) + `snappyHexMesh` para las geometrías reales; bloques estructurados para dominios simples.
- **Visualización:** ParaView.
- Toda la cadena de versiones se congela en un fichero de entorno/reproducibilidad (ver §18 y plan de contenedor Docker si se dispone).

**Nota:** la selección definitiva de solver/turbulencia/malla se fija después del mesh independence study de la Fase A. Cualquier elección se justifica por literatura y experimento comparativo, no por costumbre.

---

## 12. Turbulence model recommendation

- **Primario propuesto: SST k-ω.** Justificación prevista: buena respuesta a gradientes adversos y separación (relevante en estelas, tip vortices y su interacción); uso extendido en simulación de multirotores/UAV en la literatura (a revisar y citar con referencias verificadas en PHASE_00).
- **Comparación contra realizable k-ε** en un subconjunto de casos (p. ej. caso base + un caso alto/velocidad + un caso cargado) con métricas: V_z(x,z), anchos de estela, CV de deposición.
- **Criterio de aceptación del modelo:** diferencias en variables de interés dentro del presupuesto de incertidumbre definido en §19; en caso contrario se documenta sensibilidad y se reporta como límite.
- **LES:** no inicial. Se evaluará solo si hay pregunta física abierta de interacción estela-dispersión que RANS-URANS no pueda responder y recursos disponibles.

---

## 13. Droplet model recommendation

- **Euler-Lagrange (parcelas)**, fase continua RANS; gotas esféricas no reactivas (agua) con fuerzas: drag (Schiller–Naumann), gravedad/flotabilidad, dispersión turbulenta por eddy lifetime. Evaluar Saffman lift y Magnus solo si el análisis de sensibilidad lo justifica.
- **Monodisperso primero** (aislar física; facilita matriz de sensibilidad): d ∈ {100, 200, 300, 400, 500} µm propuesto, rango a confirmar con la medición real VMD de cada atomizador.
- Luego **distribuciones** (D10/D50/D90 y espectro medido) vía muestreo de parcelas.
- **Inyección:** condiciones iniciales por atomizador (posición XYZ, orientación, velocidad inicial, caudal, distribución) tomadas de la ficha maestra §7.
- Verificación de **one-way vs two-way** (§9.4) con caso comparativo preliminar antes de producir el dataset principal.

---

## 14. Coupling recommendation

- **Hipótesis inicial: one-way coupling** (motivo: razón de carga de masa líquido/aire estimada ~10⁻³; §9.4).
- **Plan de demostración:** correr un caso con caudales máximos y gota mínima, one-way vs two-way (acoplamiento en términos de fuente de momento en la celda de la parcela). Criterio: si la variación de deposición/velocidad entre one- y two-way excede el presupuesto de incertidumbre, se adopta two-way para caudales altos. **No se adopta sin la comparación.**

---

## 15. Validation experiment

### 15.1 Línea A — Validación de campo de viento (antes que pulverización)
- **Setup:** dron en hover (GPS/RTK estacionario) a altura H definida sobre el suelo, sin viento exterior (calma meteorológica; ventana de viento < 1 m/s verificada).
- **Instrumentos:** sondas/estaciones de anemométria sónica 3D (u,v,w) montadas en mástil o rejilla; barrido de posiciones (x,y) bajo el dron, p. ej. grid de 0.5 m; perfil vertical en al menos el eje de estela. Hot-wire como alternativa en wake cercano (si disponible). Cámara de alta velocidad para RPM (R1).
- **Campaña:** medir V_z(x,y,H) y perfil de velocidad total para ≥3 alturas; repeticiones ≥3; registrar incertidumbre instrumental y ambiental.
- **Comparación CFD vs experimento:** RMSE, MAE, R², bias, error relativo por bin espacial. Publicación de mapas de diferencia.

### 15.2 Línea B — Validación de pulverización
- **Setup:** línea transversal de colectores (longitud suficiente para capturar todo el patrón; separación 0.25 o 0.50 m según ancho característico); pasadas paralelas a velocidad y altura controladas; agua con trazador fluorescente (cuantificación por fluorescencia/espectrofotometría) y, en paralelo, tarjetas hidrosensibles para recuento de gotas/cobertura.
- **Datos:** D_exp(x) por colector; construir perfil transversal integrado en y; repetir ≥3.
- **Comparación:** D_exp(x) vs D_CFD(x) con métricas RMSE/MAE/R²/bias y análisis de perfil (posición de máximos, asimetría, CV).
- Si el terreno lo permite, grid 2D de colectores no destructivo para D_exp(x,y).

### 15.3 Condiciones
- Documentación de temperatura, HR, viento, presión por ensayo (referencia §3). Franja horaria, número de repeticiones, protocolo de calibración de colectores y de trazador. Los datos se almacenan en `/experiments/`.

---

## 16. DOE proposal

### 16.1 Variables y rangos (por UAV, físicamente válidos, se definen en PHASE_01 con la ficha maestra)
- V (velocidad de avance): mínimo–máximo operativo por modelo.
- H (altura sobre plano receptor): rango operativo por modelo.
- d (diámetro de gota): monodisperso en {100–500} µm a confirmar; luego distribución.
- L (carga): {100, 75, 50, 25, 0} % de tanque.
- Config: {2, 4} atomizadores × posición (delantera/trasera/lateral).

### 16.2 Método
- **LHS / secuencias Sobol** para variables continuas (espacio estelar); las configuraciones discretas se tratan como factores cruzados por UAV.
- **Central Composite / Box-Behnken** como alternativa para construir superficies de respuesta en el espacio continuo si el costo lo permite; comparar eficiencia.
- **Adaptive sampling** (active learning) en la fase surrogate con GP: nueva CFD donde la incertidumbre del GP o el gradiente estimado sea alto (sección 27 del contexto).
- Réplicas: 2–3 por punto de validación crítico.

### 16.3 Size preliminar (planning)
- Fase A–E en T25P: screening (20–40 casos); DOE principal (80–150 casos RANS nivel 3) + casos MRF/Sliding (~5). Las Fases F–H replican subconjunto proporcional definido tras resultados de T25P. Cifras a ajustar con costo real (§19).
- Presupuesto de simulación claramente separado en `cfd/cases`.

---

## 17. Surrogate proposal

- **Objetivo:** por dron, D̂(x | V, H, d, L, config) que reproduzca D(x) completo (o su proyección) con incertidumbre.
- **Enfoque:**
  1. Reducción de dimensionalidad funcional del output D(x) mediante PCA/FPCA (o 1D-GP sobre perfil) para trabajar con pocos coeficientes.
  2. **Gaussian Process Regression** (kernel anisotrópico) como candidato principal (interpretable, con incertidumbre, natural para active learning).
  3. Comparar con: RSM (polinomios), XGBoost, Random Forest. Redes neuronales solo si superan a los anteriores en validación y son justificables.
  4. Rangos: extrapolación explícitamente prohibida fuera del dominio DOE.
- **Validación:** partición train/validation/test + CFD nuevo fuera del espacio de entrenamiento (GATE 5: no usar en app sin validación outside-sample); métricas R², RMSE, MAE, error relativo, intervalos de confianza.
- Producto derivado para app: tabla comprimida + interpolador lineal local o GP ligero (ver §29 del contexto).

---

## 18. Data schema

### 18.1 Estructura de directorios (contexto §38)
```
DRONEWITH/
  docs/            # arquitectura, protocolos, especificaciones
  literature/      # papers, matriz, notas de lectura
  data/raw/        # mediciones experimentales + datos de ficha
  data/processed/  # datos limpios, derivados
  geometry/        # CAD simplificado por UAV (FreeCAD/Blender/Gmsh)
  cfd/cases/       # casos completos (configuración íntegra por caso)
  cfd/templates/   # plantillas reutilizables
  cfd/results/     # salidas crudas y post-proceso
  experiments/     # protocolos, hojas de datos, imagenes
  surrogate/       # modelos entrenados, métricas
  notebooks/       # análisis exploratorio
  scripts/         # utilidades reproducibles (Python/OpenFOAM)
  figures/         # figuras de publicación
  paper/           # manuscrito
  supplementary/   # material suplementario
  logs/            # research_log.md
```
Versionado Git desde el inicio; inmutabilidad de datos crudos (raw read-only).

### 18.2 Base de datos científica (contexto §28) — esquema mínimo
Tabla `cases` / `simulations`:
- id, UAV_model, config_atomizadores, V, H, d, carga, caudal, metodo_CFD, solver_version, mesh_id, modelo_turbulencia, mesh_density (coarse/medium/fine), timestep_id, convergencia_residuos, estado_validacion, fecha, software_version, tipo (aire/droplet), incertidumbre_documentada.

Tabla `deposition`:
- case_id, x, y, D(x,y) [mL/m² o g/m²], D_transversal_promediada(x), CV, asimetria, P10/P50/P90, ancho_efectivo, posicion_max/min, % dentro/fuera ancho.

Tabla `airflow`:
- case_id, x, y, z, u, v, w, |U|, p, k, omega (o epsilon), intensidad_turbulenta, TKE.

Tabla `experiments`:
- id, tipo (viento/pulverizacion), fecha, condiciones (T, HR, viento, presión), instrumentos, calibracion_ref, datos_ligados.

Tabla `surrogate`:
- id, UAV_model, tipo_metodo, parametros, r_archivo, métricas (R²/RMSE/MAE), dominio, fecha, validado_out_of_sample (bool).

Formato: CSV comprimido + SQLite como agregación; metadatos YAML/JSON por archivo con procedencia por celda (P/M/I/E/D) y fuente exacta.

---

## 19. Computational estimate

Cifras de **planning**, órdenes de magnitud, a recalcular con el hardware real disponible y tras el mesh/timestep study.

Supuestos preliminares (E, verificar):
- Dominio de cálculo propuesto para Fase A: ~60 m (x) × ~30 m (y) × ~15 m (z), con refinamiento en wake y plano receptor.
- Malla (RANS, nivel de detalle realista – geometría + rotores MRF): coarse ~8–15 M, medium ~20–40 M, fine ~50–80 M celdas (depende de rotores y refinamiento). Solo referencia, no presupuesto de resultado.

| Escenario | Nivel CFD | Celdas | Treoas | Costo por caso (núcleos·h)* | Casos | Costo total núcleos·h |
|---|---|---|---|---|---|---|
| Fase A (1 caso aire, malla medium, RANS-MRF) | 3 | ~30 M | ~100–500 | 500–2 000 | 3 mallas + verificación | 2 000–6 000 |
| Screening T25P (aire, RANS-MRF/caso) | 3 | ~25 M | ~100–500 | 500–1 500 | 30 | 15 000–45 000 |
| DOE principal T25P (con gotas, URANS-MRF) | 3 | ~25–40 M | ~1 000–5 000 | 1 500–6 000 | 100 | 150 000–600 000 |
| Casos high-fidelity (sliding mesh, selecto) | 4 | ~40–60 M | ~5 000–20 000 | 10 000–40 000 | 5 | 50 000–200 000 |
| Fases F–H (T55, T70P, T100) | 3 | ~30–60 M | — | dependerá de nº rotores | subconjunto definido | aquilatar tras Fase A–E |

\* Costo altamente dependiente de hardware. Si el nodo disponible es modesta (p. ej. 8–32 núcleos), los DOE grandes deben seccionarse o adaptarse (actuator disk para screening, MRF para selección). **Se define umbral de recursos antes de iniciar el DOE.**

Plan de contingencia por recursos: si el DOE completo es inviable, se prioriza un subconjunto sobresaliente (V, H, d, carga) y se escala el surrogate con datos parciales + incertidumbre honesta.

---

## 20. Scientific risks

| ID | Riesgo | Gravedad | Mitigación |
|---|---|---|---|
| R1 | RPM/empuje desconocidos (riesgo principal) | Alta | Telemetría autorizada, tachómetro/cámara, banco de motor, estimación inversa por empuje=peso; incertidumbre documentada |
| R2 | Geometría no fiel (especialmente hélices/rotores y posición atomizadores) | Alta | Medición física + modelado simplificado; análisis de sensibilidad; GATE 1 |
| R3 | Mesh independence no alcanzable por recursos | Media | Definir presupuesto; usar nivel AD para screening y MRF para selección; reportar límite |
| R4 | Modelo de turbulencia insuficiente para interacciones estela-dispersión | Media | Comparar SST vs k-ε; valorar LES selectivo |
| R5 | Evaporación/deriva no modelada dominante en gotas finas | Media | Sanity check de evaporación; reportar límite de aplicabilidad |
| R6 | Variabilidad experimental (viento, instrumentos) invalida validación | Media | Ventanas de calma, repeticiones, estadística, documentación |
| R7 | Acceso físico a drones para mediciones (permisos, disponibilidad) | Alta | Protocolo de permisos (§31/§32 contexto); plan B: mediciones en campo del investigador con autorización |
| R8 | Falta de literatura verificada / novedad falsa | Media | Revisión sistemática antes de publicar; matriz de literatura verificada |
| R9 | Supuesto one-way coupling inválido a caudales altos | Baja-media | Caso comparativo two-way antes del dataset |
| R10 | Reproducibilidad débil (versiones de software, casos incompletos) | Media | Congelar versiones, caso completo por carpeta, contenedor si posible |

---

## 21. Publication risks

- **Novedad falsa / gap sobreestimado:** mitigado con revisión sistemática previa y declaración final basada en evidencia.
- **Falta de validación experimental** debilita claims; el gate de publicación exige validación aire y pulverización.
- **Conflicto de interés (distribuidor DJI)** puede arrojar dudas sobre independencia → declarar explícitamente, tratar datos como independientes, no usar info confidencial sin permiso (§31).
- **Difusión de datos sensibles (técnicas de terceros):** usar datos propios en primera instancia.
- **Costo de publicación en open-access vs revista tradicional:** decidir según financiación; el dataset puede ir a repositorio abierto aunque el paper sea closed.

---

## 22. Conflict-of-interest considerations

- Un investigador trabaja en empresa que comercializa/distribuye drones Agras. Esto se declara desde el diseño y en el manuscrito.
- **Regla:** el estudio se trata como independiente salvo participación formal de DJI. No se usan CAD confidencial, curvas de motor no públicas, firmware ni telemetría restringida sin permiso escrito.
- Fuentes prioritarias: públicas (P) y mediciones propias (M). Todo dato procedente de la empresa del investigador se etiqueta y se revisa su independencia.
- Propiedad intelectual (§32): identificar equipo, financiación, propiedad de datos/CAD/software/resultados al inicio — checklist a completar con el investigador antes de PHASE_02.

---

## 23. Recommended order of execution

Mapeo fases de contexto ↔ fases del proyecto con gates:

| Fase | Contenido | Output | Gate de salida |
|---|---|---|---|
| PHASE_00_LITERATURE | Revisión sistemática, matriz de literatura verificada, matriz de novedad | `docs/literature_matrix.md` | Matriz ≥20 refs verificadas; gap confirmado o redefinido |
| PHASE_01_SPECIFICATIONS | Fichas maestras por UAV (P/M/I/E) + lista de desconocidos resueltos | `docs/specs/*.md` + `data/raw/specs_*` | GATE 1: dimensiones principales revisadas; RPM/empuje plan definido |
| PHASE_02_GEOMETRY | CAD simplificado por UAV (FreeCAD/Blender/Gmsh) + dominios | `geometry/` | GATE 1: revisión dimensional; forma apta para mallado |
| PHASE_03_BASELINE_CFD | Fase A: T25P aire; mesh independence (coarse/medium/fine); timestep para transient | `cfd/results/` | GATE 2: convergencia + independencia de malla demostrada |
| PHASE_04_AIRFLOW_VALIDATION | Campaña anemométrica vs CFD (métricas §15.1) | `experiments/`, `figures/` | GATE 3: downwash concuerda razonablemente |
| PHASE_05_DROPLETS | Gotas monodisperso + distribuciones; one-way vs two-way; tamaños | `cfd/results/` | GATE interno: acoplamiento decidido |
| PHASE_06_SPRAY_VALIDATION | Línea de colectores vs CFD deposition | `experiments/`, `figures/` | GATE 3–6: validación cuantitativa |
| PHASE_07_DOE | DOE por UAV/config (LHS/Sobol/adaptive) | `data/processed/dataset_*` | GATE 6: cobertura y calidad |
| PHASE_08_DATASET | Base completa (esquema §18) con metadatos/incertidumbre | `data/processed/`, `cfd/results/` | Integridad y reproducibilidad |
| PHASE_09_SURROGATE | GP (y comparativos) por dron; validación out-of-sample | `surrogate/` | GATE 5 |
| PHASE_10_OPTIMIZATION | Interlineado óptimo por patrón; modos; CV vs spacing | `figures/`, `data/processed/` | Métricas cerradas |
| PHASE_11_PAPER | Manuscrito + suplementario + declaraciones | `paper/` | Revisión interna + revisores |

**Secuencia en el contexto (Fases A–H):** A (T25P aire) → B (gotas) → C (tamaños) → D (carga) → E (2/4 atomizadores) → F–H (T55, T70P, T100). La carga (D) y atomizadores (E) se incorporan en T25P antes de escalar a los otros drones.

**Orden de trabajo inmediato tras este documento (PHASE_00 → PHASE_02):**
1. Confirmación del investigador de: acceso a drones, hardware CFD, dataset de especificaciones oficiales disponible.
2. Ejecutar PHASE_00 (literatura) en paralelo con PHASE_01 (fichas).
3. GATE 1 antes de generar geometría.

---

## 24. Explicit stop/go criteria for the next phase (PHASE_02_GEOMETRY)

**Condiciones para pasar de PHASE_01 → PHASE_02 (GATE 1):**

1. **Fichas maestras de los 4 UAV completas o con plan de cierre** — cada parámetro crítico (diámetro de rotor, nº rotores, posiciones XYZ de atomizadores y rotores, MTOW, carga líquida) etiquetado P (url+fecha) o M (protocolo). Se toleran E/I solo con marca explícita y con plan de medición.
2. **RPM/empuje resuelto en al menos un régimen por UAV** (medido o estimado inverso con incertidumbre < umbral definido, p. ej. objetivo ±10 % en velocidad inducida verificable).
3. **Revisión de dimensiones principales** (longitudes, diámetros, alturas) por el investigador o documentador antes de construir CAD.
4. **Hardware CFD confirmado** y presupuesto computacional definido (núcleos, tiempo, almacenamiento); DOE compatible.
5. **Condiciones de acceso/permiso** (drones, telemetría, propiedad intelectual) documentadas.
6. **Acuerdo sobre condiciones atmosféricas de referencia** (§3) y sobre el método de validación (acceso a anemómetros/colectores confirmado).

**Stop (no avanzar) si:** no hay ficha de al menos T25P para iniciar Fase A (caso base), o no hay mecanismo para obtener RPM con incertidumbre aceptable. En ese caso se ajusta el plan (p. ej., iniciar con geometrías públicamente documentadas y deferred RPM) con revisión explícita.

**Nota:** cumplir estos criterios NO garantiza continuar; el investigador principal revisa este documento (v1) y decide:

- (a) aprobar como está;
- (b) solicitar cambios;
- (c) rechazar puntos específicos.

Tras la revisión se inicia PHASE_00 (literatura) y PHASE_01 (fichas).

---

## Anexo A — Estado de este documento

| Elemento | Estado | Nota |
|---|---|---|
| Problem definition | OK (definitivo) | — |
| Specs de los 4 UAV | **INCOMPLETO (a propósito)** | No se inventan; se completan en PHASE_01 |
| Revisión de literatura | **PLANTILLA** | Referencias a verificar; ninguna fabricada |
| Cifras de costo CFD | E (planning) | Recálculo con hardware real |
| Decisión de solver/turbulencia | Propuesta | A confirmar tras Fase A (verificación) |

---

*Documento generado por agente de investigación. Sometido a revisión del investigador principal antes de continuar a PHASE_02.*