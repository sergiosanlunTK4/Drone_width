# Modelos geométricos CFD — DJI Agras T25P · T55 · T70P · T100

Los cuatro modelos se generan con **el mismo sistema** (`scripts/agras_model/`, FreeCAD 1.1 / OpenCASCADE), la misma terna de ejes y la misma convención de inclinación. Por eso las simulaciones son comparables entre plataformas.

```bash
python scripts/agras_model/run.py all              # construye las 4 plataformas (~6 min) + JSON + figuras
python scripts/agras_model/run.py t55              # solo una
python scripts/agras_model/run.py t55 --solo-post  # solo JSON y figuras (sin FreeCAD)
python scripts/agras_model/fotogrametria/medir_inclinacion.py all   # re-mide la inclinación (clase S)
```

Cada cota está en `scripts/agras_model/platforms/<p>.py` con su clase: **P** ficha DJI · **P-A** DJI Academy · **M** medido por el propietario · **S** medido sobre imagen oficial · **I** inferido. Para corregir un valor se edita ese archivo y se vuelve a generar.

## 1. Resumen por plataforma

| | T25P | T55 | T70P | T100 |
|---|---|---|---|---|
| Rotores | 4 simples, 50 in | 4 simples, 62 in | 4 simples, 62 in | **8 (4 pares coaxiales)**, 62 in |
| Diagonal modelo / oficial | 1972 / 1970 mm | 2439 / 2415 mm | 2444 / 2440 mm | 2330 / 2330 mm |
| Sobre con hélices, modelo / oficial | 2630 × 2702 / 2650 × 2700 | 3150 × 3520 / 3190 × 3570 | 3179 × 3501 / 3200 × 3520 | 3247 × 3247 / 3220 × 3224 |
| Altura | 820 mm (= oficial) | 934 mm (=) | 960 mm (=) | 975 mm (=) |
| Plano de hélice sobre el suelo | 0.695 m | 0.700 m | 0.765 m | 0.875 / 0.585 m |
| Disco del atomizador sobre el suelo | 0.29 m | 0.29 m | 0.30 m | 0.28 m |
| Atomizadores | 2 bajo los motores traseros (1420 mm) | barra con 2 en V por brazo trasero (1800 mm, exteriores) | 2 bajo los motores traseros (1874 mm) | barra LS100 trasera, 4 (1834 mm, exteriores) |
| **Inclinación del motor** (a lo largo del brazo) | −2.2° (I; S −1.6 ± 1.2) | −2.2° (I) | **−2.2°** (S + M) | **−3.3°** (S) |
| Planta | S (foto cenital) | **I** (sin vista cenital) | S | M + S |

Todos los modelos son un sólido B-rep válido, con mallas STL cerradas, sin non-manifold ni auto-intersecciones y sin interferencias entre los discos actuadores y el fuselaje. Los chequeos automáticos están en `_build_report.json`.

## 2. Terna de ejes (común, dextrógira)

- Origen XY: centroide de los bujes. Origen Z: plano de raíz de los brazos (en el T100, el plano medio del par coaxial).
- **+X adelante** (lado del radar) · **+Y izquierda** (babor) · **+Z arriba**. El suelo de cada modelo está en `coordinate_system.ground_plane_z_m` del JSON.
- STL en metros, STEP en milímetros.

> El modelo T100 anterior (guardado en `T100_CFD/_anterior_v1/`) declaraba "+Y estribor, +Z arriba, mano derecha". Esa terna es levógira y espejaba el dron respecto a sus sentidos de giro. Aquí se conservan los **nombres** de rotor (FR = delantero-derecho, etc.) en una terna dextrógira.

## 3. Inclinación de los motores y de los atomizadores

Según el propietario, **el motor va fijado perpendicular al tubo del brazo**. Por eso la inclinación se modela así:

- Es un giro rígido del grupo motor (motor, abrazadera, caja de montaje, hélice, disco actuador y atomizador colgante) **en el plano vertical que contiene al brazo**, alrededor de la unión brazo-motor.
- El valor negativo significa que la parte alta del eje va hacia dentro y la parte baja (el atomizador) hacia fuera.
- El empuje se reparte en `disk_normal` (JSON): un 99.93 % vertical, y el resto hacia el centro del dron y a lo largo del brazo.
- Los atomizadores montados en el grupo heredan la inclinación. Además pueden tener una inclinación propia (`own_cant_deg`), como la V del T55.
- Los bujes medidos en planta se respetan: el pivote se calcula para que el buje inclinado caiga exactamente donde se midió.

