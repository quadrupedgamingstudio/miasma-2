class_name Transition
extends CanvasLayer
## Full-screen transitions: the battle swirl (the screen twists, breaks into big pixels and fades out,
## like the PS1 JRPGs' encounter effect) and plain fades.

const SHADER := """
shader_type canvas_item;
uniform sampler2D screen : hint_screen_texture, filter_nearest;
uniform float swirl = 0.0;     // 0..1 twist
uniform float pixel = 1.0;     // block size in screen pixels
uniform float dark = 0.0;      // 0..1 to black
uniform float white = 0.0;     // 0..1 to white
void fragment() {
	vec2 res = 1.0 / SCREEN_PIXEL_SIZE;
	vec2 uv = SCREEN_UV;
	if (pixel > 1.0) {
		uv = (floor(uv * res / pixel) + 0.5) * pixel / res;
	}
	vec2 c = uv - 0.5;
	c.x *= res.x / res.y;
	float r = length(c);
	float a = swirl * 9.0 * max(0.0, 0.75 - r);
	float s = sin(a), co = cos(a);
	c = vec2(c.x * co - c.y * s, c.x * s + c.y * co);
	c.x /= res.x / res.y;
	vec3 col = texture(screen, c + 0.5).rgb;
	col = mix(col, vec3(1.0), white);
	col = mix(col, vec3(0.0), dark);
	COLOR = vec4(col, 1.0);
}
"""

var busy := false
var _rect: ColorRect
var _mat: ShaderMaterial


func _ready() -> void:
	layer = 100
	process_mode = Node.PROCESS_MODE_ALWAYS
	_rect = ColorRect.new()
	_rect.set_anchors_preset(Control.PRESET_FULL_RECT)
	_rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_mat = ShaderMaterial.new()
	var sh := Shader.new()
	sh.code = SHADER
	_mat.shader = sh
	_rect.material = _mat
	add_child(_rect)
	_rect.visible = false


func _p(p: String, v: float) -> void:
	_mat.set_shader_parameter(p, v)


## The encounter swirl, ending on black.
func swirl_out(time := 0.9) -> void:
	busy = true
	_reset()
	_rect.visible = true
	Game.sfx("charge_up", -4.0, 1.3)
	var t := create_tween().set_parallel(true)
	t.tween_method(func(v: float) -> void: _p("swirl", v), 0.0, 1.0, time).set_ease(Tween.EASE_IN)
	t.tween_method(func(v: float) -> void: _p("pixel", v), 1.0, 12.0, time).set_ease(Tween.EASE_IN)
	t.tween_method(func(v: float) -> void: _p("white", v), 0.0, 0.6, time * 0.5)
	t.chain().tween_method(func(v: float) -> void: _p("dark", v), 0.0, 1.0, 0.25)
	await t.finished


## Fades to black.
func fade_out(time := 0.5) -> void:
	busy = true
	_reset()
	_rect.visible = true
	var t := create_tween()
	t.tween_method(func(v: float) -> void: _p("dark", v), 0.0, 1.0, time)
	await t.finished


## From black (or a swirl's end) back to the picture, with the big pixels settling.
func fade_in(time := 0.6) -> void:
	_rect.visible = true
	_p("swirl", 0.0)
	_p("white", 0.0)
	var t := create_tween().set_parallel(true)
	t.tween_method(func(v: float) -> void: _p("dark", v), 1.0, 0.0, time)
	t.tween_method(func(v: float) -> void: _p("pixel", v), 10.0, 1.0, time).set_ease(Tween.EASE_OUT)
	await t.finished
	_rect.visible = false
	busy = false


func _reset() -> void:
	_p("swirl", 0.0)
	_p("pixel", 1.0)
	_p("dark", 0.0)
	_p("white", 0.0)
