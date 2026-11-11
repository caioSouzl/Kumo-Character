"""Procura o ângulo do polegar dobrado por cima dos dedos na mão fechada (70°) com o menor cruzamento. Só mede."""
import bpy, sys, os, json, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kumo_lib import Kumo
from mathutils.geometry import intersect_point_line
bpy.ops.wm.open_mainfile(filepath=sys.argv[-1])
rig = bpy.data.objects['Kumo_Rig']; body = bpy.data.objects['Kumo']
for m in body.modifiers:
    if m.type != 'ARMATURE': m.show_viewport = False
K = Kumo(rig, body)
def seg_dist(p, a, b):
    q, t = intersect_point_line(p, a, b); t = max(0, min(1, t)); return (p - (a + (b - a) * t)).length
res = []
for sd in ('L', 'R'):
    fs, vs = K.regiao(sd); K.reset(); V0, T0, _ = K.tri_data(fs, vs); rest = K.self_pairs(V0, T0)
    for s1, c1, c2 in itertools.product((10, 25, 40, 55), (0, 20, 40), (20, 45, 70)):
        K.reset(); K.poses(sd, polegar_sobre=(s1, c1, c2))['mao_fechada_polegar_sobre']()
        V, T, _ = K.tri_data(fs, vs); new = K.self_pairs(V, T) - rest; c = K.classify(V, T, new)
        pb = rig.pose.bones; tip = pb[f'polegar_2.{sd}'].tail
        dd = {k: round(min(seg_dist(tip, pb[f'dedo{k}_{j}.{sd}'].head, pb[f'dedo{k}_{j}.{sd}'].tail) for j in (1, 2)) * 1000) for k in (1, 2, 3)}
        res.append(dict(lado=sd, s1=s1, c1=c1, c2=c2, **c, ponta_ate_dedo_mm=dd))
        print('PS', sd, s1, c1, c2, c, dd, flush=True)
json.dump(res, open(sys.argv[-2], 'w'), indent=0)
