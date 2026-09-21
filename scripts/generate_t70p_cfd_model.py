"""
Generador del Modelo 3D de Alta Fidelidad y Coordenadas CFD del DJI Agras T70P.

Diseñado específicamente para simulaciones de aerodinámica (CFD), campo de downwash
e inyección lagrangiana de gotas (simulación de deposición y deriva).

Fuentes y clasificaciones metrológicas:
  - [P]   Ficha técnica oficial DJI Agras T70P (ag.dji.com/es/T70P/specs)
  - [P-A] DJI Academy / UTC "01 Conocimiento básico de un Dron" (diapositivas oficiales)
  - [S]   Evidencia visual directa en imágenes oficiales sin escala (hecho discreto, no dimensión)
  - [O]   Medición directa del investigador sobre el croquis dimensional propio (Boceto 2)
  - [I]   Inferencia / estimación razonada
  - [D]   Dato faltante / pendiente de medición

CONSIDERACIÓN ESPECIAL — INCLINACIÓN DE MOTORES (MOTOR TILT):
  El T70P incorpora una abrazadera de hélice oscilante (swing-clamp) que permite
  que el eje del motor/rotor esté inclinado HACIA AFUERA respecto a la vertical
  (outward radial cant). Este ángulo de inclinación fue medido por análisis pixel
  sobre las imágenes oficiales (vista trasera/frontal) y se estima en ~8.9°.

  IMPACTO CFD CRÍTICO:
    - El vector normal del disco actuador NO es [0, 0, 1], sino que tiene
      componente radial hacia afuera del centro del dron.
    - El vector de downwash/empuje NO es perfectamente vertical; tiene una
      componente centrífuga hacia el exterior.
    - Para actuationDiskSource en OpenFOAM, usar "diskNormal" = normal_vector
      calculado según la posición y ángulo de tilt del brazo.
    - Corrección de empuje vertical: T_z = T_total * cos(tilt_deg) = T * 0.9880

NOTA SOBRE CONFIGURACIÓN COAXIAL:
  El manifiesto t70p_geometry_manifest.json (v2.0) clasifica la topología como
  coaxial=true (S) con 8 rotores totales, basado en imágenes de DJI Academy que
  muestran pares coaxiales. Sin embargo, el Boceto 2 del investigador muestra
  solo 4 posiciones de brazo. Este script modela la configuración COAXIAL (2 rotores
  por brazo, 8 en total) con separación axial estimada, consistente con el manifiesto.

CONVENCIÓN DE ROTACIÓN (ADVERTENCIA OFICIAL DJI):
  ¡IMPORTANTE! La rotación del propulsor T70P es OPUESTA a la de los cuadricópteros
  tradicionales:
    Motor 1 (M1, FR) → CW (sentido horario)
    Motor 2 (M2, RR) → CCW (sentido antihorario)
    Motor 3 (M3, FL) → CW (sentido horario)
    Motor 4 (M4, RL) → CCW (sentido antihorario)
  Fuente: DJI Academy, "01 Conocimiento básico de un Dron" [P-A]

Salidas generadas en geometry/models/T70P_CFD/:
  1. t70p_cfd_coordinates.json  -> Catálogo exhaustivo de coordenadas 3D y parámetros de inyección
  2. t70p_airframe.stl          -> Superficies sólidas impermeables (fuselaje, brazos, tren, carcasas)
  3. t70p_rotor_disks.stl       -> 8 discos actuadores inclinados (MRF / actuationDiskSource)
  4. t70p_spray_nozzles.stl     -> Discos marcadores de puntos de inyección Lagrangiana
  5. t70p_full_assembly.stl     -> Ensamblaje completo unificado
  6. t70p_geometry_verification.png -> Gráfico de control ortográfico multieje
"""
from __future__ import annotations

import json
import math
import struct
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "geometry" / "models" / "T70P_CFD"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ==============================================================================
# 1. PARÁMETROS GEOMÉTRICOS Y METROLÓGICOS DEL DJI AGRAS T70P
# ==============================================================================
# Sistema de Coordenadas:
#   Origen (0, 0, 0): Centro geométrico del bastidor en el plano de los brazos
#   +X: Hacia adelante (dirección de vuelo frontal)
#   +Y: Hacia la derecha (estribor)
#   +Z: Hacia arriba

# --- DIMENSIONES GENERALES [P] ---
WHEELBASE_DIAG_M = 2.440          # 2440 mm diagonal entre ejes [P]
TOTAL_HEIGHT_M   = 0.960          # 960 mm (con tren de aterrizaje) [P]
UNFOLDED_MM      = [3200, 3520, 960]  # Desplegado oficial [P-A]

# --- DIÁMETRO DE ROTOR [P-A] ---
# Hélice 6223 (62 pulgadas × 23 pulgadas de paso), fibra de carbono
ROTOR_DIAMETER_M = 1.574          # 62 in = 1574 mm [P-A]
ROTOR_RADIUS_M   = ROTOR_DIAMETER_M / 2.0   # 0.787 m
ROTOR_DISK_THICKNESS_M = 0.040   # 40 mm espesor de celda de disco actuador [I]

# --- CONFIGURACIÓN COAXIAL [S] ---
# El manifiesto v2.0 clasifica coaxial=True, 8 rotores totales.
# La separación axial (gap) entre el rotor superior e inferior en cada brazo
# es un dato pendiente de medición [D]; se estima a partir de análisis visual.
COAXIAL_GAP_M   = 0.280          # Separación axial estimada entre planos coaxiales [I]
ROTOR_UPPER_Z_M = +COAXIAL_GAP_M / 2.0   # +0.140 m
ROTOR_LOWER_Z_M = -COAXIAL_GAP_M / 2.0   # -0.140 m

# --- INCLINACIÓN DE MOTORES (MOTOR TILT) [S → medición pixel ~8.9°] ---
# Los motores están inclinados RADIALMENTE hacia afuera (outward cant).
# Medición pixel sobre vista frontal oficial: ~8.9°
# Este ángulo afecta DIRECTAMENTE el vector de empuje y downwash en CFD.
MOTOR_TILT_DEG  = 8.9            # Grados de inclinación outward [S]
MOTOR_TILT_RAD  = math.radians(MOTOR_TILT_DEG)

# --- POSICIONES DE MOTORES [O] — Boceto 2, mediciones del investigador ---
# Coordenadas XY de los ejes de motor desde el centro geométrico del dron
# NOTA: La geometría es ASIMÉTRICA. Los brazos frontales y traseros tienen
#       diferente longitud y ángulo. NO es un cuadrado de 45° simétrico.
#
# Motor  | ID  | X (m)  | Y (m)  | Brazo | Rotación
# --------|-----|--------|--------|-------|----------
# Frontal Der (FR) | M1 | +0.961 | +0.270 | BR_FR | CW  [P-A]
# Frontal Izq (FL) | M3 | -0.961 | +0.270 | BR_FL | CW  [P-A]
# Trasero Der (RR) | M2 | +0.865 | -1.280 | BR_RR | CCW [P-A]
# Trasero Izq (RL) | M4 | -0.865 | -1.280 | BR_RL | CCW [P-A]
#
# Las posiciones Y positivas están hacia ADELANTE del dron (+X frontal, +Y derecha)
# NOTA: Las coordenadas del boceto usan +Y hacia arriba en el croquis (= +X frontal aquí).
# Reinterpretando el boceto con nuestra convención (+X adelante, +Y derecha):
#   - Distancia "horizontal" del boceto = eje Y del dron (lateral)
#   - Distancia "vertical" del boceto = eje X del dron (longitudinal)
#   * Y_motor_boceto → X_dron : FRx = +0.27 m (frontal), RRx = -1.28 m (trasero)
#   * X_motor_boceto → Y_dron : FRy = +0.961 m (derecha), FLy = -0.961 m (izquierda)
#
ARM_POSITIONS = {
    "M1_FR": {"x_m": +0.270, "y_m": +0.961, "rotation_upper": "CW",  "rotation_lower": "CCW", "arm_num": 1},
    "M3_FL": {"x_m": +0.270, "y_m": -0.961, "rotation_upper": "CW",  "rotation_lower": "CCW", "arm_num": 3},
    "M2_RR": {"x_m": -1.280, "y_m": +0.865, "rotation_upper": "CCW", "rotation_lower": "CW",  "arm_num": 2},
    "M4_RL": {"x_m": -1.280, "y_m": -0.865, "rotation_upper": "CCW", "rotation_lower": "CW",  "arm_num": 4},
}

