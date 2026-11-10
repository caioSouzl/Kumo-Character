"""Rodin-style pipeline in Blender, step 5: skeleton, weights, A-pose, blink, test poses.

    python kumo_rig.py [--res 900]          (bpy; run from kumo-3d-rodin/ after quad_retopo_bake.py)

Input  kumo_quad.blend (Kumo_Quad: all-quad mesh, baked texture, toon + outline modifiers).
Output kumo_rigged.blend, export/kumo_rigged.glb + .fbx, renders/rig-*.png, rig-report.json.

1. Joints measured on the mesh (body axis, arm and leg centre lines, tail centre line traced
   by geodesic distance from the tail base).
2. Armature "Kumo_Rig" (character faces -Y): root, hips, spine, chest, neck, head,
   shoulder/upper_arm/forearm/hand .L/.R, thigh/shin/foot .L/.R, tail_01..tail_10.
3. Automatic (bone heat) weights.
4. D3 A-pose: upper arms rotated to ~45 deg below horizontal, legs slightly apart; applied as the
   new rest pose. The reference arms-down pose is kept as action "Pose_Apresentacao".
5. Eyelids (Kumo_Lid_L/R): thin skin-coloured caps fitted over each painted eye (projected on
   the head), weighted to the head; shape keys Blink_L / Blink_R close them.
6. Test poses rendered (rest A-pose 4 views, presentation pose, wave, step, head turn, tail
   curl, blink) with simple deformation metrics (flipped / collapsed faces).
"""
import json
import math
import os
import sys

import bpy  # noqa: E402
import bmesh  # noqa: E402
from mathutils import Euler, Matrix, Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
RES = int(argv[argv.index("--res") + 1]) if "--res" in argv else 900

bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT, "kumo_quad.blend"))
scene = bpy.context.scene
body = bpy.data.objects["Kumo_Quad"]
body.name = "Kumo"
src = bpy.data.objects.get("Kumo_Rodin_Source")
if src:
    bpy.data.objects.remove(src)
me = body.data
V = [v.co.copy() for v in me.vertices]
report = {}


def activate(ob, *others):
    bpy.ops.object.mode_set(mode="OBJECT") if bpy.context.object and bpy.context.object.mode != "OBJECT" else None
    bpy.ops.object.select_all(action="DESELECT")
    for o in others:
        o.select_set(True)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob


def centroid(pts):
    return sum(pts, Vector()) / len(pts) if pts else None


