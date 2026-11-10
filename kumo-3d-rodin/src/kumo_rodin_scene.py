"""Official Kumo 3D model (Rodin Gen-2.5, generation fc410dfd) — scene and renders.

    python kumo_rodin_scene.py [--render] [--res 1400]      (bpy; run from kumo-3d-rodin/)

Builds kumo_rodin.blend from base_basic_pbr.glb:
  - placed in the Kumo frame: feet on the ground (z = 0), centred on x/y, total height
    1.96 (head height = 1 unit, as in the reference measurements), facing -Y;
  - original PBR material kept (for real-time / game export) plus a "toon" render setup:
    the diffuse texture shown as flat colour (no lighting) and an inverted-hull outline
    (Solidify, flipped normals, dark brown #5B3A2E) with adjustable thickness
    (object property "outline_thickness");
  - orthographic cameras: front 0, three-quarter -40, side -90, back 180, plus face close-up.
With --render writes renders/view-*.png and renders/face-front.png.
"""
import math
import os
import sys

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
RES = int(argv[argv.index("--res") + 1]) if "--res" in argv else 1400
TOTAL_H = 1.96
OUTLINE = (0x5B / 255, 0x3A / 255, 0x2E / 255)


def srgb2lin(c):
    return ((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92


bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
bpy.ops.import_scene.gltf(filepath=os.path.join(ROOT, "base_basic_pbr.glb"))
body = [o for o in scene.objects if o.type == "MESH"][0]
body.name = "Kumo"
bpy.ops.object.select_all(action="DESELECT")
body.select_set(True)
bpy.context.view_layer.objects.active = body
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# place in the Kumo frame
me = body.data
xs = [v.co.x for v in me.vertices]
ys = [v.co.y for v in me.vertices]
zs = [v.co.z for v in me.vertices]
k = TOTAL_H / (max(zs) - min(zs))
off = Vector(((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2, min(zs)))
for v in me.vertices:
    v.co = (v.co - off) * k
me.update()
# the generated mesh has inconsistent winding: merge split seams by position for the
# normal pass only, make all normals point outward, keep the UV seams intact
import bmesh  # noqa: E402
bm = bmesh.new()
bm.from_mesh(me)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)   # UVs live on face corners: unaffected
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
print("islands welded; verts", len(bm.verts), "non-manifold edges", sum(1 for e in bm.edges if not e.is_manifold))
bm.to_mesh(me)
bm.free()
me.update()

# toon look: flat diffuse colour (keeps the original PBR material for export)
pbr = me.materials[0]
pbr.name = "Kumo_PBR"
toon = pbr.copy()
toon.name = "Kumo_Toon"
nt = toon.node_tree
bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
mat_out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
em = nt.nodes.new("ShaderNodeEmission")
nt.links.new(bsdf.inputs["Base Color"].links[0].from_socket, em.inputs[0])
nt.links.new(em.outputs[0], mat_out.inputs[0])
me.materials[0] = toon

# inverted-hull outline: emission colour on back faces, transparent on front faces
line = bpy.data.materials.new("Kumo_Outline")
line.use_nodes = True
ln = line.node_tree
for n in list(ln.nodes):
    ln.nodes.remove(n)
o_out = ln.nodes.new("ShaderNodeOutputMaterial")
o_em = ln.nodes.new("ShaderNodeEmission")
o_em.inputs[0].default_value = tuple(srgb2lin(c) for c in OUTLINE) + (1,)
o_tr = ln.nodes.new("ShaderNodeBsdfTransparent")
o_geo = ln.nodes.new("ShaderNodeNewGeometry")
o_mix = ln.nodes.new("ShaderNodeMixShader")
ln.links.new(o_geo.outputs["Backfacing"], o_mix.inputs[0])
# the shell's normals are flipped: the part behind the body faces the camera (front-facing)
# and draws the outline; the part in front of the body is back-facing and transparent
ln.links.new(o_em.outputs[0], o_mix.inputs[1])
ln.links.new(o_tr.outputs[0], o_mix.inputs[2])
ln.links.new(o_mix.outputs[0], o_out.inputs[0])
line.use_backface_culling = True
me.materials.append(line)
sol = body.modifiers.new("Outline", "SOLIDIFY")
sol.offset = 1.0
sol.use_flip_normals = True
sol.use_rim = False
sol.material_offset = 1
body["outline_thickness"] = 0.02
drv = sol.driver_add("thickness").driver
drv.type = "AVERAGE"
var = drv.variables.new()
var.targets[0].id = body
var.targets[0].data_path = '["outline_thickness"]'
sol.thickness = body["outline_thickness"]

# render settings
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 16
scene.cycles.max_bounces = 0
scene.view_settings.view_transform = "Standard"
scene.render.film_transparent = True
scene.world = bpy.data.worlds.new("World")


def camera(name, az, ortho=2.25, target=(0.0, 0.0, 0.98)):
    cam = bpy.data.objects.new(name, bpy.data.cameras.new(name))
    scene.collection.objects.link(cam)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = ortho
    a = math.radians(az)
    tgt = Vector(target)
    cam.location = tgt + Vector((math.sin(a) * 10, -math.cos(a) * 10, 0))
    cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
    return cam


cams = {"front": camera("Cam_Front", 0), "three-quarter": camera("Cam_ThreeQuarter", -40),
        "side": camera("Cam_Side", -90), "back": camera("Cam_Back", 180)}
face = camera("Cam_Face", 0, ortho=1.15, target=(0.0, 0.0, 1.45))
scene.camera = cams["front"]
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "kumo_rodin.blend"))
print("saved kumo_rodin.blend; scale", round(k, 4), "faces", len(me.polygons))

if "--render" in argv:
    out = os.path.join(ROOT, "renders")
    os.makedirs(out, exist_ok=True)
    jobs = [(f"view-{v}", c, RES) for v, c in cams.items()] + [("face-front", face, int(RES * 0.7))]
    for name, cam, res in jobs:
        scene.camera = cam
        scene.render.resolution_x = scene.render.resolution_y = res
        scene.render.filepath = os.path.join(out, name + ".png")
        bpy.ops.render.render(write_still=True)
        print("rendered", name)
    scene.camera = cams["front"]
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "kumo_rodin.blend"))
