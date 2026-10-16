class_name BattleCamera
extends Camera3D
## The battle camera: glides between shots (overview, a hero's shoulder, the side view of a combo,
## behind a defender) like Legend of Dragoon's. A shot = where the camera is and what it looks at.

var _look := Vector3.ZERO
var _tween: Tween
var _drift := Vector3.ZERO      # slow sideways drift during a shot, for life
var _drift_t := 0.0
var shake := 0.0


func _ready() -> void:
	fov = Tuning.BATTLE_FOV
	near = 0.1
	far = 300.0
	current = true


## Jump straight to a shot.
func cut(pos: Vector3, look: Vector3, drift := Vector3.ZERO) -> void:
	if _tween:
		_tween.kill()
	global_position = pos
	_look = look
	_drift = drift
	_drift_t = 0.0
	_aim()


## Glide to a shot over `time` seconds.
func glide(pos: Vector3, look: Vector3, time := 0.6, drift := Vector3.ZERO) -> void:
	if _tween:
		_tween.kill()
	_drift = drift
	_drift_t = 0.0
	_tween = create_tween().set_parallel(true).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	_tween.tween_property(self, "global_position", pos, time)
	_tween.tween_property(self, "_look", look, time)


func _process(delta: float) -> void:
	_drift_t += delta
	if _drift != Vector3.ZERO and (_tween == null or not _tween.is_running()):
		global_position += _drift * delta
	shake = maxf(0.0, shake - delta * 3.0)
	_aim()


func _aim() -> void:
	if global_position.distance_to(_look) < 0.01:
		return
	look_at(_look, Vector3.UP)
	if shake > 0.0:
		rotation += Vector3(randf_range(-1, 1), randf_range(-1, 1), 0) * shake * 0.02
