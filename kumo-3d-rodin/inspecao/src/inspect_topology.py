"""Read-only topology inspection of the retopologized Kumo mesh (object "Kumo" in kumo_rigged.blend).

    python inspect_topology.py BLEND_COPY OUT_DIR [--res 900]        (bpy)

Never writes the .blend: it is opened from a temporary copy and is NOT saved. All analysis
reads the mesh data (rest pose, without the outline modifiers); renders are made with
separate duplicate objects created in memory only.

Outputs (OUT_DIR):
  topology.json        global + per-region metrics
  wire-<region>.png    enlarged wireframe close-ups with poles marked
                       (blue = 3-edge pole, red = 5-edge pole, magenta = 6+), triangles in yellow
"""
import json
import math
import os
import sys
from collections import Counter

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
import bpy  # noqa: E402
import bmesh  # noqa: E402
from mathutils import Vector  # noqa: E402

BLEND, OUT = argv[0], argv[1]
RES = int(argv[argv.index("--res") + 1]) if "--res" in argv else 900
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=BLEND)
scene = bpy.context.scene
body = bpy.data.objects["Kumo"]
rig = bpy.data.objects["Kumo_Rig"]
me = body.data

# ---------------------------------------------------------------- read-only geometry (rest pose, base mesh)
bm = bmesh.new()
bm.from_mesh(me)                      # base mesh data: no modifiers, rest shape
bm.verts.ensure_lookup_table()
bm.faces.ensure_lookup_table()
bm.normal_update()
P = [v.co.copy() for v in bm.verts]

# dominant bone per vertex (for region masks)
bone_names = {vg.index: vg.name for vg in body.vertex_groups if vg.name in rig.data.bones}
dom = {}
nbones = {}
for v in me.vertices:
    gs = [(g.weight, bone_names[g.group]) for g in v.groups if g.group in bone_names and g.weight > 1e-3]
    nbones[v.index] = len(gs)
    dom[v.index] = max(gs)[1] if gs else None
eye_vg = body.vertex_groups["outline_cut"].index
eye_v = {v.index for v in me.vertices if any(g.group == eye_vg and g.weight > 0.5 for g in v.groups) and v.co.z > 1.0}


def bone_head(name):
    return rig.matrix_world @ rig.data.bones[name].head_local


def bone_tail(name):
    return rig.matrix_world @ rig.data.bones[name].tail_local


# ---------------------------------------------------------------- global checks
def face_quality(f):
    n = len(f.verts)
    q = {}
    if n == 4:
        cs = [v.co for v in f.verts]
        angs = []
        for i in range(4):
            a, b, c = cs[i - 1], cs[i], cs[(i + 1) % 4]
            u, w = (a - b), (c - b)
            if u.length > 1e-9 and w.length > 1e-9:
                angs.append(math.degrees(u.angle(w)))
        q["skew"] = max(abs(x - 90) for x in angs) if angs else 0
        e = [(cs[(i + 1) % 4] - cs[i]).length for i in range(4)]
        q["aspect"] = max(e) / max(1e-9, min(e))
        nrm = f.normal
        c0 = f.calc_center_median()
        q["nonplanar"] = max(abs((c - c0).dot(nrm)) for c in cs) / max(1e-9, max(e))
    return q


degenerate = [f.index for f in bm.faces if f.calc_area() < 1e-8]
zero_edges = [e.index for e in bm.edges if e.calc_length() < 1e-6]
nonmanifold = [e.index for e in bm.edges if not e.is_manifold]
boundary = [e.index for e in bm.edges if e.is_boundary]
loose_v = [v.index for v in bm.verts if not v.link_edges]
inconsistent = 0
for e in bm.edges:
    lf = e.link_faces
    if len(lf) == 2:
        d = []
        for f in lf:
            for lp in f.loops:
                if lp.edge is e:
                    d.append(lp.vert is e.verts[0])
        inconsistent += d[0] == d[1]
