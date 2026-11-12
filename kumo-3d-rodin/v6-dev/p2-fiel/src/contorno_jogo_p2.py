"""Kumo v6 · contorno sem lascas entre os dedos + contorno exportável para jogos (autorizado em 2026-11-11).

  python contorno_jogo.py <kumo_maos_corretivas.blend> <pasta de saída>

1. Espessura do contorno por vértice (grupo 'outline_espessura'): onde a superfície tem outra logo à frente (fenda entre
   dedos, palma na mão fechada), a casca afina para caber na fenda. Medido por raio na direção da normal, no repouso e
   nas poses de mão fechada/aberta/polegar/alternados; vale o menor. O Solidify do Blender passa a usar esse grupo.
2. 'Kumo_Contorno': casca invertida como malha própria (mesma espessura, faces viradas, material preto sem luz com
   backface culling), com os mesmos pesos e as mesmas shape keys + drivers. Exporta para glTF/FBX e funciona em qualquer
   motor sem shader especial. O corpo exportado vai sem o Solidify.
3. Renders (antes/depois do contorno; contorno do Blender contra o de jogo), exportação GLB/FBX, reimportação e comparação.
"""
import bpy, bmesh, sys, os, json, math, time
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
sys.path.insert(0, "/home/user/Kumo-Character/kumo-3d-rodin/v6-dev/maos-corretivas/src")
from kumo_lib import Kumo
SRC, OUT = sys.argv[-2], sys.argv[-1]; os.makedirs(os.path.join(OUT, 'renders'), exist_ok=True)
REPO = '/home/user/Kumo-Character/kumo-3d-rodin'
bpy.ops.wm.open_mainfile(filepath=SRC); sc = bpy.context.scene
# P2: as texturas já apontam para p2-fiel/textures
olhos = bpy.data.objects.get('Kumo_Olhos')
rig = bpy.data.objects['Kumo_Rig']; body = bpy.data.objects['Kumo']; me = body.data; pb = rig.pose.bones
K = Kumo(rig, body); NV = len(me.vertices)
SOL = next(m for m in body.modifiers if m.type == 'SOLIDIFY'); TH = SOL.thickness
OUTL = [m for m in body.modifiers if m.type != 'ARMATURE']
def outline(on):
    for m in OUTL: m.show_viewport = on; m.show_render = on
    bpy.context.view_layer.update()
REP = dict(espessura_contorno_m=TH)
adj = [[] for _ in range(NV)]
for e in me.edges: a, b = e.vertices; adj[a].append(b); adj[b].append(a)

# ----- 1. espessura por vértice
outline(False)
fac = np.ones(NV); gap_min = np.full(NV, np.inf)
mao = set()
for sd in ('L', 'R'): mao |= K.regiao(sd)[1]
def medir():
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get(); ev = body.evaluated_get(dg); m = ev.to_mesh(); m.calc_loop_triangles()
    V = [v.co.copy() for v in m.vertices]; N = [v.normal.copy() for v in m.vertices]
    tree = BVHTree.FromPolygons(V, [tuple(t.vertices) for t in m.loop_triangles]); ev.to_mesh_clear()
    for i in mao:
        n = N[i]
        # normal para fora: a mesma orientação usada na corretiva (eixo do osso dominante)
        o = V[i] + n * 0.0004; hit = tree.ray_cast(o, n, 0.05)
        if hit[0] is not None: gap_min[i] = min(gap_min[i], hit[3] + 0.0004)
# distância até a peça vizinha (outro dedo, polegar; ponta dos dedos contra a palma), com KDTree por cadeia
from mathutils.kdtree import KDTree as _KD
def cadeia(n):
    if n is None: return None
    if n.startswith('dedo'): return n[:5]
    if n.startswith('polegar'): return 'polegar'
    return 'palma'
