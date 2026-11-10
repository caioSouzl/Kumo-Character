import bpy, bmesh, sys, json, math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
bpy.ops.wm.open_mainfile(filepath=sys.argv[-1])
body=bpy.data.objects['Kumo']; me=body.data
cut=body.vertex_groups['outline_cut'].index
bm=bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table(); bm.normal_update()
bvh=BVHTree.FromBMesh(bm)
out={}
eye={1:[],-1:[]}
for v in me.vertices:
    if v.co.z>1.0 and any(g.group==cut and g.weight>0.5 for g in v.groups): eye[1 if v.co.x>0 else -1].append(v.index)
img=bpy.data.images['kumo_quad_diffuse']; img.filepath='/home/user/kumo-character/kumo-3d-rodin/textures/kumo_quad_diffuse.png'; img.reload(); px=list(img.pixels); N=img.size[0]; uvl=me.uv_layers.active.data
def col(vi):
    acc=Vector();n=0
    for l in me.loops:
        pass
    return None
# per-vertex colour (avg of its loops)
vc={}
for p in me.polygons:
    for li in p.loop_indices:
        u,v=uvl[li].uv; i=(min(N-1,int(v*N))*N+min(N-1,int(u*N)))*4
        vc.setdefault(me.loops[li].vertex_index,[]).append(px[i:i+3])
def avg(i):
    c=vc[i]; return [sum(x[k] for x in c)/len(c) for k in range(3)]
def cls(rgb):
    r,g,b=rgb; mx=max(rgb); mn=min(rgb)
    if mx<0.12: return 'pupil'
    if mn>0.85: return 'catchlight'
    if r>0.6 and g>0.45 and b<0.55 and r>b+0.2: return 'iris_or_sclera'
    if r>0.4 and r>g and r>b+0.15: return 'amber_ring'
    if g>r and g>b: return 'skin'
    return 'dark_rim'
for s,tag in ((1,'L'),(-1,'R')):
    ids=eye[s]; P=[me.vertices[i].co for i in ids]
    c=sum(P,Vector())/len(P)
    rx=(max(p.x for p in P)-min(p.x for p in P))/2; rz=(max(p.z for p in P)-min(p.z for p in P))/2
    front=min(p.y for p in P)
    # socket floor: deepest point (max y) inside the eye footprint
    deep=max(p.y for p in P)
    # rim: skin vertices on the ring just outside the painted eye
    ring=[v.co for v in me.vertices if v.co.z>1.0 and v.co.x*s>0 and v.index not in ids and ((v.co.x-c.x)/rx)**2+((v.co.z-c.z)/rz)**2<1.5]
    rim_front=min(p.y for p in ring) if ring else None
    classes={}
    for i in ids: k=cls(avg(i)); classes[k]=classes.get(k,0)+1
    # sphere fit of the front dome (least squares on painted iris/pupil verts)
    dome=[me.vertices[i].co for i in ids if cls(avg(i)) in ('pupil','iris_or_sclera','amber_ring','catchlight')]
    import itertools
    A=[[2*p.x,2*p.y,2*p.z,1] for p in dome]; bvec=[p.length_squared for p in dome]
    # normal equations 4x4
    M=[[sum(a[i]*a[j] for a in A) for j in range(4)] for i in range(4)]; y=[sum(a[i]*bb for a,bb in zip(A,bvec)) for i in range(4)]
    # gaussian elimination
    for i in range(4):
        piv=M[i][i]
        for j in range(i+1,4):
            f=M[j][i]/piv
            for k in range(4): M[j][k]-=f*M[i][k]
            y[j]-=f*y[i]
    x=[0]*4
    for i in range(3,-1,-1): x[i]=(y[i]-sum(M[i][k]*x[k] for k in range(i+1,4)))/M[i][i]
    sc=Vector(x[:3]); R=math.sqrt(x[3]+sc.length_squared)
    res=[abs((p-sc).length-R) for p in dome]
    out[tag]=dict(painted_verts=len(ids), centre=[round(v,3) for v in c], half_width=round(rx,3), half_height=round(rz,3),
        dome_front_y=round(front,3), socket_deepest_y=round(deep,3), rim_front_y=round(rim_front,3) if rim_front else None,
        dome_protrusion_vs_rim=round(rim_front-front,3) if rim_front else None,
        colour_classes=classes, sphere_fit=dict(centre=[round(v,3) for v in sc], radius=round(R,3), rms=round(math.sqrt(sum(r*r for r in res)/len(res)),4)))
