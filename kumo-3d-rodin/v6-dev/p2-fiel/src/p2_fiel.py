"""Kumo v6 · P2 fiel: olhos de verdade na cabeça ATUAL do Kumo (forma, textura e contorno mantidos).

  python p2_fiel.py <kumo_v6_maos_jogo.blend> <olhos-simetricos.json> <saída>

- Olhos simétricos no quadro da própria cabeça (a cabeça Rodin está girada 8,5° em Z; ver simetria.py / olhos_frame.py).
- Órbita: só as faces da janela do olho saem da pele; a borda desce em uma parede curta (marrom, o aro do desenho) até
  logo acima do globo.
- Globo: esfera com textura gerada (âmbar, pupila preta vertical deslocada para o nariz, um brilho), gira pelo centro.
- Pálpebras: cascas esféricas concêntricas (superior por fora da inferior), escondidas atrás da pele em repouso; a piscada é
  giro em arco pelo centro do olho, então globo, pálpebras e pele não se cruzam por construção.
- Textura: os olhos pintados que sobram fora da janela são preenchidos com a pele em volta (cópia nova; a original fica).
"""
import bpy, bmesh, sys, os, json, math, time
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
SRC, OJ, OUT = sys.argv[-3:]; os.makedirs(os.path.join(OUT, 'renders'), exist_ok=True); os.makedirs(os.path.join(OUT, 'textures'), exist_ok=True)
ENV = lambda k, d: type(d)(os.environ.get(k, d))
STAGE = ENV('PF_STAGE', 'tudo'); RES = ENV('PF_RES', 480); SAMPLES = ENV('PF_SAMPLES', 16)
ESC = ENV('PF_JANELA', 0.92)          # janela = elipse do olho pintado médio × ESC
WALL = ENV('PF_PAREDE', 0.007)        # a parede da órbita termina a R + WALL
LUP, LLO = 0.0045, 0.003              # raios das pálpebras: R + LUP (superior, por fora), R + LLO (inferior)
REPO = '/home/user/Kumo-Character/kumo-3d-rodin'
REP = {}
bpy.ops.wm.open_mainfile(filepath=SRC); sc = bpy.context.scene
img = bpy.data.images['kumo_quad_diffuse']; img.filepath = REPO + '/textures/kumo_quad_diffuse.png'; img.reload()
rig = bpy.data.objects['Kumo_Rig']; body = bpy.data.objects['Kumo']; hull = bpy.data.objects.get('Kumo_Contorno')
if hull: bpy.data.objects.remove(hull)          # o contorno de jogo é refeito depois da cabeça (ver relatório)
me = body.data; OJd = json.load(open(OJ))
OUTL = [m for m in body.modifiers if m.type != 'ARMATURE']
def outline(on):
    for m in OUTL: m.show_viewport = on
    bpy.context.view_layer.update()
outline(False)
HW, HH = OJd['meia_largura'] * ESC, OJd['meia_altura'] * ESC
Z = Vector((0, 0, 1))
EYE = {}
for sd in ('L', 'R'):
    c0 = Vector(OJd[sd]['centro_janela']); f = Vector(OJd[sd]['eixo']).normalized()
    w = (Z - f * Z.dot(f)).normalized(); u = w.cross(f).normalized()
    EYE[sd] = dict(c0=c0, f=f, u=u, w=w)
# ---- 1. superfície no eixo do olho e escolha do raio do globo
dg = bpy.context.evaluated_depsgraph_get(); ev = body.evaluated_get(dg); m0 = ev.to_mesh()
V0 = [v.co.copy() for v in m0.vertices]; bvh = BVHTree.FromPolygons(V0, [tuple(p.vertices) for p in m0.polygons]); ev.to_mesh_clear()
def jan(sd, p):
    E = EYE[sd]; d = p - E['c0']; return (d.dot(E['u']) / HW) ** 2 + (d.dot(E['w']) / HH) ** 2, d.dot(E['f'])
for sd, E in EYE.items():
    hit = bvh.ray_cast(E['c0'] + E['f'] * 0.5, -E['f'], 1.0); s0 = hit[0]; E['s0'] = s0
    rim = [Vector(p) for p in V0 if 0.9 < jan(sd, Vector(p))[0] < 1.3 and abs(jan(sd, Vector(p))[1]) < 0.2]
    # raio fixo (igual nos dois olhos) proporcional à janela; o centro anda no eixo até a borda da pele ficar ~GAPB acima do globo
    R = ENV('PF_RAIO_FATOR', 1.70) * max(HW, HH); best = None
    for off in np.arange(-0.10, 0.10, 0.001):
        c = s0 + E['f'] * off - E['f'] * R
        med = float(np.median([(p - c).length - R for p in rim]))
        if best is None or abs(med - ENV('PF_GAPB', 0.010)) < abs(best[1] - ENV('PF_GAPB', 0.010)): best = (off, med)
    E['R'] = float(R); E['c'] = s0 + E['f'] * best[0] - E['f'] * R
    best = (float(R), best[1], best[0])
    REP.setdefault('olhos', {})[sd] = dict(raio=round(E['R'], 4), centro=[round(x, 4) for x in E['c']], frente_pele=[round(x, 4) for x in s0],
                                         borda_mediana_acima_do_globo_mm=round(best[1] * 1000, 1), vertices_borda=len(rim), frente_do_globo_alem_da_pele_mm=round(best[2] * 1000, 1))
