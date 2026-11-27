"""Axilas sem fresta: vértices quase colados (a malha tem costuras de ~1 mm sob o braço) levavam pesos diferentes
e, com o braço erguido, a pele se abria num buraco preto. Aqui cada grupo de vértices a menos de 4 mm recebe a média
dos pesos. Parado, nada muda (a malha é a mesma); só os pesos de pontos colados ficam iguais.

  blender --background kumo_v8_movimento.blend --python axila.py -- <relatório.json>"""
import bpy, sys, json
from mathutils import kdtree
REL = sys.argv[sys.argv.index('--') + 1]
o = bpy.data.objects['Kumo']; me = o.data; N = len(me.vertices); DIST = 0.004
kd = kdtree.KDTree(N)
for v in me.vertices: kd.insert(v.co, v.index)
kd.balance()
pai = list(range(N))
def raiz(i):
    while pai[i] != i: pai[i] = pai[pai[i]]; i = pai[i]
    return i
for v in me.vertices:
    for co, j, d in kd.find_range(v.co, DIST):
        if j != v.index: pai[raiz(j)] = raiz(v.index)
grupos = {}
for i in range(N): grupos.setdefault(raiz(i), []).append(i)
nomes = {g.index: g.name for g in o.vertex_groups}; tratados = 0; ajustados = 0
for r, mem in grupos.items():
    if len(mem) < 2: continue
    soma = {}
    for i in mem:
        for g in me.vertices[i].groups: soma[g.group] = soma.get(g.group, 0.0) + g.weight
    med = {k: v / len(mem) for k, v in soma.items()}
    top = dict(sorted(((k, w) for k, w in med.items() if nomes[k] != 'outline_espessura'), key=lambda kv: -kv[1])[:4])   # no máximo 4 ossos
    t = sum(top.values())
    if t <= 0: continue
    tratados += 1
    for i in mem:
        antes = {g.group: g.weight for g in me.vertices[i].groups if nomes[g.group] != 'outline_espessura'}
        for g in me.vertices[i].groups:
            if nomes[g.group] == 'outline_espessura': continue
            if g.group not in top: g.weight = 0.0
        for k, w in top.items(): o.vertex_groups[k].add([i], w / t, 'REPLACE')
        if any(abs(antes.get(k, 0) - w / t) > 0.01 for k, w in top.items()): ajustados += 1

# ---------- suaviza os pesos em volta da axila (a costura frente do braço com o tronco): um triângulo minúsculo ali
# (peso partido entre braço, ombro e coluna) virava do avesso com o braço erguido e aparecia como um buraco preto.
import bmesh
from mathutils import Vector
RAIO = 0.075; PASSOS = 6; FATOR = 0.6
bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
OSSOS_AX = [g.index for g in o.vertex_groups if g.name != 'outline_espessura']
def pesos_v(i): return {g.group: g.weight for g in me.vertices[i].groups if g.group in OSSOS_AX and g.weight > 1e-4}
suave = 0
for lado in (1, -1):
    centro = Vector((-0.19 * lado, -0.115, 0.73))
    reg = {v.index for v in bm.verts if (v.co - centro).length < RAIO}
    for _ in range(PASSOS):
        novo = {}
        for i in reg:
            viz = [e.other_vert(bm.verts[i]).index for e in bm.verts[i].link_edges]
            w0 = pesos_v(i); acc = {}
            for j in viz + [i]:
                for k, w in pesos_v(j).items(): acc[k] = acc.get(k, 0.0) + w / (len(viz) + 1)
            mix = {k: (1 - FATOR) * w0.get(k, 0.0) + FATOR * acc.get(k, 0.0) for k in set(w0) | set(acc)}
            top = dict(sorted(mix.items(), key=lambda kv: -kv[1])[:4]); t = sum(top.values())
            novo[i] = {k: w / t for k, w in top.items()}
        for i, d in novo.items():
            for g in me.vertices[i].groups:
                if g.group in OSSOS_AX and g.group not in d: g.weight = 0.0
            for k, w in d.items(): o.vertex_groups[k].add([i], w, 'REPLACE')
    suave += len(reg)
bm.free()

