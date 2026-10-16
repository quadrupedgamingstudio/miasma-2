extends Node
func _ready() -> void:
	await get_tree().create_timer(1.0).timeout
	var f = get_tree().current_scene
	print("LOG scene ", f, " leader ", f.leader.global_position, " busy ", Game.transition.busy)
	Input.action_press("move_up")
	for i in 5:
		await get_tree().create_timer(0.3).timeout
		print("LOG ", f.leader.global_position, " vec ", Input.get_vector("move_left","move_right","move_up","move_down"), " floor ", f.leader.is_on_floor(), " vel ", f.leader.velocity)
	get_tree().quit()
