"""Onde ficam os cruzamentos restantes: lista os ossos dominantes dos dois triângulos de cada par."""
import bpy, sys, os, math, collections
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'corrigir_ombros.py')).read().split("if not me.shape_keys")[0].replace("SRC, OUT = sys.argv[-2:]; os.makedirs(OUT, exist_ok=True)", "SRC = sys.argv[-1]"))
for sd in 'LR':
    fs, vs = regiao(sd); reset(); V0, T0 = geo(fs); r0 = pares(V0, T0)
    for tipo, a in (('frente', 90), ('erguer', 135), ('erguer', 150)):
        reset(); mover(sd, tipo, a); V, T = geo(fs); P = pares(V, T) - r0; c = collections.Counter()
        for x, y in P:
            if prof(V, T, (x, y)) < 0.0005: continue
            bx = collections.Counter(dom(i) for i in T[x]).most_common(1)[0][0]; by = collections.Counter(dom(i) for i in T[y]).most_common(1)[0][0]
            c[tuple(sorted((bx, by)))] += 1
        print('ONDE', sd, tipo, a, dict(c), flush=True)
