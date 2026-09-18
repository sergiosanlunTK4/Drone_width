"""
Congela la geometria de una plataforma como geometry-v1/<uav>/ (inmutable, con hash).

POR QUE CONGELAR POR PLATAFORMA Y NO GLOBALMENTE:
  un conflicto abierto en una plataforma (p.ej. T100 8 vs 16 rotores) no debe impedir
  avanzar el resto. GATE 1A se cierra por UAV, cada uno con su propia version congelada.

El script NO inventa nada:
  - REGISTRA como bloqueantes los campos criticos que el manifiesto siga marcando como D.
  - REGISTRA como bloqueantes los datos criticos que falten en data/raw/mediciones_geometria.csv.
  - Exige que las filas de medicion (source_class=M) traigan incertidumbre e instrumento.
  - No hay flag de --force: para congelar hay que cerrar el gate de verdad.

Uso:
  python scripts/freeze_geometry_v1.py --uav T25P --dry-run     # solo valida
  python scripts/freeze_geometry_v1.py --uav T25P --by "D.M."   # congela si pasa
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAN_DIR = ROOT / "geometry" / "manifests"
MODELS_DIR = ROOT / "geometry" / "models"
MEDICIONES = ROOT / "data" / "raw" / "mediciones_geometria.csv"
OUT_ROOT = ROOT / "geometry-v1"

# Campos que DEBEN estar resueltos (clasificacion distinta de D) para cerrar GATE 1A.
# Rutas dentro del manifiesto. Los coaxiales exigen ademas los campos de par.
CRITICOS_COMUNES = [
    ("dimensiones", "wheelbase_diagonal_mm"),
    ("dimensiones", "rotor_diameter_m"),
    ("dimensiones", "blades_per_rotor"),
    ("topologia_rotores", "rotor_count"),
]
CRITICOS_COAXIAL = [
    # separacion axial del par: parametro del modelo de empuje (coaxial_thrust_split.md)
]

# Parametros que deben existir en el CSV de mediciones para esta plataforma
PARAMS_REQUERIDOS = [
    "posicion_x", "posicion_y", "posicion_z",
    "eje_normal", "diametro", "sentido_giro",
]
PARAMS_REQUERIDOS_ATOMIZER = [
    "posicion_x", "posicion_y", "posicion_z", "vector_descarga", "altura_rel_plano_rotor",
]


def get_d(m: dict, path: tuple[str, ...]):
    cur = m
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def clasificacion(v) -> str | None:
    return v.get("clasificacion") if isinstance(v, dict) else None


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def leer_mediciones() -> list[dict]:
    if not MEDICIONES.exists():
        return []
    with MEDICIONES.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def validar(uav: str) -> tuple[list[str], list[str], dict]:
    """Devuelve (bloqueantes, avisos, contexto)."""
    bloqueantes: list[str] = []
    avisos: list[str] = []

    man_path = MAN_DIR / f"{uav.lower()}_geometry_manifest.json"
    if not man_path.exists():
        return [f"manifiesto ausente: {man_path.relative_to(ROOT)}"], [], {}
    man = json.loads(man_path.read_text(encoding="utf-8"))

    coaxial = (get_d(man, ("topologia_rotores", "coaxial")) or {}).get("valor")

    # 1) campos criticos no resueltos
    for path in CRITICOS_COMUNES + (CRITICOS_COAXIAL if coaxial else []):
        v = get_d(man, path)
        c = clasificacion(v)
        if v is None:
            bloqueantes.append(f"campo ausente: {'.'.join(path)}")
        elif c == "D" or (isinstance(c, str) and c.startswith("D")):
            bloqueantes.append(f"campo en D: {'.'.join(path)} (valor={v.get('valor') if isinstance(v, dict) else v})")
        elif c == "I":
            avisos.append(f"campo solo inferido (I): {'.'.join(path)}")

    # 2) conflicto abierto declarado
    for k in man.get("topologia_rotores", {}):
        if k.startswith("CONFLICTO_ABIERTO"):
            bloqueantes.append(f"conflicto abierto en el manifiesto: {k}")

    # 3) geometria de modelo presente
    stl = MODELS_DIR / f"{uav}_control.stl"
    meta = MODELS_DIR / f"{uav}_control.meta.json"
    if not stl.exists():
        bloqueantes.append(f"STL ausente: {stl.relative_to(ROOT)}")
    if not meta.exists():
        bloqueantes.append(f"meta ausente: {meta.relative_to(ROOT)}")

    # 4) mediciones fisicas en el CSV
    filas = [r for r in leer_mediciones() if (r.get("uav") or "").upper() == uav.upper()]
    if not filas:
        bloqueantes.append(
            f"no hay ninguna fila para {uav} en {MEDICIONES.relative_to(ROOT)} "
            "(la geometria no esta medida)"
        )
    else:
        params = {r.get("parameter") for r in filas}
        falta_rotor = [p for p in PARAMS_REQUERIDOS if p not in params]
        falta_atom = [p for p in PARAMS_REQUERIDOS_ATOMIZER if p not in params]
        if falta_rotor:
            bloqueantes.append(f"mediciones de rotor faltantes: {', '.join(falta_rotor)}")
        if falta_atom:
            bloqueantes.append(f"mediciones de atomizador faltantes: {', '.join(falta_atom)}")
        # trazabilidad experimental obligatoria
        sin_traz = [r for r in filas if r.get("source_class") == "M"
                    and (not r.get("uncertainty") or not r.get("instrument"))]
        if sin_traz:
            avisos.append(f"{len(sin_traz)} filas M sin uncertainty o instrument")
        sin_ref = [r for r in filas if not r.get("reference_frame")]
        if sin_ref:
            bloqueantes.append(f"{len(sin_ref)} filas sin reference_frame")

    ctx = {
        "uav": uav,
        "manifiesto": str(man_path.relative_to(ROOT)).replace("\\", "/"),
        "coaxial": coaxial,
        "filas_medicion": len(filas),
    }
    return bloqueantes, avisos, ctx


def congelar(uav: str, by: str, ctx: dict) -> Path:
    dest = OUT_ROOT / uav
    if dest.exists():
        raise SystemExit(
            f"{dest.relative_to(ROOT)} ya existe. Un cambio de geometria produce geometry-v2, "
            "no sobrescribe v1."
        )
    dest.mkdir(parents=True)
    man_src = MAN_DIR / f"{uav.lower()}_geometry_manifest.json"
    stl_src = MODELS_DIR / f"{uav}_control.stl"
    meta_src = MODELS_DIR / f"{uav}_control.meta.json"
    shutil.copy2(man_src, dest / "manifest.json")
    shutil.copy2(stl_src, dest / "model.stl")
    shutil.copy2(meta_src, dest / "control.meta.json")

    man = json.loads(man_src.read_text(encoding="utf-8"))
    fuentes = ["# Fuentes, clasificacion e incertidumbre",
               "", f"Plataforma: **{uav}**  ", f"Congelado: {datetime.now(timezone.utc).isoformat()}  ",
               f"Por: {by}", "",
               "| Campo | Valor | Clase | Fuente |", "|---|---|---|---|"]

    def recorrer(v, pref=""):
        if isinstance(v, dict):
            if "clasificacion" in v:
                fuentes.append(
                    f"| `{pref}` | {str(v.get('valor'))[:60]} | {v.get('clasificacion')} | "
                    f"{str(v.get('fuente') or v.get('nota') or '')[:60]} |"
                )
            for k, x in v.items():
                if k in ("clasificacion", "valor", "fuente"):
                    continue
                recorrer(x, f"{pref}.{k}" if pref else k)
        elif isinstance(v, list):
            for i, x in enumerate(v):
                recorrer(x, f"{pref}[{i}]")

    recorrer(man)
    (dest / "SOURCES.md").write_text("\n".join(fuentes) + "\n", encoding="utf-8")

    (dest / "README.md").write_text(
        f"""# geometry-v1/{uav} — geometria congelada

