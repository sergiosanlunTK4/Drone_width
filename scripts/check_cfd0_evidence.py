"""
Verificacion cuantitativa de la evidencia del GATE CFD-0.

Comprueba que el actuator disk HIZO algo y en la direccion correcta. Es la parte del gate
que no se puede decidir "a ojo": un signo de empuje invertido es el error mas probable y
el mas silencioso de toda la configuracion, porque el solver converge igual.

QUE COMPRUEBA:
  1. Que el perfil de downwash exista y NO sea identicamente cero.
  2. Que el downwash vaya HACIA ABAJO (Uz < 0) en la region bajo el disco.
  3. Que la magnitud sea del ORDEN esperado por momentum theory:
        v_ind = sqrt(T / (2*rho*A_disk))     y el nucleo ~ 2*v_ind
     Criterio: dentro de un factor 5 del valor esperado. Ni cero ni un orden de magnitud
     fuera. (El factor es amplio a proposito: la malla gruesa y la turbulencia no permiten
     exigir precision en un smoke test; lo que se detecta es un error de signo o de escala.)

Uso:
  python3 scripts/check_cfd0_evidence.py <case_id> <cases_dir>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

RHO = 1.1716
G = 9.81


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    case_id, cases_dir = sys.argv[1], Path(sys.argv[2])
    caso = cases_dir / case_id

    meta_path = caso / "case_meta.json"
    if not meta_path.exists():
        print("          [FALLO] falta case_meta.json")
        return 1
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    deriv = meta.get("derivados_analiticos", {})
    n_rot = deriv.get("n_rotores_modelados", 4)
    A_total = deriv.get("area_disco_total_m2", 0.0)
    T_total = deriv.get("empuje_total_N", 0.0)
    if A_total <= 0:
        print("          [FALLO] area de disco no disponible en el meta")
        return 1

    A_disk = A_total / n_rot
    T_disk = T_total / n_rot
    v_ind_esperada = math.sqrt(T_disk / (2.0 * RHO * A_disk))
    v_nucleo_esperada = 2.0 * v_ind_esperada

    print(f"          esperado por momentum theory: v_ind={v_ind_esperada:.3f} m/s, "
          f"nucleo~{v_nucleo_esperada:.3f} m/s")

    base = caso / "postProcessing" / "downwashLines"
    if not base.exists():
        print("          [FALLO] no hay postProcessing/downwashLines")
        return 1

    tiempos = sorted([d for d in base.iterdir() if d.is_dir()],
                     key=lambda d: (len(d.name), d.name))
    if not tiempos:
        print("          [FALLO] downwashLines sin subdirectorios de tiempo")
        return 1
    instantes = sorted([d for d in tiempos[-1].iterdir() if d.is_dir()],
                       key=lambda d: (len(d.name), d.name))
    if not instantes:
        print("          [FALLO] downwashLines sin instantes")
        return 1
    archivos = [f for f in instantes[-1].iterdir() if f.is_file()]
    if not archivos:
        print("          [FALLO] el instante no contiene ficheros")
        return 1

    zs, uzs = [], []
    for linea in archivos[0].read_text(errors="ignore").splitlines():
        p = linea.split()
        if len(p) >= 4:
            try:
                zs.append(float(p[2]))
                uzs.append(float(p[3]))
            except ValueError:
                continue
    if not uzs:
        print(f"          [FALLO] no se pudieron leer datos de {archivos[0].name}")
        return 1

    uz_min = min(uzs)
    uz_max = max(uzs)
    uz_medio = sum(uzs) / len(uzs)
    print(f"          leido: Uz_min={uz_min:.4f}  Uz_max={uz_max:.4f}  Uz_medio={uz_medio:.4f} m/s")

    fallos = 0
    # 1. no identicamente cero
    if abs(uz_max - uz_min) < 1e-9:
        print("          [FALLO] el perfil es CONSTANTE: el disco no actua")
        fallos += 1
    else:
        print("          [OK]    el perfil varia: el disco actua")

    # 2. signo: downwash hacia abajo
    if uz_min < 0:
        print(f"          [OK]    signo correcto: hay flujo hacia abajo (Uz_min={uz_min:.4f})")
    else:
        print(f"          [FALLO] SIGNO INVERTIDO: no hay Uz negativo (Uz_min={uz_min:.4f}). "
              "Revisar diskDir en constant/fvOptions")
        fallos += 1

    # 3. magnitud dentro de un factor 5
    ratio = abs(uz_min) / v_nucleo_esperada if v_nucleo_esperada > 0 else float("inf")
    if 0.2 <= ratio <= 5.0:
        print(f"          [OK]    magnitud del orden esperado (ratio={ratio:.2f})")
    else:
        print(f"          [FALLO] magnitud fuera de orden (ratio={ratio:.2f}; "
              "se acepta 0.2-5.0)")
        fallos += 1

    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
