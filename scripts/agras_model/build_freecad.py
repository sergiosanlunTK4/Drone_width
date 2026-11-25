"""
Constructor generico del modelo CFD de un DJI Agras con FreeCAD (OpenCASCADE B-rep).

    set AGRAS_PLATFORM=t70p        (t25p | t55 | t70p | t100)
    "C:/Program Files/FreeCAD 1.1/bin/freecadcmd.exe" scripts/agras_model/build_freecad.py
  o, mas comodo:  python scripts/agras_model/run.py t70p      (construye + post-proceso)

Salidas en geometry/models/<PLATAFORMA>_CFD/ (prefijo = plataforma en minusculas):
    <p>_model.FCStd, <p>_airframe.step/.stl/_ascii.stl, <p>_rotor_disks.stl (solids nombrados),
    <p>_rotor_blades.step/.stl, <p>_spray_nozzles.stl (solids nombrados), <p>_full_assembly.step/.stl,
    _build_report.json
STL en METROS; STEP en milimetros.
"""
import importlib
import json
import math
import os
import struct
import sys

import FreeCAD as App
import Part
import MeshPart
from FreeCAD import Vector, Rotation, Placement

HERE = os.environ.get("AGRAS_SCRIPT_DIR") or os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as C  # noqa: E402

PLATFORM = os.environ.get("AGRAS_PLATFORM", "t70p").lower()
P = importlib.import_module("platforms." + PLATFORM)
PF = C.Platform(P)

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(ROOT, P.OUT_DIR)
os.makedirs(OUT, exist_ok=True)
PFX = P.PREFIX
MM = 1000.0


def V(x, y, z):
    return Vector(x * MM, y * MM, z * MM)


# ----------------------------------------------------------------------------------
# primitivas -> solidos
# ----------------------------------------------------------------------------------
def safe(op, shape, *a):
    try:
        return op(*a)
    except Exception:
        return shape


def rect_wire(x0, x1, hy, z):
    pts = [V(x0, -hy, z), V(x1, -hy, z), V(x1, hy, z), V(x0, hy, z), V(x0, -hy, z)]
    return Part.makePolygon(pts)


def make(prim):
    k = prim["k"]
    if k == "box":
        (x0, x1), (y0, y1), (z0, z1) = prim["x"], prim["y"], prim["z"]
        s = Part.makeBox((x1 - x0) * MM, (y1 - y0) * MM, (z1 - z0) * MM, V(x0, y0, z0))
        if prim.get("fillet"):
            s = safe(s.makeFillet, s, prim["fillet"] * MM, s.Edges)
        elif prim.get("vchamfer"):   # solo aristas verticales (planta poligonal, p. ej. deposito hexagonal)
            edges = [e for e in s.Edges if abs(e.Vertexes[0].Point.z - e.Vertexes[1].Point.z) > 1e-6]
            s = safe(s.makeChamfer, s, prim["vchamfer"] * MM, edges)
        elif prim.get("chamfer"):
            ztop = z1 * MM
            edges = [e for e in s.Edges
                     if abs(e.Vertexes[0].Point.z - e.Vertexes[1].Point.z) > 1e-6
                     or (abs(e.Vertexes[0].Point.z - ztop) < 1e-6 and abs(e.Vertexes[1].Point.z - ztop) < 1e-6)]
            s = safe(s.makeChamfer, s, prim["chamfer"] * MM, edges)
        return s
    if k == "loft":
        wires = [rect_wire(sec["x"][0], sec["x"][1], sec["y"], sec["z"]) for sec in prim["sections"]]
        return Part.makeLoft(wires, True, True)
    if k == "cyl":
        return Part.makeCylinder(prim["dia"] / 2 * MM, prim["len"] * MM, V(*prim["c"]), Vector(*prim["axis"]))
    if k == "sphere":
        return Part.makeSphere(prim["dia"] / 2 * MM, V(*prim["c"]))
    if k == "tube":
        a, b = V(*prim["p0"]), V(*prim["p1"])
        d = b - a
        c = Part.makeCylinder(prim["dia"] / 2 * MM, d.Length, a, d)
        if prim.get("caps", True):
            c = c.fuse([Part.makeSphere(prim["dia"] / 2 * MM, a), Part.makeSphere(prim["dia"] / 2 * MM, b)])
        return c
    if k == "obox":
        L, W, H = prim["L"], prim["W"], prim["H"]
        b = Part.makeBox(L * MM, W * MM, H * MM, Vector(-L / 2 * MM, -W / 2 * MM, -H / 2 * MM))
        d = Vector(*prim["dir"])
        d.normalize()
        yaw = math.atan2(d.y, d.x)
        pitch = -math.asin(max(-1.0, min(1.0, d.z)))
        b.Placement = Placement(V(*prim["c"]), Rotation(math.degrees(yaw), math.degrees(pitch), 0))
        return b
    raise ValueError(k)


