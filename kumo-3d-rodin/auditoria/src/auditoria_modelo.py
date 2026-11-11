"""Kumo — auditoria técnica do modelo principal (SOMENTE LEITURA).

  python auditoria_modelo.py <kumo_rigged.blend> <pasta de saída>

Abre o .blend, mede e renderiza evidências. Nunca grava o .blend.
Blender 5.2 (módulo bpy). Cada teste registra método e limitações no JSON.
"""
import bpy, bmesh, sys, os, json, math, time
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

SRC, OUT = sys.argv[-2], sys.argv[-1]
os.makedirs(os.path.join(OUT, 'poses'), exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=SRC)
REPO = os.path.dirname(os.path.abspath(SRC))
img = bpy.data.images.get('kumo_quad_diffuse')
if img: img.filepath = os.path.join(REPO, 'textures', 'kumo_quad_diffuse.png'); img.reload()
sc = bpy.context.scene; body = bpy.data.objects['Kumo']; rig = bpy.data.objects['Kumo_Rig']; me = body.data
R = {'blender': bpy.app.version_string, 'arquivo': os.path.basename(SRC)}

# ------------------------------------------------------------------ A. objetos
R['objetos'] = [dict(nome=o.name, tipo=o.type, pai=o.parent.name if o.parent else None, osso_pai=o.parent_bone or None,
                     vertices=len(o.data.vertices) if o.type == 'MESH' else None,
                     faces=len(o.data.polygons) if o.type == 'MESH' else None,
                     modificadores=[f'{m.type}:{m.name}' for m in getattr(o, 'modifiers', [])],
                     materiais=[s.name for s in o.material_slots] if o.type == 'MESH' else None,
                     oculto_render=o.hide_render) for o in bpy.data.objects]

# ------------------------------------------------------------------ B. integridade da malha
bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
areas = [f.calc_area() for f in bm.faces]; elens = [e.calc_length() for e in bm.edges]
vol = bm.calc_volume(signed=True)
kd_dup = 0
from mathutils.kdtree import KDTree
kd = KDTree(len(bm.verts))
for v in bm.verts: kd.insert(v.co, v.index)
kd.balance()
for v in bm.verts:
    if len(kd.find_range(v.co, 1e-6)) > 1: kd_dup += 1
def pct(a, p): a = sorted(a); return a[min(len(a) - 1, int(len(a) * p))]
R['malha'] = dict(
    vertices=len(bm.verts), arestas=len(bm.edges), faces=len(bm.faces),
    triangulos=sum(1 for f in bm.faces if len(f.verts) == 3), quads=sum(1 for f in bm.faces if len(f.verts) == 4),
    ngons=sum(1 for f in bm.faces if len(f.verts) > 4),
    arestas_nao_manifold=sum(1 for e in bm.edges if not e.is_manifold), arestas_de_borda=sum(1 for e in bm.edges if e.is_boundary),
    vertices_soltos=sum(1 for v in bm.verts if not v.link_edges), faces_degeneradas=sum(1 for a in areas if a < 1e-10),
    arestas_comprimento_zero=sum(1 for l in elens if l < 1e-7), vertices_duplicados=kd_dup,
    volume_com_sinal=round(vol, 5), normais_para_fora=vol > 0,
    faces_suaves=sum(1 for f in bm.faces if f.smooth), arestas_vivas=sum(1 for e in bm.edges if not e.smooth),
    area_face_mediana=pct(areas, 0.5), area_face_p05=pct(areas, 0.05), area_face_p95=pct(areas, 0.95),
    aresta_mediana=pct(elens, 0.5), aresta_p05=pct(elens, 0.05), aresta_p95=pct(elens, 0.95),
    bbox=[[round(min(v.co[i] for v in bm.verts), 4), round(max(v.co[i] for v in bm.verts), 4)] for i in range(3)])

# autointerseção em repouso (pares de triângulos sem vértice em comum que se cruzam)
def self_pairs(obj):
    dg = bpy.context.evaluated_depsgraph_get(); ev = obj.evaluated_get(dg); m = ev.to_mesh(); m.calc_loop_triangles()
    V = [v.co.copy() for v in m.vertices]; T = [tuple(t.vertices) for t in m.loop_triangles]
    b = BVHTree.FromPolygons(V, T); pr = b.overlap(b)
    out = set()
    for a_, b_ in pr:
        if a_ < b_ and not (set(T[a_]) & set(T[b_])): out.add((a_, b_))
    volm = 0.0
    for t in T:
        a_, b_, c_ = (V[i] for i in t); volm += a_.dot(b_.cross(c_)) / 6.0
    E = [(e.vertices[0], e.vertices[1]) for e in m.edges]
    L = [(V[a_] - V[b_]).length for a_, b_ in E]
    ev.to_mesh_clear(); return out, volm, L, V, T
