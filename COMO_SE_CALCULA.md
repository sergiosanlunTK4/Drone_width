# Cómo se calcula — registro de la investigación

**Proyecto:** aerodinámica, downwash y deposición de pulverización en UAV agrícolas DJI Agras
(T25P · T55 · T70P · T100)
**Investigador principal:** Sergio Sánchez Luna
**Fecha:** 2026-09-19 · **Versión:** 1.0

---

## 0. Qué es este documento y por qué existe

Este es el **registro único de cómo se hacen las suposiciones** del proyecto. Existe porque el
investigador lo pidió explícitamente:

> *"quiero que me des el registro de como se hacen esas suposiciones para que valide"*

**La regla del proyecto es una sola:** ningún número entra al cálculo sin dos cosas —
**(a) su clase de fuente** y **(b) la forma de validarlo**. Un valor sin esas dos cosas no es un
dato: es una suposición disfrazada, y el proyecto entero se construyó para evitar eso.

### Clases de fuente

| Clase | Significado | ¿Sirve para el estudio? |
|---|---|---|
| **P** | Público oficial (ficha DJI, capturada con hash) | Sí, citando fuente y fecha |
| **P-A** | DJI Academy (formación de distribuidor) | Sí, anotando la fuente |
| **S** | Evidencia visual en documento oficial | Solo hechos discretos, nunca dimensiones |
| **O** | Aportado por el propietario, comunicación directa | Como hipótesis declarada. **Nunca se cita como de DJI** |
| **M** | Medición con instrumento | **Único origen válido para dimensiones de estudio** |
| **I** | Inferencia con razonamiento escrito | Hipótesis de trabajo declarada |
| **E** | Estimación de planificación | Solo para dimensionar el problema |
| **D** | Desconocido | Se deja `null`. Es parámetro de sensibilidad, no se rellena |

---

## 1. LA CADENA DE CÁLCULO: de las fuerzas al RPM por motor

Toda la física del proyecto sale de esta cadena. **Cada paso introduce suposiciones, y están
todas declaradas.**

```
FUERZAS  →  ACTITUD  →  REPARTO POR BRAZO  →  REPARTO POR MOTOR  →  EMPUJE POR ROTOR  →  RPM
 Paso 1      Paso 1        Paso 2                 Paso 3               Paso 4
```

**Implementado en:** `scripts/force_chain.py` (ejecutable, reproducible).

---

### PASO 0 — Entradas, con su clase

| Variable | Valor | Clase | Fuente |
|---|---|---|---|
| Masa MTOW | 175.0 kg | **P** | ficha oficial |
| Masa sin líquido | 73.0 kg | **O** | propietario (con batería, 2 boquillas) |
| Carga máxima | 100 kg / 100 L | **P** | ficha oficial |
| Nº de brazos | 4 | **O** | propietario |
| Motores por brazo | 2 | **O** | propietario (8 motores / 4 brazos) |
| Empuje máx. por brazo | **804.15 N (82 kg)** | **P-A** | Academy |
| Diámetro de rotor | 1.5748 m | **P** | 62 in (hélice 6223) |
| Paso de hélice | 23 in | **P-A** | Academy: 6223 = 62×23 in |
| Palas por rotor | 2 | **P-A** | Academy + imagen |
| Separación axial del par | 0.290 m | **M** | modelo T100 medido |
| Velocidad | 1 – 20 m/s | **O** | propietario |
| Cuerda media de pala | 0.085 m | **E** | generador del propietario, **sin fuente** |
| **RPM en hover** | **1850** | **E** | generador del propietario, **sin fuente ni cálculo** |
| **Cd efectivo** | **0.8** | **E** | ⚠ **suposición mía** |
| **Área frontal** | **1.729 m²** | **E** | ⚠ **suposición mía** |

---

### PASO 1 — Equilibrio de fuerzas → actitud

**Ecuaciones** (equilibrio estático en vuelo nivelado, sin aceleración):

