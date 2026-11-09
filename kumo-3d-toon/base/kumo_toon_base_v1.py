"""Kumo — 2.5D cel-shaded (toon) model, built procedurally in Blender.

Run with Blender's Python (Blender >= 4.2, tested on 5.2):
    blender -b -P kumo_toon.py -- [--out DIR] [--render]
or with the `bpy` wheel:
    python kumo_toon.py --out DIR --render

Builds the faceted low-poly Kumo of the approved reference
(referencia de modelo/), applies a toon shader (hard light bands, flat facets,
camouflage spots) plus dark-brown Freestyle outlines, saves kumo_toon.blend and,
with --render, renders the turnaround and the eight expressions.

Units: 1 H = head height (crest tip -> chin) = 1.0 Blender unit.
Ground z = 0, chin z = 0.96, crest tip z = 1.96 (measured on the reference).
The character faces -Y; +X is the character's LEFT (viewer's right in front view).
"""
import math
import os
import sys

import bpy  # noqa: E402  (bpy must be imported before bmesh in the bpy wheel)
import bmesh
from mathutils import Matrix, Vector

# ------------------------------------------------------------------ args
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
OUT = os.path.abspath(argv[argv.index("--out") + 1]) if "--out" in argv else os.getcwd()
DO_RENDER = "--render" in argv
ONLY = argv[argv.index("--only") + 1] if "--only" in argv else None
RES = int(argv[argv.index("--res") + 1]) if "--res" in argv else 1400
os.makedirs(OUT, exist_ok=True)

# ------------------------------------------------------------------ palette (reference)
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

# ------------------------------------------------------------------ scene
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 24
scene.cycles.use_denoising = False
scene.cycles.max_bounces = 0
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "None"
scene.render.film_transparent = True
scene.render.resolution_x = RES
scene.render.resolution_y = RES
world = bpy.data.worlds.new("World")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[1].default_value = 0.0
scene.world = world

COL = bpy.data.collections.new("Kumo")
scene.collection.children.link(COL)

LIGHT_DIR = Vector((-0.55, -0.62, 0.58)).normalized()  # key light: upper-left-front


# ------------------------------------------------------------------ materials
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


M = {
    "body": toon_material("Kumo_Body", PAL["mid"], spots=11.0),
    "torso": toon_material("Kumo_Torso", PAL["mid"], spots=3.2, belly=(0.68, 0.98, -0.08, -0.05)),
    "small": toon_material("Kumo_SmallParts", PAL["mid"]),
    "head": toon_material("Kumo_Head", PAL["mid"], spots=8.0),
    "crest": toon_material("Kumo_Crest", PAL["dark"], shade=0.80, light=1.22),
    "lid": toon_material("Kumo_Lid", PAL["mid"], shade=0.78),
    "iris": iris_material(),
    "pupil": flat_material("Kumo_Pupil", PAL["pupil"]),
    "pupilring": flat_material("Kumo_PupilRing", "#E7961F"),
    "white": flat_material("Kumo_Highlight", "#FFFFFF"),
    "line": flat_material("Kumo_Line", PAL["outline"]),
    "mouth": flat_material("Kumo_MouthInside", PAL["mouth"]),
    "tongue": flat_material("Kumo_Tongue", PAL["tongue"]),
}


# ------------------------------------------------------------------ mesh helpers
def link(ob, parent=None):
    COL.objects.link(ob)
    if parent:
        ob.parent = parent
    return ob


def flat(me, mat):
    for p in me.polygons:
        p.use_smooth = False
    me.materials.append(mat)


def hull(name, pts, mat, mirror=True, parent=None):
    """Faceted convex hull (flat shaded) of the given points; mirrored across X."""
    if mirror:
        pts = list(pts) + [(-x, y, z) for (x, y, z) in pts if abs(x) > 1e-6]
    bm = bmesh.new()
    for p in pts:
        bm.verts.new(p)
    bmesh.ops.convex_hull(bm, input=bm.verts)
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(3), verts=bm.verts, edges=bm.edges)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    flat(me, mat)
    return link(bpy.data.objects.new(name, me), parent)


