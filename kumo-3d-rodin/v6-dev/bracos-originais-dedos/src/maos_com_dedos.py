"""Kumo v6 · Braços ORIGINAIS + mãos com 3 dedos e polegar, sem mudar o estilo (pedido de 2026-11-11).

  python maos_com_dedos.py <kumo_rigged.blend> <pasta de saída>

- Parte do modelo oficial (lido, nunca salvo). Grava só a cópia <saída>/kumo_maos_dedos.blend + exportações.
- Braço, antebraço, textura e contorno ORIGINAIS. Só a ponta (o punho em bloco, além do plano do punho) é trocada
  por uma mão em "luva" do mesmo tamanho (técnica do P1: anéis, 3 dedos em colunas, polegar lateral),
  costurada à borda original; a UV da mão nova é transferida da superfície do punho original (mesma textura).
- Rig da cópia: punho movido para o início da mão; ossos novos metacarpo, dedo1..3 (2 segmentos), polegar (2 segmentos).
- Pesos: braço como em bracos-originais (razão janela/raio 2,0), mão como no P1 iteração 7 (dono = tubo que criou o vértice);
  no máximo 4 ossos por vértice, soma 1. Testes de movimento + exportação GLB/FBX com reimportação.
"""
import bpy, bmesh, sys, os, json, math, time
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

SRC, OUT = sys.argv[-2], sys.argv[-1]
os.makedirs(os.path.join(OUT, 'renders'), exist_ok=True)
FAST = bool(os.environ.get('MD_FAST')); PREVIEW = bool(os.environ.get('MD_PREVIEW'))
P = dict(tcut=-0.12, palma=0.085, dedo=0.068, larg=0.92, esp=0.80, cols=(0.34, 0.30), fd=0.86, curl=0.8, spread=0.03, rect=0.55,
         first_t=1.35, tip=(1.0, 1.0, 0.98, 1.0, 1.03, 0.94, 0.64), tl=0.75, td=1.0, tla=0.65, tdn=0.62, tpn=0.45, tout=0.022,
         tD=(0.06, 0.13, 0.22, 0.36, 0.52, 0.68, 0.84, 1.0), ttip=(0.62, 0.72, 0.86, 1.0, 1.02, 1.0, 0.90, 0.60),
         tring=1, tfist=0.5, RE=2.0, RW=2.0, RK=2.0, RJ=1.6, RT=2.0, KP=0.012, KO=0.020, TP=0.006, mcg=(-0.25, 0.85), mca=(0.010, 0.050))
P.update({'tring': 2, 'tdn': 0.62, 'tpn': 0.45, 'tl': 0.65, 'td': 0.95, 'tla': 0.75, 'tout': 0.03, 'curl': 0.6, 'esp': 0.68, 'tfist': 0.0})   # valores escolhidos pela varredura (ver RELATORIO.md)
if os.environ.get('MD_P'): P.update({k: tuple(v) if isinstance(v, list) else v for k, v in json.loads(os.environ['MD_P']).items()})
REP = dict(parametros={k: v for k, v in P.items()})

bpy.ops.wm.open_mainfile(filepath=SRC)
REPO = os.path.dirname(os.path.abspath(SRC))
img = bpy.data.images['kumo_quad_diffuse']; img.filepath = os.path.join(REPO, 'textures', 'kumo_quad_diffuse.png'); img.reload()
sc = bpy.context.scene; rig = bpy.data.objects['Kumo_Rig']; body0 = bpy.data.objects['Kumo']
body = body0.copy(); body.data = body0.data.copy(); body.name = 'Kumo_Dedos'; body.data.name = 'Kumo_Dedos'; sc.collection.objects.link(body)
for m in body0.modifiers:
    if m.type != 'ARMATURE': m.show_viewport = False          # a fonte da UV não pode ter a casca do contorno
B0 = {b.name: (b.head_local.copy(), b.tail_local.copy()) for b in rig.data.bones}

def smooth01(x):
    x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
def ss(x, a, b): return smooth01((x - a) / (b - a))
ANG = [165, 135, 105, 75, 45, 15, -15, -45, -75, -105, -135, -165]

# ------------------------------------------------------------------ 1. geometria: corta o punho em bloco e constrói a mão nova
bm = bmesh.new(); bm.from_mesh(body.data); bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
uvl = bm.loops.layers.uv.active
og = body.vertex_groups; dl = bm.verts.layers.deform.verify()
gidx = {g.name: g.index for g in og}
def medir(sd):
    E, W = B0[f'forearm.{sd}']; down = (W - E).normalized(); c = W + down * P['tcut']
    def ok(f):
        q = f.calc_center_median() - c; return q.dot(down) > 0 and (q - down * q.dot(down)).length < 0.16
    seed = max((f for f in bm.faces if ok(f)), key=lambda f: (f.calc_center_median() - c).dot(down))
    far = set(); st = [seed]
    while st:
        f = st.pop()
        if f in far: continue
        far.add(f)
        for e in f.edges:
            for g in e.link_faces:
                if g not in far and ok(g): st.append(g)
    pts = [v.co.copy() for f in far for v in f.verts]
    pn = (Vector((0, 1, 0)) - down * down.y).normalized(); lat = down.cross(pn).normalized()
    Wn = sum(pts, Vector()) / len(pts)
    e_ = lambda ax: max((p - Wn).dot(ax) for p in pts) - min((p - Wn).dot(ax) for p in pts)
    return e_(lat), e_(pn)
