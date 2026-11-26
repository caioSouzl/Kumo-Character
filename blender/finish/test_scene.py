"""Cena de teste: monta still-life, renderiza ANTES e DEPOIS da finalização.

blender -b --factory-startup --python test_scene.py -- <pasta_saida>
"""
import os, sys, math
import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import iwaac_finish as fin

out = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "/tmp"
os.makedirs(out, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

def mat(name, color, rough=0.5):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough
    return m

# cone listrado
bpy.ops.mesh.primitive_cone_add(vertices=48, radius1=0.55, radius2=0.08, depth=1.6, location=(-0.45, 0, 0.9))
cone = bpy.context.object; bpy.ops.object.shade_smooth()
orange = mat("laranja", (0.9, 0.18, 0.03))
stripe = mat("cone", (0.9, 0.18, 0.03)); nt = stripe.node_tree
tc = nt.nodes.new("ShaderNodeTexCoord"); sz = nt.nodes.new("ShaderNodeSeparateXYZ")
ramp = nt.nodes.new("ShaderNodeValToRGB"); ramp.color_ramp.interpolation = "CONSTANT"
e = ramp.color_ramp.elements; e[0].color = (0.9, 0.18, 0.03, 1); e[1].position = 0.40; e[1].color = (0.85, 0.85, 0.8, 1)
for pos, col in ((0.52, (0.9, 0.18, 0.03, 1)), (0.64, (0.85, 0.85, 0.8, 1)), (0.74, (0.9, 0.18, 0.03, 1))):
    el = e.new(pos); el.color = col
mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = -0.8; mr.inputs["From Max"].default_value = 0.8
nt.links.new(tc.outputs["Object"], sz.inputs[0]); nt.links.new(sz.outputs["Z"], mr.inputs[0])
nt.links.new(mr.outputs[0], ramp.inputs[0]); nt.links.new(ramp.outputs[0], nt.nodes["Principled BSDF"].inputs["Base Color"])
cone.data.materials.append(stripe)
bpy.ops.mesh.primitive_cube_add(size=1, location=(-0.45, 0, 0.06)); base = bpy.context.object
base.scale = (1.3, 1.3, 0.12); bpy.ops.object.transform_apply(scale=True)
bev = base.modifiers.new("b", "BEVEL"); bev.width = 0.05; bev.segments = 3
base.data.materials.append(orange)
# Suzanne roxa
bpy.ops.mesh.primitive_monkey_add(location=(0.65, -0.2, 0.55), rotation=(0, 0, math.radians(-25)))
mk = bpy.context.object; mk.scale = (0.5,) * 3; bpy.ops.object.shade_smooth()
sub = mk.modifiers.new("s", "SUBSURF"); sub.levels = sub.render_levels = 2
mk.data.materials.append(mat("roxo", (0.25, 0.12, 0.8), 0.4))
# chão / fundo
bpy.ops.mesh.primitive_plane_add(size=20); fl = bpy.context.object
fl.data.materials.append(mat("chao", (0.06, 0.05, 0.07), 0.9))
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.02, 0.018, 0.03, 1)
# câmera
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam)
cam.location = (0.3, -5.8, 2.3); cam.data.lens = 45; sc.camera = cam
from mathutils import Vector
cam.rotation_euler = (Vector((0.1, 0, 0.75)) - cam.location).to_track_quat("-Z", "Y").to_euler()

fin.setup_render(sc); fin.light_rig(sc, target=(0, 0, 0.6), size=1.0)
sc.render.resolution_percentage = 50
sc.eevee.taa_render_samples = 16

def render(name):
    sc.render.filepath = os.path.join(out, name); bpy.ops.render.render(write_still=True)

sc.compositing_node_group = None
render("antes.png")
print("[iwaac]", fin.apply(sc, render=False))
render("depois.png")
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, "teste_iwaac.blend"))
