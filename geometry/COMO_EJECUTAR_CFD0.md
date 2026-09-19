# Cómo ejecutar CFD-0 desde tu terminal

**El diagnóstico anterior era erróneo.** Decía "este entorno no tiene OpenFOAM". Es **falso**:
lo que falla es el **acceso del agente a WSL**, no la instalación. Verificado desde tu terminal:

```text
WSL:          Ubuntu 2, disponible
Instalación:  /usr/lib/openfoam/openfoam2412     ← NO en /opt
Comando:      openfoam2412                        → abre shell de sesión OpenFOAM
Build:        _b8cf4d35-20260127 (patch=260127)
```

El build **coincide** con el de `cfd/cases/T25P_baseline/log.snappyHexMesh`, así que es la misma
instalación que ya generó esa malla. **OpenFOAM funciona.**

---

## Secuencia de ejecución

### Paso 1 — entrar a WSL y cargar el entorno

```powershell
wsl -d Ubuntu
```

Dentro de Ubuntu:

```bash
openfoam2412
```

Ese comando abre una **shell de sesión** de OpenFOAM (verás el prompt `openfoam2412:...`).

> **¿Por qué no basta con `wsl -d Ubuntu`?** Porque en una shell **no interactiva** —y también
> en una interactiva recién abierta— el entorno de OpenFOAM **no está cargado**:
> `foamVersion` da "command not found". Eso es lo que te hizo dudar de la instalación.
> Los scripts del proyecto **ya cargan el entorno solos** con
> `source /usr/lib/openfoam/openfoam2412/etc/bashrc`, así que si los lanzas desde una shell
> limpia también funcionan.

### Paso 2 — ir al proyecto

```bash
cd /mnt/c/Users/Dimasur/Downloads/AUTOMATIONS/DRONEWITH
pwd
ls scripts/gate_cfd0.sh
```

### Paso 3 — verificar prerequisitos (esto va ANTES del gate)

```bash
bash scripts/verify_cfd_prereqs.sh
```

Comprueba, sin asumir nada: entorno OpenFOAM, los cinco ejecutables, **`python3`** y las
herramientas auxiliares, la ruta del proyecto y la elección del caso T25P.

> ⚠ **Punto que puede fallar:** `postprocess_case.py` y `check_cfd0_evidence.py` necesitan
> **`python3`**, y en tu salida `which python3` no apareció. Si falta:
> ```bash
> sudo apt update && sudo apt install -y python3
> ```

### Paso 4 — lanzar el smoke test

```bash
bash scripts/gate_cfd0.sh
```

Corre la secuencia sobre **un solo caso** (el T25P más cercano a V=5 m/s, H=3 m, d=200 µm):
`blockMesh → checkMesh → topoSet → simpleFoam 300 iter → evidencia del disco → function objects → postprocess`.

Al terminar dice cuántos criterios se cumplieron. **Si alguno falla, no se escala a los 128.**

---

## Qué mirar en la salida

| Criterio | Qué significa si falla |
|---|---|
| `checkMesh` no dice "Mesh OK" | la malla no es apta; ajustar `blockMeshDict` |
| `topoSet` no crea `cellZone rotorN` | los discos no existen: `fvOptions` no hará nada |
| el solver aborta | revisar `log.simpleFoam`; suele ser BC o esquema |
| **"SIGNO INVERTIDO"** | el downwash va hacia arriba. **El error más silencioso**: el solver converge igual. Corregir `diskDir` en `constant/fvOptions` |
| **"el perfil es CONSTANTE"** | el disco no actúa: `actuationDiskSource` no se está aplicando |
| magnitud fuera de un factor 5 | revisar empuje prescrito o `diskArea` |
| falta `postProcessing/<fo>` | los `function objects` no se ejecutaron |

---

## Si algo falla, tráeme esto

1. La salida completa de `verify_cfd_prereqs.sh`
2. La salida del gate hasta el primer fallo
3. Si el solver abortó: las últimas 30 líneas de `cfd/cases/<caso>/log.simpleFoam`

Con eso ajusto el caso y volvemos a intentar. **No hay que cambiar código antes de esta prueba.**

---

## Lo que sigue, en orden

```
verify_cfd_prereqs.sh  →  gate_cfd0.sh  →  (si pasa) escalar a los 128
                                          →  (después) módulo Lagrangiano
```

El gate y el runner **no se han podido probar desde el agente** (WSL y `bash` están bloqueados
en esa sesión). Están escritos para funcionar en tu terminal, pero **hasta que los corras no están
verificados** — y así queda declarado en el protocolo.
