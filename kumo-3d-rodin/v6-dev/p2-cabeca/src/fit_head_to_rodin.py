"""P3 — fit the named head control vertices to the Rodin 3D reference.

    python fit_head_to_rodin.py RODIN.glb OUT.json      (bpy)

1. Import the Rodin GLB (character faces -Y, Z up) and map its HEAD into the approved
   Kumo head frame: Rodin chin..crest tip -> z 0.955..1.965 (approved head height, 1.01 H),
   uniform scale, x centred, y aligned on the skull mid-depth at z 1.45.
2. For every named vertex of HEAD_VERTS (kumo_common), cast a ray from outside the head
   toward the head centre along the vertex direction; the first hit on the Rodin surface
   is the new position. Left and right hits are averaged (symmetric head). Rays that would
   land on the eyeball bulge are flagged.
3. Write {name: [x, y, z]} plus per-vertex deltas.

The facets stay planar: the head is rebuilt as the convex hull of these vertices by
kumo_v2_head.py --head-verts OUT.json.
"""
import json
import os
import sys

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy  # noqa: E402
import bmesh  # noqa: E402
from mathutils import Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402
from kumo_common import HEAD_VERTS  # noqa: E402

GLB, OUT = argv[0], argv[1]
CHIN_Z, TIP_Z = 0.955, 1.965
SKULL_MID_Y = 0.06          # approved head (P1) mid-depth at z 1.45: front -0.49, back +0.61
EYES = [Vector((0.30, -0.45, 1.31)), Vector((-0.30, -0.45, 1.31))]

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
ob = [o for o in bpy.context.scene.objects if o.type == "MESH"][0]
bm = bmesh.new()
bm.from_mesh(ob.data)
bm.transform(ob.matrix_world)
zs = [v.co.z for v in bm.verts]
z0, z1 = min(zs), max(zs)
s0 = 1.96 / (z1 - z0)
for v in bm.verts:                                  # whole-body frame: ground 0, height 1.96
    v.co = Vector((v.co.x * s0, v.co.y * s0, (v.co.z - z0) * s0))


def slice_(z, tol=0.012):
    return [v.co for v in bm.verts if abs(v.co.z - z) < tol]


# chin = narrowest slice between z 0.85 and 1.0 (the neck)
cands = [(max(p.x for p in slice_(z)) - min(p.x for p in slice_(z)), z) for z in [0.85 + i * 0.01 for i in range(16)] if slice_(z)]
chin = min(cands)[1]
tip = max(v.co.z for v in bm.verts)
k = (TIP_Z - CHIN_Z) / (tip - chin)
sl = slice_(chin + (1.45 - CHIN_Z) / k)
xc = (max(p.x for p in sl) + min(p.x for p in sl)) / 2
yc = (max(p.y for p in sl) + min(p.y for p in sl)) / 2
for v in bm.verts:                                  # head frame
    v.co = Vector(((v.co.x - xc) * k, (v.co.y - yc) * k + SKULL_MID_Y, CHIN_Z + (v.co.z - chin) * k))
bvh = BVHTree.FromBMesh(bm)
centre = Vector((0.0, SKULL_MID_Y, 1.42))

fitted, report = {}, {}
for name, p in HEAD_VERTS.items():
    hits = []
    for sx in ((1, -1) if abs(p[0]) > 1e-6 else (1,)):
        q = Vector((p[0] * sx, p[1], p[2]))
        d = (q - centre).normalized()
        loc, _n, _i, _dist = bvh.ray_cast(centre + d * 3.0, -d)
        if loc is not None:
            hits.append(Vector((loc.x * sx, loc.y, loc.z)))
    new = sum(hits, Vector()) / len(hits)
    if abs(p[0]) < 1e-6:
        new.x = 0.0
    on_eye = any((Vector((new.x * s, new.y, new.z)) - e).length < 0.24 for e in EYES for s in (1,))
    fitted[name] = [round(new.x, 4), round(new.y, 4), round(new.z, 4)]
    report[name] = dict(old=list(p), new=fitted[name], delta=[round(a - b, 4) for a, b in zip(fitted[name], p)],
                        lr_mismatch=round((hits[0] - hits[1]).length, 4) if len(hits) == 2 else 0.0, near_eye=on_eye)

with open(OUT, "w") as fh:
    json.dump(dict(head_verts=fitted, report=report,
                   transform=dict(body_scale=s0, head_scale=k, chin_rodin=chin, tip_rodin=tip, x_shift=xc, y_shift=yc)), fh, indent=1)
for n, r in report.items():
    print(f"{n:3s} old {r['old']} new {r['new']} d {r['delta']} lr {r['lr_mismatch']} {'EYE?' if r['near_eye'] else ''}")
