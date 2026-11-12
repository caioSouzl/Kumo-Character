"""Ombros: mede o que acontece ao erguer o braço (mesmo método de sempre: pares de triângulos novos que se cruzam,
compressão e esticamento das arestas). Só leitura.  python medir_ombros.py <blend> <saida.json>"""
import bpy, sys, json, math
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
SRC, OUT = sys.argv[-2:]
bpy.ops.wm.open_mainfile(filepath=SRC)
rig = bpy.data.objects['Kumo_Rig']; body = bpy.data.objects['Kumo']; pb = rig.pose.bones
if rig.animation_data: rig.animation_data.action = None
for m in body.modifiers:
    if m.type != 'ARMATURE': m.show_viewport = False
gi = {g.index: g.name for g in body.vertex_groups}; BN = {b.name for b in rig.data.bones if b.use_deform}
def dom(v):
    ws = [(gi[g.group], g.weight) for g in v.groups if gi[g.group] in BN]; return max(ws, key=lambda x: x[1])[0] if ws else None
def regiao(sd):
    ok = {f'shoulder.{sd}', f'upper_arm.{sd}', 'chest', 'spine', 'neck', f'forearm.{sd}'}
    vs = {v.index for v in body.data.vertices if dom(v) in ok}
    return {p.index for p in body.data.polygons if all(i in vs for i in p.vertices)}, vs
def geo(fs, vs):
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get(); ev = body.evaluated_get(dg); m = ev.to_mesh(); m.calc_loop_triangles()
    V = [ev.matrix_world @ v.co for v in m.vertices]; T = [tuple(t.vertices) for t in m.loop_triangles if t.polygon_index in fs]
    E = [(e.vertices[0], e.vertices[1]) for e in m.edges if e.vertices[0] in vs and e.vertices[1] in vs]; ev.to_mesh_clear(); return V, T, E
def pares(V, T):
    t = BVHTree.FromPolygons(V, T); return {(a, b) for a, b in t.overlap(t) if a < b and not (set(T[a]) & set(T[b]))}
def prof(V, T, p):
    out = []
    for x, y in (p, p[::-1]):
        a0, a1, a2 = (V[i] for i in T[x]); n = (a1 - a0).cross(a2 - a0)
        if n.length < 1e-12: return 0
        n.normalize(); ds = [n.dot(V[i] - a0) for i in T[y]]; out.append(min(max(0, max(ds)), max(0, -min(ds))))
    return min(out)
def reset():
    for b in pb: b.rotation_quaternion = (1, 0, 0, 0); b.rotation_euler = (0, 0, 0); b.location = (0, 0, 0)
    bpy.context.view_layer.update()
def rotw(n, axis, deg):
    b = pb[n]; bpy.context.view_layer.update(); M = b.matrix.copy(); h = M.to_translation()
    b.matrix = Matrix.Translation(h) @ Matrix.Rotation(math.radians(deg), 4, axis.normalized()) @ Matrix.Translation(-h) @ M; bpy.context.view_layer.update()
def bdir(n): return (pb[n].tail - pb[n].head).normalized()
import os
K = float(os.environ.get('OMBRO_K', '0'))      # fração do giro feita pelo ombro (clavícula), acima de 30°
def com_ombro(sd, ax, deg):
    s_ = max(0.0, abs(deg) - 30) * K * (1 if deg > 0 else -1)
    if s_: rotw(f'shoulder.{sd}', ax, s_)
    rotw(f'upper_arm.{sd}', ax, deg - s_)
def erguer(sd, deg): com_ombro(sd, bdir(f'upper_arm.{sd}').cross(Vector((0, 0, 1))), deg)          # abre o braço para o lado, para cima
def frente(sd, deg): com_ombro(sd, bdir(f'upper_arm.{sd}').cross(Vector((0, -1, 0))), deg)       # leva o braço para a frente
POSES = {**{f'erguer_{a}': (lambda sd, a=a: erguer(sd, a)) for a in (45, 60, 90, 120, 150)},
         'frente_90': lambda sd: frente(sd, 90), 'tras_30': lambda sd: frente(sd, -30),
         'erguer_90_cotovelo_90': lambda sd: (erguer(sd, 90), rotw(f'forearm.{sd}', bdir(f'forearm.{sd}').cross(Vector((0, -1, 0))), 90))}
REP = {}
for sd in ('L', 'R'):
    fs, vs = regiao(sd); reset(); V0, T0, E0 = geo(fs, vs); r0 = pares(V0, T0); L0 = [(V0[a] - V0[b]).length for a, b in E0]; out = {'repouso_pares': len(r0)}
    for nm, fn in POSES.items():
        reset(); fn(sd); V, T, E = geo(fs, vs); P = pares(V, T) - r0; ds = [prof(V, T, p) for p in P]
        rt = sorted((V[a] - V[b]).length / l for (a, b), l in zip(E, L0) if l > 1e-7)
        out[nm] = dict(reais=sum(1 for d in ds if d >= 0.0005), prof_max_mm=round(max(ds) * 1000, 1) if ds else 0, compressao_min=round(rt[0], 3), esticamento_max=round(rt[-1], 3))
        print('OM', sd, nm, out[nm], flush=True)
    REP[sd] = out
reset(); json.dump(REP, open(OUT, 'w'), indent=1)
