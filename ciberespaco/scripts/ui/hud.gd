class_name Hud
extends CanvasLayer
## Interface da live (1080 x 1920), em dois estilos desenhados para o jogo:
## - ZodIA: painel escuro com cantos chanfrados, borda neon magenta/ciano,
##   trilhas de circuito, varredura de holograma; aparece piscando em neon ou
##   em glitch.
## - Kumo: painel creme com borda de madeira, cipo, folhas, flores e pedrinhas;
##   aparece brotando e as folhas balancam.
## - Ranking: mistura os dois.
## Fontes: Orbitron (ZodIA) e Baloo 2 (Kumo), ambas OFL (assets/fonts).

const TEXT := Color(0.96, 0.94, 1.0)
const MAGENTA := Color(1.0, 0.24, 0.85)
const CYAN := Color(0.37, 0.9, 1.0)
const VIOLET_BG := Color(0.07, 0.02, 0.17, 0.86)
const CREAM := Color(0.99, 0.96, 0.86)
const WOOD := Color(0.54, 0.35, 0.2)
const KUMO_TEXT := Color(0.24, 0.42, 0.16)
const KUMO_TEXT_SOFT := Color(0.45, 0.33, 0.2)
const MAX_CARDS := 3
const UI := "res://assets/ui/"

static var _zf: Font
static var _zf_light: Font
static var _kf: Font

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
	_project.position = Vector2(24, 28)
	add_child(_project)
	_battery = BatteryWidget.new()
	_battery.position = Vector2(752, 28)
	add_child(_battery)
	_notice = NoticePanel.new()
	_notice.position = Vector2(110, 240)
	add_child(_notice)
	_board = Leaderboard.new()
	_board.position = Vector2(696, 1130)
	add_child(_board)
	_shatter = ShatterPanel.new()
	add_child(_shatter)
	_now = label("", 30, kfont(), TEXT, Color(0.08, 0.02, 0.16))
	_now.position = Vector2(30, 1792)
	_now.size = Vector2(1020, 40)
	_next = label("", 24, kfont(), Color(0.85, 0.82, 0.95), Color(0.08, 0.02, 0.16))
	_next.position = Vector2(30, 1834)
	_next.size = Vector2(1020, 34)
	_status = label("", 18, zfont(true), Color(0.7, 0.68, 0.85), Color(0.08, 0.02, 0.16))
	_status.position = Vector2(30, 1878)
	_status.size = Vector2(1020, 26)
	add_child(_now)
	add_child(_next)
	add_child(_status)
	_now.text = "Mande um presente para o Kumo aprontar!"
	EventQueue.queue_changed.connect(_refresh_queue)
	LiveConnector.status_changed.connect(func(t: String) -> void: _status.text = t)
	if not LiveConnector.is_enabled():
		_status.text = "MODO SIMULADOR · live desligada em config/game.json"


# ---------- fontes, caixas e texturas ----------

static func _font(path: String, weight: int) -> Font:
	var fv := FontVariation.new()
	fv.base_font = load(path)
	var ts := TextServerManager.get_primary_interface()
	fv.variation_opentype = {ts.name_to_tag("wght"): weight}
	return fv


static func zfont(light: bool = false) -> Font:
	if _zf == null:
		_zf = _font("res://assets/fonts/Orbitron.ttf", 800)
		_zf_light = _font("res://assets/fonts/Orbitron.ttf", 500)
	return _zf_light if light else _zf


static func kfont() -> Font:
	if _kf == null:
		_kf = _font("res://assets/fonts/Baloo2.ttf", 800)
	return _kf


static func label(text: String, size: int, font: Font, color: Color, outline: Color = Color(0, 0, 0, 0), outline_px: int = -1) -> Label:
	var l := Label.new()
	var ls := LabelSettings.new()
	ls.font = font
	ls.font_size = size
	ls.font_color = color
	ls.outline_size = outline_px if outline_px >= 0 else (maxi(int(size / 7.0), 3) if outline.a > 0.0 else 0)
	ls.outline_color = outline
	l.label_settings = ls
	l.text = text
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return l


static func tex(file: String) -> Texture2D:
	var p := UI + file
	return load(p) if ResourceLoader.exists(p) else null


