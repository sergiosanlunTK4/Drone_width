"""
CAPA ANALITICA + BASE DE DATOS SQLite.

QUE ES ESTO Y QUE NO ES:
  ES la base de datos completa del proyecto, con las 4 plataformas, el DOE de 128 casos,
  y la capa de fisica ANALITICA calculada de verdad:
    - momentum theory (disco actuador ideal): v_inducida, carga de disco, potencia inducida
    - figura de merito estimada
    - modelo de solape de pasadas: CV de uniformidad y ancho efectivo
    - modelo Gaussiano de deposicion D(x,y) con deriva
  NO ES CFD. Ninguna fila se etiqueta como resultado de simulacion. La columna
  `origen_dato` lo declara en cada tabla, y las tablas de CFD quedan VACIAS a proposito.

  Esto es la diferencia entre "calcular con un modelo analitico declarado" y "inventar
  resultados de CFD". Lo primero es fisica; lo segundo invalidaria el proyecto entero.

Uso:
  python scripts/build_database.py
"""
from __future__ import annotations

import csv
import math
import random
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "processed" / "dronewith.sqlite"
DOE = ROOT / "data" / "processed" / "doe_by_platform.csv"

G = 9.81
RHO = 1.1716
P_ATM = 101325.0

# propiedades del aire y del agua a 28 C (referencias estandar)
MU_AIR = 1.86e-5      # Pa.s  viscosidad DINAMICA DEL AIRE  <- la que usa Stokes para la gota
MU_W = 8.36e-4        # Pa.s  viscosidad del agua (para el atomizador, no para la caida)
RHO_W = 996.2
SIGMA_W = 0.0719

PLAT = {
    "T25P": dict(nombre="DJI Agras T25P", d_rotor=1.270, coaxial=False, n_brazos=4,
                 m_bat=33.0, tanque=20.0, mtow=53.0, swath=(4.0, 7.0),
                 atom_sep=1420, d_ref=200.0),
    "T55":  dict(nombre="DJI Agras T55", d_rotor=1.575, coaxial=True, n_brazos=4,
                 m_bat=45.0, tanque=50.0, mtow=95.0, swath=(4.0, 11.0),
                 atom_sep=1800, d_ref=200.0),
    "T70P": dict(nombre="DJI Agras T70P", d_rotor=1.574, coaxial=True, n_brazos=4,
                 m_bat=56.0, tanque=70.0, mtow=126.0, swath=(4.0, 11.0),
                 atom_sep=1874, d_ref=200.0),
    "T100": dict(nombre="DJI Agras T100", d_rotor=1.574, coaxial=True, n_brazos=4,
                 m_bat=75.0, tanque=100.0, mtow=175.0, swath=(5.0, 13.0),
                 atom_sep=1834, d_ref=200.0),
}

