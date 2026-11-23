class_name CameraRig
extends Camera3D
## Camera 9:16. Foca o ZodIA quase sempre; de vez em quando (ou quando um
## presente mexe com o Kumo) foca o Kumo por alguns segundos.

## Deslocamento da camera em relacao ao alvo (alto e atras, olhando de cima).
const FAR_OFFSET := Vector3(0.0, 3.6, 6.6)
const NEAR_OFFSET := Vector3(0.0, 2.5, 4.4)

var main_target: Node3D
## Ponto que puxa o enquadramento junto com o ZodIA (a plataforma).
var anchor := Vector3.ZERO

var _focus: Node3D
var _focus_left := 0.0
var _look := Vector3.ZERO


func _ready() -> void:
	keep_aspect = Camera3D.KEEP_WIDTH
	fov = 62.0
	near = 0.1
	far = 80.0
	current = true


func focus(n: Node3D, secs: float) -> void:
	_focus = n
	_focus_left = secs


func release() -> void:
	_focus_left = 0.0


func is_focusing() -> bool:
	return _focus_left > 0.0


func snap() -> void:
	_process(10.0)


func _process(delta: float) -> void:
	_focus_left = maxf(_focus_left - delta, 0.0)
	var target := anchor
	var offset := FAR_OFFSET
	var speed := 2.2
	if _focus_left > 0.0 and is_instance_valid(_focus):
		target = _focus.global_position + Vector3(0, 0.4, 0)
		offset = NEAR_OFFSET
		speed = 4.0
	elif is_instance_valid(main_target):
		target = main_target.global_position.lerp(anchor, 0.55) + Vector3(0, 1.1, 0)
	var k := minf(delta * speed, 1.0)
	global_position = global_position.lerp(target + offset, k)
	_look = _look.lerp(target, k)
	look_at(_look, Vector3.UP)
