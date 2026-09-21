"""
CADENA DE CALCULO: de las FUERZAS al RPM por motor — para el DJI Agras T100.

OBJETIVO (peticion del investigador):
  "saber que angulo debe tener la fuerza y con ello el angulo que tiene el dron, y con ello la
   fuerza dividida en cada brazo y dividida por cada motor, para poder saber las revoluciones
   de cada motor en funcion del tamano de las helices y la fuerza nominal"

Es decir: cerrar la cadena  FUERZA -> ACTITUD -> REPARTO -> EMPUJE POR ROTOR -> RPM.
Y hacerlo con TODAS las suposiciones declaradas para que el investigador las valide.

ESTRUCTURA DEL DOCUMENTO:
  CADA paso tiene: ecuacion, entradas con su CLASE de fuente, y la SUPOSICION que introduce.
  Las suposiciones que no puedo sostener quedan marcadas como A VALIDAR.

CONTRASTE CON LA LITERATURA:
  Solo se cita como verificada lo que paso scripts/verify_sources.py.
  El resto se declara como conocimiento general pendiente de verificacion.

Uso:
  python scripts/force_chain.py
  python scripts/force_chain.py --V 10        # una velocidad concreta
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

G = 9.80665
RHO = 1.1716            # aire a 28 C, nivel del mar
SIGMA_AIR = 1.0         # densidad relativa

# ======================================================================================
# ENTRADAS — cada una con su CLASE de fuente
#   P = publico oficial · P-A = DJI Academy · O = propietario · M = medido · E = estimado
#   D = desconocido
# ======================================================================================
ENTRADAS = {
    "masa_mtow_kg":        (175.0, "P", "ficha oficial: MTOW pulverizacion"),
    "masa_vacio_kg":       (73.0,  "O", "propietario: con bateria, 2 boquillas, sin liquido"),
    "carga_max_kg":        (100.0, "P", "ficha oficial: 100 L / 100 kg"),
    "n_brazos":            (4,     "O", "propietario: 4 brazos"),
    "motores_por_brazo":   (2,     "O", "propietario: 8 motores / 4 brazos"),
    "t_max_brazo_N":       (82.0 * G, "P-A", "Academy: 82 kg de empuje por brazo"),
    "rotor_diam_m":        (1.5748, "P", "62 pulgadas (helice 6223)"),
    "paso_in":             (23.0,  "P-A", "Academy: helice 6223 = 62x23 in"),
    "palas_por_rotor":     (2,     "P-A", "Academy/imagen: 2 palas"),
    "cuerda_media_m":      (0.085, "E", "generador del propietario, sin fuente declarada"),
    "sep_axial_par_m":     (0.290, "M", "modelo T100 medido"),
    "rpm_hover_declarado": (1850.0,"E", "generador del propietario, SIN FUENTE NI CALCULO"),
    "v_min_ms":            (1.0,   "O", "propietario"),
    "v_max_ms":            (20.0,  "O", "propietario"),
    "cd_efectivo":         (0.8,   "E", "SUPOSICION MIA: no medido, no de literatura verificada"),
    "area_frontal_m2":     (1.729, "E", "SUPOSICION MIA: 3.224 x 0.975 x 0.55"),
}


def v(nombre: str) -> float:
    return ENTRADAS[nombre][0]


# ======================================================================================
# PASO 1 — EQUILIBRIO DE FUERZAS  ->  ACTITUD
# ======================================================================================
def paso1_actitud(masa_kg: float, V: float, cd: float | None = None,
                  area: float | None = None) -> dict:
    """Equilibrio en vuelo estacionario (sin aceleracion).

    Vertical   :  T cos(theta) = W
    Horizontal :  T sin(theta) = D(V)
    =>  tan(theta) = D(V)/W  ;  T = W/cos(theta) = sqrt(W^2 + D^2)

    SUPOSICION 1: vuelo estacionario, sin aceleracion ni maniobra.
    SUPOSICION 2: D(V) = 0.5 rho Cd A V^2  con Cd y A CONSTANTES (ver Paso 1b).
    SUPOSICION 3: el empuje es perpendicular al plano del rotor (disco actuador ideal).
    """
    cd = cd if cd is not None else v("cd_efectivo")
    area = area if area is not None else v("area_frontal_m2")
    W = masa_kg * G
    D = 0.5 * RHO * cd * area * V ** 2
    theta = math.atan2(D, W)
    T = math.hypot(W, D)
    return {"V": V, "masa": masa_kg, "W": W, "D": D, "T": T,
            "theta_rad": theta, "theta_deg": math.degrees(theta)}


def paso1b_actitud_avanzada(masa_kg: float, V: float) -> dict:
    """Version con el termino que el modelo simple OMITE.

    En avance, el rotor ve una velocidad de entrada distinta en cada lado (lado que avanza /
    lado que retrocede). El disco actuador IDEAL en flujo oblicuo mantiene el empuje
    perpendicular al disco y la velocidad inducida perpendicular tambien (no hay
    componente de arrastre del rotor). Pero un rotor REAL produce un arrastre en el plano
    (H-force) que anade resistencia:

        D_total = D_fuselaje + H_rotor
        H_rotor ~ f(Cd0, sigma, mu, Ct)   con mu = V/(Omega R) = relacion de avance

    NO se implementa aqui porque exige datos de pala (Cd0 por seccion) que NO tenemos.
    Se deja como TERMINO FALTANTE declarado, y es una razon para MEDIR la actitud.
    """
    return {"implementado": False,
            "falta": "Cd0 de la pala y geometria de seccion",
            "efecto": "aumentaria D y por tanto theta",
            "consecuencia": "el modelo simple SUBESTIMA theta"}


# ======================================================================================
# PASO 2 — REPARTO POR BRAZO
# ======================================================================================
def paso2_brazos(T_total: float) -> dict:
    """Reparto del empuje total entre los brazos.

    SUPOSICION 4: reparto SIMETRICO por brazo cuando el CG esta en el centro.
    Es correcto SOLO si el CG coincide con el centro geometrico. Si el CG esta desplazado
    (bateria, tanque, atomizadores), el reparto NO es uniforme y hay que medirlo.
    """
    nb = int(v("n_brazos"))
    return {"n_brazos": nb, "T_por_brazo": T_total / nb,
            "suposicion": "CG en el centro geometrico",
            "validez": "a verificar con la posicion real del CG"}


# ======================================================================================
# PASO 3 — REPARTO POR MOTOR (el punto critico en coaxial)
# ======================================================================================
def paso3_motores(T_brazo: float, split: float = 0.5) -> dict:
    """Reparto del empuje del brazo entre los DOS motores/rotores del par coaxial.

    AQUI ESTA LA INCOGNITA CENTRAL DEL MODELO COAXIAL.

    Lo que sabemos:
      - 2 motores por brazo (propietario, clase O)
      - 82 kg de empuje POR BRAZO (Academy, clase P-A)  -> es el total del par, no por rotor
    Lo que NO sabemos:
      - como se reparte ese empuje entre el rotor SUPERIOR y el INFERIOR

    Por que no se puede suponer 50/50 sin justificarlo:
      El rotor inferior opera en la estela del superior: ve una velocidad de entrada mayor,
      con lo que para el mismo regimen entrega MENOS empuje. Ademas el reparto depende de la
      asignacion de control (que el flight controller decide) y del equilibrio de par.
      Ver geometry/coaxial_thrust_split.md.

    => Se trata como PARAMETRO, con barrido 0.5 / 0.6 / 0.7, y se reporta la sensibilidad.
    """
    return {"T_superior": T_brazo * split, "T_inferior": T_brazo * (1 - split),
            "split_superior": split,
            "clasificacion": "D (desconocido): PARAMETRO, no supuesto"}


# ======================================================================================
# PASO 4 — EMPUJE A RPM: dos caminos
# ======================================================================================
def paso4a_coeficiente_efectivo(T_rotor: float, rpm: float) -> dict:
    """CAMINO A — despejar el coeficiente de empuje efectivo de un punto conocido.

    De la definicion de coeficiente de empuje:
        T = Ct * rho * A * (Omega R)^2
    =>  Ct_efectivo = T / (rho * A * (Omega R)^2)

    Esto NO mide un coeficiente de pala: es un coeficiente EFECTIVO del conjunto rotor
    completo que absorbe todas las incognitas (perfil, twist, perdidas de punta, etc.).
    Sirve si hay UN punto (T, rpm) fiable; entonces escala a otros regimenes.

    OJO: el punto de partida (214.5 N, 1850 rpm) viene del generador del propietario
    SIN FUENTE NI CALCULO. Es decir: este camino ARRASTRA esa suposicion.
    """
    A = math.pi * (v("rotor_diam_m") / 2) ** 2
    R = v("rotor_diam_m") / 2
    Omega = rpm * 2 * math.pi / 60.0
    ct = T_rotor / (RHO * A * (Omega * R) ** 2)
    return {"A_m2": A, "R_m": R, "Omega_rad_s": Omega,
            "Ct_efectivo": ct, "punto_de_anclaje": f"T={T_rotor} N, rpm={rpm}"}


def paso4b_rpm_desde_Ct(T_rotor: float, ct: float) -> float:
    """Inverso: dado Ct_efectivo, el rpm necesario para un empuje."""
    A = math.pi * (v("rotor_diam_m") / 2) ** 2
    R = v("rotor_diam_m") / 2
    val = T_rotor / (ct * RHO * A)
    return math.sqrt(val) / R * 60.0 / (2 * math.pi)


def paso4c_bemt_ideal(T_rotor: float) -> dict:
    """CAMINO B — BEMT simplificado (teoria de elemento de pala + cantidad de movimiento).

    Modelo clasico de helice en hover, con sustentacion lineal y sin perdidas de punta:

        Ct_sigma = (sigma * a / 2) * (theta_tw/2 - lambda/2) ... (forma completa, no usada)

    Version de orden cero (sin twist, sin perdidas), util como CONTRASTE de plausibilidad:
        T = 0.5 * rho * a * sigma * Omega^2 * R^4 * (theta_0/3 - lambda/2)
    es demasiado gruesa sin datos de pala. Se usa en su lugar la forma compacta:

        FM (figura de merito) = P_ideal / P_real ~ 0.7

    Lo que SI se puede hacer sin datos de pala, y es lo que se hace aqui:
        usando cantidad de movimiento, la velocidad inducida en hover es
            v_i = sqrt(T / (2 rho A))
        y la potencia inducida ideal            P_i = T * v_i
        y con una figura de merito supuesta     P = P_i / FM

    Eso da POTENCIA, no RPM. Para RPM hace falta el coeficiente de empuje, que exige
    geometria de pala real. => Se declara el limite.
    """
    A = math.pi * (v("rotor_diam_m") / 2) ** 2
    vi = math.sqrt(T_rotor / (2 * RHO * A))
    Pi = T_rotor * vi
    return {"A_m2": A, "v_inducida_ms": vi, "P_ideal_W": Pi,
            "FM_supuesta": 0.70, "P_real_estimada_W": Pi / 0.70,
            "aviso": "esto da POTENCIA, no RPM. El RPM exige geometria de pala real."}


def paso4d_limite_fisico() -> dict:
    """Comprobacion de plausibilidad: solidez, carga de disco y regimen tipico.

    La solidez sigma = (n_palas * cuerda) / (pi * R) acota el rango de Ct alcanzable.
    """
    R = v("rotor_diam_m") / 2
    sigma = (v("palas_por_rotor") * v("cuerda_media_m")) / (math.pi * R)
    A = math.pi * R ** 2
    return {"solidez_sigma": round(sigma, 5),
            "A_disco_m2": round(A, 4),
            "nota": "sigma tipico de helice de dron: 0.05-0.15. En rango."}


# ======================================================================================
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--V", type=float, default=None)
    a = ap.parse_args()

    print("=" * 100)
    print("CADENA DE CALCULO  FUERZA -> ACTITUD -> REPARTO -> EMPUJE POR ROTOR -> RPM")
    print("DJI Agras T100")
    print("=" * 100)

    print("\n" + "-" * 100)
    print("PASO 0 — ENTRADAS, con su clase de fuente")
    print("-" * 100)
    print(f"\n  {'variable':26s} {'valor':>12s}  {'clase':6s} fuente")
    for k, (val, clase, fuente) in ENTRADAS.items():
        print(f"  {k:26s} {val:12.4f}  {clase:6s} {fuente}")

    print("\n  AVISO SOBRE LAS ENTRADAS CLASE E:")
    print("    'cd_efectivo' y 'area_frontal_m2' son SUPOSICIONES MIAS, no medidas ni de")
    print("    literatura verificada. Y 'rpm_hover_declarado' viene del generador del")
    print("    propietario SIN FUENTE NI CALCULO. Las tres son A VALIDAR.")

    print("\n" + "-" * 100)
    print("PASO 1 — EQUILIBRIO DE FUERZAS  ->  ACTITUD")
    print("-" * 100)
    print("""
  Ecuaciones (equilibrio estatico en vuelo nivelado):

      Vertical   :  T cos(theta) = W
      Horizontal :  T sin(theta) = D(V)
      ----------------------------------
      =>  tan(theta) = D(V) / W
      =>  T = sqrt(W^2 + D^2)          (el empuje TOTAL, no solo el que sostiene)

      D(V) = 0.5 * rho * Cd * A_frontal * V^2

  SUPOSICIONES:
    1. Vuelo estacionario (sin aceleracion, sin maniobra).
    2. Cd y A_frontal CONSTANTES con V.  <-- A VALIDAR (el Cd real varia con Re)
    3. Empuje perpendicular al disco (disco actuador ideal).
    4. No se incluye el arrastre de las helices (H-force).  <-- SUBESTIMA theta
