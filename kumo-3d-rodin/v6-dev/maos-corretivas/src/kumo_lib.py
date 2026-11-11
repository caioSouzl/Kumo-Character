"""Funções comuns (teste de cruzamento e poses), copiadas de bracos-originais-dedos/src/maos_com_dedos.py sem mudar o método."""
import bpy, math
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
import numpy as np

def smooth01(x):
    x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
def ss(x, a, b): return smooth01((x - a) / (b - a))

class Kumo:
    def __init__(self, rig, body):
        self.rig, self.body = rig, body
        self.BONES = {b.name for b in rig.data.bones}
        self.gi = {g.index: g.name for g in body.vertex_groups}
        self.MAOS = {}
        for sd in ('L', 'R'):
            hb = rig.data.bones[f'hand.{sd}']; M = hb.matrix_local.to_3x3()
            down = M.col[1].normalized(); pn = M.col[2].normalized()
            body_dir = Vector((-1 if sd == 'L' else 1, 0, 0)); lat = down.cross(pn).normalized()
            if lat.dot(body_dir) > 0: lat = -lat
            self.MAOS[sd] = dict(down=down, pn=pn, lat=lat, Wn=hb.head_local.copy())
    def handb(self, sd):
        return {f'forearm.{sd}', f'hand.{sd}', f'metacarpo.{sd}', f'polegar_1.{sd}', f'polegar_2.{sd}'} | {f'dedo{k}_{j}.{sd}' for k in (1, 2, 3) for j in (1, 2)}
    def dominante(self, v):
        ws = [(self.gi[g.group], g.weight) for g in v.groups if self.gi[g.group] in self.BONES]
        return max(ws, key=lambda x: x[1])[0] if ws else None
    def regiao(self, sd):
        me = self.body.data; hb = self.handb(sd)
        vs = {v.index for v in me.vertices if self.dominante(v) in hb}
        fs = {p.index for p in me.polygons if all(i in vs for i in p.vertices)}
        return fs, vs
    def avaliar(self):
        bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get(); ev = self.body.evaluated_get(dg); m = ev.to_mesh()
        V = np.array([tuple(ev.matrix_world @ v.co) for v in m.vertices]); N = np.array([tuple((ev.matrix_world.to_3x3() @ v.normal).normalized()) for v in m.vertices])
        ev.to_mesh_clear(); return V, N
    def tri_data(self, region, region_v):
        bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get(); ev = self.body.evaluated_get(dg); m = ev.to_mesh(); m.calc_loop_triangles()
        V = [ev.matrix_world @ v.co for v in m.vertices]
        T = [tuple(t.vertices) for t in m.loop_triangles if t.polygon_index in region]
        E_ = [(e.vertices[0], e.vertices[1]) for e in m.edges if e.vertices[0] in region_v and e.vertices[1] in region_v]
        ev.to_mesh_clear(); return V, T, E_
    @staticmethod
    def self_pairs(V, T):
        b = BVHTree.FromPolygons(V, T); return {(a_, b_) for a_, b_ in b.overlap(b) if a_ < b_ and not (set(T[a_]) & set(T[b_]))}
    @staticmethod
    def depth(V, T, pair):
        out = []
        for x, y in (pair, pair[::-1]):
            a0, a1, a2 = (V[i] for i in T[x]); n = (a1 - a0).cross(a2 - a0)
            if n.length < 1e-12: return 0.0
            n.normalize(); ds = [n.dot(V[i] - a0) for i in T[y]]; out.append(min(max(0.0, max(ds)), max(0.0, -min(ds))))
        return min(out)
    def classify(self, V, T, pairs):
        pairs = list(pairs); ds = [self.depth(V, T, p) for p in pairs]
        return dict(reais=sum(1 for x in ds if x >= 0.0005), rasantes=sum(1 for x in ds if x < 0.0005), prof_max_mm=round(max(ds) * 1000, 2) if ds else 0.0)
    def reset(self):
        for pb in self.rig.pose.bones:
            pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.rotation_euler = (0, 0, 0)
        bpy.context.view_layer.update()
    def rot_world(self, name, axis, deg):
        pb = self.rig.pose.bones[name]; bpy.context.view_layer.update(); M = pb.matrix.copy(); h = M.to_translation()
        pb.matrix = Matrix.Translation(h) @ Matrix.Rotation(math.radians(deg), 4, Vector(axis).normalized()) @ Matrix.Translation(-h) @ M
        bpy.context.view_layer.update()
    def bdir(self, n): pb = self.rig.pose.bones[n]; return (pb.tail - pb.head).normalized()
    def bend(self, n): return self.bdir(n).cross(Vector((0, -1, 0))).normalized()
    def side_ax(self, n): return self.bdir(n).cross(self.bend(n)).normalized()
    def poses(self, sd, tfist=0.0, polegar_sobre=None):
        m = self.MAOS[sd]; R = self.rot_world; bdir = self.bdir
        # eixos da palma na pose atual (iguais aos de repouso quando o punho não gira; corrige a pose combinada)
        def eixos():
            bpy.context.view_layer.update(); Q = self.rig.pose.bones[f'hand.{sd}'].matrix.to_3x3() @ self.rig.data.bones[f'hand.{sd}'].matrix_local.to_3x3().inverted()
            return (Q @ m['pn']).normalized(), (Q @ m['lat']).normalized()
        curl = lambda n: bdir(n).cross(eixos()[0]).normalized()
        spr = lambda n: eixos()[1].cross(bdir(n)).normalized()
        dedos = [f'dedo{k}_{j}.{sd}' for k in (1, 2, 3) for j in (1, 2)]
        def fist(a, sobre=None):
            def f():
                R(f'metacarpo.{sd}', curl(f'metacarpo.{sd}'), a * 20 / 70)
                for n in dedos: R(n, curl(n), a)
                if sobre:     # polegar dobrado por cima dos dedos: (abertura para o centro, dobra 1, dobra 2), proporcional a a/70
                    k = a / 70; s1, c1, c2 = sobre
                    R(f'polegar_1.{sd}', spr(f'polegar_1.{sd}'), s1 * k); R(f'polegar_1.{sd}', curl(f'polegar_1.{sd}'), c1 * k)
                    R(f'polegar_2.{sd}', curl(f'polegar_2.{sd}'), c2 * k)
                else:
                    for n in (f'polegar_1.{sd}', f'polegar_2.{sd}'): R(n, curl(n), a * tfist)
            return f
        def aberta():
            R(f'dedo1_1.{sd}', spr(f'dedo1_1.{sd}'), 15); R(f'dedo3_1.{sd}', spr(f'dedo3_1.{sd}'), -15)
            R(f'polegar_1.{sd}', spr(f'polegar_1.{sd}'), 20)
            for n in dedos + [f'polegar_1.{sd}', f'polegar_2.{sd}']: R(n, curl(n), -10)
        def dedos45():
            for n in dedos: R(n, curl(n), 45)
        def polegar():
            R(f'polegar_1.{sd}', spr(f'polegar_1.{sd}'), 20); R(f'polegar_1.{sd}', curl(f'polegar_1.{sd}'), 35)
            R(f'polegar_2.{sd}', curl(f'polegar_2.{sd}'), 45)
        def alternados():
            for k, a in ((1, 70), (2, 30), (3, 0)):
                for j in (1, 2): R(f'dedo{k}_{j}.{sd}', curl(f'dedo{k}_{j}.{sd}'), a)
            R(f'polegar_1.{sd}', curl(f'polegar_1.{sd}'), 15)
        def palma(): R(f'metacarpo.{sd}', curl(f'metacarpo.{sd}'), 20)
        def br(n, ax, deg):
            def f(): R(n, self.bend(n) if ax == 'B' else self.side_ax(n), deg)
            return f
        def both(*fs):
            def f():
                for x in fs: x()
            return f
        P = {'mao_fechada': fist(70), 'mao_aberta': aberta, 'dedos_45': dedos45, 'polegar': polegar, 'dedos_alternados': alternados,
             'palma_curvada_20': palma, 'punho_45': br(f'hand.{sd}', 'B', 45), 'punho_menos45': br(f'hand.{sd}', 'B', -45),
             'punho_lateral_30': br(f'hand.{sd}', 'S', 30), 'punho_lateral_menos30': br(f'hand.{sd}', 'S', -30),
             'cotovelo_90': br(f'forearm.{sd}', 'B', 90), 'cotovelo_100': br(f'forearm.{sd}', 'B', 100),
             'cotovelo_90_punho_45_mao_fechada': both(br(f'forearm.{sd}', 'B', 90), br(f'hand.{sd}', 'B', 45), fist(70)),
             **{f'fechar_{a}': fist(a) for a in range(30, 75, 10)}}
        if polegar_sobre:
            P.update({'mao_fechada_polegar_sobre': fist(70, polegar_sobre),
                      **{f'fechar_{a}_polegar_sobre': fist(a, polegar_sobre) for a in range(30, 75, 10)},
                      'cotovelo_90_punho_45_mao_fechada_polegar_sobre': both(br(f'forearm.{sd}', 'B', 90), br(f'hand.{sd}', 'B', 45), fist(70, polegar_sobre))})
        return P