static func sprite(file: String, sz: Vector2, pos: Vector2, rot_deg: float = 0.0, flip := Vector2.ONE) -> TextureRect:
	var r := TextureRect.new()
	r.texture = tex(file)
	r.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	r.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	r.size = sz
	r.pivot_offset = sz / 2.0
	r.position = pos - sz / 2.0
	r.rotation_degrees = rot_deg
	r.scale = flip
	r.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return r


## Painel do ZodIA: cantos chanfrados (corner_detail 1), borda neon e brilho
## em volta (sombra colorida = glow externo).
static func zodia_box(border: Color = MAGENTA, glow: float = 0.55) -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = VIOLET_BG
	sb.set_border_width_all(4)
	sb.border_color = border
	sb.set_corner_radius_all(0)
	sb.corner_radius_top_left = 26
	sb.corner_radius_bottom_right = 26
	sb.corner_radius_top_right = 8
	sb.corner_radius_bottom_left = 8
	sb.corner_detail = 1
	sb.shadow_color = Color(border.r, border.g, border.b, glow)
	sb.shadow_size = 16
	sb.anti_aliasing = true
	return sb


static func zodia_inner() -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.draw_center = false
	sb.set_border_width_all(2)
	sb.border_color = Color(CYAN, 0.55)
	sb.corner_radius_top_left = 20
	sb.corner_radius_bottom_right = 20
	sb.corner_radius_top_right = 4
	sb.corner_radius_bottom_left = 4
	sb.corner_detail = 1
	return sb


## Painel do Kumo: creme arredondado com borda de madeira e sombra macia.
static func kumo_box() -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = CREAM
	sb.set_border_width_all(6)
	sb.border_color = WOOD
	sb.set_corner_radius_all(30)
	sb.corner_detail = 10
	sb.shadow_color = Color(0.1, 0.05, 0.0, 0.35)
	sb.shadow_size = 10
	sb.shadow_offset = Vector2(0, 6)
	return sb


# ---------- API usada pelo main ----------

func set_project(pname: String, index: int, total: int, progress: float) -> void:
	_project.set_data(pname, index, total, progress)


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
			c.bump()
			return
	var card := ThanksCard.new()
	card.sender = sender
	card.gift_id = gift_id
	card.count = count
	card.style = String(def.get("style", "zodia"))
	card.plural = String(def.get("plural", def.get("label", gift_id)))
	card.one = String(def.get("thanks_one", "pelo %s" % String(def.get("label", gift_id))))
	add_child(card)
	_cards.push_front(card)
	while _cards.size() > MAX_CARDS:
		var old: ThanksCard = _cards.pop_back()
		old.leave()
	_layout_cards()

	var coins := float(def.get("coins", 1)) * count
	_scores[sender] = float(_scores.get(sender, 0.0)) + coins
	_board.set_scores(_scores, int(GameConfig.value("leaderboard_size", 5)))


func _layout_cards() -> void:
	for i in _cards.size():
		_cards[i].target_y = 1610.0 - i * 158.0


func _process(delta: float) -> void:
	for c in _cards.duplicate():
		c.life -= delta
		if c.life <= 0.0:
			_cards.erase(c)
			c.leave()
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
## Moldura base. style = "zodia" | "kumo" | "misto".

