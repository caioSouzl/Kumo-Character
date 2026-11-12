"""P2 fiel · análise (só leitura): onde estão os olhos pintados na malha e na textura, e o olho simétrico de destino."""
import bpy, sys, json, math, numpy as np
from mathutils import Vector
SRC, OUT = sys.argv[-2], sys.argv[-1]
bpy.ops.wm.open_mainfile(filepath=SRC)
REPO = '/home/user/Kumo-Character/kumo-3d-rodin'
img = bpy.data.images['kumo_quad_diffuse']; img.filepath = REPO + '/textures/kumo_quad_diffuse.png'; img.reload()
W, H = img.size; px = np.empty(W * H * 4, np.float32); img.pixels.foreach_get(px); px = px.reshape(H, W, 4)[:, :, :3]
body = bpy.data.objects['Kumo']; me = body.data; uv = me.uv_layers.active.data
import colorsys
def cls(rgb):
    h, s, v = colorsys.rgb_to_hsv(*rgb)
    if v < 0.18: return 'preto'
    if s < 0.25 and v > 0.75: return 'branco'
    if h * 360 < 52 and s > 0.35: return 'ambar_marrom'
    return 'pele'
vc = {}
for p in me.polygons:
    for li, vi in zip(p.loop_indices, p.vertices):
        u, v = uv[li].uv; c = px[min(H - 1, int(v * H)), min(W - 1, int(u * W))]
        vc.setdefault(vi, []).append(cls(tuple(c)))
olho = [vi for vi, cs in vc.items() if any(c != 'pele' for c in cs) and me.vertices[vi].co.z > 1.1 and me.vertices[vi].co.y < 0]
P = np.array([tuple(me.vertices[i].co) for i in olho])
res = {}
for sd, sg in (('L', 1), ('R', -1)):
    Q = P[P[:, 0] * sg > 0.05]
    res[sd] = dict(n=len(Q), centro=Q.mean(0).round(4).tolist(), min=Q.min(0).round(3).tolist(), max=Q.max(0).round(3).tolist())
C = json.load(open(REPO + '/olhos-v5/olhos-v5-construcao.json'))
cl = np.array(C['L']['centro_janela']); cr = np.array(C['R']['centro_janela']) * [-1, 1, 1]
fl = np.array(C['L']['eixo_f']); fr = np.array(C['R']['eixo_f']) * [-1, 1, 1]
cs = (cl + cr) / 2; fs = (fl + fr); fs /= np.linalg.norm(fs)
res['simetrico'] = dict(centro_janela=cs.round(4).tolist(), eixo=fs.round(4).tolist(), meia_largura=(C['L']['meia_largura'] + C['R']['meia_largura']) / 2,
                        meia_altura=(C['L']['meia_altura'] + C['R']['meia_altura']) / 2, angulo_para_fora_graus=round(math.degrees(math.atan2(fs[0], -fs[1])), 1))
json.dump(res, open(OUT, 'w'), indent=1); print(json.dumps(res, indent=1))
