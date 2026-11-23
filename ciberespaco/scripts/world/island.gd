class_name Island
extends Node3D
## O campinho no meio do ciberespaco (referencia: pagina do cenario no Canva):
## grama viva com manchas claras e escuras, moitas com flores roxas, brancas,
## rosas e amarelas, pedras na borda, caminho de pedras chatas ate a plataforma
## do ZodIA, borda azul luminosa e chips de circuito em volta.
## A arvore com o terrario e os brinquedos vem de assets/models/ambiente.glb
## (Hyper3D). Sem o arquivo, entra uma arvore provisoria.

const RADIUS := 40.0
const TOP := 0.05
## Faixa da borda onde a grama se desfaz em pixels e vira circuito.
const FADE := 3.0
## Quanto a borda ondula (multiplica as ondas de edge_r).
const JITTER := 2.5
## Terrario (globo de vidro) no espaco da arvore do .glb, medido no Blender.
const TERRARIUM_LOCAL := Vector3(0.068, 3.921, -0.002)
const TERRARIUM_R := 1.26
## Brinquedos nas bordas: angulo (graus, 0 = +x, 90 = frente).
const TOY_ANGLES := {"bola": 18.0, "bloco": 158.0, "carrinho": 212.0, "balanco": 268.0, "argolas": 326.0}
## Tamanho dos blocos de detalhes (cada bloco e cortado da tela sozinho).
const CHUNK := 10.0
const GRASS_DARK := Color(0.16, 0.38, 0.14)
const GRASS_LIGHT := Color(0.45, 0.72, 0.22)
const BARK := Color(0.45, 0.28, 0.18)
const ROCK := Color(0.46, 0.45, 0.52)
const PATH_STONE := Color(0.72, 0.63, 0.5)
const FLOWERS := [Color(0.62, 0.38, 0.95), Color(0.95, 0.95, 1.0), Color(1.0, 0.5, 0.72), Color(1.0, 0.84, 0.25), Color(0.75, 0.55, 1.0)]
## Nome do no no .glb -> tipo de brinquedo
const GLB_TOYS := ["bola", "bloco", "carrinho", "argolas", "balanco"]

var toys: Array[Node3D] = []
var tree_pos := Vector3(0.0, TOP, 0.0)
var tree_scale := 1.6
var nest_pos := Vector3.ZERO
## Pulos do terrario ate o chao.
var descent_path: Array = []
## Objetos solidos do mapa (arvore, brinquedos, pedras): [centro xz, raio].
## O ZodIA nao constroi em cima deles.
var solids: Array = []

var _rng := RandomNumberGenerator.new()
## Detalhes por bloco: chave Vector2i -> {tipo: [transforms, cores]}
var _decor: Dictionary = {}
## Instancias desenhadas: [MultiMeshInstance3D, posicoes xz]
var _decor_nodes: Array = []


static func ground_y(p: Vector3) -> float:
	return TOP if Vector2(p.x, p.z).length() < RADIUS else 0.0


## Raio da borda num angulo (borda organica, nao um circulo perfeito).
## O shader da grama repete a mesma conta.
static func edge_r(a: float) -> float:
	return RADIUS + (sin(a * 3.0 + 0.7) * 0.4 + sin(a * 7.0 + 2.1) * 0.25 + sin(a * 13.0) * 0.12) * JITTER


## Ponto dentro do campo (para quem anda nao sair do mapa).
static func clamp_inside(p: Vector3, margin: float = 1.0) -> Vector3:
	var v := Vector2(p.x, p.z)
	var lim := edge_r(atan2(v.y, v.x)) - FADE - margin
	if v.length() > lim:
		v = v.normalized() * lim
	return Vector3(v.x, p.y, v.y)


func _ready() -> void:
	_rng.seed = 11
	var models: Dictionary = GameConfig.value("models", {})
	tree_scale = float(models.get("tree_scale", 1.6))
	_build_ground()
	if not _load_glb(String(models.get("environment", ""))):
		_build_placeholder_tree()
		_build_placeholder_toys()
	nest_pos = tree_pos + TERRARIUM_LOCAL * tree_scale + Vector3(0, -TERRARIUM_R * tree_scale + 0.35, 0)
	descent_path = [nest_pos + Vector3(2.0, -1.0, 1.4), nest_pos + Vector3(3.2, -2.6, 2.2), Vector3(3.8, TOP, 3.0)]
	solids.append([Vector2(tree_pos.x, tree_pos.z), 3.6 * tree_scale / 1.6])
	for t in toys:
		solids.append([Vector2(t.position.x, t.position.z), 1.4])
	_build_path()
	_build_rocks()
	_build_bushes_and_flowers()
	_build_grass()
	_flush_decor()
	_build_walls()


