"""Fotos da cauda: repouso, esticada, enrolada e abanando, vista de lado e de cima.

  blender --background kumo_v8_movimento.blend --python fotos_cauda.py -- <pasta>
"""
import bpy, sys, os, math
from mathutils import Vector, Quaternion

OUT = sys.argv[sys.argv.index('--') + 1]; os.makedirs(OUT, exist_ok=True); sc = bpy.context.scene
img = bpy.data.images.get('kumo_quad_diffuse')
if img: img.filepath = '/home/user/Kumo-Character/kumo-3d-rodin/textures/kumo_quad_diffuse.png'; img.reload()
h = bpy.data.objects.get('Kumo_Contorno')
if h: h.hide_render = True
rig = bpy.data.objects['Kumo_Rig']; pb = rig.pose.bones
if rig.animation_data: rig.animation_data.action = None
CAUDA = sorted(n.name for n in pb if n.name.startswith('tail_'))
sc.render.engine = 'CYCLES'; sc.cycles.samples = 16; sc.render.resolution_x = 640; sc.render.resolution_y = 480

def cam(d, t, s_):
    c = bpy.data.objects.new('c', bpy.data.cameras.new('c')); sc.collection.objects.link(c); c.data.type = 'ORTHO'; c.data.ortho_scale = s_
    d = Vector(d).normalized(); c.location = Vector(t) + d * 8; c.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler(); return c

def zera():
    for b in pb: b.rotation_quaternion = (1, 0, 0, 0); b.location = (0, 0, 0)
    bpy.context.view_layer.update()

def esticar(fator=1.0):            # cada osso gira para a direção do primeiro (fator 1 = reta)
    D = Vector((0, 1, -0.25)).normalized()      # reta: para trás, descendo um pouco
    for n in CAUDA:
        p = pb[n]; bpy.context.view_layer.update()
        cur = (rig.matrix_world.to_3x3() @ p.matrix.to_3x3()).col[1].normalized()
        q = Quaternion().slerp(cur.rotation_difference(D), fator)
        M = p.matrix.copy(); R = rig.matrix_world.to_3x3().inverted() @ q.to_matrix() @ rig.matrix_world.to_3x3()
        Mn = (R @ M.to_3x3()).to_4x4(); Mn.translation = M.translation; p.matrix = Mn
    bpy.context.view_layer.update()

def local(eixo, graus):            # o mesmo giro em todos os ossos da cauda (como os controles da Central)
    for n in CAUDA: pb[n].rotation_quaternion = Quaternion(eixo, math.radians(graus))
    bpy.context.view_layer.update()

ESTADOS = [('repouso', lambda: None), ('esticada', lambda: esticar(1.0)), ('meio_esticada', lambda: esticar(0.5)),
           ('enrolada', lambda: local((1, 0, 0), 12)), ('abanar', lambda: local((0, 0, 1), 6))]
for vista, d, t, s_ in (('lado', (1, 0, 0), (0, 0.75, 0.75), 3.0), ('cima', (0, 0, 1), (0, 0.8, 0.4), 3.4)):
    sc.camera = cam(d, t, s_)
    for nm, f in ESTADOS:
        if vista == 'cima' and nm not in ('repouso', 'abanar', 'esticada'): continue
        zera(); f(); sc.render.filepath = f'{OUT}/cauda_{vista}_{nm}.png'; bpy.ops.render.render(write_still=True)
