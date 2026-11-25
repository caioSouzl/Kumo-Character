"""Olhos em calota (semiesfera), pedido do Caio (26/11): o globo branco era uma superfície achatada, a pálpebra
entrava nele e a íris e a pupila se deformavam ao girar. Aqui cada olho é uma calota de esfera apoiada na abertura
da pele, com a íris e a pupila pintadas sobre a calota: o olhar é a calota girando (osso olho.L/R), e a pupila fica
redonda em qualquer direção.
  blender --background kumo_v6_olhos_novos.blend --python src/olhos_domo.py -- <saída.blend> <altura_da_calota_m>
"""
import bpy, sys, json, math, os
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

OUT, H_ARG = sys.argv[-2], float(sys.argv[-1])
AQUI = os.path.dirname(os.path.abspath(__file__))
OLHO = os.path.dirname(AQUI)
INFO = json.load(open(os.path.join(AQUI, 'janelas_v5.json')))
MED = json.load(open(os.path.join(OLHO, 'medicoes_olhos_novos.json')))
V5 = '/home/user/Kumo-Character/kumo-3d-rodin/olhos-v5'
ART = os.path.join(OLHO, 'arte')
BRANCO = np.array([0xF7, 0xF3, 0xEA], np.float32) / 255
BRANCO = np.where(BRANCO <= 0.04045, BRANCO / 12.92, ((BRANCO + 0.055) / 1.055) ** 2.4).astype(np.float32)
ART_C = np.array(MED['arte']['centro_px'], float); ART_R = MED['arte']['raio_externo_px']
NPHI, NTH = 36, 96
rig = bpy.data.objects['Kumo_Rig']; body = bpy.data.objects['Kumo']; pb = rig.pose.bones
for b in pb: b.location = (0, 0, 0); b.rotation_mode = 'XYZ'; b.rotation_euler = (0, 0, 0)
bpy.context.view_layer.update()


def ler(caminho):
    im = bpy.data.images.load(caminho, check_existing=False)
    a = np.array(im.pixels[:], dtype=np.float32).reshape(im.size[1], im.size[0], 4)
    bpy.data.images.remove(im); return a


def amostra(a, x, y):
    h, w = a.shape[:2]
    x = np.asarray(x, np.float64) - 0.5; y = np.asarray(y, np.float64) - 0.5
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int); fx = (x - x0)[..., None]; fy = (y - y0)[..., None]
    def px(xx, yy):
        ok = (xx >= 0) & (xx < w) & (yy >= 0) & (yy < h)
        v = a[np.clip(yy, 0, h - 1), np.clip(xx, 0, w - 1)].copy(); v[~ok] = 0; return v
    return px(x0, y0) * (1 - fx) * (1 - fy) + px(x0 + 1, y0) * fx * (1 - fy) + px(x0, y0 + 1) * (1 - fx) * fy + px(x0 + 1, y0 + 1) * fx * fy


def sobre(fundo, topo):
    at = topo[..., 3:4]; ab = fundo[..., 3:4]; ao = at + ab * (1 - at)
    c = (topo[..., :3] * at + fundo[..., :3] * ab * (1 - at)) / np.maximum(ao, 1e-6)
    return np.concatenate([c, ao], -1)


def lin(c):
    c = np.asarray(c, np.float32); return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


# ---- arte: íris e pupila (uma imagem), anel da membrana (já colorido no pipeline) e o aro da janela
ARTE_IP = ler(os.path.join(ART, 'iris-pupila.png'))
ip = ARTE_IP.copy()
anel = (ip[..., 3] > 0.5) & (ip[..., 0] > 0.5) & (ip[..., 2] < 0.6)
ip[anel, 0:3] = lin(np.array([0xDE, 0x9C, 0x1E], np.float32) / 255)          # anel âmbar escuro (como no olho antigo)
ip[..., :3] = np.where(ip[..., 3:4] > 0.5, ip[..., :3], 0)

RESULT = {}
calotas = {}
# o olho antigo (superfície plana e decal) sai de cena no fim; antes ele vira referência do plano da pele
for s in 'LR':
    o = bpy.data.objects.get(f'KumoOlho.{s}')
    if o: o.name = f'OLD_KumoOlho.{s}'
    d_ = bpy.data.objects.get(f'Decal_Olho.{s}')
    if d_: bpy.data.objects.remove(d_)
