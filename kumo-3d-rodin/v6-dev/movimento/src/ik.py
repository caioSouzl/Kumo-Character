"""IK das pernas (pés presos ao chão) e cabeça estável.

  blender --background kumo_v8_movimento.blend --python ik.py -- <relatório.json>

- pe_ik.L/.R: controle de cada pé (filho do root). A canela tem IK de 2 ossos (coxa + canela) mirando o
  controle, e o pé copia o giro dele. Mexer o quadril (hips) não tira os pés do lugar.
- joelho.L/.R: para onde o joelho aponta (alvo de polo), à frente do joelho.
- Propriedade ik_pernas no rig (0 a 1): liga e desliga o IK.
- MCH_cabeca_mundo (filho do root, mesma direção da cabeça em repouso) e a propriedade cabeca_estavel
  (0 a 1): com 1, a cabeça mantém o giro do mundo mesmo com o corpo balançando.
- O repouso não muda: o ângulo do polo é escolhido para a perna ficar igual ao repouso (conferido em mm).
"""
import bpy, sys, json, math
from mathutils import Vector, Matrix

REL = sys.argv[sys.argv.index('--') + 1]
rig = bpy.data.objects['Kumo_Rig']; pb = rig.pose.bones
if rig.animation_data: rig.animation_data.action = None
REP = {}
bpy.context.view_layer.objects.active = rig; rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT'); E = rig.data.edit_bones
for n in [b.name for b in E if b.name.startswith(('pe_ik.', 'joelho.', 'MCH_cabeca_mundo'))]: E.remove(E[n])
for s in 'LR':
    f = E[f'foot.{s}']; c = E.new(f'pe_ik.{s}'); c.head = f.head.copy(); c.tail = f.tail.copy(); c.roll = f.roll
    c.parent = E['root']; c.use_deform = False
    k = E[f'shin.{s}'].head; j = E.new(f'joelho.{s}'); j.head = k + Vector((0, -0.45, 0)); j.tail = j.head + Vector((0, 0, 0.08))
    j.parent = E['root']; j.use_deform = False
h = E['head']; m = E.new('MCH_cabeca_mundo'); m.head = h.head.copy(); m.tail = h.tail.copy(); m.roll = h.roll; m.parent = E['root']; m.use_deform = False
bpy.ops.object.mode_set(mode='OBJECT')

rig['ik_pernas'] = 1.0; rig['cabeca_estavel'] = 0.0
ui = rig.id_properties_ui('ik_pernas'); ui.update(min=0.0, max=1.0, description='Pés presos ao chão (IK das pernas)')
ui = rig.id_properties_ui('cabeca_estavel'); ui.update(min=0.0, max=1.0, description='Cabeça mantém o giro do mundo')

def driver_influencia(con, prop):
    fc = con.driver_add('influence'); d = fc.driver; d.type = 'AVERAGE'
    v = d.variables.new(); v.name = 'p'; v.targets[0].id = rig; v.targets[0].data_path = f'["{prop}"]'

def zera():
    for b in pb:
        if b.name.startswith('MCH_'): continue
        b.rotation_mode = 'QUATERNION'; b.rotation_quaternion = (1, 0, 0, 0); b.location = (0, 0, 0)
    bpy.context.view_layer.update()

