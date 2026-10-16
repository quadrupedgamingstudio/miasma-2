extends Node
## Autoload "Game": the input map, the party's state between scenes, and moving between the field
## and a battle (with the swirl transition).

const FIELD := "res://scenes/field.tscn"
const BATTLE := "res://scenes/battle.tscn"

## Party state: id -> {hp}. Max HP and stats come from Tuning.PARTY.
var party := {}
var draughts := Tuning.START_DRAUGHTS
var exp_total := 0
var gold := 0

## The battle to start, and what to restore on the field afterwards.
var pending_encounter: Array = []
var encounter_id := ""            # the roaming monster that started it (removed on a win)
var defeated := {}                # encounter node names beaten this run
var field_return := {}            # leader position / facing / camera yaw
var fled_from := ""               # the monster you just ran from (gets a grace period)
var battle_result := ""           # "win", "flee", "lose"
## Tests only: the battle plays itself ("perfect" or "mixed" timing). See tools/test/.
var autoplay := ""

var transition: Transition
var font: Font
var font_small: Font


func _ready() -> void:
	_setup_input()
	reset_party()
	font = load("res://assets/fonts/Galmuri9.ttf")
	font_small = load("res://assets/fonts/Galmuri7.ttf")
	transition = Transition.new()
	add_child(transition)
	Ps1.apply_look()
	# test hook: godot --path . -- --driver=res://tools/test/<driver>.gd
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--driver="):
			var d: Node = (load(a.substr(9)) as GDScript).new()
			d.name = "TestDriver"
			add_child(d)


func reset_party() -> void:
	party.clear()
	for id in Tuning.PARTY:
		party[id] = {"hp": int(Tuning.PARTY[id].max_hp)}
	draughts = Tuning.START_DRAUGHTS


func heal_party() -> void:
	for id in party:
		party[id].hp = int(Tuning.PARTY[id].max_hp)


## Called by a roaming monster on the field when it touches the party.
func start_battle(encounter: String, monster_name: String, ret: Dictionary) -> void:
	if transition.busy:
		return
	pending_encounter = Tuning.ENCOUNTERS[encounter]
	encounter_id = monster_name
	field_return = ret
	await transition.swirl_out()
	get_tree().change_scene_to_file(BATTLE)


## Called by the battle when it is over.
func end_battle(result: String) -> void:
	battle_result = result
	if result == "win":
		defeated[encounter_id] = true
	elif result == "flee":
		fled_from = encounter_id
	await transition.fade_out()
	get_tree().change_scene_to_file(FIELD)


func _setup_input() -> void:
	_bind("move_left", [KEY_A, KEY_LEFT], [JOY_BUTTON_DPAD_LEFT], JOY_AXIS_LEFT_X, -1.0)
	_bind("move_right", [KEY_D, KEY_RIGHT], [JOY_BUTTON_DPAD_RIGHT], JOY_AXIS_LEFT_X, 1.0)
	_bind("move_up", [KEY_W, KEY_UP], [JOY_BUTTON_DPAD_UP], JOY_AXIS_LEFT_Y, -1.0)
	_bind("move_down", [KEY_S, KEY_DOWN], [JOY_BUTTON_DPAD_DOWN], JOY_AXIS_LEFT_Y, 1.0)
	_bind("confirm", [KEY_Z, KEY_SPACE, KEY_ENTER, KEY_KP_ENTER], [JOY_BUTTON_A])
	_bind("cancel", [KEY_X, KEY_BACKSPACE, KEY_ESCAPE], [JOY_BUTTON_B])
	_bind("run", [KEY_SHIFT], [JOY_BUTTON_X])
	_bind("cam_left", [KEY_Q], [JOY_BUTTON_LEFT_SHOULDER])
	_bind("cam_right", [KEY_E], [JOY_BUTTON_RIGHT_SHOULDER])
	_bind("fullscreen", [KEY_F11], [])


func _bind(action: String, keys: Array, buttons: Array, axis := -1, axis_dir := 0.0) -> void:
	if not InputMap.has_action(action):
		InputMap.add_action(action, 0.3)
	for k in keys:
		var e := InputEventKey.new()
		e.physical_keycode = k
		InputMap.action_add_event(action, e)
	for b in buttons:
		var e := InputEventJoypadButton.new()
		e.button_index = b
		InputMap.action_add_event(action, e)
	if axis >= 0:
		var e := InputEventJoypadMotion.new()
		e.axis = axis
		e.axis_value = axis_dir
		InputMap.action_add_event(action, e)


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("fullscreen"):
		var full := DisplayServer.window_get_mode() == DisplayServer.WINDOW_MODE_FULLSCREEN
		DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED if full else DisplayServer.WINDOW_MODE_FULLSCREEN)


## A sound, played once. Missing files are skipped.
func sfx(sound: String, volume_db := 0.0, pitch := 1.0) -> void:
	var path := "res://assets/sounds/%s.wav" % sound
	if not ResourceLoader.exists(path):
		return
	var p := AudioStreamPlayer.new()
	p.stream = load(path)
	p.volume_db = volume_db
	p.pitch_scale = pitch
	add_child(p)
	p.play()
	p.finished.connect(p.queue_free)