# --- RADIO DE MOTOR POD (CARCASA) [O] ---
MOTOR_POD_RADIUS_M = 0.160       # Ø0.32 m / 2 [O]
MOTOR_POD_HEIGHT_M = 0.280       # Estimado de imagen lateral [I]

# --- RADIO DE TUBO DE BRAZO [I] ---
ARM_TUBE_RADIUS_M  = 0.028       # Estimado 56 mm diámetro exterior [I]

# --- ALTURAS GENERALES [I/P] ---
# El T70P tiene altura oficial 960 mm. El tren es de skid circular/ovalado.
LIDAR_TOP_Z_M   = +0.350         # Cúspide del domo LiDAR / sensor [I]
SKID_BOTTOM_Z_M = -0.610         # Base de patín en el suelo [I]
# Verificación: LIDAR_TOP - SKID_BOTTOM = 0.960 m = 960 mm ✓

# --- SISTEMA DE PULVERIZACIÓN [P] ---
# T70P: 2 boquillas estándar (configuración mínima), 4 opcionales
# Separación entre boquillas: 1874 mm [P]
NOZZLE_STD_COUNT      = 2
NOZZLE_SPACING_M      = 1.8740   # 1874 mm separación par estándar [P]
# Las boquillas cuelgan debajo de los brazos traseros (visibles en vista frontal/trasera)
# Posición X longitudinal estimada en la mitad del brazo trasero [I]
NOZZLE_X_M     = -0.600          # X longitudinal (trasero) [I]
NOZZLE_Z_M     = -0.390          # Z vertical (colgando del brazo) [I]
# Separación en Y: la spec indica 1874 mm total entre las 2 boquillas estándar
NOZZLE_Y_RIGHT = +NOZZLE_SPACING_M / 2.0   # +0.937 m
NOZZLE_Y_LEFT  = -NOZZLE_SPACING_M / 2.0   # -0.937 m

# ==============================================================================
# 2. FUNCIÓN ESPECIAL: VECTOR NORMAL DE ROTOR INCLINADO
# ==============================================================================

def rotor_normal_vector(arm_x_m: float, arm_y_m: float, tilt_deg: float) -> list:
    """
    Calcula el vector normal unitario del disco de rotor con inclinación outward.

    La inclinación (cant/tilt) es RADIAL: el eje del motor se aleja del centro
    del dron en la dirección del brazo, inclinándose hacia afuera.

    Parámetros
    ----------
    arm_x_m  : coordenada X del motor respecto al centro
    arm_y_m  : coordenada Y del motor respecto al centro
    tilt_deg : ángulo de inclinación outward en grados

    Retorna
    -------
    [nx, ny, nz] : vector normal unitario del disco de rotor (apunta hacia arriba+afuera)
    """
    arm_angle_rad = math.atan2(arm_y_m, arm_x_m)   # ángulo del brazo en plano XY
    tilt_rad = math.radians(tilt_deg)
    nx = math.sin(tilt_rad) * math.cos(arm_angle_rad)
    ny = math.sin(tilt_rad) * math.sin(arm_angle_rad)
    nz = math.cos(tilt_rad)
    return [round(nx, 6), round(ny, 6), round(nz, 6)]


def rotor_disk_vertices_tilted(
    cx: float, cy: float, cz: float,
    radius: float, thickness: float,
    arm_x: float, arm_y: float,
    tilt_deg: float, nseg: int = 48
) -> list:
    """
    Genera un disco cilíndrico inclinado (motor tilt) como lista de triángulos.

    El disco se construye con su eje orientado según el vector normal del rotor
    inclinado, en lugar del eje Z puro. Esto es la representación correcta del
    disco actuador de cada rotor del T70P en CFD.
    """
    # Vector normal del rotor inclinado
    n = np.array(rotor_normal_vector(arm_x, arm_y, tilt_deg))
    n = n / np.linalg.norm(n)  # normalizar

    # Construir base ortonormal local (u, w) perpendicular a n
    arb = np.array([1.0, 0.0, 0.0]) if abs(n[0]) < 0.85 else np.array([0.0, 1.0, 0.0])
    u = np.cross(n, arb)
    u = u / np.linalg.norm(u)
    w = np.cross(n, u)
    w = w / np.linalg.norm(w)

    center = np.array([cx, cy, cz])
    half_t = thickness / 2.0

    # Centros de las tapas
    top_c = center + half_t * n
    bot_c = center - half_t * n

    angles = np.linspace(0, 2 * math.pi, nseg, endpoint=False)
    top_ring = [top_c + radius * (math.cos(a) * u + math.sin(a) * w) for a in angles]
    bot_ring = [bot_c + radius * (math.cos(a) * u + math.sin(a) * w) for a in angles]

    tris = []
    for i in range(nseg):
        j = (i + 1) % nseg
        tris.append((top_c, top_ring[i], top_ring[j]))
        tris.append((bot_c, bot_ring[j], bot_ring[i]))
        tris.append((top_ring[i], bot_ring[i], bot_ring[j]))
        tris.append((top_ring[i], bot_ring[j], top_ring[j]))
    return tris


# ==============================================================================
# 3. PRIMITIVAS GEOMÉTRICAS (STL)
# ==============================================================================

