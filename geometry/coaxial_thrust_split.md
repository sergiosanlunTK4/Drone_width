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
aeronave no rote. Pero **el equilibrio es GLOBAL, no por pareja**.

### 1.0 Corrección de rigor (2026-09-14)

La primera redacción de este documento afirmaba como restricción del par coaxial:

```
Q_u(ω_u) = Q_l(ω_l)          ← INCORRECTO como restricción universal
```

**Eso es más fuerte de lo que la física justifica.** Un UAV no exige que *cada pareja* coaxial
tenga par neto nulo. Lo que exige, en hover sin aceleración de guiñada, es que la **suma
algebraica** de las reacciones de **todos** los rotores se anule:

```
Σ_i  s_i · Q_i  ≈  0            (s_i = +1 o −1 según el sentido de giro)
```

Entre brazos, el controlador **puede compensar** desequilibrios: un par con par neto no nulo es
perfectamente admisible si otro rotor u otra pareja lo contrarresta. Por tanto **no se sigue** que
`ω_l/ω_u = √(C_Qu/C_Ql)`, y **no se sigue** que el rotor superior tenga que girar más rápido.

El punto de operación real depende de: arquitectura de propulsión, asignación de control (mixing),
`C_T`/`C_Q`, interferencia y condición operacional — **y de la condición de guiñada**.

**Consecuencia para el proyecto:** `A10` (accionamiento del par) es **más importante de lo que
parecía**, porque sin conocer la arquitectura no se sabe siquiera qué restricción aplica. **No se
adopta ninguna partición `T_l/T_u` por defecto**, ni simétrica ni derivada del par.

### 1.1 Lo único que queda firme: la relación condicional

Bajo la hipótesis **explícita y no verificada** de accionamiento independiente **con par neto nulo
por pareja**, se cumpliría:

```
Q_u(ω_u) = Q_l(ω_l)   (hipótesis, no restricción general)
   ⇒  ω_l/ω_u = sqrt( C_Qu / C_Ql )
   ⇒  T_l/T_u = (C_Tl/C_Tu) · (C_Qu/C_Ql)
```

Sirve como **modelo candidato a contrastar**, no como resultado. Predice `T_l/T_u ≠ 1` salvo que
`C_Tl/C_Tu = C_Ql/C_Qu`, y predice `ω_l < ω_u` si `C_Ql > C_Qu`. **Ambas predicciones son
falsables con la medición A11** (RPM de ambos rotores del par, simultáneas) y con la curva de banco
por rotor. Si la medición no las reproduce, la hipótesis se descarta y se documenta (§54).

De teoría de elemento de pala, para referencia:

```
T = C_T ρ A (ωR)²        (C_T ∝ C_l·σ/2  en el régimen de operación)
Q = C_Q ρ A (ωR)² R      (C_Q ∝ C_d·σ/2)
P = Q ω
```

### 1.2 Qué sí es una consecuencia robusta

Independientemente de la arquitectura, el rotor inferior opera en la estela del superior: ve
`v_in,l = v_u + δ·v_i` con `δ ≥ 0`. Eso **degrada su `C_T` y encarece su `C_Q` respecto a un rotor
aislado** — es aerodinámica, no control. Lo que **no** se puede afirmar sin medir es cómo se
reparte esa degradación en `T` y `ω` entre los dos rotores, porque eso ya es asignación de control.

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
| D5d | **RPM de cada rotor del par** en hover real, simultáneamente (2 canales de tacómetro o cámara) | contrastar la hipótesis condicional de §1.1 (`ω_l < ω_u`): si no se cumple, la hipótesis se descarta |
| D5e | **Torque de reacción** de cada uno si es medible | comprobar el reparto real de reacciones entre brazos (§1.0) |
| A10 | **Accionamiento**: nº de motores y ESC por brazo; par solidario o independiente | determina **qué restricción aplica** y si el reparto es siquiera una variable de control |

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

En la práctica:

1. **Primera aproximación declarada:** `T_i = mg/N` para rotores **no coaxiales** (T25P), donde
   el reparto es casi simétrico por geometría. Y **aun así** se contrasta con el CG medido (C5).
2. **Coaxiales (T55, T70P, T100):** **la partición `T_l/T_u` es una incógnita declarada.** No se
   adopta ni `mg/N` por disco ni la partición de §1.1, porque §1.1 es una hipótesis condicionada a
   un accionamiento que no está confirmado. Hasta resolver A10 y medir A11/D5a–D5c:
   - el CFD se corre **con la partición como parámetro**, y
   - se reporta la **sensibilidad** del resultado a ese parámetro.
   Si la campaña demuestra que el reparto es prácticamente simétrico, se documenta como resultado
   y se justifica la simplificación (§54). Si no lo es, la partición medida entra al modelo.

> **Alcance del análisis comparativo A vs B:** sirve para cuantificar si la simplificación por
> disco reproduce la estructura de estela **relevante para los atomizadores** — que es la pregunta
> que importa para H3, no la fidelidad aerodinámica en abstracto.
