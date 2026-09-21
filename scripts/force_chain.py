"""
CADENA DE CALCULO — FUERZAS + MOMENTOS -> ACTITUD -> TRIM -> EMPUJE POR ROTOR -> RPM.

CORRECCIONES APLICADAS tras la revision del investigador (2026-09-19):

  [A] ELIMINADA una deduccion ERRONEA. La version anterior afirmaba que "momentum theory da
      Ct ~ 0.0061 y por tanto el RPM coherente es 2275, no 1850". ESO ERA FALSO Y CIRCULAR.
      De la propia definicion Ct = T/(rho A (Omega R)^2) se sigue lambda_i = sqrt(Ct/2) y
      v_i = lambda_i * Omega R, que da EXACTAMENTE lo mismo que sqrt(T/(2 rho A)):
          1850 rpm -> Ct = 0.00404 -> v_i = 6.8558 m/s   (por las dos vias)
      Momentum theory NO proporciona un segundo Ct independiente. Sirve para POTENCIA, no
      para RPM. Conclusion correcta: 1850 rpm NO esta validado, pero TAMPOCO refutado.
      Simplemente NO SE SABE.

  [B] DOS COEFICIENTES CON EL MISMO NOMBRE. Se separan explicitamente:
        Ct_rotor = T/(rho A (Omega R)^2)      rotorcraft / BEMT, normalizado con Omega R
        Ct_OF, Cp_OF                          formulacion Froude de actuationDiskSource,
                                              normalizada con la velocidad incidente U_o
      NO son el mismo coeficiente.

  [C] Cp = 0. No es "fisicamente imposible". Es una RESTRICCION DEL MODELO
      actuationDiskSource/Froude, que aborta si Cp o Ct no son positivos. En hover U_inf = 0
      y cualquier coeficiente normalizado con U_inf^3 es una descripcion incomoda; en
      rotorcraft se normaliza con Omega R. Esa es la razon real.

  [D] ACTITUD: el parametro es la VELOCIDAD RELATIVA AL AIRE V_air = V_ground - V_wind, y el
      area proyectada y el Cd dependen del propio angulo -> la ecuacion es IMPLICITA
      y se resuelve iterativamente.

  [E] TRIM: falta el equilibrio de MOMENTOS. No basta sum(F)=0. Para obtener el reparto por
      brazo hay que resolver sum(M_CG)=0 con el centro de presion del arrastre respecto al CG.

  [F] DENSIDAD: rho = f(P, T, RH), no solo temperatura.

  [G] NOMBRES CORREGIDOS:
        "actitud maxima teorica"  -> "limite estatico por magnitud de empuje"
        "desplazamiento del abanico" -> "baseline geometrico (NO es desplazamiento de deposicion)"
        H8 "hallazgo"             -> "hipotesis derivada del modelo de trim"

  [H] ELIMINADO: la pregunta "comparte motor el par?" ya no aplica. Son 4 brazos, 8 motores,
      8 rotores. La incognita es T_sup/T_inf y RPM_sup/RPM_inf, y la estrategia de control.

Uso:
  python scripts/force_chain.py
  python scripts/force_chain.py --V 10 --rho 1.1716
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

G = 9.80665

# ======================================================================================
# ENTRADAS — cada una con su CLASE de fuente
# ======================================================================================
ENTRADAS = {
    "masa_mtow_kg":        (175.0, "P",     "ficha oficial: MTOW pulverizacion"),
    "masa_vacio_kg":       (73.0,  "O",     "propietario: con bateria, 2 boquillas, sin liquido"),
    "carga_max_kg":        (100.0, "P",     "ficha oficial: 100 L / 100 kg"),
    "n_brazos":            (4,     "O/M",   "propietario + modelo medido"),
    "motores_por_brazo":   (2,     "O/M",   "propietario: 4 brazos, 8 motores, 8 rotores"),
    "t_max_brazo_N":       (82.0 * G, "P-A","Academy: 82 kg de empuje por brazo"),
    "rotor_diam_m":        (1.5748, "P",    "62 pulgadas (helice 6223)"),
    "palas_por_rotor":     (2,     "P-A",   "Academy/imagen"),
    "sep_axial_par_m":     (0.290, "M",     "modelo T100 medido"),
    "v_min_ms":            (1.0,   "O",     "propietario"),
    "v_max_ms":            (20.0,  "O",     "propietario"),
    # --- supuestos debiles, declarados como tales ---
    "cd_efectivo":         (0.8,   "E",     "SUPOSICION: no medido, no verificado en literatura primaria"),
    "area_frontal_m2":     (1.729, "E",     "SUPOSICION: 3.224 x 0.975 x 0.55, factor inventado"),
    "rho_kg_m3":           (1.1716,"E",     "aire seco a 28 C, nivel del mar. Deberia ser f(P,T,RH)"),
    "x_cp_cg_m":           (0.0,   "D",     "distancia centro de presion a CG: DESCONOCIDA"),
}


def v(n: str) -> float:
    return ENTRADAS[n][0]


# ======================================================================================
# DENSIDAD DEL AIRE  rho = f(P, T, RH)
# ======================================================================================
def densidad_aire(T_C: float, P_Pa: float, RH_pct: float = 0.0) -> float:
    """Densidad del aire humedo (aproximacion estandar de gas ideal + presion de vapor).

    POR QUE: fijar rho por temperatura sola no es suficiente para un estudio de campo.
    Se usa la ley de los gases con correccion de humedad.

      P_d = P - P_v            (presion del aire seco)
      P_v = RH * P_sat(T)      (presion de vapor; Magnus)
      rho = P_d/(R_d T) + P_v/(R_v T)
    """
    T = T_C + 273.15
    # presion de saturacion (Magnus)
    P_sat = 610.94 * math.exp((17.625 * T_C) / (T_C + 243.04))
    P_v = (RH_pct / 100.0) * P_sat
    P_d = P_Pa - P_v
    R_d, R_v = 287.058, 461.495
    return P_d / (R_d * T) + P_v / (R_v * T)


def presion_isa(altitud_m: float) -> float:
    """Presion atmosferica ISA a una altitud dada (Pa)."""
    return 101325.0 * (1.0 - 2.25577e-5 * altitud_m) ** 5.25588


# ======================================================================================
# PASO 1 — ACTITUD: equilibrio de fuerzas, con ecuacion IMPLICITA
# ======================================================================================
def actitud(V_aire: float, masa_kg: float, rho: float | None = None,
            cd0: float | None = None, area0: float | None = None,
            area_depende_de_theta: bool = False) -> dict:
    """Equilibrio de fuerzas en vuelo horizontal uniforme (modelo cuasiestacionario).

        Vertical   : T cos(theta) = W
        Horizontal : T sin(theta) = D
        =>  tan(theta) = D/W  ;  T = sqrt(W^2 + D^2)

    CORRECCIONES:
      - El parametro es V_AIRE (velocidad relativa al aire), no la velocidad sobre el suelo.
      - D puede depender de theta a traves de A_proj(theta): entonces la ecuacion es
        IMPLICITA y se resuelve por iteracion de punto fijo.

    *** ADVERTENCIA SOBRE EL MODELO DE AREA PROYECTADA ***
      La version con A_proj(theta) = A_frontal*cos(theta) + A_planta*sin(theta) NO es
      utilizable con los datos actuales: trata la PLANTA COMPLETA (3.224 x 3.224 = 10.4 m2)
      como placa plana de Cd = 0.8, y a 20 m/s da theta = 41 grados, que es fisicamente
      absurdo para un dron agricola.

      Lo que falta es el ARRASTRE EN DIRECCION VERTICAL (la "planta" del dron), que es un
      dato DISTINTO del arrastre frontal y NO se conoce (clase D). Tratar la planta como
      placa plana con el mismo Cd es una extrapolacion sin base.

      => Por defecto se usa el modelo EXPLICITO con solo el area frontal (A constante).
         La correccion por actitud queda implementada pero DESACTIVADA, y su activacion
         exige antes calibrar el arrastre vertical — preferiblemente midiendo la actitud real.

    SUPOSICIONES (declaradas):
      1. Vuelo estacionario, sin aceleracion ni maniobra.
      2. Cd y A constantes en el modelo por defecto.
      3. Empuje perpendicular al disco (disco actuador ideal).
      4. NO se incluye el arrastre de las helices (H-force) -> SUBESTIMA theta.
    """
    rho = rho if rho is not None else v("rho_kg_m3")
    cd0 = cd0 if cd0 is not None else v("cd_efectivo")
    area0 = area0 if area0 is not None else v("area_frontal_m2")
    A_planta = 3.224 * 3.224      # proyeccion horizontal (P: 3224 mm), NO calibrada como placa
    W = masa_kg * G

    def A_proj(th: float) -> float:
        """Area proyectada. Solo se usa si area_depende_de_theta=True (ver advertencia)."""
        if not area_depende_de_theta:
            return area0
        return area0 * math.cos(th) + A_planta * math.sin(th)

    theta = 0.0
    for _ in range(80):
        D = 0.5 * rho * cd0 * A_proj(theta) * V_aire ** 2
        nuevo = math.atan2(D, W)
        if abs(nuevo - theta) < 1e-9:
            theta = nuevo
            break
        theta = 0.5 * (theta + nuevo)     # relajacion

    D = 0.5 * rho * cd0 * A_proj(theta) * V_aire ** 2
    return {"V_aire": V_aire, "masa": masa_kg, "rho": rho, "W": W, "D": D,
            "T": math.hypot(W, D), "theta_rad": theta, "theta_deg": math.degrees(theta),
            "implicita": area_depende_de_theta}


# ======================================================================================
# PASO 2 — TRIM: equilibrio de FUERZAS y de MOMENTOS
# ======================================================================================
def trim(masa_kg: float, V_aire: float, theta_deg: float, rho: float,
         x_cp_cg: float, r_bracos: float, n_brazos: int = 4) -> dict:
    """Resuelve el reparto por brazo con sum(F)=0 Y sum(M_CG)=0.

    POR QUE ES NECESARIO (correccion [E] del investigador):
      Dividir T/4 solo es valido si el CG esta en el centro geometrico Y la resultante
      aerodinamica pasa por el CG. En general hay un MOMENTO DE CABECEO que el reparto de
      rotores debe compensar:

          sum_i (r_i - r_CG) x T_i  +  M_aero  =  0

    Modelo simplificado en el plano X-Z (cabeceo):
      - brazos delanteros a +d del CG, traseros a -d  (d = r_bracos/sqrt(2) en X)
      - el arrastre actua a una altura/distancia x_cp_cg del CG y genera momento D*x_cp_cg
      - reparto lineal: T_del = T/4 + dM/(2d) ; T_tras = T/4 - dM/(2d)

    >>> Si x_cp_cg = 0 (arrastre pasando por el CG) se recupera el reparto simetrico T/4.
    >>> x_cp_cg es DESCONOCIDO (clase D): por eso el resultado se reporta como sensible a el.
    """
    W = masa_kg * G
    th = math.radians(theta_deg)
    T_tot = math.hypot(W, 0.5 * rho * v("cd_efectivo") * v("area_frontal_m2") * V_aire ** 2)
    D = T_tot * math.sin(th)

    # momento de cabeceo por el arrastre respecto al CG
    M_aero = D * x_cp_cg

    # distancia longitudinal de cada brazo al CG (componente X)
    d = r_bracos / math.sqrt(2.0)
    # cada par delantero/trasero soporta 2 brazos -> 2 rotores_por_brazo... simplificando:
    # 2 brazos delanteros y 2 traseros
    if d > 0:
        dT = M_aero / (2.0 * d)          # desequilibrio de empuje entre delantero y trasero
    else:
        dT = 0.0
    T_base = T_tot / n_brazos
    T_del = T_base + dT / 2.0
    T_tras = T_base - dT / 2.0
    return {"T_total": T_tot, "M_aero": M_aero, "d_brazo_x": d,
            "T_brazo_delantero": T_del, "T_brazo_trasero": T_tras,
            "T_brazo_promedio": T_base,
            "x_cp_cg": x_cp_cg,
            "nota": ("con x_cp_cg = 0 el reparto vuelve a ser simetrico. Con x_cp_cg != 0 "
                     "aparece desequilibrio delantero/trasero.")}


# ======================================================================================
# PASO 3 — REPARTO COAXIAL (incognita D, parametro)
# ======================================================================================
def reparto_coaxial(T_brazo: float, s: float) -> dict:
    """s = fraccion del empuje del brazo que va al rotor SUPERIOR.

    INCOGNITA: no se conoce T_sup/T_inf ni RPM_sup/RPM_inf. La arquitectura SI se conoce:
    4 brazos, 8 motores, 8 rotores. Lo que falta es el reparto y la estrategia de control.
    """
    return {"T_superior": T_brazo * s, "T_inferior": T_brazo * (1 - s), "s": s}


# ======================================================================================
# PASO 4 — RPM: TRES VIAS SEPARADAS (correccion [A] y [B])
# ======================================================================================
def via1_momentum(T: float, rho: float, d_rotor: float) -> dict:
    """VIA 1 — momentum theory. Da POTENCIA, NO RPM.

    v_i = sqrt(T/(2 rho A)) ; P_i = T v_i.
    NO proporciona un segundo Ct independiente: de la definicion de Ct se sigue
    lambda_i = sqrt(Ct/2) y v_i = lambda_i Omega R, que es LO MISMO.
    """
    A = math.pi * (d_rotor / 2) ** 2
    vi = math.sqrt(T / (2 * rho * A))
    return {"A_m2": A, "v_inducida_ms": vi, "P_ideal_W": T * vi,
            "aviso": "esto da POTENCIA y velocidad inducida, NO RPM"}


def via2_punto_experimental(T: float, rpm: float, rho: float, d_rotor: float) -> dict:
    """VIA 2 — punto experimental (T, RPM) medidos SIMULTANEAMENTE.

    Ct_rotor = T / (rho A (Omega R)^2)          <- definicion rotorcraft, normalizada con Omega R

    AVISO CRITICO: si el RPM NO se ha medido, este Ct es el Ct de un RPM SUPUESTO. Usarlo
    despues para "demostrar" que el RPM supuesto era correcto es CIRCULAR. Solo vale como
    interpolacion en un entorno limitado del punto REALMENTE medido.
    """
    A = math.pi * (d_rotor / 2) ** 2
    R = d_rotor / 2
    OmR = rpm * 2 * math.pi / 60.0 * R
    ct = T / (rho * A * OmR ** 2)
    # verificacion de coherencia: lambda_i = sqrt(Ct/2) y v_i = lambda_i Omega R
    lam = math.sqrt(ct / 2.0)
    vi_desde_ct = lam * OmR
    vi_directo = math.sqrt(T / (2 * rho * A))
    return {"Ct_rotor": ct, "OmegaR_ms": OmR, "lambda_i": lam,
            "v_i_desde_Ct": vi_desde_ct, "v_i_directo": vi_directo,
            "diferencia": abs(vi_desde_ct - vi_directo),
            "aviso": "mismo v_i por las dos vias: momentum NO da un Ct independiente"}


def via3_bemt(disponible: bool = False) -> dict:
    """VIA 3 — BEMT / curvas de helice. Es la UNICA via que PREDICE RPM desde empuje.

    Requiere mucho mas que diametro:
      - geometria radial completa: cuerda(r), twist(r), planform
      - caracteristicas de seccion: Cl(alpha, Re, M) y Cd(alpha, Re, M)
      - numero de palas, solidez, velocidad de punta, Reynolds
      - y en coaxial: interferencia entre los dos rotores, que NO permite asumir un Ct comun
    """
    return {"disponible": disponible,
            "falta": ["cuerda(r) y twist(r) por estacion",
                      "Cl(alpha, Re, M) y Cd(alpha, Re, M) de la seccion",
                      "numero de Reynolds de la pala",
                      "modelo de interferencia coaxial"],
            "conclusion": "SIN esto no se puede PREDECIR RPM. Solo medirlo."}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--V", type=float, default=None, help="velocidad relativa al aire (m/s)")
    ap.add_argument("--rho", type=float, default=None)
    ap.add_argument("--T_C", type=float, default=28.0)
    ap.add_argument("--P_Pa", type=float, default=None)
    ap.add_argument("--RH", type=float, default=70.0)
    ap.add_argument("--alt", type=float, default=0.0)
    a = ap.parse_args()

    print("=" * 100)
    print("CADENA DE CALCULO — FUERZAS + MOMENTOS -> ACTITUD -> TRIM -> EMPUJE -> RPM")
    print("DJI Agras T100 · version CORREGIDA tras revision del investigador")
    print("=" * 100)

    # --- densidad real -----------------------------------------------------------
    P = a.P_Pa if a.P_Pa else presion_isa(a.alt)
    rho_calc = densidad_aire(a.T_C, P, a.RH)
    print(f"\n  DENSIDAD DEL AIRE  rho = f(P, T, RH)   [correccion F]")
    print(f"    T = {a.T_C} C · P = {P:.0f} Pa · RH = {a.RH} % · alt = {a.alt} m")
    print(f"    rho = {rho_calc:.4f} kg/m3")
    print(f"    (el valor fijo 1.1716 correspondia a aire SECO a 28 C al nivel del mar)")
    rho = a.rho if a.rho else rho_calc

    # --- PASO 0 ---------------------------------------------------------------
    print("\n" + "-" * 100)
    print("PASO 0 — ENTRADAS con su clase de fuente")
    print("-" * 100)
    print(f"\n  {'variable':24s} {'valor':>13s}  {'clase':9s} fuente")
    for k, (val, clase, fuente) in ENTRADAS.items():
        print(f"  {k:24s} {val:13.4f}  {clase:9s} {fuente}")

    # --- PASO 1 ---------------------------------------------------------------
    print("\n" + "-" * 100)
    print("PASO 1 — ACTITUD (ecuacion IMPLICITA)   [correccion D]")
    print("-" * 100)
    print("""
      Vertical   :  T cos(theta) = W
      Horizontal :  T sin(theta) = D(V_aire)
      =>  tan(theta) = D/W        T = sqrt(W^2 + D^2)

      D = 0.5 rho V_aire^2 Cd(theta) A_proj(theta)

      El parametro es V_AIRE (relativa al aire), NO la velocidad sobre el suelo:
          V_aire = V_suelo - V_viento
      Y como A y Cd pueden depender de theta, la ecuacion se resuelve ITERATIVAMENTE.
      (En esta version A_proj se deja constante salvo que se active la dependencia; el
       modelo completo esta en la funcion actitud().)
