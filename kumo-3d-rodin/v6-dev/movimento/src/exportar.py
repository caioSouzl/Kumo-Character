"""Kumo v8 (cauda nova, corretivos, IK, caminhada, corrida e pulo) → GLB e FBX do jogo e GLB da Central,
com conferência na reimportação. Baseado em olhos-novos/src/exportar_calota.py.

  blender --background kumo_v8_movimento.blend --python src/exportar.py -- <saída_jogo> <saída_central>

As restrições (IK das pernas, corretivos, cabeça estável, olhar) não vão no arquivo: o exportador grava o
resultado delas em cada quadro das animações. Fora das animações, a Central refaz as contas (olhar.json,
corretivos.json).

Os olhos em calota já usam materiais simples (emissão por textura na UV 'Jogo'), então não há bake.
O glTF e o FBX não levam constraints: o osso `olho.L/.R` sai sem o Damped Track. O motor de jogo
(e a Central) giram esse osso a partir do controle `controle_olhar`, com as contas de `olhar.json`.
"""
import bpy, sys, os, json, re, shutil
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree

args = sys.argv[sys.argv.index('--') + 1:]; OUT, OUTC = args[0], args[1]
os.makedirs(OUT, exist_ok=True); os.makedirs(OUTC, exist_ok=True)
img = bpy.data.images.get('kumo_quad_diffuse')
if img: img.filepath = '/home/user/Kumo-Character/kumo-3d-rodin/textures/kumo_quad_diffuse.png'; img.reload()
rig = bpy.data.objects['Kumo_Rig']; pb = rig.pose.bones
if rig.animation_data: rig.animation_data.action = None
for b in pb: b.location = (0, 0, 0); b.rotation_quaternion = (1, 0, 0, 0); b.rotation_euler = (0, 0, 0)
bpy.context.view_layer.update()
REP = {}

# ---------------------------------------------------------------- olhos: só a UV 'Jogo' e um material por peça
OLHOS = [o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith('KumoOlho_')]
for o in OLHOS:
    me = o.data
    if 'Jogo' in me.uv_layers:
        for nm in [x.name for x in me.uv_layers if x.name != 'Jogo']: me.uv_layers.remove(me.uv_layers[nm])
    usados = {p.material_index for p in me.polygons}
    for i in range(len(o.material_slots) - 1, 0, -1):
        if i not in usados:
            o.active_material_index = i; bpy.context.view_layer.objects.active = o; bpy.ops.object.material_slot_remove()
    for im in {n.image for s in o.material_slots if s.material for n in s.material.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image}:
        orig = bpy.path.abspath(im.filepath); p = os.path.join(OUT, im.name + '.png')
        if not os.path.exists(orig): orig = os.path.join(os.path.dirname(bpy.data.filepath), '..', 'olhos-novos', 'calota', im.name + '.png')
        if os.path.abspath(orig) != os.path.abspath(p): shutil.copy(orig, p); im.filepath = p; im.reload()

# transparência recortada (MASK): sem problema de ordem de desenho no three.js e no Godot
for o in OLHOS:
    for sl in o.material_slots:
        m = sl.material; N = m.node_tree.nodes; L = m.node_tree.links; bs = N.get('Principled BSDF')
        if bs is None or not bs.inputs['Alpha'].links or bs.inputs['Alpha'].links[0].from_node.type == 'MATH': continue
        src = bs.inputs['Alpha'].links[0].from_socket
        mt = N.new('ShaderNodeMath'); mt.operation = 'ROUND'; L.new(src, mt.inputs[0]); L.new(mt.outputs[0], bs.inputs['Alpha'])

# ---------------------------------------------------------------- contas do olhar (Blender e glTF)
def g(v): return [round(v[0], 6), round(v[2], 6), round(-v[1], 6)]   # Blender (x, y, z) → glTF (x, z, -y)
OLH = {'como_usar': ('alvo = T0 + ex*Lx*gx + ez*Lz*gy (gx, gy = controle_olhar de -1 a 1); '
                     'o osso olho gira do repouso para que seu eixo (S - H) aponte de H para o alvo (Damped Track).'),
       'gltf': {}, 'blender': {}}
