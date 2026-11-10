"""Rodin-style pipeline in Blender, steps 2-3: quad remesh + texture transfer (bake).

    python quad_retopo_bake.py [--faces 8000] [--tex 2048] [--res 1200]      (bpy; run from kumo-3d-rodin/)

1. Load the official Rodin GLB, place it in the Kumo frame (feet z = 0, height 1.96) and weld
   the texture seams by position (UVs live on face corners, so the colours do not change).
2. QuadriFlow remesh of a copy -> all-quad mesh with X symmetry ("Kumo_Quad").
3. New UVs (Smart UV Project) on the quad mesh, then bake the Rodin diffuse colour onto it
   (Cycles, Selected to Active) -> textures/kumo_quad_diffuse.png.
4. Quad mesh materials: flat toon colour (emission of the baked texture) + inverted-hull outline,
   and a PBR variant for export.
5. Writes kumo_quad.blend, export/kumo_quad.glb and renders/quad-*.png (views + wireframe).
"""
import math
import os
import sys

import bpy  # noqa: E402
import bmesh  # noqa: E402
from mathutils import Vector  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
FACES = int(argv[argv.index("--faces") + 1]) if "--faces" in argv else 8000
TEX = int(argv[argv.index("--tex") + 1]) if "--tex" in argv else 2048
RES = int(argv[argv.index("--res") + 1]) if "--res" in argv else 1200
TOTAL_H = 1.96
OUTLINE = (0x5B / 255, 0x3A / 255, 0x2E / 255)
for d in ("textures", "export", "renders"):
    os.makedirs(os.path.join(ROOT, d), exist_ok=True)