def rot(shape, center, axis, ang):
    s = shape.copy()
    if ang:
        s.rotate(V(*center), Vector(*axis), ang)
    return s


def tilted(shape, arm_id):
    """Inclinacion rigida del grupo motor (perpendicular al brazo) alrededor de la union brazo-motor."""
    k, c = PF.cant(arm_id)
    return rot(shape, PF.pivot(arm_id), k, c)


def nozzle_tilted(shape, n):
    """Inclinacion propia del atomizador (alrededor de su enganche) y, si cuelga del grupo motor, la del grupo."""
    own = n.get("own_cant_deg", 0.0)
    if n["mount"] == "arm":
        return tilted(rot(shape, n["_attach"], PF.arms[n["arm"]]["k"], own), n["arm"])
    return rot(shape, n["_attach"], n.get("own_axis", (1, 0, 0)), own)


def local_group(prims, arm_id):
    """Primitivas en coordenadas locales del pivote -> solidos en su sitio, inclinados."""
    piv = PF.pivot(arm_id)
    return [tilted(make(C.translate(p, piv)), arm_id) for p in prims]


# ----------------------------------------------------------------------------------
# conjuntos
# ----------------------------------------------------------------------------------
def build_airframe_pieces():
    pieces = [make(p) for p in P.BODY] + [make(p) for p in P.GEAR]
    for arm in P.ARMS:
        aid = arm["id"]
        piv = PF.pivot(aid)
        pieces += [make(p) for p in C.arm_parts(arm["root"], piv, P.ARM_DIA, P.ESC_BOX, P.ESC_AT,
                                                P.FOLD_SLEEVE, P.FOLD_AT)]
        pieces += local_group(arm["motor_group"], aid)
    for n in P.NOZZLES:
        if n["config"] not in P.AIRFRAME_NOZZLE_CONFIGS:
            continue
        u = PF.nozzle_untilted(n)
        if n["mount"] == "arm":
            piv = PF.pivot(n["arm"])
            local = (u[0] - piv[0], u[1] - piv[1], u[2] - piv[2])
            prims = C.hanging_atomizer(local, P.ATOMIZER_ATTACH_Z - piv[2], P.ATOMIZER,
                                       bracket_from=(local[0], local[1]) if n.get("bracket") == "self" else (0.0, 0.0))
            pieces += [nozzle_tilted(make(C.translate(p, piv)), n) for p in prims]
        else:
            prims = C.hanging_atomizer((0, 0, 0), n["attach_z"] - u[2], P.ATOMIZER)
            pieces += [nozzle_tilted(make(C.translate(p, u)), n) for p in prims]
    return pieces