""")

    global_v = a.V if a.V else None
    V_test = [3, 5, 8, 10, 13, 15, 20]
    if global_v:
        V_test = [global_v]

    print(f"  {'V (m/s)':>8s} {'D (N)':>9s} {'W (N)':>9s} {'theta (deg)':>12s} "
          f"{'T total (N)':>12s} {'T/W':>7s}")
    for V in V_test:
        r = paso1_actitud(v("masa_mtow_kg"), V)
        print(f"  {V:8.1f} {r['D']:9.2f} {r['W']:9.2f} {r['theta_deg']:12.3f} "
              f"{r['T']:12.1f} {r['T']/r['W']:7.4f}")

    print(f"\n  Termino FALTANTE (paso1b): {paso1b_actitud_avanzada(v('masa_mtow_kg'), 10.0)}")

    print("\n" + "-" * 100)
    print("PASO 2 — REPARTO POR BRAZO")
    print("-" * 100)
    r1 = paso1_actitud(v("masa_mtow_kg"), 10.0)
    r2 = paso2_brazos(r1["T"])
    print(f"\n  A 10 m/s: T total = {r1['T']:.1f} N  ->  {r2['n_brazos']} brazos")
    print(f"  T por brazo = {r2['T_por_brazo']:.2f} N")
    print(f"  Suposicion: {r2['suposicion']}  ->  {r2['validez']}")

    print("\n" + "-" * 100)
    print("PASO 3 — REPARTO POR MOTOR  (INCOGNITA CENTRAL DEL MODELO COAXIAL)")
    print("-" * 100)
    print("""
  Cada brazo lleva DOS motores/rotores (coaxial). Lo que sabemos y lo que no:

    SABEMOS : 2 motores por brazo (O); 82 kg de empuje POR BRAZO (P-A)
    NO SABEMOS: como se reparte ese empuje entre el rotor SUPERIOR y el INFERIOR

  Por que NO se puede suponer 50/50 sin justificarlo:
    El rotor inferior opera en la estela del superior: ve mayor velocidad de entrada y para
    el mismo regimen entrega MENOS empuje. Ademas el reparto lo decide la asignacion de
    control del flight controller y el equilibrio de par.  Ver coaxial_thrust_split.md.

  => Se trata como PARAMETRO con barrido, y se reporta la sensibilidad.
