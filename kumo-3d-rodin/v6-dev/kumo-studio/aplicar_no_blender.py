"""Aplica no Blender uma pose ou animação copiada do Estúdio do Kumo (página kumo-studio/index.html).

Como usar no Blender (com o .blend do Kumo aberto, ex.: maos-corretivas/kumo_v6_maos_jogo.blend):
  1. Na página, clique em "Copiar pose" ou "Copiar animação".
  2. Cole o texto num arquivo .json (ou num bloco de texto do Blender chamado "kumo.json").
  3. Abra este script no Text Editor do Blender, ajuste ARQUIVO abaixo (ou deixe vazio para usar o bloco "kumo.json") e clique em Run Script.
Linha de comando: blender kumo.blend --python aplicar_no_blender.py -- pose.json

Os ossos da página têm os mesmos nomes e os mesmos eixos locais do rig do Blender (conferido no GLB),
então cada rotação é aplicada direto em pose_bone.rotation_quaternion. A animação vira a ação "Estudio_Kumo".
A correção da mão fechada liga sozinha pelos drivers do próprio .blend.
"""
import bpy, json, sys, os

ARQUIVO = ''      # caminho do .json; vazio = bloco de texto "kumo.json" ou argumento depois de "--"
FPS = 24

def ler():
    if '--' in sys.argv and len(sys.argv) > sys.argv.index('--') + 1:
        return json.load(open(sys.argv[sys.argv.index('--') + 1]))
    if ARQUIVO:
        return json.load(open(bpy.path.abspath(ARQUIVO)))
    t = bpy.data.texts.get('kumo.json')
    if t: return json.loads(t.as_string())
    raise SystemExit('Nenhum JSON: preencha ARQUIVO, crie o bloco de texto "kumo.json" ou passe o caminho depois de "--".')

def aplicar(rig, ossos, quadro=None):
    faltam = []
    for nome, q in ossos.items():
        pb = rig.pose.bones.get(nome)
        if not pb: faltam.append(nome); continue
        pb.rotation_mode = 'QUATERNION'; pb.rotation_quaternion = q
        if quadro is not None: pb.keyframe_insert('rotation_quaternion', frame=quadro)
    return faltam

dados = ler()
rig = next((o for o in bpy.data.objects if o.type == 'ARMATURE' and o.name.startswith('Kumo')), None)
if rig is None: raise SystemExit('Não achei a armadura do Kumo neste arquivo.')
sc = bpy.context.scene
if dados.get('formato') == 'kumo-pose-v1':
    faltam = aplicar(rig, dados['ossos'])
    print('Pose aplicada.', ('Ossos que não existem neste rig: ' + ', '.join(faltam)) if faltam else '')
elif dados.get('formato') == 'kumo-anim-v1':
    rig.animation_data_create()
    act = bpy.data.actions.new('Estudio_Kumo'); rig.animation_data.action = act
    sc.render.fps = FPS; faltam = []
    for q in dados['quadros']:
        f = 1 + round(q['t'] * FPS); faltam += aplicar(rig, q['ossos'], f)
    sc.frame_start = 1; sc.frame_end = 1 + round(dados.get('duracao', 2) * FPS)
    for fc in act.fcurves if hasattr(act, 'fcurves') else []:
        for k in fc.keyframe_points: k.interpolation = 'BEZIER'
    print(f'Animação aplicada: {len(dados["quadros"])} quadros-chave, ação "Estudio_Kumo", {sc.frame_end} quadros a {FPS} fps.',
          ('Ossos ausentes: ' + ', '.join(sorted(set(faltam)))) if faltam else '')
else:
    raise SystemExit('Formato desconhecido: use um JSON copiado do Estúdio do Kumo.')
