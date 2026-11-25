"""Kumo · olhos novos com a arte do Caio (pedido de 2026-11-22), feitos como no vídeo do decal (@pol.gc).

  blender --background ../boca/kumo_v6_boca.blend --python olhos_novos.py -- <pasta_da_arte> <saída>

Pedido: "Faça os novos olhos do Kumo" com as camadas enviadas (globo, círculo, membrana nictitante, íris, pupila;
o brilho fica para depois) e "faça igual aos vídeos, para não ter conflito com as camadas na hora do movimento".

Como fica:
- UMA superfície por olho, no lugar exato da pele: as faces da pele em volta do olho viram um objeto próprio
  (`KumoOlho.L/.R`), com a mesma forma, os mesmos pesos e a mesma borda da pele. Nada fica empilhado.
- UM material faz tudo, na ordem certa: pele → branco do globo → íris e pupila (decal) → membrana e contorno.
  Como é um material só, não existe camada para brigar no movimento.
- Íris e pupila são um DECAL (vídeo de @pol.gc): a imagem é projetada a partir de um Empty (`Decal_Olho.L/.R`)
  preso ao osso `olho.L/.R`. O osso gira (Damped Track num alvo) e o decal desliza pela superfície.
- O alvo de cada olho é movido pelo controle de sempre, `controle_olhar` (±1 = ±11°, os mesmos sentidos de antes).
- Pálpebras e piscada: as mesmas de antes. Saem as camadas antigas (fundo, íris, pupila, brilho, moldura).

Tentativa anterior, registrada em `tentativa_globo_esferico.py`: um globo esférico girando dentro de um buraco na
pele. Não serve para o Kumo: a região do olho é quase plana e a esfera precisaria ficar 3 a 8 cm afundada para
girar sem atravessar a pele; vista de frente, aparecia a parede de dentro da cabeça.
"""
import bpy, bmesh, sys, os, json, math
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

ARTE, OUT = sys.argv[-2:]
os.makedirs(os.path.join(OUT, 'texturas'), exist_ok=True)
AQUI = os.path.dirname(os.path.abspath(__file__))
V5 = '/home/user/Kumo-Character/kumo-3d-rodin/olhos-v5'
OLD_TEX = '/home/user/Kumo-Character/kumo-3d-rodin/v6-dev/olhos-jogo/texturas'
INFO = json.load(open(os.path.join(AQUI, 'janelas_v5.json')))
GAZE_DEG = 11.0          # controle_olhar = ±1 → ±11° (o mesmo alcance de antes)
ALAVANCA = 0.35          # o osso do olho gira 0,35 m para dentro da superfície (dá o mesmo deslocamento do olhar antigo)
Q_PATCH = 1.36           # a superfície do olho vai até 1,36 × o raio da abertura (inclui a faixa de pele limpa)
REP = {}

img = bpy.data.images.get('kumo_quad_diffuse')
if img: img.filepath = '/home/user/Kumo-Character/kumo-3d-rodin/textures/kumo_quad_diffuse.png'; img.reload()
rig = bpy.data.objects['Kumo_Rig']; pb = rig.pose.bones; body = bpy.data.objects['Kumo']
for b in pb: b.location = (0, 0, 0)
bpy.context.view_layer.update()


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
    at = topo[..., 3:4]; ab = fundo[..., 3:4]; ao = at + ab * (1 - at)
    c = (topo[..., :3] * at + fundo[..., :3] * ab * (1 - at)) / np.maximum(ao, 1e-6)
    return np.concatenate([c, ao], -1)


def salvar(a, nome, dados=False):
    h, w = a.shape[:2]; im = bpy.data.images.new(nome, w, h, alpha=True)
    im.pixels.foreach_set(np.ascontiguousarray(a, np.float32).ravel())
    p = os.path.join(OUT, 'texturas', nome + '.png'); im.filepath_raw = p; im.file_format = 'PNG'; im.save()
    im.filepath = p
    if dados: im.colorspace_settings.name = 'Non-Color'
    return im


A = {k: ler(os.path.join(ARTE, f)) for k, f in (('globo', 'globo-ocular.png'), ('circulo', 'globo-ocular-circulo.png'),
     ('membrana', 'membrana-nictitante.png'), ('iris', 'iris.png'), ('pupila', 'pupila.png'))}
