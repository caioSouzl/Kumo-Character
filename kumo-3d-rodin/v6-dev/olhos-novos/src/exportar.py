"""Kumo com os olhos novos → GLB e FBX, com conferência na reimportação.

  blender --background ../kumo_v6_olhos_novos.blend --python exportar.py -- <saída>

O decal da íris usa a coordenada de um objeto (o Empty preso ao osso do olho), o que o glTF e o FBX não levam.
Para o jogo, cada olho sai com a aparência de repouso gravada numa textura (bake), num material simples (emissão),
como os olhos de jogo anteriores. Os ossos `olho.L/.R` vão junto: o olhar no motor de jogo pede um shader que
receba a posição desses ossos (próxima etapa); a piscada continua nas shape keys `Piscar_*`.
"""
import bpy, sys, os, json, re
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree

OUT = sys.argv[-1]; os.makedirs(OUT, exist_ok=True); sc = bpy.context.scene
img = bpy.data.images.get('kumo_quad_diffuse')
if img: img.filepath = '/home/user/Kumo-Character/kumo-3d-rodin/textures/kumo_quad_diffuse.png'; img.reload()
rig = bpy.data.objects['Kumo_Rig']; pb = rig.pose.bones
if rig.animation_data: rig.animation_data.action = None
for b in pb: b.location = (0, 0, 0)
bpy.context.view_layer.update()
REP = {}

# ---------------------------------------------------------------- bake da aparência de repouso
sc.render.engine = 'CYCLES'; sc.cycles.samples = 4; sc.cycles.bake_type = 'EMIT'
sc.render.bake.use_selected_to_active = False      # o arquivo vinha com essa opção ligada (bake de outro objeto)
for s in 'LR':
    o = bpy.data.objects[f'KumoOlho.{s}']; me = o.data
    jan = me.uv_layers['Janela']; U = np.array([d.uv[:] for d in jan.data]); U0, U1 = U.min(), U.max()
    jg = me.uv_layers.new(name='Jogo')
    for i, d in enumerate(jan.data): jg.data[i].uv = ((d.uv[0] - U0) / (U1 - U0), (d.uv[1] - U0) / (U1 - U0))
    me.uv_layers.active = jg
    im = bpy.data.images.new(f'olho_{s}_jogo', 2048, 2048, alpha=False)
    m = o.material_slots[0].material; n = m.node_tree.nodes.new('ShaderNodeTexImage'); n.image = im
    for x in m.node_tree.nodes: x.select = False
    n.select = True; m.node_tree.nodes.active = n
    for x in bpy.context.selected_objects: x.select_set(False)
    o.hide_viewport = False; o.hide_select = False; o.hide_set(False); o.hide_render = False
    o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.bake(type='EMIT', margin=8, use_clear=True)
    p = os.path.join(OUT, f'olho_{s}_jogo.png'); im.filepath_raw = p; im.file_format = 'PNG'; im.save(); im.filepath = p
    # material de jogo: emissão pela textura gravada (UV 'Jogo'), como os olhos de jogo anteriores
    mj = bpy.data.materials.new(f'KumoOlho_Jogo.{s}'); mj.use_nodes = True; N = mj.node_tree.nodes; L = mj.node_tree.links
    bs = N.get('Principled BSDF'); bs.inputs['Base Color'].default_value = (0, 0, 0, 1); bs.inputs['Roughness'].default_value = 1.0
    bs.inputs['Emission Strength'].default_value = 1.0
    t = N.new('ShaderNodeTexImage'); t.image = im; u = N.new('ShaderNodeUVMap'); u.uv_map = 'Jogo'
    L.new(u.outputs['UV'], t.inputs['Vector']); L.new(t.outputs['Color'], bs.inputs['Emission Color'])
    o.material_slots[0].material = mj
    # só a UV do jogo sai no arquivo (a da pele e a da janela ficam no .blend de trabalho)
    for nm in [x.name for x in me.uv_layers if x.name != 'Jogo']: me.uv_layers.remove(me.uv_layers[nm])
    if len(o.material_slots) > 1:
        for i in range(len(o.material_slots) - 1, 0, -1):
            o.active_material_index = i; bpy.ops.object.material_slot_remove()
    REP[f'bake_{s}'] = p
for s in 'LR':
    e = bpy.data.objects.get(f'Decal_Olho.{s}')
    if e: bpy.data.objects.remove(e)

# ---------------------------------------------------------------- posições de referência
OBJS = [o.name for o in bpy.data.objects if o.type == 'MESH' and (o.name in ('Kumo', 'Kumo_Boca', 'Kumo_Lingua') or o.name.startswith(('KumoOlho.', 'KumoJogo_')))]
for nm in OBJS:
    for m in bpy.data.objects[nm].modifiers:
        if m.type != 'ARMATURE': m.show_viewport = False
def pos(o):
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get(); ev = o.evaluated_get(dg); m = ev.to_mesh()
    P = np.array([tuple(ev.matrix_world @ v.co) for v in m.vertices]); ev.to_mesh_clear(); return P
REF = {n: pos(bpy.data.objects[n]) for n in OBJS}

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'kumo_v6_olhos_novos_jogo.blend'), copy=True, relative_remap=False)
for o in bpy.context.selected_objects: o.select_set(False)
for o in bpy.data.objects:
    if o.name in OBJS + ['Kumo_Rig', 'Kumo_Contorno']: o.hide_set(False); o.select_set(True)
bpy.context.view_layer.objects.active = rig
glb = os.path.join(OUT, 'kumo_v6_jogo.glb'); fbx = os.path.join(OUT, 'kumo_v6_jogo.fbx')
bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', use_selection=True, export_apply=False, export_skins=True, export_animations=True,
                          export_animation_mode='ACTIONS', export_all_influences=False, export_morph=True, export_morph_animation=True)
bpy.ops.export_scene.fbx(filepath=fbx, use_selection=True, add_leaf_bones=False, bake_anim=True, bake_anim_use_all_actions=True, use_mesh_modifiers=False)
REP['kb'] = dict(glb=os.path.getsize(glb) // 1024, fbx=os.path.getsize(fbx) // 1024)


def reimport(fn, imp):
    bpy.ops.wm.read_homefile(use_empty=True); imp(fn); s2 = bpy.context.scene
    for a in s2.objects:
        if a.type == 'ARMATURE' and a.animation_data: a.animation_data.action = None
    res = {}
    for nm in OBJS:
        o = next((x for x in s2.objects if x.type == 'MESH' and re.sub(r'\.\d{3}$', '', x.name) == nm), None)   # o importador põe .001
        if o is None: res[nm] = 'faltou'; continue
        P1 = pos(o); kd = KDTree(len(REF[nm]))
        for i, p in enumerate(REF[nm]): kd.insert(Vector(p), i)
        kd.balance(); res[nm] = round(max(kd.find(Vector(p))[2] for p in P1) * 1000, 2)
    return res


REP['glb_erro_max_mm'] = reimport(glb, lambda f: bpy.ops.import_scene.gltf(filepath=f))
REP['fbx_erro_max_mm'] = reimport(fbx, lambda f: bpy.ops.import_scene.fbx(filepath=f))
json.dump(REP, open(os.path.join(OUT, 'medicoes_exportacao.json'), 'w'), indent=1, ensure_ascii=False)
print('EXP', json.dumps(REP, ensure_ascii=False))
