class_name Station
extends Node2D
## Balcoes, mesa de preparo e forno. A origem fica na base do movel,
## para o y-sort colocar quem esta atras/na frente corretamente.

enum Kind { ORDER_COUNTER, DELIVERY_COUNTER, PREP_TABLE, OVEN }

var kind: Kind = Kind.ORDER_COUNTER
var raw := 0
var baking := 0
var _t := 0.0


func _process(delta: float) -> void:
	_t += delta
	queue_redraw()


func _draw() -> void:
	match kind:
		Kind.ORDER_COUNTER:
			_counter(Color("#d94a3d"), "PEDIDOS")
		Kind.DELIVERY_COUNTER:
			_counter(Color("#2f9e6e"), "ENTREGA")
		Kind.PREP_TABLE:
			_prep()
		Kind.OVEN:
			_oven()


func _counter(color: Color, label: String) -> void:
	var top := Rect2(-185, -120, 370, 30)
	var front := Rect2(-175, -90, 350, 90)
	draw_rect(top.grow(5.0), Art.OUTLINE)
	draw_rect(front.grow(5.0), Art.OUTLINE)
	draw_rect(front, color)
	for i in 7:
		if i % 2 == 0:
			draw_rect(Rect2(-175 + i * 50, -90, 50, 90), color.lightened(0.25))
	draw_rect(top, Color("#f4e6c8"))
	Art.text(self, Vector2(0, -45), label, 38, Color.WHITE)


func _prep() -> void:
	var top := Rect2(-150, -95, 300, 26)
	draw_rect(top.grow(5.0), Art.OUTLINE)
	draw_rect(Rect2(-140, -69, 280, 69).grow(5.0), Art.OUTLINE)
	draw_rect(Rect2(-140, -69, 280, 69), Color("#9c6b43"))
	draw_rect(top, Color("#e8d7b5"))
	for i in raw:
		Art.pizza(self, Vector2(-80 + i * 80, -108), 28.0, true)
	Art.text(self, Vector2(0, -32), "PREPARO", 30, Color.WHITE)


func _oven() -> void:
	var body := Rect2(-130, -230, 260, 230)
	draw_rect(body.grow(5.0), Art.OUTLINE)
	draw_rect(body, Color("#8f9bb3"))
	draw_rect(Rect2(-110, -200, 220, 40), Color("#6d7891"))
	var window := Rect2(-95, -145, 190, 105)
	draw_rect(window.grow(5.0), Art.OUTLINE)
	var glow := 0.0
	if baking > 0:
		glow = 0.6 + sin(_t * 8.0) * 0.2
	draw_rect(window, Color("#3a2d3f").lerp(Color("#ff8a3d"), glow))
	for i in baking:
		Art.pizza(self, Vector2(-55 + i * 55, -92), 24.0, true)
	Art.text(self, Vector2(0, -180), "FORNO", 30, Color.WHITE)
