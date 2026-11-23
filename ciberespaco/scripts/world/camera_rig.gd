class_name CameraRig
extends Camera3D
## Camera 9:16. Foca o ZodIA quase sempre; de vez em quando (ou quando um
## presente mexe com o Kumo) foca o Kumo por alguns segundos.

## Deslocamento da camera em relacao ao alvo (alto e atras, olhando de cima).
const FAR_OFFSET := Vector3(0.0, 3.6, 6.6)
const NEAR_OFFSET := Vector3(1.6, 3.0, 3.8)
## Para mostrar um objeto do ZodIA (pronto ou quebrando).
const OBJECT_OFFSET := Vector3(0.0, 3.6, 6.0)

var main_target: Node3D
## Ponto que puxa o enquadramento junto com o ZodIA (a plataforma).
var anchor := Vector3.ZERO

var _focus: Node3D
var _focus_left := 0.0
var _focus_offset := Vector3.ZERO
var _look := Vector3.ZERO
## Obstaculo grande (a arvore no centro); a camera se posiciona do lado oposto.
var obstacle := Vector3.ZERO
var _yaw := 0.0
var _check_cut := false
var _was_focusing := false


func _ready() -> void:
	keep_aspect = Camera3D.KEEP_WIDTH
	fov = 62.0
	near = 0.1
	far = 160.0
	current = true


func focus(n: Node3D, secs: float, offset: Vector3 = NEAR_OFFSET) -> void:
	_focus = n
	_focus_left = secs
	_focus_offset = offset
	_check_cut = true


func release() -> void:
	_focus_left = 0.0
	_check_cut = true


func is_focusing() -> bool:
	return _focus_left > 0.0


func snap() -> void:
	var out := Vector2(anchor.x - obstacle.x, anchor.z - obstacle.z)
	if out.length() > 2.5:
		_yaw = atan2(out.x, out.y)
	_process(10.0)


func _process(delta: float) -> void:
	_focus_left = maxf(_focus_left - delta, 0.0)
	var target := anchor
	var offset := FAR_OFFSET
	var speed := 2.2
	if _focus_left > 0.0 and is_instance_valid(_focus):
		target = _focus.global_position + Vector3(0, 0.4 if _focus_offset == NEAR_OFFSET else 1.0, 0)
		offset = _focus_offset
		speed = 4.0
	elif is_instance_valid(main_target):
		target = main_target.global_position.lerp(anchor, 0.55) + Vector3(0, 1.1, 0)
	# a camera fica do lado de fora em relacao a arvore (centro do mapa),
	# entao o tronco nunca fica entre ela e quem esta sendo mostrado
	var out := Vector2(target.x - obstacle.x, target.z - obstacle.z)
	var focusing := _focus_left > 0.0
	if focusing != _was_focusing:
		_check_cut = true
	_was_focusing = focusing
	var cut := false
	if out.length() > 2.5:
		var goal_yaw := atan2(out.x, out.y)
		# troca de alvo do outro lado da arvore: corte seco em vez de girar
		# a camera por dentro do tronco
		if _check_cut and absf(angle_difference(_yaw, goal_yaw)) > 1.0:
			_yaw = goal_yaw
			cut = true
		_yaw = lerp_angle(_yaw, goal_yaw, minf(delta * 1.5, 1.0))
	_check_cut = false
	offset = Basis(Vector3.UP, _yaw) * offset
	var k := 1.0 if cut else minf(delta * speed, 1.0)
	if cut:
		_look = target
	global_position = global_position.lerp(target + offset, k)
	_look = _look.lerp(target, k)
	look_at(_look, Vector3.UP)
