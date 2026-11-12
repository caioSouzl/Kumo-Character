"""Confere que a ferramenta dá o mesmo resultado do ombro automático usado nas medições."""
import bpy, sys, os, math
import numpy as np
sys.argv = sys.argv[:]; BL = sys.argv[-1]
bpy.ops.wm.open_mainfile(filepath=BL); rig = bpy.data.objects['Kumo_Rig']; body = bpy.data.objects['Kumo']; pb = rig.pose.bones
if rig.animation_data: rig.animation_data.action = None
for m in body.modifiers:
    if m.type != 'ARMATURE': m.show_viewport = False
sys.path.insert(0, '/home/user/Kumo-Character/kumo-3d-rodin/v6-dev/ombros/ferramentas'); import ombro_automatico as oa
from mathutils import Vector, Matrix
def pos():
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get(); ev = body.evaluated_get(dg); m = ev.to_mesh(); P = np.array([tuple(ev.matrix_world @ v.co) for v in m.vertices]); ev.to_mesh_clear(); return P
def reset():
    for b in pb: b.rotation_quaternion = (1, 0, 0, 0); b.rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()
def rotw(n, axis, deg):
    b = pb[n]; bpy.context.view_layer.update(); M = b.matrix.copy(); h = M.to_translation()
    b.matrix = Matrix.Translation(h) @ Matrix.Rotation(math.radians(deg), 4, axis.normalized()) @ Matrix.Translation(-h) @ M; bpy.context.view_layer.update()
for sd, tipo, a in (('L', 'erguer', 120), ('R', 'frente', 90), ('L', 'erguer', 60)):
    e, f, _, _ = oa.eixos(rig, sd); ax = e if tipo == 'erguer' else f; k = oa.K_ERGUER if tipo == 'erguer' else oa.K_FRENTE
    reset(); s = max(0, a - 30) * k; rotw(f'shoulder.{sd}', ax, s); rotw(f'upper_arm.{sd}', ax, a - s); ref = pos()
    reset(); rotw(f'upper_arm.{sd}', ax, a); oa.aplicar_quadro(rig, sd); got = pos()
    print('TA', sd, tipo, a, 'dif_max_mm', round(float(np.abs(got - ref).max()) * 1000, 4))
    # com o peito inclinado, o resultado tem de ser o mesmo giro levado junto com o peito
    reset(); rotw('chest', Vector((0, 1, 0)), 25); s = max(0, a - 30) * k
    C = pb['chest'].matrix.to_3x3() @ rig.data.bones['chest'].matrix_local.to_3x3().inverted(); axc = C @ ax
    rotw(f'shoulder.{sd}', axc, s); rotw(f'upper_arm.{sd}', axc, a - s); ref = pos()
    reset(); rotw('chest', Vector((0, 1, 0)), 25); rotw(f'upper_arm.{sd}', axc, a); oa.aplicar_quadro(rig, sd); got = pos()
    print('TA', sd, tipo, a, 'peito inclinado dif_max_mm', round(float(np.abs(got - ref).max()) * 1000, 4))
