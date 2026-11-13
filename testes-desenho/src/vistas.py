"""Teste 1: o Kumo 3D oficial renderizado como desenho (emissão chapada + contorno), em 8 ângulos, para comparar
com as vistas da folha de modelo.   python vistas.py <blend> <saída>"""
import bpy, sys, os, math
from mathutils import Vector
ARGS = [a for a in sys.argv if not a.startswith('--')]; SRC, OUT = ARGS[-2:]; os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=SRC); sc = bpy.context.scene
img = bpy.data.images.get('kumo_quad_diffuse')
if img: img.filepath = '/home/user/Kumo-Character/kumo-3d-rodin/textures/kumo_quad_diffuse.png'; img.reload()
TEXD = '/home/user/Kumo-Character/kumo-3d-rodin/v6-dev/olhos-jogo/texturas'
for im in bpy.data.images:
    if im.name.startswith('olho_') and not os.path.exists(bpy.path.abspath(im.filepath)): im.filepath = os.path.join(TEXD, os.path.basename(im.filepath)); im.reload()
rig = bpy.data.objects['Kumo_Rig']
if rig.animation_data: rig.animation_data.action = None
for b in rig.pose.bones: b.rotation_quaternion = (1, 0, 0, 0); b.rotation_euler = (0, 0, 0); b.location = (0, 0, 0)
# contorno de jogo (casca invertida) depende de esconder as faces de trás, coisa que o Cycles não faz: aparece como
# manchas marrons por cima da pele. Para o teste de desenho, sem ele (o contorno vem depois, em 2D)
SEM_CASCA = '--com-casca' not in sys.argv
if SEM_CASCA:
    for o in bpy.data.objects:
        if o.name == 'Kumo_Contorno': o.hide_render = True
        if o.type == 'MESH':
            for m in o.modifiers:
                if m.type != 'ARMATURE': m.show_render = False
if '--sem-moldura' in sys.argv:
    for o in bpy.data.objects:
        if 'Moldura' in o.name: o.hide_render = True
sc.render.engine = 'CYCLES'; sc.cycles.samples = 16; sc.render.film_transparent = True; sc.cycles.transparent_max_bounces = 32
sc.render.resolution_x = sc.render.resolution_y = 900
# contorno de desenho: Freestyle só no contorno externo e nas bordas (sem as dobras das facetas, que o desenho não tem)
if SEM_CASCA:
    sc.render.use_freestyle = True; sc.render.line_thickness_mode = 'ABSOLUTE'; sc.render.line_thickness = 1.0
    vl = bpy.context.view_layer; vl.use_freestyle = True; fs = vl.freestyle_settings
    for ls in list(fs.linesets): fs.linesets.remove(ls)
    ls = fs.linesets.new('contorno'); ls.select_by_visibility = True; ls.select_by_edge_types = True
    for k in ('select_silhouette', 'select_border', 'select_crease', 'select_contour', 'select_external_contour', 'select_material_boundary'): setattr(ls, k, False)
    ls.select_silhouette = True; ls.select_border = True; ls.select_external_contour = True
    st = ls.linestyle; st.color = (0.03, 0.025, 0.02); st.thickness = 4.5; st.caps = 'ROUND'
    # as camadas dos olhos (grades finas, molduras) não ganham linha: viravam quadradinhos em volta do olho
    sem = bpy.data.collections.new('SemLinha'); sc.collection.children.link(sem)
    for o in [o for o in bpy.data.objects if o.name.startswith('KumoJogo_')]:
        for c_ in list(o.users_collection): c_.objects.unlink(o)
        sem.objects.link(o)
    ls.select_by_collection = True; ls.collection = sem; ls.collection_negation = 'EXCLUSIVE'
c = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(c); c.data.type = 'ORTHO'; c.data.ortho_scale = 2.3; sc.camera = c
alvo = Vector((0, 0, 1.0))
for ang in range(0, 360, 45):
    a = math.radians(ang); d = Vector((math.sin(a), -math.cos(a), 0.0))   # 0° = de frente (câmera em −Y)
    c.location = alvo + d * 8; c.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = os.path.join(OUT, f'ang{ang:03d}.png'); bpy.ops.render.render(write_still=True)
print('VI OK')
