# Validación del modelo T100 real — entrega del propietario (2026-09-19)

**Archivo:** `geometry/models/T100_CFD/t100_cfd_coordinates.json` (15 754 bytes)
**Generado por:** `scripts/generate_t100_cfd_model.py` (del propietario)
**Auditoría:** `scripts/audit_t100_model.py` — **sin fallos de coherencia**

---

## 1. Lo que este modelo resuelve

Casi todo lo que estaba en `D` (desconocido). Cada valor deja de ser una incógnita:

| Campo | Antes | Ahora | Nota |
|---|---|---|---|
| **Nº de rotores del T100** | `D` — conflicto 8 vs 16 | **8** (4 pares coaxiales) | **cierra C-01** |
| **Separación axial del par (A6)** | `D` | **0.290 m** | parámetro del modelo de empuje |
| **Z de los atomizadores** | `D` | **−0.448 m** | quedan a **2.552 m** sobre el suelo a H=3 m |
| **Centros XYZ de los 8 rotores** | `D` | `(±0.8238, ±0.8238, ±0.1450)` | GATE 1A |
| **Posiciones XYZ de los 4 atomizadores** | X parcial (`O`), Y derivada, Z `D` | completas | 3 de 3 ejes |
| **Sentido de giro de cada rotor** | `D` | por rotor, pares opuestos | |
| **Vectores normales y de empuje** | `D` | `[0,0,+1]` normal, `[0,0,−1]` empuje | |
| **Palas por rotor** | `S` (visual) | **2**, con cuerda media 0.085 m y paso 23 in | |
| **RPM nominal en hover** | `D` (riesgo R1) | **1850 rpm** | ¡GATE 1B parcialmente! |
| **Empuje nominal por rotor** | `E` (estimado) | **214.5 N** | |
| **Empuje máximo por brazo** | ambiguo (82 kg) | **804.15 N** (82.0 kg) | |
| **Radio del brazo / longitud de tubo** | `D` | 0.03 m / 0.885 m, ángulos 45/135/225/315° | |
| **Tren de aterrizaje** | `D` | patines 1.1 × 1.15 m, fondo en z = −0.625 m | |
| **Espectro de gota** | rango 10–500 µm | **D10=50 / D50=150 / D90=300 µm** | recomendado para el Lagrangiano |

---

## 2. Validaciones superadas (todas automáticas, `scripts/audit_t100_model.py`)

### 2.1 Coherencia con la especificación oficial — exacta

```
|X|max = 0.8238   |Y|max = 0.8238
diagonal entre rotores opuestos = 2330.1 mm
vs wheelbase oficial 2330 mm  ->  error +0.00 %
```

**Un error del 0,00 %.** El modelo es coherente con la ficha oficial al milímetro.

### 2.2 La relación geométrica candidata, CONFIRMADA por medición

La relación que dejamos como **candidata** (no como identidad) era:

```
span = D_axis/√2 + diámetro de rotor
```

Con la geometría medida del T100:

```
lado entre ejes adyacentes = 0.8238 · √2 = 1.1650 m
span = 1.1650 + 1.5748 = 2.7398 m
```

frente a las dimensiones oficiales **3220 × 3224 mm**. Diferencia: **+0,48 m**.

⚠ **Matiz importante:** el modelo declara un `modeled_envelope_with_props_mm` distinto del
`unfolded_envelope_with_props_mm`. Es decir, **la envolvente modelada no es el sobre desplegado
oficial**: el modelo no incluye algunos elementos que sí entran en el sobre de DJI. Por tanto
**la relación candidata sigue sin poder validarse con esto** — y ahora sabemos por qué: falta
saber qué incluye exactamente el "desplegado" oficial. Ver §4.

### 2.3 Direcciones de giro coherentes

Cada par coaxial gira en **sentidos opuestos**, verificado por el script:

| Par | Superior | Inferior |
|---|---|---|
| M1 (frontal derecho) | CCW | CW |
| M2 (trasero derecho) | CW | CCW |
| M3 (trasero izquierdo) | CCW | CW |
| M4 (frontal izquierdo) | CW | CCW |

### 2.4 Mi hipótesis del "par extremo" — CONFIRMADA por medición

```
|Y| del modelo : [0.917, 0.4585]
mi hipótesis   : exterior 0.917 / interior 0.4585
[OK] hipótesis del 'par extremo' CONFIRMADA por medición
```

