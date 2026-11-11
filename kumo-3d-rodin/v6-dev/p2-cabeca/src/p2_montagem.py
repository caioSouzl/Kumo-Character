"""Kumo v6 · P2 (cabeça, olhos e boca), iteração 1 — autorizado pelo Caio em 2026-11-11.

  python p2_montagem.py <kumo_v2_head.blend gerado> <fit_kumo.json> <kumo_v6_maos_jogo.blend> <saída>

Base: cabeça facetada F1.2 da linha arquivada (aprovada em 2026-11-09; gerada sem mudança por kumo_v2_head.py),
com órbitas abertas, pálpebras na própria malha, globo ocular que gira, boca com lábios e cavidade, mandíbula.
- Levada ao quadro da cabeça do Kumo oficial (queixo, topo e centro medidos em fit_cabeca_kumo.py; escala uniforme k).
- Olhos: globo + aro + pupila + brilho viram UMA malha por olho, presa por peso 1 ao osso Eye.X (exportável).
- Contorno: casca invertida (como o corpo) na cabeça.
- Testes: piscada (shape keys), olhar (ossos dos olhos), mandíbula, giro da cabeça; cruzamentos olho×cabeça e da
  própria cabeça; pesos; exportação GLB/FBX com reimportação. Renders sobre o corpo Rodin (cabeça antiga escondida).
"""
import bpy, bmesh, sys, os, json, math, time
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
HEADB, FIT, BODYB, OUT = sys.argv[-4:]
os.makedirs(os.path.join(OUT, 'renders'), exist_ok=True)
FAST = bool(os.environ.get('P2_FAST')); RES = int(os.environ.get('P2_RES', '560')); SAMPLES = int(os.environ.get('P2_SAMPLES', '16'))
REPO = '/home/user/Kumo-Character/kumo-3d-rodin'
REP = {}
bpy.ops.wm.open_mainfile(filepath=HEADB); sc = bpy.context.scene
for o in list(bpy.data.objects):
    if o.type == 'CAMERA' or o.name == 'P1_Reference_Head': bpy.data.objects.remove(o)
rig = bpy.data.objects['Kumo_v2_Rig']; head = bpy.data.objects['Kumo_v2_Head']
T = json.load(open(FIT))['transform']; k = T['escala_k']
M = Matrix.Translation((T['x_centro'], T['y_centro'] - 0.06 * k, T['queixo_z'] - 0.955 * k)) @ Matrix.Scale(k, 4)
REP['transformacao'] = dict(T, matriz='x*k + x_centro; (y-0.06)*k + y_centro; queixo + (z-0.955)*k')

# ---- 0. olho esférico + pálpebras por ossos (no quadro original da F1.2; a escala vem depois)
GAP = float(os.environ.get('P2_GAP', '0.002'))
hd = head.data; KBk = hd.shape_keys.key_blocks
HW = np.array([tuple(head.matrix_world @ v.co) for v in hd.vertices])
REP['olho_esferico'] = {}
LID = {}
for sd in ('L', 'R'):
    eye = bpy.data.objects[f'Kumo_v2_Eye_{sd}']; b = rig.data.bones[f'Eye.{sd}']
    E = np.array([tuple(eye.matrix_world @ v.co) for v in eye.data.vertices])
    a = np.array(tuple((b.tail_local - b.head_local).normalized()))
    e0 = np.array(tuple(b.head_local))
    front = e0 + a * max((E - e0) @ a)                      # ponto da frente do olho antigo, no eixo do olhar
    near = np.linalg.norm(HW - e0, axis=1) < 0.45
    # forro da órbita = vértices da borda aberta atrás do olho (escondidos): não limitam a esfera, são afastados depois
    bmh = bmesh.new(); bmh.from_mesh(hd); bnd = {v.index for v in bmh.verts if v.is_boundary}; bmh.free()
    vis = near.copy(); forro = [i for i in np.nonzero(near)[0] if i in bnd]; vis[forro] = False
    best = None
    for back in np.arange(0.0, 0.05, 0.002):
        for R in np.arange(0.40, 0.14, -0.005):
            c = front - a * (R + back); m = (np.linalg.norm(HW[vis] - c, axis=1) - R).min()
            if m >= GAP: best = (R, back, c, m); break
        if best: break
    R, back, c, m = best
    # afasta o forro para fora da esfera
    nf = 0
    for i in forro:
        d_ = HW[i] - c; r_ = np.linalg.norm(d_)
        if r_ < R + GAP:
            p_new = c + d_ / r_ * (R + GAP); hd.vertices[i].co = head.matrix_world.inverted() @ Vector(p_new.tolist()); HW[i] = p_new; nf += 1
    REP['olho_esferico'][sd] = dict(raio=round(float(R), 4), recuo_da_frente=round(float(back), 4), centro=[round(float(x), 4) for x in c],
                                   folga_min_mm=round(float(m) * 1000, 2), forro_afastado=nf, forro_total=len(forro),
                                   olho_antigo_semi_eixos=[round(float(x), 3) for x in (E.max(0) - E.min(0)) / 2])
    cv = Vector(c.tolist())
    for n, dlt in (('Eye', 0.0), ('PupilRing', 0.0006), ('Pupil', 0.0012), ('Highlight', 0.0018)):
        o = bpy.data.objects[f'Kumo_v2_{n}_{sd}']; mi = o.matrix_world.inverted()
        for v in o.data.vertices:
            pw = o.matrix_world @ v.co; v.co = mi @ (cv + (pw - cv).normalized() * (R + dlt))
    LID[sd] = dict(c=cv, R=float(R), a=Vector(a.tolist()))
