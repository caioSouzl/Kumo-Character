"""Olhos em calota com pálpebras novas (pedido do Caio, 26/11, opção 1).

  blender --background kumo_v6_olhos_novos.blend --python src/olhos_calota.py -- <saída.blend>

O olho anterior era uma superfície achatada no lugar da pele: a pálpebra de cima entrava no globo e a íris e a pupila
se deformavam no olhar. Aqui:
- Globo (`KumoOlho_Globo.L/.R`): calota de esfera de 10 cm de altura sobre a abertura, com branco, íris e pupila na
  textura. O olhar gira a calota em volta do centro da esfera (osso `olho.L/.R`, Damped Track no alvo). A calota passa
  um pouco por baixo da pele em volta, para nunca sair da abertura quando gira.
- Anel (`KumoOlho_Anel.L/.R`): as faces de pele em volta do olho (as mesmas de antes), com a pele limpa, a membrana e
  o contorno, vazado na abertura. Fica por cima da borda da calota.
- Pálpebras (`KumoJogo_Palpebra_sup/inf.L/.R`): cascas de esfera um pouco maiores que a calota. A piscada gira a casca
  sobre o globo; os estágios Piscar_25..100 e os drivers no controle_olhos são os mesmos de antes.
"""
import bpy, bmesh, sys, json, math, os
import numpy as np
from mathutils import Vector, Matrix, Quaternion

OUT = sys.argv[-1]
AQUI = os.path.dirname(os.path.abspath(__file__)); OLHO = os.path.dirname(AQUI); PASTA = os.path.dirname(OUT)
os.makedirs(PASTA, exist_ok=True)
INFO = json.load(open(os.path.join(AQUI, 'janelas_v5.json')))
MED = json.load(open(os.path.join(OLHO, 'medicoes_olhos_novos.json')))
V5 = '/home/user/Kumo-Character/kumo-3d-rodin/olhos-v5'; OLDTEX = '/home/user/Kumo-Character/kumo-3d-rodin/v6-dev/olhos-jogo/texturas'
ALTURA = 0.10            # altura da calota acima do plano da abertura
EXTRA_GLOBO = 30.0       # graus de calota além da abertura: cobre o giro do olhar (até 15,6° na diagonal) sem sair da pele
FOLGA_PALP = 0.006       # a pálpebra fica 6 mm acima da calota
ENCONTRO = -8.0          # graus: onde as pálpebras se encontram fechadas (um pouco abaixo do meio)
GAZE_DEG = 11.0; DIST_ALVO = 1.35
ART_C = np.array(MED['arte']['centro_px'], float); ART_R = MED['arte']['raio_externo_px']
img = bpy.data.images.get('kumo_quad_diffuse')
if img: img.filepath = '/home/user/Kumo-Character/kumo-3d-rodin/textures/kumo_quad_diffuse.png'; img.reload()
rig = bpy.data.objects['Kumo_Rig']; pb = rig.pose.bones
if rig.animation_data: rig.animation_data.action = None
for b in pb: b.location = (0, 0, 0); b.rotation_mode = 'QUATERNION'; b.rotation_quaternion = (1, 0, 0, 0)
bpy.context.view_layer.update()
REP = {}


def ler(caminho):
    im = bpy.data.images.load(caminho, check_existing=False)
    a = np.array(im.pixels[:], dtype=np.float32).reshape(im.size[1], im.size[0], 4); bpy.data.images.remove(im); return a


def amostra(a, x, y):
    h, w = a.shape[:2]
    x = np.asarray(x, np.float64) - 0.5; y = np.asarray(y, np.float64) - 0.5
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int); fx = (x - x0)[..., None]; fy = (y - y0)[..., None]
    def px(xx, yy):
        ok = (xx >= 0) & (xx < w) & (yy >= 0) & (yy < h)
        v = a[np.clip(yy, 0, h - 1), np.clip(xx, 0, w - 1)].copy(); v[~ok] = 0; return v
    return px(x0, y0) * (1 - fx) * (1 - fy) + px(x0 + 1, y0) * fx * (1 - fy) + px(x0, y0 + 1) * (1 - fx) * fy + px(x0 + 1, y0 + 1) * fx * fy