class Frame extends Control:
	var style := "zodia"
	var content: Control
	var _mat: ShaderMaterial
	var _glitch := 0.0
	var _t := 0.0
	var _next_glitch := 4.0
	var _deco: Array[Control] = []
	var _deco_rot: Array[float] = []

	func build(sz: Vector2, st: String) -> void:
		size = sz
		style = st
		pivot_offset = sz / 2.0
		mouse_filter = Control.MOUSE_FILTER_IGNORE
		var bg := Panel.new()
		bg.size = sz
		bg.mouse_filter = Control.MOUSE_FILTER_IGNORE
		bg.add_theme_stylebox_override("panel", Hud.kumo_box() if st == "kumo" else Hud.zodia_box())
		add_child(bg)
		if st != "kumo":
			var inner := Panel.new()
			inner.position = Vector2(10, 10)
			inner.size = sz - Vector2(20, 20)
			inner.mouse_filter = Control.MOUSE_FILTER_IGNORE
			inner.add_theme_stylebox_override("panel", Hud.zodia_inner())
			add_child(inner)
			_add_deco(Hud.sprite("circuit_corner.svg", Vector2(96, 96), Vector2(44, 44)))
			if st == "zodia":
				_add_deco(Hud.sprite("circuit_corner.svg", Vector2(96, 96), sz - Vector2(44, 44), 0.0, Vector2(-1, -1)))
		content = Control.new()
		content.size = sz
		content.mouse_filter = Control.MOUSE_FILTER_IGNORE
		add_child(content)
		if st == "kumo":
			_kumo_deco(sz)
		elif st == "misto":
			for i in 4:
				_add_deco(Hud.sprite("leaf.svg", Vector2(40, 66), sz - Vector2(30 + i * 26, 22 + (i % 2) * 10), -30.0 + i * 22.0))
			_add_deco(Hud.sprite("flower.svg", Vector2(38, 38), sz - Vector2(116, 30)))
		if st != "kumo":
			var bb := BackBufferCopy.new()
			bb.copy_mode = BackBufferCopy.COPY_MODE_VIEWPORT
			add_child(bb)
			var ov := ColorRect.new()
			ov.size = sz
			ov.mouse_filter = Control.MOUSE_FILTER_IGNORE
			_mat = ShaderMaterial.new()
			_mat.shader = load("res://shaders/hud_glitch.gdshader")
			_mat.set_shader_parameter("scan", 0.45)
			ov.material = _mat
			add_child(ov)

	func _kumo_deco(sz: Vector2) -> void:
		var vine := Hud.sprite("vine.svg", Vector2(sz.x - 60, 34), Vector2(sz.x / 2.0, 2))
		vine.stretch_mode = TextureRect.STRETCH_SCALE
		_add_deco(vine)
		_add_deco(Hud.sprite("leaf.svg", Vector2(46, 76), Vector2(18, 20), -55.0))
		_add_deco(Hud.sprite("leaf.svg", Vector2(40, 66), Vector2(50, -6), -10.0))
		_add_deco(Hud.sprite("leaf.svg", Vector2(36, 60), Vector2(-6, 50), -100.0))
		_add_deco(Hud.sprite("flower.svg", Vector2(40, 40), Vector2(34, 18)))
		_add_deco(Hud.sprite("leaf.svg", Vector2(38, 62), Vector2(sz.x - 20, 14), 50.0))
		_add_deco(Hud.sprite("flower_yellow.svg", Vector2(34, 34), Vector2(sz.x - 44, 8)))
		for i in 3:
			_add_deco(Hud.sprite("leaf.svg", Vector2(30, 50), Vector2(sz.x * (0.3 + i * 0.2), 0), (-1.0 if i % 2 else 1.0) * 70.0))
		_add_deco(Hud.sprite("pebbles.svg", Vector2(92, 42), Vector2(40, sz.y - 6)))
		_add_deco(Hud.sprite("leaf.svg", Vector2(34, 56), Vector2(sz.x - 16, sz.y - 22), 140.0))

	func _add_deco(c: Control) -> void:
		add_child(c)
		_deco.append(c)
		_deco_rot.append(c.rotation)

	## Entrada: ZodIA pisca em neon ou entra em glitch; Kumo brota.
	func appear() -> void:
		visible = true
		var tw := create_tween()
		if style == "kumo":
			scale = Vector2(0.5, 0.5)
			modulate.a = 0.0
			tw.set_parallel(true)
			tw.tween_property(self, "scale", Vector2.ONE, 0.45).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
			tw.tween_property(self, "modulate:a", 1.0, 0.18)
			for i in _deco.size():
				var d := _deco[i]
				var s := d.scale
				d.scale = Vector2.ZERO
				tw.tween_property(d, "scale", s, 0.35).set_delay(0.15 + i * 0.04).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
		elif randf() < 0.5:
			# piscadelas de neon
			scale = Vector2.ONE
			modulate.a = 0.0
			for a in [1.0, 0.1, 0.9, 0.0, 1.0, 0.35, 1.0]:
				tw.tween_property(self, "modulate:a", a, 0.05)
		else:
			# glitch
			scale = Vector2.ONE
			modulate.a = 1.0
			_glitch = 1.0
			tw.tween_interval(0.01)

	func leave() -> void:
		var tw := create_tween()
		if style == "kumo":
			tw.set_parallel(true)
			tw.tween_property(self, "scale", Vector2(0.6, 0.6), 0.25).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_IN)
			tw.tween_property(self, "modulate:a", 0.0, 0.25)
		else:
			_glitch = 1.0
			for a in [0.6, 1.0, 0.0]:
				tw.tween_property(self, "modulate:a", a, 0.06)
		tw.chain().tween_callback(queue_free)

	func bump() -> void:
		var tw := create_tween()
		tw.tween_property(self, "scale", Vector2(1.06, 1.06), 0.08)
		tw.tween_property(self, "scale", Vector2.ONE, 0.15)
		if style != "kumo":
			_glitch = maxf(_glitch, 0.5)

	func _process(delta: float) -> void:
		_t += delta
		if _mat:
			_next_glitch -= delta
			if _next_glitch <= 0.0:
				_next_glitch = randf_range(3.0, 7.0)
				_glitch = maxf(_glitch, 0.45)
			_glitch = maxf(_glitch - delta * 2.6, 0.0)
			_mat.set_shader_parameter("glitch", _glitch)
		elif style == "kumo":
			for i in _deco.size():
				_deco[i].rotation = _deco_rot[i] + sin(_t * 1.7 + i * 0.9) * 0.06


