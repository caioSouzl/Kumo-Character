"""Teste 02: o "Kumo 3D desenho" em várias poses, ângulos e expressões de olho.   python poses.py <kumo_desenho.blend> <saída>"""
import bpy, sys, os, math
from mathutils import Vector, Matrix
SRC, OUT = sys.argv[-2:]; os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=SRC); sc = bpy.context.scene
TEXD = '/home/user/Kumo-Character/kumo-3d-rodin/v6-dev/olhos-jogo/texturas'
for im in bpy.data.images:
    if im.name.startswith('olho_') and not os.path.exists(bpy.path.abspath(im.filepath)): im.filepath = os.path.join(TEXD, os.path.basename(im.filepath)); im.reload()
rig = bpy.data.objects['Kumo_Rig']; pb = rig.pose.bones
if rig.animation_data: rig.animation_data.action = None
for o in bpy.data.objects:
    if o.name == 'Kumo_Contorno' or 'Moldura' in o.name: o.hide_render = True
    if o.type == 'MESH':
        for m in o.modifiers:
            if m.type != 'ARMATURE': m.show_render = False
sc.render.engine = 'CYCLES'; sc.cycles.samples = 16; sc.render.film_transparent = True; sc.cycles.transparent_max_bounces = 32
sc.render.resolution_x = sc.render.resolution_y = 700
sc.render.use_freestyle = True; sc.render.line_thickness_mode = 'ABSOLUTE'
vl = bpy.context.view_layer; vl.use_freestyle = True; fs = vl.freestyle_settings
for ls in list(fs.linesets): fs.linesets.remove(ls)
ls = fs.linesets.new('contorno'); ls.select_by_visibility = True; ls.select_by_edge_types = True
for k in ('select_silhouette', 'select_border', 'select_crease', 'select_contour', 'select_external_contour', 'select_material_boundary'): setattr(ls, k, False)
ls.select_silhouette = True; ls.select_border = True; ls.select_external_contour = True
st = ls.linestyle; st.color = (0.03, 0.025, 0.02); st.thickness = 3.6; st.caps = 'ROUND'
sem = bpy.data.collections.new('SemLinha'); sc.collection.children.link(sem)
for o in [o for o in bpy.data.objects if o.name.startswith('KumoJogo_')]:
    for c_ in list(o.users_collection): c_.objects.unlink(o)
    sem.objects.link(o)
ls.select_by_collection = True; ls.collection = sem; ls.collection_negation = 'EXCLUSIVE'
c = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(c); c.data.type = 'ORTHO'; c.data.ortho_scale = 2.5; sc.camera = c
sys.path.insert(0, '/home/user/Kumo-Character/kumo-3d-rodin/v6-dev/ombros/ferramentas'); import ombro_automatico as oa
def reset():
    for b in pb: b.rotation_quaternion = (1, 0, 0, 0); b.rotation_euler = (0, 0, 0); b.location = (0, 0, 0)
    bpy.context.view_layer.update()
def rotw(n, axis, deg):
    b = pb[n]; bpy.context.view_layer.update(); M = b.matrix.copy(); h = M.to_translation()
    b.matrix = Matrix.Translation(h) @ Matrix.Rotation(math.radians(deg), 4, Vector(axis).normalized()) @ Matrix.Translation(-h) @ M; bpy.context.view_layer.update()
def olhos(pE=0, pD=0, gx=0, gy=0):
    pb['controle_olhos'].location = (pE, pD, 0); pb['controle_olhar'].location = (gx, gy, 0); bpy.context.view_layer.update()
def maos(fechar=0.0):
    for sd in 'LR':
        for n in [b.name for b in pb if b.name.startswith('dedo') and b.name.endswith('.' + sd)]:
            pb[n].rotation_mode = 'XYZ'; pb[n].rotation_euler = (math.radians(70 * fechar), 0, 0)
    bpy.context.view_layer.update()
X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)
def braco(sd, erguer=0.0, frente=0.0):
    """giro do braço pelos mesmos eixos das medições do ombro: erguer = para o lado e para cima; frente = para a frente"""
    e, f, _, _ = oa.eixos(rig, sd)
    if erguer: rotw(f'upper_arm.{sd}', e, erguer)
    if frente: rotw(f'upper_arm.{sd}', f, frente)
def cotovelo(sd, graus):
    e, f, _, _ = oa.eixos(rig, sd); rotw(f'forearm.{sd}', e, graus)
def acenar(): braco('R', 85); cotovelo('R', 75); rotw('head', Y, 8); olhos(0, 0, 0.3, 0.2)
def comemorar(): braco('L', 95); braco('R', 95); cotovelo('L', 60); cotovelo('R', 60); maos(1); rotw('head', X, -10); olhos(0, 0, 0, 0.35)
def curioso(): rotw('head', Y, -12); rotw('neck', X, 6); olhos(0, 0, -0.35, 0.25)
def piscando(): rotw('head', Y, 6); olhos(1, 0, 0, 0); braco('L', 45)
def pensativo(): braco('R', 20, 70); cotovelo('R', -100); rotw('head', X, -6); olhos(0.3, 0.3, -0.3, 0.35)
def sonolento(): olhos(0.55, 0.55, 0, -0.2); rotw('head', X, 10); rotw('spine', X, 6)
def apontar(): braco('L', 10, 85); olhos(0, 0, 0.35, 0); rotw('head', Z, 10)
def susto(): braco('L', 70); braco('R', 70); maos(0); rotw('spine', X, -8); olhos(0, 0, 0, 0)
POSES = [('repouso', 0, lambda: None), ('acenar', 20, acenar), ('comemorar', 0, comemorar), ('curioso', 315, curioso), ('piscadela', 30, piscando),
         ('pensativo', 330, pensativo), ('sonolento', 0, sonolento), ('apontar', 45, apontar), ('susto', 340, susto), ('de_lado', 270, lambda: olhos(0, 0, 0.3, 0)),
         ('3-4_costas', 135, lambda: rotw('head', Z, 25)), ('costas', 180, lambda: None)]
for nome, ang, f in POSES:
    reset(); olhos(); maos(0); f()
    for sd in 'LR': oa.aplicar_quadro(rig, sd)
    a = math.radians(ang); d = Vector((math.sin(a), -math.cos(a), 0.0)); alvo = Vector((0, 0, 1.05))
    c.location = alvo + d * 8 + Vector((0, 0, 0.6)); c.rotation_euler = (alvo - c.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = os.path.join(OUT, f'{nome}.png'); bpy.ops.render.render(write_still=True); print('PO', nome, flush=True)
