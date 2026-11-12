"""Kumo · olhos da v5 convertidos para jogo, com a MESMA aparência (pedido do Caio, 2026-11-12).

  python olhos_jogo.py <olhos-v5/kumo_eyes_exp.blend> <saída>

Por que converter: a v5 desenha o olho com camadas finas presas à pele por Geometry Nodes e textura projetada
de vazios (Kumo_EyeWindow / Kumo_EyeGaze); a piscada é um recorte no material (tabela de borda) e o olhar desliza
a textura. Nada disso vai para GLB/FBX. Aqui tudo vira malha com UV fixa, textura simples e shape keys:

- olho base (fundo do olho): malha da camada em repouso, UV = coordenada da janela; textura = olho × máscara (exato).
- íris, pupila e brilho: mesma malha; UV = coordenada do olhar em repouso. O olhar é shape key: cada vértice vai
  para onde a textura dele cairia com o olho girado (raio pela projeção girada até a própria casca).
- pálpebras: malha nova em grade, no espaço da janela, do contorno da borda até o fim da máscara. Cada estágio
  da piscada (25/50/75/100 %) é uma shape key: a grade é recolocada sobre a casca da v5 naquele estágio (com o
  relevo da borda), e a faixa escura da borda é uma tira própria. As formas intermediárias seguem a curva da pele.
- pesos: copiados da pele (Kumo_Olhos_PeleRef) no ponto mais próximo, até 4 ossos, soma 1.
Depois compara renders da v5 contra a conversão, nos mesmos estados, pixel a pixel.
"""
import bpy, bmesh, sys, os, json, math
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
from mathutils.geometry import barycentric_transform, intersect_point_tri_2d

SRC, OUT = sys.argv[-2:]; os.makedirs(os.path.join(OUT, 'texturas'), exist_ok=True); os.makedirs(os.path.join(OUT, 'renders'), exist_ok=True)
V5 = os.path.dirname(os.path.abspath(SRC)); TEX = os.path.join(V5, 'textures')
GAZE_DEG = float(os.environ.get('OJ_OLHAR', '11'))
ESTAGIOS = [0.25, 0.5, 0.75, 1.0]
REP = {}
bpy.ops.wm.open_mainfile(filepath=SRC); sc = bpy.context.scene
for im in bpy.data.images:                                  # caminhos relativos da v5
    if im.filepath and not os.path.exists(bpy.path.abspath(im.filepath)):
        for d_ in (TEX, os.path.join(V5, '..', 'textures')):
            p = os.path.join(d_, os.path.basename(im.filepath))
            if os.path.exists(p): im.filepath = p; im.reload(); break
rig = bpy.data.objects['Kumo_Rig']; pb = rig.pose.bones; H = pb['head']; body = bpy.data.objects['Kumo']
pele = bpy.data.objects['Kumo_Olhos_PeleRef']
LASH = tuple(bpy.data.materials['Kumo_Lash'].node_tree.nodes['Emission'].inputs['Color'].default_value)[:3]
BW = 0.021153846755623817                                   # largura da faixa escura da borda (no espaço 0..1 da janela)

def img_np(name):
    im = bpy.data.images[name]; w, h = im.size; a = np.empty(w * h * 4, np.float32); im.pixels.foreach_get(a); return a.reshape(h, w, 4)
def amostra(a, u, v):
    h, w = a.shape[:2]; x = np.clip(u * w - 0.5, 0, w - 1.001); y = np.clip(v * h - 0.5, 0, h - 1.001)
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int); fx = (x - x0)[..., None]; fy = (y - y0)[..., None]
    r = a[y0, x0] * (1 - fx) * (1 - fy) + a[y0, x0 + 1] * fx * (1 - fy) + a[y0 + 1, x0] * (1 - fx) * fy + a[y0 + 1, x0 + 1] * fx * fy
    fora = ((u < 0) | (u > 1) | (v < 0) | (v > 1))[..., None]
    return np.where(fora, 0, r)
