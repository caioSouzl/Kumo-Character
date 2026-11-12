"""Leva os olhos de jogo (conversão da v5) para o Kumo com mãos (maos-corretivas) e exporta GLB/FBX.

  python integrar.py <kumo_olhos_jogo_conversao.blend> <maos-corretivas/kumo_v6_maos_jogo.blend> <pasta texturas> <saída>

Controles (exportáveis, porque o exportador grava a animação das shape keys ligadas a ossos):
- osso `controle_olhos` (não deforma): posição X = piscar esquerdo, Y = piscar direito (0 aberto .. 1 fechado)
- osso `controle_olhar`: posição X = olhar para a direita (+) / esquerda (−), Y = para cima (+) / baixo (−), de −1 a 1
"""
import bpy, sys, os, json, math
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree
CONV, MAOS, TEXD, OUT = sys.argv[-4:]; os.makedirs(OUT, exist_ok=True)
REPO = '/home/user/Kumo-Character/kumo-3d-rodin'
bpy.ops.wm.open_mainfile(filepath=MAOS); sc = bpy.context.scene
img = bpy.data.images.get('kumo_quad_diffuse')
if img: img.filepath = os.path.join(REPO, 'textures', 'kumo_quad_diffuse.png'); img.reload()
rig = bpy.data.objects['Kumo_Rig']; body = bpy.data.objects['Kumo']; hull = bpy.data.objects.get('Kumo_Contorno')
with bpy.data.libraries.load(CONV, link=False) as (src, dst):
    dst.objects = [n for n in src.objects if n.startswith('KumoJogo_')]
OLHOS = [o for o in dst.objects if o]
for o in OLHOS:
    sc.collection.objects.link(o); o.hide_render = False; o.hide_viewport = False; o.hide_set(False)   # a comparação da conversão deixou escondidos no render
    o.parent = rig; o.matrix_parent_inverse = rig.matrix_world.inverted()
    for m in o.modifiers:
        if m.type == 'ARMATURE': m.object = rig
    for mt in o.data.materials:
        for n in mt.node_tree.nodes:
            if n.type == 'TEX_IMAGE' and n.image:
                n.image.filepath = os.path.join(TEXD, os.path.basename(n.image.filepath)); n.image.reload()
# sobras do arquivo de origem (o rig da v5 que veio junto pelas referências dos drivers)
for o in list(bpy.data.objects):
    if o.name.startswith('Kumo_Rig.') : bpy.data.objects.remove(o)
# ossos de controle
for o in bpy.context.selected_objects: o.select_set(False)
rig.select_set(True); bpy.context.view_layer.objects.active = rig; bpy.ops.object.mode_set(mode='EDIT'); EB = rig.data.edit_bones
for n, z in (('controle_olhos', 2.15), ('controle_olhar', 2.30)):
    b = EB.new(n); b.head = (0, 0, z); b.tail = (0, 0, z + 0.1); b.parent = EB['head']; b.use_deform = False
bpy.ops.object.mode_set(mode='OBJECT'); pb = rig.pose.bones
# drivers: troca as propriedades da v5 por posição dos ossos de controle
VAR = {'kumo_piscar_E': ('controle_olhos', 'LOC_X'), 'kumo_piscar_D': ('controle_olhos', 'LOC_Y'),
       'kumo_olhar_x': ('controle_olhar', 'LOC_X'), 'kumo_olhar_y': ('controle_olhar', 'LOC_Y')}
nd = 0
for o in OLHOS:
    sk = o.data.shape_keys
    if not sk or not sk.animation_data: continue
    for fc in sk.animation_data.drivers:
        for v in fc.driver.variables:
            prop = v.targets[0].data_path.strip('[]"')
            bn, tt = VAR[prop]; v.type = 'TRANSFORMS'; t = v.targets[0]; t.id = rig; t.bone_target = bn; t.transform_type = tt; t.transform_space = 'LOCAL_SPACE'
        nd += 1
print('IN drivers', nd, 'objetos', len(OLHOS))
def ctrl(pE=0.0, pD=0.0, gx=0.0, gy=0.0):
    pb['controle_olhos'].location = (pE, pD, 0); pb['controle_olhar'].location = (gx, gy, 0); bpy.context.view_layer.update()
# confere que os controles mexem
def pos(o):
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get(); ev = o.evaluated_get(dg); m = ev.to_mesh()
    P = np.array([tuple(ev.matrix_world @ v.co) for v in m.vertices]); ev.to_mesh_clear(); return P
