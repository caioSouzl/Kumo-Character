"""Kumo v6 · Protótipo P1: braço esquerdo + mão com 3 dedos e polegar (malha nova, rig e testes).

  python p1_braco_mao.py <kumo_rigged.blend> <pasta p1>

Lê o modelo oficial SOMENTE para medir a forma do braço; grava apenas p1/p1_braco_mao.blend e evidências.
Regras v6: deformação só por ossos; no máximo 4 influências por vértice, soma 1.
"""
import bpy, bmesh, sys, os, json, math, time
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

SRC, OUT = sys.argv[-2], sys.argv[-1]
os.makedirs(os.path.join(OUT, 'renders'), exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=SRC)
REPO = os.path.dirname(os.path.abspath(SRC))
img = bpy.data.images['kumo_quad_diffuse']; img.filepath = os.path.join(REPO, 'textures', 'kumo_quad_diffuse.png'); img.reload()
sc = bpy.context.scene; rig0 = bpy.data.objects['Kumo_Rig']; body = bpy.data.objects['Kumo']; me = body.data
B = rig0.data.bones
REP = {}

# ------------------------------------------------------------------ 1. região do braço atual (só leitura)
vg = {g.index: g.name for g in body.vertex_groups}
ARM = {'upper_arm.L', 'forearm.L', 'hand.L'}
def dom(v):
    ws = [(vg[g.group], g.weight) for g in v.groups if vg[g.group] not in ('outline_cut', 'outline_shell')]
    return max(ws, key=lambda x: x[1])[0] if ws else None
arm_v = {v.index for v in me.vertices if dom(v) in ARM}
arm_f = [p for p in me.polygons if all(i in arm_v for i in p.vertices)]
armbvh = BVHTree.FromPolygons([v.co for v in me.vertices], [list(p.vertices) for p in arm_f])
armpts = [me.vertices[i].co.copy() for i in arm_v]
REP['braco_atual'] = dict(vertices=len(arm_v), faces=len(arm_f))

# linha central: fatias perpendiculares ao caminho dos ossos -> centróide dos vértices do braço
ua, fa = B['upper_arm.L'], B['forearm.L']
path = [ua.head_local.copy(), ua.tail_local.copy(), fa.tail_local.copy()]
def along(s):
    L = [(path[1] - path[0]).length, (path[2] - path[1]).length]; d = s * sum(L)
    if d <= L[0]: return path[0].lerp(path[1], d / L[0]), (path[1] - path[0]).normalized()
    return path[1].lerp(path[2], (d - L[0]) / L[1]), (path[2] - path[1]).normalized()
centers = []
for k in range(0, 41):
    s = 0.12 + (1.0 - 0.12) * k / 40; c, d = along(s)
    sl = [p for p in armpts if abs((p - c).dot(d)) < 0.012]
    if len(sl) >= 6:
        cc = sum(sl, Vector()) / len(sl); cc = cc - d * (cc - c).dot(d); centers.append(cc)
# suaviza
cs = [centers[0]] + [(centers[i - 1] + centers[i] * 2 + centers[i + 1]) / 4 for i in range(1, len(centers) - 1)] + [centers[-1]]
seg = [0.0]
for i in range(1, len(cs)): seg.append(seg[-1] + (cs[i] - cs[i - 1]).length)
def cpos(t):           # t em metros ao longo da linha central
    t = max(0, min(seg[-1], t))
    for i in range(1, len(seg)):
        if t <= seg[i]:
            f = (t - seg[i - 1]) / max(seg[i] - seg[i - 1], 1e-9); return cs[i - 1].lerp(cs[i], f), (cs[i] - cs[i - 1]).normalized()
    return cs[-1], (cs[-1] - cs[-2]).normalized()
def proj_t(p):
    best = (1e9, 0)
    for i in range(1, len(cs)):
        a, b = cs[i - 1], cs[i]; ab = b - a; f = max(0, min(1, (p - a).dot(ab) / ab.length_squared))
        dd = (a + ab * f - p).length
        if dd < best[0]: best = (dd, seg[i - 1] + f * ab.length)
    return best[1]