def salvar_png(a, nome):
    h, w = a.shape[:2]; im = bpy.data.images.new(nome, w, h, alpha=True); im.pixels.foreach_set(np.ascontiguousarray(a, np.float32).ravel())
    p = os.path.join(OUT, 'texturas', nome + '.png'); im.filepath_raw = p; im.file_format = 'PNG'; im.save(); return im

def controles(piscar=0.0, pE=0.0, pD=0.0, olhar=None):
    for k, v in (('piscar', piscar), ('piscar_E', pE), ('piscar_D', pD), ('fechar_parcial_E', 0.0), ('fechar_parcial_D', 0.0)): H[k] = v
    pb['eye_target'].location = (0, 0, 0)
    for s in 'LR':
        b = pb[f'eye.{s}']; b.constraints[0].influence = 0.0 if olhar else 1.0
        b.rotation_mode = 'XYZ'; b.rotation_euler = (0, 0, 0)
        if olhar: b.rotation_euler = (math.radians(olhar[1]), 0, math.radians(olhar[0]))   # (guinada em Z local, arfagem em X local)
    rig.update_tag(); bpy.context.view_layer.update(); bpy.context.evaluated_depsgraph_get().update()

def avaliar(o):
    dg = bpy.context.evaluated_depsgraph_get(); ev = o.evaluated_get(dg); m = ev.to_mesh(); m.calc_loop_triangles()
    V = np.array([tuple(ev.matrix_world @ v.co) for v in m.vertices]); T = [tuple(t.vertices) for t in m.loop_triangles]
    ev.to_mesh_clear(); return V, T
def coords(M, V):
    Mi = np.array(M.inverted()); P = np.c_[V, np.ones(len(V))] @ Mi.T; return 0.5 + 0.5 * P[:, 0], 0.5 + 0.5 * P[:, 1]

# ---------- pesos da pele no ponto mais próximo (repouso)
controles()
dg = bpy.context.evaluated_depsgraph_get(); evp = pele.evaluated_get(dg); mp_ = evp.to_mesh(); mp_.calc_loop_triangles()
PV = [evp.matrix_world @ v.co for v in mp_.vertices]; PT = [tuple(t.vertices) for t in mp_.loop_triangles]; evp.to_mesh_clear()
bvh_pele = BVHTree.FromPolygons(PV, PT)
gi = {g.index: g.name for g in pele.vertex_groups}; ossos = {b.name for b in rig.data.bones if b.use_deform}
PW = [{gi[g.group]: g.weight for g in v.groups if gi[g.group] in ossos and g.weight > 1e-5} for v in pele.data.vertices]
def pesos_em(p):
    loc, nor, fi, d = bvh_pele.find_nearest(Vector(p)); a, b, c = PT[fi]
    w3 = barycentric_transform(loc, PV[a], PV[b], PV[c], Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)))
    acc = {}
    for vi, wv in zip((a, b, c), w3):
        for n, x in PW[vi].items(): acc[n] = acc.get(n, 0) + x * max(0.0, wv)
    top = sorted(acc.items(), key=lambda kv: -kv[1])[:4]; s = sum(x for _, x in top) or 1.0
    return {n: x / s for n, x in top}

def novo_obj(nome, V, F, uv, mat, pesos=True):
    me = bpy.data.meshes.new(nome); me.from_pydata([tuple(v) for v in V], [], F); me.update()
    ul = me.uv_layers.new(name='UVMap')
    for p in me.polygons:
        for li in p.loop_indices: ul.data[li].uv = uv[me.loops[li].vertex_index]
    me.materials.append(mat); o = bpy.data.objects.new(nome, me); sc.collection.objects.link(o)
    if pesos:
        for i, v in enumerate(V):
            for n, x in pesos_em(v).items():
                g = o.vertex_groups.get(n) or o.vertex_groups.new(name=n); g.add([i], x, 'REPLACE')
        o.parent = rig; m = o.modifiers.new('Armature', 'ARMATURE'); m.object = rig
    return o
