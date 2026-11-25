"""
Adaptador geometria v2 -> generador de casos CFD.

Lee `geometry/models/<P>_CFD/<p>_cfd_coordinates.json` (la FUENTE DE VERDAD de los casos,
INSTRUCCIONES_CFD.md §1) y lo expone en una forma estable para los scripts de casos
(build_case_suite.py, build_hover_case.py, build_prescribed_momentum.py, run_queue.py).

Sustituye a:
  - la planta "regular X" de `build_case_suite.rot_centers` (hipotesis I, retirada);
  - la bandera `coaxial` codificada a mano (T55 y T70P NO son coaxiales; solo el T100);
  - `diskDir (0 0 -1)`: cada rotor tiene su `disk_normal` inclinado (cant a lo largo del brazo).

Python puro, sin numpy; se puede importar desde Windows y desde WSL.

Terna: +X adelante, +Y izquierda (babor), +Z arriba, dextrogira. Metros.

Uso como script (resumen y autocomprobacion):
    python scripts/agras_model/cfd_geometry.py            # las 4 plataformas
    python scripts/agras_model/cfd_geometry.py T70P
"""
from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODELS = ROOT / "geometry" / "models"

PLATAFORMAS = ("T25P", "T55", "T70P", "T100")

# Caudal maximo de bomba [L/min] con 2 / 4 aspersores.
# P (fichas DJI) salvo el T55, que es del propietario (O, 2026-11-22). INSTRUCCIONES_CFD §5.5.
CAUDAL_MAX_LMIN = {
    "T25P": {2: (16.0, "P"), 4: (24.0, "P")},
    "T55":  {2: (40.0, "O"), 4: (50.0, "O")},
    "T70P": {2: (30.0, "P"), 4: (40.0, "P")},
    "T100": {2: (30.0, "P"), 4: (40.0, "P")},
}

# Velocidad maxima de trabajo [m/s] (propietario, 2026-11-22, clase O).
V_MAX_MS = {"T25P": 10.0, "T55": 20.0, "T70P": 20.0, "T100": 20.0}


@dataclass(frozen=True)
class Rotor:
    rotor_id: str
    nivel: str                      # "simple" | "upper" | "lower"
    brazo: str
    centro: tuple                   # (x, y, z) m
    normal: tuple                   # disk_normal: direccion del empuje SOBRE EL UAV (unitario)
    omega_unit: tuple               # angular_velocity_unit_vector
    giro_desde_arriba: str          # "CW" | "CCW"
    radio_m: float
    area_m2: float
    espesor_m: float
    palas: int
    stl_region: str                 # nombre de la region en <p>_rotor_disks.stl

    def extremos_cilindro(self, espesor: float | None = None) -> tuple[tuple, tuple]:
        """p1, p2 = centro -/+ (h/2)*normal, para `cylinderToCell` inclinado."""
        h = self.espesor_m if espesor is None else espesor
        c, n = self.centro, self.normal
        p1 = tuple(c[i] - 0.5 * h * n[i] for i in range(3))
        p2 = tuple(c[i] + 0.5 * h * n[i] for i in range(3))
        return p1, p2

    def fuerza_sobre_aire(self, T: float) -> tuple:
        """F_i = -T_i * disk_normal_i  (la reaccion del empuje, empuja el aire 'hacia abajo')."""
        return tuple(-T * c for c in self.normal)


@dataclass(frozen=True)
class Boquilla:
    nozzle_id: str
    configuracion: str              # "estandar" | "opcional"
    centro: tuple                   # disc_center_xyz_m
    eje: tuple                      # disc_axis
    radio_disco_m: float
    altura_sobre_suelo_m: float
    montaje: str
    clasificacion: str


