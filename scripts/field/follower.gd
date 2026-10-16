class_name Follower
extends Node3D
## The second party member (the Guard), walking a little behind the leader along their path.

var leader: Leader
var actor: Actor


func _ready() -> void:
	actor = Actor.make("guard")
	add_child(actor)
	actor.play("idle")


func _process(delta: float) -> void:
	if leader == null:
		return
	if global_position == Vector3.ZERO and leader.global_position != Vector3.ZERO:
		global_position = leader.global_position + leader.global_basis.z * Tuning.FOLLOW_GAP
	var target := _trail_point()
	if leader.velocity.length() < 0.1:
		# the leader has stopped: step to their side so the camera sees them both
		var back := leader.global_basis.z
		var right := leader.global_basis.x
		target = leader.global_position + back * 0.8 + right * 0.9
	var to := target - global_position
	to.y = 0
	var dist := to.length()
	var moving := dist > 0.08
	if moving:
		var speed := clampf(dist * 5.0, 0.0, Tuning.RUN_SPEED * 1.1)
		var step := to.normalized() * minf(dist, speed * delta)
		global_position += step
		rotation.y = lerp_angle(rotation.y, atan2(-to.x, -to.z), minf(1.0, Tuning.TURN_SPEED * delta))
		actor.play("run" if speed > Tuning.WALK_SPEED * 1.3 else "walk", 0.15)
	else:
		actor.play("idle", 0.25)
		rotation.y = lerp_angle(rotation.y, leader.rotation.y, minf(1.0, 4.0 * delta))
	global_position.y = Field.height_at(global_position.x, global_position.z)


## The point on the leader's trail FOLLOW_GAP metres back from the leader.
func _trail_point() -> Vector3:
	var trail := leader.trail
	var left := Tuning.FOLLOW_GAP
	var p := leader.global_position
	for i in range(trail.size() - 1, -1, -1):
		var d := p.distance_to(trail[i])
		if d >= left:
			return p.lerp(trail[i], left / d)
		left -= d
		p = trail[i]
	return global_position if trail.size() < 2 else p
