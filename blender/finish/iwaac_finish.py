"""Finalização 2.5D "pintada" para Blender 5.2+ (EEVEE).

Estilo estudado do perfil @alexandr.iwaac (TikTok): render em tempo real
(EEVEE) com cara de pintura digital. Três camadas:

1. Material  -> normal "pincelada" (Voronoi sobre a normal), sombra roxa em
                degraus, borda quente e variação de cor por pincelada.
2. Geometria -> contorno por casca invertida com espessura irregular (GN).
3. Compositor-> tremor de borda, bloom, sharpen + Kuwahara + sharpen, papel,
                pontilhado, grão, aberração cromática, vinheta.

Uso (sem interface):
    blender cena.blend -b --python iwaac_finish.py -- --render saida.png
    blender cena.blend -b --python iwaac_finish.py -- --save cena_final.blend

Uso dentro do Blender (Text Editor / MCP):
    import iwaac_finish as f; f.apply(bpy.context.scene)

Cada etapa pode ser ligada/desligada em apply(); os valores padrão são os
lidos nos node trees do artista (ver docs/ESTILO-FINALIZACAO.md).
"""

from __future__ import annotations

import math
import sys

import bpy
import numpy as np

TAG = "IWAAC"

# ---------------------------------------------------------------- utilidades


def _sock(node, name, value):
    """Define default_value de um input pelo nome, se existir."""
    s = node.inputs.get(name)
    if s is not None and hasattr(s, "default_value"):
        s.default_value = value
    return s


def _procedural_image(name, size, fn):
    """Cria (ou reaproveita) uma imagem empacotada gerada por numpy."""
    img = bpy.data.images.get(name)
    if img is not None and tuple(img.size) == (size, size):
        return img
    if img is not None:
        bpy.data.images.remove(img)
    rgba = fn(size).astype(np.float32)
    img = bpy.data.images.new(name, size, size, alpha=False, float_buffer=False)
    img.pixels.foreach_set(rgba.ravel())
    img.pack()
    img.colorspace_settings.name = "sRGB"
    return img


def _blur(a, r):
    """Box blur separável com wrap (mantém a textura tileável)."""
    for axis in (0, 1):
        acc = np.zeros_like(a)
        for k in range(-r, r + 1):
            acc += np.roll(a, k, axis=axis)
        a = acc / (2 * r + 1)
    return a


def _paper(size):
    rng = np.random.default_rng(7)
    base = np.zeros((size, size), np.float32)
    for r, w in ((24, 0.45), (8, 0.3), (2, 0.15), (0, 0.10)):
        n = rng.random((size, size)).astype(np.float32)
        base += w * (_blur(n, r) if r else n)
    # fibras diagonais leves
    yy, xx = np.mgrid[0:size, 0:size]
    base += 0.04 * np.sin((xx + yy) * 0.9 + rng.random() * 6)
    base = (base - base.min()) / (np.ptp(base) + 1e-6)
    v = 0.35 + 0.65 * base
    return np.dstack([v, v, v, np.ones_like(v)])


def _dots(size):
    """Pontilhado de meio-tom fino (usado em Screen com fator baixo)."""
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    period = 6.0
    d = np.hypot((xx % period) - period / 2, (yy % period) - period / 2)
    v = np.clip(1.6 - d, 0, 1)
    return np.dstack([v, v, v, np.ones_like(v)])


# ------------------------------------------------------------- 1. material