# 22/11, segundo pedido do Caio: a membrana nictitante na cor #E4A633 (a forma e a transparência ficam as da arte)
COR_MEMBRANA = np.array([0xE4, 0xA6, 0x33], np.float32) / 255
A['membrana'][..., :3] = COR_MEMBRANA
# e a íris e a pupila de uma imagem só (`iris-pupila.png`): a íris do mesmo tamanho, a pupila menor
IRIS_PUPILA = os.path.join(ARTE, 'iris-pupila.png')
ys, xs = np.nonzero(A['circulo'][..., 3] > 0.5)
ART_C = np.array([(xs.min() + xs.max() + 1) / 2, (ys.min() + ys.max() + 1) / 2])     # centro do contorno (px, y para cima)
ART_R = float(np.hypot(xs + 0.5 - ART_C[0], ys + 0.5 - ART_C[1]).max())                # raio de fora do contorno
BRANCO = A['globo'][int(ART_C[1]), int(ART_C[0]), :3].copy()
# 25/11, pedido do Caio: o branco do globo em tom dourado suave (#F4E3B5), para não destoar do olho antigo (#E4BF74).
# O valor vem em sRGB e vai para linear, como a arte que o Blender lê.
_hex = np.array([0xF7, 0xF3, 0xEA], np.float32) / 255   # 26/11: off-white, pedido do Caio (no lugar do dourado)
BRANCO = np.where(_hex <= 0.04045, _hex / 12.92, ((_hex + 0.055) / 1.055) ** 2.4).astype(np.float32)
REP['arte'] = {'centro_px': ART_C.round(1).tolist(), 'raio_externo_px': round(ART_R, 1), 'branco': BRANCO.round(3).tolist()}
# a imagem do decal: íris com a pupila por cima, no quadro da arte
if os.path.exists(IRIS_PUPILA):
    ip = ler(IRIS_PUPILA)
    # 26/11: o anel da íris em âmbar escuro (#DE9C1E), como no olho antigo; a arte tinha um âmbar mais claro
    anel = (ip[..., 3] > 0.5) & (ip[..., 0] > 0.5) & (ip[..., 2] < 0.6)
    ip[anel, 0:3] = np.array([0xDE, 0x9C, 0x1E], np.float32) / 255 * np.array([1, 1, 1], np.float32)
    # só a elipse da íris (a imagem tem um ponto solto perto da borda de baixo)
    yy_, xx_ = np.nonzero((ip[..., 3] > 0.5) & (ip[..., 0] > 0.5))
    cx_, cy_ = (xx_.min() + xx_.max()) / 2, (yy_.min() + yy_.max()) / 2; ax_, ay_ = (xx_.max() - xx_.min()) / 2 + 3, (yy_.max() - yy_.min()) / 2 + 3
    Y_, X_ = np.mgrid[0:ip.shape[0], 0:ip.shape[1]]
    ip[((X_ + 0.5 - cx_) / ax_) ** 2 + ((Y_ + 0.5 - cy_) / ay_) ** 2 > 1, 3] = 0
    REP['decal'] = {'arquivo': 'iris-pupila.png', 'iris_px': [int(xx_.max() - xx_.min() + 1), int(yy_.max() - yy_.min() + 1)]}
    im_decal = salvar(ip, 'olho_decal_iris_pupila')
else:
    im_decal = salvar(sobre(A['iris'], A['pupila']), 'olho_decal_iris_pupila')
im_decal.alpha_mode = 'STRAIGHT'


def janela_uv(Mw, P):
    Mi = Mw.inverted(); q = [Mi @ p for p in P]
    return np.array([(x.x + 1) / 2 for x in q]), np.array([(x.y + 1) / 2 for x in q])