def lowpoly(name, kind, mat, loc=(0, 0, 0), scale=(1, 1, 1), rot=(0, 0, 0), seg=8, rings=6, parent=None, smooth=False):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    if kind == "sphere":
        bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=1.0)
    elif kind == "ico":
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)
    elif kind == "cube":
        bmesh.ops.create_cube(bm, size=2.0)
    bm.to_mesh(me)
    bm.free()
    flat(me, mat)
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    ob.location = loc
    ob.scale = scale
    ob.rotation_euler = rot
    return link(ob, parent)


def tube(name, pts, radii, mat, sides=6, cap=True, parent=None):
    """Low-poly tube along a polyline with per-point radius (limbs, fingers, tail)."""
    bm = bmesh.new()
    rings = []
    n = len(pts)
    pts = [Vector(p) for p in pts]
    prev_side = None
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        if prev_side is None:
            ref = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((0, -1, 0))
            side = t.cross(ref).normalized()
        else:
            side = (prev_side - t * prev_side.dot(t)).normalized()
        prev_side = side
        up = t.cross(side).normalized()
        rings.append([bm.verts.new(p + (side * math.cos(2 * math.pi * k / sides) + up * math.sin(2 * math.pi * k / sides)) * radii[i])
                      for k in range(sides)])
    for i in range(n - 1):
        for k in range(sides):
            bm.faces.new((rings[i][k], rings[i][(k + 1) % sides], rings[i + 1][(k + 1) % sides], rings[i + 1][k]))
    if cap:
        tip = bm.verts.new(pts[-1] + (pts[-1] - pts[-2]).normalized() * radii[-1] * 0.8)
        for k in range(sides):
            bm.faces.new((rings[-1][k], rings[-1][(k + 1) % sides], tip))
        base = bm.verts.new(pts[0] - (pts[1] - pts[0]).normalized() * radii[0] * 0.5)
        for k in range(sides):
            bm.faces.new((rings[0][(k + 1) % sides], rings[0][k], base))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    flat(me, mat)
    return link(bpy.data.objects.new(name, me), parent)


def on_face(ob, offset):
    """Project a face detail (mouth) onto the head surface along Y."""
    sw = ob.modifiers.new("onFace", "SHRINKWRAP")
    sw.target = head
    sw.wrap_method = "PROJECT"
    sw.use_project_y = True
    sw.use_negative_direction = True
    sw.use_positive_direction = True
    sw.offset = offset
    return ob


# ------------------------------------------------------------------ head (faceted polyhedron)
# Rings measured on the reference silhouettes (front half-width w, side front yf / back yb).
HEAD_RINGS = [
    # z,    w,    yf,    yb
    (1.58, 0.47, -0.46, 0.50),
    (1.38, 0.55, -0.50, 0.61),
    (1.17, 0.555, -0.50, 0.59),
    (1.04, 0.47, -0.43, 0.50),
    (0.955, 0.24, -0.20, 0.30),
]
HEAD_PTS = []
for z, w, yf, yb in HEAD_RINGS:
    # flat front and back planes (no centre bulge) keep the head boxy and faceted
    HEAD_PTS += [(w * 0.80, yf, z), (w, yf * 0.62, z), (w, yb * 0.45, z), (w * 0.74, yb, z)]
# short symmetrical snout + upper-lip ledge (mouth sits under it)
HEAD_PTS += [(0.0, -0.585, 1.20), (0.16, -0.56, 1.19), (0.28, -0.52, 1.12), (0.0, -0.565, 1.11), (0.20, -0.53, 1.10)]
# the crest is part of the same polyhedron: a pyramid on top of the skull with a V
# running down between the eyes and a ridge down the back of the head.
CREST_PTS = [
    (0.0, -0.01, 1.965),                         # crest tip = 1.96 H
    (0.0, -0.475, 1.535),                        # V point between the eyes
    (0.21, -0.275, 1.775),                       # widest point of the front diamond
    (0.17, 0.22, 1.79),                          # top ridge, back
    (0.12, 0.56, 1.43), (0.0, 0.625, 1.22),      # occipital ridge down the back of the head
]
head = hull("Kumo_Head", HEAD_PTS + CREST_PTS, M["head"])
DECALS = bpy.data.collections.new("Kumo_Decals")  # painted-on shapes (no outline)
scene.collection.children.link(DECALS)


