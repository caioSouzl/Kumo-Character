"""Kumo v6 · shape keys corretivas da mão fechada (autorizadas pelo Caio em 2026-11-11).

  python corretivas.py <kumo_maos_dedos.blend> <pasta de saída>

Lê a cópia dos braços originais com dedos (nunca grava por cima). Para cada lado:
  1. pose da mão fechada (dedos a 70°); acha os pares de triângulos que se cruzam (método de sempre);
  2. empurra os vértices dos dois triângulos para dentro da própria superfície (normal), com transição suave nos vizinhos,
     até não restar cruzamento; repete (a deformação por ossos é linear, então o deslocamento volta exato para o repouso);
  3. grava o deslocamento como shape key (no espaço de repouso) ligada por driver ao fechamento dos três dedos.
Opcional (CR_POLEGAR='s,c1,c2'): segunda key para o polegar dobrado sobre o dedo 1.
"""
import bpy, sys, os, json, math, time
import numpy as np
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kumo_lib import Kumo, smooth01
SRC, OUT = sys.argv[-2], sys.argv[-1]; os.makedirs(os.path.join(OUT, 'renders'), exist_ok=True)
FAST = bool(os.environ.get('CR_FAST'))
POL = tuple(int(x) for x in os.environ['CR_POLEGAR'].split(',')) if os.environ.get('CR_POLEGAR') else None
MARGEM = float(os.environ.get('CR_MARGEM', '0.0004'))
bpy.ops.wm.open_mainfile(filepath=SRC)
REPO = os.path.abspath(os.path.join(os.path.dirname(SRC), '..', '..'))
img = bpy.data.images.get('kumo_quad_diffuse')
if img: img.filepath = os.path.join(REPO, 'textures', 'kumo_quad_diffuse.png'); img.reload()
sc = bpy.context.scene; rig = bpy.data.objects['Kumo_Rig']; body = bpy.data.objects['Kumo']; me = body.data
REP = dict(margem_mm=MARGEM * 1000, polegar=POL, matriz_rig_identidade=rig.matrix_world == Matrix(), matriz_corpo_identidade=body.matrix_world == Matrix())
OUTL = [m for m in body.modifiers if m.type != 'ARMATURE']
def outline(on):
    for m in OUTL: m.show_viewport = on
    bpy.context.view_layer.update()
outline(False)
K = Kumo(rig, body); pb = rig.pose.bones
NV = len(me.vertices)
adj = [[] for _ in range(NV)]
for e in me.edges: a, b = e.vertices; adj[a].append(b); adj[b].append(a)
# pesos (para a matriz de deformação de cada vértice)
gi = {g.index: g.name for g in body.vertex_groups}
W = [[(gi[g.group], g.weight) for g in v.groups if gi[g.group] in K.BONES and g.weight > 1e-5] for v in me.vertices]
def skin3(vs):
    M = {b.name: (pb[b.name].matrix @ b.matrix_local.inverted()).to_3x3() for b in rig.data.bones}
    return {i: sum((M[n] * w for n, w in W[i]), Matrix.Diagonal((0, 0, 0))) for i in vs}
if not me.shape_keys: body.shape_key_add(name='Basis', from_mix=False)
KB = me.shape_keys.key_blocks

