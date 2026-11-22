"""Fotos dos olhos novos: rosto de frente e 3/4 em 8 estados + corpo inteiro.
  blender --background kumo_v6_olhos_novos.blend --python fotos.py -- <saída> [prefixo]"""
import bpy, sys, os
from mathutils import Vector
OUT = sys.argv[sys.argv.index('--') + 1]; PRE = sys.argv[sys.argv.index('--') + 2] if len(sys.argv) > sys.argv.index('--') + 2 else ''
os.makedirs(OUT, exist_ok=True); sc = bpy.context.scene
img = bpy.data.images.get('kumo_quad_diffuse')
if img: img.filepath = '/home/user/Kumo-Character/kumo-3d-rodin/textures/kumo_quad_diffuse.png'; img.reload()
h = bpy.data.objects.get('Kumo_Contorno')
if h: h.hide_render = True
rig = bpy.data.objects['Kumo_Rig']; pb = rig.pose.bones
if rig.animation_data: rig.animation_data.action = None
sc.render.engine = 'CYCLES'; sc.cycles.samples = 16; sc.cycles.transparent_max_bounces = 32
sc.render.film_transparent = False
def cam(n, d, t, s_):
    c = bpy.data.objects.new(n, bpy.data.cameras.new(n)); sc.collection.objects.link(c); c.data.type = 'ORTHO'; c.data.ortho_scale = s_
    d = Vector(d).normalized(); c.location = Vector(t) + d * 6; c.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler(); return c
def ctrl(pE=0.0, pD=0.0, gx=0.0, gy=0.0):
    pb['controle_olhos'].location = (pE, pD, 0); pb['controle_olhar'].location = (gx, gy, 0); bpy.context.view_layer.update()
ESTADOS = (('aberto', (0, 0, 0, 0)), ('piscar_50', (0.5, 0.5, 0, 0)), ('piscar_100', (1, 1, 0, 0)), ('so_esquerdo', (1, 0, 0, 0)),
           ('olhar_dir', (0, 0, 1, 0)), ('olhar_esq', (0, 0, -1, 0)), ('olhar_cima', (0, 0, 0, 1)), ('olhar_baixo', (0, 0, 0, -1)))
sc.render.resolution_x = sc.render.resolution_y = 520
ctrl(); sc.camera = cam('cf', (0, -1, 0), (0, 0, 0.98), 2.2); sc.render.filepath = f'{OUT}/{PRE}corpo_frente.png'; bpy.ops.render.render(write_still=True)
sc.camera = cam('c34', (-0.57, -0.82, 0.05), (0, 0, 0.98), 2.2); sc.render.filepath = f'{OUT}/{PRE}corpo_34.png'; bpy.ops.render.render(write_still=True)
sc.render.resolution_x = sc.render.resolution_y = 420
for vista, d_, t_ in (('frente', (0, -1, 0), (0.07, -0.3, 1.38)), ('34', (-0.57, -0.82, 0.05), (0.05, -0.3, 1.38)), ('lado', (1, -0.25, 0.02), (0.2, -0.2, 1.38))):
    sc.camera = cam('h' + vista, d_, t_, 1.05)
    for nm, a in ESTADOS:
        if vista != 'frente' and nm not in ('aberto', 'olhar_dir', 'olhar_esq', 'piscar_100'): continue
        ctrl(*a); sc.render.filepath = f'{OUT}/{PRE}olho_{vista}_{nm}.png'; bpy.ops.render.render(write_still=True)
ctrl()
