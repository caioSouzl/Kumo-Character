"""Kumo v6 · P1 iteração 6: refinamento SÓ VISUAL da mão (estilos I5 = mão da iteração 5, A = luva, B = dedos curtos).
Escolha com P1_MAO=I5|A|B. Pesos e razões janela/raio da iteração 5 mantidos.

Iteração 5 (a partir da 4): janelas de peso testadas articulação por articulação (razão janela/raio),
osso estrutural de metacarpo e testes de cotovelo dentro da amplitude necessária (ver ../../AMPLITUDES.md).

Iteração 4: braço esquerdo + mão reconstruídos a partir da REFERÊNCIA (caminho A).

  python p1_iter6.py <kumo_rigged.blend> <pasta p1-iter6>

- Proporções medidas em `referencia de modelo/kumo-referencia-01.png` (vista FRENTE, braço esquerdo do Kumo,
  à direita da imagem). Ver MEDIDAS-REFERENCIA.md.
- Do modelo atual usa SOMENTE: a articulação do ombro (cabeça de upper_arm.L) e a escala do tronco
  (largura do tronco e altura ombro-virilha), para converter pixels em metros.
- Lê o modelo oficial sem gravar nele; grava apenas p1-iter6/p1_iter6.blend e evidências.
- Regras v6: deformação só por ossos; até 4 influências, soma 1; nenhum osso corretivo nesta etapa.
"""
import bpy, bmesh, sys, os, json, math, time
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

SRC, OUT = sys.argv[-2], sys.argv[-1]
os.makedirs(os.path.join(OUT, 'renders'), exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=SRC)
REPO = os.path.dirname(os.path.abspath(SRC))
img = bpy.data.images['kumo_quad_diffuse']; img.filepath = os.path.join(REPO, 'textures', 'kumo_quad_diffuse.png'); img.reload()
sc = bpy.context.scene; rig0 = bpy.data.objects['Kumo_Rig']; body = bpy.data.objects['Kumo']; me = body.data
B = rig0.data.bones
REP = {}
EW = float(os.environ.get('P1_EW', '0.12')); WW = float(os.environ.get('P1_WW', '0.05')); RS = float(os.environ.get('P1_RS', '0.045'))
FR = float(os.environ.get('P1_FR', '0.35'))
KP = float(os.environ.get('P1_KP', '0.012')); KW = float(os.environ.get('P1_KW', '0.030')); KO = float(os.environ.get('P1_KO', '0.020'))
EWU = float(os.environ.get('P1_EWU', '0.12'))      # metade da janela do lado do úmero (nunca alcança o ombro)
JW = float(os.environ.get('P1_JW', '0.022'))
TPN = float(os.environ.get('P1_TPN', '1.0')); TP = float(os.environ.get('P1_TP', '0.012')); TW = float(os.environ.get('P1_TW', '0.025'))
TLA = float(os.environ.get('P1_TLA', '0.75')); TDN = float(os.environ.get('P1_TDN', '0.45')); TOUT = float(os.environ.get('P1_TOUT', '0.020'))
MAO = os.environ.get('P1_MAO', 'A')
# estilos da mão. I5 reproduz a iteração 5. A e B seguem a referência: luva orgânica, dedos curtos e arredondados,
# curvados para a palma, integrados à palma (fenda rasa), polegar curto colado ao lado medial.
ESTILOS = {
    'I5': dict(palm_w=0.88, palm_t=1.55, cols=(0.40, 0.28), fd=1.00, fl=1.00, spread=0.16, curl=0.45, rect=1.00, first_t=1.00,
               tip=(1.0, 0.96, 0.94, 0.94, 0.92, 0.80, 0.45), tl=0.85, td=0.95, ttip=(0.62, 1.0, 0.96, 0.96, 0.92, 0.78, 0.45),
               tla=0.75, tdn=0.45, tpn=0.50, tcurva=False),
    'A':  dict(palm_w=0.80, palm_t=1.80, cols=(0.34, 0.30), fd=0.90, fl=0.80, spread=0.03, curl=0.80, rect=0.70, first_t=1.35,
               tip=(1.0, 1.0, 0.98, 1.0, 1.03, 0.94, 0.64), tl=0.80, td=1.05, ttip=(0.62, 1.0, 1.04, 1.06, 1.04, 0.92, 0.62),
               tla=0.65, tdn=0.62, tpn=0.45, tface='medial', tout=0.026,
               razoes=dict(P1_RT=2.0), tp=0.006, mcg=(-0.25, 0.85)),   # ajustes locais exigidos pela nova geometria (ver RELATORIO)
    'B':  dict(palm_w=0.84, palm_t=1.70, cols=(0.38, 0.28), fd=0.92, fl=0.95, spread=0.05, curl=0.60, rect=0.85, first_t=1.20,
               tip=(1.0, 0.98, 0.96, 0.98, 1.02, 0.92, 0.58), tl=0.78, td=0.95, ttip=(0.62, 1.0, 1.0, 1.0, 1.02, 0.90, 0.58),
               tla=0.65, tdn=0.55, tpn=0.45, tface='palmar'),
}
EST = ESTILOS[MAO]
if 'P1_TP' not in os.environ: TP = EST.get('tp', TP)
CURL = float(os.environ.get('P1_CURL', str(EST['curl'])))
FAST = bool(os.environ.get('P1_FAST'))
REP['parametros'] = dict(janela_cotovelo_umero=EWU, janela_cotovelo_antebraco=EW, janela_punho=WW, passo_aneis_articulacao=RS,
                         afinamento_dobra_cotovelo=FR, pivo_dedo=KP, janela_dedo=KW, pivo_dedo_palma=KO, janela_junta_dedo=JW,
                         curvatura_dedos=CURL, polegar=dict(lat=TLA, baixo=TDN, saida=TOUT, pivo=TP, janela=TW, fecha_para_palma=TPN))


# ------------------------------------------------------------------ 0. medidas da referência (pixels, vista FRENTE) -> metros
# Tronco na referência: largura 52 px (lateral do tronco entre os braços), altura ombro→virilha 83 px.
# Tronco no modelo atual: largura 0,40 m (z 0,55–0,65), ombro z 0,74 → virilha z 0,279 = 0,46 m.
K_W = 0.40 / 52          # m/px para espessuras (relativas à largura do tronco)
K_H = 0.46 / 83          # m/px para comprimentos (relativos à altura do tronco)
REF = dict(braco_px=57, umero_px=29, antebraco_px=28, espessura_braco_px=16, espessura_antebraco_px=14,
           espessura_punho_px=12, mao_comprimento_px=32, mao_largura_px=28,
           palma_px=18, dedo_px=13, dedo_espessura_px=7)
