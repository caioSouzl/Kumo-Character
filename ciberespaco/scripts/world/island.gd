class_name Island
extends Node3D
## O campinho no meio do ciberespaco: grama com flores, pedras, brinquedos nas
## bordas e o tronco retorcido com o terrario onde o Kumo dorme.
## Se existir assets/models/ambiente.glb (Hyper3D), ele substitui grama, arvore,
## flores e pedras; os brinquedos interativos continuam.

const RADIUS := 5.0
const TOP := 0.2
const GRASS := Color(0.27, 0.55, 0.25)
const GRASS_DARK := Color(0.18, 0.4, 0.2)
const BARK := Color(0.42, 0.27, 0.17)
const BARK_DARK := Color(0.3, 0.19, 0.12)
const STONE := Color(0.5, 0.5, 0.56)

var toys: Array[Node3D] = []
var nest_pos := Vector3(0.0, 4.2, -0.8)
## Pulos do terrario ate o chao.
var descent_path: Array = [Vector3(0.95, 2.95, -0.3), Vector3(1.65, 1.22, 0.35), Vector3(2.1, TOP, 1.3)]

var _nature: Node3D
var _rng := RandomNumberGenerator.new()


static func ground_y(p: Vector3) -> float:
	return TOP if Vector2(p.x, p.z).length() < RADIUS else 0.0


func _ready() -> void:
	_rng.seed = 7
	var models: Dictionary = GameConfig.value("models", {})
	var n: Array = models.get("kumo_nest", [nest_pos.x, nest_pos.y, nest_pos.z])
	nest_pos = Vector3(float(n[0]), float(n[1]), float(n[2]))

	_nature = Node3D.new()
	add_child(_nature)
	var glb := ModelSlot.try_load(String(models.get("environment", "")), 1.0)
	if glb:
		var fp := ModelSlot.footprint(glb)
		if fp > 0.0001:
			glb.scale = Vector3.ONE * (float(models.get("environment_radius", RADIUS)) / fp)
		add_child(glb)
		_nature.visible = false
	_build_ground()
	_build_tree()
	_build_flowers()
	_build_rocks()
	_build_toys()
	_build_collider()


func _build_ground() -> void:
	Mat.add(_nature, Mat.cyl(RADIUS, RADIUS, 0.12, 48), Mat.solid(GRASS, 1.0), Vector3(0, 0.14, 0))
	Mat.add(_nature, Mat.cyl(RADIUS + 0.08, RADIUS + 0.12, 0.1, 48), Mat.solid(Color(0.35, 0.24, 0.16), 1.0), Vector3(0, 0.05, 0))
	# borda luminosa que liga o campo ao circuito
	Mat.add(self, Mat.torus(RADIUS + 0.12, RADIUS + 0.2), Mat.glow(Color(0.3, 0.8, 1.0), 2.2), Vector3(0, 0.01, 0), Vector3.ZERO, Vector3(1, 0.15, 1))


