extends Node3D
## Fluxo do Ciberespaco.
## - O ZodIA escolhe um lugar livre do campo, projeta a plataforma ali e constroi
##   (2 min cada sem interferencia). Os objetos prontos ficam no mapa.
## - O Kumo comeca dormindo no terrario da arvore e acorda em ~1 min.
## - Curtidas recarregam a bateria do ZodIA; sem bateria ele fica lento e depois para.
## - Presentes passam pela EventQueue: alguns ajudam o ZodIA, outros mandam o Kumo
##   atrapalhar (cada um tem a sua consequencia em _on_event_started()).

const E := ZodiaFace.Expr
const PAD_SIZE := 4.4
## Primeiro lugar tentado (na frente da arvore); depois o ZodIA escolhe.
const FIRST_SITE := Vector3(0.0, 0.05, 7.5)

var _island: Island
var _pad: Node3D
var _zodia: Zodia
var _kumo: Kumo
var _project: BuildProject
## Centro da plataforma atual (muda a cada projeto).
var _site := FIRST_SITE
## Objetos ja construidos que ficam no mapa.
var _built: Array[BuildProject] = []
var _cam: CameraRig
var _hud: Hud
var _rng := RandomNumberGenerator.new()

var _projects: Array = []
var _project_index := 0
var _state := "building"   # building | done | fallen
var _battery := 100.0
var _elapsed := 0.0
var _kumo_woken := false
var _boost_left := 0.0
var _boost_mult := 1.0
## Quantos efeitos estao segurando o ZodIA (caido, rodando, comemorando...).
var _zodia_lock := 0
var _battery_notice_cd := 0.0
var _suspicious_cd := 0.0
var _orbit := 0.0
var _was_empty := false


func _ready() -> void:
	_rng.randomize()
	_battery = float(GameConfig.sub("battery", "start", 100.0))
	_projects = GameConfig.projects.duplicate()

	_build_environment()
	_island = Island.new()
	add_child(_island)
	_build_pad()

	_project = BuildProject.new()
	add_child(_project)

	_zodia = Zodia.new()
	_zodia.position = FIRST_SITE + Vector3(2.6, 0, -1.8)
	add_child(_zodia)

	_kumo = Kumo.new()
	add_child(_kumo)
	_kumo.sleep_at(_island.nest_pos)

	_cam = CameraRig.new()
	_cam.main_target = _zodia
	_cam.anchor = FIRST_SITE + Vector3(0, 0.8, 0)
	add_child(_cam)
	_cam.global_position = _cam.anchor + CameraRig.FAR_OFFSET
	_cam.snap()

	_hud = Hud.new()
	add_child(_hud)
	var sim := CanvasLayer.new()
	sim.set_script(load("res://scripts/ui/gift_simulator.gd"))
	add_child(sim)

	EventQueue.event_started.connect(_on_event_started)
	EventQueue.gift_received.connect(_hud.thanks)
	LiveConnector.likes_received.connect(_on_likes)
	_start_project()


# ---------- cenario ----------