# ======================================================================

class ProjectPanel extends Control:
	var _frame: Frame
	var _tag: Label
	var _name: Label
	var _bar: NeonBar
	var _pct: Label
	var _last := ""

	func _ready() -> void:
		_frame = Frame.new()
		add_child(_frame)
		_frame.build(Vector2(720, 168), "zodia")
		var c := _frame.content
		_tag = Hud.label("ZODIA // PROJETO", 20, Hud.zfont(true), Hud.CYAN)
		_tag.position = Vector2(96, 18)
		_tag.size = Vector2(560, 30)
		c.add_child(_tag)
		_name = Hud.label("", 40, Hud.zfont(), Hud.TEXT, Color(0.5, 0.05, 0.45, 0.8), 6)
		_name.position = Vector2(96, 46)
		_name.size = Vector2(600, 56)
		_name.autowrap_mode = TextServer.AUTOWRAP_OFF
		_name.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
		c.add_child(_name)
		_bar = NeonBar.new()
		_bar.position = Vector2(36, 116)
		_bar.size = Vector2(540, 26)
		c.add_child(_bar)
		_pct = Hud.label("0%", 26, Hud.zfont(), Hud.CYAN)
		_pct.position = Vector2(590, 108)
		_pct.size = Vector2(100, 36)
		_pct.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
		c.add_child(_pct)
		var robot := Hud.sprite("robot.svg", Vector2(58, 58), Vector2(52, 66))
		c.add_child(robot)
		_frame.appear()

	func set_data(pname: String, index: int, total: int, progress: float) -> void:
		_tag.text = "ZODIA // PROJETO %d/%d" % [index + 1, total]
		if pname != _last:
			_last = pname
			_name.text = pname.to_upper()
			_frame.bump()
		_bar.value = progress
		_pct.text = "%d%%" % floori(progress * 100.0)


## Barra em segmentos neon, com o segmento da ponta piscando.
class NeonBar extends Control:
	var value := 0.0
	var color := Hud.MAGENTA
	var _t := 0.0

	func _process(delta: float) -> void:
		_t += delta
		queue_redraw()

	func _draw() -> void:
		var n := 24
		var gap := 4.0
		var w := (size.x - gap * (n - 1)) / n
		var filled := value * n
		for i in n:
			var r := Rect2(i * (w + gap), 0, w, size.y)
			var pts := PackedVector2Array([r.position + Vector2(6, 0), Vector2(r.end.x, r.position.y), r.end - Vector2(6, 0), Vector2(r.position.x, r.end.y)])
			var on := float(i) < filled
			var col := Color(0.25, 0.12, 0.4, 0.9)
			if on:
				col = color.lerp(Hud.CYAN, float(i) / n)
				if i == int(filled) - 1 or (i == int(filled) and filled < n):
					col.a = 0.55 + 0.45 * sin(_t * 9.0)
			draw_colored_polygon(pts, col)