func _build_tree() -> void:
	var tree := Node3D.new()
	tree.position = Vector3(nest_pos.x, TOP, nest_pos.z)
	_nature.add_child(tree)
	var bark := Mat.solid(BARK, 0.95)
	var bark_dark := Mat.solid(BARK_DARK, 1.0)
	# raizes
	for i in 5:
		var a := TAU * i / 5.0 + 0.4
		var root := Mat.add(tree, Mat.cyl(0.08, 0.22, 1.1, 8), bark_dark, Vector3(cos(a) * 0.62, 0.15, sin(a) * 0.62))
		root.rotation = Vector3(0, -a, deg_to_rad(62))
	# tronco retorcido: segmentos girando e afinando
	for i in 8:
		var k := i / 7.0
		var r := lerpf(0.72, 0.45, k)
		var y := 0.25 + i * 0.44
		var off := Vector3(sin(i * 0.9) * 0.18, 0, cos(i * 1.1) * 0.1)
		Mat.add(tree, Mat.cyl(r * 0.92, r, 0.5, 10), bark if i % 2 == 0 else bark_dark, Vector3(0, y, 0) + off, Vector3(sin(i * 1.3) * 10.0, i * 31.0, cos(i * 0.9) * 10.0))
	# galho com folhas (degrau da descida)
	Mat.add(tree, Mat.cyl(0.08, 0.16, 1.2, 8), bark, Vector3(0.55, 2.55, 0.3), Vector3(0, 0, -55))
	var leaves := Mat.solid(GRASS_DARK, 1.0)
	Mat.add(tree, Mat.sphere(0.45, 0.5, 12), leaves, Vector3(0.95, 2.72, 0.5))
	Mat.add(tree, Mat.cyl(0.12, 0.18, 1.0, 8), bark, Vector3(-0.6, 2.0, -0.2), Vector3(0, 0, 50))
	Mat.add(tree, Mat.sphere(0.5, 0.55, 12), leaves, Vector3(-1.05, 2.4, -0.25))
	# toco-degrau perto da arvore
	var stump := nest_pos + Vector3(1.65, 0, 1.15)
	Mat.add(_nature, Mat.cyl(0.36, 0.42, 1.0, 10), bark, Vector3(stump.x, TOP + 0.5, stump.z))
	Mat.add(_nature, Mat.cyl(0.33, 0.33, 0.02, 10), Mat.solid(Color(0.7, 0.55, 0.35), 1.0), Vector3(stump.x, TOP + 1.01, stump.z))
	# terrario: tigela de casca, musgo e cupula de vidro
	var nest_local := Vector3(0, nest_pos.y - TOP, 0)
	Mat.add(tree, Mat.cyl(0.95, 0.5, 0.45, 14), bark, nest_local + Vector3(0, -0.28, 0))
	Mat.add(tree, Mat.cyl(0.88, 0.88, 0.04, 14), Mat.solid(Color(0.32, 0.6, 0.3), 1.0), nest_local + Vector3(0, -0.06, 0))
	var dome := SphereMesh.new()
	dome.radius = 0.92
	dome.height = 0.92
	dome.is_hemisphere = true
	dome.radial_segments = 18
	dome.rings = 8
	Mat.add(tree, dome, Mat.glass(Color(0.6, 0.9, 1.0), 0.16), nest_local + Vector3(0, -0.06, 0), Vector3.ZERO, Vector3(1, 1.15, 1))
	Mat.add(tree, Mat.torus(0.9, 0.97), Mat.glow(Color(0.35, 0.85, 1.0), 1.5), nest_local + Vector3(0, -0.06, 0))


func _rand_spot(min_r: float, max_r: float) -> Vector3:
	for _i in 30:
		var a := _rng.randf() * TAU
		var r := sqrt(_rng.randf_range(min_r * min_r, max_r * max_r))
		var p := Vector3(cos(a) * r, TOP, sin(a) * r)
		if p.distance_to(Vector3(nest_pos.x, TOP, nest_pos.z)) > 1.3:
			return p
	return Vector3(min_r, TOP, 0)


func _build_flowers() -> void:
	var colors := [Color(1.0, 0.55, 0.75), Color(1.0, 0.85, 0.3), Color(0.95, 0.95, 1.0), Color(0.7, 0.55, 1.0), Color(1.0, 0.45, 0.35)]
	var heads := _multimesh(Mat.sphere(0.07, 0.09, 8), 60)
	var stems := _multimesh(Mat.cyl(0.012, 0.012, 0.22, 4), 60)
	var tufts := _multimesh(Mat.cyl(0.0, 0.08, 0.22, 5), 140)
	for i in 60:
		var p := _rand_spot(1.2, 4.75)
		stems.multimesh.set_instance_transform(i, Transform3D(Basis(), p + Vector3(0, 0.11, 0)))
		stems.multimesh.set_instance_color(i, Color(0.25, 0.6, 0.25))
		heads.multimesh.set_instance_transform(i, Transform3D(Basis(), p + Vector3(0, 0.23, 0)))
		heads.multimesh.set_instance_color(i, colors[i % colors.size()])
	for i in 140:
		var p := _rand_spot(0.9, 4.9)
		var b := Basis(Vector3.UP, _rng.randf() * TAU).scaled(Vector3.ONE * _rng.randf_range(0.7, 1.4))
		tufts.multimesh.set_instance_transform(i, Transform3D(b, p + Vector3(0, 0.1, 0)))
		tufts.multimesh.set_instance_color(i, GRASS_DARK.lerp(Color(0.4, 0.75, 0.35), _rng.randf()))


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
	_nature.add_child(mmi)
	return mmi


func _build_rocks() -> void:
	var stone := Mat.solid(STONE, 0.9)
	for i in 7:
		var p := _rand_spot(2.0, 4.6)
		var s := _rng.randf_range(0.18, 0.4)
		Mat.add(_nature, Mat.sphere(s, s * 1.2, 8), stone, p + Vector3(0, s * 0.25, 0), Vector3(0, _rng.randf() * 360.0, 0), Vector3(1.3, 0.8, 1.0))
	# pedras-caminho ate a borda virada para a plataforma do ZodIA
	for i in 4:
		Mat.add(_nature, Mat.cyl(0.32, 0.36, 0.06, 10), stone, Vector3(0.35 * (1 if i % 2 == 0 else -1), TOP + 0.02, 2.6 + i * 0.6))


