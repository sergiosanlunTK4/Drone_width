"""
ANCHOS: derivacion de la relacion caudal-ancho y de los CUATRO anchos distintos.

CORRECCION CONCEPTUAL DEL INVESTIGADOR (2026-09-19), que este script implementa:

    ANCHO COMANDADO  !=  ABANICO AERODINAMICO  !=  ANCHO EFECTIVO DE DEPOSICION

De donde salen CUATRO anchos distintos y medibles:

    W_commanded  = Q_real / (0.006 R V)     lo que el caudal IMPLICA
    W_DJI        = interlineado/ancho configurado en el controlador Agras
    W_aero       = abanico fisico que sale de los atomizadores (Lagrangiano, sin suelo)
    W_deposition = ancho efectivo derivado de D(x,y)  <- el objetivo cientifico

LA RELACION CAUDAL-ANCHO (derivada, no citada):

    En 1 s el dron recorre V metros -> cubre V*W m2 = V*W/10000 ha
    Volumen por segundo = R * V*W/10000   [L/s]
    Volumen por minuto  = 60 R V W/10000  [L/min]

        Q = 0.006 R V W            [L/min, con R en L/ha, V en m/s, W en m]

  e invertida:  W_commanded = Q / (0.006 R V)

QUE NO SE PUEDE HACER: convertir caudal en ancho de deposicion. El caudal determina
CUANTO liquido se deposita. El campo de aire + tamano de gota + condicion inicial
determinan DONDE acaba. DJI declara 5-13 m para el T100 y aclara que el ancho efectivo
depende de la escena real de trabajo.

Uso:
  python scripts/widths.py
"""
from __future__ import annotations

import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# --- T100, datos con su clase -------------------------------------------------------
DJI_W_EFECTIVO_M = (5.0, 13.0)    # P: ficha oficial, "depende de la escena real"
Q_2BOQ_LMIN = 30.0                 # P: caudal maximo 2 boquillas
Q_4BOQ_LMIN = 40.0                 # P: caudal maximo 4 boquillas
Q_MIN_2BOQ = 16.0                  # referencia T50 para contexto (P-A)
RHO_L = 997.0                      # kg/m3 agua a 25 C
D50_UM = 150.0                     # P: recomendado por el modelo del propietario


def caudal(R: float, V: float, W: float) -> float:
    """Q = 0.006 R V W   [L/min]"""
    return 0.006 * R * V * W


def ancho_implicito(Q: float, R: float, V: float) -> float:
    """W_commanded = Q / (0.006 R V)   [m]"""
    den = 0.006 * R * V
    return Q / den if den > 0 else float("nan")


def boquillas_necesarias(Q: float, Lmin_por_boquilla: float = 10.0) -> float:
    """Numero de atomizadores para repartir un caudal (10 L/min nominal por boquilla)."""
    return Q / Lmin_por_boquilla


def masa_por_bin(Q_total_Lmin: float, d_um: float, n_bins: int = 1) -> dict:
    """De caudal a PARTICULAS: cuanto liquido y cuantas gotas por bin de diametro.

    Q [L/min] -> masa [kg/s]:   m_dot = rho_L * Q/60000
    masa de una gota:           m_d = rho_L * pi d^3 / 6
    numero de gotas por segundo: N_dot = m_dot_bin / m_d
    """
    Q_m3s = Q_total_Lmin / 60000.0
    m_dot = RHO_L * Q_m3s
    d = d_um * 1e-6
    m_d = RHO_L * math.pi * d ** 3 / 6.0
    return {"Q_m3s": Q_m3s, "m_dot_kg_s": m_dot, "m_gota_kg": m_d,
            "gotas_por_s": m_dot / m_d if m_d > 0 else float("nan")}