L_UP = REF['umero_px'] * K_H; L_FO = REF['antebraco_px'] * K_H
R_UP = REF['espessura_braco_px'] * K_W / 2; R_FO = REF['espessura_antebraco_px'] * K_W / 2; R_WR = REF['espessura_punho_px'] * K_W / 2
HAND_L = REF['mao_comprimento_px'] * K_H; HAND_W = REF['mao_largura_px'] * K_W
PALM_L = REF['palma_px'] * K_H; FING_L = REF['dedo_px'] * K_H          # mão de luva: palma longa, dedos curtos e grossos
PALM_W = HAND_W * EST['palm_w']; PALM_T = R_FO * EST['palm_t']; FING_L *= EST['fl']
REP['estilo_mao'] = dict(nome=MAO, **{k: v for k, v in EST.items()})
REP['escala'] = dict(K_W_m_por_px=round(K_W, 5), K_H_m_por_px=round(K_H, 5))
REP['medidas_m'] = {k: round(v, 4) for k, v in dict(umero=L_UP, antebraco=L_FO, raio_braco=R_UP, raio_antebraco=R_FO, raio_punho=R_WR,
                                                    mao_comprimento=HAND_L, mao_largura=HAND_W, palma_comprimento=PALM_L,
                                                    dedo_comprimento=FING_L, palma_largura=PALM_W, palma_espessura=PALM_T).items()}

# ------------------------------------------------------------------ 1. região do braço atual (só leitura, para comparar)
vg = {g.index: g.name for g in body.vertex_groups}
ARM = {'upper_arm.L', 'forearm.L', 'hand.L'}
def dom(v):
    ws = [(vg[g.group], g.weight) for g in v.groups if vg[g.group] not in ('outline_cut', 'outline_shell')]
    return max(ws, key=lambda x: x[1])[0] if ws else None
arm_v = {v.index for v in me.vertices if dom(v) in ARM}
arm_f = [p for p in me.polygons if all(i in arm_v for i in p.vertices)]
REP['braco_atual'] = dict(vertices=len(arm_v), faces=len(arm_f), umero=round(B['upper_arm.L'].length, 3), antebraco=round(B['forearm.L'].length, 3))

# ------------------------------------------------------------------ 2. esqueleto-guia a partir da referência
S = B['upper_arm.L'].head_local.copy()                       # encaixe do ombro (único dado geométrico do braço atual)
# direção: na vista frente o braço desce 24° para fora (ombro (252,622) → punho (276,676)); no perfil, quase vertical
ang = math.radians(24)
dir_arm = Vector((math.sin(ang), 0.0, -math.cos(ang))).normalized()
fwd_world = Vector((0, -1, 0))                               # frente do Kumo = −Y
lat0 = dir_arm.cross(fwd_world).normalized()                 # lateral do braço (perpendicular ao plano frente)
if lat0.x < 0: lat0 = -lat0
# cotovelo levemente dobrado para a frente (8°): pose de repouso favorável à deformação
E = S + dir_arm * L_UP + Vector((0, 0.008, 0))
uD = (E - S).normalized()
fD = (Matrix.Rotation(math.radians(-8), 3, lat0) @ dir_arm).normalized()
W = E + fD * L_FO
down = fD
pn = (Vector((0, 1, 0)) - down * Vector((0, 1, 0)).dot(down)).normalized()      # palma voltada para trás...
pn = (Matrix.Rotation(math.radians(25), 3, down) @ pn).normalized()             # ...girada 25° para o corpo
if pn.x > 0.0: pn = (Matrix.Rotation(math.radians(-50), 3, down) @ pn).normalized()
lat = down.cross(pn).normalized()                            # eixo dos 3 dedos lado a lado
if lat.x < 0: lat = -lat                                     # lat aponta para fora (lado oposto ao corpo)
REP['guia'] = dict(ombro=[round(x, 3) for x in S], cotovelo=[round(x, 3) for x in E], punho=[round(x, 3) for x in W])

def smooth01(x):
    x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)

# parâmetro s ao longo do braço: 0 no ombro, sE no cotovelo, sW no punho
sE = L_UP; sW = L_UP + L_FO
def center_dir(s_):
    if s_ <= sE: c = S + uD * s_
    else: c = E + fD * (s_ - sE)
    w = smooth01((s_ - (sE - 0.05)) / 0.10)                  # direção do anel em leque contínuo no cotovelo
    d = (uD * (1 - w) + fD * w).normalized(); return c, d
def radius(s_):
    if s_ <= sE: return R_UP + (R_FO - R_UP) * smooth01((s_ - sE * 0.55) / (sE * 0.45)) * 0.6
    f = (s_ - sE) / L_FO
    r = R_UP + (R_FO - R_UP) * (0.6 + 0.4 * smooth01(f / 0.3))   # antebraço
    return r + (R_WR - r) * smooth01((f - 0.55) / 0.45)          # afina até o punho (transição definida)

# ------------------------------------------------------------------ 3. malha por modelagem em caixa
# Anel de 12 vértices. Ordem: T0..T5 (lado da palma, +pn) e B5..B0 (dorso, −pn). Na palma o anel vira um retângulo
# arredondado cujas colunas laterais definem 3 dedos separados por 2 faixas estreitas (sem dedos colados).
ANG = [165, 135, 105, 75, 45, 15, -15, -45, -75, -105, -135, -165]   # graus a partir de +lat... ver frame()
LAT_COLS = [-1.0, -EST['cols'][0], -EST['cols'][1], EST['cols'][1], EST['cols'][0], 1.0]                      # colunas laterais na ponta da palma
def ring_circle(c, d, r, ovr=None):
    a = (lat - d * lat.dot(d)).normalized(); b = d.cross(a).normalized()
    if b.dot(pn) < 0: b = -b
    pts = []
    for k, g in enumerate(ANG):
        g = math.radians(g); x = math.cos(g); y = math.sin(g)
        # cos(165°) < 0: T0 fica do lado −lat (medial, onde nasce o polegar), T5 do lado +lat
        ry = r * ((ovr[0] if y > 0 else ovr[1]) if ovr else 1.0)
        pts.append(c + a * (x * r) + b * (y * ry))
    return pts, a, b
def ring_rect(c, d, half_w, half_t, blend):
    """blend 0 = elipse, 1 = retângulo arredondado com as colunas dos dedos"""
    a = (lat - d * lat.dot(d)).normalized(); b = d.cross(a).normalized()
    if b.dot(pn) < 0: b = -b
    pts = []
    for k, g in enumerate(ANG):
        g = math.radians(g); ex, ey = math.cos(g), math.sin(g)
        col = LAT_COLS[k] if k < 6 else LAT_COLS[11 - k]
        rx, ry = col * 0.97, (0.88 if ey > 0 else -0.88)
        by = blend * EST['rect']                              # perfil da palma mais arredondado (rect < 1)
        x = ex * (1 - blend) + rx * blend; y = ey * (1 - by) + ry * by
        pts.append(c + a * (x * half_w) + b * (y * half_t))
    return pts, a, b