vol = sum(f.calc_center_median().dot(f.normal) * f.calc_area() for f in bm.faces) / 3
# faces whose normal points into the body: ray from just outside the face along the normal
# should not hit the mesh again right away when the region is convex -> use centroid test
# per connected neighbourhood: normal vs (face centre - local centroid of neighbours' centres)
inward = 0
for f in bm.faces:
    nb = {g for e in f.edges for g in e.link_faces if g is not f}
    for v in f.verts:
        nb |= set(v.link_faces)
    c = sum((g.calc_center_median() for g in nb), Vector()) / len(nb)
    if f.normal.dot(f.calc_center_median() - c) < -1e-4 and len(nb) > 4:
        inward += 1           # locally concave: not necessarily wrong, reported as a hint only

valence = Counter(len(v.link_edges) for v in bm.verts if not v.is_boundary)
poles = {v.index: len(v.link_edges) for v in bm.verts if not v.is_boundary and len(v.link_edges) != 4}
shapes = Counter(len(f.verts) for f in bm.faces)
fq = [face_quality(f) for f in bm.faces]
dihedral = [math.degrees(e.calc_face_angle(0)) for e in bm.edges if len(e.link_faces) == 2]
smooth = sum(1 for p in me.polygons if p.use_smooth)
max_inf = Counter(nbones.values())


def pct(a, b):
    return round(100 * a / b, 2) if b else 0.0


GLOBAL = dict(
    vertices=len(bm.verts), edges=len(bm.edges), faces=len(bm.faces),
    face_sides=dict(sorted(shapes.items())), quad_pct=pct(shapes.get(4, 0), len(bm.faces)),
    degenerate_faces=len(degenerate), zero_length_edges=len(zero_edges), non_manifold_edges=len(nonmanifold),
    boundary_edges=len(boundary), loose_vertices=len(loose_v), inconsistent_winding_edges=inconsistent,
    signed_volume=round(vol, 4), normals="outward" if vol > 0 else "inward",
    locally_concave_faces_hint=inward,
    vertex_valence=dict(sorted(valence.items())), poles_total=len(poles),
    poles_3=sum(1 for d in poles.values() if d == 3), poles_5=sum(1 for d in poles.values() if d == 5),
    poles_6plus=sum(1 for d in poles.values() if d >= 6),
    quad_skew_deg=dict(mean=round(sum(q["skew"] for q in fq if q) / max(1, sum(1 for q in fq if q)), 2),
                       over_30=sum(1 for q in fq if q and q["skew"] > 30), over_45=sum(1 for q in fq if q and q["skew"] > 45)),
    quad_aspect=dict(over_3=sum(1 for q in fq if q and q["aspect"] > 3), over_5=sum(1 for q in fq if q and q["aspect"] > 5)),
    nonplanar_quads_over_5pct=sum(1 for q in fq if q and q["nonplanar"] > 0.05),
    dihedral_deg=dict(over_60=sum(1 for d in dihedral if d > 60), over_90=sum(1 for d in dihedral if d > 90), max=round(max(dihedral), 1)),
    shading=dict(smooth_faces=smooth, flat_faces=len(me.polygons) - smooth,
                 auto_smooth_or_sharp_edges=sum(1 for e in me.edges if e.use_edge_sharp)),
    bone_influences_per_vertex=dict(sorted(max_inf.items())),
)

# ---------------------------------------------------------------- regions
REG = {}


