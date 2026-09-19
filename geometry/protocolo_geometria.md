# Protocolo de geometría y medición — GATE 1A / GATE 1B

**Objetivo:** producir una geometría **físicamente validada**, no solo paramétrica y trazable.
Una geometría con procedencia correcta sigue siendo una hipótesis si no está medida
(context.md §7, §43, §51; PROJECT_MASTER_PLAN §4.2).

**Estado (2026-09-14):** `docs/specs/*.md` agota la información pública (P) y el material
DJI Academy aporta evidencia documental (**S**, ver §2). Lo que falta es **medición (M)**.

---

## 0. GATE 1 se divide en dos gates independientes

La versión anterior de este protocolo juntaba la topología geométrica con el estado
operativo del rotor. Son problemas con dependencias distintas, y acoplarlos bloquea trabajo
que sí se puede hacer. Se separan:

### GATE 1A — geometry validated
**Cierra cuando:** las 4 plataformas tienen topología, centros y ejes de cada disco de rotor,
configuración coaxial, **separación axial del par**, geometría de hélice y posición y
orientación de los atomizadores **trazables y sin `D` críticos**.

**Al cerrar 1A:** congelar `geometry-v1`, calcular hash de los manifiestos y evitar que
la geometría cambie en silencio durante el DOE.

**Bloquea:** mallado de estudio, génesis de la geometría CFD y definición del dominio.
**NO bloquea:** estructura del DOE, arquitectura de datos, selección de modelo de turbulencia,
comparación de estrategias de mallado, ni la especificación de los casos.

### GATE 1B — rotor operating state
**Cierra cuando** existe una relación defendible entre **RPM ↔ masa total ↔ empuje requerido ↔
configuración de rotor ↔ condición atmosférica** (§6.1).

**Bloquea:** CFD **cuantitativo** de alta fidelidad y toda afirmación sobre magnitud de downwash.
**NO bloquea:** validar topología, dominios, refinamientos ni comparaciones relativas entre
plataformas a igualdad de hipótesis de empuje.

### GATE CFD-0 — la suite es ejecutable (nuevo, 2026-09-14)

**El problema que resuelve:** haber generado 128 casos y verificado que su estructura de ficheros
está completa **no significa que sean físicamente ejecutables**. `actuationDiskSource`, las
`cellZone`, los signos y direcciones del empuje, las condiciones de contorno de traslación y los
`function objects` siguen siendo **hipótesis de implementación** hasta que un caso corra de
principio a fin. Decir "128/128 verificados" sin haber ejecutado ninguno es una afirmación que no
se sostiene.

**Alcance: UN SOLO caso, T25P nominal.** No se escala a los 128 antes de cerrar este gate.

**Secuencia obligatoria:**

```
blockMesh  →  checkMesh  →  topoSet  →  solver ~100-500 iteraciones
           →  confirmar actuationDiskSource  →  function objects  →  postprocess
```

**Criterios de cierre (todos verificables, ninguno interpretable):**

- [ ] `blockMesh` termina sin errores y `checkMesh` reporta **0 errores** de calidad
      (se reportan también `maxNonOrtho` y `maxSkewness` aunque pasen).
- [ ] `topoSet` crea **una `cellZone` por rotor** y el número coincide con los rotores modelados.
- [ ] El solver corre **≥100 iteraciones** sin divergir; se reporta la evolución de residuales.
- [ ] **`actuationDiskSource` se confirma efectivamente aplicado:** evidencia de que el disco
      introduce el empuje previsto. Criterio cuantitativo: el salto de presión/velocidad en la
      zona del disco es del orden del esperado por momentum theory
      (`v_ind = sqrt(T/(2·rho·A_disk))`), no cero ni un orden de magnitud fuera.
- [ ] **Signo del empuje verificado:** el downwash va **hacia abajo** (`Uz < 0` bajo el disco).
      Un signo invertido es el error más probable y más silencioso de toda la configuración.
- [ ] Los **`function objects` producen ficheros**: el plano receptor, las líneas de downwash y
      las fuerzas existen en `postProcessing/` y tienen contenido no vacío.
- [ ] `postprocess_case.py` **lee** esas salidas y escribe la fila en `cfd_airflow`.
- [ ] Se reporta el **coste** (núcleos, tiempo de pared por iteración) para dimensionar la suite.

**Bloquea:** escalar a los 128 casos, y toda la capa Lagrangiana de deposición.
**NO bloquea:** la capa analítica, el diseño del DOE ni la especificación Lagrangiana.

> **Estado actual: CFD-0 NO se ha podido ejecutar** porque este entorno **no tiene OpenFOAM**
> (`blockMesh`, `checkMesh`, `simpleFoam`, `topoSet` no están en el PATH) y **WSL está bloqueado**.
> Por tanto, los 128 casos son **casos generados, no casos CFD validados**. Así deben citarse.

### Qué falta para que cada gate cierre

