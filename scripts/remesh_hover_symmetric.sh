#!/usr/bin/env bash
# =============================================================================
# REMALLADO DEL CASO DE HOVER CON DOMINIO SIMETRICO EN HORIZONTAL
#
# POR QUE
#   Al ejecutar el caso de hover aparecio un defecto de planteamiento. El dominio de la
#   suite es x in [-6, 14], y in [-6, 6], z in [-H, 4]. En x el bloque de rotores (que ocupa
#   +-0.70 m) queda DESPLAZADO: 6 m aguas arriba y 14 m aguas abajo.
#
#   Medido en la ejecucion corregida: en el eje del rotor, Ux = +4.4 m/s a t=400 mientras
#   |Uz| = 6.0 m/s. La componente horizontal NO deberia existir: la unica direccion fisica
#   privilegiada es la vertical, por el suelo. Una deriva lateral de esa magnitud apunta a
#   asimetria del dominio, y x[-6,14] es exactamente eso.
#
#   El dominio original se dimensiono para vuelo en avance (estela aguas abajo), no para
#   hover, donde lo que gobierna es la recirculacion. El disco tiene 1.27 m de diametro, de
#   modo que 6 m laterales son ~4.7 D: ajustado.
#
#   NOTA sobre z: NO se simetriza en vertical. El problema SI es asimetrico respecto al
#   plano del rotor, porque hay un suelo. Lo unico que se corrige en z es dar mas espacio
#   por arriba para que la recirculacion se cierre lejos de la salida de presion.
#
# QUE HACE
#   1. dominio x in [-10,10], y in [-10,10], z in [-2.773, 5.0]   (simetrico en horizontal)
#   2. MISMO tamano de celda base, 0.25 m -> 80 x 80 x 32
#   3. rehace malla, cellZone de rotor y volumen de zona
#   4. regenera la fuente prescrita con los volumenes nuevos
#
#   El tamano de celda NO se cambia a proposito: la resolucion se evalua por separado. Si se
#   cambiara aqui no se sabria si una diferencia se debe al dominio o a la malla.
#
# USO
#   python3 scripts/foam_run.py bash scripts/remesh_hover_symmetric.sh
# =============================================================================
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROYECTO="$(cd "${SCRIPT_DIR}/.." && pwd)"
CASO="${1:-T25P_V3.1_H2.8_d190_f0.95_a4_HOVER_U0}"
CASO_PATH="${PROYECTO}/cfd/cases/${CASO}"

if ! command -v blockMesh >/dev/null 2>&1; then
  echo "  [BLOQUEADO] entorno OpenFOAM no cargado."
  echo "  Usa: python3 scripts/foam_run.py bash scripts/remesh_hover_symmetric.sh"
  exit 127
fi

if [[ ! -d "${CASO_PATH}" ]]; then
  echo "[FALLO] no existe ${CASO_PATH}"
  exit 1
fi

cd "${CASO_PATH}" || { echo "[FALLO] cd"; exit 1; }
echo "=============================================================="
echo " REMALLADO SIMETRICO EN HORIZONTAL  -  ${CASO}"
echo "=============================================================="

# --- 1. dominio simetrico en x e y, mismo tamano de celda ---------------------
# z0 se LEE del blockMeshDict actual para no inventar la altura del suelo.
python3 - <<'PY'
import re
from pathlib import Path

f = Path("system/blockMeshDict")
txt = f.read_text(encoding="utf-8")

m = re.search(r"\(\s*[-0-9.eE]+\s+[-0-9.eE]+\s+([-0-9.eE]+)\s*\)", txt[txt.index("vertices"):])
z0 = float(m.group(1)) if m else -2.773
z1 = 5.0
x0, x1 = -10.0, 10.0
y0, y1 = -10.0, 10.0
DX = 0.25
nx = round((x1 - x0) / DX)
ny = round((y1 - y0) / DX)
nz = round((z1 - z0) / DX)

nuevo = f"""scale 1;

vertices
(
    ({x0} {y0} {z0})
    ({x1} {y0} {z0})
    ({x1} {y1} {z0})
    ({x0} {y1} {z0})
    ({x0} {y0} {z1})
    ({x1} {y0} {z1})
    ({x1} {y1} {z1})
    ({x0} {y1} {z1})
);

blocks
(
    hex (0 1 2 3 4 5 6 7) ({nx} {ny} {nz}) simpleGrading (1 1 1)
);
"""
i = txt.index("scale")
j = txt.index("edges")
f.write_text(txt[:i] + nuevo + "\n" + txt[j:], encoding="utf-8")
print(f"  dominio: x[{x0},{x1}] y[{y0},{y1}] z[{z0},{z1}]")
print(f"  divisiones: {nx} x {ny} x {nz}  ->  {nx*ny*nz} celdas (celda base {DX} m)")
PY

# --- 2. locationInMesh coherente con el dominio nuevo -------------------------
python3 - <<'PY'
import re
from pathlib import Path
p = Path("system/snappyHexMeshDict")
if p.exists():
    t = p.read_text(encoding="utf-8")
    t = re.sub(r"locationInMesh\s*\([^)]*\)", "locationInMesh (5 0 1.5)", t)
    p.write_text(t, encoding="utf-8")
    print("  snappyHexMeshDict: locationInMesh -> (5 0 1.5)")
PY

# --- 3. limpieza y remallado --------------------------------------------------
echo
echo "-- remallado"
rm -rf constant/polyMesh postProcessing processor* log.* 2>/dev/null
for d in [1-9]*; do [[ -d "${d}" ]] && rm -rf "${d}"; done

blockMesh   > log.blockMesh 2>&1 && echo "  [OK] blockMesh" || { echo "  [FALLO] blockMesh"; tail -20 log.blockMesh; exit 1; }
checkMesh   > log.checkMesh 2>&1
if grep -q "Mesh OK" log.checkMesh; then
  echo "  [OK] checkMesh: Mesh OK"
else
  echo "  [AVISO] checkMesh no reporta 'Mesh OK'"
  grep -E "Failed|non-orthogonality" log.checkMesh | head -5
fi
grep -E "cells:" log.checkMesh | head -2 | sed 's/^/          /'

topoSet > log.topoSet 2>&1 && echo "  [OK] topoSet" || { echo "  [FALLO] topoSet"; tail -20 log.topoSet; exit 1; }

N_ZONAS=$(grep -c "rotor" constant/polyMesh/cellZones 2>/dev/null || echo 0)
echo "  [OK] cellZones escritas (menciones de 'rotor'): ${N_ZONAS}"

# --- 4. volumenes de zona desde la malla NUEVA --------------------------------
echo
echo "-- volumen de zonas de rotor"
python3 "${SCRIPT_DIR}/mesh_zone_volumes.py" --case "${CASO_PATH}" --write || exit 1

# --- 5. fuente prescrita con los volumenes nuevos -----------------------------
echo "-- fuente de momento prescrita"
python3 "${SCRIPT_DIR}/build_prescribed_momentum.py" --case "${CASO_PATH}" || exit 1

# --- 6. verificacion algebraica ----------------------------------------------
echo
echo "-- verificacion"
python3 "${SCRIPT_DIR}/verify_prescribed_force.py" --case "${CASO_PATH}" | tail -12

echo
echo "=============================================================="
echo " REMALLADO COMPLETO -> ejecutar el gate:"
echo "   python3 scripts/foam_run.py bash scripts/gate_cfd0_hover.sh ${CASO}"
echo "=============================================================="