for s in 'LR':
    b = rig.data.bones[f'olho.{s}']; t = rig.data.bones[f'MCH_alvo_olho.{s}']; c = pb[f'MCH_alvo_olho.{s}'].constraints['Olhar']
    M = rig.matrix_world; R3 = M.to_3x3() @ t.matrix_local.to_3x3()
    d = dict(H=M @ b.head_local, S=M @ b.tail_local, T0=M @ t.head_local, ex=R3.col[0].normalized(), ez=R3.col[2].normalized())
    OLH['blender'][s] = {k: [round(x, 6) for x in v] for k, v in d.items()} | {'Lx': c.to_max_x, 'Lz': c.to_max_z}
    OLH['gltf'][s] = {k: g(v) for k, v in d.items()} | {'Lx': c.to_max_x, 'Lz': c.to_max_z}
MED = json.load(open(os.path.join(os.path.dirname(bpy.data.filepath), '..', 'olhos-novos', 'calota', 'medicoes_calota.json')))
for s in 'LR':
    for k in ('gltf', 'blender'): OLH[k][s]['Rg'] = MED[s]['globo_raio_m']     # raio do globo: o centro da íris fica em H + (S-H)/|S-H| * Rg
def pupila(s):   # centro da pupila no globo em repouso (média dos pontos pretos da textura): onde a Central põe o losango
    o = bpy.data.objects.get(f'KumoOlho_Iris.{s}') or bpy.data.objects[f'KumoOlho_Globo.{s}']; me = o.data; uv = me.uv_layers['Jogo']   # a pupila mora na íris (o globo é só branco)
    im = next(n.image for n in o.material_slots[0].material.node_tree.nodes if n.type == 'TEX_IMAGE'); W, H = im.size
    px = np.array(im.pixels[:]).reshape(H, W, 4); soma = Vector(); n = 0
    for l in me.loops:
        u, v = uv.data[l.index].uv; c = px[min(H - 1, max(0, int(v * H))), min(W - 1, max(0, int(u * W)))]
        if c[3] > 0.5 and c[:3].max() < 0.08: soma += o.matrix_world @ me.vertices[l.vertex_index].co; n += 1
    return soma / max(n, 1)
for s in 'LR':
    P = pupila(s); OLH['blender'][s]['P'] = [round(x, 6) for x in P]; OLH['gltf'][s]['P'] = g(P)
# corretivos: o deslocamento de cada osso corr_* conforme o giro (para a Central e o jogo refazerem fora das animações)
CORR = json.load(open(os.path.join(os.path.dirname(bpy.data.filepath), 'medicoes_corretivos.json')))['parametros']
COR = {'como_usar': ('giro = rotação de "fonte" (head ou chest) em relação ao pai do MCH (chest ou hips), em euler XYZ do Blender '
                     '(ZYX no three.js); o osso corr_* anda de para_min a para_max (no espaço do próprio osso, em metros) '
                     'enquanto o giro no "eixo" vai de de_graus[0] a de_graus[1]; fora disso, fica no extremo.'), 'ossos': CORR}
for pasta in (OUT, OUTC): json.dump(COR, open(os.path.join(pasta, 'corretivos.json'), 'w'), indent=1, ensure_ascii=False)
for pasta in (OUT, OUTC): json.dump(OLH, open(os.path.join(pasta, 'olhar.json'), 'w'), indent=1, ensure_ascii=False)

# ---------------------------------------------------------------- posições de referência
OBJS = [o.name for o in bpy.data.objects if o.type == 'MESH' and (o.name in ('Kumo', 'Kumo_Boca', 'Kumo_Lingua') or o.name.startswith(('KumoOlho_', 'KumoJogo_')))]
for nm in OBJS:
    for m in bpy.data.objects[nm].modifiers:
        if m.type != 'ARMATURE': m.show_viewport = False
