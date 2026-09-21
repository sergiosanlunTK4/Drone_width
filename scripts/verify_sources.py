"""
Verifica si las fuentes tecnicas de la cadena de calculo son ACCESIBLES y reales.

POR QUE EXISTE (peticion del investigador):
  "el angulo tambien debemos calcularlo si es que no esta en la literatura, si si esta, hay que
   revisar si es una fuente real"

  Es decir: no basta con citar de memoria. Hay que COMPROBAR que la fuente existe, es accesible
  y dice lo que se le atribuye. Este script hace esa comprobacion y clasifica cada fuente:
      VERIFICADA  = se descargo y contiene los terminos esperados
      ACCESIBLE   = responde 200 pero no se pudo confirmar el contenido
      NO_ACCESIBLE= error de red, 403, 404 o pago
      NO_VERIFICADA = no se intento (se declara como conocimiento general, no como cita)

Uso:
  python scripts/verify_sources.py
"""
from __future__ import annotations

import json
import re
import ssl
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evidence" / "fuentes_verificadas.json"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

# terminos que deben aparecer para considerar la fuente confirmada
TERMINOS_POR_FUENTE = {
    "momentum": ["momentum", "induced", "thrust"],
    "bemt": ["blade", "element", "thrust", "coefficient"],
    "forward": ["forward flight", "advance ratio", "tilt"],
    "drag": ["drag", "coefficient", "frontal"],
}

FUENTES = [
    {
        "id": "openfoam-actuation",
        "que": "definicion de los coeficientes del disco actuador (Ct, Cp, a)",
        "url": "https://doc.openfoam.com/2412/tools/processing/numerics/fvoptions/sources/rtm/actuationDisk/",
        "esperados": ["Cp", "Ct", "diskArea", "diskDir"],
    },
    {
        "id": "openfoam-api",
        "que": "implementacion de actuationDiskSource (metodo Froude)",
        "url": "https://api.openfoam.com/2412/actuationDiskSource_8C_source.html",
        "esperados": ["Froude", "upstreamPoint", "thrustCoeff"],
    },
    {
        "id": "momentum-theory",
        "que": "teoria de cantidad de movimiento del disco actuador",
        "url": "https://en.wikipedia.org/wiki/Momentum_theory",
        "esperados": ["induced velocity", "actuator disk", "thrust"],
    },
    {
        "id": "multirotor-forward",
        "que": "vuelo en avance de multirrotor: actitud y resistencia",
        "url": "https://en.wikipedia.org/wiki/Quadcopter",
        "esperados": ["tilt", "forward", "pitch"],
    },
    {
        "id": "bemt",
        "que": "teoria de elemento de pala (BEMT) para empuje y potencia",
        "url": "https://en.wikipedia.org/wiki/Blade_element_momentum_theory",
        "esperados": ["blade element", "momentum", "thrust"],
    },
    {
        "id": "drag-fuselage",
        "que": "resistencia aerodinamica y coeficiente de arrastre",
        "url": "https://en.wikipedia.org/wiki/Drag_coefficient",
        "esperados": ["drag coefficient", "frontal area"],
    },
]


def fetch(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                              "Accept": "text/html,*/*;q=0.8"})
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=40, context=ctx) as r:
            raw = r.read()
            return {"status": r.status, "bytes": len(raw),
                    "texto": raw.decode("utf-8", errors="replace")}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "error": f"HTTP {e.code}"}
    except Exception as e:  # noqa: BLE001
        return {"status": None, "error": f"{type(e).__name__}: {e}"}


def main() -> int:
    import hashlib

    salida = {"fecha_utc": datetime.now(timezone.utc).isoformat(),
              "proposito": "comprobar que las fuentes son reales y accesibles antes de citarlas",
              "fuentes": []}

    print("=" * 94)
    print("VERIFICACION DE FUENTES DE LA CADENA DE CALCULO")
    print("=" * 94)

    for f in FUENTES:
        print(f"\n--- {f['id']}: {f['que']}")
        print(f"    {f['url']}")
        r = fetch(f["url"])
        entrada = {"id": f["id"], "que": f["que"], "url": f["url"]}

        if r.get("texto") is None:
            entrada["estado"] = "NO_ACCESIBLE"
            entrada["detalle"] = r.get("error", f"status {r.get('status')}")
            print(f"    [NO_ACCESIBLE] {entrada['detalle']}")
        else:
            txt = r["texto"]
            bajo = txt.lower()
            encontrados = [t for t in f["esperados"] if t.lower() in bajo]
            faltan = [t for t in f["esperados"] if t.lower() not in bajo]
            entrada["status"] = r["status"]
            entrada["bytes"] = r["bytes"]
            entrada["sha256"] = hashlib.sha256(txt.encode("utf-8", errors="replace")).hexdigest()
            entrada["terminos_encontrados"] = encontrados
            entrada["terminos_faltantes"] = faltan
            if not faltan:
                entrada["estado"] = "VERIFICADA"
            elif len(encontrados) >= len(f["esperados"]) // 2:
                entrada["estado"] = "ACCESIBLE_PARCIAL"
            else:
                entrada["estado"] = "ACCESIBLE_SIN_CONFIRMAR"
            print(f"    [{entrada['estado']}] status={r['status']} bytes={r['bytes']}")
            print(f"    terminos encontrados: {encontrados}")
            if faltan:
                print(f"    terminos NO encontrados: {faltan}")

        salida["fuentes"].append(entrada)

    resumen = {}
    for e in salida["fuentes"]:
        resumen[e["estado"]] = resumen.get(e["estado"], 0) + 1
    salida["resumen"] = resumen

    print("\n" + "=" * 94)
    print(f"RESUMEN: {resumen}")
    print("=" * 94)
    print("""
  REGLA QUE SE APLICA A PARTIR DE AQUI:
    - Solo se cita como FUENTE VERIFICADA lo que aparezca como VERIFICADA arriba.
    - Lo que quede NO_ACCESIBLE o ACCESIBLE_SIN_CONFIRMAR se declara como
      "conocimiento general, pendiente de verificacion", NO como cita.
    - El angulo de actitud se CALCULA con el modelo fisico, y se contrasta con literatura
      SOLO si la fuente esta verificada. No se atribuye a una fuente no comprobada.
""")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(salida, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"-> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