@dataclass
class Plataforma:
    clave: str
    nombre: str
    version_modelo: str
    coaxial: bool
    rotores: list
    boquillas: list
    z_suelo_modelo: float           # ground_plane_z_m (contacto de los patines)
    masa_vacio_kg: float            # con bateria, sin liquido
    tanque_kg: float
    mtow_kg: float
    masa_fuente: dict = field(default_factory=dict)
    dir_modelo: Path = None
    prefijo: str = ""

    # ---------------------------------------------------------------- archivos
    @property
    def stl_airframe(self) -> Path:
        return self.dir_modelo / f"{self.prefijo}_airframe.stl"

    @property
    def stl_rotor_disks(self) -> Path:
        return self.dir_modelo / f"{self.prefijo}_rotor_disks.stl"

    @property
    def stl_nozzles(self) -> Path:
        return self.dir_modelo / f"{self.prefijo}_spray_nozzles.stl"

    # ---------------------------------------------------------------- fisica
    def masa(self, f: float) -> float:
        """m(f) = m_vacio + f * tanque  (f = fraccion de carga 0..1; agua, 1 kg/L)."""
        return self.masa_vacio_kg + f * self.tanque_kg

    def boquillas_activas(self, n: int) -> list:
        """2 = estandar; 4 = estandar + opcional."""
        if n == 2:
            return [b for b in self.boquillas if b.configuracion == "estandar"]
        if n == 4:
            return list(self.boquillas)
        raise ValueError("configuracion de atomizadores: 2 o 4")

    def reparto_empuje(self, T_total: float, split_superior: float = 0.5) -> list:
        """Empuje por rotor [N], mismo orden que `self.rotores`.

        Hover / sin trim de momentos: reparto igual por brazo (la cadena C completa con
        momentos esta en scripts/force_chain.py). Coaxial: `split_superior` es la fraccion
        del empuje del brazo en el rotor SUPERIOR, PARAMETRO barrido (0.5/0.6/0.7), no supuesto.
        """
        brazos = sorted({r.brazo for r in self.rotores})
        T_brazo = T_total / len(brazos)
        out = []
        for r in self.rotores:
            if r.nivel == "simple":
                out.append(T_brazo)
            elif r.nivel == "upper":
                out.append(T_brazo * split_superior)
            elif r.nivel == "lower":
                out.append(T_brazo * (1.0 - split_superior))
            else:
                raise ValueError(f"nivel de rotor desconocido: {r.nivel}")
        return out

    def area_momentum_m2(self) -> float:
        """Area para momentum theory: en coaxial, los pares comparten estela (4 discos)."""
        if self.coaxial:
            return sum(r.area_m2 for r in self.rotores if r.nivel == "upper")
        return sum(r.area_m2 for r in self.rotores)

    def v_inducida_hover(self, masa_kg: float, rho: float = 1.1716, g: float = 9.80665) -> float:
        return math.sqrt(masa_kg * g / (2.0 * rho * self.area_momentum_m2()))

    def resumen(self) -> dict:
        d = asdict(self)
        d["dir_modelo"] = str(self.dir_modelo.relative_to(ROOT)).replace("\\", "/")
        return d


# --------------------------------------------------------------------------------------
def _masas(m: dict) -> tuple[float, float, float, dict]:
    """Las claves de `mass` varian por plataforma; se normalizan aqui, con su origen."""
    vacio = next((v for k, v in m.items() if k.startswith("con_bateria")
                  or k.startswith("pulverizacion_2boq")), None)
    tanque = m.get("tanque_kg")
    mtow = next((v for k, v in m.items() if k.startswith("mtow")), None)
    if None in (vacio, tanque, mtow):
        raise KeyError(f"no se pudo normalizar la masa: {m}")
    fuente = {"vacio": next(k for k, v in m.items() if v == vacio),
              "mtow": next(k for k, v in m.items() if v == mtow)}
    return float(vacio), float(tanque), float(mtow), fuente


def _unit(v) -> tuple:
    n = math.sqrt(sum(c * c for c in v))
    return tuple(c / n for c in v)


def cargar(clave: str) -> Plataforma:
    clave = clave.upper()
    if clave not in PLATAFORMAS:
        raise KeyError(f"plataforma desconocida: {clave!r}")
    pref = clave.lower()
    carpeta = MODELS / f"{clave}_CFD"
    j = json.loads((carpeta / f"{pref}_cfd_coordinates.json").read_text(encoding="utf-8"))

    rotores = []
    for r in j["rotors"]:
        rotores.append(Rotor(
            rotor_id=r["rotor_id"], nivel=r["level"], brazo=r["arm"],
            centro=tuple(r["center_xyz_m"]), normal=_unit(r["disk_normal"]),
            omega_unit=_unit(r["angular_velocity_unit_vector"]),
            giro_desde_arriba=r["rotation_seen_from_above"],
            radio_m=float(r["radius_m"]), area_m2=float(r["swept_area_m2"]),
            espesor_m=float(r["disk_thickness_m"]), palas=int(r["blades"]),
            stl_region=f"rotor_{r['rotor_id']}",
        ))
    boquillas = []
    for n in j["spray_system"]["nozzles"]:
        boquillas.append(Boquilla(
            nozzle_id=n["nozzle_id"], configuracion=n["configuration"],
            centro=tuple(n["disc_center_xyz_m"]), eje=_unit(n["disc_axis"]),
            radio_disco_m=float(n["disc_radius_m"]),
            altura_sobre_suelo_m=float(n["height_above_ground_m"]),
            montaje=n.get("mount", ""), clasificacion=n.get("classification", ""),
        ))
    vacio, tanque, mtow, fuente = _masas(j["mass"])
    return Plataforma(
        clave=clave, nombre=j["platform"], version_modelo=str(j["model_version"]),
        coaxial=bool(j["topology"]["coaxial"]), rotores=rotores, boquillas=boquillas,
        z_suelo_modelo=float(j["coordinate_system"]["ground_plane_z_m"]),
        masa_vacio_kg=vacio, tanque_kg=tanque, mtow_kg=mtow, masa_fuente=fuente,
        dir_modelo=carpeta, prefijo=pref,
    )


