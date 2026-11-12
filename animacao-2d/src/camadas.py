"""Kumo 2D: separa a arte original (vista de frente da folha de modelo) em camadas para animação de recorte.
Cada camada é um recorte EXATO da arte; o que fica escondido atrás dela (corpo atrás do braço, íris atrás da pupila)
é preenchido para quando a peça se mover. Montadas em repouso, as camadas refazem a arte pixel a pixel.

  python camadas.py <saída>      -> camadas PNG + camadas.json (pivôs) + conferencia.png
"""
import sys, os, json
import numpy as np, cv2
from PIL import Image
RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
ARTE = os.path.join(RAIZ, 'character-model-sheet', 'assets', 'view-front.png')
OUT = sys.argv[-1] if len(sys.argv) > 1 else 'camadas'; os.makedirs(OUT, exist_ok=True)
A = np.array(Image.open(ARTE).convert('RGBA')); H, W = A.shape[:2]
# Conserto da arte: o recorte da folha de modelo tirou como "fundo" o brilho branco da pupila direita (um furo de
# ~140 px dentro do olho). Na folha ele aparece branco porque a folha é branca; aqui o furo vira branco de verdade.
# Só dentro dos globos dos olhos; os outros vãos (entre braço e corpo, dentro da espiral da cauda) são reais.
_yy, _xx = np.mgrid[0:H, 0:W]
for (cx, cy), (rx, ry) in (((110.0, 315.0), (61.0, 89.0)), ((392.0, 314.0), (68.0, 91.0))):
    g = ((_xx - cx) / rx) ** 2 + ((_yy - cy) / ry) ** 2 < 0.9
    a_ = A[..., 3:4].astype(float) / 255.0
    A[g, :3] = (A[g, :3] * a_[g] + 255 * (1 - a_[g])).astype(np.uint8); A[g, 3] = 255
# Halo branco: a arte foi recortada de um fundo branco, então as bordas meio transparentes guardam branco misturado.
# Desfaz a mistura (cor = (C − (1−a)·255)/a), como num "defringe": sobre fundo branco fica igual; sobre outro fundo some o risco claro.
_a = A[..., 3:4].astype(float) / 255.0; _semi = (A[..., 3] > 0) & (A[..., 3] < 255)
_F = np.clip((A[..., :3].astype(float) - (1 - _a) * 255.0) / np.maximum(_a, 1e-3), 0, 255)
A[_semi, :3] = _F[_semi].astype(np.uint8)
# o que continua claro e neutro depois disso é o próprio fundo branco que ficou na borda: vira transparente (fora dos olhos)
_glob = np.zeros((H, W), bool)
for (cx, cy), (rx, ry) in (((110.0, 315.0), (61.0, 89.0)), ((392.0, 314.0), (68.0, 91.0))): _glob |= ((_xx - cx) / rx) ** 2 + ((_yy - cy) / ry) ** 2 < 1.05
_mn = A[..., :3].min(-1).astype(int); _mx = A[..., :3].max(-1).astype(int)
FUNDO = _semi & (_mn > 190) & (_mx - _mn < 45) & ~_glob
A[FUNDO, 3] = 0
# poeira do recorte: um véu de pixels quase invisíveis (alpha < 24) em volta de tudo. Parado não se vê; quando uma peça
# sai do lugar, o véu que ficou para trás desenha o contorno antigo. Vira transparente.
A[A[..., 3] < 24, 3] = 0
alpha = A[..., 3] > 0
lum = A[..., :3].astype(float) @ [0.299, 0.587, 0.114]
linha = alpha & (lum < 75)                                   # contorno escuro
def mascara_peca(poligono, corte, frac=0.85):
    """peça = pedaços sem contorno que caem quase inteiros dentro de um polígono folgado em volta dela
    (o corte fecha a passagem para o corpo, no ombro), mais o contorno que fica do lado da peça"""
    bar = (linha | ~alpha).astype(np.uint8)
    cv2.polylines(bar, [np.array(corte, np.int32)], False, 1, 3)
    n, lab = cv2.connectedComponents((1 - bar).astype(np.uint8), connectivity=4)
    pol = np.zeros((H, W), np.uint8); cv2.fillPoly(pol, [np.array(poligono, np.int32)], 1); pol = pol.astype(bool)
    cnt = np.bincount(lab.ravel(), minlength=n); dentro = np.bincount(lab[pol], minlength=n)
    ok = (dentro / np.maximum(cnt, 1) >= frac); ok[0] = False
    m = ok[lab] & alpha & ~linha
    resto = alpha & ~m & ~linha
    da = cv2.distanceTransform((~m).astype(np.uint8), cv2.DIST_L2, 3); dr = cv2.distanceTransform((~resto).astype(np.uint8), cv2.DIST_L2, 3)
    # contorno compartilhado (a linha entre a peça e o corpo) é da peça: ela está na frente
    m = m | (linha & (da < 8) & ((da <= dr) | ((da <= 5) & (dr <= 5))))
    # a franja meio transparente da borda (antisserrilhado) também: o que estiver colado na peça e longe do corpo opaco
    opaco = alpha & ~m & (A[..., 3] == 255) & ~linha
    da = cv2.distanceTransform((~m).astype(np.uint8), cv2.DIST_L2, 3); dr = cv2.distanceTransform((~opaco).astype(np.uint8), cv2.DIST_L2, 3)
    return m | (alpha & ~m & (da <= 3) & (dr > da + 1)) | (alpha & ~m & (A[..., 3] < 255) & (da <= 8) & (dr > da))
