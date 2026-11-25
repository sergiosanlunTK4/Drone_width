# Casos OBSOLETOS — geometría v1 (movidos el 2026-11-22)

Generados con `archive/scripts_geometria_v1/build_case_suite_v1.py`:
- planta "regular X" (hipótesis I), T55 y T70P tratados como coaxiales (falso: son 4 rotores);
- `diskDir (0 0 -1)`, sin inclinación de motor;
- cuerpo desde las cajas de control `geometry/models/<UAV>_control.stl`;
- aire entrando por x_min con U = (+V 0 0): en la terna v2 (+X adelante) es vuelo **hacia atrás**.

**No ejecutar ni postprocesar.** Se conservan solo por trazabilidad (Entries 016–018).
Los casos v2 están en `cfd/cases/A_*_g2/` y se gestionan desde `air_cases` en
`data/processed/dronewith.sqlite` (`scripts/build_scenario_db.py`, `scripts/run_queue.py`).