| Gate | Qué lo cierra | Estado |
|---|---|---|
| **1A** | medición física (bloques A/B) | ⬜ 0 filas |
| **1B** | RPM real + reparto de empuje | ⬜ |
| **CFD-0** | un caso T25P ejecutado de punta a punta | ⬜ sin OpenFOAM |
| **CFD-suite** | 128 casos ejecutados y convergidos | ⬜ requiere CFD-0 |
| **Lagrangiano** | deposición D(x,y) por conteo de impactos | ⬜ requiere CFD-suite |

> Regla de honestidad: todo resultado obtenido con 1B abierto debe declararse como
> **exploratorio** y no puede entrar al dataset ni al paper como dato de la plataforma real.

---

## 1. Jerarquía de fuentes

| Nivel | Fuente | Etiqueta | ¿Vale para CFD de estudio? |
|---|---|---|---|
| 1 | Ficha oficial `ag.dji.com/es/<uav>/specs` | **P** | Sí, citando fuente y fecha |
| 2 | DJI Academy (formación de distribuidor) | **P-A** | Sí, anotando la fuente |
| 3 | **Evidencia documental visual** (imagen oficial con pie inequívoco) | **S** | Solo para hechos **discretos**: nº de brazos, coaxialidad, nº de palas, posición relativa. **Nunca para dimensiones.** |
| 4 | **Aportado por el propietario** (comunicación directa) | **O** | **Solo como hipótesis declarada.** Nunca se cita como si fuera de DJI. |
| 5 | Medición propia protocolizada | **M** | Sí — único origen válido para dimensiones de estudio |
| 6 | Inferencia con razonamiento explícito | **I** | Solo como hipótesis de trabajo declarada |
| 7 | Estimación de planificación | **E** | Solo para dimensionar el problema |
| 8 | Desconocido | **D** | **Se deja `null`.** Se usa como parámetro de sensibilidad, no se rellena. |

> **Por qué existe `O`:** el propietario de las aeronaves es la fuente más cercana al objeto físico,
> así que su información es mejor que una inferencia. Pero **no es `M`**: no hay instrumento, ni
> incertidumbre, ni repetición. Confundir `O` con `M` sería el mismo error que confundir `I` con `P`.
> Y citar un dato `O` como si fuera de DJI es una **cita falsa**, no una idealización.
> El marco completo —con la tabla de hipótesis para el manuscrito— está en
> `geometry/presupuesto_hipotesis.md`.

**Regla dura:** de una fotografía **sin escala ni cota inequívoca no se derivan dimensiones**.
Se registran hechos discretos y cualitativos, con cita del archivo y la diapositiva para que
un revisor lo verifique.

---

## 2. Evidencia visual disponible (categoría S)

Extraída con `scripts/extract_pptx_media.py` → `data/raw/media/`, catalogada en
`data/processed/media_inventory.csv` (178 objetos; hojas de contactos en `figures/contact_sheets/`).

| Plataforma | Slide | Observado | Consecuencia |
|---|---|---|---|
| **T25P** | 12 | 4 brazos, **sin par coaxial** → 4 rotores. Panel de detalles: motor rotulado **10028/59KV** (coincide con estator 100×28 y KV 59 oficiales); **2 palas**; atomizador montado **por debajo** del plano del brazo | `rotor_count` sube de `I` a `S` |
| **T70P** | 11 | **Par coaxial en cada uno de los 4 brazos** → 8 rotores, con separación axial visible. Detalle de rotor: **2 palas** y abrazadera oscilante | `rotor_count` y `coaxial` suben de `I` a `S`; **falta la separación axial (D)** |
| **T100** | 10, 45 | **Par coaxial por brazo** → 8 rotores; atomizadores colgando **por debajo y por fuera, en la parte trasera**; varillas de pulverización extendidas hacia atrás | confirma "4 boquillas traseras" |
| **T55** | — | **NO LOCALIZADO** en el deck 01 | el T55 sigue sin evidencia visual: buscar en otro deck o medir |

### 2.1 ⚠ Conflicto abierto en el T100 (resolver antes del CFD)

- **Specs DJI:** "Cantidad: 8 pares" ⇒ **16 hélices**.
- **DJI Academy (texto + imagen):** "hélices duales coaxiales", 4 brazos con un par cada uno ⇒ **8 hélices**.

Ambas son fuentes oficiales y **no concuerdan**. Consecuencias si se elige mal:
área de disco total al doble, y carga de disco y velocidad inducida de hover desviadas ~√2.
**Medir y resolver antes de mallar.** Registrado en
`geometry/manifests/t100_geometry_manifest.json`.

### 2.2 Diagrama rotulado de la slide 09 — resuelto por XML, no por render

**Hipótesis inicial (incorrecta):** el `p09_0a7ec705d2dc.emf` de 16 MB parecía un diagrama
vectorial escalable en el que leer posiciones relativas.

**Verificación:** con `scripts/convert_vector_media.py` (Pillow rasteriza WMF/EMF por GDI en
Windows; Inkscape/ImageMagick no están disponibles y `winget` está bloqueado) se renderizó a
5174 × 2558 px. El resultado revela que **el objeto es un mapa de bits envuelto en un metafile**:
no hay trazados vectoriales que escalar. La premisa "vectorial ⇒ escalable" era falsa aquí.

