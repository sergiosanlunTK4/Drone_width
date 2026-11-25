"""
COLA REANUDABLE de casos de aire (nivel A) — INSTRUCCIONES_CFD.md §5.3.

Toma los `air_cases` en estado `pendiente` de `data/processed/dronewith.sqlite` por orden de
`prioridad`, genera el caso (build_case_suite v2), lo ejecuta en WSL (Allrun.sh via
foam_run.py), registra el coste real en `run_log` y marca `hecho` o `fallido`.
Pensada para correr de noche durante dias: si se interrumpe, al relanzarla los casos que
quedaron `en_curso` vuelven a `pendiente`, y el caso reutiliza la malla ya hecha.

GATES (Metodologia §10, regla 3 del proyecto): mientras `evidence/cfd0_conditions.json` no
tenga las 5 condiciones en `pasa: true`, SOLO se ejecutan casos con rol `cfd0`/`cfd0_malla`.
No hay opcion para saltarselo: se cierra el gate o no se escala.

`hecho` = el solver termino. Poblar `cfd_airflow` es trabajo de postprocess_case.py (solo
desde salidas reales). `convergido` en run_log sale del log del solver, no se supone.

Uso (desde Windows o desde WSL, en la raiz del proyecto):
    python scripts/run_queue.py --dry-run            # que haria
    python scripts/run_queue.py --max 1              # un caso
    python scripts/run_queue.py --rol cfd0 --np 8
    python scripts/run_queue.py --estado             # resumen de la cola
"""
from __future__ import annotations

import argparse
import json
import os
import re
import socket
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
DB = ROOT / "data" / "processed" / "dronewith.sqlite"
CASES = ROOT / "cfd" / "cases"
GATE_CFD0 = ROOT / "evidence" / "cfd0_conditions.json"
GATE_MALLA = ROOT / "evidence" / "cfd0_independencia_malla.json"
GATE_ACOPLE = ROOT / "evidence" / "cfd0_acoplamiento.json"
ROLES_CFD0 = ("cfd0", "cfd0_malla")
MAX_INTENTOS = 2
WSL_ROOT = "/mnt/d/AUTOMATIONS/DRONEWITH"


def ahora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def gate_cfd0_cerrado() -> tuple[bool, str]:
    if not GATE_CFD0.exists():
        return False, "no existe evidence/cfd0_conditions.json"
    conds = json.loads(GATE_CFD0.read_text(encoding="utf-8"))
    malas = [c["condicion"] for c in conds if not c.get("pasa")]
    if len(conds) < 5 or malas:
        return False, f"CFD-0 abierto: {len(conds) - len(malas)}/5 ({'; '.join(malas)})"
    # INSTRUCCIONES_CFD.md Paso 2: ademas de las 5 condiciones, independencia de malla (2-3
    # niveles) y verificacion del desacoplamiento aire/gotas (§5.1). Sin ellas no se escala.
    for extra, nombre in ((GATE_MALLA, "independencia de malla"), (GATE_ACOPLE, "desacoplamiento aire/gotas")):
        if not extra.exists():
            return False, f"CFD-0 abierto: 5/5 condiciones, falta {nombre} ({extra.name})"
        if not json.loads(extra.read_text(encoding="utf-8")).get("pasa"):
            return False, f"CFD-0 abierto: {nombre} no pasa ({extra.name})"
    return True, "CFD-0 cerrado"


def comando_wsl(cmd: str) -> list[str]:
    """Ejecuta `cmd` en la raiz del proyecto con el entorno OpenFOAM (foam_run.py)."""
    interno = f"cd {WSL_ROOT} && python3 scripts/foam_run.py bash -c {json.dumps(cmd)}"
    if os.name == "nt":
        return ["wsl.exe", "-d", "Ubuntu", "--", "bash", "-lc", interno]
    return ["bash", "-lc", interno]


def leer_log_solver(caso: Path) -> dict:
    """Coste y convergencia desde log.simpleFoam / log.checkMesh (salidas reales)."""
    out = {"celdas": None, "exec_s": None, "clock_s": None, "convergido": 0, "iter": None}
    cm = caso / "log.checkMesh"
    if cm.exists():
        m = re.search(r"^\s*cells:\s+(\d+)", cm.read_text(errors="replace"), re.M)
        out["celdas"] = int(m.group(1)) if m else None
    lg = caso / "log.simpleFoam"
    if lg.exists():
        t = lg.read_text(errors="replace")
        tiempos = re.findall(r"ExecutionTime = ([\d.]+) s\s+ClockTime = ([\d.]+) s", t)
        if tiempos:
            out["exec_s"], out["clock_s"] = float(tiempos[-1][0]), float(tiempos[-1][1])
        its = re.findall(r"^Time = (\d+)", t, re.M)
        out["iter"] = int(its[-1]) if its else None
        out["convergido"] = int("solution converged in" in t or "reached convergence" in t)
    return out


def reanudar_interrumpidos(con: sqlite3.Connection) -> int:
    cur = con.execute("UPDATE air_cases SET estado='pendiente', actualizado=? WHERE estado='en_curso'",
                      (ahora(),))
    con.commit()
    return cur.rowcount


