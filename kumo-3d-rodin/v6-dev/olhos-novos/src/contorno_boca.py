"""Contorno da boca (pedido do Caio, 26/11): a casca do contorno não acompanhava o corte da boca e se deformava com a
mandíbula (serrilhado e faixa esticada de lado). Aqui se apagam as faces da casca que têm peso na mandíbula; o contorno
então termina na borda da cabeça e não cobre a abertura.
  blender --background kumo_v6_olhos_novos.blend --python src/contorno_boca.py -- <saída.blend>
"""
import bpy, sys, bmesh
OUT = sys.argv[-1]
c = bpy.data.objects['Kumo_Contorno']
gi = c.vertex_groups['jaw'].index
peso = {v.index: max([g.weight for g in v.groups if g.group == gi] or [0]) for v in c.data.vertices}
bm = bmesh.new(); bm.from_mesh(c.data); bm.faces.ensure_lookup_table()
apagar = [f for f in bm.faces if any(peso[v.index] > 0.05 for v in f.verts)]
bmesh.ops.delete(bm, geom=apagar, context='FACES'); bm.to_mesh(c.data); bm.free(); c.data.update()
print('CONTORNO_FACES_APAGADAS', len(apagar))
bpy.ops.wm.save_as_mainfile(filepath=OUT)
