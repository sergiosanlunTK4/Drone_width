"""
DJI Agras T25P — parametros del modelo CFD.  Clases: P ficha DJI | S medido en imagen oficial | I inferido.

Topologia: 4 rotores SIMPLES de 50 in (P + S, vistas UP/LEFT/FRONT). Frente = radar (vista LEFT: radar a la
izquierda, atomizadores a la derecha). 2 atomizadores estandar bajo los motores traseros, 1420 mm (P).

Fotogrametria (geometry/models/T25P_CFD/mediciones/):
  planta T25P_UP.png: escala 4.38 mm/px ajustada a helice 50 in (radio 146.1 px) + diagonal 1970 +
  sobre 2650 x 2700 -> diagonal 1972 mm (+0.1 %), sobre 2630 x 2697 mm (-0.7 % / -0.1 %).
  alturas: T25P_LEFT / T25P_FRONT, escala vertical calibrada con la altura oficial 820 mm (tapa del deposito).
  inclinacion: mediciones_inclinacion_t25p.csv -> a lo largo del brazo -1.6 +- 1.2 grados (S, impreciso: columnas
  de 30-50 px); se adopta el valor de familia -2.2 grados (I), compatible.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common as C  # noqa: E402

NAME = "T25P"
PREFIX = "t25p"
OUT_DIR = "geometry/models/T25P_CFD"

Z_ROOT_ABOVE_GROUND = 0.565
Z_GROUND = -Z_ROOT_ABOVE_GROUND


def zg(h):
    return h - Z_ROOT_ABOVE_GROUND


# ---------------- rotor / pala ----------------
ROTOR_DIAMETER = 50 * 0.0254     # 1.270 m [P]
PROP_PITCH = 18.5 * 0.0254       # paso no publicado: misma P/D que la 6223 (0.371) [I]
BLADES_PER_ROTOR = 2             # [S]
PROP_PLANE_Z = zg(0.695)         # [S]
DISK_THICKNESS = 0.035
PROP_CLAMP_DIA = 0.060
_R62 = 0.7874
BLADE_CHORD_OVER_R = [(rr, c / _R62) for rr, c in [
    (0.045, 0.040), (0.12, 0.055), (0.20, 0.075), (0.30, 0.085), (0.40, 0.083), (0.50, 0.079),
    (0.60, 0.073), (0.70, 0.067), (0.80, 0.061), (0.90, 0.052), (0.96, 0.042), (0.995, 0.025)]]  # [I, c/R de la 6223]
BLADE_THICKNESS = [(0.045, 0.35), (0.12, 0.20), (0.20, 0.14), (0.30, 0.12), (0.50, 0.10),
                   (0.70, 0.09), (0.90, 0.08), (1.00, 0.08)]
BLADE_CAMBER, BLADE_CAMBER_POS, BLADE_PITCH_AXIS = 0.04, 0.4, 0.30
PROP_CLASS = "diametro P; paso y cuerda I (proporciones de la 6223)"

# ---------------- inclinacion ----------------
MOTOR_CANT_DEG = -2.2
CANT_SOURCE = ("I: valor de familia (T70P S+M = -2.2 grados a lo largo del brazo). Medida propia (S, imprecisa): "
               "-1.6 +- 1.2 grados, compatible. mediciones/mediciones_inclinacion_t25p.csv")

# ---------------- brazos y grupo motor ----------------
ARM_DIA = 0.045
ARM_TIP_Z = zg(0.583)
ESC_BOX, ESC_AT = (0.150, 0.060, 0.050), 0.70
FOLD_SLEEVE, FOLD_AT = (0.060, 0.080), 0.15
_HX, _HYF, _HYR = 0.680, 0.712, 0.716     # bujes [S]

_GROUP = C.single_motor_group(ARM_TIP_Z, mount_box=(0.110, 0.100), mount_z=(zg(0.500), zg(0.615)),
                              bell_dia=0.130, bell_z=(zg(0.615), zg(0.665)), clamp_dia=PROP_CLAMP_DIA,
                              disk_bottom_z=PROP_PLANE_Z - DISK_THICKNESS / 2)


def _arm(aid, hx, hy, root):
    return {"id": aid, "hub_x": hx, "hub_y": hy, "hub_ref_z": PROP_PLANE_Z, "root": root, "motor_group": _GROUP}


ARMS = [
    _arm("M1_FR", +_HX, -_HYF, (+0.270, -0.245, 0.0)),
    _arm("M2_FL", +_HX, +_HYF, (+0.270, +0.245, 0.0)),
    _arm("M3_RL", -_HX, +_HYR, (-0.277, +0.250, 0.0)),
    _arm("M4_RR", -_HX, -_HYR, (-0.277, -0.250, 0.0)),
]
# Sentido de giro NO publicado para el T25P: se asume la convencion DJI tradicional (T40/T50/T100) [I]
ROTORS = [
    {"id": "M1_FR", "arm": "M1_FR", "dji_motor": 1, "role": "delantero-derecho", "level": "simple", "plane_z": PROP_PLANE_Z, "rotation": "CCW"},
    {"id": "M2_FL", "arm": "M2_FL", "dji_motor": 2, "role": "delantero-izquierdo", "level": "simple", "plane_z": PROP_PLANE_Z, "rotation": "CW"},
    {"id": "M3_RL", "arm": "M3_RL", "dji_motor": 3, "role": "trasero-izquierdo", "level": "simple", "plane_z": PROP_PLANE_Z, "rotation": "CCW"},
    {"id": "M4_RR", "arm": "M4_RR", "dji_motor": 4, "role": "trasero-derecho", "level": "simple", "plane_z": PROP_PLANE_Z, "rotation": "CW"},
]
ROTATION_SOURCE = "I: convencion DJI tradicional (como T40/T50/T100); el T70P es la excepcion documentada. VERIFICAR"

# ---------------- pulverizacion ----------------
ATOMIZER = {"stem_dia": 0.050, "ring_dia": 0.060, "bell_dia": 0.075, "bell_h": 0.045, "ring_h": 0.010}
ATOMIZER_ATTACH_Z = zg(0.500)
ATOMIZER_DISC_RADIUS = 0.030
_DISC_Z = zg(0.290)              # [S]
NOZZLES = [
    {"id": "N1_RL", "config": "std", "mount": "arm", "arm": "M3_RL", "x": -_HX, "y": +0.710, "disc_z": _DISC_Z, "cls": "P+S"},
    {"id": "N2_RR", "config": "std", "mount": "arm", "arm": "M4_RR", "x": -_HX, "y": -0.710, "disc_z": _DISC_Z, "cls": "P+S"},
    {"id": "N3_FL", "config": "opt", "mount": "arm", "arm": "M2_FL", "x": +_HX, "y": +0.706, "disc_z": _DISC_Z, "cls": "O (delante, propietario) + I (offset)"},
    {"id": "N4_FR", "config": "opt", "mount": "arm", "arm": "M1_FR", "x": +_HX, "y": -0.706, "disc_z": _DISC_Z, "cls": "O (delante, propietario) + I (offset)"},
]
AIRFRAME_NOZZLE_CONFIGS = ("std",)
SPRAY = {"atomizer_model": "LX07550SX", "nozzle_spacing_official_m": 1.420,
         "flow_L_min": {"2_boquillas": 16.0, "4_boquillas": 24.0}, "droplet_um": [50, 500]}

# ---------------- cuerpo [S] ----------------
_RR = {"x": -0.400, "z": zg(0.140), "dia": 0.100, "len": 0.120}
BODY = [
    C.box((-0.450, 0.420), (0.185, 0.225), (-0.020, 0.020)),
    C.box((-0.450, 0.420), (-0.225, -0.185), (-0.020, 0.020)),
    C.box((-0.297, -0.257), (-0.270, 0.270), (-0.020, 0.020)),
    C.box((0.250, 0.290), (-0.265, 0.265), (-0.020, 0.020)),
] + [C.boxc(a["root"][0], a["root"][1], 0.0, 0.080, 0.072, 0.060) for a in ARMS] + [
    C.box((-0.450, -0.090), (-0.190, 0.190), (zg(0.500), zg(0.650)), chamfer=0.030),   # bateria + avionica (base)
    C.box((-0.420, -0.120), (-0.110, 0.110), (zg(0.640), zg(0.730)), chamfer=0.030),   # parte central alta (bajo las helices no)
    C.box((-0.120, 0.170), (-0.200, 0.200), (zg(0.550), zg(0.790)), fillet=0.030),     # deposito 20 L
    C.loft([{"x": (-0.060, 0.100), "y": 0.120, "z": zg(0.330)},
            {"x": (-0.100, 0.150), "y": 0.180, "z": zg(0.570)}]),
    C.cylz(0.050, 0.120, 0.090, zg(0.780), zg(0.820)),                                  # tapa (altura oficial 820)
    C.box((0.170, 0.420), (-0.210, 0.210), (zg(0.450), zg(0.640)), chamfer=0.040),     # carcasa delantera
    C.cylz(0.300, 0.0, 0.130, zg(0.640), zg(0.780)),                                   # radar
    C.box((0.360, 0.420), (-0.050, 0.050), (zg(0.290), zg(0.470))),                     # foco / FPV
    C.box((-0.060, 0.100), (-0.100, 0.100), (zg(0.270), zg(0.360))),                    # bombas
    C.cyl((_RR["x"], -_RR["len"] / 2, _RR["z"]), (0, 1, 0), _RR["dia"], _RR["len"]),    # radar inferior
]
_GD = 0.030
_REAR_LEG = {"bottom_x": -0.450, "top_x": -0.300, "top_z": zg(0.520)}
GEAR = C.u_gear(skid_y=0.250, skid_x=(-0.500, 0.360), skid_z=zg(_GD / 2), tube_dia=_GD, leg_top_y=0.225,
                rear_leg=_REAR_LEG, front_leg={"bottom_x": 0.300, "top_x": 0.220, "top_z": zg(0.500)},
                rail_y=0.205, crossbar_z=zg(0.220))
_f = (zg(0.220) - zg(_GD / 2)) / (_REAR_LEG["top_z"] - zg(_GD / 2))
GEAR.append(C.tube((_REAR_LEG["bottom_x"] + _f * (_REAR_LEG["top_x"] - _REAR_LEG["bottom_x"]), 0, zg(0.220)),
                   (_RR["x"], 0, _RR["z"]), 0.025))

OFFICIAL = {"wheelbase_m": 1.970, "envelope_m": [2.650, 2.700], "height_m": 0.820, "nozzle_spacing_m": 1.420}
MASS = {"con_bateria_kg": 33.0, "sin_bateria_kg": 26.0, "tanque_kg": 20.0, "mtow_pulverizacion_kg": 53.0}
HOVER_MASSES = [("vacio_33kg", 33.0), ("mtow_53kg", 53.0)]
REF = {"top": "geometry/models/T25P_CFD/T25P_reference/T25P_UP.png", "scale": 0.00438, "center_px": (654.75, 346.4),
       "kx": +1, "ky": +1,
       "views": ["geometry/models/T25P_CFD/T25P_reference/T25P_LEFT.png",
                 "geometry/models/T25P_CFD/T25P_reference/T25P_FRONT.png"]}
TOPOLOGY = {"rotor_count": 4, "coaxial": False, "evidence": "vistas oficiales UP/LEFT/FRONT: 1 helice por brazo",
            "classification": "S"}
NOTES = ["Planta medida en T25P_UP (+-1.5 %); casi simetrica: vias 1.424 m (del.) / 1.432 m (tras.), batalla 1.360 m.",
         "Paso de helice no publicado: se usa P/D de la 6223 (I). Sentido de giro asumido (I): VERIFICAR.",
         "Inclinacion: valor de familia -2.2 grados (I); medida propia -1.6 +- 1.2 grados (S).",
         "Atomizadores opcionales: bajo los motores delanteros (O, propietario 2026-11-22); desplazamiento lateral inferido (I)."]
