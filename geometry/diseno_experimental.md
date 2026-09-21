# Diseño experimental — DOE-A y DOE-B

**Versión:** 1.0 — 2026-09-19
**Decisión del investigador, aceptada:** separar la física del UAV de la ambiental, y no barrer
variables que están algebraicamente ligadas.

---

## 1. Por qué se rediseña

El DOE anterior (128 casos) tenía cinco problemas:

| # | Problema | Consecuencia |
|---|---|---|
| 1 | Rangos **idénticos** para las 4 plataformas | Ignoraba que cada UAV tiene su envolvente |
| 2 | `Platform` y `Atomizers` asignados **al azar** | No era un diseño cruzado |
| 3 | Muestreo por permutación uniforme, no LHS estratificado | Cobertura desigual |
| 4 | **No respetaba las restricciones de masa/batería** | Casos físicamente imposibles (T70P con tanque lleno y batería DB1580) |
| 5 | **Mezclaba variables ambientalmente ligadas** | DOE redundante (§4) |

---

## 2. Arquitectura en dos niveles

```
DOE-A  — FÍSICA PRINCIPAL DEL UAV          atmósfera CONSTANTE
         V, H, d, m_liq                    4 variables, 4 plataformas

DOE-B  — AMBIENTAL                          solo DESPUÉS, sobre un SUBCONJUNTO de DOE-A
         T, RH, P, V_viento                 para no multiplicar sin saber qué importa
```

**Razón de fondo:** multiplicar 128 casos por 3 niveles de ambiente daría miles de corridas
**antes de saber qué variables importan**. Primero la física del UAV; el ambiente después, y
solo sobre los casos que hayan resultado informativos.

---

## 3. DOE-A — variables principales

### 3.1 Las cuatro variables

| Variable | Símbolo | Rol | Clase | Por qué |
|---|---|---|---|---|
| Velocidad de vuelo | **V** | entrada | O: 1–20 m/s | cambia resistencia, actitud, tiempo en la estela |
| Altura de aplicación | **H** | entrada | I: 1.5–6 m | cambia tiempo en el downwash, expansión de estela, tiempo de vuelo de la gota, deriva |
| Tamaño de gota | **d** | entrada | P: 50–500 µm (2 boq.) · 10–500 (4 boq.) | cambia el régimen (Stokes / inercial) |
| Masa de carga | **m_liq** | entrada | P: 0–100 kg | cambia empuje requerido, downwash **y actitud** (H5, H8) |

### 3.2 Por qué **no** temperatura

La propuesta inicial incluía temperatura como cuarta variable. **Se retira**, por dos razones:

1. **Sin evaporación, el efecto de T sobre la deposición es de segundo orden**: actúa solo a
   través de `ρ` y `μ` del aire. Cambiar unos grados mueve `ρ` un ~1 %.
2. **La altura hace mucho más**: pasar de 1.5 a 4 m cambia directamente el tiempo dentro del
   downwash, la expansión de la estela, el tiempo de vuelo de la gota, la deriva lateral y el
   área de deposición.

`T`, `RH` y `P` se **fijan** en una atmósfera basal de referencia (§5) y se barren **después**,
en DOE-B.

### 3.3 Orden de prioridad si hubiera que recortar

```
1. V, H, d, m          física principal del UAV
2. V_viento            cambia trayectorias directamente
3. T, RH               efecto de segundo orden sin evaporación
4. P                   para Veracruz y un rango geográfico acotado, varía mucho menos
```

No porque la presión sea irrelevante, sino porque **en un rango geográfico acotado varía menos
que el viento**, y el viento sí cambia las trayectorias. La atmósfera basal usa **presión real**.

---

## 4. ⚠ La trampa: variables algebraicamente ligadas

### 4.1 Tasa, caudal, velocidad y ancho

```
Q = 0.006 · R · V · W
```

**No se pueden barrer simultáneamente** `R`, `Q`, `V` y `W`: al fijar tres, el cuarto queda
determinado. Sería un **DOE redundante**.

**Decisión:** en el DOE se barren `V` (variable física real) y se **fija** la estrategia de
aplicación. `R`, `Q` y `W` se registran como **derivadas**, no como dimensiones del diseño.

### 4.2 Tamaño de gota, RPM del atomizador y caudal

Si el controlador modifica la **RPM del disco** para conseguir cierto **tamaño de gota**, entonces
no son tres variables independientes:

```
configuración de gota   →  COMANDO
RPM del atomizador      →  CONSECUENCIA del comando
caudal                  →  ajuste de bomba, posiblemente ligado
```

**Decisión:** el DOE barre **`d` como comando** (que es lo que el operador configura). La RPM del
atomizador se **registra** como resultado, no se barre.

> **La telemetría real resolverá esto muy rápido:** revelará qué manda el Agras y qué resulta del
> comando. Es una de las razones de más peso para extraerla.

---

