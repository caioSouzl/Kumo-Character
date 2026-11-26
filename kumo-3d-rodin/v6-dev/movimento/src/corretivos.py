"""Ossos corretivos de pescoço e costas.

  blender --background kumo_v8_movimento.blend --python corretivos.py -- <relatório.json>

O Kumo tem a cabeça grande apoiada direto nos ombros. Ao inclinar ou levantar a cabeça, a borda de baixo
dela entra nos ombros e nas costas; ao dobrar o tronco, a barriga e a lombar amassam.

Como funciona:
- MCH_cabeca_rel (filho do peito) copia o giro da cabeça no mundo: o giro dele no próprio espaço é o giro
  total de pescoço + cabeça em relação ao peito. MCH_peito_rel (filho do quadril) faz o mesmo com o peito,
  medindo coluna + peito em relação ao quadril.
- Cada osso corretivo (corr_*) é um osso que deforma, preso ao peito ou ao quadril, com peso numa região
  pequena da pele (queda suave). Uma restrição Transformation leva o giro do MCH a um deslocamento do osso:
  a pele sai do caminho da cabeça ou do tronco.
- O tamanho de cada deslocamento é escolhido medindo os cruzamentos da pele na pose em que ele age.
O glTF e o FBX levam o resultado nas animações (o exportador grava as restrições quadro a quadro); a Central
refaz a conta com os números de corretivos.json.
"""
import bpy, sys, json, math
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

REL = sys.argv[sys.argv.index('--') + 1]
rig = bpy.data.objects['Kumo_Rig']; pb = rig.pose.bones; corpo = bpy.data.objects['Kumo']
if rig.animation_data: rig.animation_data.action = None
REP = {}

# ---------------------------------------------------------------- ossos
# nome, pai, posição (m), região: raio (m), ossos donos dos pontos que entram, MCH, eixo do giro, sinal, direção do deslocamento (mundo)
CORR = [
    # ombros: saem de baixo da borda da cabeça quando ela inclina para o lado
    ('corr_trapezio.L', 'shoulder.L', (0.19, -0.1, 0.86), 0.15, {'shoulder.L', 'chest'}, 'MCH_cabeca_rel', 'Z', -1, (0.2, 0, -1)),
    ('corr_trapezio.R', 'shoulder.R', (-0.19, -0.1, 0.86), 0.15, {'shoulder.R', 'chest'}, 'MCH_cabeca_rel', 'Z', 1, (-0.2, 0, -1)),
    # borda de baixo da cabeça: sobe um pouco do lado para onde a cabeça inclina
    ('corr_borda.L', 'head', (0.19, -0.1, 0.92), 0.14, {'head', 'neck'}, 'MCH_cabeca_rel', 'Z', -1, (0, 0, 1)),
    ('corr_borda.R', 'head', (-0.19, -0.1, 0.92), 0.14, {'head', 'neck'}, 'MCH_cabeca_rel', 'Z', 1, (0, 0, 1)),
    # nuca: cabeça para cima encosta nas costas
    ('corr_nuca', 'chest', (0.0, 0.04, 0.85), 0.16, {'chest', 'spine', 'shoulder.L', 'shoulder.R'}, 'MCH_cabeca_rel', 'X', 1, (0, 0.5, -1)),
    ('corr_borda_tras', 'head', (0.0, 0.04, 0.92), 0.14, {'head', 'neck'}, 'MCH_cabeca_rel', 'X', 1, (0, 0.3, 1)),
    # garganta: cabeça para baixo encosta no peito
    ('corr_garganta', 'chest', (0.0, -0.17, 0.92), 0.14, {'chest', 'spine'}, 'MCH_cabeca_rel', 'X', -1, (0, 0.6, -1)),
    # lombar: tronco para trás amassa a lombar
    ('corr_lombar', 'hips', (0.0, 0.12, 0.64), 0.17, {'spine', 'hips', 'chest'}, 'MCH_peito_rel', 'X', 1, (0, -1, 0)),
]
bpy.context.view_layer.objects.active = rig; rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT'); E = rig.data.edit_bones
for n in [b.name for b in E if b.name.startswith(('corr_', 'MCH_cabeca_rel', 'MCH_peito_rel'))]: E.remove(E[n])
for nome, pai, fonte in (('MCH_cabeca_rel', 'chest', 'neck'), ('MCH_peito_rel', 'hips', 'spine')):
    b = E.new(nome); b.head = E[fonte].head; b.tail = E[fonte].head + Vector((0, 0, 0.1)); b.align_roll(E[pai].z_axis)
    b.parent = E[pai]; b.use_deform = False
