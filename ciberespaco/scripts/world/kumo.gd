class_name Kumo
extends Node3D
## O Kumo, o lagartinho curioso. Dorme no terrario da arvore, acorda, desce,
## brinca com os brinquedos e so atrapalha o ZodIA quando chega o presente certo.
## Modelo provisorio (lagartinho em esferas, paleta oficial); se existir assets/models/kumo.glb, ele entra no lugar.

enum Face { OPEN, SLEEP, HAPPY, MISCHIEF }

## Paleta oficial do Kumo
const GREEN_DARK := Color("#708C32")
const GREEN := Color("#90A235")
const GREEN_LIGHT := Color("#DCDC83")
const BEIGE := Color("#D1B681")
const BELLY := Color("#DCDC83")
const INK := Color("#2a2418")
const CHEEK := Color(1.0, 0.6, 0.6)

var asleep := true
## true enquanto um presente controla o Kumo (a rotina livre espera).
var acting := false

var _body: Node3D
var _visual: Node3D
var _eyes_open: Array[Node3D] = []
var _eyes_closed: Array[Node3D] = []
var _eyes_happy: Array[Node3D] = []
var _zzz: Label3D
var _shadow: MeshInstance3D
var _t := 0.0
var _moving := false
var _token := 0
var _squash := 0.0

# modelo oficial (kumo-3d-rodin) com esqueleto: animacao feita no codigo
var _skel: Skeleton3D
var _base_rot: Dictionary = {}
var _bone: Dictionary = {}
var _tail: Array[int] = []
var _lids: Array = []
var _face_state := Face.SLEEP
var _blink_left := 0.0
var _next_blink := 3.0
var _walk_amp := 0.0
var _quad := 0.0
var _cur_speed := 0.0
## Quanto o corpo deita para frente nas quatro patas (rad) e quanto desce.
const QUAD_PITCH := 1.15
const QUAD_DROP := 0.32


func _ready() -> void:
	_shadow = Mat.add(self, Mat.cyl(0.42, 0.42, 0.01, 18), Mat.blob(), Vector3(0, 0.02, 0))
	_body = Node3D.new()
	add_child(_body)
	_visual = Node3D.new()
	_body.add_child(_visual)
	var models: Dictionary = GameConfig.value("models", {})
	var glb := ModelSlot.try_load(String(models.get("kumo", "")), float(models.get("kumo_height", 1.0)))
	if glb:
		_visual.add_child(glb)
		_setup_rig(glb, models.get("kumo_rig", {}))
	else:
		_build_placeholder()
	_zzz = Label3D.new()
	_zzz.text = "z Z"
	_zzz.font_size = 96
	_zzz.pixel_size = 0.004
	_zzz.modulate = Color(0.8, 0.9, 1.0)
	_zzz.outline_size = 18
	_zzz.outline_modulate = Color(0.2, 0.1, 0.4)
	_zzz.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	_zzz.position = Vector3(0.45, 1.35, 0)
	add_child(_zzz)
	set_face(Face.SLEEP)


