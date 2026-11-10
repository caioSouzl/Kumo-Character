"""Kumo — sistema ocular experimental (olhos-v1).

Abre kumo_rigged.blend SOMENTE para leitura e grava uma cópia nova em
olhos-v1/kumo_eyes_exp.blend. Nada da malha da cabeça, dos materiais ou das
texturas aprovadas é alterado: todo o sistema é feito de objetos novos.

Uso:
  python kumo_eyes.py <kumo_rigged.blend> <pasta olhos-v1>

Camadas por olho (de trás para frente, todas recortadas pela "janela" =
contorno exato do olho pintado):
  Kumo_Eye_X        globo/esclera: casca 1,5 mm acima da pele do olho
  Kumo_Iris_X       anel âmbar escuro em volta da pupila   (gira com o olho)
  Kumo_Pupil_X      pupila                                 (gira com o olho)
  Kumo_Catchlight_X brilho, preso ao globo/córnea          (gira com o olho)
  Kumo_LidLow_X     pálpebra inferior (gira no centro do globo)
  Kumo_LidUp_X      pálpebra superior (gira no centro do globo)
"""
import bpy, bmesh, sys, os, math, json, colorsys
import numpy as np
import cv2
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

SRC, OUT = sys.argv[-2], sys.argv[-1]
REPO_TEX = os.path.join(os.path.dirname(os.path.abspath(SRC)), 'textures', 'kumo_quad_diffuse.png')
TEXDIR = os.path.join(OUT, 'textures'); os.makedirs(TEXDIR, exist_ok=True)

K = 1.30            # meia-largura da janela em unidades do raio do olho
NPX = 512           # resolução das camadas
EPS = dict(eye=0.0010, iris=0.0004, pupil=0.0008, catch=0.0012, low=0.0018, up=0.0024)

bpy.ops.wm.open_mainfile(filepath=SRC)
body = bpy.data.objects['Kumo']; rig = bpy.data.objects['Kumo_Rig']; me = body.data
img = bpy.data.images['kumo_quad_diffuse']; img.filepath = REPO_TEX; img.reload()
TW, TH = img.size
TEX = np.array(img.pixels[:], dtype=np.float32).reshape(TH, TW, 4)[:, :, :3]   # sRGB 0..1

def sample_tex(uvs):
    uv = np.asarray(uvs, dtype=np.float32)
    x = uv[:, 0] * TW - 0.5; y = uv[:, 1] * TH - 0.5
    x0 = np.clip(np.floor(x).astype(int), 0, TW - 1); y0 = np.clip(np.floor(y).astype(int), 0, TH - 1)
    x1 = np.clip(x0 + 1, 0, TW - 1); y1 = np.clip(y0 + 1, 0, TH - 1)
    fx = (x - np.floor(x))[:, None]; fy = (y - np.floor(y))[:, None]
    return (TEX[y0, x0] * (1 - fx) * (1 - fy) + TEX[y0, x1] * fx * (1 - fy)
            + TEX[y1, x0] * (1 - fx) * fy + TEX[y1, x1] * fx * fy)

# ---------------------------------------------------------------- malha da cabeça (repouso)
bm_head = bmesh.new(); bm_head.from_mesh(me)
tri_map = bmesh.ops.triangulate(bm_head, faces=bm_head.faces[:])['face_map']
bm_head.faces.ensure_lookup_table()
uv_lay = bm_head.loops.layers.uv.active
head_bvh = BVHTree.FromBMesh(bm_head)
src_bvh = BVHTree.FromPolygons([v.co for v in me.vertices], [p.vertices for p in me.polygons])

def head_hit(origin, d):
    loc, nor, idx, dist = head_bvh.ray_cast(origin, d)
    if loc is None: return None
    f = bm_head.faces[idx]; L = f.loops
    uv = barycentric_transform(loc, L[0].vert.co, L[1].vert.co, L[2].vert.co,
                               L[0][uv_lay].uv.to_3d(), L[1][uv_lay].uv.to_3d(), L[2][uv_lay].uv.to_3d())
    return loc, nor, uv.xy, dist

# ---------------------------------------------------------------- medição do olho pintado
def cls_arr(rgb):
    hsv = cv2.cvtColor((np.clip(rgb, 0, 1) * 255).astype(np.uint8).reshape(-1, 1, 3), cv2.COLOR_RGB2HSV_FULL).reshape(-1, 3) / 255.0
    h, s, v = hsv[:, 0], hsv[:, 1], hsv[:, 2]
    out = np.full(len(h), 0, np.uint8)                       # 0 pele
    out[(h > 0.02) & (h < 0.17) & (s > 0.12) & (v > 0.45)] = 1  # quente (âmbar/creme)
    out[(s < 0.18) & (v > 0.85)] = 2                          # branco (brilho)
    out[v < 0.14] = 3                                         # preto (pupila)
    return out.reshape(rgb.shape[:-1])

vcol = {}
uvl = me.uv_layers.active.data
for p in me.polygons:
    for li in p.loop_indices:
        vcol.setdefault(me.loops[li].vertex_index, []).append(tuple(uvl[li].uv))
vi_all = sorted(vcol)
vrgb = sample_tex([np.mean(vcol[i], axis=0) for i in vi_all])
vcls = dict(zip(vi_all, cls_arr(vrgb.reshape(-1, 1, 3)).ravel()))
adj = {}
for e in me.edges:
    a, b = e.vertices; adj.setdefault(a, []).append(b); adj.setdefault(b, []).append(a)

