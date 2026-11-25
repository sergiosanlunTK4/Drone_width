"""
DJI Agras T70P — parametros del modelo CFD.  Clases: P ficha DJI | P-A DJI Academy | S medido en imagen
oficial | O/M medido por el propietario | I inferido.

Topologia: 4 rotores SIMPLES (no coaxial) [P-A + S]: "empuje de un solo eje 54.2 kg", abrazadera oscilante
"solo T70P"; slide 11 muestra 1 helice por brazo. Giro (slide 14, visto desde arriba): M1 FR CW, M2 FL CCW,
M3 RL CW, M4 RR CCW. Frente = radar rotativo; deposito atras; 2 atomizadores bajo los motores traseros.

Fotogrametria (geometry/models/T70P_CFD/mediciones/):
  planta T70P_UP.png, escala 4.95 mm/px ajustada a helice 62 in + diagonal 2440 + sobre 3200x3520
  alturas: T70P_REAR / T70P_RIGHT calibradas con la altura oficial 960 mm
  inclinacion: -2.07 +- 0.3 grados lateral (parte alta hacia dentro); el propietario midio 2-3 grados (M)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common as C  # noqa: E402

NAME = "T70P"
PREFIX = "t70p"
OUT_DIR = "geometry/models/T70P_CFD"

Z_ROOT_ABOVE_GROUND = 0.50
Z_GROUND = -Z_ROOT_ABOVE_GROUND


def zg(h):
    return h - Z_ROOT_ABOVE_GROUND


# ---------------- rotor / pala ----------------
ROTOR_DIAMETER = 1.5748          # 62 in [P]
PROP_PITCH = 23 * 0.0254         # 6223 [P-A]
BLADES_PER_ROTOR = 2
PROP_PLANE_Z = zg(0.765)         # [S]
DISK_THICKNESS = 0.040
PROP_CLAMP_DIA = 0.080
_R62 = 0.7874
BLADE_CHORD_OVER_R = [(rr, c / _R62) for rr, c in [
    (0.045, 0.040), (0.12, 0.055), (0.20, 0.075), (0.30, 0.085), (0.40, 0.083), (0.50, 0.079),
    (0.60, 0.073), (0.70, 0.067), (0.80, 0.061), (0.90, 0.052), (0.96, 0.042), (0.995, 0.025)]]  # [S/I]
BLADE_THICKNESS = [(0.045, 0.35), (0.12, 0.20), (0.20, 0.14), (0.30, 0.12), (0.50, 0.10),
                   (0.70, 0.09), (0.90, 0.08), (1.00, 0.08)]                                   # [I]
BLADE_CAMBER, BLADE_CAMBER_POS, BLADE_PITCH_AXIS = 0.04, 0.4, 0.30                            # [I]

# ---------------- inclinacion ----------------
# Motor perpendicular al tubo del brazo (propietario): inclinacion en el plano del brazo, parte alta hacia
# dentro. Vista trasera, bordes subpixel: componente lateral -1.52 +- 0.3 grados (S) en los brazos traseros
# (|u_y| = 0.783) -> -1.94 grados a lo largo del brazo. Medicion del propietario: 2-3 grados (M).
# Valor adoptado: media ponderada S (-1.94 +- 0.5) y M (-2.5 +- 0.5) = -2.2 grados.
MOTOR_CANT_DEG = -2.2
CANT_SOURCE = ("S: mediciones/mediciones_inclinacion_t70p.csv (lateral -1.52, brazos traseros -> -1.94 a lo largo "
               "del brazo) + M: propietario 2-3 grados -> -2.2 grados")

# ---------------- brazos y grupo motor ----------------
ARM_DIA = 0.055
ARM_TIP_Z = zg(0.590)            # pivote de la inclinacion = union brazo-motor [S]
ESC_BOX, ESC_AT = (0.240, 0.090, 0.075), 0.65
FOLD_SLEEVE, FOLD_AT = (0.075, 0.100), 0.12
_HX, _HYF, _HYR = 0.802, 0.963, 0.881   # bujes medidos en planta [S]

_GROUP = C.single_motor_group(ARM_TIP_Z, mount_box=(0.150, 0.130), mount_z=(zg(0.510), zg(0.660)),
                              bell_dia=0.190, bell_z=(zg(0.660), zg(0.735)), clamp_dia=PROP_CLAMP_DIA,
                              disk_bottom_z=PROP_PLANE_Z - DISK_THICKNESS / 2)


def _arm(aid, hx, hy, root):
    return {"id": aid, "hub_x": hx, "hub_y": hy, "hub_ref_z": PROP_PLANE_Z, "root": root, "motor_group": _GROUP}


ARMS = [
    _arm("M1_FR", +_HX, -_HYF, (+0.440, -0.290, 0.0)),
    _arm("M2_FL", +_HX, +_HYF, (+0.440, +0.290, 0.0)),
    _arm("M3_RL", -_HX, +_HYR, (-0.352, +0.320, 0.0)),
    _arm("M4_RR", -_HX, -_HYR, (-0.352, -0.320, 0.0)),
]
ROTORS = [
    {"id": "M1_FR", "arm": "M1_FR", "dji_motor": 1, "role": "delantero-derecho", "level": "simple", "plane_z": PROP_PLANE_Z, "rotation": "CW"},
    {"id": "M2_FL", "arm": "M2_FL", "dji_motor": 2, "role": "delantero-izquierdo", "level": "simple", "plane_z": PROP_PLANE_Z, "rotation": "CCW"},
    {"id": "M3_RL", "arm": "M3_RL", "dji_motor": 3, "role": "trasero-izquierdo", "level": "simple", "plane_z": PROP_PLANE_Z, "rotation": "CW"},
    {"id": "M4_RR", "arm": "M4_RR", "dji_motor": 4, "role": "trasero-derecho", "level": "simple", "plane_z": PROP_PLANE_Z, "rotation": "CCW"},
]
ROTATION_SOURCE = "P-A (DJI Academy deck 01, slide 14)"

# ---------------- pulverizacion ----------------
ATOMIZER = {"stem_dia": 0.065, "ring_dia": 0.078, "bell_dia": 0.100, "bell_h": 0.055, "ring_h": 0.010}
ATOMIZER_ATTACH_Z = zg(0.510)
ATOMIZER_DISC_RADIUS = 0.035
_DISC_Z = zg(0.300)
_OUT = 1.874 / 2 - _HYR          # 0.056 m fuera del buje [P + S]
NOZZLES = [
    {"id": "N1_RL", "config": "std", "mount": "arm", "arm": "M3_RL", "x": -_HX, "y": +0.937, "disc_z": _DISC_Z, "cls": "P+S"},
    {"id": "N2_RR", "config": "std", "mount": "arm", "arm": "M4_RR", "x": -_HX, "y": -0.937, "disc_z": _DISC_Z, "cls": "P+S"},
    {"id": "N3_FL", "config": "opt", "mount": "arm", "arm": "M2_FL", "x": +_HX, "y": +(_HYF + _OUT), "disc_z": _DISC_Z, "cls": "O (delante, propietario) + I (offset)"},
    {"id": "N4_FR", "config": "opt", "mount": "arm", "arm": "M1_FR", "x": +_HX, "y": -(_HYF + _OUT), "disc_z": _DISC_Z, "cls": "O (delante, propietario) + I (offset)"},
]
AIRFRAME_NOZZLE_CONFIGS = ("std",)
SPRAY = {"atomizer_model": "LX07550SX (estandar) / LX09550SX (niebla, opcional)", "nozzle_spacing_official_m": 1.874,
         "flow_L_min": {"2_boquillas": 30.0, "4_boquillas": 40.0}, "droplet_um": [50, 500], "disc_rpm_max": 14000}

# ---------------- cuerpo ----------------
_TANK_X, _TANK_Y, _TANK_Z = (-0.330, 0.210), 0.245, (zg(0.500), zg(0.830))
_RADAR_X = 0.440
_REAR_RADAR = {"x": -0.290, "z": zg(0.190), "dia": 0.115, "len": 0.150}
BODY = [
    C.box((-0.380, 0.470), (0.250, 0.290), (-0.025, 0.025)),
    C.box((-0.380, 0.470), (-0.290, -0.250), (-0.025, 0.025)),
    C.box((-0.372, -0.332), (-0.330, 0.330), (-0.025, 0.025)),
    C.box((0.420, 0.460), (-0.330, 0.330), (-0.025, 0.025)),
] + [C.boxc(a["root"][0], a["root"][1], 0.0, 0.094, 0.086, 0.074) for a in ARMS] + [
    C.box(_TANK_X, (-_TANK_Y, _TANK_Y), _TANK_Z, fillet=0.040),
    C.loft([{"x": (-0.240, 0.060), "y": 0.160, "z": zg(0.200)},
            {"x": (_TANK_X[0] + 0.02, _TANK_X[1] - 0.02), "y": _TANK_Y - 0.02, "z": _TANK_Z[0] + 0.02}]),
    C.cylz(-0.165, 0.0, 0.160, _TANK_Z[1] - 0.01, _TANK_Z[1] + 0.030),
    C.box((0.210, 0.600), (-0.240, 0.240), (zg(0.480), zg(0.720)), chamfer=0.060),
    C.cylz(_RADAR_X, 0.0, 0.120, zg(0.700), zg(0.960)),                 # radar rotativo, tope 960 mm [P]
    C.cylz(_RADAR_X, 0.0, 0.170, zg(0.690), zg(0.740)),
    C.box((0.450, 0.550), (-0.060, 0.060), (zg(0.300), zg(0.490))),
    C.box((0.040, 0.200), (-0.150, 0.150), (zg(0.130), zg(0.270))),      # bombas
    C.cyl((_REAR_RADAR["x"], -_REAR_RADAR["len"] / 2, _REAR_RADAR["z"]), (0, 1, 0), _REAR_RADAR["dia"], _REAR_RADAR["len"]),
]
_GEAR_D = 0.036
_REAR_LEG = {"bottom_x": -0.360, "top_x": -0.210, "top_z": zg(0.450)}
GEAR = C.u_gear(skid_y=0.280, skid_x=(-0.400, 0.480), skid_z=zg(_GEAR_D / 2), tube_dia=_GEAR_D, leg_top_y=0.250,
                rear_leg=_REAR_LEG, front_leg={"bottom_x": 0.450, "top_x": 0.370, "top_z": zg(0.480)},
                rail_y=0.270, crossbar_z=zg(0.260))
_f = (zg(0.260) - zg(_GEAR_D / 2)) / (_REAR_LEG["top_z"] - zg(_GEAR_D / 2))
GEAR.append(C.tube((_REAR_LEG["bottom_x"] + _f * (_REAR_LEG["top_x"] - _REAR_LEG["bottom_x"]), 0, zg(0.260)),
                   (_REAR_RADAR["x"], 0, _REAR_RADAR["z"]), 0.030))

# ---------------- referencias, comprobaciones y masa ----------------
OFFICIAL = {"wheelbase_m": 2.440, "envelope_m": [3.200, 3.520], "envelope_alt_m": [3.175, 3.490],
            "height_m": 0.960, "nozzle_spacing_m": 1.874}
MASS = {"con_bateria_DB2160_kg": 56.0, "tanque_kg": 70.0, "mtow_pulverizacion_kg": 126.0, "empuje_max_por_eje_kg": 54.2}
HOVER_MASSES = [("vacio_56kg", 56.0), ("mtow_126kg", 126.0)]
REF = {
    "top": "geometry/models/T70P_CFD/T70P_reference/T70P_UP.png", "scale": 0.00495, "center_px": (655.3, 323.4),
    "kx": +1, "ky": +1,   # x_img = cx + ky*Y/s ; y_img = cy + kx*X/s   (frente abajo, babor a la derecha)
    "views": ["geometry/models/T70P_CFD/T70P_reference/T70P_RIGHT.png", "geometry/models/T70P_CFD/T70P_reference/T70P_REAR.png"],
}
TOPOLOGY = {"rotor_count": 4, "coaxial": False, "evidence": "DJI Academy deck 01: 'empuje de un solo eje 54.2 kg', "
            "'abrazadera oscilante (solo T70P)'; slide 11 muestra 1 helice por brazo", "classification": "P-A + S"}
NOTES = ["Bujes medidos en planta (+-1.5 %); el pivote brazo-motor queda ~6 mm mas afuera por la inclinacion.",
         "Inclinacion lateral -2.07 +- 0.3 grados (S), coherente con la medicion del propietario de 2-3 grados (M).",
         "Atomizadores opcionales: bajo los motores delanteros (O, propietario 2026-11-22); desplazamiento lateral inferido (I)."]