func _build_environment() -> void:
	var env := Environment.new()
	var sky_mat := ShaderMaterial.new()
	sky_mat.shader = load("res://shaders/sky.gdshader")
	var sky := Sky.new()
	sky.sky_material = sky_mat
	sky.radiance_size = Sky.RADIANCE_SIZE_32
	env.background_mode = Environment.BG_SKY
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.55, 0.5, 0.8)
	env.ambient_light_energy = 0.9
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.glow_enabled = true
	env.glow_intensity = 0.6
	env.glow_bloom = 0.08
	env.glow_hdr_threshold = 1.1
	env.fog_enabled = true
	env.fog_light_color = Color(0.16, 0.07, 0.3)
	env.fog_density = 0.012
	env.fog_sky_affect = 0.0
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)

	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-55, 30, 0)
	sun.light_energy = 1.5
	sun.light_color = Color(0.95, 0.9, 1.0)
	sun.shadow_enabled = false
	add_child(sun)
	var rim := DirectionalLight3D.new()
	rim.rotation_degrees = Vector3(-20, 200, 0)
	rim.light_energy = 0.5
	rim.light_color = Color(0.5, 0.6, 1.0)
	add_child(rim)

	var floor_mesh := PlaneMesh.new()
	floor_mesh.size = Vector2(240, 240)
	var fm := ShaderMaterial.new()
	fm.shader = load("res://shaders/circuit_floor.gdshader")
	Mat.add(self, floor_mesh, fm)
	var floor_body := StaticBody3D.new()
	floor_body.position.y = Island.TOP
	var cs := CollisionShape3D.new()
	cs.shape = WorldBoundaryShape3D.new()
	floor_body.add_child(cs)
	add_child(floor_body)

	# chips em relevo espalhados pela placa de circuito
	var rng := RandomNumberGenerator.new()
	rng.seed = 5
	var chip_mat := Mat.solid(Color(0.06, 0.07, 0.2), 0.6)
	var chip_edge := Mat.glow(Color(0.3, 0.65, 1.0), 0.9)
	for i in 16:
		var a := rng.randf() * TAU
		var r := rng.randf_range(Island.RADIUS + 2.0, Island.RADIUS + 14.0)
		var c := Vector3(cos(a) * r, 0, sin(a) * r)
		if c.distance_to(_site) < 4.5:
			continue
		var sz := Vector3(rng.randf_range(0.8, 2.2), rng.randf_range(0.1, 0.45), rng.randf_range(0.8, 1.8))
		var chip := Node3D.new()
		chip.position = c
		chip.rotation.y = round(rng.randf() * 4.0) * PI / 4.0
		add_child(chip)
		Mat.add(chip, Mat.box(sz), chip_mat, Vector3(0, sz.y / 2.0, 0))
		for sgn in [-1.0, 1.0]:
			Mat.add(chip, Mat.box(Vector3(sz.x + 0.04, 0.03, 0.04)), chip_edge, Vector3(0, sz.y, sz.z / 2.0 * sgn))
			Mat.add(chip, Mat.box(Vector3(0.04, 0.03, sz.z + 0.04)), chip_edge, Vector3(sz.x / 2.0 * sgn, sz.y, 0))

	# particulas de dados flutuando
	var motes := CPUParticles3D.new()
	motes.amount = 50
	motes.lifetime = 6.0
	motes.preprocess = 6.0
	motes.emission_shape = CPUParticles3D.EMISSION_SHAPE_BOX
	motes.emission_box_extents = Vector3(18, 0.5, 18)
	motes.direction = Vector3.UP
	motes.spread = 10.0
	motes.initial_velocity_min = 0.3
	motes.initial_velocity_max = 0.8
	motes.gravity = Vector3.ZERO
	motes.mesh = Mat.box(Vector3(0.05, 0.05, 0.05))
	motes.material_override = Mat.glow(Color(0.5, 0.8, 1.0), 1.4)
	motes.position = Vector3(0, 0.5, 0)
	add_child(motes)


func _build_pad() -> void:
	_pad = Node3D.new()
	_pad.position = FIRST_SITE
	_pad.scale = Vector3(0.01, 1, 0.01)
	add_child(_pad)
	var floor_mat := Mat.glass(Color(0.45, 0.2, 0.9), 0.22)
	Mat.add(_pad, Mat.box(Vector3(PAD_SIZE, 0.04, PAD_SIZE)), floor_mat, Vector3(0, 0.02, 0))
	var edge := Mat.glow(Color(1.0, 0.25, 0.85), 2.5)
	var h := PAD_SIZE / 2.0
	for s in [-1.0, 1.0]:
		Mat.add(_pad, Mat.box(Vector3(PAD_SIZE + 0.1, 0.06, 0.06)), edge, Vector3(0, 0.05, h * s))
		Mat.add(_pad, Mat.box(Vector3(0.06, 0.06, PAD_SIZE + 0.1)), edge, Vector3(h * s, 0.05, 0))
	var grid := Mat.glow(Color(0.35, 0.75, 1.0), 1.0)
	for i in range(1, 4):
		var o := -h + PAD_SIZE * i / 4.0
		Mat.add(_pad, Mat.box(Vector3(PAD_SIZE, 0.01, 0.02)), grid, Vector3(0, 0.045, o))
		Mat.add(_pad, Mat.box(Vector3(0.02, 0.01, PAD_SIZE)), grid, Vector3(o, 0.045, 0))
	for x in [-1.0, 1.0]:
		for z in [-1.0, 1.0]:
			Mat.add(_pad, Mat.cyl(0.06, 0.1, 0.5, 8), Mat.glow(Color(0.35, 0.85, 1.0), 2.0), Vector3(h * x, 0.25, h * z))


# ---------- projetos ----------