def decal(name, outline, axis, mat, offset=0.004, n=48):
    """Dark-green patch conforming to the faceted head: a fine grid clipped to a 2D
    outline, projected onto the head along `axis` ('Y+', 'Y-' or 'Z-')."""
    us = [p[0] for p in outline]
    vs = [p[1] for p in outline]
    u0, u1, v0, v1 = min(us), max(us), min(vs), max(vs)

    def inside(u, v):
        c = False
        for i in range(len(outline)):
            (a1, b1), (a2, b2) = outline[i], outline[i - 1]
            if (b1 > v) != (b2 > v) and u < (a2 - a1) * (v - b1) / (b2 - b1) + a1:
                c = not c
        return c

    def to3(u, v):
        return {"Y+": (u, -1.5, v), "Y-": (u, 1.5, v), "Z-": (u, v, 2.6)}[axis]

    bm = bmesh.new()
    verts = {}
    for i in range(n):
        for j in range(n):
            cu = u0 + (u1 - u0) * (i + 0.5) / n
            cv = v0 + (v1 - v0) * (j + 0.5) / n
            if not inside(cu, cv):
                continue
            q = []
            for k in ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)):
                if k not in verts:
                    verts[k] = bm.verts.new(to3(u0 + (u1 - u0) * k[0] / n, v0 + (v1 - v0) * k[1] / n))
                q.append(verts[k])
            bm.faces.new(q)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    flat(me, mat)
    ob = bpy.data.objects.new(name, me)
    DECALS.objects.link(ob)
    sw = ob.modifiers.new("onHead", "SHRINKWRAP")
    sw.target = head
    sw.wrap_method = "PROJECT"
    sw.use_project_y = axis.startswith("Y")
    sw.use_project_z = axis.startswith("Z")
    sw.use_negative_direction = axis in ("Y-", "Z-")
    sw.use_positive_direction = axis == "Y+"
    sw.offset = offset
    # bake the projection and drop any cell that missed the head
    dg = bpy.context.evaluated_depsgraph_get()
    baked = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    ob.modifiers.clear()
    old = ob.data
    ob.data = baked
    bpy.data.meshes.remove(old)
    bm = bmesh.new()
    bm.from_mesh(baked)
    far = [v for v in bm.verts if abs(v.co.y) > 1.2 or v.co.z > 2.2]
    bmesh.ops.delete(bm, geom=far, context="VERTS")
    bm.to_mesh(baked)
    bm.free()
    for poly in baked.polygons:
        poly.use_smooth = False
    return ob


# front diamond: tip -> widest at z 1.775 -> V between the eyes
decal("Kumo_Crest_Front", [(0.0, 1.97), (0.205, 1.775), (0.0, 1.53), (-0.205, 1.775)], "Y+", M["crest"], n=140)
# occipital ridge down the back of the head
decal("Kumo_Crest_Back", [(0.0, 1.97), (0.16, 1.62), (0.0, 1.20), (-0.16, 1.62)], "Y-", M["crest"], n=140)

