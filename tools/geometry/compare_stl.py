#!/usr/bin/env python3
"""
compare_stl.py : Tabla comparativa entre STL original y reparado.

Uso:
    python compare_stl.py <original.stl> <reparado.stl>

Métricas: triángulos, vértices, componentes, bordes abiertos,
bordes non-manifold, bounding box X/Y/Z, área superficial,
volumen con signo (si componente cerrado), normales consistentes.
"""
import sys
import numpy as np
from stl import mesh as npmesh
from collections import defaultdict


def edge_key(a, b):
    return (int(a), int(b)) if a < b else (int(b), int(a))


def metrics(path):
    m = npmesh.Mesh.from_file(path)
    v = m.vectors.reshape(-1, 3)
    ntri = len(m.vectors)
    tol = 1e-9
    q = np.round(v / tol).astype(np.int64)
    _, idx = np.unique(q, axis=0, return_inverse=True)
    idx = idx.reshape(ntri, 3)

    a = m.vectors[:, 0] - m.vectors[:, 1]
    b = m.vectors[:, 0] - m.vectors[:, 2]
    area = 0.5 * np.linalg.norm(np.cross(a, b), axis=1)
    area_total = float(area.sum())

    face_of_edge = defaultdict(list)
    for t in range(ntri):
        for k in range(3):
            face_of_edge[edge_key(idx[t, k], idx[t, (k + 1) % 3])].append(t)
    n_open = sum(1 for f in face_of_edge.values() if len(f) == 1)
    n_nm = sum(1 for f in face_of_edge.values() if len(f) > 2)

    adj = defaultdict(set)
    for e, tris in face_of_edge.items():
        for i in range(len(tris)):
            for j in range(i + 1, len(tris)):
                adj[tris[i]].add(tris[j])
                adj[tris[j]].add(tris[i])
    seen = set()
    comps = 0
    for t in range(ntri):
        if t in seen:
            continue
        comps += 1
        stack = [t]
        while stack:
            c = stack.pop()
            if c in seen:
                continue
            seen.add(c)
            stack.extend(adj[c] - seen)

    vol = 0.0
    for t in range(ntri):
        p = m.vectors[t]
        vol += np.dot(p[0], np.cross(p[1], p[2]))
    vol /= 6.0

    degen = int(np.sum(area < 1e-14))
    fs = np.sort(idx, axis=1)
    _, counts = np.unique(fs.view([('', idx.dtype)] * 3).reshape(-1), return_counts=True)
    ndup = int((counts > 1).sum())

    return {
        'triángulos': ntri,
        'vértices': int(v.shape[0]),
        'componentes': comps,
        'bordes abiertos': n_open,
        'non-manifold': n_nm,
        'bbox X': f"{v[:, 0].min():.4f}..{v[:, 0].max():.4f}",
        'bbox Y': f"{v[:, 1].min():.4f}..{v[:, 1].max():.4f}",
        'bbox Z': f"{v[:, 2].min():.4f}..{v[:, 2].max():.4f}",
        'área [m²]': f"{area_total:.6f}",
        'volumen algebr. [m³]': f"{vol:.6f}",
        'degenerados': degen,
        'caras duplicadas': ndup,
    }


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit("Uso: python compare_stl.py <original.stl> <reparado.stl>")
    orig = metrics(sys.argv[1])
    clean = metrics(sys.argv[2])
    print(f"{'Métrica':<22} {'Original':<18} {'Reparado':<18} {'Δ (repara-op)'}")
    print("-" * 78)
    for k in orig:
        print(f"{k:<22} {str(orig[k]):<18} {str(clean[k]):<18}")