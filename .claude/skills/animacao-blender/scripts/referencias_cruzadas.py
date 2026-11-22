"""Imagens de referência cruzadas (frente e lado) para modelar um personagem.

Técnica do vídeo de @dreamstudio32 (TikTok): uma imagem de frente e uma de lado,
em planos perpendiculares, cada uma visível só na sua vista ortográfica
(Numpad 1 frente, Numpad 3 lado). Não é preciso a volta inteira do personagem:
a frente dá largura e altura, o lado dá profundidade e altura.

Uso dentro do Blender (ou `blender --background --python-expr`):

    import sys; sys.path.append('<pasta>/scripts')
    import referencias_cruzadas as rc
    frente, lado = rc.montar('/caminho/frente.png', '/caminho/lado.png', altura=2.0)
    rc.conferir(frente, lado)   # mede o desalinhamento das duas imagens

Convenções do Blender: frente do personagem olhando para -Y, cima +Z.
"""
import math
import bpy


def _imagem(caminho):
    img = bpy.data.images.load(caminho, check_existing=True)
    return img


def _empty(nome, img, altura, opacidade):
    ob = bpy.data.objects.new(nome, None)
    ob.empty_display_type = 'IMAGE'
    ob.data = img
    # o tamanho do empty vale para o MAIOR lado da imagem; ajustamos para a altura valer `altura`
    w, h = img.size
    ob.empty_display_size = altura * max(w, h) / h
    ob.empty_image_offset = (-0.5, 0.0)            # pés na origem, centrado na largura
    ob.empty_image_depth = 'BACK'                  # sempre atrás do modelo
    ob.show_empty_image_only_axis_aligned = True   # só aparece na vista que a encara
    ob.show_empty_image_perspective = False        # some na perspectiva: não atrapalha a 3/4
    ob.use_empty_image_alpha = True
    ob.color[3] = opacidade
    bpy.context.scene.collection.objects.link(ob)
    return ob


def montar(frente, lado, altura=2.0, recuo=1.0, opacidade=0.6):
    """Cria 'Ref_Frente' e 'Ref_Lado'.

    frente, lado: caminhos das imagens (mesma pose, mesma escala, pés na base).
    altura: altura da imagem inteira em metros (a do personagem, se a imagem
    for recortada justa nele). recuo: distância dos planos até a origem, para
    os planos ficarem atrás do modelo nas duas vistas.
    """
    f = _empty('Ref_Frente', _imagem(frente), altura, opacidade)
    f.rotation_euler = (math.radians(90), 0, 0)          # encara -Y (vista de frente)
    f.location = (0, recuo, 0)
    s = _empty('Ref_Lado', _imagem(lado), altura, opacidade)
    s.rotation_euler = (math.radians(90), 0, math.radians(90))   # encara +X (vista da direita, Numpad 3)
    s.location = (-recuo, 0, 0)
    return f, s


def _altura_util(img, limiar=0.05):
    """Primeira e última linha com pixel opaco (ou não branco), de baixo para cima, em 0..1."""
    w, h = img.size
    px = list(img.pixels)
    def cheia(y):
        base = y * w * 4
        for x in range(0, w, max(1, w // 200)):
            r, g, b, a = px[base + x * 4: base + x * 4 + 4]
            if a > 0.5 and min(r, g, b) < 1 - limiar:
                return True
        return False
    linhas = [y for y in range(0, h, max(1, h // 400)) if cheia(y)]
    if not linhas:
        return 0.0, 1.0
    return linhas[0] / h, linhas[-1] / h


def conferir(frente, lado):
    """Compara onde o personagem começa e termina em cada imagem.

    Devolve as diferenças (em metros) dos pés e do topo da cabeça. Mais de 1 a 2%
    da altura indica imagens em escalas diferentes: corrija antes de modelar,
    senão a frente e o lado brigam em toda medida.
    """
    res = {}
    for ob in (frente, lado):
        b, t = _altura_util(ob.data)
        h = ob.empty_display_size * ob.data.size[1] / max(ob.data.size)
        res[ob.name] = (b * h, t * h)
    (fb, ft), (sb, st) = res[frente.name], res[lado.name]
    return {'pes_m': round(sb - fb, 4), 'topo_m': round(st - ft, 4), 'medidas': res}
