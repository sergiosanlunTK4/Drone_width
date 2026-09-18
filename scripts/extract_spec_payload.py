"""
Extrae las tablas de especificaciones del payload JSON embebido en las capturas.

HALLAZGO QUE LO MOTIVA:
  las paginas de especificaciones son una app Next.js. El contenido NO esta en tablas
  HTML (0 encontradas) sino en un payload JSON embebido, con esta forma:

      {"title":"Sistema de propulsion - Helices",
       "specs":[{"key":"Material","value":"..."},
                {"key":"Dimensiones","value":"62 pulgadas"},
                {"key":"Cantidad","value":"8 pares"}]}

  Eso es MEJOR que una tabla HTML para nuestro proposito: da la fila COMPLETA con sus
  encabezados (key/value) y el texto literal, sin OCR ni parseo de maquetacion.

  Ademas: /es/ y /cn/ devuelven bytes identicos, asi que el chino original hay que
  buscarlo por otra via (ver informe). Este script deja constancia de eso.

REGLA: REPORTA. No interpreta "pares", no traduce, no toca manifiestos ni rotor_count.

Uso:
  python scripts/extract_spec_payload.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAP = ROOT / "data" / "raw" / "specs_captures"
OUT = CAP / "spec_tables.json"

# grupos que interesan al proyecto
GRUPOS_CLAVE = [
    "propulsi", "h[eé]lice", "motor", "aspersor", "boquilla", "pulveriz",
    "rociado", "bater", "tanque", "peso", "dimension", "ejes", "estructura",
]


def bloques_json(txt: str) -> list[dict]:
    """Localiza objetos con la forma {"title":..., "specs":[{"key":...,"value":...}]}."""
    out = []
    # captura equilibrada simple: desde {"title":" hasta el cierre del array specs
    for m in re.finditer(r'\{"title":"((?:[^"\\]|\\.)*)","specs":(\[.*?\])\}', txt):
        titulo = m.group(1)
        try:
            specs = json.loads(m.group(2))
        except json.JSONDecodeError:
            continue
        if isinstance(specs, list) and specs and "key" in specs[0]:
            out.append({"title": titulo, "specs": specs})
    # deduplicar conservando orden
    vistos, unicos = set(), []
    for b in out:
        firma = b["title"] + json.dumps(b["specs"], sort_keys=True)
        if firma not in vistos:
            vistos.add(firma)
            unicos.append(b)
    return unicos


def main() -> int:
    resultado = {}
    for f in sorted(CAP.glob("*.html")):
        uav = f.name.split("_")[0]
        loc = f.name.split("_")[1]
        txt = f.read_text(encoding="utf-8", errors="replace")
        bloques = bloques_json(txt)
        resultado.setdefault(uav, {})[loc] = bloques

    # informe legible y foco en los grupos clave
    lineas = ["# Tablas de especificaciones extraidas del payload embebido", ""]
    for uav, por_loc in resultado.items():
        ref = por_loc.get("es") or next(iter(por_loc.values()))
        lineas.append(f"\n## {uav.upper()} — {len(ref)} grupos de especificaciones\n")
        for b in ref:
            titulo = b["title"]
            lineas.append(f"### {titulo}")
            lineas.append("")
            lineas.append("| clave | valor |")
            lineas.append("|---|---|")
            for s in b["specs"]:
                lineas.append(f"| {s.get('key','')} | {s.get('value','')} |")
            lineas.append("")
        # foco helices / propulsion
        interesa = [b for b in ref
                    if re.search("|".join(GRUPOS_CLAVE), b["title"], re.I)]
        lineas.append(f"**Grupos relevantes al proyecto: {len(interesa)}/{len(ref)}**\n")

    OUT.write_text("\n".join(lineas), encoding="utf-8")
    (CAP / "spec_tables_raw.json").write_text(
        json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8")

    # resumen por consola: la fila de helices de cada plataforma
    print("=== FILA DE HELICES / PROPULSION POR PLATAFORMA ===")
    for uav, por_loc in sorted(resultado.items()):
        ref = por_loc.get("es") or next(iter(por_loc.values()))
        print(f"\n{uav.upper()}  ({len(ref)} grupos)")
        for b in ref:
            if re.search(r"h[eé]lice|propulsi", b["title"], re.I):
                for s in b["specs"]:
                    print(f"   {b['title']} :: {s.get('key')} = {s.get('value')}")

    # verificar identidad de locales (hallazgo forense importante)
    print("\n=== IDENTIDAD ENTRE LOCALES ===")
    for uav, por_loc in sorted(resultado.items()):
        if "es" in por_loc and "zh" in por_loc:
            igual = json.dumps(por_loc["es"], sort_keys=True) == json.dumps(por_loc["zh"], sort_keys=True)
            print(f"  {uav.upper()}: payload es == zh ? {igual}")
    print("\n-> si es True, la via HTTP no entrega el texto chino original.")
    print("\nREGLA: esto es evidencia documental. No se modifica ningun manifiesto.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
