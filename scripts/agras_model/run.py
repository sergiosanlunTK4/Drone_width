"""
Construye y post-procesa uno o varios modelos.

    python scripts/agras_model/run.py t70p            # una plataforma
    python scripts/agras_model/run.py all             # t25p t55 t70p t100
    python scripts/agras_model/run.py t55 --solo-post # solo JSON + figuras (sin FreeCAD)
"""
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FREECAD = os.environ.get("FREECADCMD", r"C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe")
ALL = ["t25p", "t55", "t70p", "t100"]


def run(platform, post_only=False):
    env = dict(os.environ, AGRAS_PLATFORM=platform, AGRAS_SCRIPT_DIR=str(HERE))
    if not post_only:
        sys.path.insert(0, str(HERE))
        import importlib
        out = HERE.parents[1] / importlib.import_module("platforms." + platform).OUT_DIR
        out.mkdir(parents=True, exist_ok=True)
        log = out / "mediciones" / "_build.log"
        log.parent.mkdir(exist_ok=True)
        with open(log, "w", encoding="utf-8", errors="replace") as f:
            r = subprocess.run([FREECAD, str(HERE / "build_freecad.py")], env=env, stdout=f, stderr=subprocess.STDOUT)
        txt = log.read_text(encoding="utf-8", errors="replace")
        if r.returncode != 0 or "Traceback" in txt or "Exception while processing" in txt:
            tail = "\n".join(line for line in txt.splitlines() if "%)" not in line)[-3000:]
            raise SystemExit(f"[{platform}] fallo en FreeCAD; ver {log}\n{tail}")
    subprocess.run([sys.executable, "-I", str(HERE / "export_metadata.py"), platform], check=True, cwd=str(HERE))


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    targets = ALL if not args or args[0] == "all" else args
    for p in targets:
        run(p, post_only="--solo-post" in sys.argv)
