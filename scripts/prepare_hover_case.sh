#!/usr/bin/env bash
# =============================================================================
# PREPARA EL CASO DE HOVER EN EL REPOSITORIO, EN EL ORDEN CORRECTO
#
# POR QUE HACE FALTA UN SCRIPT DE ORQUESTACION
#   `build_hover_case.py` copia el arbol del caso base con `copytree`, y eso sobrescribe
#   TODO, incluido `system/blockMeshDict`. Si se remalla primero y se parchea despues, el
#   parcheo restaura la malla asimetrica del caso base y se pierde el remallado. Ese error
#   ocurrio de verdad dos veces.
#
#   El orden obligatorio es:
#     1. copiar    -> trae la estructura (malla asimetrica del caso base)
#     2. remallar  -> dominio simetrico + cellZones + V_zone + fuente prescrita
#     3. --no-copy -> parchea BC y regenera controlDict SIN tocar malla ni fuente
#
#   Los pasos 2 y 3 necesitan Python. El paso 2 necesita OpenFOAM (blockMesh/topoSet), asi
#   que este script se lanza con el envoltorio de entorno:
#       python3 scripts/foam_run.py bash scripts/prepare_hover_case.sh
#   Si no hay entorno OpenFOAM, se hacen solo los pasos 1 y 3 y se avisa de que la malla
#   sigue siendo la del caso base.
#
# USO
#   python3 scripts/foam_run.py bash scripts/prepare_hover_case.sh
# =============================================================================
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROYECTO="$(cd "${SCRIPT_DIR}/.." && pwd)"
CASO_BASE="${1:-T25P_V3.1_H2.8_d190_f0.95_a4}"
CASO="${CASO_BASE}_HOVER_U0"

cd "${PROYECTO}" || exit 1

echo "=============================================================="
echo " PREPARACION DEL CASO DE HOVER  -  ${CASO}"
echo "=============================================================="

echo
echo "-- 1. copiar desde el caso base"
python3 scripts/build_hover_case.py --from "${CASO_BASE}" > /dev/null || {
  echo "  [FALLO] no se pudo copiar el caso base"; exit 1; }
echo "  [OK] arbol copiado"

echo
echo "-- 2. remallar el dominio simetrico"
if command -v blockMesh >/dev/null 2>&1; then
  bash scripts/remesh_hover_symmetric.sh "${CASO}" 2>&1 | \
    grep -E "dominio:|divisiones:|blockMesh|checkMesh|topoSet|rotor1 |suma vectorial|FALLO"
  FALLO_REMESH=${PIPESTATUS[0]}
  if [[ "${FALLO_REMESH}" -ne 0 ]]; then
    echo "  [FALLO] el remallado no termino bien"; exit 1
  fi
  REMESH=si
else
  echo "  [AVISO] sin entorno OpenFOAM: se OMITE el remallado."
  echo "          La malla sera la del caso base (x en [-6,14], ASIMETRICA)."
  echo "          Para remallar: python3 scripts/foam_run.py bash scripts/prepare_hover_case.sh"
  REMESH=no
fi

echo
echo "-- 3. parchear condiciones de contorno (sin recopiar)"
python3 scripts/build_hover_case.py --no-copy --from "${CASO_BASE}" | tail -9

echo
echo "-- 4. verificacion final del caso"
python3 - "$CASO" <<'PY'
import re, sys
from pathlib import Path

caso = Path("cfd/cases") / sys.argv[1]
problemas = []

# controlDict balanceado y sin funciones obsoletas
cd = (caso / "system" / "controlDict").read_text(encoding="utf-8")
if cd.count("{") != cd.count("}"):
    problemas.append(f"controlDict desbalanceado: {cd.count('{')} vs {cd.count('}')}")
for viejo in ("momInlet", "momOutlet", "uRef", "pLados"):
    if viejo in cd:
        problemas.append(f"controlDict conserva la funcion obsoleta {viejo}")
if not re.search(r"^\s+volumeMode\s+specific\s*;", (caso / "constant" / "fvOptions")
                 .read_text(encoding="utf-8"), re.M):
    problemas.append("la fuente no usa volumeMode specific")

# malla
bm = (caso / "system" / "blockMeshDict").read_text(encoding="utf-8")
v = re.findall(r"\(\s*(-?[0-9.]+)\s+(-?[0-9.]+)\s+(-?[0-9.]+)\s*\)", bm)
if v:
    xs = sorted({float(a) for a, b, c in v[:4]})
    print(f"  dominio x: {xs}")
    if abs(xs[0] + xs[-1]) > 1e-9:
        problemas.append(f"dominio NO simetrico en x: {xs}")

# BC
u = (caso / "0" / "U").read_text(encoding="utf-8")
if u.count("type slip") < 4:
    problemas.append("U: no todos los parches cerrados son slip")
if "type noSlip" not in u:
    problemas.append("U: el suelo no es noSlip")
p = (caso / "0" / "p").read_text(encoding="utf-8")
if p.count("fixedValue") != 1:
    problemas.append(f"p: {p.count('fixedValue')} salidas de presion, se exige 1")

# ficheros clave
for f in ("constant/fvOptions", "constant/rotorZoneVolumes",
          "constant/polyMesh/cellZones"):
    if not (caso / f).exists():
        problemas.append(f"falta {f}")

if problemas:
    print("  [FALLO] el caso no esta bien preparado:")
    for x in problemas:
        print(f"    - {x}")
    sys.exit(1)
print("  [ok] controlDict balanceado, fuente en specific, malla y BC coherentes")
PY

echo
echo "=============================================================="
if [[ "${REMESH}" == "si" ]]; then
  echo " CASO DE HOVER LISTO -> ejecutar el gate:"
  echo "   python3 scripts/foam_run.py bash scripts/gate_cfd0_hover.sh ${CASO}"
else
  echo " CASO COPIADO PERO NO REMALLADO (sin OpenFOAM)."
  echo " Reejecuta este script con el envoltorio para remallar."
fi
echo "=============================================================="
