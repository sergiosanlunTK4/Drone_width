# Metodología de cálculo

**Proyecto:** aerodinámica, downwash y deposición de pulverización en UAV agrícolas DJI Agras
(T25P · T55 · T70P · T100)
**Investigador principal:** Sergio Sánchez Luna
**Versión:** 2.0 — 2026-09-19
**Estado:** cuaderno técnico de trabajo, **no** manuscrito. Pendiente de validación experimental.

> **Cambio de nombre:** este documento se llamaba `COMO_SE_CALCULA.md`. Se renombra a
> **Metodología de cálculo** por indicación del investigador.

> **Correcciones de la versión 2.0.** La v1.0 contenía **un error físico central** y varias
> conclusiones adelantadas. Se corrigen y se dejan registradas:
> 1. **Eliminada** la deducción "1850 → 2275 rpm": era **circular y falsa** (§5.3).
> 2. **Separados** dos coeficientes distintos que se llamaban igual: `Ct_rotor` y `Ct_OF` (§5.4).
> 3. **Corregido** el significado de `Cp = 0`: es una restricción de un modelo, no una ley (§5.4).
> 4. **Añadido** el **equilibrio de momentos** al reparto por brazo (§4).
> 5. **Eliminada** la pregunta "¿comparte motor el par?": la arquitectura se conoce (§4.3).
> 6. **Rebajado** el desplazamiento de deposición por actitud a *baseline geométrico* (§6).
> 7. **Renombrados**: "actitud máxima teórica" → *límite estático por magnitud de empuje*;
>    H8 de "hallazgo" a **hipótesis derivada del modelo de trim**.
> 8. **Densidad** pasa a ser `ρ = f(P, T, RH)` (§3).
> 9. Corregido un **bug** en el área proyectada que duplicaba el área (§3.2).

---

## 0. Regla del proyecto

Ningún número entra al cálculo sin **dos cosas**: su **clase de fuente** y su **vía de validación**.
Un valor sin ambas no es un dato: es una suposición disfrazada.

| Clase | Significado | ¿Sirve para el estudio? |
|---|---|---|
| **P** | Público oficial (ficha DJI, capturada con hash) | Sí, citando fuente y fecha |
| **P-A** | DJI Academy (formación de distribuidor) | Sí, anotando la fuente |
| **S** | Evidencia visual en documento oficial | Solo hechos discretos |
| **O** | Aportado por el propietario | Hipótesis declarada. **Nunca se cita como de DJI** |
| **M** | Medición con instrumento | **Único origen válido para dimensiones de estudio** |
| **I** | Inferencia con razonamiento escrito | Hipótesis de trabajo |
| **E** | Estimación de planificación | Solo para dimensionar el problema |
| **D** | Desconocido | Se deja `null`. Parámetro de sensibilidad, no se rellena |

---

## 1. La cadena científicamente defendible

```
m, CG, V_aire, ρ
   ↓
Σ F = 0        y        Σ M_CG = 0          ← FUERZAS **Y MOMENTOS**
   ↓
θ, T_total, T_brazo_i
   ↓
s_i  (reparto coaxial: parámetro o medición)
   ↓
T_sup,i , T_inf,i
   ├──→  CFD principal:   T_i  →  FUENTE DE MOMENTO PRESCRITA
   └──→  RAMA INDEPENDIENTE para RPM:  T_i → curva medida o BEMT → RPM_i
```

**Punto clave:** **no se necesita el RPM para imponer el empuje** en el CFD principal
(arquitectura C→B). El RPM pertenece a **GATE 1B** y a la validación de alta fidelidad, y
**no debe volver a convertirse en bloqueo del actuator disk principal.**

**Implementado en:** `scripts/force_chain.py` (ejecutable y reproducible).

---

## 2. Entradas, con su clase

