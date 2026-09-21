# Datos y actitud — correcciones y adiciones (2026-09-19)

Recoge las aclaraciones del propietario y el **modelo de actitud**, que es nuevo y no estaba.

---

## 1. Correcciones a mis valores

| Parámetro | Yo tenía | Correcto | Clase |
|---|---|---|---|
| **Empuje máximo** | "nominal 214.5 N/rotor" | **82 kg por brazo = 804.15 N/brazo** → 4 brazos = **328 kg** total | P-A |
| **Peso sin líquido** | — | **73 kg** (con batería, 2 boquillas) | O |
| **Carga útil** | 100 kg | **100 kg / 100 L** | P |
| **Espectro de gota** | rango 10–500 µm | **2 boquillas: 50–500 µm · 4 boquillas: 10–500 µm** | O |
| **Velocidad** | 2–13 m/s | **1–20 m/s** | O |
| **Caudal** | 30/40 L/min | **30 L/min (2 boq.) · 40 L/min (4 boq.)** | O |
| **Motor T100 y T70P** | 155×16 / 155×22 | **ambos 155×16 mm**; designación "15516/60KV" | O |
| **KV** | 60 rpm/V | **60 rpm/V** | P |

**Relación empuje/peso real:** `3216.6 N / 1716.8 N = **1.874**`.
Mi "214.5 N" era el empuje **requerido en hover** (MTOW/8 rotores), no el **disponible**.
La confusión importa: el disponible determina el **margen de control** y la **actitud máxima**.

---

## 2. Incertidumbre declarada (nueva)

| Concepto | Valor | Nota |
|---|---|---|
| **Incertidumbre del instrumento** | **±0.2** | declarada por el propietario |
| **Resolución** | **0.1** | |
| **Método** | **flexómetro**, plomadas imperfectas | declarado honestamente |

> **Registro honesto del propietario:** *"el error de medición puede ser debido a que no fue muy
> exacto, lo hice con flexómetro y por ahí algunas mediciones fueron no tan bien plomadas"*.

Eso explica la **diferencia constante de +0.025 m** en la X de los atomizadores entre el JSON
(−0.875/−0.775) y el valor comunicado antes (−0.9/−0.8). **Con ±0.2 declarado, 0.025 m está dentro
de la incertidumbre** → deja de ser una discrepancia de origen y pasa a ser **dispersión normal
del método**. Se adopta el valor del JSON y se anota la diferencia.

**Clasificación:** los valores pasan a **`M` con incertidumbre ±0.2 y resolución 0.1**.
No son `M±0.005` como pedía el protocolo para las cotas críticas, pero **sí son medición**,
con su incertidumbre declarada. Eso es exactamente lo que el protocolo exige: un valor `M`
**con su incertidumbre**. El protocolo pedía ±5 mm para cotas críticas; se cumple con ±200 mm
**no**, así que se registra como `M` de precisión limitada y se declara la limitación.

---

## 3. MODELO DE ACTITUD — nuevo, y era un hueco importante

`scripts/tilt_model.py`

### 3.1 Por qué es necesario

1. En vuelo nivelado el dron **cabecea** para generar empuje hacia adelante. El disco gira con él,
   así que **la normal del disco deja de ser vertical** → el downwash deja de ser vertical.
2. **Peor:** los atomizadores del T100 son **centrífugos** — expulsan el líquido en un **plano
   horizontal respecto al dron**. Si el dron cabecea θ, ese plano se inclina θ y **la proyección
   sobre el suelo se desplaza hacia atrás**.

### 3.2 Modelo

```
Vertical:    T cos θ = W
Horizontal:  T sin θ = D(V)
⇒            tan θ = D(V) / W
             D(V) = ½ ρ Cd A_frontal V²
Actitud máxima:  cos θ_max = W / T_max   →  θ_max = 57.7°
```

### 3.3 Resultados a MTOW (175 kg)

| V (m/s) | D (N) | θ (°) | T requerido (N) | Desplazamiento del abanico (h=2.55 m) |
|---|---|---|---|---|
| 2 | 3.2 | 0.11 | 1716.8 | 0.005 m |
| 5 | 20.3 | 0.68 | 1716.9 | 0.030 m |
| 10 | 81.0 | 2.70 | 1718.7 | 0.120 m |
| 13 | 136.9 | 4.56 | 1722.2 | 0.204 m |
| 15 | 182.3 | 6.06 | 1726.4 | 0.271 m |
| **20** | **324.1** | **10.69** | **1747.1** | **0.482 m** |

**A 20 m/s el abanico se desplaza ~0.48 m hacia atrás solo por actitud.** Frente a anchos de
trabajo de 5–13 m, eso es un **sesgo del 4–10 %**, sistemático y predecible — **distinto del viento**
(que aquí es 0 por alcance del estudio).

### 3.4 También depende de la carga — y conecta con H5

| Masa | θ a 20 m/s | Margen de empuje |
|---|---|---|
| 175 kg (lleno) | 10.69° | 84 % |
| 125 kg (medio) | 14.80° | 154 % |
| 73 kg (vacío) | 24.35° | 309 % |

**A tanque vacío el dron cabecea más del doble que lleno**, a la misma velocidad. Es un acoplamiento
directo entre la carga (H5) y la actitud → **y la actitud afecta a la deposición**. Eso es una
hipótesis nueva y medible:

> **H8 (nueva):** la deposición cambia durante el vaciado del tanque no solo por el cambio de
> empuje/downwash, sino porque **la actitud necesaria para la misma velocidad aumenta** al
> reducirse la masa, desplazando el abanico de los atomizadores centrífugos.

### 3.5 Limitación importante del modelo

**`Cd` y `A_frontal` son estimaciones mías (clase E)**, no medidas. La sensibilidad es grande:

| Cd · A | θ a 20 m/s |
|---|---|
| 0.6 × 1.04 | 4.9° |
| 0.8 × 1.73 | 10.7° |
| 1.0 × 2.42 | 18.3° |

**Un factor 4.** Por tanto:

- la actitud debe entrar al CFD **como parámetro**, no como valor fijo;
- **medirla es barato y de alto valor**: la telemetría del Agras reporta actitud, o un vídeo
  lateral con referencia permite estimarla en hover y en avance a 5/10/15/20 m/s.

### 3.6 Efecto adicional no incluido: arrastre de las hélices

El modelo trata el dron como un cuerpo con Cd fijo. En realidad, en avance las hélices ven un flujo,
asimétrico (lado que avanza / lado que retrocede) que **añade resistencia y consume potencia**.
Ese término **no está incluido**. Es una limitación declarada, y una razón más para medir la actitud
en lugar de confiar en el modelo.

---

## 4. Estado tras estas correcciones

| Elemento | Estado |
|---|---|
| Geometría T100 | ✅ medida (STL + JSON), clasificación `M` ±0.2 res 0.1 |
| **Actitud** | ⚠️ **modelo analítico nuevo**, con `Cd·A` sin medir — requiere medición |
| Reparto de empuje coaxial | ❌ sigue en `D`: el empuje por brazo es conocido, el reparto no |
| Fuente de momento CFD | ❌ **bloqueo activo** (bug #6) |
| Tablas `cfd_*` | ❌ vacías, correctamente |

**Pregunta que sube de prioridad:** además de la actitud, sigue abierta la del **reparto de empuje
entre rotor superior e inferior** del par coaxial. El dato de 82 kg es **por brazo**, no por rotor.
