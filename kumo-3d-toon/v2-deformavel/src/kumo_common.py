"""Shared, versioned copy of the approved Kumo palette, toon materials and P1/P2 head
definition, for the v2 (deformable) architecture. Copied from src/kumo_toon.py at
P1/P2 so v2 never depends on (or changes) the current model's script."""
import bpy  # noqa: F401
from mathutils import Vector

LIGHT_DIR = Vector((-0.55, -0.62, 0.58)).normalized()

def hexrgb(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    # sRGB -> linear (scene uses the Standard view transform)
    return tuple(((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c) + (1.0,)

PAL = {
    "dark": "#1B5E3B",     # crest, dorsal ridge
    "mid": "#4CAF6B",      # body
    "spot": "#C9D45B",     # camouflage patches
    "belly": "#EAD9B7",    # ventral area
    "amber": "#F4B642",    # iris
    "outline": "#5B3A2E",  # lines
    "cream": "#F9D993",    # inner iris
    "pupil": "#0E0A06",
    "mouth": "#4A2418",
    "tongue": "#D9826F",
}


def _math(N, L, o, x, y=None):
    n = N.new("ShaderNodeMath")
    n.operation = o
    for i, v in enumerate((x, y)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            L.new(v, n.inputs[i])
    return n.outputs[0]


def toon_material(name, base, shade=0.72, light=1.12, spots=None, belly=None):
    """Emission-only cel shader.
    Light: N·L of the flat facet normal through a constant ramp -> three hard bands.
    spots: Voronoi cell scale for angular camouflage patches (object space), or None.
    belly: (a, b, c, y0) ellipse on the object's front (object space) painted beige."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    for n in list(N):
        N.remove(n)
    out = N.new("ShaderNodeOutputMaterial")
    emit = N.new("ShaderNodeEmission")
    L.new(emit.outputs[0], out.inputs[0])

    geo = N.new("ShaderNodeNewGeometry")
    dot = N.new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    dot.inputs[1].default_value = LIGHT_DIR
    L.new(geo.outputs["Normal"], dot.inputs[0])
    ramp = N.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    e = ramp.color_ramp.elements
    e[0].position = 0.0
    e[0].color = (shade, shade, shade, 1)
    e[1].position = 0.18
    e[1].color = ((1 + shade) / 2,) * 3 + (1,)
    e3 = e.new(0.48)
    e3.color = (1, 1, 1, 1)
    e4 = e.new(0.74)
    e4.color = (light, light, light, 1)
    L.new(dot.outputs["Value"], ramp.inputs[0])

    col = N.new("ShaderNodeRGB")
    col.outputs[0].default_value = hexrgb(base)
    color_out = col.outputs[0]
    tc = N.new("ShaderNodeTexCoord")

    if spots:
        vor = N.new("ShaderNodeTexVoronoi")
        vor.inputs["Scale"].default_value = spots
        vor.inputs["Randomness"].default_value = 1.0
        L.new(tc.outputs["Object"], vor.inputs["Vector"])
        sepc = N.new("ShaderNodeSeparateColor")
        L.new(vor.outputs["Color"], sepc.inputs[0])
        mask = _math(N, L, "GREATER_THAN", sepc.outputs[0], 0.77)
        sc = N.new("ShaderNodeRGB")
        sc.outputs[0].default_value = hexrgb(PAL["spot"])
        mix = N.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        L.new(mask, mix.inputs["Factor"])
        L.new(color_out, mix.inputs["A"])
        L.new(sc.outputs[0], mix.inputs["B"])
        color_out = mix.outputs["Result"]

    if belly:
        a, b, c, y0 = belly
        sep = N.new("ShaderNodeSeparateXYZ")
        L.new(tc.outputs["Object"], sep.inputs[0])
        ex = _math(N, L, "POWER", _math(N, L, "DIVIDE", sep.outputs["X"], a), 2)
        ez = _math(N, L, "POWER", _math(N, L, "DIVIDE", _math(N, L, "SUBTRACT", sep.outputs["Z"], c), b), 2)
        inside = _math(N, L, "LESS_THAN", _math(N, L, "ADD", ex, ez), 1.0)
        front = _math(N, L, "LESS_THAN", sep.outputs["Y"], y0)
        bmask = _math(N, L, "MULTIPLY", inside, front)
        bc = N.new("ShaderNodeRGB")
        bc.outputs[0].default_value = hexrgb(PAL["belly"])
        mix2 = N.new("ShaderNodeMix")
        mix2.data_type = "RGBA"
        L.new(bmask, mix2.inputs["Factor"])
        L.new(color_out, mix2.inputs["A"])
        L.new(bc.outputs[0], mix2.inputs["B"])
        color_out = mix2.outputs["Result"]

    mul = N.new("ShaderNodeMix")
    mul.data_type = "RGBA"
    mul.blend_type = "MULTIPLY"
    mul.inputs["Factor"].default_value = 1.0
    L.new(color_out, mul.inputs["A"])
    L.new(ramp.outputs[0], mul.inputs["B"])
    L.new(mul.outputs["Result"], emit.inputs["Color"])
    return m


def flat_material(name, hexc):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = hexrgb(hexc)
    nt.links.new(e.outputs[0], out.inputs[0])
    return m


def iris_material():
    """Eyeball: cream centre -> amber ring -> dark rim, by distance from the local -Y axis."""
    m = bpy.data.materials.new("Kumo_Iris")
    m.use_nodes = True
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    for n in list(N):
        N.remove(n)
    out = N.new("ShaderNodeOutputMaterial")
    emit = N.new("ShaderNodeEmission")
    L.new(emit.outputs[0], out.inputs[0])
    tc = N.new("ShaderNodeTexCoord")
    sep = N.new("ShaderNodeSeparateXYZ")
    L.new(tc.outputs["Object"], sep.inputs[0])
    comb = N.new("ShaderNodeCombineXYZ")
    L.new(sep.outputs["X"], comb.inputs["X"])
    L.new(sep.outputs["Z"], comb.inputs["Y"])
    ln = N.new("ShaderNodeVectorMath")
    ln.operation = "LENGTH"
    L.new(comb.outputs[0], ln.inputs[0])
    ramp = N.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    el = ramp.color_ramp.elements
    el[0].position = 0.0
    el[0].color = hexrgb("#FBE0A0")
    el[1].position = 0.55
    el[1].color = hexrgb(PAL["cream"])
    for pos, hx in ((0.72, "#F6C45E"), (0.80, PAL["amber"]), (0.90, "#D98F22"), (0.95, "#3A1E0E")):
        n = el.new(pos)
        n.color = hexrgb(hx)
    L.new(ln.outputs["Value"], ramp.inputs[0])
    L.new(ramp.outputs[0], emit.inputs["Color"])
    return m



# Approved head geometry (P1 + P2), unchanged
HEAD_VERTS = {
    # crest (raised pyramid): tip, front corner, V between the eyes, back corner, occipital end
    "T": (0.0, 0.02, 1.965), "S": (0.21, -0.21, 1.79), "V": (0.0, -0.50, 1.53),
    "Q": (0.13, 0.49, 1.62), "Bt": (0.0, 0.66, 1.24),
    # skull box: top corners, mid-side corners, lower corners
    "A": (0.50, -0.45, 1.57), "B": (0.47, 0.51, 1.55),
    "D": (0.555, -0.43, 1.24), "E": (0.555, 0.60, 1.30),
    "F": (0.47, -0.34, 1.04), "G": (0.44, 0.53, 1.04),
    # flat chin plate
    "J": (0.23, -0.17, 0.955), "K": (0.22, 0.36, 0.955),
    # short symmetrical snout and upper-lip ledge
    "N": (0.0, -0.565, 1.20), "L": (0.0, -0.50, 1.09),
}
CREST_KEYS = ("T", "S", "V", "Q", "Bt")


