"""
BASE DE DATOS DE ESCENARIOS v2 — dos niveles (INSTRUCCIONES_CFD.md §5.3).

    Nivel A  air_cases        campo de aire RANS (caro)     clave air_id
    Nivel B  lagrangian_runs  1 boquilla x 1 clase de gota sobre un campo A congelado (barato)
             spray_cases      escenario programado = suma ponderada de lagrangian_runs
                              (espectro alrededor del VMD, configuracion 2/4)  -> postproceso
    Resultados (solo desde OpenFOAM real, via postprocess_case.py):
             cfd_airflow (air_id) · deposition_maps · swath_metrics · run_log

NO BORRA NADA: crea las tablas v2 en `data/processed/dronewith.sqlite` junto a las v1
(`cases`, `analytic_metrics`, ...), que quedan marcadas `obsoleto_geometria_v1`. La tabla
`cfd_airflow` v1 (clave case_id) se conserva renombrada a `cfd_airflow_v1`.
Es idempotente: `INSERT OR IGNORE`; el estado de los casos ya existentes no se toca.

MATRIZ (etapa 1, malla gruesa de escenarios; §5.5, APROBADA por el propietario 2026-11-23):
    H = {1.5, 2.5, 3.5, 5.0} m
    V = {0, 2, 5, 8, 12, 16, 20} m/s   (T25P: {0, 2, 4, 6, 8, 10})
    f = {1, 0}
  + T100: reparto coaxial 0.6 / 0.7 en un subconjunto (H 2.5, V 0/8, f 1/0); base 0.5
  + CFD-0: T25P hover H 2.5 f 1 en mallas gruesa/media/fina (independencia)
  + efecto de los cuerpos opcionales (T25P, T70P): con/sin, H 2.5, V 0/8, f 1
  + puntos de validacion de la interpolacion (etapa 2), NO usados para interpolar

ESTADOS: pendiente | bloqueado (con motivo) | en_curso | hecho | fallido
  - V > 0: actitud theta(V, f) del MODELO E aprobado el 2026-11-23 (`agras_model/attitude.py`,
    theta_clase = 'E'). Si llega telemetria de cabeceo (O), la sustituye. Las filas creadas
    antes como `bloqueado` por theta se actualizan en `aplicar_theta_E` (sin tocar otras).

Uso:
    python scripts/build_scenario_db.py            # crea/actualiza y resume
    python scripts/build_scenario_db.py --resumen  # solo el resumen
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "agras_model"))
import cfd_geometry as cg  # noqa: E402
import attitude as att  # noqa: E402

DB = ROOT / "data" / "processed" / "dronewith.sqlite"
GEOM = "2.0"

H_ETAPA1 = [1.5, 2.5, 3.5, 5.0]
V_ETAPA1 = {"T25P": [0, 2, 4, 6, 8, 10], "_": [0, 2, 5, 8, 12, 16, 20]}
F_ETAPA1 = [1.0, 0.0]
# validacion de la interpolacion: puntos intermedios (H, V, f) que NO entran en la rejilla
VALIDACION = {"T25P": [(2.0, 0, 0.5), (3.0, 5, 0.5), (4.0, 7, 0.5)],
              "_":    [(2.0, 0, 0.5), (3.0, 10, 0.5), (4.0, 14, 0.5)]}
D_CLASES = [10, 50, 100, 150, 200, 250, 300, 350, 400, 450, 500]   # um (simulacion, nivel B)
D_VMD = [50, 100, 150, 200, 250, 300, 350, 400, 450, 500]          # um (escenario programado)

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS platforms_v2 (
    plataforma TEXT PRIMARY KEY, nombre TEXT, geometria_version TEXT,
    n_rotores INTEGER, coaxial INTEGER, masa_vacio_kg REAL, tanque_kg REAL, mtow_kg REAL,
    z_suelo_modelo_m REAL, V_max_ms REAL, V_max_clase TEXT,
    Q_max_2_Lmin REAL, Q_max_4_Lmin REAL, Q_max_clase TEXT,
    fuente_json TEXT, nota TEXT
);

-- NIVEL A: campo de aire
CREATE TABLE IF NOT EXISTS air_cases (
    air_id TEXT PRIMARY KEY,
    plataforma TEXT NOT NULL REFERENCES platforms_v2(plataforma),
    V_ms REAL NOT NULL, H_m REAL NOT NULL, f REAL NOT NULL, masa_kg REAL NOT NULL,
    theta_actitud_deg REAL, theta_clase TEXT,
    split_coax REAL,                    -- solo T100 (fraccion del brazo en el rotor superior)
    cuerpos_opcionales INTEGER NOT NULL DEFAULT 0,   -- T25P/T70P: cuerpos de atomizador delanteros
    malla TEXT NOT NULL DEFAULT 'gruesa',
    hover_bc TEXT,
    etapa INTEGER NOT NULL, rol TEXT NOT NULL, prioridad INTEGER NOT NULL,
    geometria_version TEXT NOT NULL,
    estado TEXT NOT NULL CHECK (estado IN ('pendiente','bloqueado','en_curso','hecho','fallido')),
    bloqueo_motivo TEXT, case_dir TEXT, intentos INTEGER NOT NULL DEFAULT 0,
    creado TEXT, actualizado TEXT,
    origen_dato TEXT NOT NULL DEFAULT 'ESPECIFICACION'
);

-- NIVEL B (unidad de simulacion): una boquilla x una clase de tamano, superposicion exacta
CREATE TABLE IF NOT EXISTS lagrangian_runs (
    run_id TEXT PRIMARY KEY,
    air_id TEXT NOT NULL REFERENCES air_cases(air_id),
    nozzle_id TEXT NOT NULL, configuracion_boquilla TEXT, d_clase_um REAL NOT NULL,
    clima_id TEXT NOT NULL, evaporacion INTEGER NOT NULL,
    rpm_atomizador REAL, k_exit REAL, n_parcelas INTEGER,
    requiere_boquilla_niebla INTEGER NOT NULL DEFAULT 0,
    archivo_impactos TEXT,
    estado TEXT NOT NULL DEFAULT 'pendiente_aire',
    origen_dato TEXT NOT NULL DEFAULT 'ESPECIFICACION'
);

-- NIVEL B (escenario programado): combinacion de lagrangian_runs en postproceso
CREATE TABLE IF NOT EXISTS spray_cases (
    spray_id TEXT PRIMARY KEY,
    air_id TEXT NOT NULL REFERENCES air_cases(air_id),
    d_vmd_um REAL NOT NULL, espectro_modelo TEXT, espectro_param_json TEXT, espectro_clase TEXT,
    clima_id TEXT NOT NULL,
    config_atom INTEGER NOT NULL CHECK (config_atom IN (2, 4)),
    rpm_atomizador REAL,
    Q_Lmin REAL, dosis_Lha REAL, interlineado_m REAL, realizable INTEGER,
    estado TEXT NOT NULL DEFAULT 'pendiente_aire',
    origen_dato TEXT NOT NULL DEFAULT 'ESPECIFICACION'
);

-- RESULTADOS: solo desde salidas reales de OpenFOAM (postprocess_case.py)
CREATE TABLE IF NOT EXISTS cfd_airflow (
    air_id TEXT NOT NULL REFERENCES air_cases(air_id),
    mesh_id TEXT NOT NULL, solver TEXT, solver_version TEXT, turb_model TEXT,
    celdas INTEGER, y_plus_medio REAL,
    residual_final_U REAL, residual_final_p REAL, iteraciones INTEGER,
    F_suelo_z_N REAL, F_fuselaje_z_N REAL, F_contorno_z_N REAL, suma_T_N REAL,
    cierre_momento_pct REAL, asimetria_LR_pct REAL,
    v_downwash_max_ms REAL, v_downwash_perfil_json TEXT,
    convergido INTEGER, fecha_ejecucion TEXT,
    origen_dato TEXT NOT NULL DEFAULT 'CFD',
    PRIMARY KEY (air_id, mesh_id)
);

CREATE TABLE IF NOT EXISTS deposition_maps (
    spray_id TEXT NOT NULL REFERENCES spray_cases(spray_id),
    archivo_mapa TEXT NOT NULL,          -- results/maps/<spray_id>.npz (no JSON en SQLite)
    nx INTEGER, ny INTEGER, dx_m REAL, dy_m REAL, n_particulas INTEGER,
    masa_depositada_frac REAL, fecha TEXT,
    origen_dato TEXT NOT NULL DEFAULT 'CFD',
    PRIMARY KEY (spray_id)
);

CREATE TABLE IF NOT EXISTS swath_metrics (
    spray_id TEXT NOT NULL REFERENCES spray_cases(spray_id),
    W_eff_m REAL, CV_pct REAL, interlineado_recomendado_m REAL,
    asimetria_pct REAL, deriva_fuera_pct REAL,
    p10 REAL, p50 REAL, p90 REAL, metodo TEXT,
    origen_dato TEXT NOT NULL DEFAULT 'CFD',
    PRIMARY KEY (spray_id)
);

-- error de interpolacion medido (no supuesto) en los puntos de validacion
CREATE TABLE IF NOT EXISTS interp_error (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plataforma TEXT, air_id_validacion TEXT, metrica TEXT,
    valor_cfd REAL, valor_interpolado REAL, error REAL, umbral REAL, supera_umbral INTEGER,
    fecha TEXT, origen_dato TEXT NOT NULL DEFAULT 'CFD'
);

-- coste real: sirve para planificar (INSTRUCCIONES §5.4)
CREATE TABLE IF NOT EXISTS run_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT NOT NULL CHECK (tipo IN ('air', 'spray', 'lagrangian')),
    ref_id TEXT NOT NULL, inicio TEXT, fin TEXT,
    horas_pared REAL, horas_cpu REAL, nucleos INTEGER, celdas INTEGER,
    convergido INTEGER, codigo_salida INTEGER, host TEXT, comando TEXT, nota TEXT
);

CREATE TABLE IF NOT EXISTS provenance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tabla TEXT, registro TEXT, campo TEXT, clase TEXT, fuente TEXT, nota TEXT, fecha TEXT
);

CREATE VIEW IF NOT EXISTS v_cola_aire AS
SELECT plataforma, rol, estado, COUNT(*) AS n FROM air_cases GROUP BY 1, 2, 3;
"""


