"""Boca anatômica do Kumo 3D (sem dentes).

1. Corta a pele na borda entre o focinho (verde escuro) e a mandíbula (verde claro), medida na textura por
   mapa_rosto.py. O corte só divide arestas e faces existentes nos pontos onde a linha passa: nenhum ponto antigo se
   move, então o Kumo parado fica igual (conferido por render).
2. Osso `jaw` (mandíbula), filho de `head`, com dobradiça atrás dos cantos da boca; a mandíbula e o lábio de baixo
   seguem esse osso.
3. Interior da boca (`Kumo_Boca`): uma bolsa vermelho escuro presa nos dois lábios. Fechada, fica dentro da cabeça.

  python boca.py <entrada.blend> <saída.blend>
"""
import bpy, bmesh, sys, math, json
import numpy as np
from mathutils import Vector, Matrix
SRC, DST = sys.argv[-2:]
bpy.ops.wm.open_mainfile(filepath=SRC)
rig = bpy.data.objects['Kumo_Rig']; body = bpy.data.objects['Kumo']; me = body.data
for b in rig.pose.bones: b.rotation_quaternion = (1, 0, 0, 0); b.rotation_euler = (0, 0, 0); b.location = (0, 0, 0)
if rig.animation_data: rig.animation_data.action = None
# ---------------- eixo do rosto (o rosto oficial está girado ~16°)
def centro_obj(n): o = bpy.data.objects[n]; return np.array([tuple(o.matrix_world @ v.co) for v in o.data.vertices]).mean(0)
EL, ER = centro_obj('KumoJogo_OlhoBase.L'), centro_obj('KumoJogo_OlhoBase.R')
LADO = (EL - ER)[:2] / np.linalg.norm((EL - ER)[:2]); FRENTE = np.array([LADO[1], -LADO[0]]); CENTRO = 0.5 * (EL + ER)[:2] - FRENTE * 0.30
# ---------------- linha da boca: altura em função do ângulo em volta da cabeça (simétrica, medida na textura)
PHI = [0, 10, 20, 30, 40, 50, 62]; ZL = [1.245, 1.235, 1.200, 1.160, 1.135, 1.125, 1.115]; PHI_C = 62.0
def phi_de(p): d = p[..., :2] - CENTRO; return np.degrees(np.arctan2(d @ LADO, d @ FRENTE))
def zlinha(ph): return np.interp(np.abs(ph), PHI, ZL)
MW = np.array(body.matrix_world); MWi = np.linalg.inv(MW)
def mundo(co): return (MW @ np.array([co[0], co[1], co[2], 1.0]))[:3]
def s_de(p):
    """lado da linha: < 0 embaixo (mandíbula). None fora da região onde a boca existe"""
    ph = phi_de(p); d = p[:2] - CENTRO
    if abs(ph) > PHI_C or d @ FRENTE < 0.02 or not (0.98 < p[2] < 1.36): return None
    s = p[2] - zlinha(ph); return s if abs(s) > 1e-7 else 1e-7
# ---------------- corte
# antes de cortar, as faces que a linha atravessa viram os MESMOS triângulos com que o Blender já as desenha
# (uma face de 4 pontos não é plana: dividi-la por outra diagonal mudaria a superfície um fio)
me.calc_loop_triangles()
S0 = [s_de(mundo(v.co)) for v in me.vertices]
def cruza(i, j): return S0[i] is not None and S0[j] is not None and S0[i] * S0[j] < 0
alvo = {}
for p in me.polygons:
    vs = list(p.vertices)
    if len(vs) > 3 and any(cruza(vs[k], vs[(k + 1) % len(vs)]) for k in range(len(vs))): alvo[p.index] = []
for t in me.loop_triangles:
    if t.polygon_index in alvo: alvo[t.polygon_index].append(tuple(t.vertices))
bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
faces_alvo = [(bm.faces[i], tris) for i, tris in alvo.items()]
ntri = 0
for f, tris in faces_alvo:
    # diagonais = arestas dos triângulos que não são arestas da face
    borda_f = {frozenset((e.verts[0].index, e.verts[1].index)) for e in f.edges}
    diag = {frozenset(e) for t in tris for e in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0]))} - borda_f
    atual = [f]
    for dg in diag:
        a_, b_ = [bm.verts[i] for i in dg]
        for ff in atual:
            if a_ in ff.verts and b_ in ff.verts:
                r = bmesh.utils.face_split(ff, a_, b_)
                if r and r[0]: atual = [x for x in atual if x is not ff] + [ff, r[0]]; ntri += 1
                break
print('TRIANGULADAS', len(faces_alvo), 'diagonais', ntri, flush=True)
bm.verts.ensure_lookup_table()
S = {v.index: s_de(mundo(v.co)) for v in bm.verts}
cruzam = [e for e in bm.edges if S[e.verts[0].index] is not None and S[e.verts[1].index] is not None and S[e.verts[0].index] * S[e.verts[1].index] < 0]
novos = set()
marca = bm.verts.layers.int.new('linha_boca')                     # marca os pontos da linha (as cópias herdam a marca)
for e in cruzam:
    a, b = e.verts; sa, sb = S[a.index], S[b.index]; t = sa / (sa - sb)
    ne, nv = bmesh.utils.edge_split(e, a, t); novos.add(nv); nv[marca] = 1
cortes = []
for f in list(bm.faces):
    vs = [v for v in f.verts if v in novos]
    if len(vs) == 2 and not any(vs[1] in (e.other_vert(vs[0]),) for e in vs[0].link_edges):
        r = bmesh.utils.face_split(f, vs[0], vs[1])
        if r and r[1]: cortes.append(r[1].edge)
print('CORTE arestas cruzadas', len(cruzam), 'pontos novos', len(novos), 'arestas de corte', len(cortes), flush=True)
bmesh.ops.split_edges(bm, edges=cortes)
bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
# lados do corte: cada face na região diz se está acima (focinho) ou abaixo (mandíbula)
def lado_face(f):
    c = sum((mundo(v.co) for v in f.verts), np.zeros(3)) / len(f.verts); s = s_de(c); return s
labio_inf = set(); labio_sup = set()
def na_linha(v):
    p = mundo(v.co); ph = phi_de(p); return abs(ph) <= PHI_C + 0.5 and abs(p[2] - zlinha(ph)) < 2e-4
borda = [v for v in bm.verts if v[marca] == 1]
linha_set = set(borda)
for v in borda:
    # o lado de cada cópia vem dos vizinhos dela que NÃO estão na linha (triângulos finos têm o centro quase na linha)
    ss = []
    for f in v.link_faces:
        for u in f.verts:
            if u in linha_set: continue
            x = s_de(mundo(u.co))
            if x is not None: ss.append(x)
    if not ss: continue
    (labio_inf if np.median(ss) < 0 else labio_sup).add(v.index)