# eyes ------------------------------------------------------------
EYE = {}
EYE_R = (0.185, 0.09, 0.222)  # eyeball radii (x, depth, z): 29 % of head width, tall oval
for side in (-1, 1):
    tag = "R" if side < 0 else "L"  # character's right eye is at -X
    rig = bpy.data.objects.new(f"Kumo_EyeRig_{tag}", None)
    link(rig)
    # seat the eye on the faceted face: find the head surface in front of the eye centre
    hit, loc, _n, _i = head.ray_cast(Vector((0.30 * side, -2.0, 1.31)), Vector((0, 1, 0)))
    rig.location = (0.30 * side, (loc.y if hit else -0.5) + 0.04, 1.31)
    rig.rotation_euler = (0, 0, math.radians(18 * side))  # eyes face front-outward
    ball = lowpoly(f"Kumo_Eye_{tag}", "sphere", M["iris"], scale=EYE_R, seg=28, rings=18, parent=rig, smooth=True)
    piv = bpy.data.objects.new(f"Kumo_PupilRig_{tag}", None)
    link(piv, rig)
    ring = lowpoly(f"Kumo_PupilRing_{tag}", "sphere", M["pupilring"], scale=(0.078, 0.012, 0.132), seg=20, rings=10, parent=piv, smooth=True)
    pup = lowpoly(f"Kumo_Pupil_{tag}", "sphere", M["pupil"], loc=(0, -0.004, 0), scale=(0.068, 0.012, 0.122), seg=20, rings=10, parent=piv, smooth=True)
    lowpoly(f"Kumo_Highlight_{tag}", "sphere", M["white"], loc=(0.022, -0.012, 0.055), scale=(0.019, 0.006, 0.019), seg=10, rings=6, parent=piv, smooth=True)
    lowpoly(f"Kumo_Highlight2_{tag}", "sphere", M["white"], loc=(-0.028, -0.012, -0.07), scale=(0.008, 0.004, 0.008), seg=8, rings=5, parent=piv, smooth=True)
    lids = []
    for which in ("Upper", "Lower"):
        lid = link(bpy.data.objects.new(f"Kumo_Lid{which}_{tag}", bpy.data.meshes.new(f"lid{which}{tag}")), rig)
        lid.data.materials.append(M["lid"])
        lids.append(lid)
    brow = tube(f"Kumo_Brow_{tag}", [(-0.12, 0, 0), (0, 0, 0.012), (0.12, 0, 0)], [0.02, 0.026, 0.018], M["crest"], sides=5, parent=rig)
    EYE[tag] = dict(rig=rig, pupil=piv, upper=lids[0], lower=lids[1], brow=brow, side=side)

# nostrils
for side in (-1, 1):
    lowpoly(f"Kumo_Nostril_{'R' if side < 0 else 'L'}", "sphere", M["line"], loc=(0.06 * side, -0.578, 1.17), scale=(0.017, 0.012, 0.011))


def mouth_curve(name, pts2d, width=0.0075):
    ob = tube(name, [(x, -0.62, z) for x, z in pts2d], [width] * len(pts2d), M["line"], sides=5)
    return on_face(ob, 0.012)


def mouth_open(name, outline2d, tongue=True):
    """Open mouth painted on the face (fine grid conforming to the facets) + outline."""
    inside_ = decal(name, outline2d, "Y+", M["mouth"], offset=0.008, n=60)
    parts = [inside_, mouth_curve(name + "_Edge", outline2d + [outline2d[0]], 0.008)]
    if tongue:
        # tongue = the lower part of the mouth opening, cut by a gently arched line
        zmin = min(p[1] for p in outline2d)
        zcut = zmin + 0.045
        low = [p for p in outline2d if p[1] < zcut]
        tg = low + [(low[0][0], zcut)]
        parts.append(decal(name + "_Tongue", tg, "Y+", M["tongue"], offset=0.010, n=40))
    return parts


def arc(x0, x1, zc, sag, n=11, wave=0.0):
    return [(x0 + (x1 - x0) * i / (n - 1), zc - sag * math.sin(math.pi * i / (n - 1)) + wave * math.sin(2 * math.pi * i / (n - 1)))
            for i in range(n)]


def smile_shape(w, top, depth, n=12):
    up = arc(-w, w, top, 0.004, n)
    lo = [(w - 2 * w * (k + 1) / (n + 1), top - depth * math.sin(math.pi * (k + 1) / (n + 1))) for k in range(n)]
    return up + lo


MZ = 1.085  # mouth line height (reference)
MOUTHS = {
    "neutral": [mouth_curve("Kumo_Mouth_neutral", arc(-0.30, 0.30, MZ, -0.010))],
    "curious": [mouth_curve("Kumo_Mouth_curious", [(x, z + 0.07 * (x + 0.28) ** 2 - 0.01) for x, z in arc(-0.28, 0.28, MZ, 0.012)])],
    "surprised": mouth_open("Kumo_Mouth_surprised", [(0.055 * math.cos(a), MZ - 0.045 + 0.065 * math.sin(a)) for a in [2 * math.pi * k / 24 for k in range(24)]], tongue=False),
    "happy": mouth_open("Kumo_Mouth_happy", smile_shape(0.25, MZ + 0.005, 0.10)),
    "confused": [mouth_curve("Kumo_Mouth_confused", arc(-0.24, 0.24, MZ - 0.005, 0.0, 15, wave=0.016))],
    "suspicious": [mouth_curve("Kumo_Mouth_suspicious", [(x, z + 0.11 * (x + 0.24) ** 2 - 0.015) for x, z in arc(-0.24, 0.27, MZ, 0.0)])],
    "excited": mouth_open("Kumo_Mouth_excited", smile_shape(0.29, MZ + 0.01, 0.14)),
    "thoughtful": [mouth_curve("Kumo_Mouth_thoughtful", arc(0.03, 0.19, MZ - 0.01, -0.012, 7))],
}

