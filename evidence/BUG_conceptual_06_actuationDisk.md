# Bug conceptual #6 — `actuationDiskSource` no implementa la arquitectura C→B

**Fecha:** 2026-09-19 · **Estado:** CORREGIDO (fuente prescrita implementada; ver §Corrección al final) · **Impacto:** bloqueaba GATE CFD-0

---

## El hallazgo

`actuationDiskSource` de OpenFOAM, en su **método Froude**, **no aplica un empuje prescrito**.
Calcula el empuje **a partir del flujo incidente axial**:

```
T = 2 ρ A |U_o · n|² a (1−a)

  a = 1 − Cp/Ct
  U_o = velocidad entrante monitorizada (aguas arriba, en `upstreamPoint`)
  n   = diskDir
```

Si el flujo es **perpendicular** al disco (`U_o · n ≈ 0`), entonces **T ≈ 0**,
por muy correctos que sean `Cp`, `Ct`, `diskArea`, las `cellZone` y el solver.

---

## La prueba que lo confirma

`scripts/test_axial_source.sh` — prueba unitaria sobre una **copia temporal** del caso nominal
(el caso real no se modifica). Único cambio: rotar el flujo de entrada de horizontal a vertical.

| Flujo de entrada | `U · n` | `Uz` medido bajo el rotor |
|---|---|---|
| **Horizontal** `(3.108, 0, 0)` — caso nominal | ≈ 0 | **≈ 1×10⁻⁷** (nulo) |
| **Vertical** `(0, 0, −3.108)` — test axial | ≠ 0 | **−0.289 m/s** |

**Con flujo axial aparece downwash; con flujo perpendicular no.** El empuje es función de
`U_o · n`, y sólo de eso.

---

## Por qué esto es grave y no un detalle de implementación

**1. El caso físico del proyecto es precisamente el peor caso posible para este modelo.**

En hover o vuelo nivelado, el flujo axial que entra al disco de un multirrotor es **casi nulo**:
el disco *genera* el flujo, no lo recibe. La configuración normal de `actuationDiskSource` es para
**turbinas eólicas o hélices en avance**, donde el disco opera sobre un flujo incidente que ya
existe. Aquí es al revés:

```
Modelo de OpenFOAM:  flujo incidente  ->  T (calculado)
Nuestro problema:    T prescrito      ->  flujo generado (downwash)
```

**2. Anula el objetivo científico declarado.** El proyecto existe para estudiar el downwash.
Un modelo que da `T ≈ 0` cuando el flujo axial es nulo **no puede reproducir el downwash**,
que es el fenómeno central de todo el estudio.

**3. No es un problema de malla.** La hipótesis inicial (celdas demasiado grandes) era errónea.
Refinar la malla habría dado una representación más fina de una fuerza nula. Se descartó antes
de gastar cómputo, como corresponde.

**4. Rompe la arquitectura C→B que el investigador definió.** La decisión aceptada era:

```
C → Σ T_i + W ≈ 0        equilibrio físico global
C → reparto T_i           por masa, CG y actitud
B → materializa T_i       en cada disco
```

`actuationDiskSource/Froude` **recalcula T a partir del flujo**, de modo que `T_i` deja de ser
una entrada y pasa a ser una salida. La arquitectura no está implementada, por mucho que el
nombre del modelo lo sugiera.

---

## Lo que esto invalida

- ❌ **CFD-0 no se cierra.** El caso corre, converge en 268 iteraciones y escribe resultados,
  pero **la física es nula**. Un caso que converge a un campo sin discos no valida nada.
- ❌ La suite de 128 casos **no se puede escalar** con esta formulación: produciría 128 conjuntos
  de resultados vacíos, correctamente formateados.
- ❌ Cualquier resultado de downwash, trayectorias o deposición obtenido así sería inválido.

---

## Corrección necesaria

Sustituir `actuationDiskSource` por una **fuente de momento explícita** que imponga

```
∫_{V_disk,i}  f  dV  =  T_i        (vectorial, con T_i del equilibrio del UAV)
```

**con independencia del flujo incidente**. Requisitos:

1. **Independiente de `U`**: la fuerza total debe ser `T_i` aunque `U = 0` (hover puro).
2. **Direccional**: `f` alineada con el eje del rotor (`diskDir`), repartida sobre las celdas
   de la `cellZone`.
3. **Vectorial**: cada disco puede tener su propio `T_i` (reparto coaxial superior/inferior).
4. **Verificable**: debe poder comprobarse que la fuerza total aplicada es `T_i`,
   integrando sobre la `cellZone`.

Candidatos a evaluar:
- `fvOptions` de tipo `vectorSemiImplicitSource` con `explicit` **absoluto** (no específico),
  que aplique el vector fuerza total repartido por volumen de celda.
- Un `fvOption` propio (código C++) que lea `T_i` de un diccionario y lo reparta.
- `meanVelocityForce` **no sirve**: aplica una fuerza global sobre todo el dominio, no por disco.

