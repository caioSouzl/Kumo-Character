extends CanvasLayer
## Simulador de presentes e curtidas para testar sem live.
## Teclas 1..9 = presentes (na ordem alfabetica dos ids), Shift+tecla = x10.
## L = curtidas (Shift+L = x5). F1 ou o botao "SIM" mostra/esconde o painel
## (esconda antes de transmitir).

const NAMES := ["Ana", "Bia", "Caio", "Davi", "Edu", "Fe", "Gabi", "Hugo", "Iara", "Juca"]

var _panel: VBoxContainer
var _rng := RandomNumberGenerator.new()


func _ready() -> void:
	layer = 10
	_rng.randomize()
	var toggle := Button.new()
	toggle.text = "SIM"
	toggle.position = Vector2(960, 200)
	toggle.size = Vector2(100, 60)
	toggle.modulate = Color(1, 1, 1, 0.45)
	toggle.pressed.connect(_toggle)
	add_child(toggle)

	_panel = VBoxContainer.new()
	_panel.position = Vector2(24, 520)
	_panel.add_theme_constant_override("separation", 8)
	add_child(_panel)
	var ids := GameConfig.gift_ids()
	for i in ids.size():
		var gift_id: String = ids[i]
		var def: Dictionary = GameConfig.gifts[gift_id]
		var row := HBoxContainer.new()
		_panel.add_child(row)
		for amount in [1, 10]:
			var b := Button.new()
			b.text = ("%d. %s" % [i + 1, def.get("label", gift_id)]) if amount == 1 else ("x%d" % amount)
			b.add_theme_font_size_override("font_size", 26)
			b.custom_minimum_size = Vector2(250 if amount == 1 else 80, 58)
			b.pressed.connect(_send.bind(gift_id, amount))
			row.add_child(b)
	var likes := Button.new()
	likes.text = "L. Curtidas +%d" % _likes_step()
	likes.add_theme_font_size_override("font_size", 26)
	likes.custom_minimum_size = Vector2(338, 58)
	likes.pressed.connect(_likes.bind(1))
	_panel.add_child(likes)
	var sim: Dictionary = GameConfig.value("simulator", {})
	_panel.visible = bool(sim.get("visible_on_start", true))


func _likes_step() -> int:
	var sim: Dictionary = GameConfig.value("simulator", {})
	return int(sim.get("likes_per_click", 20))


func _toggle() -> void:
	_panel.visible = not _panel.visible


func _who() -> String:
	return "Espectador%s" % NAMES[_rng.randi_range(0, NAMES.size() - 1)]


func _send(gift_id: String, amount: int) -> void:
	EventQueue.enqueue_gift(gift_id, _who(), amount)


func _likes(mult: int) -> void:
	LiveConnector.add_likes(_likes_step() * mult, _who())


func _unhandled_input(event: InputEvent) -> void:
	var k := event as InputEventKey
	if k == null or not k.pressed or k.echo:
		return
	if k.keycode == KEY_F1:
		_toggle()
		return
	if k.keycode == KEY_L:
		_likes(5 if k.shift_pressed else 1)
		return
	var n := k.keycode - KEY_1
	var ids := GameConfig.gift_ids()
	if n >= 0 and n < ids.size() and n < 9:
		_send(ids[n], 10 if k.shift_pressed else 1)