func _build_placeholder() -> void:
	# lagartinho fofo nas cores oficiais do Kumo (provisorio ate o modelo 3D)
	var green := Mat.solid(GREEN, 0.8)
	var green_dark := Mat.solid(GREEN_DARK, 0.85)
	var belly := Mat.solid(BELLY, 0.9)
	Mat.add(_visual, Mat.sphere(0.3, -1, 14), green, Vector3(0, 0.32, -0.05), Vector3.ZERO, Vector3(1.0, 0.85, 1.15))
	Mat.add(_visual, Mat.sphere(0.24, -1, 12), belly, Vector3(0, 0.28, 0.1), Vector3.ZERO, Vector3(0.9, 0.85, 0.7))
	Mat.add(_visual, Mat.sphere(0.3, -1, 16), green, Vector3(0, 0.68, 0.12), Vector3.ZERO, Vector3(1.1, 0.95, 1.0))
	Mat.add(_visual, Mat.sphere(0.16, -1, 12), Mat.solid(GREEN_LIGHT, 0.8), Vector3(0, 0.6, 0.34), Vector3.ZERO, Vector3(1.3, 0.7, 0.8))
	# cauda enrolando para tras
	for i in 5:
		var k := i / 4.0
		Mat.add(_visual, Mat.sphere(lerpf(0.13, 0.04, k), -1, 8), green if i % 2 == 0 else green_dark, Vector3(sin(k * 2.2) * 0.25, 0.14 + k * 0.12, -0.35 - k * 0.32))
	# pintinhas nas costas
	for i in 3:
		Mat.add(_visual, Mat.sphere(0.05, 0.03, 8), Mat.solid(BEIGE, 0.9), Vector3((i - 1) * 0.1, 0.55 - i * 0.05, -0.2 - i * 0.08), Vector3(-40, 0, 0))
	for x in [-0.17, 0.17]:
		for z in [-0.18, 0.12]:
			Mat.add(_visual, Mat.sphere(0.075, 0.12, 8), green_dark, Vector3(x, 0.06, z))
	var ink := Mat.solid(INK, 0.3)
	for s in [-1.0, 1.0]:
		var e := Node3D.new()
		e.position = Vector3(0.14 * s, 0.76, 0.33)
		_visual.add_child(e)
		Mat.add(e, Mat.sphere(0.075, 0.1, 10), ink)
		Mat.add(e, Mat.sphere(0.022, -1, 6), Mat.solid(Color.WHITE, 0.3), Vector3(0.02, 0.025, 0.06))
		_eyes_open.append(e)
		var c := Mat.add(_visual, Mat.box(Vector3(0.12, 0.022, 0.02)), ink, Vector3(0.14 * s, 0.74, 0.37))
		_eyes_closed.append(c)
		var h := Node3D.new()
		h.position = Vector3(0.14 * s, 0.76, 0.37)
		_visual.add_child(h)
		Mat.add(h, Mat.box(Vector3(0.08, 0.022, 0.02)), ink, Vector3(-0.03, -0.015, 0), Vector3(0, 0, 35))
		Mat.add(h, Mat.box(Vector3(0.08, 0.022, 0.02)), ink, Vector3(0.03, -0.015, 0), Vector3(0, 0, -35))
		_eyes_happy.append(h)
		Mat.add(_visual, Mat.sphere(0.05, 0.04, 8), Mat.solid(CHEEK, 0.9), Vector3(0.24 * s, 0.62, 0.3), Vector3.ZERO, Vector3(1.2, 0.6, 0.5))


func _setup_rig(glb: Node, cfg: Dictionary) -> void:
	var skels := glb.find_children("*", "Skeleton3D", true, false)
	if skels.is_empty():
		return
	_skel = skels[0] as Skeleton3D
	# pose de apresentacao (bracos baixos) como base, se existir
	var players := glb.find_children("*", "AnimationPlayer", true, false)
	if not players.is_empty():
		var ap := players[0] as AnimationPlayer
		var pose := String(cfg.get("base_pose", ""))
		if pose != "" and ap.has_animation(pose):
			ap.play(pose)
			ap.seek(0.0, true)
		ap.active = false
	for i in _skel.get_bone_count():
		_base_rot[i] = _skel.get_bone_pose_rotation(i)
	var wb: Dictionary = cfg.get("walk_bones", {})
	for key in wb:
		_bone[key] = _skel.find_bone(String(wb[key]))
	var prefix := String(cfg.get("tail_prefix", "tail_"))
	for i in _skel.get_bone_count():
		if _skel.get_bone_name(i).begins_with(prefix):
			_tail.append(i)
	for mi in glb.find_children("*", "MeshInstance3D", true, false):
		for shape in cfg.get("blink_shapes", []):
			var idx := (mi as MeshInstance3D).find_blend_shape_by_name(StringName(shape))
			if idx >= 0:
				_lids.append([mi, idx])


## Gira o osso em volta de um eixo do modelo (x = lado, y = cima, z = frente),
## somando a pose base. Assim o eixo nao depende de como o osso foi criado.
func _rotm(key: String, axis_model: Vector3, angle: float) -> void:
	var i: int = _bone.get(key, -1)
	if i < 0:
		return
	var rb := _skel.get_bone_global_rest(i).basis.orthonormalized()
	var ax := (rb.inverse() * axis_model).normalized()
	_skel.set_bone_pose_rotation(i, (_base_rot[i] as Quaternion) * Quaternion(ax, angle))