func _start_project() -> void:
	if _projects.is_empty():
		push_error("Nenhum projeto em config/projects.json")
		return
	_state = "moving"
	_site = _choose_site()
	_island.clear_decor(Vector2(_site.x, _site.z), PAD_SIZE * 0.5 + 0.3)
	_project.position = _site
	_project.setup(_projects[_project_index])
	_cam.anchor = _site + Vector3(0, 0.8, 0)
	_hud.notice("Novo projeto: %s" % _project.project_name, "zodia", 3.0)
	# a plataforma aparece no lugar novo e o ZodIA vai ate la
	_pad.position = _site
	var tw := create_tween()
	tw.tween_property(_pad, "scale", Vector3.ONE, 0.6).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	_zodia.glide_speed = 4.0
	_zodia.goal = _site + Vector3(0, 0, -PAD_SIZE * 0.5 - 1.0)
	while is_inside_tree() and Vector2(_zodia.position.x - _zodia.goal.x, _zodia.position.z - _zodia.goal.z).length() > 0.4:
		_zodia.face_point(_zodia.goal)
		await get_tree().process_frame
	_zodia.glide_speed = 1.6
	if _state == "moving":
		_state = "building"


## Lugar livre para a proxima plataforma: sem arvore, pedras, brinquedos nem
## objetos que o ZodIA ja fez. Prefere lugares perto dele.
func _choose_site() -> Vector3:
	var half := PAD_SIZE * 0.5 + 0.6
	var from := Vector2(_zodia.position.x, _zodia.position.z)
	if _built.is_empty() and _island.square_is_free(Vector2(FIRST_SITE.x, FIRST_SITE.z), half) and _project.piece_count() == 0:
		return FIRST_SITE
	for attempt in 2:
		var best := Vector2.INF
		var best_d := INF
		for i in 400:
			var a := _rng.randf() * TAU
			var r := sqrt(_rng.randf()) * (Island.RADIUS - Island.FADE - half - 1.0)
			var c := Vector2(cos(a) * r, sin(a) * r)
			if not _island.square_is_free(c, half) or _overlaps_built(c, half):
				continue
			var d := c.distance_to(from)
			if d < 6.0:
				d += 20.0  # nao colado no anterior
			if d < best_d:
				best_d = d
				best = c
		if best != Vector2.INF:
			return Vector3(best.x, Island.TOP, best.y)
		# mapa cheio: o objeto mais antigo some para abrir espaco
		_remove_oldest_built()
	return FIRST_SITE


func _overlaps_built(c: Vector2, half: float) -> bool:
	for b in _built:
		var p := Vector2(b.position.x, b.position.z)
		if absf(p.x - c.x) < half + PAD_SIZE * 0.5 + 0.4 and absf(p.y - c.y) < half + PAD_SIZE * 0.5 + 0.4:
			return true
	return false


func _remove_oldest_built() -> void:
	if _built.is_empty():
		return
	var old: BuildProject = _built.pop_front()
	old.dissolve(1.0)
	await get_tree().create_timer(1.2).timeout
	if is_instance_valid(old):
		old.queue_free()


func _complete_project() -> void:
	_state = "done"
	_zodia.set_laser(null)
	_project.celebrate()
	_zodia_lock += 1
	# camera mostra o objeto pronto
	_cam.focus(_project, float(GameConfig.sub("camera", "object_focus_sec", 4.0)), CameraRig.OBJECT_OFFSET)
	var last := _project_index >= _projects.size() - 1
	if last:
		_zodia.express(E.OCULOS_VITORIA, 7.0)
		_zodia.arm_mode = "cheer"
		_hud.notice("ZodIA concluiu todos os projetos!", "zodia", 5.0)
	else:
		_zodia.express(E.ORGULHOSO, 4.0)
		_zodia.arm_mode = "cheer"
		_hud.notice("Projeto concluído: %s!" % _project.project_name, "zodia", 3.5)
	await get_tree().create_timer(7.0 if last else GameConfig.num("next_project_delay_sec", 4.5)).timeout
	_zodia.arm_mode = "idle"
	# o objeto fica no mapa; a plataforma some
	var tw := create_tween()
	tw.tween_property(_pad, "scale", Vector3(0.01, 1, 0.01), 0.4)
	_built.append(_project)
	while _built.size() > int(GameConfig.value("max_built_objects", 20)):
		_remove_oldest_built()
	_project = BuildProject.new()
	add_child(_project)
	_zodia_lock -= 1
	if last:
		_projects.shuffle()
		_project_index = 0
	else:
		_project_index += 1
	_start_project()


