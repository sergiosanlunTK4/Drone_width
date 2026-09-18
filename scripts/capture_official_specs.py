"""
Recaptura FORENSE de las paginas oficiales de especificaciones (T100, T70P, T55).

POR QUE FORENSE Y NO UNA SIMPLE CONSULTA:
  las paginas web cambian. Para un trabajo reproducible hay que poder demostrar
  exactamente QUE version se consulto. Por eso se archiva: URL, fecha/hora, locale,
  cabeceras de respuesta, HTML crudo y hash SHA256 de cada captura.

QUE PERSIGUE (encargo del investigador):
  1. T100, T70P y T55 en la misma sesion, en ES y en ZH (original chino + internacional).
  2. De cada tabla: fila completa y encabezados, no solo el valor. El objetivo es
     determinar que significa exactamente "Cantidad" en la fila de helices.
  3. En chino, conservar el TEXTO UNICODE ORIGINAL, sin traducir. Si aparece 对 (par),
     NO se interpreta: primero hay que saber que unidad comercial esta contando DJI.
  4. Buscar ademas motor, ESC, helice/propeller, coaxial y listas de componentes:
     A10 (accionamiento del par) podria resolverse si DJI declara p.ej. 8 ESC vs 4.
  5. Hash de cada captura para archivarla como evidencia documental.

REGLA: este script REPORTA hechos de la captura. NO modifica manifests, NO cambia
rotor_count y NO convierte nada en M. Eso exige convergencia entre tabla, diagrama e
inspeccion fisica.

Uso:
  python scripts/capture_official_specs.py
"""
from __future__ import annotations

import hashlib
import json
import re
import ssl
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "specs_captures"

UAVS = ["t100", "t70p", "t55"]
LOCALES = [
    ("es", "https://ag.dji.com/es/{u}/specs"),
    ("zh", "https://ag.dji.com/cn/{u}/specs"),
]
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

# terminos a rastrear en el texto (ES y ZH)
TERMINOS = {
    "cantidad": r"Cantidad|数量|數|数目",
    "pares": r"\bpares?\b|对|對|双|雙",
    "helice": r"h[eé]lice|propeller|螺旋桨|槳|桨",
    "motor": r"\bmotor(?:es)?\b|电机|馬達|马达",
    "esc": r"\bESC\b|电调|電子調速|电子调速",
    "coaxial": r"coaxial|同轴|同軸",
    "pulgadas": r"pulgadas|inch|英寸",
    "ejes": r"entre ejes|wheelbase|轴距|軸距|对角",
}


def fetch(url: str) -> dict:
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,zh-CN;q=0.8,en;q=0.7",
    })
    ctx = ssl.create_default_context()
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=45, context=ctx) as r:
        raw = r.read()
        return {
            "status": r.status,
            "bytes": len(raw),
            "headers": {k.lower(): v for k, v in r.headers.items()},
            "raw": raw,
            "segundos": round(time.time() - t0, 2),
        }


def extraer_tablas(html: str) -> list[list[list[str]]]:
    """Extrae tablas HTML crudas conservando filas completas."""
    out = []
    for tbl in re.findall(r"<table\b.*?</table>", html, re.S | re.I):
        filas = []
        for tr in re.findall(r"<tr\b.*?</tr>", tbl, re.S | re.I):
            celdas = []
            for celda in re.findall(r"<t[hd]\b.*?</t[hd]>", tr, re.S | re.I):
                txt = re.sub(r"<[^>]+>", " ", celda)
                txt = unescape(re.sub(r"\s+", " ", txt)).strip()
                celdas.append(txt)
            if celdas:
                filas.append(celdas)
        if filas:
            out.append(filas)
    return out


