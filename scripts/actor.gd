class_name Actor
extends Node3D
## A character model, used both on the field and in battle: the party (Miasma's player model,
## assets/models/player/player.glb, dressed two ways) and the monsters (Miasma's skeleton and
## Hollow Wolf). Plays the model's own animations plus a few battle animations made here in code
## (the slashes, stance, guard, hurt, victory, knocked down) for the party.
##
## Models face -Z, like everything in Godot. Rotate the Actor to turn it.

const PLAYER_MODEL := "res://assets/models/player/player.glb"
const PLAYER_TEXTURE := "res://assets/models/player/player_s%d_h%d.png"
const WEAPON_DIR := "res://assets/models/weapons/"
const WEAPON_TEXTURE := "res://assets/models/weapons/weapons.png"
## Models rebuilt in Blender and their textures, made by tools/models/guard_hd.py. A hero or weapon
## with an "<id>_hd.glb" here uses it; the rest still use Miasma's models until they're rebuilt.
const HD_DIR := "res://assets/models/hd/"
## Where a weapon sits in the right hand (copied from Miasma's scripts/player_body.gd).
const GRIP := Vector3(-0.006, -0.072, 0.0)
const GRIP_BASIS := Basis(Vector3(1, 0, 0), Vector3(0, 0, -1), Vector3(0, 1, 0))

## How each party member is dressed: Miasma's appearance options (face, expression, hair, hair colour,
## beard, skin: indices into player_body.gd OPTIONS), the armor ids worn, and the weapon.
const DRESS := {
	"kael": {"face": 0, "expression": 2, "hair": 1, "hair_color": 2, "beard": 0, "skin": 2,
		"armor": ["leather_armor", "leather_greaves", "cloth_trousers", "satchel"], "weapon": "short_sword"},
	"guard": {"face": 1, "expression": 1, "hair": 0, "hair_color": 0, "beard": 2, "skin": 1,
		"armor": ["iron_helm", "chain_shirt", "iron_greaves", "cloth_trousers"], "weapon": "broadsword"},
}

## Monsters: "hd" = the rebuilt model (tools/models/*_hd.py), with its own animations unless "anims"
## names a model to borrow them from (the Skeleton keeps Miasma's skeleton.glb animations: same pivots).
const MONSTERS := {
	"skeleton": {"hd": "res://assets/models/hd/skeleton_hd.glb", "anims": "res://assets/models/skeleton/skeleton.glb", "scale": 1.0},
	"hollow_wolf": {"hd": "res://assets/models/hd/hollow_wolf_hd.glb", "scale": 1.0},
}
const LOOPS := ["idle", "walk", "run", "stance", "guard_hold", "down", "victory_hold"]

var kind := ""          # "kael", "guard", "skeleton", "hollow_wolf"
var is_hero := false
var model: Node3D
var anim: AnimationPlayer
var bones := {}         # bone name -> Node3D (rigid models; skinned ones use `skeleton`)
var skeleton: Skeleton3D  # the rig of a skinned model (rebuilt heroes, the Hollow Wolf)
var _materials: Array[ShaderMaterial] = []
var _meshes: Array[MeshInstance3D] = []
var _current := ""


static func make(id: String) -> Actor:
	var a := Actor.new()
	a.kind = id
	a.name = id.capitalize().replace(" ", "")
	a.is_hero = DRESS.has(id)
	if a.is_hero:
		a._build_hero()
	else:
		a._build_monster()
	return a


func _build_hero() -> void:
	if ResourceLoader.exists(HD_DIR + kind + "_hd.glb"):
		_build_hero_hd()
		return
	var d: Dictionary = DRESS[kind]
	model = (load(PLAYER_MODEL) as PackedScene).instantiate()
	add_child(model)
	_collect(model)
	var tex := PLAYER_TEXTURE % [d.skin, d.hair_color]
	if not ResourceLoader.exists(tex):
		tex = "res://assets/models/player/player.png"
	var mat := Materials.material(tex, {}, true)
	var glow := Materials.material(tex, {"self_lit": 1.0}, true)
	_materials.append_array([mat, glow])
	var worn := {}
	for id in d.armor:
		worn[id] = true
	var helmet: bool = worn.has("iron_helm") or worn.has("leather_cap")
	for mi in _meshes:
		var n := String(mi.name)
		var show := true
		if n.begins_with("face_"):
			show = n == "face_%d_%d" % [d.face, d.expression]
		elif n.begins_with("hair_"):
			var parts := n.split("__")
			show = parts[0] == "hair_%d" % d.hair and (parts.size() > 1 or not helmet)
		elif n.begins_with("beard_"):
			show = n == "beard_%d" % d.beard
		elif n.begins_with("armor_"):
			show = worn.has(n.substr(6).split("__")[0])
		elif n.begins_with("hand_"):
			show = n == "hand_grip_r" or n == "hand_open_l"
		elif n == "base_belt" or n == "base_pouch":
			show = not worn.has("chain_shirt")
		mi.visible = show
		mi.material_override = glow if n.contains("__glow") else mat
	_attach_weapon(d.weapon)
	_find_anim()
	_add_battle_anims()


