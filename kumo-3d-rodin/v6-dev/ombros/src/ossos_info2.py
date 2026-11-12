import bpy, sys, collections
bpy.ops.wm.open_mainfile(filepath=sys.argv[-1]); body=bpy.data.objects['Kumo']; gi={g.index:g.name for g in body.vertex_groups}
D=collections.defaultdict(list)
for v in body.data.vertices:
    gs=[g for g in v.groups if g.weight>0 and not gi[g.group].startswith('outline')]
    if not gs: continue
    g=max(gs,key=lambda g:g.weight); D[gi[g.group]].append(tuple(body.matrix_world@v.co))
for bn in ('chest','neck','shoulder.L','upper_arm.L','forearm.L'):
    P=D[bn]; 
    if not P: print('M',bn,0); continue
    print('M',bn,len(P),*[(round(min(p[i] for p in P),3),round(max(p[i] for p in P),3)) for i in range(3)])
# perfil: z máximo da pele do tronco/braço por faixa de x (silhueta frontal, |y| qualquer), só vértices não-cabeça
for x0 in [0.15,0.2,0.25,0.3,0.35]:
    zs=[p[2] for bn,P in D.items() if bn in('chest','spine','shoulder.L','upper_arm.L','neck') for p in P if x0-0.025<=p[0]<x0+0.025]
    print('X',x0,round(min(zs),3) if zs else None,round(max(zs),3) if zs else None)