| Variable | Valor | Clase | Fuente |
|---|---|---|---|
| Masa MTOW | 175.0 kg | **P** | ficha oficial |
| Masa sin líquido | 73.0 kg | **O** | propietario (con batería, 2 boquillas) |
| Carga máxima | 100 kg / 100 L | **P** | ficha oficial |
| Nº de brazos | 4 | **O/M** | propietario + modelo medido |
| **Motores por brazo** | **2** | **O/M** | **4 brazos, 8 motores, 8 rotores** |
| Empuje máx. por brazo | 804.15 N (82 kg) | **P-A** | Academy |
| Diámetro de rotor | 1.5748 m | **P** | 62 in (hélice 6223) |
| Separación axial del par | 0.290 m | **M** | modelo T100 medido |
| Velocidad | 1 – 20 m/s | **O** | propietario |
| Incertidumbre instrumental | ±0.2 · resolución 0.1 | **M** | propietario, flexómetro |
| **Cd efectivo** | **0.8** | **E** | ⚠ **suposición propia** |
| **Área frontal** | **1.729 m²** | **E** | ⚠ **suposición propia** |
| **Arrastre vertical (planta)** | — | **D** | **no conocido** (§3.2) |
| **x del centro de presión respecto al CG** | — | **D** | **no conocido** (§4) |

### 2.1 Telemetría del Agras — disponibilidad confirmada (2026-09-19)

| Campo | Disponible | Cierra |
|---|---|---|
| **RPM de motor individual** (los 8) | ✅ **sí** | **incógnita del reparto coaxial `s_i`** (§4.4) y `RPM_sup/RPM_inf` |
| **RPM del atomizador centrífugo** | ✅ **sí** | comando vs consecuencia del tamaño de gota (§6.8) |
| **RPM de las bombas** | ✅ **sí** | relación bomba ↔ caudal |
| **Caudal real `Q`** | ✅ **sí** | **`W_commanded` y contraste del DOE** (§6.3) |
| Actitud `θ`, `φ` | ❓ **por confirmar** | las suposiciones [1] y [3] (§8) |
| Velocidad, tasa, altura, tamaño de gota configurado | previsiblemente sí | — |
| Masa/carga | inferible | H5, H8 |

> **Consecuencia metodológica:** la telemetría disponible **cambia dos incógnitas de `D` a
> medibles** —el reparto coaxial y el RPM— y con ello **GATE 1B puede cerrarse midiendo en lugar
> de calculando**. Eso elimina la rama de RPM del camino crítico del CFD (§5).
>
> **Lo que la telemetría NO da (si la actitud no está):** `Cd`, área frontal y arrastre vertical
> **siguen siendo suposiciones**, y la actitud tendría que deducirse de `ΣF = 0` invirtiendo el
> modelo — lo que **no** valida el modelo, sino que lo asume. Si la actitud no se puede medir,
> hay que declararlo como limitación y hacer análisis de sensibilidad sobre `Cd·A`.

---

## 3. Paso 1 — Actitud

### 3.1 Ecuaciones

Modelo **cuasiestacionario** de vuelo horizontal uniforme:

```
Vertical    :  T · cos θ  =  W
Horizontal  :  T · sin θ  =  D(V_aire)
              ─────────────────────
        ⇒       tan θ  =  D(V_aire) / W
        ⇒       T  =  √(W² + D²)
```

Coincide con los modelos publicados de multirrotores en avance ([1], [2]).

**El parámetro es la velocidad relativa al aire**, no la velocidad sobre el suelo:

```
V⃗_aire  =  V⃗_suelo  −  V⃗_viento
```

Y en general `D = ½ρV²_aire · Cd(θ) · A_proj(θ)`, con lo que la ecuación es **implícita**:

```
θ  =  tan⁻¹( D(V_aire, θ) / W )
```

resoluble por iteración. Literatura reciente de multirrotores modela explícitamente
contribuciones de área frontal y superior dependientes de la actitud ([2]).

### 3.2 ⚠ El modelo de área proyectada **no es utilizable** con los datos actuales

`A_proj(θ) = A_frontal·cos θ + A_planta·sin θ` **falla** porque trata la **planta completa**
(3.224 × 3.224 = 10.4 m²) como placa plana con el mismo `Cd`. Resultado a 20 m/s: **θ = 41°**,
físicamente absurdo para un dron agrícola.

Lo que falta es el **arrastre en dirección vertical** (la "planta" del dron), que es un dato
**distinto** del arrastre frontal y **no se conoce** (clase D). Tratar la planta como placa plana
con el mismo `Cd` es una extrapolación sin base.

**Decisión:** se usa el modelo **explícito** con solo el área frontal (A constante). La corrección
por actitud queda implementada pero **desactivada**, y activarla exige antes **calibrar el
arrastre vertical** — preferiblemente **midiendo la actitud real**.

### 3.3 Resultados (modelo explícito, MTOW 175 kg, aire seco 28 °C, ρ = 1.1716)