## A rebuilt hero, skinned on the people's rig (tools/models/rig_kit.py): a Skeleton3D with the same bone
## names and pivots as player.glb, every bone's rest rotation the identity. player.glb's own animations
## (walk, run, idle...) are converted to Skeleton3D tracks, and the battle animations made below are built
## straight onto the bones.
func _build_hero_hd() -> void:
	model = (load(HD_DIR + kind + "_hd.glb") as PackedScene).instantiate()
	add_child(model)
	_collect(model)
	var mats := {}
	for mi in _meshes:
		_dress_hd(mi, mats)
	var found := model.find_children("*", "Skeleton3D", true, false)
	skeleton = found[0] if not found.is_empty() else null
	anim = AnimationPlayer.new()
	anim.name = "AnimationPlayer"
	model.add_child(anim)
	if skeleton:
		anim.root_node = anim.get_path_to(skeleton.get_parent())
		var lib := AnimationLibrary.new()
		var conv := _hero_animations(skeleton)
		for n in conv:
			lib.add_animation(n, conv[n])
		anim.add_animation_library("", lib)
	_attach_weapon(DRESS[kind].weapon)
	_find_anim()
	_add_battle_anims()


## player.glb's animations as Skeleton3D tracks (made once, shared by every rebuilt hero): a node track
## "root/hips/spine" becomes "<Skeleton3D>:spine". The rig's rest rotations are the identity and its bones
## sit at player.glb's pivots, so the keys carry over unchanged.
static var _hero_anim_cache := {}

static func _hero_animations(skel: Skeleton3D) -> Dictionary:
	var prefix := String(skel.name) + ":"
	if _hero_anim_cache.has(prefix):
		return _hero_anim_cache[prefix]
	var out := {}
	var src := (load(PLAYER_MODEL) as PackedScene).instantiate()
	var players := src.find_children("*", "AnimationPlayer", true, false)
	if not players.is_empty():
		var ap := players[0] as AnimationPlayer
		for n in ap.get_animation_list():
			var a := ap.get_animation(n)
			var b := Animation.new()
			b.length = a.length
			b.loop_mode = a.loop_mode
			for t in a.get_track_count():
				var path := a.track_get_path(t)
				var bone := String(path.get_name(path.get_name_count() - 1))
				if skel.find_bone(bone) < 0:
					continue
				var nt := b.add_track(a.track_get_type(t))
				b.track_set_path(nt, NodePath(prefix + bone))
				b.track_set_interpolation_type(nt, a.track_get_interpolation_type(t))
				for k in a.track_get_key_count(t):
					b.track_insert_key(nt, a.track_get_key_time(t, k), a.track_get_key_value(t, k), a.track_get_key_transition(t, k))
			out[n] = b
	src.free()
	_hero_anim_cache[prefix] = out
	return out


## A rebuilt model's mesh "<piece>__<material>" gets assets/models/hd/<material>.png (one material
## per kind per actor, so the hit flash reaches all of them).
func _dress_hd(mi: MeshInstance3D, mats: Dictionary) -> void:
	mi.material_override = _hd_material(String(mi.name), mats)
	if String(mi.name).ends_with("_fur"):
		# fur tufts (alpha cards) cast no shadow: their stripes would darken the whole body under them
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF


func _hd_material(mesh_name: String, mats: Dictionary) -> ShaderMaterial:
	var key := mesh_name.get_slice("__", 1)
	if key == "" or not ResourceLoader.exists(HD_DIR + key + ".png"):
		key = "iron"
	if not mats.has(key):
		var cut := key == "emblem" or key.ends_with("_rag") or key.ends_with("_fur") or key.ends_with("_cloth")
		var m := Materials.material(HD_DIR + key + ".png", {"double_sided": true, "alpha_cut": cut,
			"self_lit": 1.0 if key.ends_with("_glow") else 0.0}, true)
		mats[key] = m
		_materials.append(m)
	return mats[key]


