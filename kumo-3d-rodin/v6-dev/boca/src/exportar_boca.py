"""Animações de boca e língua para o jogo + exportação GLB/FBX com conferência na reimportação.

Animações (24 qps), com o tempo do camaleão de verdade:
  Boca_Abrir     : abre (6 quadros), segura, fecha
  Lingua_Lancar  : abre a boca e a língua sai um pouco (mira, 5 q) → dispara (2 q ≈ 0,08 s) → gruda (2 q)
                   → volta mais devagar (12 q) → fecha a boca
No Godot, para mirar num alvo: gire o osso `lingua_mira`; para o alcance, mova `lingua_controle` no Y local
(metros) e ponha cada `lingua_i` em Y = alcance·i/10 e `lingua_ponta` em Y = alcance (é o que os drivers fazem aqui).

  python exportar_boca.py <kumo_lingua.blend> <saída>
"""
import bpy, sys, os, math, json
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree
SRC, OUT = sys.argv[-2:]; os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=SRC); sc = bpy.context.scene; sc.render.fps = 24
img = bpy.data.images.get('kumo_quad_diffuse')
if img: img.filepath = '/home/user/Kumo-Character/kumo-3d-rodin/textures/kumo_quad_diffuse.png'; img.reload()
TEXD = '/home/user/Kumo-Character/kumo-3d-rodin/v6-dev/olhos-jogo/texturas'
for im in bpy.data.images:
    if im.name.startswith('olho_') and not os.path.exists(bpy.path.abspath(im.filepath)): im.filepath = os.path.join(TEXD, os.path.basename(im.filepath)); im.reload()
rig = bpy.data.objects['Kumo_Rig']; pb = rig.pose.bones
for a in [a for a in bpy.data.actions if a.name.startswith('Teste_Exportacao')]: bpy.data.actions.remove(a)
for b in pb: b.rotation_quaternion = (1, 0, 0, 0); b.rotation_euler = (0, 0, 0); b.location = (0, 0, 0)
pb['jaw'].rotation_mode = 'XYZ'
ABRE = math.radians(-32)
def acao(nome, chaves):
    """chaves: [(quadro, ângulo da mandíbula, alcance da língua, interpolação)]"""
    a = bpy.data.actions.new(nome); rig.animation_data_create(); rig.animation_data.action = a
    for f, jaw, E, interp in chaves:
        pb['jaw'].rotation_euler = (jaw, 0, 0); pb['lingua_controle'].location = (0, E, 0)
        pb['jaw'].keyframe_insert('rotation_euler', index=0, frame=f); pb['lingua_controle'].keyframe_insert('location', index=1, frame=f)
    fcs = a.fcurves if hasattr(a, 'fcurves') else [fc for l in a.layers for st in l.strips for cb in st.channelbags for fc in cb.fcurves]
    for fc in fcs:
        for k, (f, _, _, interp) in zip(fc.keyframe_points, chaves): k.interpolation = interp
    a.use_fake_user = True; return a
acao('Boca_Abrir', [(1, 0, 0, 'BEZIER'), (7, ABRE, 0, 'BEZIER'), (19, ABRE, 0, 'BEZIER'), (26, 0, 0, 'BEZIER')])
ALC = 2.4
L = acao('Lingua_Lancar', [(1, 0, 0, 'BEZIER'), (6, ABRE, 0.12, 'BEZIER'), (7, ABRE, 0.12, 'LINEAR'), (9, ABRE, ALC, 'LINEAR'), (11, ABRE, ALC, 'BEZIER'),
                          (23, ABRE, 0.0, 'BEZIER'), (28, 0, 0.0, 'BEZIER')])
rig.animation_data.action = L; sc.frame_start, sc.frame_end = 1, 28
QUADROS = [1, 4, 6, 8, 9, 11, 16, 23, 28]
OBJS = ['Kumo', 'Kumo_Boca', 'Kumo_Lingua']
for nm in OBJS:
    for m in bpy.data.objects[nm].modifiers:
        if m.type != 'ARMATURE': m.show_viewport = False
