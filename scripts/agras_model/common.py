"""
Nucleo comun (Python puro, sin numpy) del modelo CFD de los DJI Agras.

Lo usan:
  - build_freecad.py  (interprete de FreeCAD) para construir los solidos;
  - export_metadata.py (Python del sistema) para el JSON y las figuras.

SISTEMA DE COORDENADAS (mano derecha, X x Y = Z), comun a todas las plataformas:
  origen XY = centroide de los ejes de motor (bujes); origen Z = plano de raiz de los brazos
  +X adelante (radar / FPV) | +Y IZQUIERDA (babor) | +Z arriba | unidades: metros.

PRIMITIVAS (diccionarios, coordenadas en metros):
  {"k": "box",  "x": (x0, x1), "y": (y0, y1), "z": (z0, z1), "fillet": r | 0, "chamfer": r | 0}
  {"k": "loft", "sections": [{"x": (x0, x1), "y": hy, "z": z}, ...]}   rectangulos simetricos en Y
  {"k": "cyl",  "c": (x, y, z) centro de la base, "axis": (ax, ay, az), "dia": d, "len": L}
  {"k": "tube", "p0": (...), "p1": (...), "dia": d, "caps": bool}
  {"k": "sphere", "c": (...), "dia": d}
  {"k": "obox", "c": (...), "dir": (...), "L": l, "W": w, "H": h}   caja orientada segun dir
INCLINACION (cant) del grupo motor/atomizador, rigida, alrededor del pivote (union brazo-motor):
  lateral c_lat (giro en X)  y longitudinal c_lon (giro en Y); c > 0 = parte ALTA del eje hacia FUERA.
"""
from __future__ import annotations

import math


# ----------------------------------------------------------------------------------
# primitivas
# ----------------------------------------------------------------------------------
def box(x, y, z, fillet=0.0, chamfer=0.0, vchamfer=0.0):
    return {"k": "box", "x": tuple(x), "y": tuple(y), "z": tuple(z), "fillet": fillet, "chamfer": chamfer,
            "vchamfer": vchamfer}


def boxc(cx, cy, cz, lx, ly, lz, **kw):
    return box((cx - lx / 2, cx + lx / 2), (cy - ly / 2, cy + ly / 2), (cz - lz / 2, cz + lz / 2), **kw)


def cylz(x, y, dia, z0, z1):
    return {"k": "cyl", "c": (x, y, min(z0, z1)), "axis": (0.0, 0.0, 1.0), "dia": dia, "len": abs(z1 - z0)}


def cyl(c, axis, dia, length):
    return {"k": "cyl", "c": tuple(c), "axis": tuple(axis), "dia": dia, "len": length}


def tube(p0, p1, dia, caps=True):
    return {"k": "tube", "p0": tuple(p0), "p1": tuple(p1), "dia": dia, "caps": caps}


def sphere(c, dia):
    return {"k": "sphere", "c": tuple(c), "dia": dia}


def loft(sections):
    return {"k": "loft", "sections": [dict(s) for s in sections]}


def obox(c, direction, L, W, H):
    return {"k": "obox", "c": tuple(c), "dir": tuple(direction), "L": L, "W": W, "H": H}


def translate(prim, d):
    """Copia de la primitiva desplazada d (para grupos definidos en coordenadas locales)."""
    p = dict(prim)
    k = p["k"]
    if k == "box":
        p["x"] = (p["x"][0] + d[0], p["x"][1] + d[0])
        p["y"] = (p["y"][0] + d[1], p["y"][1] + d[1])
        p["z"] = (p["z"][0] + d[2], p["z"][1] + d[2])
    elif k in ("cyl", "sphere", "obox"):
        p["c"] = tuple(p["c"][i] + d[i] for i in range(3))
    elif k == "tube":
        p["p0"] = tuple(p["p0"][i] + d[i] for i in range(3))
        p["p1"] = tuple(p["p1"][i] + d[i] for i in range(3))
    elif k == "loft":
        p["sections"] = [{"x": (s["x"][0] + d[0], s["x"][1] + d[0]), "y": s["y"], "z": s["z"] + d[2]}
                         for s in p["sections"]]
        if d[1]:
            raise ValueError("loft solo admite desplazamiento en X/Z")
    return p