# ---------- chao ----------

func _build_ground() -> void:
	# disco de grama ate a borda + faixa de transicao; o shader desfaz a borda
	# em pixels e deixa o circuito aparecer por baixo
	var seg := 256
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for i in seg:
		var a0 := TAU * i / seg
		var a1 := TAU * (i + 1) / seg
		var r0 := edge_r(a0) + FADE
		var r1 := edge_r(a1) + FADE
		st.set_normal(Vector3.UP)
		st.add_vertex(Vector3(0, TOP, 0))
		st.add_vertex(Vector3(cos(a1) * r1, TOP, sin(a1) * r1))
		st.add_vertex(Vector3(cos(a0) * r0, TOP, sin(a0) * r0))
	var top := MeshInstance3D.new()
	top.mesh = st.commit()
	var gm := ShaderMaterial.new()
	gm.shader = load("res://shaders/grass.gdshader")
	gm.set_shader_parameter("radius", RADIUS)
	gm.set_shader_parameter("fade", FADE)
	gm.set_shader_parameter("jitter", JITTER)
	top.material_override = gm
	top.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(top)


func st_quad(st: SurfaceTool, a: Vector3, b: Vector3, c: Vector3, d: Vector3, col: Color) -> void:
	for v in [a, c, b, a, d, c]:
		st.set_color(col)
		st.add_vertex(v)


# ---------- arvore e brinquedos ----------

func _load_glb(path: String) -> bool:
	if path == "" or not ResourceLoader.exists(path):
		return false
	var scene: PackedScene = load(path)
	if scene == null:
		return false
	var env := scene.instantiate() as Node3D
	env.name = "AmbienteHyper3D"
	env.position = Vector3(0, TOP, 0)
	add_child(env)
	_glass_fix(env)
	var tree := env.find_child("arvore", true, false) as Node3D
	if tree:
		# arvore no centro do campo e mais alta
		tree.position = Vector3(tree_pos.x, 0.0, tree_pos.z)
		tree.scale *= tree_scale
	for kind in GLB_TOYS:
		var t := env.find_child(kind, true, false) as Node3D
		if t:
			_place_on_edge(t, kind)
			_make_toy(t, kind)
	return true


## O vidro do terrario precisa ser transparente para ver o Kumo dormindo dentro.
func _glass_fix(n: Node) -> void:
	if n is MeshInstance3D:
		var mi := n as MeshInstance3D
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		for s in mi.mesh.get_surface_count():
			var mat := mi.mesh.surface_get_material(s)
			if mat and mat.resource_name.begins_with("vidro"):
				var g := Mat.glass(Color(0.75, 0.9, 1.0), 0.18)
				g.rim_enabled = true
				g.rim = 0.6
				mi.set_surface_override_material(s, g)
	for c in n.get_children():
		_glass_fix(c)


## Brinquedos espalhados pelas extremidades, virados para o centro.
func _place_on_edge(t: Node3D, kind: String) -> void:
	var a := deg_to_rad(float(TOY_ANGLES.get(kind, _rng.randf() * 360.0)))
	var r := edge_r(a) - FADE - 0.9
	t.position = Vector3(cos(a) * r, 0.0, sin(a) * r)
	t.rotation.y = atan2(-t.position.x, -t.position.z)


func _make_toy(t: Node3D, kind: String) -> void:
	t.set_meta("kind", kind)
	t.set_meta("home", t.position)
	toys.append(t)


func _build_placeholder_tree() -> void:
	var tree := Node3D.new()
	tree.position = tree_pos
	add_child(tree)
	var bark := Mat.solid(BARK, 0.95)
	for i in 9:
		var r := lerpf(0.8, 0.4, i / 8.0)
		var off := Vector3(sin(i * 0.8) * 0.4, 0, cos(i * 0.9) * 0.2)
		Mat.add(tree, Mat.cyl(r * 0.9, r, 0.45, 10), bark, Vector3(0, 0.2 + i * 0.32, 0) + off, Vector3(sin(i * 1.3) * 14.0, i * 31.0, 0))
	tree.scale = Vector3.ONE * tree_scale
	Mat.add(tree, Mat.sphere(TERRARIUM_R, -1, 18), Mat.glass(Color(0.75, 0.9, 1.0), 0.18), TERRARIUM_LOCAL)
	Mat.add(tree, Mat.cyl(0.9, 0.5, 0.3, 14), bark, TERRARIUM_LOCAL - Vector3(0, TERRARIUM_R, 0))


