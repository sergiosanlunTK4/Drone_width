"""Radio de helice en px: distancia buje -> pixel naranja mas lejano (punta) de cada pala.
python prop_radius.py img x1,y1 x2,y2 ...   (bujes)"""
import sys
import numpy as np
from PIL import Image
a = np.asarray(Image.open(sys.argv[1]).convert('RGB')).astype(int)
R, G, B = a[..., 0], a[..., 1], a[..., 2]
orange = (R > 200) & (G > 80) & (G < 190) & (B < 110) & (R - B > 120)
ys, xs = np.nonzero(orange)
hubs = [tuple(map(float, p.split(','))) for p in sys.argv[2:]]
own = np.argmin([[np.hypot(xs - hx, ys - hy)] for hx, hy in hubs], axis=0)[0]
for i, (hx, hy) in enumerate(hubs):
    sel = own == i
    d = np.hypot(xs[sel] - hx, ys[sel] - hy)
    ang = np.degrees(np.arctan2(ys[sel] - hy, xs[sel] - hx))
    out = []
    for lo in (-180, 0):  # dos palas: separar por semiplano respecto a la direccion media
        pass
    # agrupar por angulo (dos puntas opuestas)
    a0 = ang[np.argmax(d)]
    g1 = np.abs(((ang - a0 + 180) % 360) - 180) < 90
    r1, r2 = d[g1].max(), d[~g1].max() if (~g1).any() else float('nan')
    print(f'buje {i}: ({hx},{hy})  puntas {r1:.1f} / {r2:.1f} px  media {(r1+r2)/2:.1f}')
