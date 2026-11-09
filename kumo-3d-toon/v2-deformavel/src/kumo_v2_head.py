"""Kumo v2 — F1.2: deformable head, second visual pass (2026-11-09).

F1.2 = F1.0 (frozen in kumo_v2_head_f1_0.py) + face measured on reference 01:
  inverted-V mouth line, larger pupils set toward the nose, one highlight, dark upper-lid
  band, slanted nostril slits, two on-surface lid-fold rings, smoother jaw weights,
  outline = external contour + marked feature lines only.

F1.0 docstring:

    python kumo_v2_head.py --out DIR [--render] [--res 900]

Construction (nothing here touches base/ or the current kumo_toon.blend):
 1. Rebuild the approved P1/P2 polyhedral head (same 25 named vertices, same crest faces).
 2. Simple (non-smoothing) subdivision x2: every triangle -> 3 quads, every quad -> 4 quads.
    All new vertices stay ON the original facet planes, so silhouette and flat cel shading
    are identical at rest; facet borders stay real edges (marked sharp).
 3. Eye openings: the faces over each eye are replaced by concentric quad rings
    (orbit rim -> lid fold -> lid margin -> socket lining). The lids are part of the head mesh.
 4. Mouth: the faces over the mouth line are replaced by quad rings
    (outer lip -> lip -> lip margin -> mouth bag). Upper/lower margins meet at the mouth line.
 5. Nostrils: two small insets on the snout.
 6. Rig for tests (D4 hybrid): bones Head, Jaw, Eye.L, Eye.R; shape keys Blink_L, Blink_R.
    Eyeballs are separate rigid meshes (they rotate) with their own pupil meshes (D5),
    parented to the eye bones.
 7. With --render: rest + deformation-test renders, wireframes, a P1 comparison and metrics.
"""
import json
import math
import os
import sys

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy  # noqa: E402
import bmesh  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402
from kumo_common import (CREST_KEYS, HEAD_VERTS, PAL, flat_material, hexrgb,  # noqa: E402
                         iris_material, toon_material)

OUT = os.path.abspath(argv[argv.index("--out") + 1]) if "--out" in argv else os.getcwd()
DO_RENDER = "--render" in argv
RES = int(argv[argv.index("--res") + 1]) if "--res" in argv else 900
os.makedirs(OUT, exist_ok=True)

# ------------------------------------------------------------------ parameters (approved values)
EYE_X, EYE_Z, EYE_ROT, EYE_SEAT = 0.30, 1.31, 18.0, 0.04   # from kumo_toon.py (P1 state)
EYE_R = (0.185, 0.09, 0.222)                               # eyeball radii (x, depth, z)
# measured on reference 01 (front view, 1 H = head height), F1.2
MOUTH_HALF_W = 0.255         # mouth corners at x = +-0.255
MZ_C, MZ_E = 1.097, 1.046    # mouth line: centre height and corner height (inverted V)
MZ = MZ_C                    # hinge/bag reference height


def mouth_z(x):
    t = min(1.0, abs(x) / MOUTH_HALF_W)
    return MZ_C - (MZ_C - MZ_E) * t ** 1.15


NOSTRILS = [(-0.065, 1.148, -35.0), (0.065, 1.148, 35.0)]   # x, z, slant (deg)
PUPIL_DX, PUPIL_DZ = -0.073, -0.010     # pupil centre offset toward the nose (eye local, x * side)
PUPIL_R, RING_R = (0.067, 0.139), (0.083, 0.155)
HIGHLIGHT = (0.054, 0.074, 0.025)       # offset from pupil centre (same +x for both eyes), radius
LID_SCALE = (1.08, 1.55, 1.08)       # lid shell around the eyeball (deep enough to clear pupil + highlights)
LID_OPEN_F = 0.86                    # lid margin opening, share of the eyeball outline
BLINK_Z = -0.45                      # where the lids meet (normalised, eye local): mostly the upper lid travels

# ------------------------------------------------------------------ scene
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 16
scene.cycles.use_denoising = False
scene.cycles.max_bounces = 0
scene.view_settings.view_transform = "Standard"
scene.render.film_transparent = True
world = bpy.data.worlds.new("World")
scene.world = world
COL = bpy.data.collections.new("Kumo_v2_Head")
scene.collection.children.link(COL)


def link(ob):
    COL.objects.link(ob)
    return ob