class BatteryWidget extends Control:
	var pct := 100.0
	var low_at := 25.0
	var _frame: Frame
	var _cells: BatteryCells
	var _label: Label
	var _hint: Label
	var _t := 0.0
	var _was_low := false

	func _ready() -> void:
		_frame = Frame.new()
		add_child(_frame)
		_frame.build(Vector2(304, 124), "zodia")
		var c := _frame.content
		c.add_child(Hud.sprite("bolt.svg", Vector2(40, 60), Vector2(44, 62)))
		_cells = BatteryCells.new()
		_cells.position = Vector2(76, 36)
		_cells.size = Vector2(104, 50)
		c.add_child(_cells)
		_label = Hud.label("100%", 24, Hud.zfont(), Hud.TEXT)
		_label.position = Vector2(186, 42)
		_label.size = Vector2(100, 36)
		_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		c.add_child(_label)
		_hint = Hud.label("CURTA PARA RECARREGAR!", 18, Hud.zfont(), Color(1.0, 0.55, 0.75), Color(0.2, 0.0, 0.15), 4)
		_hint.position = Vector2(-62, 132)
		_hint.size = Vector2(366, 28)
		_hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
		add_child(_hint)
		_frame.appear()

	func _process(delta: float) -> void:
		_t += delta
		_label.text = "%d%%" % roundi(pct)
		var low := pct < low_at
		_hint.visible = low and fmod(_t, 1.0) < 0.75
		_cells.pct = pct
		_cells.low = low
		if low and not _was_low:
			_frame.bump()
		_was_low = low


class BatteryCells extends Control:
	var pct := 100.0
	var low := false
	var _t := 0.0

	func _process(delta: float) -> void:
		_t += delta
		queue_redraw()

	func _draw() -> void:
		var r := Rect2(Vector2.ZERO, size - Vector2(10, 0))
		draw_rect(r, Color(1, 1, 1, 0.9), false, 4.0)
		draw_rect(Rect2(Vector2(r.end.x + 2, size.y * 0.3), Vector2(8, size.y * 0.4)), Color(1, 1, 1, 0.9))
		var n := 5
		var inner := r.grow(-7)
		var w := (inner.size.x - 4.0 * (n - 1)) / n
		var on := ceili(pct / 100.0 * n)
		for i in n:
			var col := Color(0.35, 1.0, 0.6)
			if pct < 55.0:
				col = Color(1.0, 0.82, 0.3)
			if low:
				col = Color(1.0, 0.3, 0.45) if fmod(_t, 0.7) < 0.45 else Color(0.5, 0.1, 0.2)
			if i >= on:
				col = Color(0.25, 0.15, 0.35)
			draw_rect(Rect2(inner.position + Vector2(i * (w + 4.0), 0), Vector2(w, inner.size.y)), col)


class NoticePanel extends Control:
	var _queue: Array = []
	var _frame: Frame
	var _label: Label
	var _life := 0.0

	func push(text: String, style: String, secs: float) -> void:
		for q in _queue:
			if q[0] == text:
				return
		_queue.append([text, style, secs])

	func _process(delta: float) -> void:
		if _life > 0.0:
			_life -= delta
			if _life <= 0.0 and _frame:
				_frame.leave()
				_frame = null
			return
		if _queue.is_empty():
			return
		var q: Array = _queue.pop_front()
		var style := String(q[1])
		_frame = Frame.new()
		add_child(_frame)
		_frame.build(Vector2(860, 210), style)
		var c := _frame.content
		var zod := style != "kumo"
		c.add_child(Hud.sprite("robot.svg" if zod else "leaf.svg", Vector2(80, 80) if zod else Vector2(56, 92), Vector2(86, 105), 0.0 if zod else -20.0))
		var col := Color(0.92, 0.9, 1.0) if zod else Hud.KUMO_TEXT
		var out := Color(0.6, 0.05, 0.5, 0.7) if zod else Color(1, 1, 1, 0.9)
		_label = Hud.label(String(q[0]), 40 if zod else 46, Hud.zfont() if zod else Hud.kfont(), col, out, 6)
		_label.position = Vector2(140, 20)
		_label.size = Vector2(680, 170)
		_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		c.add_child(_label)
		_life = float(q[2])
		_frame.appear()


