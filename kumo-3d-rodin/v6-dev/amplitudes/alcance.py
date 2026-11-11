"""Alcance da mão do Kumo: que alvos do próprio corpo a mão alcança e com que flexão de cotovelo.
Usa o modelo oficial só para LER a posição do ombro e da superfície; comprimentos do braço = P1 iteração 4 (referência).
Aproximação: braço de 2 segmentos no plano ombro-alvo, centro da palma encostando no alvo. Uso: python alcance.py <kumo_rigged.blend> <saida.json>
"""
import bpy, math, json
from mathutils import Vector
import sys
bpy.ops.wm.open_mainfile(filepath=sys.argv[-2])
o=bpy.data.objects['Kumo']; me=o.data; B=bpy.data.objects['Kumo_Rig'].data.bones
vg={g.index:g.name for g in o.vertex_groups}
def dom(v):
    ws=[(vg[g.group],g.weight) for g in v.groups if not vg[g.group].startswith('outline')]
    return max(ws,key=lambda x:x[1])[0] if ws else None
D=[(v.co.copy(),dom(v)) for v in me.vertices]
S=B['upper_arm.L'].head_local
head=[c for c,d in D if d=='head']; torso=[c for c,d in D if d in ('spine','chest','hips','neck')]
def front(pts, zlo, zhi, xlo=-1, xhi=1):
    c=[p for p in pts if zlo<p.z<zhi and xlo<p.x<xhi]; return min(c,key=lambda p:p.y) if c else None
T={
 'boca/focinho (frente da cabeça, parte baixa)': front(head,0.98,1.25,-0.05,0.05),
 'bochecha esquerda (lateral da cabeça)': max([p for p in head if 1.05<p.z<1.35],key=lambda p:p.x),
 'topo da cabeça': max(head,key=lambda p:p.z),
 'peito (frente do tronco, centro)': front(torso,0.70,0.80,-0.03,0.03),
 'barriga (frente, centro)': front(torso,0.48,0.58,-0.03,0.03),
 'quadril esquerdo (lateral)': max([p for p in torso if 0.40<p.z<0.50],key=lambda p:p.x),
 'ombro oposto (frente)': front(torso,0.70,0.80,-0.25,-0.15),
}
L1,L2,H=0.1607,0.1552,0.1773   # P1 iteração 4 (referência)
out={}
for k,p in T.items():
    d=(p-S).length; w=max(d-H*0.45,0.0)   # punho: centro da palma encosta no alvo
    if w>L1+L2: fl=None
    elif w<abs(L1-L2): fl=180.0
    else: fl=180-math.degrees(math.acos((L1*L1+L2*L2-w*w)/(2*L1*L2)))
    out[k]=dict(alvo=[round(x,3) for x in p], dist_ombro=round(d,3), flexao_cotovelo=None if fl is None else round(fl,1), alcancavel=fl is not None)
json.dump(out, open(sys.argv[-1], 'w'), indent=1, ensure_ascii=False); print('OK')
