# Registro de fuentes — DJI Academy (material de distribuidor)

**Carpeta original:** `C:\Users\Dimasur\OneDrive\Documents\DJI\Entrega de drones DJI\DJI ACADEMY COMPLETO\`
**Extracción:** `scripts/extract_pptx_text.py`

| # | Presentación | Tamaño | Salida extraída | Estado |
|---|---|---|---|---|
| 01a | `01 Conocimiento básico de un Dron (1).pptx` | 106 857 257 B | `data/raw/dji_academy_01_conocimiento_basico.txt` | ✅ extraída y auditada (§1–§5) |
| 01b | `01 Introducción al Flujo de Trabajo de Entrega de Productos DJI AGRAS.pptx` | 14 901 317 B | `data/raw/dji_academy_01_intro_flujo_trabajo.txt` | ✅ extraída (sin datos técnicos de plataforma) |
| 02 | `02 Planificación de Misión y Modos de Operación en drones DJI AGRAS.pptx` | 60 248 687 B | `data/raw/dji_academy_02_planificacion_mision.txt` | ✅ extraída (§6) |
| 03 | `03 Recomendaciones para la Configuración de Parámetros de aplicación en drones DJI AGRAS.pptx` | 2 612 652 B | `data/raw/dji_academy_03_parametros_aplicacion.txt` | ✅ extraída (§7 — **la más útil para el DOE**) |
| 04 | `04 Instrucciones de uso del sistema de energía.pptx` | 18 200 000 B | `data/raw/dji_academy_04_sistema_energia.txt` | ✅ extraída (§8 — sin evidencia útil) |
| 05 | `05 Precauciones para el uso de agroquímicos con drones AGRAS.pptx` | 6 100 000 B | `data/raw/dji_academy_05_agroquimicos.txt` | ✅ extraída (§8 — sin evidencia útil) |
| 06 | `06 Capacitación sobre seguridad operativa.pptx` | 484 000 000 B | `data/raw/dji_academy_06_seguridad_operativa.txt` | ✅ extraída (§8 — sin evidencia útil) |
| 07 | `07 Requerimientos básicos de habilidades de enseñanza para instructores.pptx` | 6 200 000 B | `data/raw/dji_academy_07_instructores.txt` | ✅ extraída (§8 — sin evidencia útil) |
| 08 | `08 Mantenimiento y cuidado de los equipos.pptx` | 12 600 000 B | `data/raw/dji_academy_08_mantenimiento.txt` | ✅ extraída (§8 — sin evidencia útil para A9/A10) |
| 09 | `09 Operación practica y proceso de evaluación de drones para la agricultura.pptx` | 5 000 000 B | `data/raw/dji_academy_09_operacion_practica.txt` | ✅ extraída (§8 — sin evidencia útil) |

La presentación **01a** es la fuente técnica principal; la **03** es la más relevante para el DOE.
**La carpeta completa ya está extraída y auditada** (10 decks, ~1 600 líneas de texto).

**Naturaleza de la fuente:** material de formación oficial de DJI (DJI Academy) para
distribuidores. Es **P (público)**, pero de jerarquía distinta a `ag.dji.com/.../specs`:
es documentación comercial/técnica de formación, no ficha de producto. Se registra como
**P (Academy)** y cuando contradice la ficha oficial se anota explícitamente.

---

## 1. Datos nuevos que NO estaban en las fichas maestras

| Dato | Valor | UAV | Línea del extracto | Relevancia |
|---|---|---|---|---|
| Hélice — modelo y medida | **6223**: 62 in de diámetro × 23 in de paso → **1.574 m** | T100 / T70P | 368 | Resuelve el paso de pala, que estaba como **D** |
| Motor — modelo | **155P**; diámetro de motor T70P = T100 | T100 / T70P | 365-366, 386 | Confirma estator 155 mm |
| Empuje de un solo brazo | **82 kg** (T100) | T100 | 87, 374 | Ver §4 (ambiguo) |
| Empuje de un solo eje | **54,2 kg** | T70P | 381 | Ver §4 (ambiguo) |
| ESC — corriente de pico | **370 A** | T100 | 367 | Entrada para bancada |
| **Rotación de hélices del T70P** | Motor 1/3 **CW**, motor 2/4 **CCW** = **opuesta a la de un cuadricóptero tradicional** | T70P | 102, 138 | **Crítico** para el signo de la estela (H3, H4) |
| Rotación T100 | "igual que T40/T50" (no se explicita) | T100 | 130 | Requiere medición |
| Configuración propulsiva | "Hélices duales coaxiales" | T100 | 87, 374 | **Coaxialidad confirmada** (I→P) |
| Ventaja declarada | "campo de viento fuerte" creado por hélices coaxiales duales + 4 boquillas traseras | T100 | 374 | Evidencia cualitativa de downwash (no medible) |
| Atomizador — régimen | disco del motor del atomizador hasta **14 000 rpm** | T100/T70P | 515 | **NO es RPM del rotor**: es del atomizador |
| Atomizador — boquilla niebla opcional | **10–500 µm**; propuesta escrita 50–500 µm; advertir no promover 10 µm | T100 | 515, 533 | Rango D actualizado |
| Disposición 4 boquillas | **cuatro traseras** (no delanteras+traseras) | T100 | 527 | Corrige premisa, alimenta H3 |
| Motivo de la disposición | reduce interferencia con radar LiDAR e Inteligencia Visionaria | T100 | 527 | Justificación de diseño |
| Cobertura envés de hoja | 65 % mejor que T50 | T100 | 533 | Fuera de alcance (canopia) |
| Velocidad de ascenso / descenso | **3 m/s** ascenso; **2–3 m/s** descenso | T100 / T70P | 138 | Datos operativos reales |
| Velocidad de vuelo máxima | "capaz de volar a toda velocidad a **20 m/s**" | T100 | 374 | Límite superior real; el DOE usaba solo 10 m/s |
| T100 peso en vacío | 73 kg (con batería, 2 boquillas) | T100 | 88, 92 | = peso de pulverización 2 boq. |
| T100 peso 4 boquillas / dispersión | 74,9 kg | T100 | 92 | |
| T100 peso elevación | 64,9 kg | T100 | 92 | |
| T100 carga dispersión | 150 L | T100 | 93 | Fuera de alcance |
| T70P peso con DB2160 | 56 kg | T70P | 107 | Confirma ficha |
| T70P carga dispersión | 70 kg (100 L) | T70P | 108 | Fuera de alcance |
| T25P peso / MTOW | 26 kg sin batería; **32,8 kg** con batería; MTOW pulverización **52,8 kg** | T25P | 120-122 | Ver §2 (discrepancia) |
| T25P dimensiones plegado | no incluidas; sí 2650×2700×820/850 | T25P | 125 | Confirma ficha |
| T25P batería | DB800 15 500 mAh (≈6,6 kg) | T25P | 123 | Confirma ficha |

---

## 2. Discrepancias detectadas (a resolver con medición)

| Parámetro | Ficha oficial (`docs/specs/`) | DJI Academy (extracto) | Δ | Acción |
|---|---|---|---|---|
| T25P peso con batería | 33 kg | **32,8 kg** | 0,2 kg | Redondeo; irrelevante |
| T25P MTOW pulverización | 53 kg | **52,8 kg** | 0,2 kg | Redondeo; irrelevante |
| T70P dimensiones desplegadas | **3200 × 3520 × 960 mm** | **3175 × 3490 × 960 mm** | 25 × 30 mm | ⚠ **Contradicción** entre fuentes DJI |
| T100 rotación de hélices | no declarada | "igual que T40/T50" | — | Medir |

*Nota:* la ficha oficial de T25P (`docs/specs/T25P.md` línea 36) hace el sanity check
33 + 20 = 53 kg. Las variantes 32,8/52,8 cierran igual (32,8 + 20 = 52,8 ✓).

---

## 3. Lo que el material NO aporta (sigue siendo D)

- **RPM real del rotor** en hover/aplicación (riesgo R1). El único régimen publicado
  (14 000 rpm) es del **motor del atomizador**, no del rotor. No debe usarse para el rotor.
- **Número de rotores por plataforma.** El T100 dice "hélices duales coaxiales" pero no
  cuantifica pares; el T70P numera motores 1–4 sin decir si cada brazo lleva 1 o 2 rotores.
- **Posición XYZ** de rotores y de atomizadores.
- **Número de palas** por rotor ni perfil/twist de pala.
- **Velocidad de aplicación y altura sobre el cultivo** (el deck da V máx de traslado, no de aplicación).
- **Caudal/presión** de bomba para T25P y T55 (el extracto solo detalla T100/T70P).
- **T55**: el deck no incluye una sección propia del T55 en el texto extraído.
- **Datos de tanque/mezcla**: fuera de alcance (agua pura).

---

## 4. Advertencia sobre los valores de empuje (82 kg / 54,2 kg)

Los valores "empuje de un solo brazo 82 kg" (T100) y "empuje de un solo eje 54,2 kg"
(T70P) son **ambiguos y potencialmente contradictorios entre sí y con la geometría**:

- T100, MTOW 175 kg, 4 brazos: 82 kg/brazo daría 328 kg de empuje total ⇒ relación
  empuje/peso ≈ 1,87. Plausible como empuje máximo estático, pero **no dice si "brazo"
  incluye los 2 rotores coaxiales**.
- T70P, MTOW 126 kg, 4 brazos: 54,2 kg/eje daría 217 kg ⇒ relación ≈ 1,72. Plausible,
  pero si "eje" = brazo coaxial completo, entonces un T100 (motor 155P, hélice 6223
  idéntica) no puede rendir 50 % más por brazo que un T70P con la misma hélice.
- **Conclusión:** registrar como **P (Academy) con ambigüedad explícita**. NO usarlos
  como salto de presión del disco actuador hasta resolverlos en bancada (curva empuje-RPM).

---

## 5. Uso previsto en el proyecto

1. Sustituir en las fichas los campos que este material resuelve: paso de pala (6223),
   coaxialidad del T100, rango de gota 10–500 µm de la boquilla de niebla, velocidades
   de ascenso/descenso, V máx 20 m/s, dirección de rotación del T70P.
2. Corregir la premisa de "4 boquillas delanteras+traseras" → **4 boquillas traseras**.
3. Alimentar el **protocolo de medición** (`geometry/protocolo_geometria.md`): sigue
   faltando lo esencial (RPM rotor, nº rotores, XYZ).
4. Los 106 objetos multimedia del PPTX **no se extrajeron**: pueden contener diagramas
   con cotas de brazos y posiciones de boquillas. Candidatos a inspección visual futura
   (`scripts/extract_pptx_text.py` los lista; se puede añadir un modo de extracción).

---

## 6. Aportes de la presentación 02 — Planificación de Misión

Fuente: `data/raw/dji_academy_02_planificacion_mision.txt` (30 diapositivas).

| Dato | Valor | Relevancia |
|---|---|---|
| **Parámetros de vuelo que define el usuario** | tasa de aplicación · **tamaño de gota** · **velocidad de vuelo** · **altura sobre el cultivo** · **separación de rutas** | 🔴 **Confirmación oficial de la estructura de variables independientes del proyecto** (§9). "Separación de rutas" es el término que DJI usa para el interlineado ⇒ el entregable del proyecto es directamente un parámetro del control remoto Agras |
| Distancia de seguridad a obstáculos | ≥ 2,5 m entre punta de hélice y obstáculo | cota de seguridad para el plan experimental |
| Escenarios de seguimiento de terreno | Plano / Huerto / Colina (<15°) | base de la simplificación "terreno plano" del alcance |

---

## 7. Aportes de la presentación 03 — Configuración de Parámetros de aplicación

Fuente: `data/raw/dji_academy_03_parametros_aplicacion.txt` (8 diapositivas).
**Es la fuente más relevante para la construcción del DOE.**

### 7.1 Descomposición de objetivos operativos (oficial DJI)

| Objetivo | Interlineado / ancho | Velocidad | Altura sobre cultivo | Tamaño de gota | Tasa de aplicación |
|---|---|---|---|---|---|
| Recubrimiento | – | – | – | – | mayor tasa ⇒ mayor recubrimiento |
| **Penetración** | – | **menor V ⇒ mejor** | **menor H ⇒ mejor** | **menor d ⇒ mejor** | mayor tasa ⇒ mejor |
| **Cobertura** | (ancho + V + H) **en combinación** afecta la uniformidad | | | – | – |
| **Eficiencia** | mayor ancho ⇒ mejor eficiencia, pero **peor uniformidad** | mayor V ⇒ mejor | – | – | menor tasa ⇒ mejor |
| Deriva | – | menor V ⇒ menos deriva | menor H ⇒ menos deriva | mayor d ⇒ menos deriva | – |

🔴 **Relevancia directa:** la fila "Cobertura" es, en palabras de DJI, una **interacción
ancho × velocidad × altura** — exactamente la hipótesis **H2** del proyecto. Y la fila
"Eficiencia" plantea el compromiso productividad ↔ uniformidad que sostiene **H7**.
Es evidencia cualitativa de la práctica industrial, **no** una demostración: la
cuantificación sigue siendo el aporte científico del estudio.

### 7.2 Velocidades evaluadas (slide 4)

Se comparan **3 · 5 · 7 · 10 · 13 m/s** todos a **140 µm**. El rango operativo de aplicación
llega por tanto a **13 m/s**, mientras el `doe_master_plan.csv` actual solo cubre 2,01–9,93 m/s.

### 7.3 Prácticas de reducción de deriva (slide 6)

- No pulverizar con viento > **2 m/s** (7,2 km/h). *(Nota: el límite operativo declarado en las
  fichas es nivel 3 = 6 m/s; 2 m/s es la recomendación antideriva, no el límite del aparato.)*
- Velocidad de vuelo **≤ 6 m/s**.
- Tamaño de gota "grueso" o "muy grueso".
- Zona de amortiguamiento **9–20 m**.

### 7.4 ⚠ ADVERTENCIA CRÍTICA: las tablas de parámetros son SOLO de T40/T50

Las cinco tablas de recomendación (slides 7) están etiquetadas **únicamente para T40/T50**:

| Cultivo | Tasa | Gota | Velocidad | Ancho | Altura |
|---|---|---|---|---|---|
| Insecticidas/fungicidas/foliares (T40/T50) | 15–30 L/ha | 150–300 µm | 6–10 m/s | 7,5–9 m | 3–4 m |
| Herbicidas/defoliantes (T40/T50) | 20–30 L/ha | 400–500 µm | 5–6 m/s | 6–7 m | 3–3,5 m |
| Semillas (T40/T50) | – | giro de disco 800–1000 rpm | 6–10 m/s | 4,5–5 m | 3–4 m |
| Fertilizantes (T40/T50) | – | 800–1000 rpm | 6–10 m/s | 6–7 m | 3–4 m |
| Madurantes (T40/T50) | 15–30 L/ha | 200–350 µm | 6–10 m/s | 7–8 m | 3–4 m |

**El material NO da tablas equivalentes para T25P, T55, T70P ni T100.**

Esto es, a la vez, **la confirmación del gap de novedad** y una **restricción metodológica**:
- ✅ Confirma que la práctica industrial está anclada a plataformas anteriores (T40/T50), lo que
  respalda el hueco declarado en `research/RESEARCH_ARCHITECTURE_V1.md` §3.
- ⛔ **PROHIBIDO** usar estas tablas como valores de entrada del DOE para T25P/T55/T70P/T100.
  Sería exactamente la extrapolación entre plataformas que `context.md` §30 prohíbe.
  Solo se admite como **referencia cualitativa** y como **punto de partida de los rangos a medir**.

### 7.5 Contraste útil con las fichas

- Altura sobre el cultivo **3–4 m** para T40/T50 frente a los **4–7 / 4–11 / 5–13 m de ancho
  nominal a 3 m** de las fichas verificadas: coherencia en el orden de magnitud de la altura.
- El **giro del disco de 800–1000 rpm** (esparcidor T40/T50) y los **14 000 rpm del motor del
  atomizador** (T100/T70P) son regímenes de componentes distintos y **ninguno es la RPM del rotor**.

---

## 8. Barrido de los decks 04–09: búsqueda de T55, A9 y A10

**Método:** `scripts/audit_documentary_evidence.py` — busca alias de modelo (identidad) y términos
técnicos (tema) en los 10 decks extraídos, y reporta cada coincidencia con archivo y número de
línea. **El script reporta; no concluye.**

### 8.1 Resultado negativo: el T55 no aparece

**El T55 no está en ninguno de los 10 decks.** Cero coincidencias de identidad, ni siquiera por
alias (`T55`, `Agras 55`, `55 kg/L/pulgadas`). Los decks 04–09 tratan de: sistema de energía y
generador, agroquímicos, seguridad operativa, habilidades de instructor, mantenimiento y operación
práctica. El material formativo está centrado en **T100, T70P, T25P y la generación T40/T50**.

**Consecuencia para GATE 1A del T55:** no hay evidencia documental adicional que explotar en esta
carpeta. El T55 queda **enteramente dependiente de medición física** (o de documentación DJI
específica que no está en esta carpeta).

### 8.2 A9 — origen documental del "8 pares" del T100: LOCALIZADO

La cifra **no es una lectura ambigua**: es un valor de tabla explícito de la ficha oficial.

| Fuente | Archivo | Línea | Contenido |
|---|---|---|---|
| Ficha oficial T100 | `data/raw/T100_ocr.txt` | 56–67 | `Sistema de propulsion - Hélices` … `Dimensiones` `62 pulgadas` … `Cantidad` **`8 pares`** |
| Ficha oficial T55 | `data/raw/T55_ocr.txt` | 60–66 | `Sistema de propulsion - Helice` … `62 pulgadas` … `Cantidad` **`4 pares`** |
| Ficha oficial T70P | `data/raw/T70P_ocr.txt` | 58–68 | `Sistema de propulsion - Hélices` … `62 pulgadas` … `Cantidad` **[vacío]** |

**Lecturas posibles del "8 pares" del T100:**
1. 8 pares coaxiales = **16 hélices** (lectura literal);
2. nomenclatura de "pares" que en realidad cuenta **hélices** ⇒ 8 hélices (4 pares);
3. una **versión o configuración distinta** de la plataforma.

**Lo que dice el material Academy:** 4 brazos, par coaxial por brazo ⇒ **8 hélices**, sin cuantificar
"pares" en texto.

> ⚠ **NO se resuelve aquí.** Queda como conflicto abierto (A9) con ambas fuentes citadas y sus
> líneas exactas, para que la resolución sea por **conteo físico** y no por interpretación.
> Nota de contexto: el fraseo "8 pares" es una traducción (el original probablemente usa 对,
> "par"). Una ambigüedad de traducción es una hipótesis más, no una conclusión.

**Dato nuevo colateral:** el campo `Cantidad` del **T70P está vacío en la captura**. Es un hueco
recuperable volviendo a capturar la página oficial, no una incógnita de medición. **Vía barata
identificada.**

### 8.3 A10 — accionamiento del par coaxial: SIGUE SIN RESOLVERSE

Barrido específico de `ESC`, `motor`, `coaxial`, `brazo` en los decks 04–09:
- Deck 08 (mantenimiento) menciona la categoría **"Motores y ESC"** en una lista de tareas de
  limpieza, **sin contar unidades ni describir el accionamiento**.
- Deck 04 (energía) trata del **generador** (aceite de motor del generador), no de la propulsión.
- Ningún deck declara si el par coaxial es solidario o de dos motores independientes.

**A10 permanece abierto.** No hay atajo documental: exige inspección física o manual de servicio.