def main() -> int:
    print("=" * 96)
    print("ANCHOS: del caudal a la deposicion — CUATRO anchos distintos")
    print("=" * 96)

    print("\n" + "-" * 96)
    print("1. DERIVACION DE LA RELACION CAUDAL-ANCHO")
    print("-" * 96)
    print("""
  No se cita: se deriva.

    En 1 segundo el dron recorre V metros.
    Area cubierta por segundo   = V * W          [m2/s]
    Area cubierta por segundo   = V*W/10000      [ha/s]
    Volumen por segundo         = R * V*W/10000  [L/s]
    Volumen por minuto          = 60 R V W/10000 [L/min]

        Q = 0.006 R V W        con Q en L/min, R en L/ha, V en m/s, W en m
        W_commanded = Q / (0.006 R V)
""")
    R, V, W = 10.0, 10.0, 6.0
    print(f"  Comprobacion del ejemplo del investigador (R={R:g} L/ha, V={V:g} m/s, W={W:g} m):")
    print(f"    Q = 0.006 x {R:g} x {V:g} x {W:g} = {caudal(R,V,W):.4f} L/min")
    print(f"    el investigador da 3.6 L/min -> "
          f"{'COINCIDE' if abs(caudal(R,V,W)-3.6) < 1e-9 else 'DIFIERE'}")

    print("\n" + "-" * 96)
    print("2. QUE REVELA LA RELACION INVERTIDA")
    print("-" * 96)
    print(f"\n  A R = {R:g} L/ha y V = {V:g} m/s, el ancho implicito segun el caudal real:")
    print(f"\n  {'Q (L/min)':>11s} {'caso':32s} {'W_implicito (m)':>16s} {'%':>7s}")
    escenarios = [
        (3.6, "del ejemplo del investigador"),
        (8.0, "uso tipico estimado"),
        (16.0, "caudal T50 a 2 boquillas (referencia)"),
        (Q_2BOQ_LMIN, "T100 maximo con 2 boquillas"),
        (Q_4BOQ_LMIN, "T100 maximo con 4 boquillas"),
    ]
    for Q, caso in escenarios:
        w = ancho_implicito(Q, R, V)
        marca = ""
        if not (DJI_W_EFECTIVO_M[0] <= w <= DJI_W_EFECTIVO_M[1]):
            marca = "  <- FUERA del rango DJI 5-13 m"
        print(f"  {Q:11.1f} {caso:32s} {w:16.2f} {marca}")

    print(f"""
  LECTURA: los caudales MAXIMOS del T100 (30 y 40 L/min) implican anchos de 50 y 66 m a
  R={R:g} L/ha y V={V:g} m/s — absurdos. Eso NO significa que el dato este mal: significa
  que el maximo de bomba se usa con OTRAS combinaciones de (R, V).

  La relacion invertida sirve para RECONSTRUIR la operacion real a partir de telemetria:
  con Q y V reales, y la R configurada, se obtiene el ancho que el CONTROLADOR esta asumiendo.
  Eso es W_commanded, y es DISTINTO de lo que las gotas hacen.
""")

    print("-" * 96)
    print("3. DE CAUDAL A PARTICULAS (lo que SI determina el caudal)")
    print("-" * 96)
    print("""
  El caudal NO determina el ancho. Determina CUANTO liquido se inyecta:

      m_dot = rho_L * Q[L/min]/60000        [kg/s]
      m_gota = rho_L * pi d^3 / 6           [kg]
      N_dot = m_dot / m_gota                [gotas/s]

  Y con una DISTRIBUCION de diametros, cada bin j lleva su fraccion de masa:

      N_j = (m_dot * f_j * dt) / (rho_L pi d_j^3 / 6)

  Cada particula Lagrangiana representa MUCHAS gotas mediante su peso estadistico:
  no hace falta simular millones de gotas.
""")
    print(f"  {'d (um)':>8s} {'m_gota (kg)':>14s} {'N/s a 30 L/min':>16s} {'N/s a 40 L/min':>16s}")
    for d in (50, 100, 150, 200, 300, 500):
        a = masa_por_bin(Q_2BOQ_LMIN, d)
        b = masa_por_bin(Q_4BOQ_LMIN, d)
        print(f"  {d:8d} {a['m_gota_kg']:14.3e} {a['gotas_por_s']:16.3e} {b['gotas_por_s']:16.3e}")
    print(f"""
  A d50 = {D50_UM:.0f} um y 30 L/min salen ~{masa_por_bin(Q_2BOQ_LMIN, D50_UM)['gotas_por_s']:.2e} gotas/s.
  Inyectar eso literalmente es imposible; se usa peso estadistico (parcelas).
""")

    print("-" * 96)
    print("4. LOS CUATRO ANCHOS")
    print("-" * 96)
    print(f"""
  | ancho        | que es                                  | como se obtiene            | estado |
  |--------------|-----------------------------------------|----------------------------|--------|
  | W_commanded  | el que el CAUDAL implica                | Q_real / (0.006 R V)       | derivable, requiere telemetria |
  | W_DJI        | el configurado en el controlador Agras  | lectura de la app/pantalla | P: {DJI_W_EFECTIVO_M[0]:.0f}-{DJI_W_EFECTIVO_M[1]:.0f} m (y "depende de la escena") |
  | W_aero       | abanico fisico de los atomizadores      | Lagrangiano SIN plano receptor | pendiente: requiere CFD |
  | W_deposition | ancho efectivo real                     | derivado de D(x,y)         | OBJETIVO CIENTIFICO |

  LA DIFERENCIA ENTRE LOS TRES PRIMEROS Y EL CUARTO es, probablemente, uno de los
  resultados mas valiosos de la investigacion: cuantifica cuanto se desvia la practica
  operativa (caudal y configuracion) de la fisica real de deposicion.

  DJI declara {DJI_W_EFECTIVO_M[0]:.0f}-{DJI_W_EFECTIVO_M[1]:.0f} m para el T100 y aclara explicitamente que el ancho efectivo
  DEPENDE DE LA ESCENA REAL DE TRABAJO (P). Es decir: el propio fabricante reconoce que
  no es un numero unico. Medirlo es el aporte.
""")

    print("-" * 96)
    print("5. TRAMPA DEL DOE QUE HAY QUE EVITAR")
    print("-" * 96)
    print("""
  NO meter simultaneamente como variables independientes:

      tasa (L/ha), caudal (L/min), velocidad (m/s), ancho (m)

  porque estan ligados por Q = 0.006 R V W. Seria un DOE REDUNDANTE: al fijar tres, el
  cuarto queda determinado.

  Lo mismo con: tamano de gota configurado, RPM del atomizador y caudal. Si el controlador
  modifica la RPM del disco para conseguir cierto tamano de gota, NO son tres variables
  independientes.

  => Hay que saber QUE MANDA el Agras y que RESULTA de ese comando. La telemetria real
     lo revela: la configuracion de gota es un COMANDO, la RPM del atomizador es su
     CONSECUENCIA.
""")
    print("=" * 96)
    print("Modelo analitico derivado. No usa resultados de CFD.")
    print("=" * 96)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
