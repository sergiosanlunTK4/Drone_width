# HOJA DE CAMPO — Bloque 1: metrología estática

**Plataformas:** T25P · T55 · T70P · T100  
**Generado por:** `scripts/generate_field_sheets.py`  
**Protocolo de referencia:** `geometry/protocolo_geometria.md` §10

---

## 0. ANTES DE TOCAR NINGÚN DRON — sistema de referencia

Se hace **una vez** y vale para los cuatro. Si esto queda mal, **ninguna cota**
posterior es interpretable.

```
nombre  = CG_tank50
origen  = CG en configuración de pulverización con tanque al 50 %
X       = hacia adelante (dirección de vuelo)
Y       = hacia la izquierda
Z       = hacia arriba
```

| # | paso | hecho |
|---|---|---|
| 0.1 | Elegir y **marcar físicamente** el origen (punto, cintas, plantilla) | ☐ |
| 0.2 | Describir **cómo** se materializó: ________________________________ | ☐ |
| 0.3 | **FOTO CENITAL** con etiquetas físicas `R1`–`R4` y **flecha `+X`** | ☐ |
| 0.4 | Anotar el nombre del archivo de esa foto: ____________________ | ☐ |
| 0.5 | Nivelar el dron y registrar el método de nivelación | ☐ |
| 0.6 | Anotar si el origen se fijó **antes o después** de conocer el CG medido | ☐ |

> La foto de 0.3 es la que dentro de meses impedirá discutir qué significaba «R1».
> Es obligatoria, no opcional.

### 0.1 Convención de numeración (interna, NO de DJI)

| id | `position_role` | posición |
|---|---|---|
| `R1` | `FL` | delantero izquierdo |
| `R2` | `RL` | trasero izquierdo |
| `R3` | `RR` | trasero derecho |
| `R4` | `FR` | delantero derecho |

`R1…R4` son **identificadores**; `FL/RL/RR/FR` contienen la **semántica**.
Los pares diametralmente opuestos son `FL↔RR` y `FR↔RL`.

### 0.2 Material mínimo

- [ ] Cinta métrica (clase de exactitud anotada) y regla/calibre
- [ ] Plomada o nivel láser para proyectar centros al suelo
- [ ] Nivel digital (para la normal del disco)
- [ ] Báscula con resolución conocida
- [ ] Cámara o móvil (fotos de **cada** punto medido)
- [ ] Cintas de etiquetar para marcar `R1`–`R4`, `A1`–`A4` y el origen
- [ ] Esta hoja impresa y bolígrafo (o tablet)

### 0.3 Seguridad

- [ ] **Hélices retiradas o bloqueadas** en toda medición con el dron energizado
- [ ] Ninguna medición se hace con motores armados
- [ ] Dron sobre caballete o superficie estable antes de inclinarse sobre él


---

# T25P — DJI Agras T25P

**Datos públicos de partida:** wheelbase 1970 mm · sobre desplegado 2650 × 2700 × 820 mm · Ø rotor 1270 mm · tanque 20 kg · MTOW 53 kg

**Referencias de nivel 0 para CONTRASTAR** (momentum theory, no son resultado): área de disco 5.067 m² · carga de disco 102.6 N/m² · empuje/rotor si reparto uniforme 13.3 kg · v_inducida 6.62 m/s

*Fecha:* __________  *Operador:* __________  *Lugar:* ____________________
*Condiciones:* T ___ °C  HR ___ %  P ___ hPa  viento ___ m/s
*Dron:* ☐ sobre caballete ☐ superficie plana ☐ otro: __________  *Nivelado:* ☐ sí

### A. Centros de rotor — T25P

> **Convención interna** (vista cenital, +X adelante, +Y izquierda, +Z arriba).
> No es numeración DJI. Toda fila lleva su `position_role`.

*Origen de medida (marcar uno):* ☐ buje R1 ☐ centro del cuerpo ☐ plomada al suelo
*Referencia vertical:* ☐ base del depósito ☐ plano de aterrizaje ☐ otro: __________

