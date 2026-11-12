"""Ombros: shape keys corretivas ligadas ao giro do braço (repouso intacto). Mesmo resolvedor da mão e das pálpebras:
afasta os triângulos que se cruzam, cada um para o lado em que já está, com transição suave, e devolve ao repouso
pela inversa da pele. Os drivers leem a rotação local do osso `upper_arm` (quatérnio), projetada no eixo do movimento.

  python corrigir_ombros.py <kumo_v6_olhos_jogo.blend> <saída>
"""
import bpy, sys, os, json, math
import numpy as np
from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree
SRC, OUT = sys.argv[-2:]; os.makedirs(OUT, exist_ok=True)
K = float(os.environ.get('OMBRO_K', '0'))
KF = float(os.environ.get('OMBRO_KF', str(K)))     # fração do ombro quando o braço vai à frente (protração)
KT = {'erguer': K, 'frente': KF}
bpy.ops.wm.open_mainfile(filepath=SRC); sc = bpy.context.scene
rig = bpy.data.objects['Kumo_Rig']; body = bpy.data.objects['Kumo']; me = body.data; pb = rig.pose.bones
if rig.animation_data: rig.animation_data.action = None
# ponto de giro do ombro mais alto (sugestão do Caio): só o esqueleto muda; a malha em repouso é a mesma
OMBRO_Z = os.environ.get('OMBRO_Z')
if OMBRO_Z:
    for o in bpy.context.selected_objects: o.select_set(False)
    rig.hide_set(False); rig.select_set(True); bpy.context.view_layer.objects.active = rig; bpy.ops.object.mode_set(mode='EDIT')
    for sd_ in 'LR':
        eb = rig.data.edit_bones[f'upper_arm.{sd_}']; inv = rig.matrix_world.inverted(); hw = rig.matrix_world @ eb.head
        hw.z = float(OMBRO_Z); eb.head = inv @ hw
        rig.data.edit_bones[f'shoulder.{sd_}'].tail = eb.head
    bpy.ops.object.mode_set(mode='OBJECT')
OUTL = [m for m in body.modifiers if m.type != 'ARMATURE']
for m in OUTL: m.show_viewport = False
gi = {g.index: g.name for g in body.vertex_groups}; BN = {b.name for b in rig.data.bones if b.use_deform}
W = [[(gi[g.group], g.weight) for g in v.groups if gi[g.group] in BN and g.weight > 1e-5] for v in me.vertices]
NV = len(me.vertices); adj = [[] for _ in range(NV)]
for e in me.edges: a, b = e.vertices; adj[a].append(b); adj[b].append(a)
def dom(i): return max(W[i], key=lambda x: x[1])[0] if W[i] else None
def regiao(sd):
    ok = {f'shoulder.{sd}', f'upper_arm.{sd}', 'chest', 'spine', 'neck', f'forearm.{sd}'}
    vs = {i for i in range(NV) if dom(i) in ok}; return {p.index for p in me.polygons if all(i in vs for i in p.vertices)}, vs
def geo(fs):
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get(); ev = body.evaluated_get(dg); m = ev.to_mesh(); m.calc_loop_triangles()
    V = [ev.matrix_world @ v.co for v in m.vertices]; T = [tuple(t.vertices) for t in m.loop_triangles if t.polygon_index in fs]; ev.to_mesh_clear(); return V, T
def pares(V, T):
    t = BVHTree.FromPolygons(V, T); return {(a, b) for a, b in t.overlap(t) if a < b and not (set(T[a]) & set(T[b]))}
def prof(V, T, p):
    out = []
    for x, y in (p, p[::-1]):
        a0, a1, a2 = (V[i] for i in T[x]); n = (a1 - a0).cross(a2 - a0)
        if n.length < 1e-12: return 0
        n.normalize(); ds = [n.dot(V[i] - a0) for i in T[y]]; out.append(min(max(0, max(ds)), max(0, -min(ds))))
    return min(out)
def reset():
    for b in pb: b.rotation_quaternion = (1, 0, 0, 0); b.rotation_euler = (0, 0, 0); b.location = (0, 0, 0)
    bpy.context.view_layer.update()
