#!/bin/bash
# Ejecuta las dos corridas de acoplamiento (uno, dos). Llamar via scripts/foam_run.py.
set -euo pipefail
NP=${NP:-6}
cd "$(dirname "$0")"
for c in C_*_uno C_*_dos; do
  [[ -f $c/log.kinematicParcelFoam && -n "$(grep -E '^End' $c/log.kinematicParcelFoam || true)" ]] && { echo "$c ya hecho"; continue; }
  ( cd $c
    rm -rf processor*
    foamDictionary -entry numberOfSubdomains -set $NP system/decomposeParDict > /dev/null
    decomposePar -force > log.decomposePar 2>&1
    echo "== $(date -Iseconds) $c kinematicParcelFoam x$NP"
    mpirun --oversubscribe -np $NP kinematicParcelFoam -parallel > log.kinematicParcelFoam 2>&1
    reconstructPar -latestTime > log.reconstructPar 2>&1
    rm -rf processor*
    echo "== $(date -Iseconds) $c fin" )
done
