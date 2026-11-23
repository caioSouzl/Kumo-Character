class_name BuildProject
extends Node3D
## Um projeto do ZodIA: um objeto da vida real feito de formas simples.
## Cada peca aparece de baixo para cima conforme o laser "desenha" (shader
## hologram). O Kumo pode fazer tremer, rachar a peca em construcao ou
## derrubar tudo (as pecas viram corpos fisicos e caem no chao).

var project_name := ""
var progress := 0.0

var _def: Dictionary = {}
var _pieces: Array[MeshInstance3D] = []
var _mats: Array[ShaderMaterial] = []
var _crack := 0.0
var _crack_index := -1
var _flash := 0.0
var _t := 0.0


func setup(def: Dictionary) -> void:
	clear()
	_def = def
	project_name = String(def.get("name", "Projeto"))
	for pd in def.get("pieces", []):
		var d: Dictionary = pd
		var mesh := _mesh_for(d)
		var mat := Mat.holo()
		var box := mesh.get_aabb()
		mat.set_shader_parameter("y_min", box.position.y)
		mat.set_shader_parameter("y_max", box.end.y)
		mat.set_shader_parameter("build", 0.0)
		var p: Array = d.get("pos", [0, 0, 0])
		var r: Array = d.get("rot", [0, 0, 0])
		var mi := Mat.add(self, mesh, mat, Vector3(float(p[0]), float(p[1]), float(p[2])), Vector3(float(r[0]), float(r[1]), float(r[2])))
		mi.visible = false
		_pieces.append(mi)
		_mats.append(mat)
	progress = 0.0
	set_progress(0.0)


## Recomeca o mesmo projeto do zero.
func restart() -> void:
	setup(_def)


func clear() -> void:
	for p in _pieces:
		if is_instance_valid(p):
			p.queue_free()
	_pieces.clear()
	_mats.clear()
	position = Vector3(position.x, 0.0, position.z)


func _mesh_for(d: Dictionary) -> Mesh:
	match String(d.get("shape", "box")):
		"cylinder":
			return Mat.cyl(float(d.get("radius", 0.3)), float(d.get("radius", 0.3)), float(d.get("height", 1.0)), 16)
		"cone":
			return Mat.cyl(float(d.get("top_radius", 0.0)), float(d.get("radius", 0.3)), float(d.get("height", 1.0)), 16)
		"sphere":
			return Mat.sphere(float(d.get("radius", 0.3)), -1, 14)
		_:
			var s: Array = d.get("size", [1, 1, 1])
			return Mat.box(Vector3(float(s[0]), float(s[1]), float(s[2])))


func piece_count() -> int:
	return _pieces.size()


func current_index() -> int:
	return clampi(int(progress * _pieces.size()), 0, maxi(_pieces.size() - 1, 0))


func piece_fraction(i: int) -> float:
	return clampf(progress * _pieces.size() - i, 0.0, 1.0)


func built_count() -> int:
	var n := 0
	for i in _pieces.size():
		if piece_fraction(i) > 0.0:
			n += 1
	return n


func is_complete() -> bool:
	return progress >= 1.0


func set_progress(p: float) -> void:
	progress = clampf(p, 0.0, 1.0)
	for i in _pieces.size():
		var f := piece_fraction(i)
		_pieces[i].visible = f > 0.0
		_mats[i].set_shader_parameter("build", f)


## Ponto onde o laser bate agora: varre o topo da peca em construcao.
func laser_point() -> Vector3:
	if _pieces.is_empty():
		return global_position
	var i := current_index()
	var mi := _pieces[i]
	var box := mi.mesh.get_aabb()
	var h := lerpf(box.position.y, box.end.y, piece_fraction(i))
	var local := Vector3(sin(_t * 2.3) * box.size.x * 0.45, h, cos(_t * 1.7) * box.size.z * 0.45)
	return mi.global_transform * local


func shake(secs: float) -> void:
	var tw := create_tween()
	var steps := int(secs / 0.06)
	var base := position
	for i in steps:
		var k := 1.0 - float(i) / steps
		tw.tween_property(self, "position", base + Vector3(randf_range(-1, 1), 0, randf_range(-1, 1)) * 0.07 * k, 0.06)
	tw.tween_property(self, "position", base, 0.06)
	await tw.finished


## A peca em construcao racha e volta ao comeco (precisa ser refeita).
func crack_current() -> void:
	if _pieces.is_empty() or is_complete():
		return
	_crack_index = current_index()
	_crack = 1.0
	var n := float(_pieces.size())
	var start := _crack_index / n
	var tw := create_tween()
	tw.tween_interval(0.8)
	tw.tween_method(set_progress, progress, start, 0.6)
	await tw.finished


func celebrate() -> void:
	_flash = 1.2


func dissolve(secs: float = 1.0) -> void:
	var tw := create_tween()
	tw.tween_method(_fade_mats.bind(_mats.duplicate()), 1.0, 0.0, secs)
	tw.parallel().tween_property(self, "position:y", 0.6, secs)
	await tw.finished
	clear()


## Derruba tudo: cada peca vira corpo fisico, racha e some no chao.
func knock_down(from: Vector3) -> void:
	var world := get_parent()
	var bodies: Array[RigidBody3D] = []
	for i in _pieces.size():
		if piece_fraction(i) <= 0.0:
			continue
		var mi := _pieces[i]
		var mat := _mats[i]
		mat.set_shader_parameter("build", 1.0)
		mat.set_shader_parameter("crack", 1.0)
		var rb := RigidBody3D.new()
		rb.mass = 2.0
		world.add_child(rb)
		rb.global_transform = mi.global_transform
		mi.reparent(rb)
		var cs := CollisionShape3D.new()
		var shape := BoxShape3D.new()
		var box := mi.mesh.get_aabb()
		shape.size = box.size.max(Vector3.ONE * 0.05)
		cs.shape = shape
		cs.position = box.get_center()
		rb.add_child(cs)
		var away := rb.global_position - from
		away.y = 0.0
		away = away.normalized() if away.length() > 0.01 else Vector3(randf_range(-1, 1), 0, 1).normalized()
		rb.apply_central_impulse((away * randf_range(3.0, 6.0) + Vector3.UP * randf_range(2.0, 5.0)) * rb.mass)
		rb.apply_torque_impulse(Vector3(randf_range(-1, 1), randf_range(-1, 1), randf_range(-1, 1)) * 2.0)
		bodies.append(rb)
	_pieces.clear()
	var mats := _mats.duplicate()
	_mats.clear()
	await get_tree().create_timer(3.2).timeout
	var tw := create_tween()
	tw.tween_method(_fade_mats.bind(mats), 1.0, 0.0, 1.2)
	await tw.finished
	for rb in bodies:
		if is_instance_valid(rb):
			rb.queue_free()


func _fade_mats(v: float, mats: Array) -> void:
	for m in mats:
		(m as ShaderMaterial).set_shader_parameter("fade", v)


func _process(delta: float) -> void:
	_t += delta
	if _crack > 0.0:
		_crack = maxf(_crack - delta * 0.6, 0.0)
		if _crack_index >= 0 and _crack_index < _mats.size():
			_mats[_crack_index].set_shader_parameter("crack", _crack)
	if _flash > 0.0:
		_flash = maxf(_flash - delta * 0.8, 0.0)
		var f := _flash * (0.5 + 0.5 * sin(_t * 18.0))
		for m in _mats:
			m.set_shader_parameter("flash", f)