for s in 'LR':
    Mw = Matrix(INFO[s]['Mw']); zw = (Mw.to_3x3() @ Vector((0, 0, 1))).normalized()
    e1 = (Mw.to_3x3() @ Vector((1, 0, 0))).normalized(); e1 = (e1 - zw * e1.dot(zw)).normalized(); e2 = zw.cross(e1).normalized()
    mask = ler(os.path.join(V5, 'textures', f'olho_{s}_mask.png'))[..., 3]; MH = mask.shape[0]
    yy, xx = np.nonzero(mask > 0.5); cm = np.array([(xx.mean() + 0.5) / MH, (yy.mean() + 0.5) / MH])
    cov = np.cov(np.vstack([(xx + 0.5) / MH - cm[0], (yy + 0.5) / MH - cm[1]])); ev, evec = np.linalg.eigh(cov)
    EA, EB = 2 * math.sqrt(ev[1]), 2 * math.sqrt(ev[0]); EANG = math.atan2(evec[1, 1], evec[0, 1])
    def rb_at(th):
        t = np.asarray(th) - EANG; return EA * EB / np.sqrt((EB * np.cos(t)) ** 2 + (EA * np.sin(t)) ** 2)
    # ---- aro da abertura na pele: pontos da pele logo fora da abertura (q = 1,03), por raio
    # a pele em volta do olho está quase plana: o plano é o da superfície do olho antigo (vértices da pele, zona do olho)
    pat = bpy.data.objects[f'OLD_KumoOlho.{s}']; Vp = np.array([tuple(pat.matrix_world @ v.co) for v in pat.data.vertices])
    Cp = Vp.mean(0); zarr0 = np.array(tuple(zw))
    ring = []
    for t in np.linspace(0, 2 * math.pi, 96, endpoint=False):
        r = float(rb_at(t))
        p = Mw @ Vector((2 * (cm[0] + r * math.cos(t)) - 1, 2 * (cm[1] + r * math.sin(t)) - 1, 0))
        pn = np.array(tuple(p)); pn = pn - zarr0 * ((pn - Cp) @ zarr0)
        ring.append(pn)
    ring = np.array(ring); Cc = ring.mean(0)
    rel = ring - Cc; zarr = np.array(tuple(zw)); rel_plane = rel - np.outer(rel @ zarr, zarr)
    a = float(np.sqrt((rel_plane ** 2).sum(1)).mean())
    h = H_ARG; R = (a * a + h * h) / (2 * h)
    Cs = Vector(Cc) + zw * (h - R); apex = Vector(Cc) + zw * h
    # ---- malha da calota: anéis de φ (ângulo a partir do polo) e θ
    phimax = math.asin(min(1.0, a / R))
    V = []; F = []
    for i in range(NPHI + 1):
        ph = phimax * i / NPHI
        for j in range(NTH):
            th = 2 * math.pi * j / NTH
            d = e1 * (math.sin(ph) * math.cos(th)) + e2 * (math.sin(ph) * math.sin(th)) + zw * math.cos(ph)
            V.append(Cs + d * R)
    for i in range(NPHI):
        for j in range(NTH):
            a0 = i * NTH + j; a1 = i * NTH + (j + 1) % NTH; b0 = (i + 1) * NTH + j; b1 = (i + 1) * NTH + (j + 1) % NTH
            F.append((a0, a1, b1, b0))
    me = bpy.data.meshes.new(f'KumoOlho.{s}'); me.from_pydata([tuple(v) for v in V], [], F); me.update()
    # UV = janela (espaço da textura), como antes
    uvl = me.uv_layers.new(name='Janela')
    Mi = Mw.inverted()
    U0, U1 = MED[s]['janela_da_textura']
    for lp in me.loops:
        q = Mi @ V[lp.vertex_index]; u, v = (q.x + 1) / 2, (q.y + 1) / 2
        uvl.data[lp.index].uv = ((u - U0) / (U1 - U0), (v - U0) / (U1 - U0))
    # ---- textura da calota: branco do globo + íris e pupila (espaço da janela) + aro da membrana
    RES = 1536
    g = U0 + (np.arange(RES) + 0.5) / RES * (U1 - U0); gx, gy = np.meshgrid(g, g)
    ic = np.array(INFO[s]['iris_centro']); r_med = float(MED[s]['abertura_raio_m_uv']) if 'abertura_raio_m_uv' in MED[s] else float(rb_at(np.linspace(0, 2 * math.pi, 720)).mean()); esc = ART_R / r_med
    ax = ART_C[0] + (gx - ic[0]) * esc; ay = ART_C[1] + (gy - ic[1]) * esc
    tex = np.zeros((RES, RES, 4), np.float32); tex[..., :3] = BRANCO; tex[..., 3] = 1.0
    tex = sobre(tex, amostra(ip, ax, ay))
    aro_img = ler(os.path.join(OLHO, 'texturas', f'olho_{s}_aro.png')) if os.path.exists(os.path.join(OLHO, 'texturas', f'olho_{s}_aro.png')) else None
    if aro_img is not None:
        aro_w = amostra(aro_img, (gx - U0) / (U1 - U0) * aro_img.shape[1], (gy - U0) / (U1 - U0) * aro_img.shape[0])
        tex = sobre(tex, aro_w)
    tex[..., 3] = 1.0
    im = bpy.data.images.new(f'olho_{s}_calota', RES, RES, alpha=False)
    im.pixels.foreach_set(np.ascontiguousarray(tex, np.float32).ravel()); im.update()
    p = os.path.join(OUT.rsplit('/', 1)[0], f'olho_{s}_calota.png'); im.filepath_raw = p; im.file_format = 'PNG'; im.save(); im.filepath = p
    mat = bpy.data.materials.new(f'KumoOlho.{s}'); mat.use_nodes = True; N = mat.node_tree.nodes; L = mat.node_tree.links
    bs = N.get('Principled BSDF'); bs.inputs['Base Color'].default_value = (0, 0, 0, 1); bs.inputs['Roughness'].default_value = 1.0
    bs.inputs['Emission Strength'].default_value = 1.0
    t = N.new('ShaderNodeTexImage'); t.image = im; t.extension = 'EXTEND'; u = N.new('ShaderNodeUVMap'); u.uv_map = 'Janela'
    L.new(u.outputs['UV'], t.inputs['Vector']); L.new(t.outputs['Color'], bs.inputs['Emission Color'])
    me.materials.append(mat)
    ob = bpy.data.objects.new(f'KumoOlho.{s}', me); bpy.context.scene.collection.objects.link(ob)
    ob.parent = rig; am = ob.modifiers.new('Armature', 'ARMATURE'); am.object = rig
    vg = ob.vertex_groups.new(name=f'olho.{s}'); vg.add(range(len(V)), 1.0, 'REPLACE')
    calotas[s] = dict(Cs=Cs, zw=zw, R=R, a=a, h=h, cc=Cc)
    RESULT[s] = {'calota_raio_m': round(R, 4), 'abertura_raio_m': round(a, 4), 'altura_m': h, 'centro': [round(x, 4) for x in Cs]}

# ---- remove o olho antigo (superfície plana) agora que a calota está criada
for s in 'LR':
    o = bpy.data.objects.get(f'OLD_KumoOlho.{s}')
    if o: bpy.data.objects.remove(o)
# (o nome da malha antiga pode ter ficado; mesmo nome agora é a calota)

# ---- ossos: olho.L/R no centro da calota, apontando para fora; alvo do Damped Track à frente
bpy.context.view_layer.objects.active = rig; rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT'); eb = rig.data.edit_bones
for s, d in calotas.items():
    b = eb[f'olho.{s}']; b.head = d['Cs']; b.tail = d['Cs'] + d['zw'] * 0.1; b.use_deform = True   # deforma a calota
    t = eb[f'MCH_alvo_olho.{s}']; t.head = d['Cs'] + d['zw'] * 1.0; t.tail = t.head + d['zw'] * 0.08
bpy.ops.object.mode_set(mode='OBJECT')
json.dump(RESULT, open(os.path.join(os.path.dirname(OUT), 'calotas.json'), 'w'), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print('CALOTA', json.dumps(RESULT))
