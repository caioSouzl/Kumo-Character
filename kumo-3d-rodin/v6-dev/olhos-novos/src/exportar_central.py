"""GLB leve da Central do Kumo com os olhos novos + parâmetros do decal para a página.

  blender --background ../kumo_v6_olhos_novos.blend --python exportar_central.py -- <saída>

Saídas em <saída>/:
- kumo_central.glb: como o GLB do Estúdio (sem normais, sem animações), com os olhos novos (KumoOlho.L/.R)
  levando as duas UV: a da pele (TEXCOORD_0) e a da janela (TEXCOORD_1).
- olhos.json: tudo o que a página precisa para refazer o decal e o olhar (em coordenadas do Blender).
- olhos/: as texturas do olho em 1024 px (fundo, aro, máscara) e a imagem da íris e pupila.
"""
import bpy, sys, os, json, shutil
from mathutils import Vector, Matrix

OUT = sys.argv[-1]; os.makedirs(os.path.join(OUT, 'olhos'), exist_ok=True)
rig = bpy.data.objects['Kumo_Rig']; pb = rig.pose.bones
if rig.animation_data: rig.animation_data.action = None
for b in pb: b.rotation_quaternion = (1, 0, 0, 0); b.rotation_euler = (0, 0, 0); b.location = (0, 0, 0)
bpy.context.view_layer.update()
img = bpy.data.images.get('kumo_quad_diffuse')
if img: img.filepath = '/home/user/Kumo-Character/kumo-3d-rodin/textures/kumo_quad_diffuse.png'; img.reload()

P = {}
for s in 'LR':
    o = bpy.data.objects[f'KumoOlho.{s}']; m = o.material_slots[0].material; N = m.node_tree.nodes
    imgs = {n.image.name: n.image for n in N if n.type == 'TEX_IMAGE' and n.image}
    maps = [n for n in N if n.type == 'MAPPING']
    # Mapping da janela (UV → 0..1) e do decal (objeto → arte)
    mj = next(n for n in maps if any(l.from_node.type == 'UVMAP' for l in n.inputs['Vector'].links))
    md = next(n for n in maps if any(l.from_node.type == 'TEX_COORD' for l in n.inputs['Vector'].links))
    sc_ = mj.inputs['Scale'].default_value[0]; U0 = -mj.inputs['Location'].default_value[0] / sc_; U1 = U0 + 1 / sc_
    for nome in (f'olho_{s}_fundo', f'olho_{s}_aro', f'olho_{s}_dentro', 'olho_decal_iris_pupila'):
        im = imgs[nome]; im.reload(); destino = os.path.join(OUT, 'olhos', nome + '.png')
        if nome == 'olho_decal_iris_pupila': shutil.copy(bpy.path.abspath(im.filepath), destino); continue
        c = im.copy(); c.scale(1024, 1024); c.filepath_raw = destino; c.file_format = 'PNG'; c.save()
    b = rig.data.bones[f'olho.{s}']; t = rig.data.bones[f'MCH_alvo_olho.{s}']
    cons = pb[f'MCH_alvo_olho.{s}'].constraints['Olhar']
    e = bpy.data.objects[f'Decal_Olho.{s}']
    P[s] = {
        'H': list(rig.matrix_world @ b.head_local), 'S': list(rig.matrix_world @ b.tail_local),
        'T0': list(rig.matrix_world @ t.head_local),
        'ex': list((rig.matrix_world.to_3x3() @ t.matrix_local.to_3x3()).col[0].normalized()),
        'ez': list((rig.matrix_world.to_3x3() @ t.matrix_local.to_3x3()).col[2].normalized()),
        'Lx': cons.to_max_x, 'Lz': cons.to_max_z,                 # alvo anda Lx·gx no X local e Lz·gy no Z local
        'D0': [list(r) for r in e.matrix_world],                   # decal em repouso (Blender, linhas)
        'sd': md.inputs['Scale'].default_value[0], 'artC': list(md.inputs['Location'].default_value[:2]),
        'U0': U0, 'U1': U1,
    }
json.dump(P, open(os.path.join(OUT, 'olhos.json'), 'w'), indent=1)

# material simples para o arquivo: pele pela UV 0; a UV da janela vai junto (a página troca o material)
for s in 'LR':
    o = bpy.data.objects[f'KumoOlho.{s}']
    mm = bpy.data.materials.new(f'KumoOlho.{s}'); mm.use_nodes = True; N = mm.node_tree.nodes; L = mm.node_tree.links
    bs = N.get('Principled BSDF'); bs.inputs['Base Color'].default_value = (0, 0, 0, 1); bs.inputs['Emission Strength'].default_value = 1
    t1 = N.new('ShaderNodeTexImage'); t1.image = img; u1 = N.new('ShaderNodeUVMap'); u1.uv_map = 'UVMap'
    L.new(u1.outputs['UV'], t1.inputs['Vector']); L.new(t1.outputs['Color'], bs.inputs['Emission Color'])
    o.material_slots[0].material = mm
    while len(o.material_slots) > 1:
        o.active_material_index = len(o.material_slots) - 1; bpy.context.view_layer.objects.active = o; bpy.ops.object.material_slot_remove()
    o.data.uv_layers.active = o.data.uv_layers['UVMap']
for s in 'LR':
    e = bpy.data.objects.get(f'Decal_Olho.{s}')
    if e: bpy.data.objects.remove(e)

for o in bpy.context.selected_objects: o.select_set(False)
objs = [o for o in bpy.data.objects if o.name in ('Kumo', 'Kumo_Contorno', 'Kumo_Rig', 'Kumo_Boca', 'Kumo_Lingua') or o.name.startswith(('KumoJogo_', 'KumoOlho.'))]
for o in objs: o.hide_set(False); o.select_set(True)
bpy.context.view_layer.objects.active = rig
glb = os.path.join(OUT, 'kumo_central.glb')
bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', use_selection=True, export_apply=False, export_skins=True, export_animations=False,
                          export_all_influences=False, export_morph=True, export_morph_normal=False, export_normals=False, export_tangents=False)
# confere: os olhos saíram com as duas UV?
import struct
with open(glb, 'rb') as f:
    f.read(12); n = struct.unpack('<I', f.read(4))[0]; f.read(4); js = json.loads(f.read(n))
uvs = {}
for nd in js['nodes']:
    if nd.get('name', '').startswith('KumoOlho.') and 'mesh' in nd:
        uvs[nd['name']] = sorted({k for p in js['meshes'][nd['mesh']]['primitives'] for k in p['attributes'] if k.startswith('TEXCOORD')})
print('CE', os.path.getsize(glb) // 1024, 'KB', uvs)