def resolver(sd, pose_fn, key, ativas, iters=40):
    fs, vs = K.regiao(sd); K.reset(); V0, T0, _ = K.tri_data(fs, vs); rest = K.self_pairs(V0, T0)
    hist = []
    for it in range(iters):
        K.reset(); pose_fn()
        for k_ in ativas: k_.value = 1.0
        key.value = 1.0; bpy.context.view_layer.update()
        V, T, _ = K.tri_data(fs, vs); new = list(K.self_pairs(V, T) - rest)
        ds = [K.depth(V, T, p) for p in new]
        hist.append(dict(normais_invertidas=locals().get('flips', 0), pares=len(new), reais=sum(1 for d in ds if d >= 0.0005), prof_max_mm=round(max(ds) * 1000, 2) if ds else 0))
        if not new: break
        _, N = K.avaliar()
        push = np.zeros(NV)
        for (a, b), d in zip(new, ds):
            for t in (a, b):
                for i in T[t]: push[i] = max(push[i], d / 2 + MARGEM)
        # transição suave: 3 anéis de vizinhos (fica o maior entre o próprio e 60% da média dos vizinhos)
        reg = sorted(vs)
        for _ in range(3):
            nxt = push.copy()
            for i in reg:
                if adj[i]: nxt[i] = max(push[i], 0.6 * sum(push[j] for j in adj[i]) / len(adj[i]))
            push = nxt
        mv = [i for i in reg if push[i] > 1e-7]; Ms = skin3(mv)
        flips = 0
        for i in mv:
            # orienta a normal para fora a partir do eixo do osso dominante (as normais da mão direita podem vir invertidas)
            dom = max(W[i], key=lambda x: x[1])[0]; h_, t_ = pb[dom].head, pb[dom].tail
            vv = Vector(V[i]); ab = t_ - h_; tt = max(0.0, min(1.0, (vv - h_).dot(ab) / ab.length_squared)); out_ = vv - (h_ + ab * tt)
            n_ = Vector(N[i])
            if n_.dot(out_) < 0: n_ = -n_; flips += 1
            dp = -n_ * min(push[i], 0.003)
            try: dr = Ms[i].inverted() @ dp
            except ValueError: continue
            key.data[i].co += dr
    K.reset(); pose_fn()
    for k_ in ativas: k_.value = 1.0
    key.value = 1.0; Von, _ = K.avaliar(); key.value = 0.0; Voff, _ = K.avaliar()
    desl_pose = float(np.max(np.linalg.norm(Von - Voff, axis=1)))
    K.reset()
    for k_ in ativas: k_.value = 0.0
    desl = [(key.data[i].co - KB['Basis'].data[i].co).length for i in range(NV)]
    return dict(deslocamento_na_pose_max_mm=round(desl_pose * 1000, 2), iteracoes=len(hist), historico=hist, vertices_movidos=sum(1 for x in desl if x > 1e-6), deslocamento_max_mm=round(max(desl) * 1000, 2))

# ----- driver: ângulo de fechamento (rotação local em X do primeiro segmento de cada dedo)
def angulo_x(n): return pb[n].matrix_basis.to_euler('XYZ').x
K.reset(); K.poses('L')['mao_fechada'](); SINAL = 1 if angulo_x('dedo2_1.L') > 0 else -1
REP['angulo_dedo2_fechada_70_graus'] = round(math.degrees(angulo_x('dedo2_1.L')), 2); K.reset()
def driver(key, sd, polegar=False):
    fc = key.driver_add('value'); d = fc.driver; d.type = 'SCRIPTED'
    for k in (1, 2, 3):
        v = d.variables.new(); v.name = f'a{k}'; v.type = 'TRANSFORMS'; t = v.targets[0]
        t.id = rig; t.bone_target = f'dedo{k}_1.{sd}'; t.transform_type = 'ROT_X'; t.transform_space = 'LOCAL_SPACE'; t.rotation_mode = 'XYZ'
    s = '' if SINAL > 0 else '-'
    expr = f'smoothstep(0.70, 1.20, {s}(a1+a2+a3)/3)'
    if polegar:
        v = d.variables.new(); v.name = 'p'; v.type = 'TRANSFORMS'; t = v.targets[0]
        t.id = rig; t.bone_target = f'polegar_1.{sd}'; t.transform_type = 'ROT_X'; t.transform_space = 'LOCAL_SPACE'; t.rotation_mode = 'XYZ'
        expr = f'smoothstep(0.70, 1.20, {s}(a1+a2+a3)/3) * smoothstep(0.35, 0.9, abs(p))'
    d.expression = expr
    return expr

KEYS = {}
for sd in ('L', 'R'):
    k1 = body.shape_key_add(name=f'Corretiva_MaoFechada.{sd}', from_mix=False); k1.slider_max = 1
    REP[f'resolver_maofechada_{sd}'] = resolver(sd, K.poses(sd)['mao_fechada'], k1, [])
    KEYS[sd] = [k1]
    if POL:
        k2 = body.shape_key_add(name=f'Corretiva_PolegarSobre.{sd}', from_mix=False); k2.slider_max = 1
        REP[f'resolver_polegar_{sd}'] = resolver(sd, K.poses(sd, polegar_sobre=POL)['mao_fechada_polegar_sobre'], k2, [k1], iters=60)
        KEYS[sd].append(k2)
    print('CR', sd, {k: (v['iteracoes'], v['historico'][0], v['historico'][-1], v['deslocamento_max_mm'], v['deslocamento_na_pose_max_mm'], v['vertices_movidos']) for k, v in REP.items() if k.startswith('resolver') and k.endswith(sd)}, flush=True)
for sd in ('L', 'R'):
    REP[f'driver_{sd}'] = [driver(KEYS[sd][0], sd)] + ([driver(KEYS[sd][1], sd, True)] if POL else [])