bm.verts.layers.int.remove(marca)                           # a marca não vai para o arquivo final
bm.to_mesh(me); bm.free(); me.update()
print('LABIOS sup', len(labio_sup), 'inf', len(labio_inf), 'vertices', len(me.vertices), flush=True)
# ---------------- 2. mandíbula: osso e pesos
P = np.array([tuple(body.matrix_world @ v.co) for v in me.vertices])
linha = sorted(labio_sup | labio_inf, key=lambda i: phi_de(P[i]))
cantoE, cantoD = P[linha[0]], P[linha[-1]]                   # cantos da boca (as duas pontas da linha)
DOBRA = 0.5 * (cantoE + cantoD)                               # dobradiça: entre os dois cantos, atrás da boca
F3 = np.array([FRENTE[0], FRENTE[1], 0.0]); L3 = np.array([LADO[0], LADO[1], 0.0])
for o in bpy.context.selected_objects: o.select_set(False)
rig.select_set(True); bpy.context.view_layer.objects.active = rig; bpy.ops.object.mode_set(mode='EDIT'); EB = rig.data.edit_bones
RWi = rig.matrix_world.inverted()
jb = EB.new('jaw'); jb.parent = EB['head']; jb.use_deform = True
jb.head = RWi @ Vector(DOBRA); jb.tail = RWi @ Vector(DOBRA + F3 * 0.25 - np.array([0, 0, 0.06]))
jb.align_roll(RWi.to_3x3() @ Vector((0, 0, 1)))
bpy.ops.object.mode_set(mode='OBJECT')
# eixo X local do osso tem de ser o eixo lateral (abrir = girar em X)
xl = np.array(rig.matrix_world.to_3x3() @ rig.data.bones['jaw'].matrix_local.to_3x3().col[0])
print('MANDIBULA dobradiça', DOBRA.round(3), 'eixo X do osso . lado =', round(float(abs(xl @ L3)), 3), flush=True)
def sstep(a, b, x): t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)
gi = {g.name: g.index for g in body.vertex_groups}; VG = body.vertex_groups
gj = VG.new(name='jaw') if 'jaw' not in gi else VG['jaw']
ph = phi_de(P); fwd = (P[:, :2] - CENTRO) @ FRENTE; f_dob = float((DOBRA[:2] - CENTRO) @ FRENTE)
abaixo = P[:, 2] < zlinha(ph) - 1e-5
w = abaixo * sstep(f_dob - 0.10, f_dob + 0.06, fwd) * (1 - sstep(PHI_C, PHI_C + 14, np.abs(ph))) * sstep(0.93, 1.00, P[:, 2])
nucleo = abaixo & (fwd > f_dob + 0.06) & (np.abs(ph) < PHI_C - 4) & (P[:, 2] > 1.00)   # frente da mandíbula: osso inteiro
# o lábio de cima (e tudo acima da linha) é cabeça; os pontos do lábio de baixo são mandíbula inteira
w[list(labio_sup)] = 0.0; w[list(labio_inf)] = np.maximum(w[list(labio_inf)], 1.0)
# suaviza pela malha (o corte separa os lábios, então nada vaza de um lábio para o outro)
adj = [[] for _ in range(len(me.vertices))]
for e in me.edges: a_, b_ = e.vertices; adj[a_].append(b_); adj[b_].append(a_)
fixos = set(labio_sup) | set(labio_inf)
for _ in range(6):
    nw = w.copy()
    for i in range(len(w)):
        if i in fixos or nucleo[i] or not adj[i] or w[i] == 0 and all(w[j] == 0 for j in adj[i]): continue
        nw[i] = 0.5 * w[i] + 0.5 * np.mean(w[adj[i]])
    w = nw * abaixo                                          # só suaviza a transição (dobradiça e pescoço); nunca sobe acima da linha
    w[nucleo] = 1.0
w[list(labio_inf)] = 1.0; w[list(labio_sup)] = 0.0              # os lábios ficam na linha: o "abaixo" não os pega
cab = VG['head'].index; nj = 0
for v in me.vertices:
    j = float(w[v.index])
    if j < 1e-3: continue
    gs = {body.vertex_groups[g.group].name: g.weight for g in v.groups if not body.vertex_groups[g.group].name.startswith('outline')}
    tot = sum(gs.values()) or 1.0; h = gs.get('head', 0.0)
    if h <= 0: continue
    tira = j * h; gs['head'] = h - tira; gs['jaw'] = tira
    top = sorted(gs.items(), key=lambda x: -x[1])[:4]; sm = sum(x[1] for x in top)
    for nm in gs:
        if nm not in dict(top): VG[nm].remove([v.index])
    for nm, x in top:
        if x > 1e-5: VG[nm].add([v.index], x / sm, 'REPLACE')
        else: VG[nm].remove([v.index])
    nj += 1