func _battery_mult() -> float:
	if _battery <= 0.0:
		return 0.0
	if _battery < float(GameConfig.sub("battery", "low_at", 25.0)):
		return float(GameConfig.sub("battery", "low_speed_mult", 0.45))
	return 1.0


# ---------- loop ----------

func _process(delta: float) -> void:
	_elapsed += delta
	_battery = maxf(_battery - float(GameConfig.sub("battery", "drain_per_sec", 0.55)) * delta, 0.0)
	_boost_left = maxf(_boost_left - delta, 0.0)
	_battery_notice_cd = maxf(_battery_notice_cd - delta, 0.0)
	_suspicious_cd = maxf(_suspicious_cd - delta, 0.0)

	if not _kumo_woken and _elapsed >= GameConfig.num("kumo_wake_sec", 60.0):
		_wake_kumo(false)

	_update_battery_state()
	_update_build(delta)
	_update_zodia_position(delta)
	_update_kumo_watch(delta)

	_hud.set_project(_project.project_name, _project_index, _projects.size(), _project.progress)
	_hud.set_battery(_battery, float(GameConfig.sub("battery", "low_at", 25.0)))


func _update_battery_state() -> void:
	var low := float(GameConfig.sub("battery", "low_at", 25.0))
	var empty := _battery <= 0.0
	if empty:
		_zodia.set_base(E.SEM_BATERIA)
		_zodia.slump(true)
		_zodia.arm_mode = "droop"
		if not _was_empty:
			_hud.notice("ZodIA ficou sem bateria!\nCurtam a live para religar.", "zodia", 5.0)
	elif _battery < low:
		_zodia.set_base(E.BATERIA_FRACA)
		_zodia.slump(false)
		if _battery_notice_cd <= 0.0:
			_battery_notice_cd = float(GameConfig.sub("battery", "notice_cooldown_sec", 25.0))
			_hud.notice("ZodIA está ficando sem bateria!\nCurta para recarregar.", "zodia", 4.5)
	else:
		_zodia.set_base(E.NORMAL)
		_zodia.slump(false)
	if _was_empty and not empty:
		_zodia.arm_mode = "idle"
		_zodia.express(E.ALIVIADO, 2.0)
	_was_empty = empty


func _update_build(delta: float) -> void:
	var can_build := _state == "building" and _zodia_lock == 0 and not _zodia.is_fallen()
	var mult := _battery_mult() * (_boost_mult if _boost_left > 0.0 else 1.0)
	if not can_build or mult <= 0.0:
		_zodia.set_laser(null)
		if _zodia.arm_mode == "build":
			_zodia.arm_mode = "idle"
		return
	_project.set_progress(_project.progress + delta * mult / GameConfig.num("project_build_sec", 120.0))
	var lp := _project.laser_point()
	_zodia.set_laser(lp)
	_zodia.face_point(lp)
	_zodia.arm_mode = "build"
	if _project.is_complete():
		_complete_project()


## O ZodIA ronda os cantos de tras da plataforma enquanto trabalha, de frente
## para o projeto e para a camera.
func _update_zodia_position(delta: float) -> void:
	if _zodia_lock > 0:
		return
	_orbit += delta * 0.12
	var a := PI + sin(_orbit) * deg_to_rad(62.0)
	var r := PAD_SIZE * 0.5 + 1.0
	_zodia.goal = _site + Vector3(sin(a) * r, 0, cos(a) * r)
	if _state != "building":
		_zodia.face_point(_cam.global_position)


func _update_kumo_watch(_delta: float) -> void:
	if not _kumo_woken:
		return
	# ZodIA desconfia quando o Kumo chega perto demais
	if _suspicious_cd <= 0.0 and not _zodia.has_temp_expr() and _kumo.global_position.distance_to(_zodia.global_position) < 2.6:
		_suspicious_cd = 12.0
		_zodia.express(E.DESCONFIADO, 2.2)


# ---------- Kumo ----------

func _wake_kumo(fast: bool) -> void:
	if _kumo_woken:
		return
	_kumo_woken = true
	_hud.notice("Kumo está acordando!", "kumo", 4.0)
	_cam.focus(_kumo, 3.0 if fast else GameConfig.num("kumo_focus_sec", 6.0) + 1.0)
	if not fast:
		_cam.focus(_kumo, float(GameConfig.sub("camera", "kumo_focus_sec", 6.0)) + 1.0)
	await _kumo.wake_up(fast, _island.descent_path)
	if not _zodia.has_temp_expr():
		_zodia.express(E.DESCONFIADO, 2.5)
	_kumo_roam()