```
Vertical    :  T · cos θ  =  W
Horizontal  :  T · sin θ  =  D(V)
              ─────────────────────
        ⇒       tan θ  =  D(V) / W
        ⇒       T  =  √(W² + D²)

        D(V) = ½ · ρ · Cd · A_frontal · V²
```

**Nota:** `T` es el empuje **total**, no solo el que sostiene. Incluye el término `√(W²+D²)`.

**Resultados a MTOW (175 kg, ρ = 1.1716 kg/m³ a 28 °C):**

| V (m/s) | D (N) | θ (°) | T total (N) | T/W |
|---|---|---|---|---|
| 3 | 7.3 | **0.24** | 1716.2 | 1.0000 |
| 5 | 20.3 | **0.68** | 1716.3 | 1.0001 |
| 8 | 51.9 | **1.73** | 1716.9 | 1.0005 |
| 10 | 81.0 | **2.70** | 1718.1 | 1.0011 |
| 13 | 136.9 | **4.56** | 1721.6 | 1.0032 |
| 15 | 182.3 | **6.06** | 1725.8 | 1.0056 |
| 20 | 324.1 | **10.70** | 1746.5 | 1.0177 |

**Actitud máxima teórica:** `cos θ_max = W/T_max` → **57.7°**
(margen de empuje = 3216.6 N / 1716.8 N = **1.874**)

**🔴 Suposiciones de este paso — las que hay que validar:**

| # | Suposición | Impacto | Cómo validarla |
|---|---|---|---|
| **1** | **Cd y A_frontal constantes**, con los valores que elegí | **θ a 20 m/s varía entre 4.9° y 18.3° según Cd·A — un factor 4** | **Medir la actitud real** (telemetría Agras o vídeo lateral) a varias velocidades |
| 2 | Vuelo estacionario, sin maniobra | Bajo en operación normal | — |
| 3 | Empuje perpendicular al disco | Bajo (disco actuador ideal) | — |
| **4** | **No se incluye el arrastre de las hélices (H-force)** | **Subestima θ**; no cuantificado | Requiere Cd0 de pala, o medición de actitud |
| 5 | Cd constante con Re | Pequeño en el rango | — |

> **Por qué la suposición [1] es la más grave:** `1.729 m²` lo calculé como `3.224 × 0.975 × 0.55`,
> con un factor 0.55 que **inventé** para "no es un prisma lleno". Y `Cd = 0.8` es un valor típico
> que **no verifiqué en literatura primaria**. Ambos son míos, y su producto manda sobre θ.

---

### PASO 2 — Reparto por brazo

```
T_brazo = T_total / n_brazos
```

A 10 m/s: `1718.1 N / 4 = 429.5 N por brazo`

**🔴 Suposición [6]: reparto simétrico ⇒ el CG está en el centro geométrico.**

Es correcto **solo** si el CG coincide con el centro. Con batería, tanque y atomizadores
desplazados, el reparto **no** es uniforme. **Validación:** medir la posición real del CG
(bloque C5 del protocolo, pendiente).

---

### PASO 3 — Reparto por motor ← **LA INCOGNITA CENTRAL**

```
T_superior = T_brazo · s
T_inferior = T_brazo · (1 − s)          s = split (fracción al rotor superior)
```

**Lo que sabemos y lo que no:**

- ✅ **Sabemos:** 2 motores por brazo; 82 kg de empuje **por brazo**
- ❌ **No sabemos:** cómo se reparte entre el rotor **superior** y el **inferior**

**🔴 Suposición [3] — tratada como PARÁMETRO, no como valor:**

| s (superior) | T sup (N) | T inf (N) | Diferencia |
|---|---|---|---|
| 0.50 | 214.8 | 214.8 | 0.0 |
| 0.60 | 257.7 | 171.8 | **+85.9** |
| 0.70 | 300.7 | 128.9 | **+171.8** |