print('PF OLHOS', json.dumps(REP['olhos']), flush=True)

# ---- 2. órbita: remove as faces da janela e desce a borda numa parede até R + WALL
bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table(); dl = bm.verts.layers.deform.active
gidx = {g.name: g.index for g in body.vertex_groups}
uvl = bm.loops.layers.uv.active
mat_borda = bpy.data.materials.new('Kumo_Olho_Aro'); mat_borda.use_nodes = True; nt = mat_borda.node_tree; nt.nodes.clear()
em = nt.nodes.new('ShaderNodeEmission'); em.inputs[0].default_value = (0.105, 0.042, 0.027, 1); o_ = nt.nodes.new('ShaderNodeOutputMaterial'); nt.links.new(em.outputs[0], o_.inputs[0])
me.materials.append(mat_borda); MI_ARO = len(me.materials) - 1
REP['orbita'] = {}
for sd, E in EYE.items():
    sel = [f for f in bm.faces if all(jan(sd, v.co)[0] < 1.0 and jan(sd, v.co)[1] > -0.25 for v in f.verts)]
    # só a região conexa que contém o centro (evita pegar outra parte da cabeça)
    seed = min(sel, key=lambda f: (f.calc_center_median() - E['s0']).length); sset = set(sel); comp = set(); st = [seed]
    while st:
        f = st.pop()
        if f in comp: continue
        comp.add(f); st += [g for e in f.edges for g in e.link_faces if g in sset and g not in comp]
    bmesh.ops.delete(bm, geom=list(comp), context='FACES_ONLY')
    bm.verts.ensure_lookup_table()
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bnd = [e for e in bm.edges if e.is_boundary and all(jan(sd, v.co)[0] < 2.0 for v in e.verts)]
    # borda lisa: cada vértice da borda vai para a elipse da janela, sobre a superfície original da pele
    for v in {v for e in bnd for v in e.verts}:
        d = v.co - E['c0']; a_, b_ = d.dot(E['u']) / HW, d.dot(E['w']) / HH; r_ = math.hypot(a_, b_)
        tgt = E['c0'] + E['u'] * (a_ / r_ * HW) + E['w'] * (b_ / r_ * HH)
        hit = bvh.ray_cast(tgt + E['f'] * 0.4, -E['f'], 0.8)
        if hit[0] is not None: v.co = hit[0]
    ret = bmesh.ops.extrude_edge_only(bm, edges=bnd); nv = [g for g in ret['geom'] if isinstance(g, bmesh.types.BMVert)]
    nf = [g for g in ret['geom'] if isinstance(g, bmesh.types.BMFace)]
    for v in nv:
        d = v.co - E['c']; v.co = E['c'] + d.normalized() * (E['R'] + WALL)
        v[dl].clear(); v[dl][gidx['head']] = 1.0; v[dl][gidx['outline_cut']] = 1.0
    for f in nf:
        f.material_index = MI_ARO; f.smooth = False
        for v in f.verts:
            if v not in nv: v[dl][gidx['outline_cut']] = 1.0     # sem casca de contorno entrando na órbita
    # pele que ficou perto demais do globo (abaulamento): afasta só o necessário
    pushed = 0
    for v in bm.verts:
        if v in nv: continue
        d = v.co - E['c']
        ang_ = math.degrees(d.angle(E['f'])) if d.length > 0 else 0
        if d.length < E['R'] + WALL + 0.001 and ang_ < ENV('PF_PELE_ANG', 80.0) and jan(sd, v.co)[0] < 4.0:
            v.co = E['c'] + d.normalized() * (E['R'] + WALL + 0.001); pushed += 1
    E['parede'] = [v.index for v in nv]
    REP['orbita'][sd] = dict(faces_removidas=len(comp), vertices_da_borda=len(nv), pele_afastada=pushed)
bones_def = {b.name for b in rig.data.bones}; nh = 0
for v in bm.verts:
    if any(jan(sd, v.co)[0] < ENV('PF_JAN_CABECA', 4.5) and jan(sd, v.co)[1] > -0.3 for sd in EYE):
        ks = [k for k in v[dl].keys() if body.vertex_groups[k].name in bones_def]
        if any(body.vertex_groups[k].name != 'head' and v[dl][k] > 1e-4 for k in ks):
            for k in ks: del v[dl][k]
            v[dl][gidx['head']] = 1.0; nh += 1
REP['pele_perto_dos_olhos_so_na_cabeca'] = nh
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
bm.to_mesh(me); bm.free(); me.update()
print('PF ORBITA', json.dumps(REP['orbita']), flush=True)

