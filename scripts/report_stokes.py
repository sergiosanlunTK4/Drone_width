"""
Informe del numero de Stokes CON SUS DEFINICIONES DECLARADAS.

POR QUE EXISTE:
  St = tau_p / tau_f no tiene un valor unico: depende de que escala temporal (tau_f) se
  compare. Reportar "St = 2.1" sin declarar tau_f es indefendible. Este script muestra las
  tres definiciones calculadas y, sobre todo, el dato que un St alto NO informa:
  la aceleracion por el CAMPO MEDIO.

  Un St alto significa menor seguimiento de FLUCTUACIONES y de la curvatura de las lineas
  de flujo. NO significa ausencia de aceleracion por el campo medio. Por eso se reporta
  tambien el cociente entre arrastre del downwash y peso neto.

Uso:
  python scripts/report_stokes.py
"""
from __future__ import annotations

import importlib.util
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "processed" / "dronewith.sqlite"


def cargar_modulo():
    spec = importlib.util.spec_from_file_location("bd", ROOT / "scripts" / "build_database.py")
    bd = importlib.util.module_from_spec(spec)
    sys.modules["bd"] = bd
    spec.loader.exec_module(bd)
    return bd


def main() -> int:
    bd = cargar_modulo()
    plat = bd.PLAT["T100"]
    masa = plat["mtow"]
    H = 3.0

    print("=" * 100)
    print("NUMERO DE STOKES CON DEFINICION DECLARADA  (T100 a MTOW, H = 3 m)")
    print("=" * 100)
    print(f"\n  tau_p = rho_w * d^2 / (18 * mu_aire)   [tiempo de respuesta de la gota]\n")
    print(f"  {'d (um)':>7s} {'tau_p (s)':>11s} {'St_rotor':>9s} {'St_estela':>10s} "
          f"{'St_turb':>9s} {'F_arr/F_grav':>13s} {'veredicto'}")
    print("  " + "-" * 92)
    for d in (100, 150, 200, 300, 400, 500):
        m = bd.analitico(plat, masa, float(d), H, 5.0, 2)
        ratio = m["ratio_arrastre_gravedad"]
        if ratio > 2.0:
            v = "el campo medio DOMINA"
        elif ratio > 0.5:
            v = "campo medio y gravedad comparables"
        else:
            v = "gravedad domina; wake solo deflecta"
        print(f"  {d:7d} {m['tau_particula_s']:11.3e} {m['St_rotor']:9.3f} "
              f"{m['St_estela']:10.4f} {m['St_turbulento']:9.3f} {ratio:13.3f}  {v}")

    print("\n" + "=" * 100)
    print("LAS TRES DEFINICIONES (d = 200 um)")
    print("=" * 100)
    con = sqlite3.connect(DB)
    cur = con.execute(
        "SELECT a.case_id, a.St_definicion, a.St_rotor, a.St_estela, a.St_turbulento, "
        "a.ratio_arrastre_gravedad, a.v_terminal_gota_ms "
        "FROM analytic_metrics a JOIN cases c ON a.case_id=c.case_id "
        "WHERE c.plataforma='T100' AND ABS(c.DV05_um-200)<40 LIMIT 1")
    r = cur.fetchone()
    if r:
        print(f"\n  caso: {r[0]}")
        print(f"  definicion declarada de St : {r[1]}")
        print(f"  St_rotor    (tau_f = r_rotor/v_dw)      = {r[2]:.4f}")
        print(f"  St_estela   (tau_f = H/v_dw)            = {r[3]:.4f}")
        print(f"  St_turbulento (tau_f = L_turb/u')       = {r[4]:.4f}")
        print(f"  v_terminal de la gota                   = {r[6]:.4f} m/s")
        print(f"  F_arrastre_downwash / F_gravedad        = {r[5]:.4f}")

    print("\n" + "=" * 100)
    print("LECTURA CORRECTA (y lo que NO se puede afirmar)")
    print("=" * 100)
    print("""
  St_rotor mide el seguimiento de la escala GLOBAL (el disco y su downwash medio).
  St_turbulento mide el seguimiento de las FLUCTUACIONES turbulentas. Son distintos y
  difieren en mas de un orden de magnitud, por eso se reportan los dos.

  AFIRMACION DEFENDIBLE:
    "Con St_turbulento > 1 la gota no sigue las fluctuaciones ni la curvatura de las
     lineas de flujo."

  AFIRMACION **NO** DEFENDIBLE (retirada):
    "St = 12.97 => el downwash apenas desvia la gota de 500 um."
    Alta inercia NO implica ausencia de aceleracion por el campo medio, y ademas en este
    rango St_turbulento < 1 incluso a 500 um (0.973), es decir la gota SI sigue las
    fluctuaciones a escala turbulenta.

  EL CRITERIO CORRECTO es el cociente entre arrastre del campo medio y peso neto:
  F_arrastre/F_gravedad. En el rango de este estudio vale de ~198 (100 um) a ~20 (500 um):
  DONDE HAY DOWNWASH, EL ARRASTRE SUPERA AL PESO EN MAS DE UN ORDEN DE MAGNITUD, para
  TODOS los tamanos de gota del rango operativo.

  MATIZ NECESARIO: ese cociente aplica mientras la gota esta DENTRO del flujo de la estela,
  que decae con la distancia al disco. El modelo de caida ya integra ese decaimiento.
  Lo que NO se puede concluir de aqui es la magnitud del desplazamiento lateral: eso exige
  el modulo Lagrangiano con el campo de aire real.

  CONCLUSION PARA H6: el tamano de gota NO separa limpiamente "sigue la estela" de
  "penetra balisticamente". Lo que cambia con el tamano es (a) el seguimiento de las
  FLUCTUACIONES (St_turb va de 0.039 a 0.973) y (b) el tiempo de residencia en la estela,
  porque la velocidad terminal crece mucho mas rapido que el arrastre. La formulacion de H6
  debe apoyarse en esos dos efectos, no en un unico numero de Stokes.
""")
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