# osso do olho no centro da esfera (o giro do olhar passa pelo centro)
sel_ = [o for o in bpy.context.selected_objects]
for o in sel_: o.select_set(False)
rig.select_set(True); bpy.context.view_layer.objects.active = rig; bpy.ops.object.mode_set(mode='EDIT'); EB = rig.data.edit_bones
for sd, L in LID.items():
    eb = EB[f'Eye.{sd}']; ln = eb.length; eb.head = L['c']; eb.tail = L['c'] + L['a'] * ln
    u = L['a'].cross(Vector((0, 0, 1))).normalized()
    for nm in (f'Palpebra_sup.{sd}', f'Palpebra_inf.{sd}'):
        nb = EB.new(nm); nb.head = L['c']; nb.tail = L['c'] + L['a'] * ln * 0.8; nb.parent = EB['Head']; nb.use_connect = False
        nb.align_roll(Vector((0, 0, 1)))
    L['u'] = u
bpy.ops.object.mode_set(mode='OBJECT')
# eixo de rotação das pálpebras = eixo X local do osso (horizontal, perpendicular ao olhar)
for sd, L in LID.items(): L['u'] = (rig.data.bones[f'Palpebra_sup.{sd}'].matrix_local.to_3x3() @ Vector((1, 0, 0))).normalized()
# pesos das pálpebras a partir da shape key Blink antiga: ângulo de cada vértice em torno do eixo, pelo centro do olho
def ang(p, q, c, u):
    a_ = (p - c); b_ = (q - c); a_ = a_ - u * a_.dot(u); b_ = b_ - u * b_.dot(u)
    if a_.length < 1e-9 or b_.length < 1e-9: return 0.0
    return math.atan2(u.dot(a_.cross(b_)), a_.dot(b_))
gsup = {}; ginf = {}
REP['palpebras'] = {}
for sd, L in LID.items():
    kb = KBk[f'Blink_{sd}']; th = {}
    for v in hd.vertices:
        p = head.matrix_world @ v.co; q = head.matrix_world @ kb.data[v.index].co
        if (q - p).length > 1e-6: th[v.index] = ang(p, q, L['c'], L['u'])
    up = {i: t for i, t in th.items() if (head.matrix_world @ (KBk[f'Blink_{sd}'].data[i].co) - head.matrix_world @ hd.vertices[i].co).z < 0}
    lo = {i: t for i, t in th.items() if i not in up}
    TS = max(up.values(), key=abs); TI = max(lo.values(), key=abs)
    L['TS'], L['TI'] = TS, TI
    gs = head.vertex_groups.get(f'Palpebra_sup.{sd}') or head.vertex_groups.new(name=f'Palpebra_sup.{sd}')
    gl = head.vertex_groups.get(f'Palpebra_inf.{sd}') or head.vertex_groups.new(name=f'Palpebra_inf.{sd}')
    gH = head.vertex_groups['Head']; gi_ = {g.index: g.name for g in head.vertex_groups}
    for grp, dd, TT in ((gs, up, TS), (gl, lo, TI)):
        for i, t in dd.items():
            w = max(0.0, min(1.0, t / TT))
            if w < 1e-3: continue
            v = hd.vertices[i]; old = {gi_[g.group]: g.weight for g in v.groups if gi_[g.group] in ('Head', 'Jaw')}
            tot = sum(old.values()) or 1.0
            for n_, w_ in old.items(): head.vertex_groups[n_].add([i], w_ / tot * (1 - w), 'REPLACE')
            grp.add([i], w, 'REPLACE')
    # camadas: a pálpebra superior desliza por fora da inferior (afasta do centro proporcional ao peso)
    for i, t in up.items():
        w = max(0.0, min(1.0, t / TS)); v = hd.vertices[i]; pw = head.matrix_world @ v.co; d_ = (pw - L['c'])
        r = d_.length; rmin = L['R'] + GAP + 0.0015 * w
        if r < rmin: v.co = head.matrix_world.inverted() @ (L['c'] + d_.normalized() * rmin)
    def phi(i):
        d_ = head.matrix_world @ hd.vertices[i].co - L['c']; d_ = d_ - L['u'] * d_.dot(L['u'])
        return math.atan2(L['u'].dot(L['a'].cross(d_)), L['a'].dot(d_))
    ws_ = lambda i, TT: max(0.0, min(1.0, (up if TT is TS else lo)[i] / TT))
    sup_full = [i for i in up if ws_(i, TS) > 0.99]; inf_full = [i for i in lo if ws_(i, TI) > 0.99]
    # sinal: o giro de TS leva a borda superior para baixo; medimos em "phi" com o mesmo eixo
    ups = [phi(i) for i in sup_full]; los = [phi(i) for i in inf_full]
    # posição angular depois de fechar (phi muda pelo ângulo aplicado, com o sinal do eixo)
    sgn = 1.0 if abs(min(ups) + TS - max(los) - TI) < abs(min(ups) - TS - max(los) + TI) else -1.0
    up_closed = min(ups) + sgn * TS; lo_closed = max(los) + sgn * TI
    over = lo_closed - up_closed                       # >0: as bordas se sobrepõem
    TS_new = TS - sgn * (over - math.radians(0.3)) if over > 0 else TS
    REP['palpebras_ajuste_' + sd] = dict(sobreposicao_graus=round(math.degrees(over), 2), angulo_sup_antes=round(math.degrees(TS), 1), angulo_sup_depois=round(math.degrees(TS_new), 1))
    L['TS'] = TS = TS_new
    if os.environ.get('P2_RINGS'):
        for i in sorted(up, key=lambda i: (head.matrix_world @ hd.vertices[i].co - L['c']).length):
            r_ = ((head.matrix_world @ hd.vertices[i].co - L['c']).length - L['R']) * 1000
            print('RING', sd, 'sup', round(r_, 1), round(up[i] / TS, 2), round(math.degrees(phi(i)), 1))
        for i in sorted(lo, key=lambda i: (head.matrix_world @ hd.vertices[i].co - L['c']).length):
            r_ = ((head.matrix_world @ hd.vertices[i].co - L['c']).length - L['R']) * 1000
            print('RING', sd, 'inf', round(r_, 1), round(lo[i] / TI, 2), round(math.degrees(phi(i)), 1))
    REP['palpebras'][sd] = dict(angulo_sup_graus=round(math.degrees(TS), 1), angulo_inf_graus=round(math.degrees(TI), 1), vertices_sup=len(up), vertices_inf=len(lo))
