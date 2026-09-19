"""
PRESUPUESTO DE HIPOTESIS + ranking de sensibilidad.

PARA QUE SIRVE:
  responde a la pregunta "¿podemos seguir con lo declarado en la web?" con numeros, no con
  una opinion. Separa:
    - lo que esta DOCUMENTADO (P / P-A)          -> no es hipotesis, es dato con fuente
    - lo que esta APORTADO por el propietario (O) -> mejor que inferir, pero sin instrumento
    - lo que es INFERIDO con razonamiento (I)     -> hipotesis de trabajo declarada
    - lo que es ESTIMADO de planificacion (E)
    - lo que sigue DESCONOCIDO (D)                -> se deja null

  Y para cada incognita calcula el EFECTO sobre las magnitudes del modelo, para decidir
  DONDE vale la pena gastar el esfuerzo de medicion. Esto es lo que convierte "suponga que"
  en una idealizacion defendible: la suposicion entra, pero con su impacto cuantificado.

Lo que este script NO hace: no rellena valores desconocidos ni cierra gates.

Uso:
  python scripts/assumption_budget.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "geometry" / "presupuesto_hipotesis.json"

G = 9.81
RHO = 1.1716          # 28 C, nivel del mar

PLAT = {
    "T25P": dict(mtow=53.0,  d_rotor=1.270, n_rot=4, coaxial=False),
    "T55":  dict(mtow=95.0,  d_rotor=1.575, n_rot=8, coaxial=True),
    "T70P": dict(mtow=126.0, d_rotor=1.574, n_rot=8, coaxial=True),
    "T100": dict(mtow=175.0, d_rotor=1.574, n_rot=8, coaxial=True),
}


def v_ind(mtow: float, n: int, d: float) -> float:
    A = n * math.pi * (d / 2) ** 2
    return math.sqrt((mtow * G) / (2 * RHO * A))


def pct(a: float, b: float) -> float:
    return (a - b) / b * 100.0


def main() -> int:
    print("=" * 90)
    print("PARTE 1 — INVENTARIO: que es dato y que es hipotesis")
    print("=" * 90)

    inventario = [
        # (campo, clase, fuente, entra al CFD de estudio?)
        ("Masa con bateria / MTOW", "P", "ficha oficial", "si, cita"),
        ("Diametro de rotor", "P", "ficha oficial (50/62 in)", "si, cita"),
        ("Motor: estator y KV", "P", "ficha oficial", "si, cita"),
        ("Nº de atomizadores y separacion", "P", "ficha oficial", "si, cita"),
        ("Caudales, rango de gota, ancho nominal", "P", "ficha oficial", "si, cita"),
        ("Helice 6223 = 62x23 in, palas = 2", "P-A + S", "Academy + imagen", "si, anota fuente"),
        ("Coaxialidad T70P/T100", "S", "imagen oficial", "si, como topologia"),
        ("Nº de motores (4 / 8)", "O", "propietario, comunicacion directa", "solo como hipotesis declarada"),
        ("X de atomizadores T100", "O", "propietario, comunicacion directa", "solo como hipotesis declarada"),
        ("Separacion axial del par coaxial", "D", "no disponible", "NO: parametro de sensibilidad"),
        ("Reparto de empuje superior/inferior", "D", "no disponible", "NO: parametro de sensibilidad"),
        ("Nº de rotores del T100 (8 o 16)", "D (conflicto)", "ficha dice 8 pares; imagen dice 8 helices",
         "NO: parametro de sensibilidad"),
        ("Posicion XYZ de rotores", "D", "no disponible", "NO: parametro de sensibilidad"),
        ("Posicion Z de atomizadores", "D", "no disponible", "NO: parametro de sensibilidad"),
        ("RPM real", "D", "no disponible (KV no sirve)", "NO: define la frontera CFD"),
        ("Geometria de pala (cuerda, twist)", "D", "no disponible", "NO: limita a actuator disk"),
    ]
    print(f"\n  {'campo':44s} {'clase':13s} {'fuente':40s}")
    for campo, clase, fuente, _ in inventario:
        print(f"  {campo:44s} {clase:13s} {fuente:40s}")

    print("\n" + "=" * 90)
    print("PARTE 2 — SENSIBILIDAD: cuanto cambia el resultado con cada incognita")
    print("=" * 90)

    filas = []

    # --- S1: nº de rotores del T100 (8 vs 16) -> efecto en carga de disco y v_inducida
    t100 = PLAT["T100"]
    v8 = v_ind(t100["mtow"], 8, t100["d_rotor"])
    v16 = v_ind(t100["mtow"], 16, t100["d_rotor"])
    A8 = 8 * math.pi * (t100["d_rotor"] / 2) ** 2
    A16 = 16 * math.pi * (t100["d_rotor"] / 2) ** 2
    filas.append({
        "id": "S1", "incognita": "Nº de rotores del T100 (8 vs 16)",
        "magnitud": "v_inducida en hover", "base": round(v8, 2), "alt": round(v16, 2),
        "efecto_pct": round(pct(v16, v8), 1),
        "detalle": f"area de disco {A8:.2f} -> {A16:.2f} m2; factor sqrt(2)={math.sqrt(2):.4f}",
        "criticidad": "ALTA"})

    # --- S2: separacion axial del par coaxial -> efecto en la longitud de estela
    # modelo simple: la estela del rotor superior se contrae/acelera antes de entrar al inferior.
    # Cuantificamos el EFECTO RELATIVO en la distancia disponible para que la gota sea arrastrada.
    for clave, p in PLAT.items():
        if not p["coaxial"]:
            continue
        sep = 0.20   # supuesto nominal de trabajo
        r = 0.10     # rango plausible en el que se movera el valor real
        # proxy: el espaciado axial compite con la distancia atomizador-suelo en H=3 m
        H = 3.0
        efecto = r / H * 100.0
        filas.append({
            "id": f"S2-{clave}", "incognita": "Separacion axial del par coaxial",
            "magnitud": "longitud de estela antes del disco inferior (proxy)",
            "base": sep, "alt": sep + r, "efecto_pct": round(efecto, 1),
            "detalle": f"±{r*100:.0f} cm sobre una altura de aplicacion de {H:.0f} m",
            "criticidad": "MEDIA"})

    # --- S3: posicion Z de atomizadores -> fraccion de altura que la gota cae en la estela
    for clave, p in PLAT.items():
        H = 3.0
        z_atom = -0.20   # supuesto
        dz = 0.20        # rango plausible
        efecto = dz / H * 100.0
        filas.append({
            "id": f"S3-{clave}", "incognita": "Posicion Z de atomizadores",
            "magnitud": "altura de caida dentro de la estela",
            "base": z_atom, "alt": z_atom - dz, "efecto_pct": round(efecto, 1),
            "detalle": f"±{dz*100:.0f} cm sobre H={H:.0f} m; afecta al tiempo de residencia en la estela",
            "criticidad": "ALTA"})

    # --- S4: reparto de empuje superior/inferior -> efecto en el empuje de cada disco
    for r_split in (0.5, 0.6, 0.7):
        efecto = pct(r_split, 0.5)
        filas.append({
            "id": f"S4-{r_split:.1f}", "incognita": "Reparto de empuje superior/inferior",
            "magnitud": "empuje del rotor superior (fraccion del par)",
            "base": 0.5, "alt": r_split, "efecto_pct": round(efecto, 1),
            "detalle": "si el reparto no es 50/50, el disco de arriba carga mas empuje",
            "criticidad": "ALTA" if r_split >= 0.6 else "MEDIA"})

    # --- S5: posicion XYZ de rotores -> efecto en la separacion efectiva entre discos
    for clave, p in PLAT.items():
        wb = {"T25P": 1.970, "T55": 2.415, "T70P": 2.440, "T100": 2.330}[clave]
        R = wb / 2
        lado = R / math.sqrt(2)
        err = 0.03   # 3 cm de error plausible en la posicion
        efecto = err / lado * 100.0
        filas.append({
            "id": f"S5-{clave}", "incognita": "Posicion XYZ de rotores",
            "magnitud": "separacion entre ejes adyacentes (interferencia)",
            "base": round(lado, 3), "alt": round(lado + err, 3), "efecto_pct": round(efecto, 1),
            "detalle": f"±{err*100:.0f} cm sobre {lado:.3f} m derivados del wheelbase",
            "criticidad": "MEDIA"})

    filas.sort(key=lambda f: -f["efecto_pct"])
    print(f"\n  {'id':9s} {'incognita':38s} {'magnitud':44s} {'efecto':>8s} {'criticidad':10s}")
    for f in filas:
        print(f"  {f['id']:9s} {f['incognita'][:37]:38s} {f['magnitud'][:43]:44s} "
              f"{f['efecto_pct']:+7.1f}% {f['criticidad']:10s}")
    print(f"\n  {'detalle':9s}")
    for f in filas:
        print(f"  {f['id']:9s} {f['detalle']}")

    print("\n" + "=" * 90)
    print("PARTE 3 — CONCLUSION PRACTICA: donde gastar el esfuerzo de medicion")
    print("=" * 90)
    prioridad = [
        ("1", "Nº de rotores del T100", "8 vs 16 mueve la fisica un factor sqrt(2) = +41 %",
         "contar fisicamente, con foto cenital (minutos)"),
        ("2", "Posicion Z de atomizadores", "define cuanto tiempo la gota cae dentro de la estela",
         "cinta metrica (minutos)"),
        ("3", "Reparto de empuje del par coaxial", "si no es 50/50, cambia la carga de cada disco",
         "RPM por rotor + bancada (mas costoso)"),
        ("4", "Posicion XYZ de rotores", "estructura espacial de la interferencia",
         "cinta metrica desde el origen (minutos)"),
        ("5", "Separacion axial del par", "longitud de estela antes del disco inferior",
         "cinta metrica (minutos)"),
        ("6", "RPM real", "define si el CFD va por RPM o por empuje prescrito",
         "tacometro en hover (requiere volar)"),
    ]
    for p, campo, por_que, como in prioridad:
        print(f"\n  {p}. {campo}")
        print(f"     por que: {por_que}")
        print(f"     como   : {como}")

    print("\n  OBSERVACION CLAVE: las cuatro incognitas mas criticas (1, 2, 4, 5) se resuelven")
    print("  con CINTA METRICA Y CONTEO, sin instrumentos especiales ni volar. Solo el reparto")
    print("  de empuje (3) y la RPM (6) exigen equipamiento o vuelo.")

    salida = {"generado_por": "scripts/assumption_budget.py",
              "inventario": [{"campo": c, "clase": k, "fuente": f, "uso": u}
                             for c, k, f, u in inventario],
              "sensibilidad": filas,
              "prioridad_medicion": [{"orden": p, "campo": c, "por_que": w, "como": h}
                                     for p, c, w, h in prioridad]}
    OUT.write_text(json.dumps(salida, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n-> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
