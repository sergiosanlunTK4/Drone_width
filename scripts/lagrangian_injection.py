"""
INYECCION LAGRANGIANA: del atomizador a las trayectorias.

CORRECCION CONCEPTUAL DEL INVESTIGADOR, que este modulo implementa:

    El ABANICO no se impone: SALE de D(x,y).
    El CAUDAL no determina el ancho: determina CUANTO liquido se inyecta.

CADENA FISICA:

    rotores  ->  U(x,y,z)                    [CFD, fuente de momento prescrita]
    Q, RPM_a, d, posicion/orientacion  ->  inyeccion de gotas
    U + gotas  ->  trayectorias  ->  D(x,y)  ->  W_deposition

CONDICION INICIAL DE LA GOTA (relativa al aire, no al suelo):

    V_gota,0  =  V_UAV  +  V_atomizador          (en el sistema del UAV)
    velocidad relativa al aire = V_gota,0 - U(x_a)

    Donde V_atomizador es la velocidad de lanzamiento del disco centrifugo,
    tipicamente tangencial con componente radial (abanico), no axial.

ECUACION DE MOVIMIENTO POR GOTA:

    m_p dV_p/dt  =  F_D  +  m_p g
    F_D          =  0.5 rho C_D(Re_p) A_p |V_aire - V_p| (V_aire - V_p)

    con C_D(Re_p) = 24/Re (1 + 0.15 Re^0.687) para Re < 1000  (Schiller-Naumann)
    y  Re_p = rho |V_aire - V_p| d / mu_aire

DE CAUDAL A PARTICULAS:

    m_dot  = rho_L Q/60000                    [kg/s]
    m_gota = rho_L pi d^3/6                   [kg]
    N_dot  = m_dot f_j / m_gota               [gotas/s] por bin j

    Cada parcela Lagrangiana representa N gotas (peso estadistico).

Uso:
  python scripts/lagrangian_injection.py
  python scripts/lagrangian_injection.py --Q 30 --rpm-atom 10000 --V 5
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# --- constantes fisicas ---------------------------------------------------------------
G = 9.80665
RHO_AIRE = 1.1572        # kg/m3, 28 C, 70% HR, nivel del mar (f(P,T,RH))
MU_AIRE = 1.86e-5        # Pa.s
RHO_L = 997.0            # kg/m3 agua a 25 C
MU_L = 8.90e-4

# --- datos del modelo medido del T100 (clase M) ---------------------------------------
MODELO = ROOT / "geometry" / "models" / "T100_CFD" / "t100_cfd_coordinates.json"

# --- datos de pulverizacion -----------------------------------------------------------
D_ATOMIZADOR_MM = 100.0      # M: disco centrifugo de 100 mm
RPM_ATOM_MAX = 14000.0       # M: regimen maximo del disco
Q_POR_BOQUILLA_NOMINAL = 10.0  # P: 40 L/min / 4 boquillas
D50_UM = 150.0               # modelo del propietario (recomendado)
D10_UM, D90_UM = 50.0, 300.0


def velocidad_lanzamiento(rpm: float, d_disco_mm: float = D_ATOMIZADOR_MM) -> dict:
    """Velocidad de lanzamiento del disco centrifugo.

    V_tip = omega * R_disco = 2 pi rpm/60 * (d_disco/2)

    ADVERTENCIA DE USO (correccion de criterio):
    V_tip es una ESCALA CARACTERISTICA y una COTA SUPERIOR. NO es la velocidad inicial
    de la gota. Confundirlas es un error de modelo, no una simplificacion aceptable:

      - V_tip es la velocidad tangencial del borde del disco. La gota se desprende del
        film/ligamento a una velocidad MENOR, con componente radial, y sufre atomizacion
        secundaria por arrastre con el aire en reposo relativo.
      - La velocidad inicial real de la gota es V_salida = f(rpm_atom, Q, d, geometria del
        disco y de la corona), y esa funcion NO esta caracterizada para los atomizadores
        Agras. Es un dato faltante, no un parametro libre a ajustar.
      - Si se usa V_tip como condicion inicial, se sobreestima sistematicamente el alcance
        radial inicial del abanico y se subestima el tiempo de acoplamiento de la gota al
        aire incidente.

    Uso permitido de V_tip en este modelo: cota superior de |V_rel|(t=0) y escala de
    comparacion con la velocidad terminal y con la velocidad del UAV. Nunca como valor de
    inyeccion. La inyeccion se declara con V_salida explicito y su clase de fuente.
    """
    R = d_disco_mm / 2000.0
    omega = rpm * 2 * math.pi / 60.0
    return {"rpm": rpm, "omega_rad_s": omega, "R_disco_m": R,
            "V_tip_ms": omega * R,
            "nota": "escala caracteristica y cota superior; NO es la velocidad de salida"}


def abanico_inicial(semiangulo_deg: float, V_salida: float) -> dict:
    """Componentes de la velocidad de salida del abanico."""
    a = math.radians(semiangulo_deg)
    return {"semiangulo_deg": semiangulo_deg,
            "V_radial_ms": V_salida * math.sin(a),
            "V_axial_ms": V_salida * math.cos(a)}


def rosin_rammler(dv50_um: float, q: float, n_bins: int, d_min_um: float,
                  d_max_um: float) -> list[dict]:
    """Distribucion Rosin-Rammler discretizada, con fraccion de masa por bin."""
    bins = []
    for i in range(n_bins):
        d0 = d_min_um + (d_max_um - d_min_um) * i / n_bins
        d1 = d_min_um + (d_max_um - d_min_um) * (i + 1) / n_bins
        f1 = 1.0 - math.exp(-((d1 / dv50_um) ** q))
        f0 = 1.0 - math.exp(-((d0 / dv50_um) ** q))
        frac = f1 - f0
        if frac > 1e-9:
            bins.append({"d_medio_um": round(0.5 * (d0 + d1), 1), "fraccion_masa": frac})
    tot = sum(b["fraccion_masa"] for b in bins)
    for b in bins:
        b["fraccion_masa"] = round(b["fraccion_masa"] / tot, 6)
    return bins


def gotas_por_bin(Q_Lmin: float, bins: list[dict]) -> list[dict]:
    """Numero de gotas por segundo en cada bin — el caudal como CANTIDAD, no como ancho."""
    m_dot = RHO_L * (Q_Lmin / 60000.0)
    out = []
    for b in bins:
        d = b["d_medio_um"] * 1e-6
        m_gota = RHO_L * math.pi * d ** 3 / 6.0
        N = (m_dot * b["fraccion_masa"]) / m_gota
        out.append({**b, "m_gota_kg": m_gota, "gotas_por_s": N})
    return out


def tiempo_respuesta(d_um: float) -> float:
    """Tiempo de respuesta de la gota: tau_p = rho_L d^2 / (18 mu_aire)."""
    d = d_um * 1e-6
    return RHO_L * d ** 2 / (18.0 * MU_AIRE)


def velocidad_terminal(d_um: float) -> float:
    """Velocidad terminal con arrastre de Schiller-Naumann, por iteracion."""
    d = d_um * 1e-6
    r = d / 2
    v = 2.0 * (RHO_L - RHO_AIRE) * G * r ** 2 / (9.0 * MU_AIRE)
    for _ in range(80):
        Re = max(RHO_AIRE * v * d / MU_AIRE, 1e-12)
        Cd = 24.0 / Re * (1.0 + 0.15 * Re ** 0.687)
        vn = math.sqrt(8.0 * (RHO_L - RHO_AIRE) * G * r / (3.0 * Cd * RHO_AIRE))
        if abs(vn - v) < 1e-10:
            v = vn
            break
        v = 0.5 * (v + vn)
    return v


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--Q", type=float, default=Q_POR_BOQUILLA_NOMINAL * 4,
                    help="caudal total L/min")
    ap.add_argument("--rpm-atom", type=float, default=10000.0)
    ap.add_argument("--V", type=float, default=5.0, help="velocidad del UAV m/s")
    a = ap.parse_args()

    print("=" * 100)
    print("INYECCION LAGRANGIANA — del atomizador a las trayectorias")
    print("=" * 100)
    print("""
  REGLA: el abanico NO se impone. SALE de D(x,y).
         El caudal NO determina el ancho: determina CUANTO liquido se inyecta.
