"""
DJI Agras T100 — parametros del modelo CFD.  Clases: P ficha | P-A Academy | M/O propietario | S imagen | I inferido.

Topologia: 4 PARES COAXIALES = 8 rotores 6223 (P-A: "helices duales coaxiales", sin abrazadera oscilante).
Barra trasera LS100 con 4 atomizadores (P). Frente = radar (cilindro alto); deposito 100 L atras.

Valores del PROPIETARIO que se conservan (clase M, evidence/VALIDACION_modelo_T100.md):
  bujes (+-0.8238, +-0.8238) (coinciden con la diagonal 2330 y con la planta T100_UP: radio de helice 404 px ->
  1.95 mm/px vs 1.97 de los bujes), separacion coaxial 0.290 m (S en T100_REAR: 0.29 m), planos Z = +-0.145,
  suelo Z = -0.625, altura 0.975, atomizadores (X -0.875/-0.775, Y +-0.917/+-0.4585, Z -0.448), giro por rotor.
  El modelo anterior tenia la terna levogira (+Y estribor): aqui se respetan los NOMBRES (FR = delantero-derecho)
  en una terna dextrogira (+Y babor).
Cambios por fotogrametria (S) donde el modelo anterior no coincide con las imagenes:
  tren: patines en Y = +-0.375 y X -0.45..+0.30 (antes 1.10 x 1.15 m).
  marco vertical: plano medio coaxial a 0.73 m del suelo (antes 0.625).
Inclinacion: T100_REAR, columnas coaxiales (franja entre helices), lateral -2.17 +- 0.3 grados (S) en los brazos
  traseros (|u_y| = 0.654) -> -3.3 grados a lo largo del brazo.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common as C  # noqa: E402

NAME = "T100"
PREFIX = "t100"
OUT_DIR = "geometry/models/T100_CFD"

# Marco vertical [S]: T100_REAR (0.743) y T100_RIGHT (0.720) -> plano medio coaxial a 0.73 m del suelo; radar a
# +0.25 m; suma 0.975 m = altura oficial. El modelo anterior usaba suelo a -0.625 / radar a +0.35 (misma altura
# total pero con los rotores 0.11 m mas bajos), incompatible con las imagenes (el deposito cortaria la helice).
Z_ROOT_ABOVE_GROUND = 0.730
Z_GROUND = -Z_ROOT_ABOVE_GROUND

ROTOR_DIAMETER = 1.5748
PROP_PITCH = 23 * 0.0254
BLADES_PER_ROTOR = 2
GAP = 0.290                      # [M + S]
UPPER_Z, LOWER_Z = +GAP / 2, -GAP / 2
DISK_THICKNESS = 0.040
PROP_CLAMP_DIA = 0.080
_R62 = 0.7874
BLADE_CHORD_OVER_R = [(rr, c / _R62) for rr, c in [
    (0.045, 0.040), (0.12, 0.055), (0.20, 0.075), (0.30, 0.085), (0.40, 0.083), (0.50, 0.079),
    (0.60, 0.073), (0.70, 0.067), (0.80, 0.061), (0.90, 0.052), (0.96, 0.042), (0.995, 0.025)]]
BLADE_THICKNESS = [(0.045, 0.35), (0.12, 0.20), (0.20, 0.14), (0.30, 0.12), (0.50, 0.10),
                   (0.70, 0.09), (0.90, 0.08), (1.00, 0.08)]
BLADE_CAMBER, BLADE_CAMBER_POS, BLADE_PITCH_AXIS = 0.04, 0.4, 0.30

MOTOR_CANT_DEG = -3.3
CANT_SOURCE = "S: mediciones/mediciones_inclinacion_t100.csv (lateral -2.17 +- 0.3, brazos traseros |u_y| 0.654)"

ARM_DIA = 0.060                  # radio 0.03 [M]
ARM_TIP_Z = 0.0                  # brazos horizontales; el par coaxial se monta a la altura del brazo [S]
ESC_BOX, ESC_AT = (0.200, 0.100, 0.080), 0.72
FOLD_SLEEVE, FOLD_AT = (0.080, 0.110), 0.12
_H = 0.8238                      # [M/P]

_GROUP = C.coaxial_motor_group(ARM_TIP_Z, mount_box=(0.170, 0.150), mount_z=(-0.060, 0.060), bell_dia=0.200,
                               upper_bell_z=(0.045, 0.110), lower_bell_z=(-0.110, -0.045), clamp_dia=PROP_CLAMP_DIA,
                               upper_disk_bottom_z=UPPER_Z - DISK_THICKNESS / 2,
                               lower_disk_top_z=LOWER_Z + DISK_THICKNESS / 2)


def _arm(aid, hx, hy, root):
    return {"id": aid, "hub_x": hx, "hub_y": hy, "hub_ref_z": UPPER_Z, "root": root, "motor_group": _GROUP}


ARMS = [
    _arm("M1_FR", +_H, -_H, (+0.247, -0.206, 0.0)),
    _arm("M4_FL", +_H, +_H, (+0.247, +0.206, 0.0)),
    _arm("M3_RL", -_H, +_H, (-0.086, +0.206, 0.0)),
    _arm("M2_RR", -_H, -_H, (-0.086, -0.206, 0.0)),
]


def _pair(arm, role, up_rot, num):
    lo_rot = "CW" if up_rot == "CCW" else "CCW"
    return [
        {"id": f"{arm}_upper", "arm": arm, "dji_motor": num, "role": role, "level": "upper", "plane_z": UPPER_Z, "rotation": up_rot},
        {"id": f"{arm}_lower", "arm": arm, "dji_motor": num, "role": role, "level": "lower", "plane_z": LOWER_Z, "rotation": lo_rot},
    ]


ROTORS = (_pair("M1_FR", "delantero-derecho", "CCW", 1) + _pair("M2_RR", "trasero-derecho", "CW", 2) +
          _pair("M3_RL", "trasero-izquierdo", "CCW", 3) + _pair("M4_FL", "delantero-izquierdo", "CW", 4))
ROTATION_SOURCE = "M (modelo del propietario, por nombre de rotor) + P-A ('igual que T40/T50')"

# ---------------- pulverizacion: barra LS100 ----------------
ATOMIZER = {"stem_dia": 0.060, "ring_dia": 0.072, "bell_dia": 0.095, "bell_h": 0.055, "ring_h": 0.010}
ATOMIZER_ATTACH_Z = -0.390
ATOMIZER_DISC_RADIUS = 0.035
_BOOM_Z = -0.390                 # [S, T100_REAR -0.41 / T100_RIGHT -0.37]
_NZ = -0.448                     # [M]; imagenes -0.47 / -0.49 (S): coherente
NOZZLES = [
    {"id": "N1_left_outer", "config": "std", "mount": "body", "x": -0.875, "y": +0.917, "disc_z": _NZ, "attach_z": _BOOM_Z, "cls": "M"},
    {"id": "N4_right_outer", "config": "std", "mount": "body", "x": -0.875, "y": -0.917, "disc_z": _NZ, "attach_z": _BOOM_Z, "cls": "M"},
    {"id": "N2_left_inner", "config": "opt", "mount": "body", "x": -0.775, "y": +0.4585, "disc_z": _NZ, "attach_z": _BOOM_Z, "cls": "M"},
    {"id": "N3_right_inner", "config": "opt", "mount": "body", "x": -0.775, "y": -0.4585, "disc_z": _NZ, "attach_z": _BOOM_Z, "cls": "M"},
]
AIRFRAME_NOZZLE_CONFIGS = ("std", "opt")      # la barra LS100 lleva los 4 cuerpos
SPRAY = {"atomizer_model": "LX07550SX (estandar) / LX09510DX (niebla, opcional)", "boom": "LS100",
         "nozzle_spacing_official_m": 1.834, "flow_L_min": {"2_boquillas": 30.0, "4_boquillas": 40.0},
         "droplet_um": [50, 500]}

# ---------------- cuerpo [S: T100_UP 1.96 mm/px, T100_REAR / T100_RIGHT] ----------------
_BD = 0.030
_boom = []
for s in (+1, -1):
    pts = [(-0.380, s * 0.230, _BOOM_Z), (-0.775, s * 0.4585, _BOOM_Z), (-0.875, s * 0.917, _BOOM_Z)]
    _boom += [C.tube(a, b, _BD) for a, b in zip(pts[:-1], pts[1:])]
    _boom.append(C.tube((-0.380, s * 0.230, _BOOM_Z), (-0.240, s * 0.120, -0.300), 0.026))
    _boom.append(C.boxc(-0.380, s * 0.230, _BOOM_Z, 0.060, 0.060, 0.060))   # nudo: envuelve los extremos de los tubos
BODY = [
    C.box((-0.420, 0.430), (0.225, 0.265), (-0.025, 0.025)),
    C.box((-0.420, 0.430), (-0.265, -0.225), (-0.025, 0.025)),
] + [C.boxc(a["root"][0], a["root"][1], 0.0, 0.100, 0.090, 0.080) for a in ARMS] + [
    C.box((-0.400, -0.020), (-0.260, 0.260), (-0.200, 0.077), vchamfer=0.120),        # deposito 100 L (hexagonal en planta)
    C.loft([{"x": (-0.250, 0.150), "y": 0.150, "z": -0.580},
            {"x": (-0.340, 0.200), "y": 0.215, "z": -0.170}]),                        # cuerpo inferior del deposito (solapa con el superior)
    C.cylz(-0.240, 0.0, 0.160, 0.060, 0.095),
    C.box((-0.100, 0.400), (-0.240, 0.240), (-0.115, 0.075), chamfer=0.060),         # bateria + avionica
    C.cylz(0.250, 0.0, 0.100, 0.060, 0.245),                                        # radar, tope 975 mm [P]
    C.cylz(0.250, 0.0, 0.150, 0.060, 0.100),
    C.cylz(0.330, 0.0, 0.180, -0.200, -0.105),                                      # domo inferior delantero
    C.box((-0.240, -0.040), (-0.100, 0.100), (-0.600, -0.500)),                     # bombas / caudalimetro
] + _boom
_GD = 0.040
GEAR = C.u_gear(skid_y=0.375, skid_x=(-0.450, 0.300), skid_z=Z_GROUND + _GD / 2, tube_dia=_GD, leg_top_y=0.300,
                rear_leg={"bottom_x": -0.400, "top_x": -0.100, "top_z": -0.120},
                front_leg={"bottom_x": 0.260, "top_x": 0.190, "top_z": -0.140},
                rail_y=0.245, crossbar_z=None)

OFFICIAL = {"wheelbase_m": 2.330, "envelope_m": [3.220, 3.224], "height_m": 0.975, "nozzle_spacing_m": 1.834}
MASS = {"pulverizacion_2boq_kg": 75.0, "tanque_kg": 100.0, "mtow_pulverizacion_kg": 175.0, "empuje_max_por_brazo_kg": 82.0}
HOVER_MASSES = [("vacio_75kg", 75.0), ("mtow_175kg", 175.0)]
REF = {"top": "geometry/models/T100_CFD/reference/T100_UP.png", "scale": 0.001966, "center_px": (870.0, 839.0),
       "kx": +1, "ky": +1,
       "views": ["geometry/models/T100_CFD/reference/T100_RIGHT.png", "geometry/models/T100_CFD/reference/T100_REAR.png"]}
TOPOLOGY = {"rotor_count": 8, "coaxial": True, "coaxial_gap_m": GAP,
            "evidence": "DJI Academy: 'helices duales coaxiales'; propietario (M); T100_REAR (S)", "classification": "P-A + M + S"}
NOTES = ["Terna corregida a dextrogira (+Y babor); los nombres de rotor (FR, RR, RL, FL) se respetan.",
         "Marco vertical por imagenes (S): plano medio coaxial a 0.73 m del suelo (modelo anterior: 0.625 m).",
         "Tren: patines en Y = +-0.375 m segun las imagenes (S); el modelo anterior tenia 1.10 x 1.15 m.",
         "Atomizadores: posiciones del propietario (M). En T100_UP/T100_RIGHT los discos parecen estar en X ~ -0.60 a -0.65 "
         "(S): CONFIRMAR, es la cota mas sensible para la deposicion.",
         "Inclinacion medida en las columnas coaxiales traseras: -3.3 grados a lo largo del brazo (S)."]