""")
    Vs = [a.V] if a.V else [3, 5, 8, 10, 13, 15, 20]
    print(f"  {'V_aire':>8s} {'D (N)':>9s} {'W (N)':>9s} {'theta (deg)':>12s} {'T (N)':>9s}")
    for V in Vs:
        r = actitud(V, v("masa_mtow_kg"), rho)
        print(f"  {V:8.1f} {r['D']:9.2f} {r['W']:9.2f} {r['theta_deg']:12.3f} {r['T']:9.1f}")

    theta_max = math.degrees(math.acos(min(1.0, v("masa_mtow_kg") * G / (4 * v("t_max_brazo_N")))))
    print(f"""
  LIMITE ESTATICO POR MAGNITUD DE EMPUJE  [correccion G]
      cos(theta_lim) = W / T_max  ->  theta_lim = {theta_max:.1f} grados
      NO es "la actitud maxima del dron". Ignora: perdida de capacidad en avance, potencia
      electrica disponible, interferencia coaxial, limites del controlador, bateria,
      estabilidad y momentos. Es solo una cota superior por magnitud de empuje.
""")

    # --- PASO 2 ---------------------------------------------------------------
    print("-" * 100)
    print("PASO 2 — TRIM: equilibrio de FUERZAS y MOMENTOS   [correccion E]")
    print("-" * 100)
    print("""
      CORRECCION IMPORTANTE: no basta dividir T/4. Hay que satisfacer tambien

          sum_i (r_i - r_CG) x T_i  +  M_aero  =  0

      El arrastre actua en el CENTRO DE PRESION, que no coincide con el CG. Ese desfase
      genera un momento de cabeceo que el reparto de rotores debe COMPENSAR.
