"""
Extrae la geometria de los diagramas rotulados de un PPTX: posicion y tamano de cada forma.

POR QUE:
  La slide 09 del deck 01 tiene un diagrama rotulado ("Helice", "Boquilla centrifuga",
  "Motor", "ESC", "Radar LiDAR", "Deposito de liquidos", "Bomba"...). Verificacion: los
  rotulos NO estan dentro del objeto grafico (el .emf resulto ser un mapa de bits envuelto
  en un metafile, sin trazados vectoriales), sino que son CUADROS DE TEXTO de PowerPoint
  superpuestos a una imagen. Por tanto la via correcta no es renderizar el metafile, sino
  leer el XML: cada forma trae su transformacion en EMU (914400 EMU = 1 pulgada), que es
  un dato EXACTO del archivo, no una estimacion.

QUE PRODUCE:
  - posicion y tamano de cada forma, normalizados al lienzo de la diapositiva
  - para las formas de texto: el rotulo y a que fraccion de ancho/alto cae
  - un CSV y un JSON con todo, para leer POSICIONES RELATIVAS de forma reproducible

ADVERTENCIA DE RIGOR (context.md SS51; protocolo SS1):
  Esto sigue siendo clasificacion **S** (evidencia documental visual). Da posiciones
  RELATIVAS y topologia. NO da milimetros: para eso hace falta una dimension de referencia
  fiable dentro de la misma vista, y esta geometria describe la composicion grafica de una
  lamina, no el objeto fisico. Nada de aqui sube a **M** sin calibracion independiente.

Uso:
  python scripts/extract_pptx_shape_geometry.py
"""
from __future__ import annotations

import csv
import json
import re
import zipfile
from pathlib import Path

from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = Path(r"C:\Users\Dimasur\OneDrive\Documents\DJI\Entrega de drones DJI\DJI ACADEMY COMPLETO")
OUT_DIR = ROOT / "data" / "processed" / "shape_geometry"

DECKS = {
    "01a_conocimiento_basico": "01 Conocimiento básico de un Dron (1).pptx",
    "02_planificacion_mision": "02 Planificación de Misión y Modos de Operación en drones DJI AGRAS.pptx",
    "03_parametros_aplicacion": "03 Recomendaciones para la Configuración de Parámetros  de aplicación en drones DJI AGRAS.pptx",
}

# Diapositivas de interes: diagramas con rotulos de componentes
SLIDES_OBJETIVO = {
    "01a_conocimiento_basico": [9, 10, 11, 12, 44, 45],
}

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}

EMU_PER_INCH = 914400


def texto(sp) -> str:
    ts = [t for t in sp.itertext() if t and t.strip()]
    return " ".join(ts).strip()