func _attach_weapon(id: String) -> void:
	var hand: Node3D = bones.get("hand_r")
	if skeleton and skeleton.find_bone("hand_r") >= 0:
		var att := BoneAttachment3D.new()
		att.name = "HandR"
		skeleton.add_child(att)
		att.bone_name = "hand_r"
		hand = att
	if hand == null:
		return
	if ResourceLoader.exists(HD_DIR + id + "_hd.glb"):
		var hw: Node3D = (load(HD_DIR + id + "_hd.glb") as PackedScene).instantiate()
		hw.transform = Transform3D(GRIP_BASIS, GRIP)
		hand.add_child(hw)
		var mats := {}
		for mi in hw.find_children("*", "MeshInstance3D", true, false):
			_dress_hd(mi as MeshInstance3D, mats)
			_meshes.append(mi)
		return
	if not ResourceLoader.exists(WEAPON_DIR + id + ".glb"):
		return
	var w: Node3D = (load(WEAPON_DIR + id + ".glb") as PackedScene).instantiate()
	w.transform = Transform3D(GRIP_BASIS, GRIP)
	hand.add_child(w)
	var wmat := Materials.material(WEAPON_TEXTURE, {}, true)
	_materials.append(wmat)
	for mi in w.find_children("*", "MeshInstance3D", true, false):
		(mi as MeshInstance3D).material_override = wmat
		_meshes.append(mi)


func _build_monster() -> void:
	var m: Dictionary = MONSTERS[kind]
	model = (load(m.hd) as PackedScene).instantiate()
	model.scale = Vector3.ONE * float(m.scale)
	add_child(model)
	_collect(model)
	var mats := {}
	for mi in _meshes:
		_dress_hd(mi, mats)
	var found := model.find_children("*", "Skeleton3D", true, false)
	skeleton = found[0] if not found.is_empty() else null
	if m.has("anims"):
		var src := (load(m.anims) as PackedScene).instantiate()
		var players := src.find_children("*", "AnimationPlayer", true, false)
		if not players.is_empty():
			model.add_child((players[0] as AnimationPlayer).duplicate())
		src.free()
	_find_anim()


func _collect(n: Node) -> void:
	for c in n.get_children():
		if c is MeshInstance3D:
			_meshes.append(c)
		elif c is Node3D:
			bones[String(c.name)] = c
		_collect(c)


func _find_anim() -> void:
	var found := model.find_children("*", "AnimationPlayer", true, false)
	if found.is_empty():
		return
	anim = found[0]
	for n in LOOPS:
		if anim.has_animation(n):
			anim.get_animation(n).loop_mode = Animation.LOOP_LINEAR


# --- Playing ------------------------------------------------------------------------------------------

func play(anim_name: String, blend := 0.12, speed := 1.0) -> void:
	if anim == null or not anim.has_animation(anim_name):
		return
	if _current != anim_name or not anim.is_playing():
		_current = anim_name
		anim.play(anim_name, blend)
	anim.speed_scale = speed


## Plays an animation from the start, even if it is already playing.
func replay(anim_name: String, blend := 0.06, speed := 1.0) -> void:
	if anim == null or not anim.has_animation(anim_name):
		return
	_current = anim_name
	anim.play(anim_name, blend)
	anim.seek(0.0, true)
	anim.speed_scale = speed


func anim_length(anim_name: String) -> float:
	if anim == null or not anim.has_animation(anim_name):
		return 0.0
	return anim.get_animation(anim_name).length


func has_anim(anim_name: String) -> bool:
	return anim != null and anim.has_animation(anim_name)


## A white (or coloured) flash, for hits.
func flash(color := Color(1, 1, 1), time := 0.18) -> void:
	for m in _materials:
		m.set_shader_parameter("flash_color", Color(color.r, color.g, color.b, 0.85))
	var t := create_tween()
	t.tween_method(func(a: float) -> void:
		for m in _materials:
			m.set_shader_parameter("flash_color", Color(color.r, color.g, color.b, a)), 0.85, 0.0, time)


## Point of the model's chest, for damage numbers and prompts.
func chest_point() -> Vector3:
	var h := 1.25 if kind != "hollow_wolf" else 0.75
	return global_position + Vector3(0, h, 0)