**Los rótulos no están en el gráfico.** Son **cuadros de texto de PowerPoint superpuestos**.
Por tanto la vía correcta no es renderizar el metafile, sino leer el XML de la diapositiva:
cada forma trae su transformación en EMU (914 400 EMU = 1 pulgada), que es un **dato exacto**
del archivo y no una estimación de píxeles.

`scripts/extract_pptx_shape_geometry.py` → `data/processed/shape_geometry/` (285 formas;
posiciones normalizadas al lienzo, y extremos de los 17 conectores de la slide 09).

**Componentes señalados en la slide 09** (posición normalizada del extremo de la línea guía):

| Rótulo | Posición relativa |
|---|---|
| Hélice | (0,088 , 0,265) |
| Motor | (0,152 , 0,394) |
| Control electrónico de velocidad (ESC) | (0,152 , 0,394) |
| Antena RTK | (0,426 , 0,266) |
| Cámara FPV | (0,577 , 0,223) |
| Radar hacia adelante | (0,591 , 0,166) |
| Radar LiDAR | (0,470 , 0,339) |
| Antena de transmisión de vídeo | (0,184 , 0,401) |
| Boquilla centrífuga | (0,110 , 0,612) |
| Panel de pulverización | (0,110 , 0,612) |
| Bomba de impulsor magnético | (0,110 , 0,612) |
| Radar descendente | (0,397 , 0,602) |
| Depósito de líquidos | (0,776 , 0,596) |
| Diseño de pistola doble trasera | (0,776 , 0,596) |
| Sistema de pulverización de carga útil | (0,721 , 0,709) |
| Luces LED y auxiliares inferiores | (0,447 , 0,652) |

> ⚠ **Limitación declarada.** El mapeo se obtuvo por proximidad entre rótulo y extremo de línea
> guía, y **es ambiguo**: "Motor" y "ESC" colapsan en el mismo punto (van juntos en el brazo), y
> "Boquilla centrífuga", "Panel de pulverización" y "Bomba" también. Con 17 conectores frente a
> 22 rótulos no hay correspondencia uno a uno. **Los pares rótulo–componente no deben citarse
> como hechos**; lo que sí es dato exacto son las **posiciones de las formas** en el CSV/JSON.

**Utilidad real:** da la **topología del conjunto** (qué componentes existen y en qué zona de la
aeronave caen) y sirve para diseñar mejor la medición — por ejemplo, confirma que el atomizador y
la bomba están en la zona baja del brazo, por debajo del plano de rotor. **No da milímetros.**

### 2.3 Multimedia pendiente de explotar

- Quedan 18 objetos vectoriales sin convertir (13 son `.wdp` = Windows Media Photo, que Pillow no
  lee; 5 son EMF pequeños que GDI no pudo renderizar). Ninguno es crítico: los grandes ya se
  procesaron.
- Quedan los decks **04–09** por extraer (energía, agroquímicos, seguridad, instructivos,
  mantenimiento, operación práctica). **Pueden contener material del T55**, que es la plataforma
  con menos evidencia.

---

## 3. Modelo de datos a medir: sistema propulsivo

Registrar **número de rotores** no basta para CFD. Cada disco de rotor debe describirse de
forma inequívoca. Una fila por disco:

| Campo | Descripción | Unidad | Criticidad |
|---|---|---|---|
| `rotor_id` | identificador único | — | — |
| `arm_id` | brazo al que pertenece | — | — |
| `posicion` | **centro XYZ del disco**, en sistema de referencia declarado | m | **crítica** |
| `eje_normal` | **vector normal del disco** (dirección de empuje), normalizado | — | **crítica** |
| `diametro` | diámetro de barrido | m | **crítica** |
| `sentido_giro` | CW / CCW | — | crítica |
| `rol_coaxial` | superior / inferior / único | — | crítica si coaxial |
| `separacion_axial_par` | distancia entre planos de rotor del par coaxial | m | **crítica si coaxial** |
| `n_palas` | número de palas | — | alta |
| `geometria_pala` | cuerda raíz/punta, twist, perfil, masa | m / ° / — / kg | alta |
| `rpm_nominal` | ver GATE 1B | rpm | 1B |

**Sistema de referencia obligatorio:** declarar origen y ejes una sola vez para todo el proyecto
(se propone: origen en el CG en configuración de pulverización con tanque al 50 %; X hacia
adelante, Y a la izquierda, Z hacia arriba). Sin esto, las coordenadas de rotores y atomizadores
no son comparables entre campañas ni entre plataformas.

---

## 4. Modelo de datos a medir: atomizadores

Para **H3** la posición XYZ es insuficiente. Una fila por atomizador:

| Campo | Descripción | Unidad | Criticidad |
|---|---|---|---|
| `atomizer_id` | identificador | — | — |
| `configuracion` | 2 o 4 atomizadores | — | crítica |
| `posicion` | **centro XYZ** (referencia: centro del disco de atomización) | m | **crítica** |
| `vector_descarga` | **orientación** (eje del cono de pulverización) | — | **crítica** |
| `punto_efectivo_emision` | punto de emisión efectivo si puede determinarse | m | alta |
| `altura_rel_plano_rotor` | **Δz respecto al plano de rotor más próximo** | m | **crítica para H3** |
| `rotor_mas_cercano` | a qué rotor(es) cae su estela | — | **crítica para H3** |
| `soporte` | brazo / barra / bastidor; cota al eje del brazo | — | alta |
| `caudal_por_atomizador` | a cada ajuste de bomba | L/min | alta |
| `presion` | presión de trabajo | bar | alta |
| `espectro_gota` | D10/D50/D90 por ajuste | µm | alta |

**Nota T100:** por ser **4 boquillas traseras sobre barra**, hay que registrar también la
geometría de la barra (longitud desplegada 1930 mm, cota al bastidor) y en qué medida las
boquillas traseras caen dentro o fuera de las estelas. Es el caso donde la interacción
gota–estela más puede diferir respecto de T25P/T55/T70P.

---

## 5. Plantilla de captura y esquema del CSV

No se guarda solo `valor`. La trazabilidad experimental se captura **en el momento**, porque
reconstruirla después para la publicación es mucho más caro y más frágil.

### 5.1 Campos obligatorios por fila

| Campo | Descripción | Ejemplo |
|---|---|---|
| `value` | valor numérico o categórico | `0.697` |
| `unit` | unidad explícita; `-` si es adimensional | `m` |
| `uncertainty` | incertidumbre con su tipo y cobertura | `±0.005 (k=2)` |
| `method` | cómo se obtuvo | `cinta_desde_centro_buje` |
| `instrument` | instrumento concreto, marca/modelo si aplica | `cinta Stanley 5 m, clase II` |
| `timestamp` | fecha y hora ISO 8601 | `2026-09-20T10:35:00-03:00` |
| `operator` | quién midió (iniciales o id) | `D.M.` |
| `source_class` | P / P-A / S / M / I / E / D | `M` |
| `reference_frame` | sistema de referencia de la medición | `CG_tank50` |
| `notes` | observaciones, desviaciones, dudas | `dron sobre caballete` |

Campos adicionales de contexto: `uav`, `block`, `element_id` (ej. `R1_upper`), `parameter`,
`configuracion` (2/4 atomizadores, carga de tanque), `repetitions`, `raw_file` (foto o CSV fuente).

### 5.2 Sistema de referencia (`reference_frame`)

**Se declara una sola vez para todo el proyecto** y se referencia por nombre en cada fila.
Propuesta:

```
origen  = CG en configuración de pulverización con tanque al 50 %
X       = hacia adelante (dirección de vuelo)
Y       = hacia la izquierda
Z       = hacia arriba
```

Sin esto, las coordenadas de rotores y atomizadores no son comparables entre campañas,
entre plataformas ni contra el CAD.

### 5.3 Ejemplo de filas

```csv
uav,block,element_id,parameter,value,unit,uncertainty,method,instrument,timestamp,operator,source_class,reference_frame,notes
T25P,rotor,R1,posicion_x,0.6965,m,±0.005 (k=2),cinta_desde_centro_buje,"cinta Stanley 5 m, clase II",2026-09-20T10:35:00-03:00,D.M.,M,CG_tank50,dron sobre caballete
T25P,rotor,R1,n_palas,2,-,exacto,conteo_visual,-,2026-09-20T10:36:00-03:00,D.M.,M,CG_tank50,confirma evidencia S de la slide 12
T70P,rotor,R1_upper,rpm_hover,2680,rpm,±10 %,tacometro_optico,"tacometro optico X, 2 canales",2026-09-21T09:10:00-03:00,D.M.,M,CG_tank50,medido junto con R1_lower
T100,rotor,par_A,separacion_axial_par,0.215,m,±0.005 (k=2),cinta_entre_planos,-,2026-09-22T11:00:00-03:00,D.M.,M,CG_tank50,parametro del modelo de empuje
```

### 5.4 Reglas de captura

- **Bloque `rotor`** → una fila por campo y por **disco** (§3), incluidos `R1_upper` / `R1_lower`.
- **Bloque `atomizer`** → una fila por campo y por atomizador (§4).
- **Bloques `masa`**, **`bancada`** → según §6.
- Guardar en `data/raw/mediciones_geometria.csv`. Si una medición contradice la ficha oficial,
  **gana la medición** y se anota la discrepancia en `notes`.
- Ninguna fila con `source_class = M` sin `uncertainty` y `instrument`.

---

## 6. Lista de medición priorizada

### Bloque A — sistema propulsivo (prioridad 1; bloquea GATE 1A)