def rotw(n, axis, deg):
    b = pb[n]; bpy.context.view_layer.update(); M = b.matrix.copy(); h = M.to_translation()
    b.matrix = Matrix.Translation(h) @ Matrix.Rotation(math.radians(deg), 4, axis.normalized()) @ Matrix.Translation(-h) @ M; bpy.context.view_layer.update()
REST_DIR = {n: (rig.data.bones[n].tail_local - rig.data.bones[n].head_local).normalized() for n in ('upper_arm.L', 'upper_arm.R')}
EIXO = {}                                         # eixos de mundo de cada movimento, fixos no repouso
for sd in 'LR':
    d = REST_DIR[f'upper_arm.{sd}']; EIXO[(sd, 'erguer')] = d.cross(Vector((0, 0, 1))).normalized(); EIXO[(sd, 'frente')] = d.cross(Vector((0, -1, 0))).normalized()
def mover(sd, tipo, deg):
    ax = EIXO[(sd, tipo)]; s_ = max(0.0, abs(deg) - 30) * KT[tipo] * (1 if deg > 0 else -1)
    if s_: rotw(f'shoulder.{sd}', ax, s_)
    rotw(f'upper_arm.{sd}', ax, deg - s_)
# eixo local do osso do braço para cada movimento (para o driver)
EIXO_LOCAL = {}
for sd in 'LR':
    b = rig.data.bones[f'upper_arm.{sd}']; Ml = (rig.matrix_world @ b.matrix_local).to_3x3().inverted()
    for tipo in ('erguer', 'frente'): EIXO_LOCAL[(sd, tipo)] = (Ml @ EIXO[(sd, tipo)]).normalized()
# base dual: os eixos de erguer e de ir à frente não são perpendiculares no osso do lado R; com a base dual,
# um movimento puro de erguer dá 0 no medidor de frente (e vice-versa) — sem isso a chave de frente ligava ao erguer
DUAL = {}
for sd in 'LR':
    e, f = EIXO_LOCAL[(sd, 'erguer')], EIXO_LOCAL[(sd, 'frente')]; n = e.cross(f).normalized()
    Mx = Matrix((e, f, n)).inverted()           # linhas e,f,n -> colunas da inversa = vetores duais
    DUAL[(sd, 'erguer')] = Vector(Mx.col[0]); DUAL[(sd, 'frente')] = Vector(Mx.col[1])
    print('EIXOS', sd, 'cos(erguer,frente)=', round(e.dot(f), 3), flush=True)
def angulo_local(sd, tipo):
    q = pb[f'upper_arm.{sd}'].rotation_quaternion; a = EIXO_LOCAL[(sd, tipo)]
    return 2 * math.atan2(q.x * a.x + q.y * a.y + q.z * a.z, q.w)
# ---- transição de pesos ombro↔braço mais suave (repouso intacto: peso só age com o osso girado)
VG = {g.name: g for g in body.vertex_groups}
def suavizar_pesos(sd, passos, lam=0.5, par=None):
    a, b = par or (f'shoulder.{sd}', f'upper_arm.{sd}'); soma = np.zeros(NV); fr = np.zeros(NV)
    for i in range(NV):
        d = dict(W[i]); s = d.get(a, 0) + d.get(b, 0); soma[i] = s; fr[i] = d.get(b, 0) / s if s > 1e-6 else 0
    ativo = [i for i in range(NV) if soma[i] > 0.05]; viz = {i: [j for j in adj[i] if soma[j] > 0.05] for i in ativo}
    for _ in range(passos):
        nf = fr.copy()
        for i in ativo:
            if viz[i]: nf[i] = (1 - lam) * fr[i] + lam * np.mean(fr[viz[i]])
        fr = nf
    for i in ativo:
        VG[a].add([i], float(soma[i] * (1 - fr[i])), 'REPLACE'); VG[b].add([i], float(soma[i] * fr[i]), 'REPLACE')
        d = dict(W[i]); d[a] = soma[i] * (1 - fr[i]); d[b] = soma[i] * fr[i]; W[i] = [(n, w) for n, w in d.items() if w > 1e-5]