# a shape key antiga sai (a piscada agora é por ossos); a Basis precisa acompanhar o deslocamento das camadas
for kb in list(KBk)[1:]: head.shape_key_remove(kb)
head.shape_key_remove(KBk['Basis'])
print('P2 OLHO', json.dumps(REP['olho_esferico']), json.dumps(REP['palpebras']), flush=True)

# ---- 1. olhos: uma malha por olho (globo, aro, pupila, brilho), pesada no osso
def sel(objs, act):
    for o in bpy.context.selected_objects: o.select_set(False)
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = act
OLHOS = {}
for sd in ('L', 'R'):
    parts = [bpy.data.objects[f'Kumo_v2_{n}_{sd}'] for n in ('Eye', 'PupilRing', 'Pupil', 'Highlight')]
    for p in parts:
        mw = p.matrix_world.copy(); p.parent = None; p.matrix_world = mw
    sel(parts, parts[0]); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True); bpy.ops.object.join()
    eye = bpy.context.view_layer.objects.active; eye.name = eye.data.name = f'Kumo_P2_Olho.{sd}'
    g = eye.vertex_groups.new(name=f'Eye.{sd}'); g.add(list(range(len(eye.data.vertices))), 1.0, 'REPLACE')
    eye.parent = rig; eye.matrix_parent_inverse = rig.matrix_world.inverted()
    m = eye.modifiers.new('Armature', 'ARMATURE'); m.object = rig
    OLHOS[sd] = eye
head.name = head.data.name = 'Kumo_P2_Cabeca'; rig.name = rig.data.name = 'Kumo_P2_Rig'
# ---- 2. quadro do Kumo
rig.matrix_world = M @ rig.matrix_world
sel([rig], rig); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for o in [head] + list(OLHOS.values()):
    sel([o], o); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bpy.context.view_layer.update()
pb = rig.pose.bones
# pesos: ≤4, soma 1
def pesos(o):
    bn = {b.name for b in rig.data.bones}; gi = {g.index: g.name for g in o.vertex_groups}; inf = []; su = []
    for v in o.data.vertices:
        ws = [g.weight for g in v.groups if gi[g.group] in bn and g.weight > 1e-4]; inf.append(len(ws)); su.append(sum(ws))
    return dict(vertices=len(o.data.vertices), max_influencias=max(inf), sem_peso=sum(1 for x in inf if x == 0), soma_fora_de_1=sum(1 for s in su if abs(s - 1) > 0.01))
REP['pesos'] = {o.name: pesos(o) for o in [head] + list(OLHOS.values())}
hm = head.data
REP['malha_cabeca'] = dict(vertices=len(hm.vertices), faces=len(hm.polygons), quads=sum(1 for p in hm.polygons if len(p.vertices) == 4),
                           tris=sum(1 for p in hm.polygons if len(p.vertices) == 3), ngons=sum(1 for p in hm.polygons if len(p.vertices) > 4),
                           ossos=[b.name for b in rig.data.bones])
print('P2', json.dumps(REP['pesos']), json.dumps(REP['malha_cabeca']), flush=True)

