"""Mede, no olho antigo (camadas deslizantes), quanto e para onde a íris anda em cada direção do olhar.
Serve de régua para o olho novo: o sentido do olhar tem de ser o mesmo.
  blender --background ../boca/kumo_v6_boca.blend --python olhar_antigo.py -- <saida.json>"""
import bpy, sys, json, numpy as np
out = sys.argv[-1]; rig = bpy.data.objects['Kumo_Rig']; pb = rig.pose.bones
I = json.load(open(__file__.replace('olhar_antigo.py', 'janelas_v5.json')))
def pt(s):
    o = bpy.data.objects[f'KumoJogo_Iris.{s}']; ic = I[s]['iris_centro']
    uv = o.data.uv_layers.active.data; best = None
    for lp in o.data.loops:
        d = (uv[lp.index].uv[0] - ic[0]) ** 2 + (uv[lp.index].uv[1] - ic[1]) ** 2
        if best is None or d < best[0]: best = (d, lp.vertex_index)
    dg = bpy.context.evaluated_depsgraph_get(); ev = o.evaluated_get(dg); m = ev.to_mesh(); p = ev.matrix_world @ m.vertices[best[1]].co; ev.to_mesh_clear(); return p
R = {'L': {}, 'R': {}}
for nome, (x, y) in (('dir', (1, 0)), ('esq', (-1, 0)), ('cima', (0, 1)), ('baixo', (0, -1))):
    pb['controle_olhar'].location = (0, 0, 0); bpy.context.view_layer.update(); p0 = {s: pt(s) for s in 'LR'}
    pb['controle_olhar'].location = (x, y, 0); bpy.context.view_layer.update()
    for s in 'LR': R[s][nome] = list(pt(s) - p0[s])
json.dump(R, open(out, 'w'), indent=1); print('OK', R)
