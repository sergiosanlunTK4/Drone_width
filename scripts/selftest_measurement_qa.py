"""Prueba desechable: verifica que la QA detecta los problemas que dice detectar."""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REAL = ROOT / "data" / "raw" / "mediciones_geometria.csv"
TMP = ROOT / "data" / "raw" / "_test_mediciones.csv"

CAB = ("uav,block,element_id,parameter,value,unit,uncertainty,method,instrument,timestamp,"
       "operator,source_class,reference_frame,configuracion,repetitions,setup_id,raw_file,notes")

# Casos deliberadamente problematicos + un par simetrico que deberia salir con residuo ~0
FILAS = [
    # posiciones simetricas correctas (R1 y R3 opuestos) -> residuo ~0
    "T25P,rotor,R1,posicion_x,0.6965,m,±0.005,cinta,cinta 5m,2026-09-20T10:00:00,D,M,CG_tank50,2atm,1,S1,,ok",
    "T25P,rotor,R3,posicion_x,-0.6965,m,±0.005,cinta,cinta 5m,2026-09-20T10:05:00,D,M,CG_tank50,2atm,1,S1,,ok",
    # par con RESIDUO GRANDE a proposito (30 mm)
    "T25P,rotor,R2,posicion_x,0.6965,m,±0.005,cinta,cinta 5m,2026-09-20T10:10:00,D,M,CG_tank50,2atm,1,S1,,ok",
    "T25P,rotor,R4,posicion_x,-0.7265,m,±0.005,cinta,cinta 5m,2026-09-20T10:15:00,D,M,CG_tank50,2atm,1,S1,,ok",
    # fila M sin uncertainty ni instrument -> debe marcarse
    "T25P,rotor,R1,posicion_y,0.6965,m,,,-,-,2026-09-20T10:20:00,D,M,CG_tank50,2atm,1,S1,,sin trazabilidad",
    # fila sin reference_frame -> debe marcarse
    "T25P,mass,,measured_total_mass_kg,33.1,kg,±0.02,bascula,bascula 60kg,2026-09-20T11:00:00,D,M,,2atm,1,S1,,pesada",
    # repetibilidad con MISMO setup_id -> debe avisar que no es repetibilidad
    "T25P,mass,,nominal_total_mass_kg,33.0,kg,E,derivado,-,2026-09-20T11:05:00,D,E,CG_tank50,2atm,1,S1,,nominal",
    "T25P,mass,,nominal_total_mass_kg,33.0,kg,E,derivado,-,2026-09-20T11:06:00,D,E,CG_tank50,2atm,1,S1,,nominal",
    # repetibilidad correcta (S1 y S2) -> dispersión calculable
    "T25P,geometry,,separacion_ejes_opuestos_x,1.975,m,±0.005,cinta,cinta 5m,2026-09-20T12:00:00,D,M,CG_tank50,2atm,1,S1,,opuestos",
    "T25P,geometry,,separacion_ejes_opuestos_x,1.981,m,±0.005,cinta,cinta 5m,2026-09-20T12:10:00,D,M,CG_tank50,2atm,1,S2,,recolocado",
]


def main() -> int:
    TMP.write_text(CAB + "\n" + "\n".join(FILAS) + "\n", encoding="utf-8")
    backup = ROOT / "data" / "raw" / "_mediciones_real_backup.csv"
    shutil.copy2(REAL, backup)
    try:
        shutil.copy2(TMP, REAL)
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "audit_measurement_csv.py"),
                            "--uav", "T25P"], capture_output=True, text=True, encoding="utf-8")
        print(r.stdout)
        if r.stderr.strip():
            print("STDERR:", r.stderr[:800])
    finally:
        shutil.copy2(backup, REAL)
        backup.unlink()
        TMP.unlink()
    print("\nCSV real restaurado. Filas del real:",
          len(REAL.read_text(encoding='utf-8').splitlines()) - 1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
