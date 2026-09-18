"""
Genera manifiestos geometricos auditables por UAV.

Principio de diseno (context.md SS7, SS51):
  - Cada valor lleva PROCEDENCIA: P (publico oficial) / P-A (publico DJI Academy) /
    I (inferido, con su razonamiento) / E (estimado de planificacion) / D (desconocido).
  - "D" NO se rellena con un numero inventado: se deja null y se explica que medicion falta.
  - La topologia de rotores (numero y numero de pares coaxiales) es HIPOTESIS explicita,
    nunca un hecho, mientras no haya foto/medicion.
  - El script VALIDA invariantes geometricas y fisicas y falla ruidosamente si hay
    contradiccion con las especificaciones verificadas.

Salidas:
  geometry/manifests/<uav>_geometry_manifest.json   (por plataforma, con procedencia)
  data/processed/geometry_master.csv                (resumen comparativo)

Uso:
  python scripts/build_geometry_manifests.py
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "geometry" / "manifests"
OUT_CSV = ROOT / "data" / "processed" / "geometry_master.csv"

RHO_AIR = 1.1716      # kg/m3 @ 28 C, 0 m s.n.m. (ISA), coherente con SS3 de context.md
G = 9.81              # m/s2

# ---------------------------------------------------------------------------
# DATOS VERIFICADOS (docs/specs/*.md  <=  ag.dji.com/.../specs)
# ---------------------------------------------------------------------------
SRC_SPECS = "docs/specs/{uav}.md (ag.dji.com/es/{uav}/specs, captura data/{UAV}.pdf)"
SRC_ACADEMY = "data/raw/dji_academy_01_conocimiento_basico.txt (DJI Academy, 01 Conocimiento basico de un Dron)"

PLATFORMS = {
    "T25P": {
        "nombre": "DJI Agras T25P",
        "wheelbase_diagonal_mm": 1970,
        "dims_desplegado_mm": [2650, 2700, 820],
        "rotor_diameter_m": 1.270,           # 50 in (P)
        "masa_sin_bateria_kg": 26.0,
        "masa_con_bateria_kg": 33.0,         # (P-A: 32.8)
        "tank_kg": 20.0,
        "mtow_spray_kg": 53.0,               # (P-A: 52.8)
        "atomizers_std": 2, "atomizers_opt": 4,
        "nozzle_spacing_mm": 1420,
        "flow_2_nozzle_Lmin": 16.0, "flow_4_nozzle_Lmin": 24.0,
        "drop_um": [50, 500],
        "swath_nominal_m": [4, 7],
        "motor_stator_mm": [100, 28],
        "motor_kv": 59,
        # topologia: NO confirmada
        "arm_count": 4,                       # I: cuadricoptero (dimensiones y wheelbase lo sugieren)
        "coaxial": False,                     # I
        "rotor_count_hypothesis": 4,          # I
        "blade_model": "no declarado",
    },
    "T55": {
        "nombre": "DJI Agras T55",
        "wheelbase_diagonal_mm": 2415,
        "dims_desplegado_mm": [3190, 3570, 934],
        "rotor_diameter_m": 1.575,            # 62 in (P)
        "masa_sin_bateria_kg": None,          # D  (45 kg es CON bateria DB1050)
        "masa_con_bateria_kg": 45.0,
        "tank_kg": 50.0,
        "mtow_spray_kg": 95.0,
        "atomizers_std": 2, "atomizers_opt": 4,
        "nozzle_spacing_mm": 1800,
        "flow_2_nozzle_Lmin": None, "flow_4_nozzle_Lmin": None,   # D: no capturado en PDF
        "drop_um": [50, 500],
        "swath_nominal_m": [4, 11],
        "motor_stator_mm": [155, 16],
        "motor_kv": 55,
        "arm_count": 4,                       # I: "4 pares de helices" en specs
        "coaxial": True,                      # I
        "rotor_count_hypothesis": 8,          # I: 4 brazos x par coaxial
        "blade_model": "no declarado",
    },
    "T70P": {
        "nombre": "DJI Agras T70P",
        "wheelbase_diagonal_mm": 2440,
        "dims_desplegado_mm": [3200, 3520, 960],   # ficha oficial vigente (P); ver evidence/CONFLICTS.md C-05
        "dims_discrepancia": "RESUELTO (C-05): la ficha oficial vigente dice 3200x3520x960; el deck de "
                             "DJI Academy decia 3175x3490x960 y se descarta. Convergencia entre el PDF del "
                             "investigador y la captura en vivo del 2026-09-14 (dos fuentes del mismo emisor)",
        "blade_model_6223": True,
        "rotor_diameter_m": 1.574,            # helice 6223 = 62 in (P-A)
        "masa_sin_bateria_kg": None,          # D
        "masa_con_bateria_kg": 56.0,          # con DB2160 (P) / 52 con DB1580
        "tank_kg": 70.0,
        "mtow_spray_kg": 126.0,               # DB2160, 2 boquillas
        "atomizers_std": 2, "atomizers_opt": 4,
        "nozzle_spacing_mm": 1874,
        "flow_2_nozzle_Lmin": 30.0, "flow_4_nozzle_Lmin": 40.0,    # P-A (T100/T70P comparten)
        "drop_um": [50, 500],
        "swath_nominal_m": [4, 11],
        "motor_stator_mm": [155, 22],
        "motor_kv": 65,
        "arm_count": 4,                       # I: motores numerados 1-4
        "coaxial": True,                      # I
        "rotor_count_hypothesis": 8,          # I
        "blade_model": "6223 (62 x 23 in) fibra de carbono",
        "rotacion": "motor 1/3 CW, motor 2/4 CCW -> opuesta a cuadricoptero tradicional (P-A)",
        "v_descenso_ms": [2, 3],
        "empuje_eje_kg_ambiguo": 54.2,
    },
    "T100": {
        "nombre": "DJI Agras T100",
        "wheelbase_diagonal_mm": 2330,
        "dims_desplegado_mm": [3220, 3224, 975],
        "rotor_diameter_m": 1.574,            # helice 6223 = 62 in (P-A)
        "masa_sin_bateria_kg": None,          # D
        "masa_con_bateria_kg": 75.0,          # specs oficiales (2 boquillas)
        "masa_con_bateria_kg_alt": 73.0,      # DJI Academy: 73 kg (2 boquillas)
        "masa_discrepancia": "specs oficiales: 75 kg (2 boq.) / 77 kg (4 boq.); DJI Academy: 73 kg (2 boq.) / 74,9 kg (4 boq.)",
        "masa_4_boquillas_kg": 74.9,
        "tank_kg": 100.0,
        "mtow_spray_kg": 175.0,
        "atomizers_std": 2, "atomizers_opt": 4,
        "nozzle_spacing_mm": 1834,
        "flow_2_nozzle_Lmin": 30.0, "flow_4_nozzle_Lmin": 40.0,
        "drop_um": [10, 500],                 # boquilla de niebla opcional (P-A); std 50-500
        "swath_nominal_m": [5, 13],
        "motor_stator_mm": [155, 16],
        "motor_kv": 60,
        "arm_count": 4,                       # I
        "coaxial": True,                      # P-A "helices duales coaxiales" + I: 4 brazos
        "rotor_count_hypothesis": 8,          # I; las specs dicen "8 pares" (=16) -> NO confirmado
        "rotor_count_conflicto": "specs DJI: 'Cantidad: 8 pares'; Academy: 'helices duales coaxiales' sin cuantificar",
        "blade_model": "6223 (62 x 23 in) fibra de carbono",
        "esc_peak_a": 370,
        "empuje_brazo_kg_ambiguo": 82.0,
        "v_max_traslado_ms": 20.0,
        "v_ascenso_ms": 3.0,
        "boom": {
            "modelo": "LS100",
            "plegada_mm": [880, 870, 810],
            "desplegada_mm": [1020, 1930, 810],
            "nota": "barra de pulverizacion: 4 boquillas TRASERAS sobre barra (no en brazos)",
        },
    },
}


def rotor_xyz(wheelbase_mm: float, n_arms: int) -> list[dict]:
    """Posiciones de brazo para configuracion X cuadrada.

    'Distancia diagonal entre ejes' = separacion entre EJES de rotores opuestos.
    Radio del centro a cada eje: R = wheelbase/2. Angulos 45/135/225/315 para X regular.
    """
    import math
    R = (wheelbase_mm / 1000.0) / 2.0
    out = []
    for i, ang in enumerate([45, 135, 225, 315][:n_arms], start=1):
        out.append({
            "arm_id": f"A{i}",
            "angle_deg": ang,
            "radius_from_cg_m": round(R, 4),
            "x_m": round(R * math.cos(math.radians(ang)), 4),
            "y_m": round(R * math.sin(math.radians(ang)), 4),
            "z_m": None,
            "clasificacion": "I",
            "nota": "hipotesis de configuracion X regular; posicion real pendiente de medicion (D)",
        })
    return out


def build(uav: str, d: dict) -> tuple[dict, list[str], dict]:
    errores: list[str] = []
    avisos: list[str] = []
    import math

    # --- MODELO GEOMETRICO CANDIDATO (prueba de consistencia) -----------------------
    # 'Distancia diagonal entre ejes' (specs DJI) se interpreta como D_axis: distancia entre
    # los EJES de rotores opuestos. Con planta cuadrada, el lado entre ejes adyacentes vale
    # D_axis/sqrt(2) y el alcance desplegado de las helices valdria
    #     span_candidato = D_axis/sqrt(2) + D_rotor
    # PRUEBA DE CONSISTENCIA contra las dimensiones desplegadas oficiales:
    #   T25P: 2663 vs 2650 mm (+0.5 %)   T100: 3222 vs 3220 mm (+0.05 %)   <- coinciden
    #   T55 : 3283 vs 3190 mm (+2.9 %)   T70P: 3299 vs 3175/3200 mm (+3.1..3.9 %) <- NO coinciden
    # NO es una identidad geometrica general ni una relacion descubierta: con 4 plataformas,
    # 2 coincidencias y 2 desviaciones, la evidencia no alcanza para elevarla a ley.
    # Se adopta D_axis/2 como radio al centro de rotor (hipotesis I, coherente con el no-solape).
    # Hipotesis alternativas a contrastar: geometry/protocolo_geometria.md SS7.1.
    D_axis = d["wheelbase_diagonal_mm"] / 1000.0
    R = D_axis / 2.0                       # radio del centro de la plataforma a cada eje
    d_rotor = d["rotor_diameter_m"]
    r_tip = d_rotor / 2.0
    n_arm = d["arm_count"]
    lado_entre_ejes = D_axis / math.sqrt(2.0)
    span_predicho_mm = (lado_entre_ejes + d_rotor) * 1000.0

    # --- INVARIANTE 1: los rotores vecinos no deben solaparse en el plano
    sep_vecinos = lado_entre_ejes
    margen = sep_vecinos - d_rotor
    if margen <= 0:
        errores.append(
            f"rotores vecinos solapados: separacion {sep_vecinos:.3f} m <= diametro {d_rotor:.3f} m "
            f"(wheelbase {d['wheelbase_diagonal_mm']} mm incoherente con rotor {d_rotor} m)"
        )

    # --- INVARIANTE 2: prueba de consistencia del modelo candidato contra el sobre desplegado
    dims = d["dims_desplegado_mm"]
    err_ancho = (span_predicho_mm - dims[0]) / dims[0] * 100.0
    err_largo = (span_predicho_mm - dims[1]) / dims[1] * 100.0
    if abs(err_ancho) > 1.0 and abs(err_largo) > 1.0:
        avisos.append(
            f"prueba de consistencia FALLA: span_candidato={span_predicho_mm:.0f} mm vs sobre oficial "
            f"{dims[0]}x{dims[1]} mm (err {err_ancho:+.2f} % / {err_largo:+.2f} %): "
            "el wheelbase y las dimensiones desplegadas no cierran. NO asumir error de la especificacion: "
            "contrastar las hipotesis alternativas (protocolo SS7.1) con medicion directa (A2/A8, GATE 1A)"
        )

    # --- INVARIANTE 3: coherencia de masas
    mto = d["mtow_spray_kg"]
    m_bat = d["masa_con_bateria_kg"]
    tanque = d["tank_kg"]
    if m_bat is not None:
        suma = m_bat + tanque
        if abs(suma - mto) > 1.0:
            avisos.append(
                f"masa con bateria ({m_bat}) + tanque ({tanque}) = {suma} kg != MTOW pulverizacion ({mto} kg); "
                "el tanque no puede ir completo con esta bateria (revisar configuracion de bateria)"
            )

    # --- DERIVADO (nivel 0, momentum theory): carga de disco y velocidad inducida
    n_rot = d["rotor_count_hypothesis"]
    A_total = n_rot * math.pi * r_tip ** 2
    T_hover = mto * G
    DL = T_hover / A_total                       # N/m2 por area de disco total
    v_ind = math.sqrt(T_hover / (2.0 * RHO_AIR * A_total))

    manifiesto = {
        "platform": d["nombre"],
        "schema_version": "2.0",
        "principio": "cada valor lleva clasificacion P / P-A / I / E / D y su fuente; D no se rellena con supuestos",
        "dimensiones": {
            "wheelbase_diagonal_mm": {"valor": d["wheelbase_diagonal_mm"], "clasificacion": "P",
                                      "fuente": SRC_SPECS.format(uav=uav, UAV=uav)},
            "desplegado_mm": {"valor": d["dims_desplegado_mm"],
                              "clasificacion": "P-A" if "dims_discrepancia" in d else "P",
                              "fuente": SRC_ACADEMY if "dims_discrepancia" in d else SRC_SPECS.format(uav=uav, UAV=uav),
                              "nota": d.get("dims_discrepancia")},
            "rotor_diameter_m": {"valor": d_rotor, "clasificacion": "P-A" if d.get("blade_model", "").startswith("6223") else "P",
                                 "fuente": SRC_ACADEMY,
                                 "nota": f"helice {d.get('blade_model')}" if d.get("blade_model", "").startswith("6223") else "50/62 in segun specs"},
            "blade_model_o_paso": {"valor": d.get("blade_model"), "clasificacion": "P-A" if d.get("blade_model", "").startswith("6223") else "D",
                                   "fuente": SRC_ACADEMY if d.get("blade_model", "").startswith("6223") else None},
            "blades_per_rotor": {"valor": None, "clasificacion": "D",
                                 "nota": "no declarado; tipico Agras 2 palas (I) - requiere medicion"},
            "perfil_twist_pala": {"valor": None, "clasificacion": "D", "nota": "requiere medicion/reconstruccion CAD"},
        },
        "masa": {
            "sin_bateria_kg": {"valor": d["masa_sin_bateria_kg"], "clasificacion": "P" if d["masa_sin_bateria_kg"] else "D"},
            "con_bateria_kg": {"valor": m_bat, "clasificacion": "P",
                               "valor_alternativo": d.get("masa_con_bateria_kg_alt"),
                               "discrepancia": d.get("masa_discrepancia")},
            "tanque_kg": {"valor": tanque, "clasificacion": "P"},
            "mtow_pulverizacion_kg": {"valor": mto, "clasificacion": "P"},
            "masa_total_a_carga_f": {"formula": f"{m_bat} + f*{tanque} kg  (f = fraccion de tanque)",
                                     "clasificacion": "P"},
        },
        "modelo_geometrico": {
            "tipo": "relacion geometrica CANDIDATA (prueba de consistencia, NO identidad demostrada)",
            "descripcion": "distancia diagonal entre ejes (D_axis) = separacion entre EJES de rotores opuestos",
            "lado_entre_ejes_adyacentes_m": round(lado_entre_ejes, 4),
            "radio_centro_a_eje_m": round(R, 4),
            "span_candidato_mm": round(span_predicho_mm, 1),
            "span_oficial_mm": dims,
            "error_vs_ancho_pct": round(err_ancho, 2),
            "error_vs_largo_pct": round(err_largo, 2),
            "clasificacion": "I (hipotesis de trabajo; la prueba de consistencia no la confirma en las 4 plataformas)",
            "coincide_con_el_sobre": abs(err_ancho) <= 1.0 or abs(err_largo) <= 1.0,
            "hipotesis_alternativas": "geometry/protocolo_geometria.md SS7.1",
            "nota": "NO elevar a identidad hasta que A2/A8 expliquen o descarten la desviacion (GATE 1A)",
        },
        "topologia_rotores": {
            "arm_count": {"valor": n_arm, "clasificacion": "I", "razon": "geometria y dimensiones del sobre"},
            "coaxial": {"valor": d["coaxial"], "clasificacion": "P-A" if uav == "T100" else "I",
                        "fuente": SRC_ACADEMY if uav == "T100" else None},
            "rotor_count": {"valor": None, "clasificacion": "D",
                            "hipotesis_trabajo": n_rot,
                            "conflicto": d.get("rotor_count_conflicto"),
                            "nota": "NO confirmado. Usar la hipotesis solo marcandola como tal en CFD."},
            "direccion_rotacion": {"valor": d.get("rotacion"), "clasificacion": "P-A" if d.get("rotacion") else "D",
                                   "fuente": SRC_ACADEMY if d.get("rotacion") else None},
            "posiciones_xyz": {"valor": [{"arm": a["arm_id"], "x_m": a["x_m"], "y_m": a["y_m"], "z_m": a["z_m"]}
                                         for a in rotor_xyz(d["wheelbase_diagonal_mm"], n_arm)],
                               "clasificacion": "I",
                               "nota": "plano XY hipotetico; z y posicion real pendientes de medicion (D)"},
        },
        "propulsion": {
            "motor_stator_mm": {"valor": d["motor_stator_mm"], "clasificacion": "P"},
            "motor_kv": {"valor": d["motor_kv"], "clasificacion": "P"},
            "rpm_real": {"valor": None, "clasificacion": "D",
                         "nota": "RIESGO R1. NO inferir de KV. Plan: telemetria autorizada / tachometro / camara / estimacion inversa empuje=peso"},
            "esc_peak_a": {"valor": d.get("esc_peak_a"), "clasificacion": "P-A" if d.get("esc_peak_a") else "D"},
            "empuje_declarado_kg": {"valor": d.get("empuje_brazo_kg_ambiguo") or d.get("empuje_eje_kg_ambiguo"),
                                    "clasificacion": "P-A (ambiguo)",
                                    "nota": "no se sabe si 'brazo'/'eje' = 1 rotor o el par coaxial; NO usar como salto de presion sin bancada"},
        },
        "pulverizacion": {
            "atomizers_std": {"valor": d["atomizers_std"], "clasificacion": "P"},
            "atomizers_opt": {"valor": d["atomizers_opt"], "clasificacion": "P"},
            "nozzle_spacing_mm": {"valor": d["nozzle_spacing_mm"], "clasificacion": "P"},
            "disposicion": {"valor": "cuatro boquillas TRASERAS sobre barra" if uav == "T100" else "pendiente de medicion",
                            "clasificacion": "P-A" if uav == "T100" else "D"},
            "posiciones_xyz": {"valor": None, "clasificacion": "D",
                               "nota": "CRITICO para H3. Requiere medicion directa."},
            "caudal_2_Lmin": {"valor": d["flow_2_nozzle_Lmin"], "clasificacion": "P-A" if d["flow_2_nozzle_Lmin"] else "D"},
            "caudal_4_Lmin": {"valor": d["flow_4_nozzle_Lmin"], "clasificacion": "P-A" if d["flow_4_nozzle_Lmin"] else "D"},
            "presion": {"valor": None, "clasificacion": "D", "nota": "bancada"},
            "espectro_gota_um": {"valor": d["drop_um"], "clasificacion": "P-A" if uav == "T100" else "P"},
            "ancho_nominal_m": {"valor": d["swath_nominal_m"], "clasificacion": "P",
                                "nota": "ANCHO NOMINAL DE FABRICANTE. No es ancho efectivo ni interlineado."},
            "boom": d.get("boom"),
        },
        "operacion": {
            "v_max_traslado_ms": {"valor": d.get("v_max_traslado_ms"), "clasificacion": "P-A" if d.get("v_max_traslado_ms") else "D"},
            "v_ascenso_ms": {"valor": d.get("v_ascenso_ms"), "clasificacion": "P-A" if d.get("v_ascenso_ms") else "D"},
            "v_descenso_ms": {"valor": d.get("v_descenso_ms"), "clasificacion": "P-A" if d.get("v_descenso_ms") else "D"},
            "v_aplicacion_ms": {"valor": None, "clasificacion": "D", "nota": "manual de usuario o medicion"},
            "altura_aplicacion_m": {"valor": None, "clasificacion": "D", "nota": "manual de usuario o medicion"},
        },
        "derivados_nivel0": {
            "aviso": "momentum theory: solo ordenes de magnitud (context.md SS12 nivel 0). No es resultado del estudio.",
            "rho_aire_kg_m3": RHO_AIR,
            "n_rotores_hipotesis": n_rot,
            "area_disco_total_m2": round(A_total, 3),
            "carga_disco_N_m2": round(DL, 1),
            "v_inducida_hover_ms": round(v_ind, 2),
            "carga_disco_por_rotor_N_m2": round(T_hover / n_rot / (math.pi * r_tip ** 2), 1),
            "relacion_empuje_peso_declarada": (round(((d.get("empuje_brazo_kg_ambiguo") or d.get("empuje_eje_kg_ambiguo")) * n_arm / mto), 2)
                                               if (d.get("empuje_brazo_kg_ambiguo") or d.get("empuje_eje_kg_ambiguo")) else None),
        },
        "pendiente_de_medicion": [
            "numero real de rotores y de pares coaxiales",
            "posicion XYZ real de cada rotor y z del plano de rotor",
            "numero de palas y geometria de pala (cuerda, twist)",
            "RPM real en hover y en traslacion  [RIESGO R1]",
            "posicion XYZ y orientacion de cada atomizador",
            "presion de pulverizacion y espectro real de gota",
            "velocidad y altura de aplicacion",
        ],
        "validaciones": {"errores": errores, "avisos": avisos},
    }
    resumen = {
        "uav": uav,
        "wheelbase_diagonal_mm": d["wheelbase_diagonal_mm"],
        "lado_entre_ejes_adyacentes_m": round(lado_entre_ejes, 3),
        "rotor_diameter_m": d_rotor,
        "margen_no_solape_m": round(margen, 3),
        "span_predicho_mm": round(span_predicho_mm, 1),
        "span_oficial_ancho_mm": dims[0],
        "span_err_ancho_pct": round(err_ancho, 2),
        "n_rotores_hipotesis": n_rot,
        "area_disco_total_m2": round(A_total, 3),
        "carga_disco_N_m2": round(DL, 1),
        "v_inducida_hover_ms": round(v_ind, 2),
        "masa_con_bateria_kg": m_bat,
        "tanque_kg": tanque,
        "mtow_kg": mto,
        "errores": len(errores),
        "avisos": len(avisos),
    }
    return manifiesto, errores, resumen


def main() -> int:
    OUT_JSON.mkdir(parents=True, exist_ok=True)
    filas = []
    fallo = False
    print(f"rho_aire = {RHO_AIR} kg/m3 (28 C, nivel del mar)\n")
    for uav, d in PLATFORMS.items():
        man, err, res = build(uav, d)
        p = OUT_JSON / f"{uav.lower()}_geometry_manifest.json"
        p.write_text(json.dumps(man, indent=2, ensure_ascii=False), encoding="utf-8")
        filas.append(res)
        print(f"--- {uav} ---  -> {p.relative_to(ROOT)}")
        print(f"    separacion entre ejes adyacentes = {res['lado_entre_ejes_adyacentes_m']:.3f} m ; "
              f"diametro rotor = {res['rotor_diameter_m']:.3f} m ; margen no-solape = {res['margen_no_solape_m']:+.3f} m")
        print(f"    span predicho = {res['span_predicho_mm']:.0f} mm vs oficial {res['span_oficial_ancho_mm']} mm "
              f"({res['span_err_ancho_pct']:+.2f} %)")
        print(f"    area disco total = {res['area_disco_total_m2']:.3f} m2 ; "
              f"carga disco = {res['carga_disco_N_m2']:.1f} N/m2 ; v_inducida hover = {res['v_inducida_hover_ms']:.2f} m/s")
        for e in err:
            fallo = True
            print(f"    ERROR: {e}")
        for a in man["validaciones"]["avisos"]:
            print(f"    AVISO: {a}")

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0].keys()))
        w.writeheader()
        w.writerows(filas)
    print(f"\nResumen -> {OUT_CSV.relative_to(ROOT)}")
    if fallo:
        print("\nFALLO: hay invariantes geometricas violadas. Revisar antes de mallar.")
        return 1
    print("\nOK: sin violaciones de invariantes geometricas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
