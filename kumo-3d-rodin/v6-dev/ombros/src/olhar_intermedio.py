"""Olhar sem buraco no meio do caminho.

As shape keys do olhar (Olhar_dir/esq/cima/baixo) guardam o olho girado 11°. Entre 0 e 1 o Blender (e o jogo) mistura
as posições em LINHA RETA, que corta por dentro da curva do olho: no meio do caminho as camadas (íris, pupila, brilho)
afundam umas nas outras e aparecem buracos pretos (visto com o olhar a 35%). Aqui cada olhar ganha 3 chaves
intermediárias (25%, 50%, 75%): a mistura em linha reta é COLADA de volta na casca do globo, na mesma altura em que
cada ponto estava (as camadas deslizam sobre o olho; não é um giro rígido), e os drivers passam de uma para a outra. Em 0 e em 100% nada muda.

  python olhar_intermedio.py <entrada.blend> <saída.blend>
"""
import bpy, sys, math
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
SRC, DST = sys.argv[-2:]
bpy.ops.wm.open_mainfile(filepath=SRC)
PASSOS = (0.25, 0.5, 0.75)
FORM = {'Olhar_dir': 'x', 'Olhar_esq': '(-x)', 'Olhar_cima': 'y', 'Olhar_baixo': '(-y)'}
rel = {}
def em_mundo(o, pts): M = np.array(o.matrix_world); return pts @ M[:3, :3].T + M[:3, 3]
def de_mundo(o, pts): M = np.linalg.inv(np.array(o.matrix_world)); return pts @ M[:3, :3].T + M[:3, 3]
for lado in 'LR':
    base = bpy.data.objects[f'KumoJogo_OlhoBase.{lado}']
    BV = em_mundo(base, np.array([tuple(v.co) for v in base.data.vertices]))
    arv = BVHTree.FromPolygons([Vector(p) for p in BV], [tuple(p.vertices) for p in base.data.polygons])
    def colar(P):
        """ponto mais perto na casca do globo e a altura (sinal pela normal) acima dela"""
        Q = np.zeros_like(P); N = np.zeros_like(P); h = np.zeros(len(P))
        for i, p in enumerate(P):
            q, n, _, _ = arv.find_nearest(Vector(p)); n = n.normalized(); Q[i] = q; N[i] = n; h[i] = (Vector(p) - q).dot(n)
        return Q, N, h
    for nome in ('Iris', 'Pupil', 'Catchlight'):
        o = bpy.data.objects[f'KumoJogo_{nome}.{lado}']; kb = o.data.shape_keys.key_blocks; ad = o.data.shape_keys.animation_data
        B0 = em_mundo(o, np.array([tuple(v.co) for v in kb['Basis'].data])); _, _, h0 = colar(B0)
        for k in FORM:
            B1 = em_mundo(o, np.array([tuple(v.co) for v in kb[k].data])); _, _, h1 = colar(B1)
            # só os pontos que estão sobre o globo (a grade passa da borda do olho; fora dele não há o que colar)
            sobre = (np.abs(h0) < 0.002) & (np.abs(h1) < 0.002)
            fc0 = next(f for f in ad.drivers if f.data_path == f'key_blocks["{k}"].value'); var = fc0.driver.variables[0]
            T = FORM[k].replace('x', var.name).replace('y', var.name); pior = 0.0; KS = {0.0: B0, 1.0: B1}
            for s in PASSOS:
                # mistura em linha reta (corta por dentro do olho) e cola de volta na casca, na altura que o ponto tinha
                L = (1 - s) * B0 + s * B1; Q, N, hl = colar(L); h = (1 - s) * h0 + s * h1
                P = np.where(sobre[:, None], Q + N * h[:, None], L); pior = max(pior, float(np.abs(h - hl)[sobre].max())); KS[s] = P
                nk = o.shape_key_add(name=f'{k}_{int(s * 100)}', from_mix=False)
                Pl = de_mundo(o, P)
                for v, p in zip(nk.data, Pl): v.co = p
                fc = nk.driver_add('value'); dr = fc.driver; dr.type = 'SCRIPTED'
                nv = dr.variables.new(); nv.name = var.name; nv.type = 'TRANSFORMS'; t = nv.targets[0]; t0 = var.targets[0]
                t.id = t0.id; t.bone_target = t0.bone_target; t.transform_type = t0.transform_type; t.transform_space = t0.transform_space
                dr.expression = f'max(0.0, 1.0 - abs({T} - {s}) / 0.25)'
            fc0.driver.expression = f'max(0.0, min(1.0, ({T} - 0.75) / 0.25))'
            # entre duas chaves vizinhas ainda há afundamento (arco x corda): uma chave "ergue" com a correção média do meio
            # de cada trecho, ligada por 4u(1−u) (u = posição dentro do trecho), que é a forma da flecha de um arco
            st = sorted(KS); corr = []
            for a_, b_ in zip(st, st[1:]):
                M_ = 0.5 * (KS[a_] + KS[b_]); Qm, Nm, hm = colar(M_); hh = 0.5 * (colar(KS[a_])[2] + colar(KS[b_])[2])
                corr.append(np.where(sobre[:, None], Qm + Nm * hh[:, None] - M_, 0.0))
            D = np.mean(corr, axis=0); B0l = de_mundo(o, B0); Dl = de_mundo(o, B0 + D) - B0l
            nk = o.shape_key_add(name=f'{k}_ergue', from_mix=False)
            for v, p0, d in zip(nk.data, B0l, Dl): v.co = p0 + d
            fc = nk.driver_add('value'); dr = fc.driver; dr.type = 'SCRIPTED'
            nv = dr.variables.new(); nv.name = var.name; nv.type = 'TRANSFORMS'; t = nv.targets[0]; t0 = var.targets[0]
            t.id = t0.id; t.bone_target = t0.bone_target; t.transform_type = t0.transform_type; t.transform_space = t0.transform_space
            u = f'(min(max({T}, 0.0), 1.0) * 4.0 - floor(min(max({T}, 0.0), 1.0) * 4.0))'
            dr.expression = f'4.0 * {u} * (1.0 - {u})'
            # conferência: altura mínima da camada acima do globo em 21 pontos do caminho (0 = encostada)
            minh = 9.0
            for Tv in np.linspace(0, 1, 21):
                if Tv >= 1: Pv = B1
                else:
                    j = min(int(Tv * 4), 3); a_, b_ = st[j], st[j + 1]; uu = Tv * 4 - j
                    Pv = (1 - uu) * KS[a_] + uu * KS[b_] + 4 * uu * (1 - uu) * D
                minh = min(minh, float(colar(Pv)[2][sobre].min()))
            rel[f'{o.name}|{k}'] = dict(afundava_mm=round(pior * 1000, 2), altura_min_mm=round(minh * 1000, 3), altura_repouso_mm=round(float(h0[sobre].min()) * 1000, 3), pontos_sobre=int(sobre.sum()))
bpy.ops.wm.save_as_mainfile(filepath=DST, copy=True, relative_remap=False)
import json; print('OI OK'); print(json.dumps(rel, indent=0))