_m = [medir(s_) for s_ in ('L', 'R')]
FW_MEDIA = sum(x[0] for x in _m) / 2; FT_MEDIA = sum(x[1] for x in _m) / 2
MAOS = {}
for sd in ('L', 'R'):
    E, W = B0[f'forearm.{sd}']; down = (W - E).normalized(); c = W + down * P['tcut']
    def ok(f):
        q = f.calc_center_median() - c; return q.dot(down) > 0 and (q - down * q.dot(down)).length < 0.16
    seed = max((f for f in bm.faces if ok(f)), key=lambda f: (f.calc_center_median() - c).dot(down))
    far = set(); st = [seed]
    while st:
        f = st.pop()
        if f in far: continue
        far.add(f)
        for e in f.edges:
            for g in e.link_faces:
                if g not in far and ok(g): st.append(g)
    fist_pts = [v.co.copy() for f in far for v in f.verts]
    fist_uvs = [l[uvl].uv.copy() for f in far for l in f.loops]
    fist_w = [(v.co.copy(), {k: w for k, w in v[dl].items()}) for f in far for v in f.verts]
    bnd_e = [e for e in bm.edges if sum(1 for f in e.link_faces if f in far) == 1]
    # ordena a borda
    adj = {}
    for e in bnd_e:
        a, b = e.verts; adj.setdefault(a, []).append(b); adj.setdefault(b, []).append(a)
    start = next(iter(adj)); loop = [start]; prev = None
    while True:
        nx = [v for v in adj[loop[-1]] if v is not prev]
        if not nx or nx[0] is start: break
        prev = loop[-1]; loop.append(nx[0])
        if len(loop) > len(adj): break
    bvs = set(loop)
    bmesh.ops.delete(bm, geom=list(far), context='FACES_ONLY')
    loose = [v for v in bm.verts if not v.link_faces and v not in bvs]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    Wn = sum((v.co for v in loop), Vector()) / len(loop)
    # referencial da mão: palma voltada para trás e girada para o corpo; lat aponta para fora
    pn = (Vector((0, 1, 0)) - down * down.y).normalized()
    body_dir = Vector((-1 if sd == 'L' else 1, 0, 0))
    pa_ = (Matrix.Rotation(math.radians(25), 3, down) @ pn).normalized(); pb_ = (Matrix.Rotation(math.radians(-25), 3, down) @ pn).normalized()
    pn = pa_ if pa_.dot(body_dir) > pb_.dot(body_dir) else pb_
    lat = down.cross(pn).normalized()
    if lat.dot(body_dir) > 0: lat = -lat
    rel = [p - Wn for p in fist_pts]
    ext = lambda ax: (min(q.dot(ax) for q in rel), max(q.dot(ax) for q in rel))
    el, ep, ed = ext(lat), ext(pn), ext(down)
    FW = (el[1] - el[0]); FT = (ep[1] - ep[0]); FLEN = ed[1]
    PL = P['palma']; FL = P['dedo']; PW = FW_MEDIA * P['larg']; PT = FT_MEDIA * P['esp']   # as duas mãos iguais (média dos punhos originais)
    # anel 1: forma da borda (função de suporte) logo após o corte
    def frame(dd):
        a = (lat - dd * lat.dot(dd)).normalized(); b = dd.cross(a).normalized()
        if b.dot(pn) < 0: b = -b
        return a, b
    a_, b_ = frame(down)
    bproj = [(v.co - Wn) - down * (v.co - Wn).dot(down) for v in loop]
    first_rel = []
    for g in ANG:
        g = math.radians(g); dv = (a_ * math.cos(g) + b_ * math.sin(g)).normalized()
        r = max(q.dot(dv) for q in bproj); first_rel.append(dv * r * 0.97)
    COLS = [-1.0, -P['cols'][0], -P['cols'][1], P['cols'][1], P['cols'][0], 1.0]
    def rect_rel(k, hw, ht):
        col = COLS[k] if k < 6 else COLS[11 - k]; ey = math.sin(math.radians(ANG[k]))
        return a_ * (col * 0.97 * hw) + b_ * ((0.88 if ey > 0 else -0.88) * ht * P['rect'] + math.sin(math.radians(ANG[k])) * ht * (1 - P['rect']))
    def ellip_rel(k, hw, ht):
        g = math.radians(ANG[k]); return a_ * (math.cos(g) * hw) + b_ * (math.sin(g) * ht)
    AS = [0.012, 0.030, PL * 0.55, PL * 0.80, PL]
    rings = []; ring_a = []
    for i, a in enumerate(AS):
        f = a / PL; bl = smooth01((f - 0.15) / 0.65); sh = smooth01(f / 0.6)
        hw = PW / 2; ht = PT / 2; pts = []
        for k in range(12):
            tgt = ellip_rel(k, hw, ht) * (1 - bl) + rect_rel(k, hw, ht) * bl
            if i == 0: rr = first_rel[k]
            else: rr = first_rel[k] * (1 - sh) + tgt * sh
            if k in range(6) or True:
                pass
            pts.append(Wn + down * a + rr)
        rings.append([bm.verts.new(p) for p in pts]); ring_a.append(a)
    new_faces = []
    for r0, r1 in zip(rings, rings[1:]):
        for j in range(12): new_faces.append(bm.faces.new([r0[j], r0[(j + 1) % 12], r1[(j + 1) % 12], r1[j]]))
    r0 = rings[0]; ring_edges = [bm.edges.get([r0[j], r0[(j + 1) % 12]]) or bm.edges.new([r0[j], r0[(j + 1) % 12]]) for j in range(12)]
    bnd_edges_now = [e for e in bm.edges if e.is_boundary and set(e.verts) <= bvs]
    br = bmesh.ops.bridge_loops(bm, edges=bnd_edges_now + ring_edges)
    bridge_faces = br['faces']
    end = rings[-1]
    def colq(i): return [end[i], end[i + 1], end[10 - i], end[11 - i]]
    CAPS = [colq(0), colq(2), colq(4)]
    for i in (1, 3): new_faces.append(bm.faces.new(colq(i)))
    tubes = []
    def tube(loop4, path, widths, axA, axB):
        c0 = sum((v.co for v in loop4), Vector()) / 4
        sig = [((v.co - c0).dot(axA) > 0, (v.co - c0).dot(axB) > 0) for v in loop4]
        prev = list(loop4); vs = []
        for i, (cc, (wa, wb)) in enumerate(zip(path, widths)):
            dd = (path[i] - (path[i - 1] if i else c0)).normalized()
            A = (axA - dd * axA.dot(dd)).normalized(); Bv = (axB - dd * axB.dot(dd) - A * axB.dot(A)).normalized()
            cur = [bm.verts.new(cc + A * (wa / 2 if sa else -wa / 2) + Bv * (wb / 2 if sb else -wb / 2)) for sa, sb in sig]
            for j in range(4): new_faces.append(bm.faces.new([prev[j], prev[(j + 1) % 4], cur[(j + 1) % 4], cur[j]]))
            prev = cur; vs += cur
        new_faces.append(bm.faces.new(prev)); tubes.append(vs)
    spacing = (COLS[0] + COLS[1]) / 2 * 0.97 * PW / 2
    FD = abs(spacing) * P['fd']
    FING = []
    for k, cap in enumerate(CAPS):
        c0 = sum((v.co for v in cap), Vector()) / 4
        spread = lat * (k - 1) * P['spread']
        D = [f * FL for f in (0.12, 0.32, 0.44, 0.56, 0.68, 0.86, 1.0)]
        path = [c0 + (down + spread).normalized() * dd + pn * P['curl'] * dd * dd / FL for dd in D]
        tk = [P['first_t'], 1 + (P['first_t'] - 1) * 0.4, 1, 1, 1, 1, 1]
        tube(cap, path, [(FD * t_, FD * t_ * k_) for t_, k_ in zip(P['tip'], tk)], lat, pn)
        FING.append(dict(base=c0, junta=path[3], ponta=path[-1]))
    pa, pb = rings[P['tring']], rings[P['tring'] + 1]
    tq = {pa[0], pa[11], pb[0], pb[11]}; tf = [f for f in bm.faces if set(f.verts) == tq][0]
    new_faces.remove(tf); bm.faces.remove(tf)
    tloop = [pa[0], pb[0], pb[11], pa[11]]; c0 = sum((v.co for v in tloop), Vector()) / 4
    nrm = -(lat - down * lat.dot(down)).normalized()
    dt = (-lat * P['tla'] + down * P['tdn'] + pn * P['tpn']).normalized()
    TL = FL * P['tl']; TD = FD * P['td']; TOUT = P['tout']
    tpath = []; pos = c0.copy(); pv = 0.0
    for dd in [f * TL for f in P['tD']]:
        w_ = smooth01(dd / (TOUT * 2.5)); dr = (nrm * (1 - w_) + dt * w_).normalized(); pos = pos + dr * (dd - pv); pv = dd; tpath.append(pos.copy())
    tube(tloop, tpath, [(TD * t_, TD * t_) for t_ in P['ttip']], down, pn)
    THUMB = dict(base=c0, junta=tpath[len(tpath) - 4], ponta=tpath[-1], dir=dt, nrm=nrm)
    newv = set(v for r in rings for v in r) | set(v for t in tubes for v in t)
    MAOS[sd] = dict(down=down, pn=pn, lat=lat, Wn=Wn, PL=PL, PW=PW, FD=FD, FING=FING, THUMB=THUMB, rings=rings, tubes=tubes,
                    newv=newv, borda=loop, fist_uvs=fist_uvs, fist_w=fist_w, original=dict(largura=round(FW, 3), espessura=round(FT, 3), comprimento=round(FLEN, 3)))
    # pesos provisórios das novas: copia o grupo de contorno do vértice original mais próximo; osso = mão
    kd = KDTree(len(fist_w)); [kd.insert(p, i) for i, (p, w) in enumerate(fist_w)]; kd.balance()
    for v in newv:
        _, i, _ = kd.find(v.co); src = fist_w[i][1]
        v[dl].clear()
        for gname in ('outline_cut', 'outline_shell'):
            gi_ = gidx[gname]
            if gi_ in src: v[dl][gi_] = src[gi_]
        v[dl][gidx[f'hand.{sd}']] = 1.0
    for f in new_faces + list(bridge_faces): f.material_index = 0; f.smooth = False
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.verts.index_update(); bm.verts.ensure_lookup_table()
for sd, m in MAOS.items():
    m['newi'] = {v.index for v in m['newv']}; m['bordai'] = [v.index for v in m['borda']]
    m['tubos_i'] = [{v.index for v in t} for t in m['tubes']]; m['aneis_i'] = [[v.index for v in r] for r in m['rings']]
    m['ring_a'] = None