| # | Medición | Método | Precisión objetivo |
|---|---|---|---|
| A1 | Nº real de brazos y de rotores; pares coaxiales | inspección + foto cenital | exacto |
| A2 | **Centro XYZ de cada disco** (todos los rotores) | cinta/calibre desde referencias del cuerpo; plomada al suelo para XY | ±5 mm |
| A3 | **Vector normal del disco** de cada rotor | nivel digital / foto ortogonal con referencia | ±1° |
| A4 | Diámetro de barrido real | cinta punta a punta | ±5 mm |
| A5 | Sentido de giro por rotor | manual o arranque controlado. **T70P: 1/3 CW, 2/4 CCW (P-A)** | binario |
| A6 | **Separación axial del par coaxial** | cinta entre planos de rotor | ±5 mm |
| A7 | Nº de palas (**S: 2**) y geometría de pala (cuerda raíz/punta, twist, perfil, masa) | medición + reconstrucción CAD | ±2 mm |
| A8 | **Separación entre ejes** adyacentes y opuestos, en X y en Y | cinta entre centros de buje | ±5 mm |
| A9 | Resolver el **conflicto 8 vs 16 rotores del T100** (§2.1) | conteo directo | exacto |

### Bloque B — atomizadores (prioridad 1; bloquea H3)

| # | Medición | Método |
|---|---|---|
| B1 | Nº real por configuración (2 y 4) | inspección |
| B2 | **Centro XYZ de cada atomizador**, en config. 2 y 4 | cinta desde referencias del cuerpo |
| B3 | **Vector de descarga** (orientación del cono) | foto ortogonal con referencia angular |
| B4 | **Δz al plano de rotor más próximo** y rotor(es) cuya estela recibe | derivado de A2/A6 + B2 |
| B5 | Punto efectivo de emisión, si es determinable | foto macro / ensayo de patrón en banco |
| B6 | Geometría de soporte (brazo / barra LS100), cota al eje | cinta |
| B7 | Confirmar disposición **trasera** (S: 4 boquillas traseras en T100) | inspección |

### Bloque C — masas (prioridad 2)

| # | Medición | Método |
|---|---|---|
| C1 | Masa en vacío sin batería | báscula |
| C2 | Masa de cada batería (DB800/DB1050/DB1580/DB2160/DB2212) | báscula |
| C3 | Masa total a carga 100/75/50/25/0 % | báscula + agua medida |
| C4 | Restricción de configuración: **T70P a 70 L exige DB2160** (52+70 = 122 kg > MTOW 102 con DB1580) | cálculo + báscula |
| C5 | Posición del CG en cada estado de carga | punto de equilibrio / 4 células de carga |

### Bloque D — pulverización y propulsión (prioridad 2-3; bancada)

| # | Medición | Método |
|---|---|---|
| D1 | Caudal por atomizador a cada ajuste | caudalímetro / báscula + cronómetro |
| D2 | Presión de pulverización | manómetro |
| D3 | **Espectro real** (D10/D50/D90) | PDI/Sympatec, o hidrosensibles como ordinal |
| D4 | RPM del motor del **atomizador** (P-A: hasta 14 000 rpm) y su efecto en el espectro | tacómetro óptico |
| D5 | Curva **empuje–RPM–torque–corriente por rotor** | bancada (ver §6.2) |

### Bloque A-bis — par coaxial (prioridad 1 para T55/T70P/T100)

| # | Medición | Método |
|---|---|---|
| A10 | **Accionamiento del par**: nº de motores y de ESC por brazo; ¿par solidario o independiente? | inspección, despiece o manual de servicio |
| A11 | **RPM de cada rotor del par en hover real**, simultáneamente (2 canales) | tacómetro óptico doble / cámara de alta velocidad |
| A6 | **Separación axial del par** (ya en bloque A): es **parámetro del modelo de empuje**, no una cota decorativa | cinta entre planos de rotor |

> Ver `geometry/coaxial_thrust_split.md`: el reparto de empuje del par **no se asume `mg/N`**.

---

## 6.1 GATE 1B — estado operativo del rotor y arquitectura CFD

### 6.1.1 Arquitectura adoptada: C → B para el dataset, A para sensibilidad

Decisión (2026-09-14). **C y B no son alternativas excluyentes: se combinan.**

```
C  →  Σ_i T_i + W ≈ 0              restricción física global (equilibrio de fuerzas)
C  →  reparto T_i entre rotores     a partir de masa, CG y actitud medidos
B  →  materializa T_i en cada disco del solver (actuator disk)
A  →  casos selectos: ¿reproduce el disco la estructura de estela que ven los atomizadores?
```

| Nivel | Método | Papel | Papel |
|---|---|---|---|
| **Principal (dataset)** | **Actuator disk + empuje prescrito (B)**, condición física por masa/CG/actitud (**C**) | Niveles 1–3 del plan | No necesita geometría de pala |
| **Secundario (sensibilidad)** | **RPM prescrita (A)**: MRF / sliding mesh / ALM | Casos selectos de alta fidelidad | Exige RPM real y geometría de pala fiable |