La separación declarada de 1834 mm **es** el par extremo, y el interior queda a 917 mm — **exactamente
la mitad**, como supuse. La hipótesis pasa de `I` a confirmada contra medición.

---

## 3. La única discrepancia detectada — y es sistemática

| | X del propietario (este modelo) | X que me pasaste antes |
|---|---|---|
| Exteriores | **−0.875** | −0.9 |
| Interiores | **−0.775** | −0.8 |

**Diferencia: +0.025 m en las cuatro, constante.** Coincide dentro de mis 3 cm de tolerancia, pero
una diferencia **constante de 25 mm** en las cuatro boquillas apunta a **dos orígenes de X distintos**,
no a un error de medición.

- El JSON declara: *"origen = centro geométrico del chasis en el plano medio de los tubos de los brazos"*
- Tu valor anterior debía referirse a otra referencia (¿borde trasero de la barra? ¿punto de anclaje?)

**No lo resuelvo por mi cuenta.** Pregunta concreta al propietario: **¿respecto a qué referencia
mediste el −0.9 / −0.8 m?** Con eso se reconcilia y queda un único sistema de referencia.

---

## 4. Preguntas abiertas para el propietario

1. **Referencia de X de los atomizadores** (§3). ¿−0.9 respecto a qué?
2. **¿Qué incluye el sobre desplegado oficial de 3220 × 3224 mm** que el modelo no incluye?
   (Esto es lo que impediría cerrar la relación candidata.)
3. **Clasificación y método de los datos.** El JSON **no tiene bloque de metrología**: no declara
   si las coordenadas son medidas con instrumento, estimadas del CAD, o leídas del manual. Sin eso
   **no puedo promoverlas a `M`** aunque parezcan correctas. Necesito: instrumento, método,
   incertidumbre y fecha, al menos para rotores y atomizadores.
4. **Confirmar el RPM de 1850**: ¿es medido en hover, calculado, o del manual? Si es medido, cierra
   **GATE 1B** para el T100.

---

## 5. Estado de los gates tras esta entrega

| Gate | Antes | Ahora |
|---|---|---|
| **1A (T100)** | bloqueado por A9 (8 vs 16) | **desbloqueado en lo geométrico**; pendiente la clasificación de metrología |
| **1B (T100)** | `D` | **parcialmente cubierto** (RPM y empuje nominal declarados; falta confirmar método) |
| **C-01** (8 vs 16 rotores) | abierto | **resuelto: 8 rotores** |
| **C-04** (relación candidata) | abierto | **sigue abierto**, pero ahora con una razón concreta (§2.2) |

---

## 6. Lo que sigue bloqueado — y no es la geometría

**Tener el modelo no es poder simularlo.** El bloqueo activo es
**`evidence/BUG_conceptual_06_actuationDisk.md`**: `actuationDiskSource` calcula el empuje a partir
del flujo incidente axial, y en hover ese flujo es nulo.

El `README` del modelo recomienda precisamente el enfoque que acabamos de demostrar que **no
funciona** para este problema:

```cpp
rotorSources
{
    type            actuationDiskSource;
    diskDir         (0 0 -1);
    Cp              0.0;        // <- OpenFOAM aborta: "Cp must be > 0"
    Ct              0.80;
    diskArea        15.5823;    // <- area agregada de los 8 discos, NO por rotor
}
```

Tres problemas en esas cinco líneas: **`Cp = 0` aborta el solver**, el **área agregada** impide
asignar empuje por rotor (y el reparto coaxial es la incógnita central), y **un solo `cellZone`**
no permite tampoco el reparto. Además, aun corrigiendo eso, el empuje seguiría siendo función de
`U·n`.

**Orden correcto, por tanto:**

```
1. Sustituir actuationDiskSource por una fuente de momento que imponga ∫_V f dV = T_i
2. Validarla con la prueba axial (debe dar downwash con U_axial = 0)
3. Mallar con el STL real y los 8 discos por separado
4. Recién entonces, los casos
```

**No al revés.** Mallar primero solo daría una representación más fina de una fuerza nula.

---

## 7. Lo que este modelo NO cambia

- La capa analítica de la base de datos sigue siendo **analítica**, no CFD.
- Las tablas `cfd_*` siguen **vacías**.
- Ningún valor se promueve a `M` sin el bloque de metrología del §4.3.
- GATE CFD-0 sigue **abierto**.
