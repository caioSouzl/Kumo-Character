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


## Desenhos seguem a folha "Expressoes" do design (tracos claros na tela preta).
func _draw() -> void:
	_round_rect(Rect2(6, 6, W - 12, H - 12), 34.0, SCREEN)
	var c := Vector2(W / 2.0, H / 2.0 + 2.0) + look.clamp(Vector2(-14, -8), Vector2(14, 8))
	var shake := Vector2(sin(_t * 60.0) * 3.0, 0.0) if expr == Expr.ENFURECIDO or expr == Expr.ASSUSTADO else Vector2.ZERO
	c += shake
	var le := c + Vector2(-48, -10)
	var re := c + Vector2(48, -10)
	match expr:
		Expr.NORMAL:
			# olhos ovais altos e boquinha em "v"
			var h := 5.0 if _blink > 0.0 else 40.0
			_oval(le, Vector2(17, h))
			_oval(re, Vector2(17, h))
			draw_polyline(PackedVector2Array([c + Vector2(-9, 26), c + Vector2(0, 33), c + Vector2(9, 26)]), INK, 4.0)
		Expr.CHATEADO:
			# palpebra reta por cima (olho cortado) e boca "^"
			for e in [le, re]:
				_lidded(e, Vector2(19, 40), 0.32)
			draw_polyline(PackedVector2Array([c + Vector2(-10, 32), c + Vector2(0, 23), c + Vector2(10, 32)]), INK, 4.5)
		Expr.INEXPRESSIVO:
			draw_rect(Rect2(le - Vector2(18, 6), Vector2(36, 12)), INK)
			draw_rect(Rect2(re - Vector2(18, 6), Vector2(36, 12)), INK)
			draw_line(c + Vector2(-9, 28), c + Vector2(9, 28), INK, 4.0)
		Expr.DESCONFIADO:
			# esquerdo meio fechado com traco em cima; direito aberto com sobrancelha "^"
			draw_line(le + Vector2(-14, -16), le + Vector2(14, -16), INK, 5.0)
			_lidded(le + Vector2(0, 2), Vector2(17, 34), 0.36)
			_oval(re, Vector2(16, 38))
			draw_polyline(PackedVector2Array([re + Vector2(-11, -26), re + Vector2(0, -36), re + Vector2(11, -26)]), INK, 4.5)
			draw_line(c + Vector2(14, 34), c + Vector2(26, 26), INK, 4.5)
		Expr.ASSUSTADO:
			# olhos de alvo com marquinhas, boca "o" e linhas de suor
			for e in [le, re]:
				draw_arc(e, 18.0, 0.0, TAU, 24, INK, 3.5)
				draw_circle(e, 9.0, INK)
				for k in 3:
					var ang := -2.4 + k * 0.5
					draw_line(e + Vector2.from_angle(ang) * 22.0, e + Vector2.from_angle(ang) * 27.0, INK, 3.0)
			draw_circle(c + Vector2(-2, 32), 7.0, INK)
			for k in 3:
				draw_line(re + Vector2(26 + k * 7, -30), re + Vector2(24 + k * 7, -16), INK, 3.0)
		Expr.ALIVIADO:
			draw_arc(le + Vector2(0, 6), 14.0, PI + 0.2, TAU - 0.2, 10, INK, 6.0)
			draw_arc(re + Vector2(0, 6), 14.0, PI + 0.2, TAU - 0.2, 10, INK, 6.0)
			draw_arc(c + Vector2(0, 18), 13.0, 0.3, PI - 0.3, 12, INK, 4.0)
			_drop(re + Vector2(36, -12 + fmod(_t * 18.0, 14.0)), 0.8)
		Expr.CONFUSO:
			_spiral(le, _t * 5.0)
			_spiral(re, -_t * 5.0)
			draw_circle(c + Vector2(-2, 32), 6.0, INK)
		Expr.BATERIA_FRACA:
			# bateria grande com um so tracinho piscando
			var r := Rect2(c.x - 62, c.y - 30, 112, 58)
			_round_rect_line(r, 10.0, 6.0)
			draw_rect(Rect2(r.end.x + 4, c.y - 12, 10, 22), INK)
			if fmod(_t, 1.0) < 0.6:
				draw_rect(Rect2(r.position + Vector2(10, 10), Vector2(16, r.size.y - 20)), RED)
		Expr.SEM_BATERIA:
			for e in [le, re]:
				draw_line(e + Vector2(-18, -18), e + Vector2(18, 18), INK, 5.0)
				draw_line(e + Vector2(-18, 18), e + Vector2(18, -18), INK, 5.0)
		Expr.ENFURECIDO:
			# olhos em ponta, bravos, e boca de dentes em zigue-zague
			draw_colored_polygon(PackedVector2Array([le + Vector2(-24, -14), le + Vector2(20, 4), le + Vector2(6, 16), le + Vector2(-18, 10)]), INK)
			draw_colored_polygon(PackedVector2Array([re + Vector2(24, -14), re + Vector2(-20, 4), re + Vector2(-6, 16), re + Vector2(18, 10)]), INK)
			var m := Rect2(c + Vector2(-14, 18), Vector2(28, 26))
			draw_rect(m, INK)
			var teeth := PackedVector2Array()
			for i in 5:
				teeth.append(m.position + Vector2(i * 7.0, 13.0 + (-5.0 if i % 2 == 0 else 5.0)))
			draw_polyline(teeth, SCREEN, 3.0)
			draw_line(m.position + Vector2(9, 0), m.position + Vector2(9, 26), SCREEN, 2.0)
			draw_line(m.position + Vector2(19, 0), m.position + Vector2(19, 26), SCREEN, 2.0)
		Expr.CHORAMINGANDO:
			# olhos grandes brilhando e cascatas de lagrimas
			for e in [le, re]:
				draw_arc(e + Vector2(0, -6), 18.0, 0.0, TAU, 24, INK, 3.5)
				draw_circle(e + Vector2(-5, -11), 6.0, INK)
				draw_circle(e + Vector2(6, -2), 3.0, INK)
				for k in 3:
					var pts := PackedVector2Array()
					for j in 8:
						var y := 14.0 + j * 4.5
						pts.append(e + Vector2(-10 + k * 10 + sin(j * 1.4 + _t * 8.0 + k) * 2.5, y))
					draw_polyline(pts, INK, 2.5)
			draw_circle(c + Vector2(0, 34), 3.5, INK)
		Expr.ORGULHOSO:
			# ">  <" e boca de gatinho
			draw_polyline(PackedVector2Array([le + Vector2(-14, -14), le + Vector2(12, 0), le + Vector2(-14, 14)]), INK, 5.5)
			draw_polyline(PackedVector2Array([re + Vector2(14, -14), re + Vector2(-12, 0), re + Vector2(14, 14)]), INK, 5.5)
			draw_arc(c + Vector2(-8, 26), 8.0, 0.0, PI, 10, INK, 4.0)
			draw_arc(c + Vector2(8, 26), 8.0, 0.0, PI, 10, INK, 4.0)
		Expr.OCULOS_VITORIA:
			# oculos escuros com brilho e sorriso
			var y0 := c.y - 26.0
			draw_rect(Rect2(c.x - 78, y0, 156, 10), INK)
			for sx in [-1.0, 1.0]:
				var lens: PackedVector2Array = PackedVector2Array([Vector2(c.x + sx * 8, y0 + 6), Vector2(c.x + sx * 72, y0 + 6), Vector2(c.x + sx * 66, y0 + 36), Vector2(c.x + sx * 14, y0 + 36)])
				draw_colored_polygon(lens, INK)
				var inner := PackedVector2Array()
				for v in lens:
					inner.append(v.lerp(Vector2(c.x + sx * 40, y0 + 20), 0.18))
				draw_colored_polygon(inner, Color(0.06, 0.08, 0.16))
				var gx: float = c.x + sx * 40 + fmod(_t * 50.0, 60.0) - 30.0
				draw_line(Vector2(gx - 4, y0 + 30), Vector2(gx + 6, y0 + 12), INK_SOFT, 3.0)
				draw_line(Vector2(gx + 4, y0 + 30), Vector2(gx + 14, y0 + 12), INK_SOFT, 3.0)
			draw_arc(c + Vector2(0, 26), 9.0, 0.2, PI - 0.2, 12, INK, 4.0)