skin_mat = body.material_slots[0].material
UV_PELE = body.data.uv_layers.active.name
NOVOS = {}
for s in 'LR':
    REP[s] = {}
    Mw = Matrix(INFO[s]['Mw']); zw = (Mw.to_3x3() @ Vector((0, 0, 1))).normalized()
    Me = Matrix(INFO[s]['eye_mat'])
    mask4 = ler(os.path.join(V5, 'textures', f'olho_{s}_mask.png')); mask = mask4[..., 3]; MH = mask.shape[0]
    # abertura: a elipse de mesma área e eixos da abertura antiga (a borda antiga era irregular, em degraus)
    yy, xx = np.nonzero(mask > 0.5); cm = np.array([(xx.mean() + 0.5) / MH, (yy.mean() + 0.5) / MH])
    cov = np.cov(np.vstack([(xx + 0.5) / MH - cm[0], (yy + 0.5) / MH - cm[1]])); ev, evec = np.linalg.eigh(cov)
    EA, EB = 2 * math.sqrt(ev[1]), 2 * math.sqrt(ev[0]); EANG = math.atan2(evec[1, 1], evec[0, 1])
    def rb_at(th, EA=EA, EB=EB, EANG=EANG):
        t = np.asarray(th) - EANG; return EA * EB / np.sqrt((EB * np.cos(t)) ** 2 + (EA * np.sin(t)) ** 2)
    def q_at(u, v, cm=cm, rb_at=rb_at):
        du, dv = np.asarray(u) - cm[0], np.asarray(v) - cm[1]; return np.hypot(du, dv) / rb_at(np.arctan2(dv, du))
    r_med = float(rb_at(np.linspace(0, 2 * math.pi, 720)).mean())
    REP[s].update({'abertura_centro_uv': cm.round(4).tolist(), 'elipse_semi_eixos_uv': [round(EA, 4), round(EB, 4)], 'elipse_angulo_graus': round(math.degrees(EANG), 1)})

    # ---------- a superfície do olho: as faces da pele que tocam a região (q < Q_PATCH), separadas num objeto próprio
    Cref = Vector(Me.col[3][:3])
    for o in bpy.context.selected_objects: o.select_set(False)
    body.select_set(True); bpy.context.view_layer.objects.active = body
    bpy.ops.object.mode_set(mode='EDIT'); bm = bmesh.from_edit_mesh(body.data)
    mwb = body.matrix_world; V = [mwb @ v.co for v in bm.verts]; uk, vk = janela_uv(Mw, V); qk = q_at(uk, vk)
    perto = {v.index for v in bm.verts if qk[v.index] < Q_PATCH and (V[v.index] - Cref).dot(zw) > -0.05}
    for f in bm.faces: f.select = any(v.index in perto for v in f.verts)
    nsel = sum(1 for f in bm.faces if f.select); bmesh.update_edit_mesh(body.data)
    antes = set(bpy.data.objects.keys()); bpy.ops.mesh.separate(type='SELECTED'); bpy.ops.object.mode_set(mode='OBJECT')
    olho = bpy.data.objects[(set(bpy.data.objects.keys()) - antes).pop()]
    olho.name = olho.data.name = f'KumoOlho.{s}'
    # o contorno do Kumo é um Solidify (casca invertida) que só funciona em malha fechada; numa superfície aberta ele
    # desenha uma faixa escura na borda. O olho fica só com a Armature (o contorno de fora continua no Kumo).
    for md in list(olho.modifiers):
        if md.type != 'ARMATURE': olho.modifiers.remove(md)
    REP[s]['faces_da_superficie'] = nsel
    # UV da janela (o espaço da arte)
    uvj = olho.data.uv_layers.new(name='Janela'); ug, vg = janela_uv(Mw, [olho.matrix_world @ v.co for v in olho.data.vertices])
    for lp in olho.data.loops: uvj.data[lp.index].uv = (ug[lp.vertex_index], vg[lp.vertex_index])
    olho.data.uv_layers.active = olho.data.uv_layers[UV_PELE]
    qmax = float(q_at(ug, vg).max()); U0 = min(ug.min(), vg.min()) - 0.02; U1 = max(ug.max(), vg.max()) + 0.02
    REP[s]['janela_da_textura'] = [round(U0, 3), round(U1, 3)]

    # esticamento: quanto de pele (m) cabe em 1 unidade de janela, na direção radial, junto à borda, por direção.
    # Onde a superfície se curva para longe da projeção, a mesma faixa da janela cobre mais pele: o aro afina ali.
    Vp = [olho.matrix_world @ v.co for v in olho.data.vertices]; olho.data.calc_loop_triangles()
    bvo = BVHTree.FromPolygons(Vp, [tuple(t.vertices) for t in olho.data.loop_triangles])
    def na_sup(u, v):
        return bvo.ray_cast(Mw @ Vector((2 * u - 1, 2 * v - 1, 0)) + zw * 0.6, -zw, 1.5)[0]
    THs = np.linspace(0, 2 * math.pi, 360, endpoint=False)
    # a abertura recua onde a superfície fica de lado para a projeção (normal · eixo < 0,45): ali a arte esticaria.
    # É o que a borda antiga, irregular, fazia; aqui a borda continua lisa.
    rbe = []
    for t in THs:
        r_el = float(rb_at(t)); lim = r_el
        for r in np.linspace(0.55 * r_el, 1.04 * r_el, 50):
            h_ = bvo.ray_cast(Mw @ Vector((2 * (cm[0] + r * math.cos(t)) - 1, 2 * (cm[1] + r * math.sin(t)) - 1, 0)) + zw * 0.6, -zw, 1.5)
            if h_[0] is None or h_[1].dot(zw) < 0.45: lim = min(r_el, r / 1.04); break
        rbe.append(lim)
    rbe = np.array(rbe); W_ = 10
    ext_ = np.r_[rbe[-W_:], rbe, rbe[:W_]]
    rbe = np.array([ext_[i:i + 2 * W_ + 1].min() for i in range(len(rbe))])                  # não deixa passar da dobra
    ext_ = np.r_[rbe[-W_:], rbe, rbe[:W_]]; rbe = np.convolve(ext_, np.ones(2 * W_ + 1) / (2 * W_ + 1), mode='valid')   # e alisa
    REP[s]['abertura_recuo_max_pct'] = round(float((1 - rbe / rb_at(THs)).max() * 100), 1)
    rb_el = rb_at
    def rb_at(th, THs=THs, rbe=rbe):
        return np.interp(np.mod(th, 2 * math.pi), np.r_[THs, 2 * math.pi], np.r_[rbe, rbe[0]])
    r_med = float(rbe.mean())
    est = []
    for t in THs:
        r = float(rb_at(t)); a_ = na_sup(cm[0] + r * math.cos(t), cm[1] + r * math.sin(t)); b_ = na_sup(cm[0] + 0.92 * r * math.cos(t), cm[1] + 0.92 * r * math.sin(t))
        est.append((a_ - b_).length / (0.08 * r) if a_ is not None and b_ is not None else np.nan)
    est = np.array(est); est[np.isnan(est)] = np.nanmedian(est)
    est = np.convolve(np.r_[est[-15:], est, est[:15]], np.ones(31) / 31, mode='valid')   # suaviza em volta (±15°)
    est_rel = est / np.median(est)
    REP[s]['esticamento_relativo(min,max)'] = [round(float(est_rel.min()), 2), round(float(est_rel.max()), 2)]
    est_at = lambda th: np.interp(np.mod(th, 2 * math.pi), np.r_[THs, 2 * math.pi], np.r_[est_rel, est_rel[0]])

    # ---------- texturas no espaço da janela (U0..U1)
    RES = 2048
    g = U0 + (np.arange(RES) + 0.5) / RES * (U1 - U0); mx, my = np.meshgrid(g, g)
    dx, dy = mx - cm[0], my - cm[1]; th = np.arctan2(dy, dx); rbt = rb_at(th); qq = np.hypot(dx, dy) / rbt
    px_uv = (U1 - U0) / RES
    dentro = np.clip((1.0 - qq) * rbt / px_uv + 0.5, 0, 1)            # 1 dentro da abertura, borda de 1 px
    # pele limpa na faixa logo fora da abertura: a pele antiga tem a sombra e a borda do olho velho pintadas.
    # A cor vem da pele em q = 1,30 na mesma direção; a faixa cobre até q = 1,18 e some até q = 1,28.
    velha = ler(os.path.join(OLD_TEX, f'olho_{s}_moldura.png')); MV0, MV1 = -0.14, 1.14
    # cor por direção: mediana da pele entre q = 1,30 e 1,50 (5 pontos), depois mediana em volta (±12°):
    # um traço escuro antigo num ponto só não contamina a faixa
    TA = np.linspace(-math.pi, math.pi, 720, endpoint=False); cores = []
    for t in TA:
        rq = rb_at(t) * np.linspace(1.30, 1.50, 5)
        a_ = amostra(velha, (cm[0] + rq * math.cos(t) - MV0) / (MV1 - MV0) * velha.shape[1], (cm[1] + rq * math.sin(t) - MV0) / (MV1 - MV0) * velha.shape[0])
        a_ = a_[a_[:, 3] > 0.5]; cores.append(np.median(a_[:, :3], 0) if len(a_) else np.full(3, np.nan))
    cores = np.array(cores); bad = np.isnan(cores[:, 0]); cores[bad] = np.nanmedian(cores, 0)
    W = 24; ext = np.r_[cores[-W:], cores, cores[:W]]
    cores = np.array([np.median(ext[i:i + 2 * W + 1], 0) for i in range(len(cores))])
    ia = ((th + math.pi) / (2 * math.pi) * 720).astype(int) % 720
    fonte = np.concatenate([cores[ia], np.ones(th.shape + (1,), np.float32)], -1)
    banda = np.clip((1.28 - qq) / 0.10, 0, 1) * (fonte[..., 3] > 0.5)
    fundo = np.zeros((RES, RES, 4), np.float32)
    fundo[..., :3] = fonte[..., :3] * (1 - dentro[..., None]) + BRANCO * dentro[..., None]
    fundo[..., 3] = np.maximum(dentro, banda)
    im_fundo = salvar(fundo, f'olho_{s}_fundo')
    # aro (membrana + contorno) deformado para a borda de fora do contorno cair na borda da abertura
    rho = ART_R - (1.0 - qq) * ART_R * est_at(th)       # largura do aro igual na pele em toda a volta
    sx = ART_C[0] + rho * np.cos(th); sy = ART_C[1] + rho * np.sin(th)
    aro = sobre(amostra(A['membrana'], sx, sy), amostra(A['circulo'], sx, sy)); aro[..., 3] *= dentro
    im_aro = salvar(aro, f'olho_{s}_aro')
    msk = np.zeros((RES, RES, 4), np.float32); msk[..., 0] = msk[..., 1] = msk[..., 2] = dentro; msk[..., 3] = 1
    im_dentro = salvar(msk, f'olho_{s}_dentro', dados=True)
    REP[s]['aro_largura_uv'] = round(float((ART_R - 290.8) / ART_R * r_med), 4)

    # ---------- rig: osso do olho (alavanca para dentro) + alvo à frente, como no vídeo
    ic = np.array(INFO[s]['iris_centro'])                   # onde a íris descansa: o mesmo ponto do olho antigo
    S0 = bvo.ray_cast(Mw @ Vector((2 * ic[0] - 1, 2 * ic[1] - 1, 0)) + zw * 0.6, -zw, 1.5)[0]
    NOVOS[s] = dict(olho=olho, S=S0, Mw=Mw, zw=zw, Me=Me, esc=ART_R / r_med, fundo=im_fundo, aro=im_aro, dentro=im_dentro,
                    U0=U0, U1=U1)

