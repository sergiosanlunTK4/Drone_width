#!/usr/bin/env bash
# =============================================================================
# GATE CFD-0 (HOVER) — prueba discriminante de la fuente de momento prescrita
#
# POR QUE ESTE SCRIPT Y NO `gate_cfd0.sh`
#   `gate_cfd0.sh` remalla desde cero y comprobaba `actuationDiskSource`. Ese modelo esta
#   RETIRADO (evidence/BUG_conceptual_06_actuationDisk.md). Este script corre el caso de
#   HOVER, que es el que discrimina:
#
#       con U_inf = 0 la fuerza prescrita NO puede venir del flujo incidente.
#       Si aparece downwash, la fuente implementa C -> B.
#       actuationDiskSource daba T ~ 0 aqui (Uz ~ 1e-7 m/s) y no puede pasar esta prueba.
#
#   NO remalla: reutiliza la malla y la cellZone ya verificadas, de modo que lo unico que
#   cambia respecto del caso base es la fuente y las condiciones de contorno.
#
# SECUENCIA
#   0. entorno OpenFOAM
#   1. coherencia de la fuente prescrita (Python, sin solver)
#   2. solver simpleFoam
#   3. verificacion sobre el CAMPO: fuerza integrada + downwash
#
# USO
#   python3 scripts/foam_run.py bash scripts/gate_cfd0_hover.sh
#   python3 scripts/foam_run.py bash scripts/gate_cfd0_hover.sh <case_id>
# =============================================================================
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROYECTO="$(cd "${SCRIPT_DIR}/.." && pwd)"
CASES_DIR="${CASES_DIR:-${PROYECTO}/cfd/cases}"
ITER_TEST="${ITER_TEST:-400}"
CASO="${1:-T25P_V3.1_H2.8_d190_f0.95_a4_HOVER_U0}"
CASO_PATH="${CASES_DIR}/${CASO}"

echo "=============================================================="
echo " GATE CFD-0 (HOVER) — fuente de momento prescrita"
echo "=============================================================="
echo "-- 0. entorno OpenFOAM"

if ! command -v simpleFoam >/dev/null 2>&1; then
  echo "  [BLOQUEADO] el entorno OpenFOAM no esta cargado en esta shell."
  echo
  echo "  Usa el lanzador (recomendado; NO hace source dentro del script, ese fue un bug):"
  echo "      python3 scripts/foam_run.py bash scripts/gate_cfd0_hover.sh"
  echo
  echo "  O carga el entorno a mano:"
  echo "      source /usr/lib/openfoam/openfoam2412/etc/bashrc"
  echo "      bash scripts/gate_cfd0_hover.sh"
  exit 127
fi
echo "  [OK] simpleFoam = $(command -v simpleFoam)"

if [[ ! -d "${CASO_PATH}" ]]; then
  echo "[FALLO] no existe el caso ${CASO_PATH}"
  echo "        construyelo con: python3 scripts/build_hover_case.py"
  exit 1
fi

if ! cd "${CASO_PATH}"; then
  echo "[FALLO] no se pudo entrar a ${CASO_PATH}"
  exit 1
fi
echo "  directorio de trabajo: $(pwd)"

FALLOS=0
check() {
  local desc="$1"; shift
  if "$@" >/dev/null 2>&1; then
    echo "  [OK]    ${desc}"
  else
    echo "  [FALLO] ${desc}"
    FALLOS=$((FALLOS+1))
  fi
}

# --- 1. coherencia de la fuente, ANTES de gastar computo ----------------------
echo
echo "-- 1. la fuente prescrita integra T_i (comprobacion algebraica)"
if python3 "${SCRIPT_DIR}/verify_prescribed_force.py" --case "${CASO_PATH}" > log.verify_source 2>&1; then
  echo "  [OK]    integral_{V_zone} f dV = T_i en los 4 rotores"
  grep -E "suma vectorial|T total prescrito" log.verify_source | sed 's/^/          /'
else
  echo "  [FALLO] la fuente no integra el empuje prescrito"
  cat log.verify_source | sed 's/^/          /'
  FALLOS=$((FALLOS+1))
fi

# --- 2. solver -----------------------------------------------------------------
echo
echo "-- 2. solver (${ITER_TEST} iteraciones)"
sed -i.bak "s/^endTime .*/endTime         ${ITER_TEST};/" system/controlDict
rm -f log.simpleFoam
simpleFoam > log.simpleFoam 2>&1