DOMI = {i: K.dominante(me.vertices[i]) for i in mao}
def vizinhos():
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get(); ev = body.evaluated_get(dg); m = ev.to_mesh()
    V = {i: m.vertices[i].co.copy() for i in mao}; ev.to_mesh_clear()
    for sd in ('L', 'R'):
        vs = [i for i in mao if DOMI[i] and DOMI[i].endswith('.' + sd)]
        grupos = {}
        for i in vs: grupos.setdefault(cadeia(DOMI[i]), []).append(i)
        for c, lst in grupos.items():
            outros = [j for c2, l2 in grupos.items() if c2 != c and c2 != 'palma' and c != 'palma' for j in l2]
            if c == 'palma': outros = [j for j in vs if DOMI[j].startswith('dedo') and DOMI[j].split('.')[0].endswith('_2')]
            elif c != 'polegar': outros += [j for j in vs if cadeia(DOMI[j]) == 'palma' and False]
            if not outros: continue
            kd = _KD(len(outros)); [kd.insert(V[j], k) for k, j in enumerate(outros)]; kd.balance()
            for i in lst:
                if c != 'palma' or True:
                    _, _, d = kd.find(V[i]); gap_min[i] = min(gap_min[i], d)
POSES = ['repouso', 'mao_fechada', 'mao_aberta', 'polegar', 'dedos_alternados', 'fechar_50']
for sd in ('L', 'R'):
    for pn_ in POSES:
        K.reset()
        if pn_ != 'repouso': K.poses(sd)[pn_]()
        medir(); vizinhos()
K.reset()
# a casca de cada lado da fenda pode ocupar ~45% dela
for i in mao:
    if np.isfinite(gap_min[i]): fac[i] = min(1.0, max(0.12, gap_min[i] * 0.45 / TH))
for _ in range(3):
    nxt = fac.copy()
    for i in mao:
        if adj[i]: nxt[i] = min(fac[i], 0.5 * fac[i] + 0.5 * sum(fac[j] for j in adj[i]) / len(adj[i]))
    fac = nxt
g = body.vertex_groups.get('outline_espessura') or body.vertex_groups.new(name='outline_espessura')
for i in range(NV): g.add([i], float(fac[i]), 'REPLACE')
K.gi = {gg.index: gg.name for gg in body.vertex_groups}
REG = {sd: K.regiao(sd)[1] for sd in ('L', 'R')}
REP['espessura'] = dict(vertices_afinados=int((fac < 0.999).sum()), fator_min=round(float(fac.min()), 3),
                        fator_medio_na_mao=round(float(np.mean([fac[i] for i in mao])), 3))
SOL_ANTES = dict(vertex_group=SOL.vertex_group, thickness_vertex_group=SOL.thickness_vertex_group)

# ----- renders do contorno (antes/depois)
sc.render.engine = 'CYCLES'; sc.cycles.samples = int(os.environ.get('CJ_SAMPLES', '16')); sc.render.resolution_x = sc.render.resolution_y = 480
def cam(n, d, t, s_):
    c = bpy.data.objects.new(n, bpy.data.cameras.new(n)); sc.collection.objects.link(c); c.data.type = 'ORTHO'; c.data.ortho_scale = s_
    d = Vector(d).normalized(); c.location = Vector(t) + d * 5; c.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler(); return c
def centro_mao(sd):
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get(); ev = body.evaluated_get(dg); m = ev.to_mesh()
    vs = [i for i in REG[sd] if K.dominante(me.vertices[i]) != f'forearm.{sd}']
    P = np.array([tuple(m.vertices[i].co) for i in vs]); ev.to_mesh_clear(); return Vector(((P.min(0) + P.max(0)) / 2).tolist())
def cams(sd, tag):
    m = K.MAOS[sd]; sx = 1 if sd == 'L' else -1; hc = centro_mao(sd)
    Q = pb[f'hand.{sd}'].matrix.to_3x3() @ rig.data.bones[f'hand.{sd}'].matrix_local.to_3x3().inverted()
    return {'frente': cam(f'f{tag}', (0, -1, 0), hc, 0.30), 'perspectiva': cam(f'q{tag}', (0.4 * sx, -1, 0.25), hc, 0.30),
            'dorso': cam(f'd{tag}', -(Q @ m['pn']), hc, 0.30), 'palma': cam(f'p{tag}', (Q @ m['pn']), hc, 0.30)}
IDX = {}
def shoot(tag, C, visiveis):
    for o in bpy.data.objects:
        if o.type == 'MESH': o.hide_render = o.name not in visiveis
    for k, c in C.items():
        sc.camera = c; f = os.path.join(OUT, 'renders', f'{tag}_{k}.png'); sc.render.filepath = f; bpy.ops.render.render(write_still=True); IDX[f'{tag}|{k}'] = f