def sobre(fundo, topo):
    at = topo[..., 3:4]; ab = fundo[..., 3:4]; ao = at + ab * (1 - at)
    return np.concatenate([(topo[..., :3] * at + fundo[..., :3] * ab * (1 - at)) / np.maximum(ao, 1e-6), ao], -1)


def lin(c):
    c = np.asarray(c, np.float32); return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def salvar(a, nome):
    h, w = a.shape[:2]; im = bpy.data.images.new(nome, w, h, alpha=True)
    im.pixels.foreach_set(np.ascontiguousarray(a, np.float32).ravel())
    p = os.path.join(PASTA, nome + '.png'); im.filepath_raw = p; im.file_format = 'PNG'; im.save(); im.filepath = p; return im


def mat_emissao(nome, im, uv, alfa=False):
    m = bpy.data.materials.new(nome); m.use_nodes = True; N = m.node_tree.nodes; L = m.node_tree.links
    bs = N.get('Principled BSDF'); bs.inputs['Base Color'].default_value = (0, 0, 0, 1); bs.inputs['Roughness'].default_value = 1.0
    bs.inputs['Emission Strength'].default_value = 1.0
    if im is not None:
        t = N.new('ShaderNodeTexImage'); t.image = im; t.extension = 'EXTEND'; u = N.new('ShaderNodeUVMap'); u.uv_map = uv
        L.new(u.outputs['UV'], t.inputs['Vector']); L.new(t.outputs['Color'], bs.inputs['Emission Color'])
        if alfa: L.new(t.outputs['Alpha'], bs.inputs['Alpha'])
    if alfa:
        try: m.surface_render_method = 'DITHERED'
        except Exception: pass
    return m


def mat_cor(nome, cor):
    m = bpy.data.materials.new(nome); m.use_nodes = True; bs = m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value = (0, 0, 0, 1); bs.inputs['Roughness'].default_value = 1.0
    bs.inputs['Emission Color'].default_value = tuple(cor) + (1,); bs.inputs['Emission Strength'].default_value = 1.0; return m


def janela(Mw, P, U0, U1):
    Mi = Mw.inverted(); q = Mi @ P; return (((q.x + 1) / 2 - U0) / (U1 - U0), ((q.y + 1) / 2 - U0) / (U1 - U0))


# íris e pupila (a arte do Caio, anel âmbar escuro) e o branco off-white
IP = ler(os.path.join(OLHO, 'arte', 'iris-pupila.png'))
anel = (IP[..., 3] > 0.5) & (IP[..., 0] > 0.5) & (IP[..., 2] < 0.6); IP[anel, :3] = lin(np.array([0xDE, 0x9C, 0x1E]) / 255)
BRANCO = lin(np.array([0xF7, 0xF3, 0xEA]) / 255)