print('PESOS mandíbula em', nj, 'pontos', flush=True)
# contorno de jogo: pega os pesos da pele mais próxima (sem corte: com a boca aberta ele fica esticado por cima,
# e a face esticada aponta para fora, então some no jogo, que desenha só as costas do contorno)
hull = bpy.data.objects.get('Kumo_Contorno')
if hull:
    from mathutils.kdtree import KDTree
    kd = KDTree(len(P))
    for i, p in enumerate(P): kd.insert(Vector(p), i)
    kd.balance()
    hg = hull.vertex_groups.get('jaw') or hull.vertex_groups.new(name='jaw'); hc = hull.vertex_groups['head']; nh = 0
    for v in hull.data.vertices:
        q = hull.matrix_world @ v.co; co, i, d = kd.find(q)
        j = float(w[i])
        if j < 1e-3: continue
        gs = {hull.vertex_groups[g.group].name: g.weight for g in v.groups}; h = gs.get('head', 0.0)
        if h <= 0: continue
        hc.add([v.index], h * (1 - j), 'REPLACE'); hg.add([v.index], h * j, 'REPLACE'); nh += 1
    print('CONTORNO pesos em', nh, flush=True)
# a "moldura" de pele dos olhos (cópia da pele em volta de cada olho, presa na cabeça) desce até a boca e ficaria
# parada por cima da abertura: tira as faces dela abaixo da linha da boca (ali ela é só a pele repetida)
for lado_ in 'LR':
    mo = bpy.data.objects.get(f'KumoJogo_Moldura.{lado_}')
    if not mo: continue
    bmm = bmesh.new(); bmm.from_mesh(mo.data); MWm = np.array(mo.matrix_world)
    def wco(v): return (MWm @ np.array([*v.co, 1.0]))[:3]
    tira = [f for f in bmm.faces if any(wco(v)[2] < zlinha(phi_de(wco(v))) + 0.012 and abs(phi_de(wco(v))) < PHI_C + 20 for v in f.verts)]
    bmesh.ops.delete(bmm, geom=tira, context='FACES'); bmm.to_mesh(mo.data); bmm.free(); mo.data.update()
    print('MOLDURA', lado_, 'faces tiradas', len(tira), flush=True)
# ---------------- 3. interior da boca: bolsa vermelho escuro presa nos lábios
def ordem(ids):
    ids = sorted(ids, key=lambda i: phi_de(P[i])); return ids
sup = ordem(labio_sup); inf = ordem(labio_inf)
# as pontas (cantos) não foram duplicadas pelo corte: entram nas duas listas
for c_ in (linha[0], linha[-1]):
    if c_ not in sup: sup = ordem(sup + [c_])
    if c_ not in inf: inf = ordem(inf + [c_])
K = 6
def anel_alvo(p):
    """ponto de dentro para onde cada ponto do lábio vai: na direção da dobradiça, mais fundo no meio"""
    return DOBRA + (p - DOBRA) * 0.30
def bolsa(ids, sinal):
    verts = []; pesos = []
    for k in range(K + 1):
        t = k / K
        for i in ids:
            p = P[i]; q = p + (anel_alvo(p) - p) * t
            fr = max(0.0, math.cos(math.radians(phi_de(p) * 1.4)))           # no meio da boca estufa, nos cantos não
            q = q + np.array([0, 0, sinal * 0.02 * fr * math.sin(math.pi * min(t * 1.3, 1.0))])   # teto sobe, chão desce: espaço
            verts.append(q); pesos.append(t)
    return verts, pesos
vs_s, ts_s = bolsa(sup, +1); vs_i, ts_i = bolsa(inf, -1)
# cada ponto da bolsa (menos a beira, que é o próprio lábio) tem de ficar pelo menos 6 mm por dentro da pele
from mathutils.bvhtree import BVHTree
me.calc_loop_triangles()
pele = BVHTree.FromPolygons([Vector(p) for p in P], [tuple(t.vertices) for t in me.loop_triangles])
def para_dentro(vs, ts):
    n = 0
    for k, (q, t) in enumerate(zip(vs, ts)):
        if t <= 0: continue
        for _ in range(8):
            co, nr, _, d = pele.find_nearest(Vector(q))
            fora = (Vector(q) - co).dot(nr)                     # > 0: do lado de fora da pele
            if fora < -0.006: break
            q = np.array(q) - np.array(nr) * (fora + 0.008); n += 1
        vs[k] = q
    return n