POL = {
    'braco_E': ([(176, 452), (168, 520), (153, 580), (143, 640), (135, 735), (25, 735), (25, 660), (60, 560), (120, 470)], [(160, 450), (166, 470), (170, 520)]),
    'braco_D': ([(292, 452), (312, 522), (327, 565), (337, 640), (345, 715), (430, 720), (430, 680), (400, 590), (360, 515), (320, 465)], [(300, 450), (302, 470), (311, 525)]),
}
yy, xx = np.mgrid[0:H, 0:W]
# ---------------- cabeça: corte pelo queixo (o mesmo da animação de 5 s)
QUEIXO = [(0, 395), (30, 400), (175, 472), (300, 472), (460, 422), (W, 418)]
qy = np.interp(np.arange(W), [p[0] for p in QUEIXO], [p[1] for p in QUEIXO])[None, :]
PIV_CABECA = (237.0, 468.0)
# ---------------- olhos: elipse do globo, pupila (preto) e íris (anel laranja em volta), que se movem juntas
OLHOS = {'E': dict(c=(110.0, 315.0), r=(61.0, 89.0)), 'D': dict(c=(392.0, 314.0), r=(68.0, 91.0))}
def olho(o):
    e = ((xx - o['c'][0]) / o['r'][0]) ** 2 + ((yy - o['c'][1]) / o['r'][1]) ** 2
    dark = (lum < 45) & (e < 0.85) & alpha
    n, lab, st, _ = cv2.connectedComponentsWithStats(dark.astype(np.uint8), connectivity=8)
    pup = lab == 1 + np.argmax(st[1:, 4])
    pup = cv2.morphologyEx(pup.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)).astype(bool)   # inclui o brilho branco
    pup = pup | (cv2.dilate(pup.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & (lum > 200))
    globo = (e < 1.0) & alpha
    iris = cv2.dilate(pup.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21))).astype(bool) & (e < 0.93)
    # esclera escondida atrás da íris: cor média por raio (perfil radial do globo), só com pixels de esclera
    rho = np.sqrt(e); escl = globo & ~iris & (lum > 120) & (e < 0.9)
    bins = np.clip((rho * 40).astype(int), 0, 39); perf = np.zeros((40, 3)); 
    tem = np.zeros(40, bool)
    for k in range(40):
        m = escl & (bins == k)
        if m.sum() > 20: perf[k] = A[m, :3].mean(0); tem[k] = True
    for c in range(3): perf[:, c] = np.interp(np.arange(40), np.nonzero(tem)[0], perf[tem, c])   # raios sem esclera visível: interpola
    return dict(e=e, pupila=pup, iris=iris, globo=globo, perfil=perf, bins=bins)