""")
    r_bracos = v("rotor_diam_m") / 2 + 0.3
    for x_cp in (-0.05, 0.0, 0.05):
        t = trim(v("masa_mtow_kg"), 10.0, actitud(10.0, v("masa_mtow_kg"), rho)["theta_deg"],
                 rho, x_cp, r_bracos)
        print(f"    x_cp_cg = {x_cp:+.3f} m  ->  T delantero = {t['T_brazo_delantero']:7.2f} N   "
              f"T trasero = {t['T_brazo_trasero']:7.2f} N   (delta {t['T_brazo_delantero']-t['T_brazo_trasero']:+.2f} N)")
    print(f"""
      >>> x_cp_cg es DESCONOCIDO (clase D). Con 0 se recupera T/4. Con +-5 cm el
          desequilibrio delantero/trasero es de decenas de newtons: no es despreciable.
""")

    # --- PASO 3 ---------------------------------------------------------------
    print("-" * 100)
    print("PASO 3 — REPARTO COAXIAL   [correccion H]")
    print("-" * 100)
    print("""
      ARQUITECTURA CONOCIDA: 4 brazos, 8 motores, 8 rotores. La pregunta "comparte motor el
      par?" YA NO APLICA y se ha eliminado.

      LO QUE SIGUE DESCONOCIDO (clase D):
          T_superior / T_inferior        y        RPM_superior / RPM_inferior
      mas la estrategia de control. Se trata como PARAMETRO con barrido.