# ---- 3. textura do olho (gerada) e globo + pálpebras
from PIL import Image, ImageDraw, ImageFilter
N = 1024
def textura_olho(sd):
    im = Image.new('RGB', (N, N)); px = im.load(); cx = cy = N / 2
    for y in range(N):
        for x in range(N):
            r = math.hypot((x - cx) / (N / 2), (y - cy) / (N / 2))
            # âmbar da paleta (#F4B642) mais claro no centro, escurecendo para a borda, e aro marrom (#5B3A2E) na beirada
            stops = [(0.0, (0.99, 0.83, 0.45)), (0.30, (0.957, 0.714, 0.259)), (0.62, (0.86, 0.56, 0.16)), (1.5, (0.80, 0.50, 0.13))]
            for (r0, c0_), (r1, c1_) in zip(stops, stops[1:]):
                if r0 <= r <= r1: t = (r - r0) / (r1 - r0); col = [c0_[i] * (1 - t) + c1_[i] * t for i in range(3)]; break
            px[x, y] = tuple(int(255 * c) for c in col)
    dr = ImageDraw.Draw(im)
    # pupila: proporções do olho pintado (v5): meia largura 0,325 e meia altura 0,61 da janela, deslocada 0,45 para o nariz
    sx_, sy_ = N / 2 * EYE[sd]['fu'], N / 2 * EYE[sd]['fv']; s = sx_; nose = -1 if sd == 'L' else 1           # em u: nariz fica em -u no olho E (verificado nos renders)
    # a janela ocupa a fração (fu, fv) do disco; pupila nas proporções do olho pintado (v5), deslocada para o nariz
    pcx = cx + nose * 0.45 * sx_ * 0.55; pcy = cy - 0.05 * sy_
    pw, ph = 0.325 * sx_ * 0.95, 0.61 * sy_ * 0.95
    dr.ellipse([pcx - pw, pcy - ph, pcx + pw, pcy + ph], fill=(10, 8, 8))
    hr = 0.11 * min(sx_, sy_); hx, hy = pcx + 0.35 * pw + 0.0, pcy - 0.55 * ph
    dr.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], fill=(255, 255, 255))
    im = im.filter(ImageFilter.GaussianBlur(1.2))
    fn = os.path.join(OUT, 'textures', f'kumo_olho_{sd}.png'); im.save(fn); return fn
def material_img(nome, fn):
    m = bpy.data.materials.new(nome); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(fn); t.extension = 'EXTEND'; e = nt.nodes.new('ShaderNodeEmission'); o = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(t.outputs[0], e.inputs[0]); nt.links.new(e.outputs[0], o.inputs[0]); return m
def material_cor(nome, rgb):
    m = bpy.data.materials.new(nome); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    e = nt.nodes.new('ShaderNodeEmission'); e.inputs[0].default_value = (*rgb, 1); o = nt.nodes.new('ShaderNodeOutputMaterial'); nt.links.new(e.outputs[0], o.inputs[0]); return m
# cor da pele em volta do olho (mediana da textura nas faces vizinhas da janela)
W_, H_ = img.size; pxa = np.empty(W_ * H_ * 4, np.float32); img.pixels.foreach_get(pxa); pxa = pxa.reshape(H_, W_, 4)
uvd = me.uv_layers.active.data
def pele_em_volta(sd, lado):
    cols = []
    for p in me.polygons:
        cc = Vector(p.center); j, dep = jan(sd, cc)
        if 1.05 < j < 1.8 and dep > -0.25 and (cc - EYE[sd]['c0']).dot(EYE[sd]['w']) * lado > 0.3 * HH:
            for li in p.loop_indices:
                u_, v_ = uvd[li].uv; cols.append(pxa[min(H_ - 1, int(v_ * H_)), min(W_ - 1, int(u_ * W_)), :3])
    cols = np.array(cols); mx = cols.max(1); mn = cols.min(1); sat = (mx - mn) / np.maximum(mx, 1e-6)
    g = cols[(cols[:, 1] >= cols[:, 0]) & (sat > 0.25)]                        # só tons de pele verde
    c = np.median(g if len(g) else cols, axis=0)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)          # textura em sRGB, emissão em linear
olhos = bpy.data.meshes.new('Kumo_Olhos'); ob = bpy.data.objects.new('Kumo_Olhos', olhos); sc.collection.objects.link(ob)
bm = bmesh.new(); uvo = bm.loops.layers.uv.new('UVMap'); dlo = bm.verts.layers.deform.new()
MATS = []
def esfera_parcial(E, R, a0, a1, b0, b1, na, nb, mi, grupo_i, uvfun=None, manter=None):
    """casca esférica no quadro do olho: a = elevação (em torno de u), b = azimute (em torno de w), em radianos."""
    grid = []
    for i in range(na + 1):
        a = a0 + (a1 - a0) * i / na; row = []
        for j in range(nb + 1):
            b = b0 + (b1 - b0) * j / nb
            d = E['f'] * (math.cos(a) * math.cos(b)) + E['u'] * (math.cos(a) * math.sin(b)) + E['w'] * math.sin(a)
            v = bm.verts.new(E['c'] + d * R); v[dlo][grupo_i] = 1.0; row.append(v)
        grid.append(row)
    fs = []
    for i in range(na):
        for j in range(nb):
            if manter and not manter(a0 + (a1 - a0) * (i + 0.5) / na, b0 + (b1 - b0) * (j + 0.5) / nb): continue
            f = bm.faces.new([grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j]]); f.material_index = mi; f.smooth = True; fs.append(f)
            if uvfun:
                for l in f.loops: l[uvo].uv = uvfun(l.vert.co)
    return grid, fs