# ------------------------------------------------------------------ body
torso = lowpoly("Kumo_Torso", "sphere", M["torso"], loc=(0, 0.0, 0.64), scale=(0.265, 0.19, 0.33), seg=10, rings=7)
# no visible neck: the torso top tucks under the jaw

for side in (-1, 1):
    tag = "R" if side < 0 else "L"
    s = side
    tube(f"Kumo_Arm_{tag}", [(0.20 * s, -0.01, 0.88), (0.30 * s, -0.02, 0.74), (0.37 * s, -0.03, 0.60), (0.41 * s, -0.045, 0.49)],
         [0.066, 0.06, 0.056, 0.052], M["body"], sides=6)
    # hand: palm + 3 fingers + opposable thumb
    palm = Vector((0.425 * s, -0.05, 0.45))
    lowpoly(f"Kumo_Palm_{tag}", "ico", M["small"], loc=palm, scale=(0.08, 0.06, 0.07))
    for k, ang in enumerate((-15, 0, 15)):
        a = math.radians(ang)
        d = Vector((math.sin(a) * s * 0.7 + 0.12 * s, -0.22, -math.cos(a))).normalized()
        p0 = palm + Vector((0.04 * math.sin(a) * s, -0.012, -0.04))
        tube(f"Kumo_Finger{k}_{tag}", [p0, p0 + d * 0.08, p0 + d * 0.135], [0.036, 0.033, 0.036], M["small"], sides=6)
    t0 = palm + Vector((-0.035 * s, -0.025, -0.008))
    td = Vector((-0.6 * s, -0.55, -0.58)).normalized()
    tube(f"Kumo_Thumb_{tag}", [t0, t0 + td * 0.065, t0 + td * 0.105], [0.032, 0.029, 0.032], M["small"], sides=6)
    # leg (thick, slightly splayed)
    tube(f"Kumo_Leg_{tag}", [(0.12 * s, 0.0, 0.43), (0.15 * s, -0.01, 0.27), (0.18 * s, 0.0, 0.12), (0.19 * s, 0.0, 0.07)],
         [0.095, 0.088, 0.08, 0.078], M["body"], sides=7)
    # foot: broad base + three forward toes, turned slightly outward
    fr = math.radians(-12 * s)
    foot = bpy.data.objects.new(f"Kumo_FootRig_{tag}", None)
    link(foot)
    foot.location = (0.215 * s, -0.02, 0.0)
    foot.rotation_euler = (0, 0, fr)
    lowpoly(f"Kumo_Foot_{tag}", "sphere", M["small"], loc=(0, 0.03, 0.05), scale=(0.13, 0.15, 0.065), seg=8, rings=4, parent=foot)
    for k, dx in enumerate((-0.082, 0.0, 0.082)):
        lowpoly(f"Kumo_Toe{k}_{tag}", "sphere", M["small"], loc=(dx, -0.135, 0.045), scale=(0.055, 0.085, 0.05), seg=8, rings=5, parent=foot)

# dorsal spikes: back of the head -> spine -> tail base
for i, z in enumerate((0.95, 0.87, 0.79, 0.71, 0.63, 0.55, 0.47)):
    y = 0.19 + 0.01 * math.sin(i)
    h = 0.07 - i * 0.005
    hull(f"Kumo_Spike{i}", [(0.04, y - 0.015, z - 0.045), (0.04, y - 0.015, z + 0.045), (0.0, y + h, z)], M["crest"])

