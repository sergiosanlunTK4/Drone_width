# Modelo Geométrico 3D y Coordenadas CFD — DJI Agras T100

Este directorio contiene la geometría tridimensional de alta fidelidad y el catálogo completo de coordenadas del dron agrícola **DJI Agras T100**, modelado específicamente para análisis de aerodinámica (CFD), campo de downwash e inyección y deposición lagrangiana de gotas (deriva y distribución de pulverización).

---

## 1. Archivos en este Directorio

| Archivo | Tipo / Formato | Descripción y Uso en CFD |
|---|---|---|
| [`t100_cfd_coordinates.json`](file:///c:/Users/Dimasur/Downloads/AUTOMATIONS/DRONEWITH/geometry/models/T100_CFD/t100_cfd_coordinates.json) | JSON Maestro | Catálogo completo de coordenadas XYZ, vectores normales y de empuje, especificaciones de atomizadores, espectro de gota y metrología. |
| [`t100_airframe.stl`](file:///c:/Users/Dimasur/Downloads/AUTOMATIONS/DRONEWITH/geometry/models/T100_CFD/t100_airframe.stl) | STL Binario | Superficies sólidas impermeables (`wall` sin deslizamiento): fuselaje, tanque de 100 L, brazos tubulares, tren de aterrizaje, barra trasera LS100 y carcasas de atomizadores. |
| [`t100_airframe_ascii.stl`](file:///c:/Users/Dimasur/Downloads/AUTOMATIONS/DRONEWITH/geometry/models/T100_CFD/t100_airframe_ascii.stl) | STL ASCII | Versión ASCII de la estructura sólida del dron. |
| [`t100_rotor_disks.stl`](file:///c:/Users/Dimasur/Downloads/AUTOMATIONS/DRONEWITH/geometry/models/T100_CFD/t100_rotor_disks.stl) | STL Binario | 8 volúmenes cilíndricos cerrados correspondientes al barrido de los rotores (discos actuadores para `topoSet` / `cellZone` en OpenFOAM o Ansys Fluent). |
| [`t100_rotor_disks_ascii.stl`](file:///c:/Users/Dimasur/Downloads/AUTOMATIONS/DRONEWITH/geometry/models/T100_CFD/t100_rotor_disks_ascii.stl) | STL ASCII | Versión ASCII de los 8 discos actuadores. |
| [`t100_spray_nozzles.stl`](file:///c:/Users/Dimasur/Downloads/AUTOMATIONS/DRONEWITH/geometry/models/T100_CFD/t100_spray_nozzles.stl) | STL Binario | Discos marcadores de la posición de eyección de los 4 atomizadores centrífugos. |
| [`t100_spray_nozzles_ascii.stl`](file:///c:/Users/Dimasur/Downloads/AUTOMATIONS/DRONEWITH/geometry/models/T100_CFD/t100_spray_nozzles_ascii.stl) | STL ASCII | Versión ASCII de las boquillas de atomización. |
| [`t100_full_assembly.stl`](file:///c:/Users/Dimasur/Downloads/AUTOMATIONS/DRONEWITH/geometry/models/T100_CFD/t100_full_assembly.stl) | STL Binario | Ensamblaje completo unificado (fuselaje + rotores + aspersores) para visualización en Paraview o mallado conjunto. |
| [`t100_geometry_verification.png`](file:///c:/Users/Dimasur/Downloads/AUTOMATIONS/DRONEWITH/geometry/models/T100_CFD/t100_geometry_verification.png) | Imagen PNG | Gráfico de verificación ortográfica multieje (Planta XY, Perfil XZ, Alzado YZ y ficha técnica). |

---

## 2. Sistema de Coordenadas de Referencia

Convención aeronáutica de mano derecha (estándar SAE / CFD):
- **Origen $(0, 0, 0)$:** Centro geométrico del chasis en el plano medio de los tubos de los brazos de carbono.
- **Eje $+X$:** Hacia adelante (dirección de avance en vuelo).
- **Eje $+Y$:** Hacia estribor / derecha del dron.
- **Eje $+Z$:** Vertical hacia arriba (opuesto a la gravedad y al downwash descendente).

---

## 3. Tabla Maestra de Coordenadas 3D

### A. Rotores y Discos Actuadores (8 Rotores — 4 Pares Coaxiales)
- **Hélice:** 6223 (Diámetro 62 pulgadas = 1.5748 m, Radio = 0.7874 m, Paso = 23 pulgadas).
- **Separación axial coaxial:** $\Delta Z = 0.290\text{ m}$ ($290\text{ mm}$).
- **Espesor de disco actuador:** $0.040\text{ m}$ ($40\text{ mm}$).

| Rotor ID | Brazo | Nivel | $X$ (m) | $Y$ (m) | $Z$ (m) | Rotación | Vector Normal | Vector Empuje Hover |
|---|---|---|---|---|---|---|---|---|
| `M1_FR_upper` | Frontal Der. (M1) | Superior | $+0.8238$ | $+0.8238$ | $+0.1450$ | CCW | $[0, 0, +1]$ | $[0, 0, -1]$ |
| `M1_FR_lower` | Frontal Der. (M1) | Inferior | $+0.8238$ | $+0.8238$ | $-0.1450$ | CW | $[0, 0, +1]$ | $[0, 0, -1]$ |
| `M2_RR_upper` | Trasero Der. (M2) | Superior | $-0.8238$ | $+0.8238$ | $+0.1450$ | CW | $[0, 0, +1]$ | $[0, 0, -1]$ |
| `M2_RR_lower` | Trasero Der. (M2) | Inferior | $-0.8238$ | $+0.8238$ | $-0.1450$ | CCW | $[0, 0, +1]$ | $[0, 0, -1]$ |
| `M3_RL_upper` | Trasero Izq. (M3) | Superior | $-0.8238$ | $-0.8238$ | $+0.1450$ | CCW | $[0, 0, +1]$ | $[0, 0, -1]$ |
| `M3_RL_lower` | Trasero Izq. (M3) | Inferior | $-0.8238$ | $-0.8238$ | $-0.1450$ | CW | $[0, 0, +1]$ | $[0, 0, -1]$ |
| `M4_FL_upper` | Frontal Izq. (M4) | Superior | $+0.8238$ | $-0.8238$ | $+0.1450$ | CW | $[0, 0, +1]$ | $[0, 0, -1]$ |
| `M4_FL_lower` | Frontal Izq. (M4) | Inferior | $+0.8238$ | $-0.8238$ | $-0.1450$ | CCW | $[0, 0, +1]$ | $[0, 0, -1]$ |

### B. Sistema de Pulverización (4 Atomizadores Centrífugos LX07550SX)
- **Barra de pulverización:** Modelo LS100 (barra trasera).
- **Separación exterior (N1–N4):** $1834.0\text{ mm}$ ($Y = \pm 0.9170\text{ m}$).
- **Separación interior (N2–N3):** $917.0\text{ mm}$ ($Y = \pm 0.4585\text{ m}$).
- **Caudal nominal:** $10.0\text{ L/min}$ por boquilla ($40.0\text{ L/min}$ total) $= 1.667 \times 10^{-4}\text{ m}^3\text{/s}$.
- **Régimen de giro del disco:** Hasta $14\,000\text{ RPM}$ ($v_{\text{tangencial}} = 73.3\text{ m/s}$).
- **Espectro de gota:** $D_{10} = 50\,\mu\text{m}$, $D_{50} = 150\,\mu\text{m}$, $D_{90} = 300\,\mu\text{m}$ (Rango: $10 - 500\,\mu\text{m}$).

| Boquilla ID | Rol / Posición | $X$ (m) | $Y$ (m) | $Z$ (m) | Vector Inyección | Caída bajo brazos (m) | Caída bajo rotor inf. (m) | Despeje suelo (m) |
|---|---|---|---|---|---|---|---|---|
| `N1_left_outer` | Izquierda Exterior | $-0.8750$ | $-0.9170$ | $-0.4480$ | $[0, 0, -1]$ | $0.4480$ | $0.3030$ | $0.1770$ |
| `N2_left_inner` | Izquierda Interior | $-0.7750$ | $-0.4585$ | $-0.4480$ | $[0, 0, -1]$ | $0.4480$ | $0.3030$ | $0.1770$ |
| `N3_right_inner` | Derecha Interior | $-0.7750$ | $+0.4585$ | $-0.4480$ | $[0, 0, -1]$ | $0.4480$ | $0.3030$ | $0.1770$ |
| `N4_right_outer` | Derecha Exterior | $-0.8750$ | $+0.9170$ | $-0.4480$ | $[0, 0, -1]$ | $0.4480$ | $0.3030$ | $0.1770$ |

---

## 4. Guía de Implementación en CFD (OpenFOAM / Fluent)

### 1. Mallado con `snappyHexMesh`
En el diccionario `system/snappyHexMeshDict`:
```cpp
geometry
{
    t100_airframe.stl
    {
        type triSurfaceMesh;
        name airframe;
    }
    t100_rotor_disks.stl
    {
        type triSurfaceMesh;
        name rotor_disks;
    }
}
```

### 2. Discos Actuadores con `fvOptions`
Para simular el empuje y downwash de los 8 rotores mediante momentum theory:
```cpp
rotorSources
{
    type            actuationDiskSource;
    active          true;
    selectionMode   cellZone;
    cellZone        rotor_disks;
    diskDir         (0 0 -1);       // Downwash hacia abajo (-Z)
    Cp              0.0;
    Ct              0.80;           // Coeficiente de empuje calibrado
    diskArea        15.5823;        // Área acumulada de los 8 discos
}
```

### 3. Inyección Lagrangiana para Deposición de Gotas
En el módulo de partículas (`sprayFoam`, `coalChemistryFoam`, o `simpleFoam` acoplado con DPM):
- **Tipo de inyector:** `coneInjection` o inyector de película/disco centrífugo con velocidad radial tangencial $73.3\text{ m/s}$.
- **Posiciones de inyección:** Utilizar exactamente las 4 coordenadas $(X, Y, Z)$ de la tabla B.
- **Distribución de tamaños:** Rosin-Rammler con $d_{50} = 150\,\mu\text{m}$, parámetro de dispersión $n = 2.4$, corte en $10\,\mu\text{m}$ y $500\,\mu\text{m}$.
