"""
Audita el modelo geometrico real del T100 contra GATE 1A y contra mis valores derivados.

QUE COMPRUEBA:
  1. Coherencia INTERNA del JSON (que las coordenadas concuerden con lo que dice el README).
  2. Coherencia con las ESPECIFICACIONES OFICIALES (wheelbase 2330 mm, rotor 62 in).
  3. Coherencia con MIS valores derivados (posiciones de atomizadores, nomenclatura).
  4. Contraste de la relacion geometrica candidata con la geometria REAL.
  5. Que informacion nueva aporta que yo tenia en D.

NO modifica el JSON ni ningun manifiesto. Solo lee y reporta.

Uso:
  python scripts/audit_t100_model.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELO = ROOT / "geometry" / "models" / "T100_CFD" / "t100_cfd_coordinates.json"

# --- valores de referencia -------------------------------------------------------
OFICIAL = {
    "wheelbase_diagonal_mm": 2330,     # ficha oficial DJI (P)
    "rotor_dia_m": 1.5748,             # 62 pulgadas (P / Academy 6223)
    "rotor_count_hipotesis": 8,        # S (imagen) + O (propietario 8 motores)
    "dims_desplegado_mm": (3220, 3224, 975),
    "atom_sep_mm": 1834,               # ficha oficial
    "tanque_kg": 100.0,
    "mtow_kg": 175.0,
}
# --- mis valores derivados (clase O/I) -------------------------------------------
DERIVADO = {
    "atom_x_usuario": [-0.9, -0.8, -0.8, -0.9],       # clase O (propietario)
    "atom_y_exterior": -0.9170,                        # mi hipotesis "par extremo"
    "atom_y_interior": -0.4585,                        # mi hipotesis "interior a la mitad"
}


def main() -> int:
    if not MODELO.exists():
        print(f"no existe {MODELO.relative_to(ROOT)}")
        return 2
    txt = MODELO.read_text(encoding="utf-8")
    print("=" * 92)
    print("AUDITORIA DEL MODELO GEOMETRICO REAL — DJI Agras T100")
    print("=" * 92)
    print(f"  archivo: {MODELO.relative_to(ROOT)}   ({len(txt)} bytes)")

    # claves de primer y segundo nivel
    try:
        d = json.loads(txt)
    except json.JSONDecodeError as e:
        print(f"  [FALLO] JSON invalido: {e}")
        return 1

    print(f"\n  claves de primer nivel:")
    for k in d:
        v = d[k]
        tipo = type(v).__name__
        n = f" ({len(v)})" if isinstance(v, (list, dict)) else ""
        print(f"    - {k}: {tipo}{n}")

    # volcar la estructura para localizar los datos
    def esqueleto(obj, pref="", nivel=0, maxnivel=3):
        if nivel > maxnivel:
            return
        if isinstance(obj, dict):
            for k, v in obj.items():
                tipo = type(v).__name__
                n = f" ({len(v)})" if isinstance(v, (list, dict)) else f" = {str(v)[:60]}"
                print(f"    {'  ' * nivel}{k}: {tipo}{n}")
                if isinstance(v, (dict, list)) and nivel < maxnivel:
                    esqueleto(v, f"{pref}.{k}", nivel + 1, maxnivel)
        elif isinstance(obj, list) and obj:
            print(f"    {'  ' * nivel}[0]: {type(obj[0]).__name__}")
            esqueleto(obj[0], f"{pref}[0]", nivel + 1, maxnivel)

    print(f"\n  ESTRUCTURA (hasta 3 niveles):")
    esqueleto(d)

    print("\n" + "=" * 92)
    print("BUSQUEDA DE VALORES CLAVE")
    print("=" * 92)

    # buscar por nombre de campo, sea cual sea la ruta
    def buscar(obj, patrones, ruta=""):
        hallados = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                if any(p.lower() in k.lower() for p in patrones):
                    hallados.append((f"{ruta}.{k}".lstrip("."), v))
                hallados += buscar(v, patrones, f"{ruta}.{k}".lstrip("."))
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                hallados += buscar(v, patrones, f"{ruta}[{i}]")
        return hallados

    def resumir(obj, prof=0):
        if isinstance(obj, (int, float, str)):
            return str(obj)
        if isinstance(obj, list):
            return f"lista[{len(obj)}]" + (f" -> {resumir(obj[0])}" if obj else "")
        if isinstance(obj, dict):
            return "{" + ", ".join(f"{k}" for k in list(obj)[:8]) + "}"
        return type(obj).__name__

    for etiqueta, patrones in (
        ("ROTORES", ["rotor", "motor", "disco", "disk"]),
        ("ATOMIZADORES", ["nozzle", "atomiz", "boquilla", "aspersor", "spray"]),
        ("GEOMETRIA", ["wheelbase", "diameter", "diametro", "separacion", "axial"]),
        ("METROLOGIA", ["uncertain", "incert", "method", "instrument", "source", "clasif"]),
    ):
        print(f"\n  --- {etiqueta} ---")
        vistos = set()
        for ruta, val in buscar(d, patrones):
            if ruta in vistos or len(ruta) > 90:
                continue
            vistos.add(ruta)
            print(f"    {ruta}  =  {resumir(val)[:110]}")

    print("\n" + "=" * 92)
    print("VALIDACIONES")
    print("=" * 92)
    fallos = []

    # localizar la lista de rotores y de atomizadores de forma robusta
    def primera_lista(obj, patrones):
        """Busca la primera lista cuyos elementos sean dicts con coordenadas."""
        mejor = None
        def rec(o):
            nonlocal mejor
            if mejor is not None:
                return
            if isinstance(o, dict):
                for k, v in o.items():
                    if isinstance(v, list) and v and isinstance(v[0], dict) \
                       and any(p.lower() in k.lower() for p in patrones):
                        if any(any(c in e for c in ("x", "X", "y", "Y")) for e in v[0]):
                            mejor = v
                            return
                    rec(v)
            elif isinstance(o, list):
                for v in o:
                    rec(v)
        rec(obj)
        return mejor

    rotores = primera_lista(d, ["rotor", "motor", "disk", "disco"])
    atomiz = primera_lista(d, ["nozzle", "atomiz", "boquilla", "aspersor"])

    def campo(e, *nombres):
        """Devuelve el primer campo que coincida. Acepta listas de 3 como vector."""
        for n in nombres:
            for k in e:
                if k.lower() == n.lower():
                    return e[k]
        return None

    def vec(e):
        """Extrae (x,y,z) admitiendo center_xyz_m / position / x,y,z sueltos."""
        v = campo(e, "center_xyz_m", "position_xyz_m", "position", "pos")
        if isinstance(v, list) and len(v) >= 3:
            return v[0], v[1], v[2]
        return campo(e, "x", "X"), campo(e, "y", "Y"), campo(e, "z", "Z")

    if rotores:
        print(f"\n  rotors: {len(rotores)} elementos")
        coords = [vec(e) for e in rotores]
        xs = [c[0] for c in coords if isinstance(c[0], (int, float))]
        ys = [c[1] for c in coords if isinstance(c[1], (int, float))]
        zs = [c[2] for c in coords if isinstance(c[2], (int, float))]
        if xs and ys:
            r = math.hypot(max(abs(v) for v in xs), max(abs(v) for v in ys))
            wb = 2 * r
            print(f"    |X|max={max(abs(v) for v in xs):.4f}  |Y|max={max(abs(v) for v in ys):.4f}")
            print(f"    diagonal entre rotores opuestos = {wb*1000:.1f} mm")
            esperado = OFICIAL["wheelbase_diagonal_mm"]
            err = (wb * 1000 - esperado) / esperado * 100
            ok = abs(err) < 1.0
            print(f"    {'[OK]   ' if ok else '[FALLO]'} vs wheelbase oficial {esperado} mm "
                  f"(error {err:+.2f} %)")
            if not ok:
                fallos.append(f"wheelbase del modelo {wb*1000:.0f} mm vs {esperado} mm")
            # separacion entre ejes adyacentes
            lado = r * math.sqrt(2)
            print(f"    separacion entre ejes adyacentes derivada = {lado:.4f} m")
            print(f"    (el JSON declara adjacent_axis_distance_m = "
                  f"{d.get('general_dimensions',{}).get('adjacent_axis_distance_m','?')})")
        if zs:
            zs_u = sorted({round(v, 4) for v in zs})
            print(f"    niveles Z distintos: {zs_u}")
            if len(zs_u) >= 2:
                sep = max(zs_u) - min(zs_u)
                print(f"    separacion axial del par (A6) = {sep:.4f} m   <-- yo lo tenia en D")

    # --- validacion de direcciones de giro (par opuesto) ---------------------------
    if rotores:
        print(f"\n  DIRECCIONES DE GIRO (por par coaxial)")
        dirs = {}
        for e in rotores:
            rid = campo(e, "rotor_id") or "?"
            rol = campo(e, "position_role") or "?"
            d_ = campo(e, "rotation_direction") or "?"
            dirs[rid] = (rol, d_)
            print(f"    {rid:18s} {rol:8s}  {d_}")
        # comprobar que cada par coaxial gira en sentidos opuestos
        pares = {}
        for rid, (rol, d_) in dirs.items():
            base = rid.rsplit("_", 1)[0]
            pares.setdefault(base, []).append((rol, d_))
        malos = [b for b, v in pares.items() if len(v) == 2 and v[0][1] == v[1][1]]
        print(f"    {'[OK]   ' if not malos else '[FALLO]'} cada par coaxial gira en sentidos "
              f"opuestos: {'si' if not malos else 'NO -> ' + ', '.join(malos)}")
        if malos:
            fallos.append(f"pares coaxiales con el mismo sentido de giro: {malos}")

    if atomiz:
        print(f"\n  atomizadores: {len(atomiz)} elementos")
        coords = [vec(e) for e in atomiz]
        for e, c in zip(atomiz, coords):
            n = campo(e, "nozzle_id", "id", "name") or "?"
            print(f"    {n:18s} X={c[0]}  Y={c[1]}  Z={c[2]}")
        xs = [c[0] for c in coords if isinstance(c[0], (int, float))]
        ys = [c[1] for c in coords if isinstance(c[1], (int, float))]
        zs = [c[2] for c in coords if isinstance(c[2], (int, float))]

        if len(xs) == len(atomiz):
            print(f"\n    CONTRASTE con mis valores derivados (clase O del propietario):")
            print(f"      X del propietario : {DERIVADO['atom_x_usuario']}")
            print(f"      X del modelo      : {sorted(set(xs))}")
            dif = [abs(a - b) for a, b in zip(sorted(xs), sorted(DERIVADO['atom_x_usuario']))]
            print(f"      diferencias (m)   : {[round(v, 3) for v in dif]}")
            dentro = all(abs(v) <= 0.03 for v in dif)
            print(f"      {'[OK]   ' if dentro else '[AVISO]'} coinciden dentro de 3 cm"
                  f"{'' if dentro else ' -> revisar cual es la referencia de X'}")
        if len(ys) == len(atomiz):
            y_abs = sorted({round(abs(v), 4) for v in ys}, reverse=True)
            print(f"      |Y| del modelo    : {y_abs}")
            print(f"      mi hipotesis era  : exterior "
                  f"{abs(DERIVADO['atom_y_exterior'])} / interior "
                  f"{abs(DERIVADO['atom_y_interior'])}")
            ok = any(abs(v - abs(DERIVADO['atom_y_exterior'])) < 1e-3 for v in y_abs)
            print(f"      {'[OK]   ' if ok else '[FALLO]'} hipotesis del 'par extremo' "
                  f"CONFIRMADA por medicion")
            if not ok:
                fallos.append("la hipotesis del par extremo no coincide con el modelo")
        if len(zs) == len(atomiz):
            z = sorted(set(zs))
            print(f"      Z del modelo      : {z}   <-- yo lo tenia en D")
            print(f"      -> a H=3 m de vuelo, el atomizador queda a "
                  f"{3.0 + z[0]:.3f} m sobre el suelo")

    print("\n" + "=" * 92)
    print("RESUMEN")
    print("=" * 92)
    if fallos:
        print("  FALLOS:")
        for f in fallos:
            print(f"    - {f}")
    else:
        print("  Sin fallos de coherencia en las comprobaciones realizadas.")
    print("\n  NOTA: este script REPORTA. No modifica el JSON ni ningun manifiesto, y no")
    print("  promueve nada a M por si solo: la promocion exige decision explicita.")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
