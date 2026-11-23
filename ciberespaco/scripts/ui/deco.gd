class_name Deco
extends RefCounted
## Molduras desenhadas em codigo nos dois estilos do design:
## - ZodIA: neon magenta/ciano com trilhas de circuito;
## - Kumo: cipo com folhas e pedrinhas;
## - misto (ranking): cantos neon com folhagem.

const MAGENTA := Color(1.0, 0.2, 0.85)
const CYAN := Color(0.3, 0.85, 1.0)
const VIOLET := Color(0.45, 0.2, 0.85)
const LEAF := Color(0.3, 0.62, 0.28)
const LEAF_LIGHT := Color(0.5, 0.8, 0.35)
const VINE := Color(0.4, 0.3, 0.18)
const STONE := Color(0.55, 0.55, 0.6)
const FLOWER := [Color(1.0, 0.55, 0.3), Color(1.0, 0.8, 0.25), Color(0.95, 0.4, 0.55)]


static func panel_bg(ci: CanvasItem, r: Rect2, col: Color) -> void:
	ci.draw_rect(r, col)


static func cyber_frame(ci: CanvasItem, r: Rect2, t: float) -> void:
	ci.draw_rect(r, MAGENTA, false, 6.0)
	ci.draw_rect(r.grow(-10), Color(CYAN, 0.5), false, 2.0)
	# cantos em L mais grossos
	var L := 46.0
	for c in [r.position, Vector2(r.end.x, r.position.y), Vector2(r.position.x, r.end.y), r.end]:
		var sx := 1.0 if c.x == r.position.x else -1.0
		var sy := 1.0 if c.y == r.position.y else -1.0
		ci.draw_line(c - Vector2(8 * sx, 8 * sy), c + Vector2(L * sx, -8 * sy), MAGENTA, 8.0)
		ci.draw_line(c - Vector2(8 * sx, 8 * sy), c + Vector2(-8 * sx, L * sy), MAGENTA, 8.0)
	# trilhas de circuito nos cantos sup. esquerdo e inf. direito
	for k in 4:
		var y := r.position.y + 22 + k * 14
		var x0 := r.position.x + 14
		var x1 := x0 + 40 + k * 22
		ci.draw_polyline(PackedVector2Array([Vector2(x0, y), Vector2(x1, y), Vector2(x1 + 12, y + 12)]), CYAN, 2.0)
		ci.draw_circle(Vector2(x1 + 12, y + 12), 4.0, CYAN)
		var yb := r.end.y - 22 - k * 14
		var xb := r.end.x - 14
		var xb1 := xb - 40 - k * 22
		ci.draw_polyline(PackedVector2Array([Vector2(xb, yb), Vector2(xb1, yb), Vector2(xb1 - 12, yb - 12)]), CYAN, 2.0)
		ci.draw_circle(Vector2(xb1 - 12, yb - 12), 4.0, CYAN)
	# pulso correndo pela borda de cima
	var px := r.position.x + fmod(t * 260.0, r.size.x)
	ci.draw_line(Vector2(px, r.position.y), Vector2(minf(px + 60, r.end.x), r.position.y), Color(1, 1, 1, 0.9), 6.0)


static func leaf(ci: CanvasItem, p: Vector2, ang: float, s: float, col: Color) -> void:
	var pts := PackedVector2Array()
	for i in 12:
		var a := TAU * i / 12.0
		pts.append(p + Vector2(cos(a) * 14.0 * s, sin(a) * 6.0 * s).rotated(ang))
	ci.draw_colored_polygon(pts, col)


static func vine(ci: CanvasItem, a: Vector2, b: Vector2, t: float, seed_v: float) -> void:
	var pts := PackedVector2Array()
	var n := 24
	for i in n + 1:
		var k := float(i) / n
		var p := a.lerp(b, k)
		var nrm := (b - a).normalized().orthogonal()
		pts.append(p + nrm * sin(k * 12.0 + seed_v) * 6.0)
	ci.draw_polyline(pts, VINE, 4.0)
	for i in range(1, n, 2):
		var side := 1.0 if i % 4 == 1 else -1.0
		var dir := (b - a).normalized()
		var sway := sin(t * 2.0 + i) * 0.15
		leaf(ci, pts[i] + dir.orthogonal() * side * 10.0, dir.angle() + side * 0.9 + sway, 1.1, LEAF if i % 3 else LEAF_LIGHT)