def region_from_mask(name, ids, centre, axis=None, ring=None, note=""):
    ids = set(ids)
    faces = [f for f in bm.faces if all(v.index in ids for v in f.verts)]
    if not faces:
        REG[name] = dict(note="empty region")
        return
    sh = Counter(len(f.verts) for f in faces)
    rp = {i: poles[i] for i in ids if i in poles}
    q = [face_quality(f) for f in faces]
    q = [x for x in q if x]
    out = dict(vertices=len(ids), faces=len(faces), face_sides=dict(sorted(sh.items())),
               quad_pct=pct(sh.get(4, 0), len(faces)),
               poles_3=sum(1 for d in rp.values() if d == 3), poles_5=sum(1 for d in rp.values() if d == 5),
               poles_6plus=sum(1 for d in rp.values() if d >= 6),
               skew_mean=round(sum(x["skew"] for x in q) / max(1, len(q)), 1),
               skew_over_30=sum(1 for x in q if x["skew"] > 30),
               aspect_over_3=sum(1 for x in q if x["aspect"] > 3),
               degenerate=sum(1 for f in faces if f.calc_area() < 1e-8),
               note=note)
    edges = {e for f in faces for e in f.edges}
    if axis is not None:
        # edge flow vs the bone axis: aligned (along / around the limb) vs diagonal
        ax = axis.normalized()
        along = around = diag = 0
        for e in edges:
            d = (e.verts[1].co - e.verts[0].co)
            if d.length < 1e-9:
                continue
            c = abs(d.normalized().dot(ax))
            if c > 0.8:
                along += 1
            elif c < 0.35:
                around += 1
            else:
                diag += 1
        tot = along + around + diag
        out["edge_flow"] = dict(along_bone_pct=pct(along, tot), around_bone_pct=pct(around, tot), diagonal_pct=pct(diag, tot))
        # resolution of the cross-section loop at the joint: edges crossed by the plane
        n_cross = sum(1 for e in bm.edges if ((e.verts[0].co - centre).dot(ax)) * ((e.verts[1].co - centre).dot(ax)) < 0
                      and (e.verts[0].co - centre).length < 0.14)
        out["cross_section_edges"] = n_cross
    if ring is not None:
        # concentric loop check around a feature (eye / mouth): radial vs tangential edges in the
        # local face plane
        cx, nrm = ring
        rad = tan = diag = 0
        for e in edges:
            m = (e.verts[0].co + e.verts[1].co) / 2
            r = m - cx
            r -= nrm * r.dot(nrm)
            d = e.verts[1].co - e.verts[0].co
            d -= nrm * d.dot(nrm)
            if r.length < 1e-6 or d.length < 1e-9:
                continue
            c = abs(r.normalized().dot(d.normalized()))
            if c > 0.8:
                rad += 1
            elif c < 0.35:
                tan += 1
            else:
                diag += 1
        tot = rad + tan + diag
        out["edge_flow"] = dict(radial_pct=pct(rad, tot), concentric_pct=pct(tan, tot), diagonal_pct=pct(diag, tot))
    out["pole_positions"] = [[round(c, 3) for c in P[i]] + [d] for i, d in list(rp.items())[:40]]
    REG[name] = out


def near(c, r):
    return [i for i, p in enumerate(P) if (p - c).length < r]


# eyes
for s, tag in ((1, "L"), (-1, "R")):
    ev = [i for i in eye_v if P[i].x * s > 0]
    c = sum((P[i] for i in ev), Vector()) / len(ev)
    rad = max((P[i] - c).length for i in ev) * 1.08
    region_from_mask(f"eye_{tag}", [i for i in near(c, rad) if P[i].y < c.y + 0.12], c,
                     ring=(c, Vector((0, -1, 0))), note="eye painted in the texture (no lid geometry in the body mesh)")
    REG[f"eye_{tag}"]["centre"] = [round(x, 3) for x in c]
# mouth (painted line on the lower front of the head)
mc = Vector((0.0, min(p.y for p in P if 1.0 < p.z < 1.12 and abs(p.x) < 0.1) + 0.02, 1.07))
region_from_mask("mouth_snout", [i for i in near(mc, 0.24) if P[i].z > 0.95], mc, ring=(mc, Vector((0, -1, 0))),
                 note="mouth painted in the texture; no mouth opening / lip loops in the mesh")
# neck
region_from_mask("neck", [i for i, p in enumerate(P) if 0.86 < p.z < 1.02 and dom.get(i) in ("neck", "chest", "head")],
                 bone_head("neck"), axis=bone_tail("neck") - bone_head("neck"))
