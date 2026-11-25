"""
Post-proceso generico (Python del sistema: numpy, numpy-stl, matplotlib, pillow).

    python scripts/agras_model/export_metadata.py <plataforma>

Genera en geometry/models/<P>_CFD/:
    <p>_cfd_coordinates.json, <p>_overlay_top.png, <p>_geometry_verification.png
"""
from __future__ import annotations

import importlib
import json
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402
from matplotlib.patches import Circle  # noqa: E402
from PIL import Image  # noqa: E402
from stl import mesh as stlmesh  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common as C  # noqa: E402

ROOT = HERE.parents[1]


def _r(v, n=6):
    return [round(x, n) + 0.0 for x in v]


class Ctx:
    def __init__(self, name):
        self.P = importlib.import_module("platforms." + name.lower())
        self.PF = C.Platform(self.P)
        self.OUT = ROOT / self.P.OUT_DIR
        self.pfx = self.P.PREFIX

    def load(self, suffix):
        f = self.OUT / f"{self.pfx}_{suffix}"
        parts = list(stlmesh.Mesh.from_multi_file(str(f)))
        return np.concatenate([m.vectors for m in parts]) if parts else stlmesh.Mesh.from_file(str(f)).vectors


def rotor_record(cx, r):
    P, PF = cx.P, cx.PF
    n, c = PF.rotor_axis(r), PF.rotor_center(r)
    lat, lon = PF.components(r["arm"])
    sign = +1 if r["rotation"] == "CCW" else -1
    return {
        "rotor_id": r["id"], "arm": r["arm"], "dji_motor_number": r.get("dji_motor"), "role": r["role"], "level": r["level"],
        "center_xyz_m": _r(c, 4), "height_above_ground_m": round(c[2] - P.Z_GROUND, 4),
        "arm_motor_joint_pivot_xyz_m": _r(PF.pivot(r["arm"]), 4),
        "cant_along_arm_deg": P.MOTOR_CANT_DEG, "arm_direction_xy": _r(PF.arms[r["arm"]]["u"][:2], 4),
        "cant_components_deg": {"lateral": round(lat, 3), "longitudinal": round(lon, 3)},
        "disk_normal": _r(n), "thrust_direction_on_airframe": _r(n), "downwash_direction": _r([-v for v in n]),
        "thrust_components_fraction": {"vertical": round(n[2], 5), "lateral_inward": round(abs(n[1]), 5),
                                       "longitudinal": round(n[0], 5)},
        "rotation_seen_from_above": r["rotation"], "angular_velocity_unit_vector": _r([sign * v for v in n]),
        "diameter_m": P.ROTOR_DIAMETER, "radius_m": round(P.ROTOR_DIAMETER / 2, 4),
        "swept_area_m2": round(math.pi * (P.ROTOR_DIAMETER / 2) ** 2, 4),
        "disk_thickness_m": P.DISK_THICKNESS, "blades": P.BLADES_PER_ROTOR,
    }


def nozzle_record(cx, n):
    P, PF = cx.P, cx.PF
    c, ax = PF.nozzle_center(n), PF.nozzle_axis(n)
    rec = {
        "nozzle_id": n["id"], "configuration": {"std": "estandar", "opt": "opcional"}.get(n["config"], n["config"]),
        "mount": "grupo motor (hereda la inclinacion)" if n["mount"] == "arm" else "barra / cuerpo",
        "disc_center_xyz_m": _r(c, 4), "height_above_ground_m": round(c[2] - P.Z_GROUND, 4),
        "disc_axis": _r(ax), "disc_radius_m": P.ATOMIZER_DISC_RADIUS,
        "injection": "lamina radial 360 grados en el plano perpendicular a disc_axis; v_borde = omega*R_disco",
        "own_cant_deg": n.get("own_cant_deg", 0.0),
        "classification": n["cls"],
    }
    if n["mount"] == "arm":
        rot = next(r for r in P.ROTORS if r["arm"] == n["arm"] and r["level"] in ("simple", "lower"))
        rec["mounted_under"] = n["arm"]
        rec["below_lowest_rotor_plane_m"] = round(PF.rotor_center(rot)[2] - c[2], 4)
    return rec


