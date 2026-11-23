class_name Zodia
extends Node3D
## ZodIA: o robo assistente. Flutua ao lado da plataforma, projeta as pecas com
## lasers roxos e mostra a expressao na tela do rosto.
## Modelo provisorio em formas simples; se existir assets/models/zodia.glb
## (Hyper3D), ele entra no lugar e a tela-rosto fica por cima da cabeca.

const WHITE := Color(0.95, 0.94, 1.0)
const CYAN := Color(0.35, 0.85, 1.0)
const PURPLE := Color(0.62, 0.32, 1.0)
const LASER := Color(0.85, 0.35, 1.0)

var goal := Vector3.ZERO
var glide_speed := 1.6

var _hover: Node3D
var _pose: Node3D
var _placeholder: Node3D
var _arm_l: Node3D
var _arm_r: Node3D
var _hand: Node3D
var _ring: MeshInstance3D
var _face: ZodiaFace
var _beams: Array[MeshInstance3D] = []
var _anim: AnimationPlayer
var _anim_map: Dictionary = {}
var _anim_mode := ""
var _skel: Skeleton3D
## Bracos do modelo do Hyper3D: [{idx, pivot, tip, side, q}]
var _arms: Array = []

var _spark: MeshInstance3D

var _base_expr: ZodiaFace.Expr = ZodiaFace.Expr.NORMAL
var _temp_expr: ZodiaFace.Expr = ZodiaFace.Expr.NORMAL
var _temp_left := 0.0
var _laser_target: Variant = null
var _yaw_goal := 0.0
var _t := 0.0
var _hover_h := 0.55
var _fallen := false
var _slumped := false
var _tremble := 0.0
var _spinning := false
var arm_mode := "idle"   # idle | build | wave | cheer | droop


func _ready() -> void:
	_hover_h = float(GameConfig.sub("zodia", "hover_height", 0.55))
	goal = position
	Mat.add(self, Mat.cyl(0.55, 0.55, 0.01, 20), Mat.blob(), Vector3(0, 0.03, 0))

	_hover = Node3D.new()
	add_child(_hover)
	_ring = Mat.add(_hover, Mat.torus(0.34, 0.42), Mat.glow(CYAN, 3.0), Vector3(0, -0.06, 0))
	Mat.add(_hover, Mat.torus(0.52, 0.56), Mat.glow(PURPLE, 2.0), Vector3(0, -0.12, 0))

	_pose = Node3D.new()
	_hover.add_child(_pose)

	var models: Dictionary = GameConfig.value("models", {})
	var glb := ModelSlot.try_load(String(models.get("zodia", "")), float(models.get("zodia_height", 1.9)))
	var rigged := false
	if glb:
		_pose.add_child(glb)
		rigged = _attach_to_rig(glb, models.get("zodia_rig", {}))
	else:
		_build_placeholder()
	if not rigged:
		var cfg: Dictionary = models.get("zodia_face", {})
		var off: Array = cfg.get("offset", [0, 1.52, 0.51])
		var sz: Array = cfg.get("size", [0.78, 0.48])
		_build_face(_pose, _v3(off), Vector2(float(sz[0]), float(sz[1])), Vector3.BACK)
	if _hand == null:
		_hand = Node3D.new()
		_hand.position = Vector3(0.7, 0.75, 0.2)
		_pose.add_child(_hand)

	# 2 feixes principais (um por braco) e 2 finos tremulando
	for i in 4:
		var b := Mat.add(self, Mat.cyl(0.016 if i < 2 else 0.007, 0.016 if i < 2 else 0.007, 1.0, 6), Mat.glow(LASER, 4.0 if i < 2 else 2.5))
		b.top_level = true
		b.visible = false
		_beams.append(b)
	_spark = Mat.add(self, Mat.sphere(0.07, -1, 8), Mat.glow(Color(0.8, 0.95, 1.0), 5.0))
	_spark.top_level = true
	_spark.visible = false


