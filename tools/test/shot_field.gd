extends Node
## Screenshots of the field: start, after walking a bit, with the camera turned.
var out := "user://shots/"

func _ready() -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(out))
	await get_tree().create_timer(2.0).timeout
	_shot("field_start")
	Input.action_press("move_up")
	await get_tree().create_timer(1.5).timeout
	Input.action_release("move_up")
	await get_tree().create_timer(0.6).timeout
	_shot("field_walk")
	Input.action_press("cam_left"); await get_tree().process_frame; Input.action_release("cam_left")
	await get_tree().create_timer(1.0).timeout
	_shot("field_turned")
	get_tree().quit()

func _shot(n: String) -> void:
	var img := get_viewport().get_texture().get_image()
	img.save_png(ProjectSettings.globalize_path(out) + n + ".png")
	print("SHOT ", n)