def hover_reference(P):
    rho, g = 1.1716, 9.80665
    n = len(P.ROTORS)
    A = n * math.pi * (P.ROTOR_DIAMETER / 2) ** 2
    coax = any(r["level"] == "upper" for r in P.ROTORS)
    A_eff = A / 2 if coax else A
    out = {"rho_kg_m3": rho, "rotor_count": n, "total_disk_area_m2": round(A, 4),
           "momentum_area_m2": round(A_eff, 4),
           "aviso": "teoria de cantidad de movimiento, solo orden de magnitud" +
                    ("; coaxial: se usa el area de 4 discos (los pares comparten estela)" if coax else "")}
    for label, m in P.HOVER_MASSES:
        T = m * g
        vi = math.sqrt(T / (2 * rho * A_eff))
        out[label] = {"thrust_per_rotor_N": round(T / n, 1), "disk_loading_N_m2": round(T / A_eff, 1),
                      "induced_velocity_m_s": round(vi, 2), "far_wake_velocity_m_s": round(2 * vi, 2)}
    return out


def build_json(cx, report):
    P, PF = cx.P, cx.PF
    hubs = [(a["hub_x"], a["hub_y"]) for a in P.ARMS]
    diag = max(math.hypot(a[0] - b[0], a[1] - b[1]) for a in hubs for b in hubs)
    sp = getattr(P, "SPRAY", {})
    return {
        "platform": f"DJI Agras {P.NAME}", "model_version": "2.0",
        "generated_by": "scripts/agras_model (build_freecad.py + export_metadata.py), parametros en platforms/" + P.PREFIX + ".py",
        "classification_legend": {"P": "ficha oficial DJI", "P-A": "DJI Academy", "S": "medido sobre imagen",
                                  "O/M": "medido por el propietario", "I": "inferido / estimado", "D": "desconocido"},
        "coordinate_system": {"handedness": "derecha (X x Y = Z)",
                              "origin": "XY: centroide de los bujes; Z: plano de raiz de los brazos",
                              "x_axis": "+X adelante", "y_axis": "+Y IZQUIERDA (babor)", "z_axis": "+Z arriba",
                              "ground_plane_z_m": P.Z_GROUND, "units_stl": "m", "units_step": "mm"},
        "topology": P.TOPOLOGY,
        "general_dimensions": {
            "wheelbase_diagonal_model_m": round(diag, 4), "wheelbase_diagonal_official_m": P.OFFICIAL["wheelbase_m"],
            "envelope_with_props_model_m": report.get("envelope_with_props_m"),
            "envelope_with_props_official_m": P.OFFICIAL["envelope_m"],
            "height_model_m": report.get("height_ground_to_top_m"), "height_official_m": P.OFFICIAL["height_m"],
        },
        "cant": {"motor_along_arm_deg": P.MOTOR_CANT_DEG,
                 "model": "motor perpendicular al tubo del brazo: giro rigido alrededor de la union brazo-motor, "
                          "en el plano vertical que contiene al brazo; + = parte alta hacia fuera",
                 "atomizers": "los montados en el grupo motor heredan la inclinacion; 'own_cant_deg' es adicional",
                 "source": getattr(P, "CANT_SOURCE", "")},
        "rotors": [rotor_record(cx, r) for r in P.ROTORS],
        "rotation_source": P.ROTATION_SOURCE,
        "propeller": {"diameter_m": P.ROTOR_DIAMETER, "pitch_m": round(P.PROP_PITCH, 4), "blades": P.BLADES_PER_ROTOR,
                      "beta_75R_deg": round(C.blade_beta_deg(0.75, P.ROTOR_DIAMETER / 2, P.PROP_PITCH), 2),
                      "twist_law": "beta = atan(P / (2 pi r)), congelado bajo r/R = 0.20",
                      "chord_over_R_vs_r_over_R": P.BLADE_CHORD_OVER_R,
                      "airfoil": f"NACA 4-digitos m={P.BLADE_CAMBER} p={P.BLADE_CAMBER_POS}",
                      "classification": getattr(P, "PROP_CLASS", "cuerda S/I, perfil I")},
        "spray_system": {**sp, "nozzles": [nozzle_record(cx, n) for n in P.NOZZLES]},
        "mass": P.MASS,
        "momentum_theory_hover_reference": hover_reference(P),
        "airframe_brep": report.get("airframe"), "airframe_mesh": report.get("meshes", {}).get("airframe"),
        "disk_airframe_overlap_cm3": report.get("disk_airframe_overlap_cm3"),
        "notes": P.NOTES,
    }


