"""Cauda nova: corrente de ossos que segue a espiral até a ponta, e pesos refeitos.

  blender --background <entrada.blend> --python cauda.py -- <saída.blend> <relatório.json>

Problema: os 10 ossos antigos acabavam antes do caracol da ponta (cerca de 0,3 m de malha sem osso),
então a cauda não esticava inteira.
Solução:
1. linha central da cauda: pontos médios da malha ao longo do comprimento (distância pela superfície,
   desde a base), refinada por projeção em 3 passadas;
2. N ossos de mesmo tamanho ao longo dessa linha, da base até a ponta (tail_01..tail_NN), com o eixo X
   de todos igual ao X do mundo: girar em X enrola ou desenrola a cauda no plano dela;
3. pesos: a parte da cauda de cada vértice (soma dos pesos antigos da cauda) vai para os 2 ossos
   vizinhos pela posição ao longo da linha. Pesos do corpo ficam como estão.
"""
import bpy, sys, json, math, heapq
import numpy as np
from mathutils import Vector

args = sys.argv[sys.argv.index('--') + 1:]; SAIDA, REL = args[0], args[1]
SEG = 0.075                       # tamanho de cada osso novo (m)
rig = bpy.data.objects['Kumo_Rig']; corpo = bpy.data.objects['Kumo']
ANTIGOS = sorted(b.name for b in rig.data.bones if b.name.startswith('tail_'))
REP = {'ossos_antigos': len(ANTIGOS)}

def pesos_cauda(o):
    vg = {g.index: g.name for g in o.vertex_groups}
    return np.array([sum(g.weight for g in v.groups if vg.get(g.group, '').startswith('tail_')) for v in o.data.vertices])

# ---------------------------------------------------------------- 1. linha central
me = corpo.data; P = np.array([tuple(corpo.matrix_world @ v.co) for v in me.vertices]); F = pesos_cauda(corpo)
T = set(np.nonzero(F > 0.01)[0].tolist())
viz = {i: [] for i in T}
for e in me.edges:
    a, b = e.vertices
    if a in T and b in T:
        d = float(np.linalg.norm(P[a] - P[b])); viz[a].append((b, d)); viz[b].append((a, d))
base = [i for i in T if F[i] < 0.5]                      # onde a cauda ainda divide peso com o quadril
dist = {i: 0.0 for i in base}; fila = [(0.0, i) for i in base]; heapq.heapify(fila)
while fila:
    d, i = heapq.heappop(fila)
    if d > dist.get(i, 1e9): continue
    for j, w in viz[i]:
        if d + w < dist.get(j, 1e9): dist[j] = d + w; heapq.heappush(fila, (d + w, j))
idx = np.array(sorted(dist)); g = np.array([dist[i] for i in idx]); Q = P[idx]
raiz = Vector(rig.matrix_world @ rig.data.bones['tail_01'].head_local)
PONTA = Q[int(np.argmax(g))]

def linha(param, passo=0.02):
    cs = [np.array(raiz)]
    for k in range(1, int(param.max() / passo) + 1):
        sel = (param >= (k - 0.5) * passo) & (param < (k + 0.5) * passo)
        if sel.sum() >= 3: cs.append(Q[sel].mean(0))
    cs.append(PONTA)                                      # a linha vai até a pontinha (o vértice mais longe da base)
    return np.array(cs)

def projeta(L, dica=None, janela=0.2):
    # ponto mais perto na linha; com dica (posição esperada ao longo da cauda), só vale um trecho perto dela:
    # no caracol as voltas ficam coladas e o ponto mais perto pode ser de outra volta
    seg = L[1:] - L[:-1]; ln = np.linalg.norm(seg, axis=1); acc = np.concatenate([[0], np.cumsum(ln)])
    best = np.full(len(Q), 1e9); s = np.zeros(len(Q))
    for k in range(len(seg)):
        t = np.clip(((Q - L[k]) @ seg[k]) / max(ln[k] ** 2, 1e-12), 0, 1)
        d = np.linalg.norm(Q - (L[k] + t[:, None] * seg[k]), axis=1)
        if dica is not None: d = d + 10.0 * (np.abs(acc[k] + t * ln[k] - dica) > janela)
        m = d < best; best[m] = d[m]; s[m] = acc[k] + t[m] * ln[k]
    return s, acc

