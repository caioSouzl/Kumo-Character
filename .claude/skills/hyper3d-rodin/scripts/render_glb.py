"""Import a Rodin GLB, print mesh stats and render orthographic views with flat albedo.

    python3 render_glb.py MODEL.glb OUT_DIR [--res 800]     (needs `bpy`, e.g. pip install bpy==5.2.3)

Views: front (0), three-quarter (-40), side (-90), back (180), other side (90); camera
azimuths follow kumo-3d-toon conventions (character faces -Y). PBR materials are
rewired to emit their base-colour texture, so the render shows the real colours
without lighting. Writes <view>.png, turnaround.png and stats.json.
"""
import json
import math
import os
import sys

import bpy  # noqa: E402
import bmesh  # noqa: E402
from mathutils import Vector  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
GLB, OUT = argv[0], argv[1]
RES = int(argv[argv.index("--res") + 1]) if "--res" in argv else 800
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
scene = bpy.context.scene
meshes = [o for o in scene.objects if o.type == "MESH"]

stats = []
for o in meshes:
    bm = bmesh.new()
    bm.from_mesh(o.data)
    shapes = {}
    for f in bm.faces:
        shapes[len(f.verts)] = shapes.get(len(f.verts), 0) + 1
    stats.append(dict(name=o.name, vertices=len(bm.verts), faces=len(bm.faces), face_sides=shapes,
                      non_manifold_edges=sum(1 for e in bm.edges if not e.is_manifold)))
    bm.free()

for m in bpy.data.materials:
    if not m.node_tree:
        continue
    nt = m.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    mat_out = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"), None)
    if bsdf and mat_out and bsdf.inputs["Base Color"].is_linked:
        em = nt.nodes.new("ShaderNodeEmission")
        nt.links.new(bsdf.inputs["Base Color"].links[0].from_socket, em.inputs[0])
        nt.links.new(em.outputs[0], mat_out.inputs[0])

pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
ctr = (mn + mx) / 2

scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 8
scene.view_settings.view_transform = "Standard"
scene.render.film_transparent = True
scene.render.resolution_x = scene.render.resolution_y = RES
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
scene.collection.objects.link(cam)
scene.camera = cam
cam.data.type = "ORTHO"
cam.data.ortho_scale = max(mx - mn) * 1.1

views = (("front", 0), ("three-quarter", -40), ("side", -90), ("back", 180), ("other-side", 90))
for name, az in views:
    a = math.radians(az)
    cam.location = ctr + Vector((math.sin(a) * 10, -math.cos(a) * 10, 0))
    cam.rotation_euler = (ctr - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = os.path.join(OUT, f"{name}.png")
    bpy.ops.render.render(write_still=True)

try:
    from PIL import Image
    t = 500
    sheet = Image.new("RGB", (t * len(views), t), "white")
    for i, (name, _) in enumerate(views):
        im = Image.open(os.path.join(OUT, f"{name}.png")).resize((t, t))
        sheet.paste(im, (i * t, 0), im)
    sheet.save(os.path.join(OUT, "turnaround.png"))
except ImportError:
    pass

result = dict(model=GLB, meshes=stats, bbox=[list(mn), list(mx)])
with open(os.path.join(OUT, "stats.json"), "w") as fh:
    json.dump(result, fh, indent=1)
print(json.dumps(result))
