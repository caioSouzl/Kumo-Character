extends Node2D
## Fundo fixo 2.5D: parede, cardapio, janela e piso em perspectiva.


func _draw() -> void:
	var w := 1080.0
	draw_rect(Rect2(0, 0, w, 1920), Color("#2b2140"))
	# parede
	draw_rect(Rect2(0, 230, w, 530), Color("#ffd8a8"))
	for i in 12:
		draw_rect(Rect2(i * 90, 230, 45, 530), Color("#ffcf96"))
	draw_rect(Rect2(0, 700, w, 60), Color("#c97b4a"))
	# placa
	var sign_rect := Rect2(190, 270, 700, 120)
	draw_rect(sign_rect.grow(8.0), Art.OUTLINE)
	draw_rect(sign_rect, Color("#d94a3d"))
	Art.text(self, sign_rect.get_center(), "PIZZARIA DO KUMO", 64, Color.WHITE)
	# janela
	var win := Rect2(80, 430, 220, 200)
	draw_rect(win.grow(8.0), Art.OUTLINE)
	draw_rect(win, Color("#9fd8f5"))
	draw_line(Vector2(190, 430), Vector2(190, 630), Art.OUTLINE, 6.0)
	draw_line(Vector2(80, 530), Vector2(300, 530), Art.OUTLINE, 6.0)
	# cardapio
	var menu := Rect2(860, 430, 160, 220)
	draw_rect(menu.grow(6.0), Art.OUTLINE)
	draw_rect(menu, Color("#3d3350"))
	Art.text(self, Vector2(940, 465), "MENU", 30, Color("#f3c74f"))
	for i in 3:
		Art.pizza(self, Vector2(900, 520 + i * 45), 15.0)
		draw_line(Vector2(925, 520 + i * 45), Vector2(995, 520 + i * 45), Color.WHITE, 4.0)
	# piso em perspectiva
	var top_l := Vector2(60, 760)
	var top_r := Vector2(1020, 760)
	var bot_l := Vector2(-200, 1720)
	var bot_r := Vector2(1280, 1720)
	draw_colored_polygon(PackedVector2Array([top_l, top_r, bot_r, bot_l]), Color("#f6efe1"))
	var rows := 9
	for r in rows:
		var t0 := float(r) / rows
		var t1 := float(r + 1) / rows
		var l0 := top_l.lerp(bot_l, t0)
		var r0 := top_r.lerp(bot_r, t0)
		var l1 := top_l.lerp(bot_l, t1)
		var r1 := top_r.lerp(bot_r, t1)
		var cols := 10
		for c in cols:
			if (r + c) % 2 == 0:
				continue
			var a := float(c) / cols
			var b := float(c + 1) / cols
			draw_colored_polygon(PackedVector2Array([l0.lerp(r0, a), l0.lerp(r0, b), l1.lerp(r1, b), l1.lerp(r1, a)]), Color("#e7dcc5"))
	# porta de entrada (esquerda) e saida (direita)
	draw_rect(Rect2(0, 1450, 26, 270), Color("#7a4a26"))
	draw_rect(Rect2(1054, 1450, 26, 270), Color("#7a4a26"))
	# faixa inferior (fila de presentes)
	draw_rect(Rect2(0, 1720, w, 200), Color("#2b2140"))