# joints
for tag in ("L", "R"):
    for jn, bn, rad in (("shoulder", "upper_arm", 0.10), ("elbow", "forearm", 0.075), ("wrist", "hand", 0.06),
                        ("hip", "thigh", 0.10), ("knee", "shin", 0.08), ("ankle", "foot", 0.07)):
        b = f"{bn}.{tag}"
        c = bone_head(b)
        parent = rig.data.bones[b].parent
        ax = bone_tail(b) - bone_head(b)
        if parent is not None and jn in ("elbow", "wrist", "knee", "ankle"):
            ax = (bone_tail(b) - bone_head(b)).normalized() + (parent.tail_local - parent.head_local).normalized()
        nearest = min((p - c).length for p in P)
        region_from_mask(f"{jn}_{tag}", near(c, max(rad, nearest + 0.045)), c, axis=ax)
        REG[f"{jn}_{tag}"]["bone_to_surface_dist"] = round(nearest, 3)
# hands / fingers
for tag in ("L", "R"):
    wr = bone_head(f"hand.{tag}")
    hand_w = [i for i in range(len(P)) if dom.get(i) == f"hand.{tag}"]
    ids = [i for i, p in enumerate(P) if p.z < wr.z + 0.01 and (Vector((p.x, p.y, 0)) - Vector((wr.x, wr.y, 0))).length < 0.12 and p.z > 0.2]
    c = sum((P[i] for i in ids), Vector()) / len(ids)
    region_from_mask(f"hand_fingers_{tag}", ids, c, axis=bone_tail(f"hand.{tag}") - bone_head(f"hand.{tag}"))
    # how many separate fingers show up in a cross-section near the tips
    zmin = min(P[i].z for i in ids)
    sl = [i for i in ids if P[i].z < zmin + 0.025]
    comp, seen = 0, set()
    adj = {}
    for e in bm.edges:
        a, b_ = e.verts[0].index, e.verts[1].index
        adj.setdefault(a, []).append(b_)
        adj.setdefault(b_, []).append(a)
    sls = set(sl)
    for i in sl:
        if i in seen:
            continue
        comp += 1
        st = [i]
        seen.add(i)
        while st:
            k = st.pop()
            for j in adj.get(k, []):
                if j in sls and j not in seen:
                    seen.add(j)
                    st.append(j)
    REG[f"hand_fingers_{tag}"]["separate_digit_tips_in_bottom_slice"] = comp
    REG[f"hand_fingers_{tag}"]["vertices_in_hand_geometry"] = len(ids)
    REG[f"hand_fingers_{tag}"]["vertices_dominated_by_hand_bone"] = len(hand_w)
    REG[f"hand_fingers_{tag}"]["hand_bone_length"] = round((bone_tail(f"hand.{tag}") - wr).length, 3)
    # max number of separate digits over several slices below the palm
    best = 0
    for dz in (0.01, 0.02, 0.03, 0.04, 0.05):
        sl = {i for i in ids if zmin + dz - 0.006 < P[i].z < zmin + dz + 0.006}
        seen2, comp2 = set(), 0
        for i in sl:
            if i in seen2:
                continue
            comp2 += 1
            st = [i]
            seen2.add(i)
            while st:
                k = st.pop()
                for j in adj.get(k, []):
                    if j in sl and j not in seen2:
                        seen2.add(j)
                        st.append(j)
        best = max(best, comp2)
    REG[f"hand_fingers_{tag}"]["max_separate_digits_in_slices"] = best
# feet / toes
for tag in ("L", "R"):
    ids = [i for i in range(len(P)) if dom.get(i) == f"foot.{tag}"]
    c = sum((P[i] for i in ids), Vector()) / len(ids)
    region_from_mask(f"foot_toes_{tag}", ids, c, axis=bone_tail(f"foot.{tag}") - bone_head(f"foot.{tag}"))