def cargar_todas() -> dict:
    return {k: cargar(k) for k in PLATAFORMAS}


# --------------------------------------------------------------------------------------
def autocomprobar(p: Plataforma) -> list[str]:
    """Comprobaciones de coherencia del JSON. Devuelve la lista de problemas (vacia = OK)."""
    prob = []
    n_esperado = 8 if p.clave == "T100" else 4
    if len(p.rotores) != n_esperado:
        prob.append(f"{len(p.rotores)} rotores, se esperaban {n_esperado}")
    if p.coaxial != (p.clave == "T100"):
        prob.append(f"coaxial={p.coaxial} no coincide con la topologia v2")
    for r in p.rotores:
        if abs(r.area_m2 - math.pi * r.radio_m ** 2) / r.area_m2 > 1e-3:
            prob.append(f"{r.rotor_id}: area != pi r^2")
        if r.normal[2] < 0.99:
            prob.append(f"{r.rotor_id}: normal poco vertical {r.normal}")
        if r.centro[2] <= p.z_suelo_modelo:
            prob.append(f"{r.rotor_id}: rotor bajo el suelo del modelo")
    # simetria izquierda/derecha de los centros (+Y babor)
    for r in p.rotores:
        espejo = [q for q in p.rotores if q.nivel == r.nivel
                  and abs(q.centro[0] - r.centro[0]) < 1e-3
                  and abs(q.centro[1] + r.centro[1]) < 1e-3
                  and abs(q.centro[2] - r.centro[2]) < 1e-3]
        if not espejo:
            prob.append(f"{r.rotor_id}: sin rotor espejo en -Y")
    # par motor de reaccion: suma de giros debe anularse (mitad CW, mitad CCW)
    cw = sum(1 for r in p.rotores if r.giro_desde_arriba == "CW")
    if cw * 2 != len(p.rotores):
        prob.append(f"giros no equilibrados: {cw} CW de {len(p.rotores)}")
    if len(p.boquillas_activas(2)) != 2 or len(p.boquillas) != 4:
        prob.append("se esperaban 2 boquillas estandar y 4 en total")
    return prob


def main(argv: list[str]) -> int:
    claves = [a.upper() for a in argv] or list(PLATAFORMAS)
    fallos = 0
    for k in claves:
        p = cargar(k)
        print(f"\n{k}  ({p.nombre}, modelo v{p.version_modelo})  coaxial={p.coaxial}  "
              f"z_suelo={p.z_suelo_modelo:+.3f} m")
        print(f"  masa: vacio {p.masa_vacio_kg} kg + tanque {p.tanque_kg} kg  (MTOW {p.mtow_kg} kg)")
        for r in p.rotores:
            print(f"  {r.rotor_id:13s} {r.nivel:6s} c=({r.centro[0]:+.3f} {r.centro[1]:+.3f} "
                  f"{r.centro[2]:+.3f})  n=({r.normal[0]:+.4f} {r.normal[1]:+.4f} {r.normal[2]:.5f})"
                  f"  {r.giro_desde_arriba:3s}  A={r.area_m2:.4f}  h={r.espesor_m}")
        for b in p.boquillas:
            print(f"  {b.nozzle_id:15s} {b.configuracion:9s} c=({b.centro[0]:+.3f} {b.centro[1]:+.3f} "
                  f"{b.centro[2]:+.3f})  eje=({b.eje[0]:+.4f} {b.eje[1]:+.4f} {b.eje[2]:.4f})")
        vi = p.v_inducida_hover(p.mtow_kg)
        print(f"  v_i hover MTOW (momentum, orden de magnitud) = {vi:.2f} m/s")
        prob = autocomprobar(p)
        print("  autocomprobacion:", "OK" if not prob else "; ".join(prob))
        fallos += bool(prob)
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
