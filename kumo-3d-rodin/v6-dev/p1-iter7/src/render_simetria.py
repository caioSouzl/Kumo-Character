"""Prévia de simetria: braço A7 (P1 iteração 7) espelhado também para o lado direito, nos dois lados do corpo atual.
Só renderiza; nada é gravado em nenhum .blend.   python render_simetria.py <kumo_rigged.blend> <p1_iter7_A7.blend> <saida>"""
import bpy, sys, os, math
from mathutils import Vector
SRC, ARMB, OUT = sys.argv[-3], sys.argv[-2], sys.argv[-1]; os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=SRC)
REPO = os.path.dirname(os.path.abspath(SRC))
img = bpy.data.images['kumo_quad_diffuse']; img.filepath = os.path.join(REPO, 'textures', 'kumo_quad_diffuse.png'); img.reload()
sc = bpy.context.scene; body = bpy.data.objects['Kumo']; me = body.data
with bpy.data.libraries.load(ARMB, link=False) as (src, dst): dst.objects = [n for n in src.objects]
for o in dst.objects: sc.collection.objects.link(o)
armL = bpy.data.objects['P1i7_Braco_E']
armR = armL.copy(); armR.data = armL.data; armR.name = 'P1i7_Braco_D_espelho'; sc.collection.objects.link(armR)
armR.modifiers.clear(); armR.parent = None; armR.matrix_world = armL.matrix_world.copy(); armR.scale.x *= -1; armR.location.x *= -1
vg = {g.index: g.name for g in body.vertex_groups}
BRACOS = {'upper_arm.L', 'forearm.L', 'hand.L', 'upper_arm.R', 'forearm.R', 'hand.R'}
def dom(v):
    ws = [(vg[g.group], g.weight) for g in v.groups if not vg[g.group].startswith('outline')]
    return max(ws, key=lambda x: x[1])[0] if ws else None
keep = [v.index for v in me.vertices if dom(v) not in BRACOS]
gm = body.vertex_groups.new(name='prev_sem_bracos'); gm.add(keep, 1.0, 'REPLACE')
mk = body.modifiers.new('Prev_Mascara', 'MASK'); mk.vertex_group = 'prev_sem_bracos'
with bpy.context.temp_override(object=body, active_object=body):
    bpy.ops.object.modifier_move_to_index(modifier='Prev_Mascara', index=1)
sc.render.engine = 'CYCLES'; sc.cycles.samples = 16; sc.render.film_transparent = False; sc.render.resolution_x = 700; sc.render.resolution_y = 900
if not any(o.type == 'LIGHT' for o in sc.objects):
    L = bpy.data.objects.new('Luz', bpy.data.lights.new('Luz', 'SUN')); sc.collection.objects.link(L); L.rotation_euler = (math.radians(50), math.radians(10), math.radians(-30)); L.data.energy = 3
def cam(n, d):
    c = bpy.data.objects.new(n, bpy.data.cameras.new(n)); sc.collection.objects.link(c); c.data.type = 'ORTHO'; c.data.ortho_scale = 2.2
    d = Vector(d).normalized(); t = Vector((0, 0, 0.98)); c.location = t + d * 5; c.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler(); return c
for o in bpy.data.objects:
    if o.type == 'MESH': o.hide_render = o.name not in ('Kumo', 'P1i7_Braco_E', 'P1i7_Braco_D_espelho')
for k, d in (('frente', (0, -1, 0)), ('tres_quartos', (0.6, -1, 0.1)), ('costas', (0, 1, 0))):
    sc.camera = cam(k, d); sc.render.filepath = os.path.join(OUT, f'simetria_{k}.png'); bpy.ops.render.render(write_still=True)
print('OK')
