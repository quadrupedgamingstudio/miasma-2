# Miasma II: JRPG demo

A tiny JRPG demo for the Miasma sequel idea: walk a stretch of Emberwick's outskirts
in third person, bump into a monster, and fight it with Legend of Dragoon-style timed combos.
Godot 4.7.2, Forward+ renderer. The look (Cody's pick, 2026-11-15): real lighting and fog on crisp
pixel-art textures, higher-detail textures and models rebuilt in Blender ("look B" of the look test;
the PS1 look is gone). The Guard, Kael, the Hollow Wolf and the Skeleton are all Blender-built; the people
and the wolf are skinned on real rigs.

**Getting updates:** close Godot, double-click `pull.bat` (GitHub: quadrupedgamingstudio/miasma-2).

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
- `scripts/actor.gd`: a character model (the rebuilt heroes and monsters from `assets/models/hd/`),
  player.glb's walk/run/idle converted onto the heroes' rig, and the party's battle animations made in code.
- `scripts/world_kit.gd`: scenery built in code (ground, trees, rocks, stakes, campfire, mist, sky).
- `scripts/field/`: the field (`field.gd`), leader, follower, camera, roaming monsters.
- `scripts/battle/`: the battle flow (`battle.gd`), fighters, camera, UI, the timing prompt.
- `scripts/ui/`: window styles, field HUD, the swirl transition.
- `scripts/look.gd`: lighting, fog and the screen dither; `scripts/materials.gd`: every material;
  `shaders/lit*.gdshader`: the surfaces; `shaders/dither_post.gdshader`: the dither.
- `assets/textures_hd/`: the higher-detail textures, made by `tools/textures/gen_hd.py`.
- `assets/models/hd/`: the rebuilt models and their textures, made in Blender by scripts in `tools/models/`
  (`pip install bpy`, then e.g. `python3 tools/models/guard_hd.py`): `rig_kit.py` (shared: rigs, skinning,
  shapes, animation keys), `guard_hd.py`, `kael_hd.py`, `hollow_wolf_hd.py`, `skeleton_hd.py`
  (all built from crisp pieces with tiled textures). `sculpt_kit.py` is retired (the one-mesh sculpt pass, 2026-11-15;
  Cody 2026-11-16: it looked bad in the game), kept for reference.
- `tools/test/`: screenshot drivers (`shoot.sh shot_field`, `shot_portrait`, `shot_rig` (every model in key
  poses; `RIG=guard,kael`), `battle_auto`; Forward+ needs
  Vulkan: `DRIVER=vulkan`, the default).