func _rotm2(key: String, ax1: Vector3, a1: float, ax2: Vector3, a2: float) -> void:
	var i: int = _bone.get(key, -1)
	if i < 0:
		return
	var rb := _skel.get_bone_global_rest(i).basis.orthonormalized().inverse()
	var q := Quaternion((rb * ax1).normalized(), a1) * Quaternion((rb * ax2).normalized(), a2)
	_skel.set_bone_pose_rotation(i, (_base_rot[i] as Quaternion) * q)


## Anda em pe devagar e de quatro patas quando corre.
func _animate_rig(delta: float) -> void:
	_walk_amp = move_toward(_walk_amp, 1.0 if _moving else 0.0, delta * 5.0)
	var want_quad := _moving and _cur_speed >= float(GameConfig.sub("kumo", "quad_above_speed", 3.0))
	_quad = move_toward(_quad, 1.0 if want_quad else 0.0, delta * 3.0)
	var q := _quad
	var w := _t * (13.0 if q > 0.5 else 10.0)
	var a := _walk_amp
	var X := Vector3.RIGHT
	var Z := Vector3.BACK
	# tronco inclina para frente nas quatro patas
	_rotm("hips", X, q * QUAD_PITCH + sin(w * 2.0) * 0.03 * a)
	_rotm("spine", X, q * 0.15)
	_rotm("chest", X, q * 0.1 + sin(_t * (1.6 if asleep else 2.4)) * 0.03)
	_rotm("neck", X, -q * 0.7)
	var nod := -0.25 if asleep else sin(_t * 1.3) * 0.05
	_rotm("head", X, nod - q * 0.55)
	# pernas: compensam a inclinacao e alternam o passo
	var leg := sin(w) * (0.5 + 0.15 * q) * a
	_rotm("thigh_l", X, -q * QUAD_PITCH - leg)
	_rotm("thigh_r", X, -q * QUAD_PITCH + leg)
	_rotm("shin_l", X, maxf(0.0, sin(w)) * 0.5 * a)
	_rotm("shin_r", X, maxf(0.0, -sin(w)) * 0.5 * a)
	# bracos: balancam em pe; de quatro viram patas da frente (passo cruzado)
	var arm_swing := sin(w) * (0.45 + 0.1 * q) * a
	_rotm2("arm_l", X, -q * 0.95 + arm_swing, Z, q * 0.35)
	_rotm2("arm_r", X, -q * 0.95 - arm_swing, Z, -q * 0.35)
	_rotm("forearm_l", X, -q * 0.25)
	_rotm("forearm_r", X, -q * 0.25)
	_body.position.y = -q * QUAD_DROP
	for k in _tail.size():
		var i: int = _tail[k]
		var sway := sin(_t * (2.0 + 4.0 * a) - k * 0.45) * (0.06 + 0.06 * a)
		_skel.set_bone_pose_rotation(i, (_base_rot[i] as Quaternion) * Quaternion(Vector3.FORWARD, sway))
	# olhos: dormindo fechados, feliz/arteiro meio fechados, piscada de vez em quando
	_next_blink -= delta
	if _next_blink <= 0.0:
		_next_blink = randf_range(2.5, 5.0)
		_blink_left = 0.14
	_blink_left = maxf(_blink_left - delta, 0.0)
	var lid := 0.0
	match _face_state:
		Face.SLEEP:
			lid = 1.0
		Face.HAPPY:
			lid = 0.55
		Face.MISCHIEF:
			lid = 0.4
	if _blink_left > 0.0:
		lid = 1.0
	for l in _lids:
		(l[0] as MeshInstance3D).set_blend_shape_value(int(l[1]), lid)