| id | rol | posición | X (m) | Y (m) | Z (m) | normal (x,y,z) | Ø (m) |
|---|---|---|---|---|---|---|---|
| `R1` | `FL` | delantero izquierdo |  |  |  |  |  |
| `R2` | `RL` | trasero izquierdo |  |  |  |  |  |
| `R3` | `RR` | trasero derecho |  |  |  |  |  |
| `R4` | `FR` | delantero derecho |  |  |  |  |  |

*Nota de esta plataforma:* Evidencia S (deck 01 slide 12): 4 brazos SIN par coaxial. Motor rotulado 10028/59KV.

**Separaciones** (cinta entre centros de buje, dron desplegado):

| magnitud | valor (m) | rep. 2 | rep. 3 | setup |
|---|---|---|---|---|
| separación ejes adyacentes, dirección X | | | | |
| separación ejes adyacentes, dirección Y | | | | |
| separación ejes opuestos, dirección X | | | | |
| separación ejes opuestos, dirección Y | | | | |
| alcance desplegado total, X | | | | |
| alcance desplegado total, Y | | | | |
| cota del disco al cuerpo (por si el 'desplegado' incluye guardas) | | | | |

### B. Atomizadores — T25P

> Medir en **configuración de 2** y repetir en **configuración de 4** (anotar en `configuracion`).
> `altura_rel_plano_rotor` es el Δz al plano de rotor **más próximo**: es lo crítico para H3.

| id | X (m) | Y (m) | Z (m) | vector descarga (x,y,z) | Δz al rotor (m) | rotor más cercano | soporte / cota al eje |
|---|---|---|---|---|---|---|---|
| `A1` |  |  |  |  |  |  |  |
| `A2` |  |  |  |  |  |  |  |
| `A3` |  |  |  |  |  |  |  |
| `A4` |  |  |  |  |  |  |  |

*Separación entre boquillas declarada por el fabricante:* 1420 mm.
Comprobar en campo si coincide y anotar la diferencia.

**Punto efectivo de emisión** (si es determinable, foto macro): ☐ sí ☐ no
Descripción: ______________________________________________

**Rotor(es) cuya estela recibe cada atomizador** (derivado de A + B):
A1 → ______   A2 → ______   A3 → ______   A4 → ______

### C. Masas y CG — T25P

> 🔴 **`nominal` ≠ `measured`.** La columna nominal es un valor **derivado** del planning
> (clase `E`). Antes de cada pesada hay que **pesar la configuración efectiva** y anotarla
> en `measured`. **La diferencia entre ambas es un resultado**, no un detalle.

| f (tanque) | nominal (kg) | **medido (kg)** | incert. | CG X (m) | CG Y (m) | CG Z (m) |
|---|---|---|---|---|---|---|
| 1.00 | 53.0 |  |  |  |  |
| 0.75 | 48.0 |  |  |  |  |
| 0.50 | 43.0 |  |  |  |  |
| 0.25 | 38.0 |  |  |  |  |
| 0.00 | 33.0 |  |  |  |  |

| elemento | masa (kg) | incertidumbre | instrumento |
|---|---|---|---|
| batería instalada (indicar modelo) | | | |
| tanque vacío | | | |
| dron sin batería | | | |
| atomizadores instalados (2 o 4) | | | |

*Restricción a verificar:* el T70P a 20 L exige batería **DB2160**.
Con DB1580 no cierra contra el MTOW. Anotar qué batería se usó realmente.


---

# T55 — DJI Agras T55

**Datos públicos de partida:** wheelbase 2415 mm · sobre desplegado 3190 × 3570 × 934 mm · Ø rotor 1575 mm · tanque 50 kg · MTOW 95 kg

**Referencias de nivel 0 para CONTRASTAR** (momentum theory, no son resultado): área de disco 15.586 m² · carga de disco 59.8 N/m² · empuje/rotor si reparto uniforme 11.9 kg · v_inducida 5.05 m/s

