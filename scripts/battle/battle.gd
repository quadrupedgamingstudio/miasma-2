class_name Battle
extends Node3D
## A battle: the party (Kael and the Guard) against the monsters of Game.pending_encounter, in turns
## by speed. Heroes pick Attack / Guard / Item / Flee. Attack runs an Addition, Legend of Dragoon's
## timed combo: press Confirm as each square closes on its frame to keep the combo going. On enemy
## turns, press Confirm as the blow lands to block (or, dead on time, parry and hit back).
## All numbers are in scripts/data/tuning.gd.

const HERO_ROW_Z := 3.0
const ENEMY_ROW_Z := -3.0

var heroes: Array[Battler] = []
var enemies: Array[Battler] = []
var cam: BattleCamera
var ui: BattleUi
var _presses: Array[float] = []   # times (seconds, now()) Confirm was pressed while listening
var _listening := false
var _over := false
var _rng := RandomNumberGenerator.new()


func _ready() -> void:
	_rng.seed = 11
	Ps1.apply_look()
	_build_arena()
	cam = BattleCamera.new()
	add_child(cam)
	ui = BattleUi.new()
	ui.camera = cam
	add_child(ui)
	_spawn()
	ui.setup_party(heroes)
	_run()


static func now() -> float:
	return Time.get_ticks_usec() / 1000000.0


func _unhandled_input(event: InputEvent) -> void:
	if _listening and event.is_action_pressed("confirm") and not event.is_echo():
		_presses.append(now())
		get_viewport().set_input_as_handled()


# --- Setting up ------------------------------------------------------------------------------------------

static func arena_height(x: float, z: float) -> float:
	var r := Vector2(x, z).length()
	var h := sin(x * 0.21) * 0.3 + cos(z * 0.17 + x * 0.07) * 0.35
	return h * clampf((r - 6.0) / 6.0, 0.0, 1.0) + maxf(0.0, r - 16.0) * 0.35


func _build_arena() -> void:
	var g := WorldKit.ground(-30, -30, 30, 30, 2.0, arena_height,
		func(x: float, z: float) -> String: return "dirt" if absf(x * 0.3 + z - 0.5) < 1.4 and absf(x) > 3.0 else "grass",
		func(x: float, z: float) -> float: return clampf(0.55 + z * 0.02 + sin(x * 0.5) * 0.1, 0.0, 1.0))
	add_child(g[0])
	add_child(g[1])
	add_child(WorldKit.sky(Color(0.42, 0.52, 0.72), Tuning.FOG_COLOR))
	for i in 34:
		var a := _rng.randf() * TAU
		var r := _rng.randf_range(9.0, 24.0)
		var p := Vector3(cos(a) * r, 0, sin(a) * r)
		var tree := WorldKit.sapling(_rng, _rng.randf_range(2.4, 3.8)) if _rng.randf() < 0.45 else WorldKit.dead_tree(_rng, _rng.randf_range(4.5, 7.5))
		tree.position = Vector3(p.x, arena_height(p.x, p.z) - 0.1, p.z)
		tree.rotation.y = _rng.randf() * TAU
		add_child(tree)
	for i in 6:
		var a := _rng.randf() * TAU
		var r := _rng.randf_range(7.0, 14.0)
		var rk := WorldKit.rock(_rng, _rng.randf_range(0.5, 1.2))
		rk.position = Vector3(cos(a) * r, arena_height(cos(a) * r, sin(a) * r), sin(a) * r)
		add_child(rk)
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for i in 500:
		var x := _rng.randf_range(-16, 16)
		var z := _rng.randf_range(-16, 16)
		if Vector2(x, z).length() < 2.0:
			continue
		WorldKit.grass_tuft(st, Vector3(x, arena_height(x, z) - 0.05, z), _rng.randf_range(0.4, 0.8), _rng.randf() * PI)
	var tufts := MeshInstance3D.new()
	tufts.mesh = st.commit()
	tufts.material_override = Ps1.material("res://assets/textures/forest_grass.png", {"double_sided": true, "tint": Color(0.85, 1.0, 0.7)})
	add_child(tufts)
	for i in 10:
		var a := TAU * i / 10.0
		var m := WorldKit.mist(14.0, 4.0)
		m.position = Vector3(cos(a) * 22.0, arena_height(cos(a) * 22.0, sin(a) * 22.0) - 1.5, sin(a) * 22.0)
		m.rotation.y = -a + PI * 0.5
		add_child(m)