**La elección debe validarse con la misma prueba axial:** si el nuevo modelo da downwash también
en hover (`U_axial = 0`), entonces sí implementa C→B.

---

## Lección de método

Esta cadena de hechos sólo apareció **ejecutando**:

| Paso | Qué reveló |
|---|---|
| `blockMesh` + `checkMesh` | la malla era correcta — **falsa sensación de seguridad** |
| verificación estructural de 128 casos | 128/128 «verificados» — **vacío** |
| primera ejecución del solver | 5 bugs de sintaxis, todos reales |
| solver ya sin errores | convergió, escribió resultados — **y la física era nula** |
| prueba axial controlada | la causa es de **formulación**, no de resolución |

Cada capa de verificación dio un «OK» que no significaba lo que parecía. **Sólo la prueba
física discriminante** —flujo axial sí, flujo perpendicular no— identificó la causa real.

> Un caso que corre sin errores no es un caso correcto. Y una suite que pasa 128 verificaciones
> estructurales no es una suite validada.

---

## Corrección implementada (2026-09-19)

Se sustituyó `actuationDiskSource` por una **fuente de momento prescrita** construida sobre
`vectorSemiImplicitSource` con `volumeMode absolute`. `Su` tiene unidades de N/m³, y tomando

```text
Su_c = F_aire / V_zone          (constante en la zona, F_aire = −T_i)
```

se obtiene, para **cualquier** malla,

```text
integral_{V_zone} Su dV = F_aire/V_zone · sum_c V_c = F_aire
```

> **Nota de corrección durante el diseño.** La primera formulación fue `Su_c = T·V_c/V_zone²`,
> razonando "repartir proporcionalmente al volumen". Es incorrecta: da
> `T · sum(V_c²)/V_zone² ≠ T` salvo que todas las celdas tengan el mismo volumen. El reparto
> por volumen ya lo hace la integración, porque la fuerza total de una celda es `Su·V_c`.
> **Constante es lo correcto, y además lo más simple.** Se detectó antes de escribir nada.

Ficheros:

| Fichero | Papel |
|---|---|
| `scripts/mesh_zone_volumes.py` | `V_zone` real desde la malla, por el teorema de la divergencia |
| `scripts/build_prescribed_momentum.py` | genera `constant/fvOptions` con `Su = F_aire/V_zone` |
| `scripts/verify_prescribed_force.py` | verifica `∫f dV = T_i` y el downwash sobre el campo real |
| `scripts/build_hover_case.py` | construye el caso `U_inf = 0` (prueba discriminante) |
| `scripts/gate_cfd0_hover.sh` | ejecuta la secuencia completa del gate |

**Verificación del cierre geométrico.** `mesh_zone_volumes.py` calcula el volumen total del
dominio y lo compara con la caja envolvente: `1625.520000 m³` en ambos casos, error
`+0.000000 %`, y ninguna celda con `V ≤ 0`. El volumen de cada zona de rotor resulta
`5.2914062504e-01 m³`, que coincide **exactamente** con `π·r²·h = π(0.635)²(0.375)`. El cálculo
de volúmenes es correcto, no aproximado.

**Verificación de la fuerza.** `verify_prescribed_force.py` recalcula `V_zone` de forma
independiente desde la malla (no reutiliza el fichero que usó el generador, para que un error
en ese fichero no pase desapercibido) y comprueba que `Su·V_zone = T_i` en los cuatro rotores,
con discrepancia de volumen `4.7e-12`.

**Lo que aún NO está cerrado.** El gate exige además que aparezca downwash con `U_inf = 0`.
Mientras eso no se mida, la corrección está implementada pero **el gate no está cerrado**.

## Segundo hallazgo, al ejecutar el caso de hover

El primer planteamiento del caso de hover usó `inletOutlet` en `inlet` y `outlet` con
`p = 0` en ambos. Tras 286 iteraciones:

```text
Ux: min = -20.5   max = +37.4   MEDIA = +13.1 m/s
```

La media de `Ux` debe ser **0** por simetría. Un valor de 13 m/s significa que el dominio
estaba actuando como un **canal**: con dos parches de presión fija enfrentados, el caudal de
paso es arbitrario y la fuente de momento lo arrastra. El caso estaba **mal planteado, no mal
resuelto**.

Corrección: cerrar el dominio en x e y con paredes `slip` (preservando la simetría que el canal
rompía), conservar `noSlip` en el suelo, y dejar **una sola** salida de presión en el techo.
No hay par de parches enfrentados y por tanto no hay dirección privilegiada.

**Lección de método, la misma que en el hallazgo original:** el solver convergió, los residuos
bajaron a `1e-5` y escribió resultados. Nada de eso detectó el canal. Lo detectó **comprobar
una propiedad que debía cumplirse por simetría** (`media(Ux) = 0`) y que no se cumplía.
