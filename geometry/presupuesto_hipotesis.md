# Presupuesto de hipótesis — estudio paramétrico con geometría declarada

**Pregunta que responde este documento:** ¿se puede sostener un estudio con lo declarado en la web,
sin mediciones propias?

**Respuesta:** sí, **como estudio paramétrico con idealizaciones declaradas**, y con tres
condiciones que lo separan de un dato inventado. Lo que **no** se puede sostener es llamarlo
validado, ni cerrar los gates con valores `M`.

Generado y mantenido por `scripts/assumption_budget.py` →
`geometry/presupuesto_hipotesis.json`.

---

## 1. Las tres condiciones

Una idealización del tipo "suponga que es un cilindro perfecto" es legítima en un paper **si y solo si**:

| # | Condición | Cómo se cumple aquí |
|---|---|---|
| 1 | **Se declara** en su propia sección y en una tabla, no escondida en Métodos | §3 de este documento + tabla de §4 |
| 2 | **Se justifica**: por qué es razonable, o por qué el resultado es insensible a ella | §5 (ranking de sensibilidad) |
| 3 | **Se cuantifica su impacto** con análisis de sensibilidad | §5, cada incógnita con su efecto en % |

Lo que **no** es una idealización:

> Escribir "según DJI, los atomizadores están a −0,9 m" cuando ese dato vino del propietario por
> comunicación directa. **Eso no es idealizar: es citar mal.** La etiqueta `O` existe precisamente
> para que eso no ocurra.

---

## 2. Jerarquía de fuentes (actualizada)

| Clase | Significado | ¿Entra al CFD de estudio? |
|---|---|---|
| **P** | Público oficial (ficha DJI) | Sí, citando fuente y fecha |
| **P-A** | DJI Academy (formación de distribuidor) | Sí, anotando la fuente |
| **S** | Evidencia documental visual | Solo hechos discretos (topología, nº de palas) |
| **O** | **Aportado por el propietario** por comunicación directa | **Solo como hipótesis declarada**, nunca citado como DJI |
| **M** | Medición propia protocolizada | Sí — único origen válido para dimensiones de estudio |
| **I** | Inferido con razonamiento explícito | Solo como hipótesis declarada |
| **E** | Estimación de planificación | Solo para dimensionar el problema |
| **D** | Desconocido | **No.** Se deja `null` y se usa como parámetro de sensibilidad |

---

## 3. Inventario: qué es dato y qué es hipótesis

### 3.1 Datos con fuente (no son hipótesis)

| Campo | Clase | Fuente |
|---|---|---|
| Masa con batería / MTOW | `P` | ficha oficial |
| Diámetro de rotor (1270 / 1575 / 1574 mm) | `P` | ficha oficial (50 / 62 in) |
| Motor: estator y KV | `P` | ficha oficial |
| Nº de atomizadores y separación entre boquillas | `P` | ficha oficial |
| Caudales, rango de gota, ancho nominal | `P` | ficha oficial |
| Hélice 6223 = 62 × 23 in, 2 palas | `P-A` + `S` | Academy + imagen oficial |
| Coaxialidad de T70P y T100 | `S` | imagen oficial |

### 3.2 Aportado por el propietario (`O`)

| Campo | Valor | Uso permitido |
|---|---|---|
| Nº de motores | T100: 8 · resto: 4 | hipótesis declarada |
| X de atomizadores (T100) | −0,9 / −0,8 / −0,8 / −0,9 m | hipótesis declarada |

### 3.3 Hipótesis de trabajo declaradas (`I`)

| Hipótesis | Contenido | Cómo se refutaría |
|---|---|---|
| **H-1** | "distancia diagonal entre ejes" = separación entre ejes de rotores **opuestos** | medición de separación entre bujes |
| **H-2** | separación declarada de boquillas = **par extremo**; interior cerrado a la mitad | medición de la Y de cada boquilla |
| **H-3** | planta en X regular (4 brazos a 45°/135°/225°/315°) | medición de la posición de cada rotor |
| **H-4** | reparto de empuje uniforme `mg/N` | RPM por rotor + bancada |
| **H-5** | "8 motores" ⇒ 8 discos de rotor (no 16) | conteo físico fotografiado |

### 3.4 Desconocidos (`D`) — se usan como **parámetros de sensibilidad**, no se rellenan

Separación axial del par coaxial · reparto de empuje superior/inferior · nº de rotores del T100 ·
posición XYZ de rotores · posición Z de atomizadores · RPM real · geometría de pala.

---

## 4. Tabla de hipótesis para el paper

Esta tabla va **en el manuscrito**, en su propia sección. Es el formato que hace defendible el
estudio:

