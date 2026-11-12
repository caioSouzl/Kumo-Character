"""Rig de recorte do Kumo 2D: monta as camadas de camadas.py numa pose.

pose = dict(
  cabeca=graus, braco_E=graus, braco_D=graus, cauda=graus,      # giros (positivo = anti-horário na tela)
  olhar=(dx, dy),                                                # íris/pupila, em px da arte (até ~±12 x, ±10 y)
  fecha_E=0..1, fecha_D=0..1,                                    # pálpebras
  sx=1, sy=1, dy=0)                                              # corpo inteiro: achatar/esticar nos pés e altura (px)
"""
import os, json, math
import numpy as np, cv2
from PIL import Image, ImageDraw
AQUI = os.path.dirname(os.path.abspath(__file__))
class Rig:
    def __init__(self, pasta):
        J = json.load(open(os.path.join(pasta, 'camadas.json'))); self.W, self.H = J['tamanho']; self.P = J['pivos']
        self.L = {k: np.asarray(Image.open(os.path.join(pasta, k + '.png'))).astype(np.float32) for k in J['ordem']}
        W, H = self.W, self.H; self.yy, self.xx = np.mgrid[0:H, 0:W].astype(np.float32)
        self.olhos = self.P['olhos']
        for k, o in self.olhos.items():
            e = ((self.xx - o['c'][0]) / o['r'][0]) ** 2 + ((self.yy - o['c'][1]) / o['r'][1]) ** 2
            o['dentro'] = np.clip((0.985 - e) / 0.03, 0, 1)        # máscara suave do globo (a íris não sai do olho)
        # cauda: peso que cresce para a ponta (mesma deformação da animação de 5 s)
        def a_de(y): return 432.0 if y <= 725 else (362.0 if y >= 755 else 432.0 + (362.0 - 432.0) * (y - 725) / 30.0)
        AY = np.array([a_de(y) for y in range(H)], np.float32)[:, None]
        t = np.clip((self.xx - AY) / 80.0, 0, 1); self.peso_cauda = t * t * (3 - 2 * t) * (self.yy > 520)
        # cor da pálpebra: pele em volta do olho (anel), igual à animação de 5 s
        A = sum(self.L[k] for k in ['cabeca'])
        rgb = A[..., :3]; g_ = rgb[..., 1]; mx_ = rgb.max(-1); mn_ = rgb.min(-1); peles = []
        for o in self.olhos.values():
            e = ((self.xx - o['c'][0]) / o['r'][0]) ** 2 + ((self.yy - o['c'][1]) / o['r'][1]) ** 2
            sel = (e > 1.25) & (e < 1.9) & (g_ >= rgb[..., 0]) & (g_ >= rgb[..., 2]) & (mx_ > 110) & ((mx_ - mn_) / np.maximum(mx_, 1) > 0.25) & (A[..., 3] > 250) & (self.yy < o['c'][1])
            peles.append(np.median(rgb[sel], axis=0))
        # cores da pálpebra = as da folha de expressões aprovada (character-model-sheet/src/build.mjs: lidB no alto, lidA embaixo)
        self.sombra = np.array([0x3C, 0x8F, 0x4C], np.float32); self.pele = np.array([0x5B, 0xAE, 0x5E], np.float32); self.contorno = np.array([0x2F, 0x16, 0x06], np.float32)
    # ---------- utilidades
    @staticmethod
    def sobre(a, b):
        """b por cima de a (RGBA float, alpha 0..255, cor NÃO pré-multiplicada)"""
        ab = b[..., 3:4] / 255.0; aa = a[..., 3:4] / 255.0; ao = ab + aa * (1 - ab)
        cor = (b[..., :3] * ab + a[..., :3] * aa * (1 - ab)) / np.maximum(ao, 1e-6)
        return np.concatenate([cor, ao * 255], -1)
    def girar(self, img, ang, piv, dx=0.0, dy=0.0):
        if abs(ang) < 1e-4 and dx == 0 and dy == 0: return img
        M = cv2.getRotationMatrix2D((float(piv[0]), float(piv[1])), ang, 1.0); M[0, 2] += dx; M[1, 2] += dy
        pm = img.copy(); pm[..., :3] *= pm[..., 3:4] / 255.0                    # gira pré-multiplicado e linear (o cúbico passa do ponto e, dividido por um alpha quase zero, vira risco branco)
        out = cv2.warpAffine(pm, M, (self.W, self.H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        out = np.clip(out, 0, 255); a = out[..., 3:4]; out[..., :3] = np.where(a > 0, out[..., :3] * 255.0 / np.maximum(a, 1e-6), 0); return np.clip(out, 0, 255)
    def cauda(self, img, ang):
        if abs(ang) < 1e-4: return img
        pv = self.P['cauda']; th = -math.radians(ang) * self.peso_cauda; dx, dy = self.xx - pv[0], self.yy - pv[1]
        mx = (pv[0] + dx * np.cos(th) - dy * np.sin(th)).astype(np.float32); my = (pv[1] + dx * np.sin(th) + dy * np.cos(th)).astype(np.float32)
        pm = img.copy(); pm[..., :3] *= pm[..., 3:4] / 255.0
        out = cv2.remap(pm, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        a = out[..., 3:4]; out[..., :3] = np.where(a > 0, out[..., :3] * 255.0 / np.maximum(a, 1e-6), 0); return np.clip(out, 0, 255)
    def palpebra(self, o, fecha):
        """camada da pálpebra de um olho (fecha 0..1), desenhada em 4× e reduzida"""
        W, H = self.W, self.H; S = 4; cx, cy = o['c']; rx, ry = o['r'][0] - 1, o['r'][1] - 1
        lay = Image.new('L', (W * S, H * S), 0); d = ImageDraw.Draw(lay); lin = Image.new('L', (W * S, H * S), 0); dl = ImageDraw.Draw(lin)
        borda = cy - ry + 2 * ry * min(1.0, fecha * 1.04); curva = 6 * min(1, fecha * 2)
        poly = []; seg = []
        for i in range(361):
            a = 2 * math.pi * i / 360; x = cx + rx * math.cos(a); y = cy + ry * math.sin(a)
            poly.append((x * S, min(y, borda + curva * (1 - ((x - cx) / rx) ** 2)) * S))
        for x in np.linspace(cx - rx, cx + rx, 80):
            u = max(0.0, 1 - ((x - cx) / rx) ** 2); yt = cy - ry * math.sqrt(u); yb = cy + ry * math.sqrt(u); lim = borda + curva * (1 - ((x - cx) / rx) ** 2)
            if yt < lim: seg.append((x * S, min(lim, yb) * S))
        d.polygon(poly, fill=255)
        if len(seg) > 1: dl.line(seg, fill=255, width=int(4.5 * S), joint='curve')
        m = np.asarray(lay.resize((W, H), Image.LANCZOS)).astype(np.float32) / 255.0; l = np.asarray(lin.resize((W, H), Image.LANCZOS)).astype(np.float32) / 255.0
        t = np.clip((self.yy - (cy - ry)) / (2 * ry), 0, 1)[..., None]
        cor = self.sombra * (1 - t) + self.pele * t
        cor = cor * (1 - l[..., None]) + self.contorno * l[..., None]
        return np.concatenate([cor, (np.maximum(m, l) * 255)[..., None]], -1)
    # ---------- montagem
    def montar(self, p):
        g = lambda k, d=0.0: p.get(k, d)
        corpo = self.cauda(self.L['corpo'], g('cauda'))
        out = corpo
        for lado in ('E', 'D'):
            out = self.sobre(out, self.girar(self.L['braco_' + lado], g('braco_' + lado), self.P['braco_' + lado]))
        # grupo da cabeça: cabeça + íris (presas no globo) + pálpebras, e o grupo gira junto
        cab = self.L['cabeca'].copy(); dx, dy = g('olhar', (0.0, 0.0))
        for k, o in self.olhos.items():
            ir = self.girar(self.L['iris_' + k], 0.0, (0, 0), dx, dy); ir[..., 3] *= o['dentro']
            cab = self.sobre(cab, ir)
            f = g('fecha_' + k)
            if f > 0.01: cab = self.sobre(cab, self.palpebra(o, f))
        out = self.sobre(out, self.girar(cab, g('cabeca'), self.P['cabeca']))
        return out
    def imagem(self, p):
        return Image.fromarray(np.clip(self.montar(p), 0, 255).astype(np.uint8), 'RGBA')
if __name__ == '__main__':
    import sys
    r = Rig(sys.argv[1]); a = np.asarray(Image.open(os.path.join(AQUI, '..', '..', 'character-model-sheet', 'assets', 'view-front.png')).convert('RGBA')).astype(float)
    m = r.montar({})
    pm = lambda X: np.concatenate([X[..., :3] * X[..., 3:4] / 255.0, X[..., 3:4]], -1)
    print('repouso x arte (pré-mult., fora dos olhos):', np.abs(pm(m) - pm(a)).max(-1)[(r.olhos['E']['dentro'] + r.olhos['D']['dentro']) == 0].max())
    for nm, p in {'braco_15': dict(braco_E=-15, braco_D=15), 'braco_30': dict(braco_E=30, braco_D=-30), 'olhar': dict(olhar=(-10, -6), cabeca=6), 'piscar': dict(fecha_E=1, fecha_D=0.5), 'cauda': dict(cauda=12)}.items():
        r.imagem(p).save(os.path.join(sys.argv[2], f'pose_{nm}.png'))
