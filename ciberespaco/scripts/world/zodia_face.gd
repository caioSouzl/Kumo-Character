class_name ZodiaFace
extends Control
## A tela-rosto do ZodIA, desenhada em codigo (cabe em qualquer modelo 3D:
## a textura vai num quadrado na frente da cabeca).
## As expressoes seguem a folha "Expressoes do ZodIA" do design.

enum Expr {
	NORMAL, CHATEADO, INEXPRESSIVO, DESCONFIADO, ASSUSTADO, ALIVIADO, CONFUSO,
	BATERIA_FRACA, SEM_BATERIA, ENFURECIDO, CHORAMINGANDO, ORGULHOSO, OCULOS_VITORIA,
}

const W := 256.0
const H := 160.0
const INK := Color(0.49, 0.93, 1.0)
const INK_SOFT := Color(0.49, 0.93, 1.0, 0.35)
const RED := Color(1.0, 0.33, 0.45)
const SCREEN := Color(0.02, 0.02, 0.05)

var expr: Expr = Expr.NORMAL
## Desvio dos olhos e boca (px) para o lado que a cabeca olha.
var look := Vector2.ZERO
var _t := 0.0
var _blink := 0.0
var _next_blink := 3.0


func _ready() -> void:
	size = Vector2(W, H)


func set_expr(e: Expr) -> void:
	expr = e
	queue_redraw()


func _process(delta: float) -> void:
	_t += delta
	_next_blink -= delta
	if _next_blink <= 0.0:
		_blink = 0.13
		_next_blink = randf_range(2.5, 5.0)
	_blink = maxf(_blink - delta, 0.0)
	queue_redraw()


func _draw() -> void:
	_round_rect(Rect2(6, 6, W - 12, H - 12), 34.0, SCREEN)
	var c := Vector2(W / 2.0, H / 2.0 + 4.0) + look.clamp(Vector2(-14, -8), Vector2(14, 8))
	var shake := Vector2(sin(_t * 60.0) * 3.0, 0.0) if expr == Expr.ENFURECIDO or expr == Expr.ASSUSTADO else Vector2.ZERO
	c += shake
	var le := c + Vector2(-44, -12)
	var re := c + Vector2(44, -12)
	match expr:
		Expr.NORMAL:
			var h := 6.0 if _blink > 0.0 else 40.0
			_pill(le, Vector2(17, h))
			_pill(re, Vector2(17, h))
			draw_arc(c + Vector2(0, 18), 11.0, 0.35, PI - 0.35, 12, INK, 4.0)
		Expr.CHATEADO:
			draw_line(le + Vector2(-14, -6), le + Vector2(14, 4), INK, 7.0)
			draw_line(re + Vector2(-14, 4), re + Vector2(14, -6), INK, 7.0)
			_pill(le + Vector2(0, 14), Vector2(12, 12))
			_pill(re + Vector2(0, 14), Vector2(12, 12))
			draw_polyline(PackedVector2Array([c + Vector2(-12, 32), c + Vector2(0, 22), c + Vector2(12, 32)]), INK, 4.0)
		Expr.INEXPRESSIVO:
			draw_line(le + Vector2(-16, 0), le + Vector2(16, 0), INK, 7.0)
			draw_line(re + Vector2(-16, 0), re + Vector2(16, 0), INK, 7.0)
			draw_line(c + Vector2(-10, 28), c + Vector2(10, 28), INK, 4.0)
		Expr.DESCONFIADO:
			draw_line(le + Vector2(-16, 2), le + Vector2(16, 2), INK, 7.0)
			draw_line(le + Vector2(-16, -10), le + Vector2(16, -6), INK, 4.0)
			draw_arc(re + Vector2(0, 8), 14.0, PI + 0.3, TAU - 0.3, 10, INK, 6.0)
			draw_line(c + Vector2(-8, 30), c + Vector2(12, 22), INK, 4.0)
		Expr.ASSUSTADO:
			for e in [le, re]:
				draw_arc(e, 17.0, 0.0, TAU, 20, INK, 4.0)
				draw_arc(e, 9.0, 0.0, TAU, 14, INK, 3.0)
				draw_circle(e, 3.0, INK)
			draw_arc(c + Vector2(0, 28), 6.0, 0.0, TAU, 12, INK, 3.0)
			_drop(re + Vector2(34, -20), 1.0)
		Expr.ALIVIADO:
			draw_arc(le + Vector2(0, 6), 14.0, PI + 0.2, TAU - 0.2, 10, INK, 6.0)
			draw_arc(re + Vector2(0, 6), 14.0, PI + 0.2, TAU - 0.2, 10, INK, 6.0)
			draw_arc(c + Vector2(0, 16), 13.0, 0.3, PI - 0.3, 12, INK, 4.0)
			_drop(re + Vector2(36, -12 + fmod(_t * 18.0, 14.0)), 0.8)
		Expr.CONFUSO:
			_spiral(le, _t * 5.0)
			_spiral(re, -_t * 5.0)
			var pts := PackedVector2Array()
			for i in 9:
				pts.append(c + Vector2(-18 + i * 4.5, 28 + sin(i * 1.6 + _t * 8.0) * 3.0))
			draw_polyline(pts, INK, 3.0)
		Expr.BATERIA_FRACA:
			var r := Rect2(c.x - 56, c.y - 30, 104, 56)
			draw_rect(r, INK, false, 6.0)
			draw_rect(Rect2(r.end.x + 2, c.y - 12, 10, 20), INK)
			if fmod(_t, 1.0) < 0.6:
				draw_rect(Rect2(r.position + Vector2(9, 9), Vector2(20, r.size.y - 18)), RED)
		Expr.SEM_BATERIA:
			for e in [le, re]:
				draw_line(e + Vector2(-15, -15), e + Vector2(15, 15), INK, 6.0)
				draw_line(e + Vector2(-15, 15), e + Vector2(15, -15), INK, 6.0)
		Expr.ENFURECIDO:
			draw_colored_polygon(PackedVector2Array([le + Vector2(-20, -14), le + Vector2(18, 4), le + Vector2(-16, 10)]), INK)
			draw_colored_polygon(PackedVector2Array([re + Vector2(20, -14), re + Vector2(-18, 4), re + Vector2(16, 10)]), INK)
			var teeth := PackedVector2Array()
			for i in 7:
				teeth.append(c + Vector2(-24 + i * 8, 24.0 if i % 2 == 0 else 36.0))
			draw_polyline(teeth, INK, 4.0)
			draw_rect(Rect2(c + Vector2(-26, 22), Vector2(52, 16)), INK, false, 3.0)
		Expr.CHORAMINGANDO:
			for e in [le, re]:
				draw_arc(e, 15.0, 0.0, TAU, 18, INK, 4.0)
				draw_circle(e + Vector2(3, -3), 4.0, INK)
				for k in 2:
					var y := fmod(_t * 40.0 + k * 22.0, 44.0)
					_drop(e + Vector2(-6 + k * 12, 18 + y), 0.6)
			draw_arc(c + Vector2(0, 30), 9.0, PI + 0.4, TAU - 0.4, 10, INK, 4.0)
		Expr.ORGULHOSO:
			for s in [-1.0, 1.0]:
				var e: Vector2 = le if s < 0.0 else re
				draw_polyline(PackedVector2Array([e + Vector2(-12 * s, -12), e + Vector2(12 * s, 0), e + Vector2(-12 * s, 12)]), INK, 6.0)
			draw_polyline(PackedVector2Array([c + Vector2(-16, 20), c + Vector2(-8, 30), c + Vector2(0, 22), c + Vector2(8, 30), c + Vector2(16, 20)]), INK, 4.0)
		Expr.OCULOS_VITORIA:
			var bar_y := c.y - 16.0
			draw_line(Vector2(c.x - 74, bar_y), Vector2(c.x + 74, bar_y), INK, 6.0)
			for e in [le, re]:
				var g := Rect2(e.x - 30, bar_y, 60, 30)
				draw_rect(g, INK)
				draw_rect(g.grow(-5), Color(0.1, 0.12, 0.2))
				var sx := fmod(_t * 60.0, 90.0) - 20.0
				if sx > -5.0 and sx < 55.0:
					draw_line(Vector2(g.position.x + clampf(sx, 5, 55), g.position.y + 6), Vector2(g.position.x + clampf(sx - 10, 5, 55), g.end.y - 6), INK_SOFT, 4.0)
			draw_arc(c + Vector2(0, 22), 14.0, 0.25, PI - 0.25, 12, INK, 4.0)