**Para qué sirve el modelo secundario:** para cuantificar si la simplificación por disco reproduce
la **estructura de estela relevante para los atomizadores** — que es la pregunta que importa para
**H3**, no la fidelidad aerodinámica en abstracto.

> **El reparto `T_i` NO se toma como `mg/N` como verdad experimental.**
> - **T25P (no coaxial):** `T_i ≈ mg/N` es aceptable como primera aproximación, y **aun así** se
>   contrasta con el CG medido (C5).
> - **T55 / T70P / T100 (coaxiales):** reparto **asimétrico**, determinado por `C_T`, `C_Q` y el
>   factor de interferencia. Ver `geometry/coaxial_thrust_split.md`. Si la campaña demuestra que el
>   reparto es prácticamente simétrico, se documenta como resultado y se justifica la simplificación
>   (§54). **No se asume.**

### 6.1.2 Cómo medir RPM y empuje (en este orden)

**No empezar por la bancada.** El objetivo es la RPM **en condición real de hover/carga
representativa**: una RPM de motor descargado o inferida del KV es prácticamente inútil para
el modelo aerodinámico (context.md §42).

1. **RPM en hover real**, con masa representativa: tacómetro óptico o cámara de alta velocidad
   contando palas. Método directo y no invasivo. **En coaxiales, medir los dos rotores del par a
   la vez** (A11).
2. **Telemetría autorizada** (requiere permiso escrito, §31) como contraste.
3. **Bancada de empuje**: curva empuje–RPM–torque–corriente. Necesaria para las estrategias B y C
   y para resolver la ambigüedad de los valores publicados (**82 kg/brazo** en T100 y
   **54,2 kg/eje** en T70P: no se sabe si son por rotor o por par coaxial).
4. **Estimación inversa** (empuje = peso + momentum theory): solo como contraste.

### 6.1.3 Relación a construir en 1B

```
RPM  ↔  masa total  ↔  empuje requerido  ↔  configuración de rotor  ↔  condición atmosférica
```

Cada corrida con su incertidumbre. Objetivo declarado: **±10 %**.

---

## 7. Relación geométrica candidata (prueba de consistencia, NO identidad)

Se observó que, para planta cuadrada, `span = D_axis/√2 + diámetro de rotor` reproduce el sobre
desplegado en dos plataformas y no en las otras dos:

| UAV | span predicho | ancho oficial | error |
|---|---|---|---|
| T25P | 2663 mm | 2650 mm | **+0,49 %** |
| T100 | 3222 mm | 3220 mm | **+0,05 %** |
| T55 | 3283 mm | 3190 mm | +2,90 % |
| T70P | 3299 mm | 3175 mm | +3,92 % |

**Es una relación geométrica candidata / prueba de consistencia. NO es una identidad geométrica
general ni una relación descubierta.** Con 4 plataformas, 2 coincidencias excelentes y 2
desviaciones relevantes, la evidencia no alcanza para elevarla a ley. Un 2,9–3,9 % es demasiado
grande para tratarlo como redondeo, pero **tampoco demuestra que la especificación esté mal**.

### 7.1 Hipótesis alternativas que romperían la relación (a contrastar con A2/A8)

1. Brazos no perfectamente diagonales (planta no cuadrada, asimétrica en X vs Y).
2. Discos a distinta posición longitudinal (un brazo desplazado hacia delante o atrás).
3. Definición distinta de "dimensión desplegada" por DJI según plataforma (con/sin guardas,
   con/sin sensores, con/sin barra de pulverización desplegada).
4. "Distancia diagonal entre ejes" podría referirse a la **proyección en planta** de los ejes y
   no a la distancia 3D, si los motores van inclinados.
5. Hélices o guardas que sobrepasan el disco de barrido nominal.

**Resolución:** las mediciones **A2** y **A8** de T55 y T70P discriminan entre estas hipótesis.
Si explican la desviación, la relación pasa a ser defendible; si no, se descarta y se documenta
como resultado negativo (§54).

---

## 8. Criterios de cierre

### GATE 1A — geometry validated, **se cierra POR PLATAFORMA**

Un conflicto en una plataforma **no debe bloquear a las demás**. Cada UAV se cierra de forma
independiente y se congela su propia `geometry-v1`.

**Criterios comunes (aplican a cada plataforma que se cierre):**

- [ ] A1, A2, A3, A4, A5, A6, A8 resueltos con `M`, cada uno con `uncertainty` e `instrument`.
- [ ] A7 (palas y geometría de pala) resuelto con `M` — o aceptado explícitamente como limitación
      si se va por la arquitectura principal C→B (actuator disk), que no necesita geometría de pala.
- [ ] B1, B2, B3, B4 resueltos con `M` (posición, orientación y Δz de atomizadores).
- [ ] C1, C2, C3 resueltos con `M`.
- [ ] Sistema de referencia declarado (§5.2) y aplicado a **todas** las filas.
- [ ] Manifiesto sin `D` críticos en los bloques A/B.
- [ ] `geometry-v1/<uav>/` creado, inmutable y verificado por hash (§8.2).

