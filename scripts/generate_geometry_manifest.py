"""
OBSOLETO — NO USAR. Sustituido por scripts/build_geometry_manifests.py (2026-09-14).

Sus salidas eran INCORRECTAS y contradecian las fichas verificadas. Se conserva solo
como registro de lo que se hizo (context.md SS39: no borrar errores, documentarlos).
NO LO EJECUTES: sobrescribiria geometry/*_geometry_manifest.json con datos inventados.

Defectos documentados del generador antiguo:
  1. Declaraba T25P, T55 y T70P como cuadricopteros de 4 rotores, cuando el numero de
     rotores es D (desconocido) en las propias fichas, y T55 tiene "4 pares de helices".
  2. Wheelbase inventado: 2135 / 2800 / 3300 / 3800 mm frente a los oficiales
     1970 / 2415 / 2440 / 2330 mm.
  3. Diametros de rotor inventados: 1.35 / 1.45 / 1.55 / 1.65 m frente a los oficiales
     1.270 / 1.575 / 1.575 / 1.574 m.
  4. max_rpm inventado (3400 / 2900 / 2600 / 2200) sin fuente. context.md SS42 prohibe
     inferir RPM; el riesgo R1 esta declarado como pendiente de medicion.
  5. Error geometrico: dividia el wheelbase por sqrt(2) dos veces, dejando los rotores
     a 1.51 m del centro para un wheelbase de 2135 mm.
  6. Afirmaba en el docstring "corrects rotor topologies based on exact DJI Agras
     architecture": una afirmacion de exactitud sin medicion que la respalde.

Ver geometry/protocolo_geometria.md y geometry/manifests/ para los datos corregidos.
"""
import json
import numpy as np