bm.to_mesh(body.data); bm.free(); body.data.update()
REP['malha'] = dict(vertices_original=len(body0.data.vertices), vertices_novo=len(body.data.vertices),
                    tris=sum(1 for p in body.data.polygons if len(p.vertices) == 3), ngons=sum(1 for p in body.data.polygons if len(p.vertices) > 4))
REP['mao_original_medidas'] = {sd: m['original'] for sd, m in MAOS.items()}

# UV da mão nova: um ponto da textura com a cor típica do punho original (verde liso; mesma textura e material)
import numpy as np
W_, H_ = img.size; px = np.empty(W_ * H_ * 4, dtype=np.float32); img.pixels.foreach_get(px); px = px.reshape(H_, W_, 4)
def cor(uv): return px[min(H_ - 1, max(0, int(uv.y * H_))), min(W_ - 1, max(0, int(uv.x * W_))), :3]
REP['uv_mao'] = {}
for sd, m in MAOS.items():
    cols = np.array([cor(u) for u in m['fist_uvs']]); med = np.median(cols, axis=0)
    k = int(np.argmin(((cols - med) ** 2).sum(1))); m['uv0'] = m['fist_uvs'][k]
    REP['uv_mao'][sd] = dict(cor_mediana_rgb=[round(float(x), 3) for x in med], uv=[round(m['uv0'].x, 4), round(m['uv0'].y, 4)])