def alisa(L, n=6):                                         # média móvel, sem mexer na raiz nem na ponta
    L = L.copy()
    for _ in range(n): L[1:-1] = (L[:-2] + 2 * L[1:-1] + L[2:]) / 4
    return L
def reamostra(L, passo=0.02):                              # pontos a cada 2 cm ao longo da linha
    ln = np.linalg.norm(L[1:] - L[:-1], axis=1); acc = np.concatenate([[0], np.cumsum(ln)])
    ts = np.arange(0, acc[-1], passo); out = []
    for t in ts:
        k = min(int(np.searchsorted(acc, t, side='right') - 1), len(L) - 2); u = (t - acc[k]) / max(ln[k], 1e-9); out.append(L[k] + u * (L[k + 1] - L[k]))
    out.append(L[-1]); return np.array(out)
L = reamostra(alisa(linha(g, 0.04)))
G2S = lambda gg: gg / g.max()                             # fração do caminho pela superfície: dica de onde o ponto fica
for _ in range(2):
    acc0 = np.concatenate([[0], np.cumsum(np.linalg.norm(L[1:] - L[:-1], axis=1))])
    s, acc = projeta(L, G2S(g) * acc0[-1]); L = reamostra(alisa(linha(s, 0.04)))
# ponta: no caracol fechado, alisar puxa a linha para o miolo da espiral e a malha fica longe dos ossos.
# Nos últimos 30 cm a linha passa pelo meio das fatias da própria malha (posição já achada), quase sem alisar.
acc0 = np.concatenate([[0], np.cumsum(np.linalg.norm(L[1:] - L[:-1], axis=1))])
s, acc = projeta(L, G2S(g) * acc0[-1]); corte = acc[-1] - 0.30
fat = [Q[(s >= t) & (s < t + 0.02)].mean(0) for t in np.arange(corte, acc[-1], 0.02) if ((s >= t) & (s < t + 0.02)).sum() >= 3]
L = reamostra(alisa(np.vstack([L[acc[:len(L)] < corte] if len(acc) == len(L) else L[:int(corte / 0.02)], fat, [PONTA]]), 1))
acc0 = np.concatenate([[0], np.cumsum(np.linalg.norm(L[1:] - L[:-1], axis=1))])
s, acc = projeta(L, G2S(g) * acc0[-1]); COMP = float(acc[-1])
S_KUMO = dict(zip(idx.tolist(), s.tolist()))               # posição ao longo da cauda de cada vértice do corpo
# ossos mais curtos para a ponta: o caracol fecha cada vez mais e um osso longo não acompanha a curva
EXPO = 1.7
f = lambda u: 1 - (1 - u) ** EXPO                          # fração do comprimento na junta u (0..1)
finv = lambda x: 1 - (1 - np.clip(x, 0, 1)) ** (1 / EXPO)
N = max(10, round(COMP / SEG * 1.25)); seg_len = COMP / N
junta = lambda i: COMP * f(i / N)                         # metros da base até a junta i
REP.update(comprimento_m=round(COMP, 3), ossos_novos=N, osso_base_m=round(junta(1), 3), osso_ponta_m=round(COMP - junta(N - 1), 3))

def ponto(t):                                             # ponto da linha a t metros da base
    k = int(np.searchsorted(acc, t, side='right') - 1); k = min(max(k, 0), len(L) - 2)
    u = (t - acc[k]) / max(acc[k + 1] - acc[k], 1e-9); return Vector(L[k] + u * (L[k + 1] - L[k]))

# ---------------------------------------------------------------- 2. ossos novos
bpy.context.view_layer.objects.active = rig; rig.hide_set(False); rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT'); E = rig.data.edit_bones
pai = E['tail_01'].parent
for n in ANTIGOS: E.remove(E[n])
NOVOS = ['tail_%02d' % (i + 1) for i in range(N)]
X = Vector((1, 0, 0)); ant = pai
for i, n in enumerate(NOVOS):
    b = E.new(n); b.head = rig.matrix_world.inverted() @ ponto(junta(i)); b.tail = rig.matrix_world.inverted() @ ponto(junta(i + 1))
    y = (b.tail - b.head).normalized(); z = X.cross(y).normalized(); b.align_roll(z)
    b.parent = ant; b.use_connect = i > 0; b.use_deform = True; ant = b