M = {
    "head": toon_material("Kumo_Head", PAL["mid"], spots=8.0),
    "crest": toon_material("Kumo_Crest", PAL["dark"], shade=0.80, light=1.22),
    "mouth": flat_material("Kumo_MouthInside", PAL["mouth"]),
    "line": flat_material("Kumo_Line", PAL["outline"]),
    "iris": iris_material(),
    "pupil": flat_material("Kumo_Pupil", PAL["pupil"]),
    "pupilring": flat_material("Kumo_PupilRing", "#E7961F"),
    "white": flat_material("Kumo_Highlight", "#FFFFFF"),
    "nostril": flat_material("Kumo_Nostril", PAL["pupil"]),
}
MAT_ORDER = ["head", "crest", "mouth", "line", "nostril"]
MI = {k: i for i, k in enumerate(MAT_ORDER)}


# ------------------------------------------------------------------ 1. approved P1/P2 polyhedron
def p1_bmesh():
    pts = []
    for (x, y, z) in HEAD_VERTS.values():
        pts.append((x, y, z))
        if abs(x) > 1e-6:
            pts.append((-x, y, z))
    bm = bmesh.new()
    for p in pts:
        bm.verts.new(p)
    res = bmesh.ops.convex_hull(bm, input=bm.verts)
    bmesh.ops.delete(bm, geom=[v for v in res["geom_interior"] if isinstance(v, bmesh.types.BMVert)], context="VERTS")
    crest = [Vector(HEAD_VERTS[k]) for k in CREST_KEYS] + [Vector((-HEAD_VERTS[k][0],) + HEAD_VERTS[k][1:]) for k in CREST_KEYS]
    is_crest = lambda v: any((v.co - c).length < 1e-5 for c in crest)
    for f in bm.faces:
        f.material_index = MI["crest"] if all(is_crest(v) for v in f.verts) else MI["head"]
    bmesh.ops.join_triangles(bm, faces=bm.faces, angle_face_threshold=math.radians(1.0), angle_shape_threshold=math.radians(180),
                             cmp_seam=False, cmp_sharp=False, cmp_uvs=False, cmp_vcols=False, cmp_materials=True)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def mesh_object(name, bm):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    for k in MAT_ORDER:
        me.materials.append(M[k])
    for p in me.polygons:
        p.use_smooth = False
    return link(bpy.data.objects.new(name, me))


p1 = p1_bmesh()
P1_BVH = BVHTree.FromBMesh(p1)
P1_FACE_PLANES = [(f.normal.copy(), f.calc_center_median().copy()) for f in p1.faces]
ref_obj = mesh_object("P1_Reference_Head", p1.copy())  # untouched copy, for comparison only
ref_obj.hide_render = True

# ------------------------------------------------------------------ 2. planar quad subdivision
tmp = mesh_object("tmp", p1)
for e in tmp.data.edges:
    e.use_edge_sharp = True          # facet borders = original edges
sub = tmp.modifiers.new("simple", "SUBSURF")
sub.subdivision_type = "SIMPLE"
sub.levels = sub.render_levels = 2
dg = bpy.context.evaluated_depsgraph_get()
me_sub = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
bpy.data.objects.remove(tmp)
bm = bmesh.new()
bm.from_mesh(me_sub)
bpy.data.meshes.remove(me_sub)
for f in bm.faces:
    f.tag = False


def surface_y(x, z):
    """Front surface of the approved head at (x, z), by ray cast on the reference copy."""
    loc, _n, _i, _d = P1_BVH.ray_cast(Vector((x, -3.0, z)), Vector((0, 1, 0)))
    return loc.y if loc is not None else None


# ------------------------------------------------------------------ eye frames
EYES = {}
for side, tag in ((-1, "R"), (1, "L")):     # character's right eye is at -X
    sy = surface_y(EYE_X * side, EYE_Z)
    c = Vector((EYE_X * side, sy + EYE_SEAT, EYE_Z))
    rot = Matrix.Rotation(math.radians(EYE_ROT * side), 4, "Z")
    EYES[tag] = dict(center=c, rot=rot, inv=rot.inverted(), side=side)


def to_eye(tag, p):
    e = EYES[tag]
    return e["inv"] @ (Vector(p) - e["center"])


def from_eye(tag, lp):
    e = EYES[tag]
    return e["center"] + e["rot"] @ Vector(lp)


