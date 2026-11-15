"""Língua retrátil de camaleão para o Kumo 3D.

Como no camaleão de verdade (de Groot & van Leeuwen 2004; Anderson & Deban 2010): a língua fica guardada no chão da
boca, sai um pouco para mirar (o hioide empurra para a frente), dispara num estalo elástico (≈0,07 s, até ~1,5–2×
o corpo), afina enquanto estica, tem uma ponta em bola (a almofada que gruda) e volta mais devagar.

Rig (exporta para o Godot, só osso e sem escala na ponta):
  jaw → lingua_mira (base da língua; girar = mirar)
        → lingua_00 … lingua_10 (irmãos; deslizam no eixo da língua)  → lingua_ponta (bola)
        → lingua_controle (não deforma): posição Y = quanto a língua sai, em metros (0 = guardada)
  Drivers: lingua_i.y = E·i/10 ; ponta.y = E ; os segmentos do meio afinam quando E cresce.

  python lingua.py <kumo_boca.blend> <saída.blend>
"""
import bpy, bmesh, sys, math, json
import numpy as np
from mathutils import Vector, Matrix
SRC, DST = sys.argv[-2:]
bpy.ops.wm.open_mainfile(filepath=SRC)
J = json.load(open(SRC + '.labios.json'))
rig = bpy.data.objects['Kumo_Rig']; body = bpy.data.objects['Kumo']
for b in rig.pose.bones: b.rotation_quaternion = (1, 0, 0, 0); b.rotation_euler = (0, 0, 0); b.location = (0, 0, 0); b.scale = (1, 1, 1)
DOBRA = np.array(J['dobra']); F2 = np.array(J['frente']); F3 = np.array([F2[0], F2[1], 0.0])
P = np.array([tuple(body.matrix_world @ v.co) for v in body.data.vertices])
inf = J['inf']; meio = min(inf, key=lambda i: abs(np.degrees(np.arctan2((P[i, :2] - J['centro']) @ np.array(J['lado']), (P[i, :2] - J['centro']) @ F2))))
LABIO = P[meio]                                       # meio do lábio de baixo
N = 10; R_LARG, R_ALT, R_BOLA = 0.040, 0.022, 0.034
from mathutils.bvhtree import BVHTree
dg = bpy.context.evaluated_depsgraph_get(); ev = body.evaluated_get(dg); em_ = ev.to_mesh(); em_.calc_loop_triangles()
arv = BVHTree.FromPolygons([ev.matrix_world @ v.co for v in em_.vertices], [tuple(t.vertices) for t in em_.loop_triangles]); ev.to_mesh_clear()
def folga(pts):
    m = 9.0
    for v in pts:
        co, nr, _, dd = arv.find_nearest(Vector(v)); m = min(m, -(Vector(v) - co).dot(nr))
    return m
def amostra(base, ponta):
    """pontos da superfície da língua guardada (tubo + bola), para testar se cabe"""
    e = (ponta - base) / np.linalg.norm(ponta - base); la = np.cross(e, [0, 0, 1.0]); la /= np.linalg.norm(la); ci = np.cross(la, e); L = np.linalg.norm(ponta - base); pts = []
    for u in np.linspace(0, 1, 12):
        for a in np.linspace(0, 2 * math.pi, 10, endpoint=False):
            pts.append(base + e * L * u + la * math.cos(a) * R_LARG + ci * math.sin(a) * R_ALT)
    cb = ponta + e * R_BOLA * 0.6
    for a in np.linspace(0, 2 * math.pi, 10, endpoint=False):
        for b in np.linspace(-1, 1, 5): pts.append(cb + (la * math.cos(a) + ci * math.sin(a)) * R_BOLA * math.sqrt(1 - b * b) + e * R_BOLA * b)
    return pts
melhor = None
for frac in (0.80, 0.75, 0.70, 0.65, 0.60, 0.55):
    for queda in (0.045, 0.06, 0.075, 0.09):
        base = DOBRA + (LABIO - DOBRA) * 0.20 + np.array([0, 0, -0.04]); ponta = DOBRA + (LABIO - DOBRA) * frac + np.array([0, 0, -queda])
        f_ = folga(amostra(base, ponta))
        if f_ >= 0.005: melhor = (frac, queda, base, ponta, f_); break
    if melhor: break
