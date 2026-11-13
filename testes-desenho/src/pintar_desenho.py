"""Teste 02: "Kumo 3D desenho". Numa CÓPIA do Kumo 3D oficial, pinta a textura projetando os desenhos aprovados
da folha de modelo (frente, perfil dos dois lados e costas). O oficial não muda.
A vista 3/4 NÃO é usada na pintura: fica para conferir se o resultado acerta um ângulo que ele nunca viu.

  python pintar_desenho.py <kumo_v6_ombros.blend> <saída>   ->  kumo_desenho.blend, textura_desenho.png
"""
import bpy, sys, os, math
import numpy as np, cv2
from mathutils import Vector
SRC, OUT = sys.argv[-2:]; os.makedirs(OUT, exist_ok=True)
RAIZ = '/home/user/Kumo-Character'
ASS = os.path.join(RAIZ, 'character-model-sheet', 'assets')
TX = 1024
bpy.ops.wm.open_mainfile(filepath=SRC)
rig = bpy.data.objects['Kumo_Rig']; body = bpy.data.objects['Kumo']; me = body.data
if rig.animation_data: rig.animation_data.action = None
for b in rig.pose.bones: b.rotation_quaternion = (1, 0, 0, 0); b.rotation_euler = (0, 0, 0); b.location = (0, 0, 0)
for m in body.modifiers:
    if m.type != 'ARMATURE': m.show_viewport = False
bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get(); ev = body.evaluated_get(dg); em = ev.to_mesh(); em.calc_loop_triangles()
P = np.array([tuple(ev.matrix_world @ v.co) for v in em.vertices]); Nv = np.array([tuple((ev.matrix_world.to_3x3() @ v.normal).normalized()) for v in em.vertices])
T = np.array([tuple(t.vertices) for t in em.loop_triangles]); TL = np.array([tuple(t.loops) for t in em.loop_triangles])
UV = np.array([tuple(l.uv) for l in em.uv_layers.active.data]); ev.to_mesh_clear()
gi = {g.index: g.name for g in body.vertex_groups}
def dom(v):
    gs = [g for g in v.groups if not gi[g.group].startswith('outline') and g.weight > 0]
    return gi[max(gs, key=lambda g: g.weight).group] if gs else ''
CAUDA = np.array([dom(v).startswith('tail') for v in me.vertices])
# ---------------- vistas desenhadas
def carrega(nome, espelha=False):
    im = cv2.imread(os.path.join(ASS, f'view-{nome}.png'), cv2.IMREAD_UNCHANGED)[..., [2, 1, 0, 3]]
    return im[:, ::-1].copy() if espelha else im
VISTAS = [dict(nome='front', ang=0, img=carrega('front'), sem_cauda=True),     # de frente a cauda do desenho está em outra pose
          dict(nome='side', ang=270, img=carrega('side'), sem_cauda=False),
          dict(nome='side-espelhada', ang=90, img=carrega('side', True), sem_cauda=True),   # o outro lado: o Kumo é quase simétrico
          dict(nome='back', ang=180, img=carrega('back'), sem_cauda=False)]
def eixos(ang):
    a = math.radians(ang); d = np.array([math.sin(a), -math.cos(a), 0.0]); f = -d
    r = np.cross(f, [0, 0, 1.0]); return f, r
def linhas_finas(img):
    """traço de contorno do desenho (escuro e fino). Não serve de cor para a pele: a linha volta depois, em 2D.
    Áreas escuras grandes (pupila) ficam."""
    lum = img[..., :3].astype(float) @ [0.299, 0.587, 0.114]; esc = ((lum < 80) & (img[..., 3] > 0)).astype(np.uint8)
    grosso = cv2.morphologyEx(esc, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11)))
    fino = (esc > 0) & ~(grosso > 0)
    # as linhas DENTRO da cabeça (boca, narinas, dobras da crista) são desenho do rosto: ficam
    a = img[..., 3] > 128; ys = np.nonzero(a)[0]; topo = np.zeros_like(a); topo[: ys.min() + int(0.46 * (ys.max() - ys.min()))] = True
    longe = cv2.distanceTransform(a.astype(np.uint8), cv2.DIST_L2, 3) > 9
    fino &= ~(topo & longe)
    return cv2.dilate(fino.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
def olhos_desenho(img):
    """os olhos do desenho (esclera creme, íris laranja, pupila preta) não pintam a pele: o desenho usa os olhos 3D
    aprovados (os da v5, que piscam e olham). Acha as regiões não verdes grandes na metade de cima da figura."""
    a = img[..., 3] > 128; ys = np.nonzero(a)[0]; topo = np.zeros_like(a); topo[ys.min(): ys.min() + int(0.45 * (ys.max() - ys.min()))] = True
    r, g, b = [img[..., k].astype(int) for k in range(3)]
    verde = (g >= r - 5) & (g > b + 15)
    cand = (a & topo & ~verde).astype(np.uint8)
    cand = cv2.morphologyEx(cand, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(cand, connectivity=8)
    m = np.isin(lab, [i for i in range(1, n) if st[i, 4] > 1500])
    return cv2.dilate(m.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13))) > 0