# tail
tail_bones = sorted(b.name for b in rig.data.bones if b.name.startswith("tail_"))
ids = [i for i in range(len(P)) if dom.get(i) in tail_bones]
region_from_mask("tail", ids, bone_head(tail_bones[0]), axis=bone_tail(tail_bones[0]) - bone_head(tail_bones[0]))
flows = []
for tb in tail_bones:
    tids = {i for i in range(len(P)) if dom.get(i) == tb}
    ax = (bone_tail(tb) - bone_head(tb)).normalized()
    al = ar = dg = 0
    for e in bm.edges:
        if e.verts[0].index in tids and e.verts[1].index in tids:
            d = (e.verts[1].co - e.verts[0].co)
            if d.length < 1e-9:
                continue
            c_ = abs(d.normalized().dot(ax))
            al += c_ > 0.8
            ar += c_ < 0.35
            dg += 0.35 <= c_ <= 0.8
    flows.append(dict(bone=tb, vertices=len(tids), diagonal_pct=pct(dg, al + ar + dg)))
REG["tail"]["per_segment"] = flows

report = dict(file=os.path.basename(BLEND), object="Kumo", read_only=True, global_=GLOBAL, regions=REG)
with open(os.path.join(OUT, "topology.json"), "w") as fh:
    json.dump(report, fh, indent=1)
print(json.dumps(GLOBAL))

# ---------------------------------------------------------------- enlarged wireframe renders (duplicates only)
for o in scene.objects:
    o.hide_render = True
wire_src = bpy.data.meshes.new("inspect_copy")
bm.to_mesh(wire_src)                                 # copy of the base mesh (rest pose)
surf = bpy.data.objects.new("Inspect_Surface", wire_src)
scene.collection.objects.link(surf)
clay = bpy.data.materials.new("insp_clay")
clay.use_nodes = True
nt = clay.node_tree
for n in list(nt.nodes):
    nt.nodes.remove(n)
o_ = nt.nodes.new("ShaderNodeOutputMaterial")
dif = nt.nodes.new("ShaderNodeBsdfDiffuse")
dif.inputs[0].default_value = (0.62, 0.66, 0.62, 1)
nt.links.new(dif.outputs[0], o_.inputs[0])
surf.data.materials.clear()
surf.data.materials.append(clay)
for p in surf.data.polygons:
    p.material_index = 0
    p.use_smooth = False
wire = bpy.data.objects.new("Inspect_Wire", wire_src.copy())
scene.collection.objects.link(wire)
wm = wire.modifiers.new("w", "WIREFRAME")
wm.thickness = 0.0022
wm.use_replace = True
wm.use_even_offset = True
wm.offset = 1.0
ink = bpy.data.materials.new("insp_ink")
ink.use_nodes = True
it = ink.node_tree
for n in list(it.nodes):
    it.nodes.remove(n)
io = it.nodes.new("ShaderNodeOutputMaterial")
ie = it.nodes.new("ShaderNodeEmission")
ie.inputs[0].default_value = (0.02, 0.02, 0.025, 1)
it.links.new(ie.outputs[0], io.inputs[0])
wire.data.materials.clear()
wire.data.materials.append(ink)


def emat(name, rgb):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    t = m.node_tree
    for n in list(t.nodes):
        t.nodes.remove(n)
    a = t.nodes.new("ShaderNodeOutputMaterial")
    b = t.nodes.new("ShaderNodeEmission")
    b.inputs[0].default_value = rgb + (1,)
    b.inputs[1].default_value = 1.5
    t.links.new(b.outputs[0], a.inputs[0])
    return m


M3, M5, M6, MT = emat("p3", (0.05, 0.25, 1.0)), emat("p5", (1.0, 0.08, 0.05)), emat("p6", (1.0, 0.0, 0.9)), emat("tri", (1.0, 0.85, 0.0))
mk = bmesh.new()
for i, d in poles.items():
    r = 0.006
    res = bmesh.ops.create_icosphere(mk, subdivisions=1, radius=r)
    for v in res["verts"]:
        v.co += P[i] + bm.verts[i].normal * 0.003
    mi = 0 if d == 3 else 1 if d == 5 else 2
    for f in {f for v in res["verts"] for f in v.link_faces}:
        f.material_index = mi
