"""Mapa do rosto: a pele da cabeça desenrolada em (ângulo em volta da cabeça, altura), com as cores da textura.
Serve para achar a borda entre o focinho (verde escuro) e a mandíbula (verde claro), onde a boca vai ser cortada.
  python mapa_rosto.py <blend> <saída.png> <saída.npz>"""
import bpy, sys, math
import numpy as np
SRC, OUTP, OUTN = sys.argv[-3:]
bpy.ops.wm.open_mainfile(filepath=SRC)
body = bpy.data.objects['Kumo']; me = body.data; me.calc_loop_triangles()
img = bpy.data.images['kumo_quad_diffuse']; img.filepath = '/home/user/Kumo-Character/kumo-3d-rodin/textures/kumo_quad_diffuse.png'; img.reload()
TW, TH = img.size; TEX = np.array(img.pixels[:]).reshape(TH, TW, 4)[::-1, :, :3]
P = np.array([tuple(body.matrix_world @ v.co) for v in me.vertices]); UV = np.array([tuple(l.uv) for l in me.uv_layers.active.data])
# o rosto do modelo oficial está virado ~16° em volta do eixo vertical (os olhos não estão na mesma profundidade):
# o eixo do rosto vem dos centros dos dois globos dos olhos
EL = np.array([tuple(bpy.data.objects['KumoJogo_OlhoBase.L'].matrix_world @ v.co) for v in bpy.data.objects['KumoJogo_OlhoBase.L'].data.vertices]).mean(0)
ER = np.array([tuple(bpy.data.objects['KumoJogo_OlhoBase.R'].matrix_world @ v.co) for v in bpy.data.objects['KumoJogo_OlhoBase.R'].data.vertices]).mean(0)
dir_ = (EL - ER)[:2]; dir_ /= np.linalg.norm(dir_)          # da direita para a esquerda do Kumo
FRENTE = np.array([dir_[1], -dir_[0]])                         # perpendicular, para −Y
MEIO = 0.5 * (EL + ER)[:2]; CENTRO = MEIO - FRENTE * 0.30      # eixo dentro da cabeça
print('ROSTO giro', round(float(np.degrees(np.arctan2(dir_[1], dir_[0]))), 1), 'centro', CENTRO.round(3), 'frente', FRENTE.round(3))
def theta(p):
    d = p[..., :2] - CENTRO; return np.degrees(np.arctan2(d @ dir_, d @ FRENTE))
amostras = []
rng = np.random.default_rng(0)
for t in me.loop_triangles:
    pv = P[list(t.vertices)]
    if pv[:, 2].max() < 0.95 or pv[:, 2].min() > 1.55: continue
    uv = UV[list(t.loops)]
    for _ in range(6):
        w = rng.dirichlet((1, 1, 1)); p = w @ pv; u = w @ uv
        c = TEX[min(TH - 1, int((1 - u[1]) * TH)) % TH, min(TW - 1, int(u[0] * TW)) % TW]
        amostras.append((theta(p), p[2], *c))
A = np.array(amostras)
np.savez(OUTN, th=A[:, 0], z=A[:, 1], rgb=A[:, 2:5], centro=CENTRO, frente=FRENTE, lado=dir_)
# imagem: θ de −120 a 120 (horizontal), z de 1.55 a 0.95 (vertical)
W, H = 960, 480; im = np.ones((H, W, 3)) * 0.93
xi = ((A[:, 0] + 120) / 240 * (W - 1)).astype(int); yi = ((1.55 - A[:, 1]) / 0.6 * (H - 1)).astype(int)
ok = (xi >= 0) & (xi < W) & (yi >= 0) & (yi < H); im[yi[ok], xi[ok]] = A[ok, 2:5]
from PIL import Image
Image.fromarray((np.clip(im, 0, 1) ** (1 / 2.2) * 255).astype(np.uint8)).save(OUTP)
print('MR', len(A))
