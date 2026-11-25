"""
Medicion fotogrametrica de la inclinacion (cant) de los ejes motor + atomizador (clase S).

    python scripts/agras_model/fotogrametria/medir_inclinacion.py <plataforma|all>

Salida: geometry/models/<P>_CFD/mediciones/mediciones_inclinacion_<p>.csv

METODO VALIDO: columna rigida motor-atomizador (o motor/montaje) con bordes limpios contra fondo claro,
ajuste lineal x(y) del/los borde(s), corregido por la vertical del cuerpo (bordes del cilindro del
radar en la misma imagen). Convencion: + = parte ALTA del eje hacia FUERA del dron.
  - vista trasera/frontal -> componente LATERAL; vista lateral -> componente LONGITUDINAL.
  - T70P_REAR: camara estimada a ~5.75 m, focal ~2350 px, cabeceo < 1 grado -> convergencia de
    verticales ~0.1 grados (despreciable). Para otras vistas se comprueba la simetria izq./dcha.
METODOS DESCARTADOS (no repetir):
  - pendiente del borde de la campana del motor: tapada por brazo/ESC, la curvatura de la elipse se
    confunde con inclinacion (de -7 a +2 grados segun criterio);
  - fotos en vuelo: la actitud contamina la medida.
"""
from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
G = ROOT / "geometry" / "models"


def gray(path):
    return np.asarray(Image.open(path).convert("L")).astype(float)


def fit_line(xs, ys, clip=2.5, iters=4):
    """Minimos cuadrados con rechazo iterativo de atipicos (|r| > clip*sigma): una pala o un tornillo
    que cruza la ventana no arrastra el ajuste. Devuelve (m, b, error tipico de m)."""
    xs, ys = np.asarray(xs, float), np.asarray(ys, float)
    keep = np.ones(len(xs), bool)
    for _ in range(iters):
        A = np.vstack([xs[keep], np.ones(keep.sum())]).T
        (m, b), *_ = np.linalg.lstsq(A, ys[keep], rcond=None)
        r = ys - (m * xs + b)
        sig = max(1e-6, float(np.std(r[keep])))
        new = np.abs(r) <= clip * sig
        if new.sum() < 6 or (new == keep).all():
            break
        keep = new
    r = ys[keep] - (m * xs[keep] + b)
    xk = xs[keep]
    se = math.sqrt((r @ r) / max(1, len(xk) - 2) / max(1e-9, ((xk - xk.mean()) ** 2).sum()))
    return m, b, se


def deg(m):
    return math.degrees(math.atan(m))


def _subpix(row, i_out, i_in, thr):
    """Posicion subpixel del cruce del umbral entre el pixel claro i_out y el oscuro i_in."""
    a, c = row[i_out], row[i_in]
    if a == c:
        return float(i_in)
    return i_out + (a - thr) / (a - c) * (i_in - i_out)


def _row_edges(row, thr):
    d = np.where(row < thr)[0]
    if len(d) < 3:
        return None
    l, r = d[0], d[-1]
    xl = _subpix(row, l - 1, l, thr) if l > 0 else float(l)
    xr = _subpix(row, r + 1, r, thr) if r + 1 < len(row) else float(r)
    return xl, xr


def edges_vertical(g, x0, x1, y0, y1, thr=200):
    L, R, Y = [], [], []
    for y in range(y0, y1):
        e = _row_edges(g[y, x0:x1], thr)
        if e is None:
            continue
        L.append(x0 + e[0]); R.append(x0 + e[1]); Y.append(y)
    return np.array(L, float), np.array(R, float), np.array(Y, float)


def radar_ref(g, box, thr=200):
    L, R, Y = edges_vertical(g, *box, thr=thr)
    return deg((fit_line(Y, L)[0] + fit_line(Y, R)[0]) / 2)


def inner_edge(g, x0, x1, y0, y1, side, thr=110):
    """Borde subpixel. side=-1: borde derecho de la silueta; +1: borde izquierdo."""
    xs, ys = [], []
    for y in range(y0, y1):
        e = _row_edges(g[y, x0:x1], thr)
        if e is None:
            continue
        xs.append(x0 + (e[1] if side == -1 else e[0])); ys.append(y)
    return np.array(xs, float), np.array(ys, float)


def both_edges(g, x0, x1, y0, y1, thr=100):
    Ls, Rs, Ys = [], [], []
    for y in range(y0, y1):
        row = g[y, x0:x1]
        d = np.where(row < thr)[0]
        if len(d) < 4:
            continue
        seg = max(np.split(d, np.where(np.diff(d) > 2)[0] + 1), key=len)
        l, r = seg[0], seg[-1]
        Ls.append(x0 + (_subpix(row, l - 1, l, thr) if l > 0 else l))
        Rs.append(x0 + (_subpix(row, r + 1, r, thr) if r + 1 < len(row) else r))
        Ys.append(y)
    return np.array(Ls, float), np.array(Rs, float), np.array(Ys, float)


