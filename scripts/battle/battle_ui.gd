class_name BattleUi
extends CanvasLayer
## Everything drawn on screen in a battle: the party's HP panel, the message bar, the command menu,
## target picking, damage numbers, the timed-press prompt and the victory / defeat windows.

signal chosen(index: int)

var camera: Camera3D
var _msg_panel: PanelContainer
var _msg: Label
var _party_panel: PanelContainer
var _party_rows := {}            # hero id -> {name, hp, bar, cursor}
var _menu: PanelContainer
var _menu_labels: Array[Label] = []
var _menu_index := 0
var _menu_active := false
var _menu_disabled: Array[bool] = []
var _marker: Label
var _marker_target: Battler
var _picking := false
var _pick_list: Array = []
var _pick_index := 0
var _floaters: Array = []        # [Label, world point, age]
var prompt: TimingPrompt
var _prompt_point := Vector3.ZERO
var _window: PanelContainer
var waiting_confirm := false
signal confirmed
var _t := 0.0


func _ready() -> void:
	layer = 10
	_msg_panel = UiKit.panel(Rect2(30, 6, 260, 20))
	_msg = UiKit.label("", 9)
	_msg.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_msg_panel.add_child(_msg)
	_msg_panel.visible = false
	add_child(_msg_panel)

	_party_panel = UiKit.panel(Rect2(96, 196, 220, 40))
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 0)
	_party_panel.add_child(box)
	add_child(_party_panel)

	_menu = UiKit.panel(Rect2(4, 158, 86, 78))
	var mbox := VBoxContainer.new()
	mbox.add_theme_constant_override("separation", 1)
	_menu.add_child(mbox)
	for i in 4:
		var l := UiKit.label("", 9)
		mbox.add_child(l)
		_menu_labels.append(l)
	_menu.visible = false
	add_child(_menu)

	_marker = UiKit.label("v", 9, Color(1, 0.9, 0.3))
	_marker.visible = false
	add_child(_marker)

	prompt = TimingPrompt.new()
	prompt.visible = false
	add_child(prompt)


func setup_party(heroes: Array) -> void:
	var box := _party_panel.get_child(0) as VBoxContainer
	for h: Battler in heroes:
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 4)
		var cur := UiKit.label(" ", 9, Color(1, 0.9, 0.3))
		cur.custom_minimum_size = Vector2(8, 0)
		var nm := UiKit.label(h.name, 9)
		nm.custom_minimum_size = Vector2(46, 0)
		var hp := UiKit.label("", 9)
		hp.custom_minimum_size = Vector2(66, 0)
		hp.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
		var bar := ProgressBar.new()
		bar.show_percentage = false
		bar.custom_minimum_size = Vector2(70, 5)
		bar.size_flags_vertical = Control.SIZE_SHRINK_CENTER
		var bg := StyleBoxFlat.new()
		bg.bg_color = Color(0.02, 0.02, 0.1)
		bg.border_color = Color(0.7, 0.7, 0.8)
		bg.set_border_width_all(1)
		var fg := StyleBoxFlat.new()
		fg.bg_color = Color(0.35, 0.85, 0.45)
		bar.add_theme_stylebox_override("background", bg)
		bar.add_theme_stylebox_override("fill", fg)
		row.add_child(cur)
		row.add_child(nm)
		row.add_child(hp)
		row.add_child(bar)
		box.add_child(row)
		_party_rows[h.id] = {"name": nm, "hp": hp, "bar": bar, "cursor": cur, "fill": fg}
	refresh(heroes)


func refresh(heroes: Array, active: Battler = null) -> void:
	for h: Battler in heroes:
		var r: Dictionary = _party_rows[h.id]
		(r.hp as Label).text = "%d/%d" % [h.hp, h.max_hp]
		var bar := r.bar as ProgressBar
		bar.max_value = h.max_hp
		create_tween().tween_property(bar, "value", float(h.hp), 0.3)
		var frac := float(h.hp) / h.max_hp
		(r.fill as StyleBoxFlat).bg_color = Color(0.35, 0.85, 0.45) if frac > 0.5 else (Color(0.95, 0.8, 0.3) if frac > 0.2 else Color(0.95, 0.3, 0.25))
		var col := Color(0.55, 0.5, 0.55) if h.hp <= 0 else Color(0.95, 0.95, 1.0)
		(r.name as Label).add_theme_color_override("font_color", col)
		(r.cursor as Label).text = ">" if h == active else " "


func message(text: String) -> void:
	_msg.text = text
	_msg_panel.visible = text != ""


# --- Command menu --------------------------------------------------------------------------------------

## Shows the menu and waits for a choice: returns the index, or -1 for cancel.
func choose(options: Array, disabled: Array = [], start := 0) -> int:
	for i in _menu_labels.size():
		_menu_labels[i].visible = i < options.size()
		if i < options.size():
			_menu_labels[i].text = options[i]
	_menu_disabled.clear()
	for i in options.size():
		_menu_disabled.append(i < disabled.size() and disabled[i])
	_menu_index = clampi(start, 0, options.size() - 1)
	_menu.visible = true
	_menu_active = true
	_draw_menu()
	var picked: int = await chosen
	_menu_active = false
	_menu.visible = false
	return picked


func _draw_menu() -> void:
	for i in _menu_labels.size():
		var l := _menu_labels[i]
		var t := l.text.trim_prefix("> ").trim_prefix("  ")
		l.text = ("> " if i == _menu_index else "  ") + t
		var dim := i < _menu_disabled.size() and _menu_disabled[i]
		l.add_theme_color_override("font_color", Color(0.5, 0.5, 0.6) if dim else (Color(1, 0.95, 0.6) if i == _menu_index else Color(0.95, 0.95, 1.0)))


