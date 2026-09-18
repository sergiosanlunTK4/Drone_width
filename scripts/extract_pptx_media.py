"""
Extrae y cataloga los objetos multimedia de los PPTX de DJI Academy.

Motivo: los decks contienen diagramas, vistas ortogonales y fotografias que pueden contener
evidencia geometrica (posicion de atomizadores, montaje de brazos, cotas). Son evidencia
documental (S), NO medicion (M): sin escala o cota inequivoca no se convierten en dimensiones.

Salidas:
  data/raw/media/<deck>/<archivo>            imagenes extraidas
  data/processed/media_inventory.csv         catalogo (hash, tipo, tamano, dimensiones, slide)
  figures/contact_sheets/<deck>_sheetNN.png  hoja de contactos para revision visual rapida

Uso:
  python scripts/extract_pptx_media.py
"""
from __future__ import annotations

import csv
import hashlib
import io
import zipfile
from pathlib import Path

from lxml import etree
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = Path(r"C:\Users\Dimasur\OneDrive\Documents\DJI\Entrega de drones DJI\DJI ACADEMY COMPLETO")
OUT_MEDIA = ROOT / "data" / "raw" / "media"
OUT_SHEETS = ROOT / "figures" / "contact_sheets"
OUT_CSV = ROOT / "data" / "processed" / "media_inventory.csv"

DECKS = {
    "01a_conocimiento_basico": "01 Conocimiento básico de un Dron (1).pptx",
    "01b_intro_flujo_trabajo": "01 Introducción al Flujo de Trabajo de Entrega de Productos DJI AGRAS.pptx",
    "02_planificacion_mision": "02 Planificación de Misión y Modos de Operación en drones DJI AGRAS.pptx",
    "03_parametros_aplicacion": "03 Recomendaciones para la Configuración de Parámetros  de aplicación en drones DJI AGRAS.pptx",
}

IMG_EXT = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp"}
VEC_EXT = {".emf", ".wmf", ".svg"}
P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def slide_of_media(zf: zipfile.ZipFile, deck_prefix: str) -> dict:
    """Mapea ppt/media/<archivo> -> numero de slide que lo referencia (via rels)."""
    import re
    # 1) slideN.xml.rels -> rId -> target media
    media_slide = {}
    pat = re.compile(re.escape(deck_prefix) + r"/slides/_rels/slide(\d+)\.xml\.rels$")
    for name in zf.namelist():
        m = pat.match(name)
        if not m:
            continue
        slide_num = int(m.group(1))
        root = etree.fromstring(zf.read(name))
        for rel in root:
            tgt = rel.get("Target", "")
            if "/media/" in tgt or tgt.startswith("../media/"):
                media_slide[tgt.split("/")[-1]] = slide_num
    return media_slide


def deck_prefix(zf: zipfile.ZipFile) -> str:
    for n in zf.namelist():
        if n.endswith("presentation.xml"):
            return n.rsplit("/", 1)[0]
    return "ppt"


def contact_sheet(images: list[tuple[str, Path]], out: Path, cols: int = 6, cell: int = 320, per_sheet: int = 24) -> int:
    """Hoja de contactos con etiqueta. Devuelve el numero de hojas generadas."""
    sheets = 0
    for start in range(0, len(images), per_sheet):
        chunk = images[start:start + per_sheet]
        rows = (len(chunk) + cols - 1) // cols
        W, H = cols * cell, rows * (cell + 18)
        sheet = Image.new("RGB", (W, H), (255, 255, 255))
        draw = ImageDraw.Draw(sheet)
        for i, (label, path) in enumerate(chunk):
            r, c = divmod(i, cols)
            x, y = c * cell, r * (cell + 18)
            try:
                im = Image.open(path)
                im.thumbnail((cell - 8, cell - 8))
                if im.mode not in ("RGB", "L"):
                    im = im.convert("RGB")
                sheet.paste(im, (x + 4, y + 4))
            except Exception:
                draw.rectangle([x + 4, y + 4, x + cell - 4, y + cell - 4], outline=(200, 0, 0))
                draw.text((x + 8, y + 8), "no legible", fill=(200, 0, 0))
            draw.text((x + 4, y + cell + 2), label[:46], fill=(0, 0, 0))
        sheets += 1
        out.parent.mkdir(parents=True, exist_ok=True)
        dest = out.with_name(f"{out.stem}{sheets:02d}{out.suffix}")
        sheet.save(dest)
        print(f"    hoja de contactos -> {dest.relative_to(ROOT)}")
    return sheets


def main() -> int:
    OUT_MEDIA.mkdir(parents=True, exist_ok=True)
    OUT_SHEETS.mkdir(parents=True, exist_ok=True)
    filas = []

    for deck_key, fname in DECKS.items():
        src = SRC_DIR / fname
        if not src.exists():
            print(f"  [{deck_key}] AUSENTE: {fname}")
            continue
        print(f"\n=== {deck_key} ===")
        zf = zipfile.ZipFile(src)
        prefix = deck_prefix(zf)
        media_slide = slide_of_media(zf, prefix)
        members = [n for n in zf.namelist() if "/media/" in n]
        out_dir = OUT_MEDIA / deck_key
        out_dir.mkdir(parents=True, exist_ok=True)

        extraidas = []
        for m in sorted(members):
            base = m.split("/")[-1]
            ext = Path(base).suffix.lower()
            data = zf.read(m)
            sha = hashlib.sha1(data).hexdigest()[:12]
            # nombre estable y trazable
            nuevo = f"p{media_slide.get(base, 0):02d}_{sha}{ext}"
            dest = out_dir / nuevo
            if not dest.exists():
                dest.write_bytes(data)

            ancho = alto = None
            legible = ""
            if ext in IMG_EXT:
                try:
                    im = Image.open(io.BytesIO(data))
                    ancho, alto = im.size
                    legible = "si"
                except Exception as e:
                    legible = f"no ({type(e).__name__})"
            elif ext in VEC_EXT:
                legible = "vectorial: requiere conversion"

            filas.append({
                "deck": deck_key,
                "slide": media_slide.get(base, ""),
                "archivo_original": base,
                "archivo_extraido": str(dest.relative_to(ROOT)).replace("\\", "/"),
                "extension": ext,
                "tipo": "imagen" if ext in IMG_EXT else ("vectorial" if ext in VEC_EXT else "otro"),
                "bytes": len(data),
                "ancho_px": ancho or "",
                "alto_px": alto or "",
                "legible_PIL": legible,
                "sha1_12": sha,
            })
            if ext in IMG_EXT and legible == "si":
                extraidas.append((f"s{media_slide.get(base,0):02d} {nuevo[:18]}", dest))

        print(f"  media totales: {len(members)}  |  imagenes legibles: {len(extraidas)}")
        by_slide = {}
        for f in filas:
            if f["deck"] == deck_key:
                by_slide[f["slide"]] = by_slide.get(f["slide"], 0) + 1
        print(f"  slides con media: {len(by_slide)}")
        # hojas de contactos, priorizando las slides con mas media (mas probables de ser diagramas)
        extraidas.sort(key=lambda t: t[0])
        contact_sheet(extraidas, OUT_SHEETS / f"{deck_key}_sheet.png")

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0].keys()))
        w.writeheader()
        w.writerows(filas)

    print(f"\nCatalogo -> {OUT_CSV.relative_to(ROOT)}  ({len(filas)} objetos)")
    print("\nAVISO METODOLOGICO: estos objetos son evidencia documental (S), NO medicion (M).")
    print("Solo pueden convertirse en dimensiones si existe escala o cota inequivoca en la imagen.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