*Fecha:* __________  *Operador:* __________  *Lugar:* ____________________
*Condiciones:* T ___ °C  HR ___ %  P ___ hPa  viento ___ m/s
*Dron:* ☐ sobre caballete ☐ superficie plana ☐ otro: __________  *Nivelado:* ☐ sí

### A. Centros de rotor — T55

> **Convención interna** (vista cenital, +X adelante, +Y izquierda, +Z arriba).
> No es numeración DJI. Toda fila lleva su `position_role`.

*Origen de medida (marcar uno):* ☐ buje R1 ☐ centro del cuerpo ☐ plomada al suelo
*Referencia vertical:* ☐ base del depósito ☐ plano de aterrizaje ☐ otro: __________

| id | rol | posición | X (m) | Y (m) | Z (m) | normal (x,y,z) | Ø (m) |
|---|---|---|---|---|---|---|---|
| `R1` | `FL` | delantero izquierdo |  |  |  |  |  |
| `R2` | `RL` | trasero izquierdo |  |  |  |  |  |
| `R3` | `RR` | trasero derecho |  |  |  |  |  |
| `R4` | `FR` | delantero derecho |  |  |  |  |  |

**Rotores inferiores del par coaxial** (si aplica):

| id | rol | posición | X (m) | Y (m) | Z (m) | normal (x,y,z) | Ø (m) |
|---|---|---|---|---|---|---|---|
| `R1_lower` | `FL` | delantero izquierdo (inferior) |  |  |  |  |  |
| `R2_lower` | `RL` | trasero izquierdo (inferior) |  |  |  |  |  |
| `R3_lower` | `RR` | trasero derecho (inferior) |  |  |  |  |  |
| `R4_lower` | `FR` | delantero derecho (inferior) |  |  |  |  |  |

*Nota de esta plataforma:* Topologia NO confirmada. Ficha oficial: 'Cantidad = 4 pares'. Contar brazos y rotores: es el dato que cierra GATE 1A del T55.

**Separaciones** (cinta entre centros de buje, dron desplegado):

| magnitud | valor (m) | rep. 2 | rep. 3 | setup |
|---|---|---|---|---|
| separación ejes adyacentes, dirección X | | | | |
| separación ejes adyacentes, dirección Y | | | | |
| separación ejes opuestos, dirección X | | | | |
| separación ejes opuestos, dirección Y | | | | |
| alcance desplegado total, X | | | | |
| alcance desplegado total, Y | | | | |
| cota del disco al cuerpo (por si el 'desplegado' incluye guardas) | | | | |

**Par coaxial — A6 (parámetro del modelo de empuje):**

| magnitud | valor (m) | rep. 2 | rep. 3 | setup |
|---|---|---|---|---|
| separación axial del par, brazo FL | | | | |
| separación axial del par, brazo FR | | | | |
| separación axial del par, brazo RL | | | | |
| separación axial del par, brazo RR | | | | |

### B. Atomizadores — T55

> Medir en **configuración de 2** y repetir en **configuración de 4** (anotar en `configuracion`).
> `altura_rel_plano_rotor` es el Δz al plano de rotor **más próximo**: es lo crítico para H3.

| id | X (m) | Y (m) | Z (m) | vector descarga (x,y,z) | Δz al rotor (m) | rotor más cercano | soporte / cota al eje |
|---|---|---|---|---|---|---|---|
| `A1` |  |  |  |  |  |  |  |
| `A2` |  |  |  |  |  |  |  |
| `A3` |  |  |  |  |  |  |  |
| `A4` |  |  |  |  |  |  |  |

*Separación entre boquillas declarada por el fabricante:* 1800 mm.
Comprobar en campo si coincide y anotar la diferencia.

**Punto efectivo de emisión** (si es determinable, foto macro): ☐ sí ☐ no
Descripción: ______________________________________________

**Rotor(es) cuya estela recibe cada atomizador** (derivado de A + B):
A1 → ______   A2 → ______   A3 → ______   A4 → ______

### C. Masas y CG — T55