| V_aire (m/s) | D (N) | θ (°) | T total (N) |
|---|---|---|---|
| 3 | 7.2 | **0.24** | 1716.2 |
| 5 | 20.1 | **0.67** | 1716.3 |
| 8 | 51.4 | **1.71** | 1716.9 |
| 10 | 80.3 | **2.68** | 1718.0 |
| 13 | 135.7 | **4.52** | 1721.5 |
| 15 | 180.6 | **6.01** | 1725.6 |
| 20 | 321.1 | **10.60** | 1745.9 |

### 3.4 Nomenclatura corregida: **límite estático por magnitud de empuje**

```
cos θ_lim = W / T_max      →      θ_lim = 57.8°
```

**No** es "la actitud máxima del dron". Ignora: pérdida de capacidad en avance, potencia
eléctrica disponible, interferencia coaxial, límites del controlador, batería, estabilidad y
momentos. Es solo una **cota superior por magnitud de empuje**. Un T100 no queda habilitado para
volar a 57.8° porque esa desigualdad se cumpla.

---

## 4. Paso 2 — Trim: fuerzas **y momentos**

### 4.1 Por qué no basta dividir entre cuatro

```
Σ F = 0          y          Σ M_CG = 0
```

```
Σ_i ( r_i − r_CG ) × T_i  +  M_aero  =  0
```

El arrastre actúa en el **centro de presión**, que **no coincide con el CG**. Ese desfase genera
un **momento de cabeceo** que el reparto de rotores debe compensar. Por tanto:

```
Fuerzas + momentos  →  actitud  →  T_brazo,i
```

y **no** simplemente fuerzas → actitud → dividir entre cuatro.

### 4.2 Resultado

Con `x_cp_cg = ±0.05 m` (el desfase centro de presión ↔ CG), el desequilibrio
delantero/trasero a 10 m/s es de **±2.6 N por brazo**. Con `x_cp_cg = 0` se recupera
exactamente el reparto simétrico.

`x_cp_cg` **es desconocido** (clase D). **Validación:** posición real del CG a distintos estados
de carga + estimación del centro de presión.

### 4.3 Reparto coaxial

**Arquitectura conocida: 4 brazos, 8 motores, 8 rotores.** La pregunta *"¿comparte motor el
par?"* **ya no aplica** y se ha eliminado del documento.

**Lo que sigue desconocido (clase D):**

```
T_superior / T_inferior        y        RPM_superior / RPM_inferior
```

más la **estrategia de control**. En el CFD se trata como **parámetro** con barrido:

| s (superior) | T sup (N) | T inf (N) |
|---|---|---|
| 0.50 | 214.8 | 214.8 |
| 0.60 | 257.7 | 171.8 |
| 0.70 | 300.7 | 128.9 |

**Y no existe un `Ct` único para los dos rotores coaxiales**: la interferencia entre ellos impide
asumirlo ([3], [4]).

### 4.4 ✅ La telemetría resuelve esta incógnita

Con **RPM de motor individual** (confirmado disponible, §2.1), el reparto deja de ser un parámetro
ciego:

```
RPM_sup,i  y  RPM_inf,i   medidas por separado
        ↓
s_i  =  T_sup,i / (T_sup,i + T_inf,i)      medido, no supuesto
```

**Esto convierte `s_i` de `D` (desconocido) a `M` (medido)** y cierra el barrido 0.5/0.6/0.7: ya
no hay que elegir un valor plausible, se mide.

**Procedimiento:**

1. Vuelo en hover estacionario con masa conocida.
2. Registrar `RPM_R1…RPM_R8` sincronizadas por timestamp, más masa y condiciones ambientales.
3. Del par coaxial de cada brazo, obtener `RPM_sup` y `RPM_inf`.
4. Con la curva `T(RPM)` —de bancada, o de la vía 2 de §5— obtener `T_sup` y `T_inf`.
5. `s_i` por brazo, y su dispersión entre brazos.

> **Aviso:** el paso 4 sigue necesitando una relación `T(RPM)`. Las RPM medidas **no** dan el
> empuje por sí solas: dan la **relación entre los dos rotores del par**, que es la parte que no
> se podía deducir. Es un avance real, pero no elimina la necesidad de la curva `T(RPM)`.

---

## 5. Paso 3 — De empuje a RPM: **tres vías separadas**

