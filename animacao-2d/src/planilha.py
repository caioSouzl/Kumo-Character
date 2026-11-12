"""Planilha de tempo (dope sheet) para o Kumo 2D, e um conferidor das regras de tempo da pesquisa.

Canal: lista de chaves (quadro, valor, curva). Curvas: 'lin', 'sai' (desacelera), 'entra' (acelera), 'suave' (os dois),
'passa' (passa do ponto e volta: overshoot), 'segura' (fica no valor até a próxima chave).

Regras conferidas (fontes em estudos-animacao/02-TEMPO.md):
  piscada: normal fecha 2–3, fechado 0–2, abre 2–4; longa 3 · 2 · 4 (±1); abrir não é mais rápido que fechar (24 qps)
  piscada junto de virada de cabeça (±2 quadros)
  os olhos chegam antes da cabeça: o olhar começa 1–3 quadros antes do giro
  olhada rápida (dart): 2–4 quadros
  preparação do pulo: 2–8 quadros; pico do achatamento na queda: até 2 quadros depois do contato
  loop: último quadro igual ao primeiro
"""
import math
import numpy as np
CURVAS = {
    'lin': lambda u: u,
    'sai': lambda u: 1 - (1 - u) ** 2,
    'entra': lambda u: u * u,
    'suave': lambda u: u * u * (3 - 2 * u),
    'passa': lambda u: 1 + 2.70158 * (u - 1) ** 3 + 1.70158 * (u - 1) ** 2,   # "back out": passa ~10% e volta
    'segura': lambda u: 0.0,
}
class Canal:
    def __init__(self, chaves, nome=''):
        self.k = sorted(chaves, key=lambda c: c[0]); self.nome = nome
    def __call__(self, f):
        k = self.k
        if f <= k[0][0]: return k[0][1]
        if f >= k[-1][0]: return k[-1][1]
        for (f0, v0, _), (f1, v1, c) in zip(k, k[1:]):
            if f0 <= f <= f1:
                u = (f - f0) / max(1e-9, f1 - f0); return v0 + (v1 - v0) * CURVAS[c](u)
def amostrar(fn, n):
    return np.array([fn(f) for f in range(n)])
# ---------------- conferência
def eventos_piscada(fecha, lim_alto=0.95, lim_baixo=0.05):
    """de uma curva fecha(quadro) acha cada piscada: quadros fechando, fechados, abrindo"""
    ev = []; f = 0; n = len(fecha)
    while f < n:
        if fecha[f] > lim_baixo:
            a = f
            while f < n and fecha[f] < lim_alto and fecha[f] > lim_baixo: f += 1
            b = f
            while f < n and fecha[f] >= lim_alto: f += 1
            c = f
            while f < n and fecha[f] > lim_baixo: f += 1
            ev.append(dict(inicio=a, fechando=b - a + 1, fechado=c - b, abrindo=f - c + 1 if c < n else 0, completa=c > b))
        f += 1
    return ev
def inicios(curva, lim=0.15):
    """quadros onde um canal começa a se mover (sai do repouso) depois de parado"""
    v = np.abs(np.diff(curva)); mov = v > lim * max(v.max(), 1e-9)
    return [i for i in range(1, len(mov)) if mov[i] and not mov[i - 1]] + ([0] if mov[0] else [])
