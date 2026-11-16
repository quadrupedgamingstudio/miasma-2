extends Node
## Rig check: each model frozen in key poses (walk and run mid-stride, the slashes, knocked down, the
## monsters' strikes and deaths), from the front three-quarters and the side, so joints can be checked.
## Run: tools/test/shoot.sh shot_rig   (RIG=guard,kael picks the models; default: all four)
var out := "user://shots/"

const POSES := {
	"hero": [["idle", 0.5], ["walk", 0.26], ["run", 0.17], ["atk_a", 0.11], ["atk_b", 0.2], ["atk_big", 0.18],
		["atk_big", 0.4], ["guard", 0.3], ["hurt", 0.06], ["knocked_down", 0.35], ["victory", 0.6]],
	"monster": [["idle", 0.6], ["walk", 0.2], ["run", 0.1], ["alert", 0.5], ["windup", 0.4], ["strike", 0.12],
		["stagger", 0.15], ["recover", 0.2], ["death", 0.5], ["death", 9.0]],
}


func _ready() -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(out))
	await get_tree().create_timer(0.5).timeout
	var old := get_tree().current_scene
	var root := Node3D.new()
	root.name = "RigStage"
	get_tree().root.add_child(root)
	get_tree().current_scene = root
	old.queue_free()
	Look.setup(root)
	var ground := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(20, 20)
	ground.mesh = plane
	ground.material_override = Materials.material("res://assets/textures/forest_grass.png", {"uv_scale": Vector2(10, 10)})
	root.add_child(ground)
	var floor_body := StaticBody3D.new()
	var floor_shape := CollisionShape3D.new()
	floor_shape.shape = WorldBoundaryShape3D.new()
	floor_body.add_child(floor_shape)
	root.add_child(floor_body)
	var cam := Camera3D.new()
	cam.fov = 32.0
	root.add_child(cam)
	cam.current = true
	var kinds := OS.get_environment("RIG").split(",", false)
	if kinds.is_empty():
		kinds = PackedStringArray(["guard", "kael", "hollow_wolf", "skeleton"])
	for kind in kinds:
		var a := Actor.make(kind)
		root.add_child(a)
		a.rotation.y = PI   # face the camera (+Z)
		var poses: Array = POSES["hero" if a.is_hero else "monster"]
		var tall := a.is_hero or kind == "skeleton"
		var h := 1.0 if tall else 0.55
		var d := 3.4 if tall else 2.8
		for p in poses:
			if not a.has_anim(p[0]):
				continue
			a.anim.play(p[0], 0.0)
			a.anim.seek(minf(p[1], a.anim_length(p[0])), true)
			a.anim.pause()
			for view in [["q", Vector3(-d * 0.62, h + 0.35, d * 0.78)], ["s", Vector3(d, h + 0.15, 0.0)]]:
				cam.global_position = view[1]
				cam.look_at(Vector3(0, h, 0), Vector3.UP)
				await get_tree().process_frame
				await get_tree().process_frame
				await get_tree().process_frame
				_shot("%s_%s_%d_%s" % [kind, p[0], int(p[1] * 100), view[0]])
		if kind == "skeleton":
			# the bones fly apart (Actor.scatter), like a kill in battle
			a.anim.play("idle", 0.0)
			await get_tree().process_frame
			a.scatter(Vector3(0, 0, -1) + Vector3.UP * 0.5, 3.5)
			for t in [0.15, 1.5]:
				await get_tree().create_timer(t).timeout
				cam.global_position = Vector3(-2.2, 1.6, 3.2)
				cam.look_at(Vector3(0, 0.5, 0), Vector3.UP)
				await get_tree().process_frame
				_shot("%s_scatter_%d_q" % [kind, int(t * 100)])
		a.queue_free()
		await get_tree().process_frame
	get_tree().quit()


func _shot(n: String) -> void:
	get_viewport().get_texture().get_image().save_png(ProjectSettings.globalize_path(out) + n + ".png")
	print("SHOT ", n)