OUTL = [m for m in body.modifiers if m.type in ('SOLIDIFY', 'VERTEX_WEIGHT_MIX', 'MASK')]
for m in OUTL: m.show_viewport = False
bpy.context.view_layer.update()
rest_pairs, rest_vol, rest_len, restV, restT = self_pairs(body)
R['malha']['autointersecao_repouso_pares'] = len(rest_pairs)

# simetria em X
mir = 0; devs = []
for v in bm.verts:
    co, i, d = kd.find(Vector((-v.co.x, v.co.y, v.co.z))); devs.append(d)
    if d < 0.002: mir += 1
R['simetria'] = dict(vertices_com_espelho_ate_2mm=mir, fracao=round(mir / len(bm.verts), 4),
                     desvio_mediano_m=round(pct(devs, 0.5), 5), desvio_p95_m=round(pct(devs, 0.95), 5), desvio_max_m=round(max(devs), 5),
                     metodo='para cada vértice, distância ao vértice mais próximo do ponto espelhado em X',
                     limitacao='mede simetria de posição dos vértices, não de topologia')

# ------------------------------------------------------------------ D. UV e textura
uv = bm.loops.layers.uv.active
uv_area = sum(abs(sum((l[uv].uv.x * l.link_loop_next[uv].uv.y - l.link_loop_next[uv].uv.x * l[uv].uv.y) for l in f.loops)) / 2 for f in bm.faces) if uv else 0
dens = []
if uv:
    for f, a in zip(bm.faces, areas):
        ua = abs(sum((l[uv].uv.x * l.link_loop_next[uv].uv.y - l.link_loop_next[uv].uv.x * l[uv].uv.y) for l in f.loops)) / 2
        if a > 1e-10: dens.append(ua / a)
# ilhas UV: componentes por arestas com UV contínuo
seam_edges = 0
if uv:
    for e in bm.edges:
        if len(e.link_loops) == 2:
            l1, l2 = e.link_loops
            a1, b1 = l1[uv].uv, l1.link_loop_next[uv].uv; a2, b2 = l2[uv].uv, l2.link_loop_next[uv].uv
            if (a1 - b2).length > 1e-5 or (b1 - a2).length > 1e-5: seam_edges += 1
R['uv'] = dict(camadas=[u.name for u in me.uv_layers], cobertura_do_quadrado=round(uv_area, 4), arestas_de_costura=seam_edges,
               densidade_texel_p05_p50_p95=[round(pct(dens, p), 3) for p in (0.05, 0.5, 0.95)] if dens else None,
               razao_densidade_p95_p05=round(pct(dens, 0.95) / max(pct(dens, 0.05), 1e-9), 2) if dens else None,
               imagens=[dict(nome=i.name, tamanho=list(i.size), espaco_cor=i.colorspace_settings.name, arquivo=os.path.basename(i.filepath)) for i in bpy.data.images if i.size[0]])

# ------------------------------------------------------------------ E. rig
def bone_info(b):
    pb = rig.pose.bones[b.name]
    return dict(nome=b.name, pai=b.parent.name if b.parent else None, comprimento=round(b.length, 4), deforma=b.use_deform,
                conectado=b.use_connect, modo_rotacao=pb.rotation_mode, restricoes=[c.type for c in pb.constraints],
                forma_personalizada=bool(pb.custom_shape), travas=[list(pb.lock_location), list(pb.lock_rotation)])
bones = [bone_info(b) for b in rig.data.bones]
vg = {g.index: g.name for g in body.vertex_groups}
deform = {b.name for b in rig.data.bones if b.use_deform}
infl = []; sums = []; domin = {}
for v in me.vertices:
    ws = [(vg[g.group], g.weight) for g in v.groups if vg[g.group] in deform and g.weight > 1e-4]
    infl.append(len(ws)); sums.append(sum(w for _, w in ws))
    if ws:
        d = max(ws, key=lambda x: x[1])[0]; domin[d] = domin.get(d, 0) + 1