def air_id(p: str, V: float, H: float, f: float, split, cuerpos: int, malla: str) -> str:
    s = f"_s{split:.2f}" if split is not None else ""
    c = "_cOpt" if cuerpos else ""
    m = "" if malla == "gruesa" else f"_m{malla}"
    return f"A_{p}_V{V:04.1f}_H{H:.1f}_f{f:.2f}{s}{c}{m}_g2"


SIN_EVAP = "SIN_EVAP"     # deposicion POTENCIAL (sin evaporacion): referencia "lo que deberia llegar"


def climas_activos(con: sqlite3.Connection) -> list[str]:
    """SIN_EVAP + escenarios de `climate_scenarios` (scripts/build_climate_scenarios.py, datos MMVR)."""
    try:
        ids = [r[0] for r in con.execute("SELECT clima_id FROM climate_scenarios ORDER BY cuantil_dT")]
    except sqlite3.OperationalError:
        ids = []
    if not ids:
        raise RuntimeError("no hay climate_scenarios: ejecuta scripts/build_climate_scenarios.py --escribir-db")
    return [SIN_EVAP] + ids


def migrar_nivel_b_sin_clima(con: sqlite3.Connection) -> str:
    """Entry 023: lagrangian_runs / spray_cases ganan la dimension clima_id. Las tablas previas
    (sin resultados) se conservan renombradas con sufijo _sin_clima; nada se borra."""
    cols = [r[1] for r in con.execute("PRAGMA table_info(lagrangian_runs)")]
    if not cols or "clima_id" in cols:
        return ""
    con.execute("DROP VIEW IF EXISTS v_cola_aire")
    # las FK de deposition_maps/swath_metrics seguirian a la tabla renombrada: se renombran tambien (vacias)
    for t in ("lagrangian_runs", "spray_cases", "deposition_maps", "swath_metrics"):
        con.execute(f"ALTER TABLE {t} RENAME TO {t}_sin_clima")
    con.commit()
    return "nivel B sin clima conservado como lagrangian_runs_sin_clima / spray_cases_sin_clima"


