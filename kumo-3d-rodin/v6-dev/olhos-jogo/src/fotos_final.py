"""Fotos do Kumo com olhos de jogo + mãos: repouso (contra o Kumo atual) e movimentos."""
import bpy, sys, os
from mathutils import Vector
SRC, OUT = sys.argv[-2:]; os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=SRC); sc = bpy.context.scene
img = bpy.data.images.get('kumo_quad_diffuse')
if img: img.filepath = '/home/user/Kumo-Character/kumo-3d-rodin/textures/kumo_quad_diffuse.png'; img.reload()
h = bpy.data.objects.get('Kumo_Contorno')
if h: h.hide_render = True
rig = bpy.data.objects['Kumo_Rig']; pb = rig.pose.bones
if rig.animation_data: rig.animation_data.action = None
sc.render.engine = 'CYCLES'; sc.cycles.samples = 16; sc.cycles.transparent_max_bounces = 32
def cam(n, d, t, s_):
    c = bpy.data.objects.new(n, bpy.data.cameras.new(n)); sc.collection.objects.link(c); c.data.type = 'ORTHO'; c.data.ortho_scale = s_
    d = Vector(d).normalized(); c.location = Vector(t) + d * 6; c.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler(); return c
def ctrl(pE=0.0, pD=0.0, gx=0.0, gy=0.0):
    pb['controle_olhos'].location = (pE, pD, 0); pb['controle_olhar'].location = (gx, gy, 0); bpy.context.view_layer.update()
sc.render.resolution_x = sc.render.resolution_y = 480
ctrl(); sc.camera = cam('cf', (0, -1, 0), (0, 0, 0.98), 2.2); sc.render.filepath = f'{OUT}/corpo_frente.png'; bpy.ops.render.render(write_still=True)
sc.camera = cam('c34', (-0.57, -0.82, 0.05), (0, 0, 0.98), 2.2); sc.render.filepath = f'{OUT}/corpo_34.png'; bpy.ops.render.render(write_still=True)
cab = cam('hc', (0, -1, 0), (0.07, -0.3, 1.38), 1.05); sc.camera = cab; sc.render.resolution_x = sc.render.resolution_y = 380
for nm, a in (('aberto', (0, 0, 0, 0)), ('piscar_50', (0.5, 0.5, 0, 0)), ('piscar_100', (1, 1, 0, 0)), ('so_esquerdo', (1, 0, 0, 0)),
              ('olhar_dir', (0, 0, 1, 0)), ('olhar_esq', (0, 0, -1, 0)), ('olhar_cima', (0, 0, 0, 1)), ('olhar_baixo', (0, 0, 0, -1))):
    ctrl(*a); sc.render.filepath = f'{OUT}/olho_{nm}.png'; bpy.ops.render.render(write_still=True)