**Medición (clase S):** `scripts/agras_model/fotogrametria/medir_inclinacion.py`.
- Usa los bordes subpíxel de las columnas verticales (motor-atomizador o el par coaxial) contra el fondo, con mínimos cuadrados y rechazo de atípicos a 2.5σ.
- La vertical de referencia es el cilindro del radar.
- La componente lateral se promedia por parejas izquierda/derecha, con lo que se cancela el alabeo de la cámara.
- La componente medida se proyecta sobre la dirección del brazo.
- Métodos descartados, con su motivo: ver el docstring del script.

## 4. Archivos de cada plataforma (`<P>_CFD/`, prefijo `<p>_`)

| Archivo | Uso |
|---|---|
| `<p>_airframe.stl` / `_ascii.stl` / `.step` | Pared no-slip: un sólido estanco (región `airframe`). |
| `<p>_rotor_disks.stl` | Discos actuadores **inclinados**, una región por rotor (`rotor_M1_FR`…; en el T100, `_upper` / `_lower`). |
| `<p>_rotor_blades.stl` / `.step` | Hélices con torsión de paso constante (para MRF o malla deslizante). |
| `<p>_spray_nozzles.stl` | Marcadores del disco de cada atomizador (una región por boquilla). |
| `<p>_full_assembly.step` / `.stl`, `<p>_model.FCStd` | Ensamblaje completo y documento FreeCAD. |
| `<p>_cfd_coordinates.json` | Centros, normales, ω, componentes de la inclinación, boquillas (centro, eje, altura), referencia de *momentum theory*. |
| `<p>_overlay_top.png` | El modelo proyectado sobre la foto cenital oficial a la misma escala (no existe para el T55). |
| `<p>_geometry_verification.png` | Planta, perfil y alzado del modelo junto a las fotos de referencia. |
| `mediciones/` | CSV de inclinación, recortes con rejilla y registro de la construcción. |

## 5. Uso en OpenFOAM (resumen)

- **Fuentes:** una `actuationDiskSource` (u otra fuente equivalente) **por rotor**, cada una con su `cellZone` sacada de la región correspondiente de `<p>_rotor_disks.stl`.
- **Normal del disco:** `rotors[i].disk_normal`. Ya **no** es (0, 0, 1).
- **Giro (swirl):** `angular_velocity_unit_vector`.
- **Inyección lagrangiana:** desde `spray_system.nozzles[i].disc_center_xyz_m`, como una lámina radial perpendicular a `disc_axis`.
- **Coaxial (T100):** el reparto de empuje entre el rotor superior y el inferior sigue siendo **D**. La referencia de *momentum theory* del JSON usa el área de 4 discos.

## 6. Pendientes y discrepancias abiertas (por prioridad)

1. **T100, X de los atomizadores.** Tus valores (M) dicen −0.875 / −0.775 m. La foto cenital da −0.58 m en los extremos de la barra y la lateral −0.68 m (S). Es la cota más sensible para la deposición. Hoy se usan tus valores.
2. **T55, planta inferida (I).** No hay vista cenital ortogonal. Se usaron las proporciones de la familia T70P escaladas a las tres cotas oficiales (error ≤ 1.4 %). La V de los atomizadores (±10°) también es I.
3. **T25P / T55, sentido de giro** asumido (I) con la convención DJI tradicional. Solo el T70P (P-A) y el T100 (M) están documentados.
4. **T25P / T55, inclinación** con el valor de familia −2.2° (I). En el T25P la foto da −1.6 ± 1.2°, compatible.
5. **T100, marco vertical.** Las imágenes (S, dos vistas coincidentes) sitúan el plano coaxial a 0.73 m del suelo; el modelo anterior lo ponía a 0.625 m.
6. Perfil de pala, paso del T25P y altura exacta del disco del atomizador: medir para pasar de S/I a M.