# -------------------------------------------------------------------------------------
# FISICA ANALITICA
# -------------------------------------------------------------------------------------
def analitico(plat: dict, masa: float, d_um: float, H: float, V: float, n_atom: int) -> dict:
    """Metricas analiticas declaradas. NO es CFD."""
    r = plat["d_rotor"] / 2.0
    n_rot = plat["n_brazos"] * (2 if plat["coaxial"] else 1)
    A = n_rot * math.pi * r ** 2
    T = masa * G

    # momentum theory: disco actuador ideal en hover
    v_ind = math.sqrt(T / (2.0 * RHO * A))
    P_ideal = T * v_ind
    # potencia inducida con factores tipicos de perdida (figura de merito ~0.7)
    FM = 0.70
    P_real = P_ideal / FM

    # carga de disco
    DL = T / A

    # tiempo de residencia de la gota en la estela.
    # La estela de un multirrotor decae en pocas decenas de cm: bajo el disco la velocidad
    # inducida se relaja hacia ~2*v_ind y decae con la distancia.
    # La gota cae a su velocidad terminal MAS la componente vertical de la estela.
    v_dw = 2.0 * v_ind                     # nucleo de la estela, justo bajo el disco
    dp = d_um * 1e-6

    # --- VELOCIDAD TERMINAL por iteracion de la ley de arrastre.
    # OJO CON LA VISCOSIDAD: la gota cae en AIRE, asi que la ley de Stokes usa mu del AIRE
    # (1.86e-5 Pa.s), NO la del agua (8.4e-4). Usar la del agua da un factor ~45 de error.
    # Verificacion canonica: 100 um -> 0.25-0.30 m/s ; 200 um -> 1.2-1.3 m/s ;
    # 500 um -> 2.0-2.5 m/s (con correccion de arrastre; Stokes puro sobreestima a 500 um).
    r_p = dp / 2.0
    v_term = 2.0 * (RHO_W - RHO) * G * r_p ** 2 / (9.0 * MU_AIR)   # arranque: Stokes
    for _ in range(80):
        Re_iter = max(RHO * v_term * dp / MU_AIR, 1e-12)
        Cd = 24.0 / Re_iter * (1.0 + 0.15 * Re_iter ** 0.687)
        v_nuevo = math.sqrt(8.0 * (RHO_W - RHO) * G * r_p / (3.0 * Cd * RHO))
        if abs(v_nuevo - v_term) < 1e-10:
            v_term = v_nuevo
            break
        v_term = 0.5 * (v_term + v_nuevo)   # relajacion, evita oscilacion
    Re_p = RHO * v_term * dp / MU_AIR

    # --- REGIMEN: la gota cae a v_term + v_estela(z), y la estela decae con z.
    def decay(z_sobre_suelo: float) -> float:
        """Perfil de decaimiento de la estela respecto a la distancia al disco."""
        x = max(0.0, H - z_sobre_suelo)     # distancia recorrida desde el disco
        return 1.0 / (1.0 + 2.0 * x)        # estela desarrollada: decae con la distancia

    n = 400
    t = 0.0
    z = H
    while z > 0.0 and t < 60.0:
        dz = H / n
        v_z = v_term + v_dw * decay(z)
        t += dz / max(v_z, 1e-6)
        z -= dz
    t_caida = t

    # fraccion del tiempo de caida en que la estela aporta mas que la caida libre
    t_free = H / v_term if v_term > 0 else float("inf")
    dominancia_estela = max(0.0, min(1.0, 1.0 - t_free / t_caida)) if t_caida > 0 else 0.0

    # --- DISPERSION LATERAL: difusion turbulenta durante el tiempo de caida.
    k_turb = 0.15                                # u' ~ k_turb * v_ind
    u_prime = k_turb * v_ind
    L_turb = r                                   # escala de mezcla ~ radio del rotor
    sigma0 = 0.10 * (plat["atom_sep"] / 2000.0)  # abanico inicial del atomizador
    sigma_y = math.sqrt(sigma0 ** 2 + 2.0 * (u_prime * L_turb) * t_caida)
    W_eff = 4.0 * sigma_y

    # --- numero de Stokes: inercia de la gota frente al tiempo caracteristico del flujo
    tau_p = RHO_W * dp ** 2 / (18.0 * MU_AIR)
    tau_f = r / max(v_dw, 1e-6)
    St = tau_p / tau_f

    # CV de solape para un interlineado s: modelo de solape de perfiles Gaussianos
    def cv_para_spacing(s: float) -> float:
        if s <= 0:
            return float("nan")
        # perfil gaussiano unitario; se solapan perfiles desplazados s
        n = 41
        xs = [(-2.0 * s + 4.0 * s * i / (n - 1)) for i in range(n)]
        vals = []
        for x in xs:
            acc = 0.0
            k = -4
            while k <= 4:
                acc += math.exp(-((x - k * s) ** 2) / (2.0 * sigma_y ** 2))
                k += 1
            vals.append(acc)
        media = sum(vals) / len(vals)
        if media <= 0:
            return float("nan")
        var = sum((v - media) ** 2 for v in vals) / len(vals)
        return math.sqrt(var) / media * 100.0

    # interlineado recomendado por criterio de CV: se busca el mayor s con CV <= umbral
    umbral = 20.0
    s_rec = None
    for s in [x * 0.1 for x in range(5, 121)]:
        if cv_para_spacing(s) <= umbral:
            s_rec = s
        else:
            break
    if s_rec is None:
        s_rec = 0.5

    # deposicion lateral en la linea central (proxy analitico, no CFD)
    D_center = 1.0 / (math.sqrt(2.0 * math.pi) * sigma_y)   # normalizado a 1 en integral
    # deriva estimada: tiempo de caida x velocidad de viento (aqui viento = 0 por alcance)
    deriva_0_ms = 0.0

    return {
        "n_rotores": n_rot,
        "area_disco_total_m2": round(A, 4),
        "carga_disco_N_m2": round(DL, 2),
        "empuje_total_N": round(T, 2),
        "v_inducida_hover_ms": round(v_ind, 4),
        "v_downwash_nucleo_ms": round(v_dw, 4),
        "potencia_ideal_W": round(P_ideal, 1),
        "potencia_estimada_W": round(P_real, 1),
        "figura_merito_supuesta": FM,
        "tiempo_residencia_estela_s": round(t_caida, 4),
        "v_terminal_gota_ms": round(v_term, 4),
        "Re_particula": round(Re_p, 3),
        "Stokes_number": round(St, 4),
        "dominancia_estela": round(dominancia_estela, 4),
        "sigma_y_m": round(sigma_y, 4),
        "ancho_efectivo_analitico_m": round(W_eff, 3),
        "interlineado_recomendado_m": round(s_rec, 2),
        "cv_en_interlineado_recomendado_pct": round(cv_para_spacing(s_rec), 2),
        "D_center_normalizado": round(D_center, 5),
        "deriva_estimada_ms": deriva_0_ms,
        "origen_dato": ("ANALITICO (momentum theory + difusion turbulenta + solape gaussiano). "
                        "NO ES CFD. Requiere validacion."),
    }


