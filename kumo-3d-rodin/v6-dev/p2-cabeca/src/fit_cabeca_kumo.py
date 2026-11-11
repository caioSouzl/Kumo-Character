"""P2 · ajusta os 15 vértices de controle da cabeça facetada F1.2 (kumo-3d-toon, aprovada em 2026-11-09) à cabeça do
Kumo oficial (malha Rodin em kumo_rigged.blend, só leitura). Mesmo método do fit_head_to_rodin.py da linha arquivada:
raio de fora para o centro na direção de cada vértice, média dos lados E/D (cabeça simétrica). Sem mudar escala do corpo:
o quadro da cabeça é levado para a cabeça do Kumo (queixo, topo, centro), e as alturas ficam as do Kumo.

  python fit_cabeca_kumo.py <kumo_rigged.blend> <saida.json>
"""
import bpy, bmesh, sys, os, json
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kumo_common import HEAD_VERTS
SRC, OUT = sys.argv[-2], sys.argv[-1]
bpy.ops.wm.open_mainfile(filepath=SRC)
ob = bpy.data.objects['Kumo']; rig = bpy.data.objects['Kumo_Rig']
for m in ob.modifiers:
    if m.type != 'ARMATURE': m.show_viewport = False
for pb in rig.pose.bones: pb.rotation_quaternion = (1, 0, 0, 0); pb.rotation_euler = (0, 0, 0); pb.location = (0, 0, 0)
if rig.animation_data: rig.animation_data.action = None
bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get(); ev = ob.evaluated_get(dg); me = ev.to_mesh()
bm = bmesh.new(); bm.from_mesh(me); bm.transform(ob.matrix_world); ev.to_mesh_clear()
hb = rig.data.bones.get('head') or next(b for b in rig.data.bones if 'head' in b.name.lower())
NECK = hb.head_local.z
def slice_(z, tol=0.012): return [v.co for v in bm.verts if abs(v.co.z - z) < tol and abs(v.co.x) < 0.7]
# queixo = fatia mais estreita entre o pescoço e 0,25 acima dele (mesma regra da linha arquivada)
cands = [(max(p.x for p in slice_(z)) - min(p.x for p in slice_(z)), z) for z in [NECK - 0.08 + i * 0.01 for i in range(20)] if len(slice_(z)) > 8]
chin = min(cands)[1]; tip = max(v.co.z for v in bm.verts)
CHIN_Z, TIP_Z = 0.955, 1.965; k = (tip - chin) / (TIP_Z - CHIN_Z)
sl = slice_(chin + (1.45 - CHIN_Z) * k)
xc = (max(p.x for p in sl) + min(p.x for p in sl)) / 2; yc = (max(p.y for p in sl) + min(p.y for p in sl)) / 2
def to_kumo(p): return Vector((p[0] * k + xc, (p[1] - 0.06) * k + yc, chin + (p[2] - CHIN_Z) * k))
centre = to_kumo((0.0, 0.06, 1.42))
bvh = BVHTree.FromBMesh(bm)
EYES = [to_kumo((0.30, -0.45, 1.31)), to_kumo((-0.30, -0.45, 1.31))]
fitted, report = {}, {}
for name, p in HEAD_VERTS.items():
    hits = []
    for sx in ((1, -1) if abs(p[0]) > 1e-6 else (1,)):
        q = to_kumo((p[0] * sx, p[1], p[2])); d = (q - centre).normalized()
        loc, _n, _i, _d = bvh.ray_cast(centre + d * 3.0, -d)
        if loc is not None: hits.append(Vector((loc.x * sx if abs(p[0]) > 1e-6 else loc.x, loc.y, loc.z)))
    new = sum(hits, Vector()) / len(hits)
    if abs(p[0]) < 1e-6: new.x = xc
    # de volta ao quadro da cabeça F1.2 (para o gerador), centrado em x
    hv = ((new.x - xc) / k, (new.y - yc) / k + 0.06, CHIN_Z + (new.z - chin) / k)
    fitted[name] = [round(c, 4) for c in hv]
    report[name] = dict(antigo=list(p), novo=fitted[name], delta=[round(a - b, 4) for a, b in zip(fitted[name], p)],
                        diferenca_E_D_m=round((hits[0] - hits[1]).length, 4) if len(hits) == 2 else 0.0,
                        perto_do_olho=any((new - e).length < 0.24 * k for e in EYES))
T = dict(escala_k=k, queixo_z=chin, topo_z=tip, x_centro=xc, y_centro=yc, pescoco_z=NECK)
json.dump(dict(head_verts=fitted, report=report, transform=T), open(OUT, 'w'), indent=1)
print('FIT', json.dumps(T))
for n, r in report.items(): print('FIT', n, r['antigo'], '->', r['novo'], 'ED', r['diferenca_E_D_m'], 'OLHO' if r['perto_do_olho'] else '')
