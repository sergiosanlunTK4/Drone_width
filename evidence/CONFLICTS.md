# Registro de conflictos y evidencia documental

**Propósito:** un único lugar donde vive cada conflicto abierto, con la evidencia citada de
forma verificable (archivo + línea + hash). Según la regla del investigador, **este es el único
documento que se actualiza** ante nueva evidencia documental: `rotor_count` y cualquier otro
campo de los manifiestos **no se tocan automáticamente**, aunque una captura parezca resolverlo.
Se exige convergencia entre **tabla + fotografía/diagrama + inspección física** para promover un
valor a `M`.

**Última actualización:** 2026-09-14

---

## Cómo se cita la evidencia

| Fuente | Identificador |
|---|---|
| Ficha oficial en vivo | `capture:<uav>:<locale>:<sha256[:12]>` → `data/raw/specs_captures/` |
| Payload estructurado | `data/raw/specs_captures/spec_tables.json` |
| PDF capturado por el investigador | `data/raw/<UAV>_ocr.txt` línea N |
| DJI Academy | `data/raw/dji_academy_*.txt` + `data/raw/dji_academy_01_FUENTE.md` |
| Evidencia visual | `data/raw/media/...` + `data/processed/media_inventory.csv` |
| Medición física | `data/raw/mediciones_geometria.csv` (vacío: campaña no ejecutada) |

---

## C-01 · T100 — ¿8 u 16 rotores? **ABIERTO (semántica probada ambigua)**

**Lo que se creía:** que "Cantidad = 8 pares" podía ser un error de OCR o una lectura ambigua.

**Lo que la recaptura demuestra:** la cifra es **literal y exacta**, y el OCR era correcto.

```
{"title":"Sistema de propulsión - Hélices","specs":[
   {"key":"Material",    "value":"Compuesto de fibra de carbono"},
   {"key":"Dimensiones", "value":"62 pulgadas"},
   {"key":"Cantidad",    "value":"8 pares"}]}
```

**Evidencia (recaptura forense 2026-09-14):**

| Plataforma | `Cantidad` en la fila de hélices | Fuente |
|---|---|---|
| **T100** | **`8 pares`** | `spec_tables.json`; PDF `T100_ocr.txt` L66–67 |
| **T55** | **`4 pares`** | `spec_tables.json`; PDF `T55_ocr.txt` L65–66 |
| **T70P** | **`4`** (¡sin la palabra "pares"!) | `spec_tables.json`; PDF tenía el campo en blanco |

**Corrección importante:** el `Cantidad` del **T70P no está vacío**. Dice exactamente `4`, a
secas. El hueco era del PDF capturado, no de la ficha oficial. **Vía barata cerrada.**

**Por qué el conflicto sigue ABIERTO y ahora es más interesante:**

Los tres UAV tienen **la misma arquitectura de 4 brazos con par coaxial** (evidencia `S`: T100
slide 10, T70P slide 11; y las tres fichas comparten hélice de 62 in). Sin embargo DJI escribe:

- T100 → `8 pares`
- T55 → `4 pares`
- T70P → `4` (número pelado)

Esa **inconsistencia de unidad dentro de la misma casa** es la prueba de que no se puede leer el
campo como un conteo físico sin más. Hipótesis registradas (ninguna adoptada):

1. **"pares" cuenta hélices, no pares coaxiales**: `8 pares` = 16 hélices (2 por rotor × 8
   rotores); `4 pares` del T55 = 8 hélices. Encajaría con 4 brazos coaxiales en ambos.
2. **"pares" es un criterio comercial/de suministro** (juegos de hélices CW/CCW vendidos juntos),
   no un conteo de discos instalados.
3. **El `4` pelado del T70P cuenta otra cosa** (¿rotores por…? ¿brazos?) y el campo no es
   homogéneo entre plataformas.
4. **Versión o configuración distinta** de plataforma.

**Lo que NO se ha podido obtener:** el **texto chino original**. `/cn/` devuelve **bytes
idénticos** a `/es/` (mismo `sha256`), con `lang="es"` y el payload en español; probado también
con `Accept-Language: zh-CN` y cookie de locale, y `www.dji.com/cn/...` da 404.
→ **No se dispone del carácter 对 ni de su unidad**, así que el punto 3 del encargo del
investigador **queda sin satisfacer por vía HTTP**. Registrado en
`data/raw/specs_captures/intentos_chino.json`.