def pos(o):
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get(); ev = o.evaluated_get(dg); m = ev.to_mesh()
    P = np.array([tuple(ev.matrix_world @ v.co) for v in m.vertices]); ev.to_mesh_clear(); return P
REF = {}
for f in QUADROS: sc.frame_set(f); REF[f] = {n: pos(bpy.data.objects[n]) for n in OBJS}
sc.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'kumo_v6_boca.blend'), copy=True, relative_remap=False)
for o in bpy.context.selected_objects: o.select_set(False)
for o in bpy.data.objects:
    if o.name in OBJS + ['Kumo_Rig', 'Kumo_Contorno'] or o.name.startswith('KumoJogo_'): o.hide_set(False); o.select_set(True)
bpy.context.view_layer.objects.active = rig
glb = os.path.join(OUT, 'kumo_v6_jogo.glb'); fbx = os.path.join(OUT, 'kumo_v6_jogo.fbx')
bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', use_selection=True, export_apply=False, export_skins=True, export_animations=True,
                          export_animation_mode='ACTIONS', export_all_influences=False, export_morph=True, export_morph_animation=True)
bpy.ops.export_scene.fbx(filepath=fbx, use_selection=True, add_leaf_bones=False, bake_anim=True, bake_anim_use_all_actions=True, use_mesh_modifiers=False)
REP = {'kb': dict(glb=os.path.getsize(glb) // 1024, fbx=os.path.getsize(fbx) // 1024)}
def reimport(fn, imp):
    bpy.ops.wm.read_homefile(use_empty=True); imp(fn); s2 = bpy.context.scene
    acts = [a for a in bpy.data.actions if 'Lingua_Lancar' in a.name]
    arm = next(o for o in s2.objects if o.type == 'ARMATURE')
    for a in acts:
        for sl in a.slots:
            if sl.target_id_type == 'OBJECT':
                ad = arm.animation_data_create()
                for t_ in list(ad.nla_tracks): ad.nla_tracks.remove(t_)
                ad.action = a; ad.action_slot = sl
    res = {}
    for nm in OBJS:
        o = next((x for x in s2.objects if x.type == 'MESH' and x.name.split('.')[0] == nm), None)
        if o is None: res[nm] = 'faltou'; continue
        if o.data.shape_keys:                     # liga a animação das shape keys deste objeto, se houver
            for a in acts:
                for sl in a.slots:
                    if sl.target_id_type == 'KEY' and sl.identifier == 'KE' + o.data.shape_keys.name:
                        ad = o.data.shape_keys.animation_data_create(); ad.action = a; ad.action_slot = sl
        # casa os pontos com a boca ABERTA (fechada, os lábios de cima e de baixo estão no mesmo lugar e se confundem)
        f0 = 9; s2.frame_set(f0 + int(acts[0].frame_range[0]) - 1 if acts else f0)
        P1 = pos(o); kd = KDTree(len(REF[f0][nm]))
        for i, p in enumerate(REF[f0][nm]): kd.insert(Vector(p), i)
        kd.balance(); mp = [kd.find(Vector(p))[1] for p in P1]; e = {}
        for f in QUADROS:
            s2.frame_set(f + int(acts[0].frame_range[0]) - 1 if acts else f)
            e[f] = round(float(np.linalg.norm(pos(o) - REF[f][nm][mp], axis=1).max()) * 1000, 2)
        res[nm] = e
    return res
REP['glb_erro_max_mm'] = reimport(glb, lambda f: bpy.ops.import_scene.gltf(filepath=f))
REP['fbx_erro_max_mm'] = reimport(fbx, lambda f: bpy.ops.import_scene.fbx(filepath=f, use_anim=True))
json.dump(REP, open(os.path.join(OUT, 'medicoes_boca.json'), 'w'), indent=1); print('EB', json.dumps(REP))
