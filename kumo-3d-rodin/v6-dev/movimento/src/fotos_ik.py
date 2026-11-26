"""Fotos do IK das pernas e da cabeça estável.

  blender --background kumo_v8_movimento.blend --python fotos_ik.py -- <pasta>
"""
import bpy, sys, os, math
from mathutils import Vector, Matrix

OUT = sys.argv[sys.argv.index('--') + 1]; os.makedirs(OUT, exist_ok=True); sc = bpy.context.scene
img = bpy.data.images.get('kumo_quad_diffuse')
if img: img.filepath = '/home/user/Kumo-Character/kumo-3d-rodin/textures/kumo_quad_diffuse.png'; img.reload()
h = bpy.data.objects.get('Kumo_Contorno')
if h: h.hide_render = True
rig = bpy.data.objects['Kumo_Rig']; pb = rig.pose.bones
if rig.animation_data: rig.animation_data.action = None
sc.render.engine = 'CYCLES'; sc.cycles.samples = 16; sc.render.resolution_x = 420; sc.render.resolution_y = 560

def cam(d, t, s_):
    c = bpy.data.objects.new('c', bpy.data.cameras.new('c')); sc.collection.objects.link(c); c.data.type = 'ORTHO'; c.data.ortho_scale = s_
    d = Vector(d).normalized(); c.location = Vector(t) + d * 8; c.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler(); return c

def zera():
    for b in pb:
        if b.name.startswith('MCH_'): continue
        b.rotation_mode = 'QUATERNION'; b.rotation_quaternion = (1, 0, 0, 0); b.location = (0, 0, 0)
    rig['cabeca_estavel'] = 0.0; rig['ik_pernas'] = 1.0; bpy.context.view_layer.update()

def mover(n, d):                  # desloca o osso em coordenadas do mundo
    pb[n].location = rig.data.bones[n].matrix_local.to_3x3().inverted() @ Vector(d); bpy.context.view_layer.update()

def girar(n, eixo, graus):
    pb[n].rotation_quaternion = Matrix.Rotation(math.radians(graus), 3, eixo).to_quaternion(); bpy.context.view_layer.update()

def agachar(): mover('hips', (0, 0, -0.12))
def quadril_lado(): mover('hips', (0.07, 0, -0.03))
def passo():
    mover('pe_ik.L', (0, -0.16, 0.06)); girar('pe_ik.L', 'X', -15); mover('hips', (0, -0.05, -0.04))
def estavel():
    rig['cabeca_estavel'] = 1.0; girar('spine', 'X', 20); girar('chest', 'X', 10)
def sem_estavel(): girar('spine', 'X', 20); girar('chest', 'X', 10)

ESTADOS = [('repouso', lambda: None), ('agachar', agachar), ('quadril_lado', quadril_lado), ('passo', passo),
           ('tronco_sem_cabeca_estavel', sem_estavel), ('tronco_cabeca_estavel', estavel)]
for vista, d, t, s_ in (('frente', (0, -1, 0), (0, 0, 0.95), 2.2), ('lado', (1, 0, 0), (0, 0.3, 0.95), 2.2)):
    sc.camera = cam(d, t, s_)
    for nm, f in ESTADOS:
        zera(); f(); sc.render.filepath = f'{OUT}/ik_{vista}_{nm}.png'; bpy.ops.render.render(write_still=True)
zera()
