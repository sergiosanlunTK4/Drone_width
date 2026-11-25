"""Mosaico ampliado alrededor de puntos (bujes): python hubs.py img salida.png r zoom x1,y1 x2,y2 ..."""
import sys
from PIL import Image, ImageDraw
src, out, r, z = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
pts = [tuple(map(int, a.split(','))) for a in sys.argv[5:]]
im = Image.open(src).convert('RGB'); S = 2 * r * z; tiles = []
for cx, cy in pts:
    t = im.crop((cx - r, cy - r, cx + r, cy + r)).resize((S, S), Image.LANCZOS); d = ImageDraw.Draw(t)
    for k in range(0, 2 * r + 1, 2):
        c = (255, 0, 0) if k % 10 == 0 else (255, 200, 200)
        d.line([(k * z, 0), (k * z, S)], fill=c); d.line([(0, k * z), (S, k * z)], fill=c)
    d.text((2, 2), f'{cx-r},{cy-r}', fill=(0, 0, 255)); tiles.append(t)
cols = 2; rows = (len(tiles) + 1) // 2
o = Image.new('RGB', (cols * (S + 10), rows * (S + 10)), 'white')
for i, t in enumerate(tiles): o.paste(t, ((i % 2) * (S + 10), (i // 2) * (S + 10)))
o.save(out)