> 🔴 **`nominal` ≠ `measured`.** La columna nominal es un valor **derivado** del planning
> (clase `E`). Antes de cada pesada hay que **pesar la configuración efectiva** y anotarla
> en `measured`. **La diferencia entre ambas es un resultado**, no un detalle.

| f (tanque) | nominal (kg) | **medido (kg)** | incert. | CG X (m) | CG Y (m) | CG Z (m) |
|---|---|---|---|---|---|---|
| 1.00 | 95.0 |  |  |  |  |
| 0.75 | 82.5 |  |  |  |  |
| 0.50 | 70.0 |  |  |  |  |
| 0.25 | 57.5 |  |  |  |  |
| 0.00 | 45.0 |  |  |  |  |

| elemento | masa (kg) | incertidumbre | instrumento |
|---|---|---|---|
| batería instalada (indicar modelo) | | | |
| tanque vacío | | | |
| dron sin batería | | | |
| atomizadores instalados (2 o 4) | | | |

*Restricción a verificar:* el T70P a 50 L exige batería **DB2160**.
Con DB1580 no cierra contra el MTOW. Anotar qué batería se usó realmente.


---

# T70P — DJI Agras T70P

**Datos públicos de partida:** wheelbase 2440 mm · sobre desplegado 3200 × 3520 × 960 mm · Ø rotor 1574 mm · tanque 70 kg · MTOW 126 kg

**Referencias de nivel 0 para CONTRASTAR** (momentum theory, no son resultado): área de disco 15.566 m² · carga de disco 79.4 N/m² · empuje/rotor si reparto uniforme 15.8 kg · v_inducida 5.82 m/s

*Fecha:* __________  *Operador:* __________  *Lugar:* ____________________
*Condiciones:* T ___ °C  HR ___ %  P ___ hPa  viento ___ m/s
*Dron:* ☐ sobre caballete ☐ superficie plana ☐ otro: __________  *Nivelado:* ☐ sí

### A. Centros de rotor — T70P

> **Convención interna** (vista cenital, +X adelante, +Y izquierda, +Z arriba).
> No es numeración DJI. Toda fila lleva su `position_role`.

*Origen de medida (marcar uno):* ☐ buje R1 ☐ centro del cuerpo ☐ plomada al suelo
*Referencia vertical:* ☐ base del depósito ☐ plano de aterrizaje ☐ otro: __________

| id | rol | posición | X (m) | Y (m) | Z (m) | normal (x,y,z) | Ø (m) |
|---|---|---|---|---|---|---|---|
| `R1` | `FL` | delantero izquierdo |  |  |  |  |  |
| `R2` | `RL` | trasero izquierdo |  |  |  |  |  |
| `R3` | `RR` | trasero derecho |  |  |  |  |  |
| `R4` | `FR` | delantero derecho |  |  |  |  |  |

**Rotores inferiores del par coaxial** (si aplica):

| id | rol | posición | X (m) | Y (m) | Z (m) | normal (x,y,z) | Ø (m) |
|---|---|---|---|---|---|---|---|
| `R1_lower` | `FL` | delantero izquierdo (inferior) |  |  |  |  |  |
| `R2_lower` | `RL` | trasero izquierdo (inferior) |  |  |  |  |  |
| `R3_lower` | `RR` | trasero derecho (inferior) |  |  |  |  |  |
| `R4_lower` | `FR` | delantero derecho (inferior) |  |  |  |  |  |

*Nota de esta plataforma:* Evidencia S (slide 11): par coaxial en cada brazo. A6 (separacion axial del par) es PARAMETRO DEL MODELO de empuje, no una cota decorativa.

**Separaciones** (cinta entre centros de buje, dron desplegado):

| magnitud | valor (m) | rep. 2 | rep. 3 | setup |
|---|---|---|---|---|
| separación ejes adyacentes, dirección X | | | | |
| separación ejes adyacentes, dirección Y | | | | |
| separación ejes opuestos, dirección X | | | | |
| separación ejes opuestos, dirección Y | | | | |
| alcance desplegado total, X | | | | |
| alcance desplegado total, Y | | | | |
| cota del disco al cuerpo (por si el 'desplegado' incluye guardas) | | | | |

