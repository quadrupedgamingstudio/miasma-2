class_name FieldHud
extends CanvasLayer
## The field's on-screen text: the area name banner, short messages, and a controls hint.

var _toast: PanelContainer
var _toast_label: Label
var _banner: Label


func _ready() -> void:
	var hint := UiKit.label("Move: WASD/Stick   Run: Shift/X   Camera: Q E", 7, Color(0.9, 0.9, 1.0, 0.75))
	hint.position = Vector2(4, 228)
	add_child(hint)
	_toast = UiKit.panel(Rect2(40, 8, 240, 20))
	_toast_label = UiKit.label("", 9)
	_toast_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_toast.add_child(_toast_label)
	_toast.visible = false
	add_child(_toast)
	_banner = UiKit.label("", 9, Color(1.0, 0.95, 0.8))
	_banner.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_banner.position = Vector2(0, 96)
	_banner.size = Vector2(320, 20)
	_banner.modulate.a = 0.0
	add_child(_banner)


func banner(text: String) -> void:
	_banner.text = "~  %s  ~" % text
	var t := create_tween()
	t.tween_interval(0.6)
	t.tween_property(_banner, "modulate:a", 1.0, 0.6)
	t.tween_interval(1.8)
	t.tween_property(_banner, "modulate:a", 0.0, 0.8)


func toast(text: String) -> void:
	_toast_label.text = text
	_toast.visible = true
	_toast.modulate.a = 1.0
	var t := create_tween()
	t.tween_interval(2.4)
	t.tween_property(_toast, "modulate:a", 0.0, 0.5)
	t.tween_callback(func() -> void: _toast.visible = false)
