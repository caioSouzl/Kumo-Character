"""Suaviza a transição de pesos ombro↔braço (não muda o repouso: pesos só agem com o braço girado).
Por vértice, mantém a soma (ombro + braço) e espalha a fração do braço pelos vizinhos. Mede os cruzamentos sem corretivas.
  python pesos_ombro.py <blend>         (env PASSOS="0,4,8,16")"""
import bpy, sys, os, math, json
import numpy as np
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'corrigir_ombros.py')).read().split("if not me.shape_keys")[0].replace("SRC, OUT = sys.argv[-2:]; os.makedirs(OUT, exist_ok=True)", "SRC = sys.argv[-1]"))
VG = {g.name: g for g in body.vertex_groups}
ORIG = {i: list(W[i]) for i in range(NV)}
def aplica(sd, passos, lam=0.5):
    a, b = f'shoulder.{sd}', f'upper_arm.{sd}'
    soma = np.zeros(NV); fr = np.zeros(NV)
    for i in range(NV):
        d = dict(ORIG[i]); s = d.get(a, 0) + d.get(b, 0); soma[i] = s; fr[i] = d.get(b, 0) / s if s > 1e-6 else 0
    ativo = [i for i in range(NV) if soma[i] > 0.05]
    viz = {i: [j for j in adj[i] if soma[j] > 0.05] for i in ativo}
    for _ in range(passos):
        nf = fr.copy()
        for i in ativo:
            if viz[i]: nf[i] = (1 - lam) * fr[i] + lam * np.mean(fr[viz[i]])
        fr = nf
    for i in ativo:
        VG[a].add([i], float(soma[i] * (1 - fr[i])), 'REPLACE'); VG[b].add([i], float(soma[i] * fr[i]), 'REPLACE')
        d = dict(ORIG[i]); d[a] = soma[i] * (1 - fr[i]); d[b] = soma[i] * fr[i]; W[i] = [(n, w) for n, w in d.items() if w > 1e-5]
POSES = [('erguer', 90), ('erguer', 120), ('erguer', 135), ('erguer', 150), ('frente', 60), ('frente', 90), ('frente', -30)]
def mede(sd):
    fs, vs = regiao(sd); reset(); V0, T0 = geo(fs); r0 = pares(V0, T0); out = {}
    for tipo, ang in POSES:
        reset(); mover(sd, tipo, ang); V, T = geo(fs); P = pares(V, T) - r0
        out[f'{tipo}{ang}'] = sum(1 for p in P if prof(V, T, p) >= 0.0005)
    reset(); return out
if __name__ == '__main__' and 'PESOS_SO_FUNCOES' not in os.environ:
    for passos in [int(x) for x in os.environ.get('PASSOS', '0,4,8,16').split(',')]:
        for sd in 'LR': aplica(sd, passos)
        print('PW', passos, {sd: mede(sd) for sd in 'LR'}, flush=True)