# ------------------------------------------------------------------ ossos e restrições
bpy.context.view_layer.objects.active = rig
for o in bpy.context.selected_objects: o.select_set(False)
rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT'); eb = rig.data.edit_bones
for s, d in NOVOS.items():
    eixo = d['zw']; b = eb.new(f'olho.{s}'); b.head = d['S'] - eixo * ALAVANCA; b.tail = d['S']; b.parent = eb['head']; b.use_deform = False
    ux = Vector(d['Me'].col[2][:3]).normalized().cross(eixo).normalized()    # +X do controle: giro em torno do "para cima" do olho
    uy = Vector(d['Me'].col[0][:3]).normalized().cross(eixo).normalized()    # +Y do controle: giro em torno do eixo lateral
    t = eb.new(f'MCH_alvo_olho.{s}'); t.head = d['S'] + eixo * 1.0; t.tail = t.head + eixo * 0.08
    t.align_roll(ux.cross(eixo)); t.parent = eb['head']; t.use_deform = False
    d.update(ux=ux, uy=uy, D=1.0 + ALAVANCA,
             sx=1.0 if Vector(t.x_axis).dot(ux) >= 0 else -1.0, sz=1.0 if Vector(t.z_axis).dot(uy) >= 0 else -1.0,
             ex=Vector(t.x_axis), ez=Vector(t.z_axis))