# Cada tarea: (imagen, elemento, plano, metodo, caja (x0,x1,y0,y1), outward(+1: fuera = +x imagen), extra)
CONFIGS = {
    "t70p": {
        "refs": {"T70P_REAR.png": (500, 580, 385, 425), "T70P_RIGHT.png": (770, 820, 150, 195)},
        "dir": "T70P_CFD/T70P_reference",
        "tasks": [
            ("T70P_REAR.png", "M4_RR+N2_RR", "lateral", "inner", (150, 200, 548, 600), -1, {"side": -1}),
            ("T70P_REAR.png", "M3_RL+N1_RL", "lateral", "inner", (893, 935, 548, 600), +1, {"side": +1}),
            ("T70P_RIGHT.png", "trasero_cercano", "longitudinal", "both", (330, 375, 295, 340), -1, {}),
            ("T70P_RIGHT.png", "trasero_lejano", "longitudinal", "both", (390, 430, 300, 340), -1, {}),
        ],
    },
    # T25P: vista frontal (columnas traseras, lejanas) -> lateral; vista izquierda (frente a la izquierda) ->
    # longitudinal. Bordes exteriores descartados (manguera + estrechamiento del cuerpo del atomizador).
    "t25p": {
        "refs": {"T25P_FRONT.png": (636, 671, 280, 296, 180), "T25P_LEFT.png": (553, 594, 282, 312, 175)},
        "dir": "T25P_CFD/T25P_reference",
        "tasks": [
            ("T25P_FRONT.png", "M_RR(trasero dcho)", "lateral", "inner", (465, 495, 368, 404), -1, {"side": -1}),
            ("T25P_FRONT.png", "M_RL(trasero izdo)", "lateral", "inner", (815, 850, 368, 404), +1, {"side": +1}),
            ("T25P_LEFT.png", "trasero_A", "longitudinal", "inner", (815, 845, 352, 404), +1, {"side": +1}),
            ("T25P_LEFT.png", "trasero_B", "longitudinal", "inner", (850, 880, 352, 404), +1, {"side": +1}),
        ],
    },
    # T100: vista trasera (PNG compuesto sobre blanco). Borde EXTERIOR de las columnas coaxiales, solo en la
    # franja limpia entre las dos helices (y 252-289) para no cortar palas.
    "t100": {
        "refs": {"T100_REAR.png": (585, 636, 196, 240, 200)},
        "dir": "T100_CFD/reference",
        "tasks": [
            ("T100_REAR.png", "M_izq_imagen", "lateral", "inner", (262, 300, 252, 289), -1, {"side": +1, "thr": 150}),
            ("T100_REAR.png", "M_dcha_imagen", "lateral", "inner", (905, 945, 252, 289), +1, {"side": -1, "thr": 150}),
        ],
    },
}


def run(name):
    cfg = CONFIGS[name]
    d = G / cfg["dir"]
    refs = {img: radar_ref(gray(d / img), box[:4], *(box[4:] or (200,))) for img, box in cfg["refs"].items()}
    rows = [(img, "radar", "referencia", "vertical_cuerpo_en_imagen", r, 0.0, 0) for img, r in refs.items()]
    for img, elem, plane, method, (x0, x1, y0, y1), outward, extra in cfg["tasks"]:
        g = gray(d / img)
        if method == "inner":
            xs, ys = inner_edge(g, x0, x1, y0, y1, extra["side"], extra.get("thr", 110))
            m, _, se = fit_line(ys, xs)
            lean, unc, n = deg(m), deg(se), len(xs)
        else:
            L, R, Y = both_edges(g, x0, x1, y0, y1, extra.get("thr", 100))
            mL, _, seL = fit_line(Y, L); mR, _, seR = fit_line(Y, R)
            lean = (deg(mL) + deg(mR)) / 2
            unc, n = math.hypot(deg(seL), deg(seR)) / 2 + abs(deg(mL) - deg(mR)) / 2, len(Y)
        tilt = -(lean - refs.get(img, 0.0)) * outward
        rows.append((img, elem, "columna_motor_atomizador", f"cant_{plane}", tilt, unc, n))
    out = G / cfg["dir"].split("/")[0] / "mediciones"
    out.mkdir(parents=True, exist_ok=True)
    with open(out / f"mediciones_inclinacion_{name}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["imagen", "elemento", "tipo", "parametro", "valor_deg_positivo_alto_hacia_fuera",
                    "incertidumbre_deg", "n_puntos"])
        for r in rows:
            w.writerow([r[0], r[1], r[2], r[3], f"{r[4]:+.2f}", f"{r[5]:.2f}", r[6]])
    print(f"== {name}")
    for r in rows:
        print(f"  {r[0]:22s} {r[1]:18s} {r[3]:26s} {r[4]:+6.2f}  (+-{r[5]:.2f}, n={r[6]})")
    for plane in ("lateral", "longitudinal"):
        v = [r[4] for r in rows if r[3] == f"cant_{plane}"]
        if v:
            print(f"  {plane.upper():13s}: media {np.mean(v):+.2f}  dispersion +-{(max(v) - min(v)) / 2:.2f}  (n={len(v)})")


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    for k in (CONFIGS if arg == "all" else [arg]):
        run(k)
