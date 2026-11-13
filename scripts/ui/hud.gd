class_name Hud
extends CanvasLayer
## Cronometro, caixa, estatisticas do expediente, faixa da fila de presentes
## e o painel de resultados do intervalo.

var _timer: Label
var _shift: Label
var _money: Label
var _stats: Label
var _now: Label
var _next: Label
var _status: Label
var _results: PanelContainer
var _results_text: Label
var _results_title: Label


func _ready() -> void:
	layer = 5
	_timer = _label(96, Vector2(0, 30), 1080, HORIZONTAL_ALIGNMENT_CENTER)
	_shift = _label(34, Vector2(40, 40), 400, HORIZONTAL_ALIGNMENT_LEFT)
	_money = _label(40, Vector2(640, 36), 400, HORIZONTAL_ALIGNMENT_RIGHT)
	_stats = _label(32, Vector2(0, 160), 1080, HORIZONTAL_ALIGNMENT_CENTER)
	_now = _label(36, Vector2(30, 1740), 1020, HORIZONTAL_ALIGNMENT_LEFT)
	_next = _label(28, Vector2(30, 1800), 1020, HORIZONTAL_ALIGNMENT_LEFT)
	_status = _label(24, Vector2(30, 1870), 1020, HORIZONTAL_ALIGNMENT_LEFT)
	_now.text = "Mande um presente para mexer na pizzaria!"
	_build_results()
	EventQueue.queue_changed.connect(_refresh_queue)
	LiveConnector.status_changed.connect(func(t: String) -> void: _status.text = t)
	if not LiveConnector.is_enabled():
		_status.text = "Modo simulador (live desligada em config/game.json)"


func _label(size: int, pos: Vector2, width: float, align: HorizontalAlignment) -> Label:
	var l := Label.new()
	var ls := LabelSettings.new()
	ls.font_size = size
	ls.font_color = Color.WHITE
	ls.outline_size = maxi(size / 6, 4)
	ls.outline_color = Color("#2b2140")
	l.label_settings = ls
	l.position = pos
	l.size = Vector2(width, size * 1.4)
	l.horizontal_alignment = align
	l.clip_text = true
	add_child(l)
	return l


func _build_results() -> void:
	_results = PanelContainer.new()
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color("#fff8ec")
	sb.border_color = Color("#2b2140")
	sb.set_border_width_all(8)
	sb.set_corner_radius_all(28)
	sb.set_content_margin_all(40)
	_results.add_theme_stylebox_override("panel", sb)
	_results.position = Vector2(110, 560)
	_results.size = Vector2(860, 700)
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 18)
	_results.add_child(box)
	_results_title = Label.new()
	var ts := LabelSettings.new()
	ts.font_size = 56
	ts.font_color = Color("#d94a3d")
	_results_title.label_settings = ts
	_results_title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	box.add_child(_results_title)
	_results_text = Label.new()
	var bs := LabelSettings.new()
	bs.font_size = 40
	bs.font_color = Color("#2b2140")
	bs.line_spacing = 10
	_results_text.label_settings = bs
	box.add_child(_results_text)
	_results.visible = false
	add_child(_results)


func update_play(time_left: float, shift_no: int, balance: int, s: Dictionary, on_break: bool) -> void:
	var secs := maxi(int(ceil(time_left)), 0)
	_timer.text = "%02d:%02d" % [secs / 60, secs % 60]
	_shift.text = ("Intervalo" if on_break else "Expediente %d" % shift_no)
	_money.text = "Caixa: $%d" % balance
	_stats.text = "Atendidos %d   Perdidos %d   Gorjetas $%d" % [s["served"], s["lost"], s["tips"]]


func show_results(shift_no: int, s: Dictionary, balance: int, next_in: float) -> void:
	_results.visible = true
	_results_title.text = "Fim do expediente %d" % shift_no
	_results_text.text = "\n".join([
		"Clientes atendidos: %d" % s["served"],
		"Pizzas produzidas: %d" % s["pizzas"],
		"Pedidos perdidos: %d" % s["lost"],
		"Pizzas roubadas: %d" % s["stolen"],
		"Vendas: $%d" % s["sales"],
		"Gorjetas: $%d" % s["tips"],
		"Saldo acumulado: $%d" % balance,
		"",
		"Novo expediente em %ds" % int(ceil(next_in)),
	])


func hide_results() -> void:
	_results.visible = false


func show_event(text: String) -> void:
	_now.text = "Agora: " + text


func _refresh_queue() -> void:
	var names: Array[String] = []
	for ev in EventQueue.pending():
		var def: Dictionary = ev["def"]
		var n := String(def.get("label", ev["gift_id"]))
		if int(ev["count"]) > 1:
			n += " x%d" % int(ev["count"])
		names.append(n)
	if names.is_empty():
		_next.text = "Fila: vazia"
	else:
		_next.text = "Fila: " + ", ".join(names.slice(0, 6)) + ("..." if names.size() > 6 else "")