func _build_placeholder() -> void:
	_placeholder = Node3D.new()
	_pose.add_child(_placeholder)
	var white := Mat.solid(WHITE, 0.35)
	Mat.add(_placeholder, Mat.sphere(0.45, 0.95, 20), white, Vector3(0, 0.55, 0), Vector3.ZERO, Vector3(1.0, 1.0, 0.92))
	for s in [-1.0, 1.0]:
		Mat.add(_placeholder, Mat.sphere(0.16, 0.5, 12), Mat.glow(PURPLE, 1.4), Vector3(0.39 * s, 0.58, 0.02), Vector3.ZERO, Vector3(0.35, 1.0, 0.9))
	var logo := Label3D.new()
	logo.text = "IA"
	logo.font_size = 72
	logo.outline_size = 0
	logo.pixel_size = 0.004
	logo.modulate = Color(0.12, 0.07, 0.25)
	logo.position = Vector3(0, 0.62, 0.43)
	_placeholder.add_child(logo)
	# cabeca solta acima do corpo, como no esboco
	Mat.add(_placeholder, Mat.sphere(0.5, 1.0, 22), white, Vector3(0, 1.5, 0), Vector3.ZERO, Vector3(1.3, 0.85, 1.0))
	Mat.add(_placeholder, Mat.cyl(0.12, 0.16, 0.12, 10), Mat.solid(Color(0.75, 0.74, 0.85), 0.4), Vector3(0, 1.1, 0))
	for s in [-1.0, 1.0]:
		Mat.add(_placeholder, Mat.sphere(0.09, -1, 10), Mat.glow(CYAN, 2.5), Vector3(0.64 * s, 1.5, 0), Vector3.ZERO, Vector3(0.5, 1.0, 1.0))
	_arm_l = _arm(-1.0, white)
	_arm_r = _arm(1.0, white)
	_hand = Node3D.new()
	_hand.position = Vector3(0, -0.45, 0.05)
	_arm_r.add_child(_hand)


func _arm(side: float, mat: Material) -> Node3D:
	var pivot := Node3D.new()
	pivot.position = Vector3(0.68 * side, 0.86, 0)
	_placeholder.add_child(pivot)
	Mat.add(pivot, Mat.sphere(0.2, 0.5, 12), mat, Vector3(0, -0.25, 0), Vector3.ZERO, Vector3(0.55, 1.0, 0.8))
	return pivot


## Modelo do Hyper3D com esqueleto: a tela-rosto e a mao seguem os ossos,
## e as animacoes do arquivo (comemorar, apontar...) entram no lugar dos bracos.
func _attach_to_rig(glb: Node, cfg: Dictionary) -> bool:
	var skels := glb.find_children("*", "Skeleton3D", true, false)
	if skels.is_empty() or cfg.is_empty():
		return false
	var skel := skels[0] as Skeleton3D
	_skel = skel
	for side_name in ["left", "right"]:
		var ac: Dictionary = cfg.get("arms", {}).get(side_name, {})
		var idx := skel.find_bone(String(ac.get("bone", side_name)))
		if idx >= 0 and ac.has("pivot") and ac.has("tip"):
			_arms.append({"idx": idx, "pivot": _v3(ac["pivot"]), "tip": _v3(ac["tip"]), "q": Quaternion.IDENTITY})
	if _arms.size() == 2:
		var cx := ((_arms[0]["pivot"] as Vector3).x + (_arms[1]["pivot"] as Vector3).x) / 2.0
		for arm in _arms:
			arm["side"] = signf((arm["pivot"] as Vector3).x - cx)
	# a tela-rosto vira o material do proprio visor (UV plana feita no Blender),
	# entao acompanha a curva e os movimentos da cabeca sem descolar
	var screen := _find_surface(glb, String(cfg.get("screen_material", "zodia_tela")))
	if screen.is_empty():
		return false
	_face_viewport()
	var sm := StandardMaterial3D.new()
	sm.albedo_color = Color(0.01, 0.01, 0.03)
	sm.roughness = 0.15
	sm.metallic_specular = 0.8
	sm.emission_enabled = true
	sm.emission_texture = _face_vp.get_texture()
	sm.emission_energy_multiplier = 1.4
	(screen[0] as MeshInstance3D).set_surface_override_material(int(screen[1]), sm)
	var hand := _bone_space(skel, String(cfg.get("hand_bone", "right")))
	_hand = Node3D.new()
	_hand.position = _v3(cfg.get("hand_offset", [0, 0, 0]))
	hand.add_child(_hand)
	var players := glb.find_children("*", "AnimationPlayer", true, false)
	if not players.is_empty():
		_anim = players[0] as AnimationPlayer
		_anim_map = cfg.get("anims", {})
	return true


