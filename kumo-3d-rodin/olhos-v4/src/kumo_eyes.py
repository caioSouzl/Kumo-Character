"""Kumo — sistema ocular experimental (olhos-v4: vínculo à pele deformada).

Abre kumo_rigged.blend SOMENTE para leitura e grava uma cópia nova em
olhos-v4/kumo_eyes_exp.blend. Nada da malha da cabeça, dos materiais ou das
texturas aprovadas é alterado: todo o sistema é feito de objetos novos.

Uso:
  python kumo_eyes.py <kumo_rigged.blend> <pasta olhos-v4>

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
TONE = {}
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
    green = ((hv[..., 0] > 0.17) & (hv[..., 0] < 0.45) & (hv[..., 1] > 0.25) & (hv[..., 2] > 0.25)).astype(np.uint8)
    # contorno pintado em volta do olho (na textura da cabeça): faixa não-verde/escura colada ao olho
    band = cv2.dilate(eye, k3, iterations=26) & (1 - eye) & hit.astype(np.uint8)
    cand = band & ((1 - green) | (hv[..., 2] < 0.40).astype(np.uint8) | (hv[..., 1] < 0.30).astype(np.uint8))
    nC, labC = cv2.connectedComponents(cand, connectivity=8)
    touch = cv2.dilate(eye, k3, iterations=2)
    contour = np.zeros_like(eye)
    for k_ in range(1, nC):
        comp = (labC == k_)
        if (comp & (touch > 0)).any(): contour |= comp.astype(np.uint8)
    lidm = cv2.morphologyEx(eye | contour, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    ff = lidm.copy(); m2 = np.zeros((NPX + 2, NPX + 2), np.uint8); cv2.floodFill(ff, m2, (0, 0), 1); lidm = lidm | (1 - ff)
    # canto: fios claros/laranja da textura colados ao olho (ex.: canto interno do E) entram na área que a pálpebra
    # cobre AO FECHAR; com o olho aberto nada muda (a pálpebra fica estacionada fora). Marcas escuras (nariz) ficam fora.
    band2 = cv2.dilate(lidm, k3, iterations=40) & (1 - lidm) & hit.astype(np.uint8)
    light = ((1 - green).astype(bool) & (hv[..., 2] > 0.45)).astype(np.uint8) & band2
    nL, labL = cv2.connectedComponents(light, connectivity=8); touchL = cv2.dilate(lidm, k3, iterations=3); corner = np.zeros_like(lidm)
    for k_ in range(1, nL):
        comp = (labL == k_)
        if (comp & (touchL > 0)).any(): corner |= comp.astype(np.uint8)
    lidm = lidm | corner
    lidm = cv2.dilate(lidm, k3, iterations=9)                               # o esmaecimento da borda cai sobre pele lisa
    darkmark = cv2.dilate(((hv[..., 2] < 0.22) & hit & (eye == 0)).astype(np.uint8) & (1 - cv2.dilate(eye | contour, k3, iterations=2)), k3, iterations=3)
    lidm = lidm & (1 - darkmark)                                            # não cobre marcas escuras do rosto (nariz)
    corner_px = int(corner.sum())
    # pele lisa da pálpebra: preenchida só com o verde do anel FORA da área coberta (sem traços pintados)
    # pele lisa: amostrada do anel em volta (verde E verde-amarelado), sem traços escuros nem laranja,
    # e com o brilho igualado à pele visível logo em volta do olho fechado
    ring = cv2.dilate(lidm, k3, iterations=30) & (1 - cv2.dilate(lidm, k3, iterations=6)) & hit.astype(np.uint8)
    orange = ((hv[..., 0] < 0.15) & (hv[..., 1] > 0.40)).astype(np.uint8)
    valid = ring & (hv[..., 2] > 0.30).astype(np.uint8) & (1 - orange)
    old_rgb = cv2.GaussianBlur(pushpull(rgb, (cv2.dilate(lidm, k3, iterations=18) & (1 - cv2.dilate(lidm, k3, iterations=4)) & hit.astype(np.uint8) & green).astype(np.float32)), (0, 0), 8)
    v3_rgb = cv2.GaussianBlur(pushpull(rgb, valid.astype(np.float32)), (0, 0), 3)
    # v4: base suave contínua com a borda + DETALHE real da pele vizinha em pequenos pedaços aleatórios
    # (rotações de 90°, janelas com transição suave), sem espelhamento nem repetição em grade
    base = cv2.GaussianBlur(pushpull(rgb, valid.astype(np.float32)), (0, 0), 2)
    hp = rgb - cv2.GaussianBlur(rgb, (0, 0), 5)
    rng = np.random.default_rng(11 if tag == 'L' else 23)
    vint = cv2.integral(valid.astype(np.float32))
    for ps, thr in ((40, 0.97), (32, 0.93), (24, 0.9), (16, 0.85)):    # pedaços menores se o anel for estreito
        cand_xy = [(x, y) for y in range(0, NPX - ps, 3) for x in range(0, NPX - ps, 3)
                   if (vint[y + ps, x + ps] - vint[y, x + ps] - vint[y + ps, x] + vint[y, x]) >= thr * ps * ps]
        if len(cand_xy) >= 30: break
    step = max(8, int(ps * 0.35))
    TONE.setdefault(tag, {})['pedaco_px'] = ps; TONE[tag]['pedacos_disponiveis'] = len(cand_xy)
    win2 = np.outer(np.hanning(ps), np.hanning(ps)).astype(np.float32)
    acc = np.zeros((NPX, NPX, 3), np.float32); wsum = np.zeros((NPX, NPX), np.float32)
    region = cv2.dilate(lidm, k3, iterations=6) > 0
    for y in range(-ps // 2, NPX - ps // 2, step):
        for x in range(-ps // 2, NPX - ps // 2, step):
            y0, x0 = max(0, y), max(0, x); y1, x1 = min(NPX, y + ps), min(NPX, x + ps)
            if not region[y0:y1, x0:x1].any() or not cand_xy: continue
            sx, sy = cand_xy[rng.integers(len(cand_xy))]
            patch = np.rot90(hp[sy:sy + ps, sx:sx + ps], k=int(rng.integers(4)))
            wy0, wx0 = y0 - y, x0 - x
            acc[y0:y1, x0:x1] += patch[wy0:wy0 + (y1 - y0), wx0:wx0 + (x1 - x0)] * win2[wy0:wy0 + (y1 - y0), wx0:wx0 + (x1 - x0), None]
            wsum[y0:y1, x0:x1] += win2[wy0:wy0 + (y1 - y0), wx0:wx0 + (x1 - x0)]
    det = acc / np.maximum(wsum, 1e-4)[..., None]
    ringnear = (cv2.dilate(lidm, k3, iterations=20) & (1 - cv2.dilate(lidm, k3, iterations=3)) & valid) > 0
    sd_ring = float(hp[ringnear].std()); sd_det = float(det[lidm > 0].std())
    det *= (sd_ring / max(sd_det, 1e-5))
    # decisão após teste visual (prancha 13): o detalhe inteiro (variante B) cria um padrão riscado artificial
    # na pintura cel-shading do Kumo; fica a base lisa + 40% só da frequência média do detalhe (variante C)
    bp = cv2.GaussianBlur(det - cv2.GaussianBlur(det, (0, 0), 3), (0, 0), 1.2)
    skin_rgb = np.clip(v3_rgb + 0.4 * bp, 0, 1)
    near = (cv2.dilate(lidm, k3, iterations=14) & (1 - cv2.dilate(lidm, k3, iterations=3)) & hit.astype(np.uint8) & (hv[..., 2] > 0.30).astype(np.uint8) & (1 - orange)) > 0
    lum = lambda x: (x * np.array([0.2126, 0.7152, 0.0722], np.float32)).sum(-1)
    inside = lidm > 0
    target = float(lum(rgb)[near].mean()); now = float(lum(skin_rgb)[inside].mean())
    skin_rgb = np.clip(skin_rgb * (target / max(now, 1e-4)), 0, 1)
    hpv = lambda x: x - cv2.GaussianBlur(x, (0, 0), 5)
    TONE.setdefault(tag, {}).update(lum_pele_em_volta=round(target, 4), lum_palpebra_v4=round(float(lum(skin_rgb)[inside].mean()), 4),
                     detalhe_desvio_pele_em_volta=round(sd_ring, 4),
                     detalhe_desvio_palpebra_v3=round(float(hpv(v3_rgb)[inside].std()), 4),
                     detalhe_desvio_palpebra_v4=round(float(hpv(skin_rgb.astype(np.float32))[inside].std()), 4),
                     pixels_canto_cobertos_ao_fechar=corner_px)
    contour_px = int(contour.sum())
    eye_a = soft(eye, 0.8)
    L = {
        'mask':   (np.dstack([eye_a] * 3), eye_a),
        'eye':    (sclera_rgb, eye_a),
        'iris':   (iris_rgb, soft(I, 2.0)),
        'pupil':  (pupil_rgb, soft(cv2.dilate(P2, k3), 0.8)),
        'catch':  (rgb, soft(cv2.dilate(Wt, k3), 0.8)),
        'skin':   (skin_rgb, np.ones((NPX, NPX), np.float32)),
        'lidmask': (np.dstack([soft(lidm, 3.0)] * 3), soft(lidm, 3.0)),
        'contorno': (np.dstack([contour.astype(np.float32)] * 3), contour.astype(np.float32)),
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
    lidz = cv2.dilate(lidm, k3, iterations=10); n_extra = 0
    for p_ in me.polygons:                                   # cantos que o eixo do olho não enxerga (ex.: canto interno)
        if p_.index in fset or p_.normal.dot(E['f']) <= 0.0: continue
        q = p_.center - E['O']; dep = q.dot(E['f'])
        if not (-0.15 < dep < 0.03): continue
        i_ = int((q.dot(E['r']) / E['a'] + K) / (2 * K) * NPX); j_ = int((q.dot(E['w']) / E['c'] + K) / (2 * K) * NPX)
        if 0 <= i_ < NPX and 0 <= j_ < NPX and lidz[j_, i_]: fset.add(p_.index); n_extra += 1
    TONE.setdefault(tag, {})['faces_canto_adicionadas'] = n_extra
    def colrow(m):           # extensão do olho por coluna u: topo e base em unidades de parâmetro
        top = np.full(NPX, -9.0); bot = np.full(NPX, 9.0)
        for i in range(NPX):
            js = np.nonzero(m[:, i])[0]
            if len(js): top[i] = g[js.max()]; bot[i] = g[js.min()]
        return top, bot
    top, bot = colrow(eye); ltop, lbot = colrow(lidm)
    layers[tag] = dict(lidm=lidm, eye=eye, P=P, I=I, Wt=Wt, faces=sorted(fset), top=top, bot=bot, ltop=ltop, lbot=lbot, contour_px=contour_px,
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
    p0 = p.copy()
    while inside_body(p) and k < 40: p = p + axis * 0.0005; k += 1
    if inside_body(p):                       # normal apontando para dentro de uma dobra: vai ao ponto mais próximo da pele
        loc, nor, i_, d_ = body_bvh.find_nearest(p0); p = loc + nor * 0.0012; k = 99
    elif k: p = p + axis * margin
    return p, k
PUSHED = {}
def lift_tris(V, faces, N, below=None, gap=0.0004, passes=6):
    """Garante que o INTERIOR de cada triângulo fique fora da pele (e acima de 'below', se dado):
    amostra pontos dentro do triângulo e ergue os 3 vértices ao longo da normal só onde preciso."""
    B = [(i / 4, j / 4, (4 - i - j) / 4) for i in range(5) for j in range(5 - i)]      # os mesmos pontos da subdivisão nível 2
    lifted = 0
    for _ in range(passes):
        ch = False
        for f_ in faces:
            if len(f_) != 3: continue
            a_, b_, c_ = (V[i] for i in f_)
            worst = 0.0
            for w0, w1, w2 in B:
                q = a_ * w0 + b_ * w1 + c_ * w2
                if inside_body(q):
                    loc, nor, i_, d_ = body_bvh.find_nearest(q); worst = max(worst, d_ + gap)
                elif below is not None:
                    loc, nor, i_, d_ = below.find_nearest(q)
                    if loc is not None and (q - loc).dot(nor) < gap: worst = max(worst, gap - (q - loc).dot(nor))
            if worst > 0:
                cand = [V[i] + N[i] * (worst + 0.0001) for i in f_]
                if any(inside_body(c) for c in cand): continue      # erguer entraria na borda da órbita: não ergue
                for i, c in zip(f_, cand): V[i] = c
                ch = True; lifted += 1
        if not ch: break
    return lifted
created = []
def mesh_obj(name, verts, faces, uvs=None):
    m = bpy.data.meshes.new(name); m.from_pydata(verts, [], faces); m.update()
    if uvs is not None:
        ul = m.uv_layers.new(name='UVMap')
        for p in m.polygons:
            for li in p.loop_indices: ul.data[li].uv = uvs[m.loops[li].vertex_index]
    o = link(bpy.data.objects.new(name, m)); created.append(name); return o

LUTS = {}
RELIEF = {}
def lid_material(name, im_lut, upper, lash, bone, theta):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear(); N, Lk = nt.nodes, nt.links.new
    out = N.new('ShaderNodeOutputMaterial'); em = N.new('ShaderNodeEmission'); tr = N.new('ShaderNodeBsdfTransparent'); mix = N.new('ShaderNodeMixShader')
    vec = coord_from_object(nt, CUR['win']); sep = N.new('ShaderNodeSeparateXYZ'); Lk(vec, sep.inputs[0])
    skin = tex(nt, CUR['im']['skin'], vec); lm = tex(nt, CUR['im']['lidmask'], vec)
    # t (0 aberto .. 1 fechado) lido da rotação do osso da pálpebra
    tv = N.new('ShaderNodeValue'); tv.label = 'estagio_t'
    fc = tv.outputs[0].driver_add('default_value'); d = fc.driver; d.type = 'SCRIPTED'
    v = d.variables.new(); v.name = 'a'; v.type = 'TRANSFORMS'; v.targets[0].id = rig; v.targets[0].bone_target = bone
    v.targets[0].transform_type = 'ROT_X'; v.targets[0].transform_space = 'LOCAL_SPACE'; v.targets[0].rotation_mode = 'XYZ'
    d.expression = f'min(1.0,max(0.0,a*{CUR["E"]["sx"]:.1f}/{theta:.6f}))'
    cb = N.new('ShaderNodeCombineXYZ'); Lk(sep.outputs['X'], cb.inputs['X']); Lk(tv.outputs[0], cb.inputs['Y'])
    lt = N.new('ShaderNodeTexImage'); lt.image = im_lut; lt.extension = 'EXTEND'; lt.interpolation = 'Linear'; Lk(cb.outputs[0], lt.inputs['Vector'])
    sc_ = N.new('ShaderNodeSeparateColor'); Lk(lt.outputs['Color'], sc_.inputs[0])
    dif = N.new('ShaderNodeMath'); dif.operation = 'SUBTRACT'
    if upper: Lk(sep.outputs['Y'], dif.inputs[0]); Lk(sc_.outputs[0], dif.inputs[1])     # acima da borda
    else: Lk(sc_.outputs[0], dif.inputs[0]); Lk(sep.outputs['Y'], dif.inputs[1])         # abaixo da borda
    vis = N.new('ShaderNodeMath'); vis.operation = 'GREATER_THAN'; vis.inputs[1].default_value = 0.0; Lk(dif.outputs[0], vis.inputs[0])
    isl = N.new('ShaderNodeMath'); isl.operation = 'LESS_THAN'; isl.inputs[1].default_value = lash[0] / (2 * K); Lk(dif.outputs[0], isl.inputs[0])
    mc = N.new('ShaderNodeMix'); mc.data_type = 'RGBA'; Lk(isl.outputs[0], mc.inputs['Factor']); Lk(skin.outputs['Color'], mc.inputs['A'])
    mc.inputs['B'].default_value = lash[1]
    al = N.new('ShaderNodeMath'); al.operation = 'MULTIPLY'; Lk(vis.outputs[0], al.inputs[0]); Lk(lm.outputs['Alpha'], al.inputs[1])
    Lk(mc.outputs['Result'], em.inputs['Color']); Lk(al.outputs[0], mix.inputs['Fac'])
    Lk(tr.outputs[0], mix.inputs[1]); Lk(em.outputs[0], mix.inputs[2]); Lk(mix.outputs[0], out.inputs['Surface'])
    return m
CUR = {}
for tag, E in EYES.items():
    Ly = layers[tag]
    # janela fixa (presa ao osso da cabeça) e referência de olhar (presa ao osso do olho)
    win = link(bpy.data.objects.new(f'Kumo_EyeWindow_{tag}', None)); win.empty_display_type = 'CUBE'
    win.empty_display_size = 1.0; win.matrix_world = frame_matrix(E); bone_parent(win, 'head'); created.append(win.name)
    im = {nm: load_img(tag, nm) for nm in ('mask', 'eye', 'iris', 'pupil', 'catch', 'skin', 'lidmask')}

    # --- globo / esclera: casca sobre a pele do olho, deformada pela mesma armadura
    fset = Ly['faces']; vs = sorted({v for fi in fset for v in me.polygons[fi].vertices}); vmap = {v: k for k, v in enumerate(vs)}
    # triângulos idênticos aos que o Blender renderiza para a pele (loop triangles)
    me.calc_loop_triangles(); fs_ = set(fset)
    faces = [[vmap[v] for v in lt.vertices] for lt in me.loop_triangles if lt.polygon_index in fs_]
    # refino LOCAL: só os triângulos onde a casca mais alta (pálpebra) não cabe entre o globo e a pele de cima
    # (canto da órbita); os pontos novos ficam sobre a própria pele (no meio das arestas), sem mudar a forma
    P = [me.vertices[v].co.copy() for v in vs]; Nn = [me.vertices[v].normal.copy() for v in vs]
    BB = [(i / 4, j / 4, (4 - i - j) / 4) for i in range(5) for j in range(5 - i)]
    def tight(f_):
        a_, b_, c_ = f_
        for w0, w1, w2 in BB:
            q = P[a_] * w0 + P[b_] * w1 + P[c_] * w2; n_ = (Nn[a_] * w0 + Nn[b_] * w1 + Nn[c_] * w2).normalized()
            if inside_body(q + n_ * (EPS['eye'] + EPS['up'] + 0.0004)): return True
        return False
    def refine_once(F, marked):
        F = [tuple(f_) for f_ in F]; marked = set(marked); mids = {}
        def ek(a_, b_): return (a_, b_) if a_ < b_ else (b_, a_)
        while True:                                            # fechamento conforme (sem rachaduras)
            split = {ek(f_[i], f_[(i + 1) % 3]) for k_, f_ in enumerate(F) if k_ in marked for i in range(3)}
            add = {k_ for k_, f_ in enumerate(F) if k_ not in marked and sum(ek(f_[i], f_[(i + 1) % 3]) in split for i in range(3)) >= 2}
            if not add: break
            marked |= add
        def mid(a_, b_):
            k_ = ek(a_, b_)
            if k_ not in mids:
                P.append((P[a_] + P[b_]) / 2); Nn.append((Nn[a_] + Nn[b_]).normalized()); mids[k_] = len(P) - 1
            return mids[k_]
        out = []
        for k_, (a_, b_, c_) in enumerate(F):
            if k_ in marked:
                ab, bc, ca = mid(a_, b_), mid(b_, c_), mid(c_, a_)
                out += [[a_, ab, ca], [ab, b_, bc], [ca, bc, c_], [ab, bc, ca]]
                continue
            es = [(a_, b_, c_), (b_, c_, a_), (c_, a_, b_)]
            done = False
            for x, y, z in es:
                if ek(x, y) in split:
                    m_ = mid(x, y); out += [[x, m_, z], [m_, y, z]]; done = True; break
            if not done: out.append([a_, b_, c_])
        return out, len(marked)
    n_ref = []
    for _lv in range(3):
        mk = [k_ for k_, f_ in enumerate(faces) if tight(f_)]
        if not mk: break
        faces, nm_ = refine_once(faces, mk); n_ref.append(nm_)
    PUSHED[f'casca_{tag}_triangulos_refinados_por_nivel'] = n_ref
    verts = []
    for i_ in range(len(P)):
        q, k = push_out(P[i_] + Nn[i_] * EPS['eye'], Nn[i_])
        verts.append(q); PUSHED[f'casca_{tag}'] = PUSHED.get(f'casca_{tag}', 0) + (k > 0)
    # vértice que continua dentro da cabeça mesmo após o empurrão: só existe na margem fora do contorno; sai da casca
    eyed = cv2.dilate(Ly['eye'], k3, iterations=4)
    def in_mask(p):
        q = p - E['O']; u, wv = q.dot(E['r']) / E['a'], q.dot(E['w']) / E['c']
        i = int((u + K) / (2 * K) * NPX); j = int((wv + K) / (2 * K) * NPX)
        return 0 <= i < NPX and 0 <= j < NPX and eyed[j, i] > 0
    PUSHED[f'casca_{tag}_triangulos_erguidos'] = lift_tris(verts, faces, Nn)
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
    CUR.update(win=win, im=im, E=E)
    # espaço disponível acima do globo (até a pele por cima, ex.: borda da órbita): onde falta espaço,
    # todas as camadas dividem o espaço proporcionalmente (a ordem íris < pupila < brilho < pálpebras se mantém)
    SQ = []
    for v in shell.data.vertices:
        loc, nor, fi_, dist = body_bvh.ray_cast(v.co + v.normal * 1e-4, v.normal)
        d_ = dist if loc is not None else 1.0
        SQ.append(min(1.0, 0.85 * d_ / (EPS['up'] + 0.0004)))
    PUSHED[f'globo_{tag}_vertices_comprimidos'] = sum(1 for x in SQ if x < 1.0)
    shell_rest_bvh = BVHTree.FromPolygons([v.co for v in shell.data.vertices], [list(pp.vertices) for pp in shell.data.polygons])
    def layer_shell_geom(name, extra):
        sm = shell.data; V = []
        for v in sm.vertices:
            q, k = push_out(v.co + v.normal * extra * SQ[v.index], v.normal); V.append(q)
        F_ = [list(pp.vertices) for pp in sm.polygons]
        PUSHED[name + '_triangulos_erguidos'] = lift_tris(V, F_, [v.normal for v in sm.vertices], below=shell_rest_bvh, gap=extra * 0.3)
        o = mesh_obj(name, V, F_)
        o.parent = rig
        for pp in o.data.polygons: pp.use_smooth = True
        return o
    def layer_shell(name, layer, extra):
        sm = shell.data; V = []
        for v in sm.vertices:
            q, k = push_out(v.co + v.normal * extra * SQ[v.index], v.normal); V.append(q)
            if k: PUSHED[name] = PUSHED.get(name, 0) + 1
        F_ = [list(pp.vertices) for pp in sm.polygons]
        PUSHED[name + '_triangulos_erguidos'] = lift_tris(V, F_, [v.normal for v in sm.vertices], below=shell_rest_bvh, gap=extra * 0.3)
        o = mesh_obj(name, V, F_)
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
        """Ponto da superfície em (u, w) projetado ao longo do eixo do olho, afastado 'off'."""
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
        """Pálpebra = casca que copia pele+globo (cobre toda a curvatura, inclusive as laterais íngremes).
        A borda é uma fronteira que percorre a superfície seguindo o arco de rotação em torno do centro
        do globo; o arco fica numa tabela (colunas u × estágios t) lida pelo material."""
        nu = 96
        us = [-K + 2 * K * i / nu for i in range(nu + 1)]
        def w_edge_closed(u): return w_close_up(u) if upper else w_close_low(u)
        edge3 = [place(u, w_edge_closed(u), 0.0) or to_world(E, u, w_edge_closed(u), 0) for u in us]
        lim = Ly['ltop'] if upper else Ly['lbot']        # estaciona fora da área que a pálpebra cobre
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
        step = math.radians(0.25) * (-1 if upper else 1)
        ang = 0.0
        while not clear(ang) and abs(ang) < math.radians(120): ang += step
        theta = -ang
        # tabela da borda: linha = estágio t (0 aberto .. 1 fechado), coluna = u; valor = w da borda (0..1)
        NU, NT = 256, 64
        ug = np.linspace(-K, K, NU)
        lut = np.zeros((NT, NU), np.float32)
        for ti in range(NT):
            t = ti / (NT - 1); E2 = edge_at(ang * (1 - t))
            uu = np.array([e_[0] for e_ in E2]); ww = np.array([e_[1] for e_ in E2]); o_ = np.argsort(uu)
            wl = np.interp(ug, uu[o_], ww[o_])
            lut[ti] = (wl + K) / (2 * K)
        lut = cv2.GaussianBlur(lut, (0, 0), sigmaX=2.0, sigmaY=0.01)
        LUTS[name] = lut
        RELIEF[name] = dict(win=CUR['win'], lut_path=None, mask=CUR['im']['lidmask'], bone=bone, theta=theta, sx=CUR['E']['sx'], upper=upper)
        # casca: cópia da pele+globo com a folga da pálpebra (vinculada à pele como as outras camadas)
        o = layer_shell_geom(name, extra)
        # folga disponível ao longo da normal (até a pele, ex.: borda da órbita por cima do olho): limite do relevo
        o.data.update(); att = o.data.attributes.new('folga', 'FLOAT', 'POINT'); vals = []
        for v in o.data.vertices:                                   # cone de 9 direções em volta da normal
            n_ = v.normal; t1 = n_.orthogonal().normalized(); t2 = n_.cross(t1)
            dm = 1.0
            dirs = [n_] + [(n_ + (t1 * a_ + t2 * b_) * k_).normalized() for k_ in (0.45, 0.9) for a_, b_ in ((1, 0), (-1, 0), (0, 1), (0, -1))]
            for dv in dirs:
                loc, nor, fi_, dist = body_bvh.ray_cast(v.co + dv * 1e-4, dv)
                if loc is not None: dm = min(dm, dist)
            vals.append(max(0.0, dm - 0.003))
        nb = {}                                                     # cada ponto fica com a menor folga entre os vizinhos
        for e_ in o.data.edges:
            a_, b_ = e_.vertices; nb.setdefault(a_, []).append(b_); nb.setdefault(b_, []).append(a_)
        vals = [min([vals[i]] + [vals[j] for j in nb.get(i, [])]) for i in range(len(vals))]
        att.data.foreach_set('value', vals)
        lp = os.path.join(TEXDIR, f'{name}_borda.png')                 # PNG 16 bits (precisão ~1/65535)
        cv2.imwrite(lp, np.flipud(np.clip(np.round(lut * 65535), 0, 65535).astype(np.uint16)))
        im_lut = bpy.data.images.load(lp); im_lut.name = f'{name}_borda'; im_lut.colorspace_settings.name = 'Non-Color'; im_lut.pack(); RELIEF[name]['lut'] = im_lut
        lash = (0.055, LASH) if upper else (0.03, tuple(0.5 * x + 0.5 * y for x, y in zip(LASH, (0.2, 0.25, 0.1, 1))))
        o.data.materials.append(lid_material(name, im_lut, upper, lash, bone, theta))
        return o, theta
    C, rax = E['C'], E['r']
    def w_close_up(u):  return -0.18 - 0.12 * (1 - min(1, (u / 1.1) ** 2))
    def w_close_low(u): return w_close_up(u) + 0.03
    _, E['theta_up'] = lid(f'Kumo_LidUp_{tag}', True, EPS['up'], f'lid_up.{tag}')
    _, E['theta_low'] = lid(f'Kumo_LidLow_{tag}', False, EPS['low'], f'lid_low.{tag}')

# ---------------------------------------------------------------- vínculo à pele deformada
# Cópia oculta da pele da cabeça com os MESMOS pesos aprovados (a malha e os pesos originais não são tocados).
# Cada vértice ocular, em cada quadro, acha o ponto da pele em repouso logo abaixo dele (face + baricêntrico),
# lê onde a deformação do rig levou esse ponto e mantém a mesma altura sobre a pele, na normal deformada.
hv = [v.index for v in me.vertices]          # corpo inteiro: nenhum vértice ocular cai numa borda cortada
hvs = set(hv); hmap = {v: k for k, v in enumerate(hv)}
hfaces = [[hmap[v] for v in p.vertices] for p in me.polygons if all(v in hvs for v in p.vertices)]
proxy = mesh_obj('Kumo_Olhos_PeleRef', [me.vertices[v].co.copy() for v in hv], hfaces)
for vg in body.vertex_groups:
    if vg.name in ('outline_cut', 'outline_shell'): continue
    ng = proxy.vertex_groups.new(name=vg.name)
    for v in hv:
        for gg in me.vertices[v].groups:
            if gg.group == vg.index and gg.weight > 0: ng.add([hmap[v]], gg.weight, 'REPLACE')
proxy.parent = rig; am = proxy.modifiers.new('Armature', 'ARMATURE'); am.object = rig
for k_, v_ in (('use_deform_preserve_volume', False),):
    setattr(am, k_, getattr(body.modifiers['Armature'], k_))
proxy.add_rest_position_attribute = True
proxy.hide_render = True; proxy.display_type = 'WIRE'

def bind_group():
    ng = bpy.data.node_groups.new('Kumo_VinculoPele', 'GeometryNodeTree')
    ng.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    N, Lk = ng.nodes, ng.links.new
    gi = N.new('NodeGroupInput'); go = N.new('NodeGroupOutput')
    oi = N.new('GeometryNodeObjectInfo'); oi.inputs['Object'].default_value = proxy; oi.transform_space = 'RELATIVE'
    cap = N.new('GeometryNodeCaptureAttribute'); cap.domain = 'POINT'
    cap.capture_items.new('VECTOR', 'pdef'); cap.capture_items.new('VECTOR', 'ndef')
    pos = N.new('GeometryNodeInputPosition'); nrm = N.new('GeometryNodeInputNormal')
    Lk(oi.outputs['Geometry'], cap.inputs['Geometry']); Lk(pos.outputs[0], cap.inputs['pdef']); Lk(nrm.outputs['Normal'], cap.inputs['ndef'])
    rest = N.new('GeometryNodeInputNamedAttribute'); rest.data_type = 'FLOAT_VECTOR'; rest.inputs['Name'].default_value = 'rest_position'
    sp = N.new('GeometryNodeSetPosition'); Lk(cap.outputs['Geometry'], sp.inputs['Geometry']); Lk(rest.outputs['Attribute'], sp.inputs['Position'])
    lidpos = N.new('GeometryNodeInputPosition')            # posição do vértice ocular (repouso + shape keys)
    def sample(field):
        sn = N.new('GeometryNodeSampleNearestSurface'); sn.data_type = 'FLOAT_VECTOR'
        Lk(sp.outputs['Geometry'], sn.inputs['Mesh']); Lk(field, sn.inputs['Value']); Lk(lidpos.outputs[0], sn.inputs['Sample Position'])
        return sn.outputs['Value']
    pos2 = N.new('GeometryNodeInputPosition'); nrm2 = N.new('GeometryNodeInputNormal')
    q_def = sample(cap.outputs['pdef']); n_def = sample(cap.outputs['ndef'])
    q_rest = sample(pos2.outputs[0]); n_rest = sample(nrm2.outputs['Normal'])
    def vm(op, a, b=None):
        n = N.new('ShaderNodeVectorMath'); n.operation = op; Lk(a, n.inputs[0])
        if b is not None: Lk(b, n.inputs[1])
        return n
    d = vm('SUBTRACT', lidpos.outputs[0], q_rest)
    nr = vm('NORMALIZE', n_rest); nd = vm('NORMALIZE', n_def)
    h = vm('DOT_PRODUCT', d.outputs[0], nr.outputs[0])
    sc = N.new('ShaderNodeVectorMath'); sc.operation = 'SCALE'; Lk(nd.outputs[0], sc.inputs[0]); Lk(h.outputs['Value'], sc.inputs['Scale'])
    # resíduo tangencial (≈0): mantido como está
    sc2 = N.new('ShaderNodeVectorMath'); sc2.operation = 'SCALE'; Lk(nr.outputs[0], sc2.inputs[0]); Lk(h.outputs['Value'], sc2.inputs['Scale'])
    tan = vm('SUBTRACT', d.outputs[0], sc2.outputs[0])
    p1 = vm('ADD', q_def, sc.outputs[0]); p2 = vm('ADD', p1.outputs[0], tan.outputs[0])
    st = N.new('GeometryNodeSetPosition'); Lk(gi.outputs[0], st.inputs['Geometry']); Lk(p2.outputs[0], st.inputs['Position'])
    Lk(st.outputs['Geometry'], go.inputs[0])
    return ng
BIND = bind_group()

# ---------------------------------------------------------------- relevo da borda da pálpebra
RELIEF_H = {'up': 0.0080, 'low': 0.0044}       # altura máxima do relevo (m), só para fora, ao longo da normal
RELIEF_W = {'up': 0.030, 'low': 0.022}         # largura da faixa com relevo (fração da janela do olho)
def relief_group(name, R):
    ng = bpy.data.node_groups.new(f'Kumo_Relevo_{name}', 'GeometryNodeTree')
    I = ng.interface
    I.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    k_ = 'up' if R['upper'] else 'low'
    I.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    N, Lk = ng.nodes, ng.links.new
    gi = N.new('NodeGroupInput'); go = N.new('NodeGroupOutput')
    sub = N.new('GeometryNodeSubdivideMesh'); sub.inputs['Level'].default_value = 2; Lk(gi.outputs['Geometry'], sub.inputs['Mesh'])
    oi = N.new('GeometryNodeObjectInfo'); oi.transform_space = 'RELATIVE'; oi.inputs['Object'].default_value = R['win']
    cst = {'Lado': 1.0 if R['upper'] else -1.0, 'Altura': RELIEF_H[k_], 'Largura': RELIEF_W[k_]}
    def cval(key):
        n = N.new('ShaderNodeValue'); n.label = key; n.outputs[0].default_value = cst[key]; return n.outputs[0]
    inv = N.new('FunctionNodeInvertMatrix'); Lk(oi.outputs['Transform'], inv.inputs['Matrix'])
    pos = N.new('GeometryNodeInputPosition'); tp = N.new('FunctionNodeTransformPoint')
    Lk(pos.outputs[0], tp.inputs['Vector']); Lk(inv.outputs['Matrix'], tp.inputs['Transform'])
    sep = N.new('ShaderNodeSeparateXYZ'); Lk(tp.outputs[0], sep.inputs[0])
    def m(op, a, b=None, cb=None):
        n = N.new('ShaderNodeMath'); n.operation = op
        (Lk(a, n.inputs[0]) if not isinstance(a, (int, float)) else n.inputs[0].__setattr__('default_value', a))
        if b is not None: (Lk(b, n.inputs[1]) if not isinstance(b, (int, float)) else n.inputs[1].__setattr__('default_value', b))
        return n.outputs[0]
    ux = m('MULTIPLY_ADD', sep.outputs['X'], 0.5); uy = m('MULTIPLY_ADD', sep.outputs['Y'], 0.5)
    for n in ng.nodes:
        if n.type == 'MATH' and n.operation == 'MULTIPLY_ADD': n.inputs[2].default_value = 0.5
    cv = N.new('ShaderNodeCombineXYZ'); tnode = N.new('ShaderNodeValue'); tnode.name = 'estagio_t'; tnode.label = 'estagio_t'
    Lk(ux, cv.inputs['X']); Lk(tnode.outputs[0], cv.inputs['Y'])
    lt = N.new('GeometryNodeImageTexture'); lt.interpolation = 'Linear'; lt.extension = 'EXTEND'
    lt.inputs['Image'].default_value = R['lut']; Lk(cv.outputs[0], lt.inputs['Vector'])
    sc_ = N.new('FunctionNodeSeparateColor'); Lk(lt.outputs['Color'], sc_.inputs['Color'])
    cm = N.new('ShaderNodeCombineXYZ'); Lk(ux, cm.inputs['X']); Lk(uy, cm.inputs['Y'])
    mt = N.new('GeometryNodeImageTexture'); mt.interpolation = 'Linear'; mt.extension = 'CLIP'
    mt.inputs['Image'].default_value = R['mask']; Lk(cm.outputs[0], mt.inputs['Vector'])
    d = m('MULTIPLY', m('SUBTRACT', uy, sc_.outputs['Red']), cval('Lado'))      # distância à borda, do lado da pálpebra
    def mr(v, a, b, c_, d_):
        n = N.new('ShaderNodeMapRange'); n.interpolation_type = 'SMOOTHSTEP'; n.clamp = True
        Lk(v, n.inputs['Value']); n.inputs['To Min'].default_value = c_; n.inputs['To Max'].default_value = d_
        (Lk(a, n.inputs['From Min']) if not isinstance(a, (int, float)) else n.inputs['From Min'].__setattr__('default_value', a))
        (Lk(b, n.inputs['From Max']) if not isinstance(b, (int, float)) else n.inputs['From Max'].__setattr__('default_value', b))
        return n.outputs['Result']
    fall = mr(d, 0.0, cval('Largura'), 1.0, 0.0)                                  # some até o fim da faixa
    rise = mr(d, 0.0, m('MULTIPLY', cval('Largura'), 0.3), 0.55, 1.0)            # lábio arredondado junto à borda
    on = m('GREATER_THAN', d, 0.0)
    h0 = m('MULTIPLY', m('MULTIPLY', m('MULTIPLY', fall, rise), on), m('MULTIPLY', cval('Altura'), mt.outputs['Alpha']))
    fg = N.new('GeometryNodeInputNamedAttribute'); fg.data_type = 'FLOAT'; fg.inputs['Name'].default_value = 'folga'
    h = m('MINIMUM', h0, fg.outputs['Attribute'])                                      # nunca encosta na pele
    nrm = N.new('GeometryNodeInputNormal'); off = N.new('ShaderNodeVectorMath'); off.operation = 'SCALE'
    Lk(nrm.outputs['Normal'], off.inputs[0]); Lk(h, off.inputs['Scale'])
    sp = N.new('GeometryNodeSetPosition'); Lk(sub.outputs['Mesh'], sp.inputs['Geometry']); Lk(off.outputs[0], sp.inputs['Offset'])
    Lk(sp.outputs['Geometry'], go.inputs[0])
    return ng
def add_relief(o, R):
    ng_ = relief_group(o.name, R)
    gm = o.modifiers.new('RelevoBorda', 'NODES'); gm.node_group = ng_
    # estágio t da piscada: driver no nó 'estagio_t' do grupo (mesma fórmula do material)
    fc = ng_.nodes['estagio_t'].outputs[0].driver_add('default_value'); d = fc.driver; d.type = 'SCRIPTED'
    v = d.variables.new(); v.name = 'a'; v.type = 'TRANSFORMS'; v.targets[0].id = rig; v.targets[0].bone_target = R['bone']
    v.targets[0].transform_type = 'ROT_X'; v.targets[0].transform_space = 'LOCAL_SPACE'; v.targets[0].rotation_mode = 'XYZ'
    d.expression = f'min(1.0,max(0.0,a*{R["sx"]:.1f}/{R["theta"]:.6f}))'
for tag in EYES:
    for part in ('Eye', 'Iris', 'Pupil', 'Catchlight', 'LidLow', 'LidUp'):
        o = bpy.data.objects[f'Kumo_{part}_{tag}']
        for m_ in [m_ for m_ in o.modifiers if m_.type == 'ARMATURE']: o.modifiers.remove(m_)
        gm = o.modifiers.new('VinculoPele', 'NODES'); gm.node_group = BIND
        if part.startswith('Lid'): add_relief(o, RELIEF[o.name])
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
bpy.data.objects['Kumo_Olhos_PeleRef'].hide_set(True)
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
info['tom_e_canto'] = TONE
info['relevo'] = dict(altura_m=RELIEF_H, largura=RELIEF_W)
for k_, v_ in LUTS.items(): np.save(os.path.join(TEXDIR, k_ + '_borda.npy'), v_)
info['contorno_pintado_px'] = {t: layers[t]['contour_px'] for t in EYES}
info['pontos_empurrados_para_fora'] = PUSHED
info['eixo_alvo_vertical'] = [AX, up_sign]
json.dump(info, open(os.path.join(OUT, 'olhos-v4-construcao.json'), 'w'), indent=1)
print('OK', blend_out); print(json.dumps({k: v for k, v in info.items() if k in 'LR'}, indent=1))