DADOS = {}
for s in 'LR':
    R_ = {}
    Mw = Matrix(INFO[s]['Mw']); zw = (Mw.to_3x3() @ Vector((0, 0, 1))).normalized()
    e1 = (Mw.to_3x3() @ Vector((1, 0, 0))); e1 = (e1 - zw * e1.dot(zw)).normalized(); e2 = zw.cross(e1).normalized()
    U0, U1 = MED[s]['janela_da_textura']
    mask = ler(os.path.join(V5, 'textures', f'olho_{s}_mask.png'))[..., 3]; MH = mask.shape[0]
    yy, xx = np.nonzero(mask > 0.5); cm = np.array([(xx.mean() + 0.5) / MH, (yy.mean() + 0.5) / MH])
    cov = np.cov(np.vstack([(xx + 0.5) / MH - cm[0], (yy + 0.5) / MH - cm[1]])); ev, evec = np.linalg.eigh(cov)
    EA, EB = 2 * math.sqrt(ev[1]), 2 * math.sqrt(ev[0]); EANG = math.atan2(evec[1, 1], evec[0, 1])
    def rb_at(th, EA=EA, EB=EB, EANG=EANG):
        t = np.asarray(th) - EANG; return EA * EB / np.sqrt((EB * np.cos(t)) ** 2 + (EA * np.sin(t)) ** 2)
    r_med = float(rb_at(np.linspace(0, 2 * math.pi, 720)).mean())

    # ---------- anel: a superfície de pele de antes, vazada na abertura
    anel_o = bpy.data.objects[f'KumoOlho.{s}']; anel_o.name = anel_o.data.name = f'KumoOlho_Anel.{s}'
    Vp = np.array([tuple(anel_o.matrix_world @ v.co) for v in anel_o.data.vertices]); Cp = Vp.mean(0); zn = np.array(tuple(zw))
    ring = []
    for t in np.linspace(0, 2 * math.pi, 96, endpoint=False):
        r = float(rb_at(t)); p = np.array(tuple(Mw @ Vector((2 * (cm[0] + r * math.cos(t)) - 1, 2 * (cm[1] + r * math.sin(t)) - 1, 0))))
        ring.append(p - zn * ((p - Cp) @ zn))
    ring = np.array(ring); Cc = ring.mean(0); relp = ring - Cc; relp -= np.outer(relp @ zn, zn)
    a = float(np.sqrt((relp ** 2).sum(1)).mean())
    Rg = (a * a + ALTURA * ALTURA) / (2 * ALTURA); Cs = Vector(Cc) + zw * (ALTURA - Rg)
    phimax = math.asin(min(1.0, a / Rg))
    R_.update(abertura_raio_m=round(a, 4), globo_raio_m=round(Rg, 4), abertura_angulo_graus=round(math.degrees(phimax), 1))
    # textura do anel: a pele (da textura do corpo), a faixa limpa e a membrana + contorno, gravadas na UV 'Jogo'
    me = anel_o.data
    jan = me.uv_layers['Janela']; jg = me.uv_layers.get('Jogo') or me.uv_layers.new(name='Jogo')
    for i, d in enumerate(jan.data): jg.data[i].uv = ((d.uv[0] - U0) / (U1 - U0), (d.uv[1] - U0) / (U1 - U0))
    mold = anel_o.material_slots[0].material
    for n in list(mold.node_tree.nodes):           # tira o decal antigo (a íris agora mora no globo)
        if n.type == 'TEX_COORD':
            for l in list(n.outputs['Object'].links): mold.node_tree.links.remove(l)
    for n in mold.node_tree.nodes:
        if n.type == 'MATH' and n.operation == 'MULTIPLY':
            for l in list(n.inputs[0].links): mold.node_tree.links.remove(l)
            n.inputs[0].default_value = 0.0
    RESB = 1536
    imb = bpy.data.images.new(f'olho_{s}_anel_cor', RESB, RESB, alpha=False)
    tb = mold.node_tree.nodes.new('ShaderNodeTexImage'); tb.image = imb
    for n in mold.node_tree.nodes: n.select = False
    tb.select = True; mold.node_tree.nodes.active = tb; me.uv_layers.active = jg
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = 4; sc.render.bake.use_selected_to_active = False
    for o in bpy.context.selected_objects: o.select_set(False)
    anel_o.hide_set(False); anel_o.select_set(True); bpy.context.view_layer.objects.active = anel_o
    bpy.ops.object.bake(type='EMIT', margin=8, use_clear=True)
    cor = np.array(imb.pixels[:], np.float32).reshape(RESB, RESB, 4)
    g = (np.arange(RESB) + 0.5) / RESB; gx, gy = np.meshgrid(g, g); wu = U0 + gx * (U1 - U0); wv = U0 + gy * (U1 - U0)
    aro = ler(os.path.join(OLHO, 'texturas', f'olho_{s}_aro.png')); den = ler(os.path.join(OLHO, 'texturas', f'olho_{s}_dentro.png'))
    aro_r = amostra(aro, gx * aro.shape[1], gy * aro.shape[0]); den_r = amostra(den, gx * den.shape[1], gy * den.shape[0])[..., 0]
    cor[..., 3] = np.clip(np.maximum(1.0 - den_r, aro_r[..., 3]), 0, 1)
    im_anel = salvar(cor, f'olho_{s}_anel')
    anel_o.material_slots[0].material = mat_emissao(f'KumoOlho_Anel.{s}', im_anel, 'Jogo', alfa=True)
    # tira do anel as faces que ficam inteiras dentro da abertura (vazadas de todo jeito)
    Mi = Mw.inverted()
    def q_de(p):
        qq = Mi @ p; u, v = (qq.x + 1) / 2 - cm[0], (qq.y + 1) / 2 - cm[1]; return math.hypot(u, v) / float(rb_at(math.atan2(v, u)))
    bm = bmesh.new(); bm.from_mesh(me)
    dentro = [f for f in bm.faces if all(q_de(anel_o.matrix_world @ v.co) < 0.85 for v in f.verts)]
    bmesh.ops.delete(bm, geom=dentro, context='FACES'); bm.to_mesh(me); bm.free(); me.update()
    R_['anel_faces_tiradas'] = len(dentro)

    # ---------- globo: calota de esfera, além da abertura por EXTRA_GLOBO graus
    NPHI, NTH = 48, 128
    phig = phimax + math.radians(EXTRA_GLOBO)
    V = []; F = []
    for i in range(NPHI + 1):
        ph = phig * i / NPHI
        for j in range(NTH):
            th = 2 * math.pi * j / NTH
            V.append(Cs + (e1 * (math.sin(ph) * math.cos(th)) + e2 * (math.sin(ph) * math.sin(th)) + zw * math.cos(ph)) * Rg)
    for i in range(NPHI):
        for j in range(NTH):
            a0 = i * NTH + j; a1 = i * NTH + (j + 1) % NTH; b0 = (i + 1) * NTH + j; b1 = (i + 1) * NTH + (j + 1) % NTH
            F.append((a0, b0, b1, a1))
    gm = bpy.data.meshes.new(f'KumoOlho_Globo.{s}'); gm.from_pydata([tuple(v) for v in V], [], F)
    uvg = gm.uv_layers.new(name='Jogo')
    for lp in gm.loops: uvg.data[lp.index].uv = janela(Mw, V[lp.vertex_index], U0, U1)
    for p in gm.polygons: p.use_smooth = True
    gm.update()
    if sum((gm.polygons[k].normal.dot(gm.polygons[k].center - Cs)) for k in range(0, len(gm.polygons), 50)) < 0: gm.flip_normals()
    # textura do globo: branco + íris e pupila (na janela), girando junto com a calota
    RESG = 1536; g = U0 + (np.arange(RESG) + 0.5) / RESG * (U1 - U0); gx, gy = np.meshgrid(g, g)
    ic = np.array(INFO[s]['iris_centro']); esc = ART_R / r_med
    tex = np.zeros((RESG, RESG, 4), np.float32); tex[..., :3] = BRANCO; tex[..., 3] = 1
    tex = sobre(tex, amostra(IP, ART_C[0] + (gx - ic[0]) * esc, ART_C[1] + (gy - ic[1]) * esc)); tex[..., 3] = 1
    gm.materials.append(mat_emissao(f'KumoOlho_Globo.{s}', salvar(tex, f'olho_{s}_globo'), 'Jogo'))
    go = bpy.data.objects.new(f'KumoOlho_Globo.{s}', gm); bpy.context.scene.collection.objects.link(go)
    go.parent = rig; am = go.modifiers.new('Armature', 'ARMATURE'); am.object = rig
    go.vertex_groups.new(name=f'olho.{s}').add(range(len(V)), 1.0, 'REPLACE')

    # ---------- pálpebras: cascas de esfera sobre o globo, que giram para fechar
    up = Vector((0, 0, 1)); u = (up - zw * up.dot(zw)).normalized(); hax = zw.cross(u).normalized()
    Rl = Rg + FOLGA_PALP; lat = phimax + math.radians(8)
    def pt(psi, beta):
        return Cs + (zw * (math.cos(beta) * math.cos(psi)) + u * (math.cos(beta) * math.sin(psi)) + hax * math.sin(beta)) * Rl
    psim = math.radians(ENCONTRO); topo = phimax + math.radians(10); base = -(phimax + math.radians(10))
    abre_sup = (phimax + math.radians(6)) - psim; abre_inf = -((phimax + math.radians(6)) + psim)
    old = {k: bpy.data.objects.get(f'KumoJogo_Palpebra_{k}.{s}') for k in ('sup', 'inf', 'sup_borda', 'inf_borda')}
    drv = None
    kd = old['sup'].data.shape_keys.animation_data.drivers
    for fc in kd:
        if fc.data_path.endswith('"Piscar_25"].value'): drv = (fc.driver.variables[0].targets[0].bone_target, fc.driver.variables[0].targets[0].transform_type)
    EXPR = {fc.data_path: fc.driver.expression for fc in kd}
    # cores: a pele da pálpebra antiga e a linha escura da borda
    cp = ler(os.path.join(OLDTEX, f'olho_{s}_palpebra.png')); cb = ler(os.path.join(OLDTEX, f'olho_{s}_palpebra_borda.png'))
    fora = (den_r < 0.01) & (aro_r[..., 3] < 0.01)
    cor_pele = lin(np.median(cor[fora][:, :3], 0))                # a pele em volta do olho (do anel; a textura guarda sRGB)
    cor_borda = lin(np.array([0x5B, 0x3A, 0x2E]) / 255)           # o marrom do contorno
    for k_, o_ in old.items():
        if o_: bpy.data.objects.remove(o_)
    for lado, (p0, p1, abre) in (('sup', (psim, topo, abre_sup)), ('inf', (base, psim, abre_inf))):
        NP, NB = 36, 64
        pss = [p0 + (p1 - p0) * i / NP for i in range(NP + 1)]; bs = [-lat + 2 * lat * j / NB for j in range(NB + 1)]
        Vl = [pt(ps, b_) for ps in pss for b_ in bs]
        Fl = [(i * (NB + 1) + j, i * (NB + 1) + j + 1, (i + 1) * (NB + 1) + j + 1, (i + 1) * (NB + 1) + j) for i in range(NP) for j in range(NB)]
        lm = bpy.data.meshes.new(f'KumoJogo_Palpebra_{lado}.{s}'); lm.from_pydata([tuple(v) for v in Vl], [], Fl)
        lm.materials.append(mat_cor(f'KumoJogo_Palpebra_{lado}.{s}', cor_pele)); lm.materials.append(mat_cor(f'KumoJogo_Palpebra_{lado}_borda.{s}', cor_borda))
        # a faixa da borda (a beira que fecha): ~2,5° de largura
        borda_i = 0 if lado == 'sup' else NP - 1
        nb = max(1, int(round(math.radians(2.5) / ((p1 - p0) / NP))))
        for fi, f in enumerate(lm.polygons):
            i = fi // NB
            f.material_index = 1 if (lado == 'sup' and i < nb) or (lado == 'inf' and i >= NP - nb) else 0
            f.use_smooth = True
        lm.update()
        if sum(lm.polygons[k].normal.dot(lm.polygons[k].center - Cs) for k in range(0, len(lm.polygons), 40)) < 0: lm.flip_normals()
        lo = bpy.data.objects.new(f'KumoJogo_Palpebra_{lado}.{s}', lm); bpy.context.scene.collection.objects.link(lo)
        lo.parent = rig; am = lo.modifiers.new('Armature', 'ARMATURE'); am.object = rig
        lo.vertex_groups.new(name='head').add(range(len(Vl)), 1.0, 'REPLACE')
        # a beira desce (ou sobe) até o encontro; o outro lado da faixa fica fixo além da abertura, escondido sob a pele.
        # Aberta, a faixa toda cabe entre a borda da abertura (+3°) e o lado fixo.
        fixo = p1 if lado == 'sup' else p0
        beira_aberta = (phimax + math.radians(3)) if lado == 'sup' else -(phimax + math.radians(3))
        def estagio(t):
            beira = beira_aberta + (psim - beira_aberta) * t
            return [pt(beira + (ps - psim) / (fixo - psim) * (fixo - beira), b_) for ps in pss for b_ in bs]
        for i, v in enumerate(estagio(0.0)): lm.vertices[i].co = v
        lo.shape_key_add(name='Basis', from_mix=False)
        for t in (0.25, 0.5, 0.75, 1.0):
            kb = lo.shape_key_add(name=f'Piscar_{int(t * 100)}', from_mix=False)
            for i, v in enumerate(estagio(t)): kb.data[i].co = v
        for kb in lo.data.shape_keys.key_blocks[1:]:
            fc = kb.driver_add('value'); d = fc.driver; d.type = 'SCRIPTED'
            var = d.variables.new(); var.name = 'p'; var.type = 'TRANSFORMS'; var.targets[0].id = rig
            var.targets[0].bone_target = drv[0]; var.targets[0].transform_type = drv[1]; var.targets[0].transform_space = 'LOCAL_SPACE'
            d.expression = EXPR[f'key_blocks["{kb.name}"].value']
    # ---------- membrana + contorno: faixa de esfera fixa na borda, logo acima da calota (o globo gira por baixo)
    Ra = Rg + 0.003; NA, NT = 10, 160
    NA = 24; fim = phig + math.radians(2)
    fa = [phimax * 0.82 + (fim - phimax * 0.82) * i / NA for i in range(NA + 1)]
    Va = [Cs + (e1 * (math.sin(f_) * math.cos(2 * math.pi * j / NT)) + e2 * (math.sin(f_) * math.sin(2 * math.pi * j / NT)) + zw * math.cos(f_)) * Ra for f_ in fa for j in range(NT)]
    Fa = [(i * NT + j, (i + 1) * NT + j, (i + 1) * NT + (j + 1) % NT, i * NT + (j + 1) % NT) for i in range(NA) for j in range(NT)]
    amesh = bpy.data.meshes.new(f'KumoOlho_Aro.{s}'); amesh.from_pydata([tuple(v) for v in Va], [], Fa)
    uva = amesh.uv_layers.new(name='Jogo')
    for lp in amesh.loops: uva.data[lp.index].uv = janela(Mw, Va[lp.vertex_index], U0, U1)
    amesh.update()
    if sum(amesh.polygons[k].normal.dot(amesh.polygons[k].center - Cs) for k in range(0, len(amesh.polygons), 40)) < 0: amesh.flip_normals()
    # a faixa usa a textura do anel: membrana e contorno na borda, pele fora da abertura, vazada dentro.
    # Assim ela cobre a calota onde a abertura (elipse) é mais estreita que a calota (círculo).
    amesh.materials.append(mat_emissao(f'KumoOlho_Aro.{s}', im_anel, 'Jogo', alfa=True))
    ao = bpy.data.objects.new(f'KumoOlho_Aro.{s}', amesh); bpy.context.scene.collection.objects.link(ao)
    ao.parent = rig; amo = ao.modifiers.new('Armature', 'ARMATURE'); amo.object = rig
    ao.vertex_groups.new(name='head').add(range(len(Va)), 1.0, 'REPLACE')
    R_.update(palpebra_abre_sup_graus=round(math.degrees(abre_sup), 1), palpebra_abre_inf_graus=round(math.degrees(abre_inf), 1), driver=list(drv))
    DADOS[s] = dict(Cs=Cs, zw=zw); REP[s] = R_

