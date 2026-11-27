"""Kumo: Chromatic Shift (protótipo).

A pele do Kumo troca de paleta numa onda que percorre a superfície. Cada faceta
visual (região plana da malha) vira de cor como uma peça só, com um pequeno
atraso próprio, e brilha no instante em que vira ("Facet Pulse").

Três partes:

1. bake_attributes(obj)  (Python, pose de repouso, uma vez)
   - cs_dist        (ponto): distância geodésica normalizada a partir da testa.
                    Segue a superfície: a onda contorna o focinho e desce a
                    cauda pela espiral, porque mede ao longo da malha.
   - cs_facet_t     (face) : chegada da onda em cada faceta visual (média).
   - cs_facet_rand  (face) : número aleatório por faceta (atraso, faíscas).
   Os atributos vivem na malha e acompanham o rig: a onda fica estável em
   qualquer animação.

2. chromatic_group()  (node group de shader "KumoChromaticShift")
   Entra a cor da textura e sai a cor nova (Color) + o brilho (Glow). A cor
   nova remapeia a textura: verde escuro/médio -> escuro/médio da paleta,
   manchas -> destaque da paleta, barriga -> barriga da paleta.

3. install(obj, ...)  liga o grupo no material da pele, soma o brilho na
   saída e cria as propriedades no objeto, com drivers:
       cs_progress   0..1  Transformation Progress (o único parâmetro de animação)
       cs_activation 0..1  olhos acendem + faíscas na crista
       cs_afterglow  0..1  faíscas residuais depois da troca

Nada aqui salva por cima do arquivo original: os scripts de protótipo abrem o
modelo e gravam uma cópia em kumo-chromatic-shift/.
"""

from __future__ import annotations

import heapq
import math
import random

import bpy
import bmesh
from mathutils import Vector

GROUP = "KumoChromaticShift"

# (escuro, médio, destaque das manchas, barriga) em RGB linear
PALETTES = {
    "original": None,
    "cibernetico": ((0.00, 0.10, 0.32), (0.00, 0.62, 0.95), (0.35, 0.95, 1.00), (0.78, 0.95, 1.00)),
    "vulcanico": ((0.42, 0.03, 0.02), (0.95, 0.22, 0.04), (1.00, 0.72, 0.10), (1.00, 0.84, 0.52)),
    "fantasma": ((0.16, 0.03, 0.32), (0.55, 0.12, 0.85), (1.00, 0.28, 0.78), (0.93, 0.80, 1.00)),
    "cristal": ((0.22, 0.42, 0.66), (0.58, 0.84, 1.00), (0.95, 0.98, 1.00), (1.00, 1.00, 1.00)),
}
ENERGY = (0.15, 1.0, 1.0)      # ciano da frente da onda
TRANSITION = (0.62, 0.30, 1.0)  # reflexo violeta na zona de transição


# ------------------------------------------------------------------ bake


def _group_weights(obj, name):
    g = obj.vertex_groups.get(name)
    w = [0.0] * len(obj.data.vertices)
    if g is None:
        return w
    for v in obj.data.vertices:
        for e in v.groups:
            if e.group == g.index:
                w[v.index] = e.weight
    return w


def forehead_vertex(obj):
    """Vértice da testa: linha do meio, acima e entre os olhos, na frente."""
    me = obj.data
    head = _group_weights(obj, "head")
    eyes = [o for o in bpy.data.objects if o.name.startswith("KumoOlho_Globo")]
    if eyes:
        pts = [o.matrix_world @ Vector(c) for o in eyes for c in o.bound_box]
        top = max(p.z for p in pts)
        target = Vector((0.0, min(p.y for p in pts), top))
    else:
        target = Vector((0, -10, 10))
    inv = obj.matrix_world.inverted()
    t = inv @ target
    best, bd = None, 1e9
    for v in me.vertices:
        if head[v.index] < 0.5 or abs(v.co.x) > 0.04:
            continue
        d = (v.co - t).length
        if d < bd:
            best, bd = v.index, d
    return best if best is not None else max(range(len(me.vertices)), key=lambda i: me.vertices[i].co.z)


