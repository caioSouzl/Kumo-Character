"""Reimporta kumo_maos_dedos.fbx e compara a deformação com o .blend (só leitura de ambos).
Para cada quadro do FBX, cada osso do .blend recebe a mesma deformação D = pose_mundo @ repouso_mundo^-1 do osso FBX
(independe da convenção de eixos), e as malhas deformadas são comparadas vértice a vértice (KDTree no repouso)."""
import bpy, sys, os, json
from mathutils.kdtree import KDTree
BLEND, FBX, OUT = sys.argv[-3], sys.argv[-2], sys.argv[-1]
bpy.ops.wm.open_mainfile(filepath=BLEND); sc = bpy.context.scene
rig = bpy.data.objects['Kumo_Rig']; body = bpy.data.objects['Kumo']
for m in body.modifiers:
    if m.type != 'ARMATURE': m.show_viewport = False
old = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=FBX, use_anim=True)
new = [o for o in bpy.data.objects if o not in old]
farm = next(o for o in new if o.type == 'ARMATURE'); fmesh = next(o for o in new if o.type == 'MESH')
bn = {b.name for b in farm.data.bones}; g2 = {g.index: g.name for g in fmesh.vertex_groups}
infl = [len([g for g in v.groups if g2[g.group] in bn and g.weight > 1e-4]) for v in fmesh.data.vertices]
sums = [sum(g.weight for g in v.groups if g2[g.group] in bn) for v in fmesh.data.vertices]
ad = farm.animation_data_create(); acts = [a.name for a in bpy.data.actions]
for t_ in list(ad.nla_tracks): ad.nla_tracks.remove(t_)
act = next(a for a in bpy.data.actions if a.name.endswith('Teste_Exportacao')); ad.action = act
fr = [int(x) for x in act.frame_range] if act else [1, 1]
rep = dict(ossos=len(bn), ossos_blend=len(rig.data.bones), nomes_iguais=bn == {b.name for b in rig.data.bones},
           vertices=len(fmesh.data.vertices), vertices_blend=len(body.data.vertices), max_influencias=max(infl),
           sem_peso=sum(1 for x in infl if x == 0), soma_fora_de_1=sum(1 for s in sums if abs(s - 1) > 0.01),
           escala_armadura=[round(x, 4) for x in farm.matrix_world.to_scale()], acoes=acts, acao_ativa=act.name if act else None, quadros=fr)
def pos(o):
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get(); ev = o.evaluated_get(dg); m = ev.to_mesh()
    P = [ev.matrix_world @ v.co for v in m.vertices]; ev.to_mesh_clear(); return P
def casar():
    for pb in rig.pose.bones:
        fpb = farm.pose.bones.get(pb.name)
        if not fpb: continue
    order = [b.name for b in rig.data.bones]   # ordem do pai para o filho
    for n in order:
        fpb = farm.pose.bones[n]; fb = farm.data.bones[n]; b = rig.data.bones[n]
        D = (farm.matrix_world @ fpb.matrix) @ (farm.matrix_world @ fb.matrix_local).inverted()
        rig.pose.bones[n].matrix = rig.matrix_world.inverted() @ D @ rig.matrix_world @ b.matrix_local
        bpy.context.view_layer.update()
sc.frame_set(fr[0]); casar(); A = pos(body); Bf = pos(fmesh)
kd = KDTree(len(A)); [kd.insert(p, i) for i, p in enumerate(A)]; kd.balance(); mp = [kd.find(p) for p in Bf]
rep['repouso_dist_casamento_max_mm'] = round(max(d for _, _, d in mp) * 1000, 3)
err = {}
for f in range(fr[0], fr[1] + 1):
    sc.frame_set(f); casar(); A = pos(body); Bf = pos(fmesh)
    e = [(Bf[i] - A[j]).length for i, (_, j, _) in enumerate(mp)]
    err[f] = dict(medio_mm=round(sum(e) / len(e) * 1000, 4), max_mm=round(max(e) * 1000, 4))
rep['deformacao_fbx_vs_blender'] = err
os.makedirs(OUT, exist_ok=True); json.dump(rep, open(os.path.join(OUT, 'fbx_reimportado.json'), 'w'), indent=1)
print(json.dumps(rep, indent=1))
# animação: FBX contra GLB (o GLB já foi comparado com o Blender: ≤0,003 mm)
GLB = FBX[:-4] + '.glb'; old = set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=GLB)
gn = [o for o in bpy.data.objects if o not in old]; garm = next(o for o in gn if o.type == 'ARMATURE'); gmesh = max((o for o in gn if o.type == 'MESH'), key=lambda o: len(o.data.vertices))
gad = garm.animation_data_create()
for t_ in list(gad.nla_tracks): gad.nla_tracks.remove(t_)
gad.action = next(a for a in bpy.data.actions if a.name.startswith('Teste_Exportacao') and a is not act)
sc.frame_set(1); G = pos(gmesh); Fm = pos(fmesh); kd = KDTree(len(G)); [kd.insert(p, i) for i, p in enumerate(G)]; kd.balance(); mg = [kd.find(p)[1] for p in Fm]
an = {}
for f in range(1, 5):
    sc.frame_set(f); G = pos(gmesh); Fm = pos(fmesh); R = pos(fmesh) if f == 1 else R
    e = [(Fm[i] - G[mg[i]]).length for i in range(len(Fm))]
    an[f] = dict(max_mm=round(max(e) * 1000, 4))
sc.frame_set(1); R1 = pos(fmesh)
for f in range(1, 5):
    sc.frame_set(f); Fm = pos(fmesh); an[f]['deslocamento_max_vs_quadro1_mm'] = round(max((a - b).length for a, b in zip(Fm, R1)) * 1000, 1)
rep['animacao_fbx_vs_glb'] = an
json.dump(rep, open(os.path.join(OUT, 'fbx_reimportado.json'), 'w'), indent=1); print('ANIM', json.dumps(an))
sc.frame_set(1)
for nm, o in (('fbx', fmesh), ('glb', gmesh), ('blend', body)):
    P_ = pos(o); print('BB', nm, [round(min(p[k] for p in P_), 3) for k in range(3)], [round(max(p[k] for p in P_), 3) for k in range(3)], o.parent.name if o.parent else None, [round(x,3) for x in o.matrix_world.translation])
