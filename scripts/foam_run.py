#!/usr/bin/env python3
"""
LANZADOR de la suite CFD que NO depende de `source .../etc/bashrc`.

POR QUE EXISTE (bug real encontrado al ejecutar verify_cfd_prereqs.sh en WSL):
  Al hacer `source /usr/lib/openfoam/openfoam2412/etc/bashrc` DENTRO de un script, la
  ejecucion SE CORTA en seco. El bashrc de OpenFOAM esta pensado para una shell interactiva
  (imprime un banner y puede terminar el proceso). Resultado: el script moria en silencio
  justo despues del aviso "intentando cargar el entorno...".

  Este lanzador consigue lo mismo por una via robusta:
    1. Captura el entorno que produce el comando `openfoam2412` (que ya funciona en la
       maquina, verificado) parseando sus `export`.
    2. Aplica esas variables al proceso hijo.
    3. Ejecuta el comando pedido con ese entorno.

  Asi NO se hace `source` dentro de un script y no hay corte.

USO (desde dentro de WSL, en la raiz del proyecto):
    python3 scripts/foam_run.py check                      # diagnostico del entorno
    python3 scripts/foam_run.py bash scripts/gate_cfd0.sh  # ejecutar el gate
    python3 scripts/foam_run.py -- <cualquier comando>

Sin argumentos: ejecuta el diagnostico.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Rutas candidatas del envoltorio de sesion y del bashrc (en orden de preferencia)
WRAPPERS = ["/usr/bin/openfoam2412", "openfoam2412", "openfoam", "of2412"]
BASHRC_GLOBS = [
    "/usr/lib/openfoam/openfoam*/etc/bashrc",
    "/opt/openfoam*/etc/bashrc",
]


def _run(cmd: list[str], env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=120)


def capturar_entorno_de_wrapper() -> tuple[dict | None, str]:
    """Ejecuta `openfoam2412 -c 'env'` (o equivalente) y parsea los export.

    Tambien prueba con `env` a secas tras entrar al wrapper, segun como este hecho.
    """
    wrapper = None
    for w in WRAPPERS:
        p = shutil.which(w) if not w.startswith("/") else (w if Path(w).exists() else None)
        if p:
            wrapper = p
            break
    if not wrapper:
        return None, "no se encontro el envoltorio de sesion de OpenFOAM"

    # Variante A: el wrapper acepta -c / --command
    for args in (["-c", "env"], ["--command", "env"], ["-c", "printenv"]):
        try:
            r = _run([wrapper, *args])
        except Exception:  # noqa: BLE001
            continue
        if r.returncode == 0 and "FOAM_" in r.stdout:
            return parsear_env(r.stdout), f"{wrapper} {' '.join(args)}"

    # Variante B: el wrapper lee de stdin
    try:
        r = subprocess.run([wrapper], input="env\nexit\n", capture_output=True,
                           text=True, timeout=120)
        if "FOAM_" in r.stdout:
            return parsear_env(r.stdout), f"{wrapper} (stdin)"
    except Exception:  # noqa: BLE001
        pass

    return None, (f"{wrapper} existe pero no se pudo extraer el entorno automaticamente. "
                  "Usa la via manual descrita en el mensaje final.")


def parsear_env(texto: str) -> dict:
    """Extrae asignaciones VAR=valor del texto, centrandose en FOAM_* y PATH."""
    env = {}
    for linea in texto.splitlines():
        linea = linea.strip()
        if not linea or "=" not in linea or linea.startswith("#"):
            continue
        if ":" in linea.split("=", 1)[0]:
            continue
        var, _, val = linea.partition("=")
        if not var.replace("_", "").isalnum():
            continue
        env[var] = val
    return env


def capturar_entorno_de_bashrc() -> tuple[dict | None, str]:
    """Alternativa robusta al `source`: carga el bashrc en un SUBSHELL y captura env.

    Esto evita el problema de que el bashrc corte la ejecucion del script actual: el corte
    ocurre en el subshell, no en nosotros, y lo unico que nos importa es su salida `env`.
    """
    import glob
    for patron in BASHRC_GLOBS:
        for f in sorted(glob.glob(patron)):
            for shell in ("bash", "/bin/bash"):
                if not shutil.which(shell) and not Path(shell).exists():
                    continue
                try:
                    r = _run([shell, "-c", f'source "{f}" >/dev/null 2>&1; env'])
                except Exception:  # noqa: BLE001
                    continue
                if "FOAM_" in r.stdout:
                    return parsear_env(r.stdout), f"subshell con source {f}"
    return None, "no se pudo cargar el entorno desde ningun etc/bashrc"


def construir_entorno() -> tuple[dict | None, str]:
    # 1. Si ya esta cargado, no tocar nada
    if shutil.which("blockMesh"):
        return dict(os.environ), "blockMesh ya estaba en PATH (entorno ya cargado)"

    # 2. Intentar via wrapper de sesion
    env, como = capturar_entorno_de_wrapper()
    if env:
        nuevo = dict(os.environ)
        nuevo.update(env)
        return nuevo, como

    # 3. Intentar via subshell + source
    env, como = capturar_entorno_de_bashrc()
    if env:
        nuevo = dict(os.environ)
        nuevo.update(env)
        return nuevo, como

    return None, como


def diagnostico() -> int:
    print("=" * 78)
    print(" DIAGNOSTICO DEL ENTORNO OpenFOAM (via scripts/foam_run.py)")
    print("=" * 78)

    print("\n-- binarios OpenFOAM presentes en el sistema")
    import glob
    for p in sorted(glob.glob("/usr/lib/openfoam/openfoam*")) + \
             sorted(glob.glob("/opt/openfoam*")):
        print(f"   {p}")
    for w in ("/usr/bin/openfoam2412", "/usr/bin/openfoam"):
        if Path(w).exists():
            print(f"   envoltorio de sesion: {w}")

    print("\n-- intentando construir el entorno")
    env, como = construir_entorno()
    if env is None:
        print(f"   [FALLO] {como}")
        print("\n   VIA MANUAL (carga el entorno en tu shell y vuelve a lanzar):")
        print("       source /usr/lib/openfoam/openfoam2412/etc/bashrc")
        print("       python3 scripts/foam_run.py check")
        return 2
    print(f"   [OK] {como}")

    print("\n-- ejecutables")
    fallos = 0
    for exe in ("blockMesh", "checkMesh", "topoSet", "simpleFoam"):
        ruta = shutil.which(exe, path=env.get("PATH", os.environ.get("PATH", "")))
        if ruta:
            print(f"   [OK]    {exe} -> {ruta}")
        else:
            print(f"   [FALLO] {exe} no encontrado")
            fallos += 1
    for var in ("WM_PROJECT_VERSION", "FOAM_APPBIN", "WM_PROJECT_DIR"):
        if var in env:
            print(f"   {var} = {env[var]}")

    print("\n-- herramientas auxiliares")
    for t in ("python3", "awk", "sort", "cut", "mpirun"):
        ruta = shutil.which(t, path=env.get("PATH", os.environ.get("PATH", "")))
        print(f"   {'[OK]   ' if ruta else '[AVISO]'} {t}" + (f" -> {ruta}" if ruta else ""))

    print("\n-- proyecto")
    print(f"   raiz: {ROOT}")
    casos = sorted((ROOT / "cfd" / "cases").glob("*_V*"))
    print(f"   casos encontrados: {len(casos)}")

    print("\n" + "=" * 78)
    if fallos == 0:
        print(" ENTORNO LISTO -> lanza el gate con:")
        print("     python3 scripts/foam_run.py bash scripts/gate_cfd0.sh")
    else:
        print(f" {fallos} ejecutable(s) faltante(s)")
    print("=" * 78)
    return fallos


def main() -> int:
    args = sys.argv[1:]
    if args and args[0] == "--":
        args = args[1:]
    if not args or args[0] == "check":
        return diagnostico()

    env, como = construir_entorno()
    if env is None:
        print(f"ERROR: no se pudo construir el entorno OpenFOAM ({como})")
        print("Carga el entorno a mano y reintenta:")
        print("    source /usr/lib/openfoam/openfoam2412/etc/bashrc")
        return 127
    print(f"[foam_run] entorno: {como}")

    # heredar stdio para que se vea la salida en vivo (evita pipes con nombre)
    r = subprocess.run(args, cwd=str(ROOT), env=env,
                       stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)
    return r.returncode


if __name__ == "__main__":
    raise SystemExit(main())
