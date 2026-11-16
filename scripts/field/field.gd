class_name Field
extends Node3D
## The walkable area: a stretch of Emberwick's outskirts a while after the Great Lich fell. The
## ground near the village is green again; out toward the edges it is still grey and the last of
## the Miasma hangs in walls of mist. Two monsters roam it; touching one starts a battle.
## Everything is built in code (WorldKit), so it can be regenerated or tweaked here.

const SIZE := 34.0          # the area runs from -SIZE to SIZE on x and z
const START := Vector3(0, 0, 18)

var leader: Leader
var follower: Follower
var cam: FieldCamera
var hud: FieldHud
var _fire: Node3D
var _fire_t := 0.0
var _rng := RandomNumberGenerator.new()


func _ready() -> void:
	_rng.seed = 7
	Look.setup(self)
	_build_world()
	_spawn_party()
	_spawn_monsters()
	hud = FieldHud.new()
	add_child(hud)
	if Game.battle_result == "":
		hud.banner("Emberwick Outskirts")
	Game.battle_result = ""
	var amb := AudioStreamPlayer.new()
	amb.stream = load("res://assets/sounds/amb_forest.wav")
	amb.volume_db = -10.0
	add_child(amb)
	amb.play()
	amb.finished.connect(amb.play)
	await Game.transition.fade_in()


# --- The land ---------------------------------------------------------------------------------------

## Ground height: gentle rolls, rising into hills at the edges so the area feels closed in.
static func height_at(x: float, z: float) -> float:
	var h := sin(x * 0.17) * 0.35 + cos(z * 0.13 + x * 0.05) * 0.45 + sin((x + z) * 0.31) * 0.12
	var edge := maxf(absf(x), absf(z)) - (SIZE - 7.0)
	if edge > 0.0:
		h += edge * edge * 0.22
	# the road is a little flatter
	var rd := absf(x - road_x(z))
	if rd < 2.0:
		h = lerpf(h * 0.4, h, rd / 2.0)
	return h


## The old road winds north-south through the area, toward Emberwick (south).
static func road_x(z: float) -> float:
	return sin(z * 0.09) * 4.0 - 1.0


## 1 = healthy (near the village, south) .. 0 = still scarred (north, the edges).
static func heal_at(x: float, z: float) -> float:
	var t := (z + SIZE) / (SIZE * 2.0)
	var edge := clampf((maxf(absf(x), absf(z)) - (SIZE - 12.0)) / 10.0, 0.0, 1.0)
	return clampf(t * 1.25 - 0.1 - edge * 0.5 + sin(x * 0.4) * 0.08, 0.0, 1.0)


