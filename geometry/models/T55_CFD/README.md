# DJI Agras T55 — modelo CFD (v2)

El sistema común, la terna de ejes, la inclinación, los archivos y el uso en OpenFOAM se describen en **[`../README_MODELOS_CFD.md`](../README_MODELOS_CFD.md)**. Los parámetros están en `scripts/agras_model/platforms/t55.py`.

| Dato | Valor | Clase / fuente |
|---|---|---|
| Topología | **4 rotores simples, no coaxial** | S: `T55.webp`, `T55_REAR.jpg` y las 54 fotos del propietario (`DJI_T55/`). El "4 pares" de la ficha son pares de palas |
| Hélice | 62 in = 1.5748 m, 2 palas; paso 23 in | diámetro P; paso I |
| **Planta** | batalla 1.575 m; vías 1.945 m (delantera) / 1.780 m (trasera) | **I**: no hay vista cenital ortogonal; proporciones de la familia T70P escaladas a la diagonal 2415 y al sobre 3190 × 3570 (errores ≤ 1.4 %) |
| Plano de hélice | 0.700 m sobre el suelo; suelo Z = −0.514 | S, `T55_REAR.jpg` calibrada con los 934 mm oficiales |
| Giro | FR CCW · FL CW · RL CCW · RR CW | **I**: verificar |
| **Inclinación del motor** | **−2.2° a lo largo del brazo** | I (valor de familia) |
| Atomizadores | barra bajo cada brazo trasero con **2 atomizadores en V**: exterior (estándar) en Y = ±0.900 (1800 mm), interior (opcional) 0.36 m hacia dentro a lo largo del brazo; discos 0.29 m sobre el suelo | P (1800 mm) + S (fotos 7493–7499, `T55_REAR_DOWN`) |
| V de los atomizadores | ±10° respecto al eje del motor (exterior: parte baja hacia fuera) | **I**: las fotos oblicuas no permiten medirla; conviene medirla |
| Chequeos | diagonal 2439 mm, sobre 3150 × 3520 mm, altura 934 mm; 1 sólido, mallas limpias, 0 interferencias | `_build_report.json` |

Fotos del propietario convertidas a JPG en `T55_reference/DJI_T55_png/`, con hojas de contacto en `DJI_T55_contact_*.png`.
