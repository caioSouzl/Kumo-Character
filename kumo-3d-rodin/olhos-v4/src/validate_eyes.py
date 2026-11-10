"""Validação do sistema ocular experimental.

  python validate_eyes.py orig <kumo_rigged.blend> <olhos-v4>   # renders de referência do original
  python validate_eyes.py exp  <kumo_eyes_exp.blend> <olhos-v4>  # estados, medições e renders

Nenhum arquivo .blend é gravado: as câmeras e poses de teste existem só na memória.
"""
import bpy, bmesh, sys, os, json, math
import numpy as np
from mathutils import Vector, Matrix, Euler
from mathutils.bvhtree import BVHTree

MODE, BLEND, OUT = sys.argv[-3], sys.argv[-2], sys.argv[-1]
RD = os.path.join(OUT, 'renders', 'tmp' if MODE == 'orig' else 'estados'); os.makedirs(RD, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=BLEND)
sc = bpy.context.scene; rig = bpy.data.objects['Kumo_Rig']; body = bpy.data.objects['Kumo']
REPO = os.path.dirname(os.path.abspath(OUT))
bpy.data.images['kumo_quad_diffuse'].filepath = os.path.join(REPO, 'textures', 'kumo_quad_diffuse.png')
for im in bpy.data.images:
    if im.name.startswith('olho_'): im.filepath = os.path.join(OUT, 'textures', im.name + '.png')
    im.reload()

sc.render.engine = 'CYCLES'; sc.cycles.samples = 12; sc.cycles.use_denoising = False
sc.cycles.transparent_max_bounces = 24; sc.render.film_transparent = False

# ---------------------------------------------------------------- câmeras de detalhe da cabeça
def cam(name, az, el=0.0, target=Vector((0.03, -0.25, 1.38)), scale=1.05):
    c = bpy.data.objects.new(name, bpy.data.cameras.new(name)); sc.collection.objects.link(c)
    c.data.type = 'ORTHO'; c.data.ortho_scale = scale
    d = Vector((math.sin(math.radians(az)) * math.cos(math.radians(el)), -math.cos(math.radians(az)) * math.cos(math.radians(el)), math.sin(math.radians(el))))
    c.location = target + d * 4; c.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    c.data.clip_end = 20; return c
CAMS = {'frente': cam('cf', 0), '34': cam('c34', -40), 'perfil_E': cam('cpe', -90), 'perfil_D': cam('cpd', 90), '34_D': cam('c34d', 40)}
BODY_CAMS = {'frente': bpy.data.objects['Cam_Front'], '34': bpy.data.objects['Cam_ThreeQuarter'],
             'perfil': bpy.data.objects['Cam_Side'], 'costas': bpy.data.objects['Cam_Back']}

def render(camobj, path, res=560, body_res=None):
    sc.camera = camobj
    sc.render.resolution_x = sc.render.resolution_y = res
    sc.render.filepath = path; bpy.ops.render.render(write_still=True)

def silhouette(path):
    """Render só de alfa: personagem em branco sobre transparente (para IoU)."""
    pass

import hashlib
HEAD_SHA = hashlib.sha256(np.array([c for v in body.data.vertices for c in v.co], dtype=np.float32).tobytes() + np.array([i for p in body.data.polygons for i in p.vertices], dtype=np.int32).tobytes()).hexdigest()
HEAD_MODS = [(m.name, m.type) for m in body.modifiers]
if MODE == 'orig':
    json.dump({'sha_malha_cabeca': HEAD_SHA, 'modificadores': HEAD_MODS}, open(os.path.join(OUT, 'renders', 'tmp', 'orig_head.json'), 'w'))
    for k, c in CAMS.items(): render(c, os.path.join(RD, f'orig_{k}.png'))
    hb = rig.pose.bones['head']
    for yaw in (18, 25, -25):
        q = Euler((0, math.radians(yaw), 0), 'XYZ').to_quaternion()
        if hb.rotation_mode == 'QUATERNION': hb.rotation_quaternion = q
        else: hb.rotation_euler = q.to_euler(hb.rotation_mode)
        bpy.context.view_layer.update()
        for k in ('frente', '34', 'perfil_E', 'perfil_D'): render(CAMS[k], os.path.join(RD, f'orig_virada{yaw:+d}_{k}.png'))
    hb.rotation_quaternion = (1, 0, 0, 0); hb.rotation_euler = (0, 0, 0); bpy.context.view_layer.update()
    sc.render.film_transparent = True
    for k, c in BODY_CAMS.items(): render(c, os.path.join(RD, f'orig_corpo_{k}.png'), 700)
    print('ORIG OK'); sys.exit(0)

