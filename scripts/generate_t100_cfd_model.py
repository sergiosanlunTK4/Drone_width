"""
Generador del Modelo 3D de Alta Fidelidad y Coordenadas CFD del DJI Agras T100.

Diseñado específicamente para simulaciones de aerodinámica (CFD), campo de downwash
e inyección lagrangiana de gotas (simulación de deposición y deriva).

Fuentes:
  - Ficha técnica oficial DJI Agras T100 (ag.dji.com/es/t100/specs)
  - Material oficial de formación DJI Academy / UTC (01 Conocimiento básico de un Dron)
  - Fotografías y renders ortográficos de referencia directa (T100_UP, T100_FRONT, T100_REAR, T100_RIGHT)
  - Manifiesto auditado geometry/manifests/t100_geometry_manifest.json

Salidas generadas en geometry/models/T100_CFD/:
  1. t100_cfd_coordinates.json  -> Catálogo exhaustivo de coordenadas 3D y parámetros de inyección
  2. t100_airframe.stl          -> Superficies sólidas impermeables (fuselaje, brazos, tren, barra, carcasas)
  3. t100_rotor_disks.stl       -> 8 volúmenes cilíndricos de barrido de rotores (discos actuadores / MRF)
  4. t100_spray_nozzles.stl     -> Discos/puntos marcadores de atomización centrífuga
  5. t100_full_assembly.stl     -> Ensamblaje completo unificado
  6. t100_geometry_verification.png -> Gráfico de control ortográfico multieje
"""
from __future__ import annotations

import json
import math
import struct
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "geometry" / "models" / "T100_CFD"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ==============================================================================
# 1. PARÁMETROS GEOMÉTRICOS Y METROLÓGICOS DEL DJI AGRAS T100
# ==============================================================================
# Sistema de Coordenadas:
#   Origen (0, 0, 0): Centro geométrico del bastidor / plano medio de tubos de brazos
#   +X: Hacia adelante
#   +Y: Hacia la derecha (estribor)
#   +Z: Hacia arriba

WHEELBASE_DIAG_M = 2.330          # 2330 mm entre ejes diagonales
ARM_RADIUS_M = WHEELBASE_DIAG_M / 2.0  # 1.165 m del centro al eje del motor

# Diámetro y radio de rotor (Hélices 6223: 62 pulgadas x 23 pulgadas de paso)
ROTOR_DIAMETER_M = 1.5748         # 62 pulgadas = 1574.8 mm
ROTOR_RADIUS_M = ROTOR_DIAMETER_M / 2.0  # 0.7874 m
ROTOR_DISK_THICKNESS_M = 0.040    # 40 mm de celda de disco actuador CFD

# Planos verticales de rotores coaxiales (medidos en T100_RIGHT / T100_REAR)
ROTOR_UPPER_Z_M = +0.1450         # Plano del rotor superior
ROTOR_LOWER_Z_M = -0.1450         # Plano del rotor inferior
COAXIAL_DZ_M = ROTOR_UPPER_Z_M - ROTOR_LOWER_Z_M  # 0.290 m separación axial

# Brazos de carbono
ARM_TUBE_RADIUS_M = 0.030         # Tubo de 60 mm de diámetro exterior
MOTOR_POD_RADIUS_M = 0.090        # Carcasa de motor pod 180 mm diámetro
MOTOR_POD_HALF_H_M = 0.150        # Altura del pod (+/- 150 mm)

# Alturas generales (Z)
LIDAR_TOP_Z_M = +0.3500           # Cúspide del domo LiDAR / antena RTK
SKID_BOTTOM_Z_M = -0.6250         # Base de contacto de los patines en el suelo
TOTAL_HEIGHT_M = LIDAR_TOP_Z_M - SKID_BOTTOM_Z_M  # 0.975 m = 975 mm exactos

# Sistema de pulverización: Barra trasera LS100 y atomizadores LX07550SX
NOZZLE_SPACING_OUTER_M = 1.8340   # 1834 mm separación exterior (oficial)
NOZZLE_SPACING_INNER_M = 0.9170   # 917 mm separación interior (mitad exacta)
NOZZLE_Z_M = -0.4480              # Altura del disco de atomización
NOZZLE_X_OUTER_M = -0.8750        # Retranqueo longitudinal boquillas exteriores
NOZZLE_X_INNER_M = -0.7750        # Retranqueo longitudinal boquillas interiores

# 4 Brazos a 45 grados simétricos
ARM_ANGLES_DEG = {
    "M1_FR": 45.0,    # Frontal Derecho (Front-Right)
    "M2_RR": 135.0,   # Trasero Derecho (Rear-Right)
    "M3_RL": 225.0,   # Trasero Izquierdo (Rear-Left)
    "M4_FL": 315.0,   # Frontal Izquierdo (Front-Left)
}

# Sentidos de rotación (rotación diferencial DJI estándar para cancelar par)
# En coaxial: superior e inferior contrarrotan en cada brazo
ROTOR_ROTATIONS = {
    "M1_FR": {"upper": "CCW", "lower": "CW"},
    "M2_RR": {"upper": "CW",  "lower": "CCW"},
    "M3_RL": {"upper": "CCW", "lower": "CW"},
    "M4_FL": {"upper": "CW",  "lower": "CCW"},
}

# ==============================================================================
# 2. FUNCIONES DE GENERACIÓN GEOMÉTRICA DE MALLAS 3D (TRIÁNGULOS ESTANCOS)
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
        (0, 2, 1), (0, 3, 2),  # inferior (-Z)
        (4, 5, 6), (4, 6, 7),  # superior (+Z)
        (0, 1, 5), (0, 5, 4),  # frontal (-Y)
        (2, 3, 7), (2, 7, 6),  # posterior (+Y)
        (1, 2, 6), (1, 6, 5),  # derecha (+X)
        (3, 0, 4), (3, 4, 7),  # izquierda (-X)
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
        # tapa superior
        tris.append((top_c, top_ring[i], top_ring[j]))
        # tapa inferior
        tris.append((bot_c, bot_ring[j], bot_ring[i]))
        # laterales
        tris.append((top_ring[i], bot_ring[i], bot_ring[j]))
        tris.append((top_ring[i], bot_ring[j], top_ring[j]))
    return tris