""")
    t10 = actitud(10.0, v("masa_mtow_kg"), rho)
    Tb = t10["T"] / 4
    print(f"    {'s (sup)':>9s} {'T sup (N)':>11s} {'T inf (N)':>11s}")
    for s in (0.5, 0.6, 0.7):
        r = reparto_coaxial(Tb, s)
        print(f"    {s:9.2f} {r['T_superior']:11.2f} {r['T_inferior']:11.2f}")

    # --- PASO 4 ---------------------------------------------------------------
    print("\n" + "-" * 100)
    print("PASO 4 — RPM: TRES VIAS SEPARADAS   [correcciones A y B]")
    print("-" * 100)
    T_rot = v("masa_mtow_kg") * G / 8.0
    m = via1_momentum(T_rot, rho, v("rotor_diam_m"))
    print(f"""
      VIA 1 — MOMENTUM THEORY: da POTENCIA, no RPM.
        v_inducida = {m['v_inducida_ms']:.4f} m/s
        P_ideal    = {m['P_ideal_W']:.1f} W   (x8 rotores = {8*m['P_ideal_W']/1000:.2f} kW)
        {m['aviso']}
""")
    e = via2_punto_experimental(T_rot, 1850.0, rho, v("rotor_diam_m"))
    print(f"""      VIA 2 — PUNTO EXPERIMENTAL (T, RPM medidos simultaneamente)
        Definicion rotorcraft:   Ct_rotor = T / (rho A (Omega R)^2)
        Con T = {T_rot:.2f} N y rpm = 1850 (NO medido, declarado sin fuente):
            Omega R     = {e['OmegaR_ms']:.3f} m/s
            Ct_rotor    = {e['Ct_rotor']:.6f}
            lambda_i    = sqrt(Ct/2) = {e['lambda_i']:.6f}
            v_i desde Ct = {e['v_i_desde_Ct']:.4f} m/s
            v_i directo  = {e['v_i_directo']:.4f} m/s
            DIFERENCIA   = {e['diferencia']:.2e}   <-- CERO
        {e['aviso']}
        => 1850 rpm NO esta validado, pero TAMPOCO refutado. SIMPLEMENTE NO SE SABE.