# ---------------------------------------------------------------- controles
hp = rig.pose.bones['head']
drv_ok = all(fc.driver.is_simple_expression for fc in rig.animation_data.drivers)
REST = {pb.name: (pb.location.copy(), pb.rotation_quaternion.copy(), pb.rotation_euler.copy()) for pb in rig.pose.bones}
tgt_rest = rig.data.bones['eye_target'].matrix_local.to_3x3()

def state(p=0, pe=0, pd=0, fe=0, fd=0, gaze=(0, 0), head=(0, 0, 0), ac=0.5):
    # head = (erguer, virar, inclinar) em graus, nos eixos locais do osso head (X, Y = eixo do pescoço, Z)
    for n, (l, q, e) in REST.items():
        pb = rig.pose.bones[n]; pb.location = l
        if pb.rotation_mode == 'QUATERNION': pb.rotation_quaternion = q
        else: pb.rotation_euler = e
    hp['piscar'], hp['piscar_E'], hp['piscar_D'] = p, pe, pd
    hp['fechar_parcial_E'], hp['fechar_parcial_D'], hp['acompanhar_olhar'] = fe, fd, ac
    # olhar: deslocamento do alvo no espaço da cabeça (x = esquerda do Kumo, z = cima), em unidades de mundo
    wv = Vector((gaze[0], 0, gaze[1]))
    rig.pose.bones['eye_target'].location = tgt_rest.inverted() @ wv
    hb = rig.pose.bones['head']; q = Euler([math.radians(a) for a in head], 'XYZ').to_quaternion()
    if hb.rotation_mode == 'QUATERNION': hb.rotation_quaternion = q
    else: hb.rotation_euler = q.to_euler(hb.rotation_mode)
    bpy.context.view_layer.update()

# ---------------------------------------------------------------- medição de penetração
OUTLINE = [m for m in body.modifiers if m.type in ('SOLIDIFY', 'VERTEX_WEIGHT_MIX', 'MASK')]
def evaluated_world(obj):
    dg = bpy.context.evaluated_depsgraph_get(); ev = obj.evaluated_get(dg); m = ev.to_mesh()
    V = [obj.matrix_world @ v.co for v in m.vertices] if obj.type == 'MESH' else []
    V = [ev.matrix_world @ v.co for v in m.vertices]
    F = [list(p.vertices) for p in m.polygons]; ev.to_mesh_clear(); return V, F

def mask_lookup(tag):
    im = bpy.data.images[f'olho_{tag}_mask']; w, h = im.size
    a = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)[:, :, 3]
    win = bpy.data.objects[f'Kumo_EyeWindow_{tag}']; inv = win.matrix_world.inverted()
    def f(p):
        q = inv @ p; x, y = (q.x + 1) / 2, (q.y + 1) / 2
        if not (0 <= x < 1 and 0 <= y < 1): return 0.0
        return float(a[int(y * h), int(x * w)])
    return f

DIRS = [Vector((0.3127, 0.5469, 0.7768)).normalized(), Vector((-0.6712, 0.2214, -0.7072)).normalized()]
def inside(bvh, p):
    """Paridade de raios (malha fechada): ímpar = dentro. Dois raios; conta dentro só se ambos concordam."""
    votes = 0
    for d in DIRS:
        n, o = 0, p.copy()
        for _ in range(64):
            loc, nor, i, dist = bvh.ray_cast(o, d)
            if loc is None: break
            n += 1; o = loc + d * 1e-6
        votes += n % 2
    return votes == 2

