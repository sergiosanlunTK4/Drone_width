# DJI Agras T25P — modelo CFD (v2)

El sistema común, la terna de ejes, la inclinación, los archivos y el uso en OpenFOAM se describen en **[`../README_MODELOS_CFD.md`](../README_MODELOS_CFD.md)**. Los parámetros están en `scripts/agras_model/platforms/t25p.py`.

| Dato | Valor | Clase / fuente |
|---|---|---|
| Topología | 4 rotores simples | S (vistas UP / LEFT / FRONT) |
| Hélice | 50 in = 1.270 m, 2 palas; paso 18.5 in | diámetro P; paso **I** (P/D de la 6223) |
| Bujes (X, Y) | delanteros (+0.680, ±0.712); traseros (−0.680, ±0.716) | S, `T25P_UP.png` a 4.38 mm/px (diagonal 1972 mm, +0.1 %) |
| Plano de hélice | 0.695 m sobre el suelo (Z = +0.130); suelo Z = −0.565 | S, altura calibrada con los 820 mm oficiales |
| Giro | FR CCW · FL CW · RL CCW · RR CW | **I** (convención DJI tradicional): verificar |
| **Inclinación del motor** | **−2.2° a lo largo del brazo** | I (valor de familia); medida propia −1.6 ± 1.2° (S), compatible |
| Atomizadores estándar | bajo los motores traseros, disco en (−0.680, ±0.710), 0.29 m sobre el suelo | P (1420 mm) + S |
| Atomizadores opcionales | bajo los motores delanteros | O (propietario, 2026-11-22); desplazamiento lateral I |
| Chequeos | sobre 2630 × 2702 mm (oficial 2650 × 2700), altura 820 mm; 1 sólido, mallas limpias, 0 interferencias | `_build_report.json` |

Nota de geometría: en planta, la carcasa trasera queda bajo los discos de las hélices traseras. Por eso se modela con una base ancha baja y una parte central estrecha más alta. Si fuera más alta en toda su anchura cortaría las hélices, lo cual es físicamente imposible.
