# Cómo ejecutar CFD-0 desde tu terminal

**El diagnóstico anterior era erróneo.** Decía "este entorno no tiene OpenFOAM". Es **falso**:
lo que falla es el **acceso del agente a WSL**, no la instalación. Verificado desde tu terminal:

```text
WSL:          Ubuntu 2, disponible
Instalación:  /usr/lib/openfoam/openfoam2412     ← NO en /opt
Comando:      openfoam2412                        → abre shell de sesión OpenFOAM
Build:        _b8cf4d35-20260127 (patch=260127)
python3:      /usr/bin/python3 (3.14.4)          ← disponible
mpirun:       /usr/bin/mpirun                    ← disponible
```

---

## ⚠ Dos bugs encontrados al ejecutar por primera vez (ya corregidos)

**1. `source .../etc/bashrc` dentro de un script corta la ejecución.**
Al correr `verify_cfd_prereqs.sh` desde una shell sin entorno, el script **moría en silencio**
justo en `-- 2. Entorno OpenFOAM`. El `bashrc` de OpenFOAM está pensado para una shell
**interactiva** (imprime banner y termina el proceso). Mis tres `.sh` lo hacían y se cortaban.

→ **Corregido:** los `.sh` ya **no** hacen `source`. Si el entorno no está cargado, **abortan con
instrucciones claras** en vez de morir en silencio. Nuevo lanzador `scripts/foam_run.py` que
construye el entorno **sin** hacer `source` dentro del script.

**2. `wsl -d Ubuntu` no funciona desde dentro de WSL.** Ese comando es de PowerShell. Dentro de
Ubuntu se usa `bash -lc`.

---

## Secuencia de ejecución

### Opción A — con el lanzador (recomendada, no depende de `source`)

Desde **dentro de WSL**, en la raíz del proyecto:

```bash
cd /mnt/c/Users/Dimasur/Downloads/AUTOMATIONS/DRONEWITH
python3 scripts/foam_run.py check                       # diagnóstico
python3 scripts/foam_run.py bash scripts/gate_cfd0.sh   # gate CFD-0
```

### Opción B — cargando el entorno a mano

```bash
cd /mnt/c/Users/Dimasur/Downloads/AUTOMATIONS/DRONEWITH
source /usr/lib/openfoam/openfoam2412/etc/bashrc        # en tu shell, no en un script
bash scripts/verify_cfd_prereqs.sh
bash scripts/gate_cfd0.sh
```

### Desde PowerShell, todo en una línea

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/c/Users/Dimasur/Downloads/AUTOMATIONS/DRONEWITH && python3 scripts/foam_run.py bash scripts/gate_cfd0.sh"
```

---

## Punto de partida ya verificado

Tu ejecución de `verify_cfd_prereqs.sh` confirmó todo lo esencial **antes** de cortarse:

| Comprobación | Resultado |
|---|---|
| `blockMesh` | ✅ `/usr/lib/openfoam/openfoam2412/platforms/linux64GccDPInt32Opt/bin/` |
| `checkMesh`, `topoSet`, `simpleFoam` | ✅ |
| **`python3`** | ✅ **3.14.4** |
| `mpirun` | ✅ |
| `awk`, `sort`, `cut`, `find`, `ls` | ✅ |

Lo único que falló fue **el directorio de trabajo** (estabas en `/mnt/c/Users/Dimasur`, un nivel
arriba), y esa comprobación funcionó como debía: falló con un mensaje explícito en vez de dar
resultados silenciosamente erróneos.

---

## Qué mirar en la salida del gate

| Criterio | Qué significa si falla |
|---|---|
| `checkMesh` no dice "Mesh OK" | la malla no es apta; ajustar `blockMeshDict` |
| `topoSet` no crea `cellZone rotorN` | los discos no existen: `fvOptions` no hará nada |
| el solver aborta | revisar `log.simpleFoam`; suele ser BC o esquema |
| **"SIGNO INVERTIDO"** | el downwash va hacia arriba. **El error más silencioso**: el solver converge igual. `diskDir` en `constant/fvOptions` |
| **"el perfil es CONSTANTE"** | el disco no actúa: `actuationDiskSource` no se aplica |
| magnitud fuera de un factor 5 | revisar empuje prescrito o `diskArea` |
| falta `postProcessing/<fo>` | los `function objects` no se ejecutaron |

---

## Si algo falla, tráeme esto

1. Salida completa de `python3 scripts/foam_run.py check`
2. Salida del gate hasta el primer fallo
3. Si el solver abortó: últimas 30 líneas de `cfd/cases/<caso>/log.simpleFoam`

---

## Lo que sigue, en orden

```
foam_run.py check  →  gate_cfd0.sh  →  (si pasa) escalar a los 128
                                    →  (después) módulo Lagrangiano
```

El gate y el runner **no se han podido probar desde el agente** (WSL y `bash` bloqueados en esa
sesión). Están escritos para funcionar en tu terminal, pero **hasta que los corras no están
verificados**.

