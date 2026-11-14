class_name Art
extends RefCounted
## Desenho provisorio (placeholder) e a regra de profundidade 2.5D.
## Troque por sprites quando a arte final do Kumo estiver pronta.

const FLOOR_TOP := 760.0
const FLOOR_BOTTOM := 1700.0
const OUTLINE := Color("#2b2140")


## Quanto mais perto da camera (y maior), maior o personagem.
static func depth_scale(y: float) -> float:
	return lerpf(0.78, 1.12, clampf((y - FLOOR_TOP) / (FLOOR_BOTTOM - FLOOR_TOP), 0.0, 1.0))


static func ellipse(ci: CanvasItem, center: Vector2, radii: Vector2, color: Color) -> void:
	var pts := PackedVector2Array()
	for i in 28:
		var a := TAU * i / 28.0
		pts.append(center + Vector2(cos(a) * radii.x, sin(a) * radii.y))
	ci.draw_colored_polygon(pts, color)


static func pizza(ci: CanvasItem, p: Vector2, r: float, raw: bool = false) -> void:
	ci.draw_circle(p, r + 2.0, OUTLINE)
	ci.draw_circle(p, r, Color("#e9d3a0") if raw else Color("#c8863a"))
	ci.draw_circle(p, r * 0.8, Color("#e46a4f") if raw else Color("#f3c74f"))
	for a in [0.3, 1.9, 3.4, 4.8]:
		ci.draw_circle(p + Vector2.from_angle(a) * r * 0.45, r * 0.15, Color("#b8322a"))


static func text(ci: CanvasItem, center: Vector2, s: String, size: int, color: Color) -> void:
	var font := ThemeDB.fallback_font
	var w := font.get_string_size(s, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x
	ci.draw_string(font, center + Vector2(-w / 2.0, size * 0.35), s, HORIZONTAL_ALIGNMENT_LEFT, -1, size, color)


static func bar(ci: CanvasItem, center: Vector2, width: float, frac: float, fill: Color) -> void:
	var r := Rect2(center - Vector2(width / 2.0, 7.0), Vector2(width, 14.0))
	ci.draw_rect(r.grow(3.0), OUTLINE)
	ci.draw_rect(r, Color("#ffffff"))
	ci.draw_rect(Rect2(r.position, Vector2(width * clampf(frac, 0.0, 1.0), 14.0)), fill)