bpy.ops.object.mode_set(mode='POSE')
k = math.tan(math.radians(GAZE_DEG))
for s, d in NOVOS.items():
    # o alvo anda tan(11°)·distância quando o controle vai a ±1; projetado nas direções do olhar antigo
    c = pb[f'MCH_alvo_olho.{s}'].constraints.new('TRANSFORM'); c.name = 'Olhar'; c.target = rig; c.subtarget = 'controle_olhar'
    c.target_space = 'LOCAL'; c.owner_space = 'LOCAL'; c.map_from = 'LOCATION'; c.map_to = 'LOCATION'; c.use_motion_extrapolate = True
    c.from_min_x, c.from_max_x, c.from_min_y, c.from_max_y = -1, 1, -1, 1
    c.map_to_x_from = 'X'; c.map_to_z_from = 'Y'; c.map_to_y_from = 'Z'
    L = k * d['D']
    c.to_min_x, c.to_max_x = -L * d['sx'], L * d['sx']; c.to_min_z, c.to_max_z = -L * d['sz'], L * d['sz']
    dt = pb[f'olho.{s}'].constraints.new('DAMPED_TRACK'); dt.name = 'Mira'; dt.target = rig; dt.subtarget = f'MCH_alvo_olho.{s}'; dt.track_axis = 'TRACK_Y'