func _build_placeholder_toys() -> void:
	var ball := _toy_node("bola", Vector3(4.9, TOP, 1.05))
	Mat.add(ball, Mat.sphere(0.45, -1, 14), Mat.solid(Color(0.95, 0.3, 0.3), 0.5), Vector3(0, 0.45, 0))
	var block := _toy_node("bloco", Vector3(3.7, TOP, -1.3))
	Mat.add(block, Mat.box(Vector3(0.6, 0.6, 0.6)), Mat.solid(Color(0.85, 0.55, 0.3), 0.7), Vector3(0, 0.3, 0))
	var car := _toy_node("carrinho", Vector3(-3.2, TOP, -2.9))
	Mat.add(car, Mat.box(Vector3(0.8, 0.3, 0.45)), Mat.solid(Color(0.9, 0.2, 0.25), 0.5), Vector3(0, 0.25, 0))
	var rings := _toy_node("argolas", Vector3(-3.1, TOP, 3.0))
	for i in 4:
		Mat.add(rings, Mat.torus(0.05, 0.35 - i * 0.06), Mat.solid(FLOWERS[i], 0.5), Vector3(0, 0.1 + i * 0.16, 0))
	var swing := _toy_node("balanco", Vector3(-4.4, TOP, 0.6))
	Mat.add(swing, Mat.box(Vector3(0.1, 1.6, 0.1)), Mat.solid(BARK, 0.8), Vector3(-0.9, 0.8, 0))
	Mat.add(swing, Mat.box(Vector3(0.1, 1.6, 0.1)), Mat.solid(BARK, 0.8), Vector3(0.9, 0.8, 0))
	Mat.add(swing, Mat.box(Vector3(1.9, 0.1, 0.1)), Mat.solid(BARK, 0.8), Vector3(0, 1.6, 0))
	Mat.add(swing, Mat.box(Vector3(0.6, 0.06, 0.3)), Mat.solid(Color(0.85, 0.3, 0.3), 0.8), Vector3(0, 0.5, 0))


func _toy_node(kind: String, _pos: Vector3) -> Node3D:
	var t := Node3D.new()
	t.name = kind
	add_child(t)
	_place_on_edge(t, kind)
	_make_toy(t, kind)
	return t


## O brinquedo reage quando o Kumo brinca com ele.
func toy_react(t: Node3D) -> void:
	var kind := String(t.get_meta("kind", ""))
	var home: Vector3 = t.get_meta("home", t.position)
	var tw := create_tween()
	match kind:
		"bola":
			var a := atan2(t.position.z, t.position.x) + _rng.randf_range(-0.5, 0.5)
			var r := _rng.randf_range(RADIUS - FADE - 2.6, RADIUS - FADE - 1.0)
			var dest := Vector3(cos(a) * r, t.position.y, sin(a) * r)
			tw.set_parallel(true)
			tw.tween_property(t, "position", dest, 1.3).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
			tw.tween_property(t, "rotation:x", t.rotation.x + TAU * 1.5, 1.3)
		"bloco", "argolas":
			tw.tween_property(t, "rotation:z", 0.25, 0.18)
			tw.tween_property(t, "rotation:z", -0.18, 0.2)
			tw.tween_property(t, "rotation:z", 0.08, 0.18)
			tw.tween_property(t, "rotation:z", 0.0, 0.2)
		"carrinho":
			var fwd := Vector3(sin(t.rotation.y), 0, cos(t.rotation.y)) * 0.9
			tw.tween_property(t, "position", home + fwd, 0.7).set_trans(Tween.TRANS_SINE)
			tw.tween_property(t, "position", home, 0.9).set_trans(Tween.TRANS_SINE)
		"balanco":
			for k in 3:
				tw.tween_property(t, "rotation:x", 0.06, 0.35).set_trans(Tween.TRANS_SINE)
				tw.tween_property(t, "rotation:x", -0.06, 0.35).set_trans(Tween.TRANS_SINE)
			tw.tween_property(t, "rotation:x", 0.0, 0.3)
		_:
			tw.tween_interval(0.1)


# ---------- detalhes ----------