outline(True)
for sd in ('L', 'R'):
    for pose in ('repouso', 'mao_fechada', 'mao_aberta'):
        K.reset()
        if pose != 'repouso': K.poses(sd)[pose]()
        C = cams(sd, f'{sd}{pose}')
        SOL.vertex_group = SOL_ANTES['vertex_group']; bpy.context.view_layer.update(); shoot(f'{sd}_{pose}_contorno_antes', C, {'Kumo'})
        SOL.vertex_group = 'outline_espessura'; SOL.thickness_vertex_group = 0.0; bpy.context.view_layer.update(); shoot(f'{sd}_{pose}_contorno_depois', C, {'Kumo', 'Kumo_Olhos'})
        IDX[f'cams|{sd}|{pose}'] = [c.name for c in C.values()]
K.reset()

# ----- 2. malha de contorno para jogos
outline(False)
hull = body.copy(); hull.data = me.copy(); hull.name = hull.data.name = 'Kumo_Contorno'; sc.collection.objects.link(hull)
for m in list(hull.modifiers):
    if m.type != 'ARMATURE': hull.modifiers.remove(m)
hm = hull.data
# normais de repouso (sem shape key) e deslocamento igual em todas as keys
bm = bmesh.new(); bm.from_mesh(hm); bm.normal_update(); NR = [v.normal.copy() for v in bm.verts]; bm.free()
gi = {gg.index: gg.name for gg in hull.vertex_groups}
def w(v, name): return next((x.weight for x in v.groups if gi[x.group] == name), 0.0)
offs = [NR[i] * TH * fac[i] * (1.0 if SOL.offset >= 0 else -1.0) for i in range(NV)]
for kb in hm.shape_keys.key_blocks:
    for i in range(NV): kb.data[i].co += offs[i]
for i, v in enumerate(hm.vertices): v.co += offs[i]
# drivers das keys copiados do corpo
ad = me.shape_keys.animation_data
if ad:
    for fc in ad.drivers:
        nf = hm.shape_keys.driver_add(fc.data_path); nf.driver.type = fc.driver.type; nf.driver.expression = fc.driver.expression
        for v in fc.driver.variables:
            nv = nf.driver.variables.new(); nv.name = v.name; nv.type = v.type
            for a, b in zip(v.targets, nv.targets):
                b.id = a.id; b.bone_target = a.bone_target; b.transform_type = a.transform_type; b.transform_space = a.transform_space; b.rotation_mode = a.rotation_mode
# remove o que o Blender recorta (outline_cut) e vira as faces
bm = bmesh.new(); bm.from_mesh(hm); dl = bm.verts.layers.deform.active
cut = next(gg.index for gg in hull.vertex_groups if gg.name == 'outline_cut')
corta = [v for v in bm.verts if dl and v[dl].get(cut, 0.0) > 0.0]
bmesh.ops.delete(bm, geom=corta, context='VERTS'); bmesh.ops.reverse_faces(bm, faces=bm.faces[:]); bm.to_mesh(hm); bm.free()
mat = bpy.data.materials.new('Kumo_Contorno_Jogo'); mat.use_nodes = True; nt = mat.node_tree; nt.nodes.clear()
em = nt.nodes.new('ShaderNodeEmission'); outn = nt.nodes.new('ShaderNodeOutputMaterial')
ref = bpy.data.materials['Kumo_Outline']; cor = next((n.inputs[0].default_value[:] for n in ref.node_tree.nodes if n.type == 'EMISSION'), (0.2, 0.1, 0.06, 1))
em.inputs[0].default_value = cor; em.inputs[1].default_value = 1.0; nt.links.new(em.outputs[0], outn.inputs[0])
mat.use_backface_culling = True
hm.materials.clear(); hm.materials.append(mat)
for p in hm.polygons: p.material_index = 0
REP['contorno_jogo'] = dict(vertices=len(hm.vertices), faces=len(hm.polygons), cor_rgb=[round(x, 3) for x in cor[:3]], removidos_pelo_corte=len(corta))
# testes: o contorno de jogo acompanha o do Blender? (posição da casca nas poses)
outline(True)
def pos(o):
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get(); ev = o.evaluated_get(dg); m = ev.to_mesh()
    P = np.array([tuple(ev.matrix_world @ v.co) for v in m.vertices]); ev.to_mesh_clear(); return P