# ---- 2b. compensação do afundamento das dobras com peso parcial (shape keys ligadas ao giro do osso)
head.shape_key_add(name='Basis', from_mix=False)
gi_ = {g.index: g.name for g in head.vertex_groups}
COMP = {}
for sd in (('L', 'R') if os.environ.get('P2_COMP') else ()):
    for nm, TT in ((f'Palpebra_sup.{sd}', LID[sd]['TS']), (f'Palpebra_inf.{sd}', LID[sd]['TI'])):
        bone = rig.data.bones[nm]; c_ = bone.head_local.copy(); ax = (bone.matrix_local.to_3x3() @ Vector((1, 0, 0))).normalized()
        R1 = Matrix.Rotation(TT, 3, ax); kb = head.shape_key_add(name=f'Comp_{nm}', from_mix=False); kb.slider_min = 0; kb.slider_max = 1
        n_ = 0; mx = 0.0
        for v in hd.vertices:
            w = next((g.weight for g in v.groups if gi_[g.group] == nm), 0.0)
            if w <= 1e-3 or w >= 0.999: continue
            d_ = v.co - c_
            ideal = Matrix.Rotation(TT * w, 3, ax) @ d_; lbs = (1 - w) * d_ + w * (R1 @ d_)
            Mv = Matrix.Identity(3) * (1 - w) + R1 * w
            dr = Mv.inverted() @ (ideal - lbs); kb.data[v.index].co = v.co + dr; n_ += 1; mx = max(mx, dr.length)
        fc = kb.driver_add('value'); d = fc.driver; d.type = 'SCRIPTED'; var = d.variables.new(); var.name = 'a'; var.type = 'TRANSFORMS'
        t = var.targets[0]; t.id = rig; t.bone_target = nm; t.transform_type = 'ROT_X'; t.transform_space = 'LOCAL_SPACE'; t.rotation_mode = 'XYZ'
        d.expression = f'(a / {TT:.6f}) ** 2'
        COMP[nm] = dict(vertices=n_, deslocamento_max_mm=round(mx * 1000, 2), expressao=d.expression)
REP['compensacao_dobras'] = COMP
print('P2 COMP', json.dumps(COMP), json.dumps({k: v for k, v in REP.items() if k.startswith('palpebras_ajuste')}), flush=True)
hm = head.data

# ---- 3. testes
def reset():
    for b in pb: b.rotation_quaternion = (1, 0, 0, 0); b.rotation_euler = (0, 0, 0); b.location = (0, 0, 0)
    bpy.context.view_layer.update()
def lid(sd, v):
    for nm, TT in ((f'Palpebra_sup.{sd}', LID[sd]['TS']), (f'Palpebra_inf.{sd}', LID[sd]['TI'])):
        b = pb[nm]; b.rotation_mode = 'QUATERNION'; b.rotation_quaternion = Matrix.Rotation(TT * v, 4, 'X').to_quaternion()
    bpy.context.view_layer.update()
def geo(o):
    dg = bpy.context.evaluated_depsgraph_get(); ev = o.evaluated_get(dg); m = ev.to_mesh(); m.calc_loop_triangles()
    V = [ev.matrix_world @ v.co for v in m.vertices]; Tt = [tuple(t.vertices) for t in m.loop_triangles]; ev.to_mesh_clear(); return V, Tt
def depth(VA, TA, VB, TB, a, b):
    out = []
    for (V1, T1, x), (V2, T2, y) in (((VA, TA, a), (VB, TB, b)), ((VB, TB, b), (VA, TA, a))):
        p0, p1, p2 = (V1[i] for i in T1[x]); n = (p1 - p0).cross(p2 - p0)
        if n.length < 1e-12: return 0.0
        n.normalize(); ds = [n.dot(V2[i] - p0) for i in T2[y]]; out.append(min(max(0.0, max(ds)), max(0.0, -min(ds))))
    return min(out)
def cruz(oa, ob, base=None):
    bpy.context.view_layer.update(); VA, TA = geo(oa)
    if oa is ob:
        t = BVHTree.FromPolygons(VA, TA); P = {(a, b) for a, b in t.overlap(t) if a < b and not (set(TA[a]) & set(TA[b]))}; VB, TB = VA, TA
    else:
        VB, TB = geo(ob); P = set(BVHTree.FromPolygons(VA, TA).overlap(BVHTree.FromPolygons(VB, TB)))
    if base is not None: P -= base
    ds = [depth(VA, TA, VB, TB, a, b) for a, b in P]
    return P, dict(pares=len(P), reais=sum(1 for d in ds if d >= 0.0005), prof_max_mm=round(max(ds) * 1000, 2) if ds else 0.0)
def eye_rot(sd, yaw, pitch):
    b = pb[f'Eye.{sd}']; b.rotation_mode = 'XYZ'
    # osso do olho aponta para a frente (eixo Y do osso); guinada = giro em Z do mundo, arfagem = X do mundo
    bpy.context.view_layer.update(); Mb = b.matrix.copy(); h = Mb.to_translation()
    R = Matrix.Rotation(math.radians(yaw), 4, 'Z') @ Matrix.Rotation(math.radians(pitch), 4, 'X')
    b.matrix = Matrix.Translation(h) @ R @ Matrix.Translation(-h) @ Mb; bpy.context.view_layer.update()
def jaw(deg):
    b = pb['Jaw']; bpy.context.view_layer.update(); Mb = b.matrix.copy(); h = Mb.to_translation()
    b.matrix = Matrix.Translation(h) @ Matrix.Rotation(math.radians(deg), 4, 'X') @ Matrix.Translation(-h) @ Mb; bpy.context.view_layer.update()
def headrot(axis, deg):
    b = pb['Head']; bpy.context.view_layer.update(); Mb = b.matrix.copy(); h = Mb.to_translation()
    b.matrix = Matrix.Translation(h) @ Matrix.Rotation(math.radians(deg), 4, axis) @ Matrix.Translation(-h) @ Mb; bpy.context.view_layer.update()