def measure(side):
    cand = {i for i, v in enumerate(me.vertices) if v.co.z > 1.05 and v.co.x * side > 0.02 and v.co.y < -0.2 and vcls.get(i, 0) > 0}
    best, seen = set(), set()
    for i in cand:
        if i in seen: continue
        comp, st = {i}, [i]; seen.add(i)
        while st:
            k = st.pop()
            for j in adj.get(k, []):
                if j in cand and j not in seen: seen.add(j); comp.add(j); st.append(j)
        if len(comp) > len(best): best = comp
    P = [me.vertices[i].co.copy() for i in best]
    f = sum((me.vertices[i].normal for i in best), Vector()).normalized()
    r = f.cross(Vector((0, 0, 1))).normalized()
    if r.x < 0: r = -r
    w = f.cross(r).normalized()
    if w.z < 0: w = -w
    r = w.cross(f).normalized()          # base ortonormal r,w,f
    o = sum(P, Vector()) / len(P)
    U = [(p - o).dot(r) for p in P]; W = [(p - o).dot(w) for p in P]; D = [(p - o).dot(f) for p in P]
    uc, wc = (max(U) + min(U)) / 2, (max(W) + min(W)) / 2
    a, c = (max(U) - min(U)) / 2, (max(W) - min(W)) / 2
    O = o + r * uc + w * wc + f * max(D)
    return dict(O=O, r=r, w=w, f=f, a=a, c=c, nverts=len(best))

EYES = {'L': measure(1), 'R': measure(-1)}

def to_world(E, u, wv, depth=0.0):
    return E['O'] + E['r'] * (u * E['a']) + E['w'] * (wv * E['c']) + E['f'] * depth