def generate_accurate_geometry_manifests():
    """
    Corrects rotor topologies based on exact DJI Agras architecture:
    - T25P, T55, T70P: Strict 4-rotor X-configuration (Quadcopter X).
    - T100: 8-rotor Coaxial X-configuration (Octocopter coaxial X).
    """
    
    # 1. Quadcopter X-configuration (4 rotors): T25P, T55, T70P
    quad_platforms = [
        {"name": "DJI Agras T25P", "filename": "geometry/t25p_geometry_manifest.json", "wheelbase": 2135, "rotor_dia": 1.35, "max_rpm": 3400},
        {"name": "DJI Agras T55", "filename": "geometry/t55_geometry_manifest.json", "wheelbase": 2800, "rotor_dia": 1.45, "max_rpm": 2900},
        {"name": "DJI Agras T70P", "filename": "geometry/t70p_geometry_manifest.json", "wheelbase": 3300, "rotor_dia": 1.55, "max_rpm": 2600}
    ]
    
    for plat in quad_platforms:
        wb_m = plat["wheelbase"] / 1000.0 / np.sqrt(2.0) # Diagonal offset
        spec = {
            "platform": plat["name"],
            "configuration": "Quadcopter X-configuration (4 rotors)",
            "wheelbase_mm": plat["wheelbase"],
            "rotors": [
                {"id": "R1_FL", "role": "Front-Left", "position_xyz_m": [wb_m, wb_m, 0.10], "diameter_m": plat["rotor_dia"], "direction": "CCW", "max_rpm": plat["max_rpm"]},
                {"id": "R2_FR", "role": "Front-Right", "position_xyz_m": [wb_m, -wb_m, 0.10], "diameter_m": plat["rotor_dia"], "direction": "CW", "max_rpm": plat["max_rpm"]},
                {"id": "R3_RL", "role": "Rear-Left", "position_xyz_m": [-wb_m, wb_m, 0.10], "diameter_m": plat["rotor_dia"], "direction": "CW", "max_rpm": plat["max_rpm"]},
                {"id": "R4_RR", "role": "Rear-Right", "position_xyz_m": [-wb_m, -wb_m, 0.10], "diameter_m": plat["rotor_dia"], "direction": "CCW", "max_rpm": plat["max_rpm"]}
            ],
            "atomizers": {
                "standard_dual": [
                    {"id": "N1_FrontLeft", "position_xyz_m": [0.4, 0.3, -0.25], "orientation_deg": [0.0, 0.0, -90.0]},
                    {"id": "N2_FrontRight", "position_xyz_m": [0.4, -0.3, -0.25], "orientation_deg": [0.0, 0.0, -90.0]}
                ],
                "optional_quad": [
                    {"id": "N1_FrontLeft", "position_xyz_m": [0.4, 0.3, -0.25], "orientation_deg": [0.0, 0.0, -90.0]},
                    {"id": "N2_FrontRight", "position_xyz_m": [0.4, -0.3, -0.25], "orientation_deg": [0.0, 0.0, -90.0]},
                    {"id": "N3_RearLeft", "position_xyz_m": [-0.4, 0.3, -0.25], "orientation_deg": [0.0, 0.0, -90.0]},
                    {"id": "N4_RearRight", "position_xyz_m": [-0.4, -0.3, -0.25], "orientation_deg": [0.0, 0.0, -90.0]}
                ]
            }
        }
        with open(plat["filename"], "w") as f:
            json.dump(spec, f, indent=4)

    # 2. Octocopter Coaxial X-configuration (8 rotors): T100
    wb_t100 = 3800 / 1000.0 / np.sqrt(2.0)
    t100_spec = {
        "platform": "DJI Agras T100",
        "configuration": "Octocopter Coaxial X-configuration (8 rotors)",
        "wheelbase_mm": 3800,
        "rotors": [
            {"id": "R1_FL_Upper", "role": "Front-Left Upper", "position_xyz_m": [wb_t100, wb_t100, 0.15], "diameter_m": 1.65, "direction": "CCW", "max_rpm": 2200},
            {"id": "R2_FL_Lower", "role": "Front-Left Lower", "position_xyz_m": [wb_t100, wb_t100, -0.15], "diameter_m": 1.65, "direction": "CW", "max_rpm": 2200},
            {"id": "R3_FR_Upper", "role": "Front-Right Upper", "position_xyz_m": [wb_t100, -wb_t100, 0.15], "diameter_m": 1.65, "direction": "CW", "max_rpm": 2200},
            {"id": "R4_FR_Lower", "role": "Front-Right Lower", "position_xyz_m": [wb_t100, -wb_t100, -0.15], "diameter_m": 1.65, "direction": "CCW", "max_rpm": 2200},
            {"id": "R5_RL_Upper", "role": "Rear-Left Upper", "position_xyz_m": [-wb_t100, wb_t100, 0.15], "diameter_m": 1.65, "direction": "CW", "max_rpm": 2200},
            {"id": "R6_RL_Lower", "role": "Rear-Left Lower", "position_xyz_m": [-wb_t100, wb_t100, -0.15], "diameter_m": 1.65, "direction": "CCW", "max_rpm": 2200},
            {"id": "R7_RR_Upper", "role": "Rear-Right Upper", "position_xyz_m": [-wb_t100, -wb_t100, 0.15], "diameter_m": 1.65, "direction": "CCW", "max_rpm": 2200},
            {"id": "R8_RR_Lower", "role": "Rear-Right Lower", "position_xyz_m": [-wb_t100, -wb_t100, -0.15], "diameter_m": 1.65, "direction": "CW", "max_rpm": 2200}
        ],
        "atomizers": {
            "quad_configuration": [
                {"id": "N1_FrontLeft", "position_xyz_m": [0.6, 0.5, -0.3], "orientation_deg": [0.0, 0.0, -90.0]},
                {"id": "N2_FrontRight", "position_xyz_m": [0.6, -0.5, -0.3], "orientation_deg": [0.0, 0.0, -90.0]},
                {"id": "N3_RearLeft", "position_xyz_m": [-0.6, 0.5, -0.3], "orientation_deg": [0.0, 0.0, -90.0]},
                {"id": "N4_RearRight", "position_xyz_m": [-0.6, -0.5, -0.3], "orientation_deg": [0.0, 0.0, -90.0]}
            ]
        }
    }
    with open("geometry/t100_geometry_manifest.json", "w") as f:
        json.dump(t100_spec, f, indent=4)
        
    print("Successfully updated geometry manifests: T25P, T55, T70P as 4-rotor X-copters; T100 as 8-rotor coaxial X-copter.")

if __name__ == "__main__":
    generate_accurate_geometry_manifests()