bm = bmesh.new()
rings, ring_s = [], []
def add_ring(pts, s_):
    rings.append([bm.verts.new(p) for p in pts]); ring_s.append(s_)
# braço: anéis mais densos no cotovelo (5 anéis em ±0,03) e no punho (4 anéis)
s_list = [-0.035, 0.0, 0.035, 0.07, 0.10]
s_list += [sE + RS * k for k in (-2, -1, 0, 1, 2)]
s_list += [sE + (sW - sE) * f for f in (0.45, 0.62)]
s_list += [sW - RS * 1.6, sW - RS * 0.8, sW]
s_list = sorted(x for x in s_list if x < sW + 1e-6)
for s_ in s_list:
    c, d = center_dir(s_); r = radius(max(s_, 0.0))
    gss = math.exp(-((s_ - sE) / 0.03) ** 2)
    ovr = (1.0 + 0.10 * gss, 1.0 - FR * gss)                  # olécrano atrás (+10%); dobra da frente afinada (−FR)
    pts, a, b = ring_circle(c, d, r, ovr); add_ring(pts, s_)
N_ARM = len(rings)
# palma: do punho (elipse) até a base dos dedos (retângulo com colunas)
PALM_A = [0.014, 0.032, PALM_L * 0.80, PALM_L]
for k, a_ in enumerate(PALM_A):
    f = a_ / PALM_L
    hw = R_WR + (PALM_W / 2 - R_WR) * smooth01(f / 0.6)
    ht = R_WR * 0.95 + (PALM_T / 2 - R_WR * 0.95) * smooth01(f / 0.6)
    pts, _, _ = ring_rect(W + down * a_, down, hw, ht, smooth01((f - 0.2) / 0.6)); add_ring(pts, sW + a_)
for r0, r1 in zip(rings, rings[1:]):
    for j in range(12): bm.faces.new([r0[j], r0[(j + 1) % 12], r1[(j + 1) % 12], r1[j]])
r0 = rings[0]                                                # tampa do ombro (fica dentro do tronco)
for q in ((0, 1, 10, 11), (1, 2, 9, 10), (2, 3, 8, 9), (3, 4, 7, 8), (4, 5, 6, 7)): bm.faces.new([r0[i] for i in q])
end = rings[-1]
# ponta da palma: colunas 0-1 (dedo 1, medial), 1-2 faixa, 2-3 dedo 2, 3-4 faixa, 4-5 dedo 3 (lateral)
def colquad(i): return [end[i], end[i + 1], end[10 - i], end[11 - i]]
CAPS = [colquad(0), colquad(2), colquad(4)]
for i in (1, 3): bm.faces.new(colquad(i))                    # faixas entre os dedos ficam fechadas (palma)

def tube(loop, path, widths, axA, axB):
    """extruda um laço de 4 vértices ao longo de path; widths=(wa, wb); fecha a ponta com um quad"""
    c0 = sum((v.co for v in loop), Vector()) / 4
    sig = [((v.co - c0).dot(axA) > 0, (v.co - c0).dot(axB) > 0) for v in loop]
    prev = list(loop); out = []
    for i, (c, (wa, wb)) in enumerate(zip(path, widths)):
        d = (path[i] - (path[i - 1] if i else c0)).normalized()
        A = (axA - d * axA.dot(d)).normalized(); Bv = (axB - d * axB.dot(d) - A * axB.dot(A)).normalized()
        cur = [bm.verts.new(c + A * (wa / 2 if sa else -wa / 2) + Bv * (wb / 2 if sb else -wb / 2)) for sa, sb in sig]
        for j in range(4): bm.faces.new([prev[j], prev[(j + 1) % 4], cur[(j + 1) % 4], cur[j]])
        prev = cur; out.append(cur)
    bm.faces.new(prev)
    return out
FD = REF['dedo_espessura_px'] * K_W * EST['fd']                # diâmetro do dedo medido na referência
FING = []
for k, cap in enumerate(CAPS):
    c0 = sum((v.co for v in cap), Vector()) / 4
    spread = lat * (k - 1) * EST['spread']                      # leque (quase nenhum na luva)
    D = [f * FING_L for f in (0.12, 0.32, 0.44, 0.56, 0.68, 0.86, 1.0)]
    path = [c0 + (down + spread).normalized() * dd + pn * CURL * dd * dd / FING_L for dd in D]      # dedos levemente curvados para a palma
    tk = [EST['first_t'], 1 + (EST['first_t'] - 1) * 0.4, 1, 1, 1, 1, 1]   # base mais alta: o dedo nasce da palma, sem "pescoço"
    Wd = [(FD * t_, FD * t_ * k_) for t_, k_ in zip(EST['tip'], tk)]
    tube(cap, path, Wd, lat, pn)
    FING.append(dict(base=c0, junta=path[3], ponta=path[-1]))
# polegar: face medial da palma entre o 1º e o 2º anel da palma; aponta para dentro, para baixo e para o lado da palma
pa, pb = rings[N_ARM + 1], rings[N_ARM + 2]          # face mais alta da palma (anéis 2 e 3)
TFACE = os.environ.get('P1_TFACE', EST.get('tface', 'medial'))
if TFACE == 'palmar':            # polegar nasce da face da palma junto à borda medial (eminência tenar), não da lateral
    tq = {pa[0], pa[1], pb[0], pb[1]}; tloop = [pa[0], pb[0], pb[1], pa[1]]; T_AXB = lat
else:
    tq = {pa[0], pa[11], pb[0], pb[11]}; tloop = [pa[0], pb[0], pb[11], pa[11]]; T_AXB = pn
tf = [f for f in bm.faces if set(f.verts) == tq][0]; bm.faces.remove(tf)
c0 = sum((v.co for v in tloop), Vector()) / 4
dt = (-lat * EST['tla'] + down * EST['tdn'] + pn * EST['tpn']).normalized()   # polegar: menos para o lado, mais à frente
TL = FING_L / EST['fl'] * EST['tl']; TD = FD / EST['fd'] * EST['td']
D = [f * TL for f in (0.14, 0.34, 0.47, 0.60, 0.74, 0.88, 1.0)]
nrm = -(lat - down * lat.dot(down)).normalized()
if TFACE == 'palmar':
    fn = (tloop[1].co - tloop[0].co).cross(tloop[3].co - tloop[0].co).normalized()
    nrm = fn if fn.dot(pn) > 0 else -fn