func _pill(center: Vector2, sz: Vector2) -> void:
	var r := minf(sz.x, sz.y) / 2.0
	if sz.y > sz.x:
		draw_rect(Rect2(center - Vector2(sz.x / 2.0, sz.y / 2.0 - r), Vector2(sz.x, sz.y - 2.0 * r)), INK)
		draw_circle(center - Vector2(0, sz.y / 2.0 - r), r, INK)
		draw_circle(center + Vector2(0, sz.y / 2.0 - r), r, INK)
	else:
		draw_rect(Rect2(center - Vector2(sz.x / 2.0 - r, sz.y / 2.0), Vector2(sz.x - 2.0 * r, sz.y)), INK)
		draw_circle(center - Vector2(sz.x / 2.0 - r, 0), r, INK)
		draw_circle(center + Vector2(sz.x / 2.0 - r, 0), r, INK)


func _drop(p: Vector2, s: float) -> void:
	draw_circle(p, 5.0 * s, INK)
	draw_colored_polygon(PackedVector2Array([p + Vector2(-5 * s, 0), p + Vector2(5 * s, 0), p + Vector2(0, -12 * s)]), INK)


func _spiral(center: Vector2, rot: float) -> void:
	var pts := PackedVector2Array()
	for i in 34:
		var a := i * 0.42 + rot
		pts.append(center + Vector2.from_angle(a) * (2.0 + i * 0.5))
	draw_polyline(pts, INK, 3.5)


func _round_rect(r: Rect2, rad: float, col: Color) -> void:
	draw_rect(Rect2(r.position + Vector2(rad, 0), Vector2(r.size.x - 2 * rad, r.size.y)), col)
	draw_rect(Rect2(r.position + Vector2(0, rad), Vector2(r.size.x, r.size.y - 2 * rad)), col)
	for p in [r.position + Vector2(rad, rad), Vector2(r.end.x - rad, r.position.y + rad), Vector2(r.position.x + rad, r.end.y - rad), r.end - Vector2(rad, rad)]:
		draw_circle(p, rad, col)