""")
    print(f"  {'split superior':>15s} {'T sup (N)':>11s} {'T inf (N)':>11s} {'diferencia':>11s}")
    for s in (0.5, 0.6, 0.7):
        r3 = paso3_motores(r2["T_por_brazo"], s)
        print(f"  {s:15.2f} {r3['T_superior']:11.2f} {r3['T_inferior']:11.2f} "
              f"{r3['T_superior']-r3['T_inferior']:+11.2f}")

    print("\n" + "-" * 100)
    print("PASO 4 — DE EMPUJE A RPM")
    print("-" * 100)
    print("""
  CAMINO A — coeficiente de empuje EFECTIVO, anclado a un punto conocido:

      T = Ct * rho * A * (Omega R)^2     =>     Ct = T / (rho A (Omega R)^2)

    Es un coeficiente del CONJUNTO rotor (absorbe perfil, twist, perdidas de punta...).
    Sirve si existe UN punto (T, rpm) fiable; entonces escala a otros regimenes.

    EL PROBLEMA: el punto de anclaje (214.5 N, 1850 rpm) viene del generador del
    propietario SIN FUENTE NI CALCULO. -> Este camino ARRASTRA esa suposicion.
""")
    T_rot = v("masa_mtow_kg") * G / 8.0
    r4a = paso4a_coeficiente_efectivo(T_rot, v("rpm_hover_declarado"))
    print(f"    Punto de anclaje     : T = {T_rot:.2f} N , rpm = {v('rpm_hover_declarado'):.0f}")
    print(f"    Area de disco        : {r4a['A_m2']:.4f} m2")
    print(f"    Omega R (velocidad de punta) = {r4a['Omega_rad_s']*r4a['R_m']:.2f} m/s")
    print(f"    =>  Ct_efectivo = {r4a['Ct_efectivo']:.5f}")
    print(f"\n    Comprobacion de plausibilidad: {paso4d_limite_fisico()}")

    print(f"\n    Escalado con ese Ct (rpm necesario segun el empuje por rotor):")
    print(f"    {'split':>7s} {'T rotor (N)':>12s} {'rpm':>9s} {'delta vs 1850':>14s}")
    for s in (0.5, 0.6, 0.7):
        for cual, T_r in (("sup", r2["T_por_brazo"] * s), ("inf", r2["T_por_brazo"] * (1 - s))):
            rpm = paso4b_rpm_desde_Ct(T_r, r4a["Ct_efectivo"])
            print(f"    {s:7.2f} {T_r:12.2f} {rpm:9.1f} {rpm-1850:14.1f}   ({cual})")

    print("""
  CAMINO B — BEMT / cantidad de movimiento:

    Da la POTENCIA y la velocidad inducida, pero NO el RPM:
        v_i = sqrt(T/(2 rho A)) ;  P_i = T * v_i ;  P = P_i / FM

    Para RPM hace falta la geometria real de pala (cuerda por seccion, twist, Cd0), que
    NO tenemos: el modelo solo declara 'cuerda media = 0.085 m' sin distribucion.
