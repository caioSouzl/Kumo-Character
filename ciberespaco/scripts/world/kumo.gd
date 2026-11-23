class_name Kumo
extends Node3D
## O Kumo, a nuvenzinha curiosa. Dorme no terrario da arvore, acorda, desce,
## brinca com os brinquedos e so atrapalha o ZodIA quando chega o presente certo.
## Modelo provisorio em esferas; se existir assets/models/kumo.glb, ele entra no lugar.

enum Face { OPEN, SLEEP, HAPPY, MISCHIEF }

const WHITE := Color(1.0, 1.0, 1.0)
const INK := Color(0.17, 0.13, 0.25)
const CHEEK := Color(1.0, 0.55, 0.68)

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
	_zzz.position = Vector3(0.45, 1.15, 0)
	add_child(_zzz)
	set_face(Face.SLEEP)


func _build_placeholder() -> void:
	var white := Mat.solid(WHITE, 0.9)
	for p in [[Vector3(-0.32, 0.42, 0), 0.3], [Vector3(0.32, 0.42, 0), 0.3], [Vector3(0, 0.62, 0), 0.4], [Vector3(0, 0.36, 0.05), 0.36], [Vector3(-0.18, 0.78, -0.05), 0.24], [Vector3(0.2, 0.8, -0.04), 0.22]]:
		Mat.add(_visual, Mat.sphere(p[1], -1, 14), white, p[0])
	var ink := Mat.solid(INK, 0.5)
	for s in [-1.0, 1.0]:
		var e := Mat.add(_visual, Mat.sphere(0.055, 0.12, 10), ink, Vector3(0.13 * s, 0.62, 0.37))
		_eyes_open.append(e)
		var c := Mat.add(_visual, Mat.box(Vector3(0.12, 0.022, 0.02)), ink, Vector3(0.13 * s, 0.6, 0.39))
		_eyes_closed.append(c)
		var h := Node3D.new()
		h.position = Vector3(0.13 * s, 0.62, 0.385)
		_visual.add_child(h)
		Mat.add(h, Mat.box(Vector3(0.08, 0.022, 0.02)), ink, Vector3(-0.03, -0.015, 0), Vector3(0, 0, 35))
		Mat.add(h, Mat.box(Vector3(0.08, 0.022, 0.02)), ink, Vector3(0.03, -0.015, 0), Vector3(0, 0, -35))
		_eyes_happy.append(h)
		Mat.add(_visual, Mat.sphere(0.06, 0.06, 10), Mat.solid(CHEEK, 0.9), Vector3(0.25 * s, 0.52, 0.33), Vector3.ZERO, Vector3(1.2, 0.6, 0.5))
	# pezinhos
	for s in [-1.0, 1.0]:
		Mat.add(_visual, Mat.sphere(0.1, 0.12, 10), white, Vector3(0.17 * s, 0.07, 0.05))


func set_face(f: Face) -> void:
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
	_token += 1
	var my := _token
	_moving = true
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
		_zzz.position.y = 1.15 + fmod(_t * 0.25, 0.3)
		_zzz.modulate.a = 1.0 - fmod(_t * 0.25, 0.3) / 0.3
	var bob := absf(sin(_t * 10.0)) * 0.08 if _moving else 0.0
	_visual.position.y = bob
	var sq := 1.0 - _squash * 0.6
	_visual.scale = Vector3(s * (2.0 - sq), s * sq, s * (2.0 - sq))
	_shadow.position.y = Island.ground_y(global_position) - global_position.y + 0.02
