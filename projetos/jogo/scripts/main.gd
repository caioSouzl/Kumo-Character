extends Node2D
## Fluxo do jogo: expediente (5 min) -> intervalo com resultados (20 s) -> repete.
## O Kumo trabalha sozinho em _kumo_loop(); os presentes chegam pela EventQueue
## e cada evento tem a sua consequencia em _on_event_started().

enum Phase { SHIFT, BREAK }

const SAVE_PATH := "user://kumo_save.json"

# posicoes no cenario (1080 x 1920)
const ORDER_POS := Vector2(260, 1235)
const DELIVERY_POS := Vector2(820, 1235)
const PREP_POS := Vector2(380, 960)
const OVEN_POS := Vector2(740, 960)
const KUMO_HOME := Vector2(540, 1120)
const WAIT_POS := Vector2(820, 1500)
const DOOR := Vector2(-90, 1640)
const EXIT := Vector2(1170, 1640)
const LINE_SLOTS := [Vector2(260, 1500), Vector2(150, 1590), Vector2(330, 1650), Vector2(90, 1690), Vector2(250, 1700)]

var phase := Phase.SHIFT
var time_left := 0.0
var shift_no := 0
var balance := 0
var stats := {}

var _token := 0
var _world: Node2D
var _kumo: Kumo
var _oven: Station
var _prep: Station
var _hud: Hud
var _line: Array[Customer] = []
var _customers: Array[Customer] = []
## Pedido em producao: {customer, total, prepped, ready, ruined}
var _job: Dictionary = {}
var _spawn_timer := 1.0
var _rng := RandomNumberGenerator.new()


func _ready() -> void:
	_rng.randomize()
	_load_save()

	var bg := Node2D.new()
	bg.set_script(load("res://scripts/world/background.gd"))
	add_child(bg)

	_world = Node2D.new()
	_world.y_sort_enabled = true
	add_child(_world)
	_add_station(Station.Kind.ORDER_COUNTER, Vector2(260, 1380))
	_add_station(Station.Kind.DELIVERY_COUNTER, Vector2(820, 1380))
	_prep = _add_station(Station.Kind.PREP_TABLE, Vector2(380, 880))
	_oven = _add_station(Station.Kind.OVEN, Vector2(740, 880))

	_kumo = Kumo.new()
	_kumo.walk_speed = GameConfig.num("kumo_walk_speed", 430.0)
	_kumo.position = KUMO_HOME
	_world.add_child(_kumo)

	_hud = Hud.new()
	add_child(_hud)
	var sim := CanvasLayer.new()
	sim.set_script(load("res://scripts/ui/gift_simulator.gd"))
	add_child(sim)

	EventQueue.event_started.connect(_on_event_started)
	_start_shift()
	_kumo_loop()


func _add_station(kind: Station.Kind, pos: Vector2) -> Station:
	var s := Station.new()
	s.kind = kind
	s.position = pos
	_world.add_child(s)
	return s


func _process(delta: float) -> void:
	time_left -= delta
	if phase == Phase.SHIFT:
		_spawn_timer -= delta
		if _spawn_timer <= 0.0:
			_spawn_timer = _spawn_interval()
			if _line.size() < int(GameConfig.num("max_line", 4)):
				_spawn_customer()
		if time_left <= 0.0:
			_end_shift()
	else:
		_hud.show_results(shift_no, stats, balance, time_left)
		if time_left <= 0.0:
			_start_shift()
	_hud.update_play(time_left, shift_no, balance, stats, phase == Phase.BREAK)
	if not _job.is_empty():
		_prep.raw = int(_job["prepped"]) if _oven.baking == 0 else 0


# ---------------------------------------------------------------- expediente

func _start_shift() -> void:
	shift_no += 1
	phase = Phase.SHIFT
	time_left = GameConfig.num("shift_duration_sec", 300.0)
	stats = {"served": 0, "pizzas": 0, "lost": 0, "stolen": 0, "sales": 0, "tips": 0}
	_spawn_timer = 1.0
	EventQueue.paused = false
	_hud.hide_results()


func _end_shift() -> void:
	phase = Phase.BREAK
	time_left = GameConfig.num("break_duration_sec", 20.0)
	_token += 1
	EventQueue.paused = true
	_drop_job()
	for c in _customers.duplicate():
		if not c.gone:
			c.gone = true
			c.show_order = false
			_send_out(c)
	_line.clear()
	_kumo.walk_to(KUMO_HOME)
	if stats["served"] >= stats["lost"]:
		_kumo.celebrate(3.0)
	else:
		_kumo.panic(2.0)
	_save()


# ---------------------------------------------------------------- clientes

func _spawn_interval() -> float:
	var r: Array = GameConfig.value("spawn_interval_sec", [8, 14])
	return _rng.randf_range(float(r[0]), float(r[1]))