def boundary_loop(bm, edges):
    """Order the boundary verts of a hole into one loop."""
    adj = {}
    for e in edges:
        a, b = e.verts
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)
    start = next(iter(adj))
    loop, prev, cur = [start], None, start
    while True:
        nxt = [v for v in adj[cur] if v is not prev]
        if not nxt or nxt[0] is start:
            break
        prev, cur = cur, nxt[0]
        loop.append(cur)
    return loop



def ordered_ring(bnd_edges, to2d):
    """Walk the hole border in its real order (never re-sorted, so quads cannot cross),
    orient it counter-clockwise in the 2D frame `to2d`, and give every border vertex a
    monotonic angle spread by arc length, starting at the vertex closest to angle 0."""
    loop = boundary_loop(None, bnd_edges)
    pts = [to2d(v.co) for v in loop]
    area = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts)))
    if area < 0:
        loop.reverse()
        pts.reverse()
    k0 = min(range(len(loop)), key=lambda i: abs(math.atan2(pts[i][1], pts[i][0])))
    loop, pts = loop[k0:] + loop[:k0], pts[k0:] + pts[:k0]
    seg = [math.dist(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))]
    total = sum(seg)
    th0 = math.atan2(pts[0][1], pts[0][0])
    angles, acc = [], 0.0
    for i in range(len(loop)):
        angles.append(th0 + 2 * math.pi * acc / total)
        acc += seg[i]
    return loop, angles


def cut_hole(bm, inside):
    faces = [f for f in bm.faces if not f.tag and inside(f)]
    region_edges = {e for f in faces for e in f.edges}
    bmesh.ops.delete(bm, geom=faces, context="FACES_ONLY")
    loose_edges = [e for e in region_edges if e.is_valid and not e.link_faces]
    bmesh.ops.delete(bm, geom=loose_edges, context="EDGES")
    loose_verts = [v for v in bm.verts if not v.link_edges]
    bmesh.ops.delete(bm, geom=loose_verts, context="VERTS")
    # boundary of THIS hole only: edges of the removed faces that survived as borders
    return [e for e in region_edges if e.is_valid and e.is_boundary]


def ring_faces(bm, r0, r1, mat):
    n = len(r0)
    out = []
    for i in range(n):
        f = bm.faces.new((r0[i], r0[(i + 1) % n], r1[(i + 1) % n], r1[i]))
        f.material_index = mat
        f.tag = True                      # protected: later holes never cut through new rings
        out.append(f)
    return out


# ------------------------------------------------------------------ 3. eye openings with lid rings
LID_RINGS = {}
for tag in ("R", "L"):
    fwd = EYES[tag]["rot"].to_3x3() @ Vector((0, -1, 0))

    def inside_eye(f, tag=tag, fwd=fwd):
        lp = to_eye(tag, f.calc_center_median())
        return (f.normal.dot(fwd) > 0.3 and lp.y < 0.25 and lp.z > -EYE_R[2] * 0.95 and
                (lp.x / (EYE_R[0] * 1.22)) ** 2 + (lp.z / (EYE_R[2] * 1.12)) ** 2 < 1.0)
    bnd_edges = cut_hole(bm, inside_eye)
    loop, angles = ordered_ring(bnd_edges, lambda co, tag=tag: (to_eye(tag, co).x / EYE_R[0], to_eye(tag, co).z / EYE_R[2]))
    rx, ry, rz = EYE_R[0] * LID_SCALE[0], EYE_R[1] * LID_SCALE[1], EYE_R[2] * LID_SCALE[2]
    # rings: orbit border -> fold -> lid1 -> lid2 -> margin -> socket lining
    # lid1/lid2/margin lie ON the lid ellipsoid, so the lid stays a curved cap over the eyeball
    ell = lambda f, th: Vector((f * rx * math.cos(th), -ry * math.sqrt(max(0.0, 1 - f * f)), f * rz * math.sin(th)))
    into = (EYES[tag]["rot"].to_3x3() @ Vector((0, 1, 0))).normalized()

    def on_surface(lp, tag=tag, into=into):
        w = from_eye(tag, lp)
        loc, _n, _i, _d = P1_BVH.ray_cast(w - into * 1.0, into)
        return loc if loc is not None else w

    RING_KEYS = ("fold1", "fold2", "lid1", "lid2", "margin", "socket")
    rings = {k: [] for k in RING_KEYS}
    for v, th in zip(loop, angles):
        b_local = to_eye(tag, v.co)
        l1 = ell(0.985, th)
        # two fold rings lying ON the approved facet planes (no visible crease at rest)
        rings["fold1"].append(bm.verts.new(on_surface(b_local.lerp(l1, 0.35))))
        rings["fold2"].append(bm.verts.new(on_surface(b_local.lerp(l1, 0.70))))
        rings["lid1"].append(bm.verts.new(from_eye(tag, l1)))
        rings["lid2"].append(bm.verts.new(from_eye(tag, ell(0.93, th))))
        rings["margin"].append(bm.verts.new(from_eye(tag, ell(LID_OPEN_F, th))))
        rings["socket"].append(bm.verts.new(from_eye(tag, Vector((1.02 * EYE_R[0] * math.cos(th), 0.25 * EYE_R[1], 1.02 * EYE_R[2] * math.sin(th))))))
    prev = loop
    for k in RING_KEYS:
        fs_ = ring_faces(bm, prev, rings[k], MI["head"])
        if k == "margin":                    # dark upper-lid band (lash line), top of the eye
            for f_, th in zip(fs_, angles):
                if math.sin(th) > 0.30:
                    f_.material_index = MI["line"]
        prev = rings[k]
    LID_RINGS[tag] = rings