## Rotina livre do Kumo: brinca com os brinquedos e fica observando o ZodIA.
func _kumo_roam() -> void:
	var walk := float(GameConfig.sub("kumo", "walk_speed", 1.6))
	while is_inside_tree():
		if _kumo.acting:
			await get_tree().create_timer(0.5).timeout
			continue
		if _rng.randf() < 0.6 and not _island.toys.is_empty():
			var toy: Node3D = _island.toys[_rng.randi_range(0, _island.toys.size() - 1)]
			var tp := toy.global_position
			var spot := tp + (Vector3(-tp.x, 0, -tp.z).normalized() * 1.0)
			if not await _kumo.walk_to(spot, walk) or _kumo.acting:
				continue
			_kumo.look_toward(tp)
			_kumo.set_face(Kumo.Face.HAPPY)
			await _kumo.bounce(2)
			_island.toy_react(toy)
			await get_tree().create_timer(GameConfig.range_pick("kumo", "play_sec", Vector2(4, 9), _rng)).timeout
			if not _kumo.acting:
				_kumo.set_face(Kumo.Face.OPEN)
		else:
			# observa o ZodIA da beira do campo
			var side := -1.0 if _rng.randf() < 0.5 else 1.0
			var watch := _site + Vector3(side * (PAD_SIZE / 2.0 + 1.3), 0, _rng.randf_range(-0.5, 1.5))
			if not await _kumo.walk_to(watch, walk) or _kumo.acting:
				continue
			_kumo.look_toward(_zodia.global_position)
			await get_tree().create_timer(_rng.randf_range(4.0, 8.0)).timeout


# ---------- curtidas e presentes ----------

func _on_likes(count: int, _user: String) -> void:
	_battery = minf(_battery + count * float(GameConfig.sub("battery", "per_like", 0.4)), 100.0)


func _on_event_started(ev: Dictionary) -> void:
	var def: Dictionary = ev["def"]
	var count := int(ev["count"])
	match String(ev["event"]):
		"recharge":
			_battery = minf(_battery + float(def.get("battery_per_gift", 3)) * count, 100.0)
			if not _zodia.has_temp_expr() and _battery > 0.0:
				_zodia.express(E.ALIVIADO, 1.5)
		"zodia_boost":
			_boost_mult = maxf(_boost_mult if _boost_left > 0.0 else 1.0, float(def.get("multiplier", 1.8)))
			_boost_left += float(def.get("duration_sec", 15.0)) * count
			_hud.notice("ZodIA turbinado!", "zodia", 2.5)
		"kumo_wake":
			if not _kumo_woken:
				_wake_kumo(true)
		"kumo_bump", "kumo_spin", "zodia_trip", "kumo_knockdown":
			_kumo_sabotage(ev)
		_:
			push_warning("Evento sem efeito: %s" % ev["event"])


func _kumo_sabotage(ev: Dictionary) -> void:
	_kumo.acting = true
	_kumo.cancel()
	if not _kumo_woken:
		await _wake_kumo(true)
	var run := float(GameConfig.sub("kumo", "run_speed", 4.2))
	var kind := String(ev["event"])
	if kind == "kumo_knockdown" and _project.built_count() == 0:
		kind = "kumo_bump"
	_kumo.set_face(Kumo.Face.MISCHIEF)
	_cam.focus(_kumo, 30.0)
	match kind:
		"kumo_bump":
			await _do_bump(run)
		"kumo_spin":
			await _do_spin(run)
		"zodia_trip":
			await _do_trip(run)
		"kumo_knockdown":
			await _do_knockdown(run)
	_kumo.set_face(Kumo.Face.HAPPY)
	await _kumo.bounce(2, 0.3)
	_kumo.set_face(Kumo.Face.OPEN)
	_cam.release()
	_kumo.acting = false
	EventQueue.finish(ev)


