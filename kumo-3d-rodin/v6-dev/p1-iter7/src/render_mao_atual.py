"""Renderiza a mão do modelo ATUAL nas mesmas direções de câmera do P1 iteração 6 (somente leitura; nada é salvo no .blend).
  python render_mao_atual.py <kumo_rigged.blend> <pasta de saída>"""
import bpy, sys, os, math
from mathutils import Vector
SRC, OUT = sys.argv[-2], sys.argv[-1]; os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=SRC)
REPO = os.path.dirname(os.path.abspath(SRC))
img = bpy.data.images['kumo_quad_diffuse']; img.filepath = os.path.join(REPO, 'textures', 'kumo_quad_diffuse.png'); img.reload()
sc = bpy.context.scene; B = bpy.data.objects['Kumo_Rig'].data.bones
W = B['hand.L'].head_local; d = (B['forearm.L'].tail_local - B['forearm.L'].head_local).normalized()
pn = (Vector((0, 1, 0)) - d * d.y).normalized()
me = bpy.data.objects['Kumo'].data           # centro da massa da mão atual (vértices abaixo do punho, perto dele)
pts = [v.co for v in me.vertices if (v.co - W).length < 0.14 and (v.co - W).dot(d) > -0.01 and v.co.x > 0.30]
HC = sum(pts, Vector()) / len(pts)
sc.render.film_transparent = False; sc.render.engine = 'CYCLES'; sc.cycles.samples = 12; sc.render.resolution_x = sc.render.resolution_y = 560
def cam(n, v):
    c = bpy.data.objects.new(n, bpy.data.cameras.new(n)); sc.collection.objects.link(c); c.data.type = 'ORTHO'; c.data.ortho_scale = 0.30
    v = Vector(v).normalized(); c.location = HC + v * 4; c.rotation_euler = (-v).to_track_quat('-Z', 'Y').to_euler(); return c
for k, v in (('frente', (0, -1, 0)), ('lado', (1, 0, 0)), ('dorso', -pn), ('perspectiva', (0.35, -1, 0.1))):
    sc.camera = cam(k, v); sc.render.filepath = os.path.join(OUT, f'atual_repouso_{k}.png'); bpy.ops.render.render(write_still=True)
print('OK')