# ------------------------------------------------------------------ 4. mouth rings
def inside_mouth(f):
    p = f.calc_center_median()
    return f.normal.y < -0.3 and p.y < -0.3 and (p.x / 0.31) ** 2 + ((p.z - mouth_z(p.x)) / 0.05) ** 2 < 1.0


mb_edges = cut_hole(bm, inside_mouth)
mloop, mangles = ordered_ring(mb_edges, lambda co: (co.x / 0.31, (co.z - mouth_z(co.x)) / 0.05))
lip, lmargin, bag = [], [], []
for v, th in zip(mloop, mangles):
    # lip margin: a thin lens along the mouth line (upper and lower margins nearly touch)
    x = MOUTH_HALF_W * math.cos(th)
    z = mouth_z(x) + 0.006 * math.sin(th)
    y = surface_y(x, z) or v.co.y
    m = Vector((x, y + 0.006, z))
    mid = (v.co + m) / 2
    mid.y -= 0.004
    lip.append(bm.verts.new(mid))
    lmargin.append(bm.verts.new(m))
    bag.append(bm.verts.new(Vector((x * 0.75, y + 0.12, mouth_z(x) + 0.035 * math.sin(th)))))
ring_faces(bm, mloop, lip, MI["head"])
ring_faces(bm, lip, lmargin, MI["head"])
ring_faces(bm, lmargin, bag, MI["mouth"])
# close the mouth bag with a fan (hidden inside the head: triangles are acceptable there)
centre = bm.verts.new(Vector((0.0, (sum(b.co.y for b in bag) / len(bag)) + 0.04, MZ - 0.02)))
for i in range(len(bag)):
    f = bm.faces.new((bag[i], bag[(i + 1) % len(bag)], centre))
    f.material_index = MI["mouth"]
MOUTH = dict(margin=lmargin, lip=lip)

# ------------------------------------------------------------------ 5. nostrils
for nx, nz, slant in NOSTRILS:
    target = Vector((nx, surface_y(nx, nz), nz))
    f = min((f for f in bm.faces if f.material_index == MI["head"] and not f.tag),
            key=lambda f: (f.calc_center_median() - target).length)
    bmesh.ops.inset_individual(bm, faces=[f], thickness=0.004, depth=0.0)
    vs = sorted(f.verts, key=lambda v: math.atan2(v.co.z - target.z, v.co.x - target.x))
    a = math.radians(slant)
    for k, v in enumerate(vs):             # slanted slit (rhombus) at the measured spot, pushed in
        t = 2 * math.pi * k / len(vs)
        u, w = 0.024 * math.cos(t), 0.011 * math.sin(t)
        x_, z_ = target.x + u * math.cos(a) - w * math.sin(a), target.z + u * math.sin(a) + w * math.cos(a)
        v.co = Vector((x_, (surface_y(x_, z_) or target.y) + 0.003, z_))
    f.material_index = MI["nostril"]

bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
for e in bm.edges:
    if len(e.link_faces) == 2 and e.calc_face_angle(0) > math.radians(1.0):
        e.smooth = False