for nome, pai, pos, *_ in CORR:
    b = E.new(nome); b.head = Vector(pos); b.tail = Vector(pos) + Vector((0, 0, 0.06)); b.align_roll(E[pai].z_axis)
    b.parent = E[pai]; b.use_deform = True
bpy.ops.object.mode_set(mode='OBJECT')
for nome, fonte in (('MCH_cabeca_rel', 'head'), ('MCH_peito_rel', 'chest')):
    p = pb[nome]; p.rotation_mode = 'XYZ'
    c = p.constraints.new('COPY_ROTATION'); c.target = rig; c.subtarget = fonte; c.target_space = c.owner_space = 'WORLD'
for b in pb: b.rotation_mode = 'QUATERNION' if not b.name.startswith('MCH_') else b.rotation_mode

# ---------------------------------------------------------------- pesos (queda suave em volta de cada osso)
def dominante(o):
    vg = {g.index: g.name for g in o.vertex_groups}; out = []
    for v in o.data.vertices:
        ws = [(g.weight, vg[g.group]) for g in v.groups if vg[g.group] in rig.data.bones and rig.data.bones[vg[g.group]].use_deform]
        out.append(max(ws)[1] if ws else '')
    return out

def pesar(o):
    dom = dominante(o); P = [o.matrix_world @ v.co for v in o.data.vertices]
    # o corretivo só recebe parte do peso do próprio pai: parado, ele deforma igual ao pai (nada muda)
    for nome, pai, pos, raio, donos, *_ in CORR:
        g = o.vertex_groups.get(nome) or o.vertex_groups.new(name=nome); gp = o.vertex_groups.get(pai)
        if gp is None: continue
        for i, v in enumerate(o.data.vertices):
            if dom[i] not in donos: continue
            d = (P[i] - Vector(pos)).length
            if d >= raio: continue
            gg = next((x for x in v.groups if x.group == gp.index), None)
            if gg is None or gg.weight <= 0: continue
            w = (1 - d / raio) ** 2 * gg.weight
            gg.weight -= w; g.add([i], w, 'REPLACE')
for o in (corpo, bpy.data.objects.get('Kumo_Contorno')):
    if o: pesar(o)

# ---------------------------------------------------------------- restrições: giro do MCH → deslocamento do osso
def restricao(nome, mch, eixo, sinal, direcao, quanto):
    p = pb[nome]
    for c in list(p.constraints): p.constraints.remove(c)
    c = p.constraints.new('TRANSFORM'); c.name = 'Corretivo'; c.target = rig; c.subtarget = mch
    c.target_space = c.owner_space = 'LOCAL'; c.map_from = 'ROTATION'; c.map_to = 'LOCATION'; c.mix_mode = 'ADD'
    for a in 'xyz': setattr(c, f'map_to_{a}_from', eixo)
    # 0 a 45° (no sentido que importa) → 0 a "quanto" metros na direção dada, no espaço do osso
    if sinal > 0: setattr(c, f'from_min_{eixo.lower()}_rot', 0.0); setattr(c, f'from_max_{eixo.lower()}_rot', math.radians(45))
    else: setattr(c, f'from_min_{eixo.lower()}_rot', math.radians(-45)); setattr(c, f'from_max_{eixo.lower()}_rot', 0.0)
    d = (rig.data.bones[nome].matrix_local.to_3x3().inverted() @ Vector(direcao)).normalized() * quanto
    for i, a in enumerate('xyz'):
        lo, hi = (0.0, d[i]) if sinal > 0 else (d[i], 0.0)
        setattr(c, f'to_min_{a}', lo); setattr(c, f'to_max_{a}', hi)
    c.use_motion_extrapolate = False

# ---------------------------------------------------------------- medida e escolha do tamanho
REGIAO = {'hips', 'spine', 'chest', 'neck', 'head', 'shoulder.L', 'shoulder.R', 'jaw'} | {c[0] for c in CORR}
dom = dominante(corpo); faces = [p.index for p in corpo.data.polygons if all(dom[i] in REGIAO for i in p.vertices)]
def zera():
    for b in pb:
        if b.name.startswith('MCH_'): continue
        b.rotation_mode = 'QUATERNION'; b.rotation_quaternion = (1, 0, 0, 0); b.location = (0, 0, 0)
    bpy.context.view_layer.update()