## [MeshInstance3D, indice] da superficie com esse material, ou [].
func _find_surface(root: Node, mat_name: String) -> Array:
	for mi in root.find_children("*", "MeshInstance3D", true, false):
		var m := mi as MeshInstance3D
		for i in m.mesh.get_surface_count():
			var mat := m.mesh.surface_get_material(i)
			if mat and mat.resource_name == mat_name:
				return [m, i]
	return []


var _face_vp: SubViewport


func _face_viewport() -> void:
	if _face_vp:
		return
	_face_vp = SubViewport.new()
	_face_vp.size = Vector2i(int(ZodiaFace.W), int(ZodiaFace.H))
	_face_vp.transparent_bg = true
	_face_vp.disable_3d = true
	_face_vp.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	add_child(_face_vp)
	_face = ZodiaFace.new()
	_face_vp.add_child(_face)


## No que segue o osso, mas usa as coordenadas do modelo (as medidas do
## config sao tiradas do modelo parado, nao do espaco do osso).
func _bone_space(skel: Skeleton3D, bone: String) -> Node3D:
	var att := BoneAttachment3D.new()
	att.bone_name = bone
	skel.add_child(att)
	var space := Node3D.new()
	var idx := skel.find_bone(bone)
	if idx >= 0:
		space.transform = skel.get_bone_global_rest(idx).affine_inverse()
	else:
		push_warning("Osso %s nao existe no modelo do ZodIA" % bone)
	att.add_child(space)
	return space


static func _v3(a: Variant) -> Vector3:
	var arr: Array = a
	return Vector3(float(arr[0]), float(arr[1]), float(arr[2]))


func _play_mode_anim() -> void:
	if _anim == null or _anim_mode == arm_mode:
		return
	_anim_mode = arm_mode
	var name := String(_anim_map.get(arm_mode, ""))
	if name == "" or not _anim.has_animation(name):
		# sem animacao do arquivo: bracos controlados pelo codigo
		if _anim.active:
			_anim.active = false
			if _skel:
				_skel.reset_bone_poses()
			for arm in _arms:
				arm["q"] = Quaternion.IDENTITY
		return
	_anim.active = true
	_anim.get_animation(name).loop_mode = Animation.LOOP_LINEAR
	_anim.play(name, 0.3)


func _anim_playing() -> bool:
	return _anim != null and _anim.active and _anim.is_playing()


## Bracos (paletas) giram em volta do ombro: para frente ao construir,
## para baixo parado ou sem bateria.
func _animate_rig_arms(delta: float) -> void:
	if _arms.is_empty() or _anim_playing():
		return
	for arm in _arms:
		var side: float = arm["side"]
		var target := Vector3(side * 0.12, 0.05, 1.0)
		match arm_mode:
			"build":
				target = Vector3(side * 0.12, 0.05, 1.0)
			"droop":
				target = Vector3(side * 0.2, -1.0, -0.1)
			_:
				target = Vector3(side * 0.45, -1.0, 0.2)
		var p: Vector3 = arm["pivot"]
		var rest_dir := ((arm["tip"] as Vector3) - p).normalized()
		var goal_q := Quaternion(rest_dir, target.normalized())
		var q: Quaternion = (arm["q"] as Quaternion).slerp(goal_q, minf(delta * 6.0, 1.0))
		arm["q"] = q
		var b := Basis(q)
		var idx: int = arm["idx"]
		_skel.set_bone_global_pose(idx, Transform3D(b, p - b * p) * _skel.get_bone_global_rest(idx))