def _geodesic(bm, src):
    dist = [math.inf] * len(bm.verts)
    dist[src] = 0.0
    heap = [(0.0, src)]
    bm.verts.ensure_lookup_table()
    while heap:
        d, i = heapq.heappop(heap)
        if d > dist[i]:
            continue
        v = bm.verts[i]
        for e in v.link_edges:
            j = e.other_vert(v).index
            nd = d + e.calc_length()
            if nd < dist[j]:
                dist[j] = nd
                heapq.heappush(heap, (nd, j))
    return dist


def _facets(bm, angle_deg):
    """Agrupa faces vizinhas quase coplanares (crescimento de região)."""
    lim = math.cos(math.radians(angle_deg))
    bm.faces.ensure_lookup_table()
    label = [-1] * len(bm.faces)
    n = 0
    order = sorted(range(len(bm.faces)), key=lambda i: -bm.faces[i].calc_area())
    for seed in order:
        if label[seed] != -1:
            continue
        sn = bm.faces[seed].normal.copy()
        stack = [seed]
        label[seed] = n
        while stack:
            f = bm.faces[stack.pop()]
            for e in f.edges:
                for g in e.link_faces:
                    if label[g.index] == -1 and g.normal.dot(sn) >= lim:
                        label[g.index] = n
                        stack.append(g.index)
        n += 1
    return label, n


