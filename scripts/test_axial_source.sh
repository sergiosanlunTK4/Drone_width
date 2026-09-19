#!/usr/bin/env bash
# =============================================================================
# TEST AXIAL CONTROLADO — prueba unitaria de actuationDiskSource
#
# QUE PRUEBA:
#   La hipotesis de que `actuationDiskSource` (metodo Froude) calcula el empuje a
#   partir del FLUJO INCIDENTE AXIAL:
#       T = 2 rho A |Uo . n|^2 a (1-a)
#   Si el caso nominal tiene flujo HORIZONTAL y los discos con normal VERTICAL,
#   entonces Uo . n ~ 0  =>  T ~ 0,  y el downwash es nulo POR FORMULACION,
#   no por resolucion de malla.
#
# COMO LO PRUEBA:
#   Copia el caso nominal a un directorio TEMPORAL, cambia la direccion del flujo de
#   entrada a VERTICAL (0 0 -V) y vuelve a correr. Si el empuje es funcion de U.n,
#   ahora T != 0 y debe aparecer Uz distinto de cero.
#
#   NO es un caso fisico del dron: el flujo vertical no representa vuelo nivelado.
#   Es una PRUEBA UNITARIA del modelo de OpenFOAM. El caso real no se toca.
#
# USO:
#   bash scripts/test_axial_source.sh
# =============================================================================
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROYECTO="$(cd "${SCRIPT_DIR}/.." && pwd)"
CASO="${1:-T25P_V3.1_H2.8_d190_f0.95_a4}"
ORIGEN="${PROYECTO}/cfd/cases/${CASO}"
TMP="${PROYECTO}/cfd/cases/_test_axial_${CASO}"

command -v blockMesh >/dev/null 2>&1 || {
  echo "entorno OpenFOAM no cargado"; exit 127
}

echo "=============================================================="
echo " TEST AXIAL CONTROLADO (prueba unitaria, NO caso fisico)"
echo "=============================================================="
echo " caso origen: ${CASO}"

rm -rf "${TMP}"
mkdir -p "${TMP}"
cp -r "${ORIGEN}/." "${TMP}/"
cd "${TMP}"
rm -f log.* ; rm -rf postProcessing processor* constant/polyMesh [1-9]* 2>/dev/null

# --- leer la V del caso y convertir el flujo a VERTICAL -------------------------
V=$(grep -m1 "internalField   uniform" 0/U | sed -E 's/.*\(([-0-9.]+) .*/\1/')
echo " V del caso nominal   : ${V} m/s"
echo " flujo nominal        : (${V} 0 0)   [horizontal]"
echo " flujo del test       : (0 0 -${V})  [axial, VERTICAL]"

# 0/U: inlet y campo interno pasan a vertical
sed -i "s/uniform (${V} 0 0)/uniform (0 0 -${V})/g" 0/U
# 0/p y 0/k/0/omega no cambian

echo
echo "-- ejecutando (blockMesh, topoSet, simpleFoam 300 iter)"
blockMesh > log.blockMesh 2>&1 || { echo "FALLO blockMesh"; exit 1; }
topoSet    > log.topoSet 2>&1    || { echo "FALLO topoSet";    exit 1; }
sed -i.bak 's/^endTime .*/endTime         300;/' system/controlDict
simpleFoam > log.simpleFoam 2>&1

echo
echo "-- convergencia"
grep -E "SIMPLE solution converged|FOAM FATAL" log.simpleFoam | head -3
grep "Solving for Uz" log.simpleFoam | tail -1

echo
echo "-- avisos de fvOptions"
grep -i "actuationDisk\|No cells selected" log.simpleFoam | head -6

echo
echo "-- PERFIL BAJO EL ROTOR  (columnas: z  k  omega  Ux  Uy  Uz)"
PERFIL=$(find postProcessing/downwashLines -name '*.xy' | sort | tail -1)
if [[ -n "${PERFIL}" ]]; then
  echo "   fichero: ${PERFIL}"
  echo "   --- valores en el entorno del disco (z entre -0.5 y 1.0) ---"
  awk '$1 > -0.5 && $1 < 1.0 {printf "   z=%8.4f  Ux=%12.6f  Uy=%12.6f  Uz=%12.6f\n", $1, $4, $5, $6}' "${PERFIL}" | head -14
  echo
  echo "   --- resumen ---"
  awk 'BEGIN{uzmin=1e9;uzmax=-1e9} {if($6<uzmin)uzmin=$6; if($6>uzmax)uzmax=$6} END{printf "   Uz_min = %12.6f   Uz_max = %12.6f\n", uzmin, uzmax}' "${PERFIL}"
else
  echo "   [FALLO] no se genero el perfil"
fi

echo
echo "-- fuerzas sobre el suelo"
FORZ=$(find postProcessing/forces -name 'forces.dat' 2>/dev/null | head -1)
[[ -n "${FORZ}" ]] && tail -1 "${FORZ}"

echo
echo "=============================================================="
echo " INTERPRETACION"
echo "=============================================================="
cat <<'EOT'
 Si el flujo axial produce Uz claramente distinto de cero (y/o cambian las fuerzas),
 quede demostrado que el empuje del actuationDiskSource es funcion de U.n.

   -> El Uz~0 del caso nominal NO es un problema de malla: es de FORMULACION.
   -> actuationDiskSource/Froude NO implementa la arquitectura C->B (empuje prescrito).
   -> Hay que sustituirlo por una fuente de momento que imponga
          integral_V f dV = T_i
      con independencia del flujo incidente.

 Si el flujo axial TAMBIEN da Uz ~ 0, la hipotesis se refuta y hay que buscar en otra
 parte (diskDir mal interpretado, cellZone sin celdas efectivas, etc.).
EOT