## Pontas dos dois bracos no mundo (de onde saem os lasers).
func _arm_tips() -> Array[Vector3]:
	var out: Array[Vector3] = []
	if _arms.size() == 2 and not _anim_playing():
		for arm in _arms:
			var p: Vector3 = arm["pivot"]
			var tip: Vector3 = p + (arm["q"] as Quaternion) * ((arm["tip"] as Vector3) - p) * 1.15
			out.append(_skel.global_transform * tip)
	else:
		out.append(_hand.global_position)
		out.append(_hand.global_position)
	return out


func _build_face(parent: Node3D, offset: Vector3, quad_size: Vector2, normal: Vector3) -> void:
	_face_viewport()
	var vp := _face_vp
	var q := QuadMesh.new()
	q.size = quad_size
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.albedo_texture = vp.get_texture()
	m.emission_enabled = true
	m.emission_texture = vp.get_texture()
	m.emission_energy_multiplier = 1.6
	var quad := Mat.add(parent, q, m, offset + normal.normalized() * 0.004)
	quad.basis = Basis.looking_at(-normal.normalized(), Vector3.UP)


# ---------- expressoes ----------

func express(e: ZodiaFace.Expr, secs: float) -> void:
	_temp_expr = e
	_temp_left = secs
	_face.set_expr(e)


func set_base(e: ZodiaFace.Expr) -> void:
	_base_expr = e


func expr() -> ZodiaFace.Expr:
	return _temp_expr if _temp_left > 0.0 else _base_expr


func has_temp_expr() -> bool:
	return _temp_left > 0.0


# ---------- laser ----------

func set_laser(target: Variant) -> void:
	_laser_target = target


func _update_laser() -> void:
	var on := _laser_target != null and not _fallen and not _slumped
	for i in _beams.size():
		_beams[i].visible = on and (i < 2 or fmod(_t * 7.0 + i * 1.3, 1.0) < 0.7)
	_spark.visible = on
	if not on:
		return
	var tips := _arm_tips()
	var target: Vector3 = _laser_target
	var side := global_transform.basis.x.normalized() * 0.08
	for i in _beams.size():
		var a: Vector3 = tips[i % 2]
		var off := side * (-1.0 if i % 2 == 0 else 1.0)
		if i >= 2:
			off += Vector3(sin(_t * 9.0 + i * 2.0), 0.0, cos(_t * 7.0 + i * 3.0)) * 0.3
		_place_beam(_beams[i], a, target + off)
	_spark.global_position = target
	_spark.scale = Vector3.ONE * (0.8 + 0.4 * sin(_t * 30.0))


func _place_beam(b: MeshInstance3D, a: Vector3, c: Vector3) -> void:
	var d := c - a
	var length := d.length()
	if length < 0.01:
		b.visible = false
		return
	var bs := Basis(Quaternion(Vector3.UP, d / length))
	b.global_transform = Transform3D(Basis(bs.x, bs.y * length, bs.z), (a + c) * 0.5)


# ---------- movimento ----------

func face_point(p: Vector3) -> void:
	var d := p - global_position
	if Vector2(d.x, d.z).length() > 0.05:
		_yaw_goal = atan2(d.x, d.z)


func is_fallen() -> bool:
	return _fallen


func spin(turns: float, secs: float) -> void:
	_spinning = true
	var tw := create_tween()
	tw.tween_property(_pose, "rotation:y", _pose.rotation.y + TAU * turns, secs).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	await tw.finished
	_pose.rotation.y = 0.0
	_spinning = false


func tremble(secs: float) -> void:
	_tremble = maxf(_tremble, secs)