def nearest_vertex(obj, target):
    """Vértice da pele mais perto de um objeto (Empty) na pose atual."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    n = len(obj.data.vertices)  # o Solidify acrescenta vértices depois destes
    p = target.matrix_world.translation
    mw = obj.matrix_world
    best = min(range(n), key=lambda i: (mw @ me.vertices[i].co - p).length_squared)
    ev.to_mesh_clear()
    return best


def bake_attributes(obj, *, region="head", facet_angle=22.0, seed=7, origin=None,
                    noise_scale=9.0):
    """Grava cs_dist / cs_facet_t / cs_facet_rand na malha (pose de repouso).

    region="head": a distância é normalizada pela cabeça (protótipo: a onda
    completa a cabeça em progress=1 e para no pescoço). region="body": o corpo
    inteiro, da testa à ponta da cauda.
    """
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)  # malha sem modificadores = pose de repouso
    bm.normal_update()
    if origin is None:
        src = forehead_vertex(obj)
    elif isinstance(origin, int):
        src = origin
    else:  # um objeto: a onda nasce no ponto da pele mais perto dele
        src = nearest_vertex(obj, origin)
    dist = _geodesic(bm, src)
    finite = [d for d in dist if d < math.inf]
    if region == "head":
        hw = _group_weights(obj, "head")
        jw = _group_weights(obj, "jaw")
        head = [a + b for a, b in zip(hw, jw)]  # queixo divide peso entre head e jaw
        ref = max((dist[i] for i in range(len(dist)) if head[i] > 0.5 and dist[i] < math.inf), default=max(finite))
        # protótipo: só a cabeça transforma; o resto fica além do alcance
        dist = [d if head[i] > 0.5 else math.inf for i, d in enumerate(dist)]
    else:
        ref = max(finite)
    dn = [min(d / ref, 4.0) if d < math.inf else 4.0 for d in dist]

    label, n = _facets(bm, facet_angle)
    rng = random.Random(seed)
    rnd = [rng.random() for _ in range(n)]
    acc = [0.0] * n
    cnt = [0] * n
    for f in bm.faces:
        t = sum(dn[v.index] for v in f.verts) / len(f.verts)
        acc[label[f.index]] += t
        cnt[label[f.index]] += 1
    ft = [acc[k] / max(cnt[k], 1) for k in range(n)]
    bm.free()

    from mathutils import noise as mnoise
    sz = max(obj.dimensions) / max(max(obj.scale), 1e-6)
    nz = [0.5 + 0.5 * mnoise.noise(v.co * (noise_scale / sz)) for v in me.vertices]

    for name, dom in (("cs_dist", "POINT"), ("cs_noise", "POINT"),
                      ("cs_facet_t", "FACE"), ("cs_facet_rand", "FACE")):
        if name in me.attributes:
            me.attributes.remove(me.attributes[name])
        me.attributes.new(name, "FLOAT", dom)
    me.attributes["cs_dist"].data.foreach_set("value", dn)
    me.attributes["cs_noise"].data.foreach_set("value", nz)
    me.attributes["cs_facet_t"].data.foreach_set("value", [ft[label[i]] for i in range(len(me.polygons))])
    me.attributes["cs_facet_rand"].data.foreach_set("value", [rnd[label[i]] for i in range(len(me.polygons))])
    sizes = sorted(cnt, reverse=True)
    return {"origin_vertex": src, "facets": n, "largest_facets": sizes[:5],
            "faces_per_facet": round(len(me.polygons) / n, 1)}


def bake_followers(skin, objects):
    """Peças separadas (pálpebras...) herdam a onda da face de pele mais próxima."""
    from mathutils.kdtree import KDTree
    sme = skin.data
    mw = skin.matrix_world
    dist = [0.0] * len(sme.vertices)
    sme.attributes["cs_dist"].data.foreach_get("value", dist)
    nzs = [0.5] * len(sme.vertices)
    if "cs_noise" in sme.attributes:
        sme.attributes["cs_noise"].data.foreach_get("value", nzs)
    ft = [0.0] * len(sme.polygons)
    fr = [0.0] * len(sme.polygons)
    sme.attributes["cs_facet_t"].data.foreach_get("value", ft)
    sme.attributes["cs_facet_rand"].data.foreach_get("value", fr)
    kv = KDTree(len(sme.vertices))
    for v in sme.vertices:
        kv.insert(mw @ v.co, v.index)
    kv.balance()
    kf = KDTree(len(sme.polygons))
    for p in sme.polygons:
        kf.insert(mw @ p.center, p.index)
    kf.balance()
    done = []
    for ob in objects:
        me = ob.data
        ow = ob.matrix_world
        vi = [kv.find(ow @ v.co)[1] for v in me.vertices]
        vd = [dist[i] for i in vi]
        near = [kf.find(ow @ p.center)[1] for p in me.polygons]
        for name, dom in (("cs_dist", "POINT"), ("cs_noise", "POINT"),
                          ("cs_facet_t", "FACE"), ("cs_facet_rand", "FACE")):
            if name in me.attributes:
                me.attributes.remove(me.attributes[name])
            me.attributes.new(name, "FLOAT", dom)
        me.attributes["cs_dist"].data.foreach_set("value", vd)
        me.attributes["cs_noise"].data.foreach_set("value", [nzs[i] for i in vi])
        me.attributes["cs_facet_t"].data.foreach_set("value", [ft[i] for i in near])
        me.attributes["cs_facet_rand"].data.foreach_set("value", [fr[i] for i in near])
        done.append(ob.name)
    return done


# ------------------------------------------------------------ node group


class _B:
    """Construtor enxuto de nós dentro de um node tree."""

    def __init__(self, nt):
        self.nt, self.x = nt, 0

    def n(self, t, **props):
        node = self.nt.nodes.new(t)
        node.location = (self.x, 0)
        self.x += 40
        for k, v in props.items():
            setattr(node, k, v)
        return node

    def link(self, a, b):
        self.nt.links.new(a, b)

    def math(self, op, a, b=None, c=None, clamp=False):
        m = self.n("ShaderNodeMath", operation=op, use_clamp=clamp)
        for i, v in enumerate((a, b, c)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                m.inputs[i].default_value = v
            else:
                self.link(v, m.inputs[i])
        return m.outputs[0]

    def maprange(self, v, a, b, c=0.0, d=1.0, interp="LINEAR"):
        m = self.n("ShaderNodeMapRange", interpolation_type=interp, clamp=True)
        for sock, val in zip(("Value", "From Min", "From Max", "To Min", "To Max"), (v, a, b, c, d)):
            if isinstance(val, (int, float)):
                m.inputs[sock].default_value = val
            else:
                self.link(val, m.inputs[sock])
        return m.outputs["Result"]

    def mix(self, a, b, fac, blend="MIX"):
        m = self.n("ShaderNodeMix", data_type="RGBA", blend_type=blend, clamp_factor=True)
        for sock, val in (("Factor", fac), ("A", a), ("B", b)):
            if isinstance(val, (int, float)):
                m.inputs[sock].default_value = val
            elif isinstance(val, tuple):
                m.inputs[sock].default_value = (*val[:3], 1.0)
            else:
                self.link(val, m.inputs[sock])
        return m.outputs["Result"]

    def _scale(self, col, f):
        v = self.n("ShaderNodeVectorMath", operation="SCALE")
        self.link(col, v.inputs[0])
        if isinstance(f, (int, float)):
            v.inputs["Scale"].default_value = f
        else:
            self.link(f, v.inputs["Scale"])
        return v.outputs[0]

    def add(self, a, b):
        v = self.n("ShaderNodeVectorMath", operation="ADD")
        self.link(a, v.inputs[0])
        self.link(b, v.inputs[1])
        return v.outputs[0]

    def attr(self, name):
        a = self.n("ShaderNodeAttribute", attribute_type="GEOMETRY", attribute_name=name)
        return a.outputs["Fac"]


def chromatic_group():
    ng = bpy.data.node_groups.get(GROUP)
    if ng:
        bpy.data.node_groups.remove(ng)
    ng = bpy.data.node_groups.new(GROUP, "ShaderNodeTree")
    it = ng.interface

    def inp(name, kind, default, lo=None, hi=None):
        s = it.new_socket(name, in_out="INPUT", socket_type=kind)
        s.default_value = default
        if lo is not None:
            s.min_value, s.max_value = lo, hi
        return s

    inp("Base Color", "NodeSocketColor", (0.3, 0.6, 0.2, 1))
    inp("Progress", "NodeSocketFloat", 0.0, 0.0, 1.0)
    inp("Activation", "NodeSocketFloat", 0.0, 0.0, 1.0)
    inp("Afterglow", "NodeSocketFloat", 0.0, 0.0, 1.0)
    inp("Wave Width", "NodeSocketFloat", 0.18, 0.01, 1.0)
    inp("Facet Mix", "NodeSocketFloat", 0.9, 0.0, 1.0)
    inp("Facet Variation", "NodeSocketFloat", 0.5, 0.0, 2.0)
    inp("Edge Noise", "NodeSocketFloat", 0.06, 0.0, 0.5)
    inp("Energy", "NodeSocketFloat", 1.0, 0.0, 5.0)
    for name, col in zip(("Dark", "Mid", "Accent", "Belly"), PALETTES["cibernetico"]):
        inp(name, "NodeSocketColor", (*col, 1))
    inp("Energy Color", "NodeSocketColor", (*ENERGY, 1))
    inp("Transition Color", "NodeSocketColor", (*TRANSITION, 1))
    it.new_socket("Color", in_out="OUTPUT", socket_type="NodeSocketColor")
    it.new_socket("Glow", in_out="OUTPUT", socket_type="NodeSocketColor")

    B = _B(ng)
    gi = B.n("NodeGroupInput")
    go = B.n("NodeGroupOutput")
    I = gi.outputs

    # --- paleta: remapeia a textura preservando o desenho das manchas
    hsv = B.n("ShaderNodeSeparateColor", mode="HSV")
    B.link(I["Base Color"], hsv.inputs[0])
    H, S, V = hsv.outputs[0], hsv.outputs[1], hsv.outputs[2]
    belly = B.math("MULTIPLY", B.maprange(S, 0.42, 0.30), B.maprange(V, 0.55, 0.72))
    spots = B.maprange(H, 0.265, 0.215, interp="SMOOTHSTEP")  # verde-amarelado
    main = B.mix(I["Dark"], I["Mid"], B.maprange(V, 0.30, 0.85))
    target = B.mix(main, I["Accent"], spots)
    target = B.mix(target, I["Belly"], belly)

    # --- onda: frente, distância por faceta, máscara de transformação
    W = I["Wave Width"]
    front = B.math("MULTIPLY", I["Progress"], B.math("ADD", W, 1.0))
    jitter = B.math("MULTIPLY", B.math("MULTIPLY", B.math("SUBTRACT", B.attr("cs_facet_rand"), 0.5),
                                       I["Facet Variation"]), W)
    d_f = B.math("ADD", B.attr("cs_facet_t"), jitter)
    # borda orgânica: ruído (gravado na pose de repouso) empurra a frente
    d_v = B.math("ADD", B.attr("cs_dist"),
                 B.math("MULTIPLY", B.math("SUBTRACT", B.attr("cs_noise"), 0.5), I["Edge Noise"]))
    fm = I["Facet Mix"]
    d = B.math("ADD", B.math("MULTIPLY", d_v, B.math("SUBTRACT", 1.0, fm)), B.math("MULTIPLY", d_f, fm))
    # facetas viram rápido (saltos), o modo contínuo usa a largura toda
    wt = B.math("MULTIPLY", W, B.math("SUBTRACT", 1.0, B.math("MULTIPLY", fm, 0.7)))
    local = B.maprange(B.math("SUBTRACT", front, d), 0.0, wt, interp="SMOOTHSTEP")

    # zona de transição: reflexo violeta no meio da virada
    bell = B.math("MULTIPLY", B.math("MULTIPLY", local, B.math("SUBTRACT", 1.0, local)), 4.0)
    # só pele muda: família verde/amarela (matiz ~43°..200°) e a barriga.
    # laranja do olho, vermelho da boca etc. ficam como estão.
    skin = B.math("MULTIPLY", B.maprange(H, 0.10, 0.13), B.maprange(H, 0.58, 0.52))
    skin = B.math("MAXIMUM", skin, belly)
    color = B.mix(I["Base Color"], target, B.math("MULTIPLY", local, skin))
    color = B.mix(color, I["Transition Color"], B.math("MULTIPLY", bell, 0.45))
    B.link(color, go.inputs["Color"])

    # --- brilho
    started = B.maprange(I["Progress"], 0.0, 0.03)
    # faixa ciano contínua na frente da onda (segue a superfície)
    x = B.math("DIVIDE", B.math("SUBTRACT", front, d_v), B.math("MULTIPLY", W, 0.18))
    band = B.math("EXPONENT", B.math("MULTIPLY", B.math("MULTIPLY", x, x), -1.0))
    band = B.math("MULTIPLY", band, started)
    pulse_col = B.mix(I["Energy Color"], target, 0.45)
    glow = B.add(B._scale(I["Energy Color"], B.math("MULTIPLY", band, 0.8)),
                 B._scale(pulse_col, B.math("MULTIPLY", bell, 0.9)))
    glow = B._scale(glow, I["Energy"])
    # ativação: faíscas nas facetas da crista/testa
    near = B.maprange(B.attr("cs_facet_t"), 0.12, 0.0)
    spark = B.math("MULTIPLY", B.math("MULTIPLY", near, B.math("GREATER_THAN", B.attr("cs_facet_rand"), 0.72)),
                   I["Activation"])
    glow = B.add(glow, B._scale(I["Energy Color"], B.math("MULTIPLY", spark, 0.9)))
    # residual: poucas facetas já transformadas piscam e somem
    resid = B.math("MULTIPLY", B.math("MULTIPLY", B.math("GREATER_THAN", B.attr("cs_facet_rand"), 0.93), local),
                   I["Afterglow"])
    glow = B.add(glow, B._scale(I["Accent"], resid))
    B.link(glow, go.inputs["Glow"])

    # organiza na grade para quem abrir no editor
    for i, nd in enumerate(ng.nodes):
        nd.location = ((i % 12) * 220, -(i // 12) * 260)
    return ng


# --------------------------------------------------------------- install


def _drive(sock, obj, prop):
    fc = sock.driver_add("default_value")
    drv = fc.driver
    drv.type = "AVERAGE"
    var = drv.variables.new()
    var.type = "SINGLE_PROP"
    var.targets[0].id = obj
    var.targets[0].data_path = f'["{prop}"]'
    return fc


def attach(mat, owner, palette="cibernetico"):
    """Insere o grupo antes da cor do material (Emission ou Principled)."""
    nt = mat.node_tree
    if nt.nodes.get("CS"):
        return nt.nodes["CS"]
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output)
    shader = out.inputs["Surface"].links[0].from_node
    if shader.type == "BSDF_PRINCIPLED":
        # cor vem da textura na emissão (anel do olho) ou da cor base
        e = shader.inputs["Emission Color"]
        sock = e if (e.is_linked and not shader.inputs["Base Color"].is_linked) else shader.inputs["Base Color"]
    elif "Color" in shader.inputs:
        sock = shader.inputs["Color"]
    else:
        return None  # contorno (Mix Shader) e afins: fica como está
    if sock.is_linked:
        src = sock.links[0].from_socket
    else:
        rgb = nt.nodes.new("ShaderNodeRGB")
        rgb.outputs[0].default_value = tuple(sock.default_value)
        rgb.location = (shader.location.x - 600, shader.location.y)
        src = rgb.outputs[0]
    grp = nt.nodes.new("ShaderNodeGroup")
    grp.node_tree = bpy.data.node_groups.get(GROUP) or chromatic_group()
    grp.name = "CS"
    grp.location = (shader.location.x - 300, shader.location.y + 200)
    nt.links.new(src, grp.inputs["Base Color"])
    nt.links.new(grp.outputs["Color"], sock)
    for prop, inp in (("cs_progress", "Progress"), ("cs_activation", "Activation"), ("cs_afterglow", "Afterglow")):
        _drive(grp.inputs[inp], owner, prop)
    set_palette(mat, palette)
    return grp


def install(obj, *, skin_material="Kumo_Quad_Toon", followers=(), palette="cibernetico", eye_glow=3.0):
    """Liga o efeito na pele e nas peças que a seguem (sempre numa CÓPIA)."""
    for prop in ("cs_progress", "cs_activation", "cs_afterglow"):
        obj[prop] = 0.0
        obj.id_properties_ui(prop).update(min=0.0, max=1.0, soft_min=0.0, soft_max=1.0)
    mats = [bpy.data.materials[skin_material]]
    for ob in followers:
        mats += [sl.material for sl in ob.material_slots if sl.material and sl.material not in mats
                 and not any(k in sl.material.name.lower() for k in ("outline", "contorno"))]
    mats = [m for m in mats if attach(m, obj, palette) is not None]

    # olhos: a força da emissão sobe com a ativação
    for o in bpy.data.objects:
        if not o.name.startswith("KumoOlho_Iris"):
            continue
        for sl in o.material_slots:
            m = sl.material
            b = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None) if m else None
            if b is None:
                continue
            base = b.inputs["Emission Strength"].default_value
            fc = b.inputs["Emission Strength"].driver_add("default_value")
            fc.driver.type = "SCRIPTED"
            v = fc.driver.variables.new()
            v.name, v.type = "a", "SINGLE_PROP"
            v.targets[0].id, v.targets[0].data_path = obj, '["cs_activation"]'
            fc.driver.expression = f"{base:.3f} + a * {eye_glow:.3f}"  # expressão simples: roda sem Python
    return mats


def add_glow_output(mat, strength=4.0):
    """Soma o Glow do grupo na saída final (depois da finalização toon)."""
    nt = mat.node_tree
    grp = nt.nodes.get("CS")
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output)
    src = out.inputs["Surface"].links[0].from_socket
    em = nt.nodes.new("ShaderNodeEmission")
    em.name = "CS_glow"
    em.inputs["Strength"].default_value = strength
    nt.links.new(grp.outputs["Glow"], em.inputs["Color"])
    add = nt.nodes.new("ShaderNodeAddShader")
    nt.links.new(src, add.inputs[0])
    nt.links.new(em.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], out.inputs["Surface"])


def set_palette(mat, palette):
    grp = mat.node_tree.nodes["CS"]
    cols = PALETTES[palette]
    if cols is None:
        return
    for name, c in zip(("Dark", "Mid", "Accent", "Belly"), cols):
        grp.inputs[name].default_value = (*c, 1.0)
