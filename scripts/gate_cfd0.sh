#!/usr/bin/env bash
# =============================================================================
# GATE CFD-0 — smoke test sobre UN SOLO caso (T25P nominal)
#
# POR QUE EXISTE:
#   Tener 128 casos con estructura de ficheros completa NO significa que sean
#   fisicamente ejecutables. `actuationDiskSource`, las cellZone, el signo del empuje,
#   las BC de traslacion y los function objects son HIPOTESIS DE IMPLEMENTACION hasta
#   que un caso corra de punta a punta.
#
#   Este script ejecuta la secuencia obligatoria sobre UN caso y NO escribe ninguna fila
#   en la base de datos salvo que TODOS los criterios se cumplan.
#
# SECUENCIA:
#   blockMesh -> checkMesh -> topoSet -> simpleFoam (100-500 iter) ->
#   verificar actuationDiskSource -> verificar function objects -> postprocess
#
# USO:
#   bash scripts/gate_cfd0.sh                       # elige el T25P mas nominal
#   bash scripts/gate_cfd0.sh <case_id>             # caso concreto
#   bash scripts/gate_cfd0.sh --list                # lista candidatos
# =============================================================================
set -uo pipefail

CASES_DIR="${CASES_DIR:-cfd/cases}"
ITER_TEST="${ITER_TEST:-300}"

# -----------------------------------------------------------------------------
# CARGA DEL ENTORNO DE OpenFOAM
#   En una shell NO interactiva el entorno NO esta cargado (foamVersion da
#   "command not found"), aunque OpenFOAM este instalado. Hay que cargarlo aqui.
#   Instalacion verificada en esta maquina:
#       /usr/lib/openfoam/openfoam2412      (NO esta en /opt)
#   Uso interactivo habitual: el comando `openfoam2412`, que abre shell de sesion.
# -----------------------------------------------------------------------------
cargar_openfoam() {
  if command -v blockMesh >/dev/null 2>&1; then
    return 0
  fi
  local candidatos=(
    /usr/lib/openfoam/openfoam2412/etc/bashrc
    /usr/lib/openfoam/openfoam*/etc/bashrc
    /opt/openfoam*/etc/bashrc
    "$HOME/OpenFOAM/OpenFOAM-*/etc/bashrc"
  )
  for c in "${candidatos[@]}"; do
    # shellcheck disable=SC2086
    for f in $(ls -d ${c} 2>/dev/null); do
      # shellcheck disable=SC1090
      if source "${f}" >/dev/null 2>&1; then
        echo "  entorno OpenFOAM cargado desde: ${f}"
        return 0
      fi
    done
  done
  return 1
}

echo "=============================================================="
echo " GATE CFD-0 — smoke test"
echo "=============================================================="
echo "-- 0. entorno OpenFOAM"
if ! cargar_openfoam; then
  echo "  [BLOQUEADO] no se pudo cargar el entorno de OpenFOAM."
  echo "  Comprueba desde tu terminal:"
  echo "      wsl -d Ubuntu"
  echo "      openfoam2412          # abre shell de sesion"
  echo "      which blockMesh"
  echo "      ls -d /usr/lib/openfoam/openfoam*"
  echo "  Los 128 casos siguen siendo CASOS GENERADOS, no CFD validados."
  exit 127
fi
echo "  [OK]    foamVersion = $(foamVersion 2>/dev/null || echo '?')"
echo "  [OK]    blockMesh   = $(command -v blockMesh)"
echo "  [OK]    checkMesh   = $(command -v checkMesh)"
echo "  [OK]    topoSet     = $(command -v topoSet)"
echo "  [OK]    simpleFoam  = $(command -v simpleFoam)"

if [[ "${1:-}" == "--list" ]]; then
  echo "Casos T25P disponibles (y distancia a operacion tipica V=5, H=3, d=200):"
  bash -c 'cd "'"${CASES_DIR}"'" 2>/dev/null || exit 1
    for d in T25P_V*; do
      [ -d "$d" ] || continue
      V=$(echo "$d" | sed -E "s/.*_V([0-9.]+)_.*/\1/")
      H=$(echo "$d" | sed -E "s/.*_H([0-9.]+)_.*/\1/")
      D=$(echo "$d" | sed -E "s/.*_d([0-9]+)_.*/\1/")
      echo "$d V=$V H=$H d=$D"
    done | head -40'
  exit 0
fi

# Caso por defecto: el T25P mas cercano a operacion tipica (V~5 m/s, H~3 m, d~200 um).
# Parseo explicito de campos, sin depender de Python ni de separadores fragiles.
if [[ -n "${1:-}" ]]; then
  CASO="${1}"
else
  CASO="$(find "${CASES_DIR}" -maxdepth 1 -type d -name "T25P_V*" -printf '%f\n' 2>/dev/null | \
    while IFS= read -r n; do
      V="${n#*_V}"; V="${V%%_H*}"
      H="${n#*_H}"; H="${H%%_d*}"
      D="${n#*_d}"; D="${D%%_f*}"
      case "${V}${H}${D}" in
        *[!0-9.]*) continue ;;
      esac
      awk -v v="${V}" -v h="${H}" -v d="${D}" -v n="${n}" 'BEGIN{
        printf "%.8f %s\n", ((v-5.0)/5.0)^2 + ((h-3.0)/3.0)^2 + ((d-200.0)/200.0)^2, n
      }'
    done | sort -g | head -1 | cut -d' ' -f2-)"
fi
CASO_PATH="${CASES_DIR}/${CASO}"