def material_img(nome, im, blend=True):
    m = bpy.data.materials.new(nome); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = im; t.extension = 'CLIP'; t.interpolation = 'Linear'
    em = nt.nodes.new('ShaderNodeEmission'); tr = nt.nodes.new('ShaderNodeBsdfTransparent'); mx = nt.nodes.new('ShaderNodeMixShader'); out = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(t.outputs['Color'], em.inputs['Color']); nt.links.new(t.outputs['Alpha'], mx.inputs['Fac'])
    nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(em.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], out.inputs['Surface'])
    m.blend_method = 'BLEND' if hasattr(m, 'blend_method') else None
    return m

NOVOS = {}
for s in 'LR':
    win = bpy.data.objects[f'Kumo_EyeWindow_{s}']; gaze = bpy.data.objects[f'Kumo_EyeGaze_{s}']
    Mw = win.matrix_world.copy(); Mg = gaze.matrix_world.copy()
    mask = img_np(f'olho_{s}_mask'); REP.setdefault('olhos', {})[s] = {}
    # ---------------- olho base: olho × máscara (mesmo espaço)
    eye = img_np(f'olho_{s}_eye'); base = eye.copy(); base[..., 3] *= mask[..., 3]
    o_src = bpy.data.objects[f'Kumo_Eye_{s}']; V, T = avaliar(o_src); u, v = coords(Mw, V)
    NOVOS[f'base_{s}'] = novo_obj(f'KumoJogo_OlhoBase.{s}', V, T, list(zip(u, v)), material_img(f'KumoJogo_OlhoBase.{s}', salvar_png(base, f'olho_{s}_base')))
    # ---------------- íris, pupila, brilho (textura do olhar; a máscara da janela é conferida abaixo)
    for nome, img in (('Iris', 'iris'), ('Pupil', 'pupil'), ('Catchlight', 'catch')):
        a = img_np(f'olho_{s}_{img}'); o_src = bpy.data.objects[f'Kumo_{nome}_{s}']; V, T = avaliar(o_src); u, v = coords(Mg, V)
        # quanto da textura (alpha) fica fora da janela em repouso: se é ~0, tirar a máscara não muda nada
        al = amostra(a, u, v)[:, 3]; am = amostra(mask, *coords(Mw, V))[:, 3]
        REP['olhos'][s][f'{nome}_alpha_fora_da_janela'] = round(float((al * (1 - am)).sum() / max(1e-6, al.sum())), 4)
        # malha própria, só onde a textura existe (com margem), fina: a decalcomania inteira cabe dentro da janela no olhar
        ys_, xs_ = np.nonzero(a[..., 3] > 0.003); hh, ww = a.shape[:2]
        mg = 0.03; u0, u1 = xs_.min() / ww - mg, (xs_.max() + 1) / ww + mg; v0, v1 = ys_.min() / hh - mg, (ys_.max() + 1) / hh + mg
        OFF = {'Iris': 0.00015, 'Pupil': 0.0003, 'Catchlight': 0.00045}
        NG = 40; GU = np.linspace(u0, u1, NG + 1); GV = np.linspace(v0, v1, NG + 1)
        bvh = BVHTree.FromPolygons([Vector(x) for x in V], T)
        b = rig.data.bones[f'eye.{s}']; C = rig.matrix_world @ b.head_local; Mb = (rig.matrix_world @ b.matrix_local).to_3x3()
        def projeta(M):
            zd = (M.to_3x3() @ Vector((0, 0, 1))).normalized(); P = []; falhas = 0
            for vv in GV:
                for uu in GU:
                    o_ = M @ Vector((2 * uu - 1, 2 * vv - 1, 0.0)); hit = bvh.ray_cast(o_ + zd * 0.6, -zd, 1.2)   # superfície da frente
                    if hit[0] is None:      # fora da casca: continua a superfície (mesma profundidade do ponto mais próximo)
                        q = bvh.find_nearest(o_)[0]; lq = M.inverted() @ q; P.append(M @ Vector((2 * uu - 1, 2 * vv - 1, lq.z))); falhas += 1
                    else: P.append(hit[0])
            # afasta um pouco para a frente (para a câmera), na ordem da v5: íris < pupila < brilho (evita mistura de camadas)
            P = [p_ + zd * OFF[nome] for p_ in P]
            return P, falhas
        P0, f0 = projeta(Mg)
        F = [(k * (NG + 1) + j, k * (NG + 1) + j + 1, (k + 1) * (NG + 1) + j + 1, (k + 1) * (NG + 1) + j) for k in range(NG) for j in range(NG)]
        uvg = [(uu, vv) for vv in GV for uu in GU]
        ob = novo_obj(f'KumoJogo_{nome}.{s}', P0, F, uvg, material_img(f'KumoJogo_{nome}.{s}', salvar_png(a, f'olho_{s}_{img}')))
        REP['olhos'][s][f'{nome}_repouso_sem_acerto'] = f0
        ob.shape_key_add(name='Basis', from_mix=False)
        alg = amostra(a, np.array([q[0] for q in uvg]), np.array([q[1] for q in uvg]))[:, 3]
        def fora(P):
            uw, vw = coords(Mw, np.array([tuple(x) for x in P])); am = amostra(mask, uw, vw)[:, 3]
            return float((alg * (1 - am)).sum() / max(1e-6, alg.sum()))
        for kn, eixo, ang in (('Olhar_dir', 2, GAZE_DEG), ('Olhar_esq', 2, -GAZE_DEG), ('Olhar_cima', 0, GAZE_DEG), ('Olhar_baixo', 0, -GAZE_DEG)):
            # registra quanto sai da janela em cada ângulo (para escolher o alcance que a v5 mostra sem recorte)
            for a_deg in (4, 6, 8, 10, 11):
                Rm = Matrix.Translation(C) @ Matrix.Rotation(math.radians(math.copysign(a_deg, ang)), 4, Mb.col[eixo].normalized()) @ Matrix.Translation(-C)
                REP['olhos'][s].setdefault(f'{nome}_{kn}_fora_da_janela', {})[a_deg] = round(fora(projeta(Rm @ Mg)[0]), 4)
            R = Matrix.Translation(C) @ Matrix.Rotation(math.radians(ang), 4, Mb.col[eixo].normalized()) @ Matrix.Translation(-C)
            Pk, fk = projeta(R @ Mg); kb = ob.shape_key_add(name=kn, from_mix=False)
            for i, p_ in enumerate(Pk): kb.data[i].co = p_
            REP['olhos'][s][f'{nome}_{kn}_sem_acerto'] = fk
        NOVOS[f'{nome}_{s}'] = ob
    # ---------------- moldura de pele: cópia exata da pele em volta da janela, por cima das camadas do olho.
    # Em repouso coincide com a pele de baixo; no olhar, esconde o que sai da janela (o recorte que a v5 faz no material).
    for m_ in body.modifiers:
        if m_.type != 'ARMATURE': m_.show_viewport = False
    controles(); dgb = bpy.context.evaluated_depsgraph_get(); evb = body.evaluated_get(dgb); mb_ = evb.to_mesh(); mb_.calc_loop_triangles()
    BV = [evb.matrix_world @ v.co for v in mb_.vertices]; BT = [tuple(t.vertices) for t in mb_.loop_triangles]
    BUV = [tuple(tuple(mb_.uv_layers.active.data[li].uv) for li in t.loops) for t in mb_.loop_triangles]; evb.to_mesh_clear()
    for m_ in body.modifiers: m_.show_viewport = True
    bvb = BVHTree.FromPolygons(BV, BT); zw = (Mw.to_3x3() @ Vector((0, 0, 1))).normalized()
    head = img_np(bpy.data.materials['Kumo_Quad_Toon'].node_tree.nodes['Image Texture'].image.name) if 'Image Texture' in bpy.data.materials['Kumo_Quad_Toon'].node_tree.nodes else None
    if head is None:
        head = img_np([n for n in bpy.data.materials['Kumo_Quad_Toon'].node_tree.nodes if n.type == 'TEX_IMAGE'][0].image.name)
    M0, M1, NM, RES = -0.14, 1.14, 64, 384
    camadas = []
    for nm_ in ('Eye', 'Iris', 'Pupil', 'Catchlight'):
        Vc, Tc = avaliar(bpy.data.objects[f'Kumo_{nm_}_{s}']); camadas.append(BVHTree.FromPolygons([Vector(x) for x in Vc], Tc))
    def na_pele(uu, vv):
        o_ = Mw @ Vector((2 * uu - 1, 2 * vv - 1, 0.0)); hit = bvb.ray_cast(o_ + zw * 0.6, -zw, 1.2)
        if hit[0] is None: return hit
        # se alguma camada do olho está acima da pele nesse ponto, a moldura passa por cima dela —
        # só na faixa da borda da janela (fora dela as cascas da v5 dobram para dentro e não são vistas)
        topo = hit[0]
        dentro = 0 <= uu <= 1 and 0 <= vv <= 1 and amostra(mask, np.array([uu]), np.array([vv]))[0, 3] > 0.02
        for bv_ in (camadas if (dentro and os.environ.get('OJ_MOLDURA_SOBE')) else []):   # desligado: medido pior (0,84 contra 0,46 no repouso)
            h2 = bv_.ray_cast(o_ + zw * 0.6, -zw, 1.2)
            if h2[0] is not None and (h2[0] - topo).dot(zw) > 0: topo = h2[0]
        return (topo, hit[1], hit[2], hit[3])
    Pm, UVm, ok = [], [], []
    GM = np.linspace(M0, M1, NM + 1)
    for vv in GM:
        for uu in GM:
            hit = na_pele(uu, vv); ok.append(hit[0] is not None)
            Pm.append((hit[0] if hit[0] is not None else Mw @ Vector((2 * uu - 1, 2 * vv - 1, 0))) + zw * 0.0006); UVm.append(((uu - M0) / (M1 - M0), (vv - M0) / (M1 - M0)))
    Fm = [(k * (NM + 1) + j, k * (NM + 1) + j + 1, (k + 1) * (NM + 1) + j + 1, (k + 1) * (NM + 1) + j) for k in range(NM) for j in range(NM)]
    # só faces com os 4 cantos na pele e sem salto de profundidade (aresta muito maior que a da grade)
    passo = (M1 - M0) / NM * 2 * max(Mw.to_scale()[0], Mw.to_scale()[1])
    Fm = [f for f in Fm if all(ok[i] for i in f) and max((Pm[f[i]] - Pm[f[(i + 1) % 4]]).length for i in range(4)) < 3 * passo]
    tm = np.zeros((RES, RES, 4), np.float32); hh_, ww_ = head.shape[:2]
    for yi in range(RES):
        vv = M0 + (yi + 0.5) / RES * (M1 - M0)
        for xi in range(RES):
            uu = M0 + (xi + 0.5) / RES * (M1 - M0); hit = na_pele(uu, vv)
            if hit[0] is None: continue
            a_, b_, c_ = BT[hit[2]]; w3 = barycentric_transform(hit[0], BV[a_], BV[b_], BV[c_], Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)))
            ua, ub, uc = BUV[hit[2]]; tu = ua[0] * w3[0] + ub[0] * w3[1] + uc[0] * w3[2]; tv = ua[1] * w3[0] + ub[1] * w3[1] + uc[1] * w3[2]
            tm[yi, xi, :3] = amostra(head, np.array([tu]), np.array([tv]))[0, :3]
            inside = 0 <= uu <= 1 and 0 <= vv <= 1
            tm[yi, xi, 3] = 1.0 - (amostra(mask, np.array([uu]), np.array([vv]))[0, 3] if inside else 0.0)
    NOVOS[f'moldura_{s}'] = novo_obj(f'KumoJogo_Moldura.{s}', Pm, Fm, UVm, material_img(f'KumoJogo_Moldura.{s}', salvar_png(tm, f'olho_{s}_moldura')))
    # ---------------- pálpebras: grade no espaço da janela, um estágio por shape key
    skin = img_np(f'olho_{s}_skin'); lm = img_np(f'olho_{s}_lidmask')
    tex_skin = skin.copy(); tex_skin[..., 3] = lm[..., 3]
    lin2srgb = lambda c: (12.92 * c) if c <= 0.0031308 else (1.055 * c ** (1 / 2.4) - 0.055)   # a cor da v5 é de emissão (linear); a textura guarda sRGB
    tex_band = np.zeros_like(skin); tex_band[..., :3] = [lin2srgb(c) for c in LASH]; tex_band[..., 3] = lm[..., 3]
    im_skin = salvar_png(tex_skin, f'olho_{s}_palpebra'); im_band = salvar_png(tex_band, f'olho_{s}_palpebra_borda')
    cols = np.nonzero(lm[..., 3].max(0) > 0.02)[0]; U0, U1 = (cols.min() - 1) / lm.shape[1], (cols.max() + 2) / lm.shape[1]
    def faixa_v(uu):
        c = np.clip((uu * lm.shape[1]).astype(int), 0, lm.shape[1] - 1); rows = [np.nonzero(lm[:, ci, 3] > float(os.environ.get('OJ_LIMIAR', '0.5')))[0] for ci in c]
        return np.array([(r.min() / lm.shape[0] if len(r) else 0.5) for r in rows]), np.array([((r.max() + 1) / lm.shape[0] if len(r) else 0.5) for r in rows])
    NU = int(os.environ.get('OJ_NU', '96')); UU = np.linspace(U0, U1, NU + 1); VMIN, VMAX = faixa_v(UU)
    for lado, nome_v5 in (('sup', 'LidUp'), ('inf', 'LidLow')):
        lut = np.load(os.path.join(TEX, f'Kumo_{nome_v5}_{s}_borda.npy'))
        def borda(t):
            r = min(max(t * lut.shape[0] - 0.5, 0.0), lut.shape[0] - 1.0); r0 = int(np.floor(r)); r1 = min(r0 + 1, lut.shape[0] - 1); f = r - r0
            row = lut[r0] * (1 - f) + lut[r1] * f; return np.interp(UU, (np.arange(lut.shape[1]) + 0.5) / lut.shape[1], row)
        NB, NS = 2, int(os.environ.get('OJ_NS', '20'))
        def linhas(t):
            e = borda(t)
            if lado == 'sup':
                e = np.minimum(e, VMAX); eb = np.minimum(e + BW, VMAX)
                band = [e + (eb - e) * k / NB for k in range(NB + 1)]; pelev = [eb + (VMAX - eb) * k / NS for k in range(NS + 1)]
            else:
                e = np.maximum(e, VMIN); eb = np.maximum(e - BW, VMIN)
                band = [e + (eb - e) * k / NB for k in range(NB + 1)]; pelev = [eb + (VMIN - eb) * k / NS for k in range(NS + 1)]
            return band, pelev
        # casca da v5 (com relevo) em cada estágio: posição 3D de um ponto (u, v) da janela
        o_src = bpy.data.objects[f'Kumo_{nome_v5}_{s}']
        def casca(t):
            controles(piscar=t); Vt, Tt = avaliar(o_src); ut, vt = coords(Mw, Vt)
            P2 = [Vector((a_, b_, 0)) for a_, b_ in zip(ut, vt)]; kd = KDTree(len(Tt))
            cen = [(P2[a_] + P2[b_] + P2[c_]) / 3 for a_, b_, c_ in Tt]
            for i, c_ in enumerate(cen): kd.insert(c_, i)
            kd.balance(); kdv = KDTree(len(P2))
            for i, p_ in enumerate(P2): kdv.insert(p_, i)
            kdv.balance()
            def pos(uu, vv):
                q = Vector((uu, vv, 0))
                for _, ti, _ in kd.find_n(q, 12):
                    a_, b_, c_ = Tt[ti]
                    if intersect_point_tri_2d(q, P2[a_], P2[b_], P2[c_]):
                        return barycentric_transform(q, P2[a_], P2[b_], P2[c_], Vector(Vt[a_]), Vector(Vt[b_]), Vector(Vt[c_]))
                _, vi, _ = kdv.find(q)                                       # fora da casca: continua a superfície
                lq = Mw.inverted() @ Vector(Vt[vi]); return Mw @ Vector((2 * uu - 1, 2 * vv - 1, lq.z))
            return pos
        # repouso (t = 0) e os estágios
        estados = [0.0] + ESTAGIOS; GR = {}
        for t in estados:
            pos = casca(t); band, pelev = linhas(t)
            zf = (Mw.to_3x3() @ Vector((0, 0, 1))).normalized() * (0.00025 if lado == 'sup' else 0.0)
            pos0 = pos; pos = (lambda uu, vv, _p=pos0, _z=zf: _p(uu, vv) + _z)
            GR[t] = {'band': [[pos(UU[j], band[k][j]) for j in range(NU + 1)] for k in range(NB + 1)],
                     'pele': [[pos(UU[j], pelev[k][j]) for j in range(NU + 1)] for k in range(NS + 1)]}
        controles()
        band1, pele1 = linhas(1.0)
        for parte, nr, vv, im in (('band', NB, band1, im_band), ('pele', NS, pele1, im_skin)):
            Vs = [GR[0.0][parte][k][j] for k in range(nr + 1) for j in range(NU + 1)]
            F = [(k * (NU + 1) + j, k * (NU + 1) + j + 1, (k + 1) * (NU + 1) + j + 1, (k + 1) * (NU + 1) + j) for k in range(nr) for j in range(NU)]
            uv = [(UU[j], vv[k][j]) for k in range(nr + 1) for j in range(NU + 1)]
            nome = f'KumoJogo_Palpebra_{lado}{"_borda" if parte == "band" else ""}.{s}'
            ob = novo_obj(nome, Vs, F, uv, material_img(nome, im))
            ob.shape_key_add(name='Basis', from_mix=False)
            for t in ESTAGIOS:
                kb = ob.shape_key_add(name=f'Piscar_{int(t*100)}', from_mix=False)
                for i, p_ in enumerate([GR[t][parte][k][j] for k in range(nr + 1) for j in range(NU + 1)]): kb.data[i].co = p_
            NOVOS[nome] = ob