**Por qué no se puede suponer 50/50 sin justificarlo:** el rotor inferior opera en la estela
del superior. Ve una velocidad de entrada mayor, y para el mismo régimen entrega **menos empuje**.
Además, el reparto depende de la asignación de control del flight controller y del equilibrio de
par. Ver `geometry/coaxial_thrust_split.md`.

**Validación:** (a) saber si el par comparte motor o son **dos independientes**; (b) medir RPM de
ambos rotores **simultáneamente**.

---

### PASO 4 — De empuje a RPM

#### Camino A — coeficiente de empuje efectivo (anclado a un punto conocido)

```
T = Ct · ρ · A · (Ω R)²        ⇒        Ct = T / (ρ · A · (Ω R)²)
```

Es un coeficiente del **conjunto rotor** (absorbe perfil, twist, pérdidas de punta…). Sirve si
existe **un punto (T, rpm) fiable**; entonces escala a otros regímenes.

**Punto de anclaje declarado:** T = 214.52 N, rpm = **1850**
→ A = 1.9478 m² · ΩR = 152.54 m/s · **Ct = 0.00404**

**⚠️ PROBLEMA DETECTADO EN EL PUNTO DE ANCLAJE:**

La teoría de cantidad de movimiento da, para esa carga de disco:

```
λ_i = v_i/(ΩR) = sqrt(Ct/2) ;  Ct_momentum ≈ 0.0061   (frente a 0.00404)
```

Y como `Ct ∝ Ω²`:

```
Ω_real / Ω_anclaje = sqrt(0.0061 / 0.00404) = 1.23
⇒  RPM coherente con T = 214.5 N  ≈  2275 rpm,  no 1850
```

**El valor 1850 rpm no es coherente con su propio empuje.** Además, el generador del propietario
**no contiene ningún cálculo** que lo respalde: es un número puesto a mano.

#### Escalado de RPM con ese Ct (arrastra la suposición anterior)

| s | T rotor (N) | rpm | Δ vs 1850 |
|---|---|---|---|
| 0.50 (sup/inf) | 214.8 | 1851 | +1 |
| 0.60 sup | 257.7 | 2028 | +178 |
| 0.60 inf | 171.8 | 1656 | −194 |
| 0.70 sup | 300.7 | 2190 | +340 |
| 0.70 inf | 128.9 | 1434 | −416 |

#### Camino B — BEMT / cantidad de movimiento

```
v_i = √(T / (2 ρ A))        P_i = T · v_i        P = P_i / FM
```

Resultados (un rotor a 214.5 N, FM = 0.70):

```
v_inducida = 6.86 m/s   ·   P_ideal = 1471 W   ·   P_estimada = 2101 W
× 8 rotores = 16.8 kW
```

**Da POTENCIA, no RPM.** Para RPM por teoría de pala hace falta la **geometría real de pala**
(cuerda por sección, twist, Cd0). El modelo solo declara `cuerda media = 0.085 m` **sin
distribución** → **🔴 Suposición [4]: bloquea el cálculo riguroso de RPM.**

**Comprobación de plausibilidad que sí se puede hacer:**

```
solidez σ = (2 palas × 0.085 m) / (π × 0.7874 m) = 0.0687
```

Rango típico de hélice de dron: **0.05–0.15**. → **σ está en rango.** La geometría de pala es
plausible; lo que falta es su distribución.

---

## 2. Resumen: las suposiciones a validar