**Cómo se cierra:** conteo físico (A9 en el protocolo). No por interpretación.

### C-01.1 · Evidencia nueva que apunta a 8 rotores (NO cierra el conflicto)

**Aportado por el propietario** (comunicación directa 2026-09-14, clasificación **`O`**):

> T100: **8 motores**. T25P, T55 y T70P: **4 motores**.

**Por qué es relevante y por qué no basta:**

- Si "8 motores" significa 8 unidades motrices para el T100 con 4 brazos coaxiales, corresponde a
  **8 rotores** (2 por brazo), lo que **respalda la lectura "4 pares"** y contradice la lectura
  literal "8 pares = 16 hélices".
- **Pero `O` no es `M`**: es comunicación verbal, sin instrumento, sin incertidumbre ni repetición.
  Y "motor" podría no ser sinónimo de "disco de rotor" en coaxiales.
- Si "4 motores" es correcto para T55/T70P/T100 con par coaxial, hay que confirmar explícitamente
  la relación **1 motor ↔ 2 rotores** (ver C-02).

**Convergencia alcanzada:** imagen oficial (8 hélices) + propietario (8 motores) apuntan ambos a
**8 rotores**. Falta la **tercera pata**: inspección física con conteo fotografiado. Con las tres,
el valor promueve a `M` y C-01 se cierra.

**Efecto cuantificado si estuviera mal:** `v_inducida` en hover cambia un factor √2 (−29 % de 8 a
16 rotores); área de disco de 15,57 → 31,13 m². Por eso es la incógnita **nº 1** en prioridad de
medición (`geometry/presupuesto_hipotesis.json`).

### C-01.2 · Geometría de atomizadores: X aportada, Y derivada, Z desconocida

**Aportado por el propietario** (`O`): en el T100 las cuatro boquillas traseras están a
**x = −0,9 / −0,8 / −0,8 / −0,9 m** (de izquierda a derecha), siendo **la 2ª y la 3ª las extras**
de la configuración de 4.

Regularizado a la nomenclatura del proyecto:

| id | `position_role` | X (m) | Y (m) | clase |
|---|---|---|---|---|
| `A1` | `L_out` | −0,900 | −0,917 | X: `O` · Y: `I` (derivada) |
| `A2` | `L_in` | −0,800 | −0,459 | X: `O` · Y: `I` (derivada) |
| `A3` | `R_in` | −0,800 | +0,459 | X: `O` · Y: `I` (derivada) |
| `A4` | `R_out` | −0,900 | +0,917 | X: `O` · Y: `I` (derivada) |

**Hipótesis adoptada para la Y (explícita, por decidir con medición):** la separación declarada en
la ficha (T100: 1834 mm) corresponde al **par extremo** (A1–A4); el par interior queda cerrado a la
mitad → ±0,917 m exterior y ±0,459 m interior.

- **Validación física superada:** la boquilla exterior (±0,917 m) cae **dentro** de la barra LS100
  (±0,965 m), con margen de solo **+48 mm**. Ajuste muy justo, consistente con que DJI especifique
  1834 mm.
- **Aviso registrado:** las cuatro boquillas caen **dentro de la proyección horizontal** de un disco
  de rotor (distancia al eje: 0,248 m las exteriores y 0,707 m las interiores, frente a
  r_rotor = 0,787 m). **No es una colisión** —van por debajo del plano de rotor— pero **es
  exactamente la configuración que hace relevante H3**: las gotas se emiten dentro de la estela, no
  fuera. La distancia al eje del rotor más cercano es parámetro de primer orden para H3.

**Sigue en `D`:** la coordenada **Z** de los atomizadores, y la X de las otras tres plataformas.

---

## C-02 · T100 / T55 / T70P — accionamiento del par coaxial **ABIERTO (sin evidencia)**

**Pregunta:** ¿el par coaxial es solidario (un motor) o tiene dos motores/ESC independientes?
Determina **qué restricción de par aplica** y si el reparto `T_l/T_u` es siquiera una variable de
control (ver `geometry/coaxial_thrust_split.md` §1.0).

