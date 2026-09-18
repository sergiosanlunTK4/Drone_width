"""
Extractor de texto para PPTX grandes (sin python-pptx, sin descomprimir entero).

- Lee directamente del ZIP con zipfile + lxml.
- Extrae: texto de formas, tablas (celdas), notas del orador y titulo de cada
  imagen (alt-text / descr), que es donde suelen ir las leyendas tecnicas.
- Inventario de imagenes (nombre y tamano) pero NO las extrae: el PPTX pesa
  107 MB y volcarlas al repo no aporta; se listan para decidir despues.

Uso:
  python scripts/extract_pptx_text.py "<ruta.pptx>" <salida.txt> [--grep PATRON]
"""
from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path

from lxml import etree

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def slide_key(name: str) -> int:
    m = re.search(r"slide(\d+)\.xml$", name)
    return int(m.group(1)) if m else 10**6


def text_of(el) -> str:
    return " ".join(t for t in el.itertext() if t and t.strip()).strip()


def parse_slide(xml: bytes) -> dict:
    root = etree.fromstring(xml)
    out = {"texts": [], "tables": [], "images": []}

    # Formas de texto (incluye titulos y cuadros)
    for sp in root.iter(f"{{{NS['p']}}}sp"):
        # nombre de forma
        nv = sp.find(f".//{{{NS['p']}}}cNvPr")
        label = nv.get("name") if nv is not None else ""
        descr = nv.get("descr") if nv is not None else ""
        txt = text_of(sp)
        if txt:
            out["texts"].append((label, txt))
        elif descr:
            out["texts"].append((label, f"[descr] {descr}"))

    # Tablas -> filas con celdas separadas por ' | '
    for tbl in root.iter(f"{{{NS['a']}}}tbl"):
        rows = []
        for tr in tbl.findall(f"{{{NS['a']}}}tr"):
            cells = [text_of(tc) for tc in tr.findall(f"{{{NS['a']}}}tc")]
            rows.append(cells)
        if rows:
            out["tables"].append(rows)

    # Imagenes (solo inventario y alt-text)
    for pic in root.iter(f"{{{NS['p']}}}pic"):
        nv = pic.find(f".//{{{NS['p']}}}cNvPr")
        if nv is not None:
            out["images"].append((nv.get("name", ""), nv.get("descr", "")))
    return out


def parse_notes(xml: bytes) -> str:
    root = etree.fromstring(xml)
    parts = [text_of(sp) for sp in root.iter(f"{{{NS['p']}}}sp")]
    return " ".join(p for p in parts if p).strip()


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    pattern = None
    if "--grep" in sys.argv:
        pattern = sys.argv[sys.argv.index("--grep") + 1]

    zf = zipfile.ZipFile(src)
    names = zf.namelist()
    slides = sorted([n for n in names if re.match(r"ppt/slides/slide\d+\.xml$", n)], key=slide_key)
    notes = {n: slide_key(n) for n in names if re.match(r"ppt/notesSlides/notesSlide\d+\.xml$", n)}
    media = [n for n in names if n.startswith("ppt/media/")]

    dst.parent.mkdir(parents=True, exist_ok=True)
    total_chars = 0
    with dst.open("w", encoding="utf-8") as out:
        out.write(f"# Extraccion de: {src.name}\n")
        out.write(f"# slides={len(slides)}  media={len(media)}  hojas_de_notas={len(notes)}\n\n")
        for s in slides:
            idx = slide_key(s)
            data = parse_slide(zf.read(s))
            out.write(f"\n{'=' * 78}\n### SLIDE {idx}\n{'=' * 78}\n")
            for label, txt in data["texts"]:
                out.write(f"[forma: {label or '-'}] {txt}\n")
            for i, rows in enumerate(data["tables"], 1):
                out.write(f"[tabla {i}]\n")
                for row in rows:
                    out.write("   | " + " | ".join(row) + "\n")
            for nm, descr in data["images"]:
                if descr:
                    out.write(f"[imagen: {nm}] descr: {descr}\n")
            total_chars += sum(len(t) for _, t in data["texts"])

        out.write("\n\n" + "=" * 78 + "\n### NOTAS DEL ORADOR\n" + "=" * 78 + "\n")
        for n in sorted(notes, key=lambda x: notes[x]):
            t = parse_notes(zf.read(n))
            if t:
                out.write(f"\n--- notas slide {notes[n]} ---\n{t}\n")

        out.write("\n\n" + "=" * 78 + "\n### INVENTARIO DE MEDIA (no extraido)\n" + "=" * 78 + "\n")
        for m in sorted(media):
            out.write(f"{m}  {zf.getinfo(m).file_size} bytes\n")

    print(f"OK -> {dst}")
    print(f"slides={len(slides)}  media={len(media)}  caracteres_de_texto={total_chars}")

    if pattern:
        rx = re.compile(pattern, re.IGNORECASE)
        print(f"\n--- coincidencias de /{pattern}/ ---")
        for i, line in enumerate(dst.read_text(encoding="utf-8").splitlines(), 1):
            if rx.search(line):
                print(f"{i}: {line[:300]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
