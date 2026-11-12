"""P2 fiel · olhos simétricos no quadro da própria cabeça (giro de 8,5° em Z medido em simetria.py)."""
import json, math, sys, numpy as np
C = json.load(open('/home/user/Kumo-Character/kumo-3d-rodin/olhos-v5/olhos-v5-construcao.json'))
TH = math.radians(float(sys.argv[1]) if len(sys.argv) > 1 else 8.5)
Rz = lambda a: np.array([[math.cos(a), -math.sin(a), 0], [math.sin(a), math.cos(a), 0], [0, 0, 1]])
# quadro da cabeça: normal do plano de simetria = (cos TH, sin TH, 0) -> girar o mundo por -TH leva o plano a x=0
to_h, to_w = Rz(-TH), Rz(TH)
M = np.diag([-1, 1, 1])
cl = to_h @ np.array(C['L']['centro_janela']); cr = to_h @ np.array(C['R']['centro_janela'])
fl = to_h @ np.array(C['L']['eixo_f']); fr = to_h @ np.array(C['R']['eixo_f'])
c = (cl + M @ cr) / 2; f = fl + M @ fr; f /= np.linalg.norm(f)
out = {}
for sd, S in (('L', np.eye(3)), ('R', M)):
    out[sd] = dict(centro_janela=(to_w @ S @ c).round(4).tolist(), eixo=(to_w @ S @ f).round(4).tolist())
out['meia_largura'] = round((C['L']['meia_largura'] + C['R']['meia_largura']) / 2, 4); out['meia_altura'] = round((C['L']['meia_altura'] + C['R']['meia_altura']) / 2, 4)
out['para_fora_graus_no_quadro_da_cabeca'] = round(math.degrees(math.atan2(f[0], -f[1])), 1)
out['antes'] = {sd: dict(centro=C[sd]['centro_janela'], eixo=C[sd]['eixo_f']) for sd in 'LR'}
out['giro_cabeca_graus'] = math.degrees(TH)
print(json.dumps(out, indent=1))
