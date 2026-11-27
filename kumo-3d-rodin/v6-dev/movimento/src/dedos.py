"""Dedos arredondados: no modelo do Rodin os dedos são blocos de 4 faces. Aqui a malha da mão ganha uma subdivisão
e os vértices são suavizados (por região, só da mão), mantendo pesos, UV e o encaixe com o punho.
Os dedos mantêm o comprimento; só o corte vira redondo.

  blender --background kumo_v8_movimento.blend --python dedos.py -- <relatório.json>"""
import bpy, bmesh, sys, json, math
from mathutils import Vector
REL = sys.argv[sys.argv.index('--') + 1]
SUAVE_PASSOS = int(__import__('os').environ.get('DEDOS_PASSOS', 6)); SUAVE_FATOR = float(__import__('os').environ.get('DEDOS_FATOR', 0.5))
SMOOTH_SUB = float(__import__('os').environ.get('DEDOS_SMOOTH', 0.0))
o = bpy.data.objects['Kumo']; me = o.data
vg = {g.index: g.name for g in o.vertex_groups}
MAO = ('dedo', 'polegar', 'metacarpo', 'hand.')
REP = {}
bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
dl = bm.verts.layers.deform.verify()
def peso_mao(v):
    return sum(w for g, w in v[dl].items() if vg.get(g, '').startswith(MAO) or any(k in vg.get(g, '') for k in MAO[:3]) or vg.get(g, '').startswith('hand.'))
for lado in 'LR':
    sufixo = f'.{lado}'
    grupos = {g for g, n in vg.items() if n.endswith(sufixo) and (n.startswith(('dedo', 'polegar', 'metacarpo', 'hand')))}
    def pm(v): return sum(w for g, w in v[dl].items() if g in grupos)
    faces = [f for f in bm.faces if sum(pm(v) for v in f.verts) / len(f.verts) > 0.6]
    fs = set(faces); arestas = list({e for f in faces for e in f.edges})
    ncio = sum(1 for e in arestas if all(v in {x for f in faces for x in f.verts} for v in e.verts))
    verts_antes = len(bm.verts)
    res = bmesh.ops.subdivide_edges(bm, edges=arestas, cuts=1, use_grid_fill=True, smooth=SMOOTH_SUB, use_single_edge=False)
    bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
    # região de suavização: vértices com mais de 0,6 de peso da mão (os novos herdam os pesos dos vizinhos)
    reg = [v for v in bm.verts if pm(v) > 0.6]
    # o punho (borda da região) fica parado: vértices que ainda têm vizinho fora da região não se mexem
    regset = set(reg)
    fixos = {v for v in reg if any(e.other_vert(v) not in regset for e in v.link_edges)}
    mov = [v for v in reg if v not in fixos]
    co0 = {v.index: v.co.copy() for v in mov}
    for _ in range(SUAVE_PASSOS):    # Taubin: um passo que suaviza e outro que desfaz o encolhimento (o dedo não afina)
        bmesh.ops.smooth_vert(bm, verts=mov, factor=SUAVE_FATOR, use_axis_x=True, use_axis_y=True, use_axis_z=True)
        bmesh.ops.smooth_vert(bm, verts=mov, factor=-SUAVE_FATOR * 1.06, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    # as shape keys (mão fechada, ombros) guardam posições absolutas: levam o mesmo deslocamento da base
    for nome_k, camada in bm.verts.layers.shape.items():
        for v in mov: v[camada] = v[camada] + (v.co - co0[v.index])
    REP[lado] = dict(faces_antes=len(faces), vertices_novos=len(bm.verts) - verts_antes, vertices_suavizados=len(mov), vertices_fixos=len(fixos))
for f in bm.faces: f.smooth = True if any(sum(w for g, w in v[dl].items() if vg.get(g, '').split('.')[0] in ('dedo1_1','dedo1_2','dedo2_1','dedo2_2','dedo3_1','dedo3_2','polegar_1','polegar_2','metacarpo','hand')) > 0.6 for v in f.verts) else f.smooth
bm.to_mesh(me); bm.free(); me.update()
json.dump(REP, open(REL, 'w'), indent=1); print('DEDOS', REP)
bpy.ops.wm.save_mainfile()
