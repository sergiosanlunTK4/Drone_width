from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.utils import simpleSplit
from reportlab.lib.pagesizes import letter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/pdf/mediciones_drones_guia_y_tablas.pdf'
W,H=letter
c=canvas.Canvas(str(OUT),pagesize=letter)
c.setTitle('DRONEWITH | Guía de medición y hojas de campo por modelo')
c.setAuthor('DRONEWITH')
page=0
y=0
def text(s,size=10,leading=14):
    global y
    c.setFont('Helvetica',size)
    for line in simpleSplit(s,'Helvetica',size,524):
        c.drawString(44,y,line);y-=leading
    y-=2
def heading(s):
    global y
    y-=5;c.setFont('Helvetica-Bold',12);c.drawString(44,y,s);y-=18
def start(title,sub):
    global page,y
    page+=1
    c.setFillColor(colors.HexColor('#183342'));c.rect(0,H-94,W,94,fill=1,stroke=0)
    c.setFillColor(colors.white);c.setFont('Helvetica-Bold',10);c.drawString(44,H-30,'DRONEWITH / CUADERNO DE CAMPO')
    c.setFont('Helvetica-Bold',19);c.drawString(44,H-57,title)
    c.setFont('Helvetica',10);c.drawString(44,H-78,sub)
    c.setFillColor(colors.black);y=H-110
def end():
    assert y>=42,(page,y)
    c.setStrokeColor(colors.grey);c.line(44,37,W-44,37)
    c.setFont('Helvetica',8);c.drawString(44,24,'19 sep 2026 | Longitudes en mm; convertir a m al transcribir | Carta, 100 %')
    c.drawRightString(W-44,24,str(page));c.showPage()
def table(headers,rows,widths,height=29):
    global y
    x=44; top=y
    c.setFillColor(colors.HexColor('#e8edf0'));c.rect(x,y-27,sum(widths),27,fill=1,stroke=0)
    for rownum,row in enumerate([headers]+rows):
        h=27 if rownum==0 else height
        xx=x
        for val,ww in zip(row,widths):
            c.setStrokeColor(colors.HexColor('#89959b'));c.rect(xx,y-h,ww,h,fill=0,stroke=1)
            c.setFillColor(colors.black);c.setFont('Helvetica-Bold' if rownum==0 else 'Helvetica',8.3)
            lines=simpleSplit(str(val),'Helvetica',8.3,ww-10)
            assert len(lines)*10<=h-5,(page,val,h)
            for j,line in enumerate(lines): c.drawString(xx+5,y-12-j*10,line)
            xx+=ww
        y-=h
    y-=12
def meta(model):
    text('Unidad / serie: __________________  Fecha y hora: __________________',10)
    text('Operador: __________________  Configuración real: __________________',10)
    text('Marco: __________________  Setup / repetición: ______  Instrumentos: ______',10)
def blank(rows):return [[r,'','',''] for r in rows]