# tail: thick at the base, out of the lower back toward the character's left and back,
# ending in a spiral of ~1.6 turns. The spiral plane faces front-left so it reads in
# the front, 3/4 and side views (diameter ~0.44 H projected, as on the reference).
U = Vector((1, 1, 0)).normalized()
Zv = Vector((0, 0, 1))
C = Vector((0.60, 0.58, 0.55))
RH0, RV0, R1, TURNS = 0.28, 0.23, 0.04, 1.6
pts, rad = [], []
for p, r in ((Vector((0.0, 0.17, 0.40)), 0.095), (Vector((0.10, 0.30, 0.30)), 0.09), (Vector((0.30, 0.42, 0.30)), 0.085), (Vector((0.48, 0.54, 0.31)), 0.08)):
    pts.append(p)
    rad.append(r)
a0 = math.radians(-90)
N2 = 52
for i in range(1, N2 + 1):
    t = i / N2
    a = a0 + t * TURNS * 2 * math.pi
    k = (1 - t) ** 0.95
    pts.append(C + U * (math.cos(a) * (R1 + (RH0 - R1) * k)) + Zv * (math.sin(a) * (R1 + (RV0 - R1) * k)))
    rad.append(0.078 + (0.022 - 0.078) * t)
tail = tube("Kumo_Tail", pts, rad, M["body"], sides=6)

# ------------------------------------------------------------------ outlines (Freestyle)
scene.render.use_freestyle = True
scene.render.line_thickness_mode = "RELATIVE"
vl = scene.view_layers[0]
vl.use_freestyle = True
fs = vl.freestyle_settings
fs.crease_angle = math.radians(120)
for ls in list(fs.linesets):
    fs.linesets.remove(ls)
ls = fs.linesets.new("Kumo_Outline")
ls.select_by_visibility = True
ls.visibility = "VISIBLE"
ls.select_silhouette = True
ls.select_border = True
ls.select_crease = False
ls.select_contour = True
ls.select_crease = False
ls.select_external_contour = True
ls.select_material_boundary = False
ls.select_by_collection = True
ls.collection = DECALS
ls.collection_negation = "EXCLUSIVE"
lst = ls.linestyle
lst.color = hexrgb(PAL["outline"])[:3]
lst.thickness = 3.0

# ------------------------------------------------------------------ expressions
EXPR = {
    # po: pupil offset (x, z), ps: pupil scale, lt/lb: share of the eye covered by the
    # upper/lower lid, tilt: slant of the upper lid (inner corner lower),
    # brow: (inner, outer) raise of the brow ridge; absent = no ridge (reference neutral face)
    "neutral":    dict(po=(0, 0), ps=1.0),
    "curious":    dict(po=(0.03, 0.03), ps=1.05, browR=(0.0, 0.0), browL=(0.035, 0.06)),
    "surprised":  dict(po=(0, 0), ps=0.6, brow=(0.06, 0.05)),
    "happy":      dict(po=(0, 0.015), ps=1.0, lb=0.27, brow=(0.02, 0.02)),
    "confused":   dict(po=(-0.03, 0.03), ps=1.0, ltR=0.32, browL=(0.06, 0.03), browR=(-0.025, -0.01)),
    "suspicious": dict(po=(0.05, -0.01), ps=0.95, lt=0.46, lb=0.14, tilt=-0.12, brow=(-0.03, 0.01)),
    "excited":    dict(po=(0, 0.012), ps=1.2, brow=(0.06, 0.07)),
    "thoughtful": dict(po=(-0.035, 0.05), ps=1.0, lt=0.34, browL=(0.035, 0.015), browR=(0.0, 0.0)),
}