class ThanksCard extends Control:
	var sender := ""
	var gift_id := ""
	var plural := ""
	var one := ""
	var count := 1
	var style := "zodia"
	var life := 5.0
	var target_y := 1610.0
	var _frame: Frame
	var _line1: Label
	var _line2: Label
	var _icon: TextureRect
	var _leaving := false

	func _ready() -> void:
		position = Vector2(24, target_y)
		_frame = Frame.new()
		add_child(_frame)
		_frame.build(Vector2(690, 136), style)
		var c := _frame.content
		var zod := style != "kumo"
		# avatar: inicial do nome num anel
		var av := Avatar.new()
		av.initial = sender.substr(0, 1).to_upper() if sender != "" else "?"
		av.ring = Hud.MAGENTA if zod else Hud.WOOD
		av.fill = Color(0.16, 0.06, 0.3) if zod else Color(0.56, 0.72, 0.3)
		av.font = Hud.zfont() if zod else Hud.kfont()
		av.position = Vector2(24, 18)
		av.size = Vector2(100, 100)
		c.add_child(av)
		var col := Color(1.0, 0.5, 0.9) if zod else Hud.KUMO_TEXT
		var col2 := Hud.TEXT if zod else Hud.KUMO_TEXT_SOFT
		var f := Hud.zfont() if zod else Hud.kfont()
		_line1 = Hud.label("", 28 if zod else 34, f, col)
		_line1.position = Vector2(140, 20)
		_line1.size = Vector2(430, 44)
		_line1.autowrap_mode = TextServer.AUTOWRAP_OFF
		_line1.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
		c.add_child(_line1)
		_line2 = Hud.label("", 26 if zod else 32, Hud.zfont(true) if zod else Hud.kfont(), col2)
		_line2.position = Vector2(140, 66)
		_line2.size = Vector2(430, 44)
		_line2.autowrap_mode = TextServer.AUTOWRAP_OFF
		c.add_child(_line2)
		var gift_tex := Hud.tex("gift_%s.svg" % gift_id)
		_icon = Hud.sprite("gift_%s.svg" % gift_id if gift_tex else ("robot.svg" if zod else "flower.svg"), Vector2(88, 88), Vector2(620, 68))
		c.add_child(_icon)
		refresh()
		_frame.appear()

	func refresh() -> void:
		if _line1 == null:
			return
		_line1.text = "Obrigado @%s," % sender
		_line2.text = "%s!" % one if count == 1 else "pelas %d %s!" % [count, plural]

	func bump() -> void:
		_frame.bump()
		var tw := create_tween()
		tw.tween_property(_icon, "scale", Vector2(1.35, 1.35), 0.1)
		tw.tween_property(_icon, "scale", Vector2.ONE, 0.2).set_trans(Tween.TRANS_BACK)

	func leave() -> void:
		if _leaving:
			return
		_leaving = true
		_frame.leave()
		get_tree().create_timer(0.5).timeout.connect(queue_free)

	func _process(delta: float) -> void:
		position.y = lerpf(position.y, target_y, minf(delta * 8.0, 1.0))
		if _icon:
			_icon.rotation = sin(Time.get_ticks_msec() / 400.0) * 0.08


