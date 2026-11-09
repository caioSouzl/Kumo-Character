"""kumo-inspect — read-only geometry inspection of kumo_toon.blend (never writes the .blend).

CLI-Anything style: one command, JSON for agents, Markdown for people.

    python kumo_inspect.py <file.blend> [--json out.json] [--md out.md] [--object Kumo_Head]

Reports, per mesh object (modifiers evaluated):
  vertices / edges / faces, face shapes (tri / quad / n-gon), flat vs smooth faces,
  topology problems (non-manifold edges, loose verts/edges, boundary edges,
  duplicate vertices, zero-area faces, inverted normals),
and, for the head, a face-by-face table: vertex count, shape, area, normal,
tilt (angle from vertical), azimuth, region (front / side / top / bottom / back)
and material (head / crest).
"""
import json
import math
import sys

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
import bpy  # noqa: E402
import bmesh  # noqa: E402
from mathutils import Vector  # noqa: E402

BLEND = argv[0]
OUT_JSON = argv[argv.index("--json") + 1] if "--json" in argv else None
OUT_MD = argv[argv.index("--md") + 1] if "--md" in argv else None
DETAIL = argv[argv.index("--object") + 1] if "--object" in argv else "Kumo_Head"

bpy.ops.wm.open_mainfile(filepath=BLEND)
dg = bpy.context.evaluated_depsgraph_get()

SHAPES = {3: "triangle", 4: "quad"}


def region(n):
    """Classify a face by its world normal (character faces -Y, +Z up)."""
    if n.z > 0.75:
        return "top"
    if n.z < -0.75:
        return "bottom"
    if -n.y >= abs(n.x) and -n.y > 0.35:
        return "front" + ("-upper" if n.z > 0.3 else "-lower" if n.z < -0.3 else "")
    if n.y >= abs(n.x) and n.y > 0.35:
        return "back" + ("-upper" if n.z > 0.3 else "-lower" if n.z < -0.3 else "")
    return ("side-R" if n.x < 0 else "side-L") + ("-upper" if n.z > 0.3 else "-lower" if n.z < -0.3 else "")


def inspect(ob):
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.transform(ob.matrix_world)
    bm.normal_update()
    bm.verts.ensure_lookup_table()
    faces = list(bm.faces)
    shapes = {}
    for f in faces:
        k = SHAPES.get(len(f.verts), f"ngon-{len(f.verts)}")
        shapes[k] = shapes.get(k, 0) + 1
    nonmanifold = [e.index for e in bm.edges if not e.is_manifold and not e.is_boundary]
    boundary = [e.index for e in bm.edges if e.is_boundary]
    loose_v = [v.index for v in bm.verts if not v.link_edges]
    loose_e = [e.index for e in bm.edges if not e.link_faces]
    zero = [f.index for f in faces if f.calc_area() < 1e-8]
    # duplicate vertices (within 1e-5)
    seen, dup = {}, 0
    for v in bm.verts:
        key = tuple(round(c, 5) for c in v.co)
        dup += key in seen
        seen[key] = 1
    # normal orientation: inconsistent winding = an edge whose two faces traverse it in the same direction
    inconsistent = 0
    for e in bm.edges:
        lf = e.link_faces
        if len(lf) == 2:
            dirs = []
            for f in lf:
                for lp in f.loops:
                    if lp.edge is e:
                        dirs.append(lp.vert is e.verts[0])
            inconsistent += dirs[0] == dirs[1]
    # signed volume (positive = outward normals) for closed meshes
    vol = None
    if not boundary:
        vol = sum(f.calc_center_median().dot(f.normal) * f.calc_area() for f in faces) / 3
    info = {
        "object": ob.name,
        "modifiers": [m.type for m in ob.modifiers],
        "vertices": len(bm.verts),
        "edges": len(bm.edges),
        "faces": len(faces),
        "euler_characteristic": len(bm.verts) - len(bm.edges) + len(faces),
        "face_shapes": shapes,
        "flat_faces": sum(1 for p in me.polygons if not p.use_smooth),
        "smooth_faces": sum(1 for p in me.polygons if p.use_smooth),
        "closed": not boundary,
        "problems": {
            "non_manifold_edges": len(nonmanifold),
            "boundary_edges": len(boundary),
            "loose_vertices": len(loose_v),
            "loose_edges": len(loose_e),
            "duplicate_vertices": dup,
            "zero_area_faces": len(zero),
            "inconsistent_winding_edges": inconsistent,
        },
        "signed_volume": round(vol, 5) if vol is not None else None,
        "normals": (None if vol is None else "outward" if vol > 1e-6 else "inward" if vol < -1e-6 else "flat (no volume)"),
        "loose_vertex_positions": [[round(c, 3) for c in bm.verts[i].co] for i in loose_v][:10],
        "bbox": [[round(min(v.co[i] for v in bm.verts), 4) for i in range(3)], [round(max(v.co[i] for v in bm.verts), 4) for i in range(3)]] if bm.verts else None,
    }
    detail = None
    if ob.name == DETAIL:
        mats = [m.name if m else None for m in ob.data.materials]
        detail = []
        for f in faces:
            n = f.normal
            detail.append({
                "face": f.index,
                "verts": len(f.verts),
                "shape": SHAPES.get(len(f.verts), f"ngon-{len(f.verts)}"),
                "area": round(f.calc_area(), 5),
                "center": [round(x, 3) for x in f.calc_center_median()],
                "normal": [round(x, 3) for x in n],
                "tilt_deg": round(90 - math.degrees(math.acos(max(-1, min(1, n.z)))), 1),   # + = faces up
                "azimuth_deg": round(math.degrees(math.atan2(n.x, -n.y)), 1),              # 0 = straight to the front
                "region": region(n),
                "material": mats[f.material_index] if f.material_index < len(mats) else None,
                "neighbours": sorted({g.index for e in f.edges for g in e.link_faces if g is not f}),
            })
    bm.free()
    ev.to_mesh_clear()
    return info, detail