func set_face(f: Face) -> void:
	_face_state = f
	for e in _eyes_open:
		e.visible = f == Face.OPEN or f == Face.MISCHIEF
	for e in _eyes_closed:
		e.visible = f == Face.SLEEP
	for e in _eyes_happy:
		e.visible = f == Face.HAPPY
	if f == Face.MISCHIEF and _eyes_open.size() == 2:
		_eyes_open[0].scale = Vector3(1, 0.5, 1)
		_eyes_open[1].scale = Vector3(1, 0.5, 1)
	else:
		for e in _eyes_open:
			e.scale = Vector3.ONE
	_zzz.visible = f == Face.SLEEP


## Cancela qualquer caminhada em andamento.
func cancel() -> void:
	_token += 1
	_moving = false


## Anda ate p (no chao). Retorna false se outra ordem cancelar.
func walk_to(p: Vector3, speed: float) -> bool:
	p = Island.clamp_inside(p, 0.6)
	_token += 1
	var my := _token
	_moving = true
	_cur_speed = speed
	while true:
		await get_tree().process_frame
		if my != _token:
			return false
		var to := p - position
		to.y = 0.0
		var step := speed * get_process_delta_time()
		_face_dir(to)
		if to.length() <= step:
			position = Vector3(p.x, Island.ground_y(p), p.z)
			_moving = false
			return true
		position += to.normalized() * step
		position.y = Island.ground_y(position)
	return false


## Pulo em arco ate p (usado para descer da arvore e subir na plataforma).
func hop_to(p: Vector3, height: float, secs: float) -> void:
	p = Island.clamp_inside(p, 0.6)
	cancel()
	var from := position
	_face_dir(p - from)
	var tw := create_tween()
	tw.tween_method(_arc.bind(from, p, height), 0.0, 1.0, secs)
	await tw.finished
	_squash = 0.25


func _arc(k: float, from: Vector3, to: Vector3, height: float) -> void:
	position = from.lerp(to, k) + Vector3(0, sin(k * PI) * height, 0)


func bounce(times: int, height: float = 0.35) -> void:
	for i in times:
		var tw := create_tween()
		tw.tween_property(_body, "position:y", height, 0.16).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
		tw.tween_property(_body, "position:y", 0.0, 0.16).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
		await tw.finished
		_squash = 0.2


## Rola no chao (para fazer o ZodIA tropecar).
func roll(secs: float) -> void:
	var tw := create_tween()
	tw.tween_property(_visual, "rotation:x", _visual.rotation.x + TAU * 2.0, secs)
	await tw.finished
	_visual.rotation.x = 0.0


func wake_up(fast: bool, path: Array) -> void:
	asleep = false
	set_face(Face.OPEN)
	_squash = 0.3
	if not fast:
		# espreguica
		var tw := create_tween()
		tw.tween_property(_body, "scale", Vector3(0.85, 1.25, 0.85), 0.6)
		tw.tween_property(_body, "scale", Vector3.ONE, 0.4)
		await tw.finished
		await bounce(2, 0.2)
	for p in path:
		await hop_to(p, 0.7, 0.35 if fast else 0.6)


func sleep_at(p: Vector3) -> void:
	position = p
	asleep = true
	set_face(Face.SLEEP)


func _face_dir(d: Vector3) -> void:
	if Vector2(d.x, d.z).length() > 0.01:
		rotation.y = lerp_angle(rotation.y, atan2(d.x, d.z), 0.35)


func look_toward(p: Vector3) -> void:
	_face_dir(p - position)


func _process(delta: float) -> void:
	_t += delta
	_squash = maxf(_squash - delta, 0.0)
	var s := 1.0
	if asleep:
		s = 1.0 + sin(_t * 1.6) * 0.04
		_zzz.position.y = 1.35 + fmod(_t * 0.25, 0.3)
		_zzz.modulate.a = 1.0 - fmod(_t * 0.25, 0.3) / 0.3
	if _skel:
		_animate_rig(delta)
	var bob := absf(sin(_t * 10.0)) * 0.08 if _moving else 0.0
	_visual.position.y = bob
	var sq := 1.0 - _squash * 0.6
	_visual.scale = Vector3(s * (2.0 - sq), s * sq, s * (2.0 - sq))
	_shadow.position.y = Island.ground_y(global_position) - global_position.y + 0.02
