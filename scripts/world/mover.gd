class_name Mover
extends Node2D
## Base para quem anda pelo chao: movimento ate um alvo + escala de profundidade.

signal arrived

var walk_speed := 260.0
var _target := Vector2.ZERO
var _moving := false
var _t := 0.0


func speed_mult() -> float:
	return 1.0


func is_moving() -> bool:
	return _moving


func walk_to(p: Vector2) -> void:
	_target = p
	if position.distance_to(p) < 1.0:
		_moving = false
		return
	_moving = true
	await arrived


func teleport(p: Vector2) -> void:
	position = p
	_target = p
	if _moving:
		_moving = false
		arrived.emit()


func _process(delta: float) -> void:
	_t += delta
	if _moving:
		var step := walk_speed * speed_mult() * delta
		var to := _target - position
		if to.length() <= step:
			position = _target
			_moving = false
			arrived.emit()
		elif step > 0.0:
			position += to.normalized() * step
	scale = Vector2.ONE * Art.depth_scale(position.y)
	_tick(delta)
	queue_redraw()


func _tick(_delta: float) -> void:
	pass
