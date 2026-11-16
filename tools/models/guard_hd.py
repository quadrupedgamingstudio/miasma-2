"""The Guard (Miasma 1's hero, now Emberwick's town guard) at look B's detail, skinned on the people's rig,
plus his broadsword. Run with Blender's Python module (pip install bpy), from the project root:

    python3 tools/models/guard_hd.py

Writes assets/models/hd/guard_hd.glb, broadsword_hd.glb and their textures (*.png, made here too).

- The rig is rig_kit.HUMAN_BONES (same bones and pivots as Miasma's player.glb), so player.glb's
  walk / run / idle and the battle animations in scripts/actor.gd play on it (Actor converts them to
  Skeleton3D tracks).
- One skinned mesh per material. Cloth, mail and leather bend at the joints (rig_kit.ramp weights); the
  hard "extras" ride one bone rigidly: the helm, spaulders, knee cops, greaves, sabatons, the emblem.
- He wears Emberwick's ember-red tabard with the town's flame over his mail (Cody 2026-11-15: keep it).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rig_kit as K  # noqa: E402
from rig_kit import box, ellipsoid, loft, ramp, rib, rot, at  # noqa: E402
import numpy as np  # noqa: E402


def build_guard(rig):
    P = rig.piece

    # hips: the hauberk's waist under the belt, the belt and its buckle, a pouch
    P("waist", "hips", "mail", lambda m: loft(m, [(-0.09, 0.172, 0.118), (0.0, 0.178, 0.12), (0.07, 0.176, 0.12)], "mail", e=2.3),
      ramp([(0.03, {"hips": 1}), (0.08, {"hips": 0.6, "spine": 0.4})]))
    P("belt", "hips", "leather", lambda m: loft(m, [(0.0, 0.186, 0.127), (0.048, 0.186, 0.127)], "leather", e=2.3))
    P("buckle", "hips", "brass", lambda m: box(m, (0.0, 0.024, -0.13), (0.05, 0.045, 0.012), "brass"))
    P("pouch", "hips", "leather", lambda m: box(m, (-0.17, -0.03, -0.04), (0.04, 0.075, 0.06), "leather", xf=rot("Y", -12)))

    # chest: the hauberk, the ember-red tabard over it, Emberwick's flame on the front
    trunk = ramp([(-0.25, {"hips": 0.55, "spine": 0.45}), (-0.17, {"spine": 1}), (-0.06, {"spine": 0.3, "chest": 0.7}),
                  (0.0, {"chest": 1}), (0.24, {"chest": 1}), (0.29, {"chest": 0.6, "neck": 0.4})])
    torso = [(-0.24, 0.172, 0.114), (-0.12, 0.168, 0.11), (0.0, 0.178, 0.118, 0, -0.004), (0.1, 0.19, 0.126, 0, -0.008),
             (0.18, 0.198, 0.12, 0, -0.004), (0.235, 0.18, 0.1), (0.27, 0.12, 0.08), (0.29, 0.06, 0.055)]
    P("hauberk", "chest", "mail", lambda m: loft(m, torso, "mail", e=2.4, cap1=True), trunk)
    tab = [(-0.25, 0.184, 0.126), (-0.12, 0.18, 0.122), (0.0, 0.19, 0.13, 0, -0.004), (0.1, 0.2, 0.137, 0, -0.008), (0.17, 0.205, 0.132, 0, -0.004)]
    P("tabard", "chest", "cloth", lambda m: loft(m, tab, "cloth", e=2.4), trunk)

    def emblem(m):
        z, s, y = -0.139, 0.075, 0.05
        m.face([(-s, y - s, z), (s, y - s, z), (s, y + s, z), (-s, y + s, z)], [(0, 0), (1, 0), (1, 1), (0, 1)], smooth=False)
    P("emblem", "chest", "emblem", emblem)

    # neck and head
    P("neck", "neck", "skin", lambda m: loft(m, [(-0.04, 0.046, 0.044), (0.09, 0.044, 0.042)], "skin"),
      ramp([(-0.03, {"chest": 0.5, "neck": 0.5}), (0.01, {"neck": 1}), (0.05, {"neck": 0.6, "head": 0.4}), (0.09, {"head": 1})]))
    P("head", "head", "skin", lambda m: ellipsoid(m, (0, 0.092, -0.004), (0.071, 0.104, 0.09), "skin", seg=18, rings=12))
    P("nose", "head", "skin", lambda m: box(m, (0, 0.078, -0.094), (0.022, 0.04, 0.026), "skin", xf=rot("X", -12)))
    for side in (1, -1):
        P("eye_%s" % side, "head", "dark", lambda m, s=side: ellipsoid(m, (s * 0.027, 0.1, -0.083), (0.013, 0.008, 0.006), "dark", seg=8, rings=4))
        P("brow_%s" % side, "head", "hair", lambda m, s=side: box(m, (s * 0.029, 0.114, -0.087), (0.032, 0.01, 0.012), "hair", xf=rot("Z", s * -10)))
    P("beard", "head", "hair", lambda m: ellipsoid(m, (0, 0.024, -0.026), (0.075, 0.07, 0.075), "hair", seg=18, rings=10,
                                                   keep=lambda x, y, z: y < 0.05 and z < 0.02 and not (abs(x) < 0.02 and 0.034 < y)))
    P("moustache", "head", "hair", lambda m: box(m, (0, 0.054, -0.094), (0.05, 0.014, 0.016), "hair"))
    # the iron helm: a pointed spangenhelm with a rim band, a nasal and the mail aventail
    dome = [(0.126, 0.087, 0.104), (0.168, 0.083, 0.099), (0.204, 0.071, 0.086), (0.232, 0.051, 0.063), (0.252, 0.026, 0.032), (0.264, 0.004, 0.005)]
    P("helm", "head", "iron", lambda m: loft(m, dome, "iron", seg=20))
    P("helm_band", "head", "iron", lambda m: loft(m, [(0.121, 0.093, 0.11), (0.149, 0.092, 0.109)], "iron", seg=20))
    P("nasal", "head", "iron", lambda m: box(m, (0, 0.107, -0.105), (0.016, 0.074, 0.008), "iron", xf=rot("X", -4)))
    for k in range(4):
        P("helm_rib_%d" % k, "head", "brass", lambda m, k=k: rib(m, dome[:-1], math.radians(45 + 90 * k), 0.006, "brass"))
    # the aventail hangs from the helm round the sides and back; the face stays open (65 degrees either side)
    gap = math.radians(65)
    P("aventail", "head", "mail", lambda m: loft(m, [(0.126, 0.092, 0.108), (0.06, 0.097, 0.111), (-0.02, 0.118, 0.12), (-0.075, 0.15, 0.13)],
                                                 "mail", a0=-math.pi / 2 + gap, a1=math.pi * 1.5 - gap, seg=18),
      ramp([(0.05, {"head": 1}), (-0.075, {"head": 0.45, "neck": 0.35, "chest": 0.2})]))

    # arms: mail sleeves, iron spaulders, quilted gambeson forearms, leather bracers and gloves
    for side, sn in ((1, "r"), (-1, "l")):
        arm, fore, hand = "arm_" + sn, "forearm_" + sn, "hand_" + sn
        P("sleeve_" + sn, arm, "mail", lambda m, s=side: loft(m, [(0.03, 0.064, 0.062, s * 0.008), (-0.1, 0.06, 0.057, s * 0.008),
                                                                 (-0.22, 0.057, 0.054, s * 0.01), (-0.3, 0.061, 0.058, s * 0.012), (-0.335, 0.068, 0.064, s * 0.014)], "mail"),
          ramp([(-0.335, {arm: 0.35, fore: 0.65}), (-0.27, {arm: 1}), (-0.06, {arm: 1}), (0.04, {"chest": 0.5, arm: 0.5})]))
        P("spaulder_" + sn, arm, "iron", lambda m, s=side: loft(m, [(-0.085, 0.072, 0.078), (-0.02, 0.078, 0.084), (0.025, 0.066, 0.072), (0.05, 0.04, 0.045), (0.062, 0.008, 0.01)],
                                                                "iron", xf=at(s * 0.028, 0.0, 0.0) @ rot("Z", s * -34)))
        P("forearm_" + sn, fore, "padding", lambda m: loft(m, [(0.03, 0.05, 0.048), (-0.05, 0.048, 0.046), (-0.09, 0.045, 0.043)], "padding"),
          ramp([(-0.03, {fore: 1}), (0.03, {arm: 0.55, fore: 0.45})]))
        P("bracer_" + sn, fore, "leather", lambda m: loft(m, [(-0.07, 0.049, 0.047), (-0.16, 0.044, 0.042), (-0.24, 0.043, 0.04), (-0.255, 0.048, 0.045)], "leather"),
          ramp([(-0.255, {fore: 0.5, hand: 0.5}), (-0.2, {fore: 1})]))
        for k, y in enumerate((-0.11, -0.2)):
            P("bracer_strap_%s%d" % (sn, k), fore, "dark", lambda m, y=y: loft(m, [(y, 0.0495, 0.0475), (y + 0.012, 0.0495, 0.0475)], "dark"))
        P("cuff_" + sn, hand, "boot", lambda m: loft(m, [(0.02, 0.042, 0.045), (-0.03, 0.036, 0.045)], "boot"),
          ramp([(-0.02, {hand: 1}), (0.02, {fore: 0.5, hand: 0.5})]))
        if side > 0:
            # the sword hand: a fist round the grip
            P("palm_r", "hand_r", "boot", lambda m: loft(m, [(-0.01, 0.026, 0.044), (-0.055, 0.028, 0.048), (-0.075, 0.026, 0.044)], "boot", cap1=True, e=2.6))
            P("fingers_r", "hand_r", "boot", lambda m: ellipsoid(m, (-0.006, -0.083, 0.0), (0.032, 0.03, 0.05), "boot", seg=12, rings=8))
            P("thumb_r", "hand_r", "boot", lambda m: loft(m, [(0, 0.013, 0.012), (0.045, 0.011, 0.01)], "boot", seg=8, cap1=True,
                                                           xf=at(-0.02, -0.04, -0.04) @ rot("Z", 60) @ rot("X", -30)))
        else:
            # the off hand: open, fingers together
            P("palm_l", "hand_l", "boot", lambda m: loft(m, [(-0.01, 0.022, 0.042), (-0.07, 0.022, 0.044)], "boot", cap1=True, e=2.6))
            P("fingers_l", "hand_l", "boot", lambda m: loft(m, [(-0.065, 0.019, 0.04), (-0.1, 0.016, 0.036), (-0.118, 0.01, 0.026)], "boot", cap1=True, e=2.4,
                                                             xf=at(0.004, 0, 0) @ rot("Z", -6)))
            P("thumb_l", "hand_l", "boot", lambda m: loft(m, [(0, 0.012, 0.011), (0.045, 0.01, 0.009)], "boot", seg=8, cap1=True,
                                                           xf=at(0.012, -0.03, -0.035) @ rot("Z", -150) @ rot("X", 20)))

    # legs: wool trousers, the mail skirt in two halves, knee-high boots, iron greaves and knee cops,
    # sabaton plates on the feet
    for side, sn in ((1, "r"), (-1, "l")):
        thigh, shin, foot = "thigh_" + sn, "shin_" + sn, "foot_" + sn
        P("trousers_" + sn, thigh, "trousers", lambda m: loft(m, [(0.06, 0.084, 0.084), (-0.1, 0.078, 0.075), (-0.25, 0.064, 0.062), (-0.41, 0.054, 0.057)], "trousers"),
          ramp([(-0.415, {thigh: 0.45, shin: 0.55}), (-0.36, {thigh: 1}), (-0.04, {thigh: 1}), (0.06, {"hips": 0.6, thigh: 0.4})]))
        P("skirt_" + sn, thigh, "mail", lambda m, s=side: loft(m, [(0.1, 0.1, 0.122, -s * 0.012), (0.0, 0.106, 0.128, -s * 0.01), (-0.12, 0.112, 0.132, -s * 0.004), (-0.215, 0.118, 0.136)], "mail"),
          ramp([(-0.1, {thigh: 1}), (0.0, {"hips": 0.4, thigh: 0.6}), (0.1, {"hips": 0.75, thigh: 0.25})]))
        P("boot_" + sn, shin, "boot", lambda m: loft(m, [(-0.01, 0.06, 0.064), (-0.06, 0.056, 0.06), (-0.18, 0.051, 0.056, 0, 0.004), (-0.33, 0.043, 0.047), (-0.42, 0.046, 0.05)], "boot"),
          ramp([(-0.42, {shin: 0.4, foot: 0.6}), (-0.38, {shin: 1}), (-0.06, {shin: 1}), (0.0, {thigh: 0.3, shin: 0.7})]))
        P("boot_cuff_" + sn, shin, "leather", lambda m: loft(m, [(-0.05, 0.066, 0.07), (0.0, 0.07, 0.074)], "leather"),
          ramp([(-0.05, {shin: 1}), (0.0, {thigh: 0.35, shin: 0.65})]))
        P("greave_" + sn, shin, "iron", lambda m: loft(m, [(-0.07, 0.066, 0.07), (-0.2, 0.062, 0.066, 0, 0.003), (-0.34, 0.054, 0.058)], "iron",
                                                      a0=-math.pi * 0.92, a1=-math.pi * 0.08, seg=10))
        P("knee_" + sn, shin, "iron", lambda m: loft(m, [(0.0, 0.058, 0.06), (0.03, 0.05, 0.052), (0.055, 0.03, 0.032), (0.066, 0.004, 0.004)], "iron",
                                                    xf=at(0, 0.005, -0.03) @ rot("X", -90)))
        # feet: lofted heel to toe (the loft's Y runs along +Z here; a section's z is the foot's height, down)
        P("foot_" + sn, foot, "boot", lambda m: loft(m, [(0.048, 0.03, 0.036, 0, 0.04), (0.02, 0.044, 0.052, 0, 0.03), (-0.04, 0.047, 0.045, 0, 0.045),
                                                        (-0.11, 0.045, 0.034, 0, 0.055), (-0.155, 0.036, 0.024, 0, 0.06), (-0.172, 0.012, 0.01, 0, 0.065)],
                                                    "boot", xf=rot("X", 90), cap0=True, cap1=True))
        P("sabaton_" + sn, foot, "iron", lambda m: loft(m, [(0.0, 0.05, 0.05, 0, 0.022), (-0.06, 0.05, 0.042, 0, 0.032), (-0.12, 0.046, 0.032, 0, 0.042)],
                                                       "iron", xf=rot("X", 90), a0=-math.pi * 0.92, a1=-math.pi * 0.08, seg=8))


def build_sword():
    """The broadsword, in the PS1 sword's frame: blade up +Y from the crossguard, grip at the origin."""
    r = K.Rigid([("broadsword", None, (0, 0, 0))])
    r.piece("blade", "broadsword", "steel", lambda m: loft(m, [(0.085, 0.038, 0.011), (0.3, 0.036, 0.011), (0.6, 0.033, 0.01), (0.8, 0.027, 0.009),
                                                               (0.88, 0.014, 0.006), (0.905, 0.001, 0.001)], "steel", seg=4, e=1.0, cap0=True))
    r.piece("fuller", "broadsword", "dark", lambda m: loft(m, [(0.1, 0.007, 0.0115), (0.7, 0.006, 0.0105)], "dark", seg=4, e=1.0))
    r.piece("crossguard", "broadsword", "iron", lambda m: loft(m, [(-0.122, 0.012, 0.014), (-0.1, 0.01, 0.012), (0.1, 0.01, 0.012), (0.122, 0.012, 0.014)],
                                                               "iron", seg=8, xf=at(0, 0.066, 0) @ rot("Z", 90), cap0=True, cap1=True))
    r.piece("grip", "broadsword", "grip", lambda m: loft(m, [(-0.066, 0.016, 0.014), (0.0, 0.018, 0.016), (0.058, 0.016, 0.014)], "grip", seg=10))
    r.piece("pommel", "broadsword", "iron", lambda m: ellipsoid(m, (0, -0.09, 0), (0.028, 0.03, 0.02), "iron", seg=12, rings=8))
    return r