### 5.1 El error eliminado

> ❌ **Retirado de la versión anterior:**
> *"Momentum theory da Ct ≈ 0.0061; por tanto el RPM coherente es ≈2275 y no 1850."*
>
> **Eso era falso y circular.** Verificación numérica:

```
Con T = 214.52 N, ρ = 1.1716, A = 1.9478 m², ΩR = 152.544 m/s:

    Ct_rotor      = T / (ρ A (ΩR)²)      = 0.00404
    λ_i           = √(Ct/2)              = 0.044943
    v_i desde λ_i = λ_i · ΩR             = 6.8558 m/s
    v_i directo   = √(T/(2ρA))           = 6.8558 m/s
    DIFERENCIA                           = 0.0   ← CERO
```

**Son el mismo resultado.** Momentum theory **deriva** el inflow de la definición de `Ct`; **no
proporciona un segundo `Ct` independiente** con el que corregir las RPM. NASA usa la misma
definición `C_T = T/(ρA(ΩR)²)` y calcula el inflow inducido a partir de ella ([4], [5]).

**Conclusión correcta:**

> **1850 rpm NO está validado. Pero tampoco está refutado. Simplemente NO SE SABE.**

Y el propio documento ya decía lo correcto: *"da POTENCIA, no RPM"*. **Esa frase es la que
sobrevive.**

### 5.2 Las tres vías

#### Vía 1 — Momentum theory

```
Conoce T  →  v_i = √(T/(2ρA))  →  P_i = T · v_i
```

**No determina RPM.** Da potencia y velocidad inducida.

A 214.5 N por rotor: `v_i = 6.86 m/s` · `P_ideal = 1471 W` · ×8 rotores = 11.8 kW ideal.

#### Vía 2 — Punto experimental conocido

Si se miden **simultáneamente** `T` y `RPM`:

```
Ct_rotor = T / (ρ A (Ω R)²)          ← definición rotorcraft, normalizada con ΩR
```

Sirve para **interpolar en un entorno limitado del punto medido**.

> 🔴 **Prohibido el razonamiento circular:** no se puede usar un RPM supuesto para obtener `Ct` y
> después usar ese mismo `Ct` para "demostrar" que el RPM supuesto era correcto. Es exactamente
> el error que se ha eliminado en §5.1.

#### Vía 3 — BEMT / curvas de hélice

Es la **única vía que predice RPM desde empuje**. Requiere **mucho más** que diámetro:

- geometría radial completa: **cuerda(r)**, **twist(r)**, planform;
- características de sección: **Cl(α, Re, M)** y **Cd(α, Re, M)**;
- número de Reynolds de la pala, solidez, velocidad de punta;
- y en **coaxial**: **modelo de interferencia** entre los dos rotores.

NASA señala explícitamente twist, planform, número de palas, solidez, velocidad de punta y
Reynolds como parámetros que afectan la carga del rotor ([3]).

**Estado actual:** no se dispone de nada de eso → **la predicción de RPM no es posible todavía.
Solo medirlo.**

### 5.3 Verificación de plausibilidad que **sí** se puede hacer

```
solidez σ = (2 palas × 0.085 m) / (π × 0.7874 m) = 0.0687
```

Rango típico de hélice de dron: **0.05–0.15** → **σ está en rango**. La geometría de pala es
plausible; lo que falta es su **distribución radial**.

### 5.4 ⚠ Dos coeficientes distintos que **no** deben confundirse

| Coeficiente | Definición | Normalizado con | Dónde se usa |
|---|---|---|---|
| **`Ct_rotor`** | `T / (ρ A (Ω R)²)` | **ΩR** (velocidad de punta) | rotorcraft, BEMT, **toda la cadena de §3–§5** |
| **`Ct_OF`, `Cp_OF`** | formulación Froude de `actuationDiskSource` | **U_o** (velocidad incidente) | OpenFOAM `actuationDiskSource` |

La implementación de OpenFOAM calcula ([6]):

```
T = 2 ρ A |U_o · n|² a (1 − a) ,        a = 1 − Cp_OF / Ct_OF
```

**Son coeficientes con otra formulación. El proyecto no debe tratarlos como el mismo `Ct`.**
En el código se nombran `Ct_rotor` y `Ct_OF`/`Cp_OF` respectivamente.

### 5.5 Corrección sobre `Cp = 0`