## The bones fly apart (Miasma's skeleton death, which Cody loves). The pieces stay a while.
func scatter(away: Vector3, power := 3.0) -> void:
	var world := get_parent()
	for mi in _meshes.duplicate():
		if not mi.visible or not is_instance_valid(mi):
			continue
		var xf: Transform3D = mi.global_transform
		var aabb: AABB = mi.get_aabb()
		var body := RigidBody3D.new()
		body.collision_layer = 8
		body.collision_mask = 1
		body.mass = 0.3
		var shape := CollisionShape3D.new()
		var box := BoxShape3D.new()
		box.size = (aabb.size * xf.basis.get_scale()).clamp(Vector3.ONE * 0.04, Vector3.ONE * 0.6)
		shape.shape = box
		shape.position = aabb.get_center() * xf.basis.get_scale()
		body.add_child(shape)
		world.add_child(body)
		body.global_transform = Transform3D(xf.basis.orthonormalized(), xf.origin)
		mi.reparent(body, true)
		var dir := (away + Vector3(randf_range(-0.6, 0.6), randf_range(0.4, 1.2), randf_range(-0.6, 0.6))).normalized()
		body.apply_central_impulse(dir * power * body.mass * randf_range(0.6, 1.3))
		body.apply_torque_impulse(Vector3(randf_range(-1, 1), randf_range(-1, 1), randf_range(-1, 1)) * 0.05)
	model.visible = false


# --- The party's battle animations, made in code ----------------------------------------------------------
# Keys: time -> {bone: Vector3 euler degrees} ("hips_y" = hips height offset, metres).
# Bones turn like Miasma's model: +X on an arm or thigh swings it forward, +Z on the right arm lifts it
# out to the side (-Z for the left), +X on a forearm bends the elbow, -X on a shin bends the knee.

const READY := {"arm_r": Vector3(18, 0, 6), "forearm_r": Vector3(52, 8, 0), "hand_r": Vector3(-24, 0, 0),
	"arm_l": Vector3(8, 0, -10), "forearm_l": Vector3(30, 0, 0),
	"thigh_r": Vector3(12, 0, 6), "shin_r": Vector3(-20, 0, 0), "thigh_l": Vector3(-4, 0, -6), "shin_l": Vector3(-12, 0, 0),
	"spine": Vector3(6, 0, 0), "chest": Vector3(0, -8, 0), "hips_y": -0.04}

## The moment the blade connects in each slash (seconds from its start). The battle starts a slash
## this long before the hit's time.
const SLASH_HIT := {"atk_a": 0.2, "atk_b": 0.2, "atk_big": 0.32}


