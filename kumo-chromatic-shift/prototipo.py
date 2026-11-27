"""Protótipo do Chromatic Shift no Kumo (--region head | body).

Abre o .blend do Kumo (nunca salva por cima dele), grava os atributos da onda,
liga o efeito + a finalização e renderiza:
  --stills : sequência (paleta cibernética) + as 4 paletas na metade e no fim
  --anim   : 60 quadros (2,5 s) da transformação completa da cabeça

blender kumo_v8_movimento.blend -b --python prototipo.py -- \\
    --out <pasta> --textures <pasta kumo-3d-rodin> --stills
"""
import json, os, sys
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "blender", "finish"))
import chromatic_shift as cs
import iwaac_finish as fin

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
def arg(n, d=None):
    return argv[argv.index(n) + 1] if n in argv else d

out = arg("--out", os.path.join(HERE, "renders"))
os.makedirs(out, exist_ok=True)
sc = bpy.context.scene

tex_dir = arg("--textures")
if tex_dir:
    found = {}
    for root, _, files in os.walk(tex_dir):
        for f in files:
            found.setdefault(f, os.path.join(root, f))
    for im in bpy.data.images:
        b = os.path.basename(im.filepath)
        if im.filepath and not os.path.exists(bpy.path.abspath(im.filepath)) and b in found:
            im.filepath = found[b]; im.reload()

rig = next(o for o in sc.objects if o.type == "ARMATURE")
act = bpy.data.actions.get("Pose_Apresentacao")
if act:
    rig.animation_data_create(); rig.animation_data.action = act
    if hasattr(rig.animation_data, "action_slot") and act.slots:
        rig.animation_data.action_slot = act.slots[0]
sc.frame_set(1)

kumo = bpy.data.objects["Kumo"]
REGION = arg("--region", "head")
info = cs.bake_attributes(kumo, region=REGION)
followers = [o for o in sc.objects if o.type == "MESH"
             and o.name.startswith(("KumoJogo_Palpebra", "KumoOlho_Anel", "KumoOlho_Aro", "KumoOlho_Iris"))]
# anéis primeiro: íris e aro sincronizam com o anel do mesmo olho
followers.sort(key=lambda o: 0 if o.name.startswith("KumoOlho_Anel") else 1)
info["followers"] = cs.bake_followers(kumo, followers)
print("[cs] bake", json.dumps(info))
cs_mats = cs.install(kumo, followers=followers, palette="cibernetico")
for o in followers:  # decisão do Caio: íris e aro laranja também mudam
    if o.name.startswith("KumoOlho_"):
        for sl in o.material_slots:
            if sl.material and sl.material.node_tree.nodes.get("CS"):
                sl.material.node_tree.nodes["CS"].inputs["Eye Mode"].default_value = 1.0
fin.setup_render(sc)
print("[cs] finish", fin.apply(sc, render=False, shading_kw={"cel": 0.3}))
skin = bpy.data.materials["Kumo_Quad_Toon"]
for m in cs_mats:
    cs.add_glow_output(m, strength=4.0)

# câmera na cabeça (pontos da pele com peso de "head", já na pose)
dg = bpy.context.evaluated_depsgraph_get()
ev = kumo.evaluated_get(dg).to_mesh()
hw = cs._group_weights(kumo, "head")
if REGION == "head":
    pts = [kumo.matrix_world @ v.co for v in ev.vertices if v.index < len(hw) and hw[v.index] > 0.5]
else:
    pts = [kumo.matrix_world @ v.co for v in ev.vertices]
