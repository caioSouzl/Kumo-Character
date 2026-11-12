"""Materiais dos olhos que o glTF entende: Principled com base preta, emissão = textura e alpha = alpha da textura.
O Emission + Transparent misturados (usados até aqui) renderizam igual no Blender, mas o exportador glTF perde a
transparência (as camadas saíam opacas no GLB). Confere com fotos que o Blender continua mostrando o mesmo.
  python materiais_olhos.py <entrada.blend> <saída.blend> <pasta fotos>"""
import bpy, sys, os
import numpy as np
from mathutils import Vector
SRC, DST, FOT = sys.argv[-3:]; os.makedirs(FOT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=SRC); sc = bpy.context.scene
img = bpy.data.images.get('kumo_quad_diffuse')
if img: img.filepath = '/home/user/Kumo-Character/kumo-3d-rodin/textures/kumo_quad_diffuse.png'; img.reload()
TEXD = '/home/user/Kumo-Character/kumo-3d-rodin/v6-dev/olhos-jogo/texturas'
for im in bpy.data.images:
    if im.name.startswith('olho_') and not os.path.exists(bpy.path.abspath(im.filepath)):
        im.filepath = os.path.join(TEXD, os.path.basename(im.filepath)); im.reload()
rig = bpy.data.objects['Kumo_Rig']; pb = rig.pose.bones
if rig.animation_data: rig.animation_data.action = None
h = bpy.data.objects.get('Kumo_Contorno')
sc.render.engine = 'CYCLES'; sc.cycles.samples = 16; sc.cycles.seed = 1; sc.cycles.transparent_max_bounces = 32; sc.render.resolution_x = sc.render.resolution_y = 380
c = bpy.data.objects.new('cam_mat', bpy.data.cameras.new('cam_mat')); sc.collection.objects.link(c); c.data.type = 'ORTHO'; c.data.ortho_scale = 1.05
d = Vector((0, -1, 0)); c.location = Vector((0.07, -0.3, 1.38)) + d * 6; c.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler(); sc.camera = c
ESTADOS = {'aberto': (0, 0, 0, 0), 'piscar50': (0.5, 0.5, 0, 0), 'fechado': (1, 1, 0, 0), 'olhar_dir': (0, 0, 1, 0)}
def fotos(tag):
    out = {}
    for nm, (a, b, x, y) in ESTADOS.items():
        pb['controle_olhos'].location = (a, b, 0); pb['controle_olhar'].location = (x, y, 0); bpy.context.view_layer.update()
        sc.render.filepath = f'{FOT}/{tag}_{nm}.png'; bpy.ops.render.render(write_still=True)
        im = bpy.data.images.load(sc.render.filepath); out[nm] = np.array(im.pixels[:]).reshape(-1, 4); bpy.data.images.remove(im)
    pb['controle_olhos'].location = (0, 0, 0); pb['controle_olhar'].location = (0, 0, 0); return out
A = fotos('antes')
n = 0
for m in {s.material for o in bpy.data.objects if o.name.startswith('KumoJogo_') for s in o.material_slots if s.material}:
    nt = m.node_tree; t = next(x for x in nt.nodes if x.type == 'TEX_IMAGE'); im, interp, ext = t.image, t.interpolation, t.extension
    nt.nodes.clear()
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = im; t.interpolation = interp; t.extension = ext
    p = nt.nodes.new('ShaderNodeBsdfPrincipled'); out = nt.nodes.new('ShaderNodeOutputMaterial')
    p.inputs['Base Color'].default_value = (0, 0, 0, 1); p.inputs['Roughness'].default_value = 1.0; p.inputs['Specular IOR Level'].default_value = 0.0
    nt.links.new(t.outputs['Color'], p.inputs['Emission Color']); p.inputs['Emission Strength'].default_value = 1.0
    nt.links.new(t.outputs['Alpha'], p.inputs['Alpha']); nt.links.new(p.outputs[0], out.inputs[0]); n += 1
B = fotos('depois')
print('MAT convertidos', n, {k: (round(float(np.abs(A[k] - B[k])[:, :3].mean()) * 255, 3), round(float(np.abs(A[k] - B[k])[:, :3].max()) * 255, 1)) for k in A})
bpy.data.objects.remove(c)
bpy.ops.wm.save_as_mainfile(filepath=DST, copy=True, relative_remap=False); print('MAT OK')