SUAVE = int(os.environ.get('OMBRO_SUAVE', '0'))
if SUAVE:
    for sd in 'LR': suavizar_pesos(sd, SUAVE)
# regra de jogo: no máximo 4 ossos por vértice, pesos somando 1 (o GLB descarta o 5º em diante)
def limitar_4():
    n = 0
    for i in range(NV):
        if len(W[i]) <= 4 and abs(sum(w for _, w in W[i]) - 1) < 1e-4: continue
        top = sorted(W[i], key=lambda x: -x[1])[:4]; sm = sum(w for _, w in top)
        for nm, w in W[i]:
            if nm not in dict(top): VG[nm].remove([i])
        W[i] = [(nm, w / sm) for nm, w in top]
        for nm, w in W[i]: VG[nm].add([i], w, 'REPLACE')
        n += 1
    return n
PEITO = int(os.environ.get('OMBRO_SUAVE_PEITO', '0'))      # também peito↔ombro
if PEITO:
    for sd in 'LR': suavizar_pesos(sd, PEITO, par=('chest', f'shoulder.{sd}'))
if SUAVE or PEITO: print('LIMITE4 vértices ajustados', limitar_4(), flush=True)
if not me.shape_keys: body.shape_key_add(name='Basis', from_mix=False)
KB = me.shape_keys.key_blocks
def resolver(sd, pose_fn, key, ativas, iters=70, margem=0.0005):
    fs, vs = regiao(sd); reset(); V0, T0 = geo(fs); r0 = pares(V0, T0); hist = []
    melhor = None
    for it in range(iters):
        reset(); pose_fn()
        for k_, v_ in ativas: k_.value = v_
        key.value = 1.0; V, T = geo(fs); P = pares(V, T) - r0
        ds = {p: prof(V, T, p) for p in P}; hist.append((len(P), sum(1 for d in ds.values() if d >= 0.0005), round(max(ds.values(), default=0) * 1000, 1)))
        nota = (hist[-1][1], hist[-1][2])
        if melhor is None or nota < melhor[0]: melhor = (nota, [tuple(k.co) for k in key.data], it)
        if not P or it - melhor[2] >= 15: break
        disp = np.zeros((NV, 3)); cnt = np.zeros(NV)
        for (a, b), d in ds.items():
            for x, y in ((a, b), (b, a)):
                q0, q1, q2 = (V[i] for i in T[y]); n = (q1 - q0).cross(q2 - q0)
                if n.length < 1e-12: continue
                n.normalize(); cx = sum((V[i] for i in T[x]), Vector()) / 3; sg = 1.0 if n.dot(cx - q0) >= 0 else -1.0
                for i in T[x]: disp[i] += np.array(tuple(n * sg * (d / 2 + margem))); cnt[i] += 1
        m_ = cnt > 0; disp[m_] /= cnt[m_, None]
        for _ in range(3):
            nx = disp.copy()
            for i in vs:
                if adj[i] and not m_[i]: nx[i] = 0.5 * disp[adj[i]].mean(0)
            disp = nx
        Mb = {b.name: (pb[b.name].matrix @ b.matrix_local.inverted()).to_3x3() for b in rig.data.bones}
        for i in np.nonzero(np.linalg.norm(disp, axis=1) > 1e-7)[0]:
            dv = Vector(disp[i].tolist())
            if dv.length > 0.002: dv = dv.normalized() * 0.002
            Mv = sum((Mb[n] * w for n, w in W[i]), Matrix.Diagonal((0, 0, 0)))
            try: key.data[i].co += Mv.inverted() @ dv
            except ValueError: pass
    # fica com a melhor iteração (nunca entrega uma correção que piora)
    for kd_, co in zip(key.data, melhor[1]): kd_.co = co
    reset()
    for k_, _ in ativas: k_.value = 0.0
    key.value = 0.0
    return dict(iteracoes=len(hist), inicio=hist[0], melhor=hist[melhor[2]], melhor_iteracao=melhor[2])