def project(t, view):
    if view == "top":
        return np.stack([t[:, :, 1], t[:, :, 0]], axis=-1)
    if view == "side":
        return np.stack([t[:, :, 0], t[:, :, 2]], axis=-1)
    return np.stack([-t[:, :, 1], t[:, :, 2]], axis=-1)


def draw(ax, t, view, color, alpha=1.0):
    ax.add_collection(PolyCollection(project(t, view), facecolors=color, edgecolors=color, linewidths=0, alpha=alpha))


def overlay_top(cx, air, blades):
    P, PF, ref = cx.P, cx.PF, cx.P.REF
    if not ref.get("top"):
        return
    im = Image.open(ROOT / ref["top"]).convert("RGB")
    (ccx, ccy), s, kx, ky = ref["center_px"], ref["scale"], ref["kx"], ref["ky"]

    def px(x, y):
        return ccx + ky * y / s, ccy + kx * x / s

    def to_px(t):
        return np.stack([ccx + ky * t[:, :, 1] / s, ccy + kx * t[:, :, 0] / s], axis=-1)

    fig, ax = plt.subplots(figsize=(13, 8), dpi=120)
    ax.imshow(im, alpha=0.55)
    ax.add_collection(PolyCollection(to_px(blades), facecolors="#1f77b4", edgecolors="none", alpha=0.30))
    ax.add_collection(PolyCollection(to_px(air), facecolors="#d62728", edgecolors="none", alpha=0.45))
    for r in P.ROTORS:
        if r["level"] == "lower":
            continue
        c = PF.rotor_center(r)
        u, v = px(c[0], c[1])
        ax.add_patch(Circle((u, v), P.ROTOR_DIAMETER / 2 / s, fill=False, ec="#1f77b4", lw=1.2, ls="--"))
        lab = r["arm"] + ("" if r["level"] == "simple" else " (coax)")
        ax.text(u, v - 0.12 / s, lab, ha="center", va="bottom", fontsize=8, color="#0b3d91", weight="bold")
    for n in P.NOZZLES:
        c = PF.nozzle_center(n)
        u, v = px(c[0], c[1])
        ax.plot(u, v, "o", ms=6, mfc="lime" if n["config"] == "std" else "none", mec="green", mew=1.5)
    allx = [px(PF.rotor_center(r)[0], PF.rotor_center(r)[1]) for r in P.ROTORS]
    us, vs = [a[0] for a in allx], [a[1] for a in allx]
    pad = P.ROTOR_DIAMETER / 2 / s * 1.15
    ax.set_xlim(min(us) - pad, max(us) + pad)
    ax.set_ylim(max(vs) + pad, min(vs) - pad)
    ax.set_title(f"{P.NAME}: modelo (rojo = fuselaje, azul = palas, circulos = discos, verde = atomizadores) "
                 f"sobre {Path(ref['top']).name}, escala {s*1000:.2f} mm/px", fontsize=9)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(cx.OUT / f"{cx.pfx}_overlay_top.png")
    plt.close(fig)