print('BOLSA ajustes para dentro', para_dentro(vs_s, ts_s), para_dentro(vs_i, ts_i), flush=True)
n_s, n_i = len(sup), len(inf)
# último anel: teto e chão se encontram (mesmo ponto no fundo); usa o do teto e liga o chão a ele por proximidade
verts = vs_s + vs_i[: n_i * K]; faces = []; mats = []
def idx_s(k, j): return k * n_s + j
def idx_i(k, j): return len(vs_s) + k * n_i + j if k < K else None
for k in range(K):
    for j in range(n_s - 1):
        faces.append((idx_s(k, j), idx_s(k, j + 1), idx_s(k + 1, j + 1), idx_s(k + 1, j))); mats.append(1 if k >= K - 2 else 0)
fundo = [verts[idx_s(K, j)] for j in range(n_s)]
def fundo_mais_perto(p):
    d = [np.linalg.norm(np.array(p) - np.array(f)) for f in fundo]; return int(np.argmin(d))
for k in range(K):
    for j in range(n_i - 1):
        if k + 1 < K: a4 = (idx_i(k, j), idx_i(k + 1, j), idx_i(k + 1, j + 1), idx_i(k, j + 1))
        else:
            fa, fb = idx_s(K, fundo_mais_perto(vs_i[K * n_i + j])), idx_s(K, fundo_mais_perto(vs_i[K * n_i + j + 1]))
            a4 = (idx_i(k, j), fa, fb, idx_i(k, j + 1)) if fa != fb else (idx_i(k, j), fa, idx_i(k, j + 1))
        faces.append(a4); mats.append(1 if k >= K - 2 else 0)
bm_ = bpy.data.meshes.new('Kumo_Boca'); bm_.from_pydata([tuple(MWi[:3, :3] @ np.array(v) + MWi[:3, 3]) for v in verts], [], faces); bm_.update()
ob = bpy.data.objects.new('Kumo_Boca', bm_); bpy.context.scene.collection.objects.link(ob); ob.matrix_world = body.matrix_world
for nm, cor in (('Kumo_Boca_Interior', (0.20, 0.025, 0.03)), ('Kumo_Boca_Fundo', (0.09, 0.008, 0.012))):
    mt = bpy.data.materials.get(nm) or bpy.data.materials.new(nm); mt.use_nodes = True; nt = mt.node_tree; nt.nodes.clear()
    em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (*cor, 1); out = nt.nodes.new('ShaderNodeOutputMaterial'); nt.links.new(em.outputs[0], out.inputs[0])
    mt.use_backface_culling = False; ob.data.materials.append(mt)
for f, m in zip(ob.data.polygons, mats): f.material_index = m
# pesos: teto = cabeça; chão = mandíbula na beira, metade no fundo
gh = ob.vertex_groups.new(name='head'); gjb = ob.vertex_groups.new(name='jaw')
for i in range(len(vs_s)):
    t = ts_s[i]; jj = 0.5 * t if t >= 1 - 1e-6 else 0.0
    gh.add([i], 1 - jj, 'REPLACE');
    if jj > 0: gjb.add([i], jj, 'REPLACE')
for i in range(n_i * K):
    t = ts_i[i]; jj = 1.0 - 0.5 * t; vi = len(vs_s) + i
    gjb.add([vi], jj, 'REPLACE'); gh.add([vi], 1 - jj, 'REPLACE')
ob.parent = rig; ob.matrix_parent_inverse = rig.matrix_world.inverted() @ Matrix(); ob.matrix_world = body.matrix_world
md = ob.modifiers.new('Armature', 'ARMATURE'); md.object = rig
print('INTERIOR vértices', len(verts), 'faces', len(faces), flush=True)
json.dump(dict(sup=sup, inf=inf, dobra=DOBRA.tolist(), centro=CENTRO.tolist(), frente=FRENTE.tolist(), lado=LADO.tolist(), phi=PHI, z=ZL), open(DST + '.labios.json', 'w'))
bpy.ops.wm.save_as_mainfile(filepath=DST, copy=True, relative_remap=False)
print('BOCA OK')