> ❌ **Retirado:** *"Cp = 0 significa empuje sin consumo de potencia: físicamente imposible."*
>
> **Demasiado categórico.** Lo correcto:

**El modelo `actuationDiskSource`/Froude de OpenFOAM exige `Cp > 0` y `Ct > 0`, y aborta si no lo
son** ([7]). Es una **propiedad/restricción de ese modelo**, no una demostración universal sobre
un rotor.

Y la razón de fondo es otra: en **hover `U_∞ = 0`**, y cualquier coeficiente de potencia
normalizado con `U_∞³` se vuelve una descripción **problemática**. En rotorcraft se normaliza con
`ΩR`:

```
C_P = P / (ρ A (Ω R)³)          ([8])
```

**Esa es la razón real** por la que `actuationDiskSource`/Froude es incómodo para nuestro problema
de hover — no una imposibilidad física.

---

## 6. Del atomizador a la deposición: los cuatro anchos

### 6.1 La distinción que ordena todo el problema

```
ANCHO COMANDADO  ≠  ABANICO AERODINÁMICO  ≠  ANCHO EFECTIVO DE DEPOSICIÓN
```

**El abanico no se impone: sale de `D(x,y)`. Y el caudal no determina el ancho: determina
CUÁNTO líquido se inyecta.** El campo de aire, el tamaño de gota y la condición inicial
determinan **DÓNDE** acaba.

### 6.2 Los cuatro anchos

| Ancho | Qué es | Cómo se obtiene | Estado |
|---|---|---|---|
| **W_commanded** | el que el **caudal** implica | `Q_real/(0.006 R V)` | derivable; requiere telemetría |
| **W_DJI** | el configurado en el controlador | lectura de pantalla | **P: 5–13 m** (y *"depende de la escena"*) |
| **W_aero** | abanico físico de los atomizadores | Lagrangiano **sin** plano receptor | pendiente: requiere CFD |
| **W_deposition** | ancho efectivo real | derivado de **D(x,y)** | **objetivo científico** |

> **La diferencia entre los tres primeros y el cuarto es, probablemente, uno de los resultados más
> valiosos de la investigación:** cuantifica cuánto se desvía la práctica operativa de la física
> real de deposición. Y DJI mismo reconoce que el ancho no es único: declara 5–13 m para el T100
> y aclara que **depende de la escena real de trabajo** ([9]).

### 6.3 Relación caudal-ancho (derivada, no citada)

```
En 1 s el dron recorre V m  →  cubre V·W m² = V·W/10000 ha
Volumen por minuto = 60 R V W/10000  [L/min]

    ⇒   Q = 0.006 R V W         [L/min; R en L/ha, V en m/s, W en m]
    ⇒   W_commanded = Q / (0.006 R V)
```

**Verificación** (R = 10 L/ha, V = 10 m/s, W = 6 m): `Q = 3.6000 L/min` ✓ coincide con el valor
aportado por el investigador.

**Qué revela la inversión** (a R = 10 L/ha, V = 10 m/s):

| Q (L/min) | Caso | W implícito |
|---|---|---|
| 3.6 | ejemplo | 6.0 m |
| 16 | caudal T50 (referencia) | 26.7 m |
| **30** | **T100 máx. 2 boquillas** | **50.0 m** |
| **40** | **T100 máx. 4 boquillas** | **66.7 m** |

Los máximos de bomba implican anchos absurdos **a esa tasa y velocidad** ⇒ la operación real usa
**otras combinaciones de (R, V)**. Es información que la telemetría revelará.

### 6.4 Cadena de inyección (implementada en `scripts/lagrangian_injection.py`)

```
rotores  →  U(x,y,z)                                   [CFD: fuente de momento prescrita]
Q, RPM_atomizador, d, posición/orientación  →  inyección de gotas
U + gotas  →  trayectorias  →  D(x,y)  →  W_deposition
```

**Condición inicial, relativa al aire:**

```
V_gota,0            =  V_UAV  +  V_atomizador
V_relativa al aire  =  V_gota,0  −  U(x_atomizador)
```

**Ecuación de movimiento por gota:**

```
m_p · dV_p/dt  =  F_D  +  m_p·g
F_D            =  ½ ρ C_D(Re_p) A_p |V_aire − V_p| (V_aire − V_p)
C_D(Re_p)      =  24/Re · (1 + 0.15 Re^0.687)          (Schiller-Naumann, Re < 1000)
```

