import sys, numpy as np
from PIL import Image
im = np.asarray(Image.open(sys.argv[1]).convert('L')).astype(float)
dark = im < 110
def prof(hub, tip):
    hub=np.array(hub,float); tip=np.array(tip,float)
    L=np.linalg.norm(tip-hub); u=(tip-hub)/L; n=np.array([-u[1],u[0]])
    out=[]
    for f in np.linspace(0.10,0.99,31):
        c=hub+u*L*f; w=[]
        for t in np.arange(-25,25,0.25):
            p=c+n*t; x,y=int(round(p[0])),int(round(p[1]))
            w.append(dark[y,x])
        w=np.array(w)
        idx=np.where(w)[0]
        width=(idx.max()-idx.min()+1)*0.25 if len(idx) else 0
        out.append((round(f,3), width))
    return L,out
for name,hub,tip in [('TL_a',(473,155),(582,38)),('TL_b',(473,155),(369,276)),('TR_a',(836,155),(728,38)),('TR_b',(836,155),(942,276)),('BL_a',(460,486),(372,353)),('BL_b',(460,486),(538,628))]:
    L,o=prof(hub,tip); print(name, round(L,1), ' '.join(f'{f:.2f}:{w:.1f}' for f,w in o))
