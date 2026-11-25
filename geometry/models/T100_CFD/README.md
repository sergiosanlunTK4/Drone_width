# DJI Agras T100 — modelo CFD (v2)

El sistema común, la terna de ejes, la inclinación, los archivos y el uso en OpenFOAM se describen en **[`../README_MODELOS_CFD.md`](../README_MODELOS_CFD.md)**. Los parámetros están en `scripts/agras_model/platforms/t100.py`. El modelo anterior está guardado en `_anterior_v1/`.

| Dato | Valor | Clase / fuente |
|---|---|---|
| Topología | **4 pares coaxiales = 8 rotores** 6223 | P-A ("hélices duales coaxiales") + M |
| Bujes (X, Y) | (±0.8238, ±0.8238) | M / P (diagonal 2330); confirmado en `T100_UP` (radio de hélice 404 px → 1.95 mm/px) |
| Planos de hélice | Z = ±0.145 (separación 0.290 m) | M; S en `T100_REAR`: 0.28–0.29 m |
| **Marco vertical** | plano medio coaxial a **0.73 m** del suelo (suelo Z = −0.73); radar a +0.25 | **S** (`T100_REAR` 0.743 y `T100_RIGHT` 0.720; suman los 975 mm oficiales). El modelo anterior usaba 0.625 m |
| Giro | FR sup. CCW / inf. CW · RR sup. CW · RL sup. CCW · FL sup. CW | M (por nombre de rotor) + P-A |
| **Inclinación del motor** | **−3.3° a lo largo del brazo** | S: columnas coaxiales traseras, lateral −2.17 ± 0.3° |
| Barra LS100 | a Z = −0.39; 4 cuerpos de atomizador | S |
| Atomizadores | exteriores (estándar) (−0.875, ±0.917); interiores (opcionales) (−0.775, ±0.4585); disco Z = −0.448 (0.28 m sobre el suelo) | **M**: ver la discrepancia más abajo |
| Tren | patines en Y = ±0.375, X −0.45 … +0.30 | S (el modelo anterior tenía 1.10 × 1.15 m) |
| Chequeos | diagonal 2330 mm, sobre 3247 mm (+0.8 %: los rotores inferiores inclinados sobresalen), altura 975 mm; 1 sólido, mallas limpias, 0 interferencias | `_build_report.json` |

> ⚠️ **Por confirmar: la X de los atomizadores.** En `t100_overlay_top.png`, los extremos de la barra LS100 de la foto cenital oficial caen en **X ≈ −0.58 m, Y ≈ ±0.86 m**, y la vista lateral da X ≈ −0.68 m. Tu medición dice −0.875 m, que los pone justo bajo el buje trasero. La diferencia (~0.2–0.3 m) cambia si la lámina de gotas nace bajo la estela del rotor o por dentro de ella. Se mantienen tus valores; para cambiarlos se edita `NOZZLES` en `t100.py`.

> 🔧 **Barra LS100, pendiente de corregir.** Según el propietario (2026-11-23), la barra real son **dos barras rectas** (una por lado) que **salen del tren de aterrizaje**, sin quiebros, con los dos atomizadores de cada lado sobre ella. El modelo actual la dibuja con quiebros y anclada al cuerpo. No se corrige hasta que el propietario vuelva a medir la distancia en X entre la pata trasera y cada atomizador: con las posiciones actuales, la barra recta no llega a la pata que muestran las fotos (ver `INSTRUCCIONES_CFD.md`, §7).