kumo.evaluated_get(dg).to_mesh_clear()
lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
c, size = (lo + hi) / 2, max(hi - lo)
cam = bpy.data.objects.new("cam_cs", bpy.data.cameras.new("cam_cs")); sc.collection.objects.link(cam)
sc.camera = cam; cam.data.lens = 50
k = 2.25 if REGION == "head" else 1.55
cam.location = c + Vector((-size * k * 0.42, -size * k, size * 0.3 * k / 2.25))
cam.rotation_euler = (c + Vector((0, 0, -size * 0.08)) - cam.location).to_track_quat("-Z", "Y").to_euler()
w = sc.world or bpy.data.worlds.new("w"); sc.world = w
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.03, 0.02, 0.055, 1)
fin.light_rig(sc, target=tuple(c), size=size / 1.2)
sc.render.resolution_percentage = int(arg("--percent", 50))
sc.eevee.taa_render_samples = int(arg("--samples", 16))
sc.render.image_settings.file_format = "PNG"
fin.compositor(sc, boil=True)

def palette(pal):
    for m in cs_mats:
        cs.set_palette(m, pal)

def shot(name, p, act=0.0, after=0.0, pal=None):
    if pal:
        palette(pal)
    kumo["cs_progress"], kumo["cs_activation"], kumo["cs_afterglow"] = p, act, after
    kumo.update_tag(); sc.frame_set(sc.frame_current)
    sc.render.filepath = os.path.join(out, name)
    bpy.ops.render.render(write_still=True)

if "--stills" in argv:
    seq = [(0.0, 1.0, 0.0), (0.18, 0.6, 0.0), (0.38, 0.0, 0.0), (0.58, 0.0, 0.0), (0.8, 0.0, 0.0), (1.0, 0.0, 0.6)]
    for i, (p, a, g) in enumerate(seq):
        shot(f"seq_{i}.png", p, a, g, "cibernetico")
    for pal in ("cibernetico", "vulcanico", "fantasma", "cristal"):
        shot(f"pal_{pal}_meio.png", 0.5, 0, 0, pal)
        shot(f"pal_{pal}_fim.png", 1.0, 0, 0, pal)

if "--quick" in argv:  # compara o ruído de borda no meio da onda
    for en in (0.0, 0.08, 0.18):
        for m in cs_mats:
            m.node_tree.nodes["CS"].inputs["Edge Noise"].default_value = en
        shot(f"edge_{en:.2f}.png", 0.45, 0, 0, "cibernetico")

if "--walkcheck" in argv:  # onda parada no meio enquanto o Kumo anda
    walk = bpy.data.actions.get("Caminhar")
    rig.animation_data.action = walk
    if hasattr(rig.animation_data, "action_slot") and walk.slots:
        rig.animation_data.action_slot = walk.slots[0]
    for f in (0, 6, 12, 18):
        sc.frame_set(f)
        shot(f"walk_{f:02d}.png", float(arg("--p", 0.45)), 0, 0, "cibernetico")

if "--anim" in argv:
    palette(arg("--palette", "cibernetico"))
    if REGION == "head":
        sc.frame_start, sc.frame_end = 1, 60
        keys = {  # quadro: (progress, activation, afterglow)
            1: (0, 0, 0), 6: (0, 0, 0), 16: (0, 1, 0), 20: (0.02, 1, 0),
            26: (None, 0.3, None), 34: (None, 0, None), 46: (1.0, None, 0), 50: (None, None, 1), 60: (None, None, 0),
        }
    else:  # corpo: ativação ~0,4 s, onda ~1,6 s, faíscas ~0,4 s (24 qps)
        sc.frame_start, sc.frame_end = 1, 72
        keys = {
            1: (0, 0, 0), 6: (0, 0, 0), 15: (0, 1, 0), 18: (0.0, 1, 0),
            26: (None, 0.3, None), 34: (None, 0, None), 56: (1.0, None, 0), 60: (None, None, 1), 72: (None, None, 0),
        }
    for f, vals in keys.items():
        for prop, v in zip(("cs_progress", "cs_activation", "cs_afterglow"), vals):
            if v is not None:
                kumo[prop] = v; kumo.keyframe_insert(f'["{prop}"]', frame=f)
    sc.render.use_overwrite = False
    sc.render.filepath = os.path.join(out, "frames", "cs_")
    bpy.ops.render.render(animation=True)

if "--save" in argv:
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=arg("--save"), copy=True, compress=True)
