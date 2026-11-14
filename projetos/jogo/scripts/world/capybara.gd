class_name Capybara
extends Mover
## A capivara invasora: corre atras do Kumo e come uma pizza.

var follow: Node2D = null
var eating := false


func _tick(_delta: float) -> void:
	if follow != null and is_instance_valid(follow) and _moving:
		_target = follow.position + Vector2(95, 15)


func _draw() -> void:
	var bob := sin(_t * 18.0) * 4.0 if _moving else 0.0
	var chew := sin(_t * 20.0) * 4.0 if eating else 0.0
	var o := Vector2(0, bob)
	Art.ellipse(self, Vector2.ZERO, Vector2(70, 14), Color(0, 0, 0, 0.2))
	var fur := Color("#a0683a")
	Art.ellipse(self, o + Vector2(0, -50), Vector2(72, 46), Art.OUTLINE)
	Art.ellipse(self, o + Vector2(0, -50), Vector2(66, 40), fur)
	Art.ellipse(self, o + Vector2(-62, -78), Vector2(40, 34), Art.OUTLINE)
	Art.ellipse(self, o + Vector2(-62, -78), Vector2(35, 29), fur)
	draw_circle(o + Vector2(-48, -108), 9.0, Color("#7a4a26"))
	draw_circle(o + Vector2(-60, -84), 5.0, Art.OUTLINE)
	Art.ellipse(self, o + Vector2(-90, -70 + chew), Vector2(12, 8), Color("#5b3a20"))
	for x in [-40.0, -10.0, 25.0, 50.0]:
		draw_rect(Rect2(o + Vector2(x - 7, -16), Vector2(14, 18)), fur.darkened(0.2))
	if eating:
		Art.pizza(self, o + Vector2(-112, -64), 22.0)
		Art.text(self, o + Vector2(-20, -150), "nhac nhac", 30, Color.WHITE)