for V in VISTAS:
    V['linha'] = linhas_finas(V['img']) | olhos_desenho(V['img'])
    f, r = eixos(V['ang']); img = V['img']; A = img[..., 3] > 128; ys, xs = np.nonzero(A)
    hpx = ys.max() - ys.min(); z0, z1 = P[:, 2].min(), P[:, 2].max(); s = hpx / (z1 - z0)
    # horizontal: centro da cabeça (parte de cima da figura) nos dois
    cab = ys < ys.min() + 0.45 * hpx; cx_img = 0.5 * (xs[cab].min() + xs[cab].max())
    px = P @ r; cz = P[:, 2] > z0 + 0.55 * (z1 - z0); cx3 = 0.5 * (px[cz].min() + px[cz].max())
    V['proj'] = lambda Q, s=s, r=r, cx3=cx3, cx_img=cx_img, yb=ys.max(), z0=z0: np.stack([(Q @ r - cx3) * s + cx_img, yb - (Q[:, 2] - z0) * s], -1)
    V['f'] = f
    # profundidade (z-buffer) na resolução do desenho
    H, W = A.shape; zb = np.full((H, W), np.inf); q = V['proj'](P); dep = P @ f
    for t in T:
        p = q[t]; x0, y0 = np.floor(p.min(0)).astype(int); x1, y1 = np.ceil(p.max(0)).astype(int)
        x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, W - 1), min(y1, H - 1)
        if x1 < x0 or y1 < y0: continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        (ax, ay), (bx, by), (cx, cy) = p; den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-12: continue
        l1 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / den; l2 = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / den; l3 = 1 - l1 - l2
        ins = (l1 >= -1e-4) & (l2 >= -1e-4) & (l3 >= -1e-4)
        if not ins.any(): continue
        dd = l1 * dep[t[0]] + l2 * dep[t[1]] + l3 * dep[t[2]]
        sub = zb[y0:y1 + 1, x0:x1 + 1]; upd = ins & (dd < sub); sub[upd] = dd[upd]
    V['zb'] = zb
    print('VISTA', V['nome'], 'escala', round(s, 1), flush=True)
# ---------------- texels: posição e normal de cada pixel da textura (rasteriza no espaço UV)
tpos = np.zeros((TX, TX, 3)); tnor = np.zeros((TX, TX, 3)); tcau = np.zeros((TX, TX), bool); tok = np.zeros((TX, TX), bool)
for t, tl in zip(T, TL):
    p = UV[tl] * TX; p[:, 1] = TX - p[:, 1]
    x0, y0 = np.floor(p.min(0)).astype(int); x1, y1 = np.ceil(p.max(0)).astype(int)
    x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, TX - 1), min(y1, TX - 1)
    if x1 < x0 or y1 < y0: continue
    gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
    (ax, ay), (bx, by), (cx, cy) = p; den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
    if abs(den) < 1e-14: continue
    l1 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / den; l2 = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / den; l3 = 1 - l1 - l2
    ins = (l1 >= -0.02) & (l2 >= -0.02) & (l3 >= -0.02)
    if not ins.any(): continue
    L = np.stack([l1, l2, l3], -1)[ins]; yy_, xx_ = (gy[ins] - 0.5).astype(int), (gx[ins] - 0.5).astype(int)
    tpos[yy_, xx_] = L @ P[t]; n = L @ Nv[t]; tnor[yy_, xx_] = n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
    tcau[yy_, xx_] = CAUDA[t].any(); tok[yy_, xx_] = True
print('TEXELS', tok.sum(), flush=True)
# ---------------- projeção: cada texel pega a cor das vistas que o enxergam (peso = quão de frente a superfície está)
Q = tpos[tok]; Nq = tnor[tok]; Cq = tcau[tok]
soma = np.zeros((len(Q), 3)); peso = np.zeros(len(Q)); soma_l = np.zeros((len(Q), 3)); peso_l = np.zeros(len(Q))
for V in VISTAS:
    q = V['proj'](Q); H, W = V['zb'].shape; xi = np.clip(q[:, 0].astype(int), 0, W - 1); yi = np.clip(q[:, 1].astype(int), 0, H - 1)
    dentro = (q[:, 0] >= 0) & (q[:, 0] < W) & (q[:, 1] >= 0) & (q[:, 1] < H)
    dep = Q @ V['f']; vis = dentro & (dep <= V['zb'][yi, xi] + 0.012)
    # peso bem fechado (cos^12): quase sempre manda a vista mais de frente, sem misturar duas vistas que discordam (fantasma)
    cosv = np.clip(-(Nq @ V['f']), 0, 1); ok = vis * (cosv > 0.35) * (V['img'][yi, xi, 3] > 200) * ~V['linha'][yi, xi]   # rasante demais: estica o desenho
    if V['sem_cauda']: ok = ok * ~Cq
    w = ok * cosv ** 12; wl = ok * cosv ** 2
    # duas misturas: uma "fechada" (detalhe da vista mais de frente) e uma "aberta" (cor média, sem emenda)
    V['blur'] = cv2.GaussianBlur(V['img'][..., :3].astype(np.float32), (0, 0), 6)
    soma += w[:, None] * V['img'][yi, xi, :3]; peso += w; soma_l += wl[:, None] * V['blur'][yi, xi]; peso_l += wl
    print('PESO', V['nome'], round(float((w > 0).mean()), 3), flush=True)