# ---------- textura preta: um triângulo da axila (frente, direita) apontava para um pedaço preto da textura. Tão pequeno parado,
# ninguém via; com o braço erguido ele se abria e aparecia como um buraco preto. Aqui o UV dele passa a ser o dos vizinhos.
import numpy as np
im = bpy.data.images.get('kumo_quad_diffuse')
if im: im.filepath = '/home/user/Kumo-Character/kumo-3d-rodin/textures/kumo_quad_diffuse.png'; im.reload()
W, H = im.size; px = np.array(im.pixels[:]).reshape(H, W, 4)
uv = me.uv_layers.active
def cor(u, v): return px[min(H - 1, max(0, int(v * H))), min(W - 1, max(0, int(u * W))), :3]
def preto(c):    # c é a cor; o canto também é ruim se há preto a 3 texels (a amostragem suave puxa o preto para dentro)
    return c.max() < 0.03
def perto_de_preto(u, v):
    x = min(W - 1, max(0, int(u * W))); y = min(H - 1, max(0, int(v * H)))
    return px[max(0, y - 3):y + 4, max(0, x - 3):x + 4, :3].max(axis=2).min() < 0.03
por_vert = {}
for pl in me.polygons:
    for l in pl.loop_indices: por_vert.setdefault(me.loops[l].vertex_index, []).append((pl.index, l))
uv_corrigidos = 0; ruins = []
for lado in (1, -1):
    centro = Vector((-0.19 * lado, -0.13, 0.73))
    for pl in me.polygons:
        if (sum((me.vertices[v].co for v in pl.vertices), Vector()) / len(pl.vertices) - centro).length > 0.12: continue
        ruim = [l for l in pl.loop_indices if perto_de_preto(*uv.data[l].uv)]
        bons = [l for l in pl.loop_indices if l not in ruim]
        if not ruim: continue
        ruins.append(pl.index)
        if bons:    # o canto preto passa a apontar para a média dos outros cantos da mesma face
            m = sum((uv.data[l].uv.copy() for l in bons), Vector((0, 0))) / len(bons)
            for l in ruim: uv.data[l].uv = m; uv_corrigidos += 1
        else:       # a face toda é preta: usa a média dos vizinhos que não são pretos
            for l in ruim:
                viz = [uv.data[l2].uv.copy() for (pi, l2) in por_vert[me.loops[l].vertex_index] if pi != pl.index and not perto_de_preto(*uv.data[l2].uv)]
                if viz: uv.data[l].uv = sum(viz, Vector((0, 0))) / len(viz); uv_corrigidos += 1
# faces de costura: os cantos caem em ilhas diferentes da textura e o miolo da face amostra o vazio preto entre elas.
# A face passa a usar uma só cor (a do canto mais claro), como a pele em volta.
colapsadas = 0
for lado in (1, -1):
    centro = Vector((-0.19 * lado, -0.13, 0.73))
    for pl in me.polygons:
        if (sum((me.vertices[v].co for v in pl.vertices), Vector()) / len(pl.vertices) - centro).length > 0.16: continue
        us = [uv.data[l].uv.copy() for l in pl.loop_indices]
        def escura():
            for a in (0, .17, .33, .5, .67, .83, 1):
                for b in (0, .17, .33, .5, .67, .83, 1):
                    q = (us[0] * (1 - a) + us[1] * a) * (1 - b) + (us[3] * (1 - a) + us[2] * a) * b if len(us) == 4 else us[0]
                    if cor(*q).max() < 0.05: return True
            return False
        if max((a - b).length for a in us for b in us) < 0.03 and not escura(): continue
        melhor = max(range(len(us)), key=lambda k: float(cor(*us[k]).sum()))
        for l in pl.loop_indices: uv.data[l].uv = us[melhor]
        colapsadas += 1
rel = dict(faces_de_costura_colapsadas=colapsadas, faces_de_textura_preta=len(ruins), uv_corrigidos=uv_corrigidos, vertices_suavizados_axila=suave, grupos_de_vertices_colados=tratados, vertices_ajustados=ajustados, distancia_m=DIST)
json.dump(rel, open(REL, 'w'), indent=1); print('AXILA', rel)
bpy.ops.wm.save_mainfile()