reset(); BASE_H, _ = cruz(head, head); BASE_E = {sd: cruz(OLHOS[sd], head)[0] for sd in ('L', 'R')}
REP['repouso'] = dict(cabeca_propria=len(BASE_H), olho_cabeca={sd: cruz(OLHOS[sd], head)[1] for sd in ('L', 'R')})
TESTES = {}
def blink(v, sd=None):
    def f():
        for s in ('L', 'R'):
            if sd in (None, s): lid(s, v)
    return f
def comb(*fs):
    def f():
        for x in fs: x()
    return f
CASOS = {**{f'piscada_{int(v*100)}': blink(v) for v in (0.25, 0.5, 0.75, 1.0)},
         'olhar_dir_25': lambda: [eye_rot(s, -25, 0) for s in 'LR'], 'olhar_esq_25': lambda: [eye_rot(s, 25, 0) for s in 'LR'],
         'olhar_cima_15': lambda: [eye_rot(s, 0, 15) for s in 'LR'], 'olhar_baixo_15': lambda: [eye_rot(s, 0, -15) for s in 'LR'],
         'olhar_dir_25_piscada_50': comb(lambda: [eye_rot(s, -25, 0) for s in 'LR'], blink(0.5)),
         'olhar_baixo_15_piscada_100': comb(lambda: [eye_rot(s, 0, -15) for s in 'LR'], blink(1.0)),
         'piscada_so_esquerdo': blink(1.0, 'L'), 'piscada_so_esquerdo_25': blink(0.25, 'L'), 'piscada_so_esquerdo_50': blink(0.5, 'L'),
         'piscada_so_esquerdo_75': blink(0.75, 'L'), 'piscada_so_direito': blink(1.0, 'R'), 'piscada_so_direito_50': blink(0.5, 'R'),
         'esquerdo_fechado_direito_50': comb(blink(1.0, 'L'), blink(0.5, 'R')),
         'mandibula_10': lambda: jaw(10), 'mandibula_20': lambda: jaw(20),
         'cabeca_gira_30': lambda: headrot('Z', 30), 'cabeca_inclina_20': lambda: headrot('Y', 20),
         'tudo_junto': comb(lambda: headrot('Z', 30), lambda: jaw(15), lambda: [eye_rot(s, 20, 10) for s in 'LR'], blink(0.6))}
# ---- 3b. corretivas da piscada (mesmo método da mão: empurra para dentro da própria superfície, sem cruzar)
NVh = len(hd.vertices); adjh = [[] for _ in range(NVh)]
for e in hd.edges: a_, b_ = e.vertices; adjh[a_].append(b_); adjh[b_].append(a_)
gih = {g.index: g.name for g in head.vertex_groups}; BN = {b.name for b in rig.data.bones}
WH = [[(gih[g.group], g.weight) for g in v.groups if gih[g.group] in BN and g.weight > 1e-5] for v in hd.vertices]
def normais():
    dg = bpy.context.evaluated_depsgraph_get(); ev = head.evaluated_get(dg); m = ev.to_mesh(); N = [ev.matrix_world.to_3x3() @ v.normal for v in m.vertices]; ev.to_mesh_clear(); return N
def resolver_h(posefn, key, outras, iters=int(os.environ.get('P2_ITERS', '90')), margem=0.0004):
    hist = []
    for it in range(iters):
        reset(); posefn()
        for k_, v_ in outras: k_.value = v_
        key.value = 1.0; bpy.context.view_layer.update()
        P, info = cruz(head, head, BASE_H); hist.append(info)
        if not P: break
        VA, TA = geo(head); disp = np.zeros((NVh, 3)); cnt = np.zeros(NVh)
        for a_, b_ in P:
            d_ = depth(VA, TA, VA, TA, a_, b_)
            for x, y in ((a_, b_), (b_, a_)):
                q0, q1, q2 = (VA[i] for i in TA[y]); n = (q1 - q0).cross(q2 - q0)
                if n.length < 1e-12: continue
                n.normalize(); cx = sum((VA[i] for i in TA[x]), Vector()) / 3; sgn = 1.0 if n.dot(cx - q0) >= 0 else -1.0
                for i in TA[x]: disp[i] += np.array(tuple(n * sgn * (d_ / 2 + margem))); cnt[i] += 1
        m_ = cnt > 0; disp[m_] /= cnt[m_, None]
        for _ in range(2):
            nx = disp.copy()
            for i in range(NVh):
                if adjh[i] and not m_[i]: nx[i] = 0.5 * disp[adjh[i]].mean(0)
            disp = nx
        Mb = {b.name: (pb[b.name].matrix @ b.matrix_local.inverted()).to_3x3() for b in rig.data.bones}
        for i in np.nonzero(np.linalg.norm(disp, axis=1) > 1e-7)[0]:
            dv = Vector(disp[i].tolist())
            if dv.length > 0.003: dv = dv.normalized() * 0.003
            Mv = sum((Mb[n] * w for n, w in WH[i]), Matrix.Diagonal((0, 0, 0)))
            try: dr = Mv.inverted() @ dv
            except ValueError: continue
            key.data[i].co += dr
    reset()
    for k_, v_ in outras: k_.value = 0.0
    key.value = 0.0
    return dict(iteracoes=len(hist), inicio=hist[0], fim=hist[-1])
