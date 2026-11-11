"""Kumo v6 · Braços ORIGINAIS com a técnica nova (pedido de 2026-11-11: manter os dois braços antigos e poder exportar para jogos).

  python repeso_bracos.py <kumo_rigged.blend> <pasta de saída>

- NÃO altera a malha: mesma geometria, mesmos vértices, mesma UV, mesma textura, mesmo contorno.
- Trabalha numa CÓPIA: grava <saída>/kumo_bracos_originais.blend; o kumo_rigged.blend oficial nunca é salvo.
- Troca só a DISTRIBUIÇÃO dos pesos entre upper_arm / forearm / hand (dos dois lados), pela técnica do P1:
  parâmetro ao longo do braço, janela de transição = razão × raio local, suavização sobre as arestas.
  A parte do peso que pertence a ossos fora do braço (ombro, peito) é preservada.
- Depois aplica a regra dos motores de jogo no corpo inteiro: no máximo 4 ossos por vértice e soma 1
  (só grupos de ossos; os grupos do contorno não são tocados).
- Mede antes/depois com o mesmo método da auditoria e testa a exportação glTF (+ reimportação) e FBX.
"""
import bpy, bmesh, sys, os, json, math, time
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

SRC, OUT = sys.argv[-2], sys.argv[-1]
os.makedirs(os.path.join(OUT, 'renders'), exist_ok=True)
RE = float(os.environ.get('BO_RE', '2.0')); RW = float(os.environ.get('BO_RW', '2.0'))
FAST = bool(os.environ.get('BO_FAST'))
bpy.ops.wm.open_mainfile(filepath=SRC)
REPO = os.path.dirname(os.path.abspath(SRC))
img = bpy.data.images['kumo_quad_diffuse']; img.filepath = os.path.join(REPO, 'textures', 'kumo_quad_diffuse.png'); img.reload()
sc = bpy.context.scene; rig = bpy.data.objects['Kumo_Rig']; body0 = bpy.data.objects['Kumo']; B = rig.data.bones
REP = dict(parametros=dict(razao_cotovelo=RE, razao_punho=RW))

# cópia do corpo (mesma malha, pesos novos); o original fica para comparar
body = body0.copy(); body.data = body0.data.copy(); body.name = 'Kumo_BracosOriginais'; body.data.name = 'Kumo_BracosOriginais'
sc.collection.objects.link(body)
me = body.data
BONES = {b.name for b in B}
gi = {g.index: g.name for g in body.vertex_groups}
gidx = {g.name: g.index for g in body.vertex_groups}

def smooth01(x):
    x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
def ss(x, a, b): return smooth01((x - a) / (b - a))

