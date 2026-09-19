"""
Verifica e inspecciona la base de datos del proyecto.

Uso:
  python scripts/check_database.py
  python scripts/check_database.py --sql "SELECT * FROM cases LIMIT 5"
"""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "processed" / "dronewith.sqlite"


CONSULTAS = [
    ("Estado global (vista v_estado)", "SELECT * FROM v_estado"),
    ("Plataformas",
     "SELECT plataforma, n_rotores, area_disco_m2, mtow_kg, coaxial FROM platforms ORDER BY mtow_kg"),
    ("Casos por plataforma",
     "SELECT plataforma, COUNT(*) AS casos, "
     "ROUND(MIN(V_inf_ms),1) AS V_min, ROUND(MAX(V_inf_ms),1) AS V_max, "
     "ROUND(MIN(H_m),1) AS H_min, ROUND(MAX(H_m),1) AS H_max, "
     "ROUND(MIN(masa_total_kg),1) AS m_min, ROUND(MAX(masa_total_kg),1) AS m_max "
     "FROM cases GROUP BY plataforma ORDER BY plataforma"),
    ("Metricas analiticas: carga de disco y v inducida (a MTOW)",
     "SELECT c.plataforma, COUNT(*) AS n, "
     "ROUND(AVG(a.carga_disco_N_m2),1) AS DL_media, "
     "ROUND(AVG(a.v_inducida_hover_ms),3) AS v_ind_media, "
     "ROUND(AVG(a.Stokes_number),4) AS St_media "
     "FROM analytic_metrics a JOIN cases c ON a.case_id = c.case_id "
     "GROUP BY c.plataforma"),
    ("Regimen de la gota por tamano (T100)",
     "SELECT ROUND(c.DV05_um/50)*50 AS d_um, "
     "ROUND(AVG(a.Stokes_number),4) AS St, "
     "ROUND(AVG(a.v_terminal_gota_ms),3) AS v_term, "
     "ROUND(AVG(a.dominancia_estela),4) AS dominancia_estela "
     "FROM analytic_metrics a JOIN cases c ON a.case_id=c.case_id "
     "WHERE c.plataforma='T100' GROUP BY ROUND(c.DV05_um/50) ORDER BY d_um"),
    ("Franja: ancho efectivo analitico e interlineado (promedios)",
     "SELECT c.plataforma, ROUND(AVG(a.ancho_efectivo_analitico_m),2) AS W_eff_medio, "
     "ROUND(AVG(a.interlineado_recomendado_m),2) AS s_rec_medio, "
     "ROUND(AVG(a.cv_en_interlineado_recomendado_pct),1) AS CV_medio "
     "FROM analytic_metrics a JOIN cases c ON a.case_id=c.case_id GROUP BY c.plataforma"),
    ("Ocupacion de la base (que falta)",
     "SELECT 'cfd_airflow' AS tabla, COUNT(*) AS filas FROM cfd_airflow "
     "UNION ALL SELECT 'cfd_deposition', COUNT(*) FROM cfd_deposition "
     "UNION ALL SELECT 'cfd_swath_metrics', COUNT(*) FROM cfd_swath_metrics "
     "UNION ALL SELECT 'experiments', COUNT(*) FROM experiments "
     "UNION ALL SELECT 'surrogate_models', COUNT(*) FROM surrogate_models"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sql", default=None, help="consulta libre")
    a = ap.parse_args()

    if not DB.exists():
        print(f"no existe {DB.relative_to(ROOT)}; ejecuta scripts/build_database.py")
        return 2
    con = sqlite3.connect(DB)

    if a.sql:
        cur = con.execute(a.sql)
        cols = [d[0] for d in cur.description] if cur.description else []
        print(" | ".join(cols))
        for r in cur.fetchall():
            print(" | ".join(str(x) for x in r))
        return 0

    print("=" * 92)
    print(f"BASE DE DATOS: {DB.relative_to(ROOT)}")
    print("=" * 92)

    print("\n== TABLAS Y VISTAS ==")
    for t, in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
        n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t:24s} {n:6d} filas")
    for v, in con.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name"):
        print(f"  [vista] {v}")

    for titulo, sql in CONSULTAS:
        print(f"\n== {titulo} ==")
        cur = con.execute(sql)
        cols = [d[0] for d in cur.description]
        filas = cur.fetchall()
        anchos = [max(len(str(c)), *(len(str(r[i])) for r in filas)) if filas else len(str(c))
                  for i, c in enumerate(cols)]
        print("  " + "  ".join(str(c).ljust(anchos[i]) for i, c in enumerate(cols)))
        for r in filas:
            print("  " + "  ".join(str(x).ljust(anchos[i]) for i, x in enumerate(r)))

    con.close()
    print("\n" + "=" * 92)
    print("RECORDATORIO: analytic_metrics es FISICA ANALITICA, no CFD. Las tablas cfd_* y")
    print("experiments estan vacias por diseno: se llenan solo con datos reales.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