def pos(o):
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get(); ev = o.evaluated_get(dg); m = ev.to_mesh()
    P = np.array([tuple(ev.matrix_world @ v.co) for v in m.vertices]); ev.to_mesh_clear(); return P
REF = {n: pos(bpy.data.objects[n]) for n in OBJS}

def selecionar(nomes):
    for o in bpy.context.selected_objects: o.select_set(False)
    for o in bpy.data.objects:
        if o.name in nomes: o.hide_set(False); o.select_set(True)
    bpy.context.view_layer.objects.active = rig

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'kumo_v8_jogo.blend'), copy=True, relative_remap=False)
selecionar(OBJS + ['Kumo_Rig', 'Kumo_Contorno'])
glb = os.path.join(OUT, 'kumo_v8_jogo.glb'); fbx = os.path.join(OUT, 'kumo_v8_jogo.fbx')
bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', use_selection=True, export_apply=False, export_skins=True, export_animations=True,
                          export_animation_mode='ACTIONS', export_all_influences=False, export_morph=True, export_morph_animation=True)
bpy.ops.export_scene.fbx(filepath=fbx, use_selection=True, add_leaf_bones=False, bake_anim=True, bake_anim_use_all_actions=True, use_mesh_modifiers=False)
# GLB leve da Central: sem normais, com as animações (a página toca as do arquivo)
glc = os.path.join(OUTC, 'kumo_central.glb')
selecionar([n for n in OBJS] + ['Kumo_Rig', 'Kumo_Contorno'])
bpy.ops.export_scene.gltf(filepath=glc, export_format='GLB', use_selection=True, export_apply=False, export_skins=True, export_animations=True,
                          export_animation_mode='ACTIONS', export_all_influences=False, export_morph=True, export_morph_animation=True,
                          export_morph_normal=False, export_normals=False, export_tangents=False)
REP['kb'] = dict(glb=os.path.getsize(glb) // 1024, fbx=os.path.getsize(fbx) // 1024, central=os.path.getsize(glc) // 1024)

import struct
def mats(fn):
    with open(fn, 'rb') as f:
        f.read(12); n = struct.unpack('<I', f.read(4))[0]; f.read(4); js = json.loads(f.read(n))
    return {m['name']: m.get('alphaMode', 'OPAQUE') for m in js.get('materials', []) if m['name'].startswith('KumoOlho')}
REP['alpha_glb'] = mats(glb)
def anims(fn):
    with open(fn, 'rb') as f:
        f.read(12); n = struct.unpack('<I', f.read(4))[0]; f.read(4); js = json.loads(f.read(n))
    return [a['name'] for a in js.get('animations', [])]
REP['animacoes_glb'] = anims(glb); REP['animacoes_central'] = anims(glc)


def reimport(fn, imp):
    bpy.ops.wm.read_homefile(use_empty=True); imp(fn); s2 = bpy.context.scene
    for a in s2.objects:
        if a.type == 'ARMATURE' and a.animation_data: a.animation_data.action = None
    res = {}
    for nm in OBJS:
        o = next((x for x in s2.objects if x.type == 'MESH' and re.sub(r'\.\d{3}$', '', x.name) == nm), None)   # o importador põe .001
        if o is None: res[nm] = 'faltou'; continue
        P1 = pos(o); kd = KDTree(len(REF[nm]))
        for i, p in enumerate(REF[nm]): kd.insert(Vector(p), i)
        kd.balance(); res[nm] = round(max(kd.find(Vector(p))[2] for p in P1) * 1000, 2)
    return res


REP['glb_erro_max_mm'] = reimport(glb, lambda f: bpy.ops.import_scene.gltf(filepath=f))
REP['fbx_erro_max_mm'] = reimport(fbx, lambda f: bpy.ops.import_scene.fbx(filepath=f))
REP['central_erro_max_mm'] = reimport(glc, lambda f: bpy.ops.import_scene.gltf(filepath=f))
json.dump(REP, open(os.path.join(OUT, 'medicoes_exportacao.json'), 'w'), indent=1, ensure_ascii=False)
print('EXP', json.dumps(REP, ensure_ascii=False))
