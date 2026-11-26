"""Mede cruzamentos da pele (triângulos que atravessam outros) no tronco, pescoço e cabeça, em várias poses.

  blender --background kumo_v8_movimento.blend --python medir_tronco.py -- <saída.json>

Conta pares de triângulos que se cruzam e que não são vizinhos (não dividem nenhum ponto). Só entram faces
cuja maior influência é de um osso do tronco, do pescoço, da cabeça ou dos ombros.
"""
import bpy, sys, json, math
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

OUT = sys.argv[sys.argv.index('--') + 1]
rig = bpy.data.objects['Kumo_Rig']; pb = rig.pose.bones; o = bpy.data.objects['Kumo']
if rig.animation_data: rig.animation_data.action = None
REGIAO = {'hips', 'spine', 'chest', 'neck', 'head', 'shoulder.L', 'shoulder.R', 'jaw'} | {b.name for b in rig.data.bones if b.name.startswith('corr_')}
vg = {g.index: g.name for g in o.vertex_groups}
dom = []
for v in o.data.vertices:
    ws = [(g.weight, vg[g.group]) for g in v.groups if vg[g.group] in rig.data.bones and rig.data.bones[vg[g.group]].use_deform]
    dom.append(max(ws)[1] if ws else '')
faces = [p.index for p in o.data.polygons if all(dom[i] in REGIAO for i in p.vertices)]

def zera():
    for b in pb: b.rotation_mode = 'QUATERNION'; b.rotation_quaternion = (1, 0, 0, 0); b.location = (0, 0, 0)
    bpy.context.view_layer.update()

def girar(n, eixo, graus):
    p = pb[n]; bpy.context.view_layer.update()
    R = rig.matrix_world.to_3x3().inverted() @ Matrix.Rotation(math.radians(graus), 3, Vector(eixo)) @ rig.matrix_world.to_3x3()
    M = p.matrix.copy(); Mn = (R @ M.to_3x3()).to_4x4(); Mn.translation = M.translation; p.matrix = Mn
    bpy.context.view_layer.update()

def cruzamentos():
    dg = bpy.context.evaluated_depsgraph_get(); ev = o.evaluated_get(dg); m = ev.to_mesh()
    V = [ev.matrix_world @ v.co for v in m.vertices]; P = [tuple(m.polygons[i].vertices) for i in faces]
    ev.to_mesh_clear()
    t = BVHTree.FromPolygons(V, P); n = 0; vist = set()
    for a, b in t.overlap(t):
        if a >= b or set(P[a]) & set(P[b]): continue
        n += 1; vist.update(P[a]); vist.update(P[b])
    return n, len(vist)

X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)
POSES = {
    'repouso': [],
    'cabeca_cima_55': [('neck', X, -30), ('head', X, -25)], 'cabeca_baixo_55': [('neck', X, 30), ('head', X, 25)],
    'cabeca_lado_45_E': [('neck', Y, 25), ('head', Y, 20)], 'cabeca_lado_45_D': [('neck', Y, -25), ('head', Y, -20)],
    'cabeca_girar_70': [('neck', Z, 35), ('head', Z, 35)],
    'costas_frente_50': [('spine', X, 25), ('chest', X, 25)], 'costas_tras_40': [('spine', X, -20), ('chest', X, -20)],
    'costas_lado_40': [('spine', Y, 20), ('chest', Y, 20)], 'costas_torcer_40': [('spine', Z, 20), ('chest', Z, 20)],
}
R = {'faces_medidas': len(faces)}
for nm, it in POSES.items():
    zera()
    for n, e, g in it: girar(n, e, g)
    c, v = cruzamentos(); R[nm] = {'pares': c, 'pontos': v}
zera()
json.dump(R, open(OUT, 'w'), indent=1); print('MED', json.dumps(R))
