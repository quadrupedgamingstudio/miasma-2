# Miasma II: JRPG demo

A tiny PS1-style JRPG demo for the Miasma sequel idea: walk a stretch of Emberwick's outskirts
in third person, bump into a monster, and fight it with Legend of Dragoon-style timed combos.
Godot 4.4.1, Compatibility renderer, 320x240 like Miasma.

Design: `claude/miasma-2-design.md` in the Project. Technical notes and asset list:
`claude/miasma-2-prototype.md`.

## Controls
| | Keyboard | Controller |
|---|---|---|
| Move / menus | WASD or arrows | Left stick or D-pad |
| Confirm / timed press | Z, Space or Enter | A |
| Back | X, Backspace or Esc | B |
| Run (field) | Shift | X |
| Turn camera (field) | Q / E | LB / RB |
| Fullscreen | F11 | |

## Files
- `scripts/data/tuning.gd`: every number (stats, combo timings, press windows, damage, speeds, camera).
- `scripts/game.gd`: autoload; input map, party state, field <-> battle switching.
- `scripts/actor.gd`: a character model (party: Miasma's player model dressed two ways; monsters:
  Miasma's skeleton and Hollow Wolf) plus the party's battle animations, made in code.
- `scripts/world_kit.gd`: scenery built in code (ground, trees, rocks, stakes, campfire, mist, sky).
- `scripts/field/`: the field (`field.gd`), leader, follower, camera, roaming monsters.
- `scripts/battle/`: the battle flow (`battle.gd`), fighters, camera, UI, the timing prompt.
- `scripts/ui/`: window styles, field HUD, the swirl transition.
- `shaders/ps1*.gdshader`: a trimmed copy of Miasma's PS1 shader with an outdoor sun.
- `tools/test/`: screenshot drivers (`shoot.sh shot_field`, `shoot.sh battle_auto`).
