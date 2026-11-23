class_name Hud
extends CanvasLayer
## Interface da live (1080 x 1920):
## - topo: projeto atual do ZodIA com barra de progresso, e a bateria;
## - avisos de eventos (estilo ZodIA ou Kumo);
## - quadros de agradecimento por presente (dois estilos);
## - ranking dos melhores presenteadores (estilo misto);
## - painel holografico que se quebra quando o projeto cai.

const TEXT := Color(0.95, 0.93, 1.0)
const ZODIA_TEXT := Color(1.0, 0.35, 0.85)
const KUMO_TEXT := Color(0.35, 0.5, 0.25)
const MAX_CARDS := 3

var _project: ProjectPanel
var _battery: BatteryWidget
var _notice: NoticePanel
var _board: Leaderboard
var _shatter: ShatterPanel
var _cards: Array[ThanksCard] = []
var _now: Label
var _next: Label
var _status: Label
var _scores: Dictionary = {}


func _ready() -> void:
	layer = 5
	_project = ProjectPanel.new()
	_project.position = Vector2(24, 36)
	add_child(_project)
	_battery = BatteryWidget.new()
	_battery.position = Vector2(770, 40)
	add_child(_battery)
	_notice = NoticePanel.new()
	_notice.position = Vector2(110, 250)
	add_child(_notice)
	_board = Leaderboard.new()
	_board.position = Vector2(712, 1180)
	add_child(_board)
	_shatter = ShatterPanel.new()
	add_child(_shatter)
	_now = make_label(32, Vector2(30, 1790), 1020, HORIZONTAL_ALIGNMENT_LEFT)
	_next = make_label(26, Vector2(30, 1836), 1020, HORIZONTAL_ALIGNMENT_LEFT)
	_status = make_label(22, Vector2(30, 1876), 1020, HORIZONTAL_ALIGNMENT_LEFT)
	add_child(_now)
	add_child(_next)
	add_child(_status)
	_now.text = "Mande um presente para o Kumo aprontar!"
	EventQueue.queue_changed.connect(_refresh_queue)
	LiveConnector.status_changed.connect(func(t: String) -> void: _status.text = t)
	if not LiveConnector.is_enabled():
		_status.text = "Modo simulador (live desligada em config/game.json)"


static func make_label(size: int, pos: Vector2, width: float, align: HorizontalAlignment, color: Color = TEXT, outline: Color = Color(0.08, 0.02, 0.16)) -> Label:
	var l := Label.new()
	var ls := LabelSettings.new()
	ls.font_size = size
	ls.font_color = color
	ls.outline_size = maxi(size / 6, 4)
	ls.outline_color = outline
	l.label_settings = ls
	l.position = pos
	l.size = Vector2(width, size * 1.4)
	l.horizontal_alignment = align
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	return l


# ---------- API usada pelo main ----------

func set_project(pname: String, index: int, total: int, progress: float) -> void:
	_project.title = "Projeto %d/%d · %s" % [index + 1, total, pname]
	_project.progress = progress


func set_battery(pct: float, low_at: float) -> void:
	_battery.pct = pct
	_battery.low_at = low_at


func notice(text: String, style: String, secs: float = 4.0) -> void:
	_notice.push(text, style, secs)


func shatter(text: String) -> void:
	_shatter.trigger(text)


func thanks(gift_id: String, sender: String, count: int) -> void:
	var def: Dictionary = GameConfig.gifts.get(gift_id, {})
	for c in _cards:
		if c.sender == sender and c.gift_id == gift_id and c.life > 0.6:
			c.count += count
			c.life = 5.0
			c.refresh()
			return
	var card := ThanksCard.new()
	card.sender = sender
	card.gift_id = gift_id
	card.count = count
	card.style = String(def.get("style", "zodia"))
	card.plural = String(def.get("plural", def.get("label", gift_id)))
	add_child(card)
	_cards.push_front(card)
	while _cards.size() > MAX_CARDS:
		var old: ThanksCard = _cards.pop_back()
		old.queue_free()
	card.refresh()
	_layout_cards()

	var coins := float(def.get("coins", 1)) * count
	_scores[sender] = float(_scores.get(sender, 0.0)) + coins
	_board.set_scores(_scores, int(GameConfig.value("leaderboard_size", 5)))


func _layout_cards() -> void:
	for i in _cards.size():
		_cards[i].target_y = 1600.0 - i * 150.0


