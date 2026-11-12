"""Kumo 2D · animação 2 (5 s), feita sobre as camadas fiéis (camadas.py) com o rig de recorte (rig2d.py),
seguindo as regras de tempo da pesquisa (estudos-animacao/02-TEMPO.md) e conferida por planilha.py.

  python animar_v2.py <pasta das camadas> <saída>
"""
import sys, os, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig2d import Rig
from planilha import Canal as C, amostrar, conferir, tabela, grafico
CAM, OUT = sys.argv[1], sys.argv[2]; os.makedirs(os.path.join(OUT, 'quadros'), exist_ok=True)
FPS, N = 24, 120
# ---------------- planilha (quadros a 24 qps). Mesmo roteiro da animação 1: olha para um lado, para o outro, volta, pulinho.
# piscadas: fecha 2 · fechado 1 · abre 3 (normal); longa 3 · 2 · 4 (mudança de ideia); rápida 2 · 0 · 3 (na queda)
def piscada(f0, fecha=2, segura=1, abre=3):
    return [(f0, 0, 'lin'), (f0 + fecha, 1, 'entra'), (f0 + fecha + segura, 1, 'segura'), (f0 + fecha + segura + abre, 0, 'sai')]
PISC = piscada(8) + piscada(17) + piscada(45, 3, 2, 4) + piscada(69) + piscada(99, 2, 0, 3)
fecha = C([(0, 0, 'lin')] + PISC)
# olhar: os olhos chegam antes (2 quadros) e a olhada dura 3 quadros; a cabeça vem depois, passa do ponto e assenta
olhar_x = C([(0, 0, 'lin'), (16, 0, 'segura'), (19, -9, 'sai'), (44, -9, 'segura'), (47, 10, 'sai'), (68, 10, 'segura'), (71, 0, 'sai'), (119, 0, 'segura')])
olhar_y = C([(0, 0, 'lin'), (16, 0, 'segura'), (19, -3, 'sai'), (44, -3, 'segura'), (47, -2, 'sai'), (68, -2, 'segura'), (71, 0, 'sai'), (86, 0, 'segura'), (89, -5, 'sai'), (100, -5, 'segura'), (103, 0, 'sai')])
cabeca = C([(0, 0, 'lin'), (18, 0, 'segura'), (30, 5, 'passa'), (46, 5, 'segura'), (60, -9, 'passa'), (70, -9, 'segura'), (80, 0, 'passa'), (119, 0, 'segura')])
# pulo: prepara 6 quadros (78–84), sobe esticado (pico do esticar em 3 quadros), 14 quadros no ar, toca o chão no 98,
# achata no 99–100 e volta com um pequeno quique
ALT = 95.0
def altura(f):
    if 84 <= f <= 98: u = (f - 84) / 14.0; return -ALT * 4 * u * (1 - u)
    return 0.0
sy_pulo = C([(0, 1, 'lin'), (78, 1, 'segura'), (84, 0.91, 'sai'), (87, 1.08, 'sai'), (91, 1.0, 'suave'), (96, 1.03, 'suave'), (98, 1.0, 'lin'), (100, 0.88, 'sai'), (105, 1.025, 'suave'), (110, 0.995, 'suave'), (114, 1.0, 'suave'), (119, 1, 'segura')])
# braços: balanço com a respiração (sobreposição: 3 quadros de atraso), descem e vão para trás na preparação,
# abrem no salto com 2 quadros de arrasto, e assentam depois da queda
br_pulo = C([(0, 0, 'lin'), (78, 0, 'segura'), (84, -5, 'sai'), (89, 14, 'sai'), (95, 10, 'suave'), (100, 3, 'entra'), (104, -3, 'sai'), (110, 1, 'suave'), (116, 0, 'suave'), (119, 0, 'segura')])
# cabeça atrasa no pulo (arrasto) e a cauda reage com atraso
cab_pulo = C([(0, 0, 'lin'), (84, 0, 'segura'), (88, -2.5, 'sai'), (96, 1.5, 'suave'), (100, 3, 'sai'), (106, -1, 'suave'), (112, 0, 'suave')])
cauda_pulo = C([(0, 0, 'lin'), (86, 0, 'segura'), (91, -9, 'sai'), (99, 4, 'suave'), (103, 10, 'sai'), (110, -3, 'suave'), (118, 0, 'suave')])
def respira(f):
    """inspira mais devagar que expira: 60% do ciclo subindo, 40% descendo (ciclo de 60 quadros = 2,5 s)"""
    u = (f % 60) / 60.0
    return 0.5 - 0.5 * math.cos(math.pi * u / 0.6) if u < 0.6 else 0.5 + 0.5 * math.cos(math.pi * (u - 0.6) / 0.4)