## 5. Atmósfera basal de referencia

```
CASO ATMOSFÉRICO BASAL "Veracruz-mañana"
    T_0, RH_0, P_0  →  ρ_0 = f(P_0, T_0, RH_0)
```

**Todos los casos de DOE-A usan ρ_0.** La sensibilidad ambiental se hace después, en DOE-B.

> **Aclaración sobre el debate de la densidad.** No es lo mismo fijar `ρ = 1.1716` *"porque son
> 28 °C"* —donde la temperatura se usa como si bastara para definir la densidad— que declarar un
> **caso atmosférico basal** con `T_0`, `RH_0`, `P_0` y **calcular** `ρ_0` a partir de ellos.
> Lo segundo es perfectamente defendible; lo primero no.

**Valores por confirmar con el investigador** (clase O): `T_0`, `RH_0`, `P_0` reales de la
campaña. Por ahora, como referencia provisional:

| Parámetro | Valor provisional | Clase |
|---|---|---|
| T_0 | 28 °C | E |
| RH_0 | 70 % | E |
| P_0 | 101 325 Pa (nivel del mar) | E |
| **ρ_0** | **1.1572 kg/m³** | derivado |

---

## 6. Restricciones por plataforma

Cada UAV tiene su envolvente. **Esto es lo que hacía mal el DOE anterior.**

### 6.1 Masa y carga — con la restricción de batería

```
m_total(V, H, ...) = m_seca + m_batería + m_líquido

m_líquido ∈ [0, m_tanque]   SUJETO A:   m_seca + m_batería + m_líquido  ≤  MTOW
```

**El caso crítico es el T70P:**

| Batería | Masa con batería | Tanque máx. admisible | ¿Tanque lleno? |
|---|---|---|---|
| DB1580 | 52 kg | **30 kg** (MTOW 102) | ❌ **no cabe** |
| DB2160 | 56 kg | **70 kg** (MTOW 126) | ✅ sí |

> **Consecuencia para el DOE:** el caso "100 % de carga" del T70P **exige batería DB2160**. Con
> DB1580 el máximo es ≈43 % del tanque. Cualquier caso por encima es **físicamente imposible** y
> debe excluirse del diseño.

**Y la carga no es solo masa**: cambia la **actitud** necesaria para la misma velocidad
(`tan θ = D/mg`), y la actitud desplaza el abanico de los atomizadores centrífugos → **H8**.

### 6.2 Rangos por plataforma

| Plataforma | V (m/s) | H (m) | d (µm) | m_líquido (kg) | MTOW (kg) |
|---|---|---|---|---|---|
| **T25P** | 1–20 | 1.5–6 | 50–500 | 0–20 | 53 |
| **T55** | 1–20 | 1.5–6 | 50–500 | 0–50 | 95 / 99 |
| **T70P** | 1–20 | 1.5–6 | 50–500 | **0–70 (solo DB2160)** | 126 |
| **T100** | 1–20 | 1.5–6 | 50–500 (2 boq.) · **10–500 (4 boq.)** | 0–100 | 175 |

> Los rangos de V y H son los **operativos declarados** por el propietario. Los extremos
> (1 m/s y 20 m/s) deben tratarse como **cotas**, no como puntos de operación típicos.

---

## 7. Base de datos de telemetría — grande, pero no toda en el DOE

**Principio (decisión del investigador):**

> **Tener una variable en la base de datos NO obliga a barrerla en CFD.**

Se guarda por vuelo real:

```
{V, H, m, T, RH, P, ρ,
 RPM_R1…RPM_R8,        ← RPM del ROTOR individual
 RPM_atom,             ← RPM del atomizador centrífugo
 RPM_pump,             ← RPM de la bomba
 Q_real, R, d, θ, φ,
 wind, timestamp}
```

Y se eligen **solo cuatro** para el primer DOE. La base grande permite después **descubrir
correlaciones** y diseñar DOE nuevos — que es justo lo que no se puede hacer si se descartan
columnas al capturar.

### 7.0 Disponibilidad CONFIRMADA (2026-09-19)

| Campo | Disponible | Cierra |
|---|---|---|
| **RPM de motor individual** (los 8) | ✅ **sí** | la incógnita del reparto coaxial s_i |
| **RPM del atomizador centrífugo** | ✅ **sí** | comando vs consecuencia del tamaño de gota (§4.2) |
| **RPM de las bombas** | ✅ **sí** | relación bomba ↔ caudal |
| **Caudal real Q** | ✅ **sí** | W_commanded y contraste del DOE (§8) |
| **Actitud θ, φ** | ❓ por confirmar | suposiciones [1] y [3] |

> **Esto cambia el DOE:** el RPM de motor individual convierte s_i de **parámetro** en
> **medición**. El barrido 0.5/0.6/0.7 **no se usa** si la telemetría da el reparto real.

### 7.1 Sincronización