def painterly_material(mat, *, voronoi_scale=6.0, warp=0.15, strength=1.0):
    """Insere a 'normal pincelada' antes do Normal do Principled BSDF.

    Normal -> mistura Linear Light com ruído -> Voronoi(F1).Position ->
    Normalize -> Principled.Normal. A sombra quebra em manchas de pincel.
    """
    if not mat or not mat.use_nodes:
        return False
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None or nt.nodes.get(f"{TAG}_voronoi"):
        return False
    x, y = bsdf.location.x - 900, bsdf.location.y - 500

    geo = nt.nodes.new("ShaderNodeNewGeometry")
    geo.location = (x, y)
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.location = (x, y - 250)
    _sock(noise, "Scale", 2.0)
    _sock(noise, "Detail", 2.0)
    _sock(noise, "Roughness", 0.5)
    noise.inputs["Vector"].default_value = (0, 0, 0)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    tc.location = (x - 200, y - 250)
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])

    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "LINEAR_LIGHT"
    mix.location = (x + 220, y)
    mix.inputs["Factor"].default_value = warp
    nt.links.new(geo.outputs["Normal"], mix.inputs["A"])
    nt.links.new(noise.outputs["Color"], mix.inputs["B"])

    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.name = f"{TAG}_voronoi"
    vor.location = (x + 440, y)
    vor.feature = "F1"
    _sock(vor, "Scale", voronoi_scale)
    _sock(vor, "Randomness", 1.0)
    nt.links.new(mix.outputs["Result"], vor.inputs["Vector"])

    norm = nt.nodes.new("ShaderNodeVectorMath")
    norm.operation = "NORMALIZE"
    norm.location = (x + 660, y)
    nt.links.new(vor.outputs["Position"], norm.inputs[0])

    # mistura com a normal original (strength=1 -> só pincelada)
    blend = nt.nodes.new("ShaderNodeMix")
    blend.data_type = "VECTOR"
    blend.location = (x + 860, y)
    blend.inputs["Factor"].default_value = strength
    nt.links.new(geo.outputs["Normal"], blend.inputs["A"])
    nt.links.new(norm.outputs["Vector"], blend.inputs["B"])
    nt.links.new(blend.outputs["Result"], bsdf.inputs["Normal"])

    # superfície mais "tinta": pouco brilho especular
    _sock(bsdf, "Roughness", max(0.55, bsdf.inputs["Roughness"].default_value))
    return True


def _base_color_source(nt, bsdf):
    """Socket que alimenta a cor base (ou um nó RGB com o valor fixo)."""
    s = bsdf.inputs["Base Color"]
    if s.is_linked:
        return s.links[0].from_socket
    rgb = nt.nodes.new("ShaderNodeRGB")
    rgb.outputs[0].default_value = tuple(s.default_value)
    rgb.location = (bsdf.location.x - 500, bsdf.location.y + 200)
    return rgb.outputs[0]