""")
    b = via3_bemt()
    print(f"""      VIA 3 — BEMT / curva de helice: la UNICA que PREDICE RPM desde empuje.
        Disponible: {b['disponible']}
        Falta: {b['falta']}
        {b['conclusion']}
""")

    print("=" * 100)
    print("DOS COEFICIENTES DISTINTOS QUE NO DEBEN CONFUNDIRSE   [correccion B]")
    print("=" * 100)
    print("""
      Ct_rotor = T / (rho A (Omega R)^2)      rotorcraft / BEMT. Normalizado con Omega R.
                                              Es el que usa TODA la cadena de arriba.

      Ct_OF, Cp_OF                            formulacion FROUDE de actuationDiskSource.
                                              Normalizados con la VELOCIDAD INCIDENTE U_o:
                                                  T = 2 rho A |U_o . n|^2 a (1-a)
                                                  a = 1 - Cp_OF/Ct_OF
                                              NO son el mismo coeficiente que Ct_rotor.

      En hover U_inf = 0, y cualquier coeficiente normalizado con U_inf^3 es una descripcion
      incomoda: en rotorcraft se normaliza con Omega R. Esa es la razon real por la que
      actuationDiskSource/Froude es incomodo aqui — NO que "Cp = 0 sea fisicamente imposible".
      Lo que ocurre es que ESE MODELO tiene una restriccion: exige Cp > 0 y Ct > 0, y aborta
      si no. Es una propiedad del modelo, no una ley universal sobre rotores.
""")

    print("=" * 100)
    print("CONCLUSION SOBRE RPM Y EL CFD PRINCIPAL   [correccion clave]")
    print("=" * 100)
    print("""
      NO se necesita RPM para imponer el empuje en el CFD principal (arquitectura C->B).
      El RPM pertenece a GATE 1B y a la validacion de alta fidelidad, y NO debe volver a
      convertirse en bloqueo del actuator disk principal.

      CADENA DEFENDIBLE:
          m, CG, V_aire, rho
              ->  sum F = 0 , sum M = 0
                  ->  theta, T_total, T_brazo_i
                      ->  s_i coaxial (parametro o medicion)
                          ->  T_sup_i, T_inf_i
                              ->  CFD:  T_i  ->  FUENTE DE MOMENTO PRESCRITA
                              ->  RPM:  (rama independiente)  T_i -> curva medida o BEMT -> RPM_i
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
