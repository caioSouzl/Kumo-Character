"""Fotos do tronco e do pescoço dobrando: frente, trás, lado e torção, para achar onde a pele amassa.

  blender --background kumo_v8_movimento.blend --python fotos_tronco.py -- <pasta> [prefixo]
"""
import bpy, sys, os, math
from mathutils import Vector, Quaternion, Matrix

A = sys.argv[sys.argv.index('--') + 1:]; OUT = A[0]; PRE = A[1] if len(A) > 1 else ''
os.makedirs(OUT, exist_ok=True); sc = bpy.context.scene
img = bpy.data.images.get('kumo_quad_diffuse')
if img: img.filepath = '/home/user/Kumo-Character/kumo-3d-rodin/textures/kumo_quad_diffuse.png'; img.reload()
h = bpy.data.objects.get('Kumo_Contorno')
if h: h.hide_render = True
rig = bpy.data.objects['Kumo_Rig']; pb = rig.pose.bones
if rig.animation_data: rig.animation_data.action = None
sc.render.engine = 'CYCLES'; sc.cycles.samples = 16; sc.render.resolution_x = 480; sc.render.resolution_y = 560

def cam(d, t, s_):
    c = bpy.data.objects.new('c', bpy.data.cameras.new('c')); sc.collection.objects.link(c); c.data.type = 'ORTHO'; c.data.ortho_scale = s_
    d = Vector(d).normalized(); c.location = Vector(t) + d * 8; c.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler(); return c

def zera():
    for b in [x for x in pb if not x.name.startswith('MCH_')]: b.rotation_mode = 'QUATERNION'; b.rotation_quaternion = (1, 0, 0, 0); b.location = (0, 0, 0)
    bpy.context.view_layer.update()

def girar(n, eixo, graus):        # gira o osso em torno de um eixo do mundo, a partir da pose atual
    p = pb[n]; bpy.context.view_layer.update()
    R = rig.matrix_world.to_3x3().inverted() @ Matrix.Rotation(math.radians(graus), 3, Vector(eixo)) @ rig.matrix_world.to_3x3()
    M = p.matrix.copy(); Mn = (R @ M.to_3x3()).to_4x4(); Mn.translation = M.translation; p.matrix = Mn
    bpy.context.view_layer.update()

def pose(itens):
    def f():
        for n, e, g in itens: girar(n, e, g)
    return f

X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)
# o Kumo olha para -Y: girar em X com graus negativos dobra para a frente
POSES = [
    ('cabeca_cima', 'lado', pose([('neck', X, -30), ('head', X, -25)])),
    ('cabeca_baixo', 'lado', pose([('neck', X, 30), ('head', X, 25)])),
    ('cabeca_lado_E', 'frente', pose([('neck', Y, 25), ('head', Y, 20)])),
    ('cabeca_lado_D', 'frente', pose([('neck', Y, -25), ('head', Y, -20)])),
    ('cabeca_girar', 'frente', pose([('neck', Z, 35), ('head', Z, 35)])),
    ('costas_frente', 'lado', pose([('spine', X, 25), ('chest', X, 25)])),
    ('costas_tras', 'lado', pose([('spine', X, -20), ('chest', X, -20)])),
    ('costas_lado', 'frente', pose([('spine', Y, 20), ('chest', Y, 20)])),
]
CAMS = {'lado': cam((1, 0, 0), (0, 0, 1.0), 1.6), 'frente': cam((0, -1, 0), (0, 0, 1.0), 1.6), 'tres_quartos': cam((0.6, -0.8, 0.1), (0, 0, 1.05), 2.1)}
for nm, v, f in POSES:
    sc.camera = CAMS[v]; zera(); f(); sc.render.filepath = f'{OUT}/{PRE}{nm}.png'; bpy.ops.render.render(write_still=True)
