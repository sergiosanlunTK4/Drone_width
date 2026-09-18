"""
Anade a los manifiestos geometricos la evidencia visual extraida de los PPTX de DJI Academy.

Motivo: las imagenes de las presentaciones documentan la CONFIGURACION (numero de brazos,
coaxialidad, palas por rotor, montaje del atomizador). Eso es evidencia documental visual,
que es mas fuerte que una inferencia pero NO es una medicion.

Nueva categoria introducida en el esquema:
  S = evidencia documental visual (imagen de una fuente oficial con pie de foto inequivoco)

Reglas que se aplican:
  1. Un valor respaldado por evidencia visual se eleva de I a S. NUNCA a M.
  2. De una fotografia SIN escala ni cota NO se derivan dimensiones. Solo se registran
     hechos discretos y cualitativos: numero de brazos, presencia de par coaxial,
     numero de palas, posicion relativa del atomizador.
  3. La evidencia S se cita con el archivo exacto y la diapositiva, de modo que un revisor
     pueda verificarla de forma independiente.

Uso:
  python scripts/annotate_manifests_with_media_evidence.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAN_DIR = ROOT / "geometry" / "manifests"
SRC = "data/raw/dji_academy_01_conocimiento_basico.txt (DJI Academy, deck 01)"

# Evidencia visual por plataforma. Cada entrada cita archivo extraido y diapositiva.
EVIDENCIA = {
    "T25P": {
        "slide": 12,
        "archivo": "data/raw/media/01a_conocimiento_basico/p12_24b31615128a.png",
        "muestra": "vista completa de la aeronave (perfil) y panel de caracteristicas",
        "corrobora": ["dimensiones desplegadas 2650x2700x820 mm", "distancia entre ejes maxima 1970 mm (diagonales)",
                      "peso 26 kg sin bateria / 32,8 kg con bateria", "MTOW pulverizacion 52,8 kg"],
        "observa": "configuracion de 4 brazos sin par coaxial (helicoptero convencional de 4 rotores)",
        "no_permite": "obtener cotas: la imagen no tiene escala ni cota",
    },
    "T25P_rotor_detalle": {
        "slide": 12,
        "archivo": "data/raw/media/01a_conocimiento_basico/p12_9bf0ba34ec84.png",
        "muestra": "panel de 4 detalles: 'Power System', 'Safety System', 'Spraying System', 'Spreading System'",
        "observa": "el motor lleva impreso '10028/59KV', que coincide con la especificacion publica "
                   "estator 100x28 mm y KV 59; el rotor muestra 2 PALAS; el atomizador aparece montado "
                   "por debajo del plano del brazo/rotor",
        "no_permite": "obtener cotas ni la separacion exacta atomizador-rotor",
    },
    "T55": {
        "slide": None,
        "archivo": None,
        "muestra": "NO LOCALIZADO en el deck 01",
        "observa": "el deck 01 se centra en T100, T70P y T25P; no se hallo una seccion propia del T55",
        "no_permite": "nada; el T55 sigue requiriendo medicion o busqueda en otro deck",
    },
    "T70P": {
        "slide": 11,
        "archivo": "data/raw/media/01a_conocimiento_basico/p11_be434fb85503.png",
        "muestra": "vista general de la aeronave (3/4 frontal) y detalle de rotor",
        "observa": "cada uno de los 4 brazos porta DOS helices en configuracion COAXIAL (superior e inferior, "
                   "con separacion axial visible) => 8 rotores; el detalle de rotor muestra 2 PALAS y "
                   "abrazadera de helice oscilante",
        "no_permite": "medir la separacion axial del par ni las cotas de brazo",
    },
    "T70P_rotor_detalle": {
        "slide": 11,
        "archivo": "data/raw/media/01a_conocimiento_basico/p11_d47e77a40e3b.jpeg",
        "muestra": "primer plano del conjunto helice-motor",
        "observa": "2 PALAS por rotor, con abrazadera oscilante (mecanismo exclusivo del T70P segun el texto); "
                   "el motor lleva reflector/etiqueta de superficie caliente",
        "no_permite": "cotas; requiere medicion directa",
    },
    "T100": {
        "slide": 10,
        "archivo": "data/raw/media/01a_conocimiento_basico/p10_cd92d5aa34e1.png",
        "muestra": "vista general (3/4 superior) del T100",
        "observa": "4 brazos con PAR COAXIAL por brazo (dos discos de rotor visibles por brazo) => 8 rotores; "
                   "los atomizadores (2 visibles) cuelgan por debajo y por fuera, en la parte trasera del brazo",
        "no_permite": "cotas; la perspectiva impide medir la posicion relativa al disco",
    },
    "T100_sistema_pulverizacion": {
        "slide": 45,
        "archivo": "data/raw/media/01a_conocimiento_basico/p45_63a362308218.png",
        "muestra": "conjunto de pulverizacion del T100: tanque + bastidor + brazos/varillas de pulverizacion",
        "observa": "las varillas de pulverizacion se extienden hacia atras y hacia los lados, con los "
                   "atomizadores en sus extremos, por debajo del plano del bastidor",
        "no_permite": "cotas; confirma el texto 'cuatro boquillas TRASERAS'",
    },
}

# Correcciones de topologia respaldadas por evidencia visual
TOPOLOGIA_S = {
    "T25P": {"arm_count": 4, "coaxial": False, "rotor_count": 4, "blades_per_rotor": 2,
             "clasificacion_rotor_count": "S",
             "nota": "elevado de I (hipotesis) a S (evidencia visual) por la imagen de la slide 12. "
                     "Sigue pendiente de confirmacion por medicion (M)."},
    "T55":  {"arm_count": None, "coaxial": None, "rotor_count": None, "blades_per_rotor": None,
             "clasificacion_rotor_count": "D",
             "nota": "sin evidencia visual en el deck 01; las specs DJI mencionan '4 pares de helices'. "
                     "Requiere medicion o localizacion de material propio del T55."},
    "T70P": {"arm_count": 4, "coaxial": True, "rotor_count": 8, "blades_per_rotor": 2,
             "clasificacion_rotor_count": "S",
             "nota": "elevado de I a S: la imagen de la slide 11 muestra el par coaxial en cada brazo. "
                     "Falta la separacion axial del par (D)."},
    "T100": {"arm_count": 4, "coaxial": True, "rotor_count": 8, "blades_per_rotor": 2,
             "clasificacion_rotor_count": "S",
             "nota": "elevado de I a S: par coaxial por brazo confirmado visualmente (slide 10). "
                     "CONFLICTO ABIERTO: las specs DJI dicen 'Cantidad: 8 pares' (=> 16 helices). "
                     "La imagen y el texto del deck ('helices duales coaxiales') indican 4 pares. "
                     "MEDIR Y RESOLVER antes del CFD."},
}


def main() -> int:
    for uav, topo in TOPOLOGIA_S.items():
        p = MAN_DIR / f"{uav.lower()}_geometry_manifest.json"
        if not p.exists():
            print(f"{uav}: manifiesto ausente")
            continue
        m = json.loads(p.read_text(encoding="utf-8"))

        if "evidencia_visual" in m:
            print(f"{uav}: ya anotado, no se duplica")
            continue

        # 1) nueva seccion de evidencia
        ev = []
        for clave, e in EVIDENCIA.items():
            if not clave.startswith(uav):
                continue
            ev.append({
                "clasificacion": "S",
                "fuente": SRC,
                "slide": e["slide"],
                "archivo": e["archivo"],
                "muestra": e["muestra"],
                "observa": e["observa"],
                "corrobora": e.get("corrobora"),
                "no_permite": e["no_permite"],
            })
        m["evidencia_visual"] = {
            "que_es": "evidencia documental visual (S): mas fuerte que una inferencia, NO es medicion",
            "regla": "de una fotografia sin escala o cota NO se derivan dimensiones; solo hechos discretos",
            "entradas": ev,
        }

        # 2) elevar la topologia de I a S
        rt = m["topologia_rotores"]
        if topo["rotor_count"] is not None:
            rt["rotor_count"] = {
                "valor": topo["rotor_count"],
                "clasificacion": topo["clasificacion_rotor_count"],
                "fuente": SRC,
                "nota": topo["nota"],
                "hipotesis_previa": rt["rotor_count"].get("hipotesis_trabajo"),
            }
        # conflicto abierto: se registra como campo propio, no enterrado en una nota
        nuevo_rt = {"valor": topo["coaxial"],
                    "clasificacion": "S" if topo["coaxial"] is not None else "D",
                    "fuente": SRC if topo["coaxial"] is not None else None,
                    "nota": topo["nota"]}
        conflicto_previo = rt["coaxial"].get("conflicto")
        if conflicto_previo:
            nuevo_rt["conflicto_abierto"] = conflicto_previo
        rt["coaxial"] = nuevo_rt
        if uav == "T100":
            rt["CONFLICTO_ABIERTO_rotor_count"] = {
                "descripcion": "las specs DJI dicen 'Cantidad: 8 pares' (=> 16 helices); el deck 01 "
                               "(texto 'helices duales coaxiales' + imagen de 4 brazos con un par cada uno) "
                               "indica 4 pares (=> 8 helices)",
                "estado": "ABIERTO - resolver con conteo directo (A9) antes de mallar",
                "impacto_si_se_elige_mal": "area de disco total al doble; carga de disco y velocidad "
                                           "inducida de hover desviadas ~sqrt(2); numero de discos en la malla",
                "valor_adoptado_provisionalmente": 8,
                "clasificacion": "S (provisional, no cierra GATE 1A)",
            }
        # numero de palas: pasa de D a S (evidencia visual)
        m["dimensiones"]["blades_per_rotor"] = {
            "valor": topo["blades_per_rotor"],
            "clasificacion": "S" if topo["blades_per_rotor"] else "D",
            "fuente": SRC if topo["blades_per_rotor"] else None,
            "nota": "2 palas observadas en imagen de detalle; confirmar con medicion (M)"
                    if topo["blades_per_rotor"] else "sin evidencia visual",
        }

        p.write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"{uav:5s} -> evidencia visual anadida ({len(ev)} entradas); "
              f"rotor_count={topo['rotor_count']} ({topo['clasificacion_rotor_count']}), "
              f"coaxial={topo['coaxial']}, palas={topo['blades_per_rotor']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