RING_CO = {tag: {k: [v.co.copy() for v in vs] for k, vs in LID_RINGS[tag].items()} for tag in LID_RINGS}
MOUTH_CO = {k: [v.co.copy() for v in vs] for k, vs in MOUTH.items()}
head = mesh_object("Kumo_v2_Head", bm)
bm.free()
vid = {}


def vidx(v):
    return v.index


# ------------------------------------------------------------------ 6a. eyeballs + pupils (rigid, D5)
EYEBALL = {}
for tag in ("R", "L"):
    e = EYES[tag]
    me = bpy.data.meshes.new(f"eyeball{tag}")
    b2 = bmesh.new()
    bmesh.ops.create_uvsphere(b2, u_segments=32, v_segments=20, radius=1.0)
    b2.to_mesh(me)
    b2.free()
    me.materials.append(M["iris"])
    for p in me.polygons:
        p.use_smooth = True
    ball = link(bpy.data.objects.new(f"Kumo_v2_Eye_{tag}", me))
    ball.matrix_world = Matrix.Translation(e["center"]) @ e["rot"] @ Matrix.Diagonal(Vector(EYE_R + (1,)))
    parts = []
    # D5: pupil and iris ring are curved caps that hug the eyeball (a flat disc would stand
    # proud of the curvature and poke through a closed lid); highlights sit on the surface
    def cap(name, mat, rx_c, rz_c, grow, dx=0.0):
        pm = bpy.data.meshes.new(name + tag)
        b3 = bmesh.new()
        # polar disc (smooth elliptical edge) in eye-local x/z, lifted onto the unit sphere
        cx = (PUPIL_DX * e["side"] + dx) / EYE_R[0]
        NR, NS = 6, 48
        centre_v = None
        rings_v = []
        for r in range(NR + 1):
            row = []
            for k in range(NS if r else 1):
                t = 2 * math.pi * k / NS
                ux = cx + (r / NR) * (rx_c / EYE_R[0]) * math.cos(t)
                uz = (PUPIL_DZ / EYE_R[2]) + (r / NR) * (rz_c / EYE_R[2]) * math.sin(t)
                uy = -math.sqrt(max(0.0, 1 - ux * ux - uz * uz))
                row.append(b3.verts.new((ux, uy, uz)))
            rings_v.append(row)
        for k in range(NS):
            b3.faces.new((rings_v[0][0], rings_v[1][k], rings_v[1][(k + 1) % NS]))
        for r in range(1, NR):
            for k in range(NS):
                b3.faces.new((rings_v[r][k], rings_v[r + 1][k], rings_v[r + 1][(k + 1) % NS], rings_v[r][(k + 1) % NS]))
        bmesh.ops.recalc_face_normals(b3, faces=b3.faces)
        for f in b3.faces:
            if f.normal.y > 0:
                f.normal_flip()
        b3.to_mesh(pm)
        b3.free()
        pm.materials.append(M[mat])
        for p in pm.polygons:
            p.use_smooth = True
        po = link(bpy.data.objects.new(f"Kumo_v2_{name}_{tag}", pm))
        po.matrix_world = Matrix.Translation(e["center"]) @ e["rot"] @ Matrix.Diagonal(Vector(tuple(r * grow for r in EYE_R) + (1,)))
        return po
    parts.append(cap("PupilRing", "pupilring", RING_R[0], RING_R[1], 1.006))
    parts.append(cap("Pupil", "pupil", PUPIL_R[0], PUPIL_R[1], 1.012))
    for name, loc, sc in (("Highlight", HIGHLIGHT[:2], HIGHLIGHT[2]),):   # reference 01: one highlight
        lx = PUPIL_DX * e["side"] + loc[0]
        lz = PUPIL_DZ + loc[1]
        ly = -EYE_R[1] * math.sqrt(max(0.0, 1 - (lx / EYE_R[0]) ** 2 - (lz / EYE_R[2]) ** 2)) * 1.015
        pm = bpy.data.meshes.new(name + tag)
        b3 = bmesh.new()
        bmesh.ops.create_uvsphere(b3, u_segments=16, v_segments=8, radius=1.0)
        b3.to_mesh(pm)
        b3.free()
        pm.materials.append(M["white"])
        for p in pm.polygons:
            p.use_smooth = True
        po = link(bpy.data.objects.new(f"Kumo_v2_{name}_{tag}", pm))
        po.matrix_world = Matrix.Translation(e["center"]) @ e["rot"] @ Matrix.Translation(Vector((lx, ly, lz))) @ Matrix.Diagonal(Vector((sc, sc * 0.3, sc, 1)))
        parts.append(po)
    EYEBALL[tag] = [ball] + parts

