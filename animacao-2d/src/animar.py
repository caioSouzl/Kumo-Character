"""Kumo · animação 2D de 5 segundos feita com a arte ORIGINAL da referência (sem redesenho).

  python3 animar.py <saída>

Arte: character-model-sheet/assets/view-front.png, recorte da vista frontal da referência 01.
Técnica: recorte (cutout). A cabeça é uma peça separada; a cauda se mexe por deformação suave;
o corpo inteiro respira e pula com achatamento e esticamento (squash & stretch).
A única coisa desenhada por cima é a pálpebra na piscada: verde da própria pele em volta do olho
e a linha marrom de contorno da paleta (#5B3A2E).
"""
import sys, os, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT = sys.argv[1] if len(sys.argv) > 1 else 'saida'
os.makedirs(os.path.join(OUT, 'quadros'), exist_ok=True)
FPS, DUR = 24, 5.0
N = int(FPS * DUR)
CW, CH = 1080, 1350                       # vertical, bom para ver no celular
BG = (237, 229, 211)                      # papel da folha de referência
ARTE = '/home/user/Kumo-Character/character-model-sheet/assets/view-front.png'

src = Image.open(ARTE).convert('RGBA')
W, H = src.size                            # 615 × 888
A = np.asarray(src).astype(np.float32)

# ---------------- peças
# borda de baixo da cabeça (queixo), medida na arte: (x, y)
QUEIXO = [(0, 395), (30, 400), (175, 472), (300, 472), (460, 422), (W, 418)]
def queixo(x):
    for (x0, y0), (x1, y1) in zip(QUEIXO, QUEIXO[1:]):
        if x0 <= x <= x1: return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return QUEIXO[-1][1]
yy, xx = np.mgrid[0:H, 0:W]
qy = np.array([queixo(x) for x in range(W)])[None, :]
cab_m = (yy < qy + 7)                     # a faixa de 7 px abaixo do queixo vai com a cabeça (leva o contorno inteiro, sem fiapo branco)
cabeca = A.copy(); cabeca[..., 3] *= cab_m
corpo = A.copy(); corpo[..., 3] *= ~cab_m
# dos lados do pescoço não há corpo logo abaixo do queixo: limpa o resto do contorno da cabeça que ficaria para trás
lado = (xx < 175) | (xx > 300)
corpo[..., 3] *= ~(lado & (yy < np.minimum(qy + 25, 476)))
# "pescoço": por baixo da cabeça, estende o alto do tronco para cima (só aparece se a cabeça inclinar)
for x in range(165, 312):
    y0 = int(queixo(x)) + 9
    if corpo[y0, x, 3] > 200:
        for y in range(y0 - 40, y0): corpo[y, x] = corpo[y0, x]
PIV_CAB = (237.0, 468.0)                    # pivô da cabeça: centro do pescoço

# olhos (elipses medidas na arte) e cor da pele logo acima de cada um
OLHOS = [dict(c=(110.0, 315.0), r=(61.0, 89.0)), dict(c=(392.0, 314.0), r=(68.0, 91.0))]
for o in OLHOS:
    cx, cy = o['c']; rx, ry = o['r']
    # pele num anel em volta do olho: só verdes claros (sem contorno, sem manchas escuras)
    e = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2
    rgb = A[..., :3]; g_ = rgb[..., 1]; mx_ = rgb.max(-1); mn_ = rgb.min(-1)
    sel = (e > 1.25) & (e < 1.9) & (g_ >= rgb[..., 0]) & (g_ >= rgb[..., 2]) & (mx_ > 110) & ((mx_ - mn_) / np.maximum(mx_, 1) > 0.25) & (A[..., 3] > 250) & (yy < cy)
    o['pele'] = tuple(int(v) for v in np.median(rgb[sel], axis=0))
    o['sombra'] = tuple(int(v * 0.86) for v in o['pele'])
# as duas pálpebras usam o mesmo tom (o olho esquerdo pega mais sombra da crista e ficava escuro demais)
_pele = tuple(int(v) for v in np.max(np.array([o['pele'] for o in OLHOS]), axis=0))
for o in OLHOS: o['pele'] = _pele; o['sombra'] = tuple(int(v * 0.86) for v in _pele)
CONTORNO = (43, 26, 20)                    # mesmo tom escuro do contorno da arte

# cauda: deformação suave (gira em torno da base, com peso que cresce para a ponta)
PIV_CAUDA = (395.0, 770.0)
def a_de(y):                               # onde a cauda começa a se mover, por altura (evita a mão)
    if y <= 725: return 432.0
    if y >= 755: return 362.0
    return 432.0 + (362.0 - 432.0) * (y - 725) / 30.0
