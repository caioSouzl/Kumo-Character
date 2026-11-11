"""Busca 2: o polegar (0,05 m) não alcança a 2ª falange dos dedos (≥0,079 m). Alvo possível: encostar sobre a 1ª falange do dedo 1.
Varre (abertura, dobra 1, dobra 2) em faixa larga; mede a distância da ponta ao dedo 1 e, nos melhores, os cruzamentos."""
import bpy, sys, os, json, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kumo_lib import Kumo
from mathutils.geometry import intersect_point_line
bpy.ops.wm.open_mainfile(filepath=sys.argv[-1])
rig = bpy.data.objects['Kumo_Rig']; body = bpy.data.objects['Kumo']
for m in body.modifiers:
    if m.type != 'ARMATURE': m.show_viewport = False
K = Kumo(rig, body); pb = rig.pose.bones
def seg(p, a, b):
    q, t = intersect_point_line(p, a, b); t = max(0, min(1, t)); return (p - (a + (b - a) * t)).length, t
out = {}
for sd in ('L', 'R'):
    fs, vs = K.regiao(sd); K.reset(); V0, T0, _ = K.tri_data(fs, vs); rest = K.self_pairs(V0, T0)
    cand = []
    for s1, c1, c2 in itertools.product(range(-60, 61, 20), range(-40, 81, 20), (0, 30, 60, 90)):
        K.reset(); K.poses(sd, polegar_sobre=(s1, c1, c2))['mao_fechada_polegar_sobre']()
        tip = pb[f'polegar_2.{sd}'].tail; mid = (pb[f'polegar_2.{sd}'].head + tip) / 2
        d, t = seg(tip, pb[f'dedo1_1.{sd}'].head, pb[f'dedo1_1.{sd}'].tail); dm, _ = seg(mid, pb[f'dedo1_1.{sd}'].head, pb[f'dedo1_1.{sd}'].tail)
        cand.append((d + 0.5 * dm, s1, c1, c2, round(d * 1000), round(t, 2)))
    cand.sort(); best = []
    for sc_, s1, c1, c2, d, t in cand[:12]:
        K.reset(); K.poses(sd, polegar_sobre=(s1, c1, c2))['mao_fechada_polegar_sobre']()
        V, T, _ = K.tri_data(fs, vs); c = K.classify(V, T, K.self_pairs(V, T) - rest)
        best.append(dict(s1=s1, c1=c1, c2=c2, ponta_dedo1_mm=d, t=t, **c)); print('B', sd, best[-1], flush=True)
    out[sd] = best
json.dump(out, open(sys.argv[-2], 'w'), indent=1)
