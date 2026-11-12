"""GLB leve para o Estúdio (página do celular): sem normais (a página não usa luz), sem animações gravadas.
O GLB de jogo completo é ombros/kumo_v6_jogo.glb.   python exportar_glb_estudio.py <kumo_v6_ombros.blend> <saída.glb>"""
import bpy, sys
SRC, OUT = sys.argv[-2:]
bpy.ops.wm.open_mainfile(filepath=SRC)
rig = bpy.data.objects['Kumo_Rig']
if rig.animation_data: rig.animation_data.action = None
for b in rig.pose.bones: b.rotation_quaternion = (1, 0, 0, 0); b.rotation_euler = (0, 0, 0); b.location = (0, 0, 0)
img = bpy.data.images.get('kumo_quad_diffuse')
if img: img.filepath = '/home/user/Kumo-Character/kumo-3d-rodin/textures/kumo_quad_diffuse.png'; img.reload()
for o in bpy.context.selected_objects: o.select_set(False)
objs = [o for o in bpy.data.objects if o.name in ('Kumo', 'Kumo_Contorno', 'Kumo_Rig') or o.name.startswith('KumoJogo_')]
for o in objs: o.hide_set(False); o.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True, export_apply=False, export_skins=True, export_animations=False,
                          export_all_influences=False, export_morph=True, export_morph_normal=False, export_normals=False, export_tangents=False)
import os; print('GE', os.path.getsize(OUT) // 1024, 'KB')
