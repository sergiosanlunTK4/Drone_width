"""
Anade a cada ficha maestra (docs/specs/<UAV>.md) una seccion de FUENTES P-A (DJI Academy).

No modifica las tablas existentes: la ficha sigue siendo la lectura de la fuente oficial (P).
La seccion nueva deja constancia de los valores P-A y de las discrepancias a resolver,
para que la integracion se haga de forma consciente y no silenciosa.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

NOTA = """

---

## FUENTES P-A (DJI Academy) — datos NO integrados aun en esta ficha

**Archivo:** `data/raw/dji_academy_01_conocimiento_basico.txt` (extraido de la presentacion
`01 Conocimiento basico de un Dron (1).pptx`, material DJI Academy, 2026-01-15).
**Registro completo:** `data/raw/dji_academy_01_FUENTE.md`. **Auditoria:** `research_log.md` Entry 007.

> Las tablas de arriba **no se han modificado**: siguen siendo la lectura de la ficha oficial
> de DJI (clasificacion P). Los valores de abajo provienen de la fuente P-A y deben integrarse
> a las tablas en la proxima revision de esta ficha, resolviendo antes las discrepancias.

| Parametro | Valor (P-A) | Accion |
|---|---|---|
| Helice — modelo y medida | 6223 = 62 x 23 in (1,574 m de diametro) | integrar; resuelve parcialmente "paso/twist = D" |
| Motor — modelo | 155P | integrar |
| Rotacion de helices | {ROT} | integrar; critico para el signo de la estela |
| Configuracion propulsiva | {COAX} | integrar; relevante para H4 |
| Velocidad de ascenso / descenso | 3 m/s / 2-3 m/s | integrar |
| Velocidad maxima de traslado | 20 m/s | integrar; el DOE solo llegaba a 10 m/s |
| Disposicion de atomizadores | {NOZ} | integrar; corrige la premisa de H3 |
| Rango de gota (boquilla de niebla opcional) | 10-500 um (estandar 50-500) | integrar |
| Regimen del disco del atomizador | hasta 14 000 rpm | integrar: es del ATOMIZADOR, NO del rotor |

**Discrepancias con la ficha oficial detectadas en esta plataforma:** {DISC}

**Lo que sigue en D (no lo aporta ninguna fuente publica):** numero real de rotores y pares
coaxiales, posicion XYZ de rotores y de atomizadores, RPM real del rotor, presion de
pulverizacion, espectro de gota medido y velocidad/altura de aplicacion.
Ver `geometry/protocolo_geometria.md` (bloques A y B).
"""

VAL = {
    "T25P": dict(
        ROT="no declarada; requiere medicion",
        COAX="no declarada (hipotesis I: cuadricoptero, 4 rotores)",
        NOZ="sin cambios: 2 estandar / 4 opcional, boquillas traseras a 1420 mm",
        DISC="peso con bateria 32,8 kg (Academy) vs 33 kg (specs); MTOW pulverizacion 52,8 vs 53 kg (redondeo, irrelevante)",
    ),
    "T55": dict(
        ROT="no declarada; requiere medicion",
        COAX="no declarada en el texto extraido; specs DJI dicen '4 pares de helices'",
        NOZ="sin cambios: 2 estandar / 4 opcional, 1800 mm",
        DISC="el texto extraido del deck NO incluye seccion propia del T55; las dimensiones 3175x3490x960 del deck corresponden al T70P",
    ),
    "T70P": dict(
        ROT="motor 1/3 CW, motor 2/4 CCW -> OPUESTA a la de un cuadricoptero tradicional",
        COAX="sin declarar explicitamente; el deck numera motores 1-4",
        NOZ="sin cambios: 2 estandar / 4 opcional, 1874 mm",
        DISC="dimensiones desplegadas: 3200x3520x960 mm (specs) vs 3175x3490x960 mm (Academy) -> CONTRADICCION entre fuentes DJI; resolver con medicion",
    ),
    "T100": dict(
        ROT="'igual que T40/T50' (no se explicita el sentido por motor)",
        COAX="CONFIRMADA: 'helices duales coaxiales'",
        NOZ="4 boquillas TRASERAS sobre barra (no delanteras+traseras)",
        DISC="masa de pulverizacion: 75 kg (specs, 2 boq.) vs 73 kg (Academy); 77 kg vs 74,9 kg (4 boq.) -> CONTRADICCION entre fuentes DJI",
    ),
}


def main() -> int:
    for uav, v in VAL.items():
        p = ROOT / "docs" / "specs" / f"{uav}.md"
        if not p.exists():
            print(f"{uav}: ficha ausente")
            continue
        t = p.read_text(encoding="utf-8")
        if "FUENTES P-A (DJI Academy)" in t:
            print(f"{uav}: ya tiene la seccion, no se duplica")
            continue
        nota = NOTA
        for k, val in v.items():
            nota = nota.replace("{" + k + "}", val)
        p.write_text(t.rstrip() + nota, encoding="utf-8")
        print(f"{uav}: seccion P-A anadida -> {p.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
