"""Kumo · olhos novos com a arte do Caio (pedido de 2026-11-22), feitos como nos vídeos estudados.

  blender --background ../boca/kumo_v6_boca.blend --python olhos_novos.py -- <pasta_da_arte> <saída>

Pedido: "Faça os novos olhos do Kumo" com as 5 camadas enviadas (globo, círculo, membrana nictitante, íris,
pupila; o brilho fica para depois) e "faça igual aos vídeos, para não ter conflito com as camadas na hora do
movimento".

Como os vídeos fazem, e o que isso vira aqui:
- Globo ocular de verdade (@mokunachoi): uma esfera atrás da abertura. Branco, íris e pupila numa textura só,
  pintada na esfera. Olhar = a esfera gira; nada desliza sobre nada, então não há camadas brigando.
- Rig do olhar (@pol.gc): osso do olho no centro da esfera com Damped Track num alvo à frente. Os alvos dos dois
  olhos são movidos pelo controle `controle_olhar` (um só controle geral, como no rig de @tiago_prlco).
- Abertura: a pele ganha um buraco onde fica o olho (antes, a pele passava por baixo das camadas). A moldura de
  pele que já existia (cópia exata da pele em volta da abertura) continua por cima e agora leva o contorno preto e a
  membrana, fixos na borda, como na arte.
- Pálpebras e piscada: as mesmas de antes (shape keys + `controle_olhos`).
- Saem: as camadas antigas que deslizavam (OlhoBase, Iris, Pupil, Catchlight) e as 21 shape keys de olhar delas.
"""
import bpy, bmesh, sys, os, json, math
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

ARTE, OUT = sys.argv[-2:]
os.makedirs(os.path.join(OUT, 'texturas'), exist_ok=True)
V5 = '/home/user/Kumo-Character/kumo-3d-rodin/olhos-v5'
OLD_TEX = '/home/user/Kumo-Character/kumo-3d-rodin/v6-dev/olhos-jogo/texturas'
INFO = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'janelas_v5.json')))
GAZE_DEG = 11.0          # alcance do olhar (o mesmo de antes): controle_olhar = ±1 → ±11°
FOLGA = 0.0015           # o globo fica pelo menos 1,5 mm abaixo da pele que sobra em volta
REP = {}

img = bpy.data.images.get('kumo_quad_diffuse')
if img: img.filepath = '/home/user/Kumo-Character/kumo-3d-rodin/textures/kumo_quad_diffuse.png'; img.reload()
for im in bpy.data.images:
    if im.name.startswith('olho_') and not os.path.exists(bpy.path.abspath(im.filepath)):
        im.filepath = os.path.join(OLD_TEX, os.path.basename(im.filepath)); im.reload()
rig = bpy.data.objects['Kumo_Rig']; pb = rig.pose.bones; body = bpy.data.objects['Kumo']
for b in pb: b.location = (0, 0, 0)


# ------------------------------------------------------------------ imagens (numpy, origem embaixo à esquerda)
def ler(caminho):
    im = bpy.data.images.load(caminho, check_existing=False)
    a = np.array(im.pixels[:], dtype=np.float32).reshape(im.size[1], im.size[0], 4)
    bpy.data.images.remove(im); return a


def amostra(a, x, y):
    """Bilinear em pixels (x para a direita, y para cima, origem embaixo); fora = transparente."""
    h, w = a.shape[:2]
    x = np.asarray(x, np.float64) - 0.5; y = np.asarray(y, np.float64) - 0.5
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int); fx = (x - x0)[..., None]; fy = (y - y0)[..., None]
    def px(xx, yy):
        ok = (xx >= 0) & (xx < w) & (yy >= 0) & (yy < h)
        v = a[np.clip(yy, 0, h - 1), np.clip(xx, 0, w - 1)].copy(); v[~ok] = 0; return v
    return (px(x0, y0) * (1 - fx) * (1 - fy) + px(x0 + 1, y0) * fx * (1 - fy) + px(x0, y0 + 1) * (1 - fx) * fy + px(x0 + 1, y0 + 1) * fx * fy)


def sobre(fundo, topo):
    """topo por cima de fundo (cores lineares, alfa direto)."""
    at = topo[..., 3:4]; ab = fundo[..., 3:4]; ao = at + ab * (1 - at)
    c = (topo[..., :3] * at + fundo[..., :3] * ab * (1 - at)) / np.maximum(ao, 1e-6)
    return np.concatenate([c, ao], -1)