uvd = body.data.uv_layers.active.data
for poly in body.data.polygons:
    for sd, m in MAOS.items():
        if any(i in m['newi'] for i in poly.vertices):
            for li in poly.loop_indices: uvd[li].uv = m['uv0']
            break

# ------------------------------------------------------------------ 2. rig da cópia: punho no início da mão + ossos novos
bpy.context.view_layer.objects.active = rig
for o in bpy.context.selected_objects: o.select_set(False)
rig.select_set(True); bpy.ops.object.mode_set(mode='EDIT'); EB = rig.data.edit_bones
for sd, m in MAOS.items():
    d, pn, Wn = m['down'], m['pn'], m['Wn']
    EB[f'forearm.{sd}'].tail = Wn
    h = EB[f'hand.{sd}']; h.head = Wn; h.tail = Wn + d * (m['PL'] - P['KP']); h.align_roll(pn)
    def nb(name, hd, tl, par):
        b = EB.new(name); b.head = hd; b.tail = tl; b.parent = EB[par]; b.use_connect = False; b.align_roll(pn); return b
    meta_h = Wn + d * 0.012 + m['lat'] * (m['PW'] * 0.10)
    F = m['FING']
    nb(f'metacarpo.{sd}', meta_h, F[2]['base'] - d * P['KP'] + pn * P['KO'], f'hand.{sd}')
    for k, f in enumerate(F):
        nb(f'dedo{k+1}_1.{sd}', f['base'] - d * P['KP'] + pn * P['KO'], f['junta'], f'metacarpo.{sd}' if k == 2 else f'hand.{sd}')
        nb(f'dedo{k+1}_2.{sd}', f['junta'], f['ponta'], f'dedo{k+1}_1.{sd}')
    T = m['THUMB']
    nb(f'polegar_1.{sd}', T['base'] - T['nrm'] * P['TP'], T['junta'], f'hand.{sd}')
    nb(f'polegar_2.{sd}', T['junta'], T['ponta'], f'polegar_1.{sd}')
bpy.ops.object.mode_set(mode='OBJECT')
B = rig.data.bones; BONES = {b.name for b in B}
for b in BONES:
    if b not in body.vertex_groups: body.vertex_groups.new(name=b)