""")
    r4c = paso4c_bemt_ideal(T_rot)
    print(f"    v_inducida (un rotor)  = {r4c['v_inducida_ms']:.3f} m/s")
    print(f"    P ideal (un rotor)     = {r4c['P_ideal_W']:.1f} W")
    print(f"    P estimada (FM=0.70)   = {r4c['P_real_estimada_W']:.1f} W")
    print(f"    x8 rotores             = {8*r4c['P_real_estimada_W']/1000:.2f} kW")

    print("\n" + "=" * 100)
    print("SUPOSICIONES A VALIDAR POR EL INVESTIGADOR")
    print("=" * 100)
    print("""
  [1] Cd_efectivo = 0.8 y A_frontal = 1.729 m2  -> SUPOSICION MIA (clase E)
      Impacto: theta a 20 m/s varia entre 4.9 y 18.3 grados segun Cd*A. FACTOR 4.
      Como cerrarlo: medir la actitud real (telemetria del Agras o video lateral) a
      varias velocidades. Es barato y de alto impacto.

  [2] rpm_hover = 1850  -> del generador del propietario, SIN FUENTE NI CALCULO
      Impacto: TODA la cadena de RPM cuelga de este numero.
      Como cerrarlo: (a) fuente del dato, o (b) medicion con tacometro en hover.

  [3] Reparto superior/inferior = 0.5  -> INCOGNITA (clase D), no suposicion
      Impacto: el empuje por rotor varia +-20% con split 0.6.
      Como cerrarlo: saber si el par comparte motor o si son dos independientes (A10),
      y medir RPM de ambos rotores simultaneamente.

  [4] 'cuerda_media = 0.085 m' sin distribucion -> impide BEMT real
      Impacto: bloquea el calculo de RPM por teoria de pala.
      Como cerrarlo: medir la pala (cuerda en raiz/punta, twist, perfil).

  [5] No se incluye el arrastre de las helices (H-force) -> SUBESTIMA theta
      Impacto: no cuantificado; requiere Cd0 de pala.
      Como cerrarlo: igual que [4], o medicion directa de actitud.

  [6] Cd constante con V -> en realidad varia con Re
      Impacto: pequeno en el rango de interes, pero debe declararse.

  LO QUE ESTA BIEN Y NO REQUIERE VALIDACION:
    - El equilibrio de fuerzas (Paso 1) es fisica elemental: no necesita cita.
    - La teoria de cantidad de movimiento (Paso 4, camino B) es estandar.
    - La geometria del T100 esta MEDIDA (clase M, +-0.2, resolucion 0.1).
""")
    print("=" * 100)
    print("Este script es un MODELO ANALITICO. No usa resultados de CFD ni los sustituye.")
    print("=" * 100)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
