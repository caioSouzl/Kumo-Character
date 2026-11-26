"""Teste de animação: turntable de 48 quadros (2 s) com tremor de borda.

blender -b --factory-startup --python test_anim.py -- <pasta_saida>
"""
import os, sys, math
import bpy
from mathutils import Vector

out = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "/tmp"
sys.argv = [sys.argv[0], "--", out]  # reaproveita a cena de teste
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_scene.py")).read().split("def render")[0])

sc = bpy.context.scene
cam = sc.camera
pivot = bpy.data.objects.new("pivot", None); sc.collection.objects.link(pivot)
pivot.location = (0.1, 0, 0.75)
cam.parent = pivot; cam.location = cam.location - pivot.location
cam.rotation_euler = (-cam.location).to_track_quat("-Z", "Y").to_euler()
sc.frame_start, sc.frame_end = 1, 48
pivot.rotation_euler = (0, 0, math.radians(-20)); pivot.keyframe_insert("rotation_euler", frame=1)
pivot.rotation_euler = (0, 0, math.radians(20)); pivot.keyframe_insert("rotation_euler", frame=48)
for fc in pivot.animation_data.action.layers[0].strips[0].channelbags[0].fcurves if hasattr(pivot.animation_data.action, "layers") else pivot.animation_data.action.fcurves:
    for k in fc.keyframe_points: k.interpolation = "SINE"
fin.apply(sc, render=False)
sc.render.image_settings.file_format = "PNG"
sc.render.use_overwrite = False  # retoma de onde parou
sc.render.filepath = os.path.join(out, "frames", "f_")
bpy.ops.render.render(animation=True)
