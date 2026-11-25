# Casos conservados como evidencia (no son resultados)

- `A_T25P_V00.0_H2.5_f1.00_g2_cerrado_bug8`: primer CFD-0 v2 (Entries 019 y 021). BC "cerrado" (caja
  sellada) y fuente ρ veces mayor (bug #8). Las fuerzas oscilan y no convergen. Los tiempos 500 y 3000
  se borraron con permiso del propietario (2026-11-23); quedan los logs y `postProcessing`.
- `A_T25P_V00.0_H2.5_f1.00_g2_abierto_bug8`: el mismo caso con BC "abierto", todavía con el bug #8
  (Entry 022). Converge; el balance cierra al 0.5 % respecto a ρ·T. Es la evidencia del bug #8.