def make_frustum_z(cx: float, cy: float, cz_bot: float, cz_top: float, r_bot: float, r_top: float, nseg: int = 36) -> list:
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
    # vector ortogonal
    arb = np.array([1.0, 0.0, 0.0]) if abs(v_dir[0]) < 0.85 else np.array([0.0, 1.0, 0.0])
    u = normalize(np.cross(v_dir, arb))
    w = normalize(np.cross(v_dir, u))
    
    angles = np.linspace(0, 2 * np.pi, nseg, endpoint=False)
    c1 = [p1 + r * (np.cos(a) * u + np.sin(a) * w) for a in angles]
    c2 = [p2 + r * (np.cos(a) * u + np.sin(a) * w) for a in angles]
    
    tris = []
    for i in range(nseg):
        j = (i + 1) % nseg
        # tapa p1
        tris.append((p1, c1[j], c1[i]))
        # tapa p2
        tris.append((p2, c2[i], c2[j]))
        # manto
        tris.append((c1[i], c2[i], c2[j]))
        tris.append((c1[i], c2[j], c1[j]))
    return tris

def write_stl_binary(path: Path, triangles: list, header_text: str = "DJI Agras T100 CFD") -> None:
    """Escribe archivo STL binario estanco y ultrarrápido compatible con OpenFOAM/Paraview."""
    header = header_text.encode("utf-8")[:80].ljust(80, b"\x00")
    num_triangles = len(triangles)
    with open(path, "wb") as f:
        f.write(header)
        f.write(struct.pack("<I", num_triangles))
        for p1, p2, p3 in triangles:
            n = calc_normal(p1, p2, p3)
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
        n = calc_normal(a, b, c)
        lines.append(f"  facet normal {n[0]:.6e} {n[1]:.6e} {n[2]:.6e}")
        lines.append("    outer loop")
        for v in (a, b, c):
            lines.append(f"      vertex {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}")
        lines.append("    endloop")
        lines.append("  endfacet")
    lines.append(f"endsolid {name}")
    path.write_text("\n".join(lines), encoding="utf-8")

# ==============================================================================
# 3. CONSTRUCCIÓN DE COMPONENTES DEL MODELO
# ==============================================================================

