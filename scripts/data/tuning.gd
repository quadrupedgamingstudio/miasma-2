class_name Tuning
extends RefCounted
## Every tuning number in the demo lives here, so Cody can tweak them without reading code.
## Times are in seconds, distances in metres, angles in degrees.

# --- Party -----------------------------------------------------------------------------------------
## The two party members. "addition" names their timed combo in ADDITIONS below.
## Names are placeholders (suggestion): the city-faction hero and Miasma 1's hero, now the town guard.
const PARTY := {
	"kael": {
		"name": "Kael", "max_hp": 120, "atk": 14, "def": 6, "spd": 12,
		"addition": "twin_fang",
	},
	"guard": {
		"name": "Guard", "max_hp": 160, "atk": 18, "def": 10, "spd": 8,
		"addition": "bulwark",
	},
}

# --- Additions (timed combos) -------------------------------------------------------------------------
## Each hit lands at `times[i]` seconds after the hero starts swinging. The prompt square closes on
## its frame exactly then. `mults` scale the hit's damage. A perfect press adds PERFECT_BONUS.
## Hit 1 always lands (a miss just weakens it); a miss on any later hit ends the combo there.
const ADDITIONS := {
	"twin_fang": {
		"name": "Twin Fang",
		"times": [0.55, 0.95, 1.30],
		"mults": [1.0, 1.2, 1.7],
	},
	"bulwark": {
		"name": "Bulwark",
		"times": [0.65, 1.30, 1.85, 2.60],
		"mults": [1.0, 1.1, 1.3, 2.2],
	},
}
## How long before the hit the prompt square starts closing in.
const PROMPT_LEAD := 0.5
## Press windows either side of the hit moment.
const PERFECT_WINDOW := 0.05
const GOOD_WINDOW := 0.12
## Extra damage for a perfect press (0.25 = +25%).
const PERFECT_BONUS := 0.25
## Damage of hit 1 when its press is missed (it still lands, weaker).
const MISSED_FIRST_HIT_MULT := 0.6
## Bonus for landing every hit of an Addition ("Addition complete!").
const COMPLETE_BONUS := 0.3

# --- Defending (enemy turns) -----------------------------------------------------------------------
## Press Confirm as the enemy's blow lands. Perfect = parry (no damage, counter-hit); good = block.
const PARRY_WINDOW := 0.06
const BLOCK_WINDOW := 0.16
const BLOCK_DAMAGE_MULT := 0.5
## A parry hits back for this much of the defender's normal hit.
const PARRY_COUNTER_MULT := 0.6
## Show the closing square on enemy turns too (Clair Obscur shows none: false = read the windup).
const SHOW_DEFENSE_PROMPT := true

# --- Guard command and items -------------------------------------------------------------------------
## Guard: takes this much of the damage until the hero's next turn, and heals this much of max HP.
const GUARD_DAMAGE_MULT := 0.5
const GUARD_HEAL := 0.10
## Healing Draughts the party starts with, and how much of max HP one restores.
const START_DRAUGHTS := 3
const DRAUGHT_HEAL := 0.45
## Chance to flee (0..1).
const FLEE_CHANCE := 0.7

# --- Damage -------------------------------------------------------------------------------------------
## damage = (atk * mult - def * DEF_FACTOR) * random(1 - DAMAGE_SPREAD .. 1 + DAMAGE_SPREAD), at least 1.
const DEF_FACTOR := 0.5
const DAMAGE_SPREAD := 0.1

# --- Enemies ------------------------------------------------------------------------------------------
## windup = how long the telegraph lasts before the lunge; lunge = travel time to the hero.
const ENEMIES := {
	"hollow_wolf": {
		"name": "Hollow Wolf", "max_hp": 90, "atk": 22, "def": 4, "spd": 11,
		"windup": 0.9, "lunge": 0.28, "exp": 30, "gold": 12,
	},
	"skeleton": {
		"name": "Skeleton", "max_hp": 110, "atk": 26, "def": 8, "spd": 7,
		"windup": 1.2, "lunge": 0.4, "exp": 40, "gold": 18,
	},
}
## Field encounters: which enemies each roaming monster brings into battle.
const ENCOUNTERS := {
	"wolf": ["hollow_wolf"],
	"pair": ["skeleton", "hollow_wolf"],
}

# --- Field --------------------------------------------------------------------------------------------
const WALK_SPEED := 2.6
const RUN_SPEED := 5.2
const TURN_SPEED := 12.0
## The follower keeps this far behind the leader along the leader's path.
const FOLLOW_GAP := 1.3
## Field camera: distance, height angle, and the step when turning it (Q / E).
const CAM_DISTANCE := 7.5
const CAM_PITCH := 30.0
const CAM_FOV := 50.0
const CAM_TURN_STEP := 45.0
const CAM_FOLLOW := 6.0
## Roaming monsters: wander radius, how near before they chase you, chase speed.
const ROAM_RADIUS := 4.0
const ROAM_SPEED := 1.2
const NOTICE_RANGE := 7.0
const CHASE_SPEED := 3.4
## After fleeing, monsters ignore you this long.
const FLEE_GRACE := 3.0
## The campfire heals the party fully when you rest at it.

# --- Battle presentation --------------------------------------------------------------------------------
## How far in front of its target an attacker stops, and the run there and back.
const ATTACK_GAP := 1.5
const RUN_TO_TARGET := 0.45
const RUN_BACK := 0.4
## Battle camera field of view.
const BATTLE_FOV := 45.0

# --- Look ---------------------------------------------------------------------------------------------
const AMBIENT := Color(0.42, 0.42, 0.48)
const SUN_DIRECTION := Vector3(0.45, 0.8, 0.35)
const SUN_STRENGTH := 0.75
const SUN_COLOR := Color(1.0, 0.93, 0.8)
const FOG_COLOR := Color(0.62, 0.6, 0.66)
const FOG_START := 16.0
const FOG_END := 52.0