def contexto(html: str, patron: str, ventana: int = 260) -> list[dict]:
    """Devuelve coincidencias con contexto, tal como aparecen en el documento."""
    hits = []
    for m in re.finditer(patron, html, re.I):
        ini = max(0, m.start() - ventana // 2)
        frag = html[ini:m.end() + ventana]
        frag = re.sub(r"<[^>]+>", " ", frag)
        frag = unescape(re.sub(r"\s+", " ", frag)).strip()
        hits.append({"match": m.group(0), "contexto": frag[:400]})
    return hits


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    manifiesto = {
        "proposito": "recaptura forense de fichas oficiales para resolver el significado "
                     "de 'Cantidad' (A9) y buscar evidencia de accionamiento (A10)",
        "regla": "esto es evidencia documental; NO modifica manifests ni convierte nada en M",
        "capturado_en": datetime.now(timezone.utc).isoformat(),
        "user_agent": UA,
        "capturas": [],
    }

    for uav in UAVS:
        for loc, plantilla in LOCALES:
            url = plantilla.format(u=uav)
            entrada = {"uav": uav.upper(), "locale": loc, "url": url}
            print(f"\n=== {uav.upper()} [{loc}] {url}")
            try:
                r = fetch(url)
            except Exception as e:  # noqa: BLE001
                entrada["error"] = f"{type(e).__name__}: {e}"
                print(f"    FALLO: {entrada['error']}")
                manifiesto["capturas"].append(entrada)
                continue

            html = r["raw"].decode("utf-8", errors="replace")
            sha = hashlib.sha256(r["raw"]).hexdigest()
            dest = OUT / f"{uav}_{loc}_{sha[:12]}.html"
            dest.write_bytes(r["raw"])

            entrada.update({
                "status": r["status"],
                "bytes": r["bytes"],
                "sha256": sha,
                "archivo": str(dest.relative_to(ROOT)).replace("\\", "/"),
                "content_type": r["headers"].get("content-type"),
                "server": r["headers"].get("server"),
                "last_modified": r["headers"].get("last-modified"),
                "segundos": r["segundos"],
            })
            print(f"    status={r['status']} bytes={r['bytes']} sha256={sha[:16]}...")

            tablas = extraer_tablas(html)
            entrada["n_tablas_html"] = len(tablas)
            print(f"    tablas HTML encontradas: {len(tablas)}")

            # terminos
            entrada["terminos"] = {}
            for nombre, patron in TERMINOS.items():
                hits = contexto(html, patron)
                if hits:
                    entrada["terminos"][nombre] = hits[:6]
                    print(f"    [{nombre}] {len(hits)} coincidencias")

            manifiesto["capturas"].append(entrada)

    # informe legible
    informe = [f"# Recaptura forense de fichas oficiales",
               f"", f"**Fecha (UTC):** {manifiesto['capturado_en']}  ",
               f"**User-Agent:** `{UA}`", "",
               "> Estas capturas son **evidencia documental**. No modifican manifiestos ni",
               "> convierten ningun valor en `M`. Sirven para reconstruir la semantica de la",
               "> tabla (que cuenta exactamente «Cantidad») antes de usarla como conteo fisico.", ""]
    for c in manifiesto["capturas"]:
        informe.append(f"## {c['uav']} — locale `{c['locale']}`")
        informe.append("")
        if "error" in c:
            informe.append(f"- ❌ **FALLO:** `{c['error']}`")
            informe.append("")
            continue
        informe.append(f"- URL: {c['url']}")
        informe.append(f"- status: {c['status']} · bytes: {c['bytes']} · "
                       f"content-type: {c.get('content_type')}")
        informe.append(f"- archivo: `{c['archivo']}`")
        informe.append(f"- **sha256:** `{c['sha256']}`")
        informe.append(f"- tablas HTML: {c.get('n_tablas_html')}")
        informe.append("")
        for nombre, hits in (c.get("terminos") or {}).items():
            informe.append(f"### término `{nombre}` — {len(hits)} coincidencia(s)")
            informe.append("")
            for h in hits:
                informe.append(f"- `{h['match']}` … {h['contexto'][:300]}")
            informe.append("")
    (OUT / "INFORME_capturas.md").write_text("\n".join(informe), encoding="utf-8")
    (OUT / "capturas_manifest.json").write_text(
        json.dumps(manifiesto, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\ninforme -> {(OUT / 'INFORME_capturas.md').relative_to(ROOT)}")
    print(f"manifiesto -> {(OUT / 'capturas_manifest.json').relative_to(ROOT)}")
    print("\nREGLA: esto REPORTA. No se toca rotor_count ni ningun manifiesto.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