GRP = {}
def grupo(n):
    if n not in GRP: GRP[n] = ob.vertex_groups.new(name=n).index
    return GRP[n]
REP['palpebras'] = {}
for sd, E in EYE.items():
    R = E['R']
    _ah, _bw = math.asin(min(0.99, HH / R)), math.asin(min(0.99, HW / R))
    E['fu'] = math.sin(_bw) / math.sin(min(1.45, _bw + 0.46)); E['fv'] = math.sin(_ah) / math.sin(min(1.45, _ah + 0.27))   # janela / disco
    mo = material_img(f'Kumo_Olho.{sd}', textura_olho(sd)); olhos.materials.append(mo); mi_o = len(olhos.materials) - 1
    mp_up = material_cor(f'Kumo_Palpebra_sup.{sd}', tuple(float(x) for x in pele_em_volta(sd, +1))); olhos.materials.append(mp_up); mi_pu = len(olhos.materials) - 1
    mp_lo = material_cor(f'Kumo_Palpebra_inf.{sd}', tuple(float(x) for x in pele_em_volta(sd, -1))); olhos.materials.append(mp_lo); mi_pl = len(olhos.materials) - 1
    if 'aro' not in GRP: olhos.materials.append(mat_borda); GRP['aro'] = len(olhos.materials) - 1
    mi_a = GRP['aro']
    ah, bw = math.asin(min(0.99, HH / R)), math.asin(min(0.99, HW / R))
    def uvf(p, E=E, R=R, ah=ah, bw=bw):
        # o disco da textura vai até a janela + o giro máximo (o aro marrom é a parede da órbita, não o olho)
        d = (p - E['c']); KU = math.sin(min(1.45, bw + 0.46)); KV = math.sin(min(1.45, ah + 0.27))
        return (0.5 + d.dot(E['u']) / (2 * R * KU), 0.5 + d.dot(E['w']) / (2 * R * KV))
    GV, GH = ENV('PF_CALOTA_V', 0.27), ENV('PF_CALOTA_H', 0.46)
    oval = lambda a, b, A_=ah + GV, B_=bw + GH: (a / A_) ** 2 + (b / B_) ** 2 <= 1.0
    esfera_parcial(E, R, -(ah + GV), ah + GV, -(bw + GH), bw + GH, 36, 44, mi_o, grupo(f'eye.{sd}'), uvf, oval)
    # pálpebras só um pouco maiores que a janela (para não sair pela pele em repouso); a superior tem uma linha marrom fina na borda
    MEET = ENV('PF_ENCONTRO', -0.10) * ah; MG = ENV('PF_PALP_MARGEM', 0.07); BAND = 0.035
    nasal = 1.0 if E['u'].dot(Vector((0, E['c0'].y, E['c0'].z)) - E['c0']) > 0 else -1.0     # +u aponta para o nariz?
    BN, BT = bw + ENV('PF_PALP_NARIZ', 0.02), bw + MG
    b0, b1 = (-BT, BN) if nasal > 0 else (-BN, BT)
    esfera_parcial(E, R + LUP, MEET, MEET + BAND, b0, b1, 1, 24, mi_a, grupo(f'palpebra_sup.{sd}'))
    # cantos da pálpebra fora da janela oval não são necessários para cobrir o olho fechado
    ovp = lambda a, b, A_=ah + MG, Bl=bw + MG: (a / A_) ** 2 + (b / Bl) ** 2 <= ENV('PF_PALP_OVAL', 1.25)
    esfera_parcial(E, R + LUP, MEET + BAND, ah + MG, b0, b1, 10, 24, mi_pu, grupo(f'palpebra_sup.{sd}'), None, ovp)
    esfera_parcial(E, R + LLO, -(ah + MG), MEET, b0, b1, 8, 24, mi_pl, grupo(f'palpebra_inf.{sd}'), None, ovp)
    E['ang_sup'] = (ah + MG * 0.6) - MEET; E['ang_inf'] = (ah + MG * 0.6) + MEET
    REP['palpebras'][sd] = dict(abertura_sup_graus=round(math.degrees(E['ang_sup']), 1), abertura_inf_graus=round(math.degrees(E['ang_inf']), 1),
                                janela_meia_altura_graus=round(math.degrees(ah), 1), janela_meia_largura_graus=round(math.degrees(bw), 1))
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
# normais para fora do centro de cada olho
for f in bm.faces:
    cc = f.calc_center_median(); E = EYE['L'] if (cc - EYE['L']['c']).length < (cc - EYE['R']['c']).length else EYE['R']
    if f.normal.dot(cc - E['c']) < 0: f.normal_flip()
