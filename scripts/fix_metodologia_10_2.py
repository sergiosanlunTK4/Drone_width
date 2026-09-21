#!/usr/bin/env python3
"""Retira de `Metodología de cálculo.md` el bloque obsoleto del bug #6.

El bloque quedo duplicado al insertar la seccion 10.2: la version nueva esta arriba y la
antigua (que decia "CFD-0 bloqueado") seguia mas abajo. Se elimina la antigua conservando
una marca de trazabilidad, en lugar de borrarla sin dejar rastro.
"""
from pathlib import Path

P = Path("Metodología de cálculo.md")
lines = P.read_text(encoding="utf-8").splitlines(keepends=True)

# inicio: la linea que abre el bloque obsoleto (la SEGUNDA aparicion; la primera es la nueva)
marca = "**El bug CFD #6 es real:** OpenFOAM calcula el empuje Froude"
ini = None
for i, l in enumerate(lines):
    if l.startswith(marca):
        ini = i
        break
if ini is None:
    raise SystemExit("no se encontro el bloque obsoleto")

# fin: la linea con el aviso antiguo
fin = None
for j in range(ini, len(lines)):
    if "CFD-0 se mantiene ABIERTO hasta verificar la INTEGRAL DE LA FUENTE" in lines[j]:
        fin = j + 1
        break
if fin is None:
    raise SystemExit("no se encontro el final del bloque obsoleto")

retirado = "".join(lines[ini:fin])
nuevo = [
    "<!-- Bloque obsoleto retirado por scripts/fix_metodologia_10_2.py. Decia que CFD-0\n",
    "     estaba bloqueado por el bug #6. Sustituido por la seccion 10.2. -->\n",
]

lines[ini:fin] = nuevo
P.write_text("".join(lines), encoding="utf-8")

print(f"retiradas {fin - ini} lineas (de {ini + 1} a {fin})")
print(f"caracteres retirados: {len(retirado)}")
print("marca de trazabilidad insertada")