def lid_mesh(ob, frac, upper, tilt=0.0, side=1):
    """Flat 2.5D eyelid in front of the eye: the part of the eye ellipse above (upper)
    or below (lower) a gently curved lid line. frac = share of the eye height covered."""
    me = ob.data
    me.clear_geometry()
    if frac <= 0:
        ob.hide_render = ob.hide_viewport = True
        return
    ob.hide_render = ob.hide_viewport = False
    rx, rz = EYE_R[0] * 1.0, EYE_R[2] * 1.0
    y = -(EYE_R[1] + 0.03)
    xs = [-rx + 2 * rx * i / 60 for i in range(61)]
    top = [rz * math.sqrt(max(0.0, 1 - (x / rx) ** 2)) for x in xs]
    if upper:
        line = [rz - 2 * rz * frac - 0.025 * (1 - (x / rx) ** 2) + tilt * x * side for x in xs]
        keep = [(x, t, l) for x, t, l in zip(xs, top, line) if t > l]
        poly = [(x, t) for x, t, _ in keep] + [(x, max(l, -t)) for x, t, l in reversed(keep)]
    else:
        line = [-rz + 2 * rz * frac + 0.03 * (1 - (x / rx) ** 2) for x in xs]
        keep = [(x, t, l) for x, t, l in zip(xs, top, line) if -t < l]
        poly = [(x, -t) for x, t, _ in keep] + [(x, min(l, t)) for x, t, l in reversed(keep)]
    bm = bmesh.new()
    vs = [bm.verts.new((px, y, pz)) for px, pz in poly]
    bm.faces.new(vs)
    bm.to_mesh(me)
    bm.free()


def set_expression(name):
    e = EXPR[name]
    for tag, ed in EYE.items():
        s = ed["side"]
        piv = ed["pupil"]
        # pupils sit toward the nose, as on the reference
        piv.location = Vector((-0.034 * s + e["po"][0], -EYE_R[1] - 0.004, -0.004 + e["po"][1]))
        piv.scale = (e["ps"],) * 3
        lid_mesh(ed["upper"], e.get("lt" + tag, e.get("lt", 0.0)), True, e.get("tilt", 0.0), s)
        lid_mesh(ed["lower"], e.get("lb", 0.0), False)
        b = e.get("brow" + tag, e.get("brow"))
        br = ed["brow"]
        br.hide_render = br.hide_viewport = b is None
        if b is not None:
            bi, bo = b  # inner (toward the nose) / outer raise
            br.location = Vector((0, -0.035, 0.225 + (bi + bo) / 2))
            br.rotation_euler = (0, math.atan2(bo - bi, 0.24) * s, 0)
    for k, objs in MOUTHS.items():
        for o in objs:
            o.hide_render = o.hide_viewport = k != name


set_expression("neutral")

# ------------------------------------------------------------------ cameras
def camera(name, azimuth_deg, ortho=2.45, target=(0.06, 0, 1.0)):
    cam = bpy.data.cameras.new(name)
    cam.type = "ORTHO"
    cam.ortho_scale = ortho
    ob = bpy.data.objects.new(name, cam)
    scene.collection.objects.link(ob)
    a = math.radians(azimuth_deg)
    d = 10
    tgt = Vector(target)
    ob.location = tgt + Vector((math.sin(a) * d, -math.cos(a) * d, 0))
    dirv = tgt - ob.location
    ob.rotation_euler = dirv.to_track_quat("-Z", "Y").to_euler()
    return ob


VIEWS = {
    "front": camera("Cam_Front", 0),
    "three-quarter": camera("Cam_ThreeQuarter", -45),  # turned to the viewer's right
    "side": camera("Cam_Side", -90),                    # profile facing right
    "back": camera("Cam_Back", 180),
}
FACE_CAM = camera("Cam_Face", 0, ortho=1.32, target=(0, 0, 1.40))
scene.camera = VIEWS["front"]

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "kumo_toon.blend"))
print("saved", os.path.join(OUT, "kumo_toon.blend"))

if DO_RENDER:
    os.makedirs(os.path.join(OUT, "renders"), exist_ok=True)
    jobs = []
    for v, cam in VIEWS.items():
        jobs.append((f"view-{v}", cam, "neutral", RES))
    for e in EXPR:
        jobs.append((f"expr-{e}", FACE_CAM, e, int(RES * 0.6)))
    for name, cam, ex, res in jobs:
        if ONLY and ONLY not in name:
            continue
        set_expression(ex)
        scene.camera = cam
        scene.render.resolution_x = scene.render.resolution_y = res
        scene.render.filepath = os.path.join(OUT, "renders", name + ".png")
        bpy.ops.render.render(write_still=True)
        print("rendered", name)
    set_expression("neutral")
    scene.camera = VIEWS["front"]
    scene.render.resolution_x = scene.render.resolution_y = RES
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "kumo_toon.blend"))
