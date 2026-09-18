# Reparto de empuje en el par coaxial — análisis y plan de medición

**Estado:** `ABIERTO`. Es un punto ciego del modelo de actuator disk coaxial (GATE 1B).
**Motivo:** en un par coaxial, igualar el empuje entre rotor superior e inferior (`T_i = mg/N`)
**no está justificado**. El rotor inferior opera en la estela del superior, con velocidad de
entrada mayor y ángulo de ataque efectivo menor: para el mismo régimen entrega **menos empuje**
y **más potencia inducida**. Cuánto menos es una cantidad medible, no una suposición.

Formalmente, el rotor inferior ve una velocidad inducida `v_u + δv_i`, no `v_i`; tratar el par
como dos discos independientes cada uno con `mg/N` **sobrestima** el empuje del disco inferior
y **subestima** el descenso total, justo en la región donde están los atomizadores.

---

## 1. De dónde sale la partición: no del empuje, sino del par

La restricción física real de un par coaxial **no es** que los empujes sean iguales: es que la
aeronave no rote. El reparto surge del **equilibrio de momento angular y del par motor
disponible**, no de un reparto simétrico asumido.

Con rotor superior `u` e inferior `l`, siendo `Q` el par de reacción sobre el aire:

```
Q_u(ω_u) = Q_l(ω_l)                     (par neto nulo sobre el brazo)
```

De teoría de elemento de pala:

```
T = C_T ρ A (ωR)²        (C_T ∝ C_l·σ/2  en el régimen de operación)
Q = C_Q ρ A (ωR)² R      (C_Q ∝ C_d·σ/2)
P = Q ω
```

**Sustituyendo el equilibrio de par:**

```
C_Ql ρ A (ω_l R)² R = C_Qu ρ A (ω_u R)² R
        ⇒  ω_l / ω_u = sqrt( C_Qu / C_Ql )
        ⇒  T_l / T_u = (C_Tl / C_Tu) · (ω_l / ω_u)²
        ⇒  T_l / T_u = (C_Tl / C_Tu) · (C_Qu / C_Ql)
```

**Lectura del resultado:** el reparto de empuje del par depende de la **razón de coeficientes**
del rotor inferior y superior — es decir, del grado de interferencia — y **no** de una simetría.
Solo si `C_Tl/C_Tu = C_Ql/C_Qu` el reparto sería igual a 1. Nada garantiza eso en un coaxial real.

### 1.1 Consecuencia operativa sobre las RPM

`ω_l/ω_u = sqrt(C_Qu/C_Ql)`. En un coaxial típico `C_Ql > C_Qu` (el inferior arrastra más porque
trabaja en flujo acelerado con pérdidas), luego `ω_l < ω_u`. Es decir:

> **El rotor superior debe girar más rápido que el inferior para que el par neto sea nulo.**

Esto es coherente con la práctica de rotores coaxiales, y es medible.

---

## 2. Modelo de interferencia del rotor inferior

Para el actuator disk del rotor inferior, la velocidad de entrada no es la del aire libre sino la
del flujo del rotor superior más un déficit:

```
v_in,l = v_u + δ·v_i        con 0 ≤ δ ≤ 1
```

`δ` (o de forma equivalente el factor de interferencia) **no se toma de la literatura sin
verificarlo**: se determina de la medición. Solo con `δ = 0` el par se comporta como dos rotores
aislados, y ese es precisamente el supuesto que hay que refutar o confirmar.

### 2.1 Eficiencia del par coaxial (figura de mérito)

```
FM_coaxial = T_total / (2 · P_ideal_par)
```

Si `FM_coaxial` para el mismo empuje total es de la misma calidad que un rotor aislado, el modelo
de dos discos independientes con `mg/N` es defendible; si el par pierde eficiencia, el reparto
asimétrico es obligatorio y debe entrar al modelo.

### 2.2 Sensibilidad a la separación axial

`T_l/T_u` depende de la **separación axial del par** (campo `separacion_axial_par` del protocolo
§3), porque de ella depende cuánto se ha contraído y acelerado la estela antes de entrar al
disco inferior. Por eso la separación axial **no es una cota decorativa**: es un parámetro del
modelo de empuje. Justifica por sí sola la prioridad del ítem **A6**.

---