start('Cómo medir / preparación','Aplicable a T25P, T55, T70P y T100 | Geometría estática del proyecto')
text('Objetivo: registrar medidas reales para construir la geometría de cada dron. Los espacios están vacíos a propósito: ninguna cifra nominal sustituye una medición.')
text('Base: geometry/protocolo_geometria.md, geometry/campana_T25P.md y geometry/hoja_de_campo.md del proyecto. Esta guía organiza su captura en papel.',9,12)
heading('1. Preparar y documentar')
text('Dron apagado y batería desconectada para medir geometría; brazos desplegados en posición de trabajo, equipo estable y nivelado. Registrar tanque, batería y accesorios instalados. No energizar motores para identificar su giro.')
text('Material: cinta métrica, regla/calibre, plomada o láser, nivel digital, etiquetas, cámara y báscula apropiada para la masa del conjunto. Registrar resolución y calibración de cada instrumento.')
heading('2. Marcar el origen y los ejes')
text('Marcar un origen físico O reproducible en cada unidad. +X hacia el frente, +Y hacia la izquierda del dron y +Z hacia arriba. Fotografiar origen, referencias, etiquetas y flecha +X.')
text('El proyecto propone CG_tank50 (centro de gravedad con tanque al 50 %). Si todavía no se midió ese CG, usar un marco local con nombre propio; no llamarlo CG. Conservar las coordenadas crudas y documentar después la transformación al marco del proyecto.')
table(['ID interno','Ubicación mirando hacia el frente','Signos orientativos*'],[
['R1 / FL','Delantero izquierdo','X + / Y +'],['R2 / RL','Trasero izquierdo','X - / Y +'],['R3 / RR','Trasero derecho','X - / Y -'],['R4 / FR','Delantero derecho','X + / Y -']], [95,295,134],28)
text('*Solo si O está entre los rotores. La numeración es del proyecto, no de DJI. Para coaxiales: R1 es el superior y R1_lower el inferior; igual para R2-R4. Si la topología real difiere, añadir IDs y croquis, sin forzar estas filas.',9,12)
heading('3. Repetir sin perder trazabilidad')
text('Imprimir tres copias de las hojas de geometría de cada modelo (A, B y C). Recolocar el instrumento entre mediciones y usar setups S1, S2 y S3. Cada copia registra una lectura independiente; no promediar ni reemplazar lecturas en campo.')
text('Usar N/A cuando no aplica y D cuando se desconoce. Las fotos deben mostrar el punto y la escala. Registrar incertidumbre y su tipo; si aún no se evaluó, escribir pendiente y conservar resolución y lecturas para calcularla después.',9,12)
end()

start('Cómo medir / métodos','Leer antes de completar las hojas A, B y C de cada modelo')
table(['Medición','Procedimiento y referencia'],[
['XYZ de rotor o atomizador','Proyectar con plomada el centro al plano de referencia. Medir X e Y por separado, paralelos a los ejes; Z es la altura respecto a O. No usar la distancia inclinada como coordenada.'],
['Diámetro de rotor','Con hélice desplegada y sin deformarla, medir el radio desde el eje hasta la punta más alejada: D = 2r. Registrar por rotor. No usar longitud de una pala como diámetro.'],
['Normal del rotor','Medir la inclinación del plano del disco con nivel digital en las direcciones X e Y, respecto al horizontal. Anotar signos: positivo si sube hacia +X o +Y. Conservar ángulos; derivar después la normal unitaria hacia arriba.'],
['Separación coaxial','Medir entre planos de giro superior e inferior, a lo largo del eje común. No entre carcasas de motor. Si no son paralelos o el eje no es común, registrar la diferencia y medir ambos planos.'],
['Giro y palas','Contar palas por rotor. Registrar CW (horario) o CCW (antihorario), siempre visto desde arriba hacia abajo. Confirmar con marcaje/manual identificado; si no hay evidencia, D.'],
['Atomizador y orientación','Usar el centro del disco de atomización para XYZ. Medir dos puntos P y Q del eje, con Q hacia la descarga, y registrar sus coordenadas. El vector se calcula como (Q-P)/|Q-P|. Si el eje no se identifica, D.'],
['Altura relativa al rotor','Registrar el rotor de referencia. Medir la diferencia vertical firmada entre atomizador y plano del rotor a la misma X,Y: negativa si está debajo. Con disco inclinado no restar solo alturas de los dos centros.'],
['Cotas y estructura','Medir centros de buje para distancias entre rotores; indicar si son proyecciones XY o distancias 3D. Medir cuerpo, tanque, brazos, patines y barras sin confundirlos con el alcance de las hélices.']
], [112,412],57)
text('Objetivos del piloto del proyecto: ±5 mm en centros y diámetro, ±1° en orientación. Son objetivos de medición, no incertidumbres garantizadas del instrumento.',9,12)
text('No ajustar valores para obtener simetría. Un atomizador cercano a un rotor no demuestra que quede dentro de su estela: esa relación se evalúa después.',9,12)
end()