## Ponto livre de objetos solidos, dentro do campo.
func _free_spot(min_r: float, max_r: float, clearance: float) -> Variant:
	for _i in 30:
		var a := _rng.randf() * TAU
		var r := sqrt(_rng.randf_range(min_r * min_r, max_r * max_r))
		r = minf(r, edge_r(a) - FADE - 0.4)
		var p := Vector2(cos(a) * r, sin(a) * r)
		if is_free(p, clearance):
			return Vector3(p.x, TOP, p.y)
	return null


func is_free(p: Vector2, clearance: float) -> bool:
	for sd in solids:
		if p.distance_to(sd[0]) < float(sd[1]) + clearance:
			return false
	return true


## Quadrado (centro xz, meio lado) sem nenhum objeto solido dentro e todo no campo.
func square_is_free(c: Vector2, half: float) -> bool:
	for sd in solids:
		var q: Vector2 = sd[0]
		var r := float(sd[1])
		var d := Vector2(maxf(absf(q.x - c.x) - half, 0.0), maxf(absf(q.y - c.y) - half, 0.0))
		if d.length() < r:
			return false
	for corner in [Vector2(-1, -1), Vector2(1, -1), Vector2(-1, 1), Vector2(1, 1)]:
		var k: Vector2 = c + corner * half
		if k.length() > edge_r(atan2(k.y, k.x)) - FADE - 0.5:
			return false
	return true


## Caminho de pedras chatas saindo da frente da arvore.
func _build_path() -> void:
	var stone := Mat.solid(PATH_STONE, 0.95)
	var pts := [Vector2(-1.4, 3.4), Vector2(-3.0, 6.0), Vector2(-3.4, 9.5), Vector2(-2.0, 13.0), Vector2(-2.6, 16.5)]
	var n := 16
	for i in n:
		var k := float(i) / (n - 1) * (pts.size() - 1)
		var j := mini(int(k), pts.size() - 2)
		var p: Vector2 = (pts[j] as Vector2).lerp(pts[j + 1], k - j) + Vector2(sin(i * 1.9) * 0.3, 0)
		var s := _rng.randf_range(0.32, 0.42)
		var m := Mat.sphere(s, 0.14, 7)
		m.rings = 3
		Mat.add(self, m, stone, Vector3(p.x, TOP + 0.015, p.y), Vector3(0, _rng.randf() * 360.0, 0))
		solids.append([p, s])


func _build_rocks() -> void:
	var cols := [ROCK, ROCK.darkened(0.15), Color(0.5, 0.5, 0.56)]
	for count in 70:
		var near_edge := count < 50
		var spot: Variant = _free_spot(RADIUS - FADE - 4.0, RADIUS, 1.0) if near_edge else _free_spot(5.0, RADIUS - 6.0, 2.0)
		if spot == null:
			continue
		var p: Vector3 = spot
		var s := _rng.randf_range(0.25, 0.6)
		var m := Mat.sphere(s, s * 1.6, 6)
		m.rings = 3
		Mat.add(self, m, Mat.solid(cols[count % cols.size()], 0.9), p + Vector3(0, s * 0.35, 0), Vector3(_rng.randf() * 20.0, _rng.randf() * 360.0, _rng.randf() * 20.0), Vector3(1.25, 0.8, 1.0))
		solids.append([Vector2(p.x, p.z), s * 1.25])


## Moitas de folhas largas com flores por cima, mais densas perto da borda.
func _build_bushes_and_flowers() -> void:
	for c in 320:
		var near_edge := c < 170
		var spot: Variant = _free_spot(RADIUS - FADE - 5.0 if near_edge else 4.0, RADIUS if near_edge else RADIUS - FADE - 5.0, 0.2)
		if spot == null:
			continue
		var p: Vector3 = spot
		var col: Color = FLOWERS[_rng.randi_range(0, FLOWERS.size() - 1)]
		for k in 6:
			var a := TAU * k / 6.0 + _rng.randf() * 0.5
			var b := Basis(Vector3.UP, PI / 2.0 - a) * Basis(Vector3.RIGHT, -0.5)
			var pos := p + Vector3(cos(a), 0, sin(a)) * 0.2 + Vector3(0, 0.12, 0)
			_decor_add("folha", Transform3D(b.scaled(Vector3(0.7, 1.0, 1.6) * _rng.randf_range(0.8, 1.3)), pos), GRASS_DARK.lerp(Color(0.25, 0.55, 0.2), _rng.randf()))
		for k in _rng.randi_range(3, 6):
			var off := Vector3(_rng.randf_range(-0.35, 0.35), _rng.randf_range(0.22, 0.4), _rng.randf_range(-0.35, 0.35))
			_decor_add("flor", Transform3D(Basis().scaled(Vector3.ONE * _rng.randf_range(0.8, 1.3)), p + off), col.lightened(_rng.randf() * 0.15))
	for i in 700:
		var spot: Variant = _free_spot(3.0, RADIUS, 0.05)
		if spot == null:
			continue
		var p: Vector3 = spot
		_decor_add("caule", Transform3D(Basis(), p + Vector3(0, 0.09, 0)), Color(0.25, 0.55, 0.2))
		_decor_add("flor", Transform3D(Basis(), p + Vector3(0, 0.19, 0)), FLOWERS[i % FLOWERS.size()])