def driver_lid(key, sd, expr):
    fc = key.driver_add('value'); d = fc.driver; d.type = 'SCRIPTED'; var = d.variables.new(); var.name = 'a'; var.type = 'TRANSFORMS'
    t = var.targets[0]; t.id = rig; t.bone_target = f'Palpebra_sup.{sd}'; t.transform_type = 'ROT_X'; t.transform_space = 'LOCAL_SPACE'; t.rotation_mode = 'XYZ'
    d.expression = expr.replace('V', f'min(1.0, max(0.0, a / {LID[sd]["TS"]:.6f}))')
if not hm.shape_keys: head.shape_key_add(name='Basis', from_mix=False)
REP['corretivas_piscada'] = {}; CK = {}
for sd in ('L', 'R'):
    k1 = head.shape_key_add(name=f'Corretiva_Piscada.{sd}', from_mix=False)
    REP['corretivas_piscada'][f'fechada_{sd}'] = resolver_h(blink(1.0, sd), k1, [])
    k2 = head.shape_key_add(name=f'Corretiva_PiscadaMeio.{sd}', from_mix=False)
    REP['corretivas_piscada'][f'meio_{sd}'] = resolver_h(blink(0.5, sd), k2, [(k1, 0.5)])
    CK[sd] = (k1, k2)
    print('P2 CK', sd, json.dumps({k: v for k, v in REP['corretivas_piscada'].items() if k.endswith(sd)}), flush=True)
both = lambda v: comb(blink(v, 'L'), blink(v, 'R'))
kd1 = head.shape_key_add(name='Corretiva_PiscadaDupla', from_mix=False)
REP['corretivas_piscada']['dupla'] = resolver_h(both(1.0), kd1, [(CK['L'][0], 1.0), (CK['R'][0], 1.0)])
kd2 = head.shape_key_add(name='Corretiva_PiscadaDuplaMeio', from_mix=False)
REP['corretivas_piscada']['dupla_meio'] = resolver_h(both(0.5), kd2, [(CK['L'][0], 0.5), (CK['R'][0], 0.5), (CK['L'][1], 1.0), (CK['R'][1], 1.0), (kd1, 0.25)])
print('P2 CK dupla', json.dumps({k: v for k, v in REP['corretivas_piscada'].items() if k.startswith('dupla')}), flush=True)
for sd, (k1, k2) in CK.items():
    driver_lid(k1, sd, 'V'); driver_lid(k2, sd, '4 * V * (1 - V)')
def driver2(key, expr):
    fc = key.driver_add('value'); d = fc.driver; d.type = 'SCRIPTED'
    for sd in ('L', 'R'):
        var = d.variables.new(); var.name = 'a' + sd; var.type = 'TRANSFORMS'; t = var.targets[0]
        t.id = rig; t.bone_target = f'Palpebra_sup.{sd}'; t.transform_type = 'ROT_X'; t.transform_space = 'LOCAL_SPACE'; t.rotation_mode = 'XYZ'
        expr = expr.replace('V' + sd, f'min(1.0, max(0.0, a{sd} / {LID[sd]["TS"]:.6f}))')
    d.expression = expr
driver2(kd1, 'VL * VR'); driver2(kd2, '16 * VL * (1 - VL) * VR * (1 - VR)')
for nome, fn in CASOS.items():
    reset(); fn()
    _, ch = cruz(head, head, BASE_H)
    oc = {sd: cruz(OLHOS[sd], head, BASE_E[sd])[1] for sd in ('L', 'R')}
    TESTES[nome] = dict(cabeca_propria=ch, olho_cabeca=oc); print('P2T', nome, json.dumps(TESTES[nome]), flush=True)
REP['testes'] = TESTES
if os.environ.get('P2_DIAG'):
    import collections
    gi_ = {g.index: g.name for g in head.vertex_groups}
    def cls(i):
        ws = {gi_[g.group]: g.weight for g in hd.vertices[i].groups}
        s_ = max(ws.get('Palpebra_sup.L', 0), ws.get('Palpebra_sup.R', 0)); l_ = max(ws.get('Palpebra_inf.L', 0), ws.get('Palpebra_inf.R', 0))
        return 'sup%.1f' % s_ if s_ > 0 else ('inf%.1f' % l_ if l_ > 0 else 'fixo')
    for v_ in (0.25, 1.0):
        reset(); blink(v_)(); P, _ = cruz(head, head, BASE_H); VA, TA = geo(head)
        def tcls(t):
            cs = [cls(i) for i in TA[t]]; mv = [c_ for c_ in cs if c_ != 'fixo']
            return (max(mv) if mv else 'fixo') + ('/' + str(sum(1 for c_ in cs if c_ == 'fixo')) + 'fix')
        def where(t):
            p_ = sum((VA[i] for i in TA[t]), Vector()) / 3; L_ = LID['L' if p_.x > 0 else 'R']; d_ = p_ - L_['c']
            return 'r%+.0fmm_z%+.2f' % ((d_.length - L_['R']) * 1000, d_.z)
        c = collections.Counter(tuple(sorted((tcls(a), tcls(b)))) for a, b in P)
        print('P2W', v_, collections.Counter(where(a) + '|' + where(b) for a, b in list(P)[:400]).most_common(8))
        print('P2D', v_, c.most_common(12))
        mats = collections.Counter(tuple(sorted((hd.polygons[0].material_index,))) for _ in [0])