**🔴 Hallazgo relevante:** a 10 000 rpm, la velocidad del borde del disco es

```
V_borde = ω·R_disco = 2π(10000/60)(0.05) = 52.4 m/s
```

frente a **5 m/s** del UAV. **La velocidad de lanzamiento domina sobre la del dron por un factor
10.** La condición inicial de la gota es esencialmente **el abanico del atomizador**, no la
velocidad del UAV — lo contrario de lo que asume un modelo "caudal → ancho".

**Y una incoherencia detectada en el modelo:** el vector de inyección declarado es `[0, 0, −1]`
(axial), pero **un disco centrífugo expulsa radialmente en el plano del disco**. El `[0,0,−1]`
parece ser el **eje de giro**, no la dirección de salida. Hay que reconciliarlo antes de inyectar.

### 6.5 De caudal a partículas

```
m_dot  = ρ_L · Q/60000            [kg/s]
m_gota = ρ_L · π d³/6             [kg]
N_dot  = m_dot · f_j / m_gota     [gotas/s] por bin j
```

Cada **parcela** Lagrangiana representa muchas gotas mediante su **peso estadístico**: a
d50 = 150 µm y 30 L/min salen del orden de 10⁶ gotas/s, inviable de inyectar literalmente.

### 6.6 Propiedades de la gota que determinan *dónde* acaba

| d (µm) | τ_p (s) | v_terminal (m/s) | v_term / v_borde |
|---|---|---|---|
| 50 | 1.5×10⁻⁵ | 0.061 | 0.0012 |
| 100 | 6.0×10⁻⁵ | 0.243 | 0.0046 |
| 150 | 1.3×10⁻⁴ | 0.470 | 0.0090 |
| 200 | 2.4×10⁻⁴ | 0.699 | 0.0133 |
| 300 | 5.4×10⁻⁴ | 1.164 | 0.0222 |
| 500 | 1.5×10⁻³ | 2.023 | 0.0386 |

`τ_p` es 3–5 órdenes de magnitud menor que el tiempo de vuelo (~1 s), y `v_terminal` es 25–800
veces menor que `v_borde`. **La gota se desacelera rápido hacia su velocidad terminal y después
cae, con el campo de aire actuando durante toda la caída.** No se puede atajar con una fórmula.

### 6.7 Actitud y deposición: baseline geométrico, no predicción

```
Δx = h · tan θ
```

**Puede conservarse como baseline geométrico**, pero **no debe escribirse** como "el abanico se
desplaza medio metro" ni como "sesgo de deposición del 4–10 %". Las gotas salen con la velocidad
del atomizador, llevan la del UAV, reciben downwash, gravedad, arrastre y viento, y tienen tiempos
de vuelo distintos según diámetro. **Eso lo responde el Lagrangiano.**

### H8 — hipótesis derivada del modelo de trim, **no hallazgo**

De `tan θ = D/(m g)` se sigue que, a igual resistencia, `m ↓ ⇒ θ ↑`.

**H8:** al vaciarse el tanque, la actitud necesaria para la misma velocidad aumenta, desplazando el
abanico de los atomizadores centrífugos. **Verificación:** telemetría de `m`, `V_aire` y `θ` durante
el vaciado. Es una **derivación**, no un resultado.

---

## 7. Densidad del aire

Para un estudio que compara cuatro plataformas en condiciones de campo, **no se congela una sola
ρ**. Se usa:

```
ρ = f(P, T, RH)

    P_sat = 610.94 · exp(17.625 T_C / (T_C + 243.04))        (Magnus)
    P_v   = RH · P_sat
    P_d   = P − P_v
    ρ     = P_d/(R_d T) + P_v/(R_v T)      R_d = 287.058, R_v = 461.495
```

| Condición | ρ (kg/m³) | Efecto en θ a 20 m/s |
|---|---|---|
| 28 °C, 70 % HR, nivel del mar | **1.1572** | referencia |
| 28 °C, aire seco, nivel del mar | 1.1716 | el valor de la v1.0 |
| 28 °C, 70 % HR, 1000 m | ~1.05 | **+12 % en D** → θ mayor |

---

## 8. Resumen de suposiciones