# ---------------- controles no rig: piscar (com estágios intermediários) e olhar
def driver_key(o, kname, expr, props):
    kb = o.data.shape_keys.key_blocks[kname]; fc = kb.driver_add('value'); d = fc.driver; d.type = 'SCRIPTED'
    for nm, prop in props:
        var = d.variables.new(); var.name = nm; var.type = 'SINGLE_PROP'; var.targets[0].id_type = 'OBJECT'; var.targets[0].id = rig
        var.targets[0].data_path = f'["{prop}"]'
    d.expression = expr
for k, v in (('kumo_piscar_E', 0.0), ('kumo_piscar_D', 0.0), ('kumo_olhar_x', 0.0), ('kumo_olhar_y', 0.0)): rig[k] = v
def chapeu(i):          # peso da forma do estágio i (estágios 0,25 0,5 0,75 1): interpolação por partes entre formas vizinhas
    t = ESTAGIOS[i]; a = ESTAGIOS[i - 1] if i else 0.0; b = ESTAGIOS[i + 1] if i + 1 < len(ESTAGIOS) else None
    up = f'(p-{a})/({t}-{a})'; dn = f'({b}-p)/({b}-{t})' if b else '1.0'
    return f'max(0.0, min({up}, {dn}, 1.0))'
for nome, o in NOVOS.items():
    s = nome[-1]; prop = 'kumo_piscar_E' if s == 'L' else 'kumo_piscar_D'
    if 'Palpebra' in nome:
        for i, t in enumerate(ESTAGIOS): driver_key(o, f'Piscar_{int(t*100)}', chapeu(i), [('p', prop)])
    elif o.data.shape_keys:
        driver_key(o, 'Olhar_dir', 'max(0.0, x)', [('x', 'kumo_olhar_x')]); driver_key(o, 'Olhar_esq', 'max(0.0, -x)', [('x', 'kumo_olhar_x')])
        driver_key(o, 'Olhar_cima', 'max(0.0, y)', [('y', 'kumo_olhar_y')]); driver_key(o, 'Olhar_baixo', 'max(0.0, -y)', [('y', 'kumo_olhar_y')])
