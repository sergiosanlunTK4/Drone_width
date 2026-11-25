#!/usr/bin/env bash
# Generado por scripts/build_case_suite.py (geometria v2.0).
# Uso: python3 scripts/foam_run.py bash cfd/cases/<air_id>/Allrun.sh   (desde la raiz)
set -euo pipefail
CASO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RAIZ="$(cd "$CASO/../../.." && pwd)"
cd "$CASO"
NP=${NP:-8}
paso() { echo "== $(date -Is) $*"; }
# marcador propio: snappyHexMesh ya crea un cellZones vacio, asi que no sirve de indicador
if [[ ! -f constant/polyMesh/.malla_v2_ok ]]; then
  paso blockMesh;               blockMesh > log.blockMesh 2>&1
  paso surfaceFeatureExtract;   surfaceFeatureExtract > log.surfaceFeatureExtract 2>&1
  paso snappyHexMesh;           snappyHexMesh -overwrite > log.snappyHexMesh 2>&1
  paso topoSet;                 topoSet > log.topoSet 2>&1
  date -Is > constant/polyMesh/.malla_v2_ok
fi
paso checkMesh
checkMesh -constant > log.checkMesh 2>&1 || true
if ! grep -q "Mesh OK" log.checkMesh; then echo "[FALLO] checkMesh no da 'Mesh OK'"; exit 2; fi
paso volumenes de zona y fuente prescrita
python3 "$RAIZ/scripts/mesh_zone_volumes.py" --case "$CASO" --write > log.zoneVolumes 2>&1
python3 "$RAIZ/scripts/build_prescribed_momentum.py" --case "$CASO" > log.prescribedMomentum 2>&1
grep -q vectorSemiImplicitSource constant/fvOptions || { echo "[FALLO] sin fuente prescrita"; exit 3; }
# reanudacion: si una ejecucion previa se corto, recuperar su ultimo tiempo escrito
ULT=$(ls -d processor0/[0-9]* 2>/dev/null | xargs -n1 basename 2>/dev/null | sort -g | tail -1 || true)
if [[ -n "${ULT:-}" && "$ULT" != "0" ]]; then
  paso "reanudacion desde t=$ULT (reconstructPar)"
  reconstructPar -latestTime > log.reconstructPar.reanudar 2>&1
  [[ -f log.simpleFoam ]] && mv log.simpleFoam "log.simpleFoam.hasta_t$ULT"   # conservar la historia previa
fi
paso decomposePar
rm -rf processor*
foamDictionary -entry numberOfSubdomains -set $NP system/decomposeParDict > /dev/null
decomposePar -force -latestTime > log.decomposePar 2>&1
paso simpleFoam x$NP
mpirun --oversubscribe -np $NP simpleFoam -parallel > log.simpleFoam 2>&1
paso reconstructPar
reconstructPar -latestTime > log.reconstructPar 2>&1
rm -rf processor*
paso fin