class WBVH:
    """BVH com os MESMOS triângulos que o Blender/Cycles renderizam (looptris), consultado em coordenadas de mundo."""
    def __init__(self, obj):
        dg = bpy.context.evaluated_depsgraph_get(); ev = obj.evaluated_get(dg)
        self.b = BVHTree.FromObject(ev, dg); self.M = ev.matrix_world.copy(); self.Mi = self.M.inverted()
        self.N = self.M.to_3x3().inverted().transposed()
    def find_nearest(self, p):
        loc, nor, i, d = self.b.find_nearest(self.Mi @ p)
        if loc is None: return None, None, None, 1e9
        loc = self.M @ loc; return loc, (self.N @ nor).normalized(), i, (loc - p).length
    def ray_cast(self, o, d):
        loc, nor, i, dist = self.b.ray_cast(self.Mi @ o, (self.Mi.to_3x3() @ d).normalized())
        if loc is None: return None, None, None, None
        loc = self.M @ loc; return loc, nor, i, (loc - o).length

def tri_bvh(obj):
    """BVH em coordenadas de mundo com os triângulos REAIS renderizados (para teste de interseção superfície × superfície)."""
    dg = bpy.context.evaluated_depsgraph_get(); ev = obj.evaluated_get(dg); m = ev.to_mesh(); m.calc_loop_triangles()
    V = [ev.matrix_world @ v.co for v in m.vertices]; T = [tuple(t.vertices) for t in m.loop_triangles]
    ev.to_mesh_clear(); return BVHTree.FromPolygons(V, T), V, T

def measure():
    for m in OUTLINE: m.show_viewport = False
    bpy.context.view_layer.update()
    HV, HF = evaluated_world(body); hb = WBVH(body)
    BB_, _, _ = tri_bvh(body)
    res = {}
    for tag in ('L', 'R'):
        SV, SF = evaluated_world(bpy.data.objects[f'Kumo_Eye_{tag}']); sb = WBVH(bpy.data.objects[f'Kumo_Eye_{tag}'])
        mk = mask_lookup(tag); r = {}
        sh_in = sum(1 for p in SV if mk(p) > 0.5 and inside(hb, p))
        r['Eye'] = dict(vertices=len(SV), visiveis=sum(1 for p in SV if mk(p) > 0.5), visiveis_dentro_da_cabeca=sh_in,
                        visiveis_abaixo_do_globo=0, penetracao_max_m=0.0, todos_dentro_da_cabeca_inclusive_ocultos=sum(1 for p in SV if inside(hb, p)))
        tb, TV, TT = tri_bvh(bpy.data.objects[f'Kumo_Eye_{tag}']); hit_t = {a_ for a_, b_ in tb.overlap(BB_)}
        r['Eye_superficie'] = dict(triangulos=len(TT), triangulos_cruzando_a_pele=len(hit_t),
                                   visiveis=len({a_ for a_ in hit_t if mk(sum((TV[i] for i in TT[a_]), Vector()) / 3) > 0.5}))
        for part in ('LidUp', 'LidLow', 'Iris', 'Pupil', 'Catchlight'):
            o = bpy.data.objects.get(f'Kumo_{part}_{tag}')
            if o is None: continue
            V, _ = evaluated_world(o)
            vis = in_head = in_head_all = under_eye = 0; worst = 0.0
            for p in V:
                loc, nor, i, d = hb.find_nearest(p)
                ins = inside(hb, p); sd = -d if ins else d
                l2, n2, i2, d2 = sb.find_nearest(p); se = (p - l2).dot(n2)
                v = mk(p) > 0.5 and d2 < 0.006          # sobre a superfície do olho, dentro do contorno
                if ins: in_head_all += 1
                if v:
                    vis += 1
                    if ins: in_head += 1; worst = min(worst, sd)
                    if se < -2e-4: under_eye += 1
            # interseção real triângulo × triângulo com a pele (não só vértices)
            tb, TV, TT = tri_bvh(o); pairs = tb.overlap(BB_)
            hit_t = {a_ for a_, b_ in pairs}
            vis_t = {a_ for a_ in hit_t if mk(sum((TV[i] for i in TT[a_]), Vector()) / 3) > 0.5}
            r[part + '_superficie'] = dict(triangulos=len(TT), triangulos_cruzando_a_pele=len(hit_t), visiveis=len(vis_t))
            r[part] = dict(vertices=len(V), visiveis=vis, visiveis_dentro_da_cabeca=in_head,
                           visiveis_abaixo_do_globo=under_eye, penetracao_max_m=round(-worst, 5),
                           todos_dentro_da_cabeca_inclusive_ocultos=in_head_all)
        res[tag] = r
    for m in OUTLINE: m.show_viewport = True
    return res, HV