func _build_toys() -> void:
	var ball := _toy("bola", Vector3(3.1, TOP, 1.7))
	Mat.add(ball, Mat.sphere(0.24, -1, 14), Mat.solid(Color(0.95, 0.3, 0.3), 0.5), Vector3(0, 0.24, 0))
	Mat.add(ball, Mat.torus(0.22, 0.25), Mat.solid(Color.WHITE, 0.5), Vector3(0, 0.24, 0), Vector3(90, 0, 0))

	var blocks := _toy("blocos", Vector3(-3.3, TOP, 1.0))
	var cols := [Color(0.3, 0.6, 1.0), Color(1.0, 0.8, 0.3), Color(0.5, 0.85, 0.45)]
	for i in 3:
		var bl := Mat.add(blocks, Mat.box(Vector3(0.3, 0.3, 0.3)), Mat.solid(cols[i], 0.7), Vector3(0.02 * i, 0.15 + i * 0.3, 0), Vector3(0, i * 20.0, 0))
		bl.name = "bloco%d" % i

	var car := _toy("carrinho", Vector3(-2.1, TOP, 3.1))
	Mat.add(car, Mat.box(Vector3(0.55, 0.18, 0.32)), Mat.solid(Color(0.3, 0.45, 0.95), 0.5), Vector3(0, 0.17, 0))
	Mat.add(car, Mat.box(Vector3(0.3, 0.14, 0.28)), Mat.solid(Color(0.85, 0.9, 1.0), 0.3), Vector3(-0.04, 0.32, 0))
	for x in [-0.18, 0.18]:
		for z in [-0.17, 0.17]:
			Mat.add(car, Mat.cyl(0.08, 0.08, 0.05, 10), Mat.solid(Color(0.15, 0.15, 0.2), 0.8), Vector3(x, 0.08, z), Vector3(90, 0, 0))

	var top := _toy("piao", Vector3(2.8, TOP, -2.3))
	Mat.add(top, Mat.cyl(0.24, 0.0, 0.3, 12), Mat.solid(Color(0.75, 0.4, 1.0), 0.5), Vector3(0, 0.17, 0))
	Mat.add(top, Mat.cyl(0.24, 0.24, 0.08, 12), Mat.solid(Color(1.0, 0.85, 0.35), 0.5), Vector3(0, 0.36, 0))
	Mat.add(top, Mat.cyl(0.03, 0.03, 0.14, 6), Mat.solid(Color(0.3, 0.2, 0.15), 0.5), Vector3(0, 0.46, 0))


func _toy(kind: String, pos: Vector3) -> Node3D:
	var t := Node3D.new()
	t.name = kind
	t.set_meta("kind", kind)
	t.set_meta("home", pos)
	t.position = pos
	add_child(t)
	toys.append(t)
	return t


## O brinquedo reage quando o Kumo brinca com ele.
func toy_react(t: Node3D) -> void:
	var kind := String(t.get_meta("kind", ""))
	var tw := create_tween()
	match kind:
		"bola":
			var a := atan2(t.position.z, t.position.x) + _rng.randf_range(-0.6, 0.6)
			var r := _rng.randf_range(2.8, 4.2)
			var dest := Vector3(cos(a) * r, TOP, sin(a) * r)
			tw.set_parallel(true)
			tw.tween_property(t, "position", dest, 1.2).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
			tw.tween_property(t, "rotation:x", t.rotation.x + TAU * 1.5, 1.2)
		"blocos":
			var top := t.get_node_or_null("bloco2") as Node3D
			if top:
				tw.tween_property(top, "rotation:z", 0.5, 0.25)
				tw.tween_property(top, "rotation:z", -0.35, 0.25)
				tw.tween_property(top, "rotation:z", 0.0, 0.3)
		"carrinho":
			var home: Vector3 = t.get_meta("home")
			var fwd := Vector3(cos(t.rotation.y), 0, -sin(t.rotation.y)) * 0.9
			tw.tween_property(t, "position", home + fwd, 0.7).set_trans(Tween.TRANS_SINE)
			tw.tween_property(t, "position", home, 0.9).set_trans(Tween.TRANS_SINE)
		"piao":
			tw.tween_property(t, "rotation:y", t.rotation.y + TAU * 6.0, 2.5).set_ease(Tween.EASE_OUT).set_trans(Tween.TRANS_QUAD)


func _build_collider() -> void:
	var body := StaticBody3D.new()
	var cs := CollisionShape3D.new()
	var shape := CylinderShape3D.new()
	shape.radius = RADIUS
	shape.height = TOP * 2.0
	cs.shape = shape
	body.add_child(cs)
	add_child(body)
