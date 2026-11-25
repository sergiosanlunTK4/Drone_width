# DJI Agras T70P — modelo CFD (v2)

El sistema común, la terna de ejes, la inclinación, los archivos y el uso en OpenFOAM se describen en **[`../README_MODELOS_CFD.md`](../README_MODELOS_CFD.md)**. Los parámetros están en `scripts/agras_model/platforms/t70p.py`.

| Dato | Valor | Clase / fuente |
|---|---|---|
| Topología | 4 rotores simples, **no coaxial** | P-A ("empuje de un solo eje 54.2 kg", abrazadera oscilante "solo T70P") + S (slide 11) |
| Hélice | 6223: 1.5748 m, paso 23 in, 2 palas | P / P-A |
| Bujes (X, Y) | delanteros (+0.802, ±0.963); traseros (−0.802, ±0.881) | S, `T70P_UP.png` a 4.95 mm/px |
| Plano de hélice | Z = +0.265 (0.765 m sobre el suelo); suelo Z = −0.50 | S |
| Giro (desde arriba) | M1 FR CW · M2 FL CCW · M3 RL CW · M4 RR CCW | P-A, slide 14 |
| **Inclinación del motor** | **−2.2° a lo largo del brazo** (parte alta hacia dentro) | S (vista trasera, lateral −1.52° → −1.94°) + M (propietario 2–3°) |
| Atomizadores estándar | bajo los motores traseros, disco en (−0.802, ±0.937, −0.200), 0.30 m sobre el suelo; eje inclinado con el motor | P (1874 mm) + S |
| Atomizadores opcionales | bajo los motores delanteros | O (propietario, 2026-11-22); desplazamiento lateral I |
| Motor | 155P, estator 155 × 16 mm | corrección del propietario (`evidence/DATOS_Y_ACTITUD_T100.md`) |
| Chequeos | diagonal 2444 mm (+0.2 %), sobre 3179 × 3501 mm, altura 960 mm; 1 sólido, mallas limpias, 0 interferencias | `_build_report.json` |

Mediciones: `mediciones/` (inclinación en CSV, recortes con rejilla). Imágenes oficiales descargadas: `T70P_reference/descargas_dji/`.

> `scripts/generate_t70p_cfd_model.py` (8 rotores coaxiales, inclinación de 8.9° hacia fuera) contradice la evidencia y **no se usa**. El manifiesto `geometry/manifests/t70p_geometry_manifest.json` todavía indica `coaxial: true` y 8 rotores.