TOUT = EST.get('tout', TOUT)
if EST.get('tcurva', True):
    tpath = []; pos_ = c0.copy(); prev_ = 0.0
    for dd in D:                               # curva suave: sai na normal da face e gira até dt (sem dobra brusca)
        w_ = smooth01(dd / (TOUT * 2.5)); dir_ = (nrm * (1 - w_) + dt * w_).normalized()
        pos_ = pos_ + dir_ * (dd - prev_); prev_ = dd; tpath.append(pos_.copy())
else:                                          # caminho da iteração 5 (reto para fora, depois dt), para reproduzi-la exatamente
    tpath = [c0 + nrm * min(dd, TOUT) + dt * max(dd - TOUT, 0.0) for dd in D]      # sai primeiro para fora da palma, depois dobra
tube(tloop, tpath, [(TD * t_, TD * t_) for t_ in EST['ttip']], down, T_AXB)
THUMB = dict(base=c0, junta=tpath[3], ponta=tpath[-1], dir=dt, nrm=nrm)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
nm = bpy.data.meshes.new('P1i6_Braco_E'); bm.to_mesh(nm); bm.free()
arm = bpy.data.objects.new('P1i6_Braco_E', nm); sc.collection.objects.link(arm)

# ------------------------------------------------------------------ 3b. janelas de peso por razão janela/raio (decisão: testar cada articulação)
R_E = radius(sE); R_K = FD / 2; R_T = TD / 2
# razões escolhidas pela varredura articulação por articulação + teste combinado (ver RELATORIO.md); o ambiente pode sobrescrever
RAZAO_PADRAO = dict(P1_RE=2.1, P1_RW=2.5, P1_RK=1.5, P1_RJ=1.6, P1_RT=1.0)
RAZAO_PADRAO.update(EST.get('razoes', {}))
def env_ratio(k):
    v = os.environ.get(k); return float(v) if v else RAZAO_PADRAO[k]
if env_ratio('P1_RE') is not None: EW = EWU = min(env_ratio('P1_RE') * R_E, 0.8 * min(L_UP, L_FO))
if env_ratio('P1_RW') is not None: WW = env_ratio('P1_RW') * R_WR
if env_ratio('P1_RK') is not None: KW = env_ratio('P1_RK') * R_K
if env_ratio('P1_RJ') is not None: JW = env_ratio('P1_RJ') * R_K
if env_ratio('P1_RT') is not None: TW = env_ratio('P1_RT') * R_T
MC = float(os.environ.get('P1_MC', '1'))
MCG0 = float(os.environ.get('P1_MCG0', EST.get('mcg', (0.05, 0.75))[0])); MCG1 = float(os.environ.get('P1_MCG1', EST.get('mcg', (0.05, 0.75))[1]))                     # 1 = com osso de metacarpo; 0 = sem (para comparar)
REP['raios_articulacoes'] = dict(cotovelo=round(R_E, 4), punho=round(R_WR, 4), dedo=round(R_K, 4), polegar=round(R_T, 4))
REP['razao_janela_raio'] = dict(cotovelo=round(EW / R_E, 2), punho=round(WW / R_WR, 2), no_do_dedo=round(KW / R_K, 2),
                                junta_do_dedo=round(JW / R_K, 2), polegar=round(TW / R_T, 2))
REP['parametros'].update(janela_cotovelo_umero=EWU, janela_cotovelo_antebraco=EW, janela_punho=WW, janela_dedo=KW, janela_junta_dedo=JW,
                         metacarpo=bool(MC), gradiente_metacarpo=(MCG0, MCG1), pivo_polegar=TP)

# ------------------------------------------------------------------ 4. rig e pesos procedurais (na malha base; Subsurf interpola)
ad = bpy.data.armatures.new('P1i6_Rig'); rigo = bpy.data.objects.new('P1i6_Rig', ad); sc.collection.objects.link(rigo)
bpy.context.view_layer.objects.active = rigo
for o in bpy.context.selected_objects: o.select_set(False)
rigo.select_set(True); bpy.ops.object.mode_set(mode='EDIT')
EB = ad.edit_bones
def eb(name, h, t, parent=None):
    b = EB.new(name); b.head = h; b.tail = t
    if parent: b.parent = EB[parent]; b.use_connect = (EB[parent].tail - h).length < 1e-5
    b.align_roll(pn); return b
eb('DEF-braco.L', S, E); eb('DEF-antebraco.L', E, W, 'DEF-braco.L'); eb('DEF-mao.L', W, W + down * (PALM_L - KP), 'DEF-antebraco.L')
META_H = W + down * 0.012 + lat * (PALM_W * 0.10)
if MC: eb('DEF-metacarpo.L', META_H, FING[2]['base'] - down * KP + pn * KO, 'DEF-mao.L')   # estrutural: curva a palma lateral
for k, f in enumerate(FING):
    par = 'DEF-metacarpo.L' if (MC and k == 2) else 'DEF-mao.L'
    eb(f'DEF-dedo{k+1}_1.L', f['base'] - down * KP + pn * KO, f['junta'], par)     # pivô dentro do nó do dedo
    eb(f'DEF-dedo{k+1}_2.L', f['junta'], f['ponta'], f'DEF-dedo{k+1}_1.L')
