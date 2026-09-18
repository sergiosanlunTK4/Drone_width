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

> Regla de honestidad: todo resultado obtenido con 1B abierto debe declararse como
> **exploratorio** y no puede entrar al dataset ni al paper como dato de la plataforma real.

---

## 1. Jerarquía de fuentes

| Nivel | Fuente | Etiqueta | ¿Vale para CFD de estudio? |
|---|---|---|---|
| 1 | Ficha oficial `ag.dji.com/es/<uav>/specs` | **P** | Sí, citando fuente y fecha |
| 2 | DJI Academy (formación de distribuidor) | **P-A** | Sí, anotando la fuente |
| 3 | **Evidencia documental visual** (imagen oficial con pie inequívoco) | **S** | Solo para hechos **discretos**: nº de brazos, coaxialidad, nº de palas, posición relativa. **Nunca para dimensiones.** |
| 4 | Medición propia protocolizada | **M** | Sí — único origen válido para dimensiones de estudio |
| 5 | Inferencia con razonamiento explícito | **I** | Solo como hipótesis de trabajo declarada |
| 6 | Estimación de planificación | **E** | Solo para dimensionar el problema |
| 7 | Desconocido | **D** | **Se deja `null`. No se rellena.** |

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

### 2.2 Multimedia pendiente de explotar

- `data/raw/media/01a_conocimiento_basico/p09_0a7ec705d2dc.emf` (**16 MB, vectorial**):
  la slide 9 es un **diagrama rotulado** con "Hélice", "Boquilla centrífuga", "Motor", "ESC",
  "Antena RTK", "Radar LiDAR", "Depósito de líquidos", "Bomba", etc. Un vectorial se escala sin
  pérdida ⇒ es el mejor candidato para leer **posiciones relativas**. Requiere conversión
  EMF→PNG/SVG (Inkscape o ImageMagick, no instalados en esta sesión).
- Quedan decks 04–09 por extraer (energía, agroquímicos, seguridad, instructivos, mantenimiento,
  operación práctica). Pueden contener material del **T55**.

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

## 5. Plantilla de captura

```csv
uav,bloque,id,parametro,valor,unidad,clasificacion,metodo,fecha,operador,incertidumbre,nota
T25P,rotor,R1_FL,posicion_x,0.697,m,M,cinta_desde_centro_buje,2026-XX-XX,,0.005,origen=CG
```

- **Bloque `rotor`** → una fila por campo y por rotor (§3).
- **Bloque `atomizer`** → una fila por campo y por atomizador (§4).
- **Bloques `masa`** y **`bancada`** → según §6.
- Guardar en `data/raw/mediciones_geometria.csv`. Si una medición contradice a la ficha
  oficial, **gana la medición** y se anota la discrepancia.

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
| D5 | Curva **empuje–RPM–torque–corriente** por rotor | bancada (ver §6.1) |

---

## 6.1 GATE 1B — estado operativo del rotor y decisión de frontera CFD

### 6.1.1 La pregunta que hay que cerrar primero

**¿El CFD impondrá RPM como condición de frontera, o empuje (thrust) equivalente?**

Es una decisión **previa** a la campaña de medición, porque determina qué dato es necesario:

| Estrategia CFD | Frontera que impone | Dato experimental necesario | Ventaja | Coste |
|---|---|---|---|---|
| **A. RPM prescrita** (MRF / sliding mesh / ALM) | ω del rotor + geometría de pala | **RPM en condición real** + geometría de pala fiable | Física de pala y estela de punta explícitas | Exige geometría de pala y RPM reales |
| **B. Empuje prescrito** (actuator disk) | Δp o distribución de fuerza por disco | **Empuje por rotor** en la condición de vuelo | Robusto; no necesita geometría de pala | No reproduce estelas de punta; arrastra la incertidumbre del disco |
| **C. Sustentación impuesta** (empuje = peso) | reparto de carga entre rotores | **masa total + reparto de empuje** (CG y ángulos) | Autoconsistente con el vuelo | Asume reparto uniforme salvo medición |