# ---------------- corpo atrás dos braços: fecha a silhueta (fechamento morfológico) e preenche por inpainting
def preencher_atras(rgba, buraco, raio=21):
    corpo = (rgba[..., 3] > 0) & ~buraco
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (raio, raio))
    fechado = cv2.morphologyEx(corpo.astype(np.uint8), cv2.MORPH_CLOSE, k).astype(bool)
    zona = buraco & fechado & (A[..., 3] == 255)    # sob bordas meio transparentes da peça não se pinta (senão a montagem muda)
    out = rgba.copy(); out[buraco, 3] = 0
    bgr = cv2.cvtColor(np.ascontiguousarray(rgba[..., :3]), cv2.COLOR_RGB2BGR)
    fonte = corpo & (rgba[..., 3] == 255)                          # só pele opaca serve de fonte (a borda clara não)
    pint = cv2.inpaint(bgr, (~fonte).astype(np.uint8) * 255, 9, cv2.INPAINT_TELEA)
    out[zona, :3] = cv2.cvtColor(pint, cv2.COLOR_BGR2RGB)[zona]; out[zona, 3] = 255
    # contorno escuro na borda nova da silhueta
    nova = zona & ~cv2.erode(fechado.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    out[nova, :3] = (43, 26, 20)
    return out
def gerar(OUT):
    cam = {}
    bE = mascara_peca(*POL['braco_E']) & (yy >= qy); bD = mascara_peca(*POL['braco_D']) & (yy >= qy)   # acima do queixo é cabeça
    cab = (yy < qy + 7) & ~bE & ~bD
    cab |= ((xx < 168) | (xx > 306)) & (yy < 482) & ~bE & ~bD & (yy < qy + 30)   # restos do contorno da cabeça dos lados do pescoço
    for o in OLHOS.values(): o.update(olho(o))
    # cabeça sem as íris (esclera preenchida) + íris/pupilas separadas
    cabeca = A.copy(); cabeca[~cab, 3] = 0
    for k, o in OLHOS.items():
        m = o['iris']
        # esclera escondida: continua as cores em volta (inpainting), olhando só para o globo do olho
        bgr = cv2.cvtColor(np.ascontiguousarray(A[..., :3]), cv2.COLOR_RGB2BGR)
        conhecido = o['globo'] & ~m & (lum > 140)                   # só esclera clara (sem contorno nem pupila)
        pint = cv2.inpaint(bgr, (~conhecido).astype(np.uint8) * 255, 15, cv2.INPAINT_TELEA)
        cabeca[m, :3] = cv2.cvtColor(pint, cv2.COLOR_BGR2RGB)[m]
        ir = np.zeros_like(A); ir[m] = A[m]; cam[f'iris_{k}'] = ir
    cam['cabeca'] = cabeca
    # braços e corpo (corpo = resto abaixo do queixo, com o lugar dos braços preenchido)
    for k, m in (('E', bE), ('D', bD)):
        b = np.zeros_like(A); b[m & ~cab] = A[m & ~cab]; cam[f'braco_{k}'] = b
    corpo = A.copy(); corpo[cab, 3] = 0
    corpo = preencher_atras(corpo, (bE | bD) & ~cab, raio=45)   # fecha a silhueta do tronco por trás do ombro
    # migalhas: pedacinhos soltos do corpo (franja de contorno de outras peças) vão para a peça mais próxima
    n, lab, st, _ = cv2.connectedComponentsWithStats((corpo[..., 3] > 0).astype(np.uint8), connectivity=8)
    mig = np.isin(lab, np.nonzero(st[:, 4] < 300)[0]) & (lab > 0)
    dE = cv2.distanceTransform((cam['braco_E'][..., 3] == 0).astype(np.uint8), cv2.DIST_L2, 3)
    dD = cv2.distanceTransform((cam['braco_D'][..., 3] == 0).astype(np.uint8), cv2.DIST_L2, 3)
    for k, sel in (('E', mig & (dE <= dD)), ('D', mig & (dD < dE))):
        sel = sel & (cam[f'braco_{k}'][..., 3] == 0); cam[f'braco_{k}'][sel] = corpo[sel]
    corpo[mig] = 0
    # franja clara (sobra do fundo branco da folha) e a ponta do ombro entre o braço e o tronco: vão com o braço,
    # senão ficam no tronco como risquinhos brancos quando o braço gira
    for k, m in (('E', bE), ('D', bD)):
        d = cv2.distanceTransform((cam[f'braco_{k}'][..., 3] == 0).astype(np.uint8), cv2.DIST_L2, 3)
        lado = (xx < 172) if k == 'E' else (xx > 300)
        sel = (corpo[..., 3] > 0) & (cam[f'braco_{k}'][..., 3] == 0) & (((d <= 6) & (corpo[..., 3] < 255) & (lum > 150)) | ((d <= 10) & lado & (yy < 500)))
        cam[f'braco_{k}'][sel] = corpo[sel]; corpo[sel] = 0
    # pedaços de contorno escuro que ficaram no corpo encostados no braço (o braço os cobria): vão com o braço
    escuro = (corpo[..., 3] > 0) & (corpo[..., :3].astype(int).sum(-1) < 3 * 90)
    n, lab, st, _ = cv2.connectedComponentsWithStats(escuro.astype(np.uint8), connectivity=8)
    for k in ('E', 'D'):
        d = cv2.distanceTransform((cam[f'braco_{k}'][..., 3] == 0).astype(np.uint8), cv2.DIST_L2, 3)
        perto = np.bincount(lab[(d <= 3) & escuro], minlength=n)
        for i in np.nonzero((perto > 0) & (st[:, 4] < 120))[0]:
            if i == 0: continue
            sel = (lab == i) & (cam[f'braco_{k}'][..., 3] == 0); cam[f'braco_{k}'][sel] = corpo[sel]; corpo[lab == i] = 0
    cam['corpo'] = corpo
    # pivôs (medidos na arte): ombros no alto de cada braço, onde ele encosta no tronco
    piv = {'cabeca': PIV_CABECA, 'braco_E': (160.0, 485.0), 'braco_D': (310.0, 485.0), 'cauda': (395.0, 770.0),
           'olhos': {k: dict(c=o['c'], r=o['r']) for k, o in OLHOS.items()}}
    os.makedirs(OUT, exist_ok=True)
    for k, v in cam.items(): Image.fromarray(v).save(os.path.join(OUT, k + '.png'))
    json.dump(dict(arte='character-model-sheet/assets/view-front.png', tamanho=[W, H], ordem=['corpo', 'braco_E', 'braco_D', 'cabeca', 'iris_E', 'iris_D'], pivos=piv), open(os.path.join(OUT, 'camadas.json'), 'w'), indent=1)
    # conferência: montadas em repouso, as camadas refazem a arte?
    mont = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    for k in ['corpo', 'braco_E', 'braco_D', 'cabeca', 'iris_E', 'iris_D']: mont.alpha_composite(Image.fromarray(cam[k]))
    # compara pré-multiplicado (num pixel quase transparente a cor não aparece; 1/255 de alpha muda o RGB guardado)
    pm = lambda X: np.concatenate([X[..., :3].astype(float) * X[..., 3:4] / 255.0, X[..., 3:4].astype(float)], -1)
    dif = np.abs(pm(np.array(mont)) - pm(A)); return cam, np.round(dif).astype(int)
if __name__ == '__main__':
    cam, dif = gerar(OUT)
    d = dif.max(-1); print('montagem x arte: dif máx', dif.max(), 'pixels diferentes', int((d > 0).sum()))
    if (d > 0).any(): ys, xs = np.nonzero(d); print('  onde', xs.min(), xs.max(), ys.min(), ys.max(), 'alpha', np.unique(A[d > 0, 3])[:10])
