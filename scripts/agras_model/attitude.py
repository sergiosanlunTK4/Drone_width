"""
Modelo E de ACTITUD (cabeceo) theta(V, f) para las 4 plataformas — aprobado por el propietario
el 2026-11-23 a falta de telemetria de cabeceo (que, si llega, lo sustituye: clase O).

Equilibrio en vuelo horizontal uniforme, sin viento (V_aire = V), mismo modelo que
`scripts/force_chain.py::actitud` (version explicita, area constante):

    tan(theta) = D / W ,   D = 0.5 * rho * Cd * A_frontal * V^2 ,   W = m(f) * g

Entradas y clase:
    m(f)       masa de la plataforma con fraccion de tanque f      (P/O, cfd_geometry)
    A_frontal  proyeccion del fuselaje `<p>_airframe.stl` sobre el plano Y-Z, rasterizada a
               5 mm. Clase I (derivada del modelo geometrico, no medida). NO incluye palas ni el flujo de
               los rotores; el STL es el mismo que ve snappyHexMesh.
    Cd         0.8 (clase E: fuselaje romo con tanque y tren). Sin medida ni fuente primaria.
    rho        1.1716 kg/m3 (28 C, nivel del mar), la misma del CFD.

Suposiciones declaradas (todas sesgan theta hacia ABAJO o son de signo desconocido):
    - sin H-force de las helices ni arrastre del flujo inducido (subestima theta);
    - Cd y A constantes con theta (ver la advertencia de force_chain sobre A_proj(theta));
    - pivote del cabeceo en el origen del modelo (CG real: D).
Sensibilidad: `theta(..., cd=...)` con Cd 0.6 y 1.0 para el analisis del paper.

Uso:
    python scripts/agras_model/attitude.py           # tabla theta(V, f) por plataforma
"""
from __future__ import annotations

import math
import struct
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfd_geometry import cargar  # noqa: E402

G = 9.80665
RHO = 1.1716
CD_E = 0.8
CD_SENS = (0.6, 1.0)
RES_M = 0.005
CLASE = "E"
FUENTE = ("modelo E aprobado 2026-11-23: tan(theta)=0.5 rho Cd A V^2/(m g); "
          "Cd=0.8 (E), A_frontal del STL proyectado en Y-Z (I)")


def _triangulos_stl(ruta: Path) -> np.ndarray:
    datos = ruta.read_bytes()
    n = struct.unpack("<I", datos[80:84])[0]
    reg = np.frombuffer(datos[84:84 + 50 * n], dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")]))
    return reg["v"].reshape(n, 3, 3).astype(float)


@lru_cache(maxsize=None)
def area_frontal_m2(clave: str, res: float = RES_M) -> float:
    """Area de la sombra del fuselaje vista desde +X (proyeccion sobre Y-Z), por rasterizado."""
    tri = _triangulos_stl(cargar(clave).stl_airframe)[:, :, 1:]      # (y, z)
    lo, hi = tri.reshape(-1, 2).min(0), tri.reshape(-1, 2).max(0)
    ny, nz = int(math.ceil((hi[0] - lo[0]) / res)) + 1, int(math.ceil((hi[1] - lo[1]) / res)) + 1
    malla = np.zeros((ny, nz), dtype=bool)
    for t in tri:
        a, b, c = t
        den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(den) < 1e-14:
            continue
        i0, j0 = np.floor((t.min(0) - lo) / res).astype(int)
        i1, j1 = np.ceil((t.max(0) - lo) / res).astype(int)
        ii, jj = np.meshgrid(np.arange(i0, i1 + 1), np.arange(j0, j1 + 1), indexing="ij")
        y, z = lo[0] + (ii + 0.5) * res, lo[1] + (jj + 0.5) * res
        l1 = ((b[1] - c[1]) * (y - c[0]) + (c[0] - b[0]) * (z - c[1])) / den
        l2 = ((c[1] - a[1]) * (y - c[0]) + (a[0] - c[0]) * (z - c[1])) / den
        dentro = (l1 >= 0) & (l2 >= 0) & (l1 + l2 <= 1)
        ii, jj = ii[dentro], jj[dentro]
        ok = (ii < ny) & (jj < nz)
        malla[ii[ok], jj[ok]] = True
    return float(malla.sum()) * res * res


def theta_deg(clave: str, V: float, f: float, cd: float = CD_E) -> float:
    if V <= 0:
        return 0.0
    p = cargar(clave)
    D = 0.5 * RHO * cd * area_frontal_m2(clave) * V * V
    return math.degrees(math.atan2(D, p.masa(f) * G))


def main() -> int:
    vs = (2, 5, 8, 12, 16, 20)
    for clave in ("T25P", "T55", "T70P", "T100"):
        p = cargar(clave)
        A = area_frontal_m2(clave)
        print(f"\n{clave}: A_frontal = {A:.3f} m2 (I, STL)   Cd = {CD_E} (E)   "
              f"m(1) = {p.masa(1):.1f} kg  m(0) = {p.masa(0):.1f} kg")
        print("   V  " + "".join(f"{v:>8d}" for v in vs))
        for f in (1.0, 0.0):
            print(f"  f={f:.0f} " + "".join(f"{theta_deg(clave, v, f):8.2f}" for v in vs))
        print("  sens. Cd 0.6/1.0 a 20 m/s, f=0: "
              + " / ".join(f"{theta_deg(clave, 20, 0, c):.2f}" for c in CD_SENS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
