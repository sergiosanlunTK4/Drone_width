# archive/ — documentos superados

**No borrados: archivados.** El proyecto exige trazabilidad (context.md §39: *"los resultados
negativos también son válidos"*, y el mismo criterio se aplica a los errores). Un documento
superado se conserva para poder reconstruir **por qué** se cambió de criterio.

**Documento vivo de referencia:** `COMO_SE_CALCULA.md` en la raíz.

---

| Fichero archivado | Por qué se superó | Sustituido por |
|---|---|---|
| `RESEARCH_ARCHITECTURE_V1_superado.md` | Contenía especificaciones **no verificadas** que contradicen las fichas: describía el T25P como hexacóptero, daba masas y capacidades de tanque distintas, y atribuía configuraciones de rotor sin fuente. Mezclaba decisiones metodológicas válidas con datos inventados | `research/RESEARCH_ARCHITECTURE_V1.md` (decisiones) + `docs/specs/` (datos con fuente) + `geometry/manifests/` (procedencia por campo) |
| `dji_agras_engineering_specs_superado.md` | Volcado de especificaciones sin clasificación de fuente por campo | `geometry/manifests/*.json` + `data/processed/specs_master.csv` + `docs/specs/*.md` |
| `hoja_de_campo_superada.md` | Hoja de campo para los 4 UAV generada **antes** de tener ningún modelo medido | Ya no aplica al T100, que está **medido** (`geometry/models/T100_CFD/`). Sigue siendo válida como plantilla para T25P/T55/T70P, pendientes de medición |
| `campana_T25P_superada.md` | Campaña de medición del T25P en dos jornadas. Se escribió cuando el T25P era el piloto previsto | El T100 tiene ahora modelo medido; la campaña queda pendiente de rehacer con el protocolo ya probado |

---

## Nota de método

Estos cuatro documentos **no eran malos**: eran correctos para el estado de información en que se
escribieron. Se archivan porque el proyecto avanzó —el T100 pasó de `D` (desconocido) a `M`
(medido)— y mantenerlos como referentes activos induciría a error.

**Lo que sí se conserva activamente** de ellos:
- `RESEARCH_ARCHITECTURE_V1.md` (en `research/`) mantiene las decisiones metodológicas: comparación
  de estrategias CFD, selección de turbulencia, propuesta de DOE, criterios de gate.
- La hoja de campo sigue siendo la plantilla para los tres UAV pendientes de medir.