def salvar(a, nome):
    h, w = a.shape[:2]; im = bpy.data.images.new(nome, w, h, alpha=True)
    im.pixels.foreach_set(np.ascontiguousarray(a, np.float32).ravel())
    p = os.path.join(OUT, 'texturas', nome + '.png'); im.filepath_raw = p; im.file_format = 'PNG'; im.save()
    im.filepath = p; return im


A = {k: ler(os.path.join(ARTE, f)) for k, f in (('globo', 'globo-ocular.png'), ('circulo', 'globo-ocular-circulo.png'),
     ('membrana', 'membrana-nictitante.png'), ('iris', 'iris.png'), ('pupila', 'pupila.png'))}
# a arte: 1000×1000, todas as camadas no mesmo quadro. Centro e raio externo do contorno medidos na própria arte.
tinta = (A['circulo'][..., 3] > 0.5)
ys, xs = np.nonzero(tinta)
ART_C = np.array([(xs.min() + xs.max() + 1) / 2, (ys.min() + ys.max() + 1) / 2])
ART_R = float(np.hypot(xs + 0.5 - ART_C[0], ys + 0.5 - ART_C[1]).max())
REP['arte'] = {'centro_px': ART_C.round(1).tolist(), 'raio_externo_px': round(ART_R, 1)}


# ------------------------------------------------------------------ geometria
def avaliar(o, mods=True):
    dg = bpy.context.evaluated_depsgraph_get(); ev = o.evaluated_get(dg); m = ev.to_mesh(); m.calc_loop_triangles()
    V = [ev.matrix_world @ v.co for v in m.vertices]; T = [tuple(t.vertices) for t in m.loop_triangles]; ev.to_mesh_clear(); return V, T


def janela_uv(Mw, P):
    Mi = Mw.inverted(); q = [Mi @ p for p in P]
    return np.array([(x.x + 1) / 2 for x in q]), np.array([(x.y + 1) / 2 for x in q])


