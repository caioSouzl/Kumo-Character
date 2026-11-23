class_name Island
extends Node3D
## O campinho no meio do ciberespaco (referencia: pagina do cenario no Canva):
## grama viva com manchas claras e escuras, moitas com flores roxas, brancas,
## rosas e amarelas, pedras na borda, caminho de pedras chatas ate a plataforma
## do ZodIA, borda azul luminosa e chips de circuito em volta.
## A arvore com o terrario e os brinquedos vem de assets/models/ambiente.glb
## (Hyper3D). Sem o arquivo, entra uma arvore provisoria.

const RADIUS := 6.2
const TOP := 0.25
const GRASS_DARK := Color(0.16, 0.38, 0.14)
const GRASS_LIGHT := Color(0.45, 0.72, 0.22)
const BARK := Color(0.45, 0.28, 0.18)
const SOIL := Color(0.28, 0.19, 0.14)
const ROCK := Color(0.46, 0.45, 0.52)
const PATH_STONE := Color(0.72, 0.63, 0.5)
const FLOWERS := [Color(0.62, 0.38, 0.95), Color(0.95, 0.95, 1.0), Color(1.0, 0.5, 0.72), Color(1.0, 0.84, 0.25), Color(0.75, 0.55, 1.0)]
## Nome do no no .glb -> tipo de brinquedo
const GLB_TOYS := ["bola", "bloco", "carrinho", "argolas", "balanco"]

var toys: Array[Node3D] = []
var tree_pos := Vector3(0.3, TOP, -2.06)
var nest_pos := Vector3(0.32, TOP + 2.75, -2.06)
## Pulos do terrario ate o chao.
var descent_path: Array = []

var _rng := RandomNumberGenerator.new()
## Lugares ja ocupados (centro xz, raio), para nada nascer em cima de nada.
var _taken: Array = []


static func ground_y(p: Vector3) -> float:
	return TOP if Vector2(p.x, p.z).length() < RADIUS - 0.1 else 0.0


## Raio da borda num angulo (borda organica, nao um circulo perfeito).
static func edge_r(a: float) -> float:
	return RADIUS + sin(a * 3.0 + 0.7) * 0.18 + sin(a * 7.0 + 2.1) * 0.1 + sin(a * 13.0) * 0.05


func _ready() -> void:
	_rng.seed = 11
	var models: Dictionary = GameConfig.value("models", {})
	var n: Array = models.get("kumo_nest", [])
	if n.size() == 3:
		nest_pos = Vector3(float(n[0]), float(n[1]), float(n[2]))
	descent_path = [nest_pos + Vector3(1.2, -0.5, 1.0), nest_pos + Vector3(2.0, -1.8, 1.8), Vector3(nest_pos.x + 2.4, TOP, nest_pos.z + 2.7)]

	_build_ground()
	_build_rim()
	if not _load_glb(String(models.get("environment", ""))):
		_build_placeholder_tree()
		_build_placeholder_toys()
	_taken.append([Vector2(tree_pos.x, tree_pos.z), 1.9])
	for t in toys:
		_taken.append([Vector2(t.position.x, t.position.z), 0.9])
	_build_path()
	_build_rocks()
	_build_bushes_and_flowers()
	_build_grass()
	_build_collider()


# ---------- chao ----------

func _build_ground() -> void:
	var seg := 96
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for i in seg:
		var a0 := TAU * i / seg
		var a1 := TAU * (i + 1) / seg
		var p0 := Vector3(cos(a0) * edge_r(a0), TOP, sin(a0) * edge_r(a0))
		var p1 := Vector3(cos(a1) * edge_r(a1), TOP, sin(a1) * edge_r(a1))
		st.set_normal(Vector3.UP)
		st.add_vertex(Vector3(0, TOP, 0))
		st.add_vertex(p1)
		st.add_vertex(p0)
	var top := MeshInstance3D.new()
	top.mesh = st.commit()
	var gm := ShaderMaterial.new()
	gm.shader = load("res://shaders/grass.gdshader")
	top.material_override = gm
	top.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(top)

	# barranco de terra e pedra em volta
	var side := SurfaceTool.new()
	side.begin(Mesh.PRIMITIVE_TRIANGLES)
	for i in seg:
		var a0 := TAU * i / seg
		var a1 := TAU * (i + 1) / seg
		var t0 := Vector3(cos(a0) * edge_r(a0), TOP, sin(a0) * edge_r(a0))
		var t1 := Vector3(cos(a1) * edge_r(a1), TOP, sin(a1) * edge_r(a1))
		var b0 := Vector3(cos(a0) * (edge_r(a0) + 0.25), -0.3, sin(a0) * (edge_r(a0) + 0.25))
		var b1 := Vector3(cos(a1) * (edge_r(a1) + 0.25), -0.3, sin(a1) * (edge_r(a1) + 0.25))
		var c := SOIL.lerp(ROCK, 0.5 + 0.5 * sin(i * 1.7))
		st_quad(side, t0, t1, b1, b0, c)
	side.generate_normals()
	var sm := StandardMaterial3D.new()
	sm.vertex_color_use_as_albedo = true
	sm.roughness = 1.0
	var sides := MeshInstance3D.new()
	sides.mesh = side.commit()
	sides.material_override = sm
	add_child(sides)


