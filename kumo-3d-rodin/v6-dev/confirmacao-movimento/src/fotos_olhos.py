"""Fotos de confirmação: movimento dos olhos na olhos-v5 (variante B), só leitura. Controles do próprio arquivo:
propriedades do osso head (piscar, piscar_E, piscar_D, fechar_parcial_*) e o osso eye_target (olhar)."""
import bpy, sys, os
from mathutils import Vector
SRC, OUT = sys.argv[-2:]; os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=SRC); sc = bpy.context.scene
img = bpy.data.images.get('kumo_quad_diffuse')
if img: img.filepath = '/home/user/Kumo-Character/kumo-3d-rodin/textures/kumo_quad_diffuse.png'; img.reload()
for im in bpy.data.images:
    if im.filepath and not os.path.exists(bpy.path.abspath(im.filepath)):
        alt = os.path.join(os.path.dirname(SRC), 'textures', os.path.basename(im.filepath))
        if os.path.exists(alt): im.filepath = alt; im.reload()
rig = bpy.data.objects['Kumo_Rig']; pb = rig.pose.bones; H = pb['head']
sc.render.engine = 'CYCLES'; sc.cycles.samples = 24; sc.render.resolution_x = sc.render.resolution_y = 420
def cam(n, d, t, s_):
    c = bpy.data.objects.new(n, bpy.data.cameras.new(n)); sc.collection.objects.link(c); c.data.type = 'ORTHO'; c.data.ortho_scale = s_
    d = Vector(d).normalized(); c.location = Vector(t) + d * 6; c.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler(); return c
CAMS = {'frente': cam('f', (0, -1, 0), (0, -0.1, 1.42), 1.3), '34': cam('q', (-0.57, -0.82, 0.05), (0, -0.1, 1.42), 1.3)}
def reset():
    for k in ('piscar', 'piscar_E', 'piscar_D', 'fechar_parcial_E', 'fechar_parcial_D'): H[k] = 0.0
    pb['eye_target'].location = (0, 0, 0); rig.update_tag(); bpy.context.view_layer.update()
EST = {'aberto': {}, 'piscar_50': {'piscar': 0.5}, 'piscar_100': {'piscar': 1.0}, 'so_esquerdo': {'piscar_E': 1.0}, 'so_direito': {'piscar_D': 1.0},
       'olhar_esq': {'_x': 0.35}, 'olhar_dir': {'_x': -0.35}, 'olhar_cima': {'_z': 0.25}, 'olhar_baixo': {'_z': -0.25}}
for nome, kv in EST.items():
    reset()
    for k, v in kv.items():
        if k == '_x': pb['eye_target'].location.x = v
        elif k == '_z': pb['eye_target'].location.z = v
        else: H[k] = v
    rig.update_tag(); bpy.context.view_layer.update()
    for cn, c in CAMS.items():
        sc.camera = c; sc.render.filepath = f'{OUT}/olho_{nome}_{cn}.png'; bpy.ops.render.render(write_still=True)
