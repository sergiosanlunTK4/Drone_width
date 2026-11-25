# Ficha — Guo et al. (2025)

**Guo, Q., Zhu, Y., Tang, Y., Hou, C., Fang, M., Chen, X. (2025).** *Numerical simulation of the effects of downwash airflow and crosswinds on the spray performance of quad-rotor agricultural UAVs.* Smart Agricultural Technology 11, 100940. doi:10.1016/j.atech.2025.100940 · Acceso abierto, CC BY 4.0.
PDF: `literature/1-s2.0-S277237552500173X-main.pdf` · Texto extraído: `texto.txt` (aportado por el propietario el 2026-11-22).

## Qué hace
- CFD 3D gas-líquido (Fluent 19.2) de un **cuadricóptero genérico pequeño**: 1 m entre ejes, rotores en (±0.5, ±0.5), hélices DJI 2880.
- **Variables:** velocidad 1–5 m/s, altura 2–4 m (cada 0.5 m) y viento cruzado 0–2 m/s.
- **Malla:** estructurada; independencia de malla de 51 a 253 millones de celdas, con la de **152 M** elegida. Servidor de 20 núcleos.
- **Gotas:** fase discreta Lagrangiana con dispersión turbulenta aleatoria, rotura TAB y arrastre dinámico, acoplada con el aire cada 10 iteraciones.
- **Boquillas:** **abanico plano a presión** (Lechler ST110-015), semiángulo de 55°, 0.00833 kg/s cada una, 4 boquillas 0.15 m bajo cada rotor. Gotas **monodispersas** de 50, 100 y 150 µm.
- **Validación:** túnel de viento a 1 y 2 m/s más banco de rotores. Papel hidrosensible 50 × 100 mm (7 líneas × 6 papeles, separación 0.5 m), escaneado a 600 dpi y analizado con DepositScan, a 22 °C y 70 % HR. **Error relativo medio del 27.2 % (1 m/s) y ~30 % (2 m/s).**

## Resultados principales
- A mayor velocidad, la estela se inclina hacia atrás y aumenta la deriva de las gotas pequeñas. **50 µm: 100 % de deriva a 3 m/s y 3 m de altura.**
- A mayor altura, las gotas pasan más tiempo en el aire y aumenta la deriva (con matices a 2 m por el efecto suelo).
- Recomiendan gotas medianas o grandes (100–150 µm).

## Qué aporta a nuestro proyecto
- **Antecedente directo** de H2 (V × H × d) y H6 (seguimiento del flujo según el tamaño de gota). Sirve de referencia para la discusión.
- **Referencia de error de validación publicable:** ~27–30 % con papel hidrosensible. Ayuda a fijar los criterios de comparación con el equipo de validación.
- **Referencia de coste:** resolvieron rotores en malla de 152 M celdas en un servidor de 20 núcleos. Nuestro portátil con WSL (8 núcleos, 7 GB) no puede reproducir eso, lo que **justifica los modelos de disco** (fuente prescrita / `rotorDiskSource`) para la base de datos masiva.
- **Hueco que cubrimos:** ellos usan un dron genérico, boquillas a presión, gotas de un solo tamaño y un máximo de 5 m/s. Nosotros: **4 plataformas DJI reales**, **atomizadores centrífugos**, espectro completo por superposición, hasta 20 m/s y la carga del tanque.

## Lo que NO aporta
- **No da el espectro de gota de atomizadores centrífugos** (ni de los DJI LX07550SX, LX09550SX o LX09050DX). El espectro sigue en **D**: hay que buscarlo en otra referencia o medirlo en bancada.