t_elbow = proj_t(fa.head_local); t_wrist = proj_t(fa.tail_local); t_end = seg[-1]
def radius_at(t):
    c, d = cpos(t); u = d.orthogonal().normalized(); w = d.cross(u); rs = []
    for j in range(12):
        a = 2 * math.pi * j / 12; dv = u * math.cos(a) + w * math.sin(a)
        loc, n, i, dist = armbvh.ray_cast(c, dv, 0.2)
        if loc: rs.append(dist)
    rs.sort(); return rs[len(rs) // 2] if rs else None
REP['linha_central'] = dict(pontos=len(cs), comprimento=round(seg[-1], 4), t_cotovelo=round(t_elbow, 4), t_punho=round(t_wrist, 4))

# ------------------------------------------------------------------ 2. malha por modelagem em caixa (bmesh), sem modificador Skin
# Iteração 3: a iteração 2 (Skin) tinha 657 pares de autointerseção já em repouso na palma e nos dedos.
# Agora: anéis octogonais (8 vértices) ajustados por raio à superfície do braço atual; a ponta da palma fecha com
# 3 quads, e cada quad é extrudado como um dedo (3 dedos); o polegar sai da face frontal da palma.
arm_t = sorted(set([round(x, 4) for x in
    [i * 0.025 for i in range(int(t_elbow / 0.025) - 1)] +
    [t_elbow - 0.045, t_elbow - 0.022, t_elbow, t_elbow + 0.022, t_elbow + 0.045] +
    [t_elbow + 0.045 + (t_wrist - 0.045 - t_elbow - 0.045) * k / 4 for k in range(1, 4)] +
    [t_wrist - 0.045, t_wrist - 0.022, t_wrist]]))
arm_t = [t for i, t in enumerate(arm_t) if i == 0 or t - arm_t[i - 1] > 0.012]
cW, dW = cpos(t_wrist)
down = dW
side = Vector((-1, 0, 0)); side = (side - down * side.dot(down)).normalized()   # palma voltada para o corpo
fwd = down.cross(side).normalized()
if fwd.y > 0: fwd = -fwd
# octógono: ordem T0..T3 (lado +) e B3..B0 (lado −); f = componente frente, s = componente lateral
OCT = [(-0.924, 0.383), (-0.383, 0.924), (0.383, 0.924), (0.924, 0.383), (0.924, -0.383), (0.383, -0.924), (-0.383, -0.924), (-0.924, -0.383)]
bm = bmesh.new()
def frame(d):
    sd = (side - d * side.dot(d)).normalized(); fw = d.cross(sd).normalized()
    if fw.dot(fwd) < 0: fw = -fw
    return fw, sd
def quad(vs): return bm.faces.new(vs)
rings = []
# seção de cada anel = função de suporte (casco convexo) da fatia de vértices do braço atual -> seção sempre convexa,
# centro recalculado pela própria fatia (a linha central por centróide caía fora do braço no cotovelo: raio 0 na iteração anterior)
REP['raios_aneis'] = []
c0a = cpos(0.0)[0]; cEa = cpos(t_elbow)[0]; uD = (cEa - c0a).normalized(); fD = (cW - cEa).normalized()
for t in arm_t:
    c, _ = cpos(t); wgt = max(0.0, min(1.0, (t - (t_elbow - 0.06)) / 0.12)); wgt = wgt * wgt * (3 - 2 * wgt)
    d = (uD * (1 - wgt) + fD * wgt).normalized(); fw, sd = frame(d)       # direção dos anéis em leque contínuo no cotovelo
    sl = [p - d * (p - c).dot(d) for p in armpts if abs((p - c).dot(d)) < 0.010]
    sl = [q for q in sl if (q - c).length < 0.16]
    if len(sl) >= 8: c = sum(sl, Vector()) / len(sl)
    ring = []; rr = []
    for f, s_ in OCT:
        dv = (fw * f + sd * s_).normalized()
        r = max([(q - c).dot(dv) for q in sl] + [0.02])
        rr.append(r); ring.append(bm.verts.new(c + dv * r))
    REP['raios_aneis'].append([round(x, 3) for x in rr])
    rings.append(ring)
cen = [sum((v.co for v in rg), Vector()) / 8 for rg in rings]
for it in range(2):        # suaviza posições entre anéis vizinhos (a pele atual é ondulada)
    new = []
    for i in range(len(rings)):
        a_, b_ = max(i - 1, 0), min(i + 1, len(rings) - 1)
        new.append([(rings[a_][j].co + rings[i][j].co * 2 + rings[b_][j].co) / 4 for j in range(8)])
    for i in range(1, len(rings) - 1):
        for j in range(8): rings[i][j].co = new[i][j]
PALM_L = 0.055
PALM_A = [0.016, 0.036, PALM_L]
for k, a_ in enumerate(PALM_A):
    c = cW + down * a_; rf = 0.066 + 0.006 * k; rs = 0.036
    rings.append([bm.verts.new(c + fwd * f * rf + side * s_ * rs) for f, s_ in OCT])
for r0, r1 in zip(rings, rings[1:]):
    for j in range(8): quad([r0[j], r0[(j + 1) % 8], r1[(j + 1) % 8], r1[j]])
r0 = rings[0]
for q in ((0, 1, 6, 7), (1, 2, 5, 6), (2, 3, 4, 5)): quad([r0[i] for i in q])
end = rings[-1]
CAPS = [(end[0], end[1], end[6], end[7]), (end[1], end[2], end[5], end[6]), (end[2], end[3], end[4], end[5])]
def tube(loop, path, widths, axA, axB):
    """extruda um laço de 4 vértices ao longo de path (centros); widths=(wa, wb) por anel; fecha a ponta."""
    c0 = sum((v.co for v in loop), Vector()) / 4
    sig = [((v.co - c0).dot(axA) > 0, (v.co - c0).dot(axB) > 0) for v in loop]
    prev = list(loop)
    for i, (c, (wa, wb)) in enumerate(zip(path, widths)):
        d = (path[i] - (path[i - 1] if i else c0)).normalized()
        A = (axA - d * axA.dot(d)).normalized(); Bv = (axB - d * axB.dot(d) - A * axB.dot(A)).normalized()
        cur = [bm.verts.new(c + A * (wa / 2 if sa else -wa / 2) + Bv * (wb / 2 if sb else -wb / 2)) for sa, sb in sig]
        for j in range(4): quad([prev[j], prev[(j + 1) % 4], cur[(j + 1) % 4], cur[j]])
        prev = cur
    quad(prev)
FINGC = []
for k, cap in enumerate(CAPS):
    c0 = sum((v.co for v in cap), Vector()) / 4
    spread = fwd * (k - 1) * 0.006
    D = [0.009, 0.022, 0.031, 0.040, 0.053, 0.061]
    path = [c0 + down * dd + spread * (dd / 0.05) + side * 0.10 * dd for dd in D]
    W = [(0.040, 0.040), (0.037, 0.038), (0.037, 0.038), (0.036, 0.037), (0.032, 0.033), (0.020, 0.021)]
    tube(cap, path, W, fwd, side)
    FINGC.append((c0, path[2], path[-1]))
# polegar: face frontal entre os dois primeiros anéis da palma
pa, pb = rings[-3], rings[-2]
tf = [f for f in bm.faces if set(f.verts) == {pa[3], pa[4], pb[3], pb[4]}][0]
tloop = [pa[3], pb[3], pb[4], pa[4]]; bm.faces.remove(tf)
c0 = sum((v.co for v in tloop), Vector()) / 4
dt = (fwd * 0.75 + down * 0.65 + side * 0.15).normalized()
D = [0.010, 0.021, 0.029, 0.037, 0.047, 0.053]
tpath = [c0 + fwd * 0.004 + dt * dd for dd in D]
tube(tloop, tpath, [(0.018, 0.034), (0.028, 0.036), (0.032, 0.036), (0.032, 0.035), (0.028, 0.031), (0.018, 0.019)], down, side)
TPATH = tpath; TDIR = dt
THC = (c0, tpath[2], tpath[-1])
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
nm = bpy.data.meshes.new('P1_Braco_E'); bm.to_mesh(nm); bm.free()
arm = bpy.data.objects.new('P1_Braco_E', nm); sc.collection.objects.link(arm)
sub = arm.modifiers.new('Sub', 'SUBSURF'); sub.levels = 1
dg = bpy.context.evaluated_depsgraph_get(); ev = arm.evaluated_get(dg)
nm2 = bpy.data.meshes.new_from_object(ev, depsgraph=dg); arm.modifiers.remove(sub); arm.data = nm2; nm = nm2

# ------------------------------------------------------------------ 3. reajuste à superfície do braço atual (só antes do punho)
bm = bmesh.new(); bm.from_mesh(nm); bm.verts.ensure_lookup_table()
fit = 0
for v in bm.verts:
    if True: continue      # iteração 3: reajuste desligado; reprojetar vértices subdivididos amassava a superfície (979 pares)
    t = proj_t(v.co)
    if t < 0.002: continue
    c, d = cpos(t); rd = v.co - c; rd -= d * rd.dot(d)
    if rd.length < 1e-6: continue
    loc, n, i, dist = armbvh.ray_cast(c, rd.normalized(), 0.2)
    if loc:
        v.co = loc + rd.normalized() * 0.0005; fit += 1
bm.to_mesh(nm); bm.free(); nm.update()
REP['malha_nova'] = dict(vertices=len(nm.vertices), faces=len(nm.polygons), quads=sum(1 for p in nm.polygons if len(p.vertices) == 4),
                        tris=sum(1 for p in nm.polygons if len(p.vertices) == 3), ngons=sum(1 for p in nm.polygons if len(p.vertices) > 4),
                        vertices_ajustados_ao_braco_atual=fit)

# ------------------------------------------------------------------ 4. rig P1
arm_rig_data = bpy.data.armatures.new('P1_Rig'); rigo = bpy.data.objects.new('P1_Rig', arm_rig_data); sc.collection.objects.link(rigo)
bpy.context.view_layer.objects.active = rigo
for o in bpy.context.selected_objects: o.select_set(False)
rigo.select_set(True); bpy.ops.object.mode_set(mode='EDIT')
E = arm_rig_data.edit_bones
def eb(name, h, t, parent=None, roll_to=None):
    b = E.new(name); b.head = h; b.tail = t
    if parent: b.parent = E[parent]; b.use_connect = (E[parent].tail - h).length < 1e-5
    if roll_to is not None: b.align_roll(roll_to)
    return b
c0, _ = cpos(0.0); cE, _ = cpos(t_elbow)
eb('DEF-braco.L', c0, cE, roll_to=-side)
eb('DEF-antebraco.L', cE, cW, 'DEF-braco.L', roll_to=-side)
eb('DEF-mao.L', cW, cW + down * PALM_L, 'DEF-antebraco.L', roll_to=-side)
for k, (b0, j, tip) in enumerate(FINGC):
    eb(f'DEF-dedo{k+1}_1.L', b0 - down * 0.006, j, 'DEF-mao.L', roll_to=-side)
    eb(f'DEF-dedo{k+1}_2.L', j, tip + (tip - j).normalized() * 0.006, f'DEF-dedo{k+1}_1.L', roll_to=-side)
b0, j, tip = THC
eb('DEF-polegar_1.L', b0 - (j - b0).normalized() * 0.008, j, 'DEF-mao.L', roll_to=-side)
eb('DEF-polegar_2.L', j, tip + (tip - j).normalized() * 0.006, 'DEF-polegar_1.L', roll_to=-side)
bpy.ops.object.mode_set(mode='OBJECT')
# pesos procedurais (iteração 3): transições suaves e explícitas nos 3 anéis de cada articulação, em vez de pesos por calor
for o in bpy.context.selected_objects: o.select_set(False)
arm.select_set(True); rigo.select_set(True); bpy.context.view_layer.objects.active = rigo
bpy.ops.object.parent_set(type='ARMATURE_NAME')
def ss(x, a, b):
    x = max(0.0, min(1.0, (x - a) / (b - a))); return x * x * (3 - 2 * x)
sE = (cEa - c0a).length; sW = sE + (cW - cEa).length
def arm_s(p):
    q1 = max(0.0, min(sE, (p - c0a).dot(uD))); q2 = max(0.0, (p - cEa).dot(fD))
    d1 = (c0a + uD * q1 - p).length; d2 = (cEa + fD * min(q2, sW - sE) - p).length
    if (p - cW).dot(down) > 0: return sW + (p - cW).dot(down)
    return q1 if d1 < d2 else sE + q2
G = {b.name: arm.vertex_groups[b.name] for b in arm_rig_data.bones}; EH = {}
for v in arm.data.vertices:
    p = v.co; w = {}
    a = (p - cW).dot(down); th0 = TPATH[0] - TDIR * 0.010
    ut = (p - th0).dot(TDIR)
    dthumb = min((p - q).length for q in TPATH); dpalm = (p - (cW + down * max(0, min(PALM_L, a)))).length
    if a > -0.005 and ut > 0.0 and dthumb < dpalm and dthumb < 0.03:
        jt = (THC[1] - th0).dot(TDIR); h = 1 - ss(ut, 0.004, 0.016); x = ss(ut, jt - 0.008, jt + 0.008)
        w = {'DEF-mao.L': h, 'DEF-polegar_1.L': (1 - h) * (1 - x), 'DEF-polegar_2.L': (1 - h) * x}
    elif a > PALM_L - 0.006:
        k = min(range(3), key=lambda i: abs((p - FINGC[i][0]).dot(fwd)))
        b0, jj, tip = FINGC[k]; u = (p - b0).dot(down); jk = (jj - b0).dot(down)
        h = 1 - ss(u, -0.004, 0.010); x = ss(u, jk - 0.008, jk + 0.008)
        w = {'DEF-mao.L': h, f'DEF-dedo{k+1}_1.L': (1 - h) * (1 - x), f'DEF-dedo{k+1}_2.L': (1 - h) * x}
    else:
        s_ = arm_s(p); EH[v.index] = [ss(s_, sE - 0.035, sE + 0.035), ss(s_, sW - 0.030, sW + 0.010)]; continue
    for n_, x_ in w.items():
        if x_ > 1e-4: G[n_].add([v.index], x_, 'REPLACE')
# suaviza as transições do braço sobre as arestas (a projeção no segmento mais próximo salta na parte interna do cotovelo)
nb = {i: [] for i in EH}
for e_ in arm.data.edges:
    a_, b_ = e_.vertices
    if a_ in EH and b_ in EH: nb[a_].append(b_); nb[b_].append(a_)
for it in range(12):
    EH = {i: [(EH[i][c] + sum(EH[j][c] for j in nb[i]) / max(len(nb[i]), 1)) / 2 if nb[i] else EH[i][c] for c in (0, 1)] for i in EH}
for i, (e, hh) in EH.items():
    for n_, x_ in (('DEF-braco.L', 1 - e), ('DEF-antebraco.L', e * (1 - hh)), ('DEF-mao.L', e * hh)):
        if x_ > 1e-4: G[n_].add([i], x_, 'REPLACE')
bpy.context.view_layer.objects.active = arm
for o in bpy.context.selected_objects: o.select_set(False)
arm.select_set(True)
bpy.ops.object.vertex_group_limit_total(limit=4)
bpy.ops.object.vertex_group_normalize_all(lock_active=False)
def weight_stats(o):
    infl = []; sums = []
    for v in o.data.vertices:
        ws = [g.weight for g in v.groups if g.weight > 1e-4]; infl.append(len(ws)); sums.append(sum(ws))
    return dict(max_influencias=max(infl), sem_peso=sum(1 for x in infl if x == 0), soma_fora_de_1=sum(1 for s in sums if abs(s - 1) > 0.01))
REP['pesos_novos'] = weight_stats(arm)
REP['ossos_novos'] = [b.name for b in arm_rig_data.bones]

# material de prova: verde médio da paleta da referência, facetas planas
mat = bpy.data.materials.new('P1_Verde'); mat.use_nodes = True; nt = mat.node_tree
for n in list(nt.nodes):
    if n.type != 'OUTPUT_MATERIAL': nt.nodes.remove(n)
emi = nt.nodes.new('ShaderNodeEmission'); emi.inputs['Color'].default_value = (0x4C / 255) ** 2.2, (0xAF / 255) ** 2.2, (0x6B / 255) ** 2.2, 1
nt.links.new(emi.outputs[0], nt.nodes['Material Output'].inputs['Surface'])
arm.data.materials.append(mat)
for p in arm.data.polygons: p.use_smooth = True
arm.modifiers.new('Contorno', 'SOLIDIFY')  # placeholder removido abaixo (contorno só no render de comparação)
arm.modifiers.remove(arm.modifiers['Contorno'])

# ------------------------------------------------------------------ 5. testes: mesmas medidas da auditoria, braço atual × novo
def tri_data(obj, region=None):
    dg = bpy.context.evaluated_depsgraph_get(); ev = obj.evaluated_get(dg); m = ev.to_mesh(); m.calc_loop_triangles()
    V = [ev.matrix_world @ v.co for v in m.vertices]
    T = [tuple(t.vertices) for t in m.loop_triangles if region is None or t.polygon_index in region]
    E_ = [(e.vertices[0], e.vertices[1]) for e in m.edges if region is None or (e.vertices[0] in region_v and e.vertices[1] in region_v)]
    ev.to_mesh_clear(); return V, T, E_
def self_pairs(V, T):
    b = BVHTree.FromPolygons(V, T); out = set()
    for a_, b_ in b.overlap(b):
        if a_ < b_ and not (set(T[a_]) & set(T[b_])): out.add((a_, b_))
    return out
region = {p.index for p in arm_f}; region_v = set(arm_v)
OUTL = [m for m in body.modifiers if m.type in ('SOLIDIFY', 'VERTEX_WEIGHT_MIX', 'MASK')]
for m in OUTL: m.show_viewport = False
bpy.context.view_layer.update()
def measure(obj, reg=None):
    V, T, E_ = tri_data(obj, reg); return V, T, E_
V0o, T0o, E0o = measure(body, region); rest_o = self_pairs(V0o, T0o); L0o = [(V0o[a] - V0o[b]).length for a, b in E0o]
V0n, T0n, E0n = measure(arm); rest_n = self_pairs(V0n, T0n); L0n = [(V0n[a] - V0n[b]).length for a, b in E0n]
REP['autointersecao_em_repouso'] = dict(atual_regiao_braco=len(rest_o), novo=len(rest_n))

def reset(r):
    for pb in r.pose.bones:
        pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()
def rot_world(r, name, axis, deg):
    pb = r.pose.bones[name]; bpy.context.view_layer.update(); M = pb.matrix.copy(); h = M.to_translation()
    pb.matrix = Matrix.Translation(h) @ Matrix.Rotation(math.radians(deg), 4, Vector(axis).normalized()) @ Matrix.Translation(-h) @ M
    bpy.context.view_layer.update()
def bend_axis(r, name):     # dobra para a frente (−Y), como na auditoria
    pb = r.pose.bones[name]; d = (pb.tail - pb.head).normalized(); return d.cross(Vector((0, -1, 0))).normalized()
def curl_axis(r, name):     # fecha o dedo em direção à palma
    pb = r.pose.bones[name]; d = (pb.tail - pb.head).normalized(); return d.cross(side).normalized()
MAP_OLD = {'braco': 'upper_arm.L', 'antebraco': 'forearm.L', 'mao': 'hand.L'}
MAP_NEW = {'braco': 'DEF-braco.L', 'antebraco': 'DEF-antebraco.L', 'mao': 'DEF-mao.L'}
POSES = {
    'braco_horizontal': [('braco', (0, 1, 0), -45)],
    'braco_para_frente_90': [('braco', (1, 0, 0), -90)],
    'cotovelo_90': [('antebraco', 'BEND', 90)], 'cotovelo_130': [('antebraco', 'BEND', 130)],
    'punho_45': [('mao', 'BEND', 45)], 'punho_menos45': [('mao', 'BEND', -45)],
    'mao_fechada': 'FIST', 'mao_aberta_abduzida': 'SPREAD',
}
res = {}
for pname, steps in POSES.items():
    row = {}
    for tag, r, obj, V0, T0, E0, L0, rest, MAP in (('atual', rig0, body, V0o, T0o, E0o, L0o, rest_o, MAP_OLD), ('novo', rigo, arm, V0n, T0n, E0n, L0n, rest_n, MAP_NEW)):
        reset(r)
        if steps == 'FIST':
            if tag == 'atual': row[tag] = dict(nao_suportado='o rig atual não tem ossos de dedo'); continue
            for nm_ in [b.name for b in rigo.data.bones if 'dedo' in b.name or 'polegar' in b.name]:
                rot_world(r, nm_, curl_axis(r, nm_), 75 if 'polegar' not in nm_ else 40)
        elif steps == 'SPREAD':
            if tag == 'atual': row[tag] = dict(nao_suportado='o rig atual não tem ossos de dedo'); continue
            for k, a in ((1, -14), (3, 14)):
                rot_world(r, f'DEF-dedo{k}_1.L', side, a)
            rot_world(r, 'DEF-polegar_1.L', side, -25)
        else:
            for b, ax, deg in steps:
                bn = MAP[b]; axis = bend_axis(r, bn) if ax == 'BEND' else ax
                rot_world(r, bn, axis, deg)
        V, T, E_ = measure(obj, region if tag == 'atual' else None)
        new = self_pairs(V, T) - rest
        ratio = sorted((V[a] - V[b]).length / l0 for (a, b), l0 in zip(E_, L0) if l0 > 1e-7)
        row[tag] = dict(pares_novos=len(new), pares_total=len(self_pairs(V, T)), compressao_min=round(ratio[0], 3), compressao_p01=round(ratio[int(len(ratio) * 0.01)], 3),
                        esticamento_max=round(ratio[-1], 3))
    res[pname] = row
    # evidência visual: pose atual e nova lado a lado
    for tag, r, obj in (('atual', rig0, body), ('novo', rigo, arm)):
        pass
REP['testes'] = res
REP['testes_metodo'] = ('mesmo método da auditoria (giro do osso em torno de eixo do mundo pela cabeça); no modelo atual mede só '
                        'os triângulos da região do braço (vértices com osso dominante upper_arm/forearm/hand .L)')
REP['testes_limitacoes'] = 'ombro e junção com o tronco fora do P1; poses estáticas; mão fechada/aberta só existem no rig novo'
# desempenho
reset(rigo); t0 = time.perf_counter(); N = 60
for i in range(N):
    rigo.pose.bones['DEF-antebraco.L'].rotation_mode = 'XYZ'; rigo.pose.bones['DEF-antebraco.L'].rotation_euler = (math.radians(i), 0, 0)
    bpy.context.view_layer.update(); bpy.context.evaluated_depsgraph_get()
REP['desempenho_ms_por_atualizacao_p1'] = round((time.perf_counter() - t0) / N * 1000, 3)
reset(rigo); reset(rig0)
for m in OUTL: m.show_viewport = True
bpy.context.view_layer.update()

# ------------------------------------------------------------------ 6. salva o protótipo (arquivo NOVO) e renders
sc.render.engine = 'CYCLES'; sc.cycles.samples = 8; sc.render.film_transparent = False; sc.render.resolution_x = sc.render.resolution_y = 520
def cam(n, d, t, s):
    c = bpy.data.objects.new(n, bpy.data.cameras.new(n)); sc.collection.objects.link(c); c.data.type = 'ORTHO'; c.data.ortho_scale = s
    d = Vector(d).normalized(); c.location = Vector(t) + d * 4; c.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler(); return c
tgt = (cW + cpos(0.0)[0]) / 2
CAMS = {'frente': cam('cf', (0, -1, 0), tgt, 0.55), 'lado': cam('cl', (1, 0, 0.0), tgt, 0.55), 'tras': cam('ct', (0, 1, 0), tgt, 0.55),
        'mao': cam('cm', (0.45, -1, 0.15), cW + down * 0.05, 0.26)}
arm.location.x += 0.0
def render_set(prefix, objs_show):
    for o in bpy.data.objects:
        if o.type == 'MESH': o.hide_render = o.name not in objs_show
    for k, c in CAMS.items():
        sc.camera = c; sc.render.filepath = os.path.join(OUT, 'renders', f'{prefix}_{k}.png'); bpy.ops.render.render(write_still=True)
render_set('atual_repouso', {'Kumo'})
render_set('novo_repouso', {'P1_Braco_E'})
for pname in ('cotovelo_130', 'mao_fechada', 'punho_45'):
    for tag, r, obj, MAP in (('atual', rig0, 'Kumo', MAP_OLD), ('novo', rigo, 'P1_Braco_E', MAP_NEW)):
        reset(r); steps = POSES[pname]
        if steps == 'FIST':
            if tag == 'atual': continue
            for nm_ in [b.name for b in rigo.data.bones if 'dedo' in b.name or 'polegar' in b.name]:
                rot_world(r, nm_, curl_axis(r, nm_), 75 if 'polegar' not in nm_ else 40)
        else:
            for b, ax, deg in steps:
                bn = MAP[b]; rot_world(r, bn, bend_axis(r, bn) if ax == 'BEND' else ax, deg)
        for o in bpy.data.objects:
            if o.type == 'MESH': o.hide_render = o.name != obj
        for k in ('frente', 'lado', 'mao'):
            sc.camera = CAMS[k]; sc.render.filepath = os.path.join(OUT, 'renders', f'{tag}_{pname}_{k}.png'); bpy.ops.render.render(write_still=True)
    reset(rig0); reset(rigo)
# arquivo do protótipo: só o braço novo e seu rig
for o in list(bpy.data.objects):
    if o.name not in ('P1_Braco_E', 'P1_Rig'): bpy.data.objects.remove(o)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'p1_braco_mao.blend'), relative_remap=False)
json.dump(REP, open(os.path.join(OUT, 'p1-medicoes.json'), 'w'), indent=1, default=str)
print('P1 OK'); print(json.dumps({k: v for k, v in REP.items() if k != 'testes'}, indent=0, default=str)); print(json.dumps(REP['testes'], indent=0))