| # | Suposición | Clase | Impacto | Cómo cerrarla |
|---|---|---|---|---|
| **1** | `Cd = 0.8` y `A_frontal = 1.729 m²` | **E (mía)** | **θ varía ×4 a 20 m/s** | **Medir actitud real** — barato, alto impacto |
| **2** | `rpm_hover = 1850` | **E (sin fuente)** | **Toda la cadena de RPM cuelga de aquí** | Fuente del dato, o tacómetro en hover |
| **3** | Reparto coaxial `s = 0.5` | **D (incógnita)** | ±20 % por rotor con s = 0.6 | Saber si el par comparte motor; medir RPM de ambos |
| **4** | `cuerda_media` sin distribución | **E** | Bloquea el RPM por teoría de pala | Medir la pala (raíz/punta, twist, perfil) |
| **5** | Sin arrastre de hélices (H-force) | omisión | Subestima θ | Igual que [4], o medir actitud |
| **6** | Reparto simétrico por brazo | `I` | Sesgo si el CG no está centrado | Medir el CG (bloque C5) |
| **7** | Cd constante con Re | omisión | Pequeño | Declarar |

### Lo que **no** requiere validación

- **El equilibrio de fuerzas** (Paso 1) es física elemental: no necesita cita.
- **La teoría de cantidad de movimiento** (Paso 4B) es estándar.
- **La geometría del T100 está medida** (clase `M`, incertidumbre ±0.2, resolución 0.1).

---

## 3. ¿Está el ángulo en la literatura?

**Pregunta del investigador:** *"el ángulo también debemos calcularlo si es que no está en la
literatura; si sí está, hay que revisar si es una fuente real."*

**Verificación hecha** (`scripts/verify_sources.py` → `evidence/fuentes_verificadas.json`):

| Fuente | Estado | Confirma |
|---|---|---|
| Momentum theory (actuator disk) | **VERIFICADA** | `induced velocity`, `actuator disk`, `thrust` |
| Quadcopter (vuelo en avance) | **VERIFICADA** | `tilt`, `forward`, `pitch` |
| Blade element momentum theory | **VERIFICADA** | `blade element`, `momentum`, `thrust` |
| Drag coefficient | **VERIFICADA** | `drag coefficient`, `frontal area` |
| API de OpenFOAM (`actuationDiskSource`) | **PARCIAL** | `Froude`, `upstreamPoint` |
| Documentación OpenFOAM del disco actuador | **NO ACCESIBLE** (404) | — |

**Conclusión honesta:**

1. **El ángulo NO está tabulado en la literatura** para estos modelos: **hay que calcularlo**,
   como estamos haciendo. La relación `tan θ = D/W` es física elemental, no un dato a citar.
2. Lo que sí es literatura es la **forma de calcular el arrastre** (`D = ½ρCdAV²`) y la
   **teoría de disco**. Ambas verificadas.
3. **Las 4 fuentes verificadas son enciclopedias (Wikipedia): terciarias.** Son reales y
   accesibles, pero **para el paper hacen falta fuentes primarias** (Leishman, *Principles of
   Helicopter Aerodynamics*; Prouty; y para multirrotores en avance, la literatura de
   BEMT aplicada). **Pendiente para la fase de redacción.**
4. **No se atribuye a ninguna fuente el valor de `Cd = 0.8`**: es suposición mía, declarada
   como tal. Citarlo como literatura sería una cita falsa.

---

## 4. Cómo se verifica cada cosa

