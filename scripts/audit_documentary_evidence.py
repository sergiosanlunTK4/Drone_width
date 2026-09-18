"""
Auditor documental de los textos y catalogos extraidos de los decks DJI Academy.

OBJETIVO DEL ENCARGO:
  1. buscar evidencia del T55 (rotor_count, blades_per_rotor, geometria);
  2. aportar evidencia para A9 (conflicto 8 vs 16 rotores del T100) y A10
     (accionamiento del par coaxial: solidario o independiente).

CRITERIOS EXPLICITOS:
  - Identidad: se busca el modelo por varios alias, no solo "T55", para no perder
    menciones por nomenclatura.
  - Temas: motor, rotor, helice/propeller/pala, coaxial, ESC, 6223, wheelbase/ejes,
    dimensiones, atomizador/boquilla, y el literal "pares" (origen de "8 pares").
  - Cada coincidencia se reporta con archivo y numero de linea: es verificable.
  - Se marca el TIPO de coincidencia para no confundir:
      IDENTIDAD  = aparece el modelo o su alias
      TEMA       = aparece un termino tecnico (puede no referirse al modelo)
      AMBOS      = identidad y tema en la misma linea  <- el hallazgo util
  - NO se concluye automaticamente ante una coincidencia. El script REPORTA;
    la interpretacion se registra a mano en el research log (regla del encargo).

Uso:
  python scripts/audit_documentary_evidence.py
  python scripts/audit_documentary_evidence.py --uav T55
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

# Alias por plataforma. Se evitan coincidencias espurias exigiendo limite de palabra.
ALIAS = {
    "T25P": [r"T25P", r"T25\s*P", r"\bT25\b"],
    "T55":  [r"T55", r"\bT55\b", r"Agras\s*55", r"\b55\b(?=\s*(?:kg|L|litros|pulgadas|in\b))"],
    "T70P": [r"T70P", r"T70\s*P", r"\bT70\b"],
    "T100": [r"T100", r"T\s*100"],
}
TEMAS = {
    "motor":        r"\bmotor(?:es)?\b",
    "rotor":        r"\brotor(?:es)?\b",
    "helice":       r"h[eé]lice|propeller|pala(?:s)?\b",
    "coaxial":      r"coaxial(?:es)?",
    "ESC":          r"\bESC\b|control electr[oó]nico de velocidad",
    "helice_6223":  r"\b6223\b",
    "ejes":         r"distancia (?:diagonal )?entre ejes|wheelbase|distancia m[aá]xima entre ejes",
    "dimensiones":  r"dimensiones|desplegad|plegad",
    "atomizador":   r"atomizador|boquilla|nebulizador|rociador",
    "pares":        r"\bpares?\b|\bpar de h[eé]lices\b",
    "empuje":       r"empuje",
    "rpm":          r"\bRPM\b|revoluciones",
    "brazo":        r"\bbrazo(?:s)?\b",
}
# El deck 01 ya fue auditado; se incluye igualmente para tener una vista unica.
DECKS_EXCLUIDOS = set()


def archivos() -> list[Path]:
    files = sorted(RAW.glob("dji_academy_*.txt"))
    return [f for f in files if f.name not in DECKS_EXCLUIDOS]


def lineas_de_interes(path: Path, alias: list[str], temas: dict[str, str]) -> dict:
    rx_alias = re.compile("|".join(alias), re.IGNORECASE)
    rx_tema = {k: re.compile(v, re.IGNORECASE) for k, v in temas.items()}
    out = {"identidad": [], "ambos": [], "temas": {k: [] for k in temas}}
    for i, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        tiene_alias = bool(rx_alias.search(line))
        temas_aqui = [k for k, rx in rx_tema.items() if rx.search(line)]
        if tiene_alias and temas_aqui:
            out["ambos"].append((i, temas_aqui, line.strip()))
        elif tiene_alias:
            out["identidad"].append((i, line.strip()))
        for k in temas_aqui:
            out["temas"][k].append((i, line.strip()))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--uav", default=None, choices=list(ALIAS))
    ap.add_argument("--max-linea", type=int, default=210)
    a = ap.parse_args()

    objetivos = [a.uav] if a.uav else list(ALIAS)
    files = archivos()
    print(f"deck(s) analizados: {len(files)}")
    for f in files:
        print(f"  - {f.name}  ({len(f.read_text(encoding='utf-8', errors='ignore').splitlines())} lineas)")

    for uav in objetivos:
        print("\n" + "=" * 92)
        print(f"PLATAFORMA {uav} — alias: {', '.join(ALIAS[uav])}")
        print("=" * 92)
        total_ambos = 0
        for f in files:
            r = lineas_de_interes(f, ALIAS[uav], TEMAS)
            if r["ambos"]:
                print(f"\n  ### {f.name}  — {len(r['ambos'])} lineas con IDENTIDAD + TEMA")
                for i, temas, line in r["ambos"][:14]:
                    print(f"    L{i:<5d} [{'/'.join(temas)}]  {line[:a.max_linea]}")
                total_ambos += len(r["ambos"])
            if not a.uav and r["identidad"]:
                # solo identidad: menciones sueltas, utiles para localizar secciones
                print(f"  · {f.name}: {len(r['identidad'])} menciones sin termino tecnico")
        print(f"\n  -> lineas con identidad+tema: {total_ambos}")

    # Vista por tema: donde se habla de cada asunto, en todos los decks
    if not a.uav:
        print("\n" + "=" * 92)
        print("VISTA POR TEMA (todos los decks) — senala donde buscar A9/A10")
        print("=" * 92)
        for tema in TEMAS:
            hits = []
            for f in files:
                r = lineas_de_interes(f, ALIAS["T100"], TEMAS)
                hits.extend((f.name, i, line) for i, line in r["temas"][tema])
            if not hits:
                print(f"\n  [{tema}] sin coincidencias")
                continue
            print(f"\n  [{tema}] {len(hits)} coincidencias; primeras 4:")
            for name, i, line in hits[:4]:
                print(f"    {name[:34]:36s} L{i:<5d} {line[:160]}")

    print("\n" + "-" * 92)
    print("REGLA DEL ENCARGO: este script REPORTA, no concluye. Ninguna coincidencia se")
    print("convierte en hecho ni modifica un manifiesto de forma automatica. La interpretacion")
    print("se registra a mano en research_log.md con fuente, slide y conflicto si lo hubiera.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
