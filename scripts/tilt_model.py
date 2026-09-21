"""
Modelo de ACTITUD (cabeceo) del T100 en funcion de la velocidad de avance.

POR QUE ES NECESARIO (pregunta del investigador, y es central):
  1. En vuelo nivelado el rotor debe inclinarse para generar el empuje hacia adelante que
     vence la resistencia. El disco gira con el dron, asi que la NORMAL DEL DISCO deja de
     ser vertical: el downwash deja de ser vertical.
  2. PEOR: los atomizadores del T100 son CENTRIFUGOS — expulsan el liquido en un PLANO
     HORIZONTAL respecto al dron. Si el dron cabecea theta, ese plano se inclina theta, y la
     proyeccion sobre el suelo se desplaza hacia ATRAS. A alta velocidad ese desplazamiento
     puede superar al efecto del viento.
  3. Por tanto la actitud es una variable de primer orden para D(x,y), y no estaba en el
     modelo. Se introduce aqui.

FISICA (equilibrio en vuelo estacionario, sin aceleracion):
  - Vertical:  T cos(theta) = W                      -> T = W / cos(theta)
  - Horizontal: T sin(theta) = D(V)                  -> empuje hacia adelante = resistencia
  - Combinando: tan(theta) = D(V) / W

  La resistencia se modela con el area frontal y un Cd efectivo:
      D(V) = 0.5 * rho * Cd * A_frontal * V^2

  El angulo maximo esta acotado por el margen de empuje:
      T_max >= W / cos(theta_max)   ->   cos(theta_max) = W / T_max

ENTRADAS (todas con su clase de fuente):
  W        = 175 kg (MTOW pulverizacion, clase P)          -> 1716.8 N
  T_max    = 4 brazos x 804.15 N = 3216.6 N (82 kg/brazo, P-A)  -> margen 1.874
  A_front  = estimada del modelo geometrico (clase E)      -> parametro de sensibilidad
  Cd       = 0.8 tipico de fuselaje no aerodinamico (clase E)

Uso:
  python scripts/tilt_model.py
"""
from __future__ import annotations

import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

G = 9.81
RHO = 1.1716          # 28 C, nivel del mar

# --- entradas ---------------------------------------------------------------------
M_MTOW = 175.0        # kg, MTOW pulverizacion (P)
M_VACIO = 73.0        # kg, con bateria, 2 boquillas, SIN liquido (O, propietario)
CARGA_MAX = 100.0     # kg / L (P)
N_BRAZOS = 4
T_BRAZO_MAX_N = 804.15   # 82 kg por brazo (P-A, Academy)

# geometria del sobre: 3220 x 3224 x 975 mm -> area frontal aproximada
# Se toma el ancho y el alto como seccion frontal. Clase E (estimacion).
A_FRONT_M2 = 3.224 * 0.975 * 0.55      # factor 0.55: no es un prisma lleno
CD_EFECTIVO = 0.8                       # clase E, tipico de fuselaje con tanque y tren

V_RANGE = (1.0, 20.0)   # m/s (O, propietario: min 1, max 20)


def empuje_maximo_N() -> float:
    return N_BRAZOS * T_BRAZO_MAX_N


def actitud(V: float, masa_kg: float, area: float = A_FRONT_M2, cd: float = CD_EFECTIVO) -> dict:
    """Devuelve theta, empuje requerido y si es alcanzable."""
    W = masa_kg * G
    D = 0.5 * RHO * cd * area * V ** 2          # resistencia a esa velocidad
    theta = math.atan2(D, W)                     # tan(theta) = D/W
    T_req = W / math.cos(theta)
    T_max = empuje_maximo_N()
    return {
        "V": V,
        "masa": masa_kg,
        "W_N": W,
        "D_N": D,
        "theta_deg": math.degrees(theta),
        "T_requerido_N": T_req,
        "T_max_N": T_max,
        "relacion_T_W": T_req / W,
        "alcanzable": T_req <= T_max,
        "margen_pct": (T_max / T_req - 1.0) * 100.0,
    }