def fuse_checked(pieces):
    """Union en serie; aborta si una booleana pierde volumen (multiFuse de OCC descarta piezas en silencio)."""
    acc = pieces[0]
    for i, p in enumerate(pieces[1:], 1):
        new = acc.fuse(p)
        va, vb, vn = acc.Volume, p.Volume, new.Volume
        tol = 1e-6 * (va + vb) + 0.01 * vb + 1.0   # 1 % de la pieza: ruido de integracion de OCC
        if not (vn + tol >= max(va, vb) and vn <= va + vb + tol) or not new.isValid():
            raise RuntimeError(f"union fallida en la pieza {i}: V_acc={va:.0f} V_pieza={vb:.0f} V_union={vn:.0f} mm3")
        acc = new
    return acc


# ----------------------------------------------------------------------------------
# helices
# ----------------------------------------------------------------------------------
def naca4(m, p, t, n=36, te_min=0.0):
    xs = [0.5 * (1 - math.cos(math.pi * i / n)) for i in range(n + 1)]
    up, lo = [], []
    for xc in xs:
        yt = 5 * t * (0.2969 * math.sqrt(xc) - 0.1260 * xc - 0.3516 * xc**2 + 0.2843 * xc**3 - 0.1015 * xc**4)
        yt += 0.5 * te_min * xc
        if xc < p:
            yc, dy = m / p**2 * (2 * p * xc - xc**2), 2 * m / p**2 * (p - xc)
        else:
            yc, dy = m / (1 - p)**2 * ((1 - 2 * p) + 2 * p * xc - xc**2), 2 * m / (1 - p)**2 * (p - xc)
        th = math.atan(dy)
        up.append((xc - yt * math.sin(th), yc + yt * math.cos(th)))
        lo.append((xc + yt * math.sin(th), yc - yt * math.cos(th)))
    return list(reversed(up)) + lo[1:]


def blade_section(rr, mirror):
    R = P.ROTOR_DIAMETER / 2
    r = rr * R
    c = C.interp(P.BLADE_CHORD_OVER_R, rr) * R
    t = C.interp(P.BLADE_THICKNESS, rr)
    m = P.BLADE_CAMBER * min(1.0, max(0.0, (rr - 0.045) / (0.20 - 0.045)))
    beta = math.radians(C.blade_beta_deg(rr, R, P.PROP_PITCH))
    pts = []
    for xi, ze in naca4(m, P.BLADE_CAMBER_POS, t, te_min=0.0006 / c):
        yl, zl = (P.BLADE_PITCH_AXIS - xi) * c, ze * c
        yr = yl * math.cos(beta) - zl * math.sin(beta)
        zr = yl * math.sin(beta) + zl * math.cos(beta)
        pts.append(Vector(r * MM, (-yr if mirror else yr) * MM, zr * MM))
    spl = Part.BSplineCurve()
    spl.interpolate(pts)
    return Part.Wire([spl.toShape(), Part.makeLine(pts[-1], pts[0])])


_PROP_CACHE = {}


def build_propeller(rotor):
    mirror = rotor["rotation"] == "CW"
    if mirror not in _PROP_CACHE:
        stations = [0.03, 0.08, 0.12, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 0.96, 0.995]
        blade = Part.makeLoft([blade_section(s, mirror) for s in stations], True, False)
        blades = [blade]
        for k in range(1, P.BLADES_PER_ROTOR):
            b = blade.copy()
            b.rotate(Vector(0, 0, 0), Vector(0, 0, 1), 360.0 * k / P.BLADES_PER_ROTOR)
            blades.append(b)
        hub_h = P.DISK_THICKNESS + 0.010
        hub = Part.makeCylinder(P.PROP_CLAMP_DIA / 2 * MM, hub_h * MM, Vector(0, 0, -hub_h / 2 * MM))
        _PROP_CACHE[mirror] = hub.fuse(blades).removeSplitter()
    prop = _PROP_CACHE[mirror].copy()
    a = PF.arms[rotor["arm"]]
    prop.translate(V(a["x"], a["y"], rotor["plane_z"]))
    return tilted(prop, rotor["arm"])


