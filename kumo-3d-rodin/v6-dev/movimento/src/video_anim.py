"""Quadros das animações (para a folha e o vídeo): vista de 3/4 e de lado.

  blender --background kumo_v8_movimento.blend --python video_anim.py -- <pasta> [passo]
"""
import bpy, sys, os
from mathutils import Vector

A = sys.argv[sys.argv.index('--') + 1:]; OUT = A[0]; PASSO = int(A[1]) if len(A) > 1 else 1
sc = bpy.context.scene
img = bpy.data.images.get('kumo_quad_diffuse')
if img: img.filepath = '/home/user/Kumo-Character/kumo-3d-rodin/textures/kumo_quad_diffuse.png'; img.reload()
h = bpy.data.objects.get('Kumo_Contorno')
if h: h.hide_render = True
rig = bpy.data.objects['Kumo_Rig']
sc.render.engine = 'CYCLES'; sc.cycles.samples = 8; sc.render.resolution_x = 400; sc.render.resolution_y = 500
sc.cycles.use_denoising = True

def cam(d, t, s_):
    c = bpy.data.objects.new('c', bpy.data.cameras.new('c')); sc.collection.objects.link(c); c.data.type = 'ORTHO'; c.data.ortho_scale = s_
    d = Vector(d).normalized(); c.location = Vector(t) + d * 8; c.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler(); return c
VISTAS = A[2].split(',') if len(A) > 2 else ['34', 'lado']
TODAS = {'34': ((0.65, -0.75, 0.12), (0.05, 0.15, 0.95), 2.7), 'lado': ((1, 0, 0.05), (0, 0.3, 0.95), 2.6)}
CAMS = {v: cam(*TODAS[v]) for v in VISTAS}
rig.animation_data_create()
for nome in ('Caminhar', 'Correr', 'Pular'):
    a = bpy.data.actions[nome]; rig.animation_data.action = a
    for v, c in CAMS.items():
        sc.camera = c; os.makedirs(f'{OUT}/{nome}_{v}', exist_ok=True)
        for f in range(int(a.frame_start), int(a.frame_end) + 1, PASSO):
            sc.frame_set(f); sc.render.filepath = f'{OUT}/{nome}_{v}/{f:03d}.png'; bpy.ops.render.render(write_still=True)
