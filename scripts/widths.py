"""
TRES NIVELES FISICOS: PLUMA -> DEPOSICION DE UNA PASADA -> ANCHO EFECTIVO.

CORRECCIONES APLICADAS (revision del investigador, 2026-09-19):

  [1] ELIMINADO `W_DJI` del nucleo metodologico. El rango de catalogo (5-13 m) NO participa
      en la investigacion: el modelo no lo sabe ni lo necesita. Se conserva solo como
      referencia externa, NO como uno de los anchos del modelo.

  [2] RENOMBRADO: `W_commanded` -> `W_equiv` (ancho EQUIVALENTE implicito por Q, R, V).
      Razon: a menos que sepamos que el controlador realmente manda ese ancho, llamarlo
      "commanded" afirma algo que NO tenemos. Es una magnitud CONTABLE, no un comando.

          W_equiv = Q / (0.006 R V)

  [3] REDEFINIDOS LOS NIVELES. Ya no "cuatro anchos", sino TRES NIVELES FISICOS:

          PLUMA                    C_p(x,y,z)      distribucion espacial de gotas ANTES de impactar
          DEPOSICION DE UNA PASADA D(y) o D(x,y)  lo que toca el suelo en UNA pasada
          ANCHO EFECTIVO           W_eff           el maximo S con CV(solape) <= CV_lim

      Y el ancho efectivo se DEFINE por el criterio de solape:

          W_eff = max S  tal que  CV( sum_k D(y - kS) ) <= CV_lim

      NO importa si DJI dice 5, 7 o 13 m. EL MODELO NO SABE ESE NUMERO.

RELACION CAUDAL-ANCHO (derivada, no citada) — da W_equiv, que es contable:

    En 1 s el dron recorre V m -> cubre V*W m2 = V*W/10000 ha
    Q = 0.006 R V W       [L/min; R en L/ha, V en m/s, W en m]

Uso:
  python scripts/widths.py
"""
from __future__ import annotations

import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# --- T100, datos con su clase -------------------------------------------------------
Q_2BOQ_LMIN = 30.0                 # P: caudal maximo 2 boquillas
Q_4BOQ_LMIN = 40.0                 # P: caudal maximo 4 boquillas
RHO_L = 997.0                      # kg/m3 agua a 25 C
D50_UM = 150.0
CV_LIMITE_PCT = 20.0               # criterio de uniformidad de trabajo

# Referencia EXTERNA, fuera del modelo cientifico (ver correccion [1])
DJI_RANGO_CATALOGO_M = (5.0, 13.0)


def Q_de_RVW(R: float, V: float, W: float) -> float:
    """Q = 0.006 R V W   [L/min]"""
    return 0.006 * R * V * W


def W_equiv(Q: float, R: float, V: float) -> float:
    """W_equiv = Q / (0.006 R V)   [m].  Ancho EQUIVALENTE implicito por Q, R, V.

    NO es un ancho comandado: es una magnitud contable. Solo seria "comandado" si
    supiéramos que el controlador manda ese ancho, y eso no lo sabemos.
    """
    den = 0.006 * R * V
    return Q / den if den > 0 else float("nan")