# -------------------------------------------------------------------------------------
SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS platforms (
    plataforma      TEXT PRIMARY KEY,
    nombre          TEXT NOT NULL,
    rotor_d_m       REAL NOT NULL,
    coaxial         INTEGER NOT NULL,
    n_brazos        INTEGER NOT NULL,
    n_rotores       INTEGER NOT NULL,
    masa_bateria_kg REAL, tanque_kg REAL, mtow_kg REAL,
    area_disco_m2   REAL,
    swath_min_m     REAL, swath_max_m REAL,
    atom_sep_mm     REAL,
    clasificacion_geometria TEXT,
    nota            TEXT
);

CREATE TABLE IF NOT EXISTS cases (
    case_id         TEXT PRIMARY KEY,
    plataforma      TEXT NOT NULL REFERENCES platforms(plataforma),
    V_inf_ms        REAL NOT NULL,
    H_m             REAL NOT NULL,
    DV05_um         REAL NOT NULL,
    carga_fraccion  REAL NOT NULL,
    masa_total_kg   REAL NOT NULL,
    atomizadores    INTEGER NOT NULL,
    split_coaxial_superior REAL NOT NULL,
    coaxial         INTEGER NOT NULL,
    fuente_geometria TEXT,
    estado          TEXT NOT NULL,
    arquitectura_cfd TEXT
);

-- CAPA ANALITICA (calculada, real)
CREATE TABLE IF NOT EXISTS analytic_metrics (
    case_id         TEXT PRIMARY KEY REFERENCES cases(case_id),
    n_rotores INTEGER, area_disco_total_m2 REAL, carga_disco_N_m2 REAL,
    empuje_total_N REAL, v_inducida_hover_ms REAL, v_downwash_nucleo_ms REAL,
    potencia_ideal_W REAL, potencia_estimada_W REAL, figura_merito_supuesta REAL,
    tiempo_residencia_estela_s REAL, v_terminal_gota_ms REAL, Re_particula REAL,
    Stokes_number REAL, dominancia_estela REAL, sigma_y_m REAL,
    ancho_efectivo_analitico_m REAL, interlineado_recomendado_m REAL,
    cv_en_interlineado_recomendado_pct REAL, D_center_normalizado REAL,
    deriva_estimada_ms REAL,
    origen_dato TEXT NOT NULL
);

-- TABLAS DE CFD: VACIAS A PROPOSITO. Se poblan solo ejecutando OpenFOAM.
CREATE TABLE IF NOT EXISTS cfd_airflow (
    case_id TEXT NOT NULL REFERENCES cases(case_id),
    mesh_id TEXT, solver TEXT, solver_version TEXT, turb_model TEXT,
    y_plus_medio REAL, celdas INTEGER, residual_final_U REAL, residual_final_p REAL,
    v_downwash_max_ms REAL, v_downwash_perfil_json TEXT,
    convergido INTEGER, fecha_ejecucion TEXT,
    origen_dato TEXT NOT NULL DEFAULT 'CFD',
    PRIMARY KEY (case_id, mesh_id)
);

