"""Verificacion de la velocidad terminal de la gota. Valores canonicos de referencia:
   100 um en aire  -> ~0.25-0.30 m/s
   200 um en aire  -> ~1.2-1.3 m/s
   500 um en aire  -> ~2.0-2.5 m/s
Comprueba la funcion real de scripts/build_database.py, no una copia.
"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("bd", ROOT / "scripts" / "build_database.py")
bd = importlib.util.module_from_spec(spec)
sys.modules["bd"] = bd
spec.loader.exec_module(bd)

print("Constantes del modulo:")
print(f"  RHO   = {bd.RHO}")
print(f"  RHO_W = {bd.RHO_W}")
print(f"  MU_W  = {bd.MU_W}")
print()

plat = bd.PLAT["T100"]
print(f"{'d (um)':>8s} {'v_term (m/s)':>14s} {'St':>9s} {'t_caida (s)':>12s} {'sigma_y (m)':>12s}")
for d in (100, 200, 300, 500):
    m = bd.analitico(plat, plat["mtow"], float(d), 3.0, 5.0, 2)
    print(f"{d:8d} {m['v_terminal_gota_ms']:14.4f} {m['Stokes_number']:9.4f} "
          f"{m['tiempo_residencia_estela_s']:12.4f} {m['sigma_y_m']:12.4f}")

print()
print("REFERENCIA: 100 um deberia dar ~0.25-0.30 m/s y 200 um ~1.2-1.3 m/s.")
