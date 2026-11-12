"""Confere repouso idêntico ao Kumo atual, exporta GLB/FBX com quadros de teste do ombro e confere a reimportação.
  python exportar_ombros.py <kumo_v6_ombros.blend> <kumo_v6_olhos_jogo.blend (antes)> <saída> <K> <KF>"""
import bpy, sys, os, json, math
import numpy as np
from mathutils import Vector, Matrix
from mathutils.kdtree import KDTree
SRC, ANTES, OUT, K, KF = sys.argv[-5:]; K = float(K); KF = float(KF); os.makedirs(OUT, exist_ok=True)
def pos(o):
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get(); ev = o.evaluated_get(dg); m = ev.to_mesh()
    P = np.array([tuple(ev.matrix_world @ v.co) for v in m.vertices]); ev.to_mesh_clear(); return P
def sem_extras(o):
    for m in o.modifiers:
        if m.type != 'ARMATURE': m.show_viewport = False
bpy.ops.wm.open_mainfile(filepath=ANTES); b0 = bpy.data.objects['Kumo']; sem_extras(b0)
r0 = bpy.data.objects['Kumo_Rig']
if r0.animation_data: r0.animation_data.action = None
REST0 = pos(b0)
bpy.ops.wm.open_mainfile(filepath=SRC); sc = bpy.context.scene
img = bpy.data.images.get('kumo_quad_diffuse')
if img: img.filepath = '/home/user/Kumo-Character/kumo-3d-rodin/textures/kumo_quad_diffuse.png'; img.reload()
rig = bpy.data.objects['Kumo_Rig']; body = bpy.data.objects['Kumo']; pb = rig.pose.bones; hull = bpy.data.objects.get('Kumo_Contorno')
if rig.animation_data: rig.animation_data.action = None
sem_extras(body); REP = {'repouso_dif_max_mm': round(float(np.abs(pos(body) - REST0).max()) * 1000, 4)}
def reset():
    for b in pb: b.rotation_quaternion = (1, 0, 0, 0); b.rotation_euler = (0, 0, 0); b.location = (0, 0, 0)
    bpy.context.view_layer.update()
def rotw(n, axis, deg):
    b = pb[n]; bpy.context.view_layer.update(); M = b.matrix.copy(); hh = M.to_translation()
    b.matrix = Matrix.Translation(hh) @ Matrix.Rotation(math.radians(deg), 4, axis.normalized()) @ Matrix.Translation(-hh) @ M; bpy.context.view_layer.update()
def mover(sd, tipo, deg):
    bn = rig.data.bones[f'upper_arm.{sd}']; d = (bn.tail_local - bn.head_local).normalized()
    ax = d.cross(Vector((0, 0, 1))) if tipo == 'erguer' else d.cross(Vector((0, -1, 0)))
    s_ = max(0.0, abs(deg) - 30) * (K if tipo == 'erguer' else KF) * (1 if deg > 0 else -1)
    if s_: rotw(f'shoulder.{sd}', ax, s_)
    rotw(f'upper_arm.{sd}', ax, deg - s_)
TESTE = {1: [], 2: [('L', 'erguer', 90), ('R', 'erguer', 90)], 3: [('L', 'erguer', 150), ('R', 'erguer', 120)], 4: [('L', 'frente', 90), ('R', 'frente', 60)], 5: [('L', 'erguer', 105), ('R', 'frente', 90)]}
act = bpy.data.actions.new('Teste_Exportacao'); rig.animation_data_create(); rig.animation_data.action = act
for f, mv in TESTE.items():
    sc.frame_set(f); reset()
    for a in mv: mover(*a)
    for n in ('shoulder.L', 'upper_arm.L', 'shoulder.R', 'upper_arm.R'): pb[n].keyframe_insert('rotation_euler' if pb[n].rotation_mode != 'QUATERNION' else 'rotation_quaternion', frame=f)
sc.frame_start, sc.frame_end = 1, 5
REF = {}
for f in TESTE: sc.frame_set(f); REF[f] = pos(body)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'kumo_v6_ombros.blend'), copy=True, relative_remap=False)
for o in bpy.context.selected_objects: o.select_set(False)
for o in [body, rig] + ([hull] if hull else []) + [o for o in bpy.data.objects if o.name.startswith('KumoJogo_')]: o.hide_set(False); o.select_set(True)
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
    o = next(o for o in s2.objects if o.type == 'MESH' and o.name.split('.')[0] == 'Kumo')
    for a in TA:
        for sl in a.slots:
            if sl.target_id_type == 'OBJECT': liga(arm.animation_data_create(), a, sl)
            if sl.target_id_type == 'KEY' and o.data.shape_keys and (sl.identifier == 'KE' + o.name or a.name.startswith(o.data.shape_keys.name + '|')): liga(o.data.shape_keys.animation_data_create(), a, sl)
    print('RI', o.name, len(o.data.vertices), [m.type for m in o.modifiers], [x.name for x in s2.objects][:8])
    fm = 1; s2.frame_set(fm); P1 = pos(o); kd = KDTree(len(REF[fm])); [kd.insert(Vector(p), i) for i, p in enumerate(REF[fm])]; kd.balance()
    mp = [kd.find(Vector(p))[1] for p in P1]; e = {}
    for f in TESTE: s2.frame_set(f); dd = np.linalg.norm(pos(o) - REF[f][mp], axis=1); e[f] = (round(float(dd.max()) * 1000, 3), round(float(np.percentile(dd, 99.5)) * 1000, 3), int((dd > 0.001).sum()))
    return e
REP['glb_erro_max_mm'] = reimport(glb, lambda f: bpy.ops.import_scene.gltf(filepath=f))
REP['fbx_erro_max_mm'] = reimport(fbx, lambda f: bpy.ops.import_scene.fbx(filepath=f, use_anim=True))
json.dump(REP, open(os.path.join(OUT, 'medicoes_exportacao.json'), 'w'), indent=1); print('EX', json.dumps(REP))