# ---------------------------------------------------------------- 1) a cabeça não é deformada
state(); _, HV0 = measure()
ref = {}
me = body.data
head_hash = hash(tuple(round(c, 7) for v in me.vertices for c in v.co))
o_ = json.load(open(os.path.join(OUT, 'renders', 'tmp', 'orig_head.json')))
report = {'drivers_expressao_simples': drv_ok, 'sha_malha_cabeca_original': o_['sha_malha_cabeca'], 'sha_malha_cabeca_experimento': HEAD_SHA,
          'malha_cabeca_identica': o_['sha_malha_cabeca'] == HEAD_SHA, 'modificadores_cabeca_identicos': [list(x) for x in o_['modificadores']] == [list(x) for x in HEAD_MODS]}

# ---------------------------------------------------------------- 2) varredura fina de penetração
SWEEP = {}
fine = [round(i / 40, 4) for i in range(41)]                       # estágios exatos e pontos entre eles
mid = [0.0] + [round((i + 0.5) / 20, 4) for i in range(20)] + [1.0]   # só pontos ENTRE estágios (pior caso)
cases = {
    'piscada_simultanea': lambda t: dict(p=t),
    'piscada_E': lambda t: dict(pe=t),
    'piscada_D': lambda t: dict(pd=t),
    'semicerrar_E_D': lambda t: dict(fe=t, fd=t),
    'piscada_olhar_esq': lambda t: dict(p=t, gaze=(0.18, 0)),
    'piscada_olhar_dir': lambda t: dict(p=t, gaze=(-0.18, 0)),
    'piscada_olhar_cima': lambda t: dict(p=t, gaze=(0, 0.15)),
    'piscada_olhar_baixo': lambda t: dict(p=t, gaze=(0, -0.15)),
    'piscada_virada_+18': lambda t: dict(p=t, head=(0, 18, 0)),
    'piscada_virada_-18': lambda t: dict(p=t, head=(0, -18, 0)),
    'piscada_virada_+25': lambda t: dict(p=t, head=(0, 25, 0)),
    'piscada_virada_-25': lambda t: dict(p=t, head=(0, -25, 0)),
    'olhar_lateral_virada_+25': lambda t: dict(p=t, head=(0, 25, 0), gaze=(0.18, 0)),
    'olhar_lateral_virada_-25': lambda t: dict(p=t, head=(0, -25, 0), gaze=(-0.18, 0)),
    'extra_inclinada_25': lambda t: dict(p=t, head=(0, 0, 25)),
    'extra_erguida_inclinada': lambda t: dict(p=t, head=(12, 10, 20)),
}
for cn, fn in cases.items():
    rows = []
    for t in (fine if cn in ('piscada_simultanea', 'piscada_E', 'piscada_D', 'piscada_virada_+25') else mid):
        state(**fn(t)); m, HV = measure()
        PT = [(e, pt) for e in m for pt in m[e] if not pt.endswith('_superficie')]
        SF = [(e, pt) for e in m for pt in m[e] if pt.endswith('_superficie')]
        tot = sum(m[e][pt]['visiveis_dentro_da_cabeca'] for e, pt in PT)
        under = sum(m[e][pt]['visiveis_abaixo_do_globo'] for e, pt in PT)
        hid = sum(m[e][pt]['todos_dentro_da_cabeca_inclusive_ocultos'] for e, pt in PT)
        dmax = max(m[e][pt]['penetracao_max_m'] for e, pt in PT)
        sv = sum(m[e][pt]['visiveis'] for e, pt in SF); st_ = sum(m[e][pt]['triangulos_cruzando_a_pele'] for e, pt in SF)
        rows.append(dict(t=t, penetracoes_visiveis=tot, camadas_abaixo_do_globo=under, penetracao_max_m=dmax, vertices_ocultos_dentro_da_cabeca=hid,
                         triangulos_cruzando_pele_visiveis=sv, triangulos_cruzando_pele_total=st_,
                         detalhe=m if t in (0.25, 0.5, 0.75, 1.0, 0.525) else None))
    SWEEP[cn] = rows
    print(cn, 'pontos', [r['penetracoes_visiveis'] for r in rows], 'tri_vis', [r['triangulos_cruzando_pele_visiveis'] for r in rows])