bpy.ops.object.mode_set(mode='OBJECT')

# ------------------------------------------------------------------ decal e material
for s, d in NOVOS.items():
    Mw, S = d['Mw'], d['S']
    e = bpy.data.objects.new(f'Decal_Olho.{s}', None); e.empty_display_type = 'PLAIN_AXES'; e.empty_display_size = 0.15
    e.show_in_front = True; bpy.context.scene.collection.objects.link(e)
    e.matrix_world = Matrix.Translation(S) @ Matrix((tuple(Mw.col[0][:3]) + (0,), tuple(Mw.col[1][:3]) + (0,), tuple(Mw.col[2][:3]) + (0,), (0, 0, 0, 1))).transposed()
    mw = e.matrix_world.copy(); e.parent = rig; e.parent_type = 'BONE'; e.parent_bone = f'olho.{s}'
    bpy.context.view_layer.update(); e.matrix_world = mw
    d['decal'] = e

    m = skin_mat.copy(); m.name = f'KumoOlho.{s}'; nt = m.node_tree; N = nt.nodes; Lk = nt.links
    tpele = [n for n in N if n.type == 'TEX_IMAGE'][0]; em = [n for n in N if n.type == 'EMISSION'][0]
    def tex(im, x, y, uv=None, ext='EXTEND'):
        t = N.new('ShaderNodeTexImage'); t.image = im; t.extension = ext; t.location = (x, y)
        if uv:
            u = N.new('ShaderNodeUVMap'); u.uv_map = uv; u.location = (x - 220, y); Lk.new(u.outputs['UV'], t.inputs['Vector'])
        return t
    def mix(a_sock, b_sock, fac_sock, x, y):
        mx_ = N.new('ShaderNodeMix'); mx_.data_type = 'RGBA'; mx_.location = (x, y)
        Lk.new(a_sock, mx_.inputs['A']); Lk.new(b_sock, mx_.inputs['B']); Lk.new(fac_sock, mx_.inputs['Factor']); return mx_.outputs['Result']
    up = N.new('ShaderNodeUVMap'); up.uv_map = UV_PELE; up.location = (tpele.location.x - 220, tpele.location.y); Lk.new(up.outputs['UV'], tpele.inputs['Vector'])
    # o espaço da janela vai de U0 a U1 na textura: Mapping leva a UV 'Janela' para 0..1
    def janela_tex(im, y):
        t = N.new('ShaderNodeTexImage'); t.image = im; t.extension = 'EXTEND'; t.location = (-500, y)
        u = N.new('ShaderNodeUVMap'); u.uv_map = 'Janela'; u.location = (-900, y)
        mp = N.new('ShaderNodeMapping'); mp.vector_type = 'POINT'; mp.location = (-720, y)
        sc_ = 1.0 / (d['U1'] - d['U0']); mp.inputs['Scale'].default_value = (sc_, sc_, 1); mp.inputs['Location'].default_value = (-d['U0'] * sc_, -d['U0'] * sc_, 0)
        Lk.new(u.outputs['UV'], mp.inputs['Vector']); Lk.new(mp.outputs['Vector'], t.inputs['Vector']); return t
    tf = janela_tex(d['fundo'], -300); ta = janela_tex(d['aro'], -650); td = janela_tex(d['dentro'], -1000)
    # decal: coordenada do objeto (o Empty) → Mapping → imagem da íris e pupila
    tc = N.new('ShaderNodeTexCoord'); tc.object = d['decal']; tc.location = (-900, -1350)
    mp = N.new('ShaderNodeMapping'); mp.vector_type = 'POINT'; mp.location = (-720, -1350)
    sd = d['esc'] / 2000.0       # o Empty usa os eixos da janela: 1 unidade do Empty = meia unidade de janela
    mp.inputs['Scale'].default_value = (sd, sd, 1.0); mp.inputs['Location'].default_value = (ART_C[0] / 1000, ART_C[1] / 1000, 0)
    ti = N.new('ShaderNodeTexImage'); ti.image = im_decal; ti.extension = 'CLIP'; ti.location = (-500, -1350)
    Lk.new(tc.outputs['Object'], mp.inputs['Vector']); Lk.new(mp.outputs['Vector'], ti.inputs['Vector'])
    fac_i = N.new('ShaderNodeMath'); fac_i.operation = 'MULTIPLY'; fac_i.location = (-250, -1200)
    Lk.new(ti.outputs['Alpha'], fac_i.inputs[0]); Lk.new(td.outputs['Color'], fac_i.inputs[1])
    for l in list(em.inputs['Color'].links): nt.links.remove(l)
    c1 = mix(tpele.outputs['Color'], tf.outputs['Color'], tf.outputs['Alpha'], -100, 200)      # pele → branco / pele limpa
    c2 = mix(c1, ti.outputs['Color'], fac_i.outputs[0], 100, 0)                                  # → íris e pupila
    c3 = mix(c2, ta.outputs['Color'], ta.outputs['Alpha'], 300, -200)                            # → membrana e contorno
    Lk.new(c3, em.inputs['Color'])
    d['olho'].material_slots[0].material = m