assert melhor, 'a língua não coube dentro da cabeça'
frac, queda, BASE, PONTA, f_ = melhor
print('LINGUA posição: ponta a', frac, 'do caminho até o lábio, ', queda, 'm abaixo; folga', round(f_ * 1000, 1), 'mm', flush=True)
EIXO = (PONTA - BASE) / np.linalg.norm(PONTA - BASE); L0 = float(np.linalg.norm(PONTA - BASE))
print('LINGUA comprimento guardada', round(L0, 3), 'eixo', EIXO.round(3), flush=True)
# ---------------- malha: tubo achatado + bola na ponta
LAT = np.cross(EIXO, [0, 0, 1.0]); LAT /= np.linalg.norm(LAT); CIMA = np.cross(LAT, EIXO)
NR, NA = 36, 14; verts = []; faces = []; u_de = []
for k in range(NR + 1):
    u = k / NR; c = BASE + EIXO * L0 * u
    afina = 1.0 - 0.25 * u                              # um pouco mais fina perto da ponta, antes da bola
    for j in range(NA):
        a = 2 * math.pi * j / NA
        verts.append(c + LAT * math.cos(a) * R_LARG * afina + CIMA * math.sin(a) * R_ALT * afina); u_de.append(u)
NB = 8; c_b = PONTA + EIXO * R_BOLA * 0.6; ini_b = len(verts)
for k in range(1, NB + 1):                               # bola: anéis de uma esfera, do pescoço até a frente
    th = math.pi * (0.25 + 0.75 * k / NB); rr = R_BOLA * math.sin(th); dx = -R_BOLA * math.cos(th)
    for j in range(NA):
        a = 2 * math.pi * j / NA
        verts.append(c_b + EIXO * dx + LAT * math.cos(a) * rr + CIMA * math.sin(a) * rr * 0.8); u_de.append(2.0)
verts.append(c_b + EIXO * R_BOLA); u_de.append(2.0); topo = len(verts) - 1
verts.append(BASE - EIXO * 0.01); u_de.append(0.0); fundo = len(verts) - 1
for k in range(NR + NB):
    for j in range(NA):
        a_, b_ = k * NA + j, k * NA + (j + 1) % NA
        faces.append((a_, b_, b_ + NA, a_ + NA))
ult = (NR + NB) * NA
for j in range(NA): faces.append((ult + j, ult + (j + 1) % NA, topo)); faces.append((fundo, (j + 1) % NA, j))
MWi = np.linalg.inv(np.array(body.matrix_world))
me = bpy.data.meshes.new('Kumo_Lingua'); me.from_pydata([tuple(MWi[:3, :3] @ v + MWi[:3, 3]) for v in verts], [], faces); me.update()
for p in me.polygons: p.use_smooth = True
ob = bpy.data.objects.new('Kumo_Lingua', me); bpy.context.scene.collection.objects.link(ob); ob.matrix_world = body.matrix_world
for nm, cor in (('Kumo_Lingua', (0.62, 0.17, 0.20)), ('Kumo_Lingua_Ponta', (0.45, 0.10, 0.14))):
    mt = bpy.data.materials.get(nm) or bpy.data.materials.new(nm); mt.use_nodes = True; nt = mt.node_tree; nt.nodes.clear()
    em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (*cor, 1); out = nt.nodes.new('ShaderNodeOutputMaterial'); nt.links.new(em.outputs[0], out.inputs[0])
    ob.data.materials.append(mt)
for f in ob.data.polygons:
    if min(f.vertices) >= ini_b: f.material_index = 1
# ---------------- ossos
for o in bpy.context.selected_objects: o.select_set(False)
rig.select_set(True); bpy.context.view_layer.objects.active = rig; bpy.ops.object.mode_set(mode='EDIT'); EB = rig.data.edit_bones
RWi = rig.matrix_world.inverted()
def osso(nome, cab, cauda, pai, deforma=True):
    b = EB.new(nome); b.head = RWi @ Vector(cab); b.tail = RWi @ Vector(cauda); b.parent = EB[pai]; b.use_deform = deforma
    b.align_roll(RWi.to_3x3() @ Vector(CIMA)); return b
