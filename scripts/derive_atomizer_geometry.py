"""
Deriva la geometria de los atomizadores a partir de datos declarados y la VALIDA.

DATOS APORTADOS POR EL PROPIETARIO (2026-09-14, comunicacion directa):
  - T100: 8 motores.  T25P, T55, T70P: 4 motores.
  - Atomizadores: la separacion (Y) ya se tiene de la ficha oficial. Falta la X.
      Boquilla 1 (izquierda) -> x = -0.9 m
      Boquilla 2              -> x = -0.8 m
      Boquilla 3              -> x = -0.8 m
      Boquilla 4 (derecha)    -> x = -0.9 m
      Y las boquillas 2 y 3 son las EXTRAS de la configuracion de 4.
  - El usuario pide regularizarlo a la nomenclatura del proyecto (A1..A4, position_role).

CLASIFICACION:
  Estos valores son **O = aportado por el propietario**, no medidos con protocolo (M) ni
  publicados (P). El propietario es la fuente mas cercana al objeto fisico, asi que O es
  mejor que una inferencia, pero NO es M: no hay instrumento, incertidumbre ni repeticion.
  Se registran como O y se marcan para promocion a M cuando se midan.

QUE HACE ESTE SCRIPT:
  1. Regulariza la nomenclatura (A1..A4 + rol geometrico) para las 4 plataformas.
  2. Deriva la Y de cada boquilla segun la convencion "par exterior = separacion declarada,
     par interior cerrado" (hipotesis I explicita, por decidir con medicion).
  3. VALIDA contra la fisica:
       - la separacion exterior declarada no puede exceder el alcance del rotor mas externo;
       - la separacion interior derivada debe ser menor que la exterior;
       - la distancia de cada boquilla al eje del rotor mas cercano debe ser finita y
         compatible con el ancho de la barra/brazo declarado.
  4. Emite la tabla de posiciones y las discrepancias detectadas.

NO modifica manifiestos. NO convierte nada en M.

Uso:
  python scripts/derive_atomizer_geometry.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "geometry" / "atomizer_layout.json"

# separacion declarada en la ficha oficial (P). Interpretacion: par EXTREMO.
PLAT = {
    "T25P": dict(dsep_mm=1420, n_std=2, n_opt=4, wheelbase_mm=1970,
                 boom_len_m=None, x_user=None, motores=4, coaxial=False),
    "T55":  dict(dsep_mm=1800, n_std=2, n_opt=4, wheelbase_mm=2415,
                 boom_len_m=None, x_user=None, motores=4, coaxial=True),
    "T70P": dict(dsep_mm=1874, n_std=2, n_opt=4, wheelbase_mm=2440,
                 boom_len_m=None, x_user=None, motores=4, coaxial=True),
    "T100": dict(dsep_mm=1834, n_std=2, n_opt=4, wheelbase_mm=2330,
                 boom_len_m=1.930,   # LS100 desplegada (P)
                 x_user=[-0.9, -0.8, -0.8, -0.9],
                 motores=8, coaxial=True),
}

# roles de atomizador segun la convencion interna (misma logica que los rotores):
# vistos desde atras, de izquierda a derecha -> RL, RL_inner... se usa L/R + orden.
ROLES_ATOM = [
    ("A1", "L_out", "izquierda exterior"),
    ("A2", "L_in",  "izquierda interior"),
    ("A3", "R_in",  "derecha interior"),
    ("A4", "R_out", "derecha exterior"),
]


def validar(clave: str, p: dict, pos: list[dict]) -> tuple[list[str], list[str]]:
    errores, avisos = [], []
    y_out = p["dsep_mm"] / 2000.0                      # semiseparacion exterior (m)
    r_rotor = {"T25P": 0.635, "T55": 0.7875, "T70P": 0.787, "T100": 0.787}[clave]
    R_eje = p["wheelbase_mm"] / 2000.0                 # centro a eje de rotor (m)

    # 1) la separacion exterior no puede exceder el alcance del rotor mas externo
    alcance_max = R_eje + r_rotor
    if y_out > alcance_max:
        errores.append(
            f"separacion exterior (±{y_out:.3f} m) excede el alcance del rotor mas externo "
            f"({alcance_max:.3f} m = R_eje {R_eje:.3f} + r_rotor {r_rotor:.3f})"
        )

    # 2) interior < exterior
    y_in = y_out / 2.0
    if not (0 < y_in < y_out):
        errores.append("separacion interior derivada no es menor que la exterior")

    # 3) barra: la boquilla exterior no debe salir de la barra si su longitud es conocida
    if p["boom_len_m"]:
        mitad_barra = p["boom_len_m"] / 2.0
        if y_out > mitad_barra:
            errores.append(
                f"la boquilla exterior (±{y_out:.3f} m) sale de la barra "
                f"(mitad de barra = {mitad_barra:.3f} m)"
            )
        else:
            avisos.append(
                f"la boquilla exterior (±{y_out:.3f} m) queda dentro de la barra "
                f"(±{mitad_barra:.3f} m), margen {mitad_barra - y_out:+.3f} m"
            )

    # 4) boquilla interior vs rotor interior: cae dentro del disco?
    for a in pos:
        dy = abs(abs(a["y_m"]) - R_eje)
        if dy < r_rotor:
            avisos.append(
                f"{a['id']} cae dentro del disco de barrido de un rotor "
                f"(distancia al eje {dy:.3f} m < r_rotor {r_rotor:.3f} m)"
            )
    return errores, avisos


def main() -> int:
    salida = {"clasificacion": "O (aportado por el propietario, comunicacion directa 2026-09-14)",
              "no_es": "no es M: sin instrumento, sin incertidumbre, sin repeticion",
              "plataformas": {}}
    print("=" * 84)
    print("GEOMETRIA DE ATOMIZADORES — derivacion y validacion")
    print("=" * 84)

    for clave, p in PLAT.items():
        y_out = p["dsep_mm"] / 2000.0
        y_in = y_out / 2.0
        # X: del usuario para T100; no declarada para el resto (queda D)
        xs = p["x_user"] if p["x_user"] else [None] * 4

        pos = []
        for (aid, rol, desc), x in zip(ROLES_ATOM, xs):
            if rol.endswith("out"):
                y = -y_out if rol.startswith("L") else y_out
            else:
                y = -y_in if rol.startswith("L") else y_in
            pos.append({"id": aid, "position_role": rol, "descripcion": desc,
                        "x_m": x, "y_m": round(y, 4), "z_m": None,
                        "clasificacion": "O (x) / I (y derivada de P)" if x is not None
                                        else "I (y derivada de P); x = D"})

        err, av = validar(clave, p, pos)
        salida["plataformas"][clave] = {
            "motores_declarados": p["motores"],
            "coaxial": p["coaxial"],
            "separacion_declarada_mm": p["dsep_mm"],
            "interpretacion": "par EXTREMO a la separacion declarada; par interior cerrado (hipotesis I)",
            "atomizadores": pos,
            "errores": err,
            "avisos": av,
        }

        print(f"\n--- {clave} ---  motores declarados: {p['motores']}  coaxial: {p['coaxial']}")
        print(f"    separacion declarada: {p['dsep_mm']} mm -> ±{y_out:.4f} m (par extremo)")
        print(f"    par interior (hipotesis I):        ±{y_in:.4f} m")
        print(f"    {'id':4s} {'rol':6s} {'X (m)':>8s} {'Y (m)':>8s}   clasificacion")
        for a in pos:
            xs_ = f"{a['x_m']:+.3f}" if a["x_m"] is not None else "   D  "
            print(f"    {a['id']:4s} {a['position_role']:6s} {xs_:>8s} {a['y_m']:+8.4f}   {a['clasificacion']}")
        for e in err:
            print(f"    ERROR: {e}")
        for w in av:
            print(f"    AVISO: {w}")

    OUT.write_text(json.dumps(salida, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n-> {OUT.relative_to(ROOT)}")
    print("\nRECORDATORIO: esto no cierra GATE 1A. La Y es derivada (I) y la interpretacion")
    print("'par extremo' es una hipotesis a decidir con medicion (la Z sigue en D).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