class Avatar extends Control:
	var initial := "?"
	var ring := Hud.MAGENTA
	var fill := Color(0.2, 0.1, 0.3)
	var font: Font

	func _draw() -> void:
		var c := size / 2.0
		var r := size.x / 2.0
		draw_circle(c, r, Color(ring, 0.35))
		draw_circle(c, r - 5.0, ring)
		draw_circle(c, r - 11.0, fill)
		var fs := int(r * 1.05)
		var w := font.get_string_size(initial, HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x
		draw_string(font, c + Vector2(-w / 2.0, fs * 0.36), initial, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, Color.WHITE)


class Leaderboard extends Control:
	var _frame: Frame
	var _rows: Array[Label] = []
	var _pts: Array[Label] = []
	var _crown: TextureRect
	var _order: Array = []
	var _dots: RankDots

	func _ready() -> void:
		_frame = Frame.new()
		add_child(_frame)
		_frame.build(Vector2(360, 430), "misto")
		var c := _frame.content
		var title := Hud.label("TOP", 22, Hud.zfont(true), Hud.CYAN)
		title.position = Vector2(0, 22)
		title.size = Vector2(360, 30)
		title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		c.add_child(title)
		var t2 := Hud.label("presenteadores", 30, Hud.kfont(), Color(1.0, 0.85, 0.4), Color(0.3, 0.1, 0.0, 0.8), 5)
		t2.position = Vector2(0, 46)
		t2.size = Vector2(360, 44)
		t2.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		c.add_child(t2)
		for i in 5:
			var l := Hud.label("", 28 if i == 0 else 25, Hud.kfont(), Hud.TEXT, Color(0.1, 0.0, 0.2, 0.9), 4)
			l.position = Vector2(64, 102 + i * 60)
			l.size = Vector2(200, 44)
			l.autowrap_mode = TextServer.AUTOWRAP_OFF
			l.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
			c.add_child(l)
			_rows.append(l)
			var p := Hud.label("", 22, Hud.zfont(), Hud.CYAN)
			p.position = Vector2(250, 108 + i * 60)
			p.size = Vector2(86, 36)
			p.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
			c.add_child(p)
			_pts.append(p)
		_crown = Hud.sprite("crown.svg", Vector2(44, 34), Vector2(36, 108))
		c.add_child(_crown)
		_dots = RankDots.new()
		_dots.position = Vector2(20, 102)
		c.add_child(_dots)
		visible = false

	func set_scores(scores: Dictionary, n: int) -> void:
		var names := scores.keys()
		names.sort_custom(func(a: Variant, b: Variant) -> bool: return float(scores[a]) > float(scores[b]))
		for i in _rows.size():
			if i < mini(n, names.size()):
				var who := String(names[i])
				_rows[i].text = who
				_pts[i].text = str(roundi(float(scores[names[i]])))
				var before := _order.find(who)
				if before == -1 or before > i:
					_flash(i)
			else:
				_rows[i].text = ""
				_pts[i].text = ""
		_order = names.slice(0, n)
		_dots.filled = mini(n, names.size())
		_dots.queue_redraw()
		if not visible:
			visible = true
			_frame.appear()

	func _flash(i: int) -> void:
		var l := _rows[i]
		var tw := create_tween()
		for k in 3:
			tw.tween_property(l, "modulate", Color(1.6, 1.4, 0.6), 0.08)
			tw.tween_property(l, "modulate", Color.WHITE, 0.12)
		if i == 0:
			_frame.bump()
			var cw := create_tween()
			cw.tween_property(_crown, "scale", Vector2(1.4, 1.4), 0.12)
			cw.tween_property(_crown, "scale", Vector2.ONE, 0.25).set_trans(Tween.TRANS_BACK)


class RankDots extends Control:
	var filled := 0

	func _draw() -> void:
		var cols := [Color(1, 1, 1, 0), Color(0.85, 0.88, 0.95), Color(0.85, 0.55, 0.3), Color(0.6, 0.5, 0.8), Color(0.6, 0.5, 0.8)]
		for i in range(1, mini(filled, 5)):
			var p := Vector2(16, 22 + i * 60)
			draw_circle(p, 14.0, cols[i])
			var f := Hud.zfont()
			var s := str(i + 1)
			var w := f.get_string_size(s, HORIZONTAL_ALIGNMENT_LEFT, -1, 16).x
			draw_string(f, p + Vector2(-w / 2.0, 6), s, HORIZONTAL_ALIGNMENT_LEFT, -1, 16, Color(0.1, 0.05, 0.2))


class ShatterPanel extends Control:
	## Painel holografico roxo que racha e se despedaca.
	var _shards: Array = []
	var _life := 0.0
	var _label: Label

	func _ready() -> void:
		size = Vector2(1080, 1920)
		mouse_filter = Control.MOUSE_FILTER_IGNORE
		_label = Hud.label("", 64, Hud.zfont(), Color(1.0, 0.85, 1.0), Color(0.4, 0.0, 0.5), 8)
		_label.position = Vector2(140, 880)
		_label.size = Vector2(800, 90)
		_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
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