| # | Suposición | Clase | Impacto | Cómo validarla |
|---|---|---|---|---|
| **1** | `Cd = 0.8`, `A_frontal = 1.729 m²` | **E (propia)** | **θ varía ×4 a 20 m/s** | **Medir la actitud real** |
| **2** | `rpm = 1850` | **E (sin fuente)** | No refutado, no validado | Fuente del dato, o tacómetro en hover |
| **3** | Arrastre vertical (planta) | **D** | Bloquea el modelo implícito de θ | Calibrar, o medir actitud |
| **4** | `x_cp_cg = 0` | **D** | ±2.6 N por brazo a 10 m/s | Medir CG y centro de presión |
| **5** | Reparto coaxial `s = 0.5` | **D (incógnita)** | ±20 % por rotor con s = 0.6 | Medir `T_sup/T_inf` o `RPM_sup/RPM_inf` |
| **6** | Sin arrastre de hélices (H-force) | omisión | **Subestima θ** | Cd0 de pala, o medir actitud |
| **7** | Sin geometría radial de pala | **D** | **Impide predecir RPM** | Medir cuerda(r), twist(r), Cl/Cd de sección |

**No requiere validación:** el equilibrio de fuerzas y momentos es física elemental; la teoría de
cantidad de movimiento es estándar; y la geometría del T100 está **medida** (clase M, ±0.2,
resolución 0.1).

---

## 9. Fuentes

**Verificadas con descarga** (`scripts/verify_sources.py` → `evidence/fuentes_verificadas.json`):
4 de 6 con contenido confirmado. Los enlaces de documentación de OpenFOAM dieron 404 o
confirmación parcial, así que **se citan con esa reserva**.

### Literatura primaria — para el manuscrito

| Ref | Fuente |
|---|---|
| **[1]** | *Practical Endurance Estimation for Minimizing Energy Consumption of Multirotor UAVs*, Energies 11(9):2221. https://www.mdpi.com/1996-1073/11/9/2221 |
| **[2]** | *Design of an Autonomous Airborne Recovery System: A Fixed-Wing UAV–Quadrotor Platform Using Improved NMPC and Vision-Based Control*, Drones 10(3):212. https://www.mdpi.com/2504-446X/10/3/212 |
| **[3]** | Johnson, W. *Rotorcraft Aeromechanics*. NASA/TP–2005–213477. https://rotorcraft.arc.nasa.gov/Publications/files/Johnson_TP-2005-213477.pdf |
| **[4]** | Johnson, W. NASA/TP–20250010468. https://ntrs.nasa.gov/api/citations/20250010468/downloads/Johnson%20TP-202510468.pdf |
| **[5]** | Koning, W. et al. NASA/CR–2016–219086. https://rotorcraft.arc.nasa.gov/Publications/files/Koning%20CR-2016-219086_FINAL.pdf |

### Documentación de software

| Ref | Fuente |
|---|---|
| **[6]** | OpenFOAM API — `actuationDiskSource` Class Reference. https://api.openfoam.com/2506/classFoam_1_1fv_1_1actuationDiskSource.html |
| **[7]** | OpenFOAM API — `actuationDiskSourceTemplates.C`. https://api.openfoam.com/2312/actuationDiskSourceTemplates_8C_source.html |
| **[8]** | OpenFOAM Documentation — *Semi implicit source*. https://doc.openfoam.com/2306/tools/processing/numerics/fvoptions/sources/rtm/semiImplicit/ |

### Especificaciones del fabricante

| Ref | Fuente |
|---|---|
| **[9]** | DJI AGRAS T100 — Specs. https://ag.dji.com/t100/specs · *(capturada con hash en `data/raw/specs_captures/`)* — ancho efectivo de aspersión **5–13 m**, y aclaración explícita de que **depende de la escena real de trabajo**; caudales máximos **30 L/min (2 atomizadores)** y **40 L/min (4 atomizadores)** |

> **Nota de honestidad sobre las fuentes:** el valor de `Cd = 0.8` y el de área frontal **son
> suposiciones propias**. **No se atribuyen a ninguna fuente.** Citarlos como literatura sería
> una cita falsa. Igual criterio con `rpm = 1850`.

---

## 10. Estado y bloqueo