func _add_battle_anims() -> void:
	if anim == null:
		return
	var lib := anim.get_animation_library("")
	var hi := {"arm_r": Vector3(165, 0, 25), "forearm_r": Vector3(35, 0, 0), "hand_r": Vector3(-35, 0, 0),
		"chest": Vector3(-6, 28, 0), "spine": Vector3(-10, 0, 0), "arm_l": Vector3(40, 0, -30)}
	var down := {"arm_r": Vector3(35, 0, -25), "forearm_r": Vector3(15, 0, 0), "hand_r": Vector3(15, 0, 0),
		"chest": Vector3(8, -32, 0), "spine": Vector3(16, 0, 0), "arm_l": Vector3(-20, 0, -20), "hips_y": -0.1,
		"thigh_r": Vector3(35, 0, 4), "shin_r": Vector3(-40, 0, 0), "thigh_l": Vector3(-20, 0, -4)}
	lib.add_animation("atk_a", _pose_anim([[0.0, READY], [0.11, hi], [0.2, down], [0.42, READY]]))
	var side := {"arm_r": Vector3(85, 0, 75), "forearm_r": Vector3(25, 0, 0), "hand_r": Vector3(0, 0, -30),
		"chest": Vector3(0, 42, 0), "spine": Vector3(4, 0, 0), "arm_l": Vector3(30, 0, -15)}
	var across := {"arm_r": Vector3(85, 0, -40), "forearm_r": Vector3(10, 0, 0), "hand_r": Vector3(0, 0, 20),
		"chest": Vector3(4, -40, 0), "spine": Vector3(10, 0, 0), "arm_l": Vector3(-25, 0, -25),
		"thigh_r": Vector3(30, 0, 4), "shin_r": Vector3(-35, 0, 0), "hips_y": -0.08}
	lib.add_animation("atk_b", _pose_anim([[0.0, READY], [0.11, side], [0.2, across], [0.42, READY]]))
	var leap := hi.duplicate()
	leap["hips_y"] = 0.45
	leap["thigh_r"] = Vector3(60, 0, 6)
	leap["shin_r"] = Vector3(-90, 0, 0)
	leap["thigh_l"] = Vector3(30, 0, -6)
	leap["shin_l"] = Vector3(-70, 0, 0)
	var slam := down.duplicate()
	slam["hips_y"] = -0.22
	slam["thigh_r"] = Vector3(60, 0, 6)
	slam["shin_r"] = Vector3(-80, 0, 0)
	slam["thigh_l"] = Vector3(-30, 0, -6)
	slam["shin_l"] = Vector3(-30, 0, 0)
	lib.add_animation("atk_big", _pose_anim([[0.0, READY], [0.18, leap], [0.32, slam], [0.55, slam], [0.8, READY]]))
	var bob := READY.duplicate()
	bob["hips_y"] = -0.07
	lib.add_animation("stance", _pose_anim([[0.0, READY], [0.8, bob], [1.6, READY]]))
	var guard := READY.duplicate()
	guard.merge({"arm_r": Vector3(55, 0, -35), "forearm_r": Vector3(85, 0, 0), "hand_r": Vector3(0, 0, 60),
		"arm_l": Vector3(55, 0, 20), "forearm_l": Vector3(90, 0, 0), "spine": Vector3(14, 0, 0), "chest": Vector3(0, 0, 0)}, true)
	lib.add_animation("guard", _pose_anim([[0.0, READY], [0.1, guard], [0.5, guard]]))
	lib.add_animation("guard_hold", _pose_anim([[0.0, guard], [1.0, guard]]))
	var hurt := READY.duplicate()
	hurt.merge({"spine": Vector3(-16, 0, 0), "chest": Vector3(-12, 10, 0), "arm_r": Vector3(-10, 0, 30),
		"arm_l": Vector3(-10, 0, -30), "hips_y": -0.02}, true)
	lib.add_animation("hurt", _pose_anim([[0.0, READY], [0.06, hurt], [0.4, READY]]))
	var up := READY.duplicate()
	up.merge({"arm_r": Vector3(175, 0, 12), "forearm_r": Vector3(8, 0, 0), "hand_r": Vector3(-10, 0, 0),
		"arm_l": Vector3(0, 0, -15), "forearm_l": Vector3(10, 0, 0), "spine": Vector3(-4, 0, 0), "chest": Vector3(0, 0, 0),
		"hips_y": 0.0}, true)
	lib.add_animation("victory", _pose_anim([[0.0, READY], [0.3, up], [0.6, up]]))
	lib.add_animation("victory_hold", _pose_anim([[0.0, up], [1.0, up]]))
	var knelt := {"hips_y": -0.42, "thigh_r": Vector3(95, 0, 6), "shin_r": Vector3(-125, 0, 0),
		"thigh_l": Vector3(20, 0, -6), "shin_l": Vector3(-100, 0, 0), "spine": Vector3(35, 0, 0),
		"chest": Vector3(15, 0, 0), "arm_r": Vector3(-5, 0, 10), "forearm_r": Vector3(10, 0, 0), "arm_l": Vector3(5, 0, -10)}
	lib.add_animation("knocked_down", _pose_anim([[0.0, READY], [0.35, knelt]]))
	lib.add_animation("down", _pose_anim([[0.0, knelt], [1.0, knelt]]))
	var rise := READY.duplicate()
	lib.add_animation("revive", _pose_anim([[0.0, knelt], [0.4, rise]]))


## An Animation from pose keys: [[time, {bone: euler degrees, "hips_y": metres}], ...]. On a skinned
## model the tracks drive the Skeleton3D's bones (rest rotations are the identity, so the same angles work).
func _pose_anim(keys: Array) -> Animation:
	var a := Animation.new()
	a.length = float(keys[-1][0])
	var root := anim.get_node(anim.root_node)
	var names := {}
	for k in keys:
		for b in (k[1] as Dictionary).keys():
			names[b] = true
	for b in names.keys():
		var bone: String = "hips" if b == "hips_y" else b
		var path := NodePath()
		var base := Vector3.ZERO
		if skeleton:
			var i := skeleton.find_bone(bone)
			if i < 0:
				continue
			path = NodePath(String(root.get_path_to(skeleton)) + ":" + bone)
			base = skeleton.get_bone_rest(i).origin
		else:
			if not bones.has(bone):
				continue
			path = root.get_path_to(bones[bone])
			base = (bones[bone] as Node3D).position
		if b == "hips_y":
			var tr := a.add_track(Animation.TYPE_POSITION_3D)
			a.track_set_path(tr, path)
			var last := 0.0
			for k in keys:
				last = float((k[1] as Dictionary).get("hips_y", last))
				a.position_track_insert_key(tr, float(k[0]), base + Vector3(0, last, 0))
			continue
		var tr := a.add_track(Animation.TYPE_ROTATION_3D)
		a.track_set_path(tr, path)
		var last := Vector3.ZERO
		for k in keys:
			last = (k[1] as Dictionary).get(b, last)
			var e: Vector3 = last * (PI / 180.0)
			a.rotation_track_insert_key(tr, float(k[0]), Basis.from_euler(e, EULER_ORDER_YXZ).get_rotation_quaternion())
	return a