func _process(delta: float) -> void:
	for c in _cards.duplicate():
		c.life -= delta
		if c.life <= 0.0:
			_cards.erase(c)
			c.queue_free()
			_layout_cards()


func _refresh_queue() -> void:
	var cur := EventQueue.current()
	if not cur.is_empty():
		_now.text = "Agora: %s (%s)" % [String(cur["def"].get("label", cur["gift_id"])), ", ".join(cur["senders"])]
	var pend := EventQueue.pending()
	if pend.is_empty():
		_next.text = ""
		return
	var names: Array[String] = []
	for ev in pend.slice(0, 4):
		var lbl := String(ev["def"].get("label", ev["gift_id"]))
		names.append(lbl if int(ev["count"]) <= 1 else "%s x%d" % [lbl, int(ev["count"])])
	_next.text = "Na fila: " + " • ".join(names) + (" …" if pend.size() > 4 else "")


func set_now(text: String) -> void:
	_now.text = text


# ======================================================================

class ProjectPanel extends Control:
	var title := ""
	var progress := 0.0
	var _t := 0.0
	var _label: Label
	var _name: Label

	func _ready() -> void:
		size = Vector2(700, 150)
		_name = Hud.make_label(30, Vector2(30, 18), 400, HORIZONTAL_ALIGNMENT_LEFT, Deco.CYAN)
		_name.text = "ZodIA • assistente de IA"
		add_child(_name)
		_label = Hud.make_label(38, Vector2(30, 56), 640, HORIZONTAL_ALIGNMENT_LEFT)
		add_child(_label)

	func _process(delta: float) -> void:
		_t += delta
		_label.text = title
		queue_redraw()

	func _draw() -> void:
		var r := Rect2(Vector2.ZERO, size)
		draw_rect(r, Color(0.08, 0.02, 0.18, 0.72))
		Deco.cyber_frame(self, r, _t)
		var bar := Rect2(30, 112, 640, 18)
		draw_rect(bar, Color(0.2, 0.1, 0.35))
		draw_rect(Rect2(bar.position, Vector2(bar.size.x * clampf(progress, 0.0, 1.0), bar.size.y)), Color(0.75, 0.4, 1.0))
		draw_rect(bar, Deco.CYAN, false, 2.0)


class BatteryWidget extends Control:
	var pct := 100.0
	var low_at := 25.0
	var _t := 0.0
	var _label: Label
	var _hint: Label

	func _ready() -> void:
		size = Vector2(290, 150)
		_label = Hud.make_label(40, Vector2(0, 14), 150, HORIZONTAL_ALIGNMENT_RIGHT)
		add_child(_label)
		_hint = Hud.make_label(22, Vector2(-60, 100), 350, HORIZONTAL_ALIGNMENT_RIGHT, Color(1.0, 0.75, 0.85))
		_hint.text = "Curta para recarregar!"
		add_child(_hint)

	func _process(delta: float) -> void:
		_t += delta
		_label.text = "%d%%" % roundi(pct)
		_hint.visible = pct < low_at and fmod(_t, 1.2) < 0.85
		queue_redraw()

	func _draw() -> void:
		var r := Rect2(160, 22, 110, 56)
		draw_rect(r, Color(0.08, 0.02, 0.18, 0.8))
		draw_rect(r, Color.WHITE, false, 5.0)
		draw_rect(Rect2(r.end.x + 2, r.position.y + 16, 10, 24), Color.WHITE)
		var col := Color(0.35, 1.0, 0.55)
		if pct < low_at:
			col = Color(1.0, 0.3, 0.4) if fmod(_t, 0.8) < 0.5 else Color(0.6, 0.15, 0.2)
		elif pct < 55.0:
			col = Color(1.0, 0.82, 0.3)
		var inner := r.grow(-9)
		draw_rect(Rect2(inner.position, Vector2(inner.size.x * clampf(pct / 100.0, 0.0, 1.0), inner.size.y)), col)
		# raio
		var c := r.get_center()
		draw_colored_polygon(PackedVector2Array([c + Vector2(4, -20), c + Vector2(-8, 3), c + Vector2(0, 3), c + Vector2(-4, 20), c + Vector2(8, -3), c + Vector2(0, -3)]), Color(1, 1, 1, 0.85))


