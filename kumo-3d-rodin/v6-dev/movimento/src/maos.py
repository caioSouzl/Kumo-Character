"""Palma e costas da mão diferentes: a palma (e a parte de baixo dos dedos) usa a cor clara da barriga do Kumo.
A cor vem só do UV (as faces da palma passam a apontar para um pedaço da textura que já é a barriga): sem material novo,
sem mexer na textura oficial, e vale igual no Blender, no GLB, no FBX e na Central.

O lado da palma é o lado para onde os dedos se fecham: para cada osso, o giro positivo em X (fechar) diz a direção.

  blender --background kumo_v8_movimento.blend --python maos.py -- <relatório.json>"""
import bpy, sys, json, math
import numpy as np
from mathutils import Vector, Matrix
REL = sys.argv[sys.argv.index('--') + 1]
rig = bpy.data.objects['Kumo_Rig']; B = rig.data.bones; o = bpy.data.objects['Kumo']; me = o.data
im = bpy.data.images.get('kumo_quad_diffuse')
if im: im.filepath = '/home/user/Kumo-Character/kumo-3d-rodin/textures/kumo_quad_diffuse.png'; im.reload()
W, H = im.size; px = np.array(im.pixels[:]).reshape(H, W, 4)
uv = me.uv_layers.active
def cor(u, v): return px[min(H - 1, max(0, int(v * H))), min(W - 1, max(0, int(u * W))), :3]

# ---- a cor da palma: o UV de uma face da barriga (frente do tronco, na altura do umbigo), com a cor conferida
alvo = Vector((0.0, -0.19, 0.60)); melhor = None
for pl in me.polygons:
    c = sum((me.vertices[v].co for v in pl.vertices), Vector()) / len(pl.vertices)
    d = (c - alvo).length
    if abs(c.x) < 0.06 and (melhor is None or d < melhor[0]): melhor = (d, pl)
pl_b = melhor[1]; uv_barriga = sum((uv.data[l].uv.copy() for l in pl_b.loop_indices), Vector((0, 0))) / len(pl_b.loop_indices)
COR_PALMA = [round(float(x), 2) for x in cor(*uv_barriga)]
print('BARRIGA', [round(x, 3) for x in uv_barriga], COR_PALMA)

def lado_fecha(nome):
    """direção (no espaço do armature) para onde a ponta do osso vai quando ele fecha (giro + em X do osso)"""
    b = B[nome]; M = b.matrix_local.to_3x3(); Rx = M @ Matrix.Rotation(math.radians(30), 3, 'X') @ M.inverted()
    eixo = (b.tail_local - b.head_local); mov = (b.head_local + Rx @ eixo) - b.tail_local
    return mov.normalized()

REP = {}; total = 0
for s in 'LR':
    dedos = [f'dedo{i}_{j}.{s}' for i in (1, 2, 3) for j in (1, 2)] + [f'polegar_1.{s}', f'polegar_2.{s}']
    palma = {n: lado_fecha(n) for n in dedos}
    q_mao = sum(palma.values(), Vector()).normalized()
    palma[f'hand.{s}'] = q_mao; palma[f'metacarpo.{s}'] = q_mao
    vg = {g.index: g.name for g in o.vertex_groups if g.name in palma}
    n_s = 0
    for pl in me.polygons:
        pesos = {}
        for v in pl.vertices:
            for g in me.vertices[v].groups:
                if g.group in vg: pesos[vg[g.group]] = pesos.get(vg[g.group], 0.0) + g.weight
        if not pesos or sum(pesos.values()) / len(pl.vertices) < 0.6: continue          # só faces da mão
        osso = max(pesos, key=pesos.get)
        if pl.normal.dot(palma[osso]) > 0.25:
            for l in pl.loop_indices: uv.data[l].uv = uv_barriga
            n_s += 1
    REP[s] = dict(faces_da_palma=n_s); total += n_s
REP['cor_palma_rgb'] = COR_PALMA
json.dump(REP, open(REL, 'w'), indent=1); print('MAOS', REP)
bpy.ops.wm.save_mainfile()