bpy.ops.object.mode_set(mode='OBJECT')
for n in NOVOS: rig.pose.bones[n].rotation_mode = 'QUATERNION'

# ---------------------------------------------------------------- 3. pesos
def repesar(o, sv=None):
    F = pesos_cauda(o)
    for n in ANTIGOS:
        if n in o.vertex_groups: o.vertex_groups.remove(o.vertex_groups[n])
    G = {n: o.vertex_groups.get(n) or o.vertex_groups.new(name=n) for n in NOVOS}
    Pw = np.array([tuple(o.matrix_world @ v.co) for v in o.data.vertices])
    sel = np.nonzero(F > 1e-4)[0]
    if not len(sel): return 0
    if o == corpo: sp = np.array([S_KUMO.get(int(i), 0.0) for i in sel])
    else:                                                  # outra malha (contorno): a posição do vértice do corpo mais perto
        from mathutils.kdtree import KDTree
        kd = KDTree(len(idx))
        for j, i in enumerate(idx): kd.insert(Vector(P[i]), j)
        kd.balance(); sp = np.array([s[kd.find(Vector(Pw[i]))[1]] for i in sel])
    c = finv(sp / COMP) * N - 0.5                              # posição em "ossos", centro do osso i em i
    for j, vi in enumerate(sel):
        k = int(math.floor(c[j])); u = c[j] - k
        if k < 0: par = [(0, 1.0)]
        elif k >= N - 1: par = [(N - 1, 1.0)]
        else: par = [(k, 1 - u), (k + 1, u)]
        for b, w in par:
            if w > 1e-4: G[NOVOS[b]].add([int(vi)], float(F[vi] * w), 'REPLACE')
    return len(sel)

for o in [x for x in bpy.data.objects if x.type == 'MESH' and any(g.name.startswith('tail_') for g in x.vertex_groups)]:
    REP['repesados_' + o.name] = repesar(o)

# ações: chaves dos ossos antigos da cauda não servem mais
def canais(a):                                           # Blender 5: ações em camadas (layers → strips → channelbags)
    for ly in a.layers:
        for st in ly.strips:
            for cb in st.channelbags: yield cb
for a in bpy.data.actions:
    for cb in canais(a):
        for fc in [f for f in cb.fcurves if 'pose.bones["tail_' in f.data_path]: cb.fcurves.remove(fc)

# ---------------------------------------------------------------- conferência: esticar a cauda inteira
pb = rig.pose.bones; D = (ponto(COMP) - ponto(0)).normalized()
D = Vector((0, 1, -0.25)).normalized()                       # reta: para trás, descendo um pouco
for n in NOVOS:
    p = pb[n]; bpy.context.view_layer.update()
    cur = (rig.matrix_world.to_3x3() @ p.matrix.to_3x3()).col[1].normalized()
    q = cur.rotation_difference(D)
    R = rig.matrix_world.to_3x3().inverted() @ q.to_matrix() @ rig.matrix_world.to_3x3()
    M = p.matrix.copy(); M3 = R @ M.to_3x3(); Mn = M3.to_4x4(); Mn.translation = M.translation; p.matrix = Mn
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get(); ev = corpo.evaluated_get(dg); m = ev.to_mesh()
Pe = np.array([tuple(ev.matrix_world @ v.co) for v in m.vertices]); ev.to_mesh_clear()
ti = np.array(sorted(T)); r0 = np.array(ponto(0)); dd = np.array(D)
ao_longo = (Pe[ti] - r0) @ dd; lateral = np.linalg.norm((Pe[ti] - r0) - ao_longo[:, None] * dd, axis=1)
perto = ao_longo > COMP - 0.3
REP['esticada_ponta_desvio_medio_m'] = round(float(lateral[perto].mean()), 3)
REP['esticada'] = dict(alcance_m=round(float(ao_longo.max()), 3), comprimento_linha_m=round(COMP, 3),
                       desvio_lateral_max_m=round(float(lateral[ao_longo > 0.15].max()), 3))
for n in NOVOS: pb[n].rotation_quaternion = (1, 0, 0, 0)
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=SAIDA)
json.dump(REP, open(REL, 'w'), indent=1, ensure_ascii=False)
print('CAUDA', json.dumps(REP, ensure_ascii=False))