def build_disk(rotor):
    a = PF.arms[rotor["arm"]]
    z0 = rotor["plane_z"] - P.DISK_THICKNESS / 2
    return tilted(make(C.cylz(a["x"], a["y"], P.ROTOR_DIAMETER, z0, z0 + P.DISK_THICKNESS)), rotor["arm"])


def build_nozzle_marker(n):
    u = PF.nozzle_untilted(n)
    m = make(C.cylz(u[0], u[1], 2 * P.ATOMIZER_DISC_RADIUS, u[2] - 0.005, u[2] + 0.005))
    return nozzle_tilted(m, n)


# ----------------------------------------------------------------------------------
# exportacion
# ----------------------------------------------------------------------------------
def tessellate(shape, lin, ang):
    m = MeshPart.meshFromShape(Shape=shape, LinearDeflection=lin, AngularDeflection=ang, Relative=False)
    m.removeDuplicatedPoints()
    m.harmonizeNormals()
    return m


def write_stl(path, named, ascii=True):
    if ascii:
        with open(path, "w", newline="\n") as f:
            for name, m in named:
                f.write(f"solid {name}\n")
                for fa in m.Facets:
                    n = fa.Normal
                    f.write(f"  facet normal {n.x:.6e} {n.y:.6e} {n.z:.6e}\n    outer loop\n")
                    for p in fa.Points:
                        f.write(f"      vertex {p[0]/MM:.7e} {p[1]/MM:.7e} {p[2]/MM:.7e}\n")
                    f.write("    endloop\n  endfacet\n")
                f.write(f"endsolid {name}\n")
    else:
        facets = [fa for _, m in named for fa in m.Facets]
        with open(path, "wb") as f:
            f.write(f"DJI Agras {P.NAME} CFD model - m - X fwd Y left Z up".encode().ljust(80, b" ")[:80])
            f.write(struct.pack("<I", len(facets)))
            for fa in facets:
                n = fa.Normal
                f.write(struct.pack("<3f", n.x, n.y, n.z))
                for p in fa.Points:
                    f.write(struct.pack("<3f", p[0] / MM, p[1] / MM, p[2] / MM))
                f.write(b"\0\0")


def mesh_report(m):
    return {"triangles": m.CountFacets, "is_solid_closed": bool(m.isSolid()),
            "non_manifolds": bool(m.hasNonManifolds()), "self_intersections": bool(m.hasSelfIntersections()),
            "volume_m3": round(m.Volume / MM**3, 6)}


