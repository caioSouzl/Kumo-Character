"""Monta as pranchas de avaliação e as métricas de fidelidade do olho aberto.

  python compose_sheets.py <olhos-v3>
"""
import os, sys, json, glob
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

OUT = sys.argv[-1]; RD = os.path.join(OUT, 'renders'); ST = os.path.join(RD, 'estados'); TMP = os.path.join(RD, 'tmp')
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
F = ImageFont.truetype(FONT, 22) if os.path.exists(FONT) else ImageFont.load_default()
FB = ImageFont.truetype(FONT.replace('Sans.ttf', 'Sans-Bold.ttf'), 30) if os.path.exists(FONT) else F

# a câmera em -90° vê o lado DIREITO do Kumo (x < 0); +90° vê o lado esquerdo
VIEW_LABEL = {'frente': 'Frente', '34': '3/4 (lado direito)', 'perfil_E': 'Perfil · olho direito', 'perfil_D': 'Perfil · olho esquerdo'}

def load(p): return np.array(Image.open(p).convert('RGB'))

def label(img, text, font=F):
    im = Image.fromarray(img); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, im.width, 34], fill=(25, 25, 25)); d.text((10, 5), text, fill=(240, 240, 240), font=font)
    return np.array(im)

def grid(rows, title, path, cell=360):
    tiles = [[label(cv2.resize(load(p), (cell, cell), interpolation=cv2.INTER_AREA), t) if p else np.full((cell, cell, 3), 40, np.uint8)
              for p, t in row] for row in rows]
    body = np.vstack([np.hstack(r) for r in tiles])
    head = Image.new('RGB', (body.shape[1], 56), (15, 15, 15)); ImageDraw.Draw(head).text((14, 10), title, fill=(255, 255, 255), font=FB)
    Image.fromarray(np.vstack([np.array(head), body])).save(path)

S = lambda name, v: os.path.join(ST, f'{name}_{v}.png')
V4 = ['frente', '34', 'perfil_E', 'perfil_D']

# ---------------------------------------------------------------- métricas do olho aberto
def eye_pixels(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV_FULL).astype(float) / 255
    warm = (hsv[..., 0] > 0.02) & (hsv[..., 0] < 0.17) & (hsv[..., 1] > 0.25) & (hsv[..., 2] > 0.55)
    dark = hsv[..., 2] < 0.14
    return warm | dark

metrics = {}
for v in V4:
    a, b = load(os.path.join(TMP, f'orig_{v}.png')), load(S('aberto', v))
    em = cv2.dilate(eye_pixels(a).astype(np.uint8), np.ones((9, 9), np.uint8))
    n, lab, stats, cent = cv2.connectedComponentsWithStats(em)
    keep = [k for k in range(1, n) if stats[k, cv2.CC_STAT_AREA] > 1500]
    region = np.isin(lab, keep)
    diff = np.abs(a.astype(int) - b.astype(int)).max(axis=2)
    m = dict(diferenca_media_regiao_olhos=round(float(diff[region].mean()), 2),
             pixels_regiao_olhos=int(region.sum()),
             pct_pixels_diferenca_maior_que_24=round(float((diff[region] > 24).mean() * 100), 2),
             pct_pixels_diferenca_maior_que_48=round(float((diff[region] > 48).mean() * 100), 2),
             diferenca_media_imagem_inteira=round(float(diff.mean()), 3))
    # posição: centroide dos olhos (antes x depois)
    cents = {}
    for tag, img in (('antes', a), ('depois', b)):
        e = eye_pixels(img).astype(np.uint8); n2, lab2, st2, ct2 = cv2.connectedComponentsWithStats(e)
        big = sorted([k for k in range(1, n2) if st2[k, cv2.CC_STAT_AREA] > 800 and ct2[k][1] < 450 and 20 < ct2[k][0] < 540], key=lambda k: ct2[k][0])
        cents[tag] = [[round(float(x), 1) for x in ct2[k]] for k in big]
    m['centroides_olhos_px'] = cents
    if len(cents['antes']) == 2 and len(cents['depois']) == 2:
        da = np.linalg.norm(np.subtract(*cents['antes'])); db = np.linalg.norm(np.subtract(*cents['depois']))
        m['distancia_entre_olhos_px'] = dict(antes=round(float(da), 1), depois=round(float(db), 1))
    m['deslocamento_max_centroide_px'] = round(float(max(np.linalg.norm(np.subtract(p, q)) for p, q in zip(cents['antes'], cents['depois']))), 2) if cents['antes'] and len(cents['antes']) == len(cents['depois']) else None
    metrics[v] = m
    amp = np.clip(diff * 4, 0, 255).astype(np.uint8)
    cv2.imwrite(os.path.join(TMP, f'dif_{v}.png'), cv2.applyColorMap(amp, cv2.COLORMAP_INFERNO))

# silhueta do corpo inteiro (IoU do alfa)
sil = {}
for v in ('frente', '34', 'perfil', 'costas'):
    a = np.array(Image.open(os.path.join(TMP, f'orig_corpo_{v}.png')))[..., 3] > 127
    b = np.array(Image.open(os.path.join(ST, f'exp_corpo_{v}.png')))[..., 3] > 127
    sil[v] = dict(iou=round(float((a & b).sum() / (a | b).sum()), 5), pixels_diferentes=int((a ^ b).sum()))