# direção do disparo: da base para o meio do lábio (com a boca fechada os lábios se tocam ali). Os ossos apontam
# para lá: deslizar no Y local = sair pela boca. A malha guardada fica um pouco abaixo (no chão da boca).
MIRA = LABIO + np.array([0, 0, 0.012]); AIM = (MIRA - BASE) / np.linalg.norm(MIRA - BASE)
osso('lingua_mira', BASE - AIM * 0.02, BASE + AIM * 0.05, 'jaw', False)
SEG = [BASE + EIXO * L0 * i / N for i in range(N + 1)]
for i, p in enumerate(SEG): osso(f'lingua_{i:02d}', p, p + AIM * 0.03, 'lingua_mira')
osso('lingua_ponta', PONTA, PONTA + AIM * 0.05, 'lingua_mira')
osso('lingua_controle', BASE - AIM * 0.05 + CIMA * 0.06, BASE + CIMA * 0.06, 'lingua_mira', False)
bpy.ops.object.mode_set(mode='OBJECT')
# pesos: cada anel entre os dois segmentos vizinhos; a bola toda na ponta
grupos = {f'lingua_{i:02d}': ob.vertex_groups.new(name=f'lingua_{i:02d}') for i in range(N + 1)}; gp = ob.vertex_groups.new(name='lingua_ponta')
for vi, u in enumerate(u_de):
    if u > 1.5: gp.add([vi], 1.0, 'REPLACE'); continue
    x = u * N; i0 = min(int(x), N - 1); t = x - i0
    grupos[f'lingua_{i0:02d}'].add([vi], 1 - t, 'REPLACE'); grupos[f'lingua_{i0 + 1:02d}'].add([vi], t, 'REPLACE')
ob.parent = rig; ob.matrix_parent_inverse = rig.matrix_world.inverted(); ob.matrix_world = body.matrix_world
md = ob.modifiers.new('Armature', 'ARMATURE'); md.object = rig
# drivers: E = posição Y do controle (no espaço local dele, que aponta como a língua)
pb = rig.pose.bones
def var_E(d):
    v = d.variables.new(); v.name = 'E'; v.type = 'TRANSFORMS'; t = v.targets[0]; t.id = rig; t.bone_target = 'lingua_controle'; t.transform_type = 'LOC_Y'; t.transform_space = 'LOCAL_SPACE'
for i in range(N + 1):
    b = pb[f'lingua_{i:02d}']; fc = b.driver_add('location', 1); d = fc.driver; d.type = 'SCRIPTED'; var_E(d); d.expression = f'E * {i / N:.3f}'
    if 0 < i < N:                                       # afina ao esticar (a língua real fica mais fina)
        for eixo in (0, 2):
            fs = b.driver_add('scale', eixo); ds = fs.driver; ds.type = 'SCRIPTED'; var_E(ds); ds.expression = 'max(0.6, 1.0 / (1.0 + 0.3 * max(E, 0.0)))'
fc = pb['lingua_ponta'].driver_add('location', 1); d = fc.driver; d.type = 'SCRIPTED'; var_E(d); d.expression = 'E'
# a mira volta metade do giro da mandíbula: a língua sai pelo meio da abertura (entre o lábio de cima, que fica, e o
# de baixo, que desce), e não pelo queixo
jx = np.array(rig.matrix_world.to_3x3() @ rig.data.bones['jaw'].matrix_local.to_3x3().col[0])
mx = np.array(rig.matrix_world.to_3x3() @ rig.data.bones['lingua_mira'].matrix_local.to_3x3().col[0])
sinal = 1.0 if float(jx @ mx) > 0 else -1.0
pb['lingua_mira'].rotation_mode = 'XYZ'; pb['jaw'].rotation_mode = 'XYZ'
fm = pb['lingua_mira'].driver_add('rotation_euler', 0); dm = fm.driver; dm.type = 'SCRIPTED'
vj = dm.variables.new(); vj.name = 'j'; vj.type = 'TRANSFORMS'; tj = vj.targets[0]; tj.id = rig; tj.bone_target = 'jaw'; tj.transform_type = 'ROT_X'; tj.transform_space = 'LOCAL_SPACE'; tj.rotation_mode = 'XYZ'
dm.expression = f'{-0.5 * sinal:.1f} * j'
print('MIRA eixos jaw·mira', round(float(jx @ mx), 3), flush=True)
# conferência com a malha final da língua
pior = folga(verts)
print('LINGUA dentro da pele: menor folga', round(pior * 1000, 1), 'mm (positivo = dentro)', flush=True)
bpy.ops.wm.save_as_mainfile(filepath=DST, copy=True, relative_remap=False)
import shutil; shutil.copy(SRC + '.labios.json', DST + '.labios.json')
print('LINGUA OK', len(verts), 'vértices')