REP = {}
ctrl(); R0 = {o.name: pos(o) for o in OLHOS}
for nm, args in (('piscar_100', (1, 1, 0, 0)), ('olhar_dir', (0, 0, 1, 0))):
    ctrl(*args); REP['mexe_' + nm] = round(max(float(np.linalg.norm(pos(o) - R0[o.name], axis=1).max()) for o in OLHOS) * 1000, 1)
ctrl()
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'kumo_v6_olhos_jogo.blend'), copy=True, relative_remap=False)
# ---------- exportação com quadros de teste
act = bpy.data.actions.new('Teste_Exportacao'); rig.animation_data_create(); rig.animation_data.action = act
TESTE = {1: (0, 0, 0, 0), 2: (0.5, 0.5, 0, 0), 3: (1, 1, 0, 0), 4: (1, 0, 0, 0), 5: (0, 0, 1, 0), 6: (0, 0, 0, 1), 7: (0.3, 0.3, -1, -1)}
for f, a in TESTE.items():
    sc.frame_set(f); ctrl(*a)
    for n in ('controle_olhos', 'controle_olhar'): pb[n].keyframe_insert('location', frame=f)
sc.frame_start, sc.frame_end = 1, 7
for m in body.modifiers:
    if m.type != 'ARMATURE': m.show_viewport = False
OBJS = [body] + ([hull] if hull else []) + OLHOS
REF = {}
for f in TESTE: sc.frame_set(f); REF[f] = {o.name: pos(o) for o in OLHOS}
for o in bpy.context.selected_objects: o.select_set(False)
for o in OBJS + [rig]: o.select_set(True)
bpy.context.view_layer.objects.active = rig
glb = os.path.join(OUT, 'kumo_v6_jogo.glb'); fbx = os.path.join(OUT, 'kumo_v6_jogo.fbx')
bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', use_selection=True, export_apply=False, export_skins=True, export_animations=True,
                          export_all_influences=False, export_morph=True, export_morph_animation=True)
bpy.ops.export_scene.fbx(filepath=fbx, use_selection=True, add_leaf_bones=False, bake_anim=True, use_mesh_modifiers=False)
REP['kb'] = dict(glb=round(os.path.getsize(glb) / 1024), fbx=round(os.path.getsize(fbx) / 1024))
def reimport(fn, imp):
    bpy.ops.wm.read_homefile(use_empty=True); imp(fn); s2 = bpy.context.scene
    TA = [a for a in bpy.data.actions if 'Teste_Exportacao' in a.name]
    def liga(ad, a, sl):
        for t_ in list(ad.nla_tracks): ad.nla_tracks.remove(t_)
        ad.action = a; ad.action_slot = sl
    arm = next(o for o in s2.objects if o.type == 'ARMATURE')
    for a in TA:
        for sl in a.slots:
            if sl.target_id_type == 'OBJECT': liga(arm.animation_data_create(), a, sl)
    res = {}
    for o in s2.objects:
        if o.type != 'MESH': continue
        nm = o.name if o.name in REF[1] else o.name.rsplit('.', 1)[0]
        if nm not in REF[1]: continue
        if o.data.shape_keys:
            for a in TA:
                for sl in a.slots:
                    if sl.target_id_type == 'KEY' and (sl.identifier == 'KE' + o.name or a.name.startswith(o.data.shape_keys.name + '|')): liga(o.data.shape_keys.animation_data_create(), a, sl)
        # casa os vértices num quadro sem pontos repetidos (a pálpebra aberta fica dobrada numa linha: muitos vértices no mesmo lugar)
        fm = max(TESTE, key=lambda f: len(np.unique(np.round(REF[f][nm], 6), axis=0)))
        s2.frame_set(fm); P1 = pos(o); kd = KDTree(len(REF[fm][nm])); [kd.insert(Vector(p), i) for i, p in enumerate(REF[fm][nm])]; kd.balance()
        mp = [kd.find(Vector(p))[1] for p in P1]; e = {}
        for f in TESTE: s2.frame_set(f); e[f] = round(float(np.linalg.norm(pos(o) - REF[f][nm][mp], axis=1).max()) * 1000, 3)
        res[nm] = e
    return res
REP['glb_erro_max_mm'] = reimport(glb, lambda f: bpy.ops.import_scene.gltf(filepath=f))
REP['fbx_erro_max_mm'] = reimport(fbx, lambda f: bpy.ops.import_scene.fbx(filepath=f, use_anim=True))
json.dump(REP, open(os.path.join(OUT, 'medicoes_integracao.json'), 'w'), indent=1)
print('IN', json.dumps(REP))