def extraer_slide(xml: bytes) -> tuple[tuple[int, int], list[dict]]:
    root = etree.fromstring(xml)
    sldSz = root.find(f".//{{{NS['p']}}}sldSz")
    cx = int(sldSz.get("cx")) if sldSz is not None else 12192000
    cy = int(sldSz.get("cy")) if sldSz is not None else 6858000

    formas = []
    for sp in root.iter(f"{{{NS['p']}}}sp"):
        xfrm = sp.find(f".//{{{NS['a']}}}xfrm")
        nv = sp.find(f".//{{{NS['p']}}}cNvPr")
        if xfrm is None:
            continue
        off = xfrm.find(f"{{{NS['a']}}}off")
        ext = xfrm.find(f"{{{NS['a']}}}ext")
        if off is None or ext is None:
            continue
        x, y = int(off.get("x")), int(off.get("y"))
        w, h = int(ext.get("cx")), int(ext.get("cy"))
        formas.append({
            "tipo": "texto" if texto(sp) else "forma",
            "nombre": nv.get("name") if nv is not None else "",
            "etiqueta": texto(sp),
            "x_norm": round(x / cx, 4), "y_norm": round(y / cy, 4),
            "w_norm": round(w / cx, 4), "h_norm": round(h / cy, 4),
            "cx_norm": round((x + w / 2) / cx, 4), "cy_norm": round((y + h / 2) / cy, 4),
        })
    # imagenes
    for pic in root.iter(f"{{{NS['p']}}}pic"):
        xfrm = pic.find(f".//{{{NS['a']}}}xfrm")
        nv = pic.find(f".//{{{NS['p']}}}cNvPr")
        if xfrm is None:
            continue
        off, ext = xfrm.find(f"{{{NS['a']}}}off"), xfrm.find(f"{{{NS['a']}}}ext")
        if off is None or ext is None:
            continue
        x, y = int(off.get("x")), int(off.get("y"))
        w, h = int(ext.get("cx")), int(ext.get("cy"))
        formas.append({
            "tipo": "imagen",
            "nombre": nv.get("name") if nv is not None else "",
            "etiqueta": "",
            "x_norm": round(x / cx, 4), "y_norm": round(y / cy, 4),
            "w_norm": round(w / cx, 4), "h_norm": round(h / cy, 4),
            "cx_norm": round((x + w / 2) / cx, 4), "cy_norm": round((y + h / 2) / cy, 4),
        })

    # conectores / lineas guia: dan el mapeo rotulo -> componente senalado
    for cxn in root.iter(f"{{{NS['p']}}}cxnSp"):
        xfrm = cxn.find(f".//{{{NS['a']}}}xfrm")
        nv = cxn.find(f".//{{{NS['p']}}}cNvPr")
        if xfrm is None:
            continue
        off, ext = xfrm.find(f"{{{NS['a']}}}off"), xfrm.find(f"{{{NS['a']}}}ext")
        if off is None or ext is None:
            continue
        x, y = int(off.get("x")), int(off.get("y"))
        w, h = int(ext.get("cx")), int(ext.get("cy"))
        flipH = xfrm.get("flipH") == "1"
        flipV = xfrm.get("flipV") == "1"
        # extremos del conector en coordenadas normalizadas
        x1, y1 = x, y
        x2, y2 = x + w, y + h
        if flipH:
            x1, x2 = x2, x1
        if flipV:
            y1, y2 = y2, y1
        formas.append({
            "tipo": "conector",
            "nombre": nv.get("name") if nv is not None else "",
            "etiqueta": "",
            "x_norm": round(x / cx, 4), "y_norm": round(y / cy, 4),
            "w_norm": round(w / cx, 4), "h_norm": round(h / cy, 4),
            "cx_norm": round((x + w / 2) / cx, 4), "cy_norm": round((y + h / 2) / cy, 4),
            "ini_x_norm": round(x1 / cx, 4), "ini_y_norm": round(y1 / cy, 4),
            "fin_x_norm": round(x2 / cx, 4), "fin_y_norm": round(y2 / cy, 4),
        })
    return (cx, cy), formas


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    todas = []
    for deck, fname in DECKS.items():
        src = SRC_DIR / fname
        if not src.exists():
            print(f"[{deck}] AUSENTE")
            continue
        zf = zipfile.ZipFile(src)
        objetivo = SLIDES_OBJETIVO.get(deck)
        nombres = sorted(
            [n for n in zf.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n)],
            key=lambda n: int(re.search(r"slide(\d+)\.xml", n).group(1)),
        )
        for n in nombres:
            num = int(re.search(r"slide(\d+)\.xml", n).group(1))
            if objetivo and num not in objetivo:
                continue
            (cx, cy), formas = extraer_slide(zf.read(n))
            if not formas:
                continue
            rotulos = [f for f in formas if f["etiqueta"]]
            print(f"\n=== {deck} · slide {num} ===  ({len(formas)} formas, {len(rotulos)} rotuladas)")
            for f in rotulos:
                print(f"    x={f['x_norm']:.3f} y={f['y_norm']:.3f}  "
                      f"[{f['nombre']}]  {f['etiqueta'][:70]}")
            for f in formas:
                d = dict(f)
                d["deck"] = deck
                d["slide"] = num
                todas.append(d)

    if todas:
        cols = ["deck", "slide", "tipo", "nombre", "etiqueta",
                "x_norm", "y_norm", "w_norm", "h_norm", "cx_norm", "cy_norm",
                "ini_x_norm", "ini_y_norm", "fin_x_norm", "fin_y_norm"]
        csv_path = OUT_DIR / "shape_geometry.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            for r in todas:
                w.writerow(r)
        json_path = OUT_DIR / "shape_geometry.json"
        json_path.write_text(json.dumps(todas, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n{len(todas)} formas -> {csv_path.relative_to(ROOT)}")
        print(f"                 -> {json_path.relative_to(ROOT)}")

        # interpretacion rotulo -> componente, por cercania de la linea guia
        print("\n=== Mapeo rotulo -> componente senalado (por conector mas cercano) ===")
        for r in todas:
            if r["slide"] != 9 or r["deck"] != "01a_conocimiento_basico":
                continue
            rot = [x for x in todas if x["slide"] == 9 and x["tipo"] == "texto" and x["etiqueta"]]
            con = [x for x in todas if x["slide"] == 9 and x["tipo"] == "conector"]
            if not rot or not con:
                continue
            print(f"  conectores en la slide: {len(con)}  rotulos: {len(rot)}")
            for t in rot:
                # conector cuyo extremo "ini" cae mas cerca del rotulo
                mejor, dmin = None, 9e9
                for c in con:
                    d = ((c["ini_x_norm"] - t["x_norm"]) ** 2 + (c["ini_y_norm"] - t["y_norm"]) ** 2) ** 0.5
                    if d < dmin:
                        mejor, dmin = c, d
                if mejor and dmin < 0.12:
                    print(f"    {t['etiqueta'][:46]:48s} rotulo=({t['x_norm']:.3f},{t['y_norm']:.3f})"
                          f"  ->  componente=({mejor['fin_x_norm']:.3f},{mejor['fin_y_norm']:.3f})")
            break
    print("\nRECORDATORIO: clasificacion S. Posiciones RELATIVAS de la composicion grafica,")
    print("no dimensiones fisicas. Para milimetros hace falta una referencia fiable en la vista.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