from mathutils.kdtree import KDTree
cmp_ = {}
for pose in ('repouso', 'mao_fechada', 'mao_aberta', 'cotovelo_90_punho_45_mao_fechada'):
    K.reset()
    if pose != 'repouso': K.poses('L')[pose](); K.poses('R')[pose]()
    A = pos(body); Bh = pos(hull)
    kd = KDTree(len(A)); [kd.insert(Vector(p), i) for i, p in enumerate(A)]; kd.balance()
    d = np.array([kd.find(Vector(p))[2] for p in Bh])
    cmp_[pose] = dict(dist_max_mm=round(float(d.max()) * 1000, 3), dist_p99_mm=round(float(np.percentile(d, 99)) * 1000, 3))
REP['contorno_jogo_vs_solidify'] = cmp_
K.reset()
for sd in ('L', 'R'):
    for pose in ('repouso', 'mao_fechada'):
        K.reset()
        if pose != 'repouso': K.poses(sd)[pose]()
        C = {k: bpy.data.objects[n] for k, n in zip(('frente', 'perspectiva', 'dorso', 'palma'), IDX[f'cams|{sd}|{pose}'])}
        for m in OUTL: m.show_render = False
        hm.materials[0] = bpy.data.materials['Kumo_Outline']
        shoot(f'{sd}_{pose}_contorno_jogo', C, {'Kumo', 'Kumo_Contorno', 'Kumo_Olhos'})
        hm.materials[0] = mat
        for m in OUTL: m.show_render = True
K.reset()
CORPO = {'frente': cam('cf', (0, -1, 0), (0, 0, 0.98), 2.15), 'perspectiva': cam('c34', (0.6, -1, 0.1), (0, 0, 0.98), 2.15)}
shoot('corpo_blender', CORPO, {'Kumo', 'Kumo_Olhos'})
for m in OUTL: m.show_render = False
hm.materials[0] = bpy.data.materials['Kumo_Outline']
shoot('corpo_jogo', CORPO, {'Kumo', 'Kumo_Contorno', 'Kumo_Olhos'})
hm.materials[0] = mat
for m in OUTL: m.show_render = True
json.dump(IDX, open(os.path.join(OUT, 'renders', 'indice.json'), 'w'), indent=0)
for o in [o for o in bpy.data.objects if o.type == 'CAMERA']: bpy.data.objects.remove(o)
outline(True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'kumo_v6_p2_jogo.blend'), copy=True, relative_remap=False)

# ----- 3. exportação (corpo sem Solidify + Kumo_Contorno) e reimportação
act = bpy.data.actions.new('Teste_Exportacao'); rig.animation_data_create(); rig.animation_data.action = act
TESTE = {1: None, 2: 'mao_fechada', 3: 'fechar_50', 4: 'mao_aberta', 5: 'cotovelo_90_punho_45_mao_fechada', 6: 'olhos'}
for f, pose in TESTE.items():
    sc.frame_set(f); K.reset()
    if pose == 'olhos':      # piscada parcial + olhar + cabeça girada (ossos novos do P2)
        for n_, a_ in (('palpebra_sup.L', 0.35), ('palpebra_inf.L', -0.3), ('palpebra_sup.R', 0.5), ('palpebra_inf.R', -0.4), ('eye.L', 0.25), ('eye.R', 0.25)):
            b_ = pb[n_]; b_.rotation_mode = 'QUATERNION'; b_.rotation_quaternion = Matrix.Rotation(a_, 4, 'X').to_quaternion()
        pb['head'].rotation_mode = 'QUATERNION'; pb['head'].rotation_quaternion = Matrix.Rotation(0.4, 4, 'Y').to_quaternion()
        bpy.context.view_layer.update()
    elif pose: K.poses('L')[pose](); K.poses('R')[pose]()
    for b in pb:
        b.keyframe_insert('rotation_euler', frame=f); b.keyframe_insert('rotation_quaternion', frame=f); b.keyframe_insert('location', frame=f)
sc.frame_start, sc.frame_end = 1, 6
outline(False)
REF = {}; KV = {}
for f in TESTE:
    sc.frame_set(f); REF[f] = {o.name: pos(o) for o in (body, hull, olhos)}; KV[f] = {k.name: round(k.value, 4) for k in me.shape_keys.key_blocks[1:]}
REP['valores_keys_por_quadro'] = KV
for o in bpy.context.selected_objects: o.select_set(False)
for o in (body, hull, rig, olhos): o.select_set(True)
bpy.context.view_layer.objects.active = rig
glb = os.path.join(OUT, 'kumo_v6_p2_jogo.glb'); fbx = os.path.join(OUT, 'kumo_v6_p2_jogo.fbx')
bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', use_selection=True, export_apply=False, export_skins=True, export_animations=True,
                          export_all_influences=False, export_morph=True, export_morph_animation=True, export_def_bones=False)
