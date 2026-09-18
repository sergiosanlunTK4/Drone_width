"""
Muestra las filas capturadas de una plataforma (desde el payload estructurado).

Uso:
  python scripts/show_spec_rows.py --uav T70P
  python scripts/show_spec_rows.py --uav T70P --grep "dimensi|peso|ejes"
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "raw" / "specs_captures" / "spec_tables_raw.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--uav", default=None, choices=["T100", "T55", "T70P"])
    ap.add_argument("--grep", default=None)
    ap.add_argument("--list", action="store_true", help="solo listar los titulos de grupo")
    a = ap.parse_args()

    data = json.loads(SRC.read_text(encoding="utf-8"))

    if a.list or not a.uav:
        for u, v in data.items():
            grupos = v.get("es", [])
            print(f"\n=== {u.upper()} — {len(grupos)} grupos ===")
            for i, b in enumerate(grupos, 1):
                print(f"  {i:2d}. {b['title']}")
        return 0

    # las claves de primer nivel son minusculas (t100, t55, t70p)
    grupos = (data.get(a.uav) or data.get(a.uav.lower()) or {}).get("es")
    if not grupos:
        print(f"no hay grupos para {a.uav}; ejecuta scripts/extract_spec_payload.py")
        return 2

    rx = re.compile(a.grep, re.I) if a.grep else None
    print(f"=== {a.uav} — {len(grupos)} grupos capturados ===\n")
    for b in grupos:
        if rx and not rx.search(b["title"]):
            continue
        print(f"## {b['title']}")
        for s in b["specs"]:
            print(f"   {s.get('key',''):38s} | {s.get('value','')}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
