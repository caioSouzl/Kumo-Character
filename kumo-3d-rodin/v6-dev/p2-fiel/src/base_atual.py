"""Renders do Kumo atual com as mesmas câmeras do P2 fiel (comparação)."""
import bpy, sys, os
from mathutils import Vector
SRC, OUT = sys.argv[-2:]; os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=SRC); sc = bpy.context.scene
img = bpy.data.images['kumo_quad_diffuse']; img.filepath = '/home/user/Kumo-Character/kumo-3d-rodin/textures/kumo_quad_diffuse.png'; img.reload()
h = bpy.data.objects.get('Kumo_Contorno')
if h: h.hide_render = True
sc.render.engine = 'CYCLES'; sc.cycles.samples = 16
def cam(n, d, t, s_):
    c = bpy.data.objects.new(n, bpy.data.cameras.new(n)); sc.collection.objects.link(c); c.data.type = 'ORTHO'; c.data.ortho_scale = s_
    d = Vector(d).normalized(); c.location = Vector(t) + d * 6; c.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler(); return c
HC = Vector((0, -0.1, 1.42))
for tag, cams, res in (('atual_cabeca', {'frente': cam('hf', (0, -1, 0), HC, 1.3), '34': cam('h34', (-0.57, -0.82, 0.05), HC, 1.3), 'perfil': cam('hp', (-1, 0, 0), HC, 1.3)}, 480),
                       ('atual_corpo', {'frente': cam('cf', (0, -1, 0), (0, 0, 0.98), 2.2), '34': cam('c34', (-0.57, -0.82, 0.05), (0, 0, 0.98), 2.2), 'perfil': cam('cp', (-1, 0, 0), (0, 0, 0.98), 2.2), 'costas': cam('cc', (0, 1, 0), (0, 0, 0.98), 2.2)}, 480)):
    sc.render.resolution_x = sc.render.resolution_y = res
    for k, c in cams.items(): sc.camera = c; sc.render.filepath = f'{OUT}/{tag}_{k}.png'; bpy.ops.render.render(write_still=True)