# ------------------------------------------------------------------ 6b. shape keys (blink)
head.shape_key_add(name="Basis", from_mix=False)
for tag in ("L", "R"):
    head.shape_key_add(name=f"Blink_{tag}", from_mix=False).value = 0.0

# BMVerts are gone after to_mesh; resolve ring vertices by position instead.
kd_index = {tuple(round(c, 6) for c in v.co): v.index for v in head.data.vertices}


def idx_of(co):
    return kd_index[tuple(round(c, 6) for c in co)]


RING_IDX = {tag: {k: [idx_of(c) for c in cs] for k, cs in RING_CO[tag].items()} for tag in RING_CO}
MOUTH_IDX = {k: [idx_of(c) for c in cs] for k, cs in MOUTH_CO.items()}

for tag in ("L", "R"):
    sk = head.data.shape_keys.key_blocks[f"Blink_{tag}"]
    rx, ry, rz = EYE_R[0] * LID_SCALE[0], EYE_R[1] * LID_SCALE[1], EYE_R[2] * LID_SCALE[2]
    # each ring travels a share of the way to the meeting line, staying on the lid ellipsoid
    # upper lid sweeps down (all rings travel); lower lid only lifts its margin, so the
    # eyeball's lower edge stays covered
    W_UP = {"margin": 1.0, "lid2": 0.8, "lid1": 0.5}
    W_LO = {"margin": 1.0, "lid2": 0.5, "lid1": 0.15}
    for ring_name in ("margin", "lid2", "lid1"):
        for j, i in enumerate(RING_IDX[tag][ring_name]):
            lp = to_eye(tag, head.data.vertices[i].co)
            n = Vector((lp.x / rx, lp.y / ry, lp.z / rz))
            w = (W_UP if n.z > BLINK_Z else W_LO)[ring_name]
            zt = n.z + (BLINK_Z - n.z) * w
            xt = max(-0.999, min(0.999, n.x))
            yy = -math.sqrt(max(0.0, 1 - xt * xt - zt * zt))
            new = Vector((xt * rx, yy * ry, zt * rz))
            sk.data[i].co = from_eye(tag, new)
    # upper half: the fold rolls onto lid1's rest place (the top edge of the eyeball), so the
    # part of the eyeball that stands proud of the face stays covered while lid1 travels down
    # fold2 rolls onto lid1's rest place, fold1 onto fold2's rest place (two-step roll keeps
    # the fold quads from folding over each other)
    for src, dst in (("fold2", "lid1"), ("fold1", "fold2")):
        for j, i in enumerate(RING_IDX[tag][src]):
            lp = to_eye(tag, head.data.vertices[i].co)
            if lp.z / rz > BLINK_Z:
                tgt = to_eye(tag, head.data.vertices[RING_IDX[tag][dst][j]].co)
                new = lp.lerp(tgt, 0.9)
                new.y = min(new.y, lp.y)
                sk.data[i].co = from_eye(tag, new)

# ------------------------------------------------------------------ 6c. armature (Head, Jaw, Eye.L, Eye.R)
arm_data = bpy.data.armatures.new("Kumo_v2_Rig")
arm = link(bpy.data.objects.new("Kumo_v2_Rig", arm_data))
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="EDIT")
eb = arm_data.edit_bones
b_head = eb.new("Head")
b_head.head, b_head.tail = (0, 0.05, 0.95), (0, 0.05, 1.95)
JAW_HINGE = Vector((0.0, 0.12, 1.135))
b_jaw = eb.new("Jaw")
b_jaw.head, b_jaw.tail = JAW_HINGE, Vector((0.0, -0.40, 1.02))
b_jaw.parent = b_head
for tag in ("L", "R"):
    e = EYES[tag]
    b = eb.new(f"Eye.{tag}")
    b.head = e["center"]
    b.tail = e["center"] + e["rot"] @ Vector((0, -0.25, 0))
    b.parent = b_head
bpy.ops.object.mode_set(mode="OBJECT")