func _oval(center: Vector2, sz: Vector2) -> void:
	var pts := PackedVector2Array()
	for i in 24:
		var a := TAU * i / 24.0
		pts.append(center + Vector2(cos(a) * sz.x / 2.0, sin(a) * sz.y / 2.0))
	draw_colored_polygon(pts, INK)


## Oval com a parte de cima cortada reta (palpebra baixa).
func _lidded(center: Vector2, sz: Vector2, cut: float) -> void:
	var top := center.y - sz.y / 2.0 + sz.y * cut
	var pts := PackedVector2Array()
	for i in 25:
		var a := PI * i / 24.0
		pts.append(center + Vector2(cos(a) * sz.x / 2.0, sin(a) * sz.y / 2.0))
	var y0 := center.y + 0.0
	pts.append(Vector2(center.x - sz.x / 2.0, top))
	pts.append(Vector2(center.x + sz.x / 2.0, top))
	if top >= y0:
		pts = PackedVector2Array([Vector2(center.x - sz.x / 2.0, top), Vector2(center.x + sz.x / 2.0, top), center + Vector2(0, sz.y / 2.0)])
	draw_colored_polygon(pts, INK)


func _round_rect_line(r: Rect2, rad: float, w: float) -> void:
	draw_rect(r, INK, false, w)


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