def lado(sd):
    up, fo, ha = B[f'upper_arm.{sd}'], B[f'forearm.{sd}'], B[f'hand.{sd}']
    S, E, W = up.head_local.copy(), fo.head_local.copy(), fo.tail_local.copy()
    dH = (ha.tail_local - ha.head_local).normalized() if ha.length > 1e-4 else (W - E).normalized()
    H = W + dH * 0.15                                     # cobre a mão em punho (o osso hand.L tem só 0,034)
    segs = [(S, E), (E, W), (W, H)]
    L = [(b - a).length for a, b in segs]; sE = L[0]; sW = L[0] + L[1]
    ARMB = (f'upper_arm.{sd}', f'forearm.{sd}', f'hand.{sd}')
    reg = []
    for v in me.vertices:
        ws = {gi[g.group]: g.weight for g in v.groups if gi[g.group] in BONES and g.weight > 0}
        tot = sum(ws.values()); A = sum(ws.get(n, 0) for n in ARMB)
        if tot > 0 and A / tot > 0.02: reg.append(v.index)
    def param(p):
        best = None; acc = 0.0
        for (a, b), l in zip(segs, L):
            ab = b - a; t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared)); d = (a + ab * t - p).length
            if best is None or d < best[0]: best = (d, acc + t * l)
            acc += l
        return best
    sp = {i: param(me.vertices[i].co) for i in reg}
    rE = sorted(d for i, (d, s_) in sp.items() if abs(s_ - sE) < 0.02); rE = rE[len(rE) // 2] if rE else 0.06
    rW = sorted(d for i, (d, s_) in sp.items() if abs(s_ - sW) < 0.02); rW = rW[len(rW) // 2] if rW else 0.05
    EW = min(RE * rE, 0.8 * min(L[0], L[1])); WW = min(RW * rW, 0.8 * L[1])
    EH = {i: [ss(s_, sE - EW, sE + EW), ss(s_, sW - WW, sW + WW * 0.5)] for i, (d, s_) in sp.items()}
    nb = {i: [] for i in EH}
    for e_ in me.edges:
        a_, b_ = e_.vertices
        if a_ in EH and b_ in EH: nb[a_].append(b_); nb[b_].append(a_)
    for it in range(12):
        EH = {i: [(EH[i][c] + sum(EH[j][c] for j in nb[i]) / len(nb[i])) / 2 if nb[i] else EH[i][c] for c in (0, 1)] for i in EH}
    for i, (e, h) in EH.items():
        v = me.vertices[i]
        ws = {gi[g.group]: g.weight for g in v.groups if gi[g.group] in BONES}
        tot = sum(ws.values()); A = sum(ws.get(n, 0) for n in ARMB) / tot
        new = {n: w / tot for n, w in ws.items() if n not in ARMB}
        new.update({ARMB[0]: A * (1 - e), ARMB[1]: A * e * (1 - h), ARMB[2]: A * e * h})
        for n in ARMB:
            if n not in gidx: continue
        for n, w in new.items():
            g = body.vertex_groups[n]
            if w > 1e-4: g.add([i], w, 'REPLACE')
            else: g.remove([i])
    return dict(vertices_regiao=len(reg), raio_cotovelo=round(rE, 4), raio_punho=round(rW, 4),
                janela_cotovelo=round(EW, 4), janela_punho=round(WW, 4), umero=round(L[0], 3), antebraco=round(L[1], 3))
REP['lado_E'] = lado('L'); REP['lado_D'] = lado('R')

def stats(o):
    infl = []; sums = []
    for v in o.data.vertices:
        ws = [g.weight for g in v.groups if gi[g.group] in BONES and g.weight > 1e-4]; infl.append(len(ws)); sums.append(sum(ws))
    return dict(max_influencias=max(infl), vertices_mais_de_4=sum(1 for x in infl if x > 4), sem_peso=sum(1 for x in infl if x == 0),
                soma_fora_de_1=sum(1 for s in sums if abs(s - 1) > 0.01))
REP['pesos_original'] = stats(body0)
# regra de motor de jogo: no máximo 4 ossos e soma 1 (só grupos de osso; o contorno não é tocado)
for o in bpy.context.selected_objects: o.select_set(False)
body.select_set(True); bpy.context.view_layer.objects.active = body
bpy.ops.object.vertex_group_limit_total(group_select_mode='BONE_DEFORM', limit=4)
bpy.ops.object.vertex_group_normalize_all(group_select_mode='BONE_DEFORM', lock_active=False)
REP['pesos_novo'] = stats(body)

# ------------------------------------------------------------------ testes (mesmo método da auditoria), braço E e D
OUTL = [(o, m) for o in (body0, body) for m in o.modifiers if m.type in ('SOLIDIFY', 'VERTEX_WEIGHT_MIX', 'MASK')]
for o, m in OUTL: m.show_viewport = False
bpy.context.view_layer.update()
def dom(v, o):
    g_ = {g.index: g.name for g in o.vertex_groups}
    ws = [(g_[g.group], g.weight) for g in v.groups if g_[g.group] in BONES]
    return max(ws, key=lambda x: x[1])[0] if ws else None
def regiao(sd):   # mesma região da auditoria, definida pelos pesos ORIGINAIS para os dois objetos
    vs = {v.index for v in body0.data.vertices if dom(v, body0) in (f'upper_arm.{sd}', f'forearm.{sd}', f'hand.{sd}')}
    fs = {p.index for p in body0.data.polygons if all(i in vs for i in p.vertices)}
    return fs, vs
def tri_data(obj, region, region_v):
    dg = bpy.context.evaluated_depsgraph_get(); ev = obj.evaluated_get(dg); m = ev.to_mesh(); m.calc_loop_triangles()
    V = [ev.matrix_world @ v.co for v in m.vertices]
    T = [tuple(t.vertices) for t in m.loop_triangles if t.polygon_index in region]
    E_ = [(e.vertices[0], e.vertices[1]) for e in m.edges if e.vertices[0] in region_v and e.vertices[1] in region_v]
    ev.to_mesh_clear(); return V, T, E_
def self_pairs(V, T):
    b = BVHTree.FromPolygons(V, T); return {(a_, b_) for a_, b_ in b.overlap(b) if a_ < b_ and not (set(T[a_]) & set(T[b_]))}
def depth(V, T, pair):
    out = []
    for x, y in (pair, pair[::-1]):
        a0, a1, a2 = (V[i] for i in T[x]); n = (a1 - a0).cross(a2 - a0)
        if n.length < 1e-12: return 0.0
        n.normalize(); ds = [n.dot(V[i] - a0) for i in T[y]]; out.append(min(max(0.0, max(ds)), max(0.0, -min(ds))))
    return min(out)
TOL = 0.0005
def classify(V, T, pairs):
    pairs = list(pairs); ds = [depth(V, T, p) for p in pairs]
    tri = {t for p, d in zip(pairs, ds) if d >= TOL for t in p}
    area = sum(((V[T[t][1]] - V[T[t][0]]).cross(V[T[t][2]] - V[T[t][0]])).length / 2 for t in tri)
    return dict(reais=sum(1 for d in ds if d >= TOL), rasantes=sum(1 for d in ds if d < TOL), prof_max_mm=round(max(ds) * 1000, 2) if ds else 0.0,
                area_cm2=round(area * 1e4, 2))
def reset():
    for pb in rig.pose.bones:
        pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()
def rot_world(name, axis, deg):
    pb = rig.pose.bones[name]; bpy.context.view_layer.update(); M = pb.matrix.copy(); h = M.to_translation()
    pb.matrix = Matrix.Translation(h) @ Matrix.Rotation(math.radians(deg), 4, Vector(axis).normalized()) @ Matrix.Translation(-h) @ M
    bpy.context.view_layer.update()
def bdir(n): pb = rig.pose.bones[n]; return (pb.tail - pb.head).normalized()
def bend(n): return bdir(n).cross(Vector((0, -1, 0))).normalized()
def side(n): return bdir(n).cross(bend(n)).normalized()
def poses(sd):
    sg = 1 if sd == 'L' else -1
    return {
        'braco_horizontal': [(f'upper_arm.{sd}', (0, 1, 0), -45 * sg)],
        'braco_para_frente_90': [(f'upper_arm.{sd}', (1, 0, 0), -90)],
        'braco_para_tras_40': [(f'upper_arm.{sd}', (1, 0, 0), 40)],
        'braco_torcao_45': [(f'upper_arm.{sd}', 'TWIST', 45)],
        'cotovelo_45': [(f'forearm.{sd}', 'BEND', 45)], 'cotovelo_90': [(f'forearm.{sd}', 'BEND', 90)],
        'cotovelo_100': [(f'forearm.{sd}', 'BEND', 100)], 'cotovelo_115': [(f'forearm.{sd}', 'BEND', 115)],
        'antebraco_torcao_60': [(f'forearm.{sd}', 'TWIST', 60)],
        'punho_45': [(f'hand.{sd}', 'BEND', 45)], 'punho_menos45': [(f'hand.{sd}', 'BEND', -45)],
        'punho_lateral_30': [(f'hand.{sd}', 'SIDE', 30)], 'punho_lateral_menos30': [(f'hand.{sd}', 'SIDE', -30)],
        'cotovelo_90_punho_45': [(f'forearm.{sd}', 'BEND', 90), (f'hand.{sd}', 'BEND', 45)],
    }
def apply(steps):
    for n, ax, deg in steps:
        axis = bend(n) if ax == 'BEND' else side(n) if ax == 'SIDE' else bdir(n) if ax == 'TWIST' else ax
        rot_world(n, axis, deg)
def mao_seguimento(obj, sd, steps):
    """quanto a mão acompanha o osso da mão: deslocamento médio dos vértices da mão em relação ao movimento rígido do osso (mm)"""
    reset(); dg = bpy.context.evaluated_depsgraph_get(); ev = obj.evaluated_get(dg); m = ev.to_mesh()
    W = B[f'forearm.{sd}'].tail_local; d = (B[f'forearm.{sd}'].tail_local - B[f'forearm.{sd}'].head_local).normalized()
    ids = [v.index for v in m.vertices if (v.co - W).dot(d) > 0.01 and (v.co - W).length < 0.15]
    P0 = {i: ev.matrix_world @ m.vertices[i].co for i in ids}; ev.to_mesh_clear()
    M0 = rig.pose.bones[f'hand.{sd}'].matrix.copy()
    apply(steps); M1 = rig.pose.bones[f'hand.{sd}'].matrix.copy()
    dg = bpy.context.evaluated_depsgraph_get(); ev = obj.evaluated_get(dg); m = ev.to_mesh()
    R = rig.matrix_world @ M1 @ M0.inverted() @ rig.matrix_world.inverted()
    err = [((ev.matrix_world @ m.vertices[i].co) - (R @ P0[i])).length for i in ids]; ev.to_mesh_clear(); reset()
    return round(sum(err) / max(len(err), 1) * 1000, 1)
res = {}
for sd in ('L', 'R'):
    fs, vs = regiao(sd); base = {}
    for tag, obj in (('original', body0), ('novo', body)):
        reset(); V0, T0, E0 = tri_data(obj, fs, vs); base[tag] = (V0, T0, E0, self_pairs(V0, T0), [(V0[a] - V0[b]).length for a, b in E0])
    rows = {}
    for pname, steps in poses(sd).items():
        row = {}
        for tag, obj in (('original', body0), ('novo', body)):
            V0, T0, E0, rest, L0 = base[tag]
            reset(); apply(steps); V, T, E_ = tri_data(obj, fs, vs); new = self_pairs(V, T) - rest
            ratio = sorted((V[a] - V[b]).length / l for (a, b), l in zip(E_, L0) if l > 1e-7)
            row[tag] = dict(pares_novos=len(new), **classify(V, T, new), compressao_min=round(ratio[0], 3), esticamento_max=round(ratio[-1], 3))
        res[pname] = row
    for pname in ('punho_45', 'punho_lateral_30'):
        for tag, obj in (('original', body0), ('novo', body)):
            res[pname][tag]['mao_desvio_do_osso_mm'] = mao_seguimento(obj, sd, poses(sd)[pname])
    REP['testes_' + ('E' if sd == 'L' else 'D')] = res; res = {}
    REP['repouso_' + ('E' if sd == 'L' else 'D')] = {t: len(base[t][3]) for t in base}
reset()
def perf(obj):
    other = body if obj is body0 else body0; other.hide_viewport = True
    pb = rig.pose.bones['forearm.L']; t0 = time.perf_counter(); N = 40
    for i in range(N):
        pb.rotation_euler = (math.radians(i), 0, 0); bpy.context.view_layer.update(); bpy.context.evaluated_depsgraph_get()
    dt = (time.perf_counter() - t0) / N * 1000; pb.rotation_euler = (0, 0, 0); other.hide_viewport = False; return round(dt, 2)
REP['desempenho_ms'] = dict(original=perf(body0), novo=perf(body))
for o, m in OUTL: m.show_viewport = True
bpy.context.view_layer.update()
if FAST:
    print('FAST', json.dumps({k: REP[k] for k in ('lado_E', 'lado_D', 'pesos_novo', 'repouso_E', 'repouso_D')}))
    for sdk in ('testes_E', 'testes_D'):
        for p_, r_ in REP[sdk].items(): print('FAST', sdk[-1], p_, {t: (x['pares_novos'], x['reais'], x['prof_max_mm'], x['compressao_min'], x.get('mao_desvio_do_osso_mm')) for t, x in r_.items()})
    raise SystemExit

# ------------------------------------------------------------------ renders comparativos (mesmas poses, original × novo)
sc.render.engine = 'CYCLES'; sc.cycles.samples = 16; sc.render.film_transparent = False; sc.render.resolution_x = 520; sc.render.resolution_y = 620
def cam(n, d, t, s):
    c = bpy.data.objects.new(n, bpy.data.cameras.new(n)); sc.collection.objects.link(c); c.data.type = 'ORTHO'; c.data.ortho_scale = s
    d = Vector(d).normalized(); c.location = Vector(t) + d * 5; c.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler(); return c
CF = cam('cf', (0, -1, 0), (0, 0, 0.62), 1.15); CL = cam('cl', (1, 0, 0), (0, 0, 0.62), 1.15)
RP = {'repouso': [], 'cotovelo_100': poses('L')['cotovelo_100'] + poses('R')['cotovelo_100'],
      'punho_45': poses('L')['punho_45'] + poses('R')['punho_menos45'], 'cotovelo_90_punho_45': poses('L')['cotovelo_90_punho_45'] + poses('R')['cotovelo_90_punho_45']}
for pname, steps in RP.items():
    for tag, obj in (('original', body0), ('novo', body)):
        for o in bpy.data.objects:
            if o.type == 'MESH': o.hide_render = o.name != obj.name
        reset(); apply(steps)
        for k, c in (('frente', CF), ('lado', CL)):
            sc.camera = c; sc.render.filepath = os.path.join(OUT, 'renders', f'{tag}_{pname}_{k}.png'); bpy.ops.render.render(write_still=True)
reset()

# ------------------------------------------------------------------ cópia para jogos + teste de exportação
for o in list(bpy.data.objects):
    if o.name not in ('Kumo_BracosOriginais', 'Kumo_Rig'): bpy.data.objects.remove(o)
body.name = 'Kumo'; body.data.name = 'Kumo'
blend = os.path.join(OUT, 'kumo_bracos_originais.blend')
bpy.ops.wm.save_as_mainfile(filepath=blend, copy=True, relative_remap=False)
# animação de teste (para comparar Blender × arquivo exportado)
act = bpy.data.actions.new('Teste_Exportacao'); rig.animation_data_create(); rig.animation_data.action = act
TESTE = {1: [], 2: RP['cotovelo_90_punho_45'], 3: poses('L')['braco_horizontal'] + poses('R')['antebraco_torcao_60'] + poses('L')['punho_lateral_30']}
for f, steps in TESTE.items():
    sc.frame_set(f); reset(); apply(steps)
    for pb in rig.pose.bones:
        pb.keyframe_insert('rotation_euler', frame=f); pb.keyframe_insert('location', frame=f)
sc.frame_start, sc.frame_end = 1, 3
def posicoes(obj, f):
    sc.frame_set(f); bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg); m = ev.to_mesh(); P = [ev.matrix_world @ v.co for v in m.vertices]; ev.to_mesh_clear(); return P
for m in body.modifiers:
    if m.type != 'ARMATURE': m.show_viewport = False     # contorno: em jogo vira material/shader, não geometria exportada
REF = {f: posicoes(body, f) for f in TESTE}
for o in bpy.context.selected_objects: o.select_set(False)
body.select_set(True); rig.select_set(True); bpy.context.view_layer.objects.active = rig
glb = os.path.join(OUT, 'kumo_bracos_originais.glb'); fbx = os.path.join(OUT, 'kumo_bracos_originais.fbx')
bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', use_selection=True, export_apply=False, export_skins=True,
                          export_animations=True, export_all_influences=False)