**Recomendación:** estrategia **B/C para el dataset principal** (niveles 1–3 del plan) y
**A en los casos selectos** de alta fidelidad, para cuantificar cuánto se pierde con el disco
actuador. Así el cuello de botella del dataset no depende de la geometría de pala — que es el
dato más caro de obtener.

### 6.1.2 Cómo medir RPM y empuje (en este orden)

**No empezar por la bancada.** El objetivo es la RPM **en condición real de hover/carga
representativa**: una RPM de motor descargado o inferida del KV es prácticamente inútil para
el modelo aerodinámico (context.md §42).

1. **RPM en hover real**, con masa representativa: tacómetro óptico o cámara de alta velocidad
   contando palas. Método directo y no invasivo.
2. **Telemetría autorizada** (requiere permiso escrito, §31) como contraste.
3. **Bancada de empuje**: curva empuje–RPM–torque–corriente. Necesaria de todos modos para las
   estrategias B/C y para resolver la ambigüedad de los valores publicados (**82 kg/brazo** en
   T100 y **54,2 kg/eje** en T70P: no se sabe si son por rotor o por par coaxial).
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

### GATE 1A — geometry validated

- [ ] A1, A2, A3, A4, A5, A6, A8 resueltos con `M` para las 4 plataformas.
- [ ] A7 (palas y geometría de pala) resuelto con `M` — o aceptado explícitamente como limitación
      si se decide ir por la estrategia CFD B/C sin geometría de pala.
- [ ] A9 resuelto: **conflicto 8 vs 16 rotores del T100 cerrado**.
- [ ] B1, B2, B3, B4 resueltos con `M` (posición, orientación y Δz de atomizadores).
- [ ] C1, C2, C3 resueltos con `M`.
- [ ] `geometry/manifests/*.json` sin `D` críticos en los bloques A/B.
- [ ] Sistema de referencia (§3) declarado una sola vez y aplicado a todos los datos.
- [ ] **Congelar `geometry-v1`**: hash de los manifiestos registrado en
      `geometry/manifests/FROZEN_geometry_v1.sha256`.

### GATE 1B — rotor operating state

- [ ] Estrategia de frontera CFD (§6.1.1) **decidida y documentada**.
- [ ] RPM en hover real medida con masa representativa, con incertidumbre.
- [ ] Empuje por rotor (o por par) medido en bancada; ambigüedad de 82 kg / 54,2 kg resuelta.
- [ ] Relación RPM ↔ masa ↔ empuje ↔ configuración ↔ atmósfera documentada.
- [ ] Reparto de empuje entre rotores coherente con el CG medido (C5).

**Mientras 1B esté abierto:** el CFD es exploratorio y se etiqueta como tal. Ningún resultado de
esa fase entra al dataset ni al paper como dato de la plataforma real.

---

## 9. Artefactos

| Artefacto | Generado por | Estado |
|---|---|---|
| `geometry/manifests/<uav>_geometry_manifest.json` | `scripts/build_geometry_manifests.py` + `scripts/annotate_manifests_with_media_evidence.py` | ✅ procedencia por campo + evidencia visual `S` |
| `data/processed/geometry_master.csv` | `scripts/build_geometry_manifests.py` | ✅ |
| `geometry/models/<uav>_control.stl` + `.meta.json` | `scripts/generate_control_geometry_v2.py` | ✅ geometría de control (no CAD fiel) |
| `data/raw/media/`, `data/processed/media_inventory.csv`, `figures/contact_sheets/` | `scripts/extract_pptx_media.py` | ✅ 178 objetos catalogados |
| `data/raw/mediciones_geometria.csv` | campaña de campo (bloques A–D) | ⬜ **cuello de botella** |
| `geometry/manifests/FROZEN_geometry_v1.sha256` | tras cerrar 1A | ⬜ |
| `data/raw/dji_academy_01_FUENTE.md` | registro de fuentes P-A y S | ✅ |