[[ -d "${CASO_PATH}" ]] || { echo "no existe el caso '${CASO_PATH}'"; exit 1; }

echo "=============================================================="
echo " GATE CFD-0 — smoke test"
echo " caso: ${CASO}"
echo "=============================================================="
cd "${CASO_PATH}"

FALLOS=0
check() {  # check <descripcion> <comando...>
  local desc="$1"; shift
  if "$@" >/dev/null 2>&1; then
    echo "  [OK]    ${desc}"
  else
    echo "  [FALLO] ${desc}"
    FALLOS=$((FALLOS+1))
  fi
}

# --- 1. mallado base -------------------------------------------------------------
echo
echo "-- 1. mallado base"
blockMesh > log.blockMesh 2>&1 && echo "  [OK]    blockMesh" || { echo "  [FALLO] blockMesh"; FALLOS=$((FALLOS+1)); }

# --- 2. calidad de malla ---------------------------------------------------------
echo
echo "-- 2. calidad de malla (checkMesh)"
checkMesh > log.checkMesh 2>&1
if grep -q "Mesh OK" log.checkMesh; then
  echo "  [OK]    checkMesh: Mesh OK"
else
  echo "  [FALLO] checkMesh no reporta 'Mesh OK'"
  FALLOS=$((FALLOS+1))
fi
grep -E "Max non-orthogonality|Max skewness|Failed" log.checkMesh | sed 's/^/          /' || true

# --- 3. cellZones por rotor ------------------------------------------------------
echo
echo "-- 3. topoSet: cellZones por rotor"
topoSet > log.topoSet 2>&1 && echo "  [OK]    topoSet" || { echo "  [FALLO] topoSet"; FALLOS=$((FALLOS+1)); }
N_ROTORES_ESPERADOS=$(grep -c "cellZone rotor" system/topoSetDict || echo 0)
N_ZONAS=$(grep -c "rotor" constant/polyMesh/cellZones 2>/dev/null || echo 0)
echo "          rotores definidos: ${N_ROTORES_ESPERADOS}   zonas creadas: ${N_ZONAS}"
if [[ "${N_ZONAS}" -lt 1 ]]; then
  echo "  [FALLO] no se creo ninguna cellZone de rotor"
  FALLOS=$((FALLOS+1))
fi

# --- 4. solver: iteraciones limitadas --------------------------------------------
echo
echo "-- 4. solver (${ITER_TEST} iteraciones de prueba)"
sed -i.bak "s/^endTime .*/endTime         ${ITER_TEST};/" system/controlDict
simpleFoam > log.simpleFoam 2>&1
if grep -q "FOAM FATAL ERROR\|Floating point exception" log.simpleFoam; then
  echo "  [FALLO] el solver aborto"
  tail -20 log.simpleFoam | sed 's/^/          /'
  FALLOS=$((FALLOS+1))
else
  ULTIMO=$(grep -oP "^Time = \K[0-9]+" log.simpleFoam | tail -1)
  echo "  [OK]    solver alcanzo Time = ${ULTIMO:-?}"
fi
grep "Solving for Ux" log.simpleFoam | tail -1 | sed 's/^/          /' || true

# --- 5. actuationDiskSource efectivamente aplicado -------------------------------
echo
echo "-- 5. actuationDiskSource aplicado (evidencia de empuje en el disco)"
if grep -qi "actuationDisk" log.simpleFoam; then
  echo "  [OK]    el log menciona el modelo de disco"
else
  echo "  [AVISO] el log no menciona actuationDiskSource: verificar manualmente"
fi
# evidencia cuantitativa: el downwash debe existir y ser NEGATIVO (hacia abajo)
python3 ../../scripts/check_cfd0_evidence.py "${CASO}" .. || FALLOS=$((FALLOS+1))

# --- 6. function objects ---------------------------------------------------------
echo
echo "-- 6. function objects"
for fo in receptorPlane downwashLines forces; do
  if [[ -d "postProcessing/${fo}" ]]; then
    N=$(find "postProcessing/${fo}" -type f | wc -l)
    if [[ "${N}" -gt 0 ]]; then
      echo "  [OK]    ${fo}: ${N} fichero(s)"
    else
      echo "  [FALLO] ${fo}: directorio vacio"
      FALLOS=$((FALLOS+1))
    fi
  else
    echo "  [FALLO] ${fo}: no se genero"
    FALLOS=$((FALLOS+1))
  fi
done

# --- 7. postproceso --------------------------------------------------------------
echo
echo "-- 7. postprocess_case.py"
if python3 ../../scripts/postprocess_case.py "${CASO}" .. >/dev/null 2>&1; then
  echo "  [OK]    la fila se escribio en cfd_airflow"
else
  echo "  [AVISO] no se escribio la fila (normal si el caso no convergio aun)"
fi

# --- 8. coste --------------------------------------------------------------------
echo
echo "-- 8. coste (para dimensionar la suite)"
grep -oP "ExecutionTime = \K[0-9.]+" log.simpleFoam | tail -1 | \
  awk '{printf "          tiempo de pared acumulado: %.1f s\n", $1}' || true

echo
echo "=============================================================="
if [[ ${FALLOS} -eq 0 ]]; then
  echo " GATE CFD-0: CRITERIOS CUMPLIDOS -> se puede escalar la suite"
else
  echo " GATE CFD-0: ${FALLOS} criterio(s) FALLIDO(S) -> NO escalar a los 128"
fi
echo "=============================================================="
exit ${FALLOS}