def conferir(c, fps=24):
    """c: dict de curvas amostradas (np.array por quadro): fecha, cabeca (só os giros de intenção, sem o arrasto/sobreposição),
    olhar_x (opcional), sy, dy (altura, negativo = sobe)"""
    R = []
    def regra(nome, ok, detalhe): R.append((nome, bool(ok), detalhe))
    pis = eventos_piscada(c['fecha'])
    for i, e in enumerate(pis):
        # (quadros contados com o limite 95%: o último quadro de fechar já conta como fechado)
        normal = 2 <= e['fechando'] <= 3 and 0 <= e['fechado'] <= 2 and 2 <= e['abrindo'] <= 4
        longa = 3 <= e['fechando'] <= 4 and 2 <= e['fechado'] <= 3 and 4 <= e['abrindo'] <= 5          # Bloop: longa 3 · 2 · 4
        ok = (normal or longa) and e['abrindo'] >= e['fechando'] and e['completa']
        regra(f'piscada {i + 1} (quadro {e["inicio"]})', ok, f"fecha {e['fechando']} · fechado {e['fechado']} · abre {e['abrindo']}" + ('' if e['completa'] else ' · não fecha de todo'))
    giros = inicios(c['cabeca'])
    for g in giros:
        perto = [e for e in pis if abs(e['inicio'] - g) <= 2]
        regra(f'piscada na virada da cabeça (quadro {g})', perto, 'sim' if perto else 'nenhuma piscada a ±2 quadros')
    if 'olhar_x' in c:
        olh = inicios(c['olhar_x'])
        for g in giros:
            antes = [o for o in olh if 1 <= g - o <= 3]
            regra(f'olhos antes da cabeça (giro no quadro {g})', antes, f'olhar começou {g - antes[0]} quadro(s) antes' if antes else 'o olhar não lidera')
        # duração das olhadas: quadros entre começar e parar
        mv = np.abs(np.diff(c['olhar_x'])) > 1e-3
        segs = []; i = 0
        while i < len(mv):
            if mv[i]:
                j = i
                while j < len(mv) and mv[j]: j += 1
                segs.append((i, j - i)); i = j
            else: i += 1
        for s0, d in segs: regra(f'olhada no quadro {s0}', 2 <= d <= 4, f'{d} quadros')
    else:
        regra('olhos antes da cabeça', False, 'esta animação não tem olhar separado da cabeça')
    if 'dy' in c and (c['dy'] < -1).any():
        ar = np.nonzero(c['dy'] < -0.5)[0]; dec, pou = ar[0], ar[-1] + 1
        prep = [f for f in range(max(0, dec - 12), dec) if c['sy'][f] < 0.985]
        regra('preparação antes do pulo', 2 <= len(prep) <= 8, f'{len(prep)} quadros agachando')
        apos = c['sy'][pou:pou + 10]; pico = int(np.argmin(apos)) if len(apos) else 99
        regra('achatamento na queda', pico <= 2, f'pico {pico} quadro(s) depois do contato ({apos.min():.3f})')
    # loop: do último quadro para o primeiro o salto não pode ser maior que o passo normal entre quadros
    ruins = [k for k in c if abs(c[k][-1] - c[k][0]) > 1.5 * np.abs(np.diff(c[k])).max() + 1e-6]
    regra('loop (o último emenda no primeiro)', not ruins, 'salto em: ' + ', '.join(ruins) if ruins else 'emenda sem salto')
    return R
def tabela(R):
    return '\n'.join(f"{'✔' if ok else '✘'} {n}: {d}" for n, ok, d in R)
def grafico(curvas, saida, titulo='', fps=24):
    """desenha a planilha: uma faixa por canal, réguas de quadro e de segundo"""
    from PIL import Image, ImageDraw
    n = len(next(iter(curvas.values()))); px = 9; L = 150; fx = 24; h = 64
    W = L + n * px + 20; H = 40 + len(curvas) * (h + 10) + 20
    from PIL import ImageFont
    try: fn = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 12)   # fonte com acentos
    except OSError: fn = None
    im = Image.new('RGB', (W, H), 'white'); d = ImageDraw.Draw(im); d.text((10, 10), titulo, fill='black', font=fn)
    for f in range(n + 1):
        x = L + f * px; d.line([(x, 34), (x, H - 14)], fill=(235, 235, 235) if f % fx else (150, 150, 150))
        if f % fx == 0: d.text((x + 2, H - 15), f'{f // fx}s', fill='gray', font=fn)
    for i, (nome, v) in enumerate(curvas.items()):
        y0 = 40 + i * (h + 10); v = np.asarray(v, float); lo, hi = v.min(), v.max(); rg = hi - lo if hi > lo else 1
        d.text((8, y0 + h / 2 - 7), nome, fill='black', font=fn); d.rectangle([L, y0, L + n * px, y0 + h], outline=(200, 200, 200))
        pts = [(L + f * px + px / 2, y0 + h - 4 - (v[f] - lo) / rg * (h - 8)) for f in range(n)]
        d.line(pts, fill=(30, 110, 60), width=2)
        for p in pts: d.ellipse([p[0] - 1.5, p[1] - 1.5, p[0] + 1.5, p[1] + 1.5], fill=(30, 110, 60))   # um ponto por quadro: espaçamento à vista
    im.save(saida)
