"""
Autotest de la QA de mediciones: inyecta problemas CONOCIDOS y comprueba que los detecta.

Una QA que no se ha probado no vale nada. Este script escribe un CSV desechable con casos
deliberados, ejecuta la QA sobre el, restaura el CSV real y deja el resultado a la vista.

Casos inyectados (deben detectarse TODOS):
  1. pareja opuesta FL<->RR correcta            -> residuo ~0, vector completo OK
  2. pareja opuesta FR<->RL con residuo 3D      -> RESIDUO GRANDE (distinto en X, Y y Z)
  3. fila M sin uncertainty ni instrument       -> marcada
  4. fila sin reference_frame                   -> marcada
  5. repeticiones con el MISMO setup_id         -> aviso "mide resolucion, no repetibilidad"
  6. repeticiones con setup_id distinto         -> dispersion calculable
  7. cota de separacion de ejes                 -> cierre vs wheelbase declarado
  8. rotor sin position_role                    -> aviso

Uso:
  python scripts/selftest_measurement_qa.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REAL = ROOT / "data" / "raw" / "mediciones_geometria.csv"
TMP = ROOT / "data" / "raw" / "_selftest_mediciones.csv"

CAB = ("uav,block,element_id,position_role,parameter,value,unit,uncertainty,method,"
       "instrument,timestamp,operator,source_class,reference_frame,configuracion,"
       "repetitions,setup_id,raw_file,notes")

# Convencion interna: R1=FL, R2=RL, R3=RR, R4=FR  (vista cenital, +X adelante, +Y izquierda)
FILAS = [
    # 1) FL <-> RR correctos: suma del vector ~0
    "T25P,rotor,R1,FL,posicion_x,0.6965,m,±0.005,cinta,cinta 5m,2026-09-20T10:00:00,D,M,CG_tank50,2atm,1,S1,foto_cenital.jpg,foto cenital con etiquetas y flecha +X",
    "T25P,rotor,R1,FL,posicion_y,0.6965,m,±0.005,cinta,cinta 5m,2026-09-20T10:01:00,D,M,CG_tank50,2atm,1,S1,,ok",
    "T25P,rotor,R1,FL,posicion_z,0.0050,m,±0.005,nivel,nivel digital,2026-09-20T10:02:00,D,M,CG_tank50,2atm,1,S1,,ok",
    "T25P,rotor,R3,RR,posicion_x,-0.6965,m,±0.005,cinta,cinta 5m,2026-09-20T10:05:00,D,M,CG_tank50,2atm,1,S1,,ok",
    "T25P,rotor,R3,RR,posicion_y,-0.6965,m,±0.005,cinta,cinta 5m,2026-09-20T10:06:00,D,M,CG_tank50,2atm,1,S1,,ok",
    "T25P,rotor,R3,RR,posicion_z,0.0050,m,±0.005,nivel,nivel digital,2026-09-20T10:07:00,D,M,CG_tank50,2atm,1,S1,,ok",
    # 2) FR <-> RL con residuo 3D deliberado (X: -30 mm, Y: +20 mm, Z: +10 mm)
    "T25P,rotor,R4,FR,posicion_x,0.6965,m,±0.005,cinta,cinta 5m,2026-09-20T10:10:00,D,M,CG_tank50,2atm,1,S1,,ok",
    "T25P,rotor,R4,FR,posicion_y,-0.6965,m,±0.005,cinta,cinta 5m,2026-09-20T10:11:00,D,M,CG_tank50,2atm,1,S1,,ok",
    "T25P,rotor,R4,FR,posicion_z,0.0050,m,±0.005,nivel,nivel digital,2026-09-20T10:12:00,D,M,CG_tank50,2atm,1,S1,,ok",
    "T25P,rotor,R2,RL,posicion_x,-0.7265,m,±0.005,cinta,cinta 5m,2026-09-20T10:15:00,D,M,CG_tank50,2atm,1,S1,,ok",
    "T25P,rotor,R2,RL,posicion_y,0.7165,m,±0.005,cinta,cinta 5m,2026-09-20T10:16:00,D,M,CG_tank50,2atm,1,S1,,ok",
    "T25P,rotor,R2,RL,posicion_z,0.0150,m,±0.005,nivel,nivel digital,2026-09-20T10:17:00,D,M,CG_tank50,2atm,1,S1,,ok",
    # 3) fila M sin uncertainty NI instrument (ambos vacios: dos marcas independientes)
    "T25P,rotor,R1,FL,diametro,1.270,m,,cinta,,2026-09-20T10:20:00,D,M,CG_tank50,2atm,1,S1,,sin trazabilidad",
    # 4) fila sin reference_frame
    "T25P,mass,R1,FL,measured_total_mass_kg,33.10,kg,±0.02,bascula,bascula 60kg,2026-09-20T11:00:00,D,M,,2atm,1,S1,,pesada real",
    # 5) repeticiones con MISMO setup_id -> no es repetibilidad
    "T25P,mass,R1,FL,nominal_total_mass_kg,33.0,kg,E,derivado,-,2026-09-20T11:05:00,D,E,CG_tank50,2atm,1,S1,,nominal",
    "T25P,mass,R1,FL,nominal_total_mass_kg,33.0,kg,E,derivado,-,2026-09-20T11:06:00,D,E,CG_tank50,2atm,1,S1,,nominal",
    # 6) repeticiones con setup distinto -> dispersion calculable
    "T25P,geometry,,,separacion_ejes_opuestos_x,1.975,m,±0.005,cinta,cinta 5m,2026-09-20T12:00:00,D,M,CG_tank50,2atm,1,S1,,opuestos",
    "T25P,geometry,,,separacion_ejes_opuestos_x,1.981,m,±0.005,cinta,cinta 5m,2026-09-20T12:10:00,D,M,CG_tank50,2atm,1,S2,,recolocado",
    # 8) rotor sin position_role
    "T25P,rotor,R9,,posicion_x,0.1,m,±0.005,cinta,cinta 5m,2026-09-20T12:30:00,D,M,CG_tank50,2atm,1,S1,,sin rol",
]

ESPERADOS = [
    "RESIDUO GRANDE",
    "fila M sin uncertainty",
    "fila M sin instrument",
    "fila sin reference_frame",
    "MISMO setup_id",
    "separacion_ejes_opuestos_x",
    "sin position_role",
    "reference_frame 'CG_tank50'",
]


def main() -> int:
    TMP.write_text(CAB + "\n" + "\n".join(FILAS) + "\n", encoding="utf-8")
    backup = ROOT / "data" / "raw" / "_selftest_backup.csv"
    shutil.copy2(REAL, backup)
    salida = ""
    try:
        shutil.copy2(TMP, REAL)
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "audit_measurement_csv.py"),
                            "--uav", "T25P"], capture_output=True, text=True, encoding="utf-8")
        salida = r.stdout
        print(salida)
        if r.stderr.strip():
            print("STDERR:", r.stderr[:600])
    finally:
        shutil.copy2(backup, REAL)
        backup.unlink()
        TMP.unlink()

    print("=" * 80)
    print("VERIFICACION DEL AUTOTEST")
    print("=" * 80)
    fallos = []
    for e in ESPERADOS:
        ok = e in salida
        print(f"  {'OK   ' if ok else 'FALLO'}  detecta: {e}")
        if not ok:
            fallos.append(e)
    filas_reales = len(REAL.read_text(encoding="utf-8").splitlines()) - 1
    print(f"\n  CSV real restaurado: {filas_reales} filas")
    if fallos:
        print(f"\n  {len(fallos)} comprobacion(es) NO detectada(s).")
        return 1
    print(f"\n  Las {len(ESPERADOS)} comprobaciones se detectan. QA operativa.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
