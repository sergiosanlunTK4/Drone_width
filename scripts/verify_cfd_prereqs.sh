#!/usr/bin/env bash
# =============================================================================
# VERIFICACION DE PREREQUISITOS DE CFD-0  —  ejecutar ANTES del smoke test
#
# POR QUE EXISTE:
#   Antes de lanzar el gate hay que confirmar el entorno con comandos manuales.
#   El diagnostico previo "OpenFOAM no esta instalado" era ERRONEO: lo que fallaba
#   era el acceso del agente a WSL. Esta verificacion separa las dos cosas.
#
# QUÉ COMPRUEBA (en este orden, sin asumir nada):
#   1. entorno OpenFOAM cargado (o localizado y cargado)
#   2. los cinco ejecutables
#   3. herramientas auxiliares que necesitan los scripts (python3, awk, sort)
#   4. ruta del proyecto y sus ficheros clave
#   5. un caso T25P disponible y su eleccion por cercania a operacion tipica
#
# USO (desde tu terminal, dentro de WSL):
#   cd /mnt/c/Users/Dimasur/Downloads/AUTOMATIONS/DRONEWITH
#   bash scripts/verify_cfd_prereqs.sh
# =============================================================================
set -uo pipefail

FALLOS=0
ok()    { echo "  [OK]      $*"; }
aviso() { echo "  [AVISO]   $*"; }
fallo() { echo "  [FALLO]   $*"; FALLOS=$((FALLOS+1)); }

echo "======================================================================"
echo " VERIFICACION DE PREREQUISITOS — CFD-0"
echo "======================================================================"
echo
echo "-- 1. Sistema"
echo "  usuario : $(whoami)"
echo "  host    : $(uname -n)"
echo "  kernel  : $(uname -r)"
echo "  bash    : ${BASH_VERSION}"

echo
echo "-- 2. Entorno OpenFOAM"
if command -v blockMesh >/dev/null 2>&1; then
  ok "blockMesh ya esta en PATH"
else
  aviso "blockMesh NO esta en PATH; intentando cargar el entorno..."
  CARGADO=0
  for f in $(ls -d /usr/lib/openfoam/openfoam*/etc/bashrc \
                  /opt/openfoam*/etc/bashrc \
                  "$HOME"/OpenFOAM/OpenFOAM-*/etc/bashrc 2>/dev/null); do
    if source "${f}" >/dev/null 2>&1; then
      ok "entorno cargado desde: ${f}"
      CARGADO=1
      break
    fi
  done
  if [[ ${CARGADO} -eq 0 ]]; then
    fallo "no se encontro ningun etc/bashrc de OpenFOAM"
    echo "          Busca la instalacion con:"
    echo "            ls -d /usr/lib/openfoam/openfoam*  /opt/openfoam*"
    echo "            find / -maxdepth 5 -name foamVersion 2>/dev/null"
  fi
fi

echo
echo "-- 3. Ejecutables requeridos"
for exe in blockMesh checkMesh topoSet simpleFoam foamVersion; do
  p="$(command -v "${exe}" 2>/dev/null || true)"
  if [[ -n "${p}" ]]; then ok "${exe} -> ${p}"; else fallo "${exe} no encontrado"; fi
done
v="$(foamVersion 2>/dev/null || true)"
[[ -n "${v}" ]] && echo "          foamVersion = ${v}"

echo
echo "-- 4. Herramientas auxiliares que usan los scripts"
for t in awk sort cut find ls; do
  command -v "${t}" >/dev/null 2>&1 && ok "${t}" || fallo "${t} no encontrado"
done
if command -v python3 >/dev/null 2>&1; then
  ok "python3 -> $(command -v python3)  ($(python3 --version 2>&1))"
else
  fallo "python3 NO esta disponible"
  echo "          Es necesario para postprocess_case.py y check_cfd0_evidence.py."
  echo "          Instalalo con:  sudo apt update && sudo apt install -y python3"
fi
if command -v mpirun >/dev/null 2>&1; then
  ok "mpirun -> $(command -v mpirun)"
else
  aviso "mpirun no encontrado: el smoke test corre en serie (es suficiente para CFD-0)"
fi

echo
echo "-- 5. Proyecto y ficheros clave"
PWD_NOW="$(pwd)"
echo "  directorio actual: ${PWD_NOW}"
for f in scripts/gate_cfd0.sh scripts/check_cfd0_evidence.py \
         scripts/postprocess_case.py scripts/build_case_suite.py; do
  [[ -f "${f}" ]] && ok "${f}" || fallo "falta ${f} (¿estas en la raiz del proyecto?)"
done
N_CASOS=$(find cfd/cases -maxdepth 1 -type d -name "*_V*" 2>/dev/null | wc -l)
[[ "${N_CASOS}" -gt 0 ]] && ok "casos encontrados: ${N_CASOS}" \
                         || fallo "no hay casos en cfd/cases (ejecuta build_case_suite.py)"

echo
echo "-- 6. Caso T25P seleccionado"
CASO="$(find cfd/cases -maxdepth 1 -type d -name "T25P_V*" -printf '%f\n' 2>/dev/null | \
  while IFS= read -r n; do
    V="${n#*_V}"; V="${V%%_H*}"
    H="${n#*_H}"; H="${H%%_d*}"
    D="${n#*_d}"; D="${D%%_f*}"
    case "${V}${H}${D}" in *[!0-9.]*) continue ;; esac
    awk -v v="${V}" -v h="${H}" -v d="${D}" -v n="${n}" 'BEGIN{
      printf "%.8f %s\n", ((v-5.0)/5.0)^2 + ((h-3.0)/3.0)^2 + ((d-200.0)/200.0)^2, n}'
  done | sort -g | head -1 | cut -d' ' -f2-)"
if [[ -n "${CASO}" ]]; then
  ok "caso elegido (mas cercano a V=5, H=3, d=200): ${CASO}"
  for f in system/blockMeshDict system/controlDict system/topoSetDict \
           system/fvOptions 0/U 0/p 0/k 0/omega 0/nut; do
    [[ -f "cfd/cases/${CASO}/${f}" ]] && ok "  ${f}" || fallo "  falta ${f}"
  done
  N_ZONAS=$(grep -c "cellZone rotor" "cfd/cases/${CASO}/system/topoSetDict" 2>/dev/null || echo 0)
  echo "          cellZones de rotor definidas: ${N_ZONAS}"
else
  fallo "no se pudo seleccionar un caso T25P"
fi

echo
echo "======================================================================"
if [[ ${FALLOS} -eq 0 ]]; then
  echo " PREREQUISITOS COMPLETOS -> se puede lanzar el gate:"
  echo "     bash scripts/gate_cfd0.sh"
else
  echo " ${FALLOS} problema(s) detectado(s) -> resolver ANTES de lanzar el gate"
fi
echo "======================================================================"
exit ${FALLOS}