# ---------- aparo: faces do globo e da faixa que, além da abertura, ficam por fora da pele (bochecha que recua)
from mathutils.bvhtree import BVHTree
dg = bpy.context.evaluated_depsgraph_get(); VV = []; TT = []
for n in ('Kumo', 'KumoOlho_Anel.L', 'KumoOlho_Anel.R'):
    o = bpy.data.objects[n].evaluated_get(dg); m = o.to_mesh(); m.calc_loop_triangles(); off = len(VV)
    VV += [o.matrix_world @ v.co for v in m.vertices]; TT += [tuple(off + i for i in t.vertices) for t in m.loop_triangles]; o.to_mesh_clear()
pele = BVHTree.FromPolygons(VV, TT)
o_ = bpy.data.objects['Kumo_Boca'].evaluated_get(dg); m_ = o_.to_mesh(); m_.calc_loop_triangles()
boca = BVHTree.FromPolygons([o_.matrix_world @ v.co for v in m_.vertices], [tuple(t.vertices) for t in m_.loop_triangles]); o_.to_mesh_clear()
for s in 'LR':
    Cs = DADOS[s]['Cs']; zw = DADOS[s]['zw']; ang_ab = math.radians(REP[s]['abertura_angulo_graus'])
    # tampa da boca: a parte da faixa que fica atrás da fenda da boca, na cor de dentro da boca.
    # O globo passa ali quando olha para baixo; a tampa esconde ele sem mostrar o desenho da faixa.
    ao = bpy.data.objects[f'KumoOlho_Aro.{s}']; tm = ao.data.copy(); tm.name = f'KumoOlho_Tampa.{s}'
    perto = [boca.find_nearest(ao.matrix_world @ v.co, 0.04)[0] is not None
             and ((ao.matrix_world @ v.co) - Cs).normalized().angle(zw) > ang_ab + math.radians(2) for v in tm.vertices]
    bm = bmesh.new(); bm.from_mesh(tm)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if not any(perto[v.index] for v in f.verts)], context='FACES')
    bm.to_mesh(tm); bm.free(); tm.materials.clear(); tm.materials.append(bpy.data.materials['Kumo_Boca_Interior'])
    if len(tm.polygons):
        to = bpy.data.objects.new(f'KumoOlho_Tampa.{s}', tm); bpy.context.scene.collection.objects.link(to)
        to.parent = rig; mo_ = to.modifiers.new('Armature', 'ARMATURE'); mo_.object = rig
        to.vertex_groups.new(name='head').add(range(len(tm.vertices)), 1.0, 'REPLACE')
    REP[s]['tampa_boca_faces'] = len(tm.polygons)
    for nome in (f'KumoOlho_Globo.{s}', f'KumoOlho_Aro.{s}'):
        o = bpy.data.objects[nome]; me = o.data
        gira = nome.startswith('KumoOlho_Globo')
        eixos = [zw.orthogonal().normalized()]; eixos.append(zw.cross(eixos[0]).normalized())
        poses = [Matrix.Identity(3)]
        if gira:   # o globo gira com o olhar: confere as 8 direções extremas do controle
            for ax, ay in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
                ang = math.radians(GAZE_DEG) * (1 if ax*ay == 0 else 1.414)
                poses.append(Matrix.Rotation(ang, 3, (eixos[0]*ax + eixos[1]*ay).normalized()))
        def fora(v):
            p = o.matrix_world @ v.co
            ang = (p - Cs).normalized().angle(zw)
            if gira:
                if ang > ang_ab + math.radians(GAZE_DEG + 2): return True     # globo: o que nunca chega à abertura
                qs = [Cs + R @ (p - Cs) for R in poses]
                if any((q - Cs).normalized().angle(zw) < ang_ab + math.radians(1) for q in qs): return False   # aparece na abertura em algum olhar
                return any(boca.find_nearest(q, 0.04)[0] is not None for q in qs)   # nunca na abertura e passaria pela boca
            if ang < ang_ab + math.radians(2): return False
            if boca.find_nearest(p, 0.04)[0] is not None: return True     # perto da boca: a faixa projetaria o desenho da boca
            loc, nrm, _, _ = pele.find_nearest(p)
            if loc is not None and (p - loc).dot(nrm) < -0.008: return True     # bem por dentro da pele: o globo também está, não precisa cobrir
            if ang < ang_ab + math.radians(GAZE_DEG + 2 + GAZE_DEG * 1.414 + 1): return False     # faixa: cobre o globo enquanto ele gira
            for R in poses:
                q = Cs + R @ (p - Cs)
                loc, nrm, _, _ = pele.find_nearest(q)
                if loc is not None and (q - loc).dot(nrm) > 0.002: return True
            return False
        marca = [fora(v) for v in me.vertices]
        if gira:   # o que fica e ainda sairia da pele em algum olhar (perto da mandíbula): afunda só esse ponto
            afund = 0
            for v in me.vertices:
                if marca[v.index]: continue
                p = o.matrix_world @ v.co
                if (p - Cs).normalized().angle(zw) < ang_ab + math.radians(6): continue   # perto da borda fica redondo
                dmax = 0.0
                for R in poses:
                    q = Cs + R @ (p - Cs); loc, nrm, _, _ = pele.find_nearest(q)
                    if loc is not None: dmax = max(dmax, (q - loc).dot(nrm))
                if dmax > 0.002:
                    novo = Cs + (p - Cs) * (1 - (dmax + 0.004) / (p - Cs).length)
                    v.co = o.matrix_world.inverted() @ novo; afund += 1
            REP[s]['globo_pontos_afundados'] = afund
        bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
        tira = [f for f in bm.faces if any(marca[v.index] for v in f.verts)]
        bmesh.ops.delete(bm, geom=tira, context='FACES')
        if not gira:   # a faixa fica só com o pedaço maior (ilhas soltas mostrariam a textura fora do lugar)
            bm.faces.ensure_lookup_table(); visto = set(); ilhas = []
            for f0 in bm.faces:
                if f0.index in visto: continue
                pilha = [f0]; ilha = []; visto.add(f0.index)
                while pilha:
                    f = pilha.pop(); ilha.append(f)
                    for e in f.edges:
                        for g in e.link_faces:
                            if g.index not in visto: visto.add(g.index); pilha.append(g)
                ilhas.append(ilha)
            ilhas.sort(key=len)
            soltas = [f for il in ilhas[:-1] for f in il]
            if soltas: bmesh.ops.delete(bm, geom=soltas, context='FACES')
            REP[s]['aro_ilhas_tiradas'] = len(ilhas) - 1
        bm.to_mesh(me); bm.free(); me.update()
        REP[s][f'aparo_{nome.split("_")[1].split(".")[0]}'] = len(tira)

