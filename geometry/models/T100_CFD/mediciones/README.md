# Mediciones fotogramétricas — T100 (clase S)

Medidas tomadas sobre imágenes oficiales DJI, sin cota física. Son más fuertes que una inferencia (I), pero no sustituyen una medición directa (M).

| Archivo | Contenido |
|---|---|
| `mediciones_inclinacion_t100.csv` | Inclinación de las columnas motor/atomizador: componente lateral o longitudinal, incertidumbre y n.º de puntos. Generado por `scripts/agras_model/fotogrametria/medir_inclinacion.py t100`. No existe para el T55, que no tiene vista limpia. |
| `recortes/` | Recortes con rejilla de píxeles de los que se leyeron las cotas de `scripts/agras_model/platforms/t100.py`, más las imágenes de depuración. |
| `_build.log` | Registro de la última construcción en FreeCAD. |

Herramientas en `scripts/agras_model/fotogrametria/`: `crop.py` (recorte con rejilla), `hubs.py` (mosaico ampliado de bujes), `prop_radius.py` (radio de hélice desde las puntas naranjas), `chord.py` (cuerda de la pala), `contact.py` (hojas de contacto) y `medir_inclinacion.py`.

Para pasar a clase M: inclinómetro sobre la cara de la campana del motor (o perpendicular al brazo), altura del disco del atomizador sobre el suelo y posición XY de los atomizadores. Los valores van a `data/raw/mediciones_geometria.csv`.