reset(); t0 = time.perf_counter()
for i in range(40):
    lid('L', (i % 10) / 10); pb['Jaw'].rotation_quaternion = Matrix.Rotation(math.radians(i % 20), 4, 'X').to_quaternion()
    bpy.context.view_layer.update(); bpy.context.evaluated_depsgraph_get()
REP['desempenho_ms'] = round((time.perf_counter() - t0) / 40 * 1000, 2); reset()
json.dump(REP, open(os.path.join(OUT, 'p2-medicoes.json'), 'w'), indent=1, default=str)
if FAST: print('P2 FAST OK'); raise SystemExit

# ---- 4. renders sobre o corpo do Kumo (cabeça antiga escondida)
sc.render.use_freestyle = False
with bpy.data.libraries.load(BODYB, link=False) as (src_, dst_):
    dst_.objects = [n for n in src_.objects if n in ('Kumo', 'Kumo_Rig')]
for o in dst_.objects: sc.collection.objects.link(o)
body = bpy.data.objects['Kumo']; brig = bpy.data.objects['Kumo_Rig']
img = bpy.data.images.get('kumo_quad_diffuse')
if img: img.filepath = os.path.join(REPO, 'textures', 'kumo_quad_diffuse.png'); img.reload()
gcab = body.vertex_groups.new(name='cabeca_antiga')
gcab.add([v.index for v in body.data.vertices if v.co.z > T['queixo_z'] + 0.02 and abs(v.co.x) < 0.62], 1.0, 'REPLACE')
mk = body.modifiers.new('EsconderCabecaAntiga', 'MASK'); mk.vertex_group = 'cabeca_antiga'; mk.invert_vertex_group = True
mk.show_viewport = mk.show_render = False
with bpy.context.temp_override(object=body): bpy.ops.object.modifier_move_to_index(modifier=mk.name, index=1)
# contorno da cabeça nova: casca invertida igual à do corpo
mo = bpy.data.materials['Kumo_Outline']; hd.materials.append(mo)
so = head.modifiers.new('Contorno', 'SOLIDIFY'); so.thickness = 0.012; so.offset = 1.0; so.use_flip_normals = True; so.material_offset = len(hd.materials) - 1
so.use_rim = False
sc.render.engine = 'CYCLES'; sc.cycles.samples = SAMPLES; sc.render.film_transparent = False
def cam(n, d, t, s_):
    c = bpy.data.objects.new(n, bpy.data.cameras.new(n)); sc.collection.objects.link(c); c.data.type = 'ORTHO'; c.data.ortho_scale = s_
    d = Vector(d).normalized(); c.location = Vector(t) + d * 6; c.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler(); return c
IDX = {}
def shoot(tag, cams_, vis, res=RES):
    sc.render.resolution_x = sc.render.resolution_y = res
    for o in bpy.data.objects:
        if o.type == 'MESH': o.hide_render = o.name not in vis
    for k_, c in cams_.items():
        sc.camera = c; f = os.path.join(OUT, 'renders', f'{tag}_{k_}.png'); sc.render.filepath = f; bpy.ops.render.render(write_still=True); IDX[f'{tag}|{k_}'] = f
CORPO = {'frente': cam('cf', (0, -1, 0), (0, 0, 0.98), 2.2), '34': cam('c34', (-0.57, -0.82, 0.05), (0, 0, 0.98), 2.2),
         'perfil': cam('cp', (-1, 0, 0), (0, 0, 0.98), 2.2), 'costas': cam('cc', (0, 1, 0), (0, 0, 0.98), 2.2)}
HC = Vector((0, T['y_centro'], T['queixo_z'] + 0.5 * k))
CAB = {'frente': cam('hf', (0, -1, 0), HC, 1.25), '34': cam('h34', (-0.57, -0.82, 0.05), HC, 1.25), 'perfil': cam('hp', (-1, 0, 0), HC, 1.25)}
P2VIS = {head.name, OLHOS['L'].name, OLHOS['R'].name}
reset()
shoot('atual_corpo', CORPO, {'Kumo'}); shoot('atual_cabeca', CAB, {'Kumo'})
mk.show_render = True
shoot('p2_corpo', CORPO, P2VIS | {'Kumo'}); shoot('p2_cabeca', CAB, P2VIS | {'Kumo'})
EXPR = {'neutro': lambda: None, 'piscada_50': blink(0.5), 'piscada_100': blink(1.0), 'so_esquerdo': blink(1.0, 'L'),
        'olhar_dir': lambda: [eye_rot(s_, -25, 0) for s_ in 'LR'], 'olhar_esq': lambda: [eye_rot(s_, 25, 0) for s_ in 'LR'],
        'olhar_cima': lambda: [eye_rot(s_, 0, 15) for s_ in 'LR'], 'boca_15': lambda: jaw(15), 'boca_20': lambda: jaw(20)}
for nm, fn in EXPR.items():
    reset(); fn(); shoot(f'expr_{nm}', {'frente': CAB['frente'], '34': CAB['34']}, P2VIS | {'Kumo'}, res=420)