def migrar_cfd_airflow_v1(con: sqlite3.Connection) -> str:
    cols = [r[1] for r in con.execute("PRAGMA table_info(cfd_airflow)")]
    if not cols or "air_id" in cols:
        return "sin migracion"
    n = con.execute("SELECT COUNT(*) FROM cfd_airflow").fetchone()[0]
    if n:
        existe = con.execute("SELECT 1 FROM sqlite_master WHERE name='cfd_airflow_v1'").fetchone()
        if existe:
            raise RuntimeError("cfd_airflow (v1) y cfd_airflow_v1 coexisten: revisar a mano")
        con.execute("ALTER TABLE cfd_airflow RENAME TO cfd_airflow_v1")
        return f"cfd_airflow v1 ({n} fila/s) conservada como cfd_airflow_v1"
    con.execute("DROP TABLE cfd_airflow")
    return "cfd_airflow v1 vacia: sustituida por la v2"


def filas_aire(plats: dict) -> list[dict]:
    out = []

    def add(p, V, H, f, etapa, rol, prio, split=None, cuerpos=0, malla="gruesa", motivo=None):
        P = plats[p]
        if P.coaxial and split is None:
            split = 0.5
        aid = air_id(p, V, H, f, split, cuerpos, malla)
        estado, mot = "pendiente", motivo
        theta = 0.0 if V == 0 else round(att.theta_deg(p, V, f), 4)
        tclase = "exacto (hover)" if V == 0 else att.CLASE
        if mot:
            estado = "bloqueado"
        out.append(dict(air_id=aid, plataforma=p, V_ms=float(V), H_m=float(H), f=float(f),
                        masa_kg=round(P.masa(f), 4), theta_actitud_deg=theta, theta_clase=tclase,
                        split_coax=split, cuerpos_opcionales=cuerpos, malla=malla,
                        hover_bc="abierto" if V == 0 else None, etapa=etapa, rol=rol,
                        prioridad=prio, geometria_version=GEOM, estado=estado, bloqueo_motivo=mot))

    # CFD-0 (prioridad 0): T25P hover, H 2.5, f 1, tres mallas
    add("T25P", 0, 2.5, 1.0, 0, "cfd0", 0)
    add("T25P", 0, 2.5, 1.0, 0, "cfd0_malla", 1, malla="media")
    add("T25P", 0, 2.5, 1.0, 0, "cfd0_malla", 1, malla="fina")
    vistos = {out[0]["air_id"]}

    # efecto de los cuerpos opcionales delanteros sobre el aire (T25P, T70P)
    for p in ("T25P", "T70P"):
        for V in (0, 8 if p == "T70P" else 6):
            add(p, V, 2.5, 1.0, 1, "efecto_cuerpos", 3, cuerpos=1,
                motivo="falta STL con cuerpos opcionales (AIRFRAME_NOZZLE_CONFIGS=('std',))")

    # etapa 1: rejilla gruesa. Prioridad: hover f=1/0 primero (H5 cuanto antes), luego V
    for p in cg.PLATAFORMAS:
        for f in F_ETAPA1:
            for H in H_ETAPA1:
                for V in V_ETAPA1.get(p, V_ETAPA1["_"]):
                    prio = 2 if V == 0 else 4
                    aid = air_id(p, V, H, f, 0.5 if plats[p].coaxial else None, 0, "gruesa")
                    if aid in vistos:
                        continue
                    add(p, V, H, f, 1, "etapa1", prio)
    # T100: sensibilidad al reparto coaxial
    for split in (0.6, 0.7):
        for V in (0, 8):
            for f in (1.0, 0.0):
                add("T100", V, 2.5, f, 1, "sens_split", 3, split=split)
    # etapa 2: validacion de la interpolacion
    for p in cg.PLATAFORMAS:
        for H, V, f in VALIDACION.get(p, VALIDACION["_"]):
            add(p, V, H, f, 2, "validacion_interp", 5)
    return out


