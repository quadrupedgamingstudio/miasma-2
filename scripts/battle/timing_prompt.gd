class_name TimingPrompt
extends Control
## The timed-press prompt, drawn on screen over a fighter: a fixed frame and a square that closes in
## on it, turning as it comes; press when they meet (Legend of Dragoon's Addition squares).
## Blue-white for your combos, red for blocking an enemy's blow.

var progress := 0.0        # 0 = just appeared (big) .. 1 = meets the frame (the moment to press)
var color := Color(0.6, 0.85, 1.0)
var frame_size := 22.0
var start_size := 70.0
var result := ""           # "", "perfect", "good", "miss": flashes the frame


func _init() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	size = Vector2.ZERO


func _process(_delta: float) -> void:
	queue_redraw()


func _draw() -> void:
	var c := Color(1, 0.85, 0.3) if result == "perfect" else (Color(1, 1, 1) if result == "good" else color)
	if result == "miss":
		c = Color(0.5, 0.5, 0.55)
	_square(frame_size, 0.0, c, 2.0)
	_square(frame_size - 6.0, 0.0, Color(c, 0.35), 1.0)
	if result == "":
		var p := clampf(progress, 0.0, 1.2)
		var s := lerpf(start_size, frame_size, p)
		var turn := (1.0 - clampf(p, 0.0, 1.0)) * PI * 0.5
		_square(s, turn, Color(c, clampf(p * 2.0, 0.2, 1.0)), 2.0)


func _square(s: float, angle: float, c: Color, width: float) -> void:
	var h := s * 0.5
	var pts := PackedVector2Array()
	for v in [Vector2(-h, -h), Vector2(h, -h), Vector2(h, h), Vector2(-h, h), Vector2(-h, -h)]:
		pts.append(v.rotated(angle))
	draw_polyline(pts, c, width)