R['rig'] = dict(
    ossos=len(bones), ossos_de_deformacao=sum(1 for b in bones if b['deforma']), ossos_com_restricoes=sum(1 for b in bones if b['restricoes']),
    ossos_com_forma_de_controle=sum(1 for b in bones if b['forma_personalizada']),
    tem_ik=any('IK' in b['restricoes'] for b in bones), lista=bones,
    colecoes_de_ossos=[c.name for c in rig.data.collections_all] if hasattr(rig.data, 'collections_all') else None,
    acoes=[a.name for a in bpy.data.actions], shape_keys_corpo=[k.name for k in me.shape_keys.key_blocks] if me.shape_keys else [],
    drivers=len(rig.animation_data.drivers) if rig.animation_data else 0,
    influencias_por_vertice=dict(max=max(infl), media=round(sum(infl) / len(infl), 2), acima_de_4=sum(1 for x in infl if x > 4), sem_peso=sum(1 for x in infl if x == 0)),
    soma_dos_pesos=dict(min=round(min(sums), 4), max=round(max(sums), 4), fora_de_1=sum(1 for s in sums if abs(s - 1) > 0.01)),
    vertices_por_osso_dominante=dict(sorted(domin.items(), key=lambda x: -x[1])),
    ossos_de_deformacao_sem_vertices=[b for b in deform if b not in domin],
    preservar_volume=body.modifiers['Armature'].use_deform_preserve_volume)

# ------------------------------------------------------------------ G. materiais
def mat_info(m):
    nodes = [n.type for n in m.node_tree.nodes] if m.use_nodes else []
    return dict(nome=m.name, nos=nodes, usuarios=m.users, emissao_pura='EMISSION' in nodes and 'BSDF_PRINCIPLED' not in nodes)
R['materiais'] = [mat_info(m) for m in bpy.data.materials]
R['render'] = dict(motor=sc.render.engine, transformacao_de_vista=sc.view_settings.view_transform, look=sc.view_settings.look,
                   amostras=sc.cycles.samples, film_transparent=sc.render.film_transparent)

# ------------------------------------------------------------------ F. testes de articulação
def rot_world(name, axis, deg):
    """Gira o osso em torno de um eixo do MUNDO passando pela cabeça do osso (espaço da armadura = mundo aqui)."""
    pb = rig.pose.bones[name]; bpy.context.view_layer.update()
    M = pb.matrix.copy(); h = M.to_translation()
    pb.matrix = Matrix.Translation(h) @ Matrix.Rotation(math.radians(deg), 4, Vector(axis).normalized()) @ Matrix.Translation(-h) @ M
    bpy.context.view_layer.update()
def reset():
    for pb in rig.pose.bones:
        pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.rotation_euler = (0, 0, 0); pb.scale = (1, 1, 1)
    bpy.context.view_layer.update()
def bone_dir(name):
    pb = rig.pose.bones[name]; return (pb.tail - pb.head).normalized()
X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)
def bend_axis(name, toward):      # eixo que dobra o osso em direção a 'toward'
    return bone_dir(name).cross(Vector(toward)).normalized()
POSES = {
    'cabeca_virar_45': [('head', Z, 45)], 'cabeca_virar_70': [('head', Z, 70)],
    'cabeca_baixar_30': [('head', X, -30)], 'cabeca_erguer_30': [('head', X, 30)], 'cabeca_inclinar_25': [('head', Y, 25)],
    'pescoco_cabeca_virar_60': [('neck', Z, 30), ('head', Z, 30)],
    'tronco_curvar_30': [('spine', X, -15), ('chest', X, -15)], 'tronco_torcer_30': [('spine', Z, 15), ('chest', Z, 15)],
    'braco_E_horizontal': [('upper_arm.L', Y, -45)], 'braco_E_acima_da_cabeca': [('shoulder.L', Y, -20), ('upper_arm.L', Y, -100)],
    'braco_E_para_frente_90': [('upper_arm.L', X, -90)],
    'cotovelo_E_90': [('forearm.L', 'BEND_FWD', 90)], 'cotovelo_E_130': [('forearm.L', 'BEND_FWD', 130)],
    'punho_E_45': [('hand.L', 'BEND_FWD', 45)],
    'coxa_E_frente_60': [('thigh.L', X, -60)], 'coxa_E_frente_90': [('thigh.L', X, -90)], 'coxa_E_abrir_45': [('thigh.L', Y, -45)],
    'joelho_E_90': [('shin.L', X, 90)], 'joelho_E_120': [('shin.L', X, 120)], 'joelho_D_90': [('shin.R', X, 90)],
    'tornozelo_E_30': [('foot.L', X, -30)],
    'cauda_enrolar': [(f'tail_{i:02d}', X, 18) for i in range(1, 11)], 'cauda_abanar': [(f'tail_{i:02d}', Z, 12) for i in range(1, 11)],
    'agachar': [('thigh.L', X, -80), ('shin.L', X, 110), ('thigh.R', X, -80), ('shin.R', X, 110)],
}
def cam(name, az, tgt, scale):
    c = bpy.data.objects.new(name, bpy.data.cameras.new(name)); sc.collection.objects.link(c); c.data.type = 'ORTHO'; c.data.ortho_scale = scale
    d = Vector((math.sin(math.radians(az)), -math.cos(math.radians(az)), 0)); c.location = Vector(tgt) + d * 6
    c.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler(); c.data.clip_end = 30; return c