# Deteccion de fallo deliberadamente ESTRECHA. Un grep generico de
# "FOAM FATAL ERROR|Floating point exception" da un FALSO POSITIVO: el banner de arranque
# de OpenFOAM imprime
#     trapFpe: Floating point exception trapping enabled (FOAM_SIGFPE).
# que contiene la subcadena "Floating point exception" y hacia que un caso que termino
# correctamente se reportara como abortado. Se exige linea propia.
if grep -qE "^\s*FOAM FATAL" log.simpleFoam || grep -qE "^Floating point exception" log.simpleFoam; then
  echo "  [FALLO] el solver aborto"
  grep -nE "^\s*FOAM FATAL|^Floating point exception" log.simpleFoam | head -5 | sed 's/^/          /'
  tail -25 log.simpleFoam | sed 's/^/          /'
  FALLOS=$((FALLOS+1))
else
  ULTIMO=$(grep -oP "^Time = \K[0-9]+" log.simpleFoam | tail -1)
  echo "  [OK]    el solver alcanzo Time = ${ULTIMO:-?}"
  if grep -q "^End" log.simpleFoam; then
    echo "          terminacion limpia (linea 'End' presente)"
  else
    echo "          [AVISO] no hay linea 'End': terminacion no limpia"
  fi
  grep "Solving for Uz" log.simpleFoam | tail -1 | sed 's/^/          /' || true
  CONTINUITY=$(grep -oP "time = \K[0-9.eE+-]+" log.simpleFoam | tail -1)
  echo "          continuidad local final: ${CONTINUITY:-?}"
fi

# --- 3. verificacion sobre el CAMPO (la parte que discrimina) ------------------
echo
echo "-- 3. verificacion sobre el campo: fuerza + downwash"
if python3 "${SCRIPT_DIR}/verify_prescribed_force.py" \
      --case "${CASO_PATH}" --hover --exigir-downwash > log.verify_field 2>&1; then
  echo "  [OK]    la fuente materializa el empuje: aparece downwash con U_inf = 0"
  grep -E "Uz min en zonas|downwash|Uz media" log.verify_field | sed 's/^/          /'
else
  echo "  [FALLO] no se materializa el empuje en el campo"
  cat log.verify_field | sed 's/^/          /'
  FALLOS=$((FALLOS+1))
fi

# --- 3b. LAS CINCO CONDICIONES DE CIERRE DE CFD-0 -----------------------------
# No basta con que "haya downwash": hay que declarar explicitamente cada condicion y su
# resultado. Una condicion no comprobada no es una condicion cumplida.
echo
echo "-- 3b. condiciones de cierre de CFD-0 (una por una)"
python3 "${SCRIPT_DIR}/check_cfd0_conditions.py" "${CASO_PATH}" || FALLOS=$((FALLOS+1))

# --- 4. function objects -------------------------------------------------------
echo
echo "-- 4. function objects"
if [[ -d postProcessing/downwashRotor ]]; then
  N=$(find postProcessing/downwashRotor -type f | wc -l)
  echo "  [OK]    downwashRotor: ${N} fichero(s)"
else
  echo "  [FALLO] downwashRotor: no se genero"
  FALLOS=$((FALLOS+1))
fi
if [[ -d postProcessing/flujo_rotor1 ]]; then
  echo "  [OK]    flujo_rotor1: integral de U sobre la zona del disco"
else
  echo "  [AVISO] flujo_rotor1 no se genero (revisar volFieldValue)"
fi

# --- 5. diagnostico si algo fallo ---------------------------------------------
if [[ ${FALLOS} -gt 0 ]]; then
  echo
  echo "=============================================================="
  echo " DIAGNOSTICO: cola de log.simpleFoam"
  echo "=============================================================="
  tail -40 log.simpleFoam | sed 's/^/  /'
fi

echo
echo "=============================================================="
if [[ ${FALLOS} -eq 0 ]]; then
  echo " GATE CFD-0 (HOVER): CRITERIOS CUMPLIDOS"
  echo "   - la fuente integra T_i rotor por rotor"
  echo "   - aparece downwash con flujo incidente NULO"
  echo "   => la fuerza NO depende del flujo incidente: C -> B implementada"
  echo "   => actuationDiskSource queda refutado con evidencia, no por argumento"
else
  echo " GATE CFD-0 (HOVER): ${FALLOS} criterio(s) FALLIDO(S)"
fi
echo "=============================================================="
exit ${FALLOS}