## 3. Incógnita de accionamiento (resolver en la inspección física)

La derivación de §1 supone que **ω_u y ω_l pueden ser distintas**. Hay que confirmar cuál es el
caso real, porque cambia el modelo:

| Caso | Configuración | Consecuencia |
|---|---|---|
| **I. Par mecánicamente acoplado** (un motor, dos rotores en el mismo eje) | ω_u = ω_l forzado | El reparto lo fija **solo la aerodinámica**; aparece un par neto residual que el control compensa entre brazos |
| **II. Dos motores independientes** (2 ESC por brazo) | ω_u ≠ ω_l permite equilibrar par y reparto | El reparto es una **variable de control**, no una constante; el flight controller decide |
| **III. Un ESC por brazo con dos motores en serie** | ω_u = ω_l típicamente | Igual que I |

**El deck de DJI Academy no declara el caso.** Solo documenta "Hélices duales coaxiales" y una
corriente de pico de ESC de 370 A para el T100. Por tanto, **no se puede asumir ninguno de los tres.**

> **Ítem de inspección nuevo (A10):** contar motores y ESC por brazo y determinar si el par es
> solidario o independiente. Sin esto, el modelo de empuje del coaxial no está definido.

---

## 4. Lo que hay que medir (se integra en el bloque D)

| # | Medición | Para qué |
|---|---|---|
| D5a | Curva **empuje–RPM–torque–corriente** del rotor **superior aislado** | obtener `C_Tu`, `C_Qu` |
| D5b | Curva **empuje–RPM–torque–corriente** del rotor **inferior aislado** | obtener `C_Tl`, `C_Ql` (aislado ≠ en el par: sirve de referencia) |
| D5c | Curva del **par coaxial completo**, barriendo **separación axial** si la bancada lo permite | cuantificar la interferencia y la pérdida de eficiencia del par |
| D5d | **RPM de cada rotor del par** en hover real, simultáneamente (2 canales de tacómetro o cámara) | dimensionar el reparto: `ω_l/ω_u` |
| D5e | **Torque de reacción** de cada uno si es medible | verificar el equilibrio de par de §1 |
| A10 | **Accionamiento**: nº de motores y ESC por brazo; par solidario o independiente | definir cuál de los casos de §3 aplica |

**Regla contable:** no registrar nunca "empuje del brazo" como un solo número. Registrar
`T_superior` y `T_inferior`, cada uno con `method`, `instrument`, `uncertainty` y timestamp,
porque son las dos incógnitas del modelo.

---

## 5. Impacto en la arquitectura CFD (resuelto: C → B)

Decisión adoptada:

> **Modelo principal = actuator disk con empuje prescrito (B), con la condición física impuesta
> por masa, CG y actitud (C).** **Modelo secundario = RPM prescrita (A)** para casos seleccionados,
> cuando existan RPM y geometría de pala suficientemente fiables.

Es decir, **C + B se combinan, no se eligen**:

```
C  →  Σ_i T_i + W ≈ 0            (restricción física global: equilibrio de fuerzas)
C  →  reparto T_i entre rotores  (a partir de masa, CG y actitud)
B  →  materializa T_i en cada disco del solver
A  →  casos selectos: ¿reproduce el disco la estructura de estela que ven los atomizadores?
```

Y el reparto `T_i` **no se toma como `mg/N`**:

```
T_i = T(uav, configuración del par, masa total, CG, actitud, ρ)
```

con la partición superior/inferior según §1. En la práctica:

1. **Primera aproximación declarada:** `T_i = mg/N` para rotores **no coaxiales** (T25P), donde
   el reparto sí es casi simétrico. Y **aun así** se contrasta con el CG medido (C5).
2. **Coaxiales (T55, T70P, T100):** reparto asimétrico según §1, determinado por `C_T`, `C_Q` y `δ`.
   Nada de `mg/N` por defecto — **hay que demostrarlo**, y si la campaña demuestra que el reparto
   es prácticamente simétrico, se documenta como resultado y se justifica la simplificación (§54).

> **Alcance del análisis comparativo A vs B:** sirve para cuantificar si la simplificación por
> disco reproduce la estructura de estela **relevante para los atomizadores** — que es la pregunta
> que importa para H3, no la fidelidad aerodinámica en abstracto.