**Par coaxial — A6 (parámetro del modelo de empuje):**

| magnitud | valor (m) | rep. 2 | rep. 3 | setup |
|---|---|---|---|---|
| separación axial del par, brazo FL | | | | |
| separación axial del par, brazo FR | | | | |
| separación axial del par, brazo RL | | | | |
| separación axial del par, brazo RR | | | | |

### B. Atomizadores — T70P

> Medir en **configuración de 2** y repetir en **configuración de 4** (anotar en `configuracion`).
> `altura_rel_plano_rotor` es el Δz al plano de rotor **más próximo**: es lo crítico para H3.

| id | X (m) | Y (m) | Z (m) | vector descarga (x,y,z) | Δz al rotor (m) | rotor más cercano | soporte / cota al eje |
|---|---|---|---|---|---|---|---|
| `A1` |  |  |  |  |  |  |  |
| `A2` |  |  |  |  |  |  |  |
| `A3` |  |  |  |  |  |  |  |
| `A4` |  |  |  |  |  |  |  |

*Separación entre boquillas declarada por el fabricante:* 1874 mm.
Comprobar en campo si coincide y anotar la diferencia.

**Punto efectivo de emisión** (si es determinable, foto macro): ☐ sí ☐ no
Descripción: ______________________________________________

**Rotor(es) cuya estela recibe cada atomizador** (derivado de A + B):
A1 → ______   A2 → ______   A3 → ______   A4 → ______

### C. Masas y CG — T70P

> 🔴 **`nominal` ≠ `measured`.** La columna nominal es un valor **derivado** del planning
> (clase `E`). Antes de cada pesada hay que **pesar la configuración efectiva** y anotarla
> en `measured`. **La diferencia entre ambas es un resultado**, no un detalle.

| f (tanque) | nominal (kg) | **medido (kg)** | incert. | CG X (m) | CG Y (m) | CG Z (m) |
|---|---|---|---|---|---|---|
| 1.00 | 126.0 |  |  |  |  |
| 0.75 | 108.5 |  |  |  |  |
| 0.50 | 91.0 |  |  |  |  |
| 0.25 | 73.5 |  |  |  |  |
| 0.00 | 56.0 |  |  |  |  |

| elemento | masa (kg) | incertidumbre | instrumento |
|---|---|---|---|
| batería instalada (indicar modelo) | | | |
| tanque vacío | | | |
| dron sin batería | | | |
| atomizadores instalados (2 o 4) | | | |

*Restricción a verificar:* el T70P a 70 L exige batería **DB2160**.
Con DB1580 no cierra contra el MTOW. Anotar qué batería se usó realmente.


---

# T100 — DJI Agras T100

**Datos públicos de partida:** wheelbase 2330 mm · sobre desplegado 3220 × 3224 × 975 mm · Ø rotor 1574 mm · tanque 100 kg · MTOW 175 kg

**Referencias de nivel 0 para CONTRASTAR** (momentum theory, no son resultado): área de disco 15.566 m² · carga de disco 110.3 N/m² · empuje/rotor si reparto uniforme 21.9 kg · v_inducida 6.86 m/s

*Fecha:* __________  *Operador:* __________  *Lugar:* ____________________
*Condiciones:* T ___ °C  HR ___ %  P ___ hPa  viento ___ m/s
*Dron:* ☐ sobre caballete ☐ superficie plana ☐ otro: __________  *Nivelado:* ☐ sí

### A. Centros de rotor — T100

> **Convención interna** (vista cenital, +X adelante, +Y izquierda, +Z arriba).
> No es numeración DJI. Toda fila lleva su `position_role`.

*Origen de medida (marcar uno):* ☐ buje R1 ☐ centro del cuerpo ☐ plomada al suelo
*Referencia vertical:* ☐ base del depósito ☐ plano de aterrizaje ☐ otro: __________