def median(vals):
    s = sorted(vals)
    return s[len(s) // 2]


# ---------------------------------------------------------------- 1. measure
by = median([p.y for p in V if abs(p.x) < 0.15 and 0.5 < p.z < 0.85 and p.y < 0.15])   # body axis (y)
hy = median([p.y for p in V if 1.1 < p.z < 1.5])                                        # head axis (y)


def torso_half_width(z):
    pts = [p for p in V if abs(p.z - z) < 0.025 and p.y < by + 0.25]
    xs = sorted(abs(p.x) for p in pts)
    prev = 0.0
    for x in xs:                                    # first gap = end of the torso
        if x - prev > 0.03 and prev > 0.08:
            return prev
        prev = x
    return prev


def limb_centre(z, side, x_min):
    pts = [p for p in V if abs(p.z - z) < 0.025 and p.x * side > x_min and p.y < by + 0.25]
    return centroid(pts)


# arms: outside the torso between z 0.32 and 0.70
arm = {}
for side, tag in ((1, "L"), (-1, "R")):
    # below z 0.56 the arm is separated from the torso by a gap at |x| ~ 0.21-0.30
    line = []
    for z in (0.54, 0.48, 0.42, 0.36):
        c = limb_centre(z, side, 0.245)
        if c:
            line.append(c)
    elbow, wrist = line[0], line[-1]
    hand_pts = [p for p in V if p.x * side > 0.245 and 0.24 < p.z < wrist.z and p.y < by + 0.25]
    hc = centroid(hand_pts)
    hand_tip = Vector((hc.x, hc.y, min(p.z for p in hand_pts)))
    arm[tag] = dict(shoulder=Vector((0.25 * side, by, 0.74)), elbow=elbow, wrist=wrist, tip=hand_tip)
    print("arm", tag, [tuple(round(c, 3) for c in arm[tag][k]) for k in ("shoulder", "elbow", "wrist", "tip")])

# legs
leg = {}
for side, tag in ((1, "L"), (-1, "R")):
    ank = centroid([p for p in V if p.x * side > 0.03 and 0.07 < p.z < 0.12 and p.y < by + 0.2])
    knee = centroid([p for p in V if p.x * side > 0.03 and 0.17 < p.z < 0.21 and p.y < by + 0.2])
    toe = [p for p in V if p.x * side > 0.03 and p.z < 0.05]
    toe_front = min(p.y for p in toe)
    leg[tag] = dict(hip=Vector((knee.x * 0.85, by, 0.38)), knee=knee, ankle=ank,
                    toe=Vector((ank.x, toe_front + 0.03, 0.02)))

# tail: vertices behind the body, traced from the base by mesh distance
adj = {i: [] for i in range(len(V))}
for e in me.edges:
    a, b = e.vertices
    d = (V[a] - V[b]).length
    adj[a].append((b, d))
    adj[b].append((a, d))
tail_ids = {i for i, p in enumerate(V) if p.y > by + 0.17 and p.z < 0.75}
base_ids = [i for i in tail_ids if V[i].z > 0.25 and V[i].y < by + 0.26]
import heapq  # noqa: E402
dist = {i: 0.0 for i in base_ids}
heap = [(0.0, i) for i in base_ids]
while heap:
    d, i = heapq.heappop(heap)
    if d > dist.get(i, 1e9):
        continue
    for j, w in adj[i]:
        if j in tail_ids and d + w < dist.get(j, 1e9):
            dist[j] = d + w
            heapq.heappush(heap, (d + w, j))
L_tail = max(dist.values())
N_TAIL = 10
tail_pts = [centroid([V[i] for i, d in dist.items() if L_tail * k / N_TAIL <= d < L_tail * (k + 1) / N_TAIL])
            for k in range(N_TAIL)]
tail_base = Vector((0.0, by + 0.14, centroid([V[i] for i in base_ids]).z))
tail_chain = [tail_base] + [p for p in tail_pts if p is not None]
report["measures"] = dict(body_y=round(by, 3), head_y=round(hy, 3), tail_length=round(L_tail, 3))

# ---------------------------------------------------------------- 2. armature
arm_data = bpy.data.armatures.new("Kumo_Rig")
rig = bpy.data.objects.new("Kumo_Rig", arm_data)
scene.collection.objects.link(rig)
activate(rig)
bpy.ops.object.mode_set(mode="EDIT")
eb = arm_data.edit_bones


def bone(name, head, tail, parent=None, deform=True, connect=False):
    b = eb.new(name)
    b.head, b.tail = Vector(head), Vector(tail)
    b.use_deform = deform
    if parent:
        b.parent = eb[parent]
        b.use_connect = connect
    return b


bone("root", (0, by, 0), (0, by + 0.25, 0), deform=False)
bone("hips", (0, by, 0.36), (0, by, 0.55), "root")
bone("spine", (0, by, 0.55), (0, by, 0.72), "hips", connect=True)
bone("chest", (0, by, 0.72), (0, by, 0.88), "spine", connect=True)
bone("neck", (0, by, 0.88), (0, hy, 0.98), "chest", connect=True)
bone("head", (0, hy, 0.98), (0, hy, 1.85), "neck", connect=True)
for tag in ("L", "R"):
    a = arm[tag]
    bone(f"shoulder.{tag}", (0.06 * (1 if tag == "L" else -1), by, 0.80), a["shoulder"], "chest")
    bone(f"upper_arm.{tag}", a["shoulder"], a["elbow"], f"shoulder.{tag}", connect=True)
    bone(f"forearm.{tag}", a["elbow"], a["wrist"], f"upper_arm.{tag}", connect=True)
    bone(f"hand.{tag}", a["wrist"], a["tip"], f"forearm.{tag}", connect=True)
    lg = leg[tag]
    bone(f"thigh.{tag}", lg["hip"], lg["knee"], "hips")
    bone(f"shin.{tag}", lg["knee"], lg["ankle"], f"thigh.{tag}", connect=True)
    bone(f"foot.{tag}", lg["ankle"], lg["toe"], f"shin.{tag}", connect=True)
prev = "hips"
for k in range(len(tail_chain) - 1):
    nm = f"tail_{k + 1:02d}"
    bone(nm, tail_chain[k], tail_chain[k + 1], prev, connect=k > 0)
    prev = nm
for b in eb:                                         # consistent bone rolls
    b.align_roll(Vector((0, -1, 0)) if abs(b.vector.normalized().y) < 0.9 else Vector((0, 0, 1)))
bpy.ops.object.mode_set(mode="OBJECT")
report["bones"] = len(arm_data.bones)

# ---------------------------------------------------------------- 3. automatic weights
for m in list(body.modifiers):                       # outline stack goes after the armature
    m.show_viewport = m.show_render = False
activate(body, rig)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.parent_set(type="ARMATURE_AUTO")
mods = body.modifiers
arm_mod = next(m for m in mods if m.type == "ARMATURE")
while mods.find(arm_mod.name) > 0:
    activate(body)
    bpy.ops.object.modifier_move_up(modifier=arm_mod.name)
unweighted = sum(1 for v in me.vertices if not any(g.weight > 1e-3 for g in v.groups
                                                     if body.vertex_groups[g.group].name in arm_data.bones))
report["unweighted_vertices"] = unweighted


def pose(spec):
    for pb in rig.pose.bones:
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = spec.get(pb.name, (0, 0, 0))
    bpy.context.view_layer.update()


def arm_angle(tag):
    b = rig.pose.bones[f"upper_arm.{tag}"]
    d = (rig.matrix_world @ b.tail - rig.matrix_world @ b.head).normalized()
    return math.degrees(math.atan2(d.z, abs(d.x)))


# ---------------------------------------------------------------- 4. A-pose as rest (D3)
rest_angle = arm_angle("L")
target = -45.0
lift = math.radians(target - rest_angle)              # positive = raise toward horizontal
a_pose = {}
for tag, s in (("L", 1), ("R", -1)):
    # rotate around the world Y axis (front-back) in the bone's local frame
    pb = rig.pose.bones[f"upper_arm.{tag}"]
    world_rot = Matrix.Rotation(-lift * s, 3, "Y")   # +Y rotation lowers the left arm
    local = (pb.bone.matrix_local.to_3x3().inverted() @ world_rot @ pb.bone.matrix_local.to_3x3()).to_euler()
    a_pose[f"upper_arm.{tag}"] = tuple(local)
    pb2 = rig.pose.bones[f"thigh.{tag}"]
    world_rot2 = Matrix.Rotation(-math.radians(4) * s, 3, "Y")
    a_pose[f"thigh.{tag}"] = tuple((pb2.bone.matrix_local.to_3x3().inverted() @ world_rot2 @ pb2.bone.matrix_local.to_3x3()).to_euler())
# store the presentation (reference) pose = inverse of the A-pose offsets
pres = {k: tuple(Euler(v).to_matrix().inverted().to_euler()) for k, v in a_pose.items()}
pose(a_pose)
activate(body)
for m in list(body.modifiers):
    if m.type == "ARMATURE":
        bpy.ops.object.modifier_apply(modifier=m.name)
        break
activate(rig)
bpy.ops.object.mode_set(mode="POSE")
bpy.ops.pose.armature_apply(selected=False)
bpy.ops.object.mode_set(mode="OBJECT")
new_mod = body.modifiers.new("Armature", "ARMATURE")
new_mod.object = rig
while body.modifiers.find(new_mod.name) > 0:
    activate(body)
    bpy.ops.object.modifier_move_up(modifier=new_mod.name)
for m in body.modifiers:
    m.show_viewport = m.show_render = True
pose({})
report["arm_angle_before"] = round(rest_angle, 1)
report["arm_angle_rest"] = round(arm_angle("L"), 1)

act = bpy.data.actions.new("Pose_Apresentacao")
rig.animation_data_create()
rig.animation_data.action = act
pose(pres)
for k in pres:
    rig.pose.bones[k].keyframe_insert("rotation_euler", frame=1)
rig.animation_data.action = None
act.use_fake_user = True
pose({})

# ---------------------------------------------------------------- 5. eyelids + blink
cut = body.vertex_groups["outline_cut"].index
eye_pts = {1: [], -1: []}
for v in me.vertices:
    if any(g.group == cut and g.weight > 0.5 for g in v.groups) and v.co.z > 1.0:
        eye_pts[1 if v.co.x > 0 else -1].append(v.co.copy())
bm_head = bmesh.new()
bm_head.from_mesh(me)
bvh = BVHTree.FromBMesh(bm_head)
img = bpy.data.images.get("kumo_quad_diffuse")
lid_mat = bpy.data.materials.new("Kumo_Lid")
lid_mat.use_nodes = True
lnt = lid_mat.node_tree
for n in list(lnt.nodes):
    lnt.nodes.remove(n)
l_out = lnt.nodes.new("ShaderNodeOutputMaterial")
l_em = lnt.nodes.new("ShaderNodeEmission")
l_em.inputs[0].default_value = (0.045, 0.30, 0.075, 1)       # head green (linear), sampled visually
lnt.links.new(l_em.outputs[0], l_out.inputs[0])
lash = bpy.data.materials.new("Kumo_Lash")
lash.use_nodes = True
lsn = lash.node_tree
for n in list(lsn.nodes):
    lsn.nodes.remove(n)
s_out = lsn.nodes.new("ShaderNodeOutputMaterial")
s_em = lsn.nodes.new("ShaderNodeEmission")
s_em.inputs[0].default_value = (0.10, 0.045, 0.03, 1)
lsn.links.new(s_em.outputs[0], s_out.inputs[0])
lids = {}
px = list(img.pixels) if img else None
TEXN = img.size[0] if img else 0
uvl = me.uv_layers.active.data


def skin_colour(cx, cz, rx, rz):
    """Average baked texture colour of the skin ring just outside the eye."""
    acc, n = Vector((0, 0, 0)), 0
    for poly in me.polygons:
        c = poly.center
        d = ((c.x - cx) / rx) ** 2 + ((c.z - cz) / rz) ** 2
        if 1.3 < d < 2.2 and c.y < hy:
            for li in poly.loop_indices:
                u, v = uvl[li].uv
                i = (min(TEXN - 1, int(v * TEXN)) * TEXN + min(TEXN - 1, int(u * TEXN))) * 4
                acc += Vector(px[i:i + 3])
                n += 1
    if not n:
        return (0.045, 0.30, 0.075, 1)
    lin = lambda c: ((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92   # texture pixels are sRGB
    return tuple(lin(c) for c in acc / n) + (1.0,)


def emission_mat(name, rgba):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    t = m.node_tree
    for n_ in list(t.nodes):
        t.nodes.remove(n_)
    o_ = t.nodes.new("ShaderNodeOutputMaterial")
    e_ = t.nodes.new("ShaderNodeEmission")
    e_.inputs[0].default_value = rgba
    t.links.new(e_.outputs[0], o_.inputs[0])
    return m


for s, tag in ((1, "L"), (-1, "R")):
    pts = eye_pts[s]
    x0, x1 = min(p.x for p in pts), max(p.x for p in pts)
    z0, z1 = min(p.z for p in pts), max(p.z for p in pts)
    cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
    rx, rz = (x1 - x0) / 2 * 0.98, (z1 - z0) / 2 * 1.02
    skin = emission_mat(f"Kumo_Lid_{tag}", skin_colour(cx, cz, rx, rz))

    def on_head(x, z, off):
        loc, n, _i, _d = bvh.ray_cast(Vector((x, -3.0, z)), Vector((0, 1, 0)))
        if loc is None or abs(loc.x - x) > 1e-3:
            loc, n, _i, _d = bvh.find_nearest(Vector((x, -0.6, z)))
        return loc + n.normalized() * off

    NU, NV = 24, 8
    MEET = -0.25                        # meeting line (fraction of rz below the centre): slight smile
    bm = bmesh.new()
    rows_open, rows_closed, mats = [], [], []
    for part in ("upper", "lower"):
        for j in range(NV + 1):
            t = j / NV
            ro, rc = [], []
            for i in range(NU + 1):
                u = -1 + 2 * i / NU
                h = math.sqrt(max(0.0, 1 - u * u))
                edge = cz + (rz * h if part == "upper" else -rz * 1.02 * h)
                meet = cz + rz * (MEET - 0.12 * h)      # curved closed line
                rc.append((cx + rx * u, edge + (meet - edge) * t))
                ro.append((cx + rx * u, edge + (0.004 if part == "upper" else -0.004) * t))
            rows_open.append(ro)
            rows_closed.append(rc)
    vs = [[bm.verts.new(on_head(x, z, 0.012)) for x, z in row] for row in rows_open]
    for part_i in range(2):
        base = part_i * (NV + 1)
        for j in range(NV):
            for i in range(NU):
                a_, b_ = vs[base + j], vs[base + j + 1]
                f = bm.faces.new((a_[i], a_[i + 1], b_[i + 1], b_[i]))
                f.material_index = 1 if (part_i == 0 and j == NV - 1) else 0   # lash on the upper lid margin
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    lme = bpy.data.meshes.new(f"lid{tag}")
    bm.to_mesh(lme)
    bm.free()
    lme.materials.append(skin)
    lme.materials.append(lash)
    lid = bpy.data.objects.new(f"Kumo_Lid_{tag}", lme)
    scene.collection.objects.link(lid)
    lid.shape_key_add(name="Basis")
    sk = lid.shape_key_add(name=f"Blink_{tag}")
    k = 0
    for row in rows_closed:
        for x, z in row:
            sk.data[k].co = on_head(x, z, 0.03)
            k += 1
    sk.value = 0.0
    lid.parent = rig
    lid.parent_type = "BONE"
    lid.parent_bone = "head"
    lids[tag] = lid
bm_head.free()
# lids must sit in world space exactly where they were built
for lid in lids.values():
    pb = rig.pose.bones["head"]
    lid.matrix_parent_inverse = (rig.matrix_world @ pb.matrix @ Matrix.Translation((0, pb.length, 0))).inverted()

# ---------------------------------------------------------------- 6. test poses + renders
scene.render.resolution_x = scene.render.resolution_y = RES
cams = {c.name: c for c in bpy.data.objects if c.type == "CAMERA"}
rest_faces = None


def face_data():
    dg = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(dg)
    m = ev.to_mesh()
    d = [(p.normal.copy(), p.area) for p in m.polygons[:len(me.polygons)]]
    ev.to_mesh_clear()
    return d


def deg(*a):
    return tuple(math.radians(x) for x in a)


def world_rot(name, axis, angle):
    pb = rig.pose.bones[name]
    r = Matrix.Rotation(math.radians(angle), 3, axis)
    return tuple((pb.bone.matrix_local.to_3x3().inverted() @ r @ pb.bone.matrix_local.to_3x3()).to_euler())


POSES = {
    "rest-apose": ({}, {}),
    "apresentacao": (pres, {}),
    "aceno": ({"upper_arm.L": world_rot("upper_arm.L", "Y", -75), "forearm.L": world_rot("forearm.L", "Y", -45)}, {}),
    "passo": ({"thigh.L": world_rot("thigh.L", "X", -30), "shin.L": world_rot("shin.L", "X", 35),
               "thigh.R": world_rot("thigh.R", "X", 15), "upper_arm.R": world_rot("upper_arm.R", "X", -25),
               "upper_arm.L": world_rot("upper_arm.L", "X", 20)}, {}),
    "cabeca-gira": ({"head": world_rot("head", "Z", 25), "neck": world_rot("neck", "X", 8)}, {}),
    "cauda-enrola": ({f"tail_{k:02d}": world_rot(f"tail_{k:02d}", "X", 6) for k in range(1, N_TAIL + 1)
                      if f"tail_{k:02d}" in rig.pose.bones}, {}),
    "piscada": ({}, {"Blink_L": 1.0, "Blink_R": 1.0}),
    "piscadela": ({}, {"Blink_L": 1.0}),
}
os.makedirs(os.path.join(ROOT, "renders"), exist_ok=True)
metrics = {}
for name, (bones, keys) in POSES.items():
    pose(bones)
    for tag, lid in lids.items():
        lid.data.shape_keys.key_blocks[f"Blink_{tag}"].value = keys.get(f"Blink_{tag}", 0.0)
    bpy.context.view_layer.update()
    cur = face_data()
    if rest_faces is None:
        rest_faces = cur
    metrics[name] = dict(
        flipped=sum(1 for (n0, a0), (n1, a1) in zip(rest_faces, cur) if a0 > 1e-7 and n0.dot(n1) < 0),
        collapsed=sum(1 for (n0, a0), (n1, a1) in zip(rest_faces, cur) if a0 > 1e-7 and a1 / a0 < 0.2))
    views = ("front", "three-quarter", "side", "back") if name == "rest-apose" else ("front", "three-quarter")
    if name in ("piscada", "piscadela"):
        views = ("front",)
    camname = {"front": "Cam_Front", "three-quarter": "Cam_ThreeQuarter", "side": "Cam_Side", "back": "Cam_Back"}
    for v in views:
        cam = cams[camname[v]]
        if name in ("aceno",):
            cam.data.ortho_scale = 2.6
        scene.camera = cam
        scene.render.filepath = os.path.join(ROOT, "renders", f"rig-{name}-{v}.png")
        bpy.ops.render.render(write_still=True)
        cam.data.ortho_scale = 2.25
    print("pose", name, metrics[name])
report["deformation"] = metrics
pose({})
for lid in lids.values():
    for kb in lid.data.shape_keys.key_blocks[1:]:
        kb.value = 0.0
scene.camera = cams["Cam_Front"]

# ---------------------------------------------------------------- export
os.makedirs(os.path.join(ROOT, "export"), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "kumo_rigged.blend"))
outline_mods = [m for m in body.modifiers if m.type in ("SOLIDIFY", "VERTEX_WEIGHT_MIX", "MASK")]
for m in outline_mods:
    m.show_viewport = m.show_render = False
toon = me.materials[0]
pbr = bpy.data.materials.get("Kumo_Quad_PBR")
if pbr:
    me.materials[0] = pbr
bpy.ops.object.select_all(action="DESELECT")
for o in (body, rig, *lids.values()):
    o.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.export_scene.gltf(filepath=os.path.join(ROOT, "export", "kumo_rigged.glb"), use_selection=True,
                          export_format="GLB", export_animations=True)
try:
    bpy.ops.export_scene.fbx(filepath=os.path.join(ROOT, "export", "kumo_rigged.fbx"), use_selection=True,
                             add_leaf_bones=False, bake_anim=False, path_mode="COPY", embed_textures=True)
except Exception as e:  # noqa: BLE001
    report["fbx_error"] = str(e)
with open(os.path.join(ROOT, "rig-report.json"), "w") as fh:
    json.dump(report, fh, indent=1)
print(json.dumps(report))