bpy.ops.export_scene.fbx(filepath=fbx, use_selection=True, add_leaf_bones=False, bake_anim=True, use_mesh_modifiers=False)
REP['exportacao'] = dict(glb_kb=round(os.path.getsize(glb) / 1024), fbx_kb=round(os.path.getsize(fbx) / 1024))
# reimporta o GLB numa cena limpa e compara a deformação quadro a quadro
bpy.ops.wm.read_homefile(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
sc = bpy.context.scene
mesh = [o for o in sc.objects if o.type == 'MESH'][0]; arm = [o for o in sc.objects if o.type == 'ARMATURE'][0]
bn = {b.name for b in arm.data.bones}; gi2 = {g.index: g.name for g in mesh.vertex_groups}
infl = [len([g for g in v.groups if gi2[g.group] in bn and g.weight > 1e-4]) for v in mesh.data.vertices]
sums = [sum(g.weight for g in v.groups if gi2[g.group] in bn) for v in mesh.data.vertices]
ad = arm.animation_data; acts = list(bpy.data.actions)
REP['glb_reimportado'] = dict(vertices=len(mesh.data.vertices), ossos=len(bn), max_influencias=max(infl),
                              soma_fora_de_1=sum(1 for s in sums if abs(s - 1) > 0.01), acoes=[a.name for a in acts])
teste = [a for a in acts if a.name.startswith('Teste_Exportacao')]   # o arquivo oficial também traz a ação Pose_Apresentacao
if ad is None: ad = arm.animation_data_create()
for t_ in list(ad.nla_tracks): ad.nla_tracks.remove(t_)
ad.action = teste[0]
REP['glb_reimportado']['acao_comparada'] = teste[0].name
rest = posicoes(mesh, 1)
kd = KDTree(len(REF[1])); [kd.insert(p, i) for i, p in enumerate(REF[1])]; kd.balance()
mp = [kd.find(p)[1] for p in rest]
err = {}
for f in TESTE:
    P = posicoes(mesh, f); e = [(P[i] - REF[f][mp[i]]).length for i in range(len(P))]
    err[f] = dict(medio_mm=round(sum(e) / len(e) * 1000, 3), max_mm=round(max(e) * 1000, 3))
REP['glb_deformacao_vs_blender'] = err
json.dump(REP, open(os.path.join(OUT, 'medicoes.json'), 'w'), indent=1, default=str)
print('BO OK')