report['varredura'] = SWEEP

# deformação da cabeça: com o sistema novo, a malha avaliada é idêntica ao repouso das mesmas poses
state(p=0.5, gaze=(0.13, 0.11)); _, HVa = measure(); state(p=0.0); _, HVb = measure()
report['cabeca_dif_max_entre_estados_de_olho_m'] = max((a - b).length for a, b in zip(HVa, HVb))

# ---------------------------------------------------------------- 3) renders
R = {}
def shot(name, views=('frente', '34', 'perfil_E', 'perfil_D'), **kw):
    state(**kw)
    for v in views:
        p = os.path.join(RD, f'{name}_{v}.png'); render(CAMS[v], p); R.setdefault(name, []).append(p)
shot('aberto')
for t in (0.25, 0.5, 0.75, 1.0): shot(f'fechado_{int(t*100):03d}', p=t)
shot('piscada_E', pe=1.0); shot('piscada_D', pd=1.0)
shot('piscada_E_050', pe=0.5); shot('piscada_D_050', pd=0.5)
shot('semicerrado_040', fe=0.4, fd=0.4)
for nm, gz in (('olhar_esq', (0.18, 0)), ('olhar_dir', (-0.18, 0)), ('olhar_cima', (0, 0.15)), ('olhar_baixo', (0, -0.15)), ('olhar_diag', (0.13, 0.11))):
    shot(nm, gaze=gz)
V4 = ('frente', '34', 'perfil_E', 'perfil_D')
for yaw in (18, 25):
    for t in (0, 0.25, 0.5, 0.75, 1.0): shot(f'virada{yaw:+d}_fechado_{int(t*100):03d}', views=V4, head=(0, yaw, 0), p=t)
for t in (0, 0.5, 1.0): shot(f'virada-25_fechado_{int(t*100):03d}', views=V4, head=(0, -25, 0), p=t)
shot('virada+25_olhar_esq', views=V4, head=(0, 25, 0), gaze=(0.18, 0)); shot('virada+25_olhar_dir', views=V4, head=(0, 25, 0), gaze=(-0.18, 0))
shot('virada+25_olhar_esq_050', views=V4, head=(0, 25, 0), gaze=(0.18, 0), p=0.5)
shot('extra_inclinada25_050', views=('frente', '34'), head=(0, 0, 25), p=0.5)
# sequência de piscada (3/4)
seq = [0, 0, 0.15, 0.35, 0.5, 0.65, 0.85, 1.0, 1.0, 0.7, 0.4, 0.15, 0, 0]
for i, t in enumerate(seq):
    state(p=t, head=(0, 25 * i / (len(seq) - 1), 0)); render(CAMS['frente'], os.path.join(RD, f'seq_{i:02d}.png'), 420)   # pisca enquanto a cabeça vira de 0° a 25°
# corpo inteiro, olhos abertos, para comparar silhueta
state(); sc.render.film_transparent = True
for k, c in BODY_CAMS.items(): render(c, os.path.join(RD, f'exp_corpo_{k}.png'), 700)
json.dump(report, open(os.path.join(OUT, 'olhos-v4-medicoes.json'), 'w'), indent=1)
print('EXP OK')