func _spawn() -> void:
	var ids := ["kael", "guard"]
	for i in ids.size():
		var h := Battler.hero(ids[i])
		h.home = Vector3(-1.4 + i * 2.8, 0, HERO_ROW_Z + i * 0.4)
		h.facing = 0.0
		heroes.append(h)
	var kinds: Array = Game.pending_encounter if not Game.pending_encounter.is_empty() else ["hollow_wolf"]
	for i in kinds.size():
		var e := Battler.monster(kinds[i])
		var x := 0.0 if kinds.size() == 1 else -1.8 + i * 3.6
		e.home = Vector3(x, 0, ENEMY_ROW_Z - (i % 2) * 0.5)
		e.facing = PI
		enemies.append(e)
	for b in heroes + enemies:
		b.home.y = arena_height(b.home.x, b.home.z)
		add_child(b.actor)
		b.actor.global_position = b.home
		b.actor.rotation.y = b.facing
		if b.is_hero:
			b.actor.play("down" if not b.alive() else "stance", 0.0)
		else:
			b.actor.play("idle", 0.0)


# --- Camera shots -----------------------------------------------------------------------------------------

func _overview(time := 0.8) -> void:
	cam.glide(Vector3(5.5, 3.4, 8.0), Vector3(0, 0.6, -0.8), time, Vector3(-0.15, 0, 0))


func _command_shot(h: Battler) -> void:
	var side := 1.0 if h.home.x >= 0 else -1.0
	cam.glide(h.home + Vector3(side * 1.6, 1.9, 2.6), _enemy_center() + Vector3(0, 0.7, 0), 0.6)


func _enemy_center() -> Vector3:
	var c := Vector3.ZERO
	var n := 0
	for e in enemies:
		if e.alive():
			c += e.home
			n += 1
	return c / maxf(1, n)


## The side view of a fight between two points (an Addition, an enemy's attack).
func _side_shot(a: Vector3, b: Vector3, time := 0.5, flip := false) -> void:
	var mid := (a + b) * 0.5
	var along := (b - a)
	along.y = 0
	along = along.normalized()
	var side := along.cross(Vector3.UP) * (-1.0 if flip else 1.0)
	cam.glide(mid + side * 4.2 + Vector3(0, 1.4, 0) - along * 0.6, mid + Vector3(0, 0.9, 0), time, -along * 0.12)


## Over the defender's shoulder, looking at the attacker (enemy turns).
func _defend_shot(defender: Battler, attacker: Battler) -> void:
	var to := attacker.home - defender.home
	to.y = 0
	to = to.normalized()
	var side := to.cross(Vector3.UP)
	cam.glide(defender.home - to * 2.6 + side * 1.3 + Vector3(0, 1.7, 0), attacker.home + Vector3(0, 0.9, 0), 0.6)


# --- The battle -------------------------------------------------------------------------------------------

func _run() -> void:
	# opening: low by the monsters, sweeping round to the party
	var e0 := enemies[0]
	cam.cut(e0.home + Vector3(1.8, 0.7, 2.4), e0.home + Vector3(0, 0.8, 0))
	await Game.transition.fade_in(0.5)
	var names := enemies.map(func(e: Battler) -> String: return e.name)
	ui.message("%s appear%s!" % [" and ".join(names), "" if names.size() > 1 else "s"])
	_roar(e0)
	await _wait(0.9)
	cam.glide(Vector3(-4.0, 2.6, -0.5), Vector3(0, 0.8, 0), 0.9)
	await _wait(0.9)
	_overview(1.0)
	await _wait(1.0)
	ui.message("")
	while not _over:
		var order: Array = heroes + enemies
		order = order.filter(func(b: Battler) -> bool: return b.alive())
		order.sort_custom(func(a: Battler, b: Battler) -> bool: return a.spd > b.spd)
		for b: Battler in order:
			if _over or not b.alive():
				continue
			if b.is_hero:
				await _hero_turn(b)
			else:
				await _enemy_turn(b)
			await _check_end()


func _wait(t: float) -> void:
	await get_tree().create_timer(t).timeout


func _living(list: Array) -> Array:
	return list.filter(func(b: Battler) -> bool: return b.alive())