report = {"file": BLEND, "objects": [], "detail_object": DETAIL, "detail": None}
for ob in sorted(bpy.data.objects, key=lambda o: o.name):
    if ob.type != "MESH":
        continue
    info, detail = inspect(ob)
    report["objects"].append(info)
    if detail is not None:
        report["detail"] = detail

tot = {k: sum(o[k] for o in report["objects"]) for k in ("vertices", "edges", "faces")}
report["totals"] = tot

if OUT_JSON:
    with open(OUT_JSON, "w") as fh:
        json.dump(report, fh, indent=1)

lines = [f"# Kumo mesh inspection — `{BLEND.split('/')[-1]}`", "",
         f"Totals: **{tot['vertices']} vertices · {tot['edges']} edges · {tot['faces']} faces** in {len(report['objects'])} mesh objects.", "",
         "| Object | V | E | F | Shapes | Closed | Normals | Problems |", "|---|---|---|---|---|---|---|---|"]
for o in report["objects"]:
    probs = ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in o["problems"].items() if v) or "—"
    shp = ", ".join(f"{k} {v}" for k, v in sorted(o["face_shapes"].items()))
    lines.append(f"| {o['object']} | {o['vertices']} | {o['edges']} | {o['faces']} | {shp} | {'yes' if o['closed'] else 'no'} | {o['normals'] or '—'} | {probs} |")
if report["detail"]:
    lines += ["", f"## Faces of `{DETAIL}`", "",
              "Tilt: + faces upward, − downward. Azimuth: 0° = front, ±90° = sides, 180° = back.", "",
              "| # | Shape | Area | Region | Tilt° | Azimuth° | Material | Centre (x, y, z) |", "|---|---|---|---|---|---|---|---|"]
    for f in sorted(report["detail"], key=lambda f: (-f["center"][2], f["center"][0])):
        lines.append(f"| {f['face']} | {f['shape']} | {f['area']} | {f['region']} | {f['tilt_deg']} | {f['azimuth_deg']} | {f['material']} | {tuple(f['center'])} |")
md = "\n".join(lines) + "\n"
if OUT_MD:
    with open(OUT_MD, "w") as fh:
        fh.write(md)
print(json.dumps({"totals": tot, "objects": len(report["objects"]),
                  "detail_faces": len(report["detail"] or [])}))