# weights: Jaw = everything below the mouth line at the front, fading toward the hinge
vg_head = head.vertex_groups.new(name="Head")
vg_jaw = head.vertex_groups.new(name="Jaw")
LOWER_LIP = {i for i in MOUTH_IDX["margin"] + MOUTH_IDX["lip"]}
front = side = 1.0
for i, v in enumerate(head.data.vertices):
    p = v.co
    w = 0.0
    mz = mouth_z(p.x)
    if p.z < mz - 0.001:
        t = min(1.0, (mz - p.z) / 0.012)
        depth = t * t * (3 - 2 * t)                     # lower lip and below follow the jaw
        front = min(1.0, max(0.0, (0.35 - p.y) / 0.45))  # fade out toward the back of the jaw
        t = min(1.0, max(0.0, (abs(p.x) - 0.30) / 0.20))
        side = 1.0 - t * t * (3 - 2 * t)                  # fade over the cheeks
        w = depth * front * side
    if v.index in LOWER_LIP and p.z < mz:                # lower lip margin opens fully with the jaw
        w = front * side
    if v.index in MOUTH_IDX["margin"] and p.z >= mz - 0.001:
        w = 0.0
    vg_jaw.add([i], w, "REPLACE")
    vg_head.add([i], 1.0 - w, "REPLACE")
mod = head.modifiers.new("Armature", "ARMATURE")
mod.object = arm
head.parent = arm

for tag in ("L", "R"):
    for ob in EYEBALL[tag]:
        mw = ob.matrix_world.copy()
        ob.parent = arm
        ob.parent_type = "BONE"
        ob.parent_bone = f"Eye.{tag}"
        ob.matrix_world = mw

# ------------------------------------------------------------------ outlines for the review renders (Freestyle;
# the inverted hull is phase F5). Wireframe pass uses edge marks on every head edge.
scene.render.use_freestyle = True
scene.render.line_thickness_mode = "RELATIVE"
vl = scene.view_layers[0]
fs = vl.freestyle_settings
for ls in list(fs.linesets):
    fs.linesets.remove(ls)
ls_out = fs.linesets.new("Outline")
ls_out.select_silhouette = ls_out.select_border = ls_out.select_contour = False
ls_out.select_external_contour = True        # outer silhouette only; feature lines are marked edges
ls_out.select_crease = ls_out.select_material_boundary = False
ls_out.linestyle.color = hexrgb(PAL["outline"])[:3]
ls_out.linestyle.thickness = 3.0
ls_wire = fs.linesets.new("Wire")
ls_wire.select_by_edge_types = True
for k in ("silhouette", "border", "crease", "contour", "external_contour", "material_boundary"):
    setattr(ls_wire, "select_" + k, False)
ls_wire.select_edge_mark = True
ls_wire.linestyle.color = (0.08, 0.08, 0.08)
ls_wire.linestyle.thickness = 1.2
ls_wire.show_render = False
ls_feat = fs.linesets.new("Features")         # eye rim + lip line (marked edges), deform with the mesh
ls_feat.select_by_edge_types = True
for k in ("silhouette", "border", "crease", "contour", "external_contour", "material_boundary"):
    setattr(ls_feat, "select_" + k, False)
ls_feat.select_edge_mark = True
ls_feat.linestyle.color = hexrgb(PAL["outline"])[:3]
ls_feat.linestyle.thickness = 2.2
fe = head.data.attributes.get("freestyle_edge") or head.data.attributes.new("freestyle_edge", "BOOLEAN", "EDGE")
FEATURE_VERTS = set()
for tag in RING_IDX:
    m = RING_IDX[tag]["margin"]
    FEATURE_VERTS |= {tuple(sorted((m[k], m[(k + 1) % len(m)]))) for k in range(len(m))}
mm = MOUTH_IDX["margin"]
FEATURE_VERTS |= {tuple(sorted((mm[k], mm[(k + 1) % len(mm)]))) for k in range(len(mm))}
FEATURE_MARKS = [tuple(sorted(e.vertices)) in FEATURE_VERTS for e in head.data.edges]
fe.data.foreach_set("value", FEATURE_MARKS)