# ---------------------------------------------------------------- amostragem da textura na janela
def pushpull(rgb, valid):
    """Preenchimento suave (sem estrias): média ponderada em pirâmide."""
    lv = [(rgb * valid[..., None], valid.astype(np.float32))]
    while lv[-1][1].shape[0] > 2:
        c, w = lv[-1]; h = (c.shape[0] // 2, c.shape[1] // 2)
        lv.append((cv2.resize(c, h[::-1], interpolation=cv2.INTER_AREA), cv2.resize(w, h[::-1], interpolation=cv2.INTER_AREA)))
    fill = lv[-1][0] / np.maximum(lv[-1][1], 1e-6)[..., None]
    for c, w in reversed(lv[:-1]):
        up = cv2.resize(fill, (c.shape[1], c.shape[0]), interpolation=cv2.INTER_LINEAR)
        ww = np.clip(w * 4, 0, 1)[..., None]
        fill = (c / np.maximum(w, 1e-6)[..., None]) * ww + up * (1 - ww)
    return np.where(valid[..., None] > 0, rgb, fill)

def sample(E, KK):
    gg = (np.arange(NPX) + 0.5) / NPX * 2 * KK - KK
    rgb = np.zeros((NPX, NPX, 3), np.float32); hit = np.zeros((NPX, NPX), bool)
    uvs, idx = [], []
    for j, wv in enumerate(gg):
        for i, u in enumerate(gg):
            h = head_hit(to_world(E, u, wv, 0.4), -E['f'])
            if h is None: continue
            uvs.append(h[2]); idx.append((j, i))
    col = sample_tex(uvs)
    for (j, i), cc in zip(idx, col): rgb[j, i] = cc; hit[j, i] = True
    cl = cls_arr(rgb); cl[~hit] = 0
    eye = (cl > 0).astype(np.uint8)
    n, lab = cv2.connectedComponents(eye, connectivity=8)
    pup = (cl == 3)
    best = max(range(1, n), key=lambda k: int(((lab == k) & pup).sum()))
    eye = (lab == best).astype(np.uint8)
    ff = eye.copy(); m2 = np.zeros((NPX + 2, NPX + 2), np.uint8); cv2.floodFill(ff, m2, (0, 0), 1)
    return gg, rgb, hit, cl, eye | (1 - ff)

g = None
layers = {}
for tag, E in EYES.items():
    # 1) janela larga para achar o contorno real; 2) reenquadra pelo contorno
    gg, _, _, _, eye0 = sample(E, 2.6)
    ys, xs = np.nonzero(eye0)
    u0, u1, w0, w1 = gg[xs.min()], gg[xs.max()], gg[ys.min()], gg[ys.max()]
    E['O'] = to_world(E, (u0 + u1) / 2, (w0 + w1) / 2, 0)
    E['a'] *= (u1 - u0) / 2; E['c'] *= (w1 - w0) / 2
    g, rgb, hit, cl, eye = sample(E, K)
    k3 = np.ones((3, 3), np.uint8)
    P = ((cl == 3) & (eye > 0)).astype(np.uint8)
    nP, labP = cv2.connectedComponents(P); P = (labP == max(range(1, nP), key=lambda k: (labP == k).sum())).astype(np.uint8)
    Wt = ((cl == 2) & (eye > 0)).astype(np.uint8)
    P2 = P | (Wt & cv2.dilate(P, k3, iterations=6))          # pupila inteira sob o brilho
    ff = P2.copy(); m2 = np.zeros((NPX + 2, NPX + 2), np.uint8); cv2.floodFill(ff, m2, (0, 0), 1); P2 = P2 | (1 - ff)
    ys, xs = np.nonzero(P); pc = (xs.mean(), ys.mean()); ph = ((xs.max() - xs.min()) / 2 + 1, (ys.max() - ys.min()) / 2 + 1)
    yy, xx = np.mgrid[0:NPX, 0:NPX]
    I = ((((xx - pc[0]) / (ph[0] * 1.45)) ** 2 + ((yy - pc[1]) / (ph[1] * 1.25)) ** 2) < 1).astype(np.uint8) & eye
    def soft(m, px=1.2): return cv2.GaussianBlur(m.astype(np.float32), (0, 0), px)
    hv = cv2.cvtColor((np.clip(rgb, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2HSV_FULL) / 255.0
    pupil_col = np.median(rgb[P > 0], axis=0)
    pupil_rgb = np.where(P[..., None] > 0, rgb, pupil_col)
    iris_rgb = pushpull(rgb, (I & (1 - cv2.dilate(P2 | Wt, k3, iterations=2))).astype(np.float32))
    sclera_rgb = pushpull(rgb, (eye & (1 - cv2.dilate(I | P2 | Wt, k3, iterations=3))).astype(np.float32))
    ring = cv2.dilate(eye, k3, iterations=18) & (1 - cv2.dilate(eye, k3, iterations=4)) & hit.astype(np.uint8)
    green = ((hv[..., 0] > 0.17) & (hv[..., 0] < 0.45) & (hv[..., 1] > 0.25) & (hv[..., 2] > 0.25)).astype(np.uint8)
    skin_rgb = pushpull(rgb, (ring & green).astype(np.float32))
    skin_rgb = cv2.GaussianBlur(skin_rgb, (0, 0), 6)
    lidm = cv2.dilate(eye, np.ones((5, 5), np.uint8), iterations=2)          # pálpebra cobre a borda pintada
    fb = soft(cv2.dilate(eye, k3, iterations=2), 1.5)[..., None]
    skin_rgb = skin_rgb * fb + rgb * (1 - fb)                               # fora do olho: textura real (invisível em repouso)
    eye_a = soft(eye, 0.8)
    L = {
        'mask':   (np.dstack([eye_a] * 3), eye_a),
        'eye':    (sclera_rgb, eye_a),
        'iris':   (iris_rgb, soft(I, 2.0)),
        'pupil':  (pupil_rgb, soft(cv2.dilate(P2, k3), 0.8)),
        'catch':  (rgb, soft(cv2.dilate(Wt, k3), 0.8)),
        'skin':   (skin_rgb, np.ones((NPX, NPX), np.float32)),
        'lidmask': (np.dstack([soft(lidm, 0.8)] * 3), soft(lidm, 0.8)),
    }
    for nm, (c3, al) in L.items():
        out = np.dstack([np.clip(c3, 0, 1), np.clip(al, 0, 1)])
        out = (np.flipud(out) * 255 + 0.5).astype(np.uint8)       # linha 0 = topo da imagem
        cv2.imwrite(os.path.join(TEXDIR, f'olho_{tag}_{nm}.png'), cv2.cvtColor(out, cv2.COLOR_RGBA2BGRA))
    P = P2
    # faces da cabeça cobertas pelo olho (para a casca), crescidas 2 anéis
    # casca = só a camada mais externa vista de frente (sem dobras da borda da órbita)
    fset = set()
    for j, i in zip(*np.nonzero(cv2.dilate(eye, np.ones((9, 9), np.uint8), iterations=5))):
        org = to_world(E, g[i], g[j], 0.4)
        loc, nor, fi, dist = src_bvh.ray_cast(org, -E['f'])
        if fi is not None and me.polygons[fi].normal.dot(E['f']) > 0.05: fset.add(fi)
    def colrow(m):           # extensão do olho por coluna u: topo e base em unidades de parâmetro
        top = np.full(NPX, -9.0); bot = np.full(NPX, 9.0)
        for i in range(NPX):
            js = np.nonzero(m[:, i])[0]
            if len(js): top[i] = g[js.max()]; bot[i] = g[js.min()]
        return top, bot
    top, bot = colrow(eye)
    layers[tag] = dict(eye=eye, P=P, I=I, Wt=Wt, faces=sorted(fset), top=top, bot=bot,
                       pupil_c=(float(g[int(pc[0])]), float(g[int(pc[1])])),
                       pupil_h=(float(ph[0] * 2 * K / NPX), float(ph[1] * 2 * K / NPX)),
                       catch_px=int(Wt.sum()), eye_px=int(eye.sum()))

# ---------------------------------------------------------------- utilidades de objeto/material
def link(obj):
    bpy.context.scene.collection.objects.link(obj); return obj

def load_img(tag, nm):
    p = os.path.join(TEXDIR, f'olho_{tag}_{nm}.png')
    im = bpy.data.images.load(p, check_existing=True); im.name = f'olho_{tag}_{nm}'
    return im

def coord_from_object(nt, obj):
    tc = nt.nodes.new('ShaderNodeTexCoord'); tc.object = obj
    mp = nt.nodes.new('ShaderNodeMapping'); mp.vector_type = 'POINT'
    mp.inputs['Location'].default_value = (0.5, 0.5, 0); mp.inputs['Scale'].default_value = (0.5, 0.5, 1)
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector']); return mp.outputs['Vector']

def coord_uv(nt):
    return nt.nodes.new('ShaderNodeUVMap').outputs['UV']

def tex(nt, im, vec):
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = im; t.extension = 'CLIP'; t.interpolation = 'Linear'
    nt.links.new(vec, t.inputs['Vector']); return t

def layer_material(name, color_img, color_vec_fn, alpha_img, alpha_vec_fn, clip_img, clip_obj, lash=None):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); em = nt.nodes.new('ShaderNodeEmission')
    tr = nt.nodes.new('ShaderNodeBsdfTransparent'); mix = nt.nodes.new('ShaderNodeMixShader')
    ct = tex(nt, color_img, color_vec_fn(nt)); color = ct.outputs['Color']
    at = tex(nt, alpha_img, alpha_vec_fn(nt)) if alpha_img is not color_img or alpha_vec_fn is not color_vec_fn else ct
    clip = tex(nt, clip_img, coord_from_object(nt, clip_obj))
    a1 = nt.nodes.new('ShaderNodeMath'); a1.operation = 'MULTIPLY'
    nt.links.new(at.outputs['Alpha'], a1.inputs[0]); nt.links.new(clip.outputs['Alpha'], a1.inputs[1])
    if lash is not None:     # faixa escura (cílio) perto da borda da pálpebra: UV.y = distância à borda
        sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(coord_uv(nt), sep.inputs[0])
        lt = nt.nodes.new('ShaderNodeMath'); lt.operation = 'LESS_THAN'; lt.inputs[1].default_value = lash[0]
        nt.links.new(sep.outputs['Y'], lt.inputs[0])
        mc = nt.nodes.new('ShaderNodeMix'); mc.data_type = 'RGBA'
        nt.links.new(lt.outputs[0], mc.inputs['Factor']); nt.links.new(color, mc.inputs['A'])
        mc.inputs['B'].default_value = lash[1]; color = mc.outputs['Result']
    nt.links.new(color, em.inputs['Color']); em.inputs['Strength'].default_value = 1.0
    nt.links.new(a1.outputs[0], mix.inputs['Fac'])
    nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs['Surface'])
    return m

def frame_matrix(E, centre=None):
    R = Matrix((E['r'], E['w'], E['f'])).transposed().to_4x4()
    return Matrix.Translation(centre or E['O']) @ R @ Matrix.Diagonal((E['a'] * K, E['c'] * K, 1, 1))

def bone_parent(obj, bone):
    mw = obj.matrix_world.copy()
    obj.parent = rig; obj.parent_type = 'BONE'; obj.parent_bone = bone
    bpy.context.view_layer.update(); obj.matrix_world = mw

# ---------------------------------------------------------------- ossos
LASH = tuple(bpy.data.materials['Kumo_Lash'].node_tree.nodes['Emission'].inputs['Color'].default_value)
bpy.context.view_layer.objects.active = rig
for o in bpy.context.selected_objects: o.select_set(False)
rig.select_set(True); bpy.ops.object.mode_set(mode='EDIT')
ebs = rig.data.edit_bones; headb = ebs['head']
for tag, E in EYES.items():
    Re = 1.25 * max(E['a'], E['c'])                  # raio do globo (pivô de olhar e pálpebras)
    E['R'] = Re; E['C'] = E['O'] - E['f'] * Re
    for bn in ('eye', 'lid_up', 'lid_low'):
        b = ebs.new(f'{bn}.{tag}'); b.head = E['C']; b.tail = E['C'] + E['f'] * 0.12
        b.align_roll(E['w']); b.parent = headb; b.use_deform = False
tgt = ebs.new('eye_target'); tc = (EYES['L']['C'] + EYES['R']['C']) / 2
tgt.head = tc + Vector((0, -0.9, 0)); tgt.tail = tgt.head + Vector((0, 0, 0.12)); tgt.roll = 0
tgt.parent = headb; tgt.use_deform = False
for tag, E in EYES.items():
    t = ebs.new(f'eye_target.{tag}'); t.head = E['C'] + E['f'] * 0.9; t.tail = t.head + Vector((0, 0, 0.06))
    t.parent = tgt; t.use_deform = False
bpy.ops.object.mode_set(mode='OBJECT')
bones = rig.data.bones
for tag, E in EYES.items():
    E['sx'] = 1.0 if bones[f'lid_up.{tag}'].matrix_local.col[0].xyz.dot(E['r']) > 0 else -1.0
# eixo local do eye_target que aponta para cima no mundo
tm = bones['eye_target'].matrix_local.to_3x3()
up_axis = max(range(3), key=lambda k: abs(tm.col[k].dot(Vector((0, 0, 1)))))
up_sign = 1.0 if tm.col[up_axis].dot(Vector((0, 0, 1))) > 0 else -1.0

for pb in rig.pose.bones:
    if pb.name.split('.')[0] in ('eye', 'lid_up', 'lid_low'): pb.rotation_mode = 'XYZ'
for tag in EYES:
    c = rig.pose.bones[f'eye.{tag}'].constraints.new('DAMPED_TRACK')
    c.target = rig; c.subtarget = f'eye_target.{tag}'; c.track_axis = 'TRACK_Y'
# cores de grupo/coleção para os novos ossos
for bn in [b.name for b in bones if b.name.split('.')[0] in ('eye', 'lid_up', 'lid_low', 'eye_target')]:
    rig.pose.bones[bn].color.palette = 'THEME09'

# ---------------------------------------------------------------- objetos
_outl = [m for m in body.modifiers if m.type in ('SOLIDIFY', 'VERTEX_WEIGHT_MIX', 'MASK')]
for _m in _outl: _m.show_viewport = False
bpy.context.view_layer.update()
_dg = bpy.context.evaluated_depsgraph_get(); body_bvh = BVHTree.FromObject(body.evaluated_get(_dg), _dg)
for _m in _outl: _m.show_viewport = True
_DIRS = [Vector((0.3127, 0.5469, 0.7768)).normalized(), Vector((-0.6712, 0.2214, -0.7072)).normalized()]
def inside_body(p):
    votes = 0
    for d in _DIRS:
        n, o = 0, p.copy()
        for _ in range(64):
            loc, nor, i, dist = body_bvh.ray_cast(o, d)
            if loc is None: break
            n += 1; o = loc + d * 1e-6
        votes += n % 2
    return votes == 2
def push_out(p, axis, margin=0.0004):
    """Guarda final: se o ponto ficou dentro da cabeça, empurra ao longo do eixo até sair (com folga)."""
    k = 0
    while inside_body(p) and k < 40: p = p + axis * 0.0005; k += 1
    if k: p = p + axis * margin
    return p, k
PUSHED = {}
created = []
def mesh_obj(name, verts, faces, uvs=None):
    m = bpy.data.meshes.new(name); m.from_pydata(verts, [], faces); m.update()
    if uvs is not None:
        ul = m.uv_layers.new(name='UVMap')
        for p in m.polygons:
            for li in p.loop_indices: ul.data[li].uv = uvs[m.loops[li].vertex_index]
    o = link(bpy.data.objects.new(name, m)); created.append(name); return o

for tag, E in EYES.items():
    Ly = layers[tag]
    # janela fixa (presa ao osso da cabeça) e referência de olhar (presa ao osso do olho)
    win = link(bpy.data.objects.new(f'Kumo_EyeWindow_{tag}', None)); win.empty_display_type = 'CUBE'
    win.empty_display_size = 1.0; win.matrix_world = frame_matrix(E); bone_parent(win, 'head'); created.append(win.name)
    im = {nm: load_img(tag, nm) for nm in ('mask', 'eye', 'iris', 'pupil', 'catch', 'skin', 'lidmask')}

    # --- globo / esclera: casca sobre a pele do olho, deformada pela mesma armadura
    fset = Ly['faces']; vs = sorted({v for fi in fset for v in me.polygons[fi].vertices}); vmap = {v: k for k, v in enumerate(vs)}
    verts = []
    for v in vs:
        q, k = push_out(me.vertices[v].co + me.vertices[v].normal * EPS['eye'], me.vertices[v].normal)
        verts.append(q); PUSHED[f'casca_{tag}'] = PUSHED.get(f'casca_{tag}', 0) + (k > 0)
    faces = [[vmap[v] for v in me.polygons[fi].vertices] for fi in fset]
    # vértice que continua dentro da cabeça mesmo após o empurrão: só existe na margem fora do contorno; sai da casca
    eyed = cv2.dilate(Ly['eye'], k3, iterations=4)
    def in_mask(p):
        q = p - E['O']; u, wv = q.dot(E['r']) / E['a'], q.dot(E['w']) / E['c']
        i = int((u + K) / (2 * K) * NPX); j = int((wv + K) / (2 * K) * NPX)
        return 0 <= i < NPX and 0 <= j < NPX and eyed[j, i] > 0
    bad = {k for k, q in enumerate(verts) if inside_body(q)}
    assert not any(in_mask(verts[k]) for k in bad), 'vértice da casca dentro da cabeça DENTRO do contorno'
    faces = [f_ for f_ in faces if not any(k in bad for k in f_)]
    PUSHED[f'casca_{tag}_vertices_removidos_da_margem'] = len(bad)
    shell = mesh_obj(f'Kumo_Eye_{tag}', verts, faces)
    bpy.context.view_layer.objects.active = shell
    for o_ in bpy.context.selected_objects: o_.select_set(False)
    shell.select_set(True); bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.mesh.select_loose(); bpy.ops.mesh.delete(type='VERT'); bpy.ops.object.mode_set(mode='OBJECT')
    for vg in body.vertex_groups:
        if vg.name in ('outline_cut', 'outline_shell'): continue
        ng = shell.vertex_groups.new(name=vg.name)
        for v in vs:
            for gg in me.vertices[v].groups:
                if gg.group == vg.index and gg.weight > 0: ng.add([vmap[v]], gg.weight, 'REPLACE')
    shell.parent = rig; am = shell.modifiers.new('Armature', 'ARMATURE'); am.object = rig
    shell.data.materials.append(layer_material(f'Kumo_Eye_{tag}', im['eye'], lambda nt, w=win: coord_from_object(nt, w),
                                               im['eye'], lambda nt, w=win: coord_from_object(nt, w), im['mask'], win))
    for p in shell.data.polygons: p.use_smooth = True
    sb = BVHTree.FromPolygons(verts, faces)

    def on_shell(u, wv, extra):
        org = to_world(E, u, wv, 0.4)
        loc, nor, fi, dist = sb.ray_cast(org, -E['f'])
        if loc is None:
            h = head_hit(org, -E['f'])
            return (h[0] + h[1] * (EPS['eye'] + extra)) if h else to_world(E, u, wv, 0)
        return loc + nor * extra

    def patch(name, u0, u1, w0, w1, n, extra, bone, layer, depth_off):
        verts, uvs, faces = [], [], []
        for j in range(n + 1):
            for i in range(n + 1):
                u = u0 + (u1 - u0) * i / n; wv = w0 + (w1 - w0) * j / n
                verts.append(on_shell(u, wv, extra)); uvs.append(((u / K + 1) / 2, (wv / K + 1) / 2))
        for j in range(n):
            for i in range(n):
                a = j * (n + 1) + i; faces.append([a, a + 1, a + n + 2, a + n + 1])
        o = mesh_obj(name, verts, faces, uvs)
        sw = o.modifiers.new('Shrinkwrap', 'SHRINKWRAP'); sw.target = shell
        sw.wrap_method = 'NEAREST_SURFACEPOINT'; sw.wrap_mode = 'ABOVE_SURFACE'; sw.offset = depth_off
        o.data.materials.append(layer_material(name, im[layer], coord_uv, im[layer], coord_uv, im['mask'], win))
        for p in o.data.polygons: p.use_smooth = True
        bone_parent(o, bone); return o

    def bbox(m, marg):
        ys, xs = np.nonzero(m)
        return (g[xs.min()] - marg, g[xs.max()] + marg, g[ys.min()] - marg, g[ys.max()] + marg)
    # íris, pupila e brilho: cascas fixas que copiam a córnea (nunca entram na cabeça);
    # o que gira é a projeção delas, presa ao osso eye.X através do vazio Kumo_EyeGaze_X
    gaze = link(bpy.data.objects.new(f'Kumo_EyeGaze_{tag}', None)); gaze.empty_display_type = 'SPHERE'
    gaze.empty_display_size = 0.15; gaze.matrix_world = frame_matrix(E); bone_parent(gaze, f'eye.{tag}'); created.append(gaze.name)
    def layer_shell(name, layer, extra):
        sm = shell.data; V = []
        for v in sm.vertices:
            q, k = push_out(v.co + v.normal * extra, v.normal); V.append(q)
            if k: PUSHED[name] = PUSHED.get(name, 0) + 1
        o = mesh_obj(name, V, [list(pp.vertices) for pp in sm.polygons])
        for vg in shell.vertex_groups:
            ng = o.vertex_groups.new(name=vg.name)
            for v in sm.vertices:
                for gg in v.groups:
                    if gg.group == vg.index: ng.add([v.index], gg.weight, 'REPLACE')
        o.parent = rig; am = o.modifiers.new('Armature', 'ARMATURE'); am.object = rig
        o.data.materials.append(layer_material(name, im[layer], lambda nt, gz=gaze: coord_from_object(nt, gz),
                                               im[layer], lambda nt, gz=gaze: coord_from_object(nt, gz), im['mask'], win))
        for pp in o.data.polygons: pp.use_smooth = True
        return o
    layer_shell(f'Kumo_Iris_{tag}', 'iris', EPS['iris'])
    layer_shell(f'Kumo_Pupil_{tag}', 'pupil', EPS['pupil'])
    layer_shell(f'Kumo_Catchlight_{tag}', 'catch', EPS['catch'])

    # --- pálpebras: casca deslizante em 21 estágios ao longo do arco de rotação em torno do globo
    # BVHs com a MESMA triangulação que o Blender renderiza (looptris)
    dg = bpy.context.evaluated_depsgraph_get()
    shell_bvh = BVHTree.FromObject(shell.evaluated_get(dg), dg)
    def place(u, wv, off):
        """Ponto da superfície do olho (ou da pele, fora da casca) em (u, w), afastado 'off' para fora."""
        org = to_world(E, u, wv, 0.4)
        loc, nor, fi, dist = shell_bvh.ray_cast(org, -E['f'])
        if loc is not None: return loc + nor * off
        loc, nor, fi, dist = body_bvh.ray_cast(org, -E['f'])
        if loc is not None: return loc + nor * (EPS['eye'] + off)
        return None
    def to_param(p):
        q = p - E['O']; return q.dot(E['r']) / E['a'], q.dot(E['w']) / E['c']

    NST = 40
    def lid(name, upper, extra, bone):
        nu, nv = 44, 18
        H = (K + 0.25) - (-0.30) if upper else (0.10 + K + 0.25)
        def w_edge_closed(u): return w_close_up(u) if upper else w_close_low(u)
        # borda fechada em 3D e ângulo de abertura (rotação em torno do centro do globo)
        us = [-K + 2 * K * i / nu for i in range(nu + 1)]
        edge3 = [place(u, w_edge_closed(u), 0.0) or to_world(E, u, w_edge_closed(u), 0) for u in us]
        lim = Ly['top'] if upper else Ly['bot']
        def edge_at(ang):
            Mx = Matrix.Translation(C) @ Matrix.Rotation(ang, 4, rax) @ Matrix.Translation(-C)
            return [to_param(Mx @ p) for p in edge3]
        def clear(ang):
            for u, wv in edge_at(ang):
                i = int(round((u + K) / (2 * K) * NPX - 0.5))
                if 0 <= i < NPX and lim[i] > -8:
                    if upper and wv < lim[i] + 0.10: return False
                    if not upper and wv > lim[i] - 0.10: return False
            return True
        step = math.radians(0.25) * (-1 if upper else 1)   # + em torno de r desce os pontos
        ang = 0.0
        while not clear(ang) and abs(ang) < math.radians(120): ang += step
        theta = -ang                                       # ângulo (em torno de r) que FECHA a pálpebra
        def stage(t):                                      # t = 0 aberto ... 1 fechado
            E2 = edge_at(ang * (1 - t))
            V = []
            for j in range(nv + 1):
                d = H * (j / nv) ** 1.2
                for i in range(nu + 1):
                    u2, we = E2[i]; wv = we + d if upper else we - d
                    p = place(u2, wv, extra)
                    p = p if p is not None else to_world(E, u2, wv, 0)
                    p, k = push_out(p, E['f']); V.append(p)
                    if k: PUSHED[name] = PUSHED.get(name, 0) + 1
            return V
        STG = [stage(k / NST) for k in range(NST + 1)]
        # reparo das cordas: entre dois estágios a shape key interpola em linha reta; onde essa
        # reta passaria abaixo da superfície (degrau na borda da órbita), ergue os dois estágios ao longo de f
        def surf_h(p):
            u2, w2 = to_param(p); org = to_world(E, u2, w2, 0.4)
            hs = []
            for bv, add in ((shell_bvh, 0.0), (body_bvh, EPS['eye'])):
                loc, nor, fi, dist = bv.ray_cast(org, -E['f'])
                if loc is not None: hs.append((loc - E['O']).dot(E['f']) + add)
            return max(hs) if hs else None
        lifted = 0
        for _pass in range(4):
            changed = False
            for k in range(NST):
                A, B = STG[k], STG[k + 1]
                for vi in range(len(A)):
                    if (A[vi] - B[vi]).length < 1e-6: continue
                    worst = 0.0
                    for f_ in (0.25, 0.5, 0.75):
                        q = A[vi].lerp(B[vi], f_); hs = surf_h(q)
                        if hs is None: continue
                        need = hs + extra * 0.6 - (q - E['O']).dot(E['f'])
                        worst = max(worst, need)
                    if worst > 1e-5:
                        A[vi] = A[vi] + E['f'] * (worst + 0.0002); B[vi] = B[vi] + E['f'] * (worst + 0.0002)
                        changed = True; lifted += 1
            if not changed: break
        PUSHED[name + '_cordas_erguidas'] = lifted
        V0 = STG[0]
        faces, uvs = [], []
        for j in range(nv + 1):
            for i in range(nu + 1): uvs.append((us[i], H * (j / nv) ** 1.2))
        for j in range(nv):
            for i in range(nu):
                a = j * (nu + 1) + i
                faces.append([a, a + 1, a + nu + 2, a + nu + 1] if upper else [a, a + nu + 1, a + nu + 2, a + 1])
        o = mesh_obj(name, V0, faces, uvs)
        o.shape_key_add(name='Aberto', from_mix=False)
        for k in range(1, NST + 1):
            sk = o.shape_key_add(name=f'Fecha_{k * 100 // NST:03d}', from_mix=False)
            for vi, p in enumerate(STG[k]): sk.data[vi].co = p
            # driver: estágio escolhido pela rotação do osso da pálpebra (pivô no centro do globo)
            fc = sk.driver_add('value'); d = fc.driver; d.type = 'SCRIPTED'
            v = d.variables.new(); v.name = 'a'; v.type = 'TRANSFORMS'
            v.targets[0].id = rig; v.targets[0].bone_target = bone
            v.targets[0].transform_type = 'ROT_X'; v.targets[0].transform_space = 'LOCAL_SPACE'
            v.targets[0].rotation_mode = 'XYZ'
            tt = f'(a*{E["sx"]:.1f}/{theta:.6f}*{NST})'
            d.expression = (f'max(0.0,1.0-abs({tt}-{k}))' if k < NST else f'min(1.0,max(0.0,{tt}-{NST - 1}))')
            sk.slider_min = 0.0; sk.slider_max = 1.0
        # mesma pele que está embaixo: pesos copiados do vértice mais próximo da cabeça
        for vg in body.vertex_groups:
            if vg.name not in ('outline_cut', 'outline_shell'): o.vertex_groups.new(name=vg.name)
        from mathutils.interpolate import poly_3d_calc
        for vi, p in enumerate(V0):        # pesos interpolados da pele logo abaixo (não do vértice mais próximo)
            loc, nor, fi, dist = src_bvh.find_nearest(p)
            pvs = list(me.polygons[fi].vertices); bw = poly_3d_calc([me.vertices[k].co for k in pvs], loc)
            acc = {}
            for k, b_ in zip(pvs, bw):
                for gg in me.vertices[k].groups:
                    nm = body.vertex_groups[gg.group].name
                    if nm in o.vertex_groups: acc[nm] = acc.get(nm, 0.0) + b_ * gg.weight
            for nm, wgt in acc.items():
                if wgt > 1e-4: o.vertex_groups[nm].add([vi], wgt, 'REPLACE')
        o.parent = rig; am = o.modifiers.new('Armature', 'ARMATURE'); am.object = rig
        lash = (0.055, LASH) if upper else (0.025, tuple(0.5 * x + 0.5 * y for x, y in zip(LASH, (0.2, 0.25, 0.1, 1))))
        o.data.materials.append(layer_material(name, im['skin'], lambda nt, w=win: coord_from_object(nt, w),
                                               im['lidmask'], lambda nt, w=win: coord_from_object(nt, w), im['lidmask'], win, lash=lash))
        for p in o.data.polygons: p.use_smooth = True
        return o, theta
    C, rax = E['C'], E['r']
    def w_close_up(u):  return -0.18 - 0.12 * (1 - min(1, (u / 1.1) ** 2))
    def w_close_low(u): return w_close_up(u) + 0.08
    _, E['theta_up'] = lid(f'Kumo_LidUp_{tag}', True, EPS['up'], f'lid_up.{tag}')
    _, E['theta_low'] = lid(f'Kumo_LidLow_{tag}', False, EPS['low'], f'lid_low.{tag}')

# ---------------------------------------------------------------- guarda de colisão (depois da armadura)
# cópia oculta da pele da cabeça (só armadura, sem o contorno) usada como alvo; a malha original não é tocada
hv = [v.index for v in me.vertices if v.co.z > 1.0]
hvs = set(hv); hmap = {v: k for k, v in enumerate(hv)}
hfaces = [[hmap[v] for v in p.vertices] for p in me.polygons if all(v in hvs for v in p.vertices)]
proxy = mesh_obj('Kumo_Olhos_ColisaoPele', [me.vertices[v].co.copy() for v in hv], hfaces)
for vg in body.vertex_groups:
    if vg.name in ('outline_cut', 'outline_shell'): continue
    ng = proxy.vertex_groups.new(name=vg.name)
    for v in hv:
        for gg in me.vertices[v].groups:
            if gg.group == vg.index and gg.weight > 0: ng.add([hmap[v]], gg.weight, 'REPLACE')
proxy.parent = rig; am = proxy.modifiers.new('Armature', 'ARMATURE'); am.object = rig
proxy.hide_render = True; proxy.display_type = 'WIRE'
# segunda cópia: pele com a superfície do globo nas regiões dos olhos (alvo das camadas e pálpebras)
eye_vs = set()
for tag in EYES:
    for fi in layers[tag]['faces']: eye_vs.update(me.polygons[fi].vertices)
proxy2 = mesh_obj('Kumo_Olhos_ColisaoGlobo', [me.vertices[v].co + (me.vertices[v].normal * EPS['eye'] if v in eye_vs else Vector())
                                              for v in hv], hfaces)
for vg in proxy.vertex_groups:
    ng = proxy2.vertex_groups.new(name=vg.name)
for v in hv:
    for gg in me.vertices[v].groups:
        nm = body.vertex_groups[gg.group].name
        if nm in proxy2.vertex_groups and gg.weight > 0: proxy2.vertex_groups[nm].add([hmap[v]], gg.weight, 'REPLACE')
proxy2.parent = rig; am = proxy2.modifiers.new('Armature', 'ARMATURE'); am.object = rig
proxy2.hide_render = True; proxy2.display_type = 'WIRE'
GUARD = {'Iris': 0.0003, 'Pupil': 0.0006, 'Catchlight': 0.0009, 'LidLow': 0.0013, 'LidUp': 0.0017}
for tag in EYES:
    # globo: só os vértices dentro do contorno visível, contra a pele
    sh = bpy.data.objects[f'Kumo_Eye_{tag}']; E = EYES[tag]; eyem = cv2.dilate(layers[tag]['eye'], k3, iterations=3)
    gv = sh.vertex_groups.new(name='guarda_visivel')
    for v in sh.data.vertices:
        q = v.co - E['O']; u, wv = q.dot(E['r']) / E['a'], q.dot(E['w']) / E['c']
        i = int((u + K) / (2 * K) * NPX); j = int((wv + K) / (2 * K) * NPX)
        if 0 <= i < NPX and 0 <= j < NPX and eyem[j, i]: gv.add([v.index], 1.0, 'REPLACE')
    sw = sh.modifiers.new('GuardaColisao', 'SHRINKWRAP'); sw.target = proxy; sw.vertex_group = 'guarda_visivel'
    sw.wrap_method = 'NEAREST_SURFACEPOINT'; sw.wrap_mode = 'OUTSIDE'; sw.offset = 0.0006
    for part, off in GUARD.items():
        o = bpy.data.objects.get(f'Kumo_{part}_{tag}')
        if o is None: continue
        sw = o.modifiers.new('GuardaColisao', 'SHRINKWRAP'); sw.target = proxy2
        sw.wrap_method = 'NEAREST_SURFACEPOINT'; sw.wrap_mode = 'OUTSIDE'; sw.offset = off
# ---------------------------------------------------------------- controles e drivers
hp = rig.pose.bones['head']
PROPS = {'piscar': 'Piscar os dois olhos (0 aberto, 1 fechado)',
         'piscar_E': 'Piscar só o olho esquerdo do Kumo', 'piscar_D': 'Piscar só o olho direito do Kumo',
         'fechar_parcial_E': 'Semicerrar o olho esquerdo', 'fechar_parcial_D': 'Semicerrar o olho direito',
         'acompanhar_olhar': 'Quanto as pálpebras acompanham o olhar vertical'}
for k, desc in PROPS.items():
    hp[k] = 0.5 if k == 'acompanhar_olhar' else 0.0
    ui = hp.id_properties_ui(k); ui.update(min=0.0, max=1.0, soft_min=0.0, soft_max=1.0, description=desc)
D_TGT = 0.9
AX = 'XYZ'[up_axis]
for tag, E in EYES.items():
    side = 'E' if tag == 'L' else 'D'
    for bn, th, sgn in ((f'lid_up.{tag}', E['theta_up'], 1), (f'lid_low.{tag}', E['theta_low'], 1)):
        pb = rig.pose.bones[bn]
        fc = pb.driver_add('rotation_euler', 0); d = fc.driver; d.type = 'SCRIPTED'
        for vn, prop in (('p', 'piscar'), ('pe', f'piscar_{side}'), ('fp', f'fechar_parcial_{side}'), ('ac', 'acompanhar_olhar')):
            v = d.variables.new(); v.name = vn; v.type = 'SINGLE_PROP'
            v.targets[0].id = rig; v.targets[0].data_path = f'pose.bones["head"]["{prop}"]'
        v = d.variables.new(); v.name = 'tz'; v.type = 'TRANSFORMS'
        v.targets[0].id = rig; v.targets[0].bone_target = 'eye_target'
        v.targets[0].transform_type = f'LOC_{AX}'; v.targets[0].transform_space = 'LOCAL_SPACE'
        cexp = 'min(1.0,max(p,pe,fp))'
        # ângulo em torno de r: fechamento + acompanhamento do olhar (olhar p/ baixo = +)
        psi = f'(-tz*{up_sign:.1f}/{D_TGT})'
        d.expression = f'{E["sx"]:.1f}*({th:.5f}*{cexp} + ac*0.6*{psi}*(1-{cexp}))'

# ---------------------------------------------------------------- organização e gravação
coll = bpy.data.collections.new('Kumo_Olhos_v1'); bpy.context.scene.collection.children.link(coll)
for n in created:
    o = bpy.data.objects[n]
    for c in o.users_collection: c.objects.unlink(o)
    coll.objects.link(o)
for n in ('Kumo_Lid_L', 'Kumo_Lid_R'):          # pálpebras antigas: só ocultas, para comparação
    o = bpy.data.objects[n]; o.hide_render = True; o.hide_viewport = True
bpy.data.objects['Kumo_Olhos_ColisaoPele'].hide_set(True); bpy.data.objects['Kumo_Olhos_ColisaoGlobo'].hide_set(True)
sc = bpy.context.scene
sc.cycles.transparent_max_bounces = 24
img.filepath = '//../textures/kumo_quad_diffuse.png'
for im_ in bpy.data.images:
    if im_.name.startswith('olho_'): im_.filepath = '//textures/' + os.path.basename(im_.filepath)
blend_out = os.path.join(OUT, 'kumo_eyes_exp.blend')
bpy.ops.wm.save_as_mainfile(filepath=blend_out, relative_remap=False)

info = {tag: dict(centro_janela=list(E['O']), eixo_r=list(E['r']), eixo_w=list(E['w']), eixo_f=list(E['f']),
                  meia_largura=E['a'], meia_altura=E['c'], raio_globo=E['R'], centro_globo=list(E['C']),
                  ang_fechar_sup_graus=math.degrees(E['theta_up']), ang_fechar_inf_graus=math.degrees(E['theta_low']),
                  sinal_eixo_osso=E['sx'], pupila_centro=layers[tag]['pupil_c'], pupila_meia=layers[tag]['pupil_h'],
                  pixels_brilho=layers[tag]['catch_px'], pixels_olho=layers[tag]['eye_px'],
                  faces_casca=len(layers[tag]['faces']))
        for tag, E in EYES.items()}
info['objetos_criados'] = created
info['pontos_empurrados_para_fora'] = PUSHED
info['eixo_alvo_vertical'] = [AX, up_sign]
json.dump(info, open(os.path.join(OUT, 'olhos-v1-construcao.json'), 'w'), indent=1)
print('OK', blend_out); print(json.dumps({k: v for k, v in info.items() if k in 'LR'}, indent=1))