func fall() -> void:
	_fallen = true
	var tw := create_tween().set_parallel(true)
	tw.tween_property(_pose, "rotation:x", deg_to_rad(-88.0), 0.45).set_trans(Tween.TRANS_BOUNCE).set_ease(Tween.EASE_OUT)
	tw.tween_property(_pose, "position:y", -_hover_h + 0.42, 0.45)
	tw.tween_property(_pose, "position:z", -0.2, 0.45)
	await tw.finished


func get_up() -> void:
	var tw := create_tween().set_parallel(true)
	tw.tween_property(_pose, "rotation:x", 0.0, 0.6).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	tw.tween_property(_pose, "position:y", 0.0, 0.6)
	tw.tween_property(_pose, "position:z", 0.0, 0.6)
	await tw.finished
	_fallen = false


func slump(on: bool) -> void:
	if on == _slumped:
		return
	_slumped = on
	var tw := create_tween().set_parallel(true)
	tw.tween_property(_pose, "rotation:x", deg_to_rad(18.0) if on else 0.0, 0.8)
	tw.tween_property(_pose, "position:y", (-_hover_h + 0.05) if on else 0.0, 0.8)


func _process(delta: float) -> void:
	_t += delta
	if _temp_left > 0.0:
		_temp_left -= delta
		if _temp_left <= 0.0:
			_face.set_expr(_base_expr)
	elif _face.expr != _base_expr:
		_face.set_expr(_base_expr)
	_tremble = maxf(_tremble - delta, 0.0)

	# o ZodIA so sai do campo se cair perto da borda (a queda nao e limitada)
	goal = Island.clamp_inside(goal, 1.0)
	if not _fallen:
		var to := goal - position
		to.y = 0.0
		var step := glide_speed * delta * (0.3 if _slumped else 1.0)
		if to.length() > step:
			position += to.normalized() * step
		else:
			position = Vector3(goal.x, position.y, goal.z)
	rotation.y = lerp_angle(rotation.y, _yaw_goal, minf(delta * 4.0, 1.0))

	var bob := 0.0 if (_fallen or _slumped) else sin(_t * 2.2) * 0.07
	_hover.position.y = _hover_h + bob
	_hover.position.x = sin(_t * 70.0) * 0.025 * signf(_tremble)
	_ring.visible = not _slumped
	_ring.rotation.y += delta * 2.0
	_animate_arms(delta)
	_update_laser()


func _animate_arms(delta: float) -> void:
	_play_mode_anim()
	_animate_rig_arms(delta)
	if _arm_l == null:
		return
	var l := 0.0
	var r := 0.0
	match arm_mode:
		"build":
			r = deg_to_rad(-70.0 + sin(_t * 3.0) * 12.0)
			l = deg_to_rad(sin(_t * 2.0) * 8.0)
		"wave":
			l = deg_to_rad(-120.0 + sin(_t * 18.0) * 45.0)
			r = deg_to_rad(-120.0 + sin(_t * 18.0 + 1.5) * 45.0)
		"cheer":
			l = deg_to_rad(-150.0 + sin(_t * 10.0) * 15.0)
			r = deg_to_rad(-150.0 + sin(_t * 10.0 + PI) * 15.0)
		"droop":
			l = deg_to_rad(12.0)
			r = deg_to_rad(12.0)
		_:
			l = deg_to_rad(sin(_t * 2.0) * 6.0)
			r = deg_to_rad(sin(_t * 2.0 + 1.0) * 6.0)
	# bracos giram para a frente (eixo x local)
	_arm_l.rotation.x = lerp_angle(_arm_l.rotation.x, l, minf(delta * 8.0, 1.0))
	_arm_r.rotation.x = lerp_angle(_arm_r.rotation.x, r, minf(delta * 8.0, 1.0))
	_arm_l.rotation.z = -0.15 if arm_mode == "wave" or arm_mode == "cheer" else 0.0
	_arm_r.rotation.z = 0.15 if arm_mode == "wave" or arm_mode == "cheer" else 0.0
