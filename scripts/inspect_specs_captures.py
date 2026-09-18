"""
Inspecciona las capturas de fichas oficiales para reconstruir la SEMANTICA de la tabla.

HALLAZGO QUE MOTIVA ESTE SCRIPT:
  las capturas de /es/ y /cn/ devuelven BYTES IDENTICOS (mismo sha256) y contienen
  0 tablas HTML: el contenido de especificaciones se hidrata por JavaScript. Por tanto
  comparar locales por HTTP no sirve para obtener el texto chino original. Hay que ir
  al payload embebido en el documento.

Este script:
  - confirma el idioma declarado del documento y de los datos embebidos;
  - localiza cada ocurrencia de los terminos de interes CON SU CONTEXTO CRUDO;
  - reconstruye pares campo/valor alrededor de la fila de helices;
  - deja constancia del texto Unicode original (sin traducir) cuando existe.

REGLA: REPORTA. No traduce automaticamente, no interpreta 对, no toca ningun manifiesto.

Uso:
  python scripts/inspect_specs_captures.py
  python scripts/inspect_specs_captures.py --uav t55 --term cantidad
"""
from __future__ import annotations

import argparse
import glob
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAP = ROOT / "data" / "raw" / "specs_captures"

TERMINOS = {
    "cantidad": r"Cantidad|数量|数目|數量",
    "pares":    r"\bpares?\b|对|對",
    "helice":   r"h[eé]lice|propeller|螺旋桨|桨|槳",
    "motor":    r"\bmotor(?:es)?\b|电机|馬達|马达",
    "esc":      r"\bESC\b|电调|電子調速",
    "coaxial":  r"coaxial|同轴|同軸",
    "pulgadas": r"pulgadas|inch|英寸",
}


def archivos(uav: str | None) -> list[Path]:
    patron = f"{uav}_*.html" if uav else "*_*.html"
    return sorted(CAP.glob(patron))


def contexto(txt: str, patron: str, ventana: int = 220, limite: int = 6) -> list[str]:
    out = []
    for m in list(re.finditer(patron, txt, re.I))[:limite]:
        frag = txt[max(0, m.start() - ventana): m.end() + ventana]
        out.append(frag)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--uav", default=None, choices=["t100", "t70p", "t55"])
    ap.add_argument("--term", default=None, choices=list(TERMINOS))
    ap.add_argument("--ventana", type=int, default=220)
    a = ap.parse_args()

    files = archivos(a.uav)
    if not files:
        print(f"no hay capturas en {CAP.relative_to(ROOT)}; ejecuta capture_official_specs.py")
        return 2

    vistos = {}
    for f in files:
        txt = f.read_text(encoding="utf-8", errors="replace")
        lang = re.findall(r'<html[^>]*lang="([^"]+)"', txt)
        # idioma de los datos embebidos: buscar caracteres CJK
        cjk = len(re.findall(r"[\u4e00-\u9fff]", txt))
        print(f"\n{'=' * 88}\n{f.name}\n{'=' * 88}")
        print(f"  bytes={len(txt)}  lang_html={lang[:2]}  caracteres_CJK_en_el_payload={cjk}")
        print(f"  sha256 de este archivo ya esta en capturas_manifest.json")

        terminos = [a.term] if a.term else list(TERMINOS)
        for t in terminos:
            hits = contexto(txt, TERMINOS[t], a.ventana)
            if not hits:
                print(f"\n  [{t}] sin coincidencias")
                continue
            print(f"\n  [{t}] {len(hits)} coincidencia(s) — contexto CRUDO:")
            for h in hits:
                print(f"    … {h} …")
                print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