## Tufos de grama.
func _build_grass() -> void:
	for i in 2600:
		var spot: Variant = _free_spot(2.8, RADIUS, -0.2)
		if spot == null:
			continue
		var p: Vector3 = spot
		var b := Basis(Vector3(1, 0, 0), _rng.randf_range(-0.25, 0.25)) * Basis(Vector3.UP, _rng.randf() * TAU)
		_decor_add("tufo", Transform3D(b.scaled(Vector3.ONE * _rng.randf_range(0.7, 1.5)), p + Vector3(0, 0.09, 0)), GRASS_DARK.lerp(GRASS_LIGHT, _rng.randf()))


func _decor_add(kind: String, xf: Transform3D, col: Color) -> void:
	var key := Vector2i(floori(xf.origin.x / CHUNK), floori(xf.origin.z / CHUNK))
	if not _decor.has(key):
		_decor[key] = {}
	var chunk: Dictionary = _decor[key]
	if not chunk.has(kind):
		chunk[kind] = [[], []]
	chunk[kind][0].append(xf)
	chunk[kind][1].append(col)


func _flush_decor() -> void:
	var meshes := {
		"folha": Mat.sphere(0.16, 0.06, 6),
		"flor": Mat.sphere(0.055, 0.05, 6),
		"caule": Mat.cyl(0.01, 0.01, 0.18, 4),
		"tufo": Mat.cyl(0.0, 0.05, 0.2, 4),
	}
	var m := StandardMaterial3D.new()
	m.vertex_color_use_as_albedo = true
	m.roughness = 1.0
	for key in _decor:
		var chunk: Dictionary = _decor[key]
		for kind in chunk:
			var xfs: Array = chunk[kind][0]
			var cols: Array = chunk[kind][1]
			var mm := MultiMesh.new()
			mm.transform_format = MultiMesh.TRANSFORM_3D
			mm.use_colors = true
			mm.mesh = meshes[kind]
			mm.instance_count = xfs.size()
			var pos: Array[Vector2] = []
			for i in xfs.size():
				mm.set_instance_transform(i, xfs[i])
				mm.set_instance_color(i, cols[i])
				pos.append(Vector2((xfs[i] as Transform3D).origin.x, (xfs[i] as Transform3D).origin.z))
			var mmi := MultiMeshInstance3D.new()
			mmi.multimesh = mm
			mmi.material_override = m
			mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			mmi.visibility_range_end = 55.0
			add_child(mmi)
			_decor_nodes.append([mmi, pos])
	_decor.clear()


## Some com flores e tufos dentro de um quadrado (onde o ZodIA vai construir).
func clear_decor(c: Vector2, half: float) -> void:
	for entry in _decor_nodes:
		var mmi: MultiMeshInstance3D = entry[0]
		var pos: Array[Vector2] = entry[1]
		for i in pos.size():
			var d := pos[i] - c
			if absf(d.x) < half and absf(d.y) < half:
				mmi.multimesh.set_instance_transform(i, Transform3D(Basis().scaled(Vector3.ZERO), Vector3(pos[i].x, -1.0, pos[i].y)))


## Paredes invisiveis na borda: pecas derrubadas e brinquedos nao saem do campo.
func _build_walls() -> void:
	var body := StaticBody3D.new()
	add_child(body)
	var n := 160
	for i in n:
		var a := TAU * i / n
		var r := edge_r(a) - FADE * 0.6
		var cs := CollisionShape3D.new()
		var box := BoxShape3D.new()
		box.size = Vector3(TAU * r / n + 0.4, 6.0, 0.4)
		cs.shape = box
		cs.position = Vector3(cos(a) * r, 3.0, sin(a) * r)
		cs.rotation.y = -a + PI / 2.0
		body.add_child(cs)
