"""Fotos dos ombros: mesmas poses no Kumo de antes e no de agora.  python fotos_ombros.py <blend> <saída> <K> <KF>"""
import bpy, sys, os, math
from mathutils import Vector, Matrix
SRC, OUT, K, KF = sys.argv[-4:]; K = float(K); KF = float(KF); os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=SRC); sc = bpy.context.scene
img = bpy.data.images.get('kumo_quad_diffuse')
if img: img.filepath = '/home/user/Kumo-Character/kumo-3d-rodin/textures/kumo_quad_diffuse.png'; img.reload()
h = bpy.data.objects.get('Kumo_Contorno')
if h: h.hide_render = True
rig = bpy.data.objects['Kumo_Rig']; pb = rig.pose.bones
if rig.animation_data: rig.animation_data.action = None
sc.render.engine = 'CYCLES'; sc.cycles.samples = 16; sc.cycles.transparent_max_bounces = 32; sc.render.resolution_x = sc.render.resolution_y = 520
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
def cam(d, t, s_):
    c = bpy.data.objects.new('c', bpy.data.cameras.new('c')); sc.collection.objects.link(c); c.data.type = 'ORTHO'; c.data.ortho_scale = s_
    d = Vector(d).normalized(); c.location = Vector(t) + d * 6; c.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler(); return c
for sd in 'LR':
    hd = rig.matrix_world @ rig.data.bones[f'upper_arm.{sd}'].head_local; sx = 1 if hd.x > 0 else -1
    hd = Vector((0.25 * sx, -0.04, 0.74))      # alvo fixo (o mesmo antes e agora)
    vistas = {'frente': cam((0.25 * sx, -1, 0.15), (hd.x + 0.12 * sx, hd.y, hd.z + 0.05), 1.15),
              'costas': cam((0.45 * sx, 1, 0.55), (hd.x + 0.1 * sx, hd.y, hd.z + 0.08), 1.0)}
    for tipo, a in (('erguer', 90), ('erguer', 150), ('frente', 90)):
        reset(); mover(sd, tipo, a)
        for vn, c in vistas.items():
            sc.camera = c; sc.render.filepath = f'{OUT}/{sd}_{tipo}{a}_{vn}.png'; bpy.ops.render.render(write_still=True)
reset(); print('FO OK')