def aplicar_theta_E(con: sqlite3.Connection, ahora: str) -> int:
    """Desbloquea las filas V>0 que estaban bloqueadas SOLO por la actitud (clase D)."""
    filas = con.execute("SELECT air_id, plataforma, V_ms, f FROM air_cases WHERE estado='bloqueado' "
                        "AND V_ms > 0 AND bloqueo_motivo LIKE 'actitud theta%'").fetchall()
    for aid, p, V, f in filas:
        con.execute("UPDATE air_cases SET theta_actitud_deg=?, theta_clase=?, estado='pendiente', "
                    "bloqueo_motivo=NULL, actualizado=? WHERE air_id=?",
                    (round(att.theta_deg(p, V, f), 4), att.CLASE, ahora, aid))
    if filas:
        con.execute("INSERT INTO provenance (tabla, registro, campo, clase, fuente, nota, fecha) "
                    "VALUES (?,?,?,?,?,?,?)", ("air_cases", "V>0", "theta_actitud_deg", att.CLASE,
                                               att.FUENTE, f"{len(filas)} filas desbloqueadas", ahora))
    con.commit()
    return len(filas)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--resumen", action="store_true")
    a = ap.parse_args()
    con = sqlite3.connect(DB)
    ahora = datetime.now(timezone.utc).isoformat(timespec="seconds")

    if not a.resumen:
        nota_mig = migrar_cfd_airflow_v1(con)
        nota_clima = migrar_nivel_b_sin_clima(con)
        if nota_clima:
            print(nota_clima)
        con.executescript(SCHEMA)
        climas = climas_activos(con)
        plats = cg.cargar_todas()
        for k, P in plats.items():
            q = cg.CAUDAL_MAX_LMIN[k]
            con.execute("INSERT OR REPLACE INTO platforms_v2 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                k, P.nombre, P.version_modelo, len(P.rotores), int(P.coaxial), P.masa_vacio_kg,
                P.tanque_kg, P.mtow_kg, P.z_suelo_modelo, cg.V_MAX_MS[k], "O",
                q[2][0], q[4][0], f"{q[2][1]}/{q[4][1]}",
                str((P.dir_modelo / f"{P.prefijo}_cfd_coordinates.json").relative_to(ROOT)).replace("\\", "/"),
                f"masas: {json.dumps(P.masa_fuente)}"))
        filas = filas_aire(plats)
        cols = list(filas[0])
        n_air = 0
        for r in filas:
            cur = con.execute(
                f"INSERT OR IGNORE INTO air_cases ({','.join(cols)},creado,actualizado) "
                f"VALUES ({','.join('?' * len(cols))},?,?)", [r[c] for c in cols] + [ahora, ahora])
            n_air += cur.rowcount
        # nivel B: unidades Lagrangianas y escenarios programados por cada caso de aire
        n_lag = n_spr = 0
        for r in filas:
            P = plats[r["plataforma"]]
            for cl in climas:
                ev = int(cl != SIN_EVAP)
                for b in P.boquillas:
                    for d in D_CLASES:
                        rid = f"L_{r['air_id'][2:]}_{b.nozzle_id}_d{d:03d}_{cl}"
                        cur = con.execute(
                            "INSERT OR IGNORE INTO lagrangian_runs (run_id, air_id, nozzle_id, "
                            "configuracion_boquilla, d_clase_um, clima_id, evaporacion, requiere_boquilla_niebla) "
                            "VALUES (?,?,?,?,?,?,?,?)",
                            (rid, r["air_id"], b.nozzle_id, b.configuracion, d, cl, ev, int(d < 50)))
                        n_lag += cur.rowcount
                for d in D_VMD:
                    for cfg in (2, 4):
                        sid = f"S_{r['air_id'][2:]}_vmd{d:03d}_a{cfg}_{cl}"
                        cur = con.execute(
                            "INSERT OR IGNORE INTO spray_cases (spray_id, air_id, d_vmd_um, espectro_modelo, "
                            "espectro_clase, clima_id, config_atom) VALUES (?,?,?,?,?,?,?)",
                            (sid, r["air_id"], d, "pendiente (Guo et al. 2025, falta PDF)", "D", cl, cfg))
                        n_spr += cur.rowcount
        con.execute("INSERT INTO provenance (tabla, registro, campo, clase, fuente, nota, fecha) "
                    "VALUES (?,?,?,?,?,?,?)",
                    ("air_cases", "*", "matriz", "ESPECIFICACION", "INSTRUCCIONES_CFD.md §5.5",
                     "etapa 1 APROBADA por el propietario 2026-11-23", ahora))
        n_theta = aplicar_theta_E(con, ahora)
        if n_theta:
            print(f"theta modelo E aplicado a {n_theta} caso(s) antes bloqueados")
        con.commit()
        print(f"migracion: {nota_mig}")
        print(f"insertados: air_cases {n_air} · lagrangian_runs {n_lag} · spray_cases {n_spr}")

    print("\nCOLA DE AIRE (plataforma, rol, estado, n):")
    for fila in con.execute("SELECT * FROM v_cola_aire ORDER BY 1, 2, 3"):
        print("  ", fila)
    tot = con.execute("SELECT estado, COUNT(*) FROM air_cases GROUP BY 1").fetchall()
    print("\ntotal por estado:", dict(tot))
    print("lagrangian_runs:", con.execute("SELECT COUNT(*) FROM lagrangian_runs").fetchone()[0],
          "· spray_cases:", con.execute("SELECT COUNT(*) FROM spray_cases").fetchone()[0])
    print("resultados CFD (cfd_airflow v2):", con.execute("SELECT COUNT(*) FROM cfd_airflow").fetchone()[0])
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