def siguientes(con, rol, plataforma, solo_cfd0) -> list[dict]:
    q = "SELECT * FROM air_cases WHERE estado='pendiente'"
    args = []
    if solo_cfd0:
        q += f" AND rol IN ({','.join('?' * len(ROLES_CFD0))})"
        args += list(ROLES_CFD0)
    if rol:
        q += " AND rol = ?"
        args.append(rol)
    if plataforma:
        q += " AND plataforma = ?"
        args.append(plataforma.upper())
    q += (" ORDER BY prioridad, CASE malla WHEN 'gruesa' THEN 0 WHEN 'media' THEN 1 ELSE 2 END,"
          " air_id")
    con.row_factory = sqlite3.Row
    filas = [dict(r) for r in con.execute(q, args)]
    con.row_factory = None
    return filas


def ejecutar(con, fila: dict, np_: int, dry: bool) -> str:
    from build_case_suite import escribir_caso_aire  # noqa: PLC0415

    aid = fila["air_id"]
    caso = CASES / aid
    if dry:
        print(f"  [dry-run] {aid}: escribiria {caso.relative_to(ROOT)} y lanzaria Allrun.sh (NP={np_})")
        return "dry"
    con.execute("UPDATE air_cases SET estado='en_curso', intentos=intentos+1, case_dir=?, actualizado=? "
                "WHERE air_id=?", (str(caso.relative_to(ROOT)).replace("\\", "/"), ahora(), aid))
    con.commit()
    if not (caso / "constant" / "polyMesh").exists():
        escribir_caso_aire(caso, fila, fila.get("malla") or "gruesa", fila.get("hover_bc") or "abierto")
    rel = str(caso.relative_to(ROOT)).replace("\\", "/")
    cmd = f"NP={np_} bash {rel}/Allrun.sh"
    inicio, t0 = ahora(), time.time()
    print(f"  -> {aid}  [{inicio}]  {cmd}", flush=True)
    with open(caso / "log.run_queue", "a", encoding="utf-8") as fh:
        try:
            rc = subprocess.run(comando_wsl(cmd), stdout=fh, stderr=subprocess.STDOUT).returncode
        except KeyboardInterrupt:
            con.execute("UPDATE air_cases SET estado='pendiente', actualizado=? WHERE air_id=?", (ahora(), aid))
            con.commit()
            raise
    pared_h = (time.time() - t0) / 3600.0
    info = leer_log_solver(caso)
    cpu_h = info["exec_s"] * np_ / 3600.0 if info["exec_s"] else None
    con.execute("INSERT INTO run_log (tipo, ref_id, inicio, fin, horas_pared, horas_cpu, nucleos, celdas, "
                "convergido, codigo_salida, host, comando, nota) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                ("air", aid, inicio, ahora(), round(pared_h, 4), round(cpu_h, 4) if cpu_h else None,
                 np_, info["celdas"], info["convergido"], rc, socket.gethostname(), cmd,
                 f"iteraciones={info['iter']}; ExecutionTime_s={info['exec_s']}; ClockTime_s={info['clock_s']}"))
    if rc == 0:
        estado = "hecho"
    else:
        intentos = con.execute("SELECT intentos FROM air_cases WHERE air_id=?", (aid,)).fetchone()[0]
        estado = "fallido" if intentos >= MAX_INTENTOS else "pendiente"
    con.execute("UPDATE air_cases SET estado=?, actualizado=? WHERE air_id=?", (estado, ahora(), aid))
    con.commit()
    print(f"     rc={rc}  {estado}  pared={pared_h:.2f} h  celdas={info['celdas']}  "
          f"convergido={info['convergido']}  iter={info['iter']}", flush=True)
    return estado


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--max", type=int, default=0, help="maximo de casos en esta sesion (0 = todos)")
    ap.add_argument("--rol")
    ap.add_argument("--plataforma")
    ap.add_argument("--np", type=int, default=6, help="6 medido 2.5x mas rapido que 8 (Entry 020)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--estado", action="store_true")
    a = ap.parse_args()

    con = sqlite3.connect(DB, timeout=60)
    if a.estado:
        for r in con.execute("SELECT rol, estado, COUNT(*) FROM air_cases GROUP BY 1, 2 ORDER BY 1, 2"):
            print("  ", r)
        for r in con.execute("SELECT ref_id, horas_pared, horas_cpu, celdas, convergido, codigo_salida "
                             "FROM run_log ORDER BY id DESC LIMIT 10"):
            print("   run_log:", r)
        return 0

    cerrado, motivo = gate_cfd0_cerrado()
    print(f"gate: {motivo}")
    if not a.dry_run:
        n = reanudar_interrumpidos(con)
        if n:
            print(f"reanudados {n} caso(s) que quedaron en_curso")
    hechos = 0
    while True:
        cola = siguientes(con, a.rol, a.plataforma, solo_cfd0=not cerrado)
        if a.dry_run:
            cola = cola[: a.max or len(cola)]
            for fila in cola:
                ejecutar(con, fila, a.np, True)
            print(f"{len(cola)} caso(s) en cola con los filtros dados")
            return 0
        if not cola:
            print("cola vacia (con los filtros y el gate actuales)")
            break
        ejecutar(con, cola[0], a.np, False)
        hechos += 1
        if a.max and hechos >= a.max:
            break
        if not cerrado:
            cerrado, motivo = gate_cfd0_cerrado()
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