def driver(key, sd, tipo, a, b, c):
    """peso em chapéu: 0 em a, 1 em b, 0 em c (c=None: fica 1 depois de b). Ângulos em graus."""
    fc = key.driver_add('value'); d = fc.driver; d.type = 'SCRIPTED'
    for comp in ('W', 'X', 'Y', 'Z'):
        v = d.variables.new(); v.name = comp.lower(); v.type = 'TRANSFORMS'; t = v.targets[0]; t.id = rig; t.bone_target = f'upper_arm.{sd}'
        t.transform_type = f'ROT_{comp}'; t.transform_space = 'LOCAL_SPACE'; t.rotation_mode = 'QUATERNION'
    ax = DUAL[(sd, tipo)]
    ang = f'(2*atan2(x*{ax.x:.5f}+y*{ax.y:.5f}+z*{ax.z:.5f}, w)*57.29578)'
    up = f'({ang}-{a})/({b}-{a})'; dn = f'({c}-{ang})/({c}-{b})' if c else '1.0'
    d.expression = f'max(0.0, min({up}, {dn}, 1.0))'
REP = {'ombro_z': OMBRO_Z, 'ombro_automatico_k': K, 'ombro_automatico_k_frente': KF, 'suavizacao_pesos_passos': SUAVE, 'suavizacao_peito_passos': PEITO}
CHAVES = {}
for sd in 'LR':
    k90 = body.shape_key_add(name=f'Ombro_Erguer90.{sd}', from_mix=False)
    REP[f'erguer90_{sd}'] = resolver(sd, lambda: mover(sd, 'erguer', 90), k90, [])
    k120 = body.shape_key_add(name=f'Ombro_Erguer120.{sd}', from_mix=False)
    REP[f'erguer120_{sd}'] = resolver(sd, lambda: mover(sd, 'erguer', 120), k120, [])
    k150 = body.shape_key_add(name=f'Ombro_Erguer150.{sd}', from_mix=False)
    REP[f'erguer150_{sd}'] = resolver(sd, lambda: mover(sd, 'erguer', 150), k150, [])
    kf = body.shape_key_add(name=f'Ombro_Frente90.{sd}', from_mix=False)
    REP[f'frente90_{sd}'] = resolver(sd, lambda: mover(sd, 'frente', 90), kf, [])
    CHAVES[sd] = (k90, k120, k150, kf)
    print('OC', sd, {k: v for k, v in REP.items() if k.endswith(sd)}, flush=True)
# os drivers medem a rotação do próprio osso do braço (com ombro automático, o braço gira (1-K) do total acima de 30°)
def efetivo(deg, k=K): return deg - max(0.0, deg - 30) * k
for sd, (k90, k120, k150, kf) in CHAVES.items():
    driver(k90, sd, 'erguer', efetivo(45), efetivo(90), efetivo(120)); driver(k120, sd, 'erguer', efetivo(90), efetivo(120), efetivo(150))
    driver(k150, sd, 'erguer', efetivo(120), efetivo(150), None); driver(kf, sd, "frente", efetivo(40, KF), efetivo(90, KF), None)
# testes com drivers (inclui ângulos intermediários)
TEST = {**{f'erguer_{a}': ('erguer', a) for a in (45, 60, 75, 90, 105, 120, 135, 150)}, **{f'frente_{a}': ('frente', a) for a in (45, 60, 75, 90)}, 'tras_30': ('frente', -30)}
for sd in 'LR':
    fs, vs = regiao(sd); reset(); V0, T0 = geo(fs); r0 = pares(V0, T0); out = {}
    for nm, (tipo, a) in TEST.items():
        reset(); mover(sd, tipo, a); V, T = geo(fs); P = pares(V, T) - r0; ds = [prof(V, T, p) for p in P]
        out[nm] = dict(reais=sum(1 for d in ds if d >= 0.0005), prof_max_mm=round(max(ds, default=0) * 1000, 1),
                       chaves={k.name.split('.')[0]: round(k.value, 2) for k in CHAVES[sd]})
        print('OT', sd, nm, out[nm], flush=True)
    REP['testes_' + sd] = out
reset()
for m in OUTL: m.show_viewport = True
json.dump(REP, open(os.path.join(OUT, 'medicoes_ombros.json'), 'w'), indent=1, default=str)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'kumo_v6_ombros.blend'), copy=True, relative_remap=False)
print('OC OK')