""")

    # --- 1. geometria del atomizador (modelo medido) ---------------------------------
    print("-" * 100)
    print("1. ATOMIZADORES (posicion y orientacion del modelo medido, clase M)")
    print("-" * 100)
    if MODELO.exists():
        d = json.loads(MODELO.read_text(encoding="utf-8"))
        noz = d["spraying_system"]["nozzles"]
        print(f"\n  {'id':18s} {'X (m)':>8s} {'Y (m)':>9s} {'Z (m)':>8s}  vector inyeccion")
        for n in noz:
            c = n["center_xyz_m"]
            vec = n.get("spray_injection_vector", [0, 0, -1])
            print(f"  {n['nozzle_id']:18s} {c[0]:8.3f} {c[1]:9.4f} {c[2]:8.3f}  {vec}")
        print(f"\n  Z del atomizador = {noz[0]['center_xyz_m'][2]:.3f} m")
        print(f"  A H = 3 m de vuelo, el disco queda a "
              f"{3.0 + noz[0]['center_xyz_m'][2]:.3f} m sobre el suelo")
    else:
        print("  [FALTA el modelo; usa los valores del README]")

    # --- 2. velocidad caracteristica del disco ---------------------------------------
    print("\n" + "-" * 100)
    print("2. VELOCIDAD CARACTERISTICA DEL DISCO (V_tip) - COTA, NO CONDICION INICIAL")
    print("-" * 100)
    for rpm in (5000, 8000, 10000, RPM_ATOM_MAX):
        v = velocidad_lanzamiento(rpm)
        print(f"  {rpm:6.0f} rpm -> omega = {v['omega_rad_s']:7.2f} rad/s · "
              f"V_tip = {v['V_tip_ms']:6.2f} m/s")
    print(f"""
  {velocidad_lanzamiento(10000)['nota']}

  ADVERTENCIA: V_tip NO es la velocidad inicial de la gota.
  V_tip ~ 52 m/s a 10000 rpm es una ESCALA CARACTERISTICA y una COTA SUPERIOR del borde
  del disco. La velocidad de salida real V_salida = f(rpm_atom, Q, d, geometria) es menor
  y NO esta caracterizada para los atomizadores Agras: es un dato faltante.

  Consecuencia para el modelo: lo que decide el destino de la gota es su velocidad
  RELATIVA al aire incidente, |V_rel| = |V_salida + V_UAV - u_aire|. Ni V_tip ni V_UAV
  por separado la determinan, y no puede afirmarse cual "domina" sin conocer V_salida.
  Un modelo "caudal -> ancho" ignora ambos terminos y por eso no es defendible; sustituir
  V_salida por V_tip comete el error simetrico.