def girar(n, eixo, graus):
    p = pb[n]; bpy.context.view_layer.update()
    R = rig.matrix_world.to_3x3().inverted() @ Matrix.Rotation(math.radians(graus), 3, Vector(eixo)) @ rig.matrix_world.to_3x3()
    M = p.matrix.copy(); Mn = (R @ M.to_3x3()).to_4x4(); Mn.translation = M.translation; p.matrix = Mn
    bpy.context.view_layer.update()
def cruzamentos():
    dg = bpy.context.evaluated_depsgraph_get(); ev = corpo.evaluated_get(dg); m = ev.to_mesh()
    V = [ev.matrix_world @ v.co for v in m.vertices]; P = [tuple(m.polygons[i].vertices) for i in faces]; ev.to_mesh_clear()
    t = BVHTree.FromPolygons(V, P)
    return sum(1 for a, b in t.overlap(t) if a < b and not set(P[a]) & set(P[b]))
X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)
POSES = {
    'cabeca_cima_55': [('neck', X, -30), ('head', X, -25)], 'cabeca_baixo_55': [('neck', X, 30), ('head', X, 25)],
    'cabeca_lado_45_E': [('neck', Y, 25), ('head', Y, 20)], 'cabeca_lado_45_D': [('neck', Y, -25), ('head', Y, -20)],
    'cabeca_girar_70': [('neck', Z, 35), ('head', Z, 35)],
    'costas_frente_50': [('spine', X, 25), ('chest', X, 25)], 'costas_tras_40': [('spine', X, -20), ('chest', X, -20)],
    'costas_lado_40': [('spine', Y, 20), ('chest', Y, 20)], 'costas_torcer_40': [('spine', Z, 20), ('chest', Z, 20)],
}
def medir(nomes):
    r = {}
    for nm in nomes:
        zera()
        for n, e, g in POSES[nm]: girar(n, e, g)
        r[nm] = cruzamentos()
    zera(); return r

REP['antes'] = medir(POSES)

LADOS = ['cabeca_lado_45_E', 'cabeca_lado_45_D']
AGE = {'corr_trapezio.L': LADOS, 'corr_trapezio.R': LADOS, 'corr_borda.L': LADOS, 'corr_borda.R': LADOS,
       'corr_nuca': ['cabeca_cima_55'], 'corr_borda_tras': ['cabeca_cima_55'], 'corr_garganta': ['cabeca_baixo_55'],
       'corr_lombar': ['costas_tras_40']}
ESCOLHA = {}
for k, (nome, pai, pos, raio, donos, mch, eixo, sinal, direcao) in enumerate(CORR):
    melhor = None
    for sg in (1, -1):                                   # o sentido do giro que fecha o espaço é conferido medindo
        for quanto in (0.0, 0.03, 0.06, 0.09, 0.12):
            restricao(nome, mch, eixo, sg, direcao, quanto); s = sum(medir(AGE[nome]).values())
            if melhor is None or s < melhor[0] - 0.5: melhor = (s, quanto, sg)
    restricao(nome, mch, eixo, melhor[2], direcao, melhor[1]); CORR[k] = (nome, pai, pos, raio, donos, mch, eixo, melhor[2], direcao)
    ESCOLHA[nome] = {'deslocamento_m': melhor[1], 'sinal': melhor[2], 'cruzamentos': melhor[0]}
REP['escolha'] = ESCOLHA
REP['depois'] = medir(POSES)

# parâmetros para a Central e o jogo
PAR = {}
for nome, pai, pos, raio, donos, mch, eixo, sinal, direcao in CORR:
    c = pb[nome].constraints['Corretivo']
    PAR[nome] = dict(pai=pai, mch=mch, fonte={'MCH_cabeca_rel': 'head', 'MCH_peito_rel': 'chest'}[mch], eixo=eixo, sinal=sinal,
                     de_graus=[round(math.degrees(getattr(c, f'from_min_{eixo.lower()}_rot')), 3), round(math.degrees(getattr(c, f'from_max_{eixo.lower()}_rot')), 3)],
                     para_min=[c.to_min_x, c.to_min_y, c.to_min_z], para_max=[c.to_max_x, c.to_max_y, c.to_max_z])
REP['parametros'] = PAR
bpy.ops.wm.save_mainfile()
json.dump(REP, open(REL, 'w'), indent=1, ensure_ascii=False)
print('CORR', json.dumps(REP, ensure_ascii=False))
