# Bug #7 (candidato) — normalización de `vectorSemiImplicitSource`

**Fecha:** 2026-09-19 · **Estado:** mecanismo CONFIRMADO por medida; impacto en el caso real ABIERTO
**Origen:** objeción externa al agente, verificada contra el código de v2412 y contra un caso controlado

---

## La objeción

El agente escribía:

```text
Su = F_aire / V_zone
volumeMode absolute
```

Se objetó que eso **no** es coherente con la semántica de `SemiImplicitSource`: que `absolute`
significa "cantidad total" y que v2412 **divide internamente por el volumen seleccionado**, de modo
que esa combinación dividiría por el volumen **dos veces**, aplicando un factor `1/V_zone` de más.

---

## Lo que dice el código de v2412

`src/fvOptions/cellSetOption/cellSetOption.C`:

```cpp
void Foam::fv::cellSetOption::setVol()
{
    scalar sumVol = 0;
    for (const label celli : cells_) { sumVol += mesh_.V()[celli]; }
    reduce(sumVol, sumOp<scalar>());
    V_ = sumVol;                       // V_ = volumen TOTAL de las celdas seleccionadas
}
```

`src/fvOptions/sources/general/semiImplicitSource/SemiImplicitSource.C`:

```cpp
volumeMode_ = volumeModeTypeNames_.get("volumeMode", coeffs_);
if (volumeMode_ == vmAbsolute) { VDash_ = V_; }        // SOLO en absolute
...
const dimensioned<Type> SuValue("Su", SuDims, iter2.val()->value(tmVal)/VDash_);
```

**La objeción es correcta en el mecanismo:** `absolute` divide por `V_zone`; `specific` no.

---

## La cadena dimensional, que corrige la formulación propuesta

Se propuso que la fuente coherente sería

```text
specific:  S_U = F / (rho * V_zone)
absolute:  S_U = F / rho
```

**Eso no cierra dimensionalmente.** En `simpleFoam`/`pimpleFoam` la ecuación de momento es
**cinemática**:

```cpp
fvm::div(phi, U)          // dimensiones  [0 2 -2 0 0 0 0]  = volumen*velocidad/tiempo
```

y `fvOptions` calcula las dimensiones de `Su` como

```cpp
const dimensionSet SuDims(eqn.dimensions()/dimVolume);   // [0 -1 -2 0 0 0 0]
```

es decir **aceleración por unidad de volumen**, no fuerza por unidad de masa. En un solver
incompresible **`rho` no aparece en la ecuación**: la densidad ya está implícita en las unidades.
La cadena correcta es

```text
F [N]  ->  F/V_zone [N/m³]  ->  Su
```

sin `rho`. Introducirlo daría un factor `1/rho ~ 0.85` de más.

Además, la fuerza por celda sí es `Su·V_c`: el propio `fvm::SuSp` multiplica por el volumen
(`mat.source() -= domain*susp.value()*fld...`), y `fvm::Su` también (`mat.source() += domain*susp`).

---

## La medición controlada

`scripts/calibrate_semiimplicit.py` — caso de 4 m³, `rho = 1`, sin relajación, comparando las
cuatro combinaciones de (densidad vs fuerza total) × (absolute vs specific):

| caso | modo | `su` | F medida (u.a.) | F/su |
|---|---|---|---|---|
| A | absolute | 1.00e-2 | 1.63e-6 | 1.63e-4 |
| B | specific | 1.00e-2 | 6.52e-6 | 6.52e-4 |
| C | absolute | 4.00e-2 | 6.52e-6 | 1.63e-4 |
| D | specific | 4.00e-2 | 2.61e-5 | 6.52e-4 |

**Resultado robusto e independiente de la magnitud:** el cociente entre el mismo `su` en `specific`
y en `absolute` es **exactamente 4.0 = V_zone** en las dos parejas (A/B y C/D). El factor de escala
de cada modo es constante, así que `absolute` **sí** divide por el volumen de la zona. Mecanismo
confirmado, derivado del código y reproducido por medida.

### Dos intentos de medida descartados, y por qué

1. **Conducto cerrado con fuerza uniforme, midiendo presión en las paredes.** Mal planteado: en un
   dominio cerrado la fuerza se equilibra contra un gradiente de presión, y ese equilibrio exige
   que la fuerza esté **ausente** en alguna parte del circuito cerrado. Con `f` uniforme en todo el
   dominio la presión queda constante y no hay estado estacionario real. Un test mal planteado
   también converge: los residuos bajaron a ~1e-16 porque el campo era trivial.
2. **`simpleFoam` para medir la aceleración inicial.** Con `consistent yes` el solver resuelve la
   ecuación **estacionaria**, no acumula `dU/dt`, así que lo medido no era `F/(rho V)` sino la
   respuesta amortiguada del solver. Se cambió a `pimpleFoam` (transitorio).

Los valores absolutos del test siguen siendo poco fiables (el campo se satura en lugar de acelerar
libremente), y **se declaran como tales**. Lo que el test establece con solidez es el **factor
relativo entre modos**, que es justo lo que estaba en discusión.

---

## Corrección aplicada

El generador pasa a `volumeMode specific`, con el valor del diccionario = densidad volumétrica
`F/V_zone` **sin renormalización alguna**:

```text
volumeMode      specific;
sources         { U ((F_x/V_zone  F_y/V_zone  F_z/V_zone) 0); }
```

Motivo: `specific` elimina la división por `V_zone` de la cadena, de modo que el resultado deja de
depender de que el volumen declarado coincida exactamente con el de la malla. Menos piezas móviles
para el mismo resultado físico. `verify_prescribed_force.py` ahora **exige** `specific` y falla si
encuentra `absolute`.

**Nota sobre el signo de la corrección:** con `absolute` el valor correcto habría sido `Su = F_aire`
directamente (no `F/V_zone`). Es decir, el agente tenía **un** error real en la combinación
(valor de densidad × modo absoluto), aunque por una razón distinta de la objetada: no era una doble
división, sino una división de más. El efecto neto es el mismo factor `1/V_zone`.

---

## Lo que sigue ABIERTO, y no se cierra por decreto

Que el generador escriba el valor correcto **no demuestra que el solver aplique la fuerza
correcta**. Queda pendiente:

1. **Balance global de momento** en el caso real, con la fuente contabilizada aparte:
   `F_source + F_fronteras − ∫ rho U (U·n) dA ≈ 0`. Es la condición 2 de GATE CFD-0.
2. **Convergencia de magnitudes físicas**, no de residuos: `F_suelo`, `U_z` en el eje, `m_dot` en
   fronteras. La corrida de 800 iteraciones daba `F_suelo = −2725 N` frente a `T = 509 N`; por
   balance de momento en estado estacionario debería ser `+509 N`, así que esa corrida **no estaba
   convergida**. Nota: 2725 N sobre un suelo de 400 m² son solo 6.8 Pa de presión media, así que
   una discrepancia grande en newtons puede ser pequeña en pascales — como se objetó, la
   comparación correcta es el **balance global**, no una pared aislada.
3. **Independencia de malla y dominio**, con las magnitudes del punto 2 monitorizadas.

> **CFD-0 permanece ABIERTO.** La corrida de 800 iteraciones queda etiquetada como
> **`diagnostic run` — no válida para cerrar CFD-0**.