def main():
    rep = {"platform": P.NAME}
    print(f"[{P.NAME}] 1/5 fuselaje ...", flush=True)
    fused = fuse_checked(build_airframe_pieces())
    airframe = fused.removeSplitter()
    ok = lambda sh: sh.isValid() and all(x.isValid() for x in sh.Solids)  # noqa: E731
    if not ok(airframe) and ok(fused):   # removeSplitter puede estropear caras casi coplanarias
        print(f"[{P.NAME}] removeSplitter invalida el B-rep: se conserva la union sin refinar", flush=True)
        airframe = fused
    if len(airframe.Solids) == 1:
        airframe = airframe.Solids[0]
    bb = airframe.BoundBox
    rep["airframe"] = {"brep_valid": airframe.isValid(), "solids": len(airframe.Solids),
                       "volume_m3": round(airframe.Volume / MM**3, 5), "wetted_area_m2": round(airframe.Area / MM**2, 4),
                       "bbox_m": [round(v / MM, 4) for v in (bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax)]}
    print(f"[{P.NAME}] 2/5 discos y helices ...", flush=True)
    disks = {r["id"]: build_disk(r) for r in P.ROTORS}
    props = {r["id"]: build_propeller(r) for r in P.ROTORS}
    nozzles = {n["id"]: build_nozzle_marker(n) for n in P.NOZZLES}
    rep["propellers"] = {k: {"valid": v.isValid(), "solids": len(v.Solids)} for k, v in props.items()}

    print(f"[{P.NAME}] 3/5 interferencias ...", flush=True)
    rep["disk_airframe_overlap_cm3"] = {k: round(d.common(airframe).Volume / 1e3, 3) for k, d in disks.items()}
    ids = list(disks)
    rep["disk_disk_overlap_cm3"] = {f"{a}|{b}": round(disks[a].common(disks[b]).Volume / 1e3, 3)
                                    for i, a in enumerate(ids) for b in ids[i + 1:]
                                    if disks[a].BoundBox.intersect(disks[b].BoundBox)}
    rep["height_ground_to_top_m"] = round((bb.ZMax - bb.ZMin) / MM, 4)
    rep["ground_z_m"] = round(bb.ZMin / MM, 4)
    allb = [d.BoundBox for d in disks.values()]
    rep["envelope_with_props_m"] = [round((max(b.XMax for b in allb) - min(b.XMin for b in allb)) / MM, 4),
                                    round((max(b.YMax for b in allb) - min(b.YMin for b in allb)) / MM, 4)]

    print(f"[{P.NAME}] 4/5 exportando ...", flush=True)
    airframe.exportStep(os.path.join(OUT, f"{PFX}_airframe.step"))
    Part.makeCompound(list(props.values())).exportStep(os.path.join(OUT, f"{PFX}_rotor_blades.step"))
    Part.makeCompound([airframe] + list(props.values()) + list(nozzles.values())).exportStep(
        os.path.join(OUT, f"{PFX}_full_assembly.step"))
    m_air = tessellate(airframe, 0.6, 0.08)
    m_disks = [("rotor_" + k, tessellate(v, 1.0, 0.05)) for k, v in disks.items()]
    m_props = [("prop_" + k, tessellate(v, 0.8, 0.2)) for k, v in props.items()]
    m_noz = [(k, tessellate(v, 0.3, 0.1)) for k, v in nozzles.items()]
    write_stl(os.path.join(OUT, f"{PFX}_airframe.stl"), [("airframe", m_air)], ascii=False)
    write_stl(os.path.join(OUT, f"{PFX}_airframe_ascii.stl"), [("airframe", m_air)], ascii=True)
    write_stl(os.path.join(OUT, f"{PFX}_rotor_disks.stl"), m_disks, ascii=True)
    write_stl(os.path.join(OUT, f"{PFX}_rotor_blades.stl"), m_props, ascii=False)
    write_stl(os.path.join(OUT, f"{PFX}_spray_nozzles.stl"), m_noz, ascii=True)
    write_stl(os.path.join(OUT, f"{PFX}_full_assembly.stl"), [("airframe", m_air)] + m_props + m_noz, ascii=False)
    rep["meshes"] = {"airframe": mesh_report(m_air), **{k: mesh_report(m) for k, m in m_disks},
                     **{k: mesh_report(m) for k, m in m_props}, **{k: mesh_report(m) for k, m in m_noz}}

    print(f"[{P.NAME}] 5/5 documento FreeCAD ...", flush=True)
    doc = App.newDocument(P.NAME)
    for name, shp in [("Airframe", airframe)] + [("Disk_" + k, v) for k, v in disks.items()] + \
                     [("Prop_" + k, v) for k, v in props.items()] + [("Nozzle_" + k, v) for k, v in nozzles.items()]:
        doc.addObject("Part::Feature", name).Shape = shp
    doc.recompute()
    path = os.path.join(OUT, f"{PFX}_model.FCStd")
    doc.saveAs(path)
    for f in os.listdir(OUT):
        if f.endswith(".FCBak"):
            os.remove(os.path.join(OUT, f))
    bad = [k for k, m in rep["meshes"].items()
           if not m["is_solid_closed"] or m["non_manifolds"] or m["self_intersections"]]
    rep["mesh_problems"] = bad
    with open(os.path.join(OUT, "_build_report.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=2, ensure_ascii=False)
    print(json.dumps({k: v for k, v in rep.items() if k != "meshes"}, indent=1, ensure_ascii=False))


main()