def main() -> int:
    print("=" * 96)
    print("MODELO DE ACTITUD DEL T100 EN FUNCION DE LA VELOCIDAD")
    print("=" * 96)
    W_mtow = M_MTOW * G
    T_max = empuje_maximo_N()
    print(f"\n  MTOW pulverizacion      : {M_MTOW} kg  ->  W = {W_mtow:.1f} N")
    print(f"  Empuje maximo (4 brazos): {T_max:.1f} N  (82 kg/brazo, P-A)")
    print(f"  Relacion empuje/peso    : {T_max/W_mtow:.3f}")
    cos_max = W_mtow / T_max
    theta_max = math.degrees(math.acos(min(1.0, cos_max)))
    print(f"  ACTITUD MAXIMA TEORICA  : {theta_max:.1f} grados  (cos(theta) = W/T_max)")
    print(f"\n  Area frontal estimada   : {A_FRONT_M2:.3f} m2   (clase E)")
    print(f"  Cd efectivo adoptado    : {CD_EFECTIVO}          (clase E)")

    for masa, etiqueta in ((M_MTOW, "MTOW 175 kg (tanque lleno)"),
                           (M_MTOW - 50.0, "125 kg (medio tanque)"),
                           (M_VACIO, "73 kg (sin liquido)")):
        print("\n" + "=" * 96)
        print(f"ACTITUD vs VELOCIDAD — {etiqueta}")
        print("=" * 96)
        print(f"\n  {'V (m/s)':>8s} {'D (N)':>9s} {'theta (deg)':>12s} {'T req (N)':>10s} "
              f"{'T/W':>7s} {'margen':>9s} {'alcanzable':>11s}")
        for V in (1, 2, 3, 4, 5, 6, 8, 10, 13, 15, 20):
            if V < V_RANGE[0] or V > V_RANGE[1]:
                continue
            r = actitud(V, masa)
            print(f"  {r['V']:8.1f} {r['D_N']:9.2f} {r['theta_deg']:12.2f} "
                  f"{r['T_requerido_N']:10.1f} {r['relacion_T_W']:7.3f} "
                  f"{r['margen_pct']:8.1f}% {'si' if r['alcanzable'] else 'NO':>11s}")

    # --- efecto sobre los atomizadores centrifugos ---------------------------------
    print("\n" + "=" * 96)
    print("EFECTO SOBRE LOS ATOMIZADORES CENTRIFUGOS (lo importante para D(x,y))")
    print("=" * 96)
    print("""
  Los atomizadores del T100 son CENTRIFUGOS: un disco que gira en el plano horizontal del
  dron y expulsa el liquido radialmente EN ESE PLANO. Si el dron cabecea theta:

    - el plano de expulsion se inclina theta respecto a la horizontal;
    - la proyeccion sobre el suelo se desplaza hacia ATRAS (el lado trasero del abanico
      toca antes el suelo que el delantero);
    - el ancho de trabajo medido en el suelo ya no es simetrico respecto a la linea de vuelo.

  Desplazamiento aproximado del centro del abanico al caer una altura h:
      dx = h * tan(theta)          (hacia atras)
""")
    print(f"  {'V (m/s)':>8s} {'theta (deg)':>12s} {'dx a h=2.55 m':>15s} {'dx a h=3 m':>12s}")
    h_noz = 3.0 - 0.448          # altura del atomizador sobre el suelo a H=3 m de vuelo
    for V in (2, 3, 5, 6, 8, 10, 13, 15, 20):
        r = actitud(V, M_MTOW)
        t = math.radians(r["theta_deg"])
        print(f"  {V:8.1f} {r['theta_deg']:12.2f} {h_noz*math.tan(t):15.3f} m "
              f"{3.0*math.tan(t):11.3f} m")

    print("""
  LECTURA: a 20 m/s el abanico se desplaza decenas de centimetros hacia atras SOLO por la
  actitud. No es despreciable frente al ancho de trabajo, y es un efecto SISTEMATICO y
  PREDECIBLE, distinto del viento (que aqui es 0 por alcance).
""")

    # sensibilidad
    print("=" * 96)
    print("SENSIBILIDAD: A_frontal y Cd son estimaciones (clase E)")
    print("=" * 96)
    print(f"\n  {'Cd':>5s} {'A (m2)':>8s} {'theta a 10 m/s':>16s} {'theta a 20 m/s':>16s}")
    for cd in (0.6, 0.8, 1.0):
        for a in (A_FRONT_M2 * 0.6, A_FRONT_M2, A_FRONT_M2 * 1.4):
            r10 = actitud(10.0, M_MTOW, a, cd)
            r20 = actitud(20.0, M_MTOW, a, cd)
            print(f"  {cd:5.1f} {a:8.3f} {r10['theta_deg']:16.2f} {r20['theta_deg']:16.2f}")
    print("""
  NOTA: theta depende de Cd*A, que es una ESTIMACION. A 20 m/s el angulo varia
  apreciablemente con esas suposiciones. Por eso la actitud debe:
    (a) declararse como parametro en el CFD, y
    (b) MEDIRSE si es posible (actitud real en hover y en avance, desde telemetria o video).
  Medir la actitud es barato comparado con su impacto.
""")
    print("=" * 96)
    print("Este script REPORTA un modelo analitico. NO es CFD y NO usa resultados de CFD.")
    print("=" * 96)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