class NoticePanel extends Control:
	var _queue: Array = []
	var _style := "zodia"
	var _life := 0.0
	var _t := 0.0
	var _label: Label

	func _ready() -> void:
		size = Vector2(860, 240)
		pivot_offset = size / 2.0
		_label = Hud.make_label(44, Vector2(70, 70), 720, HORIZONTAL_ALIGNMENT_CENTER)
		_label.size = Vector2(720, 110)
		_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		add_child(_label)
		modulate.a = 0.0

	func push(text: String, style: String, secs: float) -> void:
		for q in _queue:
			if q[0] == text:
				return
		_queue.append([text, style, secs])

	func _process(delta: float) -> void:
		_t += delta
		if _life > 0.0:
			_life -= delta
			modulate.a = clampf(minf(_life, 0.35) / 0.35, 0.0, 1.0)
			queue_redraw()
			return
		modulate.a = 0.0
		if _queue.is_empty():
			return
		var q: Array = _queue.pop_front()
		_label.text = q[0]
		_style = q[1]
		_life = float(q[2])
		var ls := _label.label_settings
		ls.font_color = Hud.KUMO_TEXT if _style == "kumo" else Color(0.55, 0.25, 0.95)
		ls.outline_color = Color(1, 1, 1, 0.9)
		scale = Vector2(0.6, 0.6)
		create_tween().tween_property(self, "scale", Vector2.ONE, 0.35).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)

	func _draw() -> void:
		var r := Rect2(Vector2(20, 20), size - Vector2(40, 40))
		draw_rect(r, Color(1, 1, 1, 0.93))
		if _style == "kumo":
			Deco.kumo_frame(self, r, _t)
		else:
			Deco.cyber_frame(self, r, _t)


class ThanksCard extends Control:
	var sender := ""
	var gift_id := ""
	var plural := ""
	var count := 1
	var style := "zodia"
	var life := 5.0
	var target_y := 1600.0
	var _t := 0.0
	var _label: Label

	func _ready() -> void:
		size = Vector2(680, 140)
		position = Vector2(-700, target_y)
		_label = Hud.make_label(32, Vector2(130, 14), 500, HORIZONTAL_ALIGNMENT_LEFT)
		_label.size = Vector2(500, 90)
		add_child(_label)

	func refresh() -> void:
		if _label == null:
			return
		_label.text = "Obrigado @%s,\npelas %d %s!" % [sender, count, plural]
		var ls := _label.label_settings
		ls.font_color = Hud.KUMO_TEXT if style == "kumo" else Hud.ZODIA_TEXT
		ls.outline_color = Color(1, 1, 1, 0.95)

	func _process(delta: float) -> void:
		_t += delta
		position.x = lerpf(position.x, 24.0, minf(delta * 8.0, 1.0))
		position.y = lerpf(position.y, target_y, minf(delta * 8.0, 1.0))
		modulate.a = clampf(life / 0.5, 0.0, 1.0)
		queue_redraw()

	func _draw() -> void:
		draw_rect(Rect2(0, 0, 660, 108), Color(1, 1, 1, 0.9))
		var av := Vector2(62, 54)
		var col := Deco.MAGENTA if style == "zodia" else Deco.LEAF
		draw_circle(av, 46.0, col)
		draw_circle(av, 40.0, Color(0.15, 0.08, 0.25))
		var f := ThemeDB.fallback_font
		var ini := sender.substr(0, 1).to_upper() if sender != "" else "?"
		draw_string(f, av + Vector2(-14, 15), ini, HORIZONTAL_ALIGNMENT_LEFT, -1, 44, Color.WHITE)
		Deco.robot_icon(self, Vector2(620, 74), 1.1, col)
		if style == "kumo":
			Deco.vine(self, Vector2(0, 0), Vector2(0, 100), _t, 1.0)
			Deco.vine(self, Vector2(0, 2), Vector2(120, 4), _t, 3.0)
			Deco.flowers_row(self, Vector2(330, 122), 420.0, _t)
		else:
			draw_line(Vector2(170, 4), Vector2(330, 4), Color(Deco.VIOLET, 0.8), 6.0)
			Deco.circuit_row(self, Vector2(330, 122), 420.0, _t)