""")

    # --- 3. condicion inicial relativa al aire ---------------------------------------
    print("-" * 100)
    print("3. CONDICION INICIAL (relativa al AIRE, no al suelo)")
    print("-" * 100)
    vl = velocidad_lanzamiento(a.rpm_atom)
    print(f"  V_tip = {vl['V_tip_ms']:.2f} m/s  ->  se barre V_salida = k*V_tip, k = 0.3 .. 1.0")
    for k in (0.30, 0.60, 1.00):
        V_sal = k * vl["V_tip_ms"]
        fila = []
        for semi in (15.0, 30.0, 45.0):
            ab = abanico_inicial(semi, V_sal)
            fila.append(f"{semi:2.0f}deg: Vr={ab['V_radial_ms']:6.2f} Va={ab['V_axial_ms']:6.2f}")
        print(f"  k={k:4.2f}  V_salida={V_sal:6.2f} m/s | " + " | ".join(fila))
    print(f"""
      V_gota,0 = V_UAV + V_atomizador        (V_atomizador = V_salida, NO V_tip)
      V_relativa_al_aire = V_gota,0 - U(x_atomizador)

  V_tip NO es la velocidad de salida: k es la fraccion de desprendimiento del borde y NO
  esta medida para los discos Agras. La tabla anterior es por eso un BARRIDO DE SENSIBILIDAD
  sobre un dato faltante, no un resultado.

  El semiangulo del abanico tampoco esta medido: es parametro de sensibilidad.
  El vector de inyeccion declarado en el modelo es [0,0,-1] (axial hacia abajo), pero un
  disco centrifugo expulsa RADIALMENTE en el plano del disco. Hay que reconciliar:
      - si el disco gira en el plano horizontal del dron -> expulsion horizontal y la
        gravedad + downwash la llevan al suelo;
      - el vector [0,0,-1] seria el eje de giro, no la direccion de salida.
  [ABIERTO] Mientras esto no se cierre, la direccion inicial de la gota es clase D.