# --- Target picking ------------------------------------------------------------------------------------

## Lets the player pick one of `list` (Battlers) with left / right; returns it, or null for cancel.
func pick(list: Array, start := 0) -> Battler:
	_pick_list = list
	_pick_index = clampi(start, 0, list.size() - 1)
	_picking = true
	_marker.visible = true
	_marker_target = list[_pick_index]
	message(_marker_target.name)
	var picked: int = await chosen
	_picking = false
	_marker.visible = false
	message("")
	return null if picked < 0 else list[picked]


func _unhandled_input(event: InputEvent) -> void:
	if waiting_confirm and event.is_action_pressed("confirm"):
		waiting_confirm = false
		Game.sfx("ui_select", -6.0)
		confirmed.emit()
		get_viewport().set_input_as_handled()
	elif _menu_active:
		var n := 0
		for l in _menu_labels:
			n += 1 if l.visible else 0
		if event.is_action_pressed("move_up"):
			_menu_index = (_menu_index - 1 + n) % n
			Game.sfx("ui_move", -8.0)
			_draw_menu()
		elif event.is_action_pressed("move_down"):
			_menu_index = (_menu_index + 1) % n
			Game.sfx("ui_move", -8.0)
			_draw_menu()
		elif event.is_action_pressed("confirm"):
			if _menu_index < _menu_disabled.size() and _menu_disabled[_menu_index]:
				return
			Game.sfx("ui_select", -6.0)
			chosen.emit(_menu_index)
		elif event.is_action_pressed("cancel"):
			chosen.emit(-1)
		get_viewport().set_input_as_handled()
	elif _picking:
		var n := _pick_list.size()
		if event.is_action_pressed("move_left") or event.is_action_pressed("move_up"):
			_pick_index = (_pick_index - 1 + n) % n
			Game.sfx("ui_move", -8.0)
		elif event.is_action_pressed("move_right") or event.is_action_pressed("move_down"):
			_pick_index = (_pick_index + 1) % n
			Game.sfx("ui_move", -8.0)
		elif event.is_action_pressed("confirm"):
			Game.sfx("ui_select", -6.0)
			get_viewport().set_input_as_handled()
			chosen.emit(_pick_index)
			return
		elif event.is_action_pressed("cancel"):
			get_viewport().set_input_as_handled()
			chosen.emit(-1)
			return
		_marker_target = _pick_list[_pick_index]
		message(_marker_target.name)
		get_viewport().set_input_as_handled()


# --- Things that follow the 3D scene -----------------------------------------------------------------------

func _screen(p: Vector3) -> Vector2:
	if camera == null or camera.is_position_behind(p):
		return Vector2(-100, -100)
	return camera.unproject_position(p)


func _process(delta: float) -> void:
	_t += delta
	if _marker.visible and _marker_target:
		var s := _screen(_marker_target.actor.chest_point() + Vector3(0, 0.8, 0))
		_marker.position = s - Vector2(3, 10 + absf(sin(_t * 6.0)) * 3.0)
	if prompt.visible:
		prompt.position = _screen(_prompt_point)
	for f in _floaters.duplicate():
		var l := f[0] as Label
		f[2] += delta
		var age: float = f[2]
		var s := _screen(f[1])
		var rise := minf(age, 0.25) * 60.0
		l.position = s - Vector2(l.size.x * 0.5, 10.0 + rise)
		if age > 0.9:
			l.modulate.a = maxf(0.0, 1.0 - (age - 0.9) * 3.0)
		if age > 1.3:
			l.queue_free()
			_floaters.erase(f)


## A number or word that pops up over a point in the scene and fades.
func pop(text: String, at: Vector3, color := Color(1, 1, 1), big := true) -> void:
	var l := UiKit.label(text, 9 if big else 7, color)
	l.add_theme_constant_override("outline_size", 2)
	l.add_theme_color_override("font_outline_color", Color(0, 0, 0))
	add_child(l)
	l.reset_size()
	_floaters.append([l, at + Vector3(randf_range(-0.15, 0.15), 0, 0), 0.0])


func show_prompt(at: Vector3, color: Color) -> void:
	_prompt_point = at
	prompt.color = color
	prompt.result = ""
	prompt.progress = 0.0
	prompt.position = _screen(at)
	prompt.visible = true


func hide_prompt() -> void:
	prompt.visible = false


# --- End windows ------------------------------------------------------------------------------------------

## A centred window with lines of text; waits for Confirm, or for a choice when `options` is given.
func window(lines: Array, options: Array = []) -> int:
	_window = UiKit.panel(Rect2(70, 70, 180, 30 + 14 * (lines.size() + options.size())))
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 2)
	_window.add_child(box)
	for ln in lines:
		var l := UiKit.label(ln, 9, Color(1, 0.95, 0.75) if ln == lines[0] else Color(0.95, 0.95, 1.0))
		l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		box.add_child(l)
	add_child(_window)
	var picked := 0
	if options.is_empty():
		var hint := UiKit.label("Press Z / A", 7, Color(0.8, 0.8, 0.9))
		hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		box.add_child(hint)
		await _wait_confirm()
	else:
		move_child(_menu, get_child_count() - 1)
		_menu.position = Vector2(110, 70 + 14 * lines.size() + 12)
		_menu.size = Vector2(100, 14 * options.size() + 10)
		_menu.custom_minimum_size = _menu.size
		_menu.reset_size()
		_window.size.y += 0
		picked = await choose(options)
		while picked < 0:
			picked = await choose(options)
	_window.queue_free()
	return picked


func _wait_confirm() -> void:
	await get_tree().create_timer(0.4).timeout
	waiting_confirm = true
	await confirmed