metrics['silhueta_corpo'] = sil
json.dump(metrics, open(os.path.join(OUT, 'olhos-v3-fidelidade.json'), 'w'), indent=1)
print(json.dumps(metrics, indent=1))

# ---------------------------------------------------------------- pranchas
P = os.path.join(RD)
grid([[(os.path.join(TMP, f'orig_{v}.png'), f'Original · {VIEW_LABEL[v]}'), (S('aberto', v), 'Experimento · aberto'),
       (os.path.join(TMP, f'dif_{v}.png'), 'Diferença ×4')] for v in V4],
     'Olho aberto: original × experimento', os.path.join(P, '01-aberto-comparacao.png'))
grid([[(S('aberto', v), f'{VIEW_LABEL[v]} · 0%')] + [(S(f'fechado_{k:03d}', v), f'{k}%') for k in (25, 50, 75, 100)] for v in V4],
     'Cabeça neutra · fechamento 0 · 25 · 50 · 75 · 100%', os.path.join(P, '02-fechamento-neutra.png'))
grid([[(S('fechado_050', v), f'50% · {VIEW_LABEL[v]}')] for v in V4], 'Foco: 50% de fechamento (cabeça neutra)', os.path.join(P, '03-foco-50.png'), cell=620)
grid([[(S(n, v), t) for n, t in (('piscada_E', 'Pisca só o esquerdo'), ('piscada_D', 'Pisca só o direito'),
                                ('piscada_E_050', 'Esquerdo 50%'), ('piscada_D_050', 'Direito 50%'), ('semicerrado_040', 'Semicerrar 40%'))]
      for v in ('frente', '34')], 'Piscada individual e semicerrar', os.path.join(P, '04-piscada-individual.png'))
grid([[(S(n, v), t) for n, t in (('aberto', 'Centro'), ('olhar_esq', 'Para a esquerda do Kumo'), ('olhar_dir', 'Para a direita do Kumo'),
                                ('olhar_cima', 'Para cima'), ('olhar_baixo', 'Para baixo'), ('olhar_diag', 'Diagonal'))] for v in V4],
     'Olhar (cabeça neutra)', os.path.join(P, '05-olhar.png'), cell=300)
for yaw in (18, 25):
    grid([[(S(f'virada{yaw:+d}_fechado_000', v), f'Virada {yaw}° · {VIEW_LABEL[v]}')] + [(S(f'virada{yaw:+d}_fechado_{k:03d}', v), f'{k}%') for k in (25, 50, 75, 100)] for v in V4],
         f'Cabeça virada {yaw}° · piscada 0 · 25 · 50 · 75 · 100%', os.path.join(P, f'06-virada-{yaw}.png'))
grid([[(S(f'virada-25_fechado_{k:03d}', v), f'Virada -25° · {k}% · {VIEW_LABEL[v][:12]}') for k in (0, 50, 100)] for v in V4],
     'Cabeça virada para o outro lado (-25°)', os.path.join(P, '06-virada-menos25.png'))
grid([[(S(n, v), t) for n, t in (('virada+25_olhar_esq', f'Virada 25° · olha p/ esquerda · {VIEW_LABEL[v][:12]}'), ('virada+25_olhar_dir', 'olha p/ direita'), ('virada+25_olhar_esq_050', 'olha p/ esquerda + 50%'))] for v in V4],
     'Olhar lateral durante a rotação (25°)', os.path.join(P, '07-olhar-durante-rotacao.png'))
rows = []
for yaw in (18, 25, -25):
    for v in ('frente', '34'):
        rows.append([(os.path.join(TMP, f'orig_virada{yaw:+d}_{v}.png'), f'Original · virada {yaw}° · {VIEW_LABEL[v][:10]}'),
                     (S(f'virada{yaw:+d}_fechado_000', v), 'olhos-v3 · aberto')])
grid(rows, 'Fidelidade com a cabeça virada: original × olhos-v3', os.path.join(P, '08-rotacao-original-x-v2.png'), cell=330)
V2 = os.path.join(OUT, '..', 'olhos-v2', 'renders', 'estados')
for v in ('frente', '34', 'perfil_E', 'perfil_D'):
    grid([[(os.path.join(V2, f'{n}_{v}.png'), f'v2 · {t}'), (S(n, v), f'v3 · {t}')] for n, t in (('aberto', 'aberto'), ('semicerrado_040', 'semicerrado 40%'), ('fechado_050', '50%'), ('fechado_100', 'fechado'))],
         f'v2 × v3 · {VIEW_LABEL[v]}', os.path.join(P, f'09-v2-x-v3-{v}.png'), cell=330)
seq = sorted(glob.glob(os.path.join(ST, 'seq_*.png')))
frames = [Image.open(p).convert('RGB') for p in seq]
frames[0].save(os.path.join(P, '10-piscada-animada.gif'), save_all=True, append_images=frames[1:] + frames[-1:] * 6, duration=70, loop=0)
strip = np.hstack([cv2.resize(load(p), (220, 220), interpolation=cv2.INTER_AREA) for p in seq])
Image.fromarray(strip).save(os.path.join(P, '10-piscada-sequencia.png'))
print('PRANCHAS OK')