def generate_t100_cfd_dataset():
    print("=" * 80)
    print("INICIANDO MODELADO GEOMÉTRICO 3D DEL DJI AGRAS T100 PARA CFD")
    print("=" * 80)
    
    # --------------------------------------------------------------------------
    # A. CÁLCULO DE POSICIONES DE BRAZOS Y EJES DE ROTOR
    # --------------------------------------------------------------------------
    arms_data = {}
    rotors_data = []
    airframe_tris = []
    rotor_disks_tris = []
    spray_nozzles_tris = []
    
    # Tubo central / fuselage center
    body_radius = 0.28
    
    for arm_id, deg in ARM_ANGLES_DEG.items():
        rad = np.deg2rad(deg)
        cos_a = np.cos(rad)
        sin_a = np.sin(rad)
        
        # Centro del eje de motor (intersección del brazo con eje coaxial)
        ex = ARM_RADIUS_M * cos_a
        ey = ARM_RADIUS_M * sin_a
        ez = 0.0000
        
        # Inicio del tubo de brazo en la pared del fuselaje
        sx = body_radius * cos_a
        sy = body_radius * sin_a
        sz = 0.0000
        
        p_start = np.array([sx, sy, sz])
        p_end = np.array([ex, ey, ez])
        
        arms_data[arm_id] = {
            "angle_deg": deg,
            "axis_center_m": [round(ex, 4), round(ey, 4), round(ez, 4)],
            "arm_tube_start_m": [round(sx, 4), round(sy, 4), round(sz, 4)],
            "arm_tube_radius_m": ARM_TUBE_RADIUS_M,
            "arm_tube_length_m": round(ARM_RADIUS_M - body_radius, 4),
        }
        
        # 1. Brazo de carbono tubular
        airframe_tris += make_tube(p_start, p_end, ARM_TUBE_RADIUS_M, nseg=20)
        
        # 2. Carcasa coaxial (motor pod central y soportes)
        airframe_tris += make_cylinder_z(ex, ey, ez, MOTOR_POD_RADIUS_M, MOTOR_POD_HALF_H_M * 2.0, nseg=32)
        # Campana de motor superior
        airframe_tris += make_frustum_z(ex, ey, ez + MOTOR_POD_HALF_H_M, ez + MOTOR_POD_HALF_H_M + 0.025,
                                        MOTOR_POD_RADIUS_M, MOTOR_POD_RADIUS_M * 0.75, nseg=24)
        # Campana de motor inferior
        airframe_tris += make_frustum_z(ex, ey, ez - MOTOR_POD_HALF_H_M - 0.025, ez - MOTOR_POD_HALF_H_M,
                                        MOTOR_POD_RADIUS_M * 0.75, MOTOR_POD_RADIUS_M, nseg=24)
        
        # 3. Discos actuadores coaxiales para CFD (Rotor Superior y Rotor Inferior)
        # Rotor Superior
        rot_up_id = f"{arm_id}_upper"
        rotors_data.append({
            "rotor_id": rot_up_id,
            "arm_id": arm_id,
            "position_role": "upper",
            "center_xyz_m": [round(ex, 4), round(ey, 4), round(ROTOR_UPPER_Z_M, 4)],
            "normal_vector": [0.0, 0.0, 1.0],
            "thrust_vector_hover": [0.0, 0.0, -1.0],  # Downwash empuja fluido hacia -Z
            "rotation_direction": ROTOR_ROTATIONS[arm_id]["upper"],
            "diameter_m": ROTOR_DIAMETER_M,
            "radius_m": ROTOR_RADIUS_M,
            "swept_area_m2": round(math.pi * (ROTOR_RADIUS_M ** 2), 4),
            "disk_thickness_m": ROTOR_DISK_THICKNESS_M,
            "propeller_model": "6223 (62x23 in)",
            "blades_count": 2,
            "mean_chord_m": 0.085,
            "pitch_inches": 23.0,
            "nominal_hover_thrust_N": 214.5,   # ~175 kg MTOW / 8 rotores * 9.81
            "nominal_hover_rpm": 1850.0,
        })
        disk_up_tris = make_cylinder_z(ex, ey, ROTOR_UPPER_Z_M, ROTOR_RADIUS_M, ROTOR_DISK_THICKNESS_M, nseg=48)
        rotor_disks_tris += disk_up_tris
        
        # Rotor Inferior
        rot_low_id = f"{arm_id}_lower"
        rotors_data.append({
            "rotor_id": rot_low_id,
            "arm_id": arm_id,
            "position_role": "lower",
            "center_xyz_m": [round(ex, 4), round(ey, 4), round(ROTOR_LOWER_Z_M, 4)],
            "normal_vector": [0.0, 0.0, 1.0],
            "thrust_vector_hover": [0.0, 0.0, -1.0],
            "rotation_direction": ROTOR_ROTATIONS[arm_id]["lower"],
            "diameter_m": ROTOR_DIAMETER_M,
            "radius_m": ROTOR_RADIUS_M,
            "swept_area_m2": round(math.pi * (ROTOR_RADIUS_M ** 2), 4),
            "disk_thickness_m": ROTOR_DISK_THICKNESS_M,
            "propeller_model": "6223 (62x23 in)",
            "blades_count": 2,
            "mean_chord_m": 0.085,
            "pitch_inches": 23.0,
            "nominal_hover_thrust_N": 214.5,
            "nominal_hover_rpm": 1850.0,
        })
        disk_low_tris = make_cylinder_z(ex, ey, ROTOR_LOWER_Z_M, ROTOR_RADIUS_M, ROTOR_DISK_THICKNESS_M, nseg=48)
        rotor_disks_tris += disk_low_tris

    # --------------------------------------------------------------------------
    # B. FUSELAJE CENTRAL, TANQUE DE 100 L, DOMO LIDAR Y ELECTRÓNICA
    # --------------------------------------------------------------------------
    # Cuerpo principal / módulo de aviónica
    airframe_tris += make_box(0.02, 0.00, 0.08, 0.62, 0.58, 0.24)
    # Carenado frontal aerodinámico (nariz FPV y radar)
    airframe_tris += make_frustum_z(0.32, 0.00, -0.04, 0.18, 0.22, 0.12, nseg=24)
    # Domo cilíndrico superior (LiDAR y antena RTK) -> alcanza Z = +0.350 m
    airframe_tris += make_cylinder_z(0.00, 0.00, (0.20 + LIDAR_TOP_Z_M) / 2.0, 0.085, LIDAR_TOP_Z_M - 0.20, nseg=32)
    
    # Tanque de pulverización de 100 L (volumen ~0.10 m³) montado bajo el chasis
    # Sección superior rectangular y fondo troncocónico convergente al manifold
    airframe_tris += make_box(-0.06, 0.00, -0.18, 0.58, 0.52, 0.24)
    airframe_tris += make_frustum_z(-0.06, 0.00, -0.38, -0.30, 0.16, 0.24, nseg=24)
    # Tapa de llenado de líquido (tapón sub-madre en parte superior del tanque)
    airframe_tris += make_cylinder_z(-0.14, 0.00, 0.21, 0.075, 0.035, nseg=24)
    # Bomba centrífuga magnética inferior
    airframe_tris += make_cylinder_z(-0.06, 0.00, -0.41, 0.11, 0.06, nseg=24)

    # --------------------------------------------------------------------------
    # C. TREN DE ATERRIZAJE (TRÍPODE / SKIDS)
    # --------------------------------------------------------------------------
    skid_y = 0.550
    skid_r = 0.020
    skid_z = SKID_BOTTOM_Z_M + skid_r  # -0.605 m eje, -0.625 m base
    
    # Dos patines horizontales en el suelo
    p_skid_r_start = np.array([-0.600,  skid_y, skid_z])
    p_skid_r_end   = np.array([+0.550,  skid_y, skid_z])
    p_skid_l_start = np.array([-0.600, -skid_y, skid_z])
    p_skid_l_end   = np.array([+0.550, -skid_y, skid_z])
    
    airframe_tris += make_tube(p_skid_r_start, p_skid_r_end, skid_r, nseg=18)
    airframe_tris += make_tube(p_skid_l_start, p_skid_l_end, skid_r, nseg=18)
    
    # Montantes diagonales del tren (delanteros y traseros)
    # Pata Delantera Derecha
    airframe_tris += make_tube(np.array([+0.220, +0.260, -0.100]), np.array([+0.350, +skid_y, skid_z]), skid_r, nseg=16)
    # Pata Delantera Izquierda
    airframe_tris += make_tube(np.array([+0.220, -0.260, -0.100]), np.array([+0.350, -skid_y, skid_z]), skid_r, nseg=16)
    # Pata Trasera Derecha
    airframe_tris += make_tube(np.array([-0.280, +0.260, -0.100]), np.array([-0.420, +skid_y, skid_z]), skid_r, nseg=16)
    # Pata Trasera Izquierda
    airframe_tris += make_tube(np.array([-0.280, -0.260, -0.100]), np.array([-0.420, -skid_y, skid_z]), skid_r, nseg=16)

    # --------------------------------------------------------------------------
    # D. BARRA DE PULVERIZACIÓN TRASERA MODELO LS100
    # --------------------------------------------------------------------------
    # Largueros longitudinales de soporte de barra desde el chasis inferior hacia atrás
    boom_attach_z = -0.3200
    boom_tube_r = 0.0160
    
    p_supp_r1 = np.array([-0.280, +0.280, -0.220])
    p_supp_r2 = np.array([-0.800, +0.4585, boom_attach_z])
    p_supp_l1 = np.array([-0.280, -0.280, -0.220])
    p_supp_l2 = np.array([-0.800, -0.4585, boom_attach_z])
    
    airframe_tris += make_tube(p_supp_r1, p_supp_r2, boom_tube_r, nseg=14)
    airframe_tris += make_tube(p_supp_l1, p_supp_l2, boom_tube_r, nseg=14)
    
    # Barra transversal de carbono de pulverización
    # Se extiende desde Y = -0.917 m hasta Y = +0.917 m
    p_boom_center_r = np.array([NOZZLE_X_INNER_M, +NOZZLE_SPACING_INNER_M / 2.0, boom_attach_z])
    p_boom_center_l = np.array([NOZZLE_X_INNER_M, -NOZZLE_SPACING_INNER_M / 2.0, boom_attach_z])
    p_boom_outer_r  = np.array([NOZZLE_X_OUTER_M, +NOZZLE_SPACING_OUTER_M / 2.0, boom_attach_z])
    p_boom_outer_l  = np.array([NOZZLE_X_OUTER_M, -NOZZLE_SPACING_OUTER_M / 2.0, boom_attach_z])
    
    # Tramo central de la barra
    airframe_tris += make_tube(p_boom_center_l, p_boom_center_r, boom_tube_r, nseg=14)
    # Tramo exterior derecho
    airframe_tris += make_tube(p_boom_center_r, p_boom_outer_r, boom_tube_r, nseg=14)
    # Tramo exterior izquierdo
    airframe_tris += make_tube(p_boom_center_l, p_boom_outer_l, boom_tube_r, nseg=14)

    # --------------------------------------------------------------------------
    # E. 4 ASPERSORES / ATOMIZADORES CENTRÍFUGOS LX07550SX (CRÍTICO DEPOSICIÓN)
    # --------------------------------------------------------------------------
    nozzles_data = [
        {
            "nozzle_id": "N1_left_outer",
            "position_role": "outer_left",
            "description": "Boquilla centrífuga exterior izquierda sobre barra LS100",
            "center_xyz_m": [round(NOZZLE_X_OUTER_M, 4), round(-NOZZLE_SPACING_OUTER_M / 2.0, 4), round(NOZZLE_Z_M, 4)],
            "spray_injection_vector": [0.0, 0.0, -1.0],
            "spray_sheet_angle_deg": 180.0,  # Disco centrífugo: eyección laminar radial plana 360/180
            "atomizer_model": "LX07550SX (Doble Disco Centrífugo)",
            "disc_diameter_mm": 100.0,
            "disc_rpm_max": 14000.0,
            "disc_rim_velocity_ms": round((14000.0 * 2.0 * math.pi / 60.0) * 0.05, 2),  # ~73.3 m/s
            "droplet_spectrum_um": {"d10": 50.0, "d50": 150.0, "d90": 300.0, "span": 1.67, "min": 10.0, "max": 500.0},
            "nominal_flow_Lmin": 10.0,  # 40 L/min total / 4 boquillas = 10 L/min por boquilla
            "nominal_flow_m3s": round(10.0 / 60000.0, 8),
            "boom_attachment_xyz_m": [round(p_boom_outer_l[0], 4), round(p_boom_outer_l[1], 4), round(p_boom_outer_l[2], 4)],
            "vertical_drop_from_arm_plane_m": round(abs(NOZZLE_Z_M), 4),
            "vertical_drop_from_lower_rotor_m": round(abs(NOZZLE_Z_M - ROTOR_LOWER_Z_M), 4),
            "clearance_above_ground_m": round(NOZZLE_Z_M - SKID_BOTTOM_Z_M, 4),
        },
        {
            "nozzle_id": "N2_left_inner",
            "position_role": "inner_left",
            "description": "Boquilla centrífuga interior izquierda sobre barra LS100",
            "center_xyz_m": [round(NOZZLE_X_INNER_M, 4), round(-NOZZLE_SPACING_INNER_M / 2.0, 4), round(NOZZLE_Z_M, 4)],
            "spray_injection_vector": [0.0, 0.0, -1.0],
            "spray_sheet_angle_deg": 180.0,
            "atomizer_model": "LX07550SX (Doble Disco Centrífugo)",
            "disc_diameter_mm": 100.0,
            "disc_rpm_max": 14000.0,
            "disc_rim_velocity_ms": round((14000.0 * 2.0 * math.pi / 60.0) * 0.05, 2),
            "droplet_spectrum_um": {"d10": 50.0, "d50": 150.0, "d90": 300.0, "span": 1.67, "min": 10.0, "max": 500.0},
            "nominal_flow_Lmin": 10.0,
            "nominal_flow_m3s": round(10.0 / 60000.0, 8),
            "boom_attachment_xyz_m": [round(p_boom_center_l[0], 4), round(p_boom_center_l[1], 4), round(p_boom_center_l[2], 4)],
            "vertical_drop_from_arm_plane_m": round(abs(NOZZLE_Z_M), 4),
            "vertical_drop_from_lower_rotor_m": round(abs(NOZZLE_Z_M - ROTOR_LOWER_Z_M), 4),
            "clearance_above_ground_m": round(NOZZLE_Z_M - SKID_BOTTOM_Z_M, 4),
        },
        {
            "nozzle_id": "N3_right_inner",
            "position_role": "inner_right",
            "description": "Boquilla centrífuga interior derecha sobre barra LS100",
            "center_xyz_m": [round(NOZZLE_X_INNER_M, 4), round(+NOZZLE_SPACING_INNER_M / 2.0, 4), round(NOZZLE_Z_M, 4)],
            "spray_injection_vector": [0.0, 0.0, -1.0],
            "spray_sheet_angle_deg": 180.0,
            "atomizer_model": "LX07550SX (Doble Disco Centrífugo)",
            "disc_diameter_mm": 100.0,
            "disc_rpm_max": 14000.0,
            "disc_rim_velocity_ms": round((14000.0 * 2.0 * math.pi / 60.0) * 0.05, 2),
            "droplet_spectrum_um": {"d10": 50.0, "d50": 150.0, "d90": 300.0, "span": 1.67, "min": 10.0, "max": 500.0},
            "nominal_flow_Lmin": 10.0,
            "nominal_flow_m3s": round(10.0 / 60000.0, 8),
            "boom_attachment_xyz_m": [round(p_boom_center_r[0], 4), round(p_boom_center_r[1], 4), round(p_boom_center_r[2], 4)],
            "vertical_drop_from_arm_plane_m": round(abs(NOZZLE_Z_M), 4),
            "vertical_drop_from_lower_rotor_m": round(abs(NOZZLE_Z_M - ROTOR_LOWER_Z_M), 4),
            "clearance_above_ground_m": round(NOZZLE_Z_M - SKID_BOTTOM_Z_M, 4),
        },
        {
            "nozzle_id": "N4_right_outer",
            "position_role": "outer_right",
            "description": "Boquilla centrífuga exterior derecha sobre barra LS100",
            "center_xyz_m": [round(NOZZLE_X_OUTER_M, 4), round(+NOZZLE_SPACING_OUTER_M / 2.0, 4), round(NOZZLE_Z_M, 4)],
            "spray_injection_vector": [0.0, 0.0, -1.0],
            "spray_sheet_angle_deg": 180.0,
            "atomizer_model": "LX07550SX (Doble Disco Centrífugo)",
            "disc_diameter_mm": 100.0,
            "disc_rpm_max": 14000.0,
            "disc_rim_velocity_ms": round((14000.0 * 2.0 * math.pi / 60.0) * 0.05, 2),
            "droplet_spectrum_um": {"d10": 50.0, "d50": 150.0, "d90": 300.0, "span": 1.67, "min": 10.0, "max": 500.0},
            "nominal_flow_Lmin": 10.0,
            "nominal_flow_m3s": round(10.0 / 60000.0, 8),
            "boom_attachment_xyz_m": [round(p_boom_outer_r[0], 4), round(p_boom_outer_r[1], 4), round(p_boom_outer_r[2], 4)],
            "vertical_drop_from_arm_plane_m": round(abs(NOZZLE_Z_M), 4),
            "vertical_drop_from_lower_rotor_m": round(abs(NOZZLE_Z_M - ROTOR_LOWER_Z_M), 4),
            "clearance_above_ground_m": round(NOZZLE_Z_M - SKID_BOTTOM_Z_M, 4),
        },
    ]

    for nz in nozzles_data:
        nx, ny, nz_coord = nz["center_xyz_m"]
        bx, by, bz = nz["boom_attachment_xyz_m"]
        
        # Brazo de bajada vertical/inclinado de la boquilla desde la barra
        p_boom_drop = np.array([bx, by, bz])
        p_nozzle_top = np.array([nx, ny, nz_coord + 0.060])
        airframe_tris += make_tube(p_boom_drop, p_nozzle_top, 0.0120, nseg=12)
        
        # Carcasa del motor de la boquilla centrífuga
        airframe_tris += make_cylinder_z(nx, ny, nz_coord + 0.035, 0.032, 0.050, nseg=20)
        # Campana/disco de lanzamiento centrífugo de la boquilla (superficie sólida del atomizador)
        airframe_tris += make_cylinder_z(nx, ny, nz_coord, 0.050, 0.016, nseg=24)
        
        # Geometría marcadora para inyección lagrangiana (malla de boquillas)
        spray_nozzles_tris += make_cylinder_z(nx, ny, nz_coord, 0.048, 0.008, nseg=24)

    # --------------------------------------------------------------------------
    # F. ESCRITURA DE ARCHIVOS STL
    # --------------------------------------------------------------------------
    stl_airframe_bin = OUT_DIR / "t100_airframe.stl"
    stl_airframe_asc = OUT_DIR / "t100_airframe_ascii.stl"
    write_stl_binary(stl_airframe_bin, airframe_tris, "DJI_T100_Airframe_CFD")
    write_stl_ascii(stl_airframe_asc, "t100_airframe", airframe_tris)
    print(f"[OK] Malla Airframe: {stl_airframe_bin.name} ({len(airframe_tris)} triángulos)")

    stl_rotors_bin = OUT_DIR / "t100_rotor_disks.stl"
    stl_rotors_asc = OUT_DIR / "t100_rotor_disks_ascii.stl"
    write_stl_binary(stl_rotors_bin, rotor_disks_tris, "DJI_T100_Actuator_Disks_CFD")
    write_stl_ascii(stl_rotors_asc, "t100_rotor_disks", rotor_disks_tris)
    print(f"[OK] Malla Rotores (8 discos actuadores): {stl_rotors_bin.name} ({len(rotor_disks_tris)} triángulos)")

    stl_nozzles_bin = OUT_DIR / "t100_spray_nozzles.stl"
    stl_nozzles_asc = OUT_DIR / "t100_spray_nozzles_ascii.stl"
    write_stl_binary(stl_nozzles_bin, spray_nozzles_tris, "DJI_T100_Spray_Nozzles_CFD")
    write_stl_ascii(stl_nozzles_asc, "t100_spray_nozzles", spray_nozzles_tris)
    print(f"[OK] Malla Boquillas (4 atomizadores): {stl_nozzles_bin.name} ({len(spray_nozzles_tris)} triángulos)")

    full_assembly_tris = airframe_tris + rotor_disks_tris + spray_nozzles_tris
    stl_full_bin = OUT_DIR / "t100_full_assembly.stl"
    write_stl_binary(stl_full_bin, full_assembly_tris, "DJI_T100_Full_Assembly_CFD")
    print(f"[OK] Malla Ensamblaje Completo: {stl_full_bin.name} ({len(full_assembly_tris)} triángulos)")

    # --------------------------------------------------------------------------
    # G. CONSTRUCCIÓN DEL ARCHIVO JSON MAESTRO DE COORDENADAS
    # --------------------------------------------------------------------------
    json_data = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "platform": "DJI Agras T100",
        "description": "Especificación tridimensional fiel y paramétrica de elementos funcionales del DJI Agras T100 para CFD y transporte/deposición de gotas",
        "generated_by": "scripts/generate_t100_cfd_model.py",
        "coordinate_system": {
            "origin": "Centro geométrico del chasis en el plano medio de los tubos de brazos de carbono",
            "axes_convention": "Aeronáutica mano derecha (SAE / CFD)",
            "x_axis": "+X hacia adelante (eje de avance de vuelo)",
            "y_axis": "+Y hacia estribor / derecha del dron",
            "z_axis": "+Z vertical hacia arriba (opuesto a gravedad y downwash)",
            "units": "metros (m), grados sexagesimales (deg), segundos (s), kilogramos (kg)"
        },
        "general_dimensions": {
            "wheelbase_diagonal_mm": 2330.0,
            "wheelbase_diagonal_m": WHEELBASE_DIAG_M,
            "radius_center_to_axis_m": ARM_RADIUS_M,
            "adjacent_axis_distance_m": round(math.sqrt(2.0) * ARM_RADIUS_M, 4),
            "unfolded_envelope_with_props_mm": [3220, 3224, 975],
            "modeled_envelope_with_props_mm": [
                round((2.0 * (ARM_RADIUS_M * math.cos(math.pi / 4.0)) + ROTOR_DIAMETER_M) * 1000.0, 1),
                round((2.0 * (ARM_RADIUS_M * math.sin(math.pi / 4.0)) + ROTOR_DIAMETER_M) * 1000.0, 1),
                round(TOTAL_HEIGHT_M * 1000.0, 1)
            ],
            "total_height_m": TOTAL_HEIGHT_M,
            "ground_contact_z_m": SKID_BOTTOM_Z_M,
            "lidar_top_apex_z_m": LIDAR_TOP_Z_M
        },
        "mass_and_payload": {
            "empty_weight_with_battery_2nozzles_kg": 73.0,
            "empty_weight_with_battery_4nozzles_kg": 74.9,
            "payload_tank_capacity_L": 100.0,
            "payload_tank_capacity_kg": 100.0,
            "mtow_spraying_kg": 175.0,
            "battery_model": "DB2160 (14.7 kg, 41 Ah, 52 V)"
        },
        "propulsion_and_rotors": {
            "total_rotors_count": 8,
            "coaxial_pairs_count": 4,
            "rotor_diameter_m": ROTOR_DIAMETER_M,
            "rotor_diameter_inches": 62.0,
            "propeller_pitch_inches": 23.0,
            "blades_per_rotor": 2,
            "blade_model": "6223 fibra de carbono plegable",
            "coaxial_axial_gap_m": COAXIAL_DZ_M,
            "upper_rotor_plane_z_m": ROTOR_UPPER_Z_M,
            "lower_rotor_plane_z_m": ROTOR_LOWER_Z_M,
            "actuator_disk_thickness_m": ROTOR_DISK_THICKNESS_M,
            "total_disk_area_m2": round(8.0 * math.pi * (ROTOR_RADIUS_M ** 2), 4),
            "max_arm_thrust_kg": 82.0,
            "max_arm_thrust_N": round(82.0 * 9.80665, 2),
            "motor_model": "155P (estator 155x16 mm, 60 KV)",
            "rotors": rotors_data
        },
        "arms": arms_data,
        "spraying_system": {
            "boom_model": "LS100 barra trasera",
            "atomizer_model": "LX07550SX atomizador centrífugo de doble disco",
            "total_nozzles_count": 4,
            "outer_nozzle_spacing_m": NOZZLE_SPACING_OUTER_M,
            "inner_nozzle_spacing_m": NOZZLE_SPACING_INNER_M,
            "nozzle_z_level_m": NOZZLE_Z_M,
            "max_total_flow_Lmin": 40.0,
            "standard_2nozzle_flow_Lmin": 30.0,
            "atomization_type": "centrífuga rotativa",
            "disc_max_rpm": 14000.0,
            "droplet_spectrum_um_range": [10.0, 500.0],
            "nozzles": nozzles_data
        },
        "landing_gear": {
            "skid_width_m": skid_y * 2.0,
            "skid_length_m": 1.150,
            "skid_bottom_z_m": SKID_BOTTOM_Z_M,
            "right_skid_axis": {
                "p_start_xyz_m": [round(p_skid_r_start[0], 4), round(p_skid_r_start[1], 4), round(p_skid_r_start[2], 4)],
                "p_end_xyz_m":   [round(p_skid_r_end[0], 4),   round(p_skid_r_end[1], 4),   round(p_skid_r_end[2], 4)]
            },
            "left_skid_axis": {
                "p_start_xyz_m": [round(p_skid_l_start[0], 4), round(p_skid_l_start[1], 4), round(p_skid_l_start[2], 4)],
                "p_end_xyz_m":   [round(p_skid_l_end[0], 4),   round(p_skid_l_end[1], 4),   round(p_skid_l_end[2], 4)]
            }
        },
        "cfd_openfoam_guidelines": {
            "snappyHexMesh_surfaces": {
                "airframe": "t100_airframe.stl (pared impermeable no deslizamiento)",
                "rotor_disks": "t100_rotor_disks.stl (zonas celulares cellZone para actuationDiskSource o MRF)",
                "spray_nozzles": "t100_spray_nozzles.stl (puntos o parches de inyección Lagrangiana)"
            },
            "droplet_deposition_module": {
                "injector_type": "cone / rotatingDiscInjector (centrifugal sheet atomization)",
                "injection_coordinates": [nz["center_xyz_m"] for nz in nozzles_data],
                "injection_directions": [nz["spray_injection_vector"] for nz in nozzles_data],
                "recommended_d50_um": 150.0,
                "recommended_d10_um": 50.0,
                "recommended_d90_um": 300.0,
                "fluid": "agua (rho=997.0 kg/m3, mu=1.002e-3 Pa.s a 20 C, o 28 C según context.md)"
            }
        }
    }

    json_path = OUT_DIR / "t100_cfd_coordinates.json"
    json_path.write_text(json.dumps(json_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] Archivo JSON de coordenadas generado: {json_path.name}")

    # --------------------------------------------------------------------------
    # H. GENERACIÓN DE GRÁFICO DE VERIFICACIÓN ORTOGRÁFICA Y DE CONTROL
    # --------------------------------------------------------------------------
    plot_path = OUT_DIR / "t100_geometry_verification.png"
    fig, axs = plt.subplots(2, 2, figsize=(16, 14), dpi=150)
    
    # 1. Vista Superior (Planta XY)
    ax = axs[0, 0]
    ax.set_title("VISTA SUPERIOR (Planta XY) - DJI Agras T100", fontsize=12, fontweight="bold")
    ax.set_xlabel("X (m) [Avance]", fontsize=10)
    ax.set_ylabel("Y (m) [Transversal]", fontsize=10)
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.set_aspect("equal")
    
    # Discos de rotores
    for rot in rotors_data:
        rx, ry, _ = rot["center_xyz_m"]
        col = "blue" if rot["position_role"] == "upper" else "cyan"
        circle = plt.Circle((rx, ry), ROTOR_RADIUS_M, color=col, fill=False, linestyle="-" if rot["position_role"]=="upper" else "--", alpha=0.5, linewidth=1.5)
        ax.add_patch(circle)
        ax.plot(rx, ry, marker="o", color="darkblue", markersize=4)
        
    # Brazos
    for arm_id, ainfo in arms_data.items():
        ex, ey, _ = ainfo["axis_center_m"]
        ax.plot([0, ex], [0, ey], color="black", linewidth=3, solid_capstyle="round")
        ax.text(ex * 1.12, ey * 1.12, arm_id, fontsize=9, fontweight="bold", ha="center", va="center")
    
    # Barra trasera y boquillas
    boom_xs = [NOZZLE_X_OUTER_M, NOZZLE_X_INNER_M, NOZZLE_X_INNER_M, NOZZLE_X_OUTER_M]
    boom_ys = [-NOZZLE_SPACING_OUTER_M/2, -NOZZLE_SPACING_INNER_M/2, +NOZZLE_SPACING_INNER_M/2, +NOZZLE_SPACING_OUTER_M/2]
    ax.plot(boom_xs, boom_ys, color="darkgreen", linewidth=2.5, linestyle="-", label="Barra Trasera LS100")
    
    for nz in nozzles_data:
        nx, ny, _ = nz["center_xyz_m"]
        ax.plot(nx, ny, marker="s", color="red", markersize=8)
        ax.text(nx - 0.08, ny, nz["nozzle_id"], fontsize=8, color="darkred", ha="right", va="center", fontweight="bold")
        
    # Círculo diagonal
    diag_circle = plt.Circle((0, 0), ARM_RADIUS_M, color="gray", fill=False, linestyle=":", alpha=0.7)
    ax.add_patch(diag_circle)
    ax.text(0, -ARM_RADIUS_M * 0.8, f"Wheelbase D={WHEELBASE_DIAG_M*1000:.0f} mm", color="gray", ha="center", fontsize=9)
    ax.set_xlim(-2.0, 2.0)
    ax.set_ylim(-2.0, 2.0)
    
    # 2. Vista Lateral (Perfil XZ)
    ax = axs[0, 1]
    ax.set_title("VISTA LATERAL (Perfil XZ)", fontsize=12, fontweight="bold")
    ax.set_xlabel("X (m) [Avance]", fontsize=10)
    ax.set_ylabel("Z (m) [Vertical]", fontsize=10)
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.set_aspect("equal")
    
    # Rotores planos
    ax.axhline(ROTOR_UPPER_Z_M, color="blue", linestyle="-", label=f"Rotor Sup. (Z={ROTOR_UPPER_Z_M:+.3f} m)")
    ax.axhline(ROTOR_LOWER_Z_M, color="cyan", linestyle="--", label=f"Rotor Inf. (Z={ROTOR_LOWER_Z_M:+.3f} m)")
    ax.axhline(0.0, color="gray", linestyle=":", alpha=0.7, label="Plano Brazos (Z=0)")
    ax.axhline(SKID_BOTTOM_Z_M, color="black", linestyle="-", linewidth=2, label=f"Suelo / Patines (Z={SKID_BOTTOM_Z_M:+.3f} m)")
    
    # Rotores discos
    for ex in [+ARM_RADIUS_M * math.cos(math.pi/4), -ARM_RADIUS_M * math.cos(math.pi/4)]:
        ax.plot([ex - ROTOR_RADIUS_M, ex + ROTOR_RADIUS_M], [ROTOR_UPPER_Z_M, ROTOR_UPPER_Z_M], color="blue", linewidth=3)
        ax.plot([ex - ROTOR_RADIUS_M, ex + ROTOR_RADIUS_M], [ROTOR_LOWER_Z_M, ROTOR_LOWER_Z_M], color="cyan", linewidth=3)
        ax.plot([ex, ex], [-MOTOR_POD_HALF_H_M, MOTOR_POD_HALF_H_M], color="black", linewidth=4)
        
    # Boquillas
    for nz in nozzles_data:
        nx, _, nz_coord = nz["center_xyz_m"]
        ax.plot(nx, nz_coord, marker="s", color="red", markersize=8)
    ax.axhline(NOZZLE_Z_M, color="red", linestyle=":", label=f"Boquillas (Z={NOZZLE_Z_M:+.3f} m)")
    
    ax.set_xlim(-2.0, 2.0)
    ax.set_ylim(-0.8, 0.5)
    ax.legend(loc="upper right", fontsize=8)

    # 3. Vista Trasera / Frontal (Alzado YZ)
    ax = axs[1, 0]
    ax.set_title("VISTA TRASERA / FRONTAL (Alzado YZ)", fontsize=12, fontweight="bold")
    ax.set_xlabel("Y (m) [Transversal]", fontsize=10)
    ax.set_ylabel("Z (m) [Vertical]", fontsize=10)
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.set_aspect("equal")
    
    ax.axhline(ROTOR_UPPER_Z_M, color="blue", linestyle="-", alpha=0.5)
    ax.axhline(ROTOR_LOWER_Z_M, color="cyan", linestyle="--", alpha=0.5)
    ax.axhline(SKID_BOTTOM_Z_M, color="black", linestyle="-", linewidth=2)
    
    for ey in [+ARM_RADIUS_M * math.sin(math.pi/4), -ARM_RADIUS_M * math.sin(math.pi/4)]:
        ax.plot([ey - ROTOR_RADIUS_M, ey + ROTOR_RADIUS_M], [ROTOR_UPPER_Z_M, ROTOR_UPPER_Z_M], color="blue", linewidth=3)
        ax.plot([ey - ROTOR_RADIUS_M, ey + ROTOR_RADIUS_M], [ROTOR_LOWER_Z_M, ROTOR_LOWER_Z_M], color="cyan", linewidth=3)
        ax.plot([ey, ey], [-MOTOR_POD_HALF_H_M, MOTOR_POD_HALF_H_M], color="black", linewidth=4)
        
    # Boquillas en YZ
    for nz in nozzles_data:
        _, ny, nz_coord = nz["center_xyz_m"]
        ax.plot(ny, nz_coord, marker="s", color="red", markersize=8)
        ax.text(ny, nz_coord - 0.05, f"{ny*1000:+.0f} mm", fontsize=8, ha="center", color="darkred")
    
    ax.annotate(
        f"Separación Boquillas Ext. = {NOZZLE_SPACING_OUTER_M*1000:.0f} mm",
        xy=(-NOZZLE_SPACING_OUTER_M/2, NOZZLE_Z_M),
        xytext=(0, NOZZLE_Z_M - 0.12),
        ha="center", fontsize=9, fontweight="bold", color="darkred",
        arrowprops=dict(arrowstyle="->", color="darkred", lw=1.2)
    )
    
    ax.set_xlim(-2.0, 2.0)
    ax.set_ylim(-0.8, 0.5)
    
    # 4. Resumen Metrológico y Parámetros Operativos
    ax = axs[1, 1]
    ax.axis("off")
    resumen_text = (
        "DJI AGRAS T100 — RESUMEN METROLÓGICO Y CFD\n"
        "====================================================\n\n"
        f"• Distancia entre ejes (diagonal): {WHEELBASE_DIAG_M*1000:.0f} mm\n"
        f"• Separación entre ejes adyacentes: {math.sqrt(2)*ARM_RADIUS_M*1000:.1f} mm\n"
        f"• Envergadura con hélices: {json_data['general_dimensions']['modeled_envelope_with_props_mm'][0]} x {json_data['general_dimensions']['modeled_envelope_with_props_mm'][1]} mm\n"
        f"• Altura total del modelo: {TOTAL_HEIGHT_M*1000:.1f} mm (oficial 975 mm)\n\n"
        "PROPULSIÓN COAXIAL (8 ROTORES):\n"
        f"• Hélices: 6223 (Diámetro: {ROTOR_DIAMETER_M*1000:.1f} mm / 62 in, Paso: 23 in)\n"
        f"• Separación axial coaxial: {COAXIAL_DZ_M*1000:.1f} mm (Z_sup = {ROTOR_UPPER_Z_M*1000:+.1f}, Z_inf = {ROTOR_LOWER_Z_M*1000:+.1f})\n"
        f"• Espesor de celda disco actuador: {ROTOR_DISK_THICKNESS_M*1000:.0f} mm\n"
        f"• Área total de disco actuador: {json_data['propulsion_and_rotors']['total_disk_area_m2']:.2f} m²\n\n"
        "SISTEMA DE PULVERIZACIÓN (BARRA LS100 + 4 ATOMIZADORES LX07550SX):\n"
        f"• Separación boquillas exteriores (N1, N4): {NOZZLE_SPACING_OUTER_M*1000:.0f} mm (Y = ±{NOZZLE_SPACING_OUTER_M*500:.1f} mm)\n"
        f"• Separación boquillas interiores (N2, N3): {NOZZLE_SPACING_INNER_M*1000:.0f} mm (Y = ±{NOZZLE_SPACING_INNER_M*500:.1f} mm)\n"
        f"• Cota vertical de atomización: Z = {NOZZLE_Z_M*1000:+.1f} mm ({abs(NOZZLE_Z_M)*1000:.0f} mm bajo brazos)\n"
        f"• Caída bajo rotor inferior: {abs(NOZZLE_Z_M - ROTOR_LOWER_Z_M)*1000:.1f} mm\n"
        f"• Despeje sobre el suelo: {(NOZZLE_Z_M - SKID_BOTTOM_Z_M)*1000:.1f} mm\n"
        f"• Retranqueo longitudinal (X): Exteriores X={NOZZLE_X_OUTER_M:.3f} m, Interiores X={NOZZLE_X_INNER_M:.3f} m\n"
        f"• Caudal por boquilla: {nozzles_data[0]['nominal_flow_Lmin']} L/min (Total: 40 L/min)\n"
        f"• Régimen de disco centrífugo: hasta {nozzles_data[0]['disc_rpm_max']:.0f} RPM (V_tan = {nozzles_data[0]['disc_rim_velocity_ms']} m/s)\n"
        f"• Espectro de gota: D10={nozzles_data[0]['droplet_spectrum_um']['d10']} µm, D50={nozzles_data[0]['droplet_spectrum_um']['d50']} µm, D90={nozzles_data[0]['droplet_spectrum_um']['d90']} µm"
    )
    ax.text(0.02, 0.98, resumen_text, transform=ax.transAxes, fontsize=8.5, verticalalignment="top", fontfamily="monospace",
            bbox=dict(boxstyle="round,pad=0.6", facecolor="whitesmoke", edgecolor="lightgray", alpha=0.9))
    
    plt.tight_layout()
    plt.savefig(plot_path, bbox_inches="tight")
    plt.close()
    print(f"[OK] Gráfico de verificación generado: {plot_path.name}")
    
    print("=" * 80)
    print("MODELADO COMPLETADO EXITOSAMENTE EN:", OUT_DIR)
    print("=" * 80)
    return 0

if __name__ == "__main__":
    raise SystemExit(generate_t100_cfd_dataset())