| Gate | Qué lo cierra | Estado |
|---|---|---|
| **1A (T100)** | geometría medida, sin `D` críticos | ✅ **cerrable** (falta formalizar) |
| **1A (T25P/T55/T70P)** | medición física | ⬜ pendiente |
| **1B** | RPM real y reparto de empuje | 🟢 **desbloqueado por telemetría** (§2.1, §4.4): RPM de motor individual + de atomizador + de bombas + caudal |
| **CFD-0** | un caso ejecutado + **integral de la fuente verificada** | ❌ **bloqueado: bug #6** |
| **CFD-suite** | 128 casos de DOE-A | ⬜ requiere CFD-0 |
| **Lagrangiano** | deposición D(x,y) | ⬜ requiere CFD-suite |
| **Validación experimental** | actitud, downwash, deposición | ⚠️ telemetría parcial; actitud por confirmar |

**El bug CFD #6 es real:** OpenFOAM calcula el empuje Froude en función de `|U_o·n|²`; con flujo
horizontal y disco horizontal, `U_o·n ≈ 0` y `T ≈ 0`. Coincide con el resultado medido
(`U_z ≈ 10⁻⁷`) aunque `simpleFoam` converja.

**No se repara cambiando `Cp`/`Ct`.** Para la arquitectura C→B el CFD debe recibir `T_i` y la
fuente debe satisfacer:

```
∫_{V_i}  f  dV  =  T_i
```

sin recalcular el empuje a partir de `U_∞`. OpenFOAM dispone de fuentes explícitas/semi-implícitas
y de `codedSource`, además de `rotorDiskSource` ([8]).

> **CFD-0 se mantiene ABIERTO hasta verificar la INTEGRAL DE LA FUENTE**, no solo que aparezca
> downwash.

---

## 11. Lo que necesito del investigador

**Confirmado disponible (2026-09-19):** RPM de motor individual · RPM del atomizador · RPM de las
bombas · caudal. Con eso, las necesidades [2] y [3] de la lista anterior **quedan cubiertas por
telemetría** en lugar de por cálculo.

| # | Necesidad | Para qué | Coste |
|---|---|---|---|
| **1** | **¿La actitud `θ`, `φ` está en la telemetría?** — el investigador lo está revisando | Cierra las suposiciones [1] y [3], que hoy tienen **un factor 4 de impacto**. Si **no** está, hay que declararlo como limitación y hacer sensibilidad sobre `Cd·A` | **Bajo** |
| **2** | **Curva `T(RPM)`** de bancada, al menos para un rotor | Las RPM medidas dan la **relación** entre rotores, pero no el empuje absoluto (§4.4) | Medio |
| **3** | **`T_0`, `RH_0`, `P_0` reales** de la campaña | Fija la atmósfera basal con datos, no con estimaciones (`ρ_0 = f(P,T,RH)`) | **Bajo** |
| **4** | **Rangos de `V` y `H` de aplicación** (no de traslado) | Los 1–20 m/s son cotas. El DOE necesita el rango operativo real | **Bajo** |
| **5** | **Geometría radial de pala**: cuerda(r), twist(r) | Habilita predecir RPM por BEMT (vía 3, §5) | Medio |
| **6** | **CG** por estado de carga y **centro de presión** | Cierra [4] y habilita H5/H8 | Medio |
| **7** | **Permiso de uso de la telemetría** | Sin él no se puede publicar ni archivar (§31) | Trámite |

### 11.1 Las tres nuevas preguntas que abre la telemetría

Con telemetría real aparecen preguntas que antes no se podían plantear, y son **de las
interesantes**:

1. **¿Qué manda el Agras y qué resulta del comando?** Si el operador fija "tamaño de gota", ¿la
   RPM del atomizador es **consecuencia**? Si el operador fija "tasa L/ha", ¿el caudal se calcula
   automáticamente? **Eso determina qué variables del DOE son independientes y cuáles derivadas**
   (§6.8, §4.2 de `diseno_experimental.md`).
2. **¿Cómo se reparte el empuje entre rotor superior e inferior durante el vuelo?** Se puede ver
   si el reparto **cambia con la velocidad** — algo que ningún modelo predice hoy.
3. **¿Coincide `Q_calculado = 0.006 R V W` con `Q_telemetría`?** Si sí, se valida nuestra
   interpretación de las variables operacionales. Si no, **el que está mal es el modelo, y hay
   que averiguar por qué**.

---

*Versión 2.1 — 2026-09-19. Toda suposición declarada con su clase y su vía de validación.
Generado a partir de `scripts/force_chain.py`, verificable y reproducible. Ningún valor se
atribuye a una fuente que no haya sido comprobada.*