# ---------- ossos do olho: base no centro da esfera do globo; alvo do Damped Track a 1,35 m
for s in 'LR':
    e = bpy.data.objects.get(f'Decal_Olho.{s}')
    if e: bpy.data.objects.remove(e)
bpy.context.view_layer.objects.active = rig
for o in bpy.context.selected_objects: o.select_set(False)
rig.select_set(True); bpy.ops.object.mode_set(mode='EDIT'); eb = rig.data.edit_bones
for s, d in DADOS.items():
    b = eb[f'olho.{s}']; b.head = d['Cs']; b.tail = d['Cs'] + d['zw'] * 0.1; b.use_deform = True
    t = eb[f'MCH_alvo_olho.{s}']; t.head = d['Cs'] + d['zw'] * DIST_ALVO; t.tail = t.head + d['zw'] * 0.08
bpy.ops.object.mode_set(mode='OBJECT')
k = math.tan(math.radians(GAZE_DEG)) * DIST_ALVO
for s in 'LR':
    c = pb[f'MCH_alvo_olho.{s}'].constraints['Olhar']
    sx = 1 if c.to_max_x >= 0 else -1; sz = 1 if c.to_max_z >= 0 else -1
    c.to_min_x, c.to_max_x = -k * sx, k * sx; c.to_min_z, c.to_max_z = -k * sz, k * sz
bpy.context.view_layer.update()
json.dump(REP, open(os.path.join(PASTA, 'medicoes_calota.json'), 'w'), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print('CAL', json.dumps(REP))