# ------------------------------------------------------------------ cameras
def camera(name, az, ortho=1.45, target=(0.0, 0.0, 1.43)):
    cam = bpy.data.cameras.new(name)
    cam.type = "ORTHO"
    cam.ortho_scale = ortho
    ob = bpy.data.objects.new(name, cam)
    scene.collection.objects.link(ob)
    a = math.radians(az)
    tgt = Vector(target)
    ob.location = tgt + Vector((math.sin(a) * 10, -math.cos(a) * 10, 0))
    ob.rotation_euler = (tgt - ob.location).to_track_quat("-Z", "Y").to_euler()
    return ob


CAMS = {"front": camera("Cam_Front", 0), "three-quarter": camera("Cam_ThreeQuarter", -40),
        "side": camera("Cam_Side", -90), "back": camera("Cam_Back", 180)}
scene.camera = CAMS["front"]
arm.data.display_type = "STICK"

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "kumo_v2_head.blend"))
print("saved", os.path.join(OUT, "kumo_v2_head.blend"))

# ------------------------------------------------------------------ 7. renders + metrics
POSES = {
    "rest": {},
    "blink-L": {"Blink_L": 1.0},
    "blink-R": {"Blink_R": 1.0},
    "blink-both": {"Blink_L": 1.0, "Blink_R": 1.0},
    "half-blink": {"Blink_L": 0.5, "Blink_R": 0.5},
    "jaw-open": {"bone": {"Jaw": (math.radians(15), 0, 0)}},
    "jaw-side": {"bone": {"Jaw": (math.radians(10), 0, math.radians(9))}},
    "eyes-indep": {"bone": {"Eye.L": (0, 0, math.radians(18)), "Eye.R": (math.radians(14), 0, math.radians(-8))}},
}


def apply_pose(spec):
    for kb in head.data.shape_keys.key_blocks[1:]:
        kb.value = spec.get(kb.name, 0.0)
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = spec.get("bone", {}).get(pb.name, (0, 0, 0))
    bpy.context.view_layer.update()


def evaluated_faces():
    dg = bpy.context.evaluated_depsgraph_get()
    ev = head.evaluated_get(dg)
    me = ev.to_mesh()
    data = [(p.normal.copy(), p.area) for p in me.polygons]
    ev.to_mesh_clear()
    return data


def render(path, cam, res, wire=False):
    scene.camera = cam
    scene.render.resolution_x = scene.render.resolution_y = res
    ls_out.show_render = ls_feat.show_render = not wire
    ls_wire.show_render = wire
    head.data.attributes["freestyle_edge"].data.foreach_set("value", [True] * len(head.data.edges) if wire else FEATURE_MARKS)
    vl.material_override = WIRE_MAT if wire else None
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


if DO_RENDER:
    WIRE_MAT = flat_material("Wire_Grey", "#D9D9D6")
    rd = os.path.join(OUT, "renders")
    os.makedirs(rd, exist_ok=True)
    apply_pose({})
    rest = evaluated_faces()
    metrics = {}
    for pose, spec in POSES.items():
        apply_pose(spec)
        cur = evaluated_faces()
        flipped = sum(1 for (n0, a0), (n1, a1) in zip(rest, cur) if a0 > 1e-6 and n0.dot(n1) < 0)
        collapsed = sum(1 for (n0, a0), (n1, a1) in zip(rest, cur) if a0 > 1e-6 and a1 / a0 < 0.15)
        stretched = sum(1 for (n0, a0), (n1, a1) in zip(rest, cur) if a0 > 1e-6 and a1 / a0 > 3.0)
        metrics[pose] = dict(flipped_faces=flipped, collapsed_faces=collapsed, stretched_faces=stretched)
        views = ("front", "three-quarter", "side") if pose != "rest" else tuple(CAMS)
        for v in views:
            render(os.path.join(rd, f"{pose}-{v}.png"), CAMS[v], RES)
        if pose == "rest":
            for v in CAMS:
                render(os.path.join(rd, f"wire-{v}.png"), CAMS[v], RES, wire=True)
        print("pose", pose, metrics[pose])
    # P1 comparison (same cameras, head + eyeballs only, silhouettes)
    apply_pose({})
    ref_obj.hide_render = False
    head.hide_render = True
    for v in CAMS:
        render(os.path.join(rd, f"p1-{v}.png"), CAMS[v], RES)
    head.hide_render = False
    ref_obj.hide_render = True
    with open(os.path.join(OUT, "deformation-metrics.json"), "w") as fh:
        json.dump(metrics, fh, indent=1)
    vl.material_override = None
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "kumo_v2_head.blend"))