def pose(f):
    r = respira(f); r3 = respira(f - 3)        # braços 3 quadros atrasados em relação ao peito
    sy = (1 + 0.012 * (r - 0.5) * 2) * sy_pulo(f); sx = 1 / math.sqrt(sy)
    b = br_pulo(f); bal = 1.6 * (r3 - 0.5) * 2
    return dict(cabeca=cabeca(f) + cab_pulo(f), olhar=(olhar_x(f), olhar_y(f)), fecha_E=fecha(f), fecha_D=fecha(f),
                braco_E=-(b + bal), braco_D=(b + bal), cauda=6.0 * math.sin(2 * math.pi * f / 60) + cauda_pulo(f), sx=sx, sy=sy, dy=altura(f))
# ---------------- render (mesmo enquadramento da animação 1)
CW, CH = 1080, 1350; BG = (237, 229, 211); ESC = 1.20; CHAO = CH - 100   # a animação 1 (1,30) cortava a cabeça no alto do pulo; aqui o pulo inteiro cabe
rig = Rig(CAM); W, H = rig.W, rig.H
def quadro(f):
    p = pose(f); fig = rig.imagem(p)
    sx, sy = p['sx'] * ESC, p['sy'] * ESC; fw, fh = int(round(W * sx)), int(round(H * sy))
    fig = fig.resize((fw, fh), Image.LANCZOS)
    tela = Image.new('RGBA', (CW, CH), BG + (255,))
    alt = -p['dy']; k = 1 - min(0.45, alt / 260); sw, sh = int(330 * k * p['sx']), int(46 * k)
    sombra = Image.new('RGBA', (CW, CH), (0, 0, 0, 0)); ImageDraw.Draw(sombra).ellipse([CW / 2 - 30 - sw / 2, CHAO - sh / 2, CW / 2 - 30 + sw / 2, CHAO + sh / 2], fill=(60, 50, 30, int(70 * k)))
    tela.alpha_composite(sombra.filter(ImageFilter.GaussianBlur(10)))
    pe_x = W * 0.385; x = int(round(CW / 2 - 30 - pe_x * sx)); y = int(round(CHAO - (H - 18) * sy + p['dy'] * ESC))
    tela.alpha_composite(fig, (x, y)); return tela.convert('RGB')
if __name__ == '__main__':
    P = [pose(f) for f in range(N)]
    c = {'fecha': np.array([p['fecha_E'] for p in P]), 'cabeca': amostrar(cabeca, N), 'olhar_x': np.array([p['olhar'][0] for p in P]),
         'sy': np.array([p['sy'] for p in P]), 'dy': np.array([p['dy'] for p in P])}
    R = conferir(c); print(tabela(R))
    grafico({'piscar': c['fecha'], 'olhar ← →': c['olhar_x'], 'cabeça (°)': c['cabeca'], 'braço E (°)': [p['braco_E'] for p in P], 'esticar (sy)': c['sy'], 'altura': -c['dy'], 'cauda (°)': [p['cauda'] for p in P]},
            os.path.join(OUT, 'planilha.png'), 'Animação 2 · planilha de tempo (um ponto por quadro, 24 qps)')
    if '--so-planilha' not in sys.argv:
        topo = 9999
        for f in range(N):
            im = quadro(f); im.save(os.path.join(OUT, 'quadros', f'q{f:04d}.png'))
            x = np.asarray(im).astype(int); lin = np.nonzero((np.abs(x - BG).max(-1) > 25).any(1))[0]; topo = min(topo, lin.min())
        print(('✔' if topo >= 10 else '✘') + f' cabe na tela: menor folga em cima {topo} px')
        print('quadros', N)