bm.to_mesh(olhos); bm.free()
ob.parent = rig; m_ = ob.modifiers.new('Armature', 'ARMATURE'); m_.object = rig
# ossos novos
for o in bpy.context.selected_objects: o.select_set(False)
rig.select_set(True); bpy.context.view_layer.objects.active = rig; bpy.ops.object.mode_set(mode='EDIT'); EB = rig.data.edit_bones
for sd, E in EYE.items():
    for n in (f'eye.{sd}', f'palpebra_sup.{sd}', f'palpebra_inf.{sd}'):
        b = EB.new(n); b.head = E['c']; b.tail = E['c'] + E['f'] * 0.12; b.parent = EB['head']; b.use_connect = False; b.align_roll(E['w'])
bpy.ops.object.mode_set(mode='OBJECT'); pb = rig.pose.bones
def eixo_x(n): return (rig.data.bones[n].matrix_local.to_3x3() @ Vector((1, 0, 0))).normalized()
for sd, E in EYE.items(): REP['palpebras'][sd]['eixo_x_igual_u'] = round(eixo_x(f'palpebra_sup.{sd}').dot(E['u']), 4)
def rot_local(n, ang_rad, axis='X'):
    ang_rad *= (1.0 if eixo_x(n).dot(EYE[n[-1]]['u']) > 0 else -1.0)      # ângulo dado em torno de u (mundo)
    b = pb[n]; b.rotation_mode = 'QUATERNION'; b.rotation_quaternion = (b.rotation_quaternion @ Matrix.Rotation(ang_rad, 4, axis).to_quaternion()) if False else Matrix.Rotation(ang_rad, 4, axis).to_quaternion()
# sentido: girar a superior para cima = elevação positiva. Em torno de u, +ang leva f para +w? testa e fixa o sinal
q = Matrix.Rotation(0.3, 3, EYE['L']['u']) @ EYE['L']['f']; SGN = 1.0 if q.dot(EYE['L']['w']) > 0 else -1.0
def palpebras(sd, fech):
    """fech 0 = aberto (repouso do personagem), 1 = fechado. A malha foi construída FECHADA; aberto = girada para fora."""
    E = EYE[sd]
    rot_local(f'palpebra_sup.{sd}', SGN * E['ang_sup'] * (1 - fech)); rot_local(f'palpebra_inf.{sd}', -SGN * E['ang_inf'] * (1 - fech))
def reset():
    for b in pb: b.rotation_quaternion = (1, 0, 0, 0); b.rotation_euler = (0, 0, 0); b.location = (0, 0, 0)
    for sd in EYE: palpebras(sd, 0.0)
    bpy.context.view_layer.update()
reset()
# a pose de repouso do rig deve ser o olho ABERTO: grava a rotação aberta como repouso (aplica a pose nos ossos das pálpebras)
for o in bpy.context.selected_objects: o.select_set(False)
ob.select_set(True); bpy.context.view_layer.objects.active = ob
bpy.ops.object.modifier_apply(modifier='Armature')
m_ = ob.modifiers.new('Armature', 'ARMATURE'); m_.object = rig
for b in pb: b.rotation_quaternion = (1, 0, 0, 0)
bpy.context.view_layer.update()
def palpebras(sd, fech):
    E = EYE[sd]
    rot_local(f'palpebra_sup.{sd}', -SGN * E['ang_sup'] * fech); rot_local(f'palpebra_inf.{sd}', SGN * E['ang_inf'] * fech)
def reset():
    for b in pb: b.rotation_quaternion = (1, 0, 0, 0); b.rotation_euler = (0, 0, 0); b.location = (0, 0, 0)
    bpy.context.view_layer.update()
print('PF PALP', json.dumps(REP['palpebras']), flush=True)

# ---- 4. textura da pele: o olho pintado que sobrou fora da janela vira pele (preenchimento por difusão, cópia nova)
import colorsys
def mascara_olho(a):
    rgb = a[..., :3]; mx = rgb.max(-1); mn = rgb.min(-1); s = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    h = np.zeros_like(mx); d = np.maximum(mx - mn, 1e-6)
    h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    return (mx < 0.18) | ((s < 0.25) & (mx > 0.75)) | ((h < 56) & (s > 0.18) & (mx > 0.45)) | ((h < 52) & (s > 0.35))
# só os texels das faces da região dos olhos (as faces da cabeça perto da janela)
from PIL import Image as _I
from PIL import ImageDraw as _D
_rm = _I.new('L', (W_, H_), 0); _dr = _D.Draw(_rm)
for p in me.polygons:
    cc = Vector(p.center)
    if any(jan(sd, cc)[0] < 3.5 and jan(sd, cc)[1] > -0.3 for sd in EYE) and p.material_index != MI_ARO:
        _dr.polygon([(uvd[li].uv.x * W_, uvd[li].uv.y * H_) for li in p.loop_indices], fill=255, outline=255)
reg = np.array(_rm) > 0
mask = mascara_olho(pxa) & reg
new = pxa.copy(); known = ~mask
fill = new[..., :3].copy(); fill[mask] = 0
for it in range(400):
    acc = np.zeros_like(fill); cnt = np.zeros((H_, W_))
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        acc += np.roll(np.roll(fill * known[..., None], dy, 0), dx, 1); cnt += np.roll(np.roll(known, dy, 0), dx, 1)
    upd = mask & (cnt > 0); fill[upd] = acc[upd] / cnt[upd, None]; known = known | upd
