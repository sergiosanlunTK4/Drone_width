#!/usr/bin/env python3
"""
analyze_stl.py : Auditoría topológica y geométrica de un STL.

Uso:
    python analyze_stl.py <file.stl>

Reporta por componente conectado:
    - tamaño (ntri), bbox z, área superficial, centroide
    - cerrado? (todo borde con exactamente 2 caras)
    - n bordes abiertos / non-manifold (>2 caras)
Además: triángulos degenerados, caras duplicadas, vértices coincidentes.

Dependencias: numpy, numpy-stl. No modifica ningún archivo.
"""
import sys
import numpy as np
from stl import mesh as npmesh
from collections import defaultdict


def edge_key(a, b):
    return (int(a), int(b)) if a < b else (int(b), int(a))


def analyze(path):
    m = npmesh.Mesh.from_file(path)
    v = m.vectors.reshape(-1, 3)                 # (3*n, 3)
    ntri = len(m.vectors)

    # índices de vértices fusionando coincidentes dentro de tolerancia pequeña
    tol = 1e-9
    q = np.round(v / tol).astype(np.int64)
    _, idx = np.unique(q, axis=0, return_inverse=True)
    idx = idx.reshape(ntri, 3)
    nvert = int(idx.max()) + 1

    # área y normales por triángulo
    a = m.vectors[:, 0] - m.vectors[:, 1]
    b = m.vectors[:, 0] - m.vectors[:, 2]
    cross = np.cross(a, b)
    area = 0.5 * np.linalg.norm(cross, axis=1)
    area_total = float(area.sum())
    degen = np.where(area < 1e-14)[0]

    # caras duplicadas
    fs = np.sort(idx, axis=1)
    _, counts = np.unique(fs.view([('', idx.dtype)] * 3).reshape(-1), return_counts=True)
    ndup = int((counts > 1).sum())

    # gráfos
    face_of_edge = defaultdict(list)   # edge -> triángulos
    for t in range(ntri):
        for k in range(3):
            e = edge_key(idx[t, k], idx[t, (k + 1) % 3])
            face_of_edge[e].append(t)

    open_edges = [e for e, f in face_of_edge.items() if len(f) == 1]
    nonmanifold = [e for e, f in face_of_edge.items() if len(f) > 2]

    # adyacencia entre caras
    adj = defaultdict(set)
    for e, tris in face_of_edge.items():
        for i in range(len(tris)):
            for j in range(i + 1, len(tris)):
                adj[tris[i]].add(tris[j])
                adj[tris[j]].add(tris[i])

    # componentes conectados
    seen = set()
    comps = []
    for t in range(ntri):
        if t in seen:
            continue
        stack, comp = [t], []
        while stack:
            c = stack.pop()
            if c in seen:
                continue
            seen.add(c)
            comp.append(c)
            stack.extend(adj[c] - seen)
        comps.append(comp)

    # volumen con signo global (si todo estuviera cerrado y orientado)
    # signo por componente con orientación corregida no se puede saber aquí sin reparar;
    # reportamos volumen algebraico según winding actual.
    vol = 0.0
    for t in range(ntri):
        p = m.vectors[t]
        vol += np.dot(p[0], np.cross(p[1], p[2]))
    vol = vol / 6.0

    print(f"Archivo        : {path}")
    print(f"Triángulos     : {ntri}")
    print(f"Vértices crudos: {len(v)}")
    print(f"Vértices únicos(tol={tol:g}): {nvert}")
    print(f"Bounding box   : {v.min(axis=0)} .. {v.max(axis=0)}")
    print(f"Área total     : {area_total:.6f} m^2")
    print(f"Volumen algebr.(winding actual): {vol:.6f} m^3")
    print(f"Triángulos degenerados: {len(degen)}")
    print(f"Caras duplicadas     : {ndup}")
    print(f"Bordes abiertos      : {len(open_edges)}")
    print(f"Bordes non-manifold  : {len(nonmanifold)}")
    print(f"Componentes conectados: {len(comps)}")
    print()
    print(f"{'comp':>4} {'n_tri':>6} {'cerrado':>8} {'area[m2]':>10} "
          f"{'centro(x,y,z)':>22} {'bbox z':>14} {'bordes_sueltos':>14}")
    for ci, comp in enumerate(comps):
        sub_edges = set()
        for t in comp:
            for k in range(3):
                sub_edges.add(edge_key(idx[t, k], idx[t, (k + 1) % 3]))
        n_open = sum(1 for e in sub_edges if len(face_of_edge.get(e, [])) == 1)
        n_nm = sum(1 for e in sub_edges if len(face_of_edge.get(e, [])) > 2)
        cat = m.vectors[comp].reshape(-1, 3)
        cmin = cat.min(axis=0)
        cmax = cat.max(axis=0)
        ctr = cat.mean(axis=0)
        acomp = float(area[comp].sum())
        closed = (n_open == 0 and n_nm == 0)
        print(f"{ci:>4} {len(comp):>6} {str(closed):>8} {acomp:>10.6f} "
              f"{('%.3f %.3f %.3f' % tuple(ctr)):>22} "
              f"{('[%.3f..%.3f]' % (cmin[2], cmax[2])):>14} {n_open:>14}")


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit("Uso: python analyze_stl.py <file.stl>")
    analyze(sys.argv[1])