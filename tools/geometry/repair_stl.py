#!/usr/bin/env python3

import sys
from pathlib import Path
from collections import defaultdict, deque

import numpy as np
from stl import mesh as npmesh


def edge_key(a, b):
    a = int(a)
    b = int(b)
    return (a, b) if a < b else (b, a)


def build_topology(vectors, tol=1e-9):
    flat = vectors.reshape(-1, 3)

    q = np.round(flat / tol).astype(np.int64)

    _, first_idx, inverse = np.unique(
        q,
        axis=0,
        return_index=True,
        return_inverse=True
    )

    vertices = flat[first_idx]
    faces = inverse.reshape(-1, 3)

    return vertices, faces


def build_edge_map(faces):
    edge_map = defaultdict(list)

    for fi, face in enumerate(faces):
        for i in range(3):
            a = int(face[i])
            b = int(face[(i + 1) % 3])

            edge_map[edge_key(a, b)].append(
                (fi, a, b)
            )

    return edge_map


def find_components(faces, edge_map):
    adjacency = defaultdict(set)

    for owners in edge_map.values():
        ids = [x[0] for x in owners]

        if len(ids) >= 2:
            for i in range(len(ids)):
                for j in range(i + 1, len(ids)):
                    a = ids[i]
                    b = ids[j]

                    adjacency[a].add(b)
                    adjacency[b].add(a)

    components = []
    visited = set()

    for start in range(len(faces)):
        if start in visited:
            continue

        q = deque([start])
        visited.add(start)
        component = []

        while q:
            current = q.popleft()
            component.append(current)

            for nb in adjacency[current]:
                if nb not in visited:
                    visited.add(nb)
                    q.append(nb)

        components.append(sorted(component))

    return components


def component_closed(component, faces):
    local_edges = defaultdict(int)

    for fi in component:
        f = faces[fi]

        for i in range(3):
            local_edges[
                edge_key(f[i], f[(i + 1) % 3])
            ] += 1

    return all(count == 2 for count in local_edges.values())


def orientation_constraints(faces, component):
    local_edges = defaultdict(list)

    for fi in component:
        f = faces[fi]

        for i in range(3):
            a = int(f[i])
            b = int(f[(i + 1) % 3])

            local_edges[
                edge_key(a, b)
            ].append((fi, a, b))

    constraints = defaultdict(list)

    for owners in local_edges.values():
        if len(owners) != 2:
            continue

        f1, a1, b1 = owners[0]
        f2, a2, b2 = owners[1]

        same_direction = (
            a1 == a2 and
            b1 == b2
        )

        parity = 1 if same_direction else 0

        constraints[f1].append(
            (f2, parity)
        )
        constraints[f2].append(
            (f1, parity)
        )

    return constraints


def orient_component(faces, component):
    constraints = orientation_constraints(
        faces,
        component
    )

    state = {
        component[0]: 0
    }

    q = deque([component[0]])

    while q:
        current = q.popleft()

        for nb, parity in constraints[current]:
            required = state[current] ^ parity

            if nb not in state:
                state[nb] = required
                q.append(nb)

            elif state[nb] != required:
                raise RuntimeError(
                    f"Conflicto de orientación "
                    f"entre caras {current} y {nb}"
                )

    if len(state) != len(component):
        raise RuntimeError(
            "No se pudo orientar todo el componente"
        )

    result = faces.copy()

    for fi in component:
        if state[fi] == 1:
            result[fi, [1, 2]] = (
                result[fi, [2, 1]]
            )

    return result


def signed_volume(vertices, subset):
    tri = vertices[subset]

    terms = np.einsum(
        "ij,ij->i",
        tri[:, 0],
        np.cross(
            tri[:, 1],
            tri[:, 2]
        )
    )

    return terms.sum() / 6.0


def main(input_path, output_path):
    m = npmesh.Mesh.from_file(input_path)

    vertices, faces = build_topology(
        m.vectors
    )

    edge_map = build_edge_map(faces)

    components = find_components(
        faces,
        edge_map
    )

    working = faces.copy()

    closed_components = []

    print(
        "Componentes encontrados:",
        len(components)
    )
    print()

    for ci, component in enumerate(components):

        closed = component_closed(
            component,
            working
        )

        print(
            f"Componente {ci}: "
            f"{len(component)} caras, "
            f"cerrado={closed}"
        )

        if not closed:
            print(
                "  OMITIDO del STL sólido"
            )
            continue

        working = orient_component(
            working,
            component
        )

        volume = signed_volume(
            vertices,
            working[component]
        )

        if volume < 0:
            for fi in component:
                working[fi, [1, 2]] = (
                    working[fi, [2, 1]]
                )

            volume = signed_volume(
                vertices,
                working[component]
            )

        print(
            f"  volumen final = "
            f"{volume:.9f} m3"
        )

        closed_components.extend(component)

    closed_components = sorted(
        closed_components
    )

    output_vectors = vertices[
        working[closed_components]
    ]

    out = npmesh.Mesh(
        np.zeros(
            len(output_vectors),
            dtype=npmesh.Mesh.dtype
        )
    )

    out.vectors[:] = output_vectors

    out.save(output_path)

    print()
    print(
        "Triángulos originales:",
        len(faces)
    )
    print(
        "Triángulos STL sólido:",
        len(output_vectors)
    )

    print()
    print(
        "Archivo escrito:"
    )
    print(
        Path(output_path).resolve()
    )


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(
            "Uso:\n"
            "python repair_stl.py "
            "entrada.stl salida.stl"
        )

    main(
        sys.argv[1],
        sys.argv[2]
    )