new[..., :3] = fill
REP['textura'] = dict(texels_preenchidos=int(mask.sum()))
fn_tex = os.path.join(OUT, 'textures', 'kumo_v6_diffuse.png')
_I.fromarray((np.clip(new[::-1, :, :3], 0, 1) * 255).astype(np.uint8)).save(fn_tex)
img2 = bpy.data.images.load(fn_tex); img2.name = 'kumo_v6_diffuse'
for mt in me.materials:
    if mt and mt.node_tree:
        for n in mt.node_tree.nodes:
            if n.type == 'TEX_IMAGE' and n.image == img: n.image = img2
print('PF TEX', REP['textura'], flush=True)

# ---- 5. renders rápidos (comparação)
outline(True)
sc.render.engine = 'CYCLES'; sc.cycles.samples = SAMPLES
def cam(n, d, t, s_):
    c = bpy.data.objects.new(n, bpy.data.cameras.new(n)); sc.collection.objects.link(c); c.data.type = 'ORTHO'; c.data.ortho_scale = s_
    d = Vector(d).normalized(); c.location = Vector(t) + d * 6; c.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler(); return c
IDX = {}
def shoot(tag, cams_, res=RES):
    if os.environ.get('PF_SEM_RENDER'): return
    sc.render.resolution_x = sc.render.resolution_y = res
    for k_, c in cams_.items():
        sc.camera = c; f = os.path.join(OUT, 'renders', f'{tag}_{k_}.png'); sc.render.filepath = f; bpy.ops.render.render(write_still=True); IDX[f'{tag}|{k_}'] = f
HC = Vector((0, -0.1, 1.42))
CAB = {'frente': cam('hf', (0, -1, 0), HC, 1.3), '34': cam('h34', (-0.57, -0.82, 0.05), HC, 1.3), 'perfil': cam('hp', (-1, 0, 0), HC, 1.3)}
CORPO = {'frente': cam('cf', (0, -1, 0), (0, 0, 0.98), 2.2), '34': cam('c34', (-0.57, -0.82, 0.05), (0, 0, 0.98), 2.2),
         'perfil': cam('cp', (-1, 0, 0), (0, 0, 0.98), 2.2), 'costas': cam('cc', (0, 1, 0), (0, 0, 0.98), 2.2)}
reset(); shoot('p2_cabeca', CAB); shoot('p2_corpo', CORPO)
EXPR = {'neutro': lambda: None, 'piscada_50': lambda: [palpebras(s, 0.5) for s in EYE], 'piscada_100': lambda: [palpebras(s, 1.0) for s in EYE]}
for k_, fn in EXPR.items():
    reset(); fn(); bpy.context.view_layer.update(); shoot(f'expr_{k_}', {'frente': CAB['frente'], '34': CAB['34']}, res=400)
reset()
json.dump(IDX, open(os.path.join(OUT, 'renders', 'indice.json'), 'w'), indent=0)
json.dump(REP, open(os.path.join(OUT, 'p2-medicoes.json'), 'w'), indent=1, default=str)
if STAGE == 'visual':
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'visual.blend'), copy=True); print('PF VISUAL OK'); raise SystemExit

# ---- 6. testes (mesmo método: pares de triângulos que se cruzam, novos em relação ao repouso)
outline(False)
def geo(o):
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get(); ev = o.evaluated_get(dg); m = ev.to_mesh(); m.calc_loop_triangles()
    V = [ev.matrix_world @ v.co for v in m.vertices]; T = [tuple(t.vertices) for t in m.loop_triangles]; ev.to_mesh_clear(); return V, T
def depth(VA, TA, VB, TB, a, b):
    out = []
    for (V1, T1, x), (V2, T2, y) in (((VA, TA, a), (VB, TB, b)), ((VB, TB, b), (VA, TA, a))):
        p0, p1, p2 = (V1[i] for i in T1[x]); n = (p1 - p0).cross(p2 - p0)
        if n.length < 1e-12: return 0.0
        n.normalize(); ds = [n.dot(V2[i] - p0) for i in T2[y]]; out.append(min(max(0.0, max(ds)), max(0.0, -min(ds))))
    return min(out)
CABV = None
def cabeca_tris(V, T):
    global CABV
    if CABV is None: CABV = [i for i, t in enumerate(T) if all(V[j].z > 1.0 and abs(V[j].x) < 0.7 for j in t)]   # fixado no repouso
    return CABV