reset(); mk.show_render = False
json.dump(IDX, open(os.path.join(OUT, 'renders', 'indice.json'), 'w'), indent=0)
for o in [o for o in bpy.data.objects if o.type == 'CAMERA']: bpy.data.objects.remove(o)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'kumo_p2_cabeca.blend'), copy=True, relative_remap=False)

# ---- 5. exportação da cabeça (rig + cabeça + olhos) e reimportação
for o in (body, brig): bpy.data.objects.remove(o)
so.show_viewport = so.show_render = False; head.modifiers.remove(so); hd.materials.pop(index=len(hd.materials) - 1)
act = bpy.data.actions.new('Teste_Exportacao'); rig.animation_data_create(); rig.animation_data.action = act
TQ = {1: 'neutro', 2: 'piscada_50', 3: 'piscada_100', 4: 'so_esquerdo', 5: 'olhar_dir', 6: 'boca_20'}
for f_, nm in TQ.items():
    sc.frame_set(f_); reset(); EXPR[nm]()
    for b in pb:
        b.keyframe_insert('rotation_quaternion', frame=f_); b.keyframe_insert('rotation_euler', frame=f_); b.keyframe_insert('location', frame=f_)
sc.frame_start, sc.frame_end = 1, 6
OBJS = [head, OLHOS['L'], OLHOS['R']]
def pos(o):
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get(); ev = o.evaluated_get(dg); m = ev.to_mesh()
    P = np.array([tuple(ev.matrix_world @ v.co) for v in m.vertices]); ev.to_mesh_clear(); return P
REF = {}
for f_ in TQ: sc.frame_set(f_); REF[f_] = {o.name: pos(o) for o in OBJS}
for o in bpy.context.selected_objects: o.select_set(False)
for o in OBJS + [rig]: o.select_set(True)
bpy.context.view_layer.objects.active = rig
glb = os.path.join(OUT, 'kumo_p2_cabeca.glb'); fbx = os.path.join(OUT, 'kumo_p2_cabeca.fbx')
bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', use_selection=True, export_apply=False, export_skins=True, export_animations=True,
                          export_all_influences=False, export_morph=True, export_morph_animation=True)
bpy.ops.export_scene.fbx(filepath=fbx, use_selection=True, add_leaf_bones=False, bake_anim=True, use_mesh_modifiers=False)
REP['exportacao_kb'] = dict(glb=round(os.path.getsize(glb) / 1024), fbx=round(os.path.getsize(fbx) / 1024))
def reimport(fn, imp):
    bpy.ops.wm.read_homefile(use_empty=True); imp(fn); s2 = bpy.context.scene
    TA = [a for a in bpy.data.actions if 'Teste_Exportacao' in a.name]
    def escolhe(idt, ok):
        for a in TA:
            for sl in a.slots:
                if sl.target_id_type == idt and ok(a, sl): return a, sl
        return None, None
    def liga(ad, a, sl):
        for t_ in list(ad.nla_tracks): ad.nla_tracks.remove(t_)
        ad.action = a; ad.action_slot = sl
    arm = next(o for o in s2.objects if o.type == 'ARMATURE'); liga(arm.animation_data_create(), *escolhe('OBJECT', lambda a, sl: True))
    meshes = {o.name.split('.')[0] + ('.' + o.name.split('.')[1] if o.name.split('.')[0].endswith('Olho') else ''): o for o in s2.objects if o.type == 'MESH'}
    meshes = {n: o for n, o in meshes.items() if n in REF[1]}
    for nm, o in meshes.items():
        if o.data.shape_keys:
            kn = o.data.shape_keys.name; a, sl = escolhe('KEY', lambda a, sl: sl.identifier == 'KE' + o.name or a.name.startswith(kn + '|'))
            if a: liga(o.data.shape_keys.animation_data_create(), a, sl)
    res = {}
    for nm, o in meshes.items():
        gg = {x.index: x.name for x in o.vertex_groups}; bn = {b.name for b in arm.data.bones}
        infl = [len([x for x in v.groups if gg[x.group] in bn and x.weight > 1e-4]) for v in o.data.vertices]
        r = dict(vertices=len(o.data.vertices), max_influencias=max(infl) if infl else 0, ossos=len(bn))
        s2.frame_set(1); P1 = pos(o); src = REF[1][nm]; kd = KDTree(len(src)); [kd.insert(Vector(p), i) for i, p in enumerate(src)]; kd.balance()
        mp = [kd.find(Vector(p))[1] for p in P1]; err = {}
        for f_ in TQ: s2.frame_set(f_); err[TQ[f_]] = round(float(np.linalg.norm(pos(o) - REF[f_][nm][mp], axis=1).max()) * 1000, 3)
        r['erro_max_mm'] = err; res[nm] = r
    return res
REP['glb_reimportado'] = reimport(glb, lambda f: bpy.ops.import_scene.gltf(filepath=f)); print('P2 GLB', json.dumps(REP['glb_reimportado']), flush=True)
REP['fbx_reimportado'] = reimport(fbx, lambda f: bpy.ops.import_scene.fbx(filepath=f, use_anim=True)); print('P2 FBX', json.dumps(REP['fbx_reimportado']), flush=True)
json.dump(REP, open(os.path.join(OUT, 'p2-medicoes.json'), 'w'), indent=1, default=str)
print('P2 OK')
