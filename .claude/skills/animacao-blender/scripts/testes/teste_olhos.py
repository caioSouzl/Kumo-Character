# Teste das ferramentas de modelagem e olhos. Uso: blender --background --python teste_olhos.py -- <pasta_de_saida>
import sys, math, bpy
import os; sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # pasta scripts/
import referencias_cruzadas as rc, olhos
from mathutils import Vector
D = sys.argv[sys.argv.index('--')+1]
bpy.ops.wm.read_factory_settings(use_empty=True)
# imagens de teste: retângulo escuro (personagem) com pés a 10% e topo a 90%
def img(nome, w, h, base, topo):
    im = bpy.data.images.new(nome, w, h, alpha=True); px = [1.0]*(w*h*4)
    for y in range(int(base*h), int(topo*h)):
        for x in range(w//3, 2*w//3): i=(y*w+x)*4; px[i:i+3]=[0.2,0.2,0.2]
    im.pixels = px; im.filepath_raw = f'{D}/{nome}.png'; im.file_format='PNG'; im.save(); return f'{D}/{nome}.png'
f, s = rc.montar(img('frente',100,200,0.1,0.9), img('lado',100,200,0.1,0.9), altura=2.0)
print('REF', f.rotation_euler[:], s.rotation_euler[:], rc.conferir(f, s))
f2, s2 = rc.montar(img('frente_b',100,200,0.1,0.9), img('lado_b',100,200,0.15,0.9))
print('REF_ERRADA', rc.conferir(f2, s2)['pes_m'])
for o in (f, s, f2, s2): bpy.data.objects.remove(o)
# decal: pupila escura com alfa
w = 64; pu = bpy.data.images.new('pupila', w, w, alpha=True); px=[0.0]*(w*w*4)
for y in range(w):
    for x in range(w):
        if (x-w/2+.5)**2+(y-w/2+.5)**2 < (w*0.35)**2: px[(y*w+x)*4:(y*w+x)*4+4]=[0.02,0.02,0.02,1]
pu.pixels = px
bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=64, ring_count=32); cab = bpy.context.object
cab.data.materials.append(bpy.data.materials.new('Pele'))
centro = Vector((0.35, -0.94, 0.0))
e = olhos.decal(cab, 'Ojo.L', pu, centro, tamanho=0.25)
fs = olhos.faces_no_raio(cab, centro, 0.25); olhos.atribuir_faces(cab, 'Ojo.L', fs)
arm = bpy.data.armatures.new('ojos'); rig = bpy.data.objects.new('ojosDecals', arm); bpy.context.scene.collection.objects.link(rig)
foco = olhos.rig_olhar(rig, [('OJO.L', e, centro)], foco=(0.35, -3, 0))
sc = bpy.context.scene; sc.render.engine='CYCLES'; sc.cycles.samples=8; sc.cycles.device='CPU'; sc.render.resolution_x=sc.render.resolution_y=160
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera=cam
cam.location=(0,-6,0); cam.rotation_euler=(math.radians(90),0,0); cam.data.type='ORTHO'; cam.data.ortho_scale=2.4
w0 = bpy.data.worlds.new('w'); sc.world=w0; w0.use_nodes=True; w0.node_tree.nodes['Background'].inputs[1].default_value=3
def px_em(xw, zw, nome):
    sc.render.filepath=f'{D}/{nome}.png'; bpy.ops.render.render(write_still=True)
    im = bpy.data.images.load(sc.render.filepath); W=im.size[0]
    u = int((xw/2.4+0.5)*W); v=int((zw/2.4+0.5)*W); p=im.pixels[(v*W+u)*4:(v*W+u)*4+3]; return round(sum(p)/3,3)
print('PUPILA_CENTRO', px_em(0.35, 0.0, 'r0'), 'ESCLERA_LADO', px_em(0.35+0.11, 0.0, 'r0b'))
from mathutils import Matrix
foco.matrix = Matrix.Translation((1.25, -3, 0)) @ foco.matrix.to_3x3().to_4x4()   # foco 0,9 m para +X (direita da tela)
bpy.context.view_layer.update()
xe = e.matrix_world.translation.x
print('PUPILA_NOVO_LUGAR', px_em(xe, e.matrix_world.translation.z, 'r1'), 'LUGAR_ANTIGO', px_em(0.35, 0.0, 'r1b'))
print('EMPTY_MOVEU', [round(v,3) for v in (e.matrix_world.translation)], 'vs centro', tuple(centro))
# íris para dentro
bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(5,0,0)); g = bpy.context.object; g.scale=(1,0.5,1)
g.data.materials.append(bpy.data.materials.new('Olho'))
vg = g.vertex_groups.new(name='Iris'); vg.add([v.index for v in g.data.vertices if v.co.y < -0.6], 1.0, 'REPLACE')
antes = sum(1 for p in g.data.polygons if p.normal.y < 0 and p.center.y < -0.6)
n = olhos.iris_para_dentro(g, 'Iris')
depois = sum(1 for p in g.data.polygons if p.normal.y < 0 and p.center.y < -0.6)
print('IRIS', n, 'frente_para_fora_antes', antes, 'depois', depois, 'culling', g.data.materials[0].use_backface_culling)