zera()
for s in 'LR':
    for b in (f'shin.{s}', f'foot.{s}'):
        for c in list(pb[b].constraints): pb[b].constraints.remove(c)
    ref = pb[f'shin.{s}'].matrix.copy(), pb[f'thigh.{s}'].matrix.copy()
    ik = pb[f'shin.{s}'].constraints.new('IK'); ik.name = 'IK'; ik.target = rig; ik.subtarget = f'pe_ik.{s}'
    ik.pole_target = rig; ik.pole_subtarget = f'joelho.{s}'; ik.chain_count = 2; ik.use_tail = True; ik.use_stretch = False
    driver_influencia(ik, 'ik_pernas')
    # ângulo do polo que deixa a perna igual ao repouso
    melhor = None
    for a in range(-180, 181, 1):
        ik.pole_angle = math.radians(a); bpy.context.view_layer.update()
        e = (pb[f'shin.{s}'].matrix.translation - ref[0].translation).length + (pb[f'shin.{s}'].matrix.to_quaternion().rotation_difference(ref[0].to_quaternion()).angle) * 0.1 \
            + (pb[f'thigh.{s}'].matrix.to_quaternion().rotation_difference(ref[1].to_quaternion()).angle) * 0.1
        if melhor is None or e < melhor[0]: melhor = (e, a)
    fino = melhor
    for a10 in range(melhor[1] * 10 - 10, melhor[1] * 10 + 11):
        ik.pole_angle = math.radians(a10 / 10); bpy.context.view_layer.update()
        e = (pb[f'shin.{s}'].matrix.translation - ref[0].translation).length + (pb[f'shin.{s}'].matrix.to_quaternion().rotation_difference(ref[0].to_quaternion()).angle) * 0.1 \
            + (pb[f'thigh.{s}'].matrix.to_quaternion().rotation_difference(ref[1].to_quaternion()).angle) * 0.1
        if e < fino[0]: fino = (e, a10 / 10)
    ik.pole_angle = math.radians(fino[1]); REP[f'polo_{s}_graus'] = fino[1]
    cr = pb[f'foot.{s}'].constraints.new('COPY_ROTATION'); cr.name = 'Pe_IK'; cr.target = rig; cr.subtarget = f'pe_ik.{s}'
    cr.target_space = cr.owner_space = 'WORLD'; driver_influencia(cr, 'ik_pernas')
    pb[f'pe_ik.{s}'].rotation_mode = 'QUATERNION'

for c in list(pb['head'].constraints): pb['head'].constraints.remove(c)
cr = pb['head'].constraints.new('COPY_ROTATION'); cr.name = 'Cabeca_estavel'; cr.target = rig; cr.subtarget = 'MCH_cabeca_mundo'
cr.target_space = cr.owner_space = 'WORLD'; driver_influencia(cr, 'cabeca_estavel')
# com 1, quem gira a cabeça é o próprio MCH_cabeca_mundo (no espaço do mundo): o corpo balança e ela não

# ---------------------------------------------------------------- conferências
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get(); o = bpy.data.objects['Kumo']
def malha():
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get(); ev = o.evaluated_get(dg); m = ev.to_mesh()
    P = [ev.matrix_world @ v.co for v in m.vertices]; ev.to_mesh_clear(); return P
zera(); P1 = malha()
rig['ik_pernas'] = 0.0; P0 = malha(); rig['ik_pernas'] = 1.0
REP['repouso_ik_ligado_vs_desligado_mm'] = round(max((a - b).length for a, b in zip(P0, P1)) * 1000, 2)
# agachar: quadril desce 12 cm, pés ficam
zera(); pe0 = {s: (rig.matrix_world @ pb[f'foot.{s}'].matrix).translation.copy() for s in 'LR'}
pb['hips'].location = rig.data.bones['hips'].matrix_local.to_3x3().inverted() @ Vector((0, 0, -0.12)); bpy.context.view_layer.update()
REP['agachar_12cm_pe_moveu_mm'] = {s: round(((rig.matrix_world @ pb[f'foot.{s}'].matrix).translation - pe0[s]).length * 1000, 2) for s in 'LR'}
REP['agachar_12cm_joelho_graus'] = {s: round(math.degrees(pb[f'shin.{s}'].matrix.to_3x3().col[1].angle(pb[f'thigh.{s}'].matrix.to_3x3().col[1])), 1) for s in 'LR'}
# cabeça estável: tronco inclina 20°, cabeça mantém o giro
zera(); rig['cabeca_estavel'] = 1.0
pb['spine'].rotation_quaternion = Matrix.Rotation(math.radians(20), 3, 'X').to_quaternion(); bpy.context.view_layer.update()
h0 = rig.data.bones['head'].matrix_local.to_quaternion(); h1 = pb['head'].matrix.to_quaternion()
REP['cabeca_estavel_desvio_graus'] = round(math.degrees(h0.rotation_difference(h1).angle), 2)
rig['cabeca_estavel'] = 0.0; zera()
bpy.ops.wm.save_mainfile()
json.dump(REP, open(REL, 'w'), indent=1, ensure_ascii=False); print('IK', json.dumps(REP, ensure_ascii=False))