for f in bm.faces:
    if len(f.verts) == 3:
        res = bmesh.ops.create_icosphere(mk, subdivisions=1, radius=0.005)
        c = f.calc_center_median() + f.normal * 0.003
        for v in res["verts"]:
            v.co += c
        for g in {g for v in res["verts"] for g in v.link_faces}:
            g.material_index = 3
mme = bpy.data.meshes.new("inspect_markers")
mk.to_mesh(mme)
mk.free()
for m in (M3, M5, M6, MT):
    mme.materials.append(m)
marks = bpy.data.objects.new("Inspect_Markers", mme)
scene.collection.objects.link(marks)
sun = bpy.data.objects.new("insp_sun", bpy.data.lights.new("insp_sun", "SUN"))
sun.data.energy = 3.0
sun.rotation_euler = (math.radians(50), 0, math.radians(-30))
scene.collection.objects.link(sun)
sun.hide_render = True                     # uniform ambient light only: no hard shadows on the wire
w = bpy.data.worlds.new("insp_w")
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[1].default_value = 1.6
scene.world = w
scene.render.engine = "CYCLES"
scene.cycles.samples = 8
scene.cycles.device = "CPU"
scene.render.film_transparent = False
scene.view_settings.view_transform = "Standard"
scene.render.use_freestyle = False
scene.render.resolution_x = scene.render.resolution_y = RES
cam = bpy.data.objects.new("insp_cam", bpy.data.cameras.new("insp_cam"))
cam.data.type = "ORTHO"
scene.collection.objects.link(cam)
scene.camera = cam


def shot(name, target, direction, size):
    tgt = Vector(target)
    d = Vector(direction).normalized()
    cam.location = tgt - d * 5
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam.data.ortho_scale = size
    scene.render.filepath = os.path.join(OUT, f"wire-{name}.png")
    bpy.ops.render.render(write_still=True)
    print("shot", name)


eL = Vector(REG["eye_L"]["centre"])
SHOTS = [
    ("00-corpo-frente", (0, 0, 0.98), (0, 1, 0), 2.2),
    ("01-corpo-perfil", (0, 0, 0.98), (1, 0, 0), 2.2),
    ("02-olhos", (0, eL.y, eL.z), (0, 1, 0), 0.95),
    ("03-olho-esquerdo", tuple(eL), (0, 1, 0), 0.45),
    ("04-boca-focinho", tuple(mc), (0, 1, 0.25), 0.6),
    ("05-pescoco", tuple(bone_head("neck")), (1, 0.3, 0), 0.6),
    ("06-ombro-esquerdo", tuple(bone_head("upper_arm.L")), (0.3, 1, -0.2), 0.4),
    ("07-cotovelo-esquerdo", tuple(bone_head("forearm.L")), (0.2, 1, 0), 0.3),
    ("08-mao-dedos-esquerda", tuple(bone_head("hand.L")), (0.2, 1, 0.1), 0.25),
    ("09-mao-dedos-esquerda-lado", tuple(bone_head("hand.L")), (-1, 0, 0.1), 0.25),
    ("10-quadril", tuple(bone_head("thigh.L")), (0, 1, 0), 0.6),
    ("11-joelho-tornozelo-esquerdo", tuple((bone_head("shin.L") + bone_head("foot.L")) / 2), (0.2, 1, 0), 0.4),
    ("12-pe-dedos-esquerdo", tuple(bone_head("foot.L")), (0.3, 0.6, 1.0), 0.35),
    ("13-cauda", tuple(bone_head(tail_bones[len(tail_bones) // 2])), (1, 0, 0), 1.1),
    ("14-base-da-cauda", tuple(bone_head(tail_bones[0])), (0.6, -1, 0.3), 0.45),
]
for s_ in SHOTS:
    shot(*s_)
bm.free()
# NOTE: the blend is intentionally NOT saved.