models={
'T25P':('Piloto: comprobar 4 rotores únicos y ausencia de pares coaxiales.',False),
'T55':('Topología pendiente: contar brazos, motores y discos; confirmar o descartar coaxialidad.',True),
'T70P':('Evidencia documental: 4 brazos con pares coaxiales; medir ambos niveles por separado.',True),
'T100':('Conteo pendiente: resolver la discrepancia documental contando discos físicos y palas.',True)}
roles=['R1 / FL','R2 / RL','R3 / RR','R4 / FR']
for model,(note,coax) in models.items():
    ids=roles+([r.split(' / ')[0]+'_lower / '+r.split(' / ')[1] for r in roles] if coax else [])
    start(model+' / A. Rotores','Una hoja por setup independiente | Repetir tres veces')
    meta(model);text(note,10,13)
    text('Conteo real: brazos ____  motores ____  discos ____  Foto cenital: __________',10)
    table(['Rotor / posición','X mm','Y mm','Z mm','D mm','Palas','Giro'],[[i,'','','','','',''] for i in ids],[130,70,70,70,70,50,64],24)
    text('En coaxiales R1-R4 = superiores; _lower = inferiores. Marcar N/A si no existen.',9,12)
    table(['Rotor','Inclinación X (°)','Inclinación Y (°)','Foto / incertidumbre'],[[i,'','',''] for i in ids],[130,115,115,164],22)
    text('Plano de referencia / nivelación: ______________________________________',9,12)
    text('Instrumentos, resolución e incertidumbre por magnitud: __________________',9,12)
    if not coax:
        heading('Si aparece una configuración distinta')
        text('Fotografiar y describir: _____________________________________________')
        text('_______________________________________________________________')
    end()

    start(model+' / B. Atomizadores','Una hoja por configuración real (2 o 4) y por setup independiente')
    meta(model)
    text('Cantidad instalada ____  IDs activos __________  Foto general __________',10)
    text('Asignar A1-A4 en el croquis y mantener su identidad entre configuraciones. Medir solo configuraciones disponibles; no suponer posiciones opcionales.',9,12)
    table(['ID','X mm','Y mm','Z mm','Rotor ref.','Delta Z mm','Foto'],[[f'A{i}','','','','','',''] for i in range(1,5)],[36,72,72,72,85,88,99],26)
    heading('Orientación: dos puntos del eje (ver método, página 2)')
    table(['ID','P (X, Y, Z) mm','Q (X, Y, Z) mm','Soporte / cota al eje mm'],[[f'A{i}','','',''] for i in range(1,5)],[36,160,160,168],28)
    text('Punto efectivo de emisión: identificar y fotografiar; si difiere del centro del disco, registrar su posición. No inferir el ángulo del cono solo por la carcasa.',9,12)
    table(['ID','Emisión XYZ mm / D','Foto / método / incertidumbre'],[[f'A{i}','',''] for i in range(1,5)],[36,230,258],24)
    text('Separación centro a centro: IDs ____ a ____ = ______ mm; tipo: XY / 3D',10)
    text(('T100: registrar barras traseras, extremos XYZ, longitud y fijación en hoja C.' if model=='T100' else 'Registrar barras y soportes en hoja C; fotografiar accesorios y posiciones.'),10)
    text('Instrumentos, resolución e incertidumbre: ______________________________',9,12)
    end()

    start(model+' / C. Cotas y hélices','Una hoja por setup | Duplicar para más piezas o tipos de hélice')
    meta(model)
    text('Distancias entre bujes: indicar XY o 3D. Alcance total: declarar posición de las palas. No calcular distancias a partir de una supuesta planta cuadrada.',9,12)
    rows=['Bujes R1-R4 (delanteros)','Bujes R2-R3 (traseros)','Bujes R1-R2 (izquierda)','Bujes R4-R3 (derecha)','Diagonal R1-R3','Diagonal R4-R2','Alcance total X / Y / Z','Cuerpo central: largo / ancho / alto','Tanque: largo / ancho / alto','Brazos: ID, longitud / sección','Patines: separación / altura','Barras: ID, longitud / extremos XYZ','Plano de rotor al cuerpo: ID / cota']
    if coax:rows+=['Separación axial R1 / R2 (por par)','Separación axial R3 / R4 (por par)']
    table(['Magnitud / componente','Lectura (mm)','Foto / referencia'],[[r,'',''] for r in rows],[240,134,150],21)
    text('En cada pieza registrar posición y orientación mediante croquis/fotos con cotas. Si faltan filas, añadir hoja con el mismo modelo, marco y setup.',9,12)
    heading('Hélice: identificar cada tipo y rotor donde se instala')
    text('Código de hélice __________ Rotores __________ Palas ____ Masa ____ g',9,12)
    text('Raíz / punta: definir estaciones r desde eje. Registrar r, cuerda y ángulo:',9,12)
    table(['Estación / r (mm)','Cuerda (mm)','Ángulo local (°)','Foto / método'],[['','','',''],['','','','']],[131,131,131,131],25)
    text('Medir cuerda entre borde de ataque y salida; ángulo respecto al plano de giro. Perfil: adjuntar plantilla/escaneo o D. Incertidumbres: ___________________',9,12)
    end()

    start(model+' / D. Masa y cierre','Hoja complementaria | Medir masa con el dron apagado')
    meta(model)
    text('Pesar la configuración completa en una báscula adecuada o sumar lecturas simultáneas de apoyos calibrados. Tarar el soporte. Registrar agua real y accesorios; los porcentajes son estados de planificación.',10,14)
    table(['Carga objetivo','Agua real kg','Masa total kg','Incert. kg','Foto / setup'],[[v,'','','',''] for v in ['0 %','25 %','50 %','75 %','100 %']],[94,100,110,85,135],27)
    text('Carga máxima usada como base del 100 %: ______ kg. Fuente: ____________',10)
    text('Batería (modelo / serie): __________________  Atomizadores instalados: ____',10)
    if model=='T70P':text('T70P: documentar especialmente el modelo de batería; el proyecto distingue DB2160 y DB1580. Verificar la configuración autorizada antes de definir la carga máxima.',9,12)
    table(['Elemento pesado por separado','Masa kg','Foto / incertidumbre'],[[s,'',''] for s in ['Batería','Tanque vacío, si es desmontable','Dron sin batería (declarar accesorios)']],[265,95,164],25)
    heading('Centro de gravedad y transformación del marco')
    text('Con reacciones y posiciones de apoyos se puede calcular CG en X,Y. Eso no determina CG en Z: requiere un método adicional documentado. Si no se midió, escribir D. No confundir centro geométrico con CG.',9,12)
    text('Estado de carga ____ CG X ____ Y ____ Z ____ mm; método ______________',10)
    text('Marco local a CG_tank50: traslación / rotación y evidencia _______________',9,12)
    heading('Revisión antes de entregar')
    text('[  ] Origen y ejes fotografiados   [  ] Cada rotor y atomizador identificado\n[  ] Tres setups independientes   [  ] Instrumentos e incertidumbre registrados',9,12)
    text('[  ] Fotos vinculadas a las lecturas   [  ] D y N/A explicados\n[  ] Diferencias y asimetrías conservadas   [  ] Configuración y serie completas',9,12)
    text('Entregar hojas y fotos. Transcribir a data/raw/mediciones_geometria.csv: una fila por parámetro, elemento y repetición; mm / 1000 = m. Conservar setup, marco, instrumento, incertidumbre y archivo de evidencia.',9,12)
    text('Después: auditar el bloque estático antes de la campaña operativa. RPM por rotor, empuje, caudal y gotas requieren sus ensayos específicos; este cuaderno no autoriza ni sustituye esas pruebas.',9,12)
    end()

c.save()
print(OUT)
print('Páginas:',page)