**Bloqueos específicos por plataforma:**

| Plataforma | Estado 1A | Bloqueo específico |
|---|---|---|
| **T25P** | candidato a cerrar primero | ninguno detectado: no coaxial, evidencia `S` de 4 rotores y 2 palas. **Es el candidato natural para el caso base.** |
| **T55** | bloqueado | sin evidencia visual (`S`); requiere medición completa o localizar documentación propia |
| **T70P** | bloqueado | separación axial del par (A6) + reparto de empuje del coaxial + discrepancia dimensional |
| **T100** | **bloqueado hasta resolver A9** | **conflicto 8 vs 16 rotores sin cerrar** — cambia el modelo físico completo |

- [ ] **A9 cerrado:** determinar si "8 pares" se refiere a pares coaxiales, a otra nomenclatura del
      sistema propulsivo, o si una de las fuentes describe otra configuración o versión.
- [ ] Registrado el motivo de la discrepancia, no solo el valor elegido.

### GATE 1B — rotor operating state

- [ ] Arquitectura CFD (§6.1.1) decidida y documentada: **C→B principal, A secundaria**.
- [ ] RPM en hover real medida con masa representativa, con incertidumbre.
- [ ] **A10 resuelto:** accionamiento del par coaxial (solidario o independiente).
- [ ] **A11 resuelto:** RPM de ambos rotores del par medidas simultáneamente.
- [ ] Curva empuje–RPM–torque–corriente **por rotor** (D5a/D5b) y del par coaxial (D5c).
- [ ] **Reparto de empuje superior/inferior** determinado y contrastado
      (`geometry/coaxial_thrust_split.md`). `mg/N` **no** se usa como verdad experimental.
- [ ] Relación RPM ↔ masa ↔ empuje ↔ configuración ↔ atmósfera documentada.
- [ ] Reparto coherente con el CG medido (C5).

**Mientras 1B esté abierto:** el CFD es exploratorio y se etiqueta como tal. Ningún resultado de
esa fase entra al dataset ni al paper como dato de la plataforma real.

### 8.2 Congelación inmutable de geometría

Al cerrar 1A para una plataforma se crea `geometry-v1/<uav>/` con:

```
geometry-v1/<uav>/
    manifest.json        manifiesto cerrado (sin D críticos)
    model.stl            geometría de estudio
    SOURCES.md           fuentes, clasificación e incertidumbre de cada cota
    SHA256SUMS           hashes de los tres archivos anteriores
    README.md            fecha de cierre, quién lo cerró, alcance y limitaciones
```

Generado y verificado por `scripts/freeze_geometry_v1.py`. Regla: **una vez creado, el
directorio no se modifica**; cualquier cambio produce `geometry-v2/<uav>/` y obliga a
re-ejecutar los casos que dependían de v1.

---

## 9. Artefactos

| Artefacto | Generado por | Estado |
|---|---|---|
| `geometry/manifests/<uav>_geometry_manifest.json` | `scripts/build_geometry_manifests.py` + `scripts/annotate_manifests_with_media_evidence.py` | ✅ procedencia por campo + evidencia visual `S` |
| `data/processed/geometry_master.csv` | `scripts/build_geometry_manifests.py` | ✅ |
| `geometry/models/<uav>_control.stl` + `.meta.json` | `scripts/generate_control_geometry_v2.py` | ✅ geometría de control (no CAD fiel) |
| `data/raw/media/`, `data/processed/media_inventory.csv`, `figures/contact_sheets/` | `scripts/extract_pptx_media.py` | ✅ 178 objetos catalogados |
| `data/raw/media_converted/` | `scripts/convert_vector_media.py` (Pillow/GDI) | ✅ render a alta resolución; los `.wdp` no son legibles |
| `data/processed/shape_geometry/` | `scripts/extract_pptx_shape_geometry.py` | ✅ 285 formas + conectores en EMU (clase `S`) |
| `geometry/coaxial_thrust_split.md` | análisis + plan de medición del par coaxial | ✅ abierto, con derivación |
| `data/raw/mediciones_geometria.csv` | campaña de campo (bloques A–D, §5) | ⬜ **cuello de botella** |
| `geometry/campana_T25P.md` | `scripts/prepare_t25p_campaign.py` | ✅ **dos jornadas con parada obligatoria** |
| `scripts/audit_measurement_csv.py` | QA del CSV: trazabilidad, repetibilidad, residuos de simetría, cobertura, no-circularidad | ✅ |
| `scripts/selftest_measurement_qa.py` | autotest de la QA: inyecta 8 problemas conocidos y verifica que los detecta | ✅ |
| `geometry-v1/<uav>/` | `scripts/freeze_geometry_v1.py` tras cerrar 1A | ⬜ |
| `data/raw/dji_academy_01_FUENTE.md` | registro de fuentes P-A y S | ✅ |
| `evidence/CONFLICTS.md` | registro único de conflictos con evidencia citada | ✅ |
| `data/raw/specs_captures/` | capturas forenses de fichas oficiales con sha256 | ✅ |

