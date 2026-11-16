"""Kael (the placeholder city-faction hero), second pass: one continuous skinned mesh with his own 256 px
pixel-art atlas (sculpt_kit.py), plus his short sword. Run with Blender's Python module (pip install bpy),
from the project root:

    python3 tools/models/kael_hd.py

Writes assets/models/hd/kael_hd.glb (mesh `kael_body__kael_atlas` on the people's rig), kael_atlas.png,
short_sword_hd.glb, tools/models/blend/kael.blend and tools/models/maps/kael.npz.

His outfit is Actor.DRESS["kael"] (Cody 2026-11-15: same as before; likely the fighter class's default): a
moulded leather cuirass with tassets and shoulder guards over a linen shirt, leather bracers and greaves,
fingerless gloves, cloth trousers, boots, a satchel slung behind the left hip, the short sword. Young,
clean-shaven, copper hair swept back.

How it's written: `F` = closed forms (they make the body's shape and carry the skin weights), `S` = open
plates (thickened, then fused like the forms), `D` = decals (snapped onto the surface; only painted). Every
piece is placed in a bone's frame (Godot axes: Y up, -Z = his front, +X = his right hand), as in rig_kit.py.
The arms hang clear of the torso and the legs clear of each other (gaps over 1.5 cm), so the fused mesh only
joins them at the shoulders and the hips and the animations don't drag one into the other.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rig_kit as K  # noqa: E402
from rig_kit import box, ellipsoid, loft, ramp, rot, at  # noqa: E402
import sculpt_kit as SK  # noqa: E402
from mathutils import Vector  # noqa: E402
import numpy as np  # noqa: E402

for k in ("kael_skin", "kael_hair", "kael_leather", "kael_linen", "kael_trousers", "kael_lip", "kael_brow",
          "kael_eye", "kael_iris", "kael_mouth"):
    K.TILE.setdefault(k, 0.2)

PALETTES = {
    "kael_skin": [(122, 74, 56), (158, 102, 78), (192, 134, 104), (216, 160, 126), (234, 184, 150), (246, 206, 174)],
    "kael_lip": [(168, 104, 84), (188, 122, 100), (206, 140, 116)],
    "kael_mouth": [(70, 32, 26), (96, 48, 38), (120, 64, 52)],
    "kael_hair": [(52, 18, 10), (80, 30, 14), (110, 44, 20), (142, 62, 26), (174, 86, 38), (204, 116, 56), (226, 146, 80)],
    "kael_brow": [(60, 22, 12), (88, 34, 16), (116, 48, 22)],
    "kael_eye": [(170, 164, 150), (206, 200, 186), (228, 224, 212)],
    "kael_iris": [(28, 32, 18), (48, 64, 32), (70, 92, 46)],
    "kael_leather": [(32, 15, 10), (50, 24, 15), (70, 34, 20), (92, 46, 27), (114, 60, 35), (138, 78, 46), (160, 98, 60), (182, 122, 80)],
    "leather": [(24, 16, 10), (40, 26, 16), (58, 40, 26), (78, 56, 36), (100, 74, 48)],
    "kael_linen": [(98, 88, 70), (132, 120, 96), (164, 152, 126), (190, 180, 152), (212, 204, 178), (228, 222, 198)],
    "kael_trousers": [(22, 24, 18), (34, 38, 28), (48, 52, 38), (62, 68, 50), (78, 84, 62)],
    "boot": [(26, 18, 12), (42, 30, 20), (62, 46, 30), (84, 62, 42), (106, 80, 54)],
    "brass": [(70, 48, 18), (116, 84, 32), (162, 126, 54), (204, 172, 92), (230, 210, 140)],
    "dark": [(12, 10, 8), (26, 22, 18), (40, 34, 28)],
}
# what covers what (a higher layer gets a contact line where it meets a lower one)
LAYERS = {"kael_skin": 1, "kael_linen": 2, "kael_trousers": 2, "kael_hair": 4, "boot": 3, "kael_leather": 5,
          "leather": 7, "brass": 9, "dark": 8, "kael_lip": 1, "kael_mouth": 1, "kael_brow": 1, "kael_eye": 1, "kael_iris": 1}


def hair_streaks(pos, nrm, rng):
    """Strands running front to back over the head (the clumps' own grooves come from the AO)."""
    p = pos.reshape(-1, 3)
    c = np.array([0.0, 0.0, 1.618])   # head centre (Blender coords)
    d = p - c
    ang = np.arctan2(d[:, 0], d[:, 2])          # around the front-back axis
    wob = SK.noise3(p, 0.02, 9) * 2.5
    return (np.sin(ang * 30 + wob * 1.6) * 0.07 + (SK.noise3(p * np.array([3, 0.6, 3]), 0.025, 4) - 0.5) * 0.3)


def cloth_folds(axis, freq, amp):
    def fn(pos, nrm, rng):
        p = pos.reshape(-1, 3)
        return np.sin(p[:, axis] * freq + SK.noise3(p, 0.05, 2) * 6) * amp
    return fn


def leather_wear(pos, nrm, rng):
    p = pos.reshape(-1, 3)
    return (SK.noise3(p, 0.01, 7) - 0.5) * 0.16 + (SK.noise3(p, 0.05, 8) - 0.5) * 0.3


STYLE = {
    "kael_skin": dict(base=0.64, ao=0.6, cav=0.12, up=0.1, noise=0.025, cell=0.03, dither=0.3),
    "kael_hair": dict(base=0.4, ao=1.5, cav=0.6, up=0.25, noise=0.0, pattern=hair_streaks, dither=0.5),
    "kael_leather": dict(base=0.42, ao=1.2, cav=0.6, up=0.15, noise=0.0, pattern=leather_wear, dither=0.35),
    "leather": dict(base=0.5, ao=1.0, cav=0.4, noise=0.08),
    "kael_linen": dict(base=0.6, ao=1.2, cav=0.45, up=0.15, noise=0.05, pattern=cloth_folds(2, 140, 0.07)),
    "kael_trousers": dict(base=0.5, ao=1.2, cav=0.45, up=0.12, noise=0.06, pattern=cloth_folds(0, 90, 0.06)),
    "boot": dict(base=0.5, ao=1.1, cav=0.6, up=0.2, noise=0.07),
    "brass": dict(base=0.55, ao=0.8, cav=0.8, up=0.3, noise=0.05),
    "kael_eye": dict(base=0.75, ao=0.4, cav=0.0, up=0.0, noise=0.0, dither=0.2),
    "kael_iris": dict(base=0.5, ao=0.3, cav=0.0, up=0.0, noise=0.0, dither=0.2),
    "kael_lip": dict(base=0.55, ao=0.8, cav=0.2, noise=0.0, dither=0.3),
    "kael_mouth": dict(base=0.4, ao=0.5, cav=0.0, up=0.0, noise=0.0, dither=0.2),
    "kael_brow": dict(base=0.4, ao=0.5, cav=0.0, noise=0.05),
}


def build(sc):
    F, S, D = sc.F.piece, sc.S.piece, sc.D.piece
    trunk = ramp([(-0.25, {"hips": 0.55, "spine": 0.45}), (-0.17, {"spine": 1}), (-0.06, {"spine": 0.3, "chest": 0.7}),
                  (0.0, {"chest": 1}), (0.22, {"chest": 1}), (0.27, {"chest": 0.6, "neck": 0.4})])

    # --- torso (chest frame; the chest bone is at y 1.214). Narrow where the arms hang, deep in the chest.
    cuir = [(-0.275, 0.152, 0.108, 0, 0.004), (-0.2, 0.146, 0.103), (-0.12, 0.141, 0.104, 0, -0.004),
            (-0.04, 0.145, 0.112, 0, -0.01), (0.04, 0.139, 0.119, 0, -0.016), (0.11, 0.124, 0.117, 0, -0.014),
            (0.165, 0.122, 0.107, 0, -0.008), (0.2, 0.112, 0.093, 0, -0.004)]
    F("cuirass", "chest", "kael_leather", lambda m: loft(m, cuir, "kael_leather", e=2.4, cap0=True, cap1=True), trunk)
    # the cuirass moulded over a broad chest (one plate, so it reads as leather over muscle, not two mounds)
    F("chestplate", "chest", "kael_leather", lambda m: ellipsoid(m, (0, 0.07, -0.092), (0.118, 0.075, 0.044), "kael_leather", seg=16, rings=9), trunk)
    F("abs", "chest", "kael_leather", lambda m: ellipsoid(m, (0, -0.08, -0.085), (0.085, 0.12, 0.04), "kael_leather", seg=14, rings=9), trunk)
    # the shirt's yoke over the shoulders (the trapezius slope), joining the deltoids
    F("yoke", "chest", "kael_linen", lambda m: ellipsoid(m, (0, 0.196, 0.006), (0.172, 0.052, 0.09), "kael_linen", seg=20, rings=10), trunk)
    F("collar", "chest", "kael_linen", lambda m: loft(m, [(0.225, 0.064, 0.06), (0.262, 0.056, 0.052)], "kael_linen", cap0=True, cap1=True), trunk)

    # --- hips (hips frame, y 0.961): the cuirass's skirt edge, belt and buckle, the seat of the trousers
    hipw = ramp([(-0.1, {"hips": 1}), (0.03, {"hips": 1}), (0.09, {"hips": 0.6, "spine": 0.4})])
    F("seat", "hips", "kael_trousers", lambda m: ellipsoid(m, (0, -0.045, 0.008), (0.14, 0.1, 0.102), "kael_trousers", seg=18, rings=10), hipw)
    F("waist", "hips", "kael_leather", lambda m: loft(m, [(-0.05, 0.142, 0.104), (0.04, 0.145, 0.106)], "kael_leather", e=2.4, cap0=True, cap1=True), hipw)
    F("belt", "hips", "leather", lambda m: loft(m, [(-0.012, 0.15, 0.112), (0.04, 0.151, 0.113)], "leather", e=2.4, cap0=True, cap1=True), hipw)
    F("buckle", "hips", "brass", lambda m: box(m, (0.0, 0.014, -0.116), (0.046, 0.038, 0.012), "brass"))
    # satchel slung behind the left hip (clear of the left arm)
    F("satchel", "hips", "kael_leather", lambda m: box(m, (-0.1, -0.075, 0.13), (0.15, 0.125, 0.055), "kael_leather", xf=rot("Y", 18), smooth=False))
    F("satchel_flap", "hips", "leather", lambda m: box(m, (-0.104, -0.035, 0.155), (0.152, 0.07, 0.014), "leather", xf=rot("Y", 18)))
    F("satchel_clasp", "hips", "brass", lambda m: box(m, (-0.098, -0.06, 0.168), (0.022, 0.02, 0.008), "brass", xf=rot("Y", 18)))
    for side, sn in ((1, "r"), (-1, "l")):
        thigh = "thigh_" + sn
        S("tasset_" + sn, thigh, "kael_leather",
          lambda m, s=side: loft(m, [(0.085, 0.076, 0.108, -s * 0.014), (0.0, 0.081, 0.112, -s * 0.012), (-0.12, 0.085, 0.114, -s * 0.008)],
                                 "kael_leather", a0=-math.pi * 1.05, a1=math.pi * 0.05, seg=12),
          ramp([(-0.1, {thigh: 1}), (0.0, {"hips": 0.4, thigh: 0.6}), (0.085, {"hips": 0.75, thigh: 0.25})]))

    # --- neck and head (head frame, y 1.518)
    F("neck", "neck", "kael_skin", lambda m: loft(m, [(-0.05, 0.05, 0.046), (0.02, 0.046, 0.044, 0, -0.004), (0.08, 0.044, 0.044, 0, -0.008)], "kael_skin", cap0=True, cap1=True),
      ramp([(-0.03, {"chest": 0.5, "neck": 0.5}), (0.01, {"neck": 1}), (0.05, {"neck": 0.6, "head": 0.4}), (0.09, {"head": 1})]))
    H = "head"
    _F = F

    def F(name, bone, mat, fn, w=None):   # noqa: N802  (head pieces scaled up a little: he looked pinheaded)
        if bone == H:
            return _F(name, bone, mat, lambda m: (fn(m), _scale(m, HEAD_SCALE)), w)
        return _F(name, bone, mat, fn, w)
    _D = D

    def D(name, bone, mat, fn, w=None):   # noqa: N802
        if bone == H:
            return _D(name, bone, mat, lambda m: (fn(m), _scale(m, HEAD_SCALE)), w)
        return _D(name, bone, mat, fn, w)
    F("cranium", H, "kael_skin", lambda m: ellipsoid(m, (0, 0.1, 0.006), (0.071, 0.096, 0.087), "kael_skin", seg=22, rings=14))
    face(F, D, H, FACE)
    # hair: a base over the crown (it shows only above the hairline) and swept-back clumps over it
    F("hair_base", H, "kael_hair", lambda m: ellipsoid(m, (0, 0.11, 0.04), (0.069, 0.092, 0.075), "kael_hair", seg=22, rings=14))
    hair_clumps(F)

    # --- arms (arm frame at the shoulder joint; the elbow is at (0.03, -0.309, 0.018))
    for side, sn in ((1, "r"), (-1, "l")):
        arm, fore, hand = "arm_" + sn, "forearm_" + sn, "hand_" + sn
        upper = ramp([(-0.33, {arm: 0.35, fore: 0.65}), (-0.27, {arm: 1}), (-0.05, {arm: 1}), (0.04, {"chest": 0.45, arm: 0.55})])
        F("deltoid_" + sn, arm, "kael_linen", lambda m, s=side: ellipsoid(m, (s * 0.01, -0.03, 0.0), (0.05, 0.07, 0.054), "kael_linen", seg=14, rings=10), upper)
        F("sleeve_" + sn, arm, "kael_linen",
          lambda m, s=side: loft(m, [(0.0, 0.053, 0.055), (-0.08, 0.054, 0.054, s * 0.008, 0.002), (-0.13, 0.053, 0.056, s * 0.012, -0.004),
                                     (-0.2, 0.05, 0.05, s * 0.019, 0.011), (-0.27, 0.047, 0.047, s * 0.026, 0.016), (-0.33, 0.046, 0.046, s * 0.032, 0.019)],
                                 "kael_linen", cap0=True, cap1=True), upper)
        S("pauldron_" + sn, arm, "kael_leather",
          lambda m, s=side: loft(m, [(-0.085, 0.062, 0.066), (-0.035, 0.066, 0.07), (0.0, 0.062, 0.066), (0.03, 0.046, 0.05), (0.048, 0.02, 0.024)],
                                 "kael_leather", seg=12, a0=(-0.6 if s > 0 else 0.4) * math.pi, a1=(0.6 if s > 0 else 1.6) * math.pi,
                                 xf=at(s * 0.018, -0.005, 0.0) @ rot("Z", s * -24)), upper)
        forew = ramp([(-0.25, {fore: 0.5, hand: 0.5}), (-0.2, {fore: 1}), (-0.03, {fore: 1}), (0.03, {arm: 0.55, fore: 0.45})])
        F("elbow_" + sn, fore, "kael_linen", lambda m: loft(m, [(0.035, 0.047, 0.047), (-0.05, 0.045, 0.044, 0.003, -0.006)], "kael_linen", cap0=True, cap1=True), forew)
        F("bracer_" + sn, fore, "kael_leather",
          lambda m, s=side: loft(m, [(-0.035, 0.047, 0.047, s * 0.004, -0.004), (-0.13, 0.042, 0.043, s * 0.01, -0.015),
                                     (-0.225, 0.037, 0.037, s * 0.014, -0.026), (-0.248, 0.04, 0.04, s * 0.015, -0.029)],
                                 "kael_leather", cap0=True, cap1=True), forew)
        for k, y in enumerate((-0.08, -0.17)):
            D("bracer_strap_%s%d" % (sn, k), fore, "leather",
              lambda m, y=y, s=side: loft(m, [(y, 0.05, 0.048, s * 0.006, -0.01), (y - 0.012, 0.05, 0.048, s * 0.006, -0.011)], "leather"))
        handw = ramp([(-0.02, {hand: 1}), (0.02, {fore: 0.5, hand: 0.5})])
        F("glove_" + sn, hand, "boot", lambda m: loft(m, [(0.02, 0.035, 0.042), (-0.02, 0.028, 0.044), (-0.055, 0.026, 0.047), (-0.075, 0.023, 0.043)], "boot", e=2.6, cap0=True, cap1=True), handw)
        if side > 0:   # the sword hand, closed round the grip
            F("fingers_r", "hand_r", "kael_skin", lambda m: ellipsoid(m, (-0.004, -0.083, -0.002), (0.03, 0.03, 0.046), "kael_skin", seg=12, rings=8))
            F("thumb_r", "hand_r", "kael_skin", lambda m: loft(m, [(0, 0.012, 0.011), (0.042, 0.01, 0.009)], "kael_skin", seg=8, cap0=True, cap1=True,
                                                                xf=at(-0.012, -0.045, -0.04) @ rot("Z", 22) @ rot("X", -40)))
        else:
            F("fingers_l", "hand_l", "kael_skin", lambda m: loft(m, [(-0.065, 0.019, 0.039), (-0.1, 0.016, 0.035), (-0.118, 0.01, 0.024)], "kael_skin", e=2.4, cap0=True, cap1=True,
                                                                  xf=at(0.004, 0, 0) @ rot("Z", -6)))
            F("thumb_l", "hand_l", "kael_skin", lambda m: loft(m, [(0, 0.011, 0.01), (0.042, 0.009, 0.008)], "kael_skin", seg=8, cap0=True, cap1=True,
                                                                xf=at(0.012, -0.03, -0.035) @ rot("Z", -150) @ rot("X", 20)))

    # --- legs (thigh frame; the knee is at (0.005, -0.415, -0.01))
    for side, sn in ((1, "r"), (-1, "l")):
        thigh, shin, foot = "thigh_" + sn, "shin_" + sn, "foot_" + sn
        thw = ramp([(-0.415, {thigh: 0.45, shin: 0.55}), (-0.36, {thigh: 1}), (-0.04, {thigh: 1}), (0.06, {"hips": 0.6, thigh: 0.4})])
        F("trousers_" + sn, thigh, "kael_trousers",
          lambda m, s=side: loft(m, [(0.03, 0.074, 0.082, -s * 0.002), (-0.06, 0.073, 0.079, 0, -0.003), (-0.18, 0.067, 0.071, s * 0.004, -0.006),
                                     (-0.3, 0.058, 0.061, s * 0.004, -0.007), (-0.4, 0.053, 0.057, s * 0.005, -0.01), (-0.44, 0.053, 0.057, s * 0.005, -0.01)],
                                 "kael_trousers", cap0=True, cap1=True), thw)
        shw = ramp([(-0.42, {shin: 0.4, foot: 0.6}), (-0.38, {shin: 1}), (-0.06, {shin: 1}), (0.0, {thigh: 0.3, shin: 0.7})])
        F("boot_" + sn, shin, "boot",
          lambda m: loft(m, [(-0.01, 0.054, 0.058), (-0.08, 0.053, 0.062, 0, 0.005), (-0.2, 0.047, 0.053, 0.001, 0.008),
                             (-0.33, 0.041, 0.045, 0.002, 0.013), (-0.42, 0.044, 0.048, 0.003, 0.02)], "boot", cap0=True, cap1=True), shw)
        F("boot_cuff_" + sn, shin, "boot", lambda m: loft(m, [(-0.045, 0.061, 0.066), (0.005, 0.064, 0.069)], "boot", cap0=True, cap1=True),
          ramp([(-0.045, {shin: 1}), (0.005, {thigh: 0.35, shin: 0.65})]))
        S("greave_" + sn, shin, "kael_leather",
          lambda m: loft(m, [(-0.065, 0.062, 0.068), (-0.2, 0.057, 0.063, 0, 0.004), (-0.33, 0.05, 0.055, 0, 0.012)], "kael_leather",
                         a0=-math.pi * 0.95, a1=-math.pi * 0.05, seg=10), shw)
        for k, y in enumerate((-0.11, -0.27)):
            D("greave_strap_%s%d" % (sn, k), shin, "leather", lambda m, y=y: loft(m, [(y, 0.06, 0.064, 0, 0.005), (y - 0.014, 0.06, 0.064, 0, 0.006)], "leather"))
        F("knee_" + sn, shin, "kael_leather", lambda m: ellipsoid(m, (0, 0.012, -0.05), (0.044, 0.05, 0.024), "kael_leather", seg=12, rings=8),
          ramp([(-0.03, {shin: 1}), (0.05, {thigh: 0.4, shin: 0.6})]))
        F("foot_" + sn, foot, "boot",
          lambda m: loft(m, [(0.046, 0.03, 0.034, 0, 0.04), (0.02, 0.042, 0.05, 0, 0.03), (-0.04, 0.045, 0.043, 0, 0.045),
                             (-0.11, 0.043, 0.032, 0, 0.055), (-0.152, 0.034, 0.022, 0, 0.06), (-0.168, 0.012, 0.01, 0, 0.065)],
                         "boot", xf=rot("X", 90), cap0=True, cap1=True))

    # --- decals on the torso: the side lacing, the strap of the satchel (right shoulder to left hip, both sides)
    for s in (1, -1):
        for k in range(5):
            y = -0.18 + k * 0.065
            D("lace_%d_%d" % (s, k), "chest", "dark", lambda m, s=s, y=y: box(m, (s * 0.14, y, 0.0), (0.012, 0.007, 0.05), "dark", xf=rot("Z", s * 8)))
    for front in (True, False):
        z0 = -1 if front else 1
        pts = [(0.13, 0.25, 0.0), (0.08, 0.17, z0 * 0.12), (-0.02, 0.05, z0 * 0.125), (-0.1, -0.08, z0 * 0.12), (-0.14, -0.2, z0 * 0.11), (-0.14, -0.27, z0 * 0.11)]
        D("strap_%s" % front, "chest", "leather", lambda m, pts=pts: strip(m, pts, 0.022))


HEAD_SCALE = 1.07
FACE = os.environ.get("KAEL_FACE", "A")   # Cody picked A (2026-11-15); B and C kept for reference

# three takes on his face (Cody 2026-11-15: fix the scowl, the nose and the mouth). Numbers in the head frame (metres).
FACES = {
    # A, soft: a gentle brow, thin arched brows, a fine straight nose, thin lips
    "A": dict(ridge=(0.052, 0.011, 0.014, -0.068), brow=[(0.011, 0.1185), (0.03, 0.1225), (0.046, 0.1195)], brow_w=0.0082,
              bridge=(0.008, 0.026, 0.01), tip=(0.0, 0.08, -0.097, 0.011, 0.01, 0.011), alae=(0.0105, 0.077, -0.089, 0.0075),
              upper=(0.02, 0.0055, 0.008, 0.056), lower=(0.018, 0.0065, 0.0085, 0.046), mouth_w=0.034,
              jaw=(0.056, 0.024, 2.2), chin=(0.022, 0.019, 0.017), cheek=(0.03, 0.022, 0.016)),
    # B, strong: level, heavier brows, a longer straight nose, a fuller lower lip, a squarer jaw and chin
    "B": dict(ridge=(0.056, 0.012, 0.016, -0.069), brow=[(0.011, 0.1195), (0.03, 0.121), (0.047, 0.1195)], brow_w=0.0085,
              bridge=(0.0105, 0.03, 0.011), tip=(0.0, 0.077, -0.099, 0.0135, 0.012, 0.012), alae=(0.012, 0.074, -0.09, 0.0085),
              upper=(0.021, 0.0055, 0.008, 0.054), lower=(0.02, 0.0075, 0.0095, 0.044), mouth_w=0.038,
              jaw=(0.06, 0.031, 2.6), chin=(0.028, 0.022, 0.019), cheek=(0.031, 0.021, 0.016)),
    # C, young: brows higher and arched, a short slightly upturned nose, small full lips, rounder cheeks
    "C": dict(ridge=(0.05, 0.01, 0.012, -0.067), brow=[(0.012, 0.12), (0.03, 0.1245), (0.045, 0.121)], brow_w=0.007,
              bridge=(0.0075, 0.02, 0.009), tip=(0.0, 0.084, -0.095, 0.0115, 0.0105, 0.011), alae=(0.0105, 0.081, -0.088, 0.0075),
              upper=(0.018, 0.006, 0.0085, 0.058), lower=(0.017, 0.0075, 0.009, 0.0485), mouth_w=0.03,
              jaw=(0.053, 0.021, 2.0), chin=(0.02, 0.017, 0.016), cheek=(0.032, 0.024, 0.018)),
}


def face(F, D, H, which):
    f = FACES[which]
    # the lower face: a jaw that tapers from the cheekbones to the chin along a clean jawline, flat in front
    # (Cody: one round jaw blob bulged round the mouth, as if he were pushing his cheeks up)
    jw, cw, e = f["jaw"]
    secs = [(0.006, cw * 0.8, 0.016, 0, -0.066), (0.022, cw, 0.026, 0, -0.058), (0.04, cw + (jw - cw) * 0.45, 0.044, 0, -0.04),
            (0.065, cw + (jw - cw) * 0.8, 0.058, 0, -0.024), (0.092, jw, 0.068, 0, -0.012), (0.118, jw + 0.008, 0.078, 0, -0.004)]
    F("jaw", H, "kael_skin", lambda m: loft(m, secs, "kael_skin", e=e, seg=20, cap0=True, cap1=True))
    F("chin", H, "kael_skin", lambda m: ellipsoid(m, (0, 0.02, -0.07), f["chin"], "kael_skin", seg=12, rings=8))
    rx, ry, rz, cz = f["ridge"]
    F("brow", H, "kael_skin", lambda m: ellipsoid(m, (0, 0.121, cz), (rx, ry, rz), "kael_skin", seg=16, rings=8))
    for s in (1, -1):
        F("ear_%d" % s, H, "kael_skin", lambda m, s=s: ellipsoid(m, (s * 0.07, 0.092, 0.01), (0.011, 0.025, 0.016), "kael_skin", seg=10, rings=7, xf=rot("Y", s * -12)))
    # the nose: a narrow bridge running down from between the eyes into the tip, wings either side
    bw, bl, bd = f["bridge"]
    tx, ty, tz, trx, try_, trz = f["tip"]
    top = Vector((0, 0.112, -0.082))
    tipc = Vector((0, ty, tz))
    mid = (top + tipc) / 2
    ang = math.degrees(math.atan2(tipc.z - top.z, top.y - tipc.y))
    F("nose_bridge", H, "kael_skin", lambda m: ellipsoid(m, tuple(mid), (bw, (top - tipc).length / 2 + 0.004, bd), "kael_skin", seg=10, rings=8,
                                                          xf=at(*mid) @ rot("X", -ang) @ at(*(-mid))))
    F("nose_tip", H, "kael_skin", lambda m: ellipsoid(m, (tx, ty, tz), (trx, try_, trz), "kael_skin", seg=10, rings=7))
    ax, ay, az, ar = f["alae"]
    for s in (1, -1):
        F("nostril_%d" % s, H, "kael_skin", lambda m, s=s: ellipsoid(m, (s * ax, ay, az), (ar, ar * 0.8, ar), "kael_skin", seg=8, rings=6))
    # lips: upper and lower, the lower a touch fuller; the mouth's line painted between them
    ux, uy, uz, uyc = f["upper"]
    lx, ly, lz, lyc = f["lower"]
    F("lip_upper", H, "kael_skin", lambda m: ellipsoid(m, (0, uyc, -0.0785), (ux, uy, uz), "kael_skin", seg=12, rings=7))
    F("lip_lower", H, "kael_skin", lambda m: ellipsoid(m, (0, lyc, -0.0765), (lx, ly, lz), "kael_skin", seg=12, rings=7))
    mw = f["mouth_w"]
    ym = (uyc + lyc) / 2 + 0.001
    D("mouth", H, "kael_mouth", lambda m: strip(m, [(-mw / 2, ym - 0.0012, -0.09), (-mw / 4, ym, -0.093), (mw / 4, ym, -0.093), (mw / 2, ym - 0.0012, -0.09)], 0.0011))
    D("lip_col", H, "kael_lip", lambda m: ellipsoid(m, (0, lyc - 0.001, -0.085), (lx * 0.75, ly * 0.55, 0.005), "kael_lip", seg=10, rings=5))
    # eyes (white, then the iris on top) and brows as arched strips
    for s in (1, -1):
        D("eye_%d" % s, H, "kael_eye", lambda m, s=s: ellipsoid(m, (s * 0.026, 0.104, -0.078), (0.0105, 0.0048, 0.006), "kael_eye", seg=10, rings=5))
        D("iris_%d" % s, H, "kael_iris", lambda m, s=s: ellipsoid(m, (s * 0.025, 0.1035, -0.08), (0.0058, 0.0055, 0.004), "kael_iris", seg=8, rings=5))
        pts = [(s * x, y, -0.088) for x, y in f["brow"]]
        D("browhair_%d" % s, H, "kael_brow", lambda m, pts=pts: strip(m, pts, f["brow_w"] / 2))


def _scale(m, k):
    for v in m.bm.verts:
        v.co = v.co * k


def strip(m, pts, w):
    for a, b in zip(pts, pts[1:]):
        a, b = Vector(a), Vector(b)
        d = (b - a)
        n = Vector((-d.y, d.x, 0)).normalized() * w
        q = [a - n, a + n, b + n, b - n]
        m.face([tuple(p) for p in q], [(0, 0), (1, 0), (1, 1), (0, 1)], smooth=False)


def hair_clumps(P):
    """Copper hair swept back: clumps like longitude lines from the hairline over the crown to the nape,
    uneven in width, lift and length (so it reads as hair, not a cap), a quiff over the brow, close-cropped
    at the sides, a little longer at the nape."""
    c = Vector((0, 0.104, 0.008))
    r = Vector((0.074, 0.1, 0.09))
    rnd = np.random.default_rng(23)

    def surf(psi, beta, lift):
        # psi: from the top toward the front (+) / back (-); beta: turned about the front-back axis
        d = Vector((0.0, math.cos(psi), -math.sin(psi)))
        cb, sb = math.cos(beta), math.sin(beta)
        d = Vector((d.x * cb - d.y * sb, d.x * sb + d.y * cb, d.z))
        p = Vector((d.x * r.x, d.y * r.y, d.z * r.z))
        nrm = Vector((d.x / r.x, d.y / r.y, d.z / r.z)).normalized()
        return c + p + nrm * lift, nrm
    n = 17
    for i in range(n):
        beta = math.radians(-76 + 152 * i / (n - 1) + rnd.uniform(-3, 3))
        side = abs(beta) / math.radians(76)
        temple = math.exp(-((side - 0.42) / 0.16) ** 2)         # the temples recede, the middle comes to a soft peak
        psi0 = math.radians(47 - 7 * side - 16 * temple - 18 * max(0.0, side - 0.6) + rnd.uniform(-3, 3))
        psi1 = math.radians(-126 + 26 * side + rnd.uniform(-6, 6))
        steps = 12
        w0 = 0.016 * rnd.uniform(0.8, 1.25)
        quiff = max(0.0, 1 - side * 1.6) * rnd.uniform(0.8, 1.2)
        crop = 0.35 + 0.65 * max(0.0, 1 - side * 1.3)        # close-cropped at the sides
        pts, nrms, wid, thk = [], [], [], []
        for k in range(steps):
            t = k / (steps - 1)
            psi = psi0 + (psi1 - psi0) * t
            rise = math.sin(math.pi * min(t / 0.5, 1.0)) if t < 0.5 else 0.0
            lift = 0.0015 + 0.016 * quiff * rise + 0.003 * math.sin(t * math.pi) * crop
            p, nr = surf(psi, beta + math.radians(rnd.uniform(-1.5, 1.5)), lift)
            pts.append(p)
            nrms.append(nr)
            taper = min(1.0, t * 7) * (1 - t * 0.7)              # thins to nothing at the hairline
            wid.append(w0 * max(taper, 0.15))
            thk.append(((0.004 + 0.008 * crop) * taper + 0.0008))
        P("clump_%d" % i, "head", "kael_hair", lambda m, a=pts, b=nrms, w=wid, h=thk: SK.strand(m, a, b, w, h))
    # a few loose locks lifting up and back off the quiff
    for i, (bx, up) in enumerate(((-0.022, 0.02), (0.0, 0.026), (0.02, 0.022))):
        base, nr = surf(math.radians(30), math.radians(bx * 900), 0.014)
        tip = base + Vector((bx * 0.3, up * 0.6, up))
        mid = (base + tip) / 2 + nr * 0.006
        P("lock_%d" % i, "head", "kael_hair", lambda m, a=[base, mid, tip], b=[nr, nr, nr]: SK.strand(m, a, b, [0.012, 0.01, 0.002], [0.007, 0.006, 0.0015]))
    # the nape: a few short clumps hanging lower at the back
    for i, bx in enumerate((-0.03, 0.0, 0.03)):
        base, nr = surf(math.radians(-128), math.radians(bx * 900), 0.004)
        tip = base + Vector((bx * 0.15, -0.035, 0.008))
        P("nape_%d" % i, "head", "kael_hair", lambda m, a=[base, (base + tip) / 2, tip], b=[nr, nr, nr]: SK.strand(m, a, b, [0.014, 0.012, 0.003], [0.006, 0.005, 0.0015]))


def build_sword():
    """The short sword, in the PS1 sword's frame: blade up +Y from the crossguard, grip at the origin."""
    r = K.Rigid([("short_sword", None, (0, 0, 0))])
    n = "short_sword"
    r.piece("blade", n, "steel", lambda m: loft(m, [(0.06, 0.03, 0.009), (0.25, 0.028, 0.009), (0.45, 0.025, 0.008), (0.56, 0.018, 0.007),
                                                    (0.62, 0.008, 0.004), (0.64, 0.001, 0.001)], "steel", seg=4, e=1.0, cap0=True))
    r.piece("fuller", n, "dark", lambda m: loft(m, [(0.08, 0.005, 0.0095), (0.42, 0.004, 0.0088)], "dark", seg=4, e=1.0))
    r.piece("crossguard", n, "iron", lambda m: loft(m, [(-0.08, 0.011, 0.012), (-0.06, 0.009, 0.011), (0.06, 0.009, 0.011), (0.08, 0.011, 0.012)],
                                                    "iron", seg=8, xf=at(0, 0.05, 0) @ rot("Z", 90), cap0=True, cap1=True))
    r.piece("grip", n, "grip", lambda m: loft(m, [(-0.05, 0.015, 0.013), (0.0, 0.017, 0.015), (0.045, 0.015, 0.013)], "grip", seg=10))
    r.piece("pommel", n, "brass", lambda m: ellipsoid(m, (0, -0.068, 0), (0.022, 0.022, 0.018), "brass", seg=12, rings=8))
    return r


def main():
    K.clear()
    sc = SK.Sculpt("kael", K.HUMAN_BONES, voxel=0.0045, target_tris=7000, atlas=256)
    sc.palettes = PALETTES
    sc.layer = LAYERS
    sc.style = STYLE
    sc.decal_lift = {"kael_eye": 0.0015, "kael_iris": 0.0025, "kael_brow": 0.0028, "kael_lip": 0.0012, "kael_mouth": 0.0022, "dark": 0.003, "leather": 0.0025}
    sc.stitch = [("kael_leather", "kael_linen"), ("kael_leather", "kael_trousers")]
    # texel density: the head and face twice the body's, the hands a little more
    sc.density = [(lambda w, c: w.get("head", 0) + w.get("neck", 0) * 0.5 > 1.5, 2.6),
                  (lambda w, c: w.get("hand_r", 0) + w.get("hand_l", 0) > 1.5, 1.3)]
    # the face keeps more triangles than the body when the sculpt is decimated
    # the sides of the face smoothed on the sculpt (Cody 2026-11-15: the cheeks were far too prominent), the
    # nose, lips and brow left sharp
    sc.smooth_region = lambda p: (1.0 if (1.53 < p.z < 1.66 and p.y > 0.02 and abs(p.x) > 0.018) else 0.0)
    sc.detail = lambda p: 1.0 if (p.z > 1.53 and p.z < 1.69 and p.y > 0.03) else 0.0   # Blender axes: +Y is his front
    build(sc)
    sc.finish()
    K.clear()
    r = build_sword()
    K.export(os.path.join(K.OUT, "short_sword_hd.glb"))
    print("short_sword_hd.glb: %d triangles" % r.tris)


if __name__ == "__main__":
    main()