Todo por **timestamp**, para poder cruzar variables. Sin sincronía, la telemetría es una lista de
números sin relación.

### 7.2 Por qué la telemetría cambia el proyecto

Si están disponibles `RPM_rotor`, `RPM_atom`, `RPM_pump`, `Q`, `θ`, `φ`, **`m`** y **`V`**, entonces:

> **No se calcula lo que se puede medir.**

- El **RPM real** cierra GATE 1B directamente, en lugar de deducirlo del empuje (que es
  precisamente el error circular que se eliminó en la Metodología §5.1).
- La **actitud real** cierra las suposiciones de `Cd` y área frontal, que hoy tienen un factor 4
  de impacto.
- El **caudal real** permite contrastar `Q_calculado = 0.006 R V W` contra `Q_telemetría`.

---

## 8. Los cuatro anchos — el resultado científico más prometedor

| Ancho | Qué es | Cómo se obtiene | Estado |
|---|---|---|---|
| **W_commanded** | el que el **caudal** implica | `Q_real / (0.006 R V)` | derivable; requiere telemetría |
| **W_DJI** | el configurado en el controlador | lectura de pantalla | **P: 5–13 m** (y *"depende de la escena"*) |
| **W_aero** | abanico físico de los atomizadores | Lagrangiano **sin** plano receptor | pendiente: requiere CFD |
| **W_deposition** | ancho efectivo real | derivado de **D(x,y)** | **objetivo científico** |

> **La diferencia entre los tres primeros y el cuarto es, probablemente, uno de los resultados más
> valiosos de la investigación:** cuantifica cuánto se desvía la práctica operativa (caudal y
> configuración) de la física real de deposición.

Y el propio fabricante reconoce que el ancho no es único: DJI declara **5–13 m para el T100** y
aclara explícitamente que **depende de la escena real de trabajo** ([1]).

**Contraste previsto:** `Q_calculado` vs `Q_telemetría`. Si coinciden razonablemente, se valida
nuestra interpretación de las variables operacionales.

---

## 9. Verificación de la relación caudal-ancho

Derivada, no citada:

```
En 1 s el dron recorre V m  →  cubre V·W m² = V·W/10000 ha
Volumen por minuto = 60 R V W / 10000  [L/min]
    ⇒   Q = 0.006 R V W            (Q en L/min, R en L/ha, V en m/s, W en m)
    ⇒   W_commanded = Q / (0.006 R V)
```

**Verificación con el ejemplo del investigador** (R = 10 L/ha, V = 10 m/s, W = 6 m):

```
Q = 0.006 × 10 × 10 × 6 = 3.6000 L/min     ✓
```

**Qué revela la inversión** (a R = 10 L/ha, V = 10 m/s):

| Q (L/min) | Caso | W implícito |
|---|---|---|
| 3.6 | ejemplo | 6.00 m |
| 16 | caudal T50 (referencia) | 26.7 m |
| **30** | **T100 máx. 2 boquillas** | **50.0 m** |
| **40** | **T100 máx. 4 boquillas** | **66.7 m** |

Los máximos de bomba implican anchos absurdos **a esa tasa y velocidad** — lo que significa que la
operación real usa **otras combinaciones de (R, V)**. Es exactamente la información que la
telemetría revelará.

---

## 10. Estado

| Elemento | Estado |
|---|---|
| DOE-A (4 variables, 4 plataformas) | ✅ **diseñado** |
| Restricciones de masa/batería | ✅ **incorporadas** |
| Trampas de redundancia | ✅ **identificadas** |
| Atmósfera basal ρ_0 = f(P,T,RH) | ✅ método definido; **valores por confirmar** (clase O) |
| DOE-B (ambiental) | ⬜ diseñado **después** de DOE-A |
| Telemetría | ⬜ **pendiente de confirmar disponibilidad y permisos** |
| CFD | ❌ **bloqueado: bug #6** (fuente de momento) |

---

## 11. Lo que necesito

| # | Necesidad | Para qué |
|---|---|---|
| **1** | **Confirmar la telemetría disponible** (qué campos exactamente) y su **permiso de uso** | Cierra GATE 1B, la actitud y la validación del DOE sin deducir nada |
| **2** | `T_0`, `RH_0`, `P_0` reales de la campaña | Fija la atmósfera basal con datos, no con estimaciones |
| **3** | Rangos de `V` y `H` **de aplicación** (no de traslado) | Los actuales son cotas, no operación típica |
| **4** | Confirmar qué **manda** el Agras y qué **resulta** del comando | Resuelve la redundancia §4.2 |

---

## Referencias

| Ref | Fuente |
|---|---|
| [1] | DJI AGRAS T100 — Specs. https://ag.dji.com/t100/specs |

*Diseño experimental. Ninguna corrida ejecutada. El bloqueo activo es la fuente de momento
prescrita (`evidence/BUG_conceptual_06_actuationDisk.md`).*