func st_quad(st: SurfaceTool, a: Vector3, b: Vector3, c: Vector3, d: Vector3, col: Color) -> void:
	for v in [a, c, b, a, d, c]:
		st.set_color(col)
		st.add_vertex(v)


## Linha azul luminosa contornando o campo, como na referencia.
func _build_rim() -> void:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var seg := 128
	for i in seg:
		var a0 := TAU * i / seg
		var a1 := TAU * (i + 1) / seg
		var r0 := edge_r(a0) + 0.32
		var r1 := edge_r(a1) + 0.32
		var o0 := Vector3(cos(a0), 0, sin(a0))
		var o1 := Vector3(cos(a1), 0, sin(a1))
		st_quad(st, o0 * r0 + Vector3(0, 0.02, 0), o1 * r1 + Vector3(0, 0.02, 0), o1 * (r1 + 0.07) + Vector3(0, 0.02, 0), o0 * (r0 + 0.07) + Vector3(0, 0.02, 0), Color.WHITE)
	var rim := MeshInstance3D.new()
	rim.mesh = st.commit()
	var m := Mat.glow(Color(0.3, 0.7, 1.0), 3.0)
	m.cull_mode = BaseMaterial3D.CULL_DISABLED
	rim.material_override = m
	add_child(rim)


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
		tree_pos = tree.global_position
	for kind in GLB_TOYS:
		var t := env.find_child(kind, true, false) as Node3D
		if t:
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
	var local_nest := nest_pos - tree_pos
	Mat.add(tree, Mat.sphere(1.2, -1, 18), Mat.glass(Color(0.75, 0.9, 1.0), 0.18), local_nest + Vector3(0, 1.0, 0))
	Mat.add(tree, Mat.cyl(0.9, 0.5, 0.3, 14), bark, local_nest + Vector3(0, -0.1, 0))


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


func _toy_node(kind: String, pos: Vector3) -> Node3D:
	var t := Node3D.new()
	t.name = kind
	t.position = pos
	add_child(t)
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
			var r := _rng.randf_range(3.6, 5.0)
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

func _free_spot(min_r: float, max_r: float, clearance: float) -> Variant:
	for _i in 40:
		var a := _rng.randf() * TAU
		var r := sqrt(_rng.randf_range(min_r * min_r, max_r * max_r))
		r = minf(r, edge_r(a) - 0.25)
		var p := Vector2(cos(a) * r, sin(a) * r)
		var ok := true
		for t in _taken:
			if p.distance_to(t[0]) < float(t[1]) + clearance:
				ok = false
				break
		if ok:
			return Vector3(p.x, TOP, p.y)
	return null


## Caminho de pedras chatas da arvore ate a borda da frente (rumo a plataforma).
func _build_path() -> void:
	var stone := Mat.solid(PATH_STONE, 0.95)
	var start := Vector2(tree_pos.x + 0.2, tree_pos.z + 1.9)
	var end := Vector2(0.2, RADIUS - 0.4)
	var n := 7
	for i in n:
		var k := float(i) / (n - 1)
		var p := start.lerp(end, k) + Vector2(sin(i * 1.9) * 0.35, 0)
		var s := _rng.randf_range(0.32, 0.42)
		Mat.add(self, _rock_mesh(s, 0.07, 7), stone, Vector3(p.x, TOP + 0.015, p.y), Vector3(0, _rng.randf() * 360.0, 0))
		_taken.append([p, s + 0.1])


func _rock_mesh(r: float, h: float, segs: int) -> Mesh:
	var m := Mat.sphere(r, h * 2.0, segs)
	m.rings = 3
	return m


func _build_rocks() -> void:
	var cols := [ROCK, ROCK.darkened(0.15), Color(0.5, 0.5, 0.56)]
	var count := 0
	while count < 11:
		var spot: Variant = _free_spot(4.9, 6.0, 0.6) if count < 9 else _free_spot(1.8, 2.8, 0.3)
		if spot == null:
			count += 1
			continue
		var p: Vector3 = spot
		var s := _rng.randf_range(0.22, 0.42)
		var m := Mat.sphere(s, s * 1.6, 6)
		m.rings = 3
		Mat.add(self, m, Mat.solid(cols[count % cols.size()], 0.9), p + Vector3(0, s * 0.35, 0), Vector3(_rng.randf() * 20.0, _rng.randf() * 360.0, _rng.randf() * 20.0), Vector3(1.25, 0.8, 1.0))
		_taken.append([Vector2(p.x, p.z), s])
		count += 1


