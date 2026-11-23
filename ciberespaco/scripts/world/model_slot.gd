class_name ModelSlot
extends RefCounted
## Troca o modelo provisorio por um .glb exportado do Hyper3D, se existir.
## O Hyper3D entrega malhas estaticas com escala livre: aqui o modelo e
## normalizado para a altura pedida, centralizado e apoiado no chao (y = 0).
## As animacoes (flutuar, girar, cair) sao feitas no no pai, entao funcionam
## com o modelo provisorio e com o .glb.


static func try_load(path: String, target_height: float) -> Node3D:
	if path == "" or not ResourceLoader.exists(path):
		return null
	var res: Resource = load(path)
	if not (res is PackedScene):
		push_warning("Modelo %s nao e uma cena importada." % path)
		return null
	var inst: Node = (res as PackedScene).instantiate()
	if not (inst is Node3D):
		inst.queue_free()
		return null
	var holder := Node3D.new()
	holder.name = "Modelo_" + path.get_file().get_basename()
	holder.add_child(inst)
	var box := _aabb(inst as Node3D, Transform3D.IDENTITY)
	if box.size.y > 0.0001:
		var s := target_height / box.size.y
		var n3 := inst as Node3D
		n3.scale = Vector3.ONE * s
		var c := box.get_center() * s
		n3.position = Vector3(-c.x, -box.position.y * s, -c.z)
	_no_shadows(inst)
	return holder


## Raio horizontal (x/z) do modelo ja normalizado.
static func footprint(holder: Node3D) -> float:
	var b := _aabb(holder, Transform3D.IDENTITY)
	return maxf(b.size.x, b.size.z) * 0.5


static func _aabb(n: Node3D, xf: Transform3D) -> AABB:
	var t := xf * n.transform
	var out := AABB()
	var first := true
	if n is VisualInstance3D:
		var b: AABB = t * (n as VisualInstance3D).get_aabb()
		out = b
		first = false
	for c in n.get_children():
		if c is Node3D:
			var cb := _aabb(c as Node3D, t)
			if cb.size == Vector3.ZERO and cb.position == Vector3.ZERO:
				continue
			out = cb if first else out.merge(cb)
			first = false
	return out


static func _no_shadows(n: Node) -> void:
	if n is GeometryInstance3D:
		(n as GeometryInstance3D).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	for c in n.get_children():
		_no_shadows(c)