func _build_world() -> void:
	var g := WorldKit.ground(-SIZE - 10, -SIZE - 10, SIZE + 10, SIZE + 10, 1.0, height_at,
		func(x: float, z: float) -> String: return "dirt" if absf(x - road_x(z)) < 1.3 else "grass", heal_at,
		func(x: float, z: float) -> float: return 1.0 - smoothstep(0.8, 1.8, absf(x - road_x(z))))
	add_child(g[0])
	add_child(g[1])
	add_child(WorldKit.sky(Color(0.42, 0.52, 0.72), Tuning.FOG_COLOR))

	# dead trees out in the scarred land, saplings where it is healing
	for i in 70:
		var p := Vector3(_rng.randf_range(-SIZE - 6, SIZE + 6), 0, _rng.randf_range(-SIZE - 6, SIZE + 6))
		if absf(p.x - road_x(p.z)) < 3.0 or p.distance_to(START) < 5.0 or Vector2(p.x - 6, p.z - 4).length() < 4.0:
			continue
		var heal := heal_at(p.x, p.z)
		var tree: Node3D
		if _rng.randf() < heal * 0.8:
			tree = WorldKit.sapling(_rng, _rng.randf_range(2.2, 3.6))
		else:
			tree = WorldKit.dead_tree(_rng, _rng.randf_range(4.0, 7.0))
		tree.position = Vector3(p.x, height_at(p.x, p.z) - 0.1, p.z)
		tree.rotation.y = _rng.randf() * TAU
		add_child(tree)
	for i in 18:
		var p := Vector3(_rng.randf_range(-SIZE, SIZE), 0, _rng.randf_range(-SIZE, SIZE))
		if absf(p.x - road_x(p.z)) < 2.5 or p.distance_to(START) < 4.0:
			continue
		var r := WorldKit.rock(_rng, _rng.randf_range(0.5, 1.3))
		r.position = Vector3(p.x, height_at(p.x, p.z), p.z)
		r.rotation.y = _rng.randf() * TAU
		add_child(r)

	# grass tufts, thicker where it's healthy
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for i in 900:
		var x := _rng.randf_range(-SIZE, SIZE)
		var z := _rng.randf_range(-SIZE, SIZE)
		if absf(x - road_x(z)) < 1.5 or _rng.randf() > heal_at(x, z) + 0.15:
			continue
		WorldKit.grass_tuft(st, Vector3(x, height_at(x, z) - 0.05, z), _rng.randf_range(0.4, 0.8), _rng.randf() * PI)
	var tufts := MeshInstance3D.new()
	tufts.mesh = st.commit()
	tufts.material_override = WorldKit.tuft_material()
	add_child(tufts)

	# Emberwick's old palisade, south, along the road's end
	for side in [-1, 1]:
		var s := WorldKit.stakes(_rng, 14)
		var x0: float = road_x(SIZE - 3) + side * 3.0 + (0.0 if side > 0 else -14 * 0.55)
		s.position = Vector3(x0, height_at(x0, SIZE - 3), SIZE - 3)
		add_child(s)
	var sign := WorldKit.signpost()
	sign.position = Vector3(road_x(12) + 2.2, height_at(road_x(12) + 2.2, 12), 12)
	sign.rotation.y = 0.3
	add_child(sign)
	var c := WorldKit.cart()
	c.position = Vector3(road_x(-6) + 3.0, height_at(road_x(-6) + 3.0, -6) + 0.05, -6)
	c.rotation.y = 0.6
	add_child(c)
	# stakes left out in the field, from the old outer ring
	for i in 4:
		var s := WorldKit.stakes(_rng, 3 + _rng.randi() % 3)
		var x := _rng.randf_range(-SIZE + 8, SIZE - 8)
		var z := _rng.randf_range(-SIZE + 8, 4)
		if absf(x - road_x(z)) < 3.0:
			x += 6.0
		s.position = Vector3(x, height_at(x, z), z)
		s.rotation.y = _rng.randf() * TAU
		add_child(s)

	# the campfire: rest here to heal
	_fire = WorldKit.campfire(_rng)
	_fire.position = Vector3(6, height_at(6, 4), 4)
	add_child(_fire)
	var rest := Area3D.new()
	rest.name = "RestArea"
	var cs := CollisionShape3D.new()
	var sph := SphereShape3D.new()
	sph.radius = 1.8
	cs.shape = sph
	rest.add_child(cs)
	rest.collision_mask = 2
	_fire.add_child(rest)
	rest.body_entered.connect(_on_rest)

	# the last of the miasma: mist walls ringing the north and the sides, and invisible walls
	for i in 12:
		var a := -PI + TAU * i / 12.0
		var r := SIZE - 3.0
		var p := Vector3(sin(a) * r, 0, -cos(a) * r)
		if p.z > SIZE * 0.5:
			continue
		var m := WorldKit.mist(16.0, 7.0)
		m.position = Vector3(p.x, height_at(p.x, p.z) - 1.0, p.z)
		m.rotation.y = -a
		add_child(m)
	for w in [[Vector3(0, 0, -SIZE), Vector3(SIZE * 2, 20, 1)], [Vector3(0, 0, SIZE), Vector3(SIZE * 2, 20, 1)],
			[Vector3(-SIZE, 0, 0), Vector3(1, 20, SIZE * 2)], [Vector3(SIZE, 0, 0), Vector3(1, 20, SIZE * 2)]]:
		var body := StaticBody3D.new()
		var shape := CollisionShape3D.new()
		var b := BoxShape3D.new()
		b.size = w[1]
		shape.shape = b
		body.add_child(shape)
		body.position = w[0]
		add_child(body)


func _process(delta: float) -> void:
	_fire_t += delta
	var flick := 1.4 + sin(_fire_t * 11.0) * 0.15 + sin(_fire_t * 23.0) * 0.1
	Materials.set_light(0, _fire.global_position + Vector3(0, 0.8, 0), flick, Color(1.0, 0.6, 0.3), 6.0)
	var flame := _fire.get_node("Flame") as MeshInstance3D
	flame.scale = Vector3(1.0, 0.9 + sin(_fire_t * 9.0) * 0.12, 1.0)


func _on_rest(body: Node) -> void:
	if body == leader:
		Game.heal_party()
		Game.draughts = maxi(Game.draughts, Tuning.START_DRAUGHTS)
		Game.sfx("torch", -6.0)
		hud.toast("The party rests by the fire. HP restored.")


# --- The party and the monsters -------------------------------------------------------------------------

func _spawn_party() -> void:
	leader = Leader.new()
	leader.name = "Leader"
	add_child(leader)
	var pos: Vector3 = Game.field_return.get("position", START)
	leader.global_position = Vector3(pos.x, height_at(pos.x, pos.z) + 0.1, pos.z)
	leader.rotation.y = Game.field_return.get("yaw", 0.0)
	follower = Follower.new()
	follower.name = "Follower"
	follower.leader = leader
	add_child(follower)
	cam = FieldCamera.new()
	cam.target = leader
	cam.yaw = Game.field_return.get("cam_yaw", 0.0)
	add_child(cam)
	leader.cam = cam
	cam.snap()


func _spawn_monsters() -> void:
	var spots := {"WolfA": [Vector3(-9, 0, 0), "wolf", "hollow_wolf"], "Pair": [Vector3(3, 0, -16), "pair", "skeleton"]}
	for n in spots:
		if Game.defeated.has(n):
			continue
		var m := FieldMonster.new()
		m.name = n
		m.encounter = spots[n][1]
		m.look = spots[n][2]
		m.home = spots[n][0]
		m.leader = leader
		if Game.fled_from == n:
			m.grace = Tuning.FLEE_GRACE
		add_child(m)
		var h: Vector3 = spots[n][0]
		m.global_position = Vector3(h.x, height_at(h.x, h.z), h.z)
	Game.fled_from = ""
	if Game.defeated.size() >= spots.size():
		hud_later("The outskirts are quiet again.")


func hud_later(text: String) -> void:
	await get_tree().create_timer(1.0).timeout
	if hud:
		hud.toast(text)