def pares(oa, ob_, base=None, so_cabeca=False):
    VA, TA = geo(oa)
    global CABV
    if oa is ob_:
        idx = cabeca_tris(VA, TA) if so_cabeca else list(range(len(TA))); TT = [TA[i] for i in idx]
        t = BVHTree.FromPolygons(VA, TT); P = {(a, b) for a, b in t.overlap(t) if a < b and not (set(TT[a]) & set(TT[b]))}; VB, TB, TA = VA, TT, TT
    else:
        VB, TB = geo(ob_); P = set(BVHTree.FromPolygons(VA, TA).overlap(BVHTree.FromPolygons(VB, TB)))
    if base is not None: P = P - base
    ds = [depth(VA, TA, VB, TB, a, b) for a, b in P]
    return P, dict(pares=len(P), reais=sum(1 for d in ds if d >= 0.0005), prof_max_mm=round(max(ds) * 1000, 2) if ds else 0.0)
def fura_pele():
    """vértices de pálpebra fora da pele (raio do centro do olho até o vértice cruza a pele antes)"""
    Vb, Tb = geo(body); tb = BVHTree.FromPolygons(Vb, Tb); Vo, _ = geo(ob); gi = {g.index: g.name for g in ob.vertex_groups}; n = 0
    for v, P_ in zip(ob.data.vertices, Vo):
        g = gi[v.groups[0].group] if v.groups else ''
        if not g.startswith('palpebra'): continue
        E = EYE[g[-1]]; c = Vector(tuple(pb[f'eye.{g[-1]}'].head)); d = P_ - c
        hit = tb.ray_cast(c, d.normalized(), d.length)
        if hit[0] is not None and hit[3] < d.length - 0.0005: n += 1
    return n
def eye_rot(sd, yaw, pitch):
    b = pb[f'eye.{sd}']; bpy.context.view_layer.update(); Mb = b.matrix.copy(); h = Mb.to_translation(); E = EYE[sd]
    R_ = Matrix.Rotation(math.radians(yaw), 4, E['w']) @ Matrix.Rotation(math.radians(pitch), 4, E['u'])
    b.matrix = Matrix.Translation(h) @ R_ @ Matrix.Translation(-h) @ Mb; bpy.context.view_layer.update()
def headrot(axis, deg):
    b = pb['head']; bpy.context.view_layer.update(); Mb = b.matrix.copy(); h = Mb.to_translation()
    b.matrix = Matrix.Translation(h) @ Matrix.Rotation(math.radians(deg), 4, axis) @ Matrix.Translation(-h) @ Mb; bpy.context.view_layer.update()
def blink(v, lados='LR'):
    def f():
        for s_ in lados: palpebras(s_, v)
        bpy.context.view_layer.update()
    return f
def comb(*fs):
    def f():
        for x in fs: x()
    return f
reset()
B_OC, rep_oc = pares(ob, body); B_OO, rep_oo = pares(ob, ob); B_CC, rep_cc = pares(body, body, so_cabeca=True)
def furos_lado(sd, nome):
    Vb, Tb = geo(body); tb = BVHTree.FromPolygons(Vb, Tb); Vo, _ = geo(ob); gi = {g.index: g.name for g in ob.vertex_groups}; n = 0
    c = Vector(tuple(pb[f'eye.{sd}'].head))
    for v, P_ in zip(ob.data.vertices, Vo):
        if not v.groups or gi[v.groups[0].group] != nome: continue
        d = P_ - c; hit = tb.ray_cast(c, d.normalized(), d.length)
        if hit[0] is not None and hit[3] < d.length - 0.0005: n += 1
    return n
REP['abertura_ajustada'] = {}
for sd, E in EYE.items():
    for nome, key, sg in ((f'palpebra_sup.{sd}', 'ang_sup', 1), (f'palpebra_inf.{sd}', 'ang_inf', -1)):
        base = E[key]; achou = None
        for extra in np.arange(0.0, 0.60, 0.02):
            reset(); rot_local(nome, sg * SGN * float(extra)); bpy.context.view_layer.update()   # sinal: afasta da janela
            n_ = furos_lado(sd, nome)
            if n_ == 0: achou = float(extra); break
        if achou is None:
            for extra in np.arange(0.0, -0.30, -0.02):
                reset(); rot_local(nome, sg * SGN * float(extra)); bpy.context.view_layer.update()
                if furos_lado(sd, nome) == 0: achou = float(extra); break
        E[key + '_extra'] = achou or 0.0
        if achou:
            # incorpora o giro extra no repouso da malha e aumenta o fechamento na mesma medida
            reset(); rot_local(nome, sg * SGN * achou); bpy.context.view_layer.update()
            for o_ in bpy.context.selected_objects: o_.select_set(False)
            ob.select_set(True); bpy.context.view_layer.objects.active = ob
            bpy.ops.object.modifier_apply(modifier='Armature'); m2 = ob.modifiers.new('Armature', 'ARMATURE'); m2.object = rig
            E[key] += achou; reset()
        REP['abertura_ajustada'][nome] = dict(graus_extra=round(math.degrees(achou), 1) if achou is not None else None)