# ----- testes com os drivers ligados (todas as poses do relatório anterior)
def valores(sd): return {k.name: round(k.value, 3) for k in KEYS[sd]}
for sd in ('L', 'R'):
    fs, vs = K.regiao(sd); K.reset(); V0, T0, E0 = K.tri_data(fs, vs); rest = K.self_pairs(V0, T0); L0 = [(V0[a] - V0[b]).length for a, b in E0]
    out = dict(repouso=dict(pares=len(rest), **K.classify(V0, T0, rest), keys=valores(sd)))
    for pname, fn in K.poses(sd, polegar_sobre=POL).items():
        K.reset(); fn(); bpy.context.view_layer.update(); V, T, E_ = K.tri_data(fs, vs); new = K.self_pairs(V, T) - rest
        ratio = sorted((V[a] - V[b]).length / l for (a, b), l in zip(E_, L0) if l > 1e-7)
        out[pname] = dict(pares_novos=len(new), **K.classify(V, T, new), compressao_min=round(ratio[0], 3), esticamento_max=round(ratio[-1], 3), keys=valores(sd))
        print('T', sd, pname, out[pname], flush=True)
    REP['testes_' + ('E' if sd == 'L' else 'D')] = out
K.reset()
pbf = pb['forearm.L']; t0 = time.perf_counter()
for i in range(40):
    pbf.rotation_euler = (math.radians(i), 0, 0); pb['dedo1_1.L'].rotation_euler = (math.radians(i * 1.5), 0, 0)
    bpy.context.view_layer.update(); bpy.context.evaluated_depsgraph_get()
REP['desempenho_ms'] = round((time.perf_counter() - t0) / 40 * 1000, 2); K.reset()
for b in pb: b.rotation_euler = (0, 0, 0)
json.dump(REP, open(os.path.join(OUT, 'medicoes.json'), 'w'), indent=1, default=str)
if FAST: print('CR FAST OK'); raise SystemExit

# ----- renders: mão fechada sem e com a corretiva (com textura e contorno)
outline(True)
sc.render.engine = 'CYCLES'; sc.cycles.samples = int(os.environ.get('CR_SAMPLES', '16')); sc.render.resolution_x = sc.render.resolution_y = 480
def cam(n, d, t, s_):
    c = bpy.data.objects.new(n, bpy.data.cameras.new(n)); sc.collection.objects.link(c); c.data.type = 'ORTHO'; c.data.ortho_scale = s_
    d = Vector(d).normalized(); c.location = Vector(t) + d * 5; c.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler(); return c
REND = {}
for sd in ('L', 'R'):
    m = K.MAOS[sd]; sx = 1 if sd == 'L' else -1
    for nome, pose in (('mao_fechada', 'mao_fechada'), ('fechar_50', 'fechar_50')):
        K.reset(); K.poses(sd)[pose](); bpy.context.view_layer.update()
        hc = (pb[f'hand.{sd}'].head + pb[f'dedo2_1.{sd}'].tail) / 2
        Q = pb[f'hand.{sd}'].matrix.to_3x3() @ rig.data.bones[f'hand.{sd}'].matrix_local.to_3x3().inverted()
        C = {'frente': cam(f'f{sd}{nome}', (0, -1, 0), hc, 0.36), 'dorso': cam(f'd{sd}{nome}', -(Q @ m['pn']), hc, 0.36),
             'palma': cam(f'p{sd}{nome}', (Q @ m['pn']), hc, 0.36), 'perspectiva': cam(f'q{sd}{nome}', (0.4 * sx, -1, 0.25), hc, 0.36)}
        for estado in ('sem', 'com'):
            KEYS[sd][0].mute = estado == 'sem'; bpy.context.view_layer.update()
            for k, c in C.items():
                sc.camera = c; f = os.path.join(OUT, 'renders', f'{sd}_{nome}_{estado}_{k}.png'); sc.render.filepath = f
                bpy.ops.render.render(write_still=True); REND[(sd, nome, estado, k)] = f
        KEYS[sd][0].mute = False
K.reset()
for o in [o for o in bpy.data.objects if o.type == 'CAMERA']: bpy.data.objects.remove(o)
json.dump({'|'.join(k): v for k, v in REND.items()}, open(os.path.join(OUT, 'renders', 'indice.json'), 'w'), indent=0)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'kumo_maos_corretivas.blend'), copy=True, relative_remap=False)
print('CR OK')