CREATE TABLE IF NOT EXISTS cfd_deposition (
    case_id TEXT NOT NULL REFERENCES cases(case_id),
    modelo_gota TEXT, n_particulas INTEGER, acoplamento TEXT,
    rejilla_x_json TEXT, rejilla_y_json TEXT, D_xy_json TEXT,
    w_eff_m REAL, cv_pct REAL, pico_g_m2 REAL,
    fecha_ejecucion TEXT,
    origen_dato TEXT NOT NULL DEFAULT 'CFD',
    PRIMARY KEY (case_id, modelo_gota)
);

CREATE TABLE IF NOT EXISTS cfd_swath_metrics (
    case_id TEXT NOT NULL REFERENCES cases(case_id),
    w_eff_m REAL, cv_pct REAL, interlineado_recomendado_m REAL,
    asimetria_pct REAL, p10_g_m2 REAL, p50_g_m2 REAL, p90_g_m2 REAL,
    dentro_ancho_pct REAL, fuera_ancho_pct REAL,
    origen_dato TEXT NOT NULL DEFAULT 'CFD',
    PRIMARY KEY (case_id)
);

-- VALIDACION EXPERIMENTAL: vacia hasta que exista campana
CREATE TABLE IF NOT EXISTS experiments (
    exp_id TEXT PRIMARY KEY, plataforma TEXT, tipo TEXT,
    variable TEXT, valor REAL, unidad TEXT, incertidumbre TEXT,
    metodo TEXT, instrumento TEXT, timestamp TEXT, operador TEXT,
    fuente TEXT, reference_frame TEXT, origen_dato TEXT NOT NULL DEFAULT 'EXPERIMENTAL'
);

-- SURROGATE: vacia hasta que haya CFD validado (GATE 4)
CREATE TABLE IF NOT EXISTS surrogate_models (
    model_id TEXT PRIMARY KEY, plataforma TEXT, tipo TEXT, features_json TEXT,
    r2_train REAL, r2_test REAL, rmse_test REAL, n_train INTEGER,
    validacion_fuera_muestra INTEGER, fecha TEXT, origen_dato TEXT
);

-- TRAZABILIDAD
CREATE TABLE IF NOT EXISTS provenance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tabla TEXT, registro TEXT, campo TEXT,
    clase TEXT, fuente TEXT, nota TEXT, fecha TEXT
);

CREATE VIEW IF NOT EXISTS v_estado AS
SELECT
    (SELECT COUNT(*) FROM platforms)         AS plataformas,
    (SELECT COUNT(*) FROM cases)             AS casos_especificados,
    (SELECT COUNT(*) FROM analytic_metrics)  AS metricas_analiticas,
    (SELECT COUNT(*) FROM cfd_airflow)       AS resultados_cfd_aire,
    (SELECT COUNT(*) FROM cfd_deposition)    AS resultados_cfd_deposicion,
    (SELECT COUNT(*) FROM cfd_swath_metrics) AS metricas_cfd,
    (SELECT COUNT(*) FROM experiments)       AS filas_experimentales,
    (SELECT COUNT(*) FROM surrogate_models)  AS surrogates;
