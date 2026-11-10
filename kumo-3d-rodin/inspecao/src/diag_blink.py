import bpy, sys, math
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=sys.argv[-2]); out=sys.argv[-1]
sc=bpy.context.scene
img=bpy.data.images['kumo_quad_diffuse']; img.filepath='/home/user/kumo-character/kumo-3d-rodin/textures/kumo_quad_diffuse.png'; img.reload()
red=bpy.data.materials.new('red'); red.use_nodes=True; nt=red.node_tree
for n in list(nt.nodes): nt.nodes.remove(n)
o=nt.nodes.new('ShaderNodeOutputMaterial'); e=nt.nodes.new('ShaderNodeEmission'); e.inputs[0].default_value=(1,0.05,0.05,1); nt.links.new(e.outputs[0],o.inputs[0])
for tag in ('L','R'):
    lid=bpy.data.objects[f'Kumo_Lid_{tag}']
    for i in range(len(lid.data.materials)): lid.data.materials[i]=red
cam=bpy.data.objects['Cam_Front']; sc.camera=cam
sc.render.resolution_x=sc.render.resolution_y=900
for t in (0.0,0.3,0.5,0.7,1.0):
    for tag in ('L','R'): bpy.data.objects[f'Kumo_Lid_{tag}'].data.shape_keys.key_blocks[f'Blink_{tag}'].value=t
    for name,az,tgt,size in (('frente',0,(0,-0.3,1.38),0.9),('34',-50,(0.25,-0.3,1.38),0.75)):
        a=math.radians(az); T=Vector(tgt); cam.location=T+Vector((math.sin(a)*10,-math.cos(a)*10,0)); cam.rotation_euler=(T-cam.location).to_track_quat('-Z','Y').to_euler(); cam.data.ortho_scale=size
        sc.render.filepath=f'{out}/diag-{name}-{int(t*100):03d}.png'; bpy.ops.render.render(write_still=True)