A_Y = np.array([a_de(y) for y in range(H)])[:, None]
def smooth(t): t = np.clip(t, 0, 1); return t * t * (3 - 2 * t)
PESO = smooth((xx - A_Y) / 80.0) * (yy > 520)

def deforma_cauda(img, ang):
    """amostragem inversa: cada pixel busca a cor girada de volta pelo seu peso."""
    if abs(ang) < 1e-4: return img
    th = -math.radians(ang) * PESO
    dx, dy = xx - PIV_CAUDA[0], yy - PIV_CAUDA[1]
    sx = PIV_CAUDA[0] + dx * np.cos(th) - dy * np.sin(th); sy = PIV_CAUDA[1] + dx * np.sin(th) + dy * np.cos(th)
    x0 = np.clip(np.floor(sx).astype(int), 0, W - 2); y0 = np.clip(np.floor(sy).astype(int), 0, H - 2)
    fx = (sx - x0)[..., None]; fy = (sy - y0)[..., None]
    out = (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy) + img[y0 + 1, x0] * (1 - fx) * fy + img[y0 + 1, x0 + 1] * fx * fy)
    m = (PESO > 0)[..., None]
    fora = ((sx < 0) | (sx > W - 1) | (sy < 0) | (sy > H - 1))[..., None]
    out = np.where(fora, 0, out)
    return np.where(m, out, img)

def palpebras(img, fecha):
    """fecha 0..1. Desenha em 4× e reduz (borda suave)."""
    if fecha <= 0.01: return img
    S = 4; lay = Image.new('RGBA', (W * S, H * S), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for o in OLHOS:
        cx, cy = o['c']; rx, ry = o['r']; rx -= 1; ry -= 1
        borda = cy - ry + 2 * ry * min(1.0, fecha * 1.04)
        pts = []
        for i in range(0, 181):
            a = math.pi + math.pi * i / 180          # metade de cima da elipse, da esquerda para a direita
            pts.append((cx + rx * math.cos(a), cy + ry * math.sin(a)))
        # recorta a elipse pela linha da borda (levemente curva, como uma pálpebra)
        poly = []
        for i in range(0, 361):
            a = 2 * math.pi * i / 360; x = cx + rx * math.cos(a); y = cy + ry * math.sin(a)
            lim = borda + 6 * (1 - ((x - cx) / rx) ** 2) * min(1, fecha * 2)
            poly.append((x, min(y, lim)))
        d.polygon([(x * S, y * S) for x, y in poly], fill=(255, 255, 255, 255))   # máscara; a cor vem depois, em degradê
        linha = [(cx + rx * math.cos(a) * 1.0, 0) for a in []]
        xs = np.linspace(cx - rx, cx + rx, 80)
        seg = []
        for x in xs:
            yb = cy + ry * math.sqrt(max(0.0, 1 - ((x - cx) / rx) ** 2))
            lim = borda + 6 * (1 - ((x - cx) / rx) ** 2) * min(1, fecha * 2)
            yt = cy - ry * math.sqrt(max(0.0, 1 - ((x - cx) / rx) ** 2))
            if yt < lim: seg.append((x * S, min(lim, yb) * S))
        if len(seg) > 1: d.line(seg, fill=CONTORNO + (255,), width=int(4.5 * S), joint='curve')
    lay = np.asarray(lay.resize((W, H), Image.LANCZOS)).astype(np.float32)
    # cor da pálpebra: degradê vertical, um pouco mais escuro no alto (como a sombra da pele sob a sobrancelha)
    cor = np.zeros((H, W, 3), np.float32)
    for o in OLHOS:
        cx, cy = o['c']; rx, ry = o['r']
        t = np.clip((yy - (cy - ry)) / (2 * ry), 0, 1)[..., None]
        reg = (np.abs(xx - cx) <= rx + 2)[..., None]
        cor = np.where(reg, np.array(o['sombra'])[None, None] * (1 - t) + np.array(o['pele'])[None, None] * t, cor)
    linha = (lay[..., 0] < 128)[..., None]                       # o traço do contorno foi desenhado escuro
    a_ = lay[..., 3:4] / 255.0
    col = np.where(linha, lay[..., :3], cor)
    out = img.copy(); out[..., :3] = img[..., :3] * (1 - a_) + col * a_; out[..., 3:4] = np.maximum(img[..., 3:4], lay[..., 3:4])
    return out

# ---------------- roteiro (segundos) — começa e termina na mesma pose, então pode repetir
def ease(t): return 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, t)))
def janela(t, a, b): return ease((t - a) / (b - a))
def piscada(t, t0, dur=0.20):
    u = (t - t0) / dur
    if u < 0 or u > 1: return 0.0
    return math.sin(math.pi * u) ** 0.7