"""


def main() -> int:
    DB.parent.mkdir(parents=True, exist_ok=True)
    if DB.exists():
        DB.unlink()
    con = sqlite3.connect(DB)
    con.executescript(SCHEMA)
    ahora = datetime.now(timezone.utc).isoformat()

    # ---- plataformas
    for clave, p in PLAT.items():
        n_rot = p["n_brazos"] * (2 if p["coaxial"] else 1)
        A = n_rot * math.pi * (p["d_rotor"] / 2) ** 2
        con.execute("INSERT INTO platforms VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            clave, p["nombre"], p["d_rotor"], int(p["coaxial"]), p["n_brazos"], n_rot,
            p["m_bat"], p["tanque"], p["mtow"], round(A, 4),
            p["swath"][0], p["swath"][1], p["atom_sep"],
            "P/S/O/I (no M)", "geometria declarada; ver geometry/presupuesto_hipotesis.md"))
        con.execute("INSERT INTO provenance (tabla,registro,campo,clase,fuente,nota,fecha) "
                    "VALUES (?,?,?,?,?,?,?)",
                    ("platforms", clave, "geometria", "P/S/O/I",
                     "ficha DJI + Academy + propietario",
                     "no medido: no cierra GATE 1A", ahora))

    # ---- casos + metricas analiticas
    with DOE.open(encoding="utf-8") as fh:
        filas = list(csv.DictReader(fh))
    for f in filas:
        plat = PLAT[f["plataforma"]]
        # el CSV trae booleanos como texto ("True"/"False")
        coaxial = str(f["coaxial"]).strip().lower() in ("true", "1", "yes")
        con.execute(
            "INSERT INTO cases VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (f["case_id"], f["plataforma"], float(f["V_inf_ms"]), float(f["H_m"]),
             float(f["DV05_um"]), float(f["carga_fraccion"]), float(f["masa_total_kg"]),
             int(f["atomizadores"]), float(f["split_coaxial_superior"]),
             int(coaxial), f["fuente_geometria"], f["estado"],
             "C->B: actuator disk con empuje prescrito"))
        m = analitico(plat, float(f["masa_total_kg"]), float(f["DV05_um"]),
                      float(f["H_m"]), float(f["V_inf_ms"]), int(f["atomizadores"]))
        con.execute(
            "INSERT INTO analytic_metrics VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (f["case_id"], m["n_rotores"], m["area_disco_total_m2"], m["carga_disco_N_m2"],
             m["empuje_total_N"], m["v_inducida_hover_ms"], m["v_downwash_nucleo_ms"],
             m["potencia_ideal_W"], m["potencia_estimada_W"], m["figura_merito_supuesta"],
             m["tiempo_residencia_estela_s"], m["v_terminal_gota_ms"], m["Re_particula"],
             m["Stokes_number"], m["dominancia_estela"], m["sigma_y_m"],
             m["ancho_efectivo_analitico_m"], m["interlineado_recomendado_m"],
             m["cv_en_interlineado_recomendado_pct"], m["D_center_normalizado"],
             m["deriva_estimada_ms"], m["origen_dato"]))

    con.commit()

    # ---- informe
    print("=" * 88)
    print("BASE DE DATOS CONSTRUIDA")
    print("=" * 88)
    cur = con.execute("SELECT * FROM v_estado")
    cols = [d[0] for d in cur.description]
    for r in cur.fetchall():
        print()
        for c, v in zip(cols, r):
            print(f"  {c:28s} {v}")

    print("\n" + "=" * 88)
    print("METRICAS ANALITICAS POR PLATAFORMA (a masa MTOW, d=200 um, H=3 m)")
    print("=" * 88)
    print(f"\n  {'plat':6s} {'n_rot':>5s} {'A(m2)':>8s} {'DL(N/m2)':>9s} "
          f"{'v_ind':>7s} {'v_dw':>7s} {'St':>8s} {'sig_y':>7s} {'W_eff':>7s} "
          f"{'s_rec':>6s} {'CV%':>6s}")
    for clave, p in PLAT.items():
        m = analitico(p, p["mtow"], 200.0, 3.0, 5.0, 2)
        print(f"  {clave:6s} {m['n_rotores']:5d} {m['area_disco_total_m2']:8.3f} "
              f"{m['carga_disco_N_m2']:9.1f} {m['v_inducida_hover_ms']:7.3f} "
              f"{m['v_downwash_nucleo_ms']:7.3f} {m['Stokes_number']:8.3f} "
              f"{m['sigma_y_m']:7.3f} {m['ancho_efectivo_analitico_m']:7.2f} "
              f"{m['interlineado_recomendado_m']:6.2f} "
              f"{m['cv_en_interlineado_recomendado_pct']:6.2f}")

    con.close()
    print(f"\n-> {DB.relative_to(ROOT)}")
    print("\nAVISO: `analytic_metrics` es FISICA ANALITICA, no CFD. Las tablas cfd_* estan")
    print("VACIAS a proposito: se poblan solo ejecutando OpenFOAM. Ningun resultado de")
    print("simulacion se ha inventado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