| id | rol | posición | X (m) | Y (m) | Z (m) | normal (x,y,z) | Ø (m) |
|---|---|---|---|---|---|---|---|
| `R1` | `FL` | delantero izquierdo |  |  |  |  |  |
| `R2` | `RL` | trasero izquierdo |  |  |  |  |  |
| `R3` | `RR` | trasero derecho |  |  |  |  |  |
| `R4` | `FR` | delantero derecho |  |  |  |  |  |

**Rotores inferiores del par coaxial** (si aplica):

| id | rol | posición | X (m) | Y (m) | Z (m) | normal (x,y,z) | Ø (m) |
|---|---|---|---|---|---|---|---|
| `R1_lower` | `FL` | delantero izquierdo (inferior) |  |  |  |  |  |
| `R2_lower` | `RL` | trasero izquierdo (inferior) |  |  |  |  |  |
| `R3_lower` | `RR` | trasero derecho (inferior) |  |  |  |  |  |
| `R4_lower` | `FR` | delantero derecho (inferior) |  |  |  |  |  |

*Nota de esta plataforma:* CONFLICTO ABIERTO: ficha oficial dice 'Cantidad = 8 pares'; el material Academy indica 4 brazos con un par cada uno. ESTE CONTEO ES A9: hacerlo con foto cenital y contando fisicamente, no interpretando la tabla.

**Separaciones** (cinta entre centros de buje, dron desplegado):

| magnitud | valor (m) | rep. 2 | rep. 3 | setup |
|---|---|---|---|---|
| separación ejes adyacentes, dirección X | | | | |
| separación ejes adyacentes, dirección Y | | | | |
| separación ejes opuestos, dirección X | | | | |
| separación ejes opuestos, dirección Y | | | | |
| alcance desplegado total, X | | | | |
| alcance desplegado total, Y | | | | |
| cota del disco al cuerpo (por si el 'desplegado' incluye guardas) | | | | |

**Par coaxial — A6 (parámetro del modelo de empuje):**

| magnitud | valor (m) | rep. 2 | rep. 3 | setup |
|---|---|---|---|---|
| separación axial del par, brazo FL | | | | |
| separación axial del par, brazo FR | | | | |
| separación axial del par, brazo RL | | | | |
| separación axial del par, brazo RR | | | | |

### B. Atomizadores — T100

> Medir en **configuración de 2** y repetir en **configuración de 4** (anotar en `configuracion`).
> `altura_rel_plano_rotor` es el Δz al plano de rotor **más próximo**: es lo crítico para H3.

| id | X (m) | Y (m) | Z (m) | vector descarga (x,y,z) | Δz al rotor (m) | rotor más cercano | soporte / cota al eje |
|---|---|---|---|---|---|---|---|
| `A1` |  |  |  |  |  |  |  |
| `A2` |  |  |  |  |  |  |  |
| `A3` |  |  |  |  |  |  |  |
| `A4` |  |  |  |  |  |  |  |

*Separación entre boquillas declarada por el fabricante:* 1834 mm.
Comprobar en campo si coincide y anotar la diferencia.

**Punto efectivo de emisión** (si es determinable, foto macro): ☐ sí ☐ no
Descripción: ______________________________________________

**Rotor(es) cuya estela recibe cada atomizador** (derivado de A + B):
A1 → ______   A2 → ______   A3 → ______   A4 → ______

### C. Masas y CG — T100

> 🔴 **`nominal` ≠ `measured`.** La columna nominal es un valor **derivado** del planning
> (clase `E`). Antes de cada pesada hay que **pesar la configuración efectiva** y anotarla
> en `measured`. **La diferencia entre ambas es un resultado**, no un detalle.

| f (tanque) | nominal (kg) | **medido (kg)** | incert. | CG X (m) | CG Y (m) | CG Z (m) |
|---|---|---|---|---|---|---|
| 1.00 | 175.0 |  |  |  |  |
| 0.75 | 150.0 |  |  |  |  |
| 0.50 | 125.0 |  |  |  |  |
| 0.25 | 100.0 |  |  |  |  |
| 0.00 | 75.0 |  |  |  |  |

