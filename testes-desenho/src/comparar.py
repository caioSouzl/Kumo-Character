"""Medidor de fidelidade: compara imagens do Kumo com as vistas aprovadas da folha de modelo.
Para cada vista, alinha (mesma altura, pés na mesma linha, mesmo centro) e mede:
  silhueta: IoU das máscaras (1 = contorno idêntico)
  cor: diferença média de cor dentro da área comum (0 = igual; escala 0–255)
  python comparar.py <pasta com PNGs> <saída.png> [vistas: front,three-quarter,side,back]
"""
import sys, os, glob, json
import numpy as np
from PIL import Image, ImageDraw, ImageOps
RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
VISTAS = {v: os.path.join(RAIZ, 'character-model-sheet', 'assets', f'view-{v}.png') for v in ('front', 'three-quarter', 'side', 'back')}
def cortar(im):
    a = np.asarray(im)[..., 3] > 128; ys, xs = np.nonzero(a)
    return im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
def alinhar(ref, img, H=600):
    r = cortar(ref); i = cortar(img)
    r = r.resize((max(1, round(r.width * H / r.height)), H), Image.LANCZOS); i = i.resize((max(1, round(i.width * H / i.height)), H), Image.LANCZOS)
    W = max(r.width, i.width) + 20
    def pad(x): c = Image.new('RGBA', (W, H), (0, 0, 0, 0)); c.alpha_composite(x, ((W - x.width) // 2, 0)); return c
    return pad(r), pad(i)
def medir(ref, img):
    r, i = alinhar(ref, img); R = np.asarray(r).astype(float); I = np.asarray(i).astype(float)
    mr, mi = R[..., 3] > 128, I[..., 3] > 128; iou = (mr & mi).sum() / max(1, (mr | mi).sum())
    ok = mr & mi; cor = np.abs(R[ok, :3] - I[ok, :3]).mean() if ok.any() else 255
    return iou, cor, r, i
if __name__ == '__main__':
    pasta, saida = sys.argv[1], sys.argv[2]; quais = sys.argv[3].split(',') if len(sys.argv) > 3 else list(VISTAS)
    cand = sorted(glob.glob(os.path.join(pasta, '*.png'))); res = {}; linhas = []
    # cada vista só compara com os ângulos certos (a silhueta de frente e de costas é parecida e enganava a escolha)
    ANG = {'front': ['000'], 'three-quarter': ['045', '315'], 'side': ['090', '270'], 'back': ['180']}
    for v in quais:
        ref = Image.open(VISTAS[v]).convert('RGBA'); melhor = None
        for f in [f for f in cand if any(a in os.path.basename(f) for a in ANG[v])] or cand:
            im = Image.open(f).convert('RGBA')
            for esp in (False, True):
                x = ImageOps.mirror(im) if esp else im
                iou, cor, r, i = medir(ref, x)
                if melhor is None or iou > melhor[0]: melhor = (iou, cor, os.path.basename(f) + (' (espelhado)' if esp else ''), r, i)
        res[v] = dict(silhueta_iou=round(melhor[0], 3), cor_dif=round(melhor[1], 1), imagem=melhor[2]); linhas.append((v, melhor))
        print(v, res[v])
    H = 600; o = Image.new('RGB', (sum(2 * l[1][3].width + 30 for l in linhas), H + 40), 'white'); d = ImageDraw.Draw(o); x = 0
    for v, m in linhas:
        for k, im in enumerate((m[3], m[4])):
            b = Image.new('RGBA', im.size, (237, 229, 211, 255)); b.alpha_composite(im); o.paste(b.convert('RGB'), (x, 40)); x += im.width + (30 if k else 0)
        d.text((x - 2 * m[3].width - 30 + 4, 6), f'{v}: referência | teste   silhueta {m[0]:.2f} · cor {m[1]:.0f}', fill='black')
    o.save(saida); json.dump(res, open(os.path.splitext(saida)[0] + '.json', 'w'), indent=1)
