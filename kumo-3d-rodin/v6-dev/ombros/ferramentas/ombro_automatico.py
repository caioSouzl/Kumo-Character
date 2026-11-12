"""Ombro automático do Kumo (rode dentro do Blender, com o Kumo_Rig na cena).

Você anima só o braço (upper_arm). Este script passa uma parte do giro para o ombro, como num corpo de verdade:
acima de 30° (medidos em relação ao peito), o ombro leva 45% de erguer o braço e 65% de levá-lo à frente. A direção final do braço não muda.
Grava as chaves do ombro na ação ativa, então a exportação (GLB/FBX) já sai pronta para o jogo.

  Blender > Scripting > abrir este arquivo > Run Script            (todos os quadros com chave no braço)
  ou: blender kumo.blend --python ombro_automatico.py
"""
import bpy, math
from mathutils import Vector, Matrix, Quaternion
K_ERGUER, K_FRENTE, LIMIAR = 0.45, 0.65, 30.0
def eixos(rig, sd):
    b = rig.data.bones[f'upper_arm.{sd}']; d = (b.tail_local - b.head_local).normalized()
    e = d.cross(Vector((0, 0, 1))).normalized(); f = d.cross(Vector((0, -1, 0))).normalized(); n = e.cross(f).normalized()
    Mx = Matrix((e, f, n)).inverted(); return e, f, Vector(Mx.col[0]), Vector(Mx.col[1])
def parte_ombro(a, k):
    return math.copysign(max(0.0, abs(a) - LIMIAR) * k, a)
def aplicar_quadro(rig, sd):
    """Mede o giro do braço em relação ao peito (assim inclinar o corpo não move o ombro) e reparte."""
    pb = rig.pose.bones; ob, ab = pb[f'shoulder.{sd}'], pb[f'upper_arm.{sd}']; pai = ob.parent
    braco = ab.matrix.copy()                                   # pose atual do braço (espaço da armadura)
    ob.matrix_basis = Matrix.Identity(4); bpy.context.view_layer.update()
    P = pai.matrix.to_3x3(); P0 = pai.bone.matrix_local.to_3x3()
    cur = P.inverted() @ braco.to_3x3(); rst = P0.inverted() @ ab.bone.matrix_local.to_3x3()
    q = (cur @ rst.inverted()).to_quaternion()                 # giro do braço no referencial do peito
    if q.w < 0: q = -q
    ang = 2 * math.atan2(Vector(q[1:]).length, q.w); v = Vector(q[1:]).normalized() * ang if ang > 1e-9 else Vector()
    e, f, de, df = eixos(rig, sd)
    para_peito = P0.inverted() @ rig.matrix_world.to_3x3().inverted()
    e, f, de, df = (para_peito @ x for x in (e, f, de, df))     # (os duais seguem válidos: a mudança é uma rotação)
    a_e, a_f = math.degrees(v.dot(de)), math.degrees(v.dot(df))
    S = Matrix.Rotation(math.radians(parte_ombro(a_e, K_ERGUER)), 3, e) @ Matrix.Rotation(math.radians(parte_ombro(a_f, K_FRENTE)), 3, f)
    Sa = (P @ S @ P.inverted()).to_4x4()                       # o mesmo giro, no espaço da armadura
    M = ob.matrix.copy(); h = M.to_translation()
    ob.matrix = Matrix.Translation(h) @ Sa @ Matrix.Translation(-h) @ M; bpy.context.view_layer.update()
    ab.matrix = braco; bpy.context.view_layer.update()         # o braço fica onde estava
def rodar(rig=None, quadros=None):
    rig = rig or bpy.data.objects['Kumo_Rig']; sc = bpy.context.scene; act = rig.animation_data.action if rig.animation_data else None
    if quadros is None:
        quadros = sorted({int(k.co[0]) for fc in (act.fcurves if act and hasattr(act, 'fcurves') else []) if 'upper_arm' in fc.data_path for k in fc.keyframe_points}) or [sc.frame_current]
    for fr in quadros:
        sc.frame_set(fr)
        for sd in 'LR':
            aplicar_quadro(rig, sd)
            if act:
                for n in (f'shoulder.{sd}', f'upper_arm.{sd}'):
                    b = rig.pose.bones[n]; b.keyframe_insert('rotation_quaternion' if b.rotation_mode == 'QUATERNION' else 'rotation_euler', frame=fr)
    return quadros
if __name__ == '__main__': print('ombro automático nos quadros', rodar())
