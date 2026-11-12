"""P2 fiel · plano de simetria da cabeça (só leitura): giro em Z e deslocamento que melhor espelham a cabeça nela mesma."""
import bpy, sys, json, math, numpy as np
from mathutils.kdtree import KDTree
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=sys.argv[-1]); me = bpy.data.objects['Kumo'].data
P = np.array([tuple(v.co) for v in me.vertices if v.co.z > 1.0 and abs(v.co.x) < 0.65])
kd = KDTree(len(P)); [kd.insert(Vector(p), i) for i, p in enumerate(P)]; kd.balance()
best = None
for th in np.arange(-25, 25.1, 0.5):
    n = np.array([math.cos(math.radians(th)), math.sin(math.radians(th)), 0])
    for off in np.arange(-0.08, 0.081, 0.01):
        d = P @ n - off; M = P - 2 * d[:, None] * n
        e = np.mean([kd.find(Vector(m))[2] for m in M[::7]])
        if best is None or e < best[0]: best = (e, th, off)
print('MELHOR giro %.1f graus, deslocamento %.3f, erro medio %.1f mm' % (best[1], best[2], best[0] * 1000))
n = np.array([1, 0, 0]); d = P @ n; M = P - 2 * d[:, None] * n
print('sem giro (plano x=0): erro medio %.1f mm' % (np.mean([kd.find(Vector(m))[2] for m in M[::7]]) * 1000))