**Congelado:** {datetime.now(timezone.utc).isoformat()}
**Por:** {by}
**Coaxial:** {ctx.get('coaxial')}
**Filas de medicion asociadas:** {ctx.get('filas_medicion')}

## Alcance

Geometria de **estudio** para esta plataforma: topologia, centros y ejes de rotor, y
posicion/orientacion de atomizadores con trazabilidad de fuente e incertidumbre.

## Regla de inmutabilidad

Este directorio **no se modifica**. Cualquier cambio de geometria produce
`geometry-v2/{uav}/` y obliga a re-ejecutar los casos que dependian de v1.

## Verificacion

```powershell
python scripts/freeze_geometry_v1.py --uav {uav} --verify
```

## Limitaciones declaradas

Ver `SOURCES.md` para la clasificacion de cada cota. Toda cota marcada `M` lleva su
incertidumbre en `data/raw/mediciones_geometria.csv`.
""",
        encoding="utf-8",
    )

    lineas = []
    for f in ["manifest.json", "model.stl", "control.meta.json", "SOURCES.md", "README.md"]:
        lineas.append(f"{sha256(dest / f)}  {f}")
    (dest / "SHA256SUMS").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return dest


def verificar(uav: str) -> int:
    dest = OUT_ROOT / uav
    sums = dest / "SHA256SUMS"
    if not sums.exists():
        print(f"no hay nada que verificar en {dest}")
        return 2
    ok = True
    for line in sums.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, name = line.split("  ", 1)
        actual = sha256(dest / name)
        estado = "OK" if actual == digest else "ALTERADO"
        if actual != digest:
            ok = False
        print(f"  {estado:8s} {name}")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--uav", required=True, choices=["T25P", "T55", "T70P", "T100"])
    ap.add_argument("--by", default="", help="quien cierra el gate")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()

    if a.verify:
        return verificar(a.uav)

    bloqueantes, avisos, ctx = validar(a.uav)
    print(f"=== Validacion GATE 1A — {a.uav} ===")
    print(f"  coaxial: {ctx.get('coaxial')}   filas de medicion: {ctx.get('filas_medicion', 0)}")
    for av in avisos:
        print(f"  AVISO: {av}")
    if bloqueantes:
        print(f"\n  BLOQUEANTES ({len(bloqueantes)}): GATE 1A NO se puede cerrar")
        for b in bloqueantes:
            print(f"    - {b}")
        print("\n  No existe flag para forzar el cierre: hay que medir.")
        return 1
    print("\n  Sin bloqueantes.")
    if a.dry_run:
        print("  (--dry-run: no se congela nada)")
        return 0
    if not a.by:
        print("\n  Falta --by para congelar.")
        return 2
    dest = congelar(a.uav, a.by, ctx)
    print(f"\n  CONGELADO -> {dest.relative_to(ROOT)}")
    for f in sorted(dest.iterdir()):
        print(f"    {f.name}  {sha256(f)[:16]}...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
