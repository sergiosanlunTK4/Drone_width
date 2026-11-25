"""Hoja de contactos de una carpeta de imagenes: python contact.py <carpeta_img> <salida_prefijo> [excluir_carpeta ...]"""
import os, sys
from PIL import Image, ImageDraw
src, out, excl = sys.argv[1], sys.argv[2], sys.argv[3:]
skip = set(f for d in excl if os.path.isdir(d) for f in os.listdir(d))
fs = [f for f in sorted(os.listdir(src)) if f not in skip]
tiles = []
for i, f in enumerate(fs):
    try:
        im = Image.open(os.path.join(src, f)).convert('RGB'); w, h = im.size
    except Exception:
        continue
    if w < 400 or h < 300:
        continue
    im.thumbnail((240, 160)); t = Image.new('RGB', (240, 180), 'white'); t.paste(im, (0, 0))
    ImageDraw.Draw(t).text((2, 164), f'{f[:8]} {w}x{h}', fill=(255, 0, 0)); tiles.append(t)
cols = 8
for k in range(0, len(tiles), 48):
    sub = tiles[k:k + 48]; rows = (len(sub) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * 240, rows * 180), 'white')
    for j, t in enumerate(sub): sheet.paste(t, ((j % cols) * 240, (j // cols) * 180))
    sheet.save(f'{out}_{k // 48}.png')
print(len(tiles), 'imagenes')