C34 = cam('a34', -35, (0, 0, 1.0), 2.5); CL = cam('aL', 55, (0, 0, 1.0), 2.5)
sc.render.engine = 'CYCLES'; sc.cycles.samples = 8; sc.render.resolution_x = sc.render.resolution_y = 360; sc.render.film_transparent = False
tests = {}
names = {b.name for b in rig.data.bones}
for pname, steps in POSES.items():
    reset(); ok = True
    for bn, ax, deg in steps:
        if bn not in names: ok = False; break
        if ax == 'BEND_FWD': ax = bend_axis(bn, (0, -1, 0))
        rot_world(bn, ax, deg)
    if not ok: tests[pname] = dict(erro='osso ausente'); continue
    t0 = time.perf_counter(); pairs, volm, L, V, T = self_pairs(body); dt = time.perf_counter() - t0
    new = pairs - rest_pairs
    ratio = sorted(l / r for l, r in zip(L, rest_len) if r > 1e-7)
    tests[pname] = dict(passos=[(b, (list(a) if not isinstance(a, str) else a), d) for b, a, d in steps],
                        pares_de_autointersecao_novos=len(new), triangulos_envolvidos=len({i for p in new for i in p}),
                        volume_relativo=round(volm / rest_vol, 4),
                        aresta_esticamento_p99=round(ratio[int(len(ratio) * 0.99)], 3), aresta_esticamento_max=round(ratio[-1], 3),
                        aresta_compressao_p01=round(ratio[int(len(ratio) * 0.01)], 3), aresta_compressao_min=round(ratio[0], 3))
    for m in OUTL: m.show_viewport = True
    for cn, c in (('34', C34), ('lado', CL)):
        sc.camera = c; sc.render.filepath = os.path.join(OUT, 'poses', f'{pname}_{cn}.png'); bpy.ops.render.render(write_still=True)
    for m in OUTL: m.show_viewport = False
reset()
R['articulacoes'] = dict(resultados=tests,
    metodo='cada osso é girado em torno de um eixo do mundo pela cabeça do osso; mede-se na malha avaliada (só armadura): '
           'pares de triângulos sem vértice comum que se cruzam e que não se cruzavam em repouso; volume fechado relativo ao repouso; '
           'razão de comprimento de cada aresta (pose/repouso)',
    limitacoes='poses isoladas e estáticas (sem animação contínua); autointerseção conta pares de triângulos, não profundidade; '
               'volume global dilui perdas locais; eixos de dobra aproximados por eixos do mundo')

# ------------------------------------------------------------------ H. desempenho do rig
for m in OUTL: m.show_viewport = True
hb = rig.pose.bones['head']; t0 = time.perf_counter(); N = 40
for i in range(N):
    hb.rotation_mode = 'XYZ'; hb.rotation_euler = (0, math.radians(i), 0); bpy.context.view_layer.update()
    bpy.context.evaluated_depsgraph_get()
R['desempenho'] = dict(ms_por_atualizacao=round((time.perf_counter() - t0) / N * 1000, 2), metodo=f'{N} atualizações do depsgraph girando a cabeça',
                       limitacao='mede só a avaliação da cena em modo background, não a taxa de quadros na viewport')
reset()
json.dump(R, open(os.path.join(OUT, 'auditoria-dados.json'), 'w'), indent=1, default=str)
print('AUDITORIA OK')
