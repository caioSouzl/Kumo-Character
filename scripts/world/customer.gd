class_name Customer
extends Mover
## Cliente simples: entra, faz o pedido (1 a 3 pizzas), espera e sai
## feliz ou bravo quando a paciencia acaba.

signal ran_out

var kind := "normal"
var pizzas := 1
var patience_max := 90.0
var patience := 90.0
var body_color := Color("#5b8def")
var show_order := false
var cooking := false
var cooking_mult := 0.5
## Saiu ou ja foi atendido: o pedido nao vale mais.
var gone := false

var _mood := "normal"
var _mood_t := 0.0
var _sent := false


func setup(p_kind: String, p_pizzas: int, p_patience: float, p_color: Color, p_speed: float) -> void:
	kind = p_kind
	pizzas = p_pizzas
	patience_max = p_patience
	patience = p_patience
	body_color = p_color
	walk_speed = p_speed


func lose_patience(secs: float) -> void:
	if gone:
		return
	patience = maxf(patience - secs, 0.0)
	_mood = "annoyed"
	_mood_t = 1.5


func receive() -> void:
	gone = true
	show_order = false
	_mood = "happy"
	_mood_t = 99.0


func leave_angry() -> void:
	gone = true
	show_order = false
	_mood = "angry"
	_mood_t = 99.0


func _tick(delta: float) -> void:
	_mood_t -= delta
	if _mood_t <= 0.0 and not gone:
		_mood = "normal"
	if gone:
		return
	patience -= delta * (cooking_mult if cooking else 1.0)
	if patience <= 0.0 and not _sent:
		_sent = true
		ran_out.emit()


func _draw() -> void:
	var bob := sin(_t * 12.0) * 4.0 if _moving else 0.0
	if _mood == "happy":
		bob = -absf(sin(_t * 10.0)) * 30.0
	var o := Vector2(0, bob)
	Art.ellipse(self, Vector2.ZERO, Vector2(44, 12), Color(0, 0, 0, 0.2))
	Art.ellipse(self, o + Vector2(0, -62), Vector2(42, 60), Art.OUTLINE)
	Art.ellipse(self, o + Vector2(0, -62), Vector2(36, 54), body_color)
	var skin := Color("#ffd9b3")
	if _mood == "angry" or (kind == "impatient" and patience < patience_max * 0.35 and not gone):
		skin = Color("#ff8a7a")
	draw_circle(o + Vector2(0, -146), 38.0, Art.OUTLINE)
	draw_circle(o + Vector2(0, -146), 33.0, skin)
	for s in [-1.0, 1.0]:
		draw_circle(o + Vector2(12 * s, -150), 5.0, Art.OUTLINE)
	match _mood:
		"happy":
			draw_arc(o + Vector2(0, -136), 12.0, 0.1, PI - 0.1, 10, Art.OUTLINE, 4.0)
		"angry", "annoyed":
			draw_arc(o + Vector2(0, -124), 11.0, PI + 0.3, TAU - 0.3, 10, Art.OUTLINE, 4.0)
			for s in [-1.0, 1.0]:
				draw_line(o + Vector2(20 * s, -166), o + Vector2(5 * s, -160), Art.OUTLINE, 4.0)
		_:
			draw_line(o + Vector2(-9, -132), o + Vector2(9, -132), Art.OUTLINE, 4.0)
	if kind == "impatient" and not gone:
		Art.text(self, o + Vector2(44, -190), "!", 40, Color("#e0544b"))

	if not gone:
		var frac := patience / patience_max
		var col := Color("#47b881").lerp(Color("#e0544b"), 1.0 - frac)
		Art.bar(self, o + Vector2(0, -200), 80.0, frac, col)

	if show_order:
		var w := 30.0 + pizzas * 52.0
		var r := Rect2(o + Vector2(-w / 2.0, -300), Vector2(w, 72))
		draw_rect(r.grow(5.0), Art.OUTLINE)
		draw_rect(r, Color.WHITE)
		draw_colored_polygon(PackedVector2Array([o + Vector2(-12, -228), o + Vector2(12, -228), o + Vector2(0, -212)]), Color.WHITE)
		for i in pizzas:
			Art.pizza(self, o + Vector2(-w / 2.0 + 41 + i * 52, -264), 21.0)