bpy.context.view_layer.update()
NOVOS = {}
for s in 'LR':
    Mw = Matrix(INFO[s]['Mw']); zw = (Mw.to_3x3() @ Vector((0, 0, 1))).normalized()
    Me = Matrix(INFO[s]['eye_mat'])                       # osso do olho da v5: eixos do olhar antigo
    mask4 = ler(os.path.join(V5, 'textures', f'olho_{s}_mask.png')); mask = mask4[..., 3]; MH = mask.shape[0]
    m_at = lambda u, v: amostra(mask4, np.asarray(u) * MH, np.asarray(v) * MH)[..., 3]
    # centro e raio da abertura (borda da máscara, por direção)
    yy, xx = np.nonzero(mask > 0.5); cm = np.array([(xx.mean() + 0.5) / MH, (yy.mean() + 0.5) / MH])
    TH = np.linspace(0, 2 * math.pi, 720, endpoint=False); RB = []
    for t in TH:
        rr = np.linspace(0, 0.6, 1200); vals = m_at(cm[0] + rr * math.cos(t), cm[1] + rr * math.sin(t))
        dentro = np.nonzero(vals > 0.5)[0]; RB.append(rr[dentro.max()] if len(dentro) else 0.0)
    RB = np.array(RB)
    # a borda antiga é irregular (degraus da projeção da v5); a abertura nova é a elipse de mesma área e mesmos eixos
    cov = np.cov(np.vstack([(xx + 0.5) / MH - cm[0], (yy + 0.5) / MH - cm[1]])); ev, evec = np.linalg.eigh(cov)
    EA, EB = 2 * math.sqrt(ev[1]), 2 * math.sqrt(ev[0]); EANG = math.atan2(evec[1, 1], evec[0, 1])
    def rb_at(th):
        t = np.asarray(th) - EANG; return EA * EB / np.sqrt((EB * np.cos(t)) ** 2 + (EA * np.sin(t)) ** 2)
    def q_at(u, v):                                       # 1 na borda da abertura, <1 dentro
        du, dv = np.asarray(u) - cm[0], np.asarray(v) - cm[1]; return np.hypot(du, dv) / rb_at(np.arctan2(dv, du))
    RB = rb_at(TH); r_med = float(RB.mean())
    REP.setdefault(s, {})['elipse_semi_eixos_uv'] = [round(EA, 4), round(EB, 4), round(math.degrees(EANG), 1)]
    REP[s].update({'abertura_centro_uv': cm.round(4).tolist(), 'abertura_raio_uv': [round(float(RB.min()), 4), round(r_med, 4), round(float(RB.max()), 4)]})

    # superfície do olho antigo dentro da abertura → esfera ajustada (centro do globo)
    Vb, Tb = avaliar(bpy.data.objects[f'KumoJogo_OlhoBase.{s}']); bvb = BVHTree.FromPolygons(Vb, Tb)
    P = []
    for vv in np.linspace(0.05, 0.95, 46):
        for uu in np.linspace(0.05, 0.95, 46):
            if q_at(uu, vv) < 1.0:
                o_ = Mw @ Vector((2 * uu - 1, 2 * vv - 1, 0)) + zw * 0.6; h = bvb.ray_cast(o_, -zw, 1.5)
                if h[0] is not None: P.append(tuple(h[0]))
    P = np.array(P); Am = np.c_[2 * P, np.ones(len(P))]; c4 = np.linalg.lstsq(Am, (P ** 2).sum(1), rcond=None)[0]
    C = Vector(c4[:3]); R_fit = float(math.sqrt(c4[3] + (c4[:3] ** 2).sum()))

    # ---------- moldura nova: grade na janela projetada na pele ainda inteira (+0,6 mm), sem filtrar por profundidade
    Vk0, Tk0 = avaliar(body); bvk0 = BVHTree.FromPolygons(Vk0, Tk0)
    M0, M1, NM = -0.14, 1.14, 128
    GM = np.linspace(M0, M1, NM + 1); Pm, ok = [], []
    for vv in GM:
        for uu in GM:
            h_ = bvk0.ray_cast(Mw @ Vector((2 * uu - 1, 2 * vv - 1, 0)) + zw * 0.6, -zw, 1.5)
            ok.append(h_[0] is not None); Pm.append((h_[0] if h_[0] is not None else Mw @ Vector((2 * uu - 1, 2 * vv - 1, 0))) + zw * 0.0006)
    Fm = [(k * (NM + 1) + j, k * (NM + 1) + j + 1, (k + 1) * (NM + 1) + j + 1, (k + 1) * (NM + 1) + j) for k in range(NM) for j in range(NM)]
    passo = (M1 - M0) / NM * 2 * max(Mw.to_scale()[0], Mw.to_scale()[1])
    Fm = [f for f in Fm if all(ok[i] for i in f) and max((Pm[f[i]] - Pm[f[(i + 1) % 4]]).length for i in range(4)) < 6 * passo]
    mo_velha = bpy.data.objects[f'KumoJogo_Moldura.{s}']
    mmesh = bpy.data.meshes.new(f'KumoOlho_Moldura.{s}'); mmesh.from_pydata([tuple(p) for p in Pm], [], Fm)
    uvm = mmesh.uv_layers.new(name='UVMap')
    for lp in mmesh.loops:
        i_ = lp.vertex_index; uvm.data[lp.index].uv = ((i_ % (NM + 1)) / NM, (i_ // (NM + 1)) / NM)
    mmesh.materials.append(mo_velha.material_slots[0].material)
    mnova = bpy.data.objects.new(f'KumoOlho_Moldura.{s}', mmesh); bpy.context.scene.collection.objects.link(mnova)
    # pesos: do vértice mais próximo da pele (como a moldura antiga)
    from mathutils.kdtree import KDTree
    kd = KDTree(len(Vk0))
    for i_, p in enumerate(Vk0): kd.insert(p, i_)
    kd.balance(); gnome = {g.index: g.name for g in body.vertex_groups}; grupos = {}
    for i_, p in enumerate(Pm):
        _, j_, _ = kd.find(p)
        for g in body.data.vertices[j_].groups:
            if g.weight > 1e-4 and not gnome[g.group].startswith(('outline', 'DEF', 'ORG')): grupos.setdefault(gnome[g.group], []).append((i_, g.weight))
    for gn, lst in grupos.items():
        vg_ = mnova.vertex_groups.new(name=gn)
        for i_, w_ in lst: vg_.add([i_], w_, 'REPLACE')
    mnova.parent = rig; amm = mnova.modifiers.new('Armature', 'ARMATURE'); amm.object = rig
    bpy.data.objects.remove(mo_velha)
    REP[s]['moldura_faces'] = len(Fm)

    # ---------- buraco na pele: faces da frente cuja projeção toca a abertura
    Vk, _ = avaliar(body)
    uk, vk = janela_uv(Mw, Vk); mk = q_at(uk, vk)
    frente = np.array([(p - C).dot(zw) > 0 for p in Vk])
    tocar = set(np.nonzero((mk < 1.0) & frente)[0].tolist())
    me = body.data; bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
    apagar = [f for f in bm.faces if any(v.index in tocar for v in f.verts)]
    REP[s]['faces_da_pele_removidas'] = len(apagar)
    bmesh.ops.delete(bm, geom=apagar, context='FACES'); bm.to_mesh(me); bm.free(); me.update()
    bpy.context.view_layer.update()

    # ---------- raio do globo: o maior que fica FOLGA abaixo de toda a pele que sobra perto da abertura
    Vk, Tk = avaliar(body); bvk = BVHTree.FromPolygons(Vk, Tk)
    # centro e raio do globo: procura o centro que deixa o globo o mais perto possível da superfície antiga do olho,
    # com a condição de ficar FOLGA abaixo de toda a pele que sobra dentro da calota (abertura + alcance do olhar).
    hc = bvb.ray_cast(Mw @ Vector((2 * cm[0] - 1, 2 * cm[1] - 1, 0)) + zw * 0.6, -zw, 1.5)[0]
    bordaw = [Mw @ Vector((2 * (cm[0] + r * math.cos(t)) - 1, 2 * (cm[1] + r * math.sin(t)) - 1, 0)) for t, r in zip(TH[::12], RB[::12])]
    bordaw = np.array([tuple(bvb.ray_cast(Vector(b_) + zw * 0.6, -zw, 1.5)[0] or Vector(b_)) for b_ in bordaw])
    VK = np.array([tuple(p) for p in Vk]); PP = P; HC = np.array(tuple(hc))
    # pontos da superfície antiga junto à borda (q = 0,96): é ali que o fundo do globo aparece visto de lado
    PR = []
    for t, r in zip(TH[::4], RB[::4]):
        b_ = Mw @ Vector((2 * (cm[0] + 0.96 * r * math.cos(t)) - 1, 2 * (cm[1] + 0.96 * r * math.sin(t)) - 1, 0))
        h_ = bvb.ray_cast(b_ + zw * 0.6, -zw, 1.5)[0]
        if h_ is not None: PR.append(tuple(h_))
    PR = np.array(PR)
    a1 = np.array(tuple(Vector(Mw.col[0][:3]).normalized())); a2 = np.array(tuple(Vector(Mw.col[1][:3]).normalized())); zn = np.array(tuple(zw))
    def avalia(Cn):
        e = HC - Cn; e /= np.linalg.norm(e)
        cb = (bordaw - Cn) / np.linalg.norm(bordaw - Cn, axis=1)[:, None]; ab = math.degrees(math.acos(min(1, (cb @ e).min())))
        cap = ab + GAZE_DEG + 6.0
        dv = VK - Cn; nv = np.linalg.norm(dv, axis=1); cosv = (dv @ e) / nv
        sel = cosv > math.cos(math.radians(cap + 16))     # a calota gira até ~15,6° (olhar na diagonal)
        if not sel.any(): return None
        Rn = nv[sel].min() - FOLGA; rec = np.linalg.norm(PP - Cn, axis=1) - Rn
        if rec.min() < 0.0005: return None          # o globo fica abaixo da superfície antiga (onde as pálpebras fecham)
        rb_ = np.linalg.norm(PR - Cn, axis=1) - Rn
        return float(rb_.mean() + 0.5 * rb_.max()), Rn, e, ab, cap, rec
    melhor = None
    C0 = np.array(tuple(C))
    for t in np.linspace(-0.6, 0.6, 25):
        for l1 in np.linspace(-0.2, 0.2, 11):
            for l2 in np.linspace(-0.2, 0.2, 11):
                Cn = C0 - zn * t + a1 * l1 + a2 * l2
                r_ = avalia(Cn)
                if r_ and r_[1] > 0.15 and (melhor is None or r_[0] < melhor[0][0]): melhor = (r_, Cn)
    (custo, R_globo, e, ang_ab, CAP, rec), Cn = melhor
    C = Vector(Cn); eixo = Vector(e)
    REP[s].update({'esfera_ajustada_raio_m': round(R_fit, 4), 'globo_centro': [round(x, 4) for x in C], 'globo_raio_m': round(R_globo, 4),
                   'abertura_angulo_graus': round(ang_ab, 2), 'calota_graus': round(CAP, 2)})
    # recuo: quanto o globo fica abaixo da superfície antiga do olho, no meio e na borda
    REP[s]['recuo_mm(min,mediana,max)'] = [round(float(rec.min()) * 1000, 1), round(float(np.median(rec)) * 1000, 1), round(float(rec.max()) * 1000, 1)]
    rbd = (np.linalg.norm(PR - np.array(tuple(C)), axis=1) - R_globo) * 1000
    REP[s]['recuo_na_borda_mm(min,media,max)'] = [round(float(rbd.min()), 1), round(float(rbd.mean()), 1), round(float(rbd.max()), 1)]

    # ---------- o globo: calota de esfera, polo no eixo da abertura
    gm = bpy.data.meshes.new(f'KumoOlho_Globo.{s}'); bmg = bmesh.new()
    NA, NR = 96, 40
    q = eixo.to_track_quat('Z', 'Y'); Rq = q.to_matrix()
    verts = [bmg.verts.new(C + Rq @ Vector((0, 0, R_globo)))]
    for i in range(1, NR + 1):
        a_ = math.radians(CAP) * i / NR
        for j in range(NA):
            t = 2 * math.pi * j / NA
            verts.append(bmg.verts.new(C + Rq @ (Vector((math.sin(a_) * math.cos(t), math.sin(a_) * math.sin(t), math.cos(a_))) * R_globo)))
    for j in range(NA): bmg.faces.new((verts[0], verts[1 + j], verts[1 + (j + 1) % NA]))
    for i in range(NR - 1):
        for j in range(NA):
            a0 = 1 + i * NA; a1 = 1 + (i + 1) * NA
            bmg.faces.new((verts[a0 + j], verts[a1 + j], verts[a1 + (j + 1) % NA], verts[a0 + (j + 1) % NA]))
    bmg.to_mesh(gm); bmg.free()
    # UV = coordenada da janela no repouso (a textura é pintada nesse espaço)
    ug, vg = janela_uv(Mw, [v.co for v in gm.vertices]); uvl = gm.uv_layers.new(name='UVMap')
    for lp in gm.loops: uvl.data[lp.index].uv = (ug[lp.vertex_index], vg[lp.vertex_index])
    for p in gm.polygons: p.use_smooth = True

    # ---------- textura do globo: branco + íris + pupila (a arte, na escala da abertura)
    RES = 2048
    gx, gy = np.meshgrid((np.arange(RES) + 0.5) / RES, (np.arange(RES) + 0.5) / RES)
    ic = np.array(INFO[s]['iris_centro'])                   # onde a íris descansa (olhando para a frente)
    esc = ART_R / r_med                                      # px da arte por unidade de janela
    ax_ = ART_C[0] + (gx - ic[0]) * esc; ay_ = ART_C[1] + (gy - ic[1]) * esc   # imagens lidas com y para cima
    tex = np.zeros((RES, RES, 4), np.float32); tex[..., :3] = A['globo'][500, 500, :3]; tex[..., 3] = 1.0   # branco do globo
    for k in ('iris', 'pupila'):
        tex = sobre(tex, amostra(A[k], ax_, ay_))
    tex[..., 3] = 1.0
    im_g = salvar(tex, f'olho_{s}_globo')
    mat = bpy.data.materials['KumoJogo_OlhoBase.' + s].copy(); mat.name = f'KumoOlho_Globo.{s}'
    for nd in mat.node_tree.nodes:
        if nd.type == 'TEX_IMAGE': nd.image = im_g; nd.extension = 'EXTEND'
    try: mat.surface_render_method = 'DITHERED'
    except Exception: pass
    gm.materials.append(mat)
    go = bpy.data.objects.new(f'KumoOlho_Globo.{s}', gm); bpy.context.scene.collection.objects.link(go)

    # ---------- moldura: pele + contorno + membrana, deformados para casar com a borda da abertura
    mt = mnova.material_slots[0].material.copy(); mt.name = f'KumoOlho_Moldura.{s}'; mnova.material_slots[0].material = mt
    timg = [n for n in mt.node_tree.nodes if n.type == 'TEX_IMAGE'][0]
    velha = ler(os.path.join(OLD_TEX, f'olho_{s}_moldura.png'))
    RM = 1536
    px_ = M0 + (np.arange(RM) + 0.5) / RM * (M1 - M0); mx, my = np.meshgrid(px_, px_)
    pele = amostra(velha, (mx - M0) / (M1 - M0) * velha.shape[1], (my - M0) / (M1 - M0) * velha.shape[0])
    dx, dy = mx - cm[0], my - cm[1]; rr = np.hypot(dx, dy); th = np.arctan2(dy, dx)
    # faixa logo fora da abertura: a pele antiga tem a sombra e a borda do olho velho pintadas.
    # Na faixa q de 1 a 1,22 a cor vem da pele em q = 1,28 na mesma direção (e se mistura de volta até 1,30).
    qq = rr / rb_at(th); fonte = amostra(velha, ((cm[0] + 1.28 * rb_at(th) * np.cos(th)) - M0) / (M1 - M0) * velha.shape[1],
                                         ((cm[1] + 1.28 * rb_at(th) * np.sin(th)) - M0) / (M1 - M0) * velha.shape[0])
    wmix = np.clip((1.30 - qq) / 0.08, 0, 1)[..., None]
    pele[..., :3] = pele[..., :3] * (1 - wmix) + fonte[..., :3] * wmix
    rho = rr / rb_at(th) * ART_R                             # borda da abertura = borda de fora do contorno
    sx = ART_C[0] + rho * np.cos(th); sy = ART_C[1] + rho * np.sin(th)
    aro = sobre(amostra(A['membrana'], sx, sy), amostra(A['circulo'], sx, sy))
    px_uv = (M1 - M0) / RM; mk_ = np.clip((1.0 - qq) * rb_at(th) / px_uv + 0.5, 0, 1)   # dentro da elipse, com 1 px de suavização
    pele[..., 3] = 1.0 - mk_                                 # pele só fora da abertura
    mold = sobre(pele, aro * mk_[..., None])                 # aro só dentro da abertura
    im_m = salvar(mold, f'olho_{s}_moldura_nova'); timg.image = im_m
    REP[s]['aro_largura_uv'] = round(float((ART_R - 290.8) / ART_R * r_med), 4)

    # ---------- osso do olho + alvo (Damped Track), como no vídeo do decal
    D = 1.0                                                  # distância do alvo à frente do olho
    ux = Vector(Me.col[2][:3]).normalized().cross(eixo).normalized()   # +X do controle: giro em torno do "para cima" do olho
    uy = Vector(Me.col[0][:3]).normalized().cross(eixo).normalized()   # +Y do controle: giro em torno do eixo lateral
    NOVOS[s] = dict(obj=go, C=C, eixo=eixo, ux=ux, uy=uy, D=D)
    # o ponto da íris no repouso, para conferir o sentido do olhar contra o olhar antigo
    pc = Mw @ Vector((2 * ic[0] - 1, 2 * ic[1] - 1, 0)) + zw * 0.6
    hit = bvb.ray_cast(pc, -zw, 1.5)[0]
    NOVOS[s]['iris_antiga_repouso'] = hit

# ------------------------------------------------------------------ rig
bpy.context.view_layer.objects.active = rig; rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT'); eb = rig.data.edit_bones
for s, d in NOVOS.items():
    b = eb.new(f'olho.{s}'); b.head = d['C']; b.tail = d['C'] + d['eixo'] * 0.12; b.parent = eb['head']; b.use_deform = True
    # alvo: osso mecânico à frente do olho; os eixos locais dele = direções do olhar (X = +controle X, Z = +controle Y)
    t = eb.new(f'MCH_alvo_olho.{s}'); t.head = d['C'] + d['eixo'] * d['D']; t.tail = t.head + d['eixo'] * 0.08
    t.align_roll(d['uy'] if d['uy'].dot(d['ux'].cross(d['eixo'])) >= 0 else -d['uy'])
    t.parent = eb['head']; t.use_deform = False
    # sinal do eixo Z local do alvo em relação a +Y do controle
    d['sz'] = 1.0 if Vector(t.z_axis).dot(d['uy']) >= 0 else -1.0
    d['sx'] = 1.0 if Vector(t.x_axis).dot(d['ux']) >= 0 else -1.0
bpy.ops.object.mode_set(mode='POSE')
k = math.tan(math.radians(GAZE_DEG))
for s, d in NOVOS.items():
    mch = pb[f'MCH_alvo_olho.{s}']
    c = mch.constraints.new('TRANSFORM'); c.name = 'Olhar'; c.target = rig; c.subtarget = 'controle_olhar'
    c.target_space = 'LOCAL'; c.owner_space = 'LOCAL'; c.map_from = 'LOCATION'; c.map_to = 'LOCATION'; c.use_motion_extrapolate = True
    c.from_min_x, c.from_max_x, c.from_min_y, c.from_max_y = -1, 1, -1, 1
    c.map_to_x_from = 'X'; c.map_to_z_from = 'Y'; c.map_to_y_from = 'Z'
    c.to_min_x, c.to_max_x = -k * d['D'] * d['sx'], k * d['D'] * d['sx']
    c.to_min_z, c.to_max_z = -k * d['D'] * d['sz'], k * d['D'] * d['sz']
    dt = pb[f'olho.{s}'].constraints.new('DAMPED_TRACK'); dt.target = rig; dt.subtarget = f'MCH_alvo_olho.{s}'; dt.track_axis = 'TRACK_Y'
bpy.ops.object.mode_set(mode='OBJECT')
for s, d in NOVOS.items():
    go = d['obj']; vg = go.vertex_groups.new(name=f'olho.{s}'); vg.add(range(len(go.data.vertices)), 1.0, 'REPLACE')
    go.parent = rig; am = go.modifiers.new('Armature', 'ARMATURE'); am.object = rig

# ------------------------------------------------------------------ sai o olho antigo (camadas que deslizavam e o brilho)
for s in 'LR':
    for n in ('OlhoBase', 'Iris', 'Pupil', 'Catchlight'):
        o = bpy.data.objects.get(f'KumoJogo_{n}.{s}')
        if o: bpy.data.objects.remove(o)


# ------------------------------------------------------------------ conferência do olhar: o sentido bate com o antigo?
def ponto_iris(s):
    go = NOVOS[s]['obj']; V, _ = avaliar(go)
    Mw = Matrix(INFO[s]['Mw']); ug, vg = janela_uv(Mw, [v.co for v in go.data.vertices])
    ic = np.array(INFO[s]['iris_centro']); i = int(np.argmin((ug - ic[0]) ** 2 + (vg - ic[1]) ** 2)); return V[i]


ANT = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'olhar_antigo.json')))
REP['olhar'] = {}
for nome, (gx_, gy_) in (('dir', (1, 0)), ('esq', (-1, 0)), ('cima', (0, 1)), ('baixo', (0, -1))):
    pb['controle_olhar'].location = (0, 0, 0); bpy.context.view_layer.update(); p0 = {s: ponto_iris(s) for s in 'LR'}
    pb['controle_olhar'].location = (gx_, gy_, 0); bpy.context.view_layer.update()
    for s in 'LR':
        dn = ponto_iris(s) - p0[s]; da = Vector(ANT[s][nome])
        ang = math.degrees(pb[f'olho.{s}'].matrix.to_3x3().col[1].angle(NOVOS[s]['eixo']))
        REP['olhar'][f'{nome}_{s}'] = {'giro_graus': round(ang, 2), 'desloc_mm': round(dn.length * 1000, 1),
                                       'antigo_mm': round(da.length * 1000, 1), 'angulo_entre_sentidos_graus': round(math.degrees(dn.angle(da)), 1) if da.length > 1e-6 and dn.length > 1e-6 else None}
pb['controle_olhar'].location = (0, 0, 0); bpy.context.view_layer.update()

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'kumo_v6_olhos_novos.blend'))
json.dump(REP, open(os.path.join(OUT, 'medicoes_olhos_novos.json'), 'w'), indent=1, ensure_ascii=False)
print('REP', json.dumps(REP, ensure_ascii=False))