## Moitas de folhas largas com flores por cima, mais densas perto da borda.
func _build_bushes_and_flowers() -> void:
	var leaf_mesh := Mat.sphere(0.16, 0.06, 6)
	var flower_mesh := Mat.sphere(0.055, 0.05, 6)
	var leaves := _multimesh(leaf_mesh, 360)
	var flowers := _multimesh(flower_mesh, 300)
	var li := 0
	var fi := 0
	for c in 40:
		var near_edge := c < 26
		var spot: Variant = _free_spot(4.4 if near_edge else 1.4, 6.0 if near_edge else 4.4, 0.25)
		if spot == null:
			continue
		var p: Vector3 = spot
		var col: Color = FLOWERS[_rng.randi_range(0, FLOWERS.size() - 1)]
		for k in 9:
			if li >= 360:
				break
			var a := TAU * k / 9.0 + _rng.randf() * 0.4
			var b := Basis(Vector3.UP, PI / 2.0 - a) * Basis(Vector3.RIGHT, -0.5)
			var pos := p + Vector3(cos(a), 0, sin(a)) * 0.2 + Vector3(0, 0.12, 0)
			leaves.multimesh.set_instance_transform(li, Transform3D(b.scaled(Vector3(0.7, 1.0, 1.6) * _rng.randf_range(0.8, 1.3)), pos))
			leaves.multimesh.set_instance_color(li, GRASS_DARK.lerp(Color(0.25, 0.55, 0.2), _rng.randf()))
			li += 1
		var nf := _rng.randi_range(4, 8)
		for k in nf:
			if fi >= 300:
				break
			var off := Vector3(_rng.randf_range(-0.35, 0.35), _rng.randf_range(0.22, 0.4), _rng.randf_range(-0.35, 0.35))
			flowers.multimesh.set_instance_transform(fi, Transform3D(Basis().scaled(Vector3.ONE * _rng.randf_range(0.8, 1.3)), p + off))
			flowers.multimesh.set_instance_color(fi, col.lightened(_rng.randf() * 0.15))
			fi += 1
		_taken.append([Vector2(p.x, p.z), 0.45])
	leaves.multimesh.visible_instance_count = li
	flowers.multimesh.visible_instance_count = fi
	# flores soltas pelo campo
	var loose := _multimesh(flower_mesh, 90)
	var stems := _multimesh(Mat.cyl(0.01, 0.01, 0.18, 4), 90)
	var n := 0
	for i in 90:
		var spot: Variant = _free_spot(1.2, 5.9, 0.05)
		if spot == null:
			continue
		var p: Vector3 = spot
		stems.multimesh.set_instance_transform(n, Transform3D(Basis(), p + Vector3(0, 0.09, 0)))
		stems.multimesh.set_instance_color(n, Color(0.25, 0.55, 0.2))
		loose.multimesh.set_instance_transform(n, Transform3D(Basis(), p + Vector3(0, 0.19, 0)))
		loose.multimesh.set_instance_color(n, FLOWERS[i % FLOWERS.size()])
		n += 1
	loose.multimesh.visible_instance_count = n
	stems.multimesh.visible_instance_count = n


## Tufos de grama.
func _build_grass() -> void:
	var tufts := _multimesh(Mat.cyl(0.0, 0.05, 0.2, 4), 260)
	var n := 0
	for i in 260:
		var spot: Variant = _free_spot(0.8, 6.1, -0.2)
		if spot == null:
			continue
		var p: Vector3 = spot
		var b := Basis(Vector3(1, 0, 0), _rng.randf_range(-0.25, 0.25)) * Basis(Vector3.UP, _rng.randf() * TAU)
		tufts.multimesh.set_instance_transform(n, Transform3D(b.scaled(Vector3.ONE * _rng.randf_range(0.7, 1.5)), p + Vector3(0, 0.09, 0)))
		tufts.multimesh.set_instance_color(n, GRASS_DARK.lerp(GRASS_LIGHT, _rng.randf()))
		n += 1
	tufts.multimesh.visible_instance_count = n


func _multimesh(mesh: Mesh, count: int) -> MultiMeshInstance3D:
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.use_colors = true
	mm.mesh = mesh
	mm.instance_count = count
	var mmi := MultiMeshInstance3D.new()
	mmi.multimesh = mm
	var m := StandardMaterial3D.new()
	m.vertex_color_use_as_albedo = true
	m.roughness = 1.0
	mmi.material_override = m
	mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(mmi)
	return mmi


func _build_collider() -> void:
	var body := StaticBody3D.new()
	var cs := CollisionShape3D.new()
	var shape := CylinderShape3D.new()
	shape.radius = RADIUS
	shape.height = TOP * 2.0
	cs.shape = shape
	body.add_child(cs)
	add_child(body)
