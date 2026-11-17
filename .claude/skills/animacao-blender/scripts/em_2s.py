"""Ferramentas do processo de animação estilizada (blocking em degraus, "em 2s", trechos "em 1s", câmera).

Uso dentro do Blender (ou do Python com bpy):
    import em_2s
    em_2s.degraus(acao)                                  # blocking: toda chave segura até a próxima (CONSTANT)
    em_2s.em_2s(acao, 1, 28, em_1s=[(7, 11)])            # pose nova a cada 2 quadros; nos trechos em_1s, a cada quadro
    em_2s.segurar_na_camera(cena, rig, 'hips', cam, 1, 28, em_1s=[(7, 11)])   # corrige o tremor quando a câmera se move
    em_2s.trajetoria(rig, 'hips', 1, 28)                 # liga o motion path do osso para conferir os arcos
"""
import bpy
from mathutils import Vector

def curvas(acao):
    """fcurves de uma ação (Blender 4.4+ guarda em camadas/slots; antes, direto em acao.fcurves)"""
    if hasattr(acao, 'fcurves') and len(getattr(acao, 'layers', [])) == 0: return list(acao.fcurves)
    return [fc for l in acao.layers for st in l.strips for cb in st.channelbags for fc in cb.fcurves]

def degraus(acao):
    for fc in curvas(acao):
        for k in fc.keyframe_points: k.interpolation = 'CONSTANT'
        fc.update()

def _segurado(f, ini, em_1s):
    """quadro cuja pose vale no quadro f: o próprio f nos trechos em 1s; senão o quadro par anterior (a partir de ini)"""
    if any(a <= f <= b for a, b in em_1s): return f
    return ini + 2 * ((f - ini) // 2)

def em_2s(acao, ini, fim, em_1s=()):
    """Refaz as chaves: uma pose a cada 2 quadros (tirada da curva atual), em degraus. em_1s = [(a, b), ...] são os
    trechos que ficam com pose em todo quadro (movimentos rápidos que se quer destacar)."""
    quadros = [f for f in range(ini, fim + 1) if _segurado(f, ini, em_1s) == f]
    for fc in curvas(acao):
        vals = [fc.evaluate(f) for f in quadros]
        fc.keyframe_points.clear(); fc.keyframe_points.add(len(quadros))
        for k, f, v in zip(fc.keyframe_points, quadros, vals):
            k.co = (f, v); k.interpolation = 'CONSTANT'; k.handle_left_type = k.handle_right_type = 'AUTO'
        fc.update()
    return quadros

def segurar_na_camera(cena, rig, osso, cam, ini, fim, em_1s=()):
    """"Camera hold": animando em 2s com a câmera em movimento, a pose fica parada mas escorrega na tela no quadro
    repetido, e a animação treme. Aqui, em cada quadro repetido, o rig é deslocado para o osso (quadril) ficar no
    MESMO ponto da tela em que estava no quadro da pose. Chaves na posição do objeto do rig, em degraus."""
    def no_cam(): return cam.matrix_world.inverted() @ (rig.matrix_world @ rig.pose.bones[osso].head)
    base = {}
    for f in range(ini, fim + 1): cena.frame_set(f); base[f] = rig.location.copy()
    feitos = 0
    for f in range(ini, fim + 1):
        h = _segurado(f, ini, em_1s); cena.frame_set(h); rig.location = base[h]; bpy.context.view_layer.update(); pk = no_cam()
        cena.frame_set(f); rig.location = base[f]; bpy.context.view_layer.update()
        if h != f:
            pn = no_cam()
            alvo = Vector((pk.x, pk.y, pn.z)) if cam.data.type == 'ORTHO' else Vector((pk.x * pn.z / pk.z, pk.y * pn.z / pk.z, pn.z))
            rig.location = base[f] + (cam.matrix_world @ alvo - cam.matrix_world @ pn); feitos += 1
        rig.keyframe_insert('location', frame=f)
    acao = rig.animation_data.action
    for fc in curvas(acao):
        if fc.data_path == 'location':
            for k in fc.keyframe_points: k.interpolation = 'CONSTANT'
    return feitos

def trajetoria(rig, osso, ini, fim):
    """Motion path do osso (em geral o quadril, centro de gravidade), para conferir se o movimento faz arcos limpos."""
    bpy.context.view_layer.objects.active = rig; bpy.ops.object.mode_set(mode='POSE')
    for pb in rig.pose.bones:                           # Blender 5: a seleção fica no osso de pose; antes, no osso
        alvo = pb if hasattr(pb, 'select') else pb.bone
        alvo.select = (pb.name == osso)
    rig.data.bones.active = rig.data.bones[osso]
    mp = rig.pose.animation_visualization.motion_path; mp.frame_start, mp.frame_end = ini, fim; mp.range = 'MANUAL'
    bpy.ops.pose.paths_calculate(); bpy.ops.object.mode_set(mode='OBJECT')