**Búsqueda hecha:** términos `motor`, `ESC`, `电调`, `coaxial`, `同轴` en los 10 decks de DJI
Academy y en las capturas de las fichas oficiales.

**Resultado: NEGATIVO.**
- Las fichas oficiales **no declaran** ni el número de motores ni el de ESC por brazo. El grupo
  `Sistema de propulsión - Motores` solo da estator y KV.
- El deck 08 menciona la categoría "Motores y ESC" en una lista de limpieza, **sin contar
  unidades ni describir el accionamiento**.
- El deck 04 trata del **generador**, no de la propulsión.

**Cómo se cierra:** inspección física o manual de servicio (A10 en el protocolo).

---

## C-03 · T55 — topología sin evidencia **ABIERTO**

- **No aparece en ninguno de los 10 decks** de DJI Academy (cero coincidencias de identidad, ni
  por alias), auditado con `scripts/audit_documentary_evidence.py`.
- Las capturas oficiales dan: hélice 62 in, `Cantidad = 4 pares`, `wheelbase 2415 mm`,
  estator 155×16, KV 55.
- **No hay evidencia visual** de su número de rotores en el material disponible.

→ El T55 queda **enteramente dependiente de medición física** para `rotor_count` y
`blades_per_rotor`. Es la plataforma con más campos en `D` (19).

---

## C-04 · T55 / T70P — relación geométrica candidata no cierra **ABIERTO**

`span_candidato = D_axis/√2 + diámetro de rotor` coincide en T25P (+0,49 %) y T100 (+0,05 %),
y **no** en T55 (+2,90 %) y T70P (+3,92 %).

**Nota nueva de la recaptura:** el T55 y el T70P comparten hélice de 62 in (1,575 / 1,574 m) y
sin embargo tienen wheelbases distintos (2415 vs 2440 mm) y **sobres desplegados muy distintos**
(3190×3570 vs 3175×3490 mm). El T55 declara ser **más ancho** que el T70P pese a tener menor
wheelbase — lo que apunta a la hipótesis 3 de `protocolo_geometria.md` §7.1 (definición distinta
de "desplegado" o componentes que sobresalen), no necesariamente a un error de especificación.

**Cómo se cierra:** mediciones A2/A8 en T55 y T70P.

---

## C-05 · T70P — dimensiones desplegadas **RESUELTO en favor de la ficha oficial**

| Fuente | Dimensiones desplegadas |
|---|---|
| **Ficha oficial en vivo** (captura 2026-09-14) | **3200 × 3520 × 960 mm** |
| DJI Academy (deck 01) | 3175 × 3490 × 960 mm |
| PDF del investigador | 3200 × 3520 × 960 mm (coincide con la ficha) |

**Resolución:** la ficha oficial vigente dice **3200 × 3520 × 960 mm**. El valor del deck de
Academy (3175 × 3490) **no coincide con la ficha oficial actual** y se descarta como fuente de
dimensiones. Consecuencia: el manifiesto del T70P debe usar 3200 × 3520 × 960 mm, y su prueba de
consistencia geométrica pasa de +3,92 % a **+3,10 %** (sigue sin cerrar, así que C-04 continúa).

> Nota de método: esto **no** es una promoción automática. La ficha oficial es la fuente de mayor
> jerarquía (`P`), y aquí hay convergencia entre el PDF del investigador y la captura en vivo
> —dos fuentes independientes del mismo emisor—, que es exactamente el criterio de convergencia
> exigido. Las **cotas que siguen sin cerrar** (C-04) NO se resuelven así: exigen medición.

---

## C-06 · T100 — masa de pulverización **ABIERTO (menor)**

| Fuente | Valor |
|---|---|
| Ficha oficial | 75 kg (2 boquillas) / 77 kg (4 boquillas) |
| DJI Academy | 73 kg (2 boquillas) / 74,9 kg (4 boquillas) |

La ficha oficial cierra con el MTOW (75 + 100 = 175 ✓); Academy no (73 + 100 = 173 ≠ 175).
**Se adopta provisionalmente la ficha oficial** por coherencia con el balance de masas, y se
anota la discrepancia. No es bloqueante.

---

## C-07 · MTOW de esparcido — discrepancias menores entre fuentes **ABIERTO (fuera de alcance)**