# ----------------------------------------------------------------------------------
# inclinacion rigida (motor perpendicular al tubo del brazo)
# ----------------------------------------------------------------------------------
def arm_axis(u):
    """Eje horizontal perpendicular al brazo (z x u). Girar +c alrededor de el lleva la parte alta
    del eje del motor hacia +u (hacia FUERA a lo largo del brazo)."""
    return (-u[1], u[0], 0.0)


def rotate_point(p, pivot, axis, ang_deg):
    """Rodrigues: gira p alrededor del eje (unitario) que pasa por pivot."""
    if not ang_deg:
        return tuple(p)
    a = math.radians(ang_deg)
    k = axis
    v = (p[0] - pivot[0], p[1] - pivot[1], p[2] - pivot[2])
    c, s_ = math.cos(a), math.sin(a)
    kxv = (k[1] * v[2] - k[2] * v[1], k[2] * v[0] - k[0] * v[2], k[0] * v[1] - k[1] * v[0])
    kv = k[0] * v[0] + k[1] * v[1] + k[2] * v[2]
    r = tuple(v[i] * c + kxv[i] * s_ + k[i] * kv * (1 - c) for i in range(3))
    return (r[0] + pivot[0], r[1] + pivot[1], r[2] + pivot[2])


def rotate_vec(v, axis, ang_deg):
    return rotate_point(v, (0.0, 0.0, 0.0), axis, ang_deg)


# ----------------------------------------------------------------------------------
# plataforma: resolucion de pivotes y posiciones derivadas
# ----------------------------------------------------------------------------------
class Platform:
    """Envuelve un modulo de parametros de plataforma y deriva todo lo calculado.
    Inclinacion: MOTOR_CANT_DEG a lo largo del brazo (+ = parte alta hacia fuera), rigida alrededor
    de la union brazo-motor; el atomizador montado en el grupo la hereda y puede sumar 'own_cant_deg'."""

    def __init__(self, mod):
        self.m = mod
        self.arms = {a["id"]: dict(a) for a in mod.ARMS}
        self.rotors = [dict(r) for r in mod.ROTORS]
        for a in self.arms.values():
            dx, dy = a["hub_x"] - a["root"][0], a["hub_y"] - a["root"][1]
            L = math.hypot(dx, dy)
            a["u"] = (dx / L, dy / L, 0.0)
            a["k"] = arm_axis(a["u"])
        self._solve_pivots()

    def cant(self, arm_id):
        return self.arms[arm_id]["k"], self.m.MOTOR_CANT_DEG

    def pivot(self, arm_id):
        a = self.arms[arm_id]
        return (a["x"], a["y"], self.m.ARM_TIP_Z)

    def tilt(self, arm_id, p):
        k, c = self.cant(arm_id)
        return rotate_point(p, self.pivot(arm_id), k, c)

    def axis(self, arm_id):
        k, c = self.cant(arm_id)
        return rotate_vec((0.0, 0.0, 1.0), k, c)

    def components(self, arm_id):
        """(lateral, longitudinal) en grados, convencion + = parte alta hacia fuera."""
        n = self.axis(arm_id)
        a = self.arms[arm_id]
        sy = 1.0 if a["hub_y"] > 0 else -1.0
        sx = 1.0 if a["hub_x"] > 0 else -1.0
        return math.degrees(math.atan2(n[1] * sy, n[2])), math.degrees(math.atan2(n[0] * sx, n[2]))

    def _solve_pivots(self):
        """Los bujes medidos en planta (hub_x, hub_y) estan en el plano de la helice de referencia;
        el pivote (x, y del brazo) se resuelve para que el buje inclinado caiga ahi."""
        for a in self.arms.values():
            a["x"], a["y"] = a["hub_x"], a["hub_y"]
            for _ in range(8):
                c = self.tilt(a["id"], (a["x"], a["y"], a["hub_ref_z"]))
                a["x"] += a["hub_x"] - c[0]
                a["y"] += a["hub_y"] - c[1]

    # --- rotores
    def rotor_center(self, r):
        a = self.arms[r["arm"]]
        return self.tilt(r["arm"], (a["x"], a["y"], r["plane_z"]))

    def rotor_axis(self, r):
        return self.axis(r["arm"])

    # --- atomizadores
    def _nozzle_tilt(self, n, p):
        """Inclinacion propia (alrededor del punto de enganche) y luego la del grupo motor."""
        own = n.get("own_cant_deg", 0.0)
        if n["mount"] == "arm":
            k = self.arms[n["arm"]]["k"]
            if own:
                p = rotate_point(p, n["_attach"], k, own)
            return self.tilt(n["arm"], p)
        if own:
            p = rotate_point(p, n["_attach"], n["own_axis"], own)
        return p

    def _attach(self, n, disc_untilted):
        z = self.m.ATOMIZER_ATTACH_Z if n["mount"] == "arm" else n["attach_z"]
        return (disc_untilted[0], disc_untilted[1], z)

    def nozzle_untilted(self, n):
        """Centro del disco SIN inclinar tal que, inclinado, quede en (n.x, n.y, n.disc_z)."""
        p = (n["x"], n["y"], n["disc_z"])
        for _ in range(10):
            n["_attach"] = self._attach(n, p)
            q = self._nozzle_tilt(n, p)
            p = (p[0] + n["x"] - q[0], p[1] + n["y"] - q[1], p[2] + n["disc_z"] - q[2])
        n["_attach"] = self._attach(n, p)
        return p

    def nozzle_center(self, n):
        u = self.nozzle_untilted(n)
        return self._nozzle_tilt(n, u)

    def nozzle_axis(self, n):
        own = n.get("own_cant_deg", 0.0)
        v = (0.0, 0.0, 1.0)
        if n["mount"] == "arm":
            k = self.arms[n["arm"]]["k"]
            v = rotate_vec(v, k, own)
            return rotate_vec(v, *self.cant(n["arm"]))
        return rotate_vec(v, n.get("own_axis", (1.0, 0.0, 0.0)), own)


