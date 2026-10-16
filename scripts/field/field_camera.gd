class_name FieldCamera
extends Camera3D
## The field camera: high and behind at a fixed angle, like the PS1 JRPGs. Q / E (or the shoulder
## buttons) turn it in 45-degree steps.

var target: Node3D
var yaw := 0.0          # degrees; 0 = looking north (-Z)
var _yaw_shown := 0.0
var _focus := Vector3.ZERO


func _ready() -> void:
	fov = Tuning.CAM_FOV
	near = 0.1
	far = 300.0
	current = true
	_yaw_shown = yaw


func snap() -> void:
	if target:
		_focus = target.global_position
	_yaw_shown = yaw
	_place()


func _process(delta: float) -> void:
	if Input.is_action_just_pressed("cam_left"):
		yaw += Tuning.CAM_TURN_STEP
	if Input.is_action_just_pressed("cam_right"):
		yaw -= Tuning.CAM_TURN_STEP
	_yaw_shown = lerpf(_yaw_shown, yaw, minf(1.0, 8.0 * delta))
	if target:
		_focus = _focus.lerp(target.global_position, minf(1.0, Tuning.CAM_FOLLOW * delta))
	_place()


func _place() -> void:
	var dir := Basis(Vector3.UP, deg_to_rad(_yaw_shown)) * Basis(Vector3.RIGHT, deg_to_rad(-Tuning.CAM_PITCH)) * Vector3(0, 0, 1)
	var look_at_point := _focus + Vector3(0, 1.0, 0)
	global_position = look_at_point + dir * Tuning.CAM_DISTANCE
	look_at(look_at_point, Vector3.UP)
