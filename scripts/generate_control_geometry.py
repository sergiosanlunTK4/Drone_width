import os

def write_stl_ascii(filename, name, triangles):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w') as f:
        f.write(f"solid {name}\n")
        for tri in triangles:
            f.write("  facet normal 0 0 0\n    outer loop\n")
            for v in tri:
                f.write(f"      vertex {v[0]:.4f} {v[1]:.4f} {v[2]:.4f}\n")
            f.write("    endloop\n  endfacet\n")
        f.write(f"endsolid {name}\n")

def get_rotor_disk(x, y, z, r):
    # 8-sided disk
    tris = []
    v_center = (x, y, z)
    angles = np.linspace(0, 2*np.pi, 9)
    for i in range(8):
        v1 = (x + r*np.cos(angles[i]), y + r*np.sin(angles[i]), z)
        v2 = (x + r*np.cos(angles[i+1]), y + r*np.sin(angles[i+1]), z)
        tris.append((v_center, v1, v2))
    return tris

def get_box(x, y, z, dx, dy, dz):
    # Center box
    v = [
        (x-dx, y-dy, z-dz), (x+dx, y-dy, z-dz), (x+dx, y+dy, z-dz), (x-dx, y+dy, z-dz),
        (x-dx, y-dy, z+dz), (x+dx, y-dy, z+dz), (x+dx, y+dy, z+dz), (x-dx, y+dy, z+dz)
    ]
    return [
        (v[0], v[1], v[2]), (v[0], v[2], v[3]), # bottom
        (v[4], v[5], v[6]), (v[4], v[6], v[7]), # top
        (v[0], v[1], v[5]), (v[0], v[5], v[4]), # front
        (v[2], v[3], v[7]), (v[2], v[7], v[6]), # back
        (v[1], v[2], v[6]), (v[1], v[6], v[5]), # right
        (v[3], v[0], v[4]), (v[3], v[4], v[7])  # left
    ]

import numpy as np

# Full definitions
drones = {
    'T25P': {'wheel': 1.970/2, 'rotor_r': 0.5, 'atoms': [(0.5, 0.5, -0.2), (0.5, -0.5, -0.2)]},
    'T55':  {'wheel': 2.415/2, 'rotor_r': 0.6, 'atoms': [(0.6, 0.6, -0.2), (0.6, -0.6, -0.2)]},
    'T70P': {'wheel': 2.440/2, 'rotor_r': 0.6, 'atoms': [(0.7, 0.7, -0.3), (0.7, -0.7, -0.3)]},
    'T100': {'wheel': 2.330/2, 'rotor_r': 0.6, 'atoms': [(0.8, 0.8, -0.3), (0.8, -0.8, -0.3)]}
}

for name, cfg in drones.items():
    triangles = []
    # Body
    triangles.extend(get_box(0, 0, 0, 0.25, 0.25, 0.15))
    # Rotors (simplifying to 4 main rotor positions for AD/AL model control)
    w = cfg['wheel'] / np.sqrt(2)
    for rx, ry in [(w, w), (w, -w), (-w, w), (-w, -w)]:
        triangles.extend(get_rotor_disk(rx, ry, 0.1, cfg['rotor_r']))
    # Atomizers
    for ax, ay, az in cfg['atoms']:
        triangles.extend(get_box(ax, ay, az, 0.05, 0.05, 0.05))
    
    write_stl_ascii(f'geometry/models/{name}_control.stl', name, triangles)
    print(f"STL saved: {name}")