# ----------------------------------------------------------------------------------
# grupos tipicos (coordenadas LOCALES respecto al pivote, sin inclinar)
# ----------------------------------------------------------------------------------
def single_motor_group(pivot_z, mount_box, mount_z, bell_dia, bell_z, clamp_dia, disk_bottom_z):
    """Motor simple: caja de montaje bajo el motor, campana, pedestal de abrazadera."""
    mx, my = mount_box
    return [
        box((-mx / 2, mx / 2), (-my / 2, my / 2), (mount_z[0] - pivot_z, mount_z[1] - pivot_z), fillet=0.015),
        cylz(0, 0, bell_dia, bell_z[0] - pivot_z, bell_z[1] - pivot_z),
        cylz(0, 0, clamp_dia, bell_z[1] - pivot_z - 0.005, disk_bottom_z - pivot_z - 0.002),
    ]


def coaxial_motor_group(pivot_z, mount_box, mount_z, bell_dia, upper_bell_z, lower_bell_z, clamp_dia,
                        upper_disk_bottom_z, lower_disk_top_z):
    """Par coaxial: bloque central, motor superior hacia arriba y motor inferior hacia abajo."""
    mx, my = mount_box
    return [
        box((-mx / 2, mx / 2), (-my / 2, my / 2), (mount_z[0] - pivot_z, mount_z[1] - pivot_z), fillet=0.015),
        cylz(0, 0, bell_dia, upper_bell_z[0] - pivot_z, upper_bell_z[1] - pivot_z),
        cylz(0, 0, bell_dia, lower_bell_z[0] - pivot_z, lower_bell_z[1] - pivot_z),
        cylz(0, 0, clamp_dia, upper_bell_z[1] - pivot_z - 0.005, upper_disk_bottom_z - pivot_z - 0.002),
        cylz(0, 0, clamp_dia, lower_disk_top_z - pivot_z + 0.002, lower_bell_z[0] - pivot_z + 0.005),
    ]


