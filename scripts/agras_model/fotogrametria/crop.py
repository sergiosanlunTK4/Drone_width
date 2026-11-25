import sys
from PIL import Image, ImageDraw, ImageFont
src, out, x0, y0, x1, y1, z = sys.argv[1], sys.argv[2], *map(int, sys.argv[3:7]), float(sys.argv[7])
step = int(sys.argv[8]) if len(sys.argv) > 8 else 20
im = Image.open(src).convert('RGB').crop((x0, y0, x1, y1))
im = im.resize((int((x1-x0)*z), int((y1-y0)*z)), Image.LANCZOS)
d = ImageDraw.Draw(im)
for gx in range((x0//step)*step, x1, step):
    if gx < x0: continue
    X = (gx-x0)*z; d.line([(X,0),(X,im.size[1])], fill=(255,0,0) if gx%(step*5)==0 else (255,180,180), width=1)
    if gx%(step*5)==0: d.text((X+2,2), str(gx), fill=(255,0,0))
for gy in range((y0//step)*step, y1, step):
    if gy < y0: continue
    Y = (gy-y0)*z; d.line([(0,Y),(im.size[0],Y)], fill=(0,0,255) if gy%(step*5)==0 else (180,180,255), width=1)
    if gy%(step*5)==0: d.text((2,Y+2), str(gy), fill=(0,0,255))
im.save(out)