| Nivel | Qué verifica | Herramienta | Estado |
|---|---|---|---|
| Estructura | Que los ficheros y campos existan | `verify_case_suite.py` | ✅ 128/128 |
| Ejecutabilidad | Que OpenFOAM corra el caso | `gate_cfd0.sh` | ⚠️ **bloqueado (bug #6)** |
| Física del modelo | Que el disco genere empuje | `test_axial_source.sh` | ✅ **refuta el modelo actual** |
| Fuentes | Que la literatura exista | `verify_sources.py` | ✅ 4/6 |
| Medición | Que los datos tengan incertidumbre | `audit_measurement_csv.py` | ✅ 8/8 autotest |

---

## 5. Organización del repositorio

```
context.md                       Encargo original del proyecto (57 secciones)
PROJECT_MASTER_PLAN_V1.md        Plan operativo unificado
research_log.md                  Diario de investigación — 17 entradas, con correcciones
COMO_SE_CALCULA.md               ESTE DOCUMENTO — registro de suposiciones y cálculo

docs/specs/                      Fichas de los 4 UAV (P, con fuente)
geometry/
  protocolo_geometria.md         Protocolo de medición + gates 1A/1B/CFD-0
  coaxial_thrust_split.md        Análisis del reparto coaxial (suposición [3])
  presupuesto_hipotesis.md       Marco de idealizaciones + texto para el paper
  models/T100_CFD/               MODELO REAL MEDIDO del T100 (clase M)
  manifests/                     Manifiestos con procedencia por campo
evidence/
  CONFLICTS.md                   Registro único de conflictos documentales
  BUG_conceptual_06_*.md         El bloqueo activo del CFD
  VALIDACION_modelo_T100.md      Auditoría del modelo medido
  DATOS_Y_ACTITUD_T100.md        Correcciones del propietario + actitud
  fuentes_verificadas.json       Fuentes comprobadas
data/processed/
  dronewith.sqlite               Base de datos (capa analítica poblada; cfd_* vacías a propósito)
scripts/                         Todo el código, ejecutable y reproducible
```

### Documentos **archivados** (superados, se conservan por trazabilidad)

| Fichero | Motivo |
|---|---|
| `RESEARCH_ARCHITECTURE_V1.md` (raíz) | Contenía especificaciones **no verificadas** (masas, rotores) que contradicen las fichas. Superado por `research/` + `docs/specs/` |
| `research/specifications/dji_agras_engineering_specs.md` | Sustituido por los manifiestos con procedencia por campo |
| `geometry/hoja_de_campo.md` | Sustituido por el modelo real medido del T100 |
| `geometry/campana_T25P.md` | Campaña de medición: ya no aplica al T100, que está medido |
| `geometry/COMO_EJECUTAR_CFD0.md` | Procedimiento operativo; se conserva pero no es documento de investigación |

---

## 6. Estado del proyecto

| Gate | Qué lo cierra | Estado |
|---|---|---|
| **1A (T100)** | geometría medida, sin `D` críticos | ✅ **cerrable** (falta formalizar) |
| **1A (T25P/T55/T70P)** | medición física | ⬜ pendiente |
| **1B** | RPM real y reparto de empuje | ⚠️ parcial (RPM declarado sin fuente) |
| **CFD-0** | un caso ejecutado de punta a punta | ❌ **bloqueado: bug conceptual #6** |
| **CFD-suite** | 128 casos | ⬜ requiere CFD-0 |
| **Lagrangiano** | deposición D(x,y) | ⬜ requiere CFD-suite |

**El bloqueo activo no es la geometría —que ya está medida— sino que
`actuationDiskSource` no impone el empuje.** Detalle en `evidence/BUG_conceptual_06_actuationDisk.md`.

---

## 7. Lo que necesito del investigador para seguir

| # | Necesidad | Para qué | Coste |
|---|---|---|---|
| **1** | **Medir la actitud real** a 3/5/8/10/15/20 m/s | Cerrar la suposición [1], que tiene un factor 4 de impacto | **Bajo** (telemetría o vídeo) |
| **2** | **Fuente del rpm = 1850**, o medición con tacómetro | Cerrar la suposición [2]; toda la cadena de RPM cuelga de ahí | Bajo/Medio |
| **3** | Confirmar si el par coaxial comparte motor o son **dos independientes** | Cerrar la suposición [3] | Inspección visual |
| **4** | Medir la **pala**: cuerda raíz/punta, twist, perfil | Habilita el RPM por teoría de pala (suposición [4]) | Medio |
| **5** | Posición real del **CG** a distintos estados de carga | Cerrar la suposición [6] y habilitar H5 | Medio |

---

*Documento generado a partir de `scripts/force_chain.py`, verificable y reproducible.
Toda suposición está declarada con su clase y su vía de validación. Nada se atribuye a una
fuente que no haya sido comprobada.*