class Leaderboard extends Control:
	var _rows: Array[Label] = []
	var _t := 0.0

	func _ready() -> void:
		size = Vector2(350, 420)
		var title := Hud.make_label(30, Vector2(20, 22), 310, HORIZONTAL_ALIGNMENT_CENTER, Color(0.95, 0.9, 1.0))
		title.text = "Top presenteadores"
		add_child(title)
		for i in 5:
			var l := Hud.make_label(28, Vector2(30, 82 + i * 58), 300, HORIZONTAL_ALIGNMENT_LEFT)
			add_child(l)
			_rows.append(l)
		visible = false

	func set_scores(scores: Dictionary, n: int) -> void:
		var names := scores.keys()
		names.sort_custom(func(a: Variant, b: Variant) -> bool: return float(scores[a]) > float(scores[b]))
		for i in _rows.size():
			if i < mini(n, names.size()):
				var who := String(names[i])
				if who.length() > 12:
					who = who.substr(0, 11) + "…"
				_rows[i].text = "%d. %s  %d" % [i + 1, who, roundi(float(scores[names[i]]))]
			else:
				_rows[i].text = ""
		visible = not names.is_empty()
		size.y = 96.0 + mini(n, names.size()) * 58.0

	func _process(delta: float) -> void:
		_t += delta
		queue_redraw()

	func _draw() -> void:
		var r := Rect2(Vector2.ZERO, size)
		draw_rect(r, Color(0.08, 0.02, 0.18, 0.7))
		Deco.mixed_frame(self, r, _t)
		var medal := [Color(1.0, 0.82, 0.3), Color(0.85, 0.88, 0.95), Color(0.85, 0.55, 0.3)]
		for i in 3:
			if _rows[i].text != "":
				draw_circle(Vector2(18, 102 + i * 58), 8.0, medal[i])


class ShatterPanel extends Control:
	## Painel holografico roxo que racha e se despedaca.
	var _shards: Array = []
	var _life := 0.0
	var _label: Label

	func _ready() -> void:
		size = Vector2(1080, 1920)
		mouse_filter = Control.MOUSE_FILTER_IGNORE
		_label = Hud.make_label(64, Vector2(140, 880), 800, HORIZONTAL_ALIGNMENT_CENTER, Color(1.0, 0.85, 1.0), Color(0.4, 0.0, 0.5))
		add_child(_label)
		visible = false

	func trigger(text: String) -> void:
		_label.text = text
		_shards.clear()
		var r := Rect2(190, 720, 700, 420)
		var cols := 6
		var rows := 4
		var rng := RandomNumberGenerator.new()
		rng.randomize()
		var c := r.get_center()
		for y in rows:
			for x in cols:
				var p0 := r.position + Vector2(r.size.x * x / cols, r.size.y * y / rows)
				var p1 := p0 + Vector2(r.size.x / cols, r.size.y / rows)
				var tris := [[p0, Vector2(p1.x, p0.y), p1], [p0, p1, Vector2(p0.x, p1.y)]]
				for tri in tris:
					var mid: Vector2 = (tri[0] + tri[1] + tri[2]) / 3.0
					_shards.append({
						"pts": tri, "mid": mid,
						"vel": (mid - c).normalized() * rng.randf_range(250, 700) + Vector2(0, rng.randf_range(-200, 100)),
						"rot": rng.randf_range(-4, 4),
						"col": Color(0.6, 0.3, 1.0, 0.75).lerp(Color(1.0, 0.4, 0.9, 0.75), rng.randf()),
					})
		_life = 0.55
		visible = true

	func _process(delta: float) -> void:
		if _life <= 0.0:
			visible = false
			return
		_life -= delta
		_label.modulate.a = clampf((_life - 0.25) / 0.15, 0.0, 1.0)
		_label.position.x = 140 + sin(_life * 80.0) * 6.0
		queue_redraw()

	func _draw() -> void:
		# rapido: racha (0,15 s), estoura e some em menos de 1 s,
		# para o efeito de quebra no objeto aparecer
		var age := 0.55 - _life
		var burst := maxf(age - 0.1, 0.0) * 3.0
		for s in _shards:
			var off: Vector2 = s["vel"] * burst + Vector2(0, 600.0 * burst * burst)
			var ang: float = s["rot"] * burst
			var mid: Vector2 = s["mid"]
			var pts := PackedVector2Array()
			for p in s["pts"]:
				pts.append(mid + ((p as Vector2) - mid).rotated(ang) * 0.96 + off)
			var col: Color = s["col"]
			col.a *= clampf(_life / 0.35, 0.0, 1.0) * 0.8
			draw_colored_polygon(pts, col)
			draw_polyline(PackedVector2Array([pts[0], pts[1], pts[2], pts[0]]), Color(1, 0.8, 1, col.a), 2.0)
		if age < 0.1:
			# rachaduras antes de quebrar
			var c := Vector2(540, 930)
			for i in 9:
				var a := i * 0.7
				draw_line(c, c + Vector2.from_angle(a) * 330.0 * (age / 0.1), Color(1, 1, 1, 0.9), 3.0)
