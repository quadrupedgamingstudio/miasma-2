class_name Battler
extends RefCounted
## One fighter in a battle: a party member or a monster, with its stats (Tuning) and its Actor.

var id := ""             # "kael", "guard", "skeleton", "hollow_wolf"
var name := ""
var is_hero := false
var max_hp := 1
var hp := 1
var atk := 1
var def := 1
var spd := 1
var guarding := false
var actor: Actor
var home := Vector3.ZERO  # where it stands
var facing := 0.0         # yaw when standing home
var exp_value := 0
var gold := 0


static func hero(hero_id: String) -> Battler:
	var b := Battler.new()
	var d: Dictionary = Tuning.PARTY[hero_id]
	b.id = hero_id
	b.name = d.name
	b.is_hero = true
	b.max_hp = d.max_hp
	b.hp = clampi(int(Game.party.get(hero_id, {}).get("hp", d.max_hp)), 0, b.max_hp)
	b.atk = d.atk
	b.def = d.def
	b.spd = d.spd
	b.actor = Actor.make(hero_id)
	return b


static func monster(kind: String) -> Battler:
	var b := Battler.new()
	var d: Dictionary = Tuning.ENEMIES[kind]
	b.id = kind
	b.name = d.name
	b.max_hp = d.max_hp
	b.hp = b.max_hp
	b.atk = d.atk
	b.def = d.def
	b.spd = d.spd
	b.exp_value = d.exp
	b.gold = d.gold
	b.actor = Actor.make(kind)
	return b


func alive() -> bool:
	return hp > 0


## Damage this attacker deals to `target` for one hit of `mult` strength.
func damage_to(target: Battler, mult: float) -> int:
	var raw := atk * mult - target.def * Tuning.DEF_FACTOR
	raw *= randf_range(1.0 - Tuning.DAMAGE_SPREAD, 1.0 + Tuning.DAMAGE_SPREAD)
	if target.guarding:
		raw *= Tuning.GUARD_DAMAGE_MULT
	return maxi(1, roundi(raw))


func take(amount: int) -> void:
	hp = clampi(hp - amount, 0, max_hp)


func heal(amount: int) -> void:
	hp = clampi(hp + amount, 0, max_hp)