# ------------------------------------------------------------------ sai o olho antigo (camadas e moldura)
for s in 'LR':
    for n in ('OlhoBase', 'Iris', 'Pupil', 'Catchlight', 'Moldura'):
        o = bpy.data.objects.get(f'KumoJogo_{n}.{s}')
        if o: bpy.data.objects.remove(o)

# ------------------------------------------------------------------ conferência do olhar contra o olho antigo
ANT = json.load(open(os.path.join(AQUI, 'olhar_antigo.json')))
REP['olhar'] = {}
for nome, (gx_, gy_) in (('dir', (1, 0)), ('esq', (-1, 0)), ('cima', (0, 1)), ('baixo', (0, -1)), ('diag', (1, 1))):
    pb['controle_olhar'].location = (0, 0, 0); bpy.context.view_layer.update(); p0 = {s: NOVOS[s]['decal'].matrix_world.translation.copy() for s in 'LR'}
    pb['controle_olhar'].location = (gx_, gy_, 0); bpy.context.view_layer.update()
    for s in 'LR':
        dn = NOVOS[s]['decal'].matrix_world.translation - p0[s]
        ang = math.degrees(pb[f'olho.{s}'].matrix.to_3x3().col[1].angle(NOVOS[s]['zw']))
        r_ = {'giro_graus': round(ang, 2), 'desloc_mm': round(dn.length * 1000, 1)}
        if nome in ANT[s]:
            da = Vector(ANT[s][nome]); r_.update(antigo_mm=round(da.length * 1000, 1), angulo_entre_sentidos_graus=round(math.degrees(dn.angle(da)), 1))
        REP['olhar'][f'{nome}_{s}'] = r_
pb['controle_olhar'].location = (0, 0, 0); bpy.context.view_layer.update()

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'kumo_v6_olhos_novos.blend'))
json.dump(REP, open(os.path.join(OUT, 'medicoes_olhos_novos.json'), 'w'), indent=1, ensure_ascii=False)
print('REP', json.dumps(REP, ensure_ascii=False))