func _hero_turn(h: Battler) -> void:
	h.guarding = false
	h.actor.play("stance", 0.2)
	while true:
		ui.refresh(heroes, h)
		_command_shot(h)
		ui.message("%s's turn" % h.name)
		var pick := await ui.choose(["Attack", "Guard", "Item x%d" % Game.draughts, "Flee"], [false, false, Game.draughts <= 0, false])
		ui.message("")
		if pick == 0:
			var foes := _living(enemies)
			cam.glide(h.home + Vector3(0, 2.2, 3.4), _enemy_center() + Vector3(0, 0.6, 0), 0.4)
			var t: Battler = await ui.pick(foes)
			if t == null:
				continue
			await _hero_attack(h, t)
			break
		elif pick == 1:
			h.guarding = true
			h.actor.play("guard", 0.1)
			await _wait(0.2)
			h.actor.play("guard_hold", 0.2)
			var heal := roundi(h.max_hp * Tuning.GUARD_HEAL)
			h.heal(heal)
			ui.pop("+%d" % heal, h.actor.chest_point(), Color(0.5, 1.0, 0.6))
			ui.message("%s braces." % h.name)
			Game.sfx("shield_block", -6.0)
			await _wait(0.8)
			break
		elif pick == 2:
			var t: Battler = await ui.pick(heroes, heroes.find(h))
			if t == null:
				continue
			await _use_draught(h, t)
			break
		elif pick == 3:
			if await _try_flee():
				return
			break
	ui.refresh(heroes)
	ui.message("")


func _use_draught(user: Battler, target: Battler) -> void:
	Game.draughts -= 1
	ui.message("%s uses a Healing Draught." % user.name)
	Game.sfx("draught", -4.0)
	await _wait(0.4)
	var was_down := not target.alive()
	var amount := roundi(target.max_hp * Tuning.DRAUGHT_HEAL)
	target.heal(amount)
	target.actor.flash(Color(0.5, 1.0, 0.6), 0.4)
	ui.pop("+%d" % amount, target.actor.chest_point(), Color(0.5, 1.0, 0.6))
	if was_down:
		target.actor.play("revive", 0.1)
		await _wait(0.4)
		target.actor.play("stance", 0.2)
	ui.refresh(heroes)
	await _wait(0.8)


func _try_flee() -> bool:
	ui.message("The party tries to run...")
	await _wait(0.6)
	if randf() < Tuning.FLEE_CHANCE:
		ui.message("Got away!")
		for h in _living(heroes):
			h.actor.rotation.y = PI
			h.actor.play("run", 0.1)
			var t := create_tween()
			t.tween_property(h.actor, "global_position", h.home + Vector3(0, 0, 6), 0.9)
		await _wait(0.8)
		_save_party()
		_over = true
		Game.end_battle("flee")
		return true
	ui.message("Couldn't escape!")
	await _wait(0.8)
	return false


# --- Additions (the party's timed combos) -------------------------------------------------------------------

