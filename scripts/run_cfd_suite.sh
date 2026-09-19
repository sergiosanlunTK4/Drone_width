#!/usr/bin/env bash
# =============================================================================
# RUNNER DE LA SUITE CFD — ejecuta los casos generados por scripts/build_case_suite.py
#
# POR QUE EXISTE: el entorno de desarrollo NO tiene OpenFOAM (WSL no accesible), asi que
# los casos estan generados y validados estructuralmente pero NO ejecutados. Este script
# es la pieza que produce los datos reales cuando haya OpenFOAM disponible.
#
# ARQUITECTURA: C -> B (equilibrio fisico global + actuator disk con empuje prescrito)
#   Ver geometry/coaxial_thrust_split.md
#
# USO:
#   ./run_cfd_suite.sh                    # todos los casos, 8 en paralelo
#   ./run_cfd_suite.sh T100               # solo una plataforma
#   ./run_cfd_suite.sh T100 4             # plataforma y nº de procesos
#   ./run_cfd_suite.sh --dry-run          # solo comprobar los casos, sin ejecutar
# =============================================================================
set -euo pipefail

CASES_DIR="${CASES_DIR:-cfd/cases}"
NPROC="${2:-8}"
PLATFORM="${1:-all}"
DRY=0
[[ "${1:-}" == "--dry-run" ]] && { DRY=1; PLATFORM="all"; }

# -----------------------------------------------------------------------------
# ENTORNO DE OpenFOAM
#   NO se hace `source .../etc/bashrc` dentro del script: BUG ENCONTRADO
#   (2026-09-14) ese bashrc CORTA la ejecucion del script en seco.
#   Via correcta:  python3 scripts/foam_run.py bash scripts/run_cfd_suite.sh all 8
# -----------------------------------------------------------------------------
if ! command -v blockMesh >/dev/null 2>&1; then
  echo "=============================================================="
  echo " SUITE CFD: BLOQUEADA — entorno OpenFOAM no cargado"
  echo "=============================================================="
  echo " Cargalo primero:"
  echo "     source /usr/lib/openfoam/openfoam2412/etc/bashrc"
  echo "     bash scripts/run_cfd_suite.sh"
  echo " O usa el lanzador (recomendado):"
  echo "     python3 scripts/foam_run.py bash scripts/run_cfd_suite.sh all 8"
  echo "=============================================================="
  exit 127
fi

echo "==================================================================="
echo " SUITE CFD — arquitectura C (equilibrio) -> B (actuator disk)"
echo " casos en: ${CASES_DIR}"
echo " plataforma: ${PLATFORM}   procesos por caso: ${NPROC}"
echo "==================================================================="

mapfile -t CASOS < <(find "${CASES_DIR}" -maxdepth 1 -type d -name "*_V*_H*_d*" | sort)
[[ ${#CASOS[@]} -eq 0 ]] && { echo "No hay casos. Ejecuta: python scripts/build_case_suite.py"; exit 1; }

if [[ "${PLATFORM}" != "all" ]]; then
  mapfile -t CASOS < <(printf '%s\n' "${CASOS[@]}" | grep "/${PLATFORM}_")
fi

echo "Casos a procesar: ${#CASOS[@]}"
echo

FALLOS=0
EJECUTADOS=0

for caso in "${CASOS[@]}"; do
  nombre="$(basename "${caso}")"
  echo "--- ${nombre}"

  if [[ ${DRY} -eq 1 ]]; then
    # comprobacion estructural: los diccionarios necesarios existen
    faltan=0
    for f in system/blockMeshDict system/controlDict system/fvSchemes system/fvSolution \
             system/topoSetDict 0/U 0/p 0/k 0/omega 0/nut \
             constant/turbulenceProperties constant/transportProperties constant/fvOptions; do
      [[ -f "${caso}/${f}" ]] || { echo "    FALTA: ${f}"; faltan=1; }
    done
    [[ ${faltan} -eq 0 ]] && echo "    OK estructural"
    continue
  fi

  (
    cd "${caso}"
    # 1) malla base
    blockMesh > log.blockMesh 2>&1
    # 2) zonas de disco (una cellZone cilindrica por rotor)
    topoSet > log.topoSet 2>&1
    # 3) mallado del cuerpo si hay STL (opcional: sin STL se corre sobre blockMesh)
    if [[ -f constant/triSurface/model.stl ]]; then
      snappyHexMesh -overwrite > log.snappyHexMesh 2>&1
    fi
    # 4) solver en paralelo
    decomposePar -force > log.decomposePar 2>&1
    mpirun -np "${NPROC}" simpleFoam -parallel > log.simpleFoam 2>&1 || {
      echo "    FALLO en simpleFoam"; exit 1;
    }
    reconstructPar -latestTime > log.reconstructPar 2>&1
    # 5) extraccion de resultados a la base de datos
    python3 ../../scripts/postprocess_case.py "${nombre}" ../
  ) && EJECUTADOS=$((EJECUTADOS+1)) || { FALLOS=$((FALLOS+1)); echo "    FALLO"; }
done

echo
echo "==================================================================="
echo " ejecutados: ${EJECUTADOS}   fallos: ${FALLOS}"
echo "==================================================================="
echo
echo "SIGUIENTE PASO tras ejecutar:"
echo "  python scripts/audit_convergence.py      # independencia de malla y convergencia"
echo "  python scripts/build_database.py         # re-construye la DB con los resultados"