""")

    # --- 4. de caudal a particulas ---------------------------------------------------
    print("-" * 100)
    print("4. DE CAUDAL A PARTICULAS (lo que el caudal SI determina)")
    print("-" * 100)
    bins = rosin_rammler(D50_UM, q=2.0, n_bins=12, d_min_um=D10_UM, d_max_um=D90_UM * 1.5)
    gb = gotas_por_bin(a.Q, bins)
    print(f"\n  Q total = {a.Q:.1f} L/min  ->  m_dot = {RHO_L*a.Q/60000.0:.6f} kg/s")
    print(f"  Distribucion Rosin-Rammler: d50 = {D50_UM:.0f} um, q = 2.0 (supuesto), "
          f"{len(bins)} bins")
    print(f"\n  {'d (um)':>8s} {'frac masa':>10s} {'m_gota (kg)':>14s} {'gotas/s':>12s}")
    for g in gb:
        print(f"  {g['d_medio_um']:8.1f} {g['fraccion_masa']:10.4f} "
              f"{g['m_gota_kg']:14.3e} {g['gotas_por_s']:12.3e}")
    tot = sum(g["gotas_por_s"] for g in gb)
    print(f"\n  TOTAL = {tot:.3e} gotas/s por boquilla.")
    print(f"""  Inyectar eso literalmente es inviable: se usan PARCELAS con peso estadistico.
  Si cada parcela representa 1e6 gotas -> {tot/1e6:.2f} parcelas/s. Perfectamente tratable.
""")

    # --- 5. propiedades de la gota ---------------------------------------------------
    print("-" * 100)
    print("5. PROPIEDADES DE LA GOTA POR TAMANO (que determinan DONDE acaba)")
    print("-" * 100)
    print(f"\n  {'d (um)':>8s} {'tau_p (s)':>11s} {'v_term (m/s)':>13s} {'v_term/V_tip':>13s}")
    for d in (50, 100, 150, 200, 300, 500):
        tau = tiempo_respuesta(d)
        vt = velocidad_terminal(d)
        print(f"  {d:8d} {tau:11.5f} {vt:13.3f} {vt/vl['V_tip_ms']:13.4f}")
    print(f"""
  LECTURA (corregida; la version anterior tenia un error de factor ~500 en tau_p):
    tau_p = rho_d d^2 / (18 mu_aire)  ->  va de 7.4e-3 s (50 um) a 7.4e-1 s (500 um).
    NO es "despreciable frente al vuelo": para d = 500 um, tau_p ~ 0.74 s es del MISMO ORDEN
    que el tiempo de vuelo (~0.6-1 s desde 2.55 m). Esa gota llega al suelo sin haber
    alcanzado su velocidad terminal (alcanza ~55 % en 0.6 s).
    Para d <= 200 um el acoplamiento si es practicamente instantaneo (tau_p <= 0.12 s).

  CONCLUSION ROBUSTA: el atomizador lanza la gota a una velocidad 26-770 veces mayor que su
  velocidad terminal de caida. Es decir el destino de la gota lo fija el CAMPO DE AIRE
  (downwash + viento + arrastre), no la caida libre, y CADA DIAMETRO tiene su propia historia
  de aceleracion. Por eso hay que resolverlo con el Lagrangiano y no con una formula.

  NOTA sobre el dato faltante: la comparacion es contra V_tip por ser la unica escala de
  velocidad del atomizador disponible. Como V_exit <= V_tip, el cociente real es todavia
  MAS desfavorable, asi que esta conclusion se refuerza al corregir V_exit, no se debilita.
  (tau_p, en cambio, no depende de V_exit: solo de d y mu_aire.)
""")

    print("-" * 100)
    print("6. LO QUE FALTA PARA PODER INYECTAR")
    print("-" * 100)
    print("""
  MEDIDO / CONOCIDO:
    [x] posicion y orientacion de los 4 atomizadores  (M)
    [x] diametro de disco 100 mm y RPM maxima 14000   (M)
    [x] caudal nominal por boquilla 10 L/min          (P)
    [x] espectro recomendado d10/d50/d90              (modelo, E)
    [x] separacion axial del par coaxial 0.290 m      (M)

  PARAMETRO (barrido, no supuesto):
    [~] semiangulo del abanico (15/30/45 grados)
    [~] fraccion de desprendimiento k = V_salida/V_tip (0.3 .. 1.0)
    [~] parametro q de Rosin-Rammler (2.0)

  DESCONOCIDO (clase D):
    [ ] V_salida real de la gota = f(rpm_atom, Q, d, geometria)  <- dato faltante clave
    [ ] RPM real del atomizador en operacion (el 14000 es el MAXIMO)
    [ ] espectro MEDIDO (d10/d50/d90 reales, no el recomendado del modelo)
    [ ] direccion real de salida respecto al disco
    [ ] reparto de caudal entre las 4 boquillas (se asume igual)

  BLOQUEANTE EXTERNO:
    [!] el CAMPO DE AIRE U(x,y,z) — sin el, no hay trayectorias.
        Y el campo de aire depende de la fuente de momento prescrita (bug #6).
""")
    print("=" * 100)
    print("Especificacion completa. NO produce resultados: falta el campo de aire.")
    print("=" * 100)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