func _hero_attack(h: Battler, target: Battler) -> void:
	var add: Dictionary = Tuning.ADDITIONS[Tuning.PARTY[h.id].addition]
	var times: Array = add.times
	var mults: Array = add.mults
	var n := times.size()
	var to_hero := (h.home - target.home)
	to_hero.y = 0
	var stand := target.home + to_hero.normalized() * Tuning.ATTACK_GAP
	stand.y = arena_height(stand.x, stand.z)
	ui.message("%s   (Z as the squares meet)" % add.name)
	_side_shot(h.home, target.home, 0.5, h.home.x < 0)
	# run in
	_face(h.actor, stand)
	h.actor.play("run", 0.1)
	var run := create_tween()
	run.tween_property(h.actor, "global_position", stand, Tuning.RUN_TO_TARGET)
	await run.finished
	_face(h.actor, target.home)
	h.actor.play("stance", 0.08)
	await _wait(0.1)
	_side_shot(stand, target.home, 0.35, h.home.x < 0)

	# the combo
	var anims := []
	for i in n:
		anims.append("atk_big" if i == n - 1 else ("atk_a" if i % 2 == 0 else "atk_b"))
	var t0 := now()
	var started := []
	started.resize(n)
	started.fill(false)
	_presses.clear()
	_listening = true
	var k := 0
	var all_good := true
	var pending := ""          # a press rated before the hit's moment: applied when the moment comes
	var hits_landed := 0
	while k < n:
		await get_tree().process_frame
		var t := now() - t0
		var hit_t: float = times[k]
		if Game.autoplay != "" and pending == "" and _presses.is_empty() and t >= hit_t + _auto_offset(k):
			_presses.append(t0 + t)
		if not started[k] and t >= hit_t - Actor.SLASH_HIT[anims[k]]:
			started[k] = true
			h.actor.replay(anims[k], 0.05)
			Game.sfx("sword_swing", -4.0, randf_range(0.9, 1.15))
		var lead := Tuning.PROMPT_LEAD
		if t >= hit_t - lead and pending == "":
			if not ui.prompt.visible:
				ui.show_prompt(target.actor.chest_point(), Color(0.6, 0.85, 1.0))
			ui.prompt.progress = (t - (hit_t - lead)) / lead
		var res := ""
		if pending == "":
			if not _presses.is_empty():
				var p: float = _presses[0] - t0
				_presses.clear()
				var d := p - hit_t
				if d < -Tuning.GOOD_WINDOW:
					res = "miss"
				elif absf(d) <= Tuning.PERFECT_WINDOW:
					pending = "perfect"
				elif absf(d) <= Tuning.GOOD_WINDOW:
					pending = "good"
				else:
					res = "miss"
			elif t > hit_t + Tuning.GOOD_WINDOW:
				res = "miss"
		if pending != "":
			ui.prompt.progress = 1.0
			if t >= hit_t:
				res = pending
				pending = ""
			else:
				_presses.clear()
		if res == "":
			continue
		ui.prompt.result = res
		var landed := res != "miss"
		if res == "miss":
			all_good = false
		if landed or k == 0:
			var mult: float = mults[k]
			if res == "miss":
				mult *= Tuning.MISSED_FIRST_HIT_MULT
			elif res == "perfect":
				mult *= 1.0 + Tuning.PERFECT_BONUS
			if k == n - 1 and all_good:
				mult *= 1.0 + Tuning.COMPLETE_BONUS
			hits_landed += 1
			_strike(h, target, h.damage_to(target, mult), k == n - 1, true, hits_landed - 1)
			if res != "miss":
				ui.pop("PERFECT" if res == "perfect" else "GOOD", target.actor.chest_point() + Vector3(0.5, 0.35 + 0.22 * (hits_landed - 1), 0),
					Color(1, 0.85, 0.3) if res == "perfect" else Color(0.8, 0.9, 1.0), false)
		if res == "miss":
			ui.pop("MISS", target.actor.chest_point() + Vector3(0, 0.6, 0), Color(0.7, 0.7, 0.75), false)
		k += 1
		_flash_prompt_off()
		if res == "miss" or not target.alive():
			break
	_listening = false
	if k >= n and all_good:
		ui.message("%s complete!  %d hits" % [add.name, hits_landed])
		Game.sfx("level_up", -6.0, 1.2)
	elif hits_landed > 1:
		ui.message("%d hits" % hits_landed)
	await _wait(0.7)
	ui.hide_prompt()
	if not target.alive():
		await _kill(target, (target.home - stand).normalized())
	elif target.actor.has_anim("idle"):
		target.actor.play("idle", 0.3)
	# run back
	_face(h.actor, h.home)
	h.actor.play("run", 0.1)
	var back := create_tween()
	back.tween_property(h.actor, "global_position", h.home, Tuning.RUN_BACK)
	_overview(0.7)
	await back.finished
	h.actor.rotation.y = h.facing
	h.actor.play("stance", 0.15)
	ui.message("")


## Test autoplay (Game.autoplay): when the bot presses, relative to the moment. "perfect" presses on
## time; "mixed" misses the last hit of every combo and blocks instead of parrying.
func _auto_offset(k: int) -> float:
	if Game.autoplay == "none":
		return 99.0
	if Game.autoplay == "mixed":
		return 0.3 if k == 2 else (0.1 if k == -1 else 0.0)
	return 0.0


func _flash_prompt_off() -> void:
	await _wait(0.12)
	if not ui.prompt.result.is_empty():
		ui.hide_prompt()


## One hit landing: damage, number, flash, sound, the target flinching.
func _strike(attacker: Battler, target: Battler, dmg: int, heavy := false, react := true, stack := 0) -> void:
	target.take(dmg)
	target.actor.flash()
	ui.pop(str(dmg), target.actor.chest_point() + Vector3(0, 0.22 * stack, 0), Color(1, 1, 1) if not target.is_hero else Color(1, 0.55, 0.45))
	Game.sfx("sword_hit", -2.0 if heavy else -4.0, randf_range(0.9, 1.1))
	cam.shake = 0.9 if heavy else 0.5
	if not react:
		pass
	elif target.is_hero:
		if target.alive():
			target.actor.replay("hurt", 0.05)
			Game.sfx("player_hurt", -6.0)
	else:
		target.actor.replay("stagger", 0.05, 1.4)
		Game.sfx(_monster_sound(target, "hurt"), -4.0)
	var push := (target.actor.global_position - attacker.actor.global_position)
	push.y = 0
	var kb := create_tween()
	var p0 := target.actor.global_position
	kb.tween_property(target.actor, "global_position", p0 + push.normalized() * 0.12, 0.06)
	kb.tween_property(target.actor, "global_position", p0, 0.2)
	ui.refresh(heroes)


