class_name Leader
extends CharacterBody3D
## The party member you walk around with on the field (Kael). Moves relative to the camera.

var cam: FieldCamera
var actor: Actor
var trail: Array[Vector3] = []   # recent positions, for the follower
var _step_t := 0.0
var _gravity := 18.0


func _ready() -> void:
	collision_layer = 2
	collision_mask = 1
	var shape := CollisionShape3D.new()
	var cap := CapsuleShape3D.new()
	cap.radius = 0.3
	cap.height = 1.7
	shape.shape = cap
	shape.position = Vector3(0, 0.85, 0)
	add_child(shape)
	actor = Actor.make("kael")
	add_child(actor)
	actor.play("idle")
	floor_snap_length = 0.5


func _physics_process(delta: float) -> void:
	var input := Input.get_vector("move_left", "move_right", "move_up", "move_down")
	var busy := Game.transition.busy
	if busy:
		input = Vector2.ZERO
	var dir := Vector3.ZERO
	if input.length() > 0.1 and cam:
		var basis := Basis(Vector3.UP, deg_to_rad(cam.yaw))
		dir = (basis * Vector3(input.x, 0, input.y))
		dir.y = 0
		dir = dir.normalized() * minf(1.0, input.length())
	var running := Input.is_action_pressed("run")
	var speed := Tuning.RUN_SPEED if running else Tuning.WALK_SPEED
	velocity.x = dir.x * speed
	velocity.z = dir.z * speed
	velocity.y = 0.0 if is_on_floor() else velocity.y - _gravity * delta
	move_and_slide()
	if dir.length() > 0.05:
		var want := atan2(-dir.x, -dir.z)
		rotation.y = lerp_angle(rotation.y, want, minf(1.0, Tuning.TURN_SPEED * delta))
		actor.play("run" if running else "walk", 0.15, 1.0 if running else 1.15)
		_step_t -= delta
		if _step_t <= 0.0:
			_step_t = 0.28 if running else 0.42
			Game.sfx("fstep_soft_%d" % (1 + randi() % 3), -14.0, randf_range(0.9, 1.1))
	else:
		actor.play("idle", 0.25)
	if trail.is_empty() or trail[-1].distance_to(global_position) > 0.15:
		trail.append(global_position)
		if trail.size() > 80:
			trail.pop_front()
