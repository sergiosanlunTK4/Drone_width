"""
Persigue el texto CHINO ORIGINAL de la fila de helices (termino 对 / 桨).

POR QUE HACE FALTA:
  la fila "Sistema de propulsion - Helices :: Cantidad = 8 pares" (T100) y "4 pares" (T55)
  frente a "4" a secas (T70P) deja la semantica sin resolver. El original chino usaria
  对 (par) o 支/个/片 (piezas), y saber QUE palabra usa DJI resolveria que esta contando.
  Pero /es/ y /cn/ devuelven bytes identicos, asi que hay que intentar otras vias.

VIAS QUE PRUEBA ESTE SCRIPT:
  1. /cn/ con Accept-Language zh-CN explicito y cookie de locale.
  2. El endpoint de API que alimenta la app (__NEXT_DATA__ / /api/ / _next/data).
  3. Chunks de localizacion estaticos.

REGLA: REPORTA. Guarda lo que obtiene con hash y deja constancia de lo que falla.
NO interpreta 对 ni toca manifiestos.

Uso:
  python scripts/fetch_chinese_specs.py
"""
from __future__ import annotations

import hashlib
import json
import re
import ssl
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "specs_captures"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

INTENTOS = [
    ("cn_zh_header", "https://ag.dji.com/cn/t100/specs",
     {"Accept-Language": "zh-CN,zh;q=0.9"}),
    ("cn_cookie", "https://ag.dji.com/cn/t100/specs",
     {"Accept-Language": "zh-CN,zh;q=0.9", "Cookie": "locale=zh-CN; lang=zh-CN; dji_locale=zh-CN"}),
    ("intl_zh", "https://www.dji.com/cn/t100/specs",
     {"Accept-Language": "zh-CN,zh;q=0.9"}),
]


def get(url: str, extra: dict | None = None) -> dict:
    h = {"User-Agent": UA,
         "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}
    h.update(extra or {})
    req = urllib.request.Request(url, headers=h)
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=45, context=ctx) as r:
        raw = r.read()
        return {"status": r.status, "url": r.geturl(), "raw": raw,
                "headers": {k.lower(): v for k, v in r.headers.items()}}


def cjk(txt: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]", txt))


def buscar_fila_helices(txt: str) -> list[str]:
    """Busca la fila de helices en el payload, sea cual sea el idioma."""
    out = []
    for m in re.finditer(r'\{[^{}]*"(?:title|name)"\s*:\s*"((?:[^"\\]|\\.)*)"[^{}]*\}', txt):
        t = m.group(1)
        if re.search(r"h[eé]lice|螺旋桨|桨|槳|propeller", t, re.I):
            out.append(m.group(0)[:600])
    # tambien el bloque completo con specs
    for m in re.finditer(r'\{"title":"((?:[^"\\]|\\.)*)","specs":(\[.*?\])\}', txt):
        if re.search(r"h[eé]lice|螺旋桨|桨|槳|propeller", m.group(1), re.I):
            out.append(m.group(0)[:800])
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    log = {"fecha_utc": datetime.now(timezone.utc).isoformat(),
           "objetivo": "obtener el texto chino original de la fila de helices (对 / 桨)",
           "intentos": []}

    for nombre, url, extra in INTENTOS:
        entrada = {"nombre": nombre, "url": url, "headers_extra": extra}
        print(f"\n=== {nombre}: {url}")
        try:
            r = get(url, extra)
        except Exception as e:  # noqa: BLE001
            entrada["error"] = f"{type(e).__name__}: {e}"
            print(f"    FALLO: {entrada['error']}")
            log["intentos"].append(entrada)
            continue

        txt = r["raw"].decode("utf-8", errors="replace")
        sha = hashlib.sha256(r["raw"]).hexdigest()
        dest = OUT / f"zh_{nombre}_{sha[:12]}.html"
        dest.write_bytes(r["raw"])
        entrada.update({
            "status": r["status"], "url_final": r["url"], "bytes": len(r["raw"]),
            "sha256": sha, "archivo": str(dest.relative_to(ROOT)).replace("\\", "/"),
            "lang_html": re.findall(r'<html[^>]*lang="([^"]+)"', txt)[:2],
            "caracteres_CJK": cjk(txt),
            "content_type": r["headers"].get("content-type"),
        })
        print(f"    status={r['status']} bytes={len(r['raw'])} CJK={entrada['caracteres_CJK']} "
              f"lang={entrada['lang_html']}")
        filas = buscar_fila_helices(txt)
        if filas:
            entrada["filas_helices"] = filas[:4]
            print(f"    filas de helices encontradas: {len(filas)}")
            for f in filas[:3]:
                print(f"      {f[:220]}")
        else:
            print("    sin filas de helices en el payload")
        # buscar el caracter 对 explicitamente
        for m in list(re.finditer(r".{60}对.{60}", txt))[:3]:
            print(f"    [对] … {m.group(0)} …")
            entrada.setdefault("contextos_dui", []).append(m.group(0))
        log["intentos"].append(entrada)

    (OUT / "intentos_chino.json").write_text(
        json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nlog -> {(OUT / 'intentos_chino.json').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
