extends Node
## Plays a whole battle: timed presses by Game.autoplay, menus by real input events (PLAN), taking
## a screenshot every 0.4 s; confirms the end window and shoots the field it returns to.
## Run: tools/test/shoot.sh battle_auto
## Env: MODE=perfect|mixed  ENC=pair|wolf  PLAN=attack,guard,item,flee (cycled per turn)
##      FIELD=1 starts on the field and walks into the wolf instead. LOWHP=1 starts the party at 5 HP
##      (MODE=none presses nothing) to see the defeat window.
var out := "user://shots/"
var n := 0
var plan: PackedStringArray
var turn := 0
var busy := false

func _env(k: String, d: String) -> String:
	return OS.get_environment(k) if OS.get_environment(k) != "" else d

func _ready() -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(out))
	Game.autoplay = _env("MODE", "perfect")
	plan = _env("PLAN", "attack").split(",")
	await get_tree().create_timer(0.5).timeout
	if _env("FIELD", "") == "1":
		var f = get_tree().current_scene
		await get_tree().create_timer(1.0).timeout
		f.leader.global_position = Vector3(-8, Field.height_at(-8, 3) + 0.2, 3)
		_shot()
		Input.action_press("move_up")
		await get_tree().create_timer(0.6).timeout
		Input.action_release("move_up")
	else:
		if _env("LOWHP", "") == "1":
			Game.party = {"kael": {"hp": 5}, "guard": {"hp": 5}}
		Game.pending_encounter = Tuning.ENCOUNTERS[_env("ENC", "pair")]
		Game.encounter_id = "Pair"
		get_tree().change_scene_to_file(Game.BATTLE)
	var t := 0.0
	var field_seen := 0
	while t < float(_env("SECS", "60")):
		await get_tree().create_timer(0.4).timeout
		t += 0.4
		var b = get_tree().current_scene
		if b is Battle:
			var hp := []
			for x in b.heroes + b.enemies:
				hp.append("%s:%d" % [x.name, x.hp])
			print("LOG t=%.1f %s msg=%s" % [t, " ".join(hp), b.ui._msg.text])
			if not busy:
				_menus(b.ui)
		elif b is Field and t > 3.0:
			field_seen += 1
			if field_seen == 4:
				print("LOG back on the field; party ", Game.party, " defeated ", Game.defeated)
				_shot()
				break
		_shot()
	get_tree().quit()

func _menus(ui: BattleUi) -> void:
	busy = true
	if ui._menu_active and ui._window == null or (ui._menu_active and not is_instance_valid(ui._window)):
		var step := plan[turn % plan.size()]
		turn += 1
		print("LOG plan: ", step)
		match step:
			"guard": await _keys(["move_down", "confirm"])
			"item": await _keys(["move_down", "move_down", "confirm"])
			"flee": await _keys(["move_up", "confirm"])
			_: await _keys(["confirm"])
	elif ui._picking:
		await _keys(["confirm"])
	elif ui.waiting_confirm or ui._menu_active:
		await _keys(["confirm"])
	busy = false

func _keys(actions: Array) -> void:
	for a in actions:
		var e := InputEventAction.new()
		e.action = a
		e.pressed = true
		Input.parse_input_event(e)
		await get_tree().create_timer(0.08).timeout
		var r := InputEventAction.new()
		r.action = a
		r.pressed = false
		Input.parse_input_event(r)
		await get_tree().create_timer(0.08).timeout

func _shot() -> void:
	n += 1
	get_viewport().get_texture().get_image().save_png(ProjectSettings.globalize_path(out) + "b%03d.png" % n)
