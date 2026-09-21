"""
AMBIENTE BASAL — calculo de rho desde T, RH, P y su verificacion.

CORRECCIONES APLICADAS (revision del investigador, 2026-09-19):
  - No es "rho = 1.1716 porque son 28 C": es un ESCENARIO BASAL REPRESENTATIVO declarado
    con T_0, RH_0, P_0 explicitos, del que se CALCULA rho_0.
  - Valores de septiembre en Veracruz: T media ~26.4 C, RH ~83%.
    Se adopta T_0 = 26 C, RH_0 = 85%, P_0 = 101.0 kPa como escenario basal.
  - MEJORA PENDIENTE (mejor que elegir un valor "porque Veracruz es calido"):
    descargar varios anos de observaciones horarias de la estacion MMVR
    (Aeropuerto General Heriberto Jara), filtrar horas tipicas de aplicacion
    (06:00-09:00 local) y usar la MEDIANA de T, RH, P.

Uso:
  python scripts/basal_ambiente.py
"""
from __future__ import annotations

import math

# --- escenario basal representativo (declarado, NO medido en campana) ----------------
T0_C = 26.0          # E: media de septiembre en Veracruz
RH0_PCT = 85.0       # E: humedad de septiembre
P0_KPA = 101.0       # E: nivel del mar, aeropuerto Gral. Heriberto Jara

# constantes de gas
R_D = 287.058        # J/(kg K) aire seco
R_V = 461.495        # J/(kg K) vapor de agua


def presion_saturacion(T_C: float) -> float:
    """Presion de saturacion del vapor de agua (Magnus). Devuelve Pa."""
    return 610.94 * math.exp((17.625 * T_C) / (T_C + 243.04))


def densidad(T_C: float, P_Pa: float, RH_pct: float) -> float:
    """Densidad del aire HUMEDO.

        P_sat = 610.94 exp(17.625 T/(T+243.04))     [Pa]
        P_v   = RH * P_sat
        P_d   = P - P_v
        rho   = P_d/(R_d T) + P_v/(R_v T)
    """
    T = T_C + 273.15
    P_v = (RH_pct / 100.0) * presion_saturacion(T_C)
    P_d = P_Pa - P_v
    return P_d / (R_D * T) + P_v / (R_V * T)


def desglose(T_C: float, P_Pa: float, RH_pct: float) -> dict:
    T = T_C + 273.15
    P_sat = presion_saturacion(T_C)
    P_v = (RH_pct / 100.0) * P_sat
    P_d = P_Pa - P_v
    rho_d = P_d / (R_D * T)
    rho_v = P_v / (R_V * T)
    return {"T_K": T, "P_sat_Pa": P_sat, "P_v_Pa": P_v, "P_d_Pa": P_d,
            "rho_seco": rho_d, "rho_vapor": rho_v, "rho_total": rho_d + rho_v}


def main() -> int:
    print("=" * 96)
    print("AMBIENTE BASAL — rho calculado desde T, RH, P")
    print("=" * 96)

    print(f"""
  ESCENARIO BASAL REPRESENTATIVO (declarado, no medido en campana):
      T_0  = {T0_C:.1f} C      (media de septiembre en Veracruz)
      RH_0 = {RH0_PCT:.0f} %       (humedad de septiembre)
      P_0  = {P0_KPA:.1f} kPa  (nivel del mar, aeropuerto Gral. Heriberto Jara)

  NO es "el promedio exacto medido": es un escenario basal declarado como tal.
""")

    d = desglose(T0_C, P0_KPA * 1000.0, RH0_PCT)
    print("  DESGLOSE DEL CALCULO:")
    print(f"    T          = {d['T_K']:.2f} K")
    print(f"    P_sat(26C) = {d['P_sat_Pa']:.1f} Pa")
    print(f"    P_v        = RH*P_sat = {d['P_v_Pa']:.1f} Pa")
    print(f"    P_d        = P - P_v  = {d['P_d_Pa']:.1f} Pa")
    print(f"    rho_seco   = P_d/(R_d T) = {d['rho_seco']:.4f} kg/m3")
    print(f"    rho_vapor  = P_v/(R_v T) = {d['rho_vapor']:.4f} kg/m3")
    print(f"    ---------------------------------------------------")
    print(f"    rho_0      = {d['rho_total']:.4f} kg/m3")

    print(f"""
  COMPARACION con lo que se usaba antes:
      rho = 1.1716  (aire SECO a 28 C, nivel del mar)     -> sin justificar
      rho = {d['rho_total']:.4f}  (escenario basal Veracruz-manana)  -> con T, RH, P explicitos
      Diferencia: {(d['rho_total']-1.1716)/1.1716*100:+.2f} %
""")

    print("-" * 96)
    print("SENSIBILIDAD al escenario ambiental")
    print("-" * 96)
    print(f"\n  {'caso':38s} {'T (C)':>7s} {'RH (%)':>7s} {'P (kPa)':>8s} {'rho':>8s} {'vs base':>9s}")
    base = d["rho_total"]
    casos = [
        ("BASAL Veracruz septiembre", T0_C, RH0_PCT, P0_KPA),
        ("aire seco a 28 C (lo anterior)", 28.0, 0.0, 101.325),
        ("manana fresca (20 C, 90%)", 20.0, 90.0, 101.0),
        ("mediodia caluroso (34 C, 60%)", 34.0, 60.0, 101.0),
        ("temporada de lluvias (24 C, 95%)", 24.0, 95.0, 101.0),
        ("altitud 500 m, 26 C, 85%", 26.0, 85.0, 95.5),
    ]
    for nombre, T, RH, P in casos:
        r = densidad(T, P * 1000.0, RH)
        print(f"  {nombre:38s} {T:7.1f} {RH:7.0f} {P:8.1f} {r:8.4f} "
              f"{(r-base)/base*100:+8.2f} %")

    print("""
  LECTURA: la variacion de rho entre escenarios realistas de una campana de manana es de
  unos pocos por ciento. Eso respalda la decision de FIJAR el ambiente en DOE-A y barrerlo
  despues en DOE-B: no es la variable que domina.
""")

    print("-" * 96)
    print("MEJORA PENDIENTE: percentiles de observaciones reales")
    print("-" * 96)
    print("""
  En vez de elegir un valor "porque Veracruz es calido", el procedimiento correcto es:

    1. Descargar varios anos de observaciones HORARIAS de la estacion MMVR
       (Aeropuerto General Heriberto Jara, Veracruz).
    2. Filtrar solo horas tipicas de aplicacion: 06:00-09:00 local.
    3. Tomar la MEDIANA de T, RH y P (y sus P10/P90 para el DOE-B).

  Eso convierte el escenario basal en algo derivado de datos, no de una impresion.
  Queda PENDIENTE: requiere acceso a los registros de la estacion.
""")

    print("=" * 96)
    print("Calculo reproducible. No usa CFD.")
    print("=" * 96)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
