class_name FieldMonster
extends Node3D
## A monster roaming the field. It wanders near home, chases the party when they come close, and
## starts a battle when it touches the leader (visible encounters, no random battles).

var encounter := "wolf"   # key in Tuning.ENCOUNTERS
var look := "hollow_wolf" # which model shows on the field
var home := Vector3.ZERO
var leader: Leader
var grace := 0.0          # seconds it ignores you (after you flee)
var actor: Actor
var _goal := Vector3.ZERO
var _wait := 0.0
var _triggered := false


func _ready() -> void:
	actor = Actor.make(look)
	add_child(actor)
	actor.play("idle")
	_goal = home
	if grace > 0.0:
		actor.visible = true


func _process(delta: float) -> void:
	if leader == null or _triggered:
		return
	grace = maxf(0.0, grace - delta)
	if grace > 0.0:
		actor.visible = fmod(grace, 0.3) > 0.12   # blinks while it ignores you
	else:
		actor.visible = true
	var to_leader := leader.global_position - global_position
	to_leader.y = 0
	var chasing := grace <= 0.0 and to_leader.length() < Tuning.NOTICE_RANGE and not Game.transition.busy
	var target := leader.global_position if chasing else _goal
	var to := target - global_position
	to.y = 0
	if not chasing and to.length() < 0.3:
		_wait -= delta
		actor.play("idle", 0.3)
		if _wait <= 0.0:
			_wait = randf_range(1.0, 3.0)
			var a := randf() * TAU
			_goal = home + Vector3(cos(a), 0, sin(a)) * randf_range(1.0, Tuning.ROAM_RADIUS)
	else:
		var speed := Tuning.CHASE_SPEED if chasing else Tuning.ROAM_SPEED
		global_position += to.normalized() * minf(to.length(), speed * delta)
		rotation.y = lerp_angle(rotation.y, atan2(-to.x, -to.z), minf(1.0, 8.0 * delta))
		if chasing and actor.has_anim("run"):
			actor.play("run", 0.15)
		else:
			actor.play("walk", 0.15, 1.6 if chasing else 1.0)
	global_position.y = Field.height_at(global_position.x, global_position.z)
	if grace <= 0.0 and to_leader.length() < 0.9 and not Game.transition.busy:
		_triggered = true
		var field := get_parent() as Field
		Game.start_battle(encounter, String(name), {
			"position": leader.global_position, "yaw": leader.rotation.y, "cam_yaw": field.cam.yaw if field else 0.0})