func _spawn_customer() -> void:
	var types: Array = GameConfig.value("customers", [])
	if types.is_empty():
		return
	var total := 0.0
	for t in types:
		total += float(t.get("weight", 1))
	var pick := _rng.randf() * total
	var def: Dictionary = types[0]
	for t in types:
		pick -= float(t.get("weight", 1))
		if pick <= 0.0:
			def = t
			break
	var colors: Array = def.get("colors", ["#5b8def"])
	var c := Customer.new()
	c.setup(
		String(def.get("kind", "normal")),
		_rng.randi_range(1, int(GameConfig.num("max_pizzas_per_order", 3))),
		float(def.get("patience_sec", 90)),
		Color(String(colors[_rng.randi_range(0, colors.size() - 1)])),
		GameConfig.num("customer_walk_speed", 260.0))
	c.cooking_mult = GameConfig.num("patience_while_cooking_mult", 0.5)
	c.position = DOOR
	c.ran_out.connect(_on_customer_ran_out.bind(c))
	_world.add_child(c)
	_customers.append(c)
	_line.append(c)
	_relayout_line()


func _relayout_line() -> void:
	for i in _line.size():
		_line[i].walk_to(LINE_SLOTS[mini(i, LINE_SLOTS.size() - 1)])
		_line[i].show_order = i == 0


func _on_customer_ran_out(c: Customer) -> void:
	if c.gone:
		return
	stats["lost"] += 1
	c.leave_angry()
	_line.erase(c)
	_relayout_line()
	_float_text("Cliente foi embora!", c.position + Vector2(0, -260), Color("#e0544b"))
	_send_out(c)


func _send_out(c: Customer) -> void:
	await c.walk_to(EXIT)
	_customers.erase(c)
	c.queue_free()


# ---------------------------------------------------------------- Kumo

func _job_aborted(token: int) -> bool:
	if token != _token or _job.is_empty():
		return true
	var c: Customer = _job["customer"]
	return not is_instance_valid(c) or c.gone


func _kumo_loop() -> void:
	while true:
		await get_tree().process_frame
		if phase != Phase.SHIFT or _line.is_empty():
			continue
		var token := _token

		# 1. atender no balcao
		await _kumo.walk_to(ORDER_POS)
		if token != _token or _line.is_empty():
			continue
		var c: Customer = _line[0]
		while token == _token and is_instance_valid(c) and not c.gone and c.is_moving():
			await get_tree().process_frame
		if token != _token or not is_instance_valid(c) or c.gone:
			continue
		var took: bool = await _kumo.work(GameConfig.num("take_order_sec", 1.2),
				func() -> bool: return token != _token or not is_instance_valid(c) or c.gone)
		if not took:
			continue
		_line.erase(c)
		_relayout_line()
		c.show_order = true
		c.cooking = true
		c.walk_to(WAIT_POS)
		_job = {"customer": c, "total": c.pizzas, "prepped": 0, "ready": 0, "ruined": false}
		var abort := func() -> bool: return _job_aborted(token)
		var abort_or_ruined := func() -> bool: return _job_aborted(token) or bool(_job.get("ruined", false))

		# 2. preparar e assar ate ter todas as pizzas prontas
		while not _job_aborted(token) and int(_job["ready"]) < int(_job["total"]):
			if int(_job["prepped"]) + int(_job["ready"]) < int(_job["total"]):
				await _kumo.walk_to(PREP_POS)
				if _job_aborted(token):
					break
				_job["ruined"] = false
				var made: bool = await _kumo.work(GameConfig.num("prep_sec_per_pizza", 2.6), abort_or_ruined)
				if made:
					_job["prepped"] = int(_job["prepped"]) + 1
				continue
			await _kumo.walk_to(OVEN_POS)
			if _job_aborted(token):
				break
			_oven.baking = int(_job["prepped"])
			var baked: bool = await _kumo.work(GameConfig.num("bake_sec_per_batch", 3.5), abort)
			_oven.baking = 0
			if baked and not _job_aborted(token):
				var n := int(_job["prepped"])
				_job["ready"] = int(_job["ready"]) + n
				_job["prepped"] = 0
				stats["pizzas"] += n
				_kumo.carrying = int(_job["ready"])

		# 3. entregar
		if _job_aborted(token):
			_drop_job()
			continue
		await _kumo.walk_to(DELIVERY_POS)
		if _job_aborted(token):
			_drop_job()
			continue
		var delivered: bool = await _kumo.work(GameConfig.num("deliver_sec", 0.8), abort)
		if not delivered or _job_aborted(token):
			_drop_job()
			continue
		var pay := int(_job["total"]) * int(GameConfig.num("price_per_pizza", 10))
		stats["served"] += 1
		stats["sales"] += pay
		balance += pay
		c.receive()
		_float_text("+$%d" % pay, c.position + Vector2(0, -260), Color("#f3c74f"))
		_send_out(c)
		_drop_job()
		_kumo.celebrate(1.0)
		_save()