reset()
print('PF ABERTURA', json.dumps(REP['abertura_ajustada']), flush=True)
REP['repouso'] = dict(olhos_x_corpo=rep_oc, olhos_x_olhos=rep_oo, cabeca_propria=rep_cc, palpebra_fora_da_pele=fura_pele())
print('PF REPOUSO', json.dumps(REP['repouso']), flush=True)
import collections
if os.environ.get('PF_DIAG'):
    Vo, To = geo(ob); Vb, Tb = geo(body); gi = {g.index: g.name for g in ob.vertex_groups}
    def gname(t): v = ob.data.vertices[To[t][0]]; return gi[v.groups[0].group] if v.groups else '?'
    import collections
    print('PF DIAG oc', collections.Counter(gname(a) for a, b in B_OC).most_common(6))
    print('PF DIAG oo', collections.Counter(tuple(sorted((gname(a), gname(b)))) for a, b in B_OO).most_common(6))
CASOS = {**{f'piscada_{int(v*100)}': blink(v) for v in (0.25, 0.5, 0.75, 1.0)},
         'piscada_so_E': blink(1.0, 'L'), 'piscada_so_D': blink(1.0, 'R'), 'piscada_so_E_50': blink(0.5, 'L'),
         'olhar_dir_25': lambda: [eye_rot(s_, 25, 0) for s_ in 'LR'], 'olhar_esq_25': lambda: [eye_rot(s_, -25, 0) for s_ in 'LR'],
         'olhar_cima_15': lambda: [eye_rot(s_, 0, 15) for s_ in 'LR'], 'olhar_baixo_15': lambda: [eye_rot(s_, 0, -15) for s_ in 'LR'],
         'olhar_dir_25_piscada_50': comb(lambda: [eye_rot(s_, 25, 0) for s_ in 'LR'], blink(0.5)),
         'olhar_baixo_15_piscada_100': comb(lambda: [eye_rot(s_, 0, -15) for s_ in 'LR'], blink(1.0)),
         'cabeca_gira_30': lambda: headrot('Z', 30), 'cabeca_inclina_20': lambda: headrot('Y', 20), 'cabeca_baixa_20': lambda: headrot('X', 20),
         'tudo_junto': comb(lambda: headrot('Z', 25), lambda: [eye_rot(s_, 20, 10) for s_ in 'LR'], blink(0.6))}
TESTES = {}
for nome, fn in CASOS.items():
    reset(); fn()
    if os.environ.get('PF_DIAG'):
        Po, _ = pares(ob, ob, B_OO); Vo, To = geo(ob); gi_ = {g.index: g.name for g in ob.vertex_groups}
        gn = lambda t: gi_[ob.data.vertices[To[t][0]].groups[0].group]
        if Po: print('PF DIAGT', nome, collections.Counter(tuple(sorted((gn(a), gn(b)))) for a, b in Po).most_common(4))
    TESTES[nome] = dict(olhos_x_corpo=pares(ob, body, B_OC)[1], olhos_x_olhos=pares(ob, ob, B_OO)[1], cabeca_propria=pares(body, body, B_CC, True)[1],
                        palpebra_fora_da_pele=fura_pele())
    print('PFT', nome, json.dumps(TESTES[nome]), flush=True)
REP['testes'] = TESTES; reset()
def pesos(o):
    bn = {b.name for b in rig.data.bones}; gi = {g.index: g.name for g in o.vertex_groups}; inf = []; su = []
    for v in o.data.vertices:
        ws = [g.weight for g in v.groups if gi[g.group] in bn and g.weight > 1e-4]; inf.append(len(ws)); su.append(sum(ws))
    return dict(vertices=len(o.data.vertices), max_influencias=max(inf), sem_peso=sum(1 for x in inf if x == 0), soma_fora_de_1=sum(1 for x in su if abs(x - 1) > 0.01))
REP['pesos'] = {o.name: pesos(o) for o in (body, ob)}
t0 = time.perf_counter()
for i in range(40):
    palpebras('L', (i % 10) / 10); eye_rot('R', 1, 0); bpy.context.view_layer.update(); bpy.context.evaluated_depsgraph_get()
REP['desempenho_ms'] = round((time.perf_counter() - t0) / 40 * 1000, 2); reset()
print('PF PESOS', json.dumps(REP['pesos']), REP['desempenho_ms'], flush=True)
# expressões extras para a prancha
outline(True)
EXPR2 = {'olhar_dir': lambda: [eye_rot(s_, 25, 0) for s_ in 'LR'], 'olhar_esq': lambda: [eye_rot(s_, -25, 0) for s_ in 'LR'],
         'olhar_cima': lambda: [eye_rot(s_, 0, 15) for s_ in 'LR'], 'piscada_so_E': blink(1.0, 'L'), 'cabeca_gira_30': lambda: headrot('Z', 30)}
for k_, fn in EXPR2.items():
    reset(); fn(); shoot(f'expr_{k_}', {'frente': CAB['frente'], '34': CAB['34']}, res=400)
reset()
json.dump(IDX, open(os.path.join(OUT, 'renders', 'indice.json'), 'w'), indent=0)
for o in [o for o in bpy.data.objects if o.type == 'CAMERA']: bpy.data.objects.remove(o)
img2.filepath = fn_tex
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'kumo_v6_p2.blend'), copy=True, relative_remap=False)
json.dump(REP, open(os.path.join(OUT, 'p2-medicoes.json'), 'w'), indent=1, default=str)
print('PF OK')
