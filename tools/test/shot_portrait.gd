extends Node
## Close-ups of the party in the battle arena: the Guard's face, front, three-quarters, side and back,
## and Kael and the Guard together. Run: tools/test/shoot.sh shot_portrait   (WHO=kael frames Kael instead)
var out := "user://shots/"

func _ready() -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(out))
	await get_tree().create_timer(0.5).timeout
	Game.pending_encounter = Tuning.ENCOUNTERS["wolf"]
	Game.encounter_id = "WolfA"
	get_tree().change_scene_to_file(Game.BATTLE)
	await get_tree().create_timer(2.5).timeout
	var b = get_tree().current_scene
	b.ui.visible = false
	var guard: Actor = b.heroes[1].actor
	var kael: Actor = b.heroes[0].actor
	var cam := Camera3D.new()
	cam.fov = 35.0
	b.add_child(cam)
	cam.current = true
	var who := OS.get_environment("WHO")
	if who == "":
		who = "guard"
	var subject: Actor = kael if who == "kael" else guard
	var g := subject.global_position
	var shots := [
		[who + "_face", g + Vector3(0.15, 1.55, -1.05), g + Vector3(0, 1.5, 0)],
		[who + "_face_side", g + Vector3(0.75, 1.58, -0.8), g + Vector3(0, 1.55, 0)],
		[who + "_front", g + Vector3(0.3, 1.2, -3.2), g + Vector3(0, 0.95, 0)],
		[who + "_three_quarter", g + Vector3(-2.0, 1.4, -2.4), g + Vector3(0, 1.0, 0)],
		[who + "_side", g + Vector3(3.0, 1.2, -0.2), g + Vector3(0, 1.0, 0)],
		[who + "_back", g + Vector3(-0.6, 1.6, 2.8), g + Vector3(0, 1.1, 0)],
		["party", (guard.global_position + kael.global_position) * 0.5 + Vector3(0.5, 1.5, -4.6), (guard.global_position + kael.global_position) * 0.5 + Vector3(0, 0.9, 0)],
	]
	for s in shots:
		cam.global_position = s[1]
		cam.look_at(s[2], Vector3.UP)
		await get_tree().create_timer(0.6).timeout
		_shot(s[0])
	get_tree().quit()

func _shot(n: String) -> void:
	get_viewport().get_texture().get_image().save_png(ProjectSettings.globalize_path(out) + n + ".png")
	print("SHOT ", n)