# --- textures (64 px pixel art) -------------------------------------------------------------------

def textures():
    r = np.random.default_rng(5)
    n = 64
    yy, xx = np.mgrid[0:n, 0:n]
    noise = lambda s: K.wrapnoise(r, n, s)  # noqa: E731
    img = lambda v, cols: K.ramp_img(v, cols, n)  # noqa: E731
    out = {}

    # mail: rows of rings, each row offset, lit from the top left
    v = np.full((n, n), 0.05)
    ring = 8
    for row in range(n // ring + 1):
        off = (row % 2) * ring // 2
        for col in range(n // ring + 1):
            cy, cx = row * ring + ring // 2, col * ring + off
            dy = (yy - cy + n // 2) % n - n // 2
            dx = (xx - cx + n // 2) % n - n // 2
            d = np.hypot(dy, dx * 0.9)
            m = (d > 1.6) & (d < 3.9)
            light = 0.55 - (dy + dx) / 10.0
            v = np.where(m, np.maximum(v, light), v)
    v += (noise(6) - 0.5) * 0.2
    out["mail"] = img(v, [(22, 23, 28), (40, 42, 49), (60, 63, 71), (82, 86, 94), (108, 112, 120), (140, 144, 150)])

    # iron: dark hammered plate
    v = 0.45 + (noise(8) - 0.5) * 0.4 + (noise(1.5) - 0.5) * 0.25
    for _ in range(14):
        cy, cx = r.integers(0, n, 2)
        d = np.hypot((yy - cy + n // 2) % n - n // 2, (xx - cx + n // 2) % n - n // 2)
        v += np.exp(-(d / 3.5) ** 2) * 0.18 * np.sign(r.random() - 0.4)
    for _ in range(6):
        y0, x0 = r.integers(0, n, 2)
        for t in range(r.integers(5, 14)):
            v[(y0 + t // 3) % n, (x0 + t) % n] = 0.95
    out["iron"] = img(v, [(44, 46, 54), (64, 68, 76), (86, 90, 99), (110, 114, 122), (138, 142, 150), (172, 176, 182)])

    # steel: brighter, polished blade
    v = 0.6 + (noise(10) - 0.5) * 0.4 + (xx % 16 == 0) * 0.2
    out["steel"] = img(v, [(70, 74, 82), (110, 114, 122), (150, 154, 162), (186, 190, 196), (220, 224, 228)])

    # leather: brown with grain and a stitched seam
    v = 0.5 + (noise(5) - 0.5) * 0.5 + (noise(0.8) - 0.5) * 0.35
    v[(yy % 32 == 30) & (xx % 4 < 2)] = 0.95
    v[(yy % 32 == 31)] -= 0.25
    out["leather"] = img(v, [(40, 26, 18), (62, 40, 26), (86, 56, 36), (108, 74, 48), (136, 98, 64)])
    out["boot"] = img(v * 0.9, [(24, 18, 14), (38, 28, 20), (56, 40, 28), (74, 54, 38), (96, 72, 50)])
    out["grip"] = img(((xx + yy) % 8 < 4) * 0.5 + v * 0.4, [(30, 20, 14), (56, 36, 24), (84, 56, 36), (110, 76, 50)])

    # dark: straps, eyes, the fuller's shadow
    out["dark"] = img(0.4 + (noise(3) - 0.5) * 0.3, [(14, 12, 12), (26, 22, 20), (38, 32, 28)])

    # cloth: Emberwick's ember-red wool tabard, a soft weave
    weave = ((xx % 4 < 2) ^ (yy % 4 < 2)) * 0.12
    v = 0.5 + weave + (noise(7) - 0.5) * 0.45 + (noise(1) - 0.5) * 0.15
    out["cloth"] = img(v, [(52, 14, 12), (78, 22, 16), (106, 32, 20), (134, 44, 24), (164, 62, 32)])

    # padding: the quilted gambeson (diamond quilting)
    q = ((xx + yy) % 16 == 0) | ((xx - yy) % 16 == 0)
    v = 0.6 + (noise(4) - 0.5) * 0.3 - q * 0.4
    out["padding"] = img(v, [(62, 54, 42), (96, 86, 66), (128, 116, 90), (156, 144, 114), (180, 170, 140)])

    # trousers: dark brown-grey wool
    v = 0.5 + (noise(6) - 0.5) * 0.5 + ((yy % 3) == 0) * 0.08
    out["trousers"] = img(v, [(34, 30, 28), (50, 44, 40), (68, 60, 54), (88, 78, 70)])

    # skin and hair (the Guard's: skin 1, dark brown hair)
    v = 0.55 + (noise(5) - 0.5) * 0.3
    out["skin"] = img(v, [(168, 114, 84), (194, 138, 104), (214, 160, 124), (232, 184, 148)])
    v = 0.5 + np.sin(xx * 1.7 + noise(4) * 9) * 0.3 + (noise(1) - 0.5) * 0.3
    out["hair"] = img(v, [(26, 18, 14), (44, 30, 22), (64, 44, 30), (88, 62, 42)])

    # brass: buckle, helm ribs
    v = 0.55 + (noise(4) - 0.5) * 0.6
    out["brass"] = img(v, [(86, 60, 22), (130, 96, 38), (176, 136, 58), (214, 176, 90)])

    for k, im in out.items():
        K.save_png(k, im)

    # emblem: Emberwick's flame in a ring, gold on the red, with alpha
    s = 64
    yy, xx = np.mgrid[0:s, 0:s].astype(float)
    cx, cy = 31.5, 31.5
    d = np.hypot(xx - cx, yy - cy)
    rgba = np.zeros((s, s, 4), dtype=np.uint8)
    ring_m = (d > 25) & (d < 30)
    ny = (yy - 12) / 40.0
    flame = np.zeros((s, s), bool)
    for ox, w, top in ((0, 11, 0.0), (-9, 6, 0.35), (9, 6, 0.3)):
        prof = np.clip((ny - top) / (1 - top), 0, 1)
        half = w * np.sin(np.clip(prof, 0, 1) * math.pi * 0.85) ** 0.8
        flame |= (np.abs(xx - cx - ox * prof) < half) & (ny > top) & (ny < 1.0)
    inner = flame & ~(np.roll(flame, 2, 0) & np.roll(flame, -2, 0) & np.roll(flame, 2, 1) & np.roll(flame, -2, 1))
    gold, dark = (226, 170, 60), (40, 14, 10)
    rgba[ring_m] = (*gold, 255)
    rgba[flame] = (*gold, 255)
    rgba[flame & (ny > 0.62)] = (250, 214, 110, 255)
    rgba[inner] = (*dark, 255)
    rgba[(d >= 30) & (d < 31.5)] = (*dark, 255)
    K.save_png("emblem", rgba)


def main():
    textures()
    K.clear()
    rig = K.Rig(K.HUMAN_BONES, "guard")
    build_guard(rig)
    rig.build()
    K.export(os.path.join(K.OUT, "guard_hd.glb"))
    print("guard_hd.glb: skinned, %d triangles" % rig.tris)

    K.clear()
    r = build_sword()
    K.export(os.path.join(K.OUT, "broadsword_hd.glb"))
    print("broadsword_hd.glb: %d triangles" % r.tris)


if __name__ == "__main__":
    main()