def srgb2lin(c):
    return ((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92


def activate(ob, *others):
    bpy.ops.object.select_all(action="DESELECT")
    for o in others:
        o.select_set(True)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob


# ---------------------------------------------------------------- 1. source
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
bpy.ops.import_scene.gltf(filepath=os.path.join(ROOT, "base_basic_pbr.glb"))
src = [o for o in scene.objects if o.type == "MESH"][0]
src.name = "Kumo_Rodin_Source"
activate(src)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
me = src.data
zs = [v.co.z for v in me.vertices]
k = TOTAL_H / (max(zs) - min(zs))
xs = [v.co.x for v in me.vertices]
ys = [v.co.y for v in me.vertices]
off = Vector(((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2, min(zs)))
bm = bmesh.new()
bm.from_mesh(me)
for v in bm.verts:
    v.co = (v.co - off) * k
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.to_mesh(me)
bm.free()
me.update()

# ---------------------------------------------------------------- 2. quad remesh
quad = src.copy()
quad.data = src.data.copy()
quad.name = "Kumo_Quad"
scene.collection.objects.link(quad)
quad.data.materials.clear()
activate(quad)
bpy.ops.object.quadriflow_remesh(target_faces=FACES, use_mesh_symmetry=True, use_preserve_sharp=True,
                                 use_preserve_boundary=True, preserve_attributes=False,
                                 smooth_normals=False, mode="FACES")
qme = quad.data
for p in qme.polygons:
    p.use_smooth = True
n_quads = sum(1 for p in qme.polygons if len(p.vertices) == 4)
print(f"quad mesh: {len(qme.polygons)} faces, {n_quads} quads, {len(qme.vertices)} verts")

# ---------------------------------------------------------------- 3. UVs + bake
while qme.uv_layers:
    qme.uv_layers.remove(qme.uv_layers[0])
qme.uv_layers.new(name="UVMap")
activate(quad)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.004)
bpy.ops.object.mode_set(mode="OBJECT")

img = bpy.data.images.new("kumo_quad_diffuse", TEX, TEX, alpha=False)
bake_mat = bpy.data.materials.new("Kumo_Quad_Bake")
bake_mat.use_nodes = True
bnt = bake_mat.node_tree
tex_node = bnt.nodes.new("ShaderNodeTexImage")
tex_node.image = img
bnt.nodes.active = tex_node
qme.materials.append(bake_mat)

scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 4
scene.render.bake.use_selected_to_active = True
scene.render.bake.cage_extrusion = 0.03
scene.render.bake.max_ray_distance = 0.08
scene.render.bake.use_pass_direct = False
scene.render.bake.use_pass_indirect = False
scene.render.bake.use_pass_color = True
scene.render.bake.margin = 8
activate(quad, src)
bpy.ops.object.bake(type="DIFFUSE", pass_filter={"COLOR"})
img.filepath_raw = os.path.join(ROOT, "textures", "kumo_quad_diffuse.png")
img.file_format = "PNG"
img.save()
print("baked", img.filepath_raw)

# ---------------------------------------------------------------- 4. materials
qme.materials.clear()
pbr = bpy.data.materials.new("Kumo_Quad_PBR")
pbr.use_nodes = True
pn = pbr.node_tree
pt = pn.nodes.new("ShaderNodeTexImage")
pt.image = img
pb = next(n for n in pn.nodes if n.type == "BSDF_PRINCIPLED")
pb.inputs["Roughness"].default_value = 0.6
pn.links.new(pt.outputs["Color"], pb.inputs["Base Color"])

toon = bpy.data.materials.new("Kumo_Quad_Toon")
toon.use_nodes = True
tn = toon.node_tree
for n in list(tn.nodes):
    tn.nodes.remove(n)
t_out = tn.nodes.new("ShaderNodeOutputMaterial")
t_em = tn.nodes.new("ShaderNodeEmission")
t_tex = tn.nodes.new("ShaderNodeTexImage")
t_tex.image = img
tn.links.new(t_tex.outputs["Color"], t_em.inputs["Color"])
tn.links.new(t_em.outputs[0], t_out.inputs[0])

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
ln.links.new(o_em.outputs[0], o_mix.inputs[1])
ln.links.new(o_tr.outputs[0], o_mix.inputs[2])
ln.links.new(o_mix.outputs[0], o_out.inputs[0])
line.use_backface_culling = True

# export GLB with the PBR material only (no outline shell)
qme.materials.append(pbr)
activate(quad)
bpy.ops.export_scene.gltf(filepath=os.path.join(ROOT, "export", "kumo_quad.glb"), use_selection=True,
                          export_format="GLB", export_apply=True)

# Blender scene: toon + outline
qme.materials[0] = toon
qme.materials.append(line)
sol = quad.modifiers.new("Outline", "SOLIDIFY")
sol.offset = 1.0
sol.use_flip_normals = True
sol.use_rim = False
sol.material_offset = 1
quad["outline_thickness"] = 0.02
drv = sol.driver_add("thickness").driver
drv.type = "AVERAGE"
var = drv.variables.new()
var.targets[0].id = quad
var.targets[0].data_path = '["outline_thickness"]'
sol.thickness = 0.02
src.hide_render = True
src.hide_set(True)

# ---------------------------------------------------------------- 5. renders
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
scene.render.resolution_x = scene.render.resolution_y = RES
for v, c in cams.items():
    scene.camera = c
    scene.render.filepath = os.path.join(ROOT, "renders", f"quad-{v}.png")
    bpy.ops.render.render(write_still=True)

# wireframe views (Freestyle on every edge, grey clay)
scene.render.use_freestyle = True
scene.render.line_thickness_mode = "RELATIVE"
vl = scene.view_layers[0]
fs = vl.freestyle_settings
for s_ in list(fs.linesets):
    fs.linesets.remove(s_)
lw = fs.linesets.new("Wire")
lw.select_by_edge_types = True
for kk in ("silhouette", "border", "crease", "contour", "external_contour", "material_boundary"):
    setattr(lw, "select_" + kk, False)
lw.select_edge_mark = True
lw.linestyle.color = (0.1, 0.1, 0.1)
lw.linestyle.thickness = 1.0
fe = qme.attributes.get("freestyle_edge") or qme.attributes.new("freestyle_edge", "BOOLEAN", "EDGE")
fe.data.foreach_set("value", [True] * len(qme.edges))
clay = bpy.data.materials.new("Clay")
clay.use_nodes = True
cn = clay.node_tree
for n in list(cn.nodes):
    cn.nodes.remove(n)
c_out = cn.nodes.new("ShaderNodeOutputMaterial")
c_em = cn.nodes.new("ShaderNodeEmission")
c_em.inputs[0].default_value = (0.75, 0.75, 0.72, 1)
cn.links.new(c_em.outputs[0], c_out.inputs[0])
sol.show_render = False
vl.material_override = clay
for v in ("front", "side"):
    scene.camera = cams[v]
    scene.render.filepath = os.path.join(ROOT, "renders", f"quad-wire-{v}.png")
    bpy.ops.render.render(write_still=True)
vl.material_override = None
sol.show_render = True
scene.render.use_freestyle = False
fe.data.foreach_set("value", [False] * len(qme.edges))
scene.camera = cams["front"]
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "kumo_quad.blend"))
print("saved kumo_quad.blend")
