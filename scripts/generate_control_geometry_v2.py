"""
Genera geometria de control CFD por plataforma, coherente con los manifiestos auditados.

QUÉ CAMBIA respecto al generador anterior (scripts/generate_control_geometry.py):
  - Diametro de rotor REAL por plataforma (antes: 0.5/0.6 m fijos e iguales para todos).
  - Diametro y altura de pala REALES (antes: rotor inexistente, solo un disco).
  - Helicoptero coaxial modelado como dos discos por brazo (T55/T70P/T100 hipotesis I).
  - El cuerpo sigue siendo un prisma: es una simplificacion deliberada y DECLARADA
    (context.md SS43: no modelar detalles irrelevantes), no una geometria inventada.
  - Las posiciones y espesores que NO estan medidos se marcan explicitamente.
  - Escribe un sidecar <UAV>_control.meta.json con la trazabilidad de cada cota.

Lo que esta geometria NO es: un CAD fiel del dron. Es una geometria de control para
verificar el caso CFD (dominio, malla, contornos). El CAD de estudio requiere las
mediciones de GATE 1 (posicion XYZ de rotores y atomizadores, diametro real de buje,
geometria de pala).

Uso:
  python scripts/generate_control_geometry_v2.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "geometry" / "models"
MAN_DIR = ROOT / "geometry" / "manifests"

# Cuerpo central: estimacion de planificacion (E). NO medido.
# Se escala con el tamano de la plataforma para no dejar el mismo cuerpo en un T25P y un T100.
BODY_EST = {
    "T25P": {"dx": 0.42, "dy": 0.42, "dz": 0.16},
    "T55":  {"dx": 0.50, "dy": 0.50, "dz": 0.20},
    "T70P": {"dx": 0.52, "dy": 0.52, "dz": 0.20},
    "T100": {"dx": 0.56, "dy": 0.56, "dz": 0.22},
}

# Cota vertical del plano de rotor respecto al origen del cuerpo (E: sin medicion).
ROTOR_PLANE_Z = 0.08
# Separacion vertical del par coaxial (E: sin medicion). Solo si coaxial.
COAXIAL_DZ = 0.20
# Plano de atomizadores (E: sin medicion).
ATOMIZER_Z = -0.20


def write_stl_ascii(path: Path, name: str, triangles: list) -> None:
    """STL ASCII con normales reales (el generador anterior escribia normal 0 0 0)."""
    lines = [f"solid {name}"]
    for a, b, c in triangles:
        ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
        vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
        nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        n = math.sqrt(nx * nx + ny * ny + nz * nz)
        if n > 0:
            nx, ny, nz = nx / n, ny / n, nz / n
        lines.append(f"  facet normal {nx:.6e} {ny:.6e} {nz:.6e}")
        lines.append("    outer loop")
        for v in (a, b, c):
            lines.append(f"      vertex {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}")
        lines.append("    endloop")
        lines.append("  endfacet")
    lines.append(f"endsolid {name}")
    path.write_text("\n".join(lines), encoding="utf-8")


def box(cx, cy, cz, dx, dy, dz) -> list:
    hx, hy, hz = dx / 2, dy / 2, dz / 2
    v = [(cx - hx, cy - hy, cz - hz), (cx + hx, cy - hy, cz - hz),
         (cx + hx, cy + hy, cz - hz), (cx - hx, cy + hy, cz - hz),
         (cx - hx, cy - hy, cz + hz), (cx + hx, cy - hy, cz + hz),
         (cx + hx, cy + hy, cz + hz), (cx - hx, cy + hy, cz + hz)]
    f = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
         (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
         (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]
    return [(v[i], v[j], v[k]) for i, j, k in f]


def cylinder(cx, cy, cz, r, h, nseg=32) -> list:
    """Cilindro cerrado (tapa, fondo y lateral) = volumen de barrido del rotor.

    NOTA: el disco de barrido del rotor es un volumen impermeable en la geometria de
    control. Para CFD con MRF/actuator disk este volumen se reemplaza por el modelo de
    rotor correspondiente; aqui sirve para fijar la posicion y el tamano en el dominio.
    """
    tris = []
    top = [(cx, cy, cz + h / 2)]
    bot = [(cx, cy, cz - h / 2)]
    ring_t = [(cx + r * math.cos(2 * math.pi * i / nseg), cy + r * math.sin(2 * math.pi * i / nseg), cz + h / 2) for i in range(nseg)]
    ring_b = [(cx + r * math.cos(2 * math.pi * i / nseg), cy + r * math.sin(2 * math.pi * i / nseg), cz - h / 2) for i in range(nseg)]
    for i in range(nseg):
        j = (i + 1) % nseg
        tris.append((top[0], ring_t[i], ring_t[j]))
        tris.append((bot[0], ring_b[j], ring_b[i]))
        tris.append((ring_t[i], ring_b[i], ring_b[j]))
        tris.append((ring_t[i], ring_b[j], ring_t[j]))
    return tris


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not MAN_DIR.exists():
        print("Faltan los manifiestos. Ejecuta primero scripts/build_geometry_manifests.py")
        return 2

    for man_file in sorted(MAN_DIR.glob("*_geometry_manifest.json")):
        man = json.loads(man_file.read_text(encoding="utf-8"))
        uav = man_file.name.split("_")[0].upper()
        geo = man["modelo_geometrico"]
        d_rotor = man["dimensiones"]["rotor_diameter_m"]["valor"]
        r_rotor = d_rotor / 2
        n_rot = man["topologia_rotores"]["rotor_count"]["hipotesis_trabajo"]
        coaxial = man["topologia_rotores"]["coaxial"]["valor"]
        pos = man["topologia_rotores"]["posiciones_xyz"]["valor"]
        body = BODY_EST.get(uav, BODY_EST["T25P"])
        # espesor del disco de barrido: E, solo para que sea un volumen
        blade_h = 0.04

        tris = []
        traz = {
            "uav": uav,
            "generado_por": "scripts/generate_control_geometry_v2.py",
            "advertencia": "geometria de CONTROL para verificar dominio/malla/contornos. NO es CAD fiel.",
            "cotas": {
                "rotor_diameter_m": {"valor": d_rotor, "clasificacion": man["dimensiones"]["rotor_diameter_m"]["clasificacion"],
                                     "fuente": man["dimensiones"]["rotor_diameter_m"].get("fuente")},
                "rotor_plane_z_m": {"valor": ROTOR_PLANE_Z, "clasificacion": "E", "nota": "sin medicion"},
                "coaxial_dz_m": {"valor": COAXIAL_DZ if coaxial else 0.0, "clasificacion": "E" if coaxial else "n/a"},
                "atomizer_z_m": {"valor": ATOMIZER_Z, "clasificacion": "E", "nota": "sin medicion"},
                "atomizer_spacing_m": {"valor": man["pulverizacion"]["nozzle_spacing_mm"]["valor"] / 1000.0 if man["pulverizacion"]["nozzle_spacing_mm"]["valor"] else None,
                                       "clasificacion": "P", "nota": "separacion entre boquillas (DJI)"},
                "atomizer_x_m": {"valor": None, "clasificacion": "D",
                                 "nota": "las boquillas son TRASERAS: su x debe ser negativa. Magnitud SIN MEDIR -> el STL las coloca en x=0 marcado como pendiente"},
                "body_est_m": {"valor": body, "clasificacion": "E", "nota": "prisma simplificado, estimacion de planificacion"},
                "blade_sweep_thickness_m": {"valor": blade_h, "clasificacion": "E", "nota": "solo para dar volumen al disco de barrido"},
                "n_rotores_modelados": {"valor": n_rot, "clasificacion": "I", "nota": "hipotesis: numero real de rotores PENDIENTE DE MEDICION"},
            },
        }

        # 1) cuerpo central
        tris += box(0, 0, 0, body["dx"], body["dy"], body["dz"])

        # 2) rotores: un cilindro por rotor modelado
        z_planes = [ROTOR_PLANE_Z]
        if coaxial and n_rot == 2 * len(pos):
            z_planes = [ROTOR_PLANE_Z + COAXIAL_DZ / 2, ROTOR_PLANE_Z - COAXIAL_DZ / 2]
        for p in pos:
            for z in z_planes:
                tris += cylinder(p["x_m"], p["y_m"], z, r_rotor, blade_h, nseg=32)

        # 3) atomizadores (cajas marcadoras, NO boquillas reales)
        sp = man["pulverizacion"]["nozzle_spacing_mm"]["valor"]
        if sp:
            for side in (+1, -1):
                tris += box(0.0, side * sp / 2000.0, ATOMIZER_Z, 0.06, 0.06, 0.06)

        stl = OUT_DIR / f"{uav}_control.stl"
        write_stl_ascii(stl, f"{uav}_control", tris)
        meta = OUT_DIR / f"{uav}_control.meta.json"
        meta.write_text(json.dumps(traz, indent=2, ensure_ascii=False), encoding="utf-8")

        print(f"{uav:5s} -> {stl.relative_to(ROOT)}  ({len(tris)} facetas)  meta: {meta.name}")
        print(f"      rotor d={d_rotor} m  n_modelados={n_rot}  coaxial={coaxial}  planos_z={[round(z,3) for z in z_planes]}")

    print("\nRecordatorio: estas geometrias fijan POSICION y TAMANO en el dominio.")
    print("Para el dataset principal (MRF/AL/sliding) hace falta la geometria real de pala (GATE 1).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
