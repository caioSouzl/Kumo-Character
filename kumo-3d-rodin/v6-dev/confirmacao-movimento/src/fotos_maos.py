"""Fotos de confirmação: movimento das mãos e dedos (versão maos-corretivas, só leitura)."""
import bpy, sys, os
sys.path.insert(0, '/home/user/Kumo-Character/kumo-3d-rodin/v6-dev/maos-corretivas/src')
from kumo_lib import Kumo
from mathutils import Vector
SRC, OUT = sys.argv[-2:]; os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=SRC); sc = bpy.context.scene
rig = bpy.data.objects['Kumo_Rig']; body = bpy.data.objects['Kumo']
h = bpy.data.objects.get('Kumo_Contorno')
if h: h.hide_render = True
K = Kumo(rig, body); sc.render.engine = 'CYCLES'; sc.cycles.samples = 16; sc.render.resolution_x = sc.render.resolution_y = 420
def cam(n, d, t, s_):
    c = bpy.data.objects.new(n, bpy.data.cameras.new(n)); sc.collection.objects.link(c); c.data.type = 'ORTHO'; c.data.ortho_scale = s_
    d = Vector(d).normalized(); c.location = Vector(t) + d * 6; c.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler(); return c
POSES = ['repouso', 'mao_aberta', 'dedos_45', 'mao_fechada', 'polegar', 'dedos_alternados', 'punho_45']
for sd in ('L', 'R'):
    for p in POSES:
        K.reset()
        if p != 'repouso': K.poses(sd)[p]()
        bpy.context.view_layer.update()
        hc = (rig.pose.bones[f'hand.{sd}'].head + rig.pose.bones[f'dedo2_1.{sd}'].tail) / 2; sx = 1 if sd == 'L' else -1
        c = cam(f'c{sd}{p}', (0.35 * sx, -1, 0.15), hc, 0.42); sc.camera = c
        sc.render.filepath = f'{OUT}/mao_{sd}_{p}.png'; bpy.ops.render.render(write_still=True)
K.reset()
for sd in ('L', 'R'): K.poses(sd)['mao_fechada']()
sc.camera = cam('corpo', (0, -1, 0), (0, 0, 0.98), 2.2); sc.render.filepath = f'{OUT}/corpo_maos_fechadas.png'; bpy.ops.render.render(write_still=True)
