"""Renderiza um personagem (o Kumo) antes/depois da finalização.

blender kumo_v8_movimento.blend -b --python render_kumo.py -- \\
    --out <pasta> [--textures <pasta com os png>] [--action Caminhar] [--frame 6]
    [--anim]   (renderiza a ação inteira em vez de um quadro)
"""
import os, sys, math
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import iwaac_finish as fin

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
def arg(name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default

out = arg("--out", "/tmp/kumo_finish")
os.makedirs(out, exist_ok=True)
sc = bpy.context.scene

# texturas com caminho quebrado: procura pelo nome do arquivo
tex_dir = arg("--textures")
if tex_dir:
    found = {}
    for root, _, files in os.walk(tex_dir):
        for f in files:
            found.setdefault(f, os.path.join(root, f))
    for im in bpy.data.images:
        base = os.path.basename(im.filepath)
        if im.filepath and not os.path.exists(bpy.path.abspath(im.filepath)) and base in found:
            im.filepath = found[base]
            im.reload()

# ação
rig = next((o for o in sc.objects if o.type == "ARMATURE"), None)
action = arg("--action")
if rig and action and action in bpy.data.actions:
    rig.animation_data_create()
    act = bpy.data.actions[action]
    rig.animation_data.action = act
    if hasattr(rig.animation_data, "action_slot") and act.slots:
        rig.animation_data.action_slot = act.slots[0]
    sc.frame_start, sc.frame_end = int(act.frame_range[0]), int(act.frame_range[1])
sc.frame_set(int(arg("--frame", sc.frame_start)))

# enquadramento pelo tamanho do personagem
meshes = [o for o in sc.objects if o.type == "MESH" and not o.hide_render]
pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
center, height = (lo + hi) / 2, hi.z - lo.z

cam = bpy.data.objects.new("cam_finish", bpy.data.cameras.new("cam_finish"))
sc.collection.objects.link(cam); sc.camera = cam
cam.data.lens = 50
dist = height * 2.6
ang = math.radians(float(arg("--angle", -28)))   # 3/4 de frente (-Y é a frente)
cam.location = center + Vector((math.sin(-ang) * dist * -1, -math.cos(ang) * dist, height * 0.12))
cam.rotation_euler = (center + Vector((0, 0, -height * 0.04)) - cam.location).to_track_quat("-Z", "Y").to_euler()

# chão e fundo
bpy.ops.mesh.primitive_plane_add(size=height * 20, location=(center.x, center.y, lo.z))
floor = bpy.context.object
fm = bpy.data.materials.new("chao"); fm.use_nodes = True
fb = fm.node_tree.nodes["Principled BSDF"]
fb.inputs["Base Color"].default_value = (0.09, 0.07, 0.12, 1); fb.inputs["Roughness"].default_value = 0.9
floor.data.materials.append(fm)
w = sc.world or bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.035, 0.025, 0.06, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 1.0

fin.setup_render(sc)
fin.light_rig(sc, target=tuple(center), size=height / 1.6)
sc.render.resolution_percentage = int(arg("--percent", 50))
sc.eevee.taa_render_samples = int(arg("--samples", 16))
sc.render.image_settings.file_format = "PNG"

def still(name):
    sc.render.filepath = os.path.join(out, name)
    bpy.ops.render.render(write_still=True)

if "--anim" not in argv and "--no-before" not in argv:
    sc.compositing_node_group = None
    still("kumo_antes.png")
import json
sc.view_settings.exposure = float(arg("--exposure", 0))
print("[iwaac]", fin.apply(sc, render=False, shading_kw=json.loads(arg("--shading", "{}"))))
if "--anim" in argv:
    sc.render.use_overwrite = False
    sc.render.filepath = os.path.join(out, "frames", "k_")
    bpy.ops.render.render(animation=True)
else:
    still(arg("--name", "kumo_depois.png"))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, "kumo_finish.blend"), copy=True)