json.dump(REP, open(os.path.join(OUT, 'medicoes.json'), 'w'), indent=1)
print('OJ CRIADOS', len(NOVOS), json.dumps(REP))

# ---------------- comparação: v5 × conversão, mesmos estados, mesmas câmeras
V5OBJ = [o for o in bpy.data.objects if o.name.startswith('Kumo_') and o.name[-2:] in ('_L', '_R') and o.type == 'MESH' and not o.hide_render]
NEW = list(NOVOS.values())
sc.render.engine = 'CYCLES'; sc.cycles.samples = int(os.environ.get('OJ_SAMPLES', '24')); sc.render.resolution_x = sc.render.resolution_y = 520
sc.cycles.transparent_max_bounces = 32
def cam(n, d, t, s_):
    c = bpy.data.objects.new(n, bpy.data.cameras.new(n)); sc.collection.objects.link(c); c.data.type = 'ORTHO'; c.data.ortho_scale = s_
    d = Vector(d).normalized(); c.location = Vector(t) + d * 6; c.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler(); return c
CAMS = {'frente': cam('cf', (0, -1, 0), (0.07, -0.3, 1.38), 1.05), '34': cam('c34', (0.5, -0.86, 0.05), (0.07, -0.3, 1.38), 1.05)}
ESTADOS = {'repouso': {}, 'piscar_25': {'p': 0.25}, 'piscar_50': {'p': 0.5}, 'piscar_75': {'p': 0.75}, 'piscar_100': {'p': 1.0},
           'so_esquerdo': {'pE': 1.0}, 'olhar_dir': {'g': (GAZE_DEG, 0)}, 'olhar_esq': {'g': (-GAZE_DEG, 0)}, 'olhar_cima': {'g': (0, GAZE_DEG)}, 'olhar_baixo': {'g': (0, -GAZE_DEG)}}