---

## 10. Campaña en dos jornadas (aplicable a T25P y, tras el piloto, a las demás)

El piloto **no mide todo de una vez**: un error metodológico en la metrología contaminaría la
campaña completa. Se parte en dos bloques con **parada obligatoria** entre ellos.

| | Bloque 1 — Metrología estática | Bloque 2 — Estado operativo |
|---|---|---|
| UAV | **apagado** | energizado / en hover |
| Mide | sistema de referencia, rotores, atomizadores, cotas | masas reales, CG, ambiente, RPM |
| Cierra | **GATE 1A** | **GATE 1B** |
| Salida | `block=rotor\|atomizer\|geometry` | `block=mass\|operation` |

**Parada obligatoria:** procesar el bloque 1 con `scripts/audit_measurement_csv.py` **antes de
volar**. Solo si pasa el post-mortem se ejecuta el bloque 2.

### 10.1 Convención de numeración de rotores (interna, no de DJI)

**No se usa numeración de DJI**: no está demostrada. Se adopta una **convención geométrica
interna** — vista desde arriba, `+X` adelante, `+Y` izquierda, `+Z` arriba:

| id | `position_role` | posición |
|---|---|---|
| `R1` | `FL` | delantero izquierdo |
| `R2` | `RL` | trasero izquierdo |
| `R3` | `RR` | trasero derecho |
| `R4` | `FR` | delantero derecho |

`R1…R4` son **identificadores**; `FL/RL/RR/FR` contienen la **semántica geométrica** y van en la
columna `position_role` (obligatoria en filas de rotor). Así, si un manual DJI numera los motores
de otra forma, **no hay que reinterpretar mediciones antiguas**.

La QA **deriva los pares diametralmente opuestos de `position_role`** (`FL↔RR`, `FR↔RL`), no de una
lista fija de identificadores.

**Evidencia fotográfica obligatoria:** foto cenital con las etiquetas físicas `R1`–`R4` visibles y
una flecha `+X`, asociada al `reference_frame`. Es lo que impide discutir dentro de meses qué
significaba exactamente "R1".

### 10.2 Contraste de oposición: vector completo, no ejes sueltos

Comprobar solo `x₁+x₃ ≈ 0` **no demuestra oposición**. Para cada pareja se comprueba el **vector
completo**:

```
r_FL + r_RR ≈ 2·r_c        r_FR + r_RL ≈ 2·r_c
```

y si el origen está en el centro geométrico esperado, `r_c = 0`:

```
r_i + r_j ≈ 0
```

Se reportan los residuos **X, Y, Z y la norma 3D (y la XY)**, y **nunca se usan para corregir las
mediciones**. Eso detecta lo que dos pruebas aisladas en X e Y pueden esconder.

### 10.3 Reglas de medición que no se relajan

1. **Repetibilidad ≠ resolución.** Las repeticiones críticas exigen **recolocar el instrumento**
   entre lecturas y usar **otro `setup_id`**. Tres lecturas seguidas sin moverse miden resolución
   instrumental, no repetibilidad, y la QA lo marca.
2. **Los residuos no se corrigen.** Si `x1 + x3 ≠ 0`, el residuo **es el dato**. Lecturas posibles:
   el CG real no coincide con el origen; la planta no es simétrica; error de medición. **Está
   prohibido ajustar coordenadas para forzar la simetría.**
3. **Masa nominal ≠ masa medida.** Los puntos 33/38/43/48/53 kg son **nominales derivados**
   (clase `E`). Antes de cada vuelo se pesa la configuración efectiva. En el CSV son **variables
   distintas**: `nominal_total_mass_kg` y `measured_total_mass_kg`. La diferencia es un resultado.
4. **RPM por rotor, no una sola del UAV.** Se registra `rpm_hover` con `element_id` = R1…R4.
   Diferencias entre rotores son evidencia directa contra el supuesto de reparto uniforme `mg/N`,
   y se pierden si se promedian.
5. **Sistema de referencia documentado, no solo declarado.** Hay que registrar **cómo** se
   materializó el origen y fotografiarlo. Un origen no documentado invalida todas las cotas.

### 10.2 No-circularidad del gate

**GATE 1A debe poder cerrarse exclusivamente con geometría y evidencia experimental.** Si el
script que decide el gate usara valores derivados de CFD, se introduciría circularidad antes de
empezar a simular.

Verificado automáticamente: `scripts/audit_measurement_csv.py` comprueba que ningún script del
gate (`build_geometry_manifests.py`, `annotate_manifests_with_media_evidence.py`,
`freeze_geometry_v1.py`) construya rutas a `cfd/results` ni `cfd/cases`.

> Nota: los manifiestos incluyen `derivados_nivel0` (momentum theory). Son **física analítica**,
> no CFD, y están marcados como órdenes de magnitud (§12 nivel 0). No crean circularidad, pero
> **no** son criterio de cierre del gate: solo contraste.