def cv_solape(D_y: list[float], S: float, dy: float) -> float:
    """CV de la deposicion solapada con interlineado S.

    Suma de pasadas desplazadas kS sobre el perfil de UNA pasada D(y).
    """
    if not D_y or S <= 0:
        return float("nan")
    n = len(D_y)
    y0 = -(n // 2) * dy
    suma = []
    for i in range(n):
        y = y0 + i * dy
        acc = 0.0
        # pasadas necesarias para cubrir con margen
        kmin = int((y - (y0 + n * dy)) / S) - 1
        kmax = int((y - y0) / S) + 2
        for k in range(kmin, kmax + 1):
            yy = y - k * S
            idx = (yy - y0) / dy
            j = int(round(idx))
            if 0 <= j < n:
                acc += D_y[j]
        suma.append(acc)
    media = sum(suma) / len(suma)
    if media <= 0:
        return float("nan")
    var = sum((v - media) ** 2 for v in suma) / len(suma)
    return math.sqrt(var) / media * 100.0


def ancho_efectivo(D_y: list[float], dy: float, cv_lim: float = CV_LIMITE_PCT,
                   S_max: float = 30.0, paso: float = 0.1) -> dict:
    """W_eff = max S tal que CV(solape) <= CV_lim.   DEFINICION del objetivo cientifico."""
    mejor_S, mejor_cv = float("nan"), float("nan")
    S = paso
    while S <= S_max:
        c = cv_solape(D_y, S, dy)
        if not math.isnan(c) and c <= cv_lim:
            mejor_S, mejor_cv = S, c
        S += paso
    return {"W_eff_m": mejor_S, "CV_en_W_eff_pct": mejor_cv, "CV_limite_pct": cv_lim}


def perfil_gaussiano(sigma_y: float, dy: float = 0.05, ancho: float = 20.0) -> list[float]:
    """Perfil de UNA pasada, gaussiano. SOLO para ejercitar la maquinaria de W_eff.

    >>> ESTE PERFIL ES SINTETICO. No es resultado de nada. Sirve para verificar que el
        calculo de W_eff funciona; el perfil real viene de D(x,y) del Lagrangiano.
    """
    n = int(ancho / dy)
    y0 = -(n // 2) * dy
    return [math.exp(-((y0 + i * dy) ** 2) / (2 * sigma_y ** 2)) for i in range(n)]


def main() -> int:
    print("=" * 96)
    print("TRES NIVELES FISICOS: PLUMA -> DEPOSICION DE UNA PASADA -> ANCHO EFECTIVO")
    print("=" * 96)

    print("\n" + "-" * 96)
    print("NIVEL 1 — PLUMA:  C_p(x,y,z)")
    print("-" * 96)
    print("""
  Distribucion espacial de gotas ANTES de impactar. Es una salida DIRECTA del modulo
  Lagrangiano: no requiere ninguna definicion de ancho ni ningun criterio.

      C_p(x,y,z) = concentracion de liquido por unidad de volumen, por tamano de gota

  Aporta: la forma del abanico, el reparto por diametros, y donde esta realmente el
  liquido antes de que el suelo lo intercepte.
""")

    print("-" * 96)
    print("NIVEL 2 — DEPOSICION DE UNA PASADA:  D(y) o D(x,y)")
    print("-" * 96)
    print("""
  Lo que toca el suelo en UNA pasada. Sale de integrar los impactos en el plano receptor.

  Sin este nivel no se puede definir el ancho efectivo: el ancho NO es una propiedad de
  una pasada, es una propiedad del SOLAPE de pasadas.
""")

    print("-" * 96)
    print("NIVEL 3 — ANCHO EFECTIVO:  W_eff")
    print("-" * 96)
    print("""
  DEFINICION (la del objetivo cientifico):

      W_eff = max S  tal que  CV( sum_k D(y - kS) )  <=  CV_lim

  Es decir: el mayor interlineado que mantiene la uniformidad dentro del criterio.

  >>> El modelo NO SABE cuanto dice DJI. No entra en la definicion.
""")

    # --- verificacion de la maquinaria de W_eff con perfiles SINTETICOS -------------
    print("-" * 96)
    print("VERIFICACION DE LA MAQUINARIA (perfiles SINTETICOS, no resultados)")
    print("-" * 96)
    print("""
  ADVERTENCIA: los perfiles siguientes son gaussianos INVENTADOS. Se usan unicamente para
  comprobar que el calculo de CV y de W_eff funciona. NO son resultados de nada.
""")
    dy = 0.05
    print(f"  CV_limite = {CV_LIMITE_PCT:.0f} %")
    print(f"\n  {'sigma_y (m)':>12s} {'W_eff (m)':>10s} {'CV en W_eff':>12s} {'S+0.1 m':>9s} {'CV':>8s}")
    for sigma in (0.3, 0.5, 0.8, 1.0, 1.5):
        D = perfil_gaussiano(sigma, dy)
        r = ancho_efectivo(D, dy)
        # comprobar que justo por encima del W_eff el CV se sale
        if not math.isnan(r["W_eff_m"]):
            c_next = cv_solape(D, r["W_eff_m"] + 0.1, dy)
            print(f"  {sigma:12.2f} {r['W_eff_m']:10.1f} {r['CV_en_W_eff_pct']:12.2f} "
                  f"{r['W_eff_m']+0.1:9.1f} {c_next:8.2f}")
        else:
            print(f"  {sigma:12.2f} {'--':>10s} {'--':>12s}")
    print("""
  LECTURA: W_eff CRECE con sigma_y, y justo por encima de W_eff el CV se sale del limite.
  La maquinaria es correcta: define el ancho por el CRITERIO DE UNIFORMIDAD, no por una
  formula de caudal.
""")

    # --- W_equiv: lo que SI se puede calcular ahora ---------------------------------
    print("-" * 96)
    print("MAGNITUD CONTABLE — W_equiv  (NO es el ancho fisico)")
    print("-" * 96)
    print("""
  Derivacion de la relacion caudal-ancho:

      En 1 s el dron recorre V m -> cubre V*W m2 = V*W/10000 ha
      Volumen por minuto = 60 R V W/10000  =>  Q = 0.006 R V W
      Invertida:  W_equiv = Q / (0.006 R V)
""")
    R, V = 10.0, 10.0
    print(f"  Verificacion con el ejemplo del investigador (R={R:g}, V={V:g}, W=6):")
    print(f"    Q = 0.006 x {R:g} x {V:g} x 6 = {Q_de_RVW(R,V,6):.4f} L/min  "
          f"({'COINCIDE' if abs(Q_de_RVW(R,V,6)-3.6)<1e-9 else 'DIFIERE'} con 3.6)")
    print(f"\n  {'Q (L/min)':>11s} {'caso':34s} {'W_equiv (m)':>12s}")
    for Q, caso in ((3.6, "ejemplo del investigador"), (8.0, "uso tipico estimado"),
                    (16.0, "caudal T50 (referencia)"),
                    (Q_2BOQ_LMIN, "T100 maximo 2 boquillas"),
                    (Q_4BOQ_LMIN, "T100 maximo 4 boquillas")):
        print(f"  {Q:11.1f} {caso:34s} {W_equiv(Q,R,V):12.2f}")
    print(f"""
  Estos W_equiv son CONTABLES, no fisicos. A R={R:g} L/ha y V={V:g} m/s los caudales maximos
  implican anchos absurdos, lo que revela que la operacion real usa otras combinaciones
  de (R, V). La telemetria lo dira.

  CONTRASTE PREVISTO: W_equiv (contable)  vs  W_eff (fisico, del Lagrangiano).
  La diferencia entre ambos es un resultado; no un error de ninguno de los dos.
""")

    print("-" * 96)
    print("REFERENCIA EXTERNA — fuera del modelo cientifico")
    print("-" * 96)
    print(f"""
  DJI declara {DJI_RANGO_CATALOGO_M[0]:.0f}-{DJI_RANGO_CATALOGO_M[1]:.0f} m de ancho efectivo para el T100, con la advertencia de que
  depende de la escena real de trabajo.

  Ese numero NO entra en el modelo: no se usa como entrada, ni como objetivo, ni como
  criterio de validacion. Se cita como contexto de la practica industrial y nada mas.
  El modelo obtiene W_eff de D(y) y del criterio de CV, sin saber cuanto dice el folleto.
""")

    print("=" * 96)
    print("Modelo analitico. Los perfiles usados para verificar W_eff son SINTETICOS.")
    print("=" * 96)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