# lids: intersection test with the head at several blink values (lid vertices inside the head volume)
def inside(p):
    hits=0; o=p.copy(); d=Vector((0.0123,0.0071,1.0)).normalized()
    while True:
        loc,n,i,dist=bvh.ray_cast(o,d)
        if loc is None: break
        hits+=1; o=loc+d*1e-5
    return hits%2==1
lid_report={}
for tag in ('L','R'):
    lid=bpy.data.objects[f'Kumo_Lid_{tag}']; kb=lid.data.shape_keys.key_blocks
    base=[v.co.copy() for v in kb['Basis'].data]; blink=[v.co.copy() for v in kb[f'Blink_{tag}'].data]
    mw=lid.matrix_world
    rows=[]
    for t in (0.0,0.25,0.5,0.75,1.0):
        pts=[mw@(b+(c-b)*t) for b,c in zip(base,blink)]
        ins=sum(1 for p in pts if inside(p))
        # distance from the dome surface
        dists=[]
        for p in pts:
            loc,n,i,d=bvh.find_nearest(p); dists.append((p-loc).dot(n))
        rows.append(dict(t=t, verts_inside_head=ins, of=len(pts), min_signed_dist=round(min(dists),4), max_dist=round(max(dists),4)))
    # world placement check: lid basis vs head at rest
    lid_report[tag]=dict(parent=lid.parent.name if lid.parent else None, parent_bone=lid.parent_bone, rows=rows,
        max_vertex_travel=round(max((c-b).length for b,c in zip(base,blink)),4))
out['lids']=lid_report
# weights of the eye region vs lid parenting
heads=[]
for tag,s in (('L',1),('R',-1)):
    ws={}
    for i in eye[s]:
        for g in me.vertices[i].groups:
            n=body.vertex_groups[g.group].name
            if n in ('head','neck','chest','outline_cut','outline_shell'): continue
            ws[n]=ws.get(n,0)+g.weight
    hd=sum(g.weight for i in eye[s] for g in me.vertices[i].groups if body.vertex_groups[g.group].name=='head')/len(eye[s])
    heads.append((tag,round(hd,3),{k:round(v/len(eye[s]),3) for k,v in sorted(ws.items(),key=lambda x:-x[1])[:4]}))
out['eye_region_weights']=heads
print(json.dumps(out))
json.dump(out,open(sys.argv[-1].replace('copy.blend','eye_inspect.json'),'w'),indent=1)
# painted iris / pupil centres and sizes (more reliable than the grown outline mask)
extra={}
for s,tag in ((1,'L'),(-1,'R')):
    near=[v.index for v in me.vertices if v.co.z>1.05 and v.co.x*s>0.05 and v.co.y<-0.3]
    pts={k:[me.vertices[i].co for i in near if cls(avg(i))==k] for k in ('pupil','iris_or_sclera','amber_ring','catchlight')}
    allp=pts['pupil']+pts['iris_or_sclera']+pts['amber_ring']
    def box(P): return dict(x=[round(min(p.x for p in P),3),round(max(p.x for p in P),3)],z=[round(min(p.z for p in P),3),round(max(p.z for p in P),3)],y=[round(min(p.y for p in P),3),round(max(p.y for p in P),3)]) if P else None
    extra[tag]=dict(eye_visible=box(allp), pupil=box(pts['pupil']), catchlight=box(pts['catchlight']))
print('EXTRA',json.dumps(extra))