## Kumo esbarra sem querer: o projeto treme, mas nao cai.
func _do_bump(run: float) -> void:
	var sx := -1.0 if _kumo.global_position.x < _site.x else 1.0
	var side := _site + Vector3(sx * (PAD_SIZE / 2.0 + 0.45), 0, 0.3)
	await _kumo.walk_to(side, run)
	_kumo.look_toward(_site)
	_kumo.bounce(1, 0.2)
	_cam.focus(_zodia, 4.0)
	_zodia.express(E.ASSUSTADO, 1.8)
	_zodia.tremble(1.4)
	await _project.shake(1.4)
	_zodia.express(E.ALIVIADO, 1.8)
	await get_tree().create_timer(1.2).timeout
	_cam.focus(_kumo, 3.0)
	await _kumo.walk_to(_site + Vector3(sx * (PAD_SIZE / 2.0 + 1.6), 0, 1.2), run * 0.7)


## Kumo passa correndo pertinho e o ZodIA rodopia.
func _do_spin(run: float) -> void:
	var zp := _zodia.global_position
	var perp := (zp - _site).normalized().cross(Vector3.UP)
	await _kumo.walk_to(zp - perp * 2.2 + Vector3(0, 0, 0.6), run)
	_cam.focus(_zodia, 5.0)
	_kumo.walk_to(zp + perp * 2.4 + Vector3(0, 0, 0.6), run * 1.4)
	await get_tree().create_timer(0.35).timeout
	_zodia_lock += 1
	_zodia.express(E.CONFUSO, 3.2)
	await _zodia.spin(3.0, 1.6)
	_zodia_lock -= 1
	await get_tree().create_timer(1.0).timeout


## Kumo rola por baixo do ZodIA, que tropeca e cai. A peca em construcao racha.
func _do_trip(run: float) -> void:
	var zp := _zodia.global_position
	await _kumo.walk_to(zp + (zp - _site).normalized() * 1.6, run)
	_cam.focus(_zodia, 7.0)
	_kumo.roll(0.8)
	await _kumo.walk_to(zp, run * 1.3)
	_zodia_lock += 1
	_zodia.set_laser(null)
	_zodia.express(E.ASSUSTADO, 0.6)
	await _zodia.fall()
	# camera mostra a peca rachando e se despedacando, depois volta ao ZodIA
	_cam.focus(_project, 3.4, CameraRig.OBJECT_OFFSET)
	_project.crack_current()
	_zodia.express(E.INEXPRESSIVO, 3.4)
	await get_tree().create_timer(3.4).timeout
	_cam.focus(_zodia, 5.0)
	_zodia.express(E.CONFUSO, 2.2)
	_kumo.walk_to(_site + Vector3(PAD_SIZE / 2.0 + 1.5, 0, 1.0), run * 0.7)
	await get_tree().create_timer(2.0).timeout
	await _zodia.get_up()
	_zodia.express(E.CHATEADO, 2.5)
	_zodia_lock -= 1


## Kumo pula na plataforma e derruba o projeto inteiro.
func _do_knockdown(run: float) -> void:
	var edge := _site + Vector3(-PAD_SIZE / 2.0 - 0.6, 0, 0.4)
	await _kumo.walk_to(edge, run)
	_kumo.look_toward(_site)
	await _kumo.hop_to(_site + Vector3(-0.8, 0.05, 0.4), 1.4, 0.55)
	_kumo.bounce(1, 0.3)
	_state = "fallen"
	_zodia_lock += 1
	_zodia.set_laser(null)
	_zodia.express(E.ASSUSTADO, 3.8)
	# camera no objeto: racha, despedaca, cai e some (~3,6 s)
	_cam.focus(_project, 3.8, CameraRig.OBJECT_OFFSET)
	_project.knock_down(_kumo.global_position)
	await get_tree().create_timer(0.9).timeout
	_hud.shatter("Projeto derrubado!")
	_kumo.hop_to(_site + Vector3(-PAD_SIZE / 2.0 - 1.2, 0, 1.2), 1.2, 0.6)
	await get_tree().create_timer(2.9).timeout
	_kumo.walk_to(_site + Vector3(-PAD_SIZE / 2.0 - 2.2, 0, 2.0), run)
	_cam.focus(_zodia, 7.0)
	_zodia.express(E.ENFURECIDO, 3.2)
	_zodia.arm_mode = "wave"
	await get_tree().create_timer(3.2).timeout
	_zodia.arm_mode = "droop"
	_zodia.express(E.CHORAMINGANDO, 3.0)
	await get_tree().create_timer(3.0).timeout
	_zodia.arm_mode = "idle"
	_project.restart()
	_state = "building"
	_hud.notice("Recomeçando: %s" % _project.project_name, "zodia", 2.5)
	_zodia_lock -= 1