Detectado al leer el grupo `Aeronave` de las capturas en vivo:

| Plataforma | Ficha oficial en vivo | DJI Academy | Nota |
|---|---|---|---|
| **T55** | esparcido **104 kg** (DB1050) / **108 kg** (DB1580) | 108 kg | El `specs_master.csv` tiene 108; la ficha da **104** con DB1050 |
| **T70P** | esparcido **126 kg** (DB1580) / **130 kg** (DB2160) | 126 kg | El deck dice 126 para ambos; la ficha distingue por batería |
| **T100** | *(por leer del payload)* | 175 kg | — |

**Impacto:** **ninguno en este estudio.** El esparcido está explícitamente fuera del alcance de
este primer paper (context.md §3; plan maestro §3). Se registra para no perder la discrepancia,
no se corrige el `specs_master.csv` —que es de pulverización— en esta ronda.

---

## C-08 · `actuationDiskSource` no implementa la arquitectura C→B **CONFIRMADO EXPERIMENTALMENTE**

**Detectado:** 2026-09-19, ejecutando GATE CFD-0 en WSL. **Detalle completo:**
`evidence/BUG_conceptual_06_actuationDisk.md`.

**Qué pasa:** el método Froude de `actuationDiskSource` calcula el empuje **a partir del flujo
incidente axial**, `T = 2ρA|U_o·n|²a(1−a)`. Si el flujo es perpendicular al disco, `T ≈ 0`
**aunque `Cp`, `Ct`, `diskArea`, las `cellZone` y el solver sean correctos**.

**Prueba discriminante** (`scripts/test_axial_source.sh`, copia temporal, el caso real intacto):

| Flujo de entrada | `Uz` medido bajo el rotor |
|---|---|
| Horizontal `(3.108, 0, 0)` — caso nominal | **≈ 1×10⁻⁷** (nulo) |
| Vertical `(0, 0, −3.108)` — test axial | **−0.289 m/s** |

**Por qué es grave:** el caso físico del proyecto es el peor posible para este modelo. En hover
el flujo axial entrante es ≈ 0 porque **el disco genera el flujo, no lo recibe**. El modelo está
pensado para turbinas/hélices en avance (flujo incidente → T calculado); nosotros necesitamos lo
contrario (T prescrito → flujo generado).

**Consecuencias:** CFD-0 **no se cierra** (corre y converge, pero la física es nula); la suite de
128 casos **no se escala** con esta formulación; cualquier downwash o deposición obtenido así
sería inválido.

**Corrección:** fuente de momento explícita con `∫_V f dV = T_i`, independiente de `U`.
`meanVelocityForce` no sirve (fuerza global, no por disco). Candidatos y requisitos en el
documento del bug.

**Lo que NO era:** un problema de malla. La hipótesis de resolución insuficiente se descartó
**antes** de gastar cómputo, con una prueba de una sola ejecución.

---

## Resumen de estado

| ID | Conflicto | Estado | Se cierra con |
|---|---|---|---|
| C-01 | T100 8 vs 16 rotores | **ABIERTO** — semántica probada ambigua | conteo físico (A9) |
| C-02 | Accionamiento del par coaxial | **ABIERTO** — sin evidencia documental | inspección (A10) |
| C-03 | T55 topología | **ABIERTO** — sin evidencia | medición |
| C-04 | Relación geométrica T55/T70P | **ABIERTO** | medición A2/A8 |
| C-05 | T70P dimensiones | ✅ **RESUELTO** (ficha oficial vigente) | — |
| C-06 | T100 masa de pulverización | **ABIERTO (menor)** | medición en báscula |
| C-07 | MTOW de esparcido | **ABIERTO (fuera de alcance)** | no aplica a este paper |
| **C-08** | **`actuationDiskSource` no impone el empuje (arquitectura C→B no implementada)** | **CONFIRMADO experimentalmente** | **sustituir por fuente de momento explícita** |

**De los 7 conflictos, 1 quedó resuelto por convergencia documental.** Lo importante: C-01 pasó de
"posible error de OCR" a **"ambigüedad semántica demostrada en la documentación oficial de DJI"**,
que es un resultado más sólido y más citable que una duda de digitalización — y **no se ha cerrado
con él**, precisamente para no convertir una decisión documental en un supuesto físico.