func _drop_job() -> void:
	_job = {}
	_kumo.carrying = 0
	_prep.raw = 0
	_oven.baking = 0


# ---------------------------------------------------------------- presentes

func _on_event_started(ev: Dictionary) -> void:
	var def: Dictionary = ev["def"]
	var count := int(ev["count"])
	var senders: Array = ev["senders"]
	var who := String(senders[0]) if senders.size() == 1 else "%s e mais %d" % [senders[0], senders.size() - 1]
	var label := String(def.get("label", ev["gift_id"]))
	var desc := "%s x%d de %s" % [label, count, who]
	match String(ev["event"]):
		"tip":
			var amount := int(def.get("tip_per_gift", 1)) * count
			stats["tips"] += amount
			balance += amount
			_kumo.celebrate(1.5)
			_float_text("+$%d de gorjeta!" % amount, _kumo.position + Vector2(0, -300), Color("#ff8fb1"))
			_hud.show_event(desc + " -> gorjeta $%d" % amount)
			_save()
		"speed_boost":
			_kumo.boost(float(def.get("multiplier", 1.7)), float(def.get("duration_sec", 12)) * count)
			_float_text("VELOCIDADE!", _kumo.position + Vector2(0, -300), Color("#ff5c8a"))
			_hud.show_event(desc + " -> Kumo acelerou")
		"capybara_raid":
			_hud.show_event(desc + " -> capivara na cozinha!")
			_capybara_raid(ev)
		"impatience":
			var secs := float(def.get("patience_loss_sec", 15)) * count
			for c in _customers:
				c.lose_patience(secs)
			_float_text("Clientes impacientes!", Vector2(540, 1450), Color("#e0544b"))
			_hud.show_event(desc + " -> clientes impacientes")
		_:
			push_warning("Evento desconhecido: %s" % ev["event"])
			_hud.show_event(desc)
			EventQueue.finish(ev)


func _capybara_raid(ev: Dictionary) -> void:
	var def: Dictionary = ev["def"]
	var cap := Capybara.new()
	cap.walk_speed = 900.0
	cap.position = EXIT
	cap.follow = _kumo
	_world.add_child(cap)
	await cap.walk_to(_kumo.position + Vector2(95, 15))
	_kumo.panic(float(def.get("panic_sec", 2.5)))
	cap.eating = true
	_steal_pizza()
	_float_text("A capivara comeu uma pizza!", _kumo.position + Vector2(0, -300), Color("#ffb36b"))
	await get_tree().create_timer(float(def.get("eat_sec", 2.0))).timeout
	cap.eating = false
	cap.follow = null
	await cap.walk_to(EXIT)
	cap.queue_free()
	EventQueue.finish(ev)


## Efeito proprio da capivara: o pedido continua, mas uma pizza se perde
## e o Kumo precisa refazer.
func _steal_pizza() -> void:
	if _job.is_empty():
		return
	stats["stolen"] += 1
	if int(_job["ready"]) > 0:
		_job["ready"] = int(_job["ready"]) - 1
		_kumo.carrying = int(_job["ready"])
	elif int(_job["prepped"]) > 0:
		_job["prepped"] = int(_job["prepped"]) - 1
		_oven.baking = mini(_oven.baking, int(_job["prepped"]))
	else:
		_job["ruined"] = true


# ---------------------------------------------------------------- utilidades

func _float_text(text: String, pos: Vector2, color: Color) -> void:
	var l := Label.new()
	var ls := LabelSettings.new()
	ls.font_size = 44
	ls.font_color = color
	ls.outline_size = 10
	ls.outline_color = Color("#2b2140")
	l.label_settings = ls
	l.text = text
	l.z_index = 100
	add_child(l)
	l.position = pos - Vector2(l.get_minimum_size().x / 2.0, 0)
	var tw := create_tween()
	tw.set_parallel(true)
	tw.tween_property(l, "position:y", l.position.y - 120.0, 1.6)
	tw.tween_property(l, "modulate:a", 0.0, 1.6).set_delay(0.6)
	tw.chain().tween_callback(l.queue_free)


func _load_save() -> void:
	var f := FileAccess.open(SAVE_PATH, FileAccess.READ)
	if f == null:
		return
	var data: Variant = JSON.parse_string(f.get_as_text())
	if typeof(data) == TYPE_DICTIONARY:
		balance = int(data.get("balance", 0))
		shift_no = int(data.get("shifts", 0))


func _save() -> void:
	var f := FileAccess.open(SAVE_PATH, FileAccess.WRITE)
	if f == null:
		return
	f.store_string(JSON.stringify({"balance": balance, "shifts": shift_no}))