# ------------------------------------------------------------------ 3. pesos
me = body.data
gi = {g.index: g.name for g in body.vertex_groups}
def lado(sd):
    up, fo, ha = B[f'upper_arm.{sd}'], B[f'forearm.{sd}'], B[f'hand.{sd}']
    S, E, W = up.head_local.copy(), fo.head_local.copy(), fo.tail_local.copy()
    H = W + (ha.tail_local - ha.head_local).normalized() * 0.25
    segs = [(S, E), (E, W), (W, H)]; L = [(b - a).length for a, b in segs]; sE = L[0]; sW = L[0] + L[1]
    ARMB = (f'upper_arm.{sd}', f'forearm.{sd}', f'hand.{sd}')
    reg = []
    for v in me.vertices:
        ws = {gi[g.group]: g.weight for g in v.groups if gi[g.group] in BONES and g.weight > 0}
        tot = sum(ws.values()); A = sum(ws.get(n, 0) for n in ARMB)
        if tot > 0 and A / tot > 0.02: reg.append(v.index)
    def param(p):
        best = None; acc = 0.0
        for (a, b), l in zip(segs, L):
            ab = b - a; t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared)); dd = (a + ab * t - p).length
            if best is None or dd < best[0]: best = (dd, acc + t * l)
            acc += l
        return best
    sp = {i: param(me.vertices[i].co) for i in reg}
    rE = sorted(dd for i, (dd, s_) in sp.items() if abs(s_ - sE) < 0.02); rE = rE[len(rE) // 2] if rE else 0.06
    rW = sorted(dd for i, (dd, s_) in sp.items() if abs(s_ - sW) < 0.02); rW = rW[len(rW) // 2] if rW else 0.05
    EW = min(P['RE'] * rE, 0.8 * min(L[0], L[1])); WW = min(P['RW'] * rW, 0.8 * L[1])
    EH = {i: [ss(s_, sE - EW, sE + EW), ss(s_, sW - WW, sW + WW * 0.5)] for i, (dd, s_) in sp.items()}
    nbh = {i: [] for i in EH}
    for e_ in me.edges:
        a_, b_ = e_.vertices
        if a_ in EH and b_ in EH: nbh[a_].append(b_); nbh[b_].append(a_)
    for it in range(12):
        EH = {i: [(EH[i][c] + sum(EH[j][c] for j in nbh[i]) / len(nbh[i])) / 2 if nbh[i] else EH[i][c] for c in (0, 1)] for i in EH}
    for i, (e, h) in EH.items():
        v = me.vertices[i]
        ws = {gi[g.group]: g.weight for g in v.groups if gi[g.group] in BONES}
        tot = sum(ws.values()); A = sum(ws.get(n, 0) for n in ARMB) / tot
        new = {n: w / tot for n, w in ws.items() if n not in ARMB}
        new.update({ARMB[0]: A * (1 - e), ARMB[1]: A * e * (1 - h), ARMB[2]: A * e * h})
        for n, w in new.items():
            g = body.vertex_groups[n]
            if w > 1e-4: g.add([i], w, 'REPLACE')
            else: g.remove([i])
    return dict(raio_cotovelo=round(rE, 4), raio_punho=round(rW, 4), janela_cotovelo=round(EW, 4), janela_punho=round(WW, 4),
                antebraco_ate_novo_punho=round(L[1], 3))
REP['bracos'] = {sd: lado(sd) for sd in ('L', 'R')}
# mão: dedos/polegar pelo tubo dono; base dos dedos começa a seguir o dedo da coluna; metacarpo na metade lateral da palma
for sd, m in MAOS.items():
    d, pn, lat, Wn = m['down'], m['pn'], m['lat'], m['Wn']; FD = m['FD']; F = m['FING']; T = m['THUMB']
    KW = P['RK'] * FD / 2; JW = P['RJ'] * FD / 2; TW = P['RT'] * FD * P['td'] / 2
    endring = m['aneis_i'][-1]
    for k_ in range(12):
        i = endring[k_]; col = k_ if k_ < 6 else 11 - k_; kf = col // 2 + 1
        hh = 1 - ss(0.0, -KW, KW * 1.4); w = {f'hand.{sd}': hh, f'dedo{kf}_1.{sd}': 1 - hh}
        for gname in list(w): pass
        m.setdefault('override', {})[i] = w
    for t_idx, tset in enumerate(m['tubos_i']):
        for i in tset:
            p = me.vertices[i].co
            if t_idx == 3:
                ut = (p - T['base']).dot(T['dir']); jt = (T['junta'] - T['base']).dot(T['dir'])
                hh = 1 - ss(ut, -TW, TW * 1.4); x = ss(ut, jt - JW, jt + JW)
                w = {f'hand.{sd}': hh, f'polegar_1.{sd}': (1 - hh) * (1 - x), f'polegar_2.{sd}': (1 - hh) * x}
            else:
                f = F[t_idx]; ax = (f['ponta'] - f['base']).normalized(); u = (p - f['base']).dot(ax); jk = (f['junta'] - f['base']).dot(ax)
                hh = 1 - ss(u, -KW, KW * 1.4); x = ss(u, jk - JW, jk + JW)
                w = {f'hand.{sd}': hh, f'dedo{t_idx+1}_1.{sd}': (1 - hh) * (1 - x), f'dedo{t_idx+1}_2.{sd}': (1 - hh) * x}
            m['override'][i] = w
    for i, w in m['override'].items():
        v = me.vertices[i]
        for g in list(v.groups):
            if gi[g.group] in BONES: body.vertex_groups[gi[g.group]].remove([i])
        for n, x in w.items():
            if x > 1e-4: body.vertex_groups[n].add([i], x, 'REPLACE')
    # metacarpo: parte do peso da mão na metade lateral da palma (inclusive dedo 3 por herança)
    for v in me.vertices:
        if v.index not in m['newi'] and v.index not in set(m['bordai']): continue
        hw_ = next((g.weight for g in v.groups if gi[g.group] == f'hand.{sd}'), 0.0)
        if hw_ <= 0: continue
        latc = (v.co - Wn).dot(lat) / (m['PW'] / 2); a_ = (v.co - Wn).dot(d)
        mm = ss(latc, P['mcg'][0], P['mcg'][1]) * ss(a_, P['mca'][0], P['mca'][1])
        if mm > 1e-4:
            body.vertex_groups[f'hand.{sd}'].add([v.index], hw_ * (1 - mm), 'REPLACE'); body.vertex_groups[f'metacarpo.{sd}'].add([v.index], hw_ * mm, 'REPLACE')
for o in bpy.context.selected_objects: o.select_set(False)
body.select_set(True); bpy.context.view_layer.objects.active = body
bpy.ops.object.vertex_group_limit_total(group_select_mode='BONE_DEFORM', limit=4)
bpy.ops.object.vertex_group_normalize_all(group_select_mode='BONE_DEFORM', lock_active=False)
gi = {g.index: g.name for g in body.vertex_groups}
def stats(o):
    gg = {g.index: g.name for g in o.vertex_groups}; infl = []; sums = []
    for v in o.data.vertices:
        ws = [g.weight for g in v.groups if gg[g.group] in BONES and g.weight > 1e-4]; infl.append(len(ws)); sums.append(sum(ws))
    return dict(max_influencias=max(infl), sem_peso=sum(1 for x in infl if x == 0), soma_fora_de_1=sum(1 for s in sums if abs(s - 1) > 0.01))
REP['pesos'] = stats(body)
REP['ossos_novos'] = sorted(n for n in BONES if n.startswith(('dedo', 'polegar', 'metacarpo')))

# ------------------------------------------------------------------ 4. testes
body0.hide_viewport = True
OUTL = [m for m in body.modifiers if m.type in ('SOLIDIFY', 'VERTEX_WEIGHT_MIX', 'MASK')]
for m in OUTL: m.show_viewport = False
bpy.context.view_layer.update()
HANDB = lambda sd: {f'forearm.{sd}', f'hand.{sd}', f'metacarpo.{sd}', f'polegar_1.{sd}', f'polegar_2.{sd}'} | {f'dedo{k}_{j}.{sd}' for k in (1, 2, 3) for j in (1, 2)}
def regiao(sd):
    def dom(v):
        ws = [(gi[g.group], g.weight) for g in v.groups if gi[g.group] in BONES]; return max(ws, key=lambda x: x[1])[0] if ws else None
    vs = {v.index for v in me.vertices if dom(v) in HANDB(sd)} | MAOS[sd]['newi']
    fs = {p.index for p in me.polygons if all(i in vs for i in p.vertices)}
    return fs, vs
def tri_data(region, region_v):
    dg = bpy.context.evaluated_depsgraph_get(); ev = body.evaluated_get(dg); m = ev.to_mesh(); m.calc_loop_triangles()
    V = [ev.matrix_world @ v.co for v in m.vertices]
    T = [tuple(t.vertices) for t in m.loop_triangles if t.polygon_index in region]
    E_ = [(e.vertices[0], e.vertices[1]) for e in m.edges if e.vertices[0] in region_v and e.vertices[1] in region_v]
    ev.to_mesh_clear(); return V, T, E_
def self_pairs(V, T):
    b = BVHTree.FromPolygons(V, T); return {(a_, b_) for a_, b_ in b.overlap(b) if a_ < b_ and not (set(T[a_]) & set(T[b_]))}
def depth(V, T, pair):
    out = []
    for x, y in (pair, pair[::-1]):
        a0, a1, a2 = (V[i] for i in T[x]); n = (a1 - a0).cross(a2 - a0)
        if n.length < 1e-12: return 0.0
        n.normalize(); ds = [n.dot(V[i] - a0) for i in T[y]]; out.append(min(max(0.0, max(ds)), max(0.0, -min(ds))))
    return min(out)
def classify(V, T, pairs):
    pairs = list(pairs); ds = [depth(V, T, p) for p in pairs]
    return dict(reais=sum(1 for x in ds if x >= 0.0005), rasantes=sum(1 for x in ds if x < 0.0005), prof_max_mm=round(max(ds) * 1000, 2) if ds else 0.0)
def reset():
    for pb in rig.pose.bones:
        pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()
def rot_world(name, axis, deg):
    pb = rig.pose.bones[name]; bpy.context.view_layer.update(); M = pb.matrix.copy(); h = M.to_translation()
    pb.matrix = Matrix.Translation(h) @ Matrix.Rotation(math.radians(deg), 4, Vector(axis).normalized()) @ Matrix.Translation(-h) @ M
    bpy.context.view_layer.update()
def bdir(n): pb = rig.pose.bones[n]; return (pb.tail - pb.head).normalized()
def bend(n): return bdir(n).cross(Vector((0, -1, 0))).normalized()
def side_ax(n): return bdir(n).cross(bend(n)).normalized()
def poses(sd):
    m = MAOS[sd]; pn, lat = m['pn'], m['lat']
    curl = lambda n: bdir(n).cross(pn).normalized()
    spr = lambda n: lat.cross(bdir(n)).normalized()          # giro + leva a ponta para −lat (lado medial)
    dedos = [f'dedo{k}_{j}.{sd}' for k in (1, 2, 3) for j in (1, 2)]
    def fist(a):
        def f():
            rot_world(f'metacarpo.{sd}', curl(f'metacarpo.{sd}'), a * 20 / 70)
            for n in dedos: rot_world(n, curl(n), a)
            for n in (f'polegar_1.{sd}', f'polegar_2.{sd}'): rot_world(n, curl(n), a * P['tfist'])   # polegar na mão fechada
        return f
    def aberta():
        rot_world(f'dedo1_1.{sd}', spr(f'dedo1_1.{sd}'), 15); rot_world(f'dedo3_1.{sd}', spr(f'dedo3_1.{sd}'), -15)
        rot_world(f'polegar_1.{sd}', spr(f'polegar_1.{sd}'), 20)
        for n in dedos + [f'polegar_1.{sd}', f'polegar_2.{sd}']: rot_world(n, curl(n), -10)
    def dedos45():
        for n in dedos: rot_world(n, curl(n), 45)
    def polegar():
        rot_world(f'polegar_1.{sd}', spr(f'polegar_1.{sd}'), 20); rot_world(f'polegar_1.{sd}', curl(f'polegar_1.{sd}'), 35)
        rot_world(f'polegar_2.{sd}', curl(f'polegar_2.{sd}'), 45)
    def alternados():
        for k, a in ((1, 70), (2, 30), (3, 0)):
            for j in (1, 2): rot_world(f'dedo{k}_{j}.{sd}', curl(f'dedo{k}_{j}.{sd}'), a)
        rot_world(f'polegar_1.{sd}', curl(f'polegar_1.{sd}'), 15)
    def palma(): rot_world(f'metacarpo.{sd}', curl(f'metacarpo.{sd}'), 20)
    def br(n, ax, deg):
        def f(): rot_world(n, bend(n) if ax == 'B' else side_ax(n), deg)
        return f
    def both(*fs):
        def f():
            for x in fs: x()
        return f
    return {'mao_fechada': fist(70), 'mao_aberta': aberta, 'dedos_45': dedos45, 'polegar': polegar, 'dedos_alternados': alternados,
            'palma_curvada_20': palma, 'punho_45': br(f'hand.{sd}', 'B', 45), 'punho_menos45': br(f'hand.{sd}', 'B', -45),
            'punho_lateral_30': br(f'hand.{sd}', 'S', 30), 'punho_lateral_menos30': br(f'hand.{sd}', 'S', -30),
            'cotovelo_90': br(f'forearm.{sd}', 'B', 90), 'cotovelo_100': br(f'forearm.{sd}', 'B', 100),
            'cotovelo_90_punho_45_mao_fechada': both(br(f'forearm.{sd}', 'B', 90), br(f'hand.{sd}', 'B', 45), fist(70)),
            **{f'fechar_{a}': fist(a) for a in range(30, 75, 10)}}
for sd in (() if PREVIEW else ('L', 'R')):
    fs, vs = regiao(sd); reset(); V0, T0, E0 = tri_data(fs, vs); rest = self_pairs(V0, T0); L0 = [(V0[a] - V0[b]).length for a, b in E0]
    out = dict(repouso=dict(pares=len(rest), **classify(V0, T0, rest)))
    import collections
    def lab(T_, t):
        v = me.vertices[T_[t][0]]
        if v.index in MAOS[sd]['newi']:
            for ti, ts in enumerate(MAOS[sd]['tubos_i']):
                if v.index in ts: return ('dedo%d' % (ti + 1)) if ti < 3 else 'polegar'
            return 'palma_nova'
        return 'original'
    if FAST: print('FAST', sd, 'rest_labels', collections.Counter(tuple(sorted((lab(T0, a), lab(T0, b)))) for a, b in rest))
    for pname, fn in poses(sd).items():
        reset(); fn(); V, T, E_ = tri_data(fs, vs); new = self_pairs(V, T) - rest
        ratio = sorted((V[a] - V[b]).length / l for (a, b), l in zip(E_, L0) if l > 1e-7)
        if FAST and pname in ('mao_fechada', 'polegar', 'mao_aberta'):
            print('FAST', sd, pname, 'labels', collections.Counter(tuple(sorted((lab(T, a), lab(T, b)))) for a, b in new if depth(V, T, (a, b)) >= 0.0005))
        out[pname] = dict(pares_novos=len(new), **classify(V, T, new), compressao_min=round(ratio[0], 3), esticamento_max=round(ratio[-1], 3))
    REP['testes_' + ('E' if sd == 'L' else 'D')] = out
reset()
pbf = rig.pose.bones['forearm.L']; t0 = time.perf_counter()
for i in range(40):
    pbf.rotation_euler = (math.radians(i), 0, 0); bpy.context.view_layer.update(); bpy.context.evaluated_depsgraph_get()
REP['desempenho_ms'] = round((time.perf_counter() - t0) / 40 * 1000, 2); pbf.rotation_euler = (0, 0, 0)
for m in OUTL: m.show_viewport = True
body0.hide_viewport = False
for m in body0.modifiers: m.show_viewport = True
bpy.context.view_layer.update()
if FAST and not PREVIEW:
    print('FAST', json.dumps({k: REP[k] for k in ('malha', 'mao_original_medidas', 'pesos', 'bracos')}))
    for sdk in ('testes_E', 'testes_D'):
        for p_, x in REP[sdk].items(): print('FAST', sdk[-1], p_, {k: x.get(k) for k in ('pares', 'pares_novos', 'reais', 'prof_max_mm', 'compressao_min', 'esticamento_max')})
    raise SystemExit

# ------------------------------------------------------------------ 5. renders (com textura e contorno)
sc.render.engine = 'CYCLES'; sc.cycles.samples = 16; sc.render.film_transparent = False; sc.render.resolution_x = sc.render.resolution_y = 560
def cam(n, d, t, s):
    c = bpy.data.objects.new(n, bpy.data.cameras.new(n)); sc.collection.objects.link(c); c.data.type = 'ORTHO'; c.data.ortho_scale = s
    d = Vector(d).normalized(); c.location = Vector(t) + d * 5; c.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler(); return c
def shoot(name, cams, objname):
    for o in bpy.data.objects:
        if o.type == 'MESH': o.hide_render = o.name != objname
    for k, c in cams.items():
        sc.camera = c; sc.render.filepath = os.path.join(OUT, 'renders', f'{name}_{k}.png'); bpy.ops.render.render(write_still=True)
CORPO = {'corpo_frente': cam('cf', (0, -1, 0), (0, 0, 0.98), 2.15), 'corpo_34': cam('c34', (0.6, -1, 0.1), (0, 0, 0.98), 2.15)}
reset(); shoot('original', CORPO, 'Kumo'); shoot('dedos', CORPO, 'Kumo_Dedos')
for sd in ('L', 'R'):
    m = MAOS[sd]; hc = sum((body.data.vertices[i].co for i in m['newi']), Vector()) / len(m['newi']); sx = 1 if sd == 'L' else -1
    HC = {'frente': cam(f'hf{sd}', (0, -1, 0), hc, 0.42), 'lado': cam(f'hl{sd}', (sx, 0, 0), hc, 0.42),
          'dorso': cam(f'hd{sd}', -m['pn'], hc, 0.42), 'perspectiva': cam(f'hp{sd}', (0.35 * sx, -1, 0.1), hc, 0.42)}
    reset(); shoot(f'original_{sd}_repouso', HC, 'Kumo')
    for pname in (('repouso', 'mao_fechada') if PREVIEW else ('repouso', 'mao_aberta', 'mao_fechada', 'polegar', 'dedos_alternados', 'punho_45')):
        reset()
        if pname != 'repouso': poses(sd)[pname]()
        shoot(f'dedos_{sd}_{pname}', HC if pname in ('repouso', 'mao_fechada') else {k: HC[k] for k in ('frente', 'perspectiva')}, 'Kumo_Dedos')
reset()
if PREVIEW: print('MD PREVIEW OK'); raise SystemExit

# ------------------------------------------------------------------ 6. cópia + exportação + reimportação
for o in list(bpy.data.objects):
    if o.name not in ('Kumo_Dedos', 'Kumo_Rig'): bpy.data.objects.remove(o)
body.name = 'Kumo'; body.data.name = 'Kumo'
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'kumo_maos_dedos.blend'), copy=True, relative_remap=False)
act = bpy.data.actions.new('Teste_Exportacao'); rig.animation_data_create(); rig.animation_data.action = act
TESTE = {1: None, 2: 'mao_fechada', 3: 'mao_aberta', 4: 'cotovelo_90_punho_45_mao_fechada'}
for f, pname in TESTE.items():
    sc.frame_set(f); reset()
    if pname:
        poses('L')[pname](); poses('R')[pname]()
    for pb in rig.pose.bones:
        pb.keyframe_insert('rotation_euler', frame=f); pb.keyframe_insert('rotation_quaternion', frame=f); pb.keyframe_insert('location', frame=f)
