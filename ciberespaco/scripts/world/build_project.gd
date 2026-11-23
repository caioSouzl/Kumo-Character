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
## true enquanto uma peca racha e se despedaca (o ZodIA espera).
var _breaking := false


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
	position = Vector3(position.x, Island.TOP, position.z)


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


func is_breaking() -> bool:
	return _breaking


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


## Pontos que os lasers varrem: correm em volta da borda da peca em
## construcao, na altura que esta sendo desenhada.
func laser_points(n: int = 4) -> Array:
	var out: Array = []
	if _pieces.is_empty():
		return [global_position]
	var i := current_index()
	var mi := _pieces[i]
	var box := mi.mesh.get_aabb()
	var h := lerpf(box.position.y, box.end.y, piece_fraction(i))
	var c := box.get_center()
	for k in n:
		var a := _t * (1.6 + 0.3 * k) + TAU * k / n
		var rx := maxf(box.size.x * 0.55, 0.45)
		var rz := maxf(box.size.z * 0.55, 0.45)
		var local := Vector3(c.x + cos(a) * rx, h + sin(a * 2.0) * 0.08, c.z + sin(a) * rz)
		out.append(mi.global_transform * local)
	return out


func shake(secs: float) -> void:
	var tw := create_tween()
	var steps := int(secs / 0.06)
	var base := position
	for i in steps:
		var k := 1.0 - float(i) / steps
		tw.tween_property(self, "position", base + Vector3(randf_range(-1, 1), 0, randf_range(-1, 1)) * 0.07 * k, 0.06)
	tw.tween_property(self, "position", base, 0.06)
	await tw.finished


## A peca em construcao racha, se despedaca e volta ao comeco (refazer).
func crack_current() -> void:
	if _pieces.is_empty() or is_complete():
		return
	# quebra a peca em construcao e a ultima peca pronta antes dela, para o
	# estrago ser visivel mesmo logo depois de outro tombo
	var i := current_index()
	var idx: Array = []
	if piece_fraction(i) > 0.05:
		idx.append(i)
	if i > 0:
		idx.append(i - 1)
	if idx.is_empty():
		return
	var lowest: int = idx.min()
	_breaking = true
	await _break_pieces(idx, _pieces[i].global_position + Vector3(0, 0, 1), 0.6)
	set_progress(float(lowest) / _pieces.size())
	_breaking = false


func celebrate() -> void:
	_flash = 1.2


func dissolve(secs: float = 1.0) -> void:
	var tw := create_tween()
	tw.tween_method(_fade_mats.bind(_mats.duplicate()), 1.0, 0.0, secs)
	tw.parallel().tween_property(self, "position:y", 0.6, secs)
	await tw.finished
	clear()


## Derruba tudo: as pecas rachadas se despedacam em estilhacos, caem e somem.
func knock_down(from: Vector3) -> void:
	var idx: Array = []
	for i in _pieces.size():
		if piece_fraction(i) > 0.0:
			idx.append(i)
	await _break_pieces(idx, from, 1.0)
	clear()


## Efeito de quebra em 3 tempos:
## 1. racha (linhas de falha piscando, a peca treme);
## 2. se despedaca em estilhacos (pedacos do proprio objeto);
## 3. os estilhacos caem no chao e somem.
func _break_pieces(idx: Array, from: Vector3, force: float) -> void:
	var world := get_parent()
	# 1. rachar
	var tw := create_tween().set_parallel(true)
	for i in idx:
		tw.tween_method(_set_crack.bind(_mats[i]), 0.0, 1.0, 0.9)
	var base := {}
	for i in idx:
		base[i] = _pieces[i].position
	var t := 0.0
	while t < 0.9:
		await get_tree().process_frame
		t += get_process_delta_time()
		for i in idx:
			_pieces[i].position = (base[i] as Vector3) + Vector3(randf_range(-1, 1), 0, randf_range(-1, 1)) * 0.03 * t
	# 2. estilhacos
	var shards: Array[RigidBody3D] = []
	var shard_mats: Array = []
	for i in idx:
		var mi := _pieces[i]
		mi.position = base[i]
		var box := mi.mesh.get_aabb()
		var mat := Mat.holo()
		mat.set_shader_parameter("y_min", -1.0)
		mat.set_shader_parameter("y_max", 1.0)
		mat.set_shader_parameter("build", 1.0)
		mat.set_shader_parameter("crack", 1.0)
		shard_mats.append(mat)
		var cnt := Vector3i(clampi(roundi(box.size.x / 0.35), 1, 3), clampi(roundi(box.size.y / 0.35), 1, 3), clampi(roundi(box.size.z / 0.35), 1, 3))
		var cell := box.size / Vector3(cnt)
		var center := mi.global_transform * box.get_center()
		for x in cnt.x:
			for y in cnt.y:
				for z in cnt.z:
					var local := box.position + cell * Vector3(x + 0.5, y + 0.5, z + 0.5)
					var sz := (cell * randf_range(0.7, 0.95)).max(Vector3.ONE * 0.05)
					var rb := RigidBody3D.new()
					rb.mass = 0.3
					world.add_child(rb)
					rb.global_transform = Transform3D(mi.global_transform.basis.orthonormalized() * Basis.from_euler(Vector3(randf(), randf(), randf()) * 0.4), mi.global_transform * local)
					var m := MeshInstance3D.new()
					m.mesh = Mat.box(sz)
					m.material_override = mat
					m.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
					rb.add_child(m)
					var cs := CollisionShape3D.new()
					var shape := BoxShape3D.new()
					shape.size = sz
					cs.shape = shape
					rb.add_child(cs)
					var out := rb.global_position - center
					var away := rb.global_position - from
					away.y = 0.0
					var dir := (out.normalized() * 0.6 + away.normalized() * 0.4)
					rb.apply_central_impulse((dir * randf_range(0.8, 1.8) * force + Vector3.UP * randf_range(0.5, 1.5)) * rb.mass)
					rb.apply_torque_impulse(Vector3(randf_range(-1, 1), randf_range(-1, 1), randf_range(-1, 1)) * 0.08)
					shards.append(rb)
		mi.visible = false
	# 3. caem e somem
	await get_tree().create_timer(1.8).timeout
	var fade := create_tween().set_parallel(true)
	fade.tween_method(_fade_mats.bind(shard_mats), 1.0, 0.0, 0.9)
	for rb in shards:
		fade.tween_property(rb.get_child(0), "scale", Vector3.ONE * 0.2, 0.9)
	await fade.finished
	for rb in shards:
		if is_instance_valid(rb):
			rb.queue_free()
	for i in idx:
		if i < _mats.size():
			_set_crack(0.0, _mats[i])
			_pieces[i].visible = piece_fraction(i) > 0.0


func _set_crack(v: float, mat: ShaderMaterial) -> void:
	mat.set_shader_parameter("crack", v)


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