def pose(t):
    # cabeça: olha para um lado (curioso), depois para o outro, volta
    inc = 5.0 * janela(t, 0.7, 1.4) - 9.0 * janela(t, 1.9, 2.6) + 4.0 * janela(t, 2.9, 3.3)
    # cauda: balanço contínuo, que fecha um ciclo em 5 s
    cauda = 6.0 * math.sin(2 * math.pi * t / 2.5)
    # respiração (fica no pulo como base)
    resp = math.sin(2 * math.pi * t / 2.5)
    sx, sy, dy = 1 - 0.006 * resp, 1 + 0.012 * resp, 0.0
    # pulo feliz: prepara (agacha), sobe esticado, cai, amortece
    if 3.30 <= t < 3.55: k = ease((t - 3.30) / 0.25); sy *= 1 - 0.09 * k; sx *= 1 + 0.06 * k
    elif 3.55 <= t < 4.15:
        u = (t - 3.55) / 0.60; dy = -95 * 4 * u * (1 - u)
        st = 1 + 0.07 * math.sin(math.pi * min(1, u * 1.6)) * (1 - u)
        sy *= st if u < 0.5 else 1 + 0.04 * (1 - u); sx *= 1 / math.sqrt(sy)
        if u < 0.15: sy *= 1 - 0.09 * (1 - u / 0.15)
    elif 4.15 <= t < 4.55:
        u = (t - 4.15) / 0.40; k = math.sin(math.pi * u) * (1 - u * 0.3)
        sy *= 1 - 0.10 * k; sx *= 1 + 0.07 * k
    inc_extra = -3.0 * math.sin(math.pi * max(0, min(1, (t - 3.55) / 0.6)))   # cabeça "atrasa" no pulo
    fecha = max(piscada(t, 0.35), piscada(t, 2.15), piscada(t, 4.35, 0.18))
    return dict(inc=inc + inc_extra, cauda=cauda, sx=sx, sy=sy, dy=dy, fecha=fecha)

# ---------------- render
ESC = 1.30                                  # arte → tela
CHAO = CH - 120
def quadro(t):
    p = pose(t)
    corpo_i = deforma_cauda(corpo, p['cauda'])
    cab = palpebras(cabeca, p['fecha'])
    cab_img = Image.fromarray(np.clip(cab, 0, 255).astype(np.uint8), 'RGBA')
    cab_img = cab_img.rotate(p['inc'], resample=Image.BICUBIC, center=PIV_CAB)
    figura = Image.fromarray(np.clip(corpo_i, 0, 255).astype(np.uint8), 'RGBA'); figura.alpha_composite(cab_img)
    # achatamento/esticamento em torno dos pés, escala e posição na tela
    sx, sy = p['sx'] * ESC, p['sy'] * ESC
    fw, fh = int(round(W * sx)), int(round(H * sy))
    fig = figura.resize((fw, fh), Image.LANCZOS)
    tela = Image.new('RGBA', (CW, CH), BG + (255,))
    # sombra no chão (encolhe quando ele sobe)
    alt = -p['dy']; k = 1 - min(0.45, alt / 260)
    sw, sh = int(330 * k * p['sx']), int(46 * k)
    sombra = Image.new('RGBA', (CW, CH), (0, 0, 0, 0)); ds = ImageDraw.Draw(sombra)
    ds.ellipse([CW / 2 - 30 - sw / 2, CHAO - sh / 2, CW / 2 - 30 + sw / 2, CHAO + sh / 2], fill=(60, 50, 30, int(70 * k)))
    tela.alpha_composite(sombra.filter(ImageFilter.GaussianBlur(10)))
    pe_x = W * 0.385                         # meio entre os pés, na arte
    x = int(round(CW / 2 - 30 - pe_x * sx)); y = int(round(CHAO - (H - 18) * sy + p['dy'] * ESC))
    tela.alpha_composite(fig, (x, y))
    return tela.convert('RGB')

if __name__ == '__main__':
    for i in range(N):
        quadro(i / FPS).save(os.path.join(OUT, 'quadros', f'q{i:04d}.png'))
    print('quadros', N)