func _kill(target: Battler, away: Vector3) -> void:
	Game.sfx(_monster_sound(target, "death"), -2.0)
	if target.id == "skeleton":
		target.actor.scatter(away + Vector3.UP * 0.5, 3.5)
	elif target.actor.has_anim("death"):
		target.actor.replay("death", 0.05)
		await _wait(target.actor.anim_length("death"))
		var t := create_tween()
		t.tween_property(target.actor, "global_position:y", target.actor.global_position.y - 1.2, 1.0)
	await _wait(0.6)


func _face(a: Actor, point: Vector3) -> void:
	var d := point - a.global_position
	d.y = 0
	if d.length() > 0.01:
		a.rotation.y = atan2(-d.x, -d.z)


func _monster_sound(b: Battler, what: String) -> String:
	var pre := "skel" if b.id == "skeleton" else "wolf"
	if what == "windup":
		return "skel_windup" if pre == "skel" else "wolf_growl"
	if what == "strike":
		return "skel_swing" if pre == "skel" else "wolf_snap"
	return "%s_%s" % [pre, what]


func _roar(e: Battler) -> void:
	if e.actor.has_anim("alert"):
		e.actor.replay("alert", 0.1)
	Game.sfx("wolf_howl" if e.id == "hollow_wolf" else "skel_rattle", -4.0)


# --- Enemy turns (block / parry) --------------------------------------------------------------------------

func _enemy_turn(e: Battler) -> void:
	var targets := _living(heroes)
	if targets.is_empty():
		return
	var h: Battler = targets[_rng.randi() % targets.size()]
	var d: Dictionary = Tuning.ENEMIES[e.id]
	var windup: float = d.windup
	var lunge: float = d.lunge
	ui.message("%s attacks %s!   Z: block" % [e.name, h.name])
	_defend_shot(h, e)
	await _wait(0.5)
	var to := h.home - e.home
	to.y = 0
	var stand := h.home - to.normalized() * Tuning.ATTACK_GAP
	stand.y = arena_height(stand.x, stand.z)
	_face(e.actor, h.home)
	var wl := e.actor.anim_length("windup")
	e.actor.replay("windup", 0.1, wl / windup if wl > 0.0 else 1.0)
	Game.sfx(_monster_sound(e, "windup"), -4.0)
	var t0 := now()
	var impact := windup + lunge
	_presses.clear()
	_listening = true
	var lunged := false
	var res := ""
	while res == "":
		await get_tree().process_frame
		var t := now() - t0
		if Game.autoplay != "" and _listening and _presses.is_empty() and t >= impact + _auto_offset(-1):
			_presses.append(t0 + t)
		if not lunged and t >= windup:
			lunged = true
			var sl := e.actor.anim_length("strike")
			e.actor.replay("strike", 0.05, sl / (lunge + 0.12) if sl > 0.0 else 1.0)
			Game.sfx(_monster_sound(e, "strike"), -4.0)
			var mv := create_tween()
			mv.tween_property(e.actor, "global_position", stand, lunge).set_ease(Tween.EASE_IN)
		if Tuning.SHOW_DEFENSE_PROMPT and t >= impact - Tuning.PROMPT_LEAD:
			if not ui.prompt.visible:
				ui.show_prompt(h.actor.chest_point(), Color(1.0, 0.4, 0.35))
			ui.prompt.progress = (t - (impact - Tuning.PROMPT_LEAD)) / Tuning.PROMPT_LEAD
		if not _presses.is_empty():
			var p: float = _presses[0] - t0
			_presses.clear()
			var off := p - impact
			if off < -Tuning.BLOCK_WINDOW:
				res = "late_guard"     # pressed too early: the guard drops before the blow
			elif absf(off) <= Tuning.PARRY_WINDOW:
				res = "parry"
			elif absf(off) <= Tuning.BLOCK_WINDOW:
				res = "block"
			else:
				res = "hit"
			if res != "late_guard" and t < impact:
				# rated early: wait for the blow to actually land
				while now() - t0 < impact:
					await get_tree().process_frame
			if res == "late_guard":
				res = ""
				_listening = false     # one try per blow
		elif t > impact + Tuning.BLOCK_WINDOW:
			res = "hit"
		if not _listening and res == "" and t >= impact:
			res = "hit"
	_listening = false
	ui.prompt.result = "perfect" if res == "parry" else ("good" if res == "block" else "miss")
	var dmg := e.damage_to(h, 1.0)
	if res == "parry":
		ui.pop("PARRY!", h.actor.chest_point() + Vector3(0, 0.6, 0), Color(1, 0.85, 0.3), false)
		Game.sfx("parry", -2.0)
		h.actor.replay("guard", 0.04)
		cam.shake = 0.6
		await _wait(0.25)
		h.actor.replay("atk_a", 0.05)
		await _wait(Actor.SLASH_HIT["atk_a"])
		_strike(h, e, h.damage_to(e, Tuning.PARRY_COUNTER_MULT))
	elif res == "block":
		dmg = maxi(1, roundi(dmg * Tuning.BLOCK_DAMAGE_MULT))
		ui.pop("BLOCK", h.actor.chest_point() + Vector3(0, 0.6, 0), Color(0.8, 0.9, 1.0), false)
		Game.sfx("shield_block", -3.0)
		h.actor.replay("guard", 0.04)
		_strike(e, h, dmg, false, false)
	else:
		_strike(e, h, dmg, true)
	await _wait(0.15)
	ui.hide_prompt()
	if not h.alive():
		h.actor.play("knocked_down", 0.1)
		ui.message("%s falls!" % h.name)
		Game.sfx("player_death", -4.0)
	await _wait(0.5)
	if e.alive():
		if e.actor.has_anim("recover"):
			e.actor.replay("recover", 0.1)
		_face(e.actor, e.home)
		e.actor.play("walk", 0.15, 1.6)
		var back := create_tween()
		back.tween_property(e.actor, "global_position", e.home, 0.5)
		await back.finished
		e.actor.rotation.y = e.facing
		e.actor.play("idle", 0.2)
	else:
		await _kill(e, (e.actor.global_position - h.home).normalized())
	if h.alive():
		h.actor.play("guard_hold" if h.guarding else "stance", 0.2)
	else:
		h.actor.play("down", 0.2)
	_overview(0.6)
	ui.message("")
	await _wait(0.3)