bpy.ops.export_scene.fbx(filepath=fbx, use_selection=True, add_leaf_bones=False, bake_anim=True, use_mesh_modifiers=False)
REP['exportacao_kb'] = dict(glb=round(os.path.getsize(glb) / 1024), fbx=round(os.path.getsize(fbx) / 1024))
# conteúdo do GLB (JSON): materiais, morphs, canais de animação
import struct
with open(glb, 'rb') as fh:
    fh.read(12); ln, _ = struct.unpack('<II', fh.read(8)); J = json.loads(fh.read(ln))
REP['glb_conteudo'] = dict(malhas=[(m_['name'], len(m_['primitives']), len(m_['primitives'][0].get('targets', [])), m_.get('extras', {}).get('targetNames')) for m_ in J['meshes']],
                           materiais=[(m_['name'], m_.get('doubleSided', False), list(m_.get('extensions', {}).keys())) for m_ in J['materials']],
                           animacoes=[(a['name'], sorted({c['target']['path'] for c in a['channels']})) for a in J.get('animations', [])],
                           extensoes=J.get('extensionsUsed', []))
print('CJ GLB', json.dumps(REP['glb_conteudo']), flush=True)
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
    arm = next(o for o in s2.objects if o.type == 'ARMATURE')
    liga(arm.animation_data_create(), *escolhe('OBJECT', lambda a, sl: True))
    meshes = {o.name.split('.')[0]: o for o in s2.objects if o.type == 'MESH' and o.name.split('.')[0] in REF[1]}
    for nm, o in meshes.items():
        if o.data.shape_keys:
            kn = o.data.shape_keys.name
            a, sl = escolhe('KEY', lambda a, sl: sl.identifier == 'KE' + o.name or a.name.startswith(kn + '|'))
            if a: liga(o.data.shape_keys.animation_data_create(), a, sl)
    res = {}
    for nm, o in meshes.items():
        gg = {x.index: x.name for x in o.vertex_groups}; bn = {b.name for b in arm.data.bones}
        infl = [len([x for x in v.groups if gg[x.group] in bn and x.weight > 1e-4]) for v in o.data.vertices]
        sums = [sum(x.weight for x in v.groups if gg[x.group] in bn) for v in o.data.vertices]
        r = dict(vertices=len(o.data.vertices), max_influencias=max(infl), soma_fora_de_1=sum(1 for x in sums if abs(x - 1) > 0.01),
                 shape_keys=[k.name for k in o.data.shape_keys.key_blocks] if o.data.shape_keys else [])
        s2.frame_set(1); P1 = pos(o); src = REF[1].get(nm)
        if src is None: res[nm] = r; continue
        kd = KDTree(len(src)); [kd.insert(Vector(p), i) for i, p in enumerate(src)]; kd.balance(); mp = [kd.find(Vector(p))[1] for p in P1]
        err = {}
        for f in TESTE:
            s2.frame_set(f); Pp = pos(o); e = np.linalg.norm(Pp - REF[f][nm][mp], axis=1); err[f] = round(float(e.max()) * 1000, 4)
            if o.data.shape_keys: err[f'{f}_keys'] = {k.name: round(k.value, 3) for k in o.data.shape_keys.key_blocks[1:]}
        r['erro_max_mm_por_quadro'] = err; res[nm] = r
    return res, [a.name for a in bpy.data.actions]
REP['glb_reimportado'], acts = reimport(glb, lambda f: bpy.ops.import_scene.gltf(filepath=f)); REP['glb_acoes'] = acts
print('CJ GLBR', json.dumps(REP['glb_reimportado']), acts, flush=True)
REP['fbx_reimportado'], acts = reimport(fbx, lambda f: bpy.ops.import_scene.fbx(filepath=f, use_anim=True)); REP['fbx_acoes'] = acts
print('CJ FBXR', json.dumps(REP['fbx_reimportado']), acts, flush=True)
json.dump(REP, open(os.path.join(OUT, 'medicoes_contorno.json'), 'w'), indent=1, default=str)
print('CJ OK', json.dumps({k: REP[k] for k in ('espessura', 'contorno_jogo', 'contorno_jogo_vs_solidify')}))