def paint_shading(mat, *, dabs=0.12, shadow_tint=(0.36, 0.22, 0.72), shadow_mix=0.85,
                  steps=(0.22, 0.55), rim=1.6, rim_color=(1.0, 0.62, 0.35)):
    """Sombra tingida em degraus + variação de cor por pincelada + borda quente.

    Precisa rodar depois de painterly_material (usa o mesmo Voronoi).
    Principled -> Shader to RGB -> luminância -> ColorRamp (degrau suave):
      claro  = cor iluminada
      sombra = mistura da cor iluminada com base * tinta roxa
    + Layer Weight (Facing) -> borda quente somada -> Emission.
    """
    if not mat or not mat.use_nodes:
        return False
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    vor = nt.nodes.get(f"{TAG}_voronoi")
    out = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output), None)
    if bsdf is None or out is None or nt.nodes.get(f"{TAG}_paint"):
        return False
    L = nt.links
    x, y = bsdf.location.x + 350, bsdf.location.y
    base = _base_color_source(nt, bsdf)

    # 1) variação de valor por "pincelada" (mesmas células da normal)
    if vor is not None and dabs > 0:
        bw = nt.nodes.new("ShaderNodeRGBToBW")
        bw.location = (x - 900, y + 350)
        L.new(vor.outputs["Color"], bw.inputs[0])
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.location = (x - 700, y + 350)
        mr.inputs["To Min"].default_value = 1 - dabs
        mr.inputs["To Max"].default_value = 1 + dabs
        L.new(bw.outputs[0], mr.inputs["Value"])
        mul = nt.nodes.new("ShaderNodeMix")
        mul.data_type = "RGBA"
        mul.blend_type = "MULTIPLY"
        mul.inputs["Factor"].default_value = 1.0
        mul.location = (x - 500, y + 350)
        L.new(base, mul.inputs["A"])
        L.new(mr.outputs["Result"], mul.inputs["B"])
        base = mul.outputs["Result"]
        L.new(base, bsdf.inputs["Base Color"])

    # 2) luz -> degrau
    s2r = nt.nodes.new("ShaderNodeShaderToRGB")
    s2r.name = f"{TAG}_paint"
    s2r.location = (x, y)
    L.new(bsdf.outputs[0], s2r.inputs[0])
    lum = nt.nodes.new("ShaderNodeRGBToBW")
    lum.location = (x + 200, y - 150)
    L.new(s2r.outputs["Color"], lum.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.location = (x + 380, y - 150)
    e = ramp.color_ramp.elements
    e[0].position, e[0].color = steps[0], (0, 0, 0, 1)
    e[1].position, e[1].color = steps[1], (1, 1, 1, 1)
    L.new(lum.outputs[0], ramp.inputs["Factor"])

    tint = nt.nodes.new("ShaderNodeMix")
    tint.data_type = "RGBA"
    tint.blend_type = "MULTIPLY"
    tint.inputs["Factor"].default_value = 1.0
    tint.inputs["B"].default_value = (*shadow_tint, 1)
    tint.location = (x + 200, y + 200)
    L.new(base, tint.inputs["A"])
    shadow = nt.nodes.new("ShaderNodeMix")
    shadow.data_type = "RGBA"
    shadow.inputs["Factor"].default_value = shadow_mix
    shadow.location = (x + 400, y + 200)
    L.new(s2r.outputs["Color"], shadow.inputs["A"])
    L.new(tint.outputs["Result"], shadow.inputs["B"])

    toon = nt.nodes.new("ShaderNodeMix")
    toon.data_type = "RGBA"
    toon.location = (x + 650, y)
    L.new(ramp.outputs["Color"], toon.inputs["Factor"])
    L.new(shadow.outputs["Result"], toon.inputs["A"])
    L.new(s2r.outputs["Color"], toon.inputs["B"])
    col = toon.outputs["Result"]

    # 3) borda quente (rim) usando a normal pincelada
    if rim > 0:
        lw = nt.nodes.new("ShaderNodeLayerWeight")
        lw.location = (x + 400, y - 400)
        lw.inputs["Blend"].default_value = 0.35
        if bsdf.inputs["Normal"].is_linked:
            L.new(bsdf.inputs["Normal"].links[0].from_socket, lw.inputs["Normal"])
        rr = nt.nodes.new("ShaderNodeMapRange")
        rr.location = (x + 600, y - 400)
        rr.inputs["From Min"].default_value = 0.35
        rr.inputs["From Max"].default_value = 0.85
        rr.inputs["To Max"].default_value = rim
        L.new(lw.outputs["Facing"], rr.inputs["Value"])
        rc = nt.nodes.new("ShaderNodeMix")
        rc.data_type = "RGBA"
        rc.blend_type = "MULTIPLY"
        rc.inputs["Factor"].default_value = 1.0
        rc.inputs["B"].default_value = (*rim_color, 1)
        rc.location = (x + 600, y - 250)
        L.new(base, rc.inputs["A"])
        add = nt.nodes.new("ShaderNodeMix")
        add.data_type = "RGBA"
        add.blend_type = "ADD"
        add.location = (x + 850, y)
        L.new(rr.outputs["Result"], add.inputs["Factor"])
        L.new(col, add.inputs["A"])
        L.new(rc.outputs["Result"], add.inputs["B"])
        col = add.outputs["Result"]

    em = nt.nodes.new("ShaderNodeEmission")
    em.location = (x + 1050, y)
    L.new(col, em.inputs["Color"])
    L.new(em.outputs[0], out.inputs["Surface"])
    out.location = (x + 1250, y)
    return True


def outline_material():
    m = bpy.data.materials.get(f"{TAG}_outline")
    if m:
        return m
    m = bpy.data.materials.new(f"{TAG}_outline")
    m.use_nodes = True
    m.use_backface_culling = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    _sock(em, "Color", (0.035, 0.02, 0.03, 1))  # quase preto, puxado pro vinho
    # a casca não pode projetar sombra: vira transparente para raios de sombra
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    lp = nt.nodes.new("ShaderNodeLightPath")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lp.outputs["Is Shadow Ray"], mix.inputs["Fac"])
    nt.links.new(em.outputs[0], mix.inputs[1])
    nt.links.new(tr.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    for attr, val in (("use_transparent_shadow", True), ("surface_render_method", "DITHERED")):
        if hasattr(m, attr):
            setattr(m, attr, val)
    m.diffuse_color = (0.035, 0.02, 0.03, 1)
    return m


# ------------------------------------------------------------ 2. contorno


def outline_nodegroup():
    ng = bpy.data.node_groups.get(f"{TAG}_Outline")
    if ng:
        return ng
    ng = bpy.data.node_groups.new(f"{TAG}_Outline", "GeometryNodeTree")
    ng.is_modifier = True
    iface = ng.interface
    iface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    w = iface.new_socket("Thickness", in_out="INPUT", socket_type="NodeSocketFloat")
    w.default_value, w.min_value = 0.012, 0.0
    v = iface.new_socket("Variation", in_out="INPUT", socket_type="NodeSocketFloat")
    v.default_value, v.min_value, v.max_value = 0.8, 0.0, 1.0
    s = iface.new_socket("Noise Scale", in_out="INPUT", socket_type="NodeSocketFloat")
    s.default_value = 3.0
    iface.new_socket("Material", in_out="INPUT", socket_type="NodeSocketMaterial")
    iface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")

    N, L = ng.nodes, ng.links
    gi, go = N.new("NodeGroupInput"), N.new("NodeGroupOutput")
    gi.location, go.location = (-900, 0), (700, 0)

    pos = N.new("GeometryNodeInputPosition")
    nrm = N.new("GeometryNodeInputNormal")
    noise = N.new("ShaderNodeTexNoise")
    noise.location = (-600, -300)
    L.new(pos.outputs[0], noise.inputs["Vector"])
    L.new(gi.outputs["Noise Scale"], noise.inputs["Scale"])
    # largura = T * mix(1, ruído*2, variação)
    mr = N.new("ShaderNodeMapRange")
    mr.location = (-400, -300)
    mr.inputs["From Min"].default_value = 0.3
    mr.inputs["From Max"].default_value = 0.7
    mr.inputs["To Min"].default_value = 0.15
    mr.inputs["To Max"].default_value = 1.6
    L.new(noise.outputs["Fac"], mr.inputs["Value"])
    lerp = N.new("ShaderNodeMix")
    lerp.data_type = "FLOAT"
    lerp.location = (-200, -300)
    lerp.inputs["A"].default_value = 1.0
    L.new(gi.outputs["Variation"], lerp.inputs["Factor"])
    L.new(mr.outputs["Result"], lerp.inputs["B"])
    mul = N.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    L.new(lerp.outputs["Result"], mul.inputs[0])
    L.new(gi.outputs["Thickness"], mul.inputs[1])
    off = N.new("ShaderNodeVectorMath")
    off.operation = "SCALE"
    off.location = (0, -200)
    L.new(nrm.outputs[0], off.inputs[0])
    L.new(mul.outputs[0], off.inputs["Scale"])

    setp = N.new("GeometryNodeSetPosition")
    setp.location = (150, -100)
    L.new(gi.outputs["Geometry"], setp.inputs["Geometry"])
    L.new(off.outputs[0], setp.inputs["Offset"])
    flip = N.new("GeometryNodeFlipFaces")
    flip.location = (330, -100)
    L.new(setp.outputs[0], flip.inputs[0])
    setm = N.new("GeometryNodeSetMaterial")
    setm.location = (500, -100)
    L.new(flip.outputs[0], setm.inputs["Geometry"])
    L.new(gi.outputs["Material"], setm.inputs["Material"])
    join = N.new("GeometryNodeJoinGeometry")
    join.location = (600, 0)
    L.new(setm.outputs[0], join.inputs[0])
    L.new(gi.outputs["Geometry"], join.inputs[0])
    L.new(join.outputs[0], go.inputs["Geometry"])
    return ng


def _set_mod_input(mod, identifier, value):
    """Blender 5.x: mod.properties.inputs.<id>.value; 4.x: mod[id]."""
    props = getattr(mod, "properties", None)
    if props is not None and hasattr(props, "inputs"):
        getattr(props.inputs, identifier).value = value
    else:
        mod[identifier] = value


def add_outline(obj, thickness=None, variation=0.8):
    if obj.type != "MESH" or obj.modifiers.get(f"{TAG}_Outline"):
        return False
    dims = sorted(obj.dimensions)
    if dims[0] < 0.01 * dims[2]:  # chão/parede/plano: contorno não faz sentido
        return False
    mod = obj.modifiers.new(f"{TAG}_Outline", "NODES")
    mod.node_group = outline_nodegroup()
    if thickness is None:  # ~1.2% da maior dimensão do objeto
        thickness = 0.012 * max(obj.dimensions) / max(max(obj.scale), 1e-6)
    ids = {s.name: s.identifier for s in mod.node_group.interface.items_tree
           if getattr(s, "in_out", "") == "INPUT"}
    _set_mod_input(mod, ids["Thickness"], thickness)
    _set_mod_input(mod, ids["Variation"], variation)
    _set_mod_input(mod, ids["Material"], outline_material())
    # o slot precisa existir para o EEVEE usar o material do contorno
    if outline_material().name not in [m.name for m in obj.data.materials if m]:
        obj.data.materials.append(outline_material())
    return True


# ------------------------------------------------------------- 3. render


def setup_render(scene, *, vertical=True, fps=24):
    scene.render.engine = "BLENDER_EEVEE"
    if vertical:
        scene.render.resolution_x, scene.render.resolution_y = 1080, 1920
    scene.render.fps = fps
    scene.render.film_transparent = False
    vs = scene.view_settings
    vs.view_transform = "AgX"
    for look in ("AgX - Punchy", "Punchy"):
        try:
            vs.look = look
            break
        except TypeError:
            pass
    vs.exposure, vs.gamma = 0.0, 1.0
    ee = scene.eevee
    for attr, val in (("taa_render_samples", 64), ("use_shadows", True),
                      ("use_raytracing", True), ("fast_gi_method", "GLOBAL_ILLUMINATION")):
        if hasattr(ee, attr):
            try:
                setattr(ee, attr, val)
            except (TypeError, AttributeError):
                pass


def light_rig(scene, target=(0, 0, 0), size=2.0, warm=(1.0, 0.72, 0.45), cool=(0.45, 0.6, 1.0)):
    """Key quente + recorte (rim) frio forte + preenchimento roxo baixo."""
    col = bpy.data.collections.get(f"{TAG}_Lights") or bpy.data.collections.new(f"{TAG}_Lights")
    if col.name not in scene.collection.children:
        scene.collection.children.link(col)
    tx, ty, tz = target

    def area(name, color, energy, loc, sz):
        ob = bpy.data.objects.get(name)
        if ob is None:
            ld = bpy.data.lights.new(name, "AREA")
            ob = bpy.data.objects.new(name, ld)
            col.objects.link(ob)
        ob.data.color, ob.data.energy, ob.data.size = color, energy, sz
        ob.location = loc
        d = (tx - loc[0], ty - loc[1], tz - loc[2])
        ob.rotation_euler = _look_rot(d)
        return ob

    s = size
    area(f"{TAG}_Key", warm, 900 * s * s, (tx - 3 * s, ty - 3 * s, tz + 3 * s), 2 * s)
    area(f"{TAG}_Rim", cool, 1600 * s * s, (tx + 2.5 * s, ty + 3 * s, tz + 1.5 * s), 1.2 * s)
    area(f"{TAG}_Fill", (0.6, 0.45, 1.0), 150 * s * s, (tx + 3 * s, ty - 2 * s, tz), 3 * s)


def _look_rot(d):
    from mathutils import Vector
    return Vector(d).to_track_quat("-Z", "Y").to_euler()


def compositor(scene, *, boil=True, displace_px=3.0, bloom=0.37, kuwahara=4,
               paper=0.30, dots=0.02, grain=0.12, chroma=0.03, vignette=0.40):
    """Monta a pilha de finalização. Substitui o compositor da cena."""
    ng = bpy.data.node_groups.get(f"{TAG}_Finish")
    if ng:
        bpy.data.node_groups.remove(ng)
    ng = bpy.data.node_groups.new(f"{TAG}_Finish", "CompositorNodeTree")
    ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    scene.compositing_node_group = ng
    N, L = ng.nodes, ng.links
    X = [0]

    def node(t, **inputs):
        n = N.new(t)
        n.location = (X[0], 0)
        X[0] += 220
        for k, v in inputs.items():
            _sock(n, k, v)
        return n

    rl = node("CompositorNodeRLayers")
    rl.scene = scene
    img = rl.outputs["Image"]

    # 3a. tremor de borda: ruído procedural vira deslocamento em pixels.
    if displace_px > 0:
        coords = N.new("CompositorNodeImageCoordinates")
        coords.location = (0, -400)
        L.new(img, coords.inputs["Image"])
        nz = N.new("ShaderNodeTexNoise")
        nz.noise_dimensions = "4D"
        nz.location = (220, -400)
        _sock(nz, "Scale", 40.0)
        _sock(nz, "Detail", 1.0)
        L.new(coords.outputs[0], nz.inputs["Vector"])
        if boil:  # muda a cada 2 frames ("on twos"), como desenho animado
            t = N.new("CompositorNodeSceneTime")
            t.location = (0, -650)
            fl = N.new("ShaderNodeMath")
            fl.operation = "SNAP"
            fl.location = (220, -650)
            fl.inputs[1].default_value = 2.0
            L.new(t.outputs["Frame"], fl.inputs[0])
            sc = N.new("ShaderNodeMath")
            sc.operation = "MULTIPLY"
            sc.location = (400, -650)
            sc.inputs[1].default_value = 0.37
            L.new(fl.outputs[0], sc.inputs[0])
            L.new(sc.outputs[0], nz.inputs["W"])
        sub = N.new("ShaderNodeVectorMath")
        sub.operation = "SUBTRACT"
        sub.location = (440, -400)
        sub.inputs[1].default_value = (0.5, 0.5, 0.5)
        L.new(nz.outputs["Color"], sub.inputs[0])
        amp = N.new("ShaderNodeVectorMath")
        amp.operation = "SCALE"
        amp.location = (660, -400)
        amp.inputs["Scale"].default_value = displace_px * 2
        L.new(sub.outputs[0], amp.inputs[0])
        disp = node("CompositorNodeDisplace")
        L.new(img, disp.inputs["Image"])
        L.new(amp.outputs[0], disp.inputs["Displacement"])
        img = disp.outputs[0]

    # 3b. bloom
    glare = node("CompositorNodeGlare", Type="Bloom", Quality="Medium",
                 Threshold=0.8, Strength=bloom, Saturation=1.0, Size=0.1)
    L.new(img, glare.inputs["Image"])
    img = glare.outputs["Image"]

    # 3c. sharpen -> Kuwahara (pincel) -> sharpen
    sh1 = node("CompositorNodeFilter", Type="Diamond Sharpen", Factor=0.513)
    L.new(img, sh1.inputs["Image"])
    kw = node("CompositorNodeKuwahara", Type="Anisotropic", Size=kuwahara,
              Uniformity=4, Sharpness=1.0, Eccentricity=1.0)
    L.new(sh1.outputs[0], kw.inputs["Image"])
    sh2 = node("CompositorNodeFilter", Type="Diamond Sharpen", Factor=0.573)
    L.new(kw.outputs[0], sh2.inputs["Image"])
    img = sh2.outputs[0]

    # 3d. papel (Overlay) e pontilhado (Screen), texturas tileadas
    def texture(name, gen, size, scale):
        im = node("CompositorNodeImage")
        im.image = _procedural_image(name, size, gen)
        im.location.y = -300
        tr = node("CompositorNodeTransform", Scale=scale,
                  Interpolation="Nearest", **{"Extension X": "Repeat", "Extension Y": "Repeat"})
        tr.location.y = -300
        L.new(im.outputs["Image"], tr.inputs["Image"])
        return tr.outputs[0]

    for name, gen, size, scale, mode, fac in (
        (f"{TAG}_paper", _paper, 512, 1.0, "OVERLAY", paper),
        (f"{TAG}_dots", _dots, 256, 1.0, "SCREEN", dots),
    ):
        if fac <= 0:
            continue
        tex = texture(name, gen, size, scale)
        mx = node("ShaderNodeMix")
        mx.data_type = "RGBA"
        mx.blend_type = mode
        mx.clamp_factor = True
        mx.inputs["Factor"].default_value = fac
        L.new(img, mx.inputs["A"])
        L.new(tex, mx.inputs["B"])
        img = mx.outputs["Result"]

    # 3e. grão de sensor (luminância), animado
    if grain > 0:
        gc = N.new("CompositorNodeImageCoordinates")
        gc.location = (X[0], -400)
        L.new(img, gc.inputs["Image"])
        gn = N.new("ShaderNodeTexWhiteNoise")
        gn.noise_dimensions = "4D"
        gn.location = (X[0] + 200, -400)
        sc = N.new("ShaderNodeVectorMath")
        sc.operation = "SCALE"
        sc.inputs["Scale"].default_value = 1000.0
        sc.location = (X[0] + 100, -550)
        L.new(gc.outputs[0], sc.inputs[0])
        L.new(sc.outputs[0], gn.inputs["Vector"])
        tm = N.new("CompositorNodeSceneTime")
        tm.location = (X[0], -700)
        L.new(tm.outputs["Frame"], gn.inputs["W"])
        mx = node("ShaderNodeMix")
        mx.data_type = "RGBA"
        mx.blend_type = "SOFT_LIGHT"
        mx.inputs["Factor"].default_value = grain
        L.new(img, mx.inputs["A"])
        L.new(gn.outputs["Value"], mx.inputs["B"])
        img = mx.outputs["Result"]

    # 3f. aberração cromática
    if chroma > 0:
        ld = node("CompositorNodeLensdist", Type="Radial", Distortion=0.0, Dispersion=chroma)
        L.new(img, ld.inputs["Image"])
        img = ld.outputs[0]

    # 3g. vinheta: elipse desfocada multiplicando
    if vignette > 0:
        el = N.new("CompositorNodeEllipseMask")
        el.location = (X[0], -350)
        _sock(el, "Size", (0.95, 0.95))
        bl = N.new("CompositorNodeBlur")
        bl.location = (X[0] + 200, -350)
        _sock(bl, "Size", (300, 300))
        L.new(el.outputs[0], bl.inputs["Image"])
        inv = N.new("ShaderNodeMath")
        inv.operation = "MULTIPLY_ADD"
        inv.location = (X[0] + 400, -350)
        inv.inputs[1].default_value = vignette
        inv.inputs[2].default_value = 1 - vignette
        L.new(bl.outputs[0], inv.inputs[0])
        mx = node("ShaderNodeMix")
        mx.data_type = "RGBA"
        mx.blend_type = "MULTIPLY"
        mx.inputs["Factor"].default_value = 1.0
        L.new(img, mx.inputs["A"])
        L.new(inv.outputs[0], mx.inputs["B"])
        img = mx.outputs["Result"]

    out = node("NodeGroupOutput")
    L.new(img, out.inputs[0])
    return ng


# ------------------------------------------------------------------ apply


def apply(scene=None, *, materials=True, shading=True, outlines=True, comp=True,
          lights=False, render=True, shading_kw=None, **comp_kw):
    scene = scene or bpy.context.scene
    if render:
        setup_render(scene)
    done = {"materials": 0, "outlines": 0}
    for ob in scene.objects:
        if ob.type != "MESH":
            continue
        if materials:
            for slot in ob.material_slots:
                if slot.material and slot.material.name != f"{TAG}_outline":
                    done["materials"] += painterly_material(slot.material)
                    if shading:
                        paint_shading(slot.material, **(shading_kw or {}))
        if outlines:
            done["outlines"] += add_outline(ob)
    if lights:
        light_rig(scene)
    if comp:
        compositor(scene, **comp_kw)
    return done


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    print("[iwaac]", apply(bpy.context.scene, lights="--lights" in argv))
    if "--save" in argv:
        bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath(argv[argv.index("--save") + 1]))
    if "--render" in argv:
        bpy.context.scene.render.filepath = argv[argv.index("--render") + 1]
        bpy.ops.render.render(write_still=True)