cor = np.zeros((TX, TX, 3), np.uint8); vazio = np.ones((TX, TX), bool)
tem = peso > 1e-4; idx = np.argwhere(tok)
# detalhe da vista mais de frente + cor de fundo misturada entre as vistas: a emenda entre frente e lado some
# (o detalhe vem da vista fechada menos o desfoque dela mesma; o tom vem da mistura aberta)
det = soma[tem] / peso[tem, None]
somab = np.zeros((len(Q), 3)); pesob = np.zeros(len(Q))
for V in VISTAS:
    q = V['proj'](Q); H, W = V['zb'].shape; xi = np.clip(q[:, 0].astype(int), 0, W - 1); yi = np.clip(q[:, 1].astype(int), 0, H - 1)
    dentro = (q[:, 0] >= 0) & (q[:, 0] < W) & (q[:, 1] >= 0) & (q[:, 1] < H); dep = Q @ V['f']; vis = dentro & (dep <= V['zb'][yi, xi] + 0.012)
    cosv = np.clip(-(Nq @ V['f']), 0, 1); ok = vis * (cosv > 0.35) * (V['img'][yi, xi, 3] > 200) * ~V['linha'][yi, xi]
    if V['sem_cauda']: ok = ok * ~Cq
    w = ok * cosv ** 12; somab += w[:, None] * V['blur'][yi, xi]; pesob += w
baixa_fechada = somab[tem] / np.maximum(pesob[tem, None], 1e-9); baixa_aberta = soma_l[tem] / np.maximum(peso_l[tem, None], 1e-9)
final = det - baixa_fechada + baixa_aberta
cor[idx[tem, 0], idx[tem, 1]] = np.clip(final, 0, 255).astype(np.uint8); vazio[idx[tem, 0], idx[tem, 1]] = False
print('SEM COR (nenhuma vista vê)', round(float(((~tem)).mean()), 3), flush=True)
# o que nenhuma vista enxerga (topo da cabeça, embaixo do queixo, sola, dobras): cor dos pontos vistos mais próximos
# NA SUPERFÍCIE 3D (não na textura: lá as ilhas de UV vizinhas não são vizinhas no corpo, e o preenchimento riscava)
from scipy.spatial import cKDTree
vis_pos = Q[tem]; vis_cor = cor[idx[tem, 0], idx[tem, 1]].astype(float); arv = cKDTree(vis_pos)
d_, j_ = arv.query(Q[~tem], k=12); w_ = 1.0 / np.maximum(d_, 1e-4) ** 2
cor[idx[~tem, 0], idx[~tem, 1]] = np.clip((vis_cor[j_] * w_[..., None]).sum(1) / w_.sum(1, keepdims=True), 0, 255).astype(np.uint8)
# sangra um pouco para fora das ilhas de UV (evita fio escuro nas emendas da textura)
bgr = cv2.cvtColor(cor, cv2.COLOR_RGB2BGR); bgr = cv2.inpaint(bgr, (~tok).astype(np.uint8) * 255, 3, cv2.INPAINT_TELEA)
tex = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
cv2.imwrite(os.path.join(OUT, 'textura_desenho.png'), bgr)
# ---------------- cópia: troca a textura, tira os olhos de jogo (no desenho os olhos são pintados)
im = bpy.data.images.load(os.path.join(OUT, 'textura_desenho.png')); im.name = 'kumo_desenho'
mat = me.materials[0]; n = next(x for x in mat.node_tree.nodes if x.type == 'TEX_IMAGE'); n.image = im
# os olhos 3D (v5) ficam: são eles que fazem o olho do desenho em qualquer ângulo
cv2.imwrite(os.path.join(OUT, 'mascara_olhos_frente.png'), (VISTAS[0]['linha'] * 255).astype(np.uint8))
for m in body.modifiers: m.show_viewport = True
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'kumo_desenho.blend'), copy=True, relative_remap=False)
print('PD OK')