def normalize(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else np.zeros_like(v)

def calc_normal(p1: np.ndarray, p2: np.ndarray, p3: np.ndarray) -> np.ndarray:
    u = p2 - p1
    v = p3 - p1
    return normalize(np.cross(u, v))

def make_box(cx: float, cy: float, cz: float, dx: float, dy: float, dz: float) -> list:
    """Caja ortogonal cerrada orientada según ejes."""
    hx, hy, hz = dx / 2.0, dy / 2.0, dz / 2.0
    corners = np.array([
        [cx - hx, cy - hy, cz - hz],
        [cx + hx, cy - hy, cz - hz],
        [cx + hx, cy + hy, cz - hz],
        [cx - hx, cy + hy, cz - hz],
        [cx - hx, cy - hy, cz + hz],
        [cx + hx, cy - hy, cz + hz],
        [cx + hx, cy + hy, cz + hz],
        [cx - hx, cy + hy, cz + hz],
    ])
    faces = [
        (0, 2, 1), (0, 3, 2),
        (4, 5, 6), (4, 6, 7),
        (0, 1, 5), (0, 5, 4),
        (2, 3, 7), (2, 7, 6),
        (1, 2, 6), (1, 6, 5),
        (3, 0, 4), (3, 4, 7),
    ]
    return [(corners[i], corners[j], corners[k]) for i, j, k in faces]

def make_cylinder_z(cx: float, cy: float, cz: float, r: float, h: float, nseg: int = 36) -> list:
    """Cilindro vertical cerrado con tapas."""
    tris = []
    hz = h / 2.0
    top_c = np.array([cx, cy, cz + hz])
    bot_c = np.array([cx, cy, cz - hz])
    angles = np.linspace(0, 2 * np.pi, nseg, endpoint=False)
    top_ring = [np.array([cx + r * np.cos(a), cy + r * np.sin(a), cz + hz]) for a in angles]
    bot_ring = [np.array([cx + r * np.cos(a), cy + r * np.sin(a), cz - hz]) for a in angles]
    for i in range(nseg):
        j = (i + 1) % nseg
        tris.append((top_c, top_ring[i], top_ring[j]))
        tris.append((bot_c, bot_ring[j], bot_ring[i]))
        tris.append((top_ring[i], bot_ring[i], bot_ring[j]))
        tris.append((top_ring[i], bot_ring[j], top_ring[j]))
    return tris

def make_frustum_z(cx: float, cy: float, cz_bot: float, cz_top: float,
                   r_bot: float, r_top: float, nseg: int = 36) -> list:
    """Tronco de cono cerrado orientado en Z."""
    tris = []
    top_c = np.array([cx, cy, cz_top])
    bot_c = np.array([cx, cy, cz_bot])
    angles = np.linspace(0, 2 * np.pi, nseg, endpoint=False)
    top_ring = [np.array([cx + r_top * np.cos(a), cy + r_top * np.sin(a), cz_top]) for a in angles]
    bot_ring = [np.array([cx + r_bot * np.cos(a), cy + r_bot * np.sin(a), cz_bot]) for a in angles]
    for i in range(nseg):
        j = (i + 1) % nseg
        if r_top > 1e-4:
            tris.append((top_c, top_ring[i], top_ring[j]))
        if r_bot > 1e-4:
            tris.append((bot_c, bot_ring[j], bot_ring[i]))
        tris.append((top_ring[i], bot_ring[i], bot_ring[j]))
        tris.append((top_ring[i], bot_ring[j], top_ring[j]))
    return tris

def make_tube(p1: np.ndarray, p2: np.ndarray, r: float, nseg: int = 18) -> list:
    """Tubo cilíndrico cerrado entre dos puntos arbitrarios p1 y p2."""
    v = p2 - p1
    L = np.linalg.norm(v)
    if L < 1e-6:
        return []
    v_dir = v / L
    arb = np.array([1.0, 0.0, 0.0]) if abs(v_dir[0]) < 0.85 else np.array([0.0, 1.0, 0.0])
    u = normalize(np.cross(v_dir, arb))
    w = normalize(np.cross(v_dir, u))
    angles = np.linspace(0, 2 * np.pi, nseg, endpoint=False)
    c1 = [p1 + r * (np.cos(a) * u + np.sin(a) * w) for a in angles]
    c2 = [p2 + r * (np.cos(a) * u + np.sin(a) * w) for a in angles]
    tris = []
    for i in range(nseg):
        j = (i + 1) % nseg
        tris.append((p1, c1[j], c1[i]))
        tris.append((p2, c2[i], c2[j]))
        tris.append((c1[i], c2[i], c2[j]))
        tris.append((c1[i], c2[j], c1[j]))
    return tris

def write_stl_binary(path: Path, triangles: list, header_text: str = "DJI Agras T70P CFD") -> None:
    """Escribe archivo STL binario compatible con OpenFOAM/Paraview."""
    header = header_text.encode("utf-8")[:80].ljust(80, b"\x00")
    num_triangles = len(triangles)
    with open(path, "wb") as f:
        f.write(header)
        f.write(struct.pack("<I", num_triangles))
        for p1, p2, p3 in triangles:
            n = calc_normal(np.array(p1), np.array(p2), np.array(p3))
            data = struct.pack(
                "<12fH",
                float(n[0]), float(n[1]), float(n[2]),
                float(p1[0]), float(p1[1]), float(p1[2]),
                float(p2[0]), float(p2[1]), float(p2[2]),
                float(p3[0]), float(p3[1]), float(p3[2]),
                0
            )
            f.write(data)

def write_stl_ascii(path: Path, name: str, triangles: list) -> None:
    """Escribe STL ASCII estándar con normales unitarias calculadas."""
    lines = [f"solid {name}"]
    for a, b, c in triangles:
        n = calc_normal(np.array(a), np.array(b), np.array(c))
        lines.append(f"  facet normal {n[0]:.6e} {n[1]:.6e} {n[2]:.6e}")
        lines.append("    outer loop")
        for v in (a, b, c):
            lines.append(f"      vertex {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}")
        lines.append("    endloop")
        lines.append("  endfacet")
    lines.append(f"endsolid {name}")
    path.write_text("\n".join(lines), encoding="utf-8")


# ==============================================================================
# 4. CONSTRUCCIÓN DEL MODELO T70P
# ==============================================================================

def generate_t70p_cfd_dataset():
    print("=" * 80)
    print("INICIANDO MODELADO GEOMÉTRICO 3D DEL DJI AGRAS T70P PARA CFD")
    print("=" * 80)
    print(f"[!] MOTOR TILT: {MOTOR_TILT_DEG}° outward radial (vector normal ≠ [0,0,1])")
    print(f"[!] BRAZOS ASIMÉTRICOS: no es 45° — FR/FL Y=±0.961m, RR/RL Y=±0.865m")
    print()

    airframe_tris    = []
    rotor_disks_tris = []
    spray_nozzles_tris = []
    rotors_data      = []
    arms_data        = {}

    # --------------------------------------------------------------------------
    # A. BRAZOS, CARCASAS DE MOTOR Y DISCOS ACTUADORES
    # --------------------------------------------------------------------------
    body_radius = 0.22    # radio del fuselaje central

    for arm_id, apos in ARM_POSITIONS.items():
        ex, ey = apos["x_m"], apos["y_m"]
        ez = 0.0

        # Vector de dirección del brazo en plano XY
        arm_len = math.sqrt(ex**2 + ey**2)
        arm_angle_rad = math.atan2(ey, ex)
        arm_angle_deg = math.degrees(arm_angle_rad)

        # Punto de inicio del brazo en la pared del fuselaje central
        sx = body_radius * math.cos(arm_angle_rad)
        sy = body_radius * math.sin(arm_angle_rad)
        sz = 0.0

        p_start = np.array([sx, sy, sz])
        p_end   = np.array([ex, ey, ez])

        # Calcular vector normal del rotor inclinado
        norm_vec = rotor_normal_vector(ex, ey, MOTOR_TILT_DEG)
        # Vector de empuje (downwash): opuesto al normal outward
        thrust_vec = [-norm_vec[0], -norm_vec[1], -norm_vec[2]]
        # Corrección vertical del empuje por tilt
        thrust_z_correction = round(math.cos(MOTOR_TILT_RAD), 6)

        arms_data[arm_id] = {
            "arm_id": arm_id,
            "motor_num": apos["arm_num"],
            "axis_center_m": [round(ex, 4), round(ey, 4), round(ez, 4)],
            "arm_angle_deg": round(arm_angle_deg, 2),
            "arm_length_m": round(arm_len, 4),
            "arm_tube_start_m": [round(sx, 4), round(sy, 4), round(sz, 4)],
            "arm_tube_radius_m": ARM_TUBE_RADIUS_M,
            "motor_tilt_deg": MOTOR_TILT_DEG,
            "motor_tilt_direction": "outward_radial",
            "rotor_normal_vector": norm_vec,
            "thrust_vector_hover": thrust_vec,
            "thrust_z_correction_factor": thrust_z_correction,
            "classification": "O (posicion XY: Boceto 2 investigador); S (tilt: medicion pixel imagenes oficiales)"
        }

        # --- Tubo de brazo de carbono ---
        airframe_tris += make_tube(p_start, p_end, ARM_TUBE_RADIUS_M, nseg=20)

        # --- Carcasa del motor pod (cilindro central) ---
        # El pod del T70P tiene Ø0.32 m
        airframe_tris += make_cylinder_z(ex, ey, ez + 0.050, MOTOR_POD_RADIUS_M, MOTOR_POD_HEIGHT_M, nseg=28)
        # Campana superior del motor
        airframe_tris += make_frustum_z(ex, ey,
                                        ez + 0.050 + MOTOR_POD_HEIGHT_M / 2.0,
                                        ez + 0.050 + MOTOR_POD_HEIGHT_M / 2.0 + 0.040,
                                        MOTOR_POD_RADIUS_M, MOTOR_POD_RADIUS_M * 0.70, nseg=20)

        # --- Discos actuadores coaxiales INCLINADOS ---
        # Rotor Superior
        rz_upper = ROTOR_UPPER_Z_M
        rot_up_id = f"{arm_id}_upper"
        rotors_data.append({
            "rotor_id": rot_up_id,
            "arm_id": arm_id,
            "motor_num": apos["arm_num"],
            "position_role": "upper",
            "center_xyz_m": [round(ex, 4), round(ey, 4), round(rz_upper, 4)],
            "normal_vector": norm_vec,
            "thrust_vector_hover": thrust_vec,
            "rotation_direction": apos["rotation_upper"],
            "rotation_note": "T70P usa rotacion OPUESTA al cuadricoptero tradicional [P-A]",
            "diameter_m": ROTOR_DIAMETER_M,
            "radius_m": ROTOR_RADIUS_M,
            "swept_area_m2": round(math.pi * (ROTOR_RADIUS_M ** 2), 4),
            "disk_thickness_m": ROTOR_DISK_THICKNESS_M,
            "propeller_model": "6223 (62x23 in) fibra de carbono",
            "blades_count": 2,
            "propeller_mechanism": "abrazadera oscilante (swing clamp) - reduce vibracion 40%",
            "tilt_deg": MOTOR_TILT_DEG,
            "tilt_direction": "outward_radial",
            "thrust_z_fraction": thrust_z_correction,
            "nominal_hover_thrust_N": round(56.0 * 9.80665 / 8.0, 2),   # MTOW / 8 rotores
            "classification_position": "O (Boceto 2)",
            "classification_tilt": "S (imagen pixel)"
        })
        rotor_disks_tris += rotor_disk_vertices_tilted(
            ex, ey, rz_upper, ROTOR_RADIUS_M, ROTOR_DISK_THICKNESS_M,
            ex, ey, MOTOR_TILT_DEG, nseg=48
        )

        # Rotor Inferior
        rz_lower = ROTOR_LOWER_Z_M
        rot_low_id = f"{arm_id}_lower"
        rotors_data.append({
            "rotor_id": rot_low_id,
            "arm_id": arm_id,
            "motor_num": apos["arm_num"],
            "position_role": "lower",
            "center_xyz_m": [round(ex, 4), round(ey, 4), round(rz_lower, 4)],
            "normal_vector": norm_vec,
            "thrust_vector_hover": thrust_vec,
            "rotation_direction": apos["rotation_lower"],
            "rotation_note": "T70P usa rotacion OPUESTA al cuadricoptero tradicional [P-A]",
            "diameter_m": ROTOR_DIAMETER_M,
            "radius_m": ROTOR_RADIUS_M,
            "swept_area_m2": round(math.pi * (ROTOR_RADIUS_M ** 2), 4),
            "disk_thickness_m": ROTOR_DISK_THICKNESS_M,
            "propeller_model": "6223 (62x23 in) fibra de carbono",
            "blades_count": 2,
            "propeller_mechanism": "abrazadera oscilante (swing clamp) - reduce vibracion 40%",
            "tilt_deg": MOTOR_TILT_DEG,
            "tilt_direction": "outward_radial",
            "thrust_z_fraction": thrust_z_correction,
            "nominal_hover_thrust_N": round(56.0 * 9.80665 / 8.0, 2),
            "classification_position": "O (Boceto 2)",
            "classification_tilt": "S (imagen pixel)"
        })
        rotor_disks_tris += rotor_disk_vertices_tilted(
            ex, ey, rz_lower, ROTOR_RADIUS_M, ROTOR_DISK_THICKNESS_M,
            ex, ey, MOTOR_TILT_DEG, nseg=48
        )

    print(f"[OK] Brazos y discos actuadores: {len(rotors_data)} rotores (4 brazos × 2 coaxiales)")

    # --------------------------------------------------------------------------
    # B. FUSELAJE CENTRAL, TANQUE Y ELECTRÓNICA
    # --------------------------------------------------------------------------
    # Módulo de aviónica / FC / batería
    airframe_tris += make_box(0.00, 0.00, 0.12, 0.55, 0.48, 0.22)
    # Carenado frontal
    airframe_tris += make_frustum_z(0.28, 0.00, -0.04, 0.14, 0.20, 0.10, nseg=20)
    # Domo LiDAR / antena RTK
    airframe_tris += make_cylinder_z(0.00, 0.00, (0.22 + LIDAR_TOP_Z_M) / 2.0,
                                     0.080, LIDAR_TOP_Z_M - 0.22, nseg=28)

    # Tanque de 70 L montado bajo el chasis
    airframe_tris += make_box(-0.04, 0.00, -0.16, 0.52, 0.44, 0.22)
    airframe_tris += make_frustum_z(-0.04, 0.00, -0.32, -0.24, 0.14, 0.22, nseg=20)
    # Bomba centrífuga inferior
    airframe_tris += make_cylinder_z(-0.04, 0.00, -0.36, 0.10, 0.055, nseg=20)

    # --------------------------------------------------------------------------
    # C. TREN DE ATERRIZAJE — SKID CIRCULAR / OVALADO
    # --------------------------------------------------------------------------
    # El T70P usa patines en arco (visible en vista lateral oficial).
    # Se modelan como tubos curvos izquierdo y derecho.
    skid_y_offset = 0.450        # Desplazamiento Y del patín
    skid_r = 0.018               # Radio del tubo de patín
    skid_z = SKID_BOTTOM_Z_M + skid_r

    # Patín lateral derecho (tubo horizontal + diagonales de montaje)
    p_skid_r_f = np.array([+0.380,  skid_y_offset, skid_z])
    p_skid_r_b = np.array([-0.520,  skid_y_offset, skid_z])
    p_skid_l_f = np.array([+0.380, -skid_y_offset, skid_z])
    p_skid_l_b = np.array([-0.520, -skid_y_offset, skid_z])

    airframe_tris += make_tube(p_skid_r_f, p_skid_r_b, skid_r, nseg=16)
    airframe_tris += make_tube(p_skid_l_f, p_skid_l_b, skid_r, nseg=16)

    # Diagonales de montante (izquierdo y derecho, delantero y trasero)
    mount_z_top = -0.100
    airframe_tris += make_tube(np.array([+0.200, +0.240, mount_z_top]),
                               np.array([+0.300, +skid_y_offset, skid_z]), skid_r, nseg=14)
    airframe_tris += make_tube(np.array([+0.200, -0.240, mount_z_top]),
                               np.array([+0.300, -skid_y_offset, skid_z]), skid_r, nseg=14)
    airframe_tris += make_tube(np.array([-0.250, +0.240, mount_z_top]),
                               np.array([-0.360, +skid_y_offset, skid_z]), skid_r, nseg=14)
    airframe_tris += make_tube(np.array([-0.250, -0.240, mount_z_top]),
                               np.array([-0.360, -skid_y_offset, skid_z]), skid_r, nseg=14)

    # Travesaño inferior transversal
    airframe_tris += make_tube(p_skid_r_f, p_skid_l_f, skid_r, nseg=14)
    airframe_tris += make_tube(p_skid_r_b, p_skid_l_b, skid_r, nseg=14)

    # --------------------------------------------------------------------------
    # D. BOQUILLAS / ASPERSORES CENTRÍFUGOS (SISTEMA DE PULVERIZACIÓN)
    # --------------------------------------------------------------------------
    # El T70P usa 2 boquillas estándar (configuración mínima):
    # Cuelgan debajo de los brazos traseros, con anillos naranjas visibles en imágenes.
    # Separación oficial: 1874 mm entre centros [P]
    nozzles_data = [
        {
            "nozzle_id": "N1_right",
            "position_role": "right_standard",
            "description": "Boquilla centrífuga derecha — configuración estándar 2 boquillas",
            "center_xyz_m": [round(NOZZLE_X_M, 4), round(NOZZLE_Y_RIGHT, 4), round(NOZZLE_Z_M, 4)],
            "spray_injection_vector": [0.0, 0.0, -1.0],
            "spray_sheet_angle_deg": 180.0,
            "atomizer_model": "Doble atomización centrífuga (T70P spec)",
            "droplet_spectrum_um": {"min": 50.0, "max": 500.0, "classification": "P"},
            "nominal_flow_Lmin": 15.0,  # 30 L/min total / 2 boquillas
            "nominal_flow_m3s": round(15.0 / 60000.0, 8),
            "nozzle_spacing_m": NOZZLE_SPACING_M,
            "classification": "P (espaciado); I (posicion XYZ: estimado de imagenes)",
        },
        {
            "nozzle_id": "N2_left",
            "position_role": "left_standard",
            "description": "Boquilla centrífuga izquierda — configuración estándar 2 boquillas",
            "center_xyz_m": [round(NOZZLE_X_M, 4), round(NOZZLE_Y_LEFT, 4), round(NOZZLE_Z_M, 4)],
            "spray_injection_vector": [0.0, 0.0, -1.0],
            "spray_sheet_angle_deg": 180.0,
            "atomizer_model": "Doble atomización centrífuga (T70P spec)",
            "droplet_spectrum_um": {"min": 50.0, "max": 500.0, "classification": "P"},
            "nominal_flow_Lmin": 15.0,
            "nominal_flow_m3s": round(15.0 / 60000.0, 8),
            "nozzle_spacing_m": NOZZLE_SPACING_M,
            "classification": "P (espaciado); I (posicion XYZ: estimado de imagenes)",
        },
    ]

    for nz in nozzles_data:
        nx, ny, nz_z = nz["center_xyz_m"]
        # Brazo de tubería colgante desde el brazo del dron
        p_nozzle_top = np.array([nx, ny, nz_z + 0.120])
        p_nozzle_bottom = np.array([nx, ny, nz_z + 0.020])
        airframe_tris += make_tube(p_nozzle_top, p_nozzle_bottom, 0.010, nseg=12)

        # Carcasa del motor de la boquilla centrífuga
        airframe_tris += make_cylinder_z(nx, ny, nz_z + 0.040, 0.035, 0.055, nseg=20)
        # Disco anular naranja (visualmente identificado en las imágenes)
        airframe_tris += make_frustum_z(nx, ny, nz_z, nz_z + 0.012, 0.050, 0.040, nseg=24)

        # Marcador de inyección Lagrangiana
        spray_nozzles_tris += make_cylinder_z(nx, ny, nz_z, 0.046, 0.008, nseg=24)

    print(f"[OK] Sistema de boquillas: {len(nozzles_data)} atomizadores centrífugos")
    print(f"     Posición N1: Y=+{NOZZLE_Y_RIGHT:.3f} m  |  N2: Y={NOZZLE_Y_LEFT:.3f} m")
    print(f"     Separación oficial: {NOZZLE_SPACING_M*1000:.0f} mm [P]")

    # --------------------------------------------------------------------------
    # E. ESCRITURA DE ARCHIVOS STL
    # --------------------------------------------------------------------------
    stl_af_bin = OUT_DIR / "t70p_airframe.stl"
    stl_af_asc = OUT_DIR / "t70p_airframe_ascii.stl"
    write_stl_binary(stl_af_bin, airframe_tris, "DJI_T70P_Airframe_CFD")
    write_stl_ascii(stl_af_asc, "t70p_airframe", airframe_tris)
    print(f"[OK] Malla Airframe: {stl_af_bin.name} ({len(airframe_tris)} triángulos)")

    stl_rot_bin = OUT_DIR / "t70p_rotor_disks.stl"
    stl_rot_asc = OUT_DIR / "t70p_rotor_disks_ascii.stl"
    write_stl_binary(stl_rot_bin, rotor_disks_tris, "DJI_T70P_Actuator_Disks_CFD")
    write_stl_ascii(stl_rot_asc, "t70p_rotor_disks", rotor_disks_tris)
    print(f"[OK] Malla Rotores (8 discos actuadores inclinados): {stl_rot_bin.name} ({len(rotor_disks_tris)} triángulos)")

    stl_nz_bin = OUT_DIR / "t70p_spray_nozzles.stl"
    stl_nz_asc = OUT_DIR / "t70p_spray_nozzles_ascii.stl"
    write_stl_binary(stl_nz_bin, spray_nozzles_tris, "DJI_T70P_Spray_Nozzles_CFD")
    write_stl_ascii(stl_nz_asc, "t70p_spray_nozzles", spray_nozzles_tris)
    print(f"[OK] Malla Boquillas (2 atomizadores): {stl_nz_bin.name} ({len(spray_nozzles_tris)} triángulos)")

    full_tris = airframe_tris + rotor_disks_tris + spray_nozzles_tris
    stl_full = OUT_DIR / "t70p_full_assembly.stl"
    write_stl_binary(stl_full, full_tris, "DJI_T70P_Full_Assembly_CFD")
    print(f"[OK] Malla Ensamblaje Completo: {stl_full.name} ({len(full_tris)} triángulos)")

    # --------------------------------------------------------------------------
    # F. CONSTRUCCIÓN DEL ARCHIVO JSON MAESTRO DE COORDENADAS
    # --------------------------------------------------------------------------
    # Cálculo de envolvente del modelo
    motor_xs = [a["x_m"] for a in ARM_POSITIONS.values()]
    motor_ys = [a["y_m"] for a in ARM_POSITIONS.values()]
    env_x = (max(motor_xs) - min(motor_xs)) + ROTOR_DIAMETER_M
    env_y = (max(motor_ys) - min(motor_ys)) + ROTOR_DIAMETER_M
    env_z = TOTAL_HEIGHT_M

    # Verificación diagonal
    diag_FR_RL = math.sqrt(
        (ARM_POSITIONS["M1_FR"]["x_m"] - ARM_POSITIONS["M4_RL"]["x_m"])**2 +
        (ARM_POSITIONS["M1_FR"]["y_m"] - ARM_POSITIONS["M4_RL"]["y_m"])**2
    )
    diag_FL_RR = math.sqrt(
        (ARM_POSITIONS["M3_FL"]["x_m"] - ARM_POSITIONS["M2_RR"]["x_m"])**2 +
        (ARM_POSITIONS["M3_FL"]["y_m"] - ARM_POSITIONS["M2_RR"]["y_m"])**2
    )

    json_data = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "platform": "DJI Agras T70P",
        "description": (
            "Especificación tridimensional paramétrica del DJI Agras T70P para CFD "
            "de deposición/deriva de gotas. Incluye geometría asimétrica de brazos "
            "(medición directa del investigador) e inclinación de motores (motor tilt)."
        ),
        "generated_by": "scripts/generate_t70p_cfd_model.py",
        "schema_version": "1.0",

        "coordinate_system": {
            "origin": "Centro geométrico del chasis en el plano de los tubos de brazos de carbono",
            "axes_convention": "Aeronáutica mano derecha (SAE / CFD estándar)",
            "x_axis": "+X hacia adelante (eje de avance de vuelo)",
            "y_axis": "+Y hacia estribor / derecha del dron",
            "z_axis": "+Z vertical hacia arriba (opuesto a gravedad y downwash)",
            "units": "metros (m), grados sexagesimales (deg), segundos (s), kilogramos (kg)",
            "origin_note": "El boceto del investigador (Boceto 2) usa eje vertical = longitudinal dron (+X) y eje horizontal = lateral dron (+Y)"
        },

        "general_dimensions": {
            "wheelbase_diagonal_mm": WHEELBASE_DIAG_M * 1000,
            "wheelbase_diagonal_m": WHEELBASE_DIAG_M,
            "classification_wheelbase": "P (spec oficial DJI T70P)",
            "unfolded_envelope_mm_xyz": UNFOLDED_MM,
            "classification_unfolded": "P-A (DJI Academy / spec)",
            "modeled_envelope_mm_xyz": [
                round(env_x * 1000.0, 1),
                round(env_y * 1000.0, 1),
                round(env_z * 1000.0, 1)
            ],
            "total_height_m": TOTAL_HEIGHT_M,
            "ground_contact_z_m": SKID_BOTTOM_Z_M,
            "lidar_top_apex_z_m": LIDAR_TOP_Z_M,
            "verification": {
                "diagonal_M1FR_to_M4RL_m": round(diag_FR_RL, 4),
                "diagonal_M3FL_to_M2RR_m": round(diag_FL_RR, 4),
                "official_wheelbase_m": WHEELBASE_DIAG_M,
                "error_diag1_pct": round(abs(diag_FR_RL - WHEELBASE_DIAG_M) / WHEELBASE_DIAG_M * 100, 2),
                "error_diag2_pct": round(abs(diag_FL_RR - WHEELBASE_DIAG_M) / WHEELBASE_DIAG_M * 100, 2),
                "note": "La diagonal oficial DJI es 2440 mm. Boceto 2 del investigador da ~2395 mm (error ~1.8%). Usar Boceto 2 [O] como fuente primaria de posición por ser medicion directa."
            }
        },

        "mass_and_payload": {
            "total_with_battery_kg": 56.0,
            "classification": "P",
            "tank_capacity_L": 70.0,
            "mtow_spraying_kg": 126.0,
            "battery_model": "DB2160"
        },

        "motor_tilt": {
            "_CRITICAL_CFD_NOTE": (
                "El T70P incorpora abrazadera de hélice oscilante (swing-clamp propeller). "
                "El eje del motor/rotor está inclinado RADIALMENTE HACIA AFUERA (outward cant). "
                "El vector normal del disco actuador NO es [0,0,1]; tiene componente radial. "
                "Para actuationDiskSource en OpenFOAM: usar 'diskNormal' = normal_vector de cada rotor. "
                "El vector de downwash/empuje NO es perfectamente vertical: T_z = T_total * cos(tilt)."
            ),
            "tilt_angle_deg": MOTOR_TILT_DEG,
            "tilt_direction": "outward_radial",
            "classification": "S (medicion pixel sobre imagenes oficiales: vista frontal/trasera)",
            "cos_tilt": round(math.cos(MOTOR_TILT_RAD), 6),
            "sin_tilt": round(math.sin(MOTOR_TILT_RAD), 6),
            "thrust_z_fraction": round(math.cos(MOTOR_TILT_RAD), 6),
            "thrust_radial_fraction": round(math.sin(MOTOR_TILT_RAD), 6),
            "swing_clamp_mechanism": "Abrazadera oscilante propietaria DJI T70P — reduce vibracion 40% vs fija",
            "vibration_reduction_pct": 40,
            "cfd_implementation": {
                "openfoam_directive": "actuationDiskSource",
                "diskNormal": "usar normal_vector de cada rotor en rotors[] — NO usar [0,0,1]",
                "example_M1_FR": rotor_normal_vector(
                    ARM_POSITIONS["M1_FR"]["x_m"],
                    ARM_POSITIONS["M1_FR"]["y_m"],
                    MOTOR_TILT_DEG
                )
            }
        },

        "propulsion_and_rotors": {
            "total_rotors_count": 8,
            "coaxial_pairs_count": 4,
            "arms_count": 4,
            "classification_topology": "S (manifiesto v2.0 basado en DJI Academy slide 11)",
            "rotor_diameter_m": ROTOR_DIAMETER_M,
            "rotor_diameter_inches": 62.0,
            "propeller_pitch_inches": 23.0,
            "blades_per_rotor": 2,
            "blade_model": "6223 fibra de carbono, abrazadera oscilante",
            "classification_rotor_diameter": "P-A",
            "coaxial_axial_gap_m": COAXIAL_GAP_M,
            "upper_rotor_plane_z_m": ROTOR_UPPER_Z_M,
            "lower_rotor_plane_z_m": ROTOR_LOWER_Z_M,
            "classification_axial_gap": "I (estimado; dato real pendiente de medicion [D])",
            "actuator_disk_thickness_m": ROTOR_DISK_THICKNESS_M,
            "total_disk_area_m2": round(8.0 * math.pi * (ROTOR_RADIUS_M ** 2), 4),
            "motor_model": "155P (estator 155x22 mm, 65 KV)",
            "classification_motor": "P",
            "rotation_convention": {
                "_WARNING_": "La rotacion del T70P es OPUESTA a cuadricoptero tradicional [P-A]",
                "M1_FR": "CW (Motor 1 → sentido horario)",
                "M2_RR": "CCW (Motor 2 → sentido antihorario)",
                "M3_FL": "CW (Motor 3 → sentido horario)",
                "M4_RL": "CCW (Motor 4 → sentido antihorario)",
                "upper_lower": "En cada par coaxial, superior e inferior contrarrotan",
                "source": "DJI Academy 01 Conocimiento basico de un Dron [P-A]"
            },
            "arm_geometry_note": (
                "GEOMETRIA ASIMETRICA: Los brazos NO estan a 45 grados. "
                "Brazo FR/FL: angulo desde eje +X = atan2(0.961, 0.270) = 74.3 deg. "
                "Brazo RR/RL: angulo desde eje +X = atan2(0.865, -1.280) = 145.9 deg. "
                "Fuente: Boceto 2 del investigador [O]."
            ),
            "rotors": rotors_data
        },

        "arms": arms_data,

        "spraying_system": {
            "atomizer_type": "centrífuga de doble atomización",
            "nozzles_standard_count": 2,
            "nozzles_optional_count": 4,
            "nozzle_spacing_standard_m": NOZZLE_SPACING_M,
            "nozzle_spacing_standard_mm": NOZZLE_SPACING_M * 1000,
            "classification_nozzle_spacing": "P (spec oficial DJI T70P)",
            "nozzle_z_level_m": NOZZLE_Z_M,
            "classification_nozzle_z": "I (estimado de imagenes)",
            "nozzle_x_level_m": NOZZLE_X_M,
            "classification_nozzle_x": "I (estimado de imagenes)",
            "flow_2nozzles_Lmin": 30.0,
            "flow_4nozzles_Lmin": 40.0,
            "droplet_spectrum_um": {"min": 50.0, "max": 500.0},
            "spray_coverage_m": [4.0, 11.0],
            "nozzles": nozzles_data
        },

        "landing_gear": {
            "type": "skid_arc_oval",
            "description": "Patín en arco ovalado (tubo curvado), diferente al A-frame del T100",
            "skid_y_offset_m": skid_y_offset,
            "skid_bottom_z_m": SKID_BOTTOM_Z_M,
            "classification": "S (observado en vista lateral oficial)",
            "right_skid": {
                "p_front_xyz_m": [round(p_skid_r_f[0], 4), round(p_skid_r_f[1], 4), round(p_skid_r_f[2], 4)],
                "p_rear_xyz_m":  [round(p_skid_r_b[0], 4), round(p_skid_r_b[1], 4), round(p_skid_r_b[2], 4)]
            },
            "left_skid": {
                "p_front_xyz_m": [round(p_skid_l_f[0], 4), round(p_skid_l_f[1], 4), round(p_skid_l_f[2], 4)],
                "p_rear_xyz_m":  [round(p_skid_l_b[0], 4), round(p_skid_l_b[1], 4), round(p_skid_l_b[2], 4)]
            }
        },

        "cfd_openfoam_guidelines": {
            "snappyHexMesh_surfaces": {
                "airframe":      "t70p_airframe.stl (pared impermeable no-deslizamiento)",
                "rotor_disks":   "t70p_rotor_disks.stl (zonas MRF / actuationDiskSource con diskNormal inclinado)",
                "spray_nozzles": "t70p_spray_nozzles.stl (parches de inyeccion Lagrangiana)"
            },
            "actuationDiskSource_critical": {
                "note": "Cada disco actuador tiene diskNormal != [0,0,1]. Ver motor_tilt.cfd_implementation",
                "thrust_correction": "T_disk = T_total * cos(8.9 deg) = T_total * 0.9880",
                "radial_force_note": "El componente radial del empuje puede modelarse como fuerza de cuerpo en la celda o ignorarse en primera aproximacion"
            },
            "droplet_deposition_module": {
                "injector_type": "cone / rotatingDiscInjector (centrifugal sheet atomization)",
                "injection_coordinates": [nz["center_xyz_m"] for nz in nozzles_data],
                "injection_directions": [nz["spray_injection_vector"] for nz in nozzles_data],
                "droplet_spectrum_um_range": [50.0, 500.0],
                "fluid": "agua (rho=997.0 kg/m3, mu=1.002e-3 Pa.s a 20°C)"
            }
        }
    }

    json_path = OUT_DIR / "t70p_cfd_coordinates.json"
    json_path.write_text(json.dumps(json_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] Archivo JSON de coordenadas: {json_path.name}")

    # --------------------------------------------------------------------------
    # G. GRÁFICO DE VERIFICACIÓN ORTOGRÁFICA
    # --------------------------------------------------------------------------
    plot_path = OUT_DIR / "t70p_geometry_verification.png"
    fig, axs = plt.subplots(2, 2, figsize=(18, 15), dpi=150)
    fig.suptitle("DJI AGRAS T70P — Verificación Geométrica CFD\n"
                 f"Motor Tilt: {MOTOR_TILT_DEG}° outward | Brazos asimétricos | Coaxial 8 rotores",
                 fontsize=13, fontweight="bold", y=0.98)

    COLORS = {
        "upper": ("#1565C0", "-"),     # azul sólido
        "lower": ("#42A5F5", "--"),    # azul claro punteado
        "arm":   "black",
        "nozzle": "#E53935",
        "tilt_vec": "#FF6F00"
    }

    # -------------------------
    # 1. Vista Superior (XY)
    # -------------------------
    ax = axs[0, 0]
    ax.set_title("VISTA SUPERIOR (Planta XY)", fontsize=11, fontweight="bold")
    ax.set_xlabel("X (m) [Adelante →]")
    ax.set_ylabel("Y (m) [Derecha →]")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.set_aspect("equal")

    # Brazos y rotores
    for arm_id, apos in ARM_POSITIONS.items():
        ex, ey = apos["x_m"], apos["y_m"]
        arm_len = math.sqrt(ex**2 + ey**2)
        ax.plot([0, ex], [0, ey], color=COLORS["arm"], linewidth=3.5, solid_capstyle="round", zorder=3)

        for role, (col, ls) in [("upper", COLORS["upper"]), ("lower", COLORS["lower"])]:
            circle = plt.Circle((ex, ey), ROTOR_RADIUS_M, color=col, fill=False,
                                linestyle=ls, alpha=0.6, linewidth=1.5)
            ax.add_patch(circle)

        ax.plot(ex, ey, "o", color="darkblue", markersize=6, zorder=5)

        # Vector tilt proyectado en XY
        nv = rotor_normal_vector(ex, ey, MOTOR_TILT_DEG)
        scale = 0.30
        ax.annotate("", xy=(ex + nv[0]*scale, ey + nv[1]*scale),
                    xytext=(ex, ey),
                    arrowprops=dict(arrowstyle="->", color=COLORS["tilt_vec"], lw=1.5))

        arm_num = apos["arm_num"]
        ax.text(ex * 1.10, ey * 1.10, f"{arm_id}\n(M{arm_num})",
                fontsize=8, fontweight="bold", ha="center", va="center",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.8))

    # Boquillas en planta
    for nz in nozzles_data:
        nx, ny, _ = nz["center_xyz_m"]
        ax.plot(nx, ny, "s", color=COLORS["nozzle"], markersize=10, zorder=6)
        ax.text(nx + 0.06, ny, nz["nozzle_id"], fontsize=8, color="darkred",
                fontweight="bold", va="center")

    # Línea de separación entre boquillas
    ax.plot([NOZZLE_X_M, NOZZLE_X_M], [NOZZLE_Y_LEFT, NOZZLE_Y_RIGHT],
            color=COLORS["nozzle"], linewidth=2, linestyle=":", zorder=4)
    ax.text(NOZZLE_X_M - 0.15, 0, f"{NOZZLE_SPACING_M*1000:.0f} mm", color="darkred",
            fontsize=8, ha="right", va="center", fontweight="bold")

    # Anotación de asimetría
    ax.annotate("", xy=(ARM_POSITIONS["M1_FR"]["x_m"], ARM_POSITIONS["M1_FR"]["y_m"]),
                xytext=(ARM_POSITIONS["M2_RR"]["x_m"], ARM_POSITIONS["M2_RR"]["y_m"]),
                arrowprops=dict(arrowstyle="<->", color="gray", lw=1.2, linestyle="--"))
    ax.text(-0.5, -0.4, f"Diag FR→RL\n{diag_FR_RL*1000:.0f} mm", fontsize=7, color="gray", ha="center")

    ax.axhline(0, color="gray", linewidth=0.5, linestyle=":")
    ax.axvline(0, color="gray", linewidth=0.5, linestyle=":")
    ax.set_xlim(-2.0, 1.8)
    ax.set_ylim(-2.0, 2.0)

    # Leyenda
    legend_patches = [
        mpatches.Patch(color=COLORS["upper"][0], label="Rotor superior (upper)"),
        mpatches.Patch(color=COLORS["lower"][0], label="Rotor inferior (lower)"),
        mpatches.Patch(color=COLORS["nozzle"], label="Boquilla pulverizadora"),
        mpatches.Patch(color=COLORS["tilt_vec"], label=f"Vector tilt outward ({MOTOR_TILT_DEG}°)"),
    ]
    ax.legend(handles=legend_patches, fontsize=7, loc="lower right")

    # -------------------------
    # 2. Vista Lateral (XZ)
    # -------------------------
    ax = axs[0, 1]
    ax.set_title("VISTA LATERAL (Perfil XZ)", fontsize=11, fontweight="bold")
    ax.set_xlabel("X (m) [Adelante →]")
    ax.set_ylabel("Z (m) [Arriba →]")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.set_aspect("equal")

    # Planos de rotor
    ax.axhline(ROTOR_UPPER_Z_M, color=COLORS["upper"][0], linestyle="-",
               label=f"Rotor sup. Z={ROTOR_UPPER_Z_M:+.3f} m")
    ax.axhline(ROTOR_LOWER_Z_M, color=COLORS["lower"][0], linestyle="--",
               label=f"Rotor inf. Z={ROTOR_LOWER_Z_M:+.3f} m")
    ax.axhline(SKID_BOTTOM_Z_M, color="black", linestyle="-", linewidth=2,
               label=f"Suelo Z={SKID_BOTTOM_Z_M:+.3f} m")
    ax.axhline(NOZZLE_Z_M, color=COLORS["nozzle"], linestyle=":",
               label=f"Boquillas Z={NOZZLE_Z_M:+.3f} m")

    # Representar los rotores en XZ (proyectar posiciones X de motores)
    for arm_id, apos in ARM_POSITIONS.items():
        ex = apos["x_m"]
        nv = rotor_normal_vector(ex, apos["y_m"], MOTOR_TILT_DEG)
        # Dibujar disco inclinado como elipse proyectada
        for rz, col in [(ROTOR_UPPER_Z_M, COLORS["upper"][0]), (ROTOR_LOWER_Z_M, COLORS["lower"][0])]:
            # Proyección del disco inclinado en XZ: los extremos del diámetro
            dx_proj = ROTOR_RADIUS_M * math.cos(MOTOR_TILT_RAD)
            ax.plot([ex - dx_proj, ex + dx_proj], [rz, rz], color=col, linewidth=2.5, alpha=0.7)

        # Vector de tilt en XZ
        scale_tilt = 0.25
        ax.annotate("", xy=(ex + nv[0]*scale_tilt, 0 + nv[2]*scale_tilt),
                    xytext=(ex, 0),
                    arrowprops=dict(arrowstyle="->", color=COLORS["tilt_vec"], lw=1.5))
        ax.plot(ex, 0, "o", color="darkblue", markersize=5)

    # Boquillas
    for nz in nozzles_data:
        nx, _, nz_z = nz["center_xyz_m"]
        ax.plot(nx, nz_z, "s", color=COLORS["nozzle"], markersize=8)

    ax.set_xlim(-2.1, 1.5)
    ax.set_ylim(-0.75, 0.55)
    ax.legend(fontsize=7, loc="upper right")

    # Anotación del tilt
    ax.text(0.0, 0.15, f"Motor Tilt\n= {MOTOR_TILT_DEG}° outward",
            fontsize=8, color=COLORS["tilt_vec"][0] if isinstance(COLORS["tilt_vec"], tuple) else COLORS["tilt_vec"],
            ha="center", fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#FFF9C4", edgecolor="#FF6F00", alpha=0.9))

    # -------------------------
    # 3. Vista Frontal/Trasera (YZ)
    # -------------------------
    ax = axs[1, 0]
    ax.set_title("VISTA FRONTAL/TRASERA (Alzado YZ)\n[Motor tilt outward visible]",
                 fontsize=11, fontweight="bold")
    ax.set_xlabel("Y (m) [Izq ← | → Der]")
    ax.set_ylabel("Z (m) [Arriba →]")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.set_aspect("equal")

    ax.axhline(ROTOR_UPPER_Z_M, color=COLORS["upper"][0], linestyle="-", alpha=0.4)
    ax.axhline(ROTOR_LOWER_Z_M, color=COLORS["lower"][0], linestyle="--", alpha=0.4)
    ax.axhline(SKID_BOTTOM_Z_M, color="black", linewidth=2)
    ax.axhline(NOZZLE_Z_M, color=COLORS["nozzle"], linestyle=":", linewidth=1.5)

    # Proyectar motores en YZ (vista trasera)
    for arm_id, apos in ARM_POSITIONS.items():
        ey = apos["y_m"]
        nv = rotor_normal_vector(apos["x_m"], ey, MOTOR_TILT_DEG)

        for rz, col in [(ROTOR_UPPER_Z_M, COLORS["upper"][0]), (ROTOR_LOWER_Z_M, COLORS["lower"][0])]:
            # El disco inclinado en vista YZ muestra el efecto del tilt
            dy_proj = ROTOR_RADIUS_M  # ancho full del disco en Y
            dz_tilt = ROTOR_RADIUS_M * math.sin(MOTOR_TILT_RAD)  # elevación por tilt
            # Extremo interior del disco (hacia el centro) está más alto (tilt outward)
            sign_y = 1 if ey > 0 else -1
            y_inner = ey - sign_y * ROTOR_RADIUS_M
            y_outer = ey + sign_y * ROTOR_RADIUS_M
            z_inner = rz + dz_tilt  # la punta hacia el centro sube
            z_outer = rz - dz_tilt  # la punta hacia afuera baja
            ax.plot([y_inner, y_outer], [z_inner, z_outer], color=col, linewidth=2.5, alpha=0.8)

        # Centro del motor
        ax.plot(ey, 0, "o", color="darkblue", markersize=5)
        # Vector tilt proyectado en YZ
        scale_t = 0.28
        ax.annotate("", xy=(ey + nv[1]*scale_t, 0 + nv[2]*scale_t),
                    xytext=(ey, 0),
                    arrowprops=dict(arrowstyle="->", color=COLORS["tilt_vec"], lw=1.5))

    # Boquillas en YZ
    for nz in nozzles_data:
        _, ny, nz_z = nz["center_xyz_m"]
        ax.plot(ny, nz_z, "s", color=COLORS["nozzle"], markersize=10, zorder=6)
        ax.text(ny, nz_z - 0.05, f"{ny*1000:+.0f} mm", fontsize=8,
                ha="center", color="darkred", fontweight="bold")

    ax.annotate("",
                xy=(+NOZZLE_Y_RIGHT, NOZZLE_Z_M - 0.08),
                xytext=(-NOZZLE_Y_RIGHT, NOZZLE_Z_M - 0.08),
                arrowprops=dict(arrowstyle="<->", color="darkred", lw=1.5))
    ax.text(0, NOZZLE_Z_M - 0.14, f"Separación boquillas = {NOZZLE_SPACING_M*1000:.0f} mm [P]",
            ha="center", fontsize=9, color="darkred", fontweight="bold")

    # Anotación ángulo de tilt
    ax.text(0, -0.40,
            f"Tilt = {MOTOR_TILT_DEG}°\n(outward cant)\ncos(θ)={math.cos(MOTOR_TILT_RAD):.4f}\n→ T_z = T×{math.cos(MOTOR_TILT_RAD):.4f}",
            ha="center", fontsize=8, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.4", facecolor="#FFF9C4", edgecolor="#FF6F00"))
    ax.set_xlim(-2.0, 2.0)
    ax.set_ylim(-0.75, 0.55)

    # -------------------------
    # 4. Resumen metrológico
    # -------------------------
    ax = axs[1, 1]
    ax.axis("off")

    arm_info_lines = ""
    for arm_id, ainfo in arms_data.items():
        arm_angle = ainfo["arm_angle_deg"]
        nv = ainfo["rotor_normal_vector"]
        arm_info_lines += (
            f"  {arm_id}: X={ainfo['axis_center_m'][0]:+.3f}, Y={ainfo['axis_center_m'][1]:+.3f} m\n"
            f"    Ángulo={arm_angle:.1f}° | L_brazo={ainfo['arm_length_m']:.3f} m\n"
            f"    normal=({nv[0]:+.4f}, {nv[1]:+.4f}, {nv[2]:+.4f})\n"
        )

    resumen_text = (
        "DJI AGRAS T70P — RESUMEN METROLÓGICO Y CFD\n"
        "=" * 52 + "\n\n"
        f"• Distancia entre ejes (diagonal oficial): {WHEELBASE_DIAG_M*1000:.0f} mm [P]\n"
        f"• Diagonal M1_FR→M4_RL (Boceto 2):     {diag_FR_RL*1000:.1f} mm [O]\n"
        f"• Diagonal M3_FL→M2_RR (Boceto 2):     {diag_FL_RR*1000:.1f} mm [O]\n"
        f"• Envolvente modelo (con hélices):       {env_x*1000:.0f}×{env_y*1000:.0f}×{TOTAL_HEIGHT_M*1000:.0f} mm\n"
        f"• Envolvente oficial desplegada:         {UNFOLDED_MM[0]}×{UNFOLDED_MM[1]}×{UNFOLDED_MM[2]} mm [P-A]\n\n"
        "MOTOR TILT (INCLINACIÓN ESPECIAL T70P):\n"
        f"• Ángulo tilt outward:     {MOTOR_TILT_DEG}° [S, medición pixel]\n"
        f"• Mecanismo:               Abrazadera oscilante (swing clamp)\n"
        f"• Reducción de vibración:  40% vs abrazadera fija\n"
        f"• cos(tilt) =              {math.cos(MOTOR_TILT_RAD):.6f}\n"
        f"• Fracción empuje vertical: T_z = T × {math.cos(MOTOR_TILT_RAD):.4f}\n"
        f"• Fracción radial:         T_r = T × {math.sin(MOTOR_TILT_RAD):.4f}\n\n"
        "PROPULSIÓN COAXIAL (8 ROTORES, 4 BRAZOS ASIMÉTRICOS):\n"
        f"• Hélices: 6223 (Ø={ROTOR_DIAMETER_M*1000:.0f} mm / 62 in, paso=23 in) [P-A]\n"
        f"• Gap axial coaxial: {COAXIAL_GAP_M*1000:.0f} mm (estimado) [I]\n"
        f"• Z_sup={ROTOR_UPPER_Z_M*1000:+.0f} mm | Z_inf={ROTOR_LOWER_Z_M*1000:+.0f} mm\n"
        f"• Área disco total: {8.0*math.pi*(ROTOR_RADIUS_M**2):.3f} m² (8 rotores)\n"
        f"• ⚠ ROTACIÓN INVERSA vs cuadricóptero [P-A]\n"
        f"  M1/M3 → CW  |  M2/M4 → CCW\n\n"
        "POSICIONES DE MOTORES (Boceto 2 [O]):\n" + arm_info_lines +
        "\nSISTEMA DE PULVERIZACIÓN:\n"
        f"• Boquillas estándar: 2 (4 opcional)\n"
        f"• Separación: {NOZZLE_SPACING_M*1000:.0f} mm [P]\n"
        f"• N1_right: Y=+{NOZZLE_Y_RIGHT:.3f} m\n"
        f"• N2_left:  Y={NOZZLE_Y_LEFT:.3f} m\n"
        f"• Z boquillas: {NOZZLE_Z_M*1000:+.0f} mm [I]\n"
        f"• Gota: 50–500 µm [P]\n"
        f"• Caudal 2 boquillas: 30 L/min [P-A]"
    )
    ax.text(0.01, 0.99, resumen_text, transform=ax.transAxes, fontsize=7.5,
            verticalalignment="top", fontfamily="monospace",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="whitesmoke",
                      edgecolor="lightgray", alpha=0.95))

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(plot_path, bbox_inches="tight")
    plt.close()
    print(f"[OK] Gráfico de verificación: {plot_path.name}")

    print()
    print("=" * 80)
    print(f"MODELADO T70P COMPLETADO EN: {OUT_DIR}")
    print(f"Archivos generados: airframe | rotor_disks | spray_nozzles | full_assembly | json | png")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    raise SystemExit(generate_t70p_cfd_dataset())