# --- The end ---------------------------------------------------------------------------------------------

func _check_end() -> void:
	if _over:
		return
	if _living(enemies).is_empty():
		_over = true
		await _victory()
	elif _living(heroes).is_empty():
		_over = true
		await _defeat()


func _victory() -> void:
	ui.message("")
	var ex := 0
	var gd := 0
	for e in enemies:
		ex += e.exp_value
		gd += e.gold
	Game.exp_total += ex
	Game.gold += gd
	var shot := Vector3(0, 1.6, HERO_ROW_Z - 4.2)
	for h in heroes:
		if h.alive():
			_face(h.actor, shot)
			h.actor.play("victory", 0.15)
	cam.glide(shot, Vector3(0, 1.0, HERO_ROW_Z), 1.0, Vector3(0.25, 0, 0))
	Game.sfx("level_up", -2.0)
	await _wait(0.6)
	for h in heroes:
		if h.alive():
			h.actor.play("victory_hold", 0.1)
	await _wait(0.6)
	await ui.window(["VICTORY", "EXP  %d" % ex, "Gold  %d" % gd])
	_save_party()
	Game.end_battle("win")


func _defeat() -> void:
	ui.message("")
	cam.glide(Vector3(2.0, 4.5, HERO_ROW_Z + 4.0), Vector3(0, 0.3, HERO_ROW_Z), 1.6)
	await _wait(1.4)
	var pick := await ui.window(["The party has fallen..."], ["Try again", "Back to the field"])
	Game.heal_party()
	Game.draughts = Tuning.START_DRAUGHTS
	if pick == 0:
		await Game.transition.fade_out()
		get_tree().reload_current_scene()
	else:
		Game.fled_from = Game.encounter_id
		Game.end_battle("lose")


## Writes the party's HP back to Game (a knocked-out hero gets up with 1 HP after the battle).
func _save_party() -> void:
	for h in heroes:
		Game.party[h.id] = {"hp": maxi(1, h.hp)}