static func kumo_frame(ci: CanvasItem, r: Rect2, t: float) -> void:
	vine(ci, r.position + Vector2(0, 10), Vector2(r.end.x - 20, r.position.y + 18), t, 0.0)
	vine(ci, r.position + Vector2(8, 0), Vector2(r.position.x + 14, r.end.y - 30), t, 2.0)
	vine(ci, Vector2(r.position.x + 30, r.end.y - 6), Vector2(r.end.x, r.end.y - 10), t, 4.0)
	# pedrinhas e folhas altas no canto inferior esquerdo
	for i in 3:
		var c := Vector2(r.position.x + 20 + i * 28, r.end.y - 4 - (i % 2) * 6)
		var pts := PackedVector2Array()
		for k in 10:
			var a := TAU * k / 10.0
			pts.append(c + Vector2(cos(a) * (22 - i * 4), sin(a) * (13 - i * 2)))
		ci.draw_colored_polygon(pts, STONE.darkened(i * 0.12))
	for i in 6:
		var base := Vector2(r.position.x + 110 + i * 34, r.end.y - 8)
		leaf(ci, base + Vector2(0, -22), -PI / 2.0 + sin(t * 1.5 + i) * 0.12, 1.8, LEAF if i % 2 else LEAF_LIGHT)


static func flowers_row(ci: CanvasItem, center: Vector2, width: float, t: float) -> void:
	ci.draw_line(center - Vector2(width / 2.0, 0), center + Vector2(width / 2.0, 0), VINE, 3.0)
	var n := 5
	for i in n:
		var p := center + Vector2(-width / 2.0 + width * (i + 0.5) / n, 0)
		for k in 6:
			var a := TAU * k / 6.0 + t * 0.4
			ci.draw_circle(p + Vector2.from_angle(a) * 9.0, 7.0, FLOWER[i % FLOWER.size()])
		ci.draw_circle(p, 5.0, Color(0.95, 0.85, 0.35))
		leaf(ci, p + Vector2(-20, 4), 0.3, 1.0, LEAF)
		leaf(ci, p + Vector2(20, 4), -0.3, 1.0, LEAF_LIGHT)


static func circuit_row(ci: CanvasItem, center: Vector2, width: float, t: float) -> void:
	var y := center.y
	var x0 := center.x - width / 2.0
	var pts := PackedVector2Array()
	var n := 8
	for i in n + 1:
		var x := x0 + width * i / n
		pts.append(Vector2(x, y + (10.0 if i % 2 else -10.0)))
	ci.draw_polyline(pts, MAGENTA, 4.0)
	ci.draw_polyline(pts, Color(1, 1, 1, 0.4 + 0.3 * sin(t * 4.0)), 1.5)
	ci.draw_circle(center, 10.0, MAGENTA)
	ci.draw_circle(center, 5.0, Color(0.1, 0.0, 0.2))


static func mixed_frame(ci: CanvasItem, r: Rect2, t: float) -> void:
	var L := 90.0
	for k in 2:
		var g := 8.0 * k
		var col := MAGENTA if k == 0 else CYAN
		ci.draw_polyline(PackedVector2Array([Vector2(r.position.x + g, r.position.y + L), Vector2(r.position.x + g, r.position.y + g), Vector2(r.position.x + L * 1.6, r.position.y + g)]), col, 4.0)
		ci.draw_polyline(PackedVector2Array([Vector2(r.end.x - g, r.end.y - L), Vector2(r.end.x - g, r.end.y - g), Vector2(r.end.x - L * 1.6, r.end.y - g)]), col, 4.0)
	vine(ci, r.position + Vector2(20, 10), r.position + Vector2(36, 180), t, 1.0)
	for i in 5:
		leaf(ci, r.end + Vector2(-30 - i * 18, -24 - (i % 2) * 14), -PI / 2.0 + 0.5 - i * 0.25, 1.6, LEAF if i % 2 else LEAF_LIGHT)


## Iconezinho de robo (no lugar do emoji, que a fonte padrao nao tem).
static func robot_icon(ci: CanvasItem, c: Vector2, s: float, col: Color) -> void:
	ci.draw_rect(Rect2(c + Vector2(-14, -10) * s, Vector2(28, 22) * s), col)
	ci.draw_circle(c + Vector2(-6, 0) * s, 3.0 * s, Color(0.1, 0.05, 0.2))
	ci.draw_circle(c + Vector2(6, 0) * s, 3.0 * s, Color(0.1, 0.05, 0.2))
	ci.draw_line(c + Vector2(0, -10) * s, c + Vector2(0, -17) * s, col, 2.0 * s)
	ci.draw_circle(c + Vector2(0, -18) * s, 3.0 * s, col)
