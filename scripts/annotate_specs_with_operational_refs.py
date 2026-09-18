"""
Anade a cada ficha maestra (docs/specs/<UAV>.md) las REFERENCIAS OPERATIVAS de la
presentacion 03 de DJI Academy, marcadas como NO aplicables a estas plataformas.

Motivo: el material oficial solo publica tablas de parametros para T40/T50. Registrarlas
es util como referencia cualitativa, pero usarlas como entrada del DOE para T25P/T55/
T70P/T100 seria la extrapolacion entre plataformas que context.md SS30 prohibe.
La nota deja esa prohibicion por escrito en cada ficha.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

NOTA = """
### Referencias operativas oficiales — SOLO T40/T50 (NO aplicables a esta plataforma)

**Fuente:** `data/raw/dji_academy_03_parametros_aplicacion.txt` (DJI Academy, deck 03).

> ⛔ **PROHIBIDO usar estos valores como entradas del DOE para {UAV}.**
> El material oficial etiqueta estas tablas exclusivamente para **T40/T50**. Aplicarlas a
> {UAV} seria una extrapolacion entre plataformas, prohibida por `context.md` §30.
> Se registran unicamente como referencia cualitativa y como punto de partida de los
> rangos que deben medirse (GATE 1).

| Cultivo / uso | Tasa | Gota | Velocidad | Ancho | Altura sobre cultivo |
|---|---|---|---|---|---|
| Insecticidas, fungicidas, foliares | 15–30 L/ha | 150–300 µm | 6–10 m/s | 7,5–9 m | 3–4 m |
| Herbicidas y defoliantes | 20–30 L/ha | 400–500 µm | 5–6 m/s | 6–7 m | 3–3,5 m |
| Semillas | — | disco 800–1000 rpm | 6–10 m/s | 4,5–5 m | 3–4 m |
| Fertilizantes | — | disco 800–1000 rpm | 6–10 m/s | 6–7 m | 3–4 m |
| Madurantes | 15–30 L/ha | 200–350 µm | 6–10 m/s | 7–8 m | 3–4 m |

**Velocidades comparadas por DJI (todas a 140 µm):** 3 · 5 · 7 · 10 · **13 m/s**
→ el rango real de aplicación llega a 13 m/s, por encima del techo de 10 m/s asumido en
`data/processed/doe_master_plan.csv`.

**Practicas antideriva:** viento ≤ 2 m/s · V ≤ 6 m/s · gota gruesa o muy gruesa ·
zona de amortiguamiento 9–20 m. (El limite del aparato segun fichas es viento ≤ 6 m/s:
son dos cifras distintas y no deben confundirse.)

**Descomposicion oficial de objetivos** (util para las metricas derivadas, §21–§23):
- *Penetracion* mejora con menor V, menor altura y menor tamano de gota.
- *Cobertura* depende de la **combinacion ancho + velocidad + altura** (respaldo cualitativo de H2).
- *Eficiencia* mejora con mayor ancho, a costa de peor uniformidad (respaldo cualitativo de H7).
"""


def main() -> int:
    for uav in ["T25P", "T55", "T70P", "T100"]:
        p = ROOT / "docs" / "specs" / f"{uav}.md"
        if not p.exists():
            print(f"{uav}: ficha ausente")
            continue
        t = p.read_text(encoding="utf-8")
        if "Referencias operativas oficiales" in t:
            print(f"{uav}: ya tiene la seccion, no se duplica")
            continue
        p.write_text(t.rstrip() + "\n" + NOTA.replace("{UAV}", uav), encoding="utf-8")
        print(f"{uav}: referencias operativas anadidas -> {p.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