eb('DEF-polegar_1.L', THUMB['base'] - THUMB['nrm'] * TP, THUMB['junta'], 'DEF-mao.L')     # pivô dentro da palma
eb('DEF-polegar_2.L', THUMB['junta'], THUMB['ponta'], 'DEF-polegar_1.L')
bpy.ops.object.mode_set(mode='OBJECT')
arm.parent = rigo
amod = arm.modifiers.new('Armature', 'ARMATURE'); amod.object = rigo
G = {b.name: arm.vertex_groups.new(name=b.name) for b in ad.bones}
def ss(x, a, b): return smooth01((x - a) / (b - a))
ring_of = {i: i // 12 for i in range(len(rings) * 12)}     # os anéis foram os primeiros vértices criados
for v in nm.vertices:
    p = v.co
    if v.index in ring_of:                                   # anel do braço/palma: parâmetro exato do anel
        s_ = ring_s[ring_of[v.index]]
        e = ss(s_, sE - EWU, sE + EW); h = ss(s_, sW - WW, sW + WW * 0.5)
        w = {'DEF-braco.L': 1 - e, 'DEF-antebraco.L': e * (1 - h), 'DEF-mao.L': e * h}
        if ring_of[v.index] == len(rings) - 1:              # anel da base dos dedos: já começa a seguir o dedo da sua coluna
            j = v.index % 12; col = j if j < 6 else 11 - j; kf = col // 2 + 1
            hh = 1 - ss(0.0, -KW, KW * 1.4); w = {'DEF-mao.L': hh, f'DEF-dedo{kf}_1.L': 1 - hh}
    else:                                                    # vértice de dedo ou polegar
        ut = (p - THUMB['base']).dot(THUMB['dir'])
        dth = min(((p - (THUMB['base'] + THUMB['dir'] * x)).length for x in [ut]))
        cand = []
        for k, f in enumerate(FING):
            ax = (f['ponta'] - f['base']).normalized(); u = (p - f['base']).dot(ax)
            cand.append(((p - (f['base'] + ax * u)).length, k, u, (f['junta'] - f['base']).dot(ax)))
        dmin, k, u, jk = min(cand)
        if dth < dmin and ut > 0:
            jt = (THUMB['junta'] - THUMB['base']).dot(THUMB['dir'])
            hh = 1 - ss(ut, -TW, TW * 1.4); x = ss(ut, jt - JW, jt + JW)
            w = {'DEF-mao.L': hh, 'DEF-polegar_1.L': (1 - hh) * (1 - x), 'DEF-polegar_2.L': (1 - hh) * x}
        else:
            hh = 1 - ss(u, -KW, KW * 1.4); x = ss(u, jk - JW, jk + JW)
            w = {'DEF-mao.L': hh, f'DEF-dedo{k+1}_1.L': (1 - hh) * (1 - x), f'DEF-dedo{k+1}_2.L': (1 - hh) * x}
    if MC and 'DEF-mao.L' in w:                              # metade lateral da palma passa ao metacarpo (gradiente suave)
        latc = (p - W).dot(lat) / (PALM_W / 2); a_ = (p - W).dot(down)
        m = ss(latc, MCG0, MCG1) * ss(a_, 0.010, 0.050)          # gradiente do metacarpo (mais largo = vinco mais suave)
        w['DEF-metacarpo.L'] = w['DEF-mao.L'] * m; w['DEF-mao.L'] *= (1 - m)
    for n_, x_ in w.items():
        if x_ > 1e-4: G[n_].add([v.index], x_, 'REPLACE')
REP['malha_base'] = dict(vertices=len(nm.vertices), faces=len(nm.polygons))
# Subsurf 1 aplicado (interpola os pesos), depois limite de 4 influências e normalização (regra v6)
sub = arm.modifiers.new('Sub', 'SUBSURF'); sub.levels = 1
bpy.ops.object.mode_set(mode='OBJECT')
for o in bpy.context.selected_objects: o.select_set(False)
arm.select_set(True); bpy.context.view_layer.objects.active = arm
bpy.ops.object.modifier_move_to_index(modifier='Sub', index=0)
bpy.ops.object.modifier_apply(modifier='Sub')
bpy.ops.object.vertex_group_limit_total(limit=4)
bpy.ops.object.vertex_group_normalize_all(lock_active=False)
nm = arm.data
for p in nm.polygons: p.use_smooth = False
def weight_stats(o):
    infl = []; sums = []
    for v in o.data.vertices:
        ws = [g.weight for g in v.groups if g.weight > 1e-4]; infl.append(len(ws)); sums.append(sum(ws))
    return dict(max_influencias=max(infl), sem_peso=sum(1 for x in infl if x == 0), soma_fora_de_1=sum(1 for s in sums if abs(s - 1) > 0.01))
REP['malha_nova'] = dict(vertices=len(nm.vertices), faces=len(nm.polygons), quads=sum(1 for p in nm.polygons if len(p.vertices) == 4),
                        tris=sum(1 for p in nm.polygons if len(p.vertices) == 3), ngons=sum(1 for p in nm.polygons if len(p.vertices) > 4))
REP['pesos_novos'] = weight_stats(arm)
REP['ossos_novos'] = [b.name for b in ad.bones]
mat = bpy.data.materials.new('P1i6_Verde'); mat.use_nodes = True; nt = mat.node_tree
for n in list(nt.nodes):
    if n.type != 'OUTPUT_MATERIAL': nt.nodes.remove(n)
bsdf = nt.nodes.new('ShaderNodeBsdfDiffuse'); bsdf.inputs['Color'].default_value = (0x4C / 255) ** 2.2, (0xAF / 255) ** 2.2, (0x6B / 255) ** 2.2, 1
nt.links.new(bsdf.outputs[0], nt.nodes['Material Output'].inputs['Surface'])
arm.data.materials.append(mat)

# ------------------------------------------------------------------ 5. testes (mesmo método da auditoria e das iterações 1–3)
def tri_data(obj, region=None, region_v=None):
    dg = bpy.context.evaluated_depsgraph_get(); ev = obj.evaluated_get(dg); m = ev.to_mesh(); m.calc_loop_triangles()
    V = [ev.matrix_world @ v.co for v in m.vertices]
    T = [tuple(t.vertices) for t in m.loop_triangles if region is None or t.polygon_index in region]
    E_ = [(e.vertices[0], e.vertices[1]) for e in m.edges if region is None or (e.vertices[0] in region_v and e.vertices[1] in region_v)]
    ev.to_mesh_clear(); return V, T, E_
def self_pairs(V, T):
    b = BVHTree.FromPolygons(V, T); out = set()
    for a_, b_ in b.overlap(b):
        if a_ < b_ and not (set(T[a_]) & set(T[b_])): out.add((a_, b_))
    return out
def depth(V, T, pair):
    """profundidade da travessia: o quanto um triângulo atravessa o plano do outro, pelo lado menor (m)"""
    out = []
    for x, y in (pair, pair[::-1]):
        a0, a1, a2 = (V[i] for i in T[x]); n = (a1 - a0).cross(a2 - a0)
        if n.length < 1e-12: return 0.0
        n.normalize(); ds = [n.dot(V[i] - a0) for i in T[y]]
        out.append(min(max(0.0, max(ds)), max(0.0, -min(ds))))
    return min(out)
TOL = 0.0005     # abaixo de 0,5 mm: contato rasante / ruído numérico (possível falso positivo)
def classify(V, T, pairs):
    pairs = list(pairs); ds = [depth(V, T, p) for p in pairs]
    tri = {t for p, d in zip(pairs, ds) if d >= TOL for t in p}
    area = sum(((V[T[t][1]] - V[T[t][0]]).cross(V[T[t][2]] - V[T[t][0]])).length / 2 for t in tri)
    return dict(reais=sum(1 for d in ds if d >= TOL), rasantes=sum(1 for d in ds if d < TOL),
                prof_max_mm=round(max(ds) * 1000, 2) if ds else 0.0, area_envolvida_cm2=round(area * 1e4, 2))
region = {p.index for p in arm_f}; region_v = set(arm_v)
OUTL = [m for m in body.modifiers if m.type in ('SOLIDIFY', 'VERTEX_WEIGHT_MIX', 'MASK')]
for m in OUTL: m.show_viewport = False
bpy.context.view_layer.update()
V0o, T0o, E0o = tri_data(body, region, region_v); rest_o = self_pairs(V0o, T0o); L0o = [(V0o[a] - V0o[b]).length for a, b in E0o]
V0n, T0n, E0n = tri_data(arm); rest_n = self_pairs(V0n, T0n); L0n = [(V0n[a] - V0n[b]).length for a, b in E0n]
if FAST and rest_n:
    import collections
    gi_ = {g.index: g.name for g in arm.vertex_groups}
    def lab0(t):
        vv = arm.data.vertices[T0n[t][0]]; return max(((gi_[g.group][4:], g.weight) for g in vv.groups), key=lambda x: x[1])[0]
    print('FAST rest_labels', collections.Counter(tuple(sorted((lab0(a_), lab0(b_)))) for a_, b_ in rest_n))
REP['autointersecao_em_repouso'] = dict(atual_regiao_braco=dict(pares=len(rest_o), **classify(V0o, T0o, rest_o)),
                                        novo=dict(pares=len(rest_n), **classify(V0n, T0n, rest_n)))
def reset(r):
    for pb in r.pose.bones:
        pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()
def rot_world(r, name, axis, deg):
    pb = r.pose.bones[name]; bpy.context.view_layer.update(); M = pb.matrix.copy(); h = M.to_translation()
    pb.matrix = Matrix.Translation(h) @ Matrix.Rotation(math.radians(deg), 4, Vector(axis).normalized()) @ Matrix.Translation(-h) @ M
    bpy.context.view_layer.update()
def bone_dir(r, name):
    pb = r.pose.bones[name]; return (pb.tail - pb.head).normalized()
def bend_axis(r, name):     # dobra para a frente (−Y), como na auditoria
    return bone_dir(r, name).cross(Vector((0, -1, 0))).normalized()
def side_axis(r, name):     # desvio lateral (punho para fora/dentro)
    d = bone_dir(r, name); return d.cross(bend_axis(r, name)).normalized()
def curl_axis(r, name):     # fecha o dedo em direção à palma; o polegar fecha atravessando a palma (oposição)
    tgt_ = (pn * TPN + lat * (1 - TPN)).normalized() if 'polegar' in name else pn
    return bone_dir(r, name).cross(tgt_).normalized()
MAP_OLD = {'braco': 'upper_arm.L', 'antebraco': 'forearm.L', 'mao': 'hand.L'}
MAP_NEW = {'braco': 'DEF-braco.L', 'antebraco': 'DEF-antebraco.L', 'mao': 'DEF-mao.L'}
POSES = {
    'braco_horizontal': [('braco', (0, 1, 0), -45)],
    'braco_para_frente_90': [('braco', (1, 0, 0), -90)],
    'braco_para_tras_40': [('braco', (1, 0, 0), 40)],
    'braco_torcao_45': [('braco', 'TWIST', 45)],
    'cotovelo_45': [('antebraco', 'BEND', 45)],
    'cotovelo_90': [('antebraco', 'BEND', 90)], 'cotovelo_100': [('antebraco', 'BEND', 100)],
    'cotovelo_115': [('antebraco', 'BEND', 115)], 'cotovelo_130': [('antebraco', 'BEND', 130)],
    'antebraco_torcao_60': [('antebraco', 'TWIST', 60)],
    'punho_45': [('mao', 'BEND', 45)], 'punho_menos45': [('mao', 'BEND', -45)],
    'punho_lateral_30': [('mao', 'SIDE', 30)], 'punho_lateral_menos30': [('mao', 'SIDE', -30)],
    'cotovelo_90_punho_45': [('antebraco', 'BEND', 90), ('mao', 'BEND', 45)],
    'mao_fechada': 'FIST', 'mao_aberta_abduzida': 'SPREAD', 'palma_curvada_20': 'CUP',
    'dedos_flexao_45': 'CURL45', 'polegar_movimento': 'THUMB', 'dedos_alternados': 'ALT',
}
def apply_pose(r, steps, MAP, tag):
    if steps == 'FIST':
        if tag == 'atual': return False
        if 'DEF-metacarpo.L' in r.pose.bones: rot_world(r, 'DEF-metacarpo.L', curl_axis(r, 'DEF-metacarpo.L'), 20)
        for nm_ in [b.name for b in rigo.data.bones if 'dedo' in b.name or 'polegar' in b.name]:
            rot_world(r, nm_, curl_axis(r, nm_), 70 if 'polegar' not in nm_ else 35)
        return True
    if steps in ('CURL45', 'THUMB', 'ALT'):
        if tag == 'atual': return False
        if steps == 'CURL45':
            for nm_ in [b.name for b in rigo.data.bones if 'dedo' in b.name]: rot_world(r, nm_, curl_axis(r, nm_), 45)
        elif steps == 'THUMB':
            rot_world(r, 'DEF-polegar_1.L', pn, 20); rot_world(r, 'DEF-polegar_1.L', curl_axis(r, 'DEF-polegar_1.L'), 35)
            rot_world(r, 'DEF-polegar_2.L', curl_axis(r, 'DEF-polegar_2.L'), 45)
        else:
            for k_, a_ in ((1, 70), (2, 30), (3, 0)):
                for j_ in (1, 2): rot_world(r, f'DEF-dedo{k_}_{j_}.L', curl_axis(r, f'DEF-dedo{k_}_{j_}.L'), a_)
            rot_world(r, 'DEF-polegar_1.L', curl_axis(r, 'DEF-polegar_1.L'), 15)
        return True
    if steps == 'CUP':
        if tag == 'atual' or 'DEF-metacarpo.L' not in r.pose.bones: return False
        rot_world(r, 'DEF-metacarpo.L', curl_axis(r, 'DEF-metacarpo.L'), 20); return True
    if steps == 'SPREAD':
        if tag == 'atual': return False
        # giro positivo em torno de pn leva a ponta para −lat (lado medial): dedo 1 (medial) +, dedo 3 (lateral) −, polegar + (afasta)
        for k, a in ((1, 15), (3, -15)): rot_world(r, f'DEF-dedo{k}_1.L', pn, a)
        rot_world(r, 'DEF-polegar_1.L', pn, 20)
        for nm_ in [b.name for b in rigo.data.bones if b.name.endswith('_1.L') or b.name.endswith('_2.L')]:
            rot_world(r, nm_, curl_axis(r, nm_), -10)                # abre: estende levemente
        return True
    for b, ax, deg in steps:
        bn = MAP[b]
        if ax == 'BEND': axis = bend_axis(r, bn)
        elif ax == 'SIDE': axis = side_axis(r, bn)
        elif ax == 'TWIST': axis = bone_dir(r, bn)
        else: axis = ax
        rot_world(r, bn, axis, deg)
    return True
res = {}
for pname, steps in POSES.items():
    row = {}
    for tag, r, obj, V0, T0, E0, L0, rest, MAP, reg in (('atual', rig0, body, V0o, T0o, E0o, L0o, rest_o, MAP_OLD, (region, region_v)),
                                                        ('novo', rigo, arm, V0n, T0n, E0n, L0n, rest_n, MAP_NEW, (None, None))):
        reset(r)
        if not apply_pose(r, steps, MAP, tag):
            row[tag] = dict(nao_suportado='o rig atual não tem ossos de dedo'); continue
        V, T, E_ = tri_data(obj, *reg)
        allp = self_pairs(V, T); new = allp - rest
        if FAST and tag == 'novo' and pname == 'mao_fechada' and new:
            import collections
            gi2 = {g.index: g.name for g in arm.vertex_groups}
            def lab2(t):
                vv = arm.data.vertices[T[t][0]]; return max(((gi2[g.group][4:], g.weight) for g in vv.groups), key=lambda x: x[1])[0]
            print('FAST fist_labels', collections.Counter(tuple(sorted((lab2(a_), lab2(b_)))) for a_, b_ in new if depth(V, T, (a_, b_)) >= TOL))
        ratio = sorted((V[a] - V[b]).length / l0 for (a, b), l0 in zip(E_, L0) if l0 > 1e-7)
        row[tag] = dict(pares_novos=len(new), **classify(V, T, new), pares_total=len(allp),
                        compressao_min=round(ratio[0], 3), compressao_p01=round(ratio[int(len(ratio) * 0.01)], 3),
                        esticamento_max=round(ratio[-1], 3))
    res[pname] = row
    reset(rig0); reset(rigo)
# fechamento máximo da mão sem travessia real (mesmo giro da mão fechada, ângulo crescente)
lim = []
for ang_ in range(30, 75, 5):
    reset(rigo)
    if 'DEF-metacarpo.L' in rigo.pose.bones: rot_world(rigo, 'DEF-metacarpo.L', curl_axis(rigo, 'DEF-metacarpo.L'), ang_ * 20 / 70)
    for nm_ in [b.name for b in rigo.data.bones if 'dedo' in b.name or 'polegar' in b.name]:
        rot_world(rigo, nm_, curl_axis(rigo, nm_), ang_ if 'polegar' not in nm_ else ang_ / 2)
    V, T, E_ = tri_data(arm); new = self_pairs(V, T) - rest_n; c_ = classify(V, T, new)
    lim.append(dict(angulo=ang_, pares=len(new), **c_))
    if FAST and ang_ == 30:
        import collections
        gi = {g.index: g.name for g in arm.vertex_groups}
        def lab_(t):
            vv = arm.data.vertices[T[t][0]]; return max(((gi[g.group][4:], g.weight) for g in vv.groups), key=lambda x: x[1])[0]
        print('FAST dbg30', collections.Counter(tuple(sorted((lab_(a_), lab_(b_)))) for a_, b_ in new))
        down_ = down
        for a_, b_ in list(new)[:6]:
            ca = sum((V[i] for i in T[a_]), Vector()) / 3; cb = sum((V[i] for i in T[b_]), Vector()) / 3
            print('FAST pos', [round((ca - W).dot(x), 3) for x in (down_, lat, pn)], [round((cb - W).dot(x), 3) for x in (down_, lat, pn)])
reset(rigo)
REP['mao_fechamento_por_angulo'] = lim
REP['testes'] = res
def proporcoes():
    V, T, E_ = tri_data(arm)
    mao = [p for p in V if (p - W).dot(down) > 0.0]
    ante = [p for p in V if abs((p - (E + fD * L_FO * 0.5)).dot(fD)) < 0.006]
    dedos = [p for p in mao if (p - W).dot(down) > PALM_L]
    larg_mao = max(p.x for p in mao) - min(p.x for p in mao); larg_ante = max(p.x for p in ante) - min(p.x for p in ante)
    comp_mao = W.z - min(p.z for p in mao)
    comp_dedo = (W + down * PALM_L).z - min(p.z for p in dedos)
    return dict(mao_largura_sobre_antebraco=round(larg_mao / larg_ante, 2), mao_comprimento_sobre_largura=round(comp_mao / larg_mao, 2),
                dedo_comprimento_sobre_espessura=round(comp_dedo / FD, 2), polegar_sobre_dedo=round(EST['tl'] / EST['fl'], 2),
                palma_sobre_dedo=round(PALM_L / max(comp_dedo, 1e-6), 2))
REP['proporcoes_vista_frente'] = proporcoes()
REP['proporcoes_referencia'] = dict(mao_largura_sobre_antebraco=round(28 / 14, 2), mao_comprimento_sobre_largura=round(32 / 28, 2),
                                    dedo_comprimento_sobre_espessura=round(13 / 7, 2), polegar_sobre_dedo='~0,7 (estimado, polegar parcialmente oculto)',
                                    palma_sobre_dedo=round(18 / 13, 2))
REP['testes_metodo'] = ('giro do osso em torno de eixo do mundo pela cabeça do osso (mesmo método da auditoria); no modelo atual só os '
                        'triângulos da região do braço (osso dominante upper_arm/forearm/hand .L). "reais" = travessia >= 0,5 mm; '
                        '"rasantes" = < 0,5 mm (contato ou ruído numérico, possível falso positivo)')
REP['testes_limitacoes'] = ('o ombro e a junção com o tronco ficam fora do P1, então poses só do úmero (horizontal, frente, trás, torção) '
                            'movem o braço novo como peça rígida; mão fechada/aberta só existem no rig novo; poses estáticas')
# desempenho: mesma medida das iterações anteriores (média de 60 avaliações da cena)
def perf(r, bone):
    reset(r); pb = r.pose.bones[bone]; pb.rotation_mode = 'XYZ'; t0 = time.perf_counter(); N = 60
    for i in range(N):
        pb.rotation_euler = (math.radians(i), 0, 0); bpy.context.view_layer.update(); bpy.context.evaluated_depsgraph_get()
    dt_ = (time.perf_counter() - t0) / N * 1000; pb.rotation_euler = (0, 0, 0); pb.rotation_mode = 'QUATERNION'; reset(r); return round(dt_, 3)
body.hide_viewport = True; REP['desempenho_ms_p1_sozinho'] = perf(rigo, 'DEF-antebraco.L'); body.hide_viewport = False
arm.hide_viewport = True; REP['desempenho_ms_modelo_atual_inteiro'] = perf(rig0, 'forearm.L'); arm.hide_viewport = False
for m in OUTL: m.show_viewport = True
bpy.context.view_layer.update()

PREVIEW = bool(os.environ.get('P1_PREVIEW'))
if FAST:
    print('FAST', json.dumps({k: REP[k] for k in ('parametros', 'autointersecao_em_repouso')}))
    for p_, r_ in REP['testes'].items(): print('FAST', p_, {t: (x.get('pares_novos'), x.get('reais'), x.get('area_envolvida_cm2'), x.get('prof_max_mm'), x.get('compressao_min')) for t, x in r_.items() if 'pares_novos' in x})
    print('FAST prop', REP['proporcoes_vista_frente'])
    print('FAST razoes', REP['razao_janela_raio'], REP['raios_articulacoes'])
    print('FAST lim', [(x['angulo'], x['reais'], x['prof_max_mm']) for x in REP['mao_fechamento_por_angulo']])
    if not PREVIEW: raise SystemExit
# ------------------------------------------------------------------ 6. renders: peça isolada e encaixe no corpo (cópia em memória)
sc.render.engine = 'CYCLES'; sc.cycles.samples = 12; sc.render.film_transparent = False; sc.render.resolution_x = sc.render.resolution_y = 560
if not any(o.type == 'LIGHT' for o in sc.objects):
    L = bpy.data.objects.new('P1i6_Luz', bpy.data.lights.new('P1i6_Luz', 'SUN')); sc.collection.objects.link(L)
    L.rotation_euler = (math.radians(50), math.radians(10), math.radians(-30)); L.data.energy = 3
def cam(n, d, t, s):
    c = bpy.data.objects.new(n, bpy.data.cameras.new(n)); sc.collection.objects.link(c); c.data.type = 'ORTHO'; c.data.ortho_scale = s
    d = Vector(d).normalized(); c.location = Vector(t) + d * 4; c.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler(); return c
tgt = (S + W + down * HAND_L) / 2
CAMS = {'frente': cam('cf', (0, -1, 0), tgt, 0.62), 'lado': cam('cl', (1, 0, 0), tgt, 0.62),
        'mao': cam('cm', (0.35, -1, 0.1), W + down * HAND_L * 0.5, 0.30), 'palma': cam('cp', (-0.3, 1, 0.0), W + down * HAND_L * 0.5, 0.30)}
CAM_CORPO = cam('cc', (0, -1, 0), Vector((0, 0, 0.98)), 2.1)
# corpo sem o braço esquerdo atual, só para o render de encaixe (máscara criada em memória; o arquivo oficial não é gravado)
gm = body.vertex_groups.new(name='p1i6_sem_braco'); gm.add([i for i in range(len(me.vertices)) if i not in arm_v], 1.0, 'REPLACE')
mk = body.modifiers.new('P1i6_Mascara', 'MASK'); mk.vertex_group = 'p1i6_sem_braco'
with bpy.context.temp_override(object=body, active_object=body):
    bpy.ops.object.modifier_move_to_index(modifier='P1i6_Mascara', index=1)
mk.show_render = False
def shoot(name, cams, show):
    for o in bpy.data.objects:
        if o.type == 'MESH': o.hide_render = o.name not in show
    for k, c in cams.items():
        sc.camera = c; sc.render.filepath = os.path.join(OUT, 'renders', f'{name}_{k}.png'); bpy.ops.render.render(write_still=True)
HC = W + down * HAND_L * 0.5
HCAMS = {'frente': cam('hf', (0, -1, 0), HC, 0.30), 'lado': cam('hl', (1, 0, 0), HC, 0.30),
         'dorso': cam('hd', -pn, HC, 0.30), 'perspectiva': cam('hp', (0.35, -1, 0.1), HC, 0.30)}
wire = arm.copy(); wire.name = 'P1i6_Arame'; sc.collection.objects.link(wire)
wm_ = wire.modifiers.new('Arame', 'WIREFRAME'); wm_.thickness = 0.0007; wm_.use_replace = True
wmat = bpy.data.materials.new('P1i6_Arame'); wmat.use_nodes = True; wn = wmat.node_tree
for n in list(wn.nodes):
    if n.type != 'OUTPUT_MATERIAL': wn.nodes.remove(n)
we = wn.nodes.new('ShaderNodeEmission'); we.inputs['Color'].default_value = (0.02, 0.06, 0.03, 1); wn.links.new(we.outputs[0], wn.nodes['Material Output'].inputs['Surface'])
wire.data = arm.data; wire.material_slots[0].link = 'OBJECT'; wire.material_slots[0].material = wmat
# corpo atual: mesma mão, mesmas câmeras (comparação com o original)
if not PREVIEW: reset(rig0); shoot('atual_repouso', HCAMS, {'Kumo'})
RENDER_POSES = ['repouso', 'mao_aberta_abduzida', 'mao_fechada', 'dedos_flexao_45', 'polegar_movimento', 'dedos_alternados',
                'punho_45', 'punho_menos45']
if PREVIEW: RENDER_POSES = ['repouso', 'mao_fechada', 'polegar_movimento']
for pname in RENDER_POSES:
    reset(rigo)
    if pname != 'repouso': apply_pose(rigo, POSES[pname], MAP_NEW, 'novo')
    shoot(f'novo_{pname}', HCAMS if pname in ('repouso', 'mao_aberta_abduzida', 'mao_fechada') else {k: HCAMS[k] for k in ('frente', 'perspectiva')},
          {'P1i6_Braco_E'})
    if pname in ('repouso', 'mao_fechada') and not PREVIEW: shoot(f'arame_{pname}', HCAMS, {'P1i6_Braco_E', 'P1i6_Arame'})
reset(rigo)
if PREVIEW: print('P1i6 PREVIEW OK'); raise SystemExit
mk.show_render = True
shoot('encaixe_novo', {'corpo': CAM_CORPO}, {'Kumo', 'P1i6_Braco_E'})
mk.show_render = False
shoot('encaixe_atual', {'corpo': CAM_CORPO}, {'Kumo'})
# arquivo do protótipo: só o braço novo e seu rig (o oficial nunca é salvo)
for o in list(bpy.data.objects):
    if o.name not in ('P1i6_Braco_E', 'P1i6_Rig'): bpy.data.objects.remove(o)
OUT_BLEND = os.path.join(OUT, f'p1_iter6_{MAO}.blend')
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND, relative_remap=False)
json.dump(REP, open(os.path.join(OUT, f'p1-iter6-{MAO}-medicoes.json'), 'w'), indent=1, default=str)
print('P1i6 OK')