def estado(e, qual):
    controles(piscar=e.get('p', 0.0), pE=e.get('pE', 0.0), olhar=e.get('g'))
    rig['kumo_piscar_E'] = max(e.get('p', 0.0), e.get('pE', 0.0)); rig['kumo_piscar_D'] = e.get('p', 0.0)
    g = e.get('g', (0, 0)); rig['kumo_olhar_x'] = g[0] / GAZE_DEG; rig['kumo_olhar_y'] = g[1] / GAZE_DEG
    for o in V5OBJ: o.hide_render = qual != 'v5'
    for o in NEW: o.hide_render = qual != 'novo'
    rig.update_tag(); bpy.context.view_layer.update()
IDX = {}
for en, e in ESTADOS.items():
    for qual in ('v5', 'novo'):
        estado(e, qual)
        for cn, c in CAMS.items():
            sc.camera = c; f = os.path.join(OUT, 'renders', f'{en}_{qual}_{cn}.png'); sc.render.filepath = f; bpy.ops.render.render(write_still=True); IDX[f'{en}|{qual}|{cn}'] = f
json.dump(IDX, open(os.path.join(OUT, 'renders', 'indice.json'), 'w'))
from PIL import Image
dif = {}
for en in ESTADOS:
    for cn in CAMS:
        a = np.asarray(Image.open(IDX[f'{en}|v5|{cn}']).convert('RGB')).astype(int); b = np.asarray(Image.open(IDX[f'{en}|novo|{cn}']).convert('RGB')).astype(int)
        d = np.abs(a - b).max(-1); dif[f'{en}|{cn}'] = dict(media=round(float(d.mean()), 3), pixels_acima_de_24=int((d > 24).sum()), max=int(d.max()))
REP['comparacao_v5_x_novo'] = dif
print('OJ DIF', json.dumps(dif))
for o in V5OBJ: o.hide_render = False
estado({}, 'v5')
for o in [o for o in bpy.data.objects if o.type == 'CAMERA' and o.name in ('cf', 'c34')]: bpy.data.objects.remove(o)
json.dump(REP, open(os.path.join(OUT, 'medicoes.json'), 'w'), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'kumo_olhos_jogo_conversao.blend'), copy=True, relative_remap=False)
print('OJ OK')
