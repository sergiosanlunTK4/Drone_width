"""
DJI Agras T55 — parametros del modelo CFD.  Clases: P ficha DJI | S medido en imagen | I inferido.

Topologia: 4 rotores SIMPLES de 62 in — NO coaxial (S): T55.webp, T55_REAR.jpg y las 54 fotos del propietario
(DJI_T55/) muestran 1 helice por brazo; el "4 pares" de la ficha son pares de palas, no pares coaxiales.
Atomizadores: barra bajo cada brazo trasero con DOS atomizadores en V (fotos 7493-7499, T55_REAR_DOWN):
el exterior (bajo el motor) es el estandar (2 x, 1800 mm, P); el interior es el opcional (4 x).

PLANTA: no hay vista cenital ortografica (solo perspectivas). Se usan las proporciones de la familia T70P
(via trasera / delantera = 0.915) escaladas para cerrar las 3 cotas oficiales: diagonal 2415, sobre 3190 x 3570
-> batalla 1.575, vias 1.945 / 1.780 m; errores -1.3 % / -1.4 % / +1.0 % [P + I].
ALTURAS: T55_REAR.jpg, escala calibrada con la altura oficial 934 mm (radar -> patas) [S].
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common as C  # noqa: E402

NAME = "T55"
PREFIX = "t55"
OUT_DIR = "geometry/models/T55_CFD"

Z_ROOT_ABOVE_GROUND = 0.514
Z_GROUND = -Z_ROOT_ABOVE_GROUND


def zg(h):
    return h - Z_ROOT_ABOVE_GROUND


ROTOR_DIAMETER = 1.5748          # 62 in [P]
PROP_PITCH = 23 * 0.0254         # no publicado; misma familia 62 in [I]
BLADES_PER_ROTOR = 2
PROP_PLANE_Z = zg(0.700)         # [S]
DISK_THICKNESS = 0.040
PROP_CLAMP_DIA = 0.080
_R62 = 0.7874
BLADE_CHORD_OVER_R = [(rr, c / _R62) for rr, c in [
    (0.045, 0.040), (0.12, 0.055), (0.20, 0.075), (0.30, 0.085), (0.40, 0.083), (0.50, 0.079),
    (0.60, 0.073), (0.70, 0.067), (0.80, 0.061), (0.90, 0.052), (0.96, 0.042), (0.995, 0.025)]]
BLADE_THICKNESS = [(0.045, 0.35), (0.12, 0.20), (0.20, 0.14), (0.30, 0.12), (0.50, 0.10),
                   (0.70, 0.09), (0.90, 0.08), (1.00, 0.08)]
BLADE_CAMBER, BLADE_CAMBER_POS, BLADE_PITCH_AXIS = 0.04, 0.4, 0.30
PROP_CLASS = "diametro P; paso, cuerda y perfil I (familia 62 in)"

MOTOR_CANT_DEG = -2.2
CANT_SOURCE = "I: valor de familia (T70P S+M); no hay vista limpia del T55 para medirlo. VERIFICAR con medicion"

ARM_DIA = 0.055
ARM_TIP_Z = zg(0.600)
ESC_BOX, ESC_AT = (0.230, 0.090, 0.070), 0.62
FOLD_SLEEVE, FOLD_AT = (0.075, 0.100), 0.12
_HX, _HYF, _HYR = 0.7875, 0.9725, 0.890

_MOUNT_Z = (zg(0.480), zg(0.615))
_GROUP = C.single_motor_group(ARM_TIP_Z, mount_box=(0.150, 0.130), mount_z=_MOUNT_Z,
                              bell_dia=0.190, bell_z=(zg(0.615), zg(0.675)), clamp_dia=PROP_CLAMP_DIA,
                              disk_bottom_z=PROP_PLANE_Z - DISK_THICKNESS / 2)
ATOMIZER_ATTACH_Z = _MOUNT_Z[0]
_BAR_LEN = 0.46                  # barra porta-atomizadores bajo el brazo trasero [S, fotos 7497/7498]


def _unit(hx, hy, root):
    dx, dy = hx - root[0], hy - root[1]
    L = math.hypot(dx, dy)
    return dx / L, dy / L


def _rear_group(hx, hy, root):
    ux, uy = _unit(hx, hy, root)
    c = (-ux * (_BAR_LEN / 2 - 0.06), -uy * (_BAR_LEN / 2 - 0.06), ATOMIZER_ATTACH_Z - ARM_TIP_Z - 0.005)
    return _GROUP + [C.obox(c, (ux, uy, 0.0), _BAR_LEN, 0.060, 0.050)]


def _arm(aid, hx, hy, root, rear=False):
    return {"id": aid, "hub_x": hx, "hub_y": hy, "hub_ref_z": PROP_PLANE_Z, "root": root,
            "motor_group": _rear_group(hx, hy, root) if rear else _GROUP}


_ROOTS = {"M1_FR": (+0.430, -0.290, 0.0), "M2_FL": (+0.430, +0.290, 0.0),
          "M3_RL": (-0.350, +0.310, 0.0), "M4_RR": (-0.350, -0.310, 0.0)}
ARMS = [
    _arm("M1_FR", +_HX, -_HYF, _ROOTS["M1_FR"]),
    _arm("M2_FL", +_HX, +_HYF, _ROOTS["M2_FL"]),
    _arm("M3_RL", -_HX, +_HYR, _ROOTS["M3_RL"], rear=True),
    _arm("M4_RR", -_HX, -_HYR, _ROOTS["M4_RR"], rear=True),
]
ROTORS = [
    {"id": "M1_FR", "arm": "M1_FR", "dji_motor": 1, "role": "delantero-derecho", "level": "simple", "plane_z": PROP_PLANE_Z, "rotation": "CCW"},
    {"id": "M2_FL", "arm": "M2_FL", "dji_motor": 2, "role": "delantero-izquierdo", "level": "simple", "plane_z": PROP_PLANE_Z, "rotation": "CW"},
    {"id": "M3_RL", "arm": "M3_RL", "dji_motor": 3, "role": "trasero-izquierdo", "level": "simple", "plane_z": PROP_PLANE_Z, "rotation": "CCW"},
    {"id": "M4_RR", "arm": "M4_RR", "dji_motor": 4, "role": "trasero-derecho", "level": "simple", "plane_z": PROP_PLANE_Z, "rotation": "CW"},
]
ROTATION_SOURCE = "I: convencion DJI tradicional (como T40/T50/T100). VERIFICAR"

# ---------------- pulverizacion ----------------
ATOMIZER = {"stem_dia": 0.060, "ring_dia": 0.072, "bell_dia": 0.095, "bell_h": 0.055, "ring_h": 0.010}
ATOMIZER_DISC_RADIUS = 0.035
_DISC_Z = zg(0.290)              # [S]
ATOMIZER_V_CANT_DEG = 10.0       # apertura en V de cada atomizador respecto a su eje motor [I, fotos oblicuas]
_INNER_OFFSET = 0.36             # distancia exterior -> interior a lo largo del brazo [S, fotos]


def _pair(arm, hx, hy, root, side):
    ux, uy = _unit(hx, hy, root)
    yo = side * 0.900                                    # 1800 mm [P]
    xo = hx + (yo - hy) * ux / uy
    xi, yi = xo - _INNER_OFFSET * ux, yo - _INNER_OFFSET * uy
    tag = "L" if side > 0 else "R"
    return [
        {"id": f"N_R{tag}_ext", "config": "std", "mount": "arm", "arm": arm, "x": xo, "y": yo, "disc_z": _DISC_Z,
         "own_cant_deg": -ATOMIZER_V_CANT_DEG, "bracket": "self", "cls": "P (Y) + S (X, Z) + I (V)"},
        {"id": f"N_R{tag}_int", "config": "opt", "mount": "arm", "arm": arm, "x": xi, "y": yi, "disc_z": _DISC_Z,
         "own_cant_deg": +ATOMIZER_V_CANT_DEG, "bracket": "self", "cls": "S + I (V)"},
    ]


NOZZLES = _pair("M3_RL", -_HX, +_HYR, _ROOTS["M3_RL"], +1) + _pair("M4_RR", -_HX, -_HYR, _ROOTS["M4_RR"], -1)
AIRFRAME_NOZZLE_CONFIGS = ("std", "opt")      # la barra con los dos atomizadores es fija en el dron
SPRAY = {"atomizer_model": "LX09050DX (estandar) / LX09510DX (niebla, opcional)", "nozzle_spacing_official_m": 1.800,
         "flow_L_min": {"2_boquillas": 40.0, "4_boquillas": 50.0}, "flow_class": "O (propietario 2026-11-22)",
         "droplet_um": [50, 500],
         "v_cant_deg": ATOMIZER_V_CANT_DEG}

# ---------------- cuerpo [S/I, layout de la familia T70P con cotas del T55] ----------------
_TX, _TY, _TZ = (-0.320, 0.170), 0.235, (zg(0.500), zg(0.750))
BODY = [
    C.box((-0.380, 0.480), (0.240, 0.280), (-0.025, 0.025)),
    C.box((-0.380, 0.480), (-0.280, -0.240), (-0.025, 0.025)),
    C.box((-0.370, -0.330), (-0.330, 0.330), (-0.025, 0.025)),
    C.box((0.410, 0.450), (-0.320, 0.320), (-0.025, 0.025)),
] + [C.boxc(r[0], r[1], 0.0, 0.094, 0.086, 0.074) for r in _ROOTS.values()] + [
    C.box(_TX, (-_TY, _TY), _TZ, fillet=0.040),
    C.loft([{"x": (-0.200, 0.030), "y": 0.140, "z": zg(0.185)},
            {"x": (_TX[0] + 0.02, _TX[1] - 0.02), "y": _TY - 0.02, "z": _TZ[0] + 0.02}]),
    C.cylz(-0.120, 0.0, 0.150, _TZ[1] - 0.01, _TZ[1] + 0.030),
    C.box((0.170, 0.520), (-0.220, 0.220), (zg(0.450), zg(0.700)), chamfer=0.050),
    C.cylz(0.340, 0.0, 0.110, zg(0.680), zg(0.934)),                   # radar, tope 934 mm [P]
    C.cylz(0.340, 0.0, 0.160, zg(0.670), zg(0.715)),
    C.box((0.420, 0.500), (-0.050, 0.050), (zg(0.300), zg(0.460))),
    C.box((0.000, 0.150), (-0.140, 0.140), (zg(0.150), zg(0.260))),     # bombas
]
_GD = 0.035
GEAR = C.u_gear(skid_y=0.250, skid_x=(-0.400, 0.450), skid_z=zg(_GD / 2), tube_dia=_GD, leg_top_y=0.240,
                rear_leg={"bottom_x": -0.330, "top_x": -0.200, "top_z": zg(0.450)},
                front_leg={"bottom_x": 0.400, "top_x": 0.320, "top_z": zg(0.450)},
                rail_y=0.260, crossbar_z=zg(0.260))

OFFICIAL = {"wheelbase_m": 2.415, "envelope_m": [3.190, 3.570], "height_m": 0.934, "nozzle_spacing_m": 1.800}
MASS = {"con_bateria_DB1050_kg": 45.0, "tanque_kg": 50.0, "mtow_pulverizacion_2boq_kg": 95.0}
HOVER_MASSES = [("vacio_45kg", 45.0), ("mtow_95kg", 95.0)]
REF = {"top": None,
       "views": ["geometry/models/T55_CFD/T55_reference/T55.png", "geometry/models/T55_CFD/T55_reference/T55_REAR.jpg",
                 "geometry/models/T55_CFD/T55_reference/T55_REAR_DOWN.png"]}
TOPOLOGY = {"rotor_count": 4, "coaxial": False,
            "evidence": "T55.webp, T55_REAR.jpg, fotos del propietario DJI_T55/: 1 helice por brazo. Ficha: '4 pares' = pares de palas",
            "classification": "S"}
NOTES = ["PLANTA INFERIDA: sin vista cenital ortografica; proporciones T70P escaladas a las 3 cotas oficiales (error <= 1.4 %).",
         "Atomizadores en V sobre barra bajo cada brazo trasero; angulo de la V +-10 grados (I): MEDIR.",
         "Inclinacion del motor: valor de familia -2.2 grados (I). Sentido de giro asumido (I).",
         "Alturas medidas en T55_REAR.jpg (S)."]
