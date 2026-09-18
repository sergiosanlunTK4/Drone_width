# geometry/manifests — manifiestos geométricos auditables

**Generado por:** `scripts/build_geometry_manifests.py` (re-ejecutable, determinista)
**Enriquecido por:** `scripts/annotate_manifests_with_media_evidence.py` (evidencia visual `S`)
**Reemplaza a:** `geometry/t25p_geometry_manifest.json` y equivalentes (eliminados — ver `research_log.md` Entry 007)

> ⚠ **Estos manifiestos son trazables, NO validados físicamente.**
> Una geometría con procedencia correcta sigue siendo una **hipótesis** mientras no esté medida.
> El hito pendiente es cerrar **GATE 1A** (`geometry/protocolo_geometria.md` §0 y §8).

## Por qué existe este directorio

Los manifiestos anteriores declaraban como hechos datos que las propias fichas marcaban como
**desconocidos**: número de rotores, wheelbase, diámetro de rotor y —lo más grave— un `max_rpm`
inventado para cada plataforma. Eso viola las reglas de `context.md` §7, §42 y §51 y hacía
imposible auditar de dónde salía cada número.

Aquí **cada campo lleva su procedencia y su fuente**. Un dato que no se conoce queda en `null`.

## Clasificación de datos

| Etiqueta | Significado | Puede usarse en CFD de estudio |
|---|---|---|
| **P** | Público oficial (`ag.dji.com/es/<uav>/specs`) | Sí, citando fuente y fecha |
| **P-A** | Público DJI Academy (material de formación de distribuidor) | Sí, anotando la fuente |
| **S** | **Evidencia documental visual** (imagen oficial con pie inequívoco) | Solo hechos **discretos**: nº de brazos, coaxialidad, nº de palas, posición relativa. **Nunca dimensiones.** |
| **M** | Medido con protocolo propio | Sí — es el único origen válido para geometría de estudio |
| **I** | Inferido, con el razonamiento escrito | Solo como **hipótesis de trabajo**, declarada |
| **E** | Estimación de planificación | Solo para dimensionar el problema |
| **D** | Desconocido | **No.** Se deja `null` y se anota qué medición falta |

**Regla dura:** de una fotografía **sin escala ni cota inequívoca no se derivan dimensiones**.
Los objetos visuales extraídos están en `data/raw/media/`, catalogados en
`data/processed/media_inventory.csv` y revisables en `figures/contact_sheets/`.

## Contenido de cada manifiesto

- `dimensiones` — wheelbase, sobre desplegado, diámetro de rotor, paso de pala, palas por rotor
- `modelo_geometrico` — la **relación candidata** (prueba de consistencia) y su contraste contra el sobre oficial
- `evidencia_visual` — entradas `S` con archivo, diapositiva, qué muestra y qué **no** permite
- `masa` — masas por configuración y fórmula de masa a carga `f`
- `topologia_rotores` — nº de brazos, coaxialidad, nº de rotores (**hipótesis**), rotación, posiciones XY
- `propulsion` — motor, KV, `rpm_real` (**D: riesgo R1**), ESC, empuje publicado (ambiguo)
- `pulverizacion` — atomizadores, separación, caudales, espectro, ancho nominal, barra
- `operacion` — velocidades, alturas
- `derivados_nivel0` — momentum theory (solo órdenes de magnitud, §12 nivel 0)
- `pendiente_de_medicion` — lista cerrada de lo que falta
- `validaciones` — errores y avisos del propio generador

## Relación geométrica candidata (prueba de consistencia, NO identidad)

`distancia diagonal entre ejes` (D_axis) = separación entre **ejes** de rotores opuestos. Para planta cuadrada:

```
lado entre ejes adyacentes = D_axis / √2
alcance desplegado (span)  = lado + diámetro de rotor
```

Contraste contra el sobre oficial:

| UAV | span candidato | ancho oficial | error | ¿cierra? |
|---|---|---|---|---|
| T25P | 2663 mm | 2650 mm | +0,49 % | ✅ |
| T100 | 3222 mm | 3220 mm | +0,05 % | ✅ |
| T55 | 3283 mm | 3190 mm | +2,90 % | ❌ no cierra |
| T70P | 3299 mm | 3175 mm | +3,92 % | ❌ no cierra |

**Esto es una prueba de consistencia, no una identidad.** Con 2 coincidencias y 2 desviaciones la
evidencia no alcanza para elevarla a ley. Un 2,9–3,9 % es demasiado grande para tratarlo como
redondeo, pero **tampoco demuestra que la especificación esté mal**: hay al menos cinco hipótesis
alternativas (brazos no diagonales, discos desplazados longitudinalmente, definición distinta de
"desplegado", proyección en planta vs distancia 3D, guardas que sobresalen del disco).
Se discriminan con las mediciones **A2** y **A8** de T55 y T70P.
Detalle en `geometry/protocolo_geometria.md` §7 y §7.1.

Invariante de no-solape (`lado > diámetro de rotor`) verificada en las 4 plataformas:

| UAV | lado entre ejes | diámetro rotor | margen |
|---|---|---|---|
| T25P | 1,393 m | 1,270 m | +0,123 m |
| T55 | 1,708 m | 1,575 m | +0,133 m |
| T70P | 1,725 m | 1,574 m | +0,151 m |
| T100 | 1,648 m | 1,574 m | +0,074 m |

## Cómo usarlo

```powershell
# regenerar manifiestos y resumen
python scripts/build_geometry_manifests.py

# anadir la evidencia visual (categoria S) a los manifiestos
python scripts/annotate_manifests_with_media_evidence.py

# regenerar STL de control + sidecar de trazabilidad
python scripts/generate_control_geometry_v2.py

# extraer/catalogar multimedia de los PPTX
python scripts/extract_pptx_media.py

# auditoría completa del estado de preparación de datos
python scripts/audit_target_readiness.py
```

## Advertencia

Estos manifiestos contienen **hipótesis y evidencia documental**, no mediciones. Mientras el
bloque A/B de `geometry/protocolo_geometria.md` siga en `D`:

- **GATE 1A** sigue abierto → no se malla la geometría de estudio.
- **GATE 1B** sigue abierto → cualquier CFD es **exploratorio** y no puede entrar al dataset ni al
  paper como dato de la plataforma real.

Conflicto abierto que hay que resolver antes de mallar: **T100 con 8 u 16 rotores** (specs DJI dicen
"8 pares"; el material DJI Academy indica 4 pares). Ver `CONFLICTO_ABIERTO_rotor_count` en el
manifiesto del T100.