sc.frame_start, sc.frame_end = 1, 4
def posicoes(obj, f):
    sc.frame_set(f); bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg); mm = ev.to_mesh(); Pp = [ev.matrix_world @ v.co for v in mm.vertices]; ev.to_mesh_clear(); return Pp
for m in body.modifiers:
    if m.type != 'ARMATURE': m.show_viewport = False
REF = {f: posicoes(body, f) for f in TESTE}
for o in bpy.context.selected_objects: o.select_set(False)
body.select_set(True); rig.select_set(True); bpy.context.view_layer.objects.active = rig
glb = os.path.join(OUT, 'kumo_maos_dedos.glb'); fbx = os.path.join(OUT, 'kumo_maos_dedos.fbx')
bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', use_selection=True, export_apply=False, export_skins=True, export_animations=True, export_all_influences=False)
bpy.ops.export_scene.fbx(filepath=fbx, use_selection=True, add_leaf_bones=False, bake_anim=True, use_mesh_modifiers=False)
REP['exportacao'] = dict(glb_kb=round(os.path.getsize(glb) / 1024), fbx_kb=round(os.path.getsize(fbx) / 1024))
bpy.ops.wm.read_homefile(use_empty=True); bpy.ops.import_scene.gltf(filepath=glb); sc = bpy.context.scene
mesh = [o for o in sc.objects if o.type == 'MESH'][0]; arm = [o for o in sc.objects if o.type == 'ARMATURE'][0]
bn = {b.name for b in arm.data.bones}; g2 = {g.index: g.name for g in mesh.vertex_groups}
infl = [len([g for g in v.groups if g2[g.group] in bn and g.weight > 1e-4]) for v in mesh.data.vertices]
sums = [sum(g.weight for g in v.groups if g2[g.group] in bn) for v in mesh.data.vertices]
acts = list(bpy.data.actions); teste = [a for a in acts if a.name.startswith('Teste_Exportacao')]
ad = arm.animation_data or arm.animation_data_create()
for t_ in list(ad.nla_tracks): ad.nla_tracks.remove(t_)
ad.action = teste[0]
REP['glb_reimportado'] = dict(vertices=len(mesh.data.vertices), ossos=len(bn), max_influencias=max(infl), soma_fora_de_1=sum(1 for s in sums if abs(s - 1) > 0.01))
rest = posicoes(mesh, 1); kd = KDTree(len(REF[1])); [kd.insert(p, i) for i, p in enumerate(REF[1])]; kd.balance()
mp = [kd.find(p)[1] for p in rest]; err = {}
for f in TESTE:
    Pp = posicoes(mesh, f); e = [(Pp[i] - REF[f][mp[i]]).length for i in range(len(Pp))]
    err[f] = dict(medio_mm=round(sum(e) / len(e) * 1000, 3), max_mm=round(max(e) * 1000, 3))
REP['glb_deformacao_vs_blender'] = err
json.dump(REP, open(os.path.join(OUT, 'medicoes.json'), 'w'), indent=1, default=str)
print('MD OK')
