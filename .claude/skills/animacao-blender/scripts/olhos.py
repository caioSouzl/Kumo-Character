"""Duas técnicas de olho estilizado.

1. Olho 2D por decal (@pol.gc, TikTok "Anima tus ojos 2D con decals y rigging"):
   a pupila é uma imagem projetada na pele por um Empty. Mover o Empty move a
   pupila; o Empty fica preso a um osso do olho, que mira um alvo (Damped Track).
   Serve para olho pintado na própria cabeça, sem globo ocular.

       import olhos
       e = olhos.decal(cabeca, 'Ojo.L', '/caminho/pupila.png', centro=(x, y, z), tamanho=0.09)
       olhos.atribuir_faces(cabeca, 'Ojo.L', indices_das_faces_do_olho)
       olhos.rig_olhar(rig, [('OJO.L', e, centro_l), ('OJO.R', e2, centro_r)], foco=(0, -1, z))

2. Íris para dentro (@mokunachoi, TikTok "3D eye tutorial"): a parte da íris do
   globo tem as normais invertidas e o material corta as faces de trás
   (Backface Culling). A câmera passa a ver o fundo do globo por dentro e a íris
   parece afundar, com paralaxe ao girar.

       olhos.iris_para_dentro(globo, 'Iris')   # grupo de vértices com a frente da íris

Convenção: frente do personagem para -Y, cima +Z (padrão do Blender).
"""
import math
import bmesh
import bpy


# ---------------------------------------------------------------- 1. decal
def material_decal(nome, imagem, alvo, esclera=(1, 1, 1, 1)):
    """Material: Texture Coordinate (Object = alvo) → Mapping → Image → Mix → Principled.

    Mapping em Point com Location 0,5 (o centro do Empty vira o centro da
    imagem) e Rotation X -90° (a imagem fica de pé na frente, plano XZ).
    A imagem fica em Extension = Clip: fora dela, só a esclera. O Mix usa o
    alfa da imagem como fator: A = cor da esclera, B = cor da pupila.
    """
    mat = bpy.data.materials.new(nome)
    mat.use_nodes = True
    nt = mat.node_tree
    n = nt.nodes
    bsdf = n.get('Principled BSDF')
    tc = n.new('ShaderNodeTexCoord'); tc.object = alvo; tc.location = (-900, 0)
    mp = n.new('ShaderNodeMapping'); mp.vector_type = 'POINT'; mp.location = (-700, 0)
    mp.inputs['Location'].default_value = (0.5, 0.5, 0.5)
    mp.inputs['Rotation'].default_value = (math.radians(-90), 0, 0)
    im = n.new('ShaderNodeTexImage'); im.location = (-480, 0)
    im.image = bpy.data.images.load(imagem, check_existing=True) if isinstance(imagem, str) else imagem
    im.extension = 'CLIP'
    mx = n.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.location = (-200, 0)
    mx.inputs['A'].default_value = esclera
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
    nt.links.new(mp.outputs['Vector'], im.inputs['Vector'])
    nt.links.new(im.outputs['Alpha'], mx.inputs['Factor'])
    nt.links.new(im.outputs['Color'], mx.inputs['B'])
    nt.links.new(mx.outputs['Result'], bsdf.inputs['Base Color'])
    return mat


def decal(obj, nome, imagem, centro, tamanho=0.1, esclera=(1, 1, 1, 1)):
    """Cria o Empty 'Decal_<nome>' no centro do olho e o material <nome> em obj.

    tamanho: largura da imagem da pupila na superfície, em metros (é a escala
    do Empty). O material entra num slot novo; use atribuir_faces para dizer
    quais faces são o olho.
    """
    e = bpy.data.objects.new('Decal_' + nome, None)
    e.empty_display_type = 'PLAIN_AXES'
    e.empty_display_size = 0.5
    e.show_in_front = True
    e.location = centro
    e.scale = (tamanho, tamanho, tamanho)
    bpy.context.scene.collection.objects.link(e)
    obj.data.materials.append(material_decal(nome, imagem, e, esclera))
    return e


def atribuir_faces(obj, nome_material, faces):
    """Põe as faces (índices) no slot do material."""
    idx = [m.name for m in obj.data.materials].index(nome_material)
    for f in faces:
        obj.data.polygons[f].material_index = idx


def faces_no_raio(obj, centro, raio):
    """Índices das faces cujo centro (no mundo) está a até `raio` de `centro`."""
    from mathutils import Vector
    c, mw = Vector(centro), obj.matrix_world
    return [p.index for p in obj.data.polygons if (mw @ p.center - c).length <= raio]


def rig_olhar(rig, olhos, foco, nome_foco='FOCO', profundidade=0.3, comprimento=0.1):
    """Ossos dos olhos mirando um alvo comum, com os Empties presos a eles.

    olhos: lista de (nome_do_osso, empty_do_decal, centro_do_olho na superfície).
    foco: posição do alvo, à frente do rosto. Mover o FOCO move as duas pupilas;
    cada Empty continua livre para um ajuste fino no próprio olho.
    profundidade: a base do osso fica esse tanto PARA DENTRO da cabeça, e a
    ponta no olho. O osso gira na base, então o Empty, na ponta, desliza pela
    superfície. Com a base no próprio olho, o Empty só giraria no lugar e a
    pupila quase não andaria. Use mais ou menos o raio da curva do rosto ali.
    """
    from mathutils import Vector
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    eb = rig.data.edit_bones
    alvo = eb.new(nome_foco); alvo.head = foco; alvo.tail = Vector(foco) + Vector((0, 0, comprimento))
    for nome, _, centro in olhos:
        b = eb.new(nome); b.tail = centro; b.head = Vector(centro) + Vector((0, profundidade, 0))
    bpy.ops.object.mode_set(mode='POSE')
    for nome, _, _ in olhos:
        c = rig.pose.bones[nome].constraints.new('DAMPED_TRACK')
        c.target = rig; c.subtarget = nome_foco; c.track_axis = 'TRACK_Y'
    bpy.ops.object.mode_set(mode='OBJECT')
    for nome, e, _ in olhos:            # Ctrl+P → Bone, mantendo a posição atual do Empty
        mw = e.matrix_world.copy()
        e.parent = rig; e.parent_type = 'BONE'; e.parent_bone = nome
        bpy.context.view_layer.update()
        e.matrix_world = mw
    return rig.pose.bones[nome_foco]


# ---------------------------------------------------------------- 2. íris para dentro
def iris_para_dentro(globo, grupo):
    """Inverte as normais das faces do grupo de vértices e liga o Backface Culling.

    No Blender: Edit Mode, selecionar a íris, Alt+N → Flip; conferir com o
    overlay Face Orientation (a íris fica vermelha); no material, Settings →
    Backface Culling → Camera. Devolve quantas faces foram invertidas.
    Observação: Backface Culling vale no EEVEE e no viewport; no Cycles não há
    essa opção. No Godot, o material padrão já descarta as faces de trás.
    """
    gi = globo.vertex_groups[grupo].index
    no_grupo = {v.index for v in globo.data.vertices if any(g.group == gi and g.weight > 0.5 for g in v.groups)}
    bm = bmesh.new(); bm.from_mesh(globo.data)
    alvo = [f for f in bm.faces if all(v.index in no_grupo for v in f.verts)]
    bmesh.ops.reverse_faces(bm, faces=alvo)
    bm.to_mesh(globo.data); bm.free(); globo.data.update()
    for m in globo.data.materials:
        if m:
            m.use_backface_culling = True
    return len(alvo)