def hanging_atomizer(local_disc, attach_z_local, dims, bracket_from=(0.0, 0.0)):
    """Atomizador colgante en coordenadas locales del pivote.
    local_disc = (dx, dy, dz) del centro del disco; attach_z_local = Z local donde engancha al grupo.
    dims = {"stem_dia", "ring_dia", "bell_dia", "bell_h", "ring_h"}"""
    dx, dy, dz = local_disc
    hw = max(0.045, dims["stem_dia"] / 2 + 0.012)
    bx0, by0 = bracket_from
    out = [box((min(dx, bx0) - hw, max(dx, bx0) + hw), (min(dy, by0) - hw, max(dy, by0) + hw),
               (attach_z_local - 0.01, attach_z_local + 0.04))]
    bell_bot = dz - 0.015
    bell_top = bell_bot + dims["bell_h"]
    ring_top = bell_top + dims["ring_h"]
    out += [cylz(dx, dy, dims["stem_dia"], ring_top, attach_z_local + 0.01),
            cylz(dx, dy, dims["ring_dia"], bell_top, ring_top),
            cylz(dx, dy, dims["bell_dia"], bell_bot, bell_top + 0.001)]
    return out


def u_gear(skid_y, skid_x, skid_z, tube_dia, leg_top_y, rear_leg, front_leg, rail_y,
           crossbar_z=None, end_rise=0.07):
    """Tren de dos marcos en U (patin + 2 patas + soportes). Diametros escalonados para que las
    esferas de union nunca sean tangentes/coincidentes (booleanas robustas)."""
    d = tube_dia
    out = []
    for s in (+1, -1):
        yb, yt = s * skid_y, s * leg_top_y
        xr, xf = skid_x
        pts = [(xr - 0.02, yb, skid_z + end_rise), (xr + 0.03, yb, skid_z), (xf - 0.03, yb, skid_z),
               (xf + 0.02, yb, skid_z + end_rise)]
        for a, b in zip(pts[:-1], pts[1:]):
            out.append(tube(a, b, d))
        dl, ds = 0.94 * d, 0.88 * d
        for leg in (rear_leg, front_leg):
            out.append(tube((leg["bottom_x"], yb, skid_z), (leg["top_x"], yt, leg["top_z"]), dl))
            out.append(tube((leg["top_x"], yt, leg["top_z"]), (leg["top_x"], s * rail_y, 0.0), ds))
    if crossbar_z is not None:
        f = (crossbar_z - skid_z) / (rear_leg["top_z"] - skid_z)
        xc = rear_leg["bottom_x"] + f * (rear_leg["top_x"] - rear_leg["bottom_x"])
        yc = skid_y + f * (leg_top_y - skid_y)
        out.append(tube((xc, -yc, crossbar_z), (xc, yc, crossbar_z), 0.80 * d, caps=False))
    return out


def arm_parts(root, tip, dia, esc_box, esc_at, fold_sleeve, fold_at):
    """Tubo de brazo + caja ESC + manguito de plegado."""
    out = [tube(root, tip, dia)]
    d = tuple(tip[i] - root[i] for i in range(3))
    L = math.sqrt(sum(v * v for v in d))
    u = tuple(v / L for v in d)
    at = lambda f: tuple(root[i] + f * d[i] for i in range(3))  # noqa: E731
    if esc_box:
        el, ew, eh = esc_box
        c = at(esc_at)
        out.append(obox((c[0], c[1], c[2] + dia / 2 + eh / 2 - 0.01), d, el, ew, eh))
    if fold_sleeve:
        fd, fl = fold_sleeve
        c = at(fold_at)
        out.append(tube(tuple(c[i] - u[i] * fl / 2 for i in range(3)),
                        tuple(c[i] + u[i] * fl / 2 for i in range(3)), fd, caps=False))
    return out


# ----------------------------------------------------------------------------------
# pala
# ----------------------------------------------------------------------------------
def interp(table, x):
    if x <= table[0][0]:
        return table[0][1]
    for (x0, y0), (x1, y1) in zip(table[:-1], table[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return table[-1][1]


def blade_beta_deg(r_over_R, radius, pitch, clamp_rr=0.20):
    r = max(r_over_R, clamp_rr) * radius
    return math.degrees(math.atan(pitch / (2 * math.pi * r)))
