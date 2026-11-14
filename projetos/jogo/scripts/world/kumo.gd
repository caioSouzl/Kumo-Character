class_name Kumo
extends Mover
## O Kumo. Trabalha sozinho; os presentes mudam o comportamento dele
## (acelera, entra em panico, comemora).

var carrying := 0
var work_progress := -1.0

var _boost_mult := 1.0
var _boost_left := 0.0
var _stun_left := 0.0
var _celebrate_left := 0.0


func speed_mult() -> float:
	if _stun_left > 0.0:
		return 0.0
	return _boost_mult if _boost_left > 0.0 else 1.0


func boost(mult: float, secs: float) -> void:
	_boost_mult = maxf(_boost_mult if _boost_left > 0.0 else 1.0, mult)
	_boost_left += secs


func panic(secs: float) -> void:
	_stun_left = maxf(_stun_left, secs)


func celebrate(secs: float = 1.2) -> void:
	_celebrate_left = maxf(_celebrate_left, secs)


func is_boosted() -> bool:
	return _boost_left > 0.0


## Trabalha por `seconds` (afetado por boost/panico). Retorna false se `abort` ficar true.
func work(seconds: float, abort: Callable) -> bool:
	var done := 0.0
	work_progress = 0.0
	while done < seconds:
		await get_tree().process_frame
		if abort.call():
			work_progress = -1.0
			return false
		done += get_process_delta_time() * speed_mult()
		work_progress = done / seconds
	work_progress = -1.0
	return true


func _tick(delta: float) -> void:
	_boost_left = maxf(_boost_left - delta, 0.0)
	_stun_left = maxf(_stun_left - delta, 0.0)
	_celebrate_left = maxf(_celebrate_left - delta, 0.0)


func _draw() -> void:
	var bob := sin(_t * 14.0) * 5.0 if _moving and speed_mult() > 0.0 else sin(_t * 2.5) * 2.0
	var jump := -absf(sin(_t * 11.0)) * 45.0 if _celebrate_left > 0.0 else 0.0
	var shake := Vector2(sin(_t * 70.0) * 7.0, 0.0) if _stun_left > 0.0 else Vector2.ZERO
	var o := Vector2(0.0, bob + jump) + shake
	var body := Color("#fff3fa") if is_boosted() else Color("#ffffff")

	Art.ellipse(self, Vector2.ZERO, Vector2(62, 16), Color(0, 0, 0, 0.22))

	# corpo de nuvem (contorno + preenchimento)
	var puffs := [[Vector2(-46, -70), 44.0], [Vector2(46, -70), 44.0], [Vector2(0, -112), 58.0], [Vector2(0, -60), 54.0]]
	for p in puffs:
		draw_circle(o + p[0], p[1] + 6.0, Art.OUTLINE)
	for p in puffs:
		draw_circle(o + p[0], p[1], body)

	# chapeu de cozinheiro
	draw_rect(Rect2(o + Vector2(-38, -196), Vector2(76, 40)).grow(5.0), Art.OUTLINE)
	for c in [Vector2(-26, -204), Vector2(0, -216), Vector2(26, -204)]:
		draw_circle(o + c, 27.0, Art.OUTLINE)
	for c in [Vector2(-26, -204), Vector2(0, -216), Vector2(26, -204)]:
		draw_circle(o + c, 22.0, Color.WHITE)
	draw_rect(Rect2(o + Vector2(-38, -196), Vector2(76, 40)), Color.WHITE)

	# rosto
	if _stun_left > 0.0:
		for s in [-1.0, 1.0]:
			draw_circle(o + Vector2(20 * s, -112), 12.0, Art.OUTLINE)
			draw_circle(o + Vector2(20 * s, -112), 7.0, Color.WHITE)
		draw_circle(o + Vector2(0, -84), 11.0, Art.OUTLINE)
		draw_circle(o + Vector2(52, -138), 8.0, Color("#7cc6f2"))
	else:
		for s in [-1.0, 1.0]:
			draw_circle(o + Vector2(20 * s, -112), 8.0, Art.OUTLINE)
			draw_circle(o + Vector2(20 * s + 3, -115), 2.5, Color.WHITE)
		if _celebrate_left > 0.0:
			draw_arc(o + Vector2(0, -96), 16.0, 0.1, PI - 0.1, 12, Art.OUTLINE, 5.0)
		else:
			draw_arc(o + Vector2(0, -98), 10.0, 0.3, PI - 0.3, 10, Art.OUTLINE, 4.0)
	for s in [-1.0, 1.0]:
		Art.ellipse(self, o + Vector2(40 * s, -92), Vector2(11, 6), Color(1.0, 0.55, 0.65, 0.7))

	if is_boosted():
		for i in 3:
			var hp := o + Vector2(-70 + i * 70, -250 - fmod(_t * 60.0 + i * 25.0, 60.0))
			draw_circle(hp + Vector2(-6, 0), 8.0, Color("#ff5c8a"))
			draw_circle(hp + Vector2(6, 0), 8.0, Color("#ff5c8a"))
			draw_colored_polygon(PackedVector2Array([hp + Vector2(-13, 3), hp + Vector2(13, 3), hp + Vector2(0, 17)]), Color("#ff5c8a"))

	# pizzas na mao
	for i in carrying:
		Art.pizza(self, o + Vector2(0, -40 - i * 14), 30.0)

	if work_progress >= 0.0:
		Art.bar(self, o + Vector2(0, -260), 110.0, work_progress, Color("#47b881"))
