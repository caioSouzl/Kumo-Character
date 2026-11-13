"""Teste 1: o Kumo 3D oficial renderizado como desenho (emissão chapada + contorno), em 8 ângulos, para comparar
com as vistas da folha de modelo.   python vistas.py <blend> <saída>"""
import bpy, sys, os, math
from mathutils import Vector
SRC, OUT = sys.argv[-2:]; os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=SRC); sc = bpy.context.scene
img = bpy.data.images.get('kumo_quad_diffuse')
if img: img.filepath = '/home/user/Kumo-Character/kumo-3d-rodin/textures/kumo_quad_diffuse.png'; img.reload()
TEXD = '/home/user/Kumo-Character/kumo-3d-rodin/v6-dev/olhos-jogo/texturas'
for im in bpy.data.images:
    if im.name.startswith('olho_') and not os.path.exists(bpy.path.abspath(im.filepath)): im.filepath = os.path.join(TEXD, os.path.basename(im.filepath)); im.reload()
rig = bpy.data.objects['Kumo_Rig']
if rig.animation_data: rig.animation_data.action = None
for b in rig.pose.bones: b.rotation_quaternion = (1, 0, 0, 0); b.rotation_euler = (0, 0, 0); b.location = (0, 0, 0)
sc.render.engine = 'CYCLES'; sc.cycles.samples = 16; sc.render.film_transparent = True; sc.cycles.transparent_max_bounces = 32
sc.render.resolution_x = sc.render.resolution_y = 900
c = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(c); c.data.type = 'ORTHO'; c.data.ortho_scale = 2.3; sc.camera = c
alvo = Vector((0, 0, 1.0))
for ang in range(0, 360, 45):
    a = math.radians(ang); d = Vector((math.sin(a), -math.cos(a), 0.0))   # 0° = de frente (câmera em −Y)
    c.location = alvo + d * 8; c.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = os.path.join(OUT, f'ang{ang:03d}.png'); bpy.ops.render.render(write_still=True)
print('VI OK')