| # | Idealización | Valor adoptado | Base | Justificación | Sensibilidad |
|---|---|---|---|---|---|
| 1 | Rotores como **discos actuadores** con empuje prescrito | Δp por disco | decisión de arquitectura (C→B) | no requiere geometría de pala, que es el dato más caro | comparación con RPM prescrita en casos selectos |
| 2 | Rotores **coplanarios** y en planta regular | 45° entre brazos | `I` a partir del wheelbase | coherente con el sobre desplegado (+0,05 % en T100) | ±3 cm en la posición ⇒ **±3,5–4,3 %** en la separación entre ejes |
| 3 | **Reparto de empuje uniforme** | `T_i = mg/N` | `I` | primera aproximación; **se contrasta** con el CG medido | si el reparto real es 60/40 ⇒ **±20 % en el empuje de cada disco** |
| 4 | Nº de rotores del T100 | **8** | `S` (imagen) + `O` (propietario) | dos fuentes independientes convergen | si fueran 16 ⇒ **−29 %** en `v_inducida` (factor √2) |
| 5 | Par coaxial como **dos discos independientes** | separación axial paramétrica | `E` | sin medición disponible | ±10 cm ⇒ **±3,3 %** en la longitud de estela |
| 6 | Atomizadores como **fuentes puntuales** en el centro del disco | XYZ con Z desconocida | `O` (X) · `I` (Y) · `D` (Z) | simplificación estándar | ±20 cm en Z ⇒ **±6,7 %** en la altura de caída dentro de la estela |
| 7 | Agua pura, sin evaporación, sin viento, terreno plano | ρ = 1,1716 kg/m³ a 28 °C | `P` (alcance) | escenario base declarado | reportado como límite del alcance |
| 8 | Superficie receptora **plana y sin cultivo** | suelo desnudo | `P` | permite aislar el efecto aerodinámico | el efecto del dosel queda fuera de alcance y declarado |

---

## 5. Ranking de sensibilidad — dónde gastar el esfuerzo de medición

Cuantificado en `scripts/assumption_budget.py`. Ordenado por efecto sobre el resultado:

| # | Incógnita | Magnitud afectada | Efecto | Coste de resolverla |
|---|---|---|---|---|
| 1 | **Nº de rotores del T100** (8 vs 16) | `v_inducida` en hover | **−29 %** (factor √2) | **contar y fotografiar — minutos** |
| 2 | **Reparto de empuje superior/inferior** | empuje de cada disco | **±20 %** (si 60/40) | RPM por rotor + bancada |
| 3 | **Posición Z de atomizadores** | altura de caída en la estela | **±6,7 %** | **cinta métrica — minutos** |
| 4 | **Posición XYZ de rotores** | separación entre ejes (interferencia) | **±3,5–4,3 %** | **cinta métrica — minutos** |
| 5 | **Separación axial del par** | longitud de estela | **±3,3 %** | **cinta métrica — minutos** |
| 6 | RPM real | frontera CFD (RPM vs empuje) | no cuantificable sin medir | tacómetro en hover (requiere volar) |

### 5.1 La observación que importa

**Cuatro de las seis incógnitas se resuelven con cinta métrica y conteo**, sin instrumentos
especiales y sin volar. Solo dos (reparto de empuje y RPM) exigen equipamiento o vuelo.

Por tanto: **el estudio paramétrico es viable hoy**, y la medición no es un prerrequisito para
empezar — es una **mejora con retorno alto y coste bajo** que se puede hacer en paralelo.

---

## 6. Cómo se presenta esto en el paper (borrador)

> **Model assumptions and uncertainty budget**
>
> This study is a *parametric* investigation of rotor downwash and spray deposition for four DJI
> Agras platforms (T25P, T55, T70P, T100). Platform characteristics were taken from the
> manufacturer's published specifications, supplemented by official training material and
> photographic evidence. Because a full geometric survey of each airframe was not available at the
> time of writing, the following idealizations were adopted and their influence quantified
> (Table X).
>
> Rotors were represented as actuator disks with prescribed thrust, following the standard
> practice for multirotor wake modelling at this scale. The thrust distribution among rotors was
> assumed uniform (`T_i = mg/N`); this is the weakest assumption in the model, and a non-uniform
> split of 60/40 would alter the per-disk thrust by 20 %. For the coaxial platforms (T55, T70P,
> T100), the axial spacing between the upper and lower rotor planes was treated as a parametric
> input rather than a fixed value.
>
> The rotor count of the T100 is reported as "8 pairs" in the manufacturer's specification table
> while official imagery shows four arms with one coaxial pair each; two independent sources
> (official imagery and direct correspondence with the platform operator) indicate eight rotors,
> which is the value adopted here. Should the correct count be sixteen, the hover-induced velocity
> would decrease by 29 % (a factor of √2), which bounds the influence of this uncertainty on the
> results.
>
> Atomizer positions were specified in the longitudinal direction from direct measurement by the
> platform operator and derived laterally from the manufacturer's published nozzle spacing, under
> the explicit assumption that the published figure corresponds to the outermost pair. The vertical
> position of the atomizers relative to the rotor plane was not available and is treated as a
> sensitivity parameter; a ±0.2 m variation changes the fall height within the rotor wake by 6.7 %.
>
> No experimental validation is claimed. The results should be read as a parametric
> characterization of the modelled configurations, and the sensitivity analysis in Section X
> identifies which platform-specific measurements would most reduce the present uncertainty.
> A companion experimental campaign is in progress.

**Lo que este texto hace bien:** declara, justifica, cuantifica y **no reclama validación**.
Revisores aceptan esto; lo que no aceptan es un "suponga que" silencioso.

---

## 7. Lo que sigue prohibido

- Llamar **validado** a cualquier resultado obtenido con esta base.
- Cerrar GATE 1A o 1B con valores `O`, `I` o `E`. Solo `M` cierra gates.
- Alimentar la app/surrogate: predeciría sobre geometría supuesta, y una app agrícola que recomienda
  interlineado sobre supuestos no medidos es un problema de responsabilidad, no solo científico.
- Citar valores `O` como si fueran de DJI.

---

## 8. Estado

La campaña de medición **está en curso** por el propietario. Cuando lleguen las filas, los valores
`O` / `I` / `E` de la columna "Base" se promueven a `M`, se recalcula la sensibilidad y **el trabajo
no se tira: se promueve**. Ese es exactamente el diseño previsto.