def verification(cx, air, disks, noz, blades, report):
    P = cx.P
    span = max(report["envelope_with_props_m"]) / 2 + 0.1
    zmin, zmax = P.Z_GROUND - 0.05, report["airframe"]["bbox_m"][5] + 0.1
    fig = plt.figure(figsize=(18, 11), dpi=105)
    gs = fig.add_gridspec(2, 3)
    views = [("top", "Planta (desde +Z) - frente abajo, babor a la derecha", (-span, span), (span, -span), "Y [m]", "X [m]"),
             ("side", "Perfil derecho (desde -Y) - frente a la derecha", (-span, span), (zmin, zmax), "X [m]", "Z [m]"),
             ("rear", "Alzado trasero (desde -X)", (-span, span), (zmin, zmax), "-Y [m]", "Z [m]")]
    for i, (v, title, xl, yl, xlab, ylab) in enumerate(views):
        ax = fig.add_subplot(gs[0, i])
        draw(ax, disks, v, "#9ecae1", 0.30)
        draw(ax, blades, v, "#3182bd", 0.85)
        draw(ax, air, v, "#555555", 1.0)
        draw(ax, noz, v, "#31a354", 1.0)
        if v != "top":
            ax.axhline(P.Z_GROUND, color="#8c6d31", lw=1)
        ax.set_xlim(*xl); ax.set_ylim(*yl); ax.set_aspect("equal"); ax.grid(alpha=0.3)
        ax.set_title(title, fontsize=10); ax.set_xlabel(xlab); ax.set_ylabel(ylab)
    refs = [r for r in [P.REF.get("top")] + list(P.REF.get("views", [])) if r]
    for i, f in enumerate(refs[:3]):
        ax = fig.add_subplot(gs[1, i])
        ax.imshow(Image.open(ROOT / f).convert("RGB"))
        ax.set_title("Referencia: " + Path(f).name, fontsize=10)
        ax.axis("off")
    a = report["airframe"]
    j = build_json(cx, report)["general_dimensions"]
    fig.suptitle(f"DJI Agras {P.NAME} - modelo CFD | {j['wheelbase_diagonal_model_m']*1000:.0f} mm diagonal "
                 f"(oficial {P.OFFICIAL['wheelbase_m']*1000:.0f}) | sobre {report['envelope_with_props_m'][0]*1000:.0f} x "
                 f"{report['envelope_with_props_m'][1]*1000:.0f} mm (oficial {P.OFFICIAL['envelope_m'][0]*1000:.0f} x "
                 f"{P.OFFICIAL['envelope_m'][1]*1000:.0f}) | altura {report['height_ground_to_top_m']*1000:.0f} mm "
                 f"(oficial {P.OFFICIAL['height_m']*1000:.0f}) | motor {P.MOTOR_CANT_DEG:+.2f} grados a lo largo del brazo | "
                 f"fuselaje {a['solids']} solido, {a['wetted_area_m2']} m2", fontsize=10)
    fig.tight_layout()
    fig.savefig(cx.OUT / f"{cx.pfx}_geometry_verification.png")
    plt.close(fig)


def main(name):
    cx = Ctx(name)
    report = json.loads((cx.OUT / "_build_report.json").read_text(encoding="utf-8"))
    air, disks = cx.load("airframe.stl"), cx.load("rotor_disks.stl")
    noz, blades = cx.load("spray_nozzles.stl"), cx.load("rotor_blades.stl")
    (cx.OUT / f"{cx.pfx}_cfd_coordinates.json").write_text(json.dumps(build_json(cx, report), indent=2, ensure_ascii=False),
                                                           encoding="utf-8")
    overlay_top(cx, air, blades)
    verification(cx, air, disks, noz, blades, report)
    print(f"[{cx.P.NAME}] JSON + figuras OK")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "t70p")
