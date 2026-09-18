"""
Convierte los objetos vectoriales (EMF/WMF) extraidos de los PPTX a PNG y SVG legibles.

POR QUE HACE FALTA:
  los diagramas rotulados del deck 01 (slide 09) estan en formato EMF vectorial y son el
  mejor candidato para leer POSICIONES RELATIVAS sin depender de una escala externa.
  En este entorno no hay Inkscape, ImageMagick ni LibreOffice, y winget esta bloqueado.
  Pillow SI puede rasterizar WMF/EMF en Windows a traves de GDI (se verifico que carga el
  archivo a 2587x1279), asi que se usa ese camino sin instalar nada.

ADVERTENCIA DE RIGOR (context.md SS51; protocolo SS1):
  Que el original sea vectorial NO lo hace metrico. El dibujo pudo deformarse al insertarlo
  o escalarlo en PowerPoint. Por tanto:
    - los objetos derivados aqui siguen siendo clasificacion **S** (evidencia documental);
    - sirven para topologia, angulos y posiciones RELATIVAS;
    - para pasar de pixeles del dibujo a milimetros hace falta al menos UNA dimension de
      referencia fiable dentro de la MISMA vista;
    - nada de lo obtenido aqui se sube a **M** sin calibracion independiente.

Sobre el SVG: Pillow envuelve el mapa de bits en un SVG, por lo que el resultado NO son
trazados vectoriales. El PNG escalado es el entregable util. Se documenta la limitacion en
vez de presentar un SVG que no es lo que aparenta.

Uso:
  python scripts/convert_vector_media.py
  python scripts/convert_vector_media.py --scale 3     # mas resolucion
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "data" / "raw" / "media"
OUT = ROOT / "data" / "raw" / "media_converted"

VECTOR_EXT = {".emf", ".wmf", ".wdp"}


def convertir(src: Path, dest_dir: Path, scale: float) -> dict:
    dest_dir.mkdir(parents=True, exist_ok=True)
    res = {"origen": str(src.relative_to(ROOT)).replace("\\", "/"), "ok": False}
    try:
        with Image.open(src) as im:
            res["formato_detectado"] = im.format
            res["tamano_nativo_px"] = im.size
            if im.mode not in ("RGB", "RGBA"):
                im = im.convert("RGB")
            nuevo = (max(1, int(im.size[0] * scale)), max(1, int(im.size[1] * scale)))
            grande = im.resize(nuevo, Image.LANCZOS)
            png = dest_dir / f"{src.stem}.png"
            grande.save(png)
            res["png"] = str(png.relative_to(ROOT)).replace("\\", "/")
            res["png_px"] = grande.size
            res["ok"] = True
    except Exception as e:  # noqa: BLE001
        res["error"] = f"{type(e).__name__}: {e}"
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", type=float, default=2.0,
                    help="factor de escala del PNG (default 2.0)")
    a = ap.parse_args()

    if not MEDIA.exists():
        print(f"no existe {MEDIA.relative_to(ROOT)}; ejecuta antes scripts/extract_pptx_media.py")
        return 2

    vectores = [p for p in MEDIA.rglob("*") if p.suffix.lower() in VECTOR_EXT]
    if not vectores:
        print("no se encontraron objetos vectoriales")
        return 0

    print(f"objetos vectoriales: {len(vectores)}  (escala x{a.scale})\n")
    resultados = []
    for src in sorted(vectores, key=lambda p: -p.stat().st_size):
        r = convertir(src, OUT / src.parent.name, a.scale)
        resultados.append(r)
        mb = src.stat().st_size / 1e6
        if r["ok"]:
            print(f"  OK   {mb:6.2f} MB  {r['formato_detectado']:4s} {r['tamano_nativo_px']} -> "
                  f"{r['png_px']} px  {r['png']}")
        else:
            print(f"  FALLO {mb:6.2f} MB  {src.name}: {r.get('error')}")

    ok = sum(1 for r in resultados if r["ok"])
    print(f"\nconvertidos: {ok}/{len(resultados)}")
    print("\nRECORDATORIO: salida clasificada S (evidencia documental visual), no M.")
    print("Sirve para topologia y posiciones relativas. Para milimetros hace falta una")
    print("dimension de referencia fiable en la MISMA vista.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