| elemento | masa (kg) | incertidumbre | instrumento |
|---|---|---|---|
| batería instalada (indicar modelo) | | | |
| tanque vacío | | | |
| dron sin batería | | | |
| atomizadores instalados (2 o 4) | | | |

*Restricción a verificar:* el T70P a 100 L exige batería **DB2160**.
Con DB1580 no cierra contra el MTOW. Anotar qué batería se usó realmente.


---

# 5. BLOQUE OPERATIVO (opcional — requiere volar)

> Solo si el Bloque 1 pasó el post-mortem. **No se vuela antes de auditar las filas
> estáticas.** Aquí se cierra GATE 1B.

## 5.1 RPM en hover — INDIVIDUAL POR ROTOR

> 🔴 **No registrar una sola «RPM del dron».** Diferencias entre rotores son evidencia
> directa contra el supuesto de reparto uniforme `mg/N`, y **se pierden si se promedian**.

| plataforma | estado de carga | R1 (rpm) | R2 | R3 | R4 | R1_low | R2_low | R3_low | R4_low |
|---|---|---|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |  |  |  |

*Método:* ☐ tacómetro óptico de 2 canales ☐ cámara alta velocidad  *Instrumento:* ______________
*Medir RPM en hover ANTES que en bancada* (context.md §42).

## 5.2 Orden recomendado

1. RPM en hover real con **masa medida** (no nominal), en los 5 estados de carga.
2. Bancada de empuje **por rotor**, no por brazo: D5a/D5b/D5c de `coaxial_thrust_split.md`.
3. Comprobar A10 (¿un motor o dos por brazo? ¿ESC compartido o independiente?).

---

# 6. Reglas de captura

1. **Si una medición parece rara: NO se reemplaza la fila anterior.** Se añade una
   repetición con **otro `setup_id`** y se anota la incidencia. Así después se distingue
   **error de captura / repetibilidad / asimetría real** — hoy son indistinguibles.
2. **Repeticiones independientes:** para repetibilidad hay que **soltar y volver a montar**
   el instrumento entre lecturas (≥3, con distinto `setup_id`). Tres lecturas seguidas sin
   moverse miden **resolución**, no repetibilidad.
3. **Los residuos no se corrigen.** Si `r_i + r_j ≠ 0`, ese residuo **es el dato**.
   Nunca se ajustan coordenadas para forzar la simetría.
4. **`nominal` ≠ `measured`** en masa. Son variables distintas, ambas en el CSV.
5. Toda fila `M` necesita `uncertainty` e `instrument`. Toda fila necesita `reference_frame`.
6. **Fotografiar cada punto medido** y anotar el nombre del archivo.
7. Si una medición **contradice la ficha oficial, gana la medición** — y la discrepancia
   se anota en `notes`.

---

# 7. Cómo entregar los datos

Transcribir la hoja a `data/raw/mediciones_geometria.csv` con estas columnas:

```
uav,block,element_id,position_role,parameter,value,unit,uncertainty,method,
instrument,timestamp,operator,source_class,reference_frame,configuracion,
repetitions,setup_id,raw_file,notes
```

Ejemplo de tres filas reales:

```csv
T25P,rotor,R1,FL,posicion_x,0.6965,m,±0.005 (k=2),cinta desde centro de buje,
"cinta Stanley 5 m",2026-09-20T10:35:00-03:00,D.M.,M,CG_tank50,2atm,3,S1,
foto_R1_xy.jpg,origen marcado con cinta
```

**Entregar:** el CSV + las fotografías + notas de campo. Con eso corro la QA, calculo
incertidumbres, residuos 3D y consistencia geométrica, y decidimos GATE 1A.

*Recordatorio del orden acordado:* primero se ve **lo que dicen las mediciones**, y
**después** se buscan explicaciones. No se ajusta la geometría para hacerla coincidir
ni con DJI ni con la relación geométrica candidata.