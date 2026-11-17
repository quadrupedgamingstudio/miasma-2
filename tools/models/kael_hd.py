"""Kael (the placeholder city-faction hero) at look B's detail, built the Guard's way: crisp pieces skinned on the
people's rig, tiled 64 px pixel-art textures. Plus his short sword. Run with Blender's Python module (pip install bpy),
from the project root:

    python3 tools/models/kael_hd.py

Writes assets/models/hd/kael_hd.glb, short_sword_hd.glb and Kael's own textures (kael_*.png); shares the Guard's
iron / steel / boot / dark / brass / grip / leather tiles (made by guard_hd.py).

History: the first pass (the rig update) was pieces like this; the second pass (2026-11-15) was one sculpted mesh with
its own atlas (tools/models/sculpt_kit.py). Cody saw that one in the game (2026-11-16): "he looks terrible", the face
and head, blobby melted forms and the proportions, while the Guard "looks pretty good". So Kael is pieces again, at the
Guard's build and detail (Cody's pick: build like the Guard), with a short copper beard (Cody's pick) to frame the face
the way the Guard's beard and helm frame his, and the hair he picked earlier: swept back, a higher hairline, short sides.

His outfit (Actor.DRESS["kael"]; likely the fighter class's default): a leather cuirass with tassets and shoulder
guards over a linen shirt, bracers, fingerless gloves, leather greaves over boots, cloth trousers, a satchel slung
behind the left hip on a strap, the short sword. Same rig and weights scheme as guard_hd.py (see rig_kit.py).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rig_kit as K  # noqa: E402
from rig_kit import box, ellipsoid, loft, ramp, rot, at  # noqa: E402
import numpy as np  # noqa: E402

K.TILE.update({"kael_skin": 0.2, "kael_hair": 0.09, "kael_beard": 0.06, "kael_eye": 0.05, "kael_leather": 0.26,
               "kael_linen": 0.2, "kael_trousers": 0.25})

# the head, in the head bone's frame (the Guard's size): y up, -z is the face
HEAD_C, HEAD_R = (0.0, 0.092, -0.004), (0.071, 0.104, 0.09)
# the hair's shell over it
SCALP_C, SCALP_R = (0.0, 0.095, 0.002), (0.076, 0.108, 0.095)


def scalp_top(x, z):
    """Height of the hair shell's surface over (x, z), or None past its edge."""
    t = 1 - (x / SCALP_R[0]) ** 2 - ((z - SCALP_C[2]) / SCALP_R[2]) ** 2
    return None if t <= 0 else SCALP_C[1] + SCALP_R[1] * math.sqrt(t)


def lock(m, x0, x1, z0, z1, width, thick, n=6, lift=0.0, taper=0.45):
    """One swept lock of hair lying on the shell, combed from the front (z0) to the back (z1), drifting from x0 to x1.
    A loft along the head's +Z (rot X 90: the loft's Y runs to the back, a section's z points down)."""
    secs = []
    for k in range(n + 1):
        t = k / n
        z = z0 + (z1 - z0) * t
        x = x0 + (x1 - x0) * t
        top = scalp_top(x, z)
        if top is None:
            break
        # full in the middle, thin at both ends; the front lifted a little (the sweep)
        w = width * (0.5 + 0.5 * math.sin(math.pi * min(1.0, t * 1.6 + 0.1))) * (1 - taper * t)
        h = thick * math.sin(math.pi * min(0.5, t * 1.8 + 0.04)) * (1 - 0.5 * t)
        rise = lift * math.sin(math.pi * min(1.0, t * 2.5))
        secs.append((z, w, h, x, -(top + h - 0.004 + rise)))
    loft(m, secs, "kael_hair", xf=rot("X", 90), seg=10, e=2.6, cap0=True, cap1=True)


def build_kael(rig):
    P = rig.piece
    trunk = ramp([(-0.25, {"hips": 0.55, "spine": 0.45}), (-0.17, {"spine": 1}), (-0.06, {"spine": 0.3, "chest": 0.7}),
                  (0.0, {"chest": 1}), (0.24, {"chest": 1}), (0.29, {"chest": 0.6, "neck": 0.4})])

    # torso, at the Guard's build: the linen shirt shows at the neck and arms; the leather cuirass over it, laced up
    # the sides, with a moulded chest plate
    shirt = [(-0.22, 0.164, 0.108), (-0.1, 0.161, 0.104), (0.05, 0.172, 0.113, 0, -0.004), (0.17, 0.19, 0.115),
             (0.232, 0.174, 0.097), (0.268, 0.115, 0.076), (0.288, 0.057, 0.052)]
    P("shirt", "chest", "kael_linen", lambda m: loft(m, shirt, "kael_linen", e=2.3, cap1=True), trunk)
    cuir = [(-0.24, 0.174, 0.118), (-0.12, 0.17, 0.114), (0.0, 0.18, 0.123, 0, -0.006), (0.1, 0.192, 0.129, 0, -0.01),
            (0.19, 0.196, 0.121, 0, -0.005), (0.238, 0.168, 0.102)]
    P("cuirass", "chest", "kael_leather", lambda m: loft(m, cuir, "kael_leather", e=2.5), trunk)
    P("plate", "chest", "kael_leather", lambda m: loft(m, [(-0.04, 0.12, 0.012, 0, -0.12), (0.08, 0.142, 0.015, 0, -0.133), (0.17, 0.13, 0.012, 0, -0.123)],
                                                     "kael_leather", a0=-math.pi, a1=0.0, seg=10, e=2.6), trunk)
    # the cuirass's top edge: a dark rolled rim at the neck and armholes
    P("cuirass_rim", "chest", "leather", lambda m: loft(m, [(0.232, 0.172, 0.105), (0.244, 0.165, 0.1)], "leather", e=2.5), trunk)
    for s in (1, -1):
        for k in range(4):
            y = -0.14 + k * 0.07
            P("lace_%d_%d" % (s, k), "chest", "dark", lambda m, s=s, y=y: box(m, (s * 0.178, y, 0.0), (0.012, 0.008, 0.05), "dark", xf=rot("Z", s * 8)), trunk)

    # the satchel's strap: over the right shoulder, across the chest and back, down to the satchel behind the left hip
    # (a real strap now, 4 mm proud of the cuirass, not a flat decal)
    def strap(m):
        front = [(0.175, 0.24, -0.06), (0.09, 0.17, -0.13), (-0.02, 0.05, -0.136), (-0.12, -0.08, -0.128), (-0.17, -0.17, -0.09)]
        back = [(0.175, 0.24, 0.06), (0.09, 0.17, 0.127), (-0.02, 0.05, 0.133), (-0.12, -0.08, 0.126), (-0.165, -0.19, 0.11)]
        for pts in (front, back):
            K.tube(m, pts, 0.011, "leather", seg=4, cap=False)
    P("strap", "chest", "leather", strap, trunk)
    P("strap_top", "chest", "leather", lambda m: K.tube(m, [(0.175, 0.24, -0.06), (0.2, 0.27, 0.0), (0.175, 0.24, 0.06)], 0.011, "leather", seg=4, cap=False), trunk)

    # hips: the cuirass skirt under the belt, the belt and buckle, tassets in two halves (they ride the thighs), the
    # satchel slung behind the left hip, clear of the arm
    P("waist", "hips", "kael_leather", lambda m: loft(m, [(-0.07, 0.17, 0.116), (0.0, 0.173, 0.118), (0.07, 0.172, 0.118)], "kael_leather", e=2.3),
      ramp([(0.03, {"hips": 1}), (0.08, {"hips": 0.6, "spine": 0.4})]))
    P("belt", "hips", "leather", lambda m: loft(m, [(-0.005, 0.182, 0.125), (0.045, 0.182, 0.125)], "leather", e=2.3))
    P("buckle", "hips", "brass", lambda m: box(m, (0.0, 0.02, -0.129), (0.044, 0.04, 0.01), "brass"))
    bag = at(-0.15, -0.075, 0.1) @ rot("Y", -50)
    P("satchel", "hips", "kael_leather", lambda m: box(m, (0, 0, 0), (0.05, 0.13, 0.16), "kael_leather", xf=bag))
    P("satchel_flap", "hips", "leather", lambda m: box(m, (0.0, 0.035, 0.0), (0.06, 0.075, 0.165), "leather", xf=bag @ at(-0.006, 0, 0)))
    P("satchel_buckle", "hips", "brass", lambda m: box(m, (-0.033, 0.0, 0.0), (0.006, 0.02, 0.026), "brass", xf=bag))
    for side, sn in ((1, "r"), (-1, "l")):
        thigh = "thigh_" + sn
        P("tasset_" + sn, thigh, "kael_leather", lambda m, s=side: loft(m, [(0.09, 0.096, 0.118, -s * 0.012), (0.0, 0.101, 0.123, -s * 0.01), (-0.12, 0.105, 0.125, -s * 0.004)],
                                                                         "kael_leather", a0=-math.pi * 1.1, a1=math.pi * 0.1, seg=12),
          ramp([(-0.1, {thigh: 1}), (0.0, {"hips": 0.4, thigh: 0.6}), (0.09, {"hips": 0.75, thigh: 0.25})]))
        P("tasset_rim_" + sn, thigh, "leather", lambda m, s=side: loft(m, [(-0.124, 0.107, 0.127, -s * 0.004), (-0.11, 0.106, 0.126, -s * 0.005)],
                                                                      "leather", a0=-math.pi * 1.1, a1=math.pi * 0.1, seg=12),
          ramp([(-0.1, {thigh: 1}), (0.0, {"hips": 0.4, thigh: 0.6})]))

    # neck and head: young, a short copper beard, copper hair swept back
    P("neck", "neck", "kael_skin", lambda m: loft(m, [(-0.04, 0.047, 0.045), (0.09, 0.045, 0.043)], "kael_skin"),
      ramp([(-0.03, {"chest": 0.5, "neck": 0.5}), (0.01, {"neck": 1}), (0.05, {"neck": 0.6, "head": 0.4}), (0.09, {"head": 1})]))
    P("collar", "chest", "kael_linen", lambda m: loft(m, [(0.25, 0.064, 0.06), (0.296, 0.054, 0.052)], "kael_linen"), trunk)
    P("head", "head", "kael_skin", lambda m: ellipsoid(m, HEAD_C, HEAD_R, "kael_skin", seg=18, rings=12))
    # a jaw that tapers to the chin (the beard covers most of it); a brow ridge so the eyes sit in shadow
    P("jaw", "head", "kael_skin", lambda m: ellipsoid(m, (0, 0.042, -0.034), (0.05, 0.038, 0.056), "kael_skin", seg=14, rings=8))
    P("brow_ridge", "head", "kael_skin", lambda m: ellipsoid(m, (0, 0.111, -0.083), (0.05, 0.011, 0.013), "kael_skin", seg=12, rings=6))
    P("nose", "head", "kael_skin", lambda m: box(m, (0, 0.079, -0.09), (0.016, 0.036, 0.014), "kael_skin", xf=rot("X", -6)))
    P("mouth", "head", "dark", lambda m: box(m, (0, 0.05, -0.088), (0.024, 0.004, 0.006), "dark"))
    for side in (1, -1):
        P("ear_%s" % side, "head", "kael_skin", lambda m, s=side: ellipsoid(m, (s * 0.071, 0.09, 0.006), (0.012, 0.024, 0.016), "kael_skin", seg=8, rings=5))
        # eyes: a pale white and a dark iris, set under the ridge
        P("eye_%s" % side, "head", "kael_eye", lambda m, s=side: ellipsoid(m, (s * 0.027, 0.1, -0.083), (0.012, 0.0065, 0.005), "kael_eye", seg=8, rings=4))
        P("iris_%s" % side, "head", "dark", lambda m, s=side: ellipsoid(m, (s * 0.025, 0.1, -0.087), (0.0055, 0.0055, 0.003), "dark", seg=8, rings=4))
        # brows: copper, firm (at least 8 mm tall so they hold as pixels), angled a touch
        P("brow_%s" % side, "head", "kael_beard", lambda m, s=side: box(m, (s * 0.028, 0.116, -0.089), (0.03, 0.009, 0.006), "kael_beard", xf=rot("Z", s * -8)))

    # the short beard: a close shell over the jaw and chin, up the cheeks to the sideburns, open round the mouth
    def beard_keep(x, y, z):
        if z > 0.03:
            return False
        if abs(x) < 0.03:
            return y < 0.047
        return y < 0.074 - max(0.0, -z - 0.07) * 0.6
    P("beard", "head", "kael_beard", lambda m: ellipsoid(m, (0, 0.047, -0.016), (0.066, 0.052, 0.074), "kael_beard", seg=18, rings=10, keep=beard_keep))
    P("moustache", "head", "kael_beard", lambda m: box(m, (0, 0.058, -0.09), (0.044, 0.008, 0.01), "kael_beard"))
    for side in (1, -1):
        P("moustache_%s" % side, "head", "kael_beard", lambda m, s=side: box(m, (s * 0.025, 0.053, -0.085), (0.008, 0.012, 0.008), "kael_beard", xf=rot("Z", s * 18)))
        P("sideburn_%s" % side, "head", "kael_beard", lambda m, s=side: box(m, (s * 0.069, 0.088, -0.016), (0.01, 0.05, 0.026), "kael_beard"))

    # hair: close-cropped sides and back (a shell), the crown combed back in five swept locks; the hairline higher
    # with a soft peak, the temples receding
    def scalp_keep(x, y, z):
        return y > 0.146 + 0.22 * abs(x) or (z > -0.03 and y > 0.085) or (z > 0.015 and y > 0.04)
    P("scalp", "head", "kael_hair", lambda m: ellipsoid(m, SCALP_C, SCALP_R, "kael_hair", seg=20, rings=14, keep=scalp_keep))
    P("lock_c", "head", "kael_hair", lambda m: lock(m, 0.0, 0.0, -0.074, 0.093, 0.036, 0.011, lift=0.003))
    for side in (1, -1):
        P("lock_m_%s" % side, "head", "kael_hair", lambda m, s=side: lock(m, s * 0.028, s * 0.042, -0.07, 0.09, 0.03, 0.01, lift=0.002))
        P("lock_o_%s" % side, "head", "kael_hair", lambda m, s=side: lock(m, s * 0.052, s * 0.06, -0.05, 0.084, 0.024, 0.008, lift=0.0))

    # arms: linen sleeves, leather shoulder guards, bracers, fingerless gloves
    for side, sn in ((1, "r"), (-1, "l")):
        arm, fore, hand = "arm_" + sn, "forearm_" + sn, "hand_" + sn
        P("sleeve_" + sn, arm, "kael_linen", lambda m, s=side: loft(m, [(0.03, 0.063, 0.061, s * 0.007), (-0.1, 0.059, 0.056, s * 0.008),
                                                                       (-0.22, 0.056, 0.053, s * 0.01), (-0.3, 0.058, 0.055, s * 0.012), (-0.333, 0.062, 0.058, s * 0.013)], "kael_linen"),
          ramp([(-0.333, {arm: 0.35, fore: 0.65}), (-0.27, {arm: 1}), (-0.06, {arm: 1}), (0.04, {"chest": 0.5, arm: 0.5})]))
        P("shoulder_" + sn, arm, "kael_leather", lambda m, s=side: loft(m, [(-0.085, 0.07, 0.076), (-0.02, 0.076, 0.082), (0.022, 0.064, 0.07), (0.048, 0.037, 0.043), (0.058, 0.006, 0.008)],
                                                                        "kael_leather", xf=at(s * 0.026, 0.0, 0.0) @ rot("Z", s * -32)))
        P("shoulder_rim_" + sn, arm, "leather", lambda m, s=side: loft(m, [(-0.093, 0.073, 0.079), (-0.077, 0.074, 0.08)], "leather",
                                                                      xf=at(s * 0.026, 0.0, 0.0) @ rot("Z", s * -32)))
        P("forearm_" + sn, fore, "kael_linen", lambda m: loft(m, [(0.03, 0.049, 0.047), (-0.06, 0.047, 0.045)], "kael_linen"),
          ramp([(-0.03, {fore: 1}), (0.03, {arm: 0.55, fore: 0.45})]))
        P("bracer_" + sn, fore, "kael_leather", lambda m: loft(m, [(-0.05, 0.05, 0.048), (-0.15, 0.046, 0.044), (-0.235, 0.044, 0.042), (-0.25, 0.048, 0.046)], "kael_leather"),
          ramp([(-0.25, {fore: 0.5, hand: 0.5}), (-0.2, {fore: 1})]))
        for k, y in enumerate((-0.09, -0.18)):
            P("bracer_strap_%s%d" % (sn, k), fore, "leather", lambda m, y=y: loft(m, [(y, 0.0485, 0.0465), (y + 0.012, 0.0485, 0.0465)], "leather"))
        P("cuff_" + sn, hand, "boot", lambda m: loft(m, [(0.02, 0.041, 0.044), (-0.03, 0.036, 0.044)], "boot"),
          ramp([(-0.02, {hand: 1}), (0.02, {fore: 0.5, hand: 0.5})]))
        if side > 0:
            P("palm_r", "hand_r", "boot", lambda m: loft(m, [(-0.01, 0.025, 0.043), (-0.055, 0.027, 0.047), (-0.074, 0.025, 0.043)], "boot", cap1=True, e=2.6))
            P("fingers_r", "hand_r", "kael_skin", lambda m: ellipsoid(m, (-0.006, -0.082, 0.0), (0.031, 0.029, 0.048), "kael_skin", seg=12, rings=8))
            P("thumb_r", "hand_r", "kael_skin", lambda m: loft(m, [(0, 0.012, 0.011), (0.044, 0.01, 0.009)], "kael_skin", seg=8, cap1=True,
                                                                xf=at(-0.02, -0.04, -0.04) @ rot("Z", 60) @ rot("X", -30)))
        else:
            P("palm_l", "hand_l", "boot", lambda m: loft(m, [(-0.01, 0.021, 0.041), (-0.068, 0.021, 0.043)], "boot", cap1=True, e=2.6))
            P("fingers_l", "hand_l", "kael_skin", lambda m: loft(m, [(-0.063, 0.018, 0.039), (-0.098, 0.015, 0.035), (-0.116, 0.009, 0.025)], "kael_skin", cap1=True, e=2.4,
                                                                  xf=at(0.004, 0, 0) @ rot("Z", -6)))
            P("thumb_l", "hand_l", "kael_skin", lambda m: loft(m, [(0, 0.011, 0.01), (0.044, 0.009, 0.008)], "kael_skin", seg=8, cap1=True,
                                                                xf=at(0.012, -0.03, -0.035) @ rot("Z", -150) @ rot("X", 20)))

    # legs: cloth trousers, boots, leather greaves strapped over them, knee cops
    for side, sn in ((1, "r"), (-1, "l")):
        thigh, shin, foot = "thigh_" + sn, "shin_" + sn, "foot_" + sn
        P("trousers_" + sn, thigh, "kael_trousers", lambda m: loft(m, [(0.06, 0.083, 0.083), (-0.1, 0.077, 0.074), (-0.25, 0.063, 0.061), (-0.41, 0.053, 0.056)], "kael_trousers"),
          ramp([(-0.415, {thigh: 0.45, shin: 0.55}), (-0.36, {thigh: 1}), (-0.04, {thigh: 1}), (0.06, {"hips": 0.6, thigh: 0.4})]))
        P("boot_" + sn, shin, "boot", lambda m: loft(m, [(-0.01, 0.058, 0.062), (-0.06, 0.055, 0.059), (-0.18, 0.05, 0.055, 0, 0.004), (-0.33, 0.043, 0.047), (-0.42, 0.046, 0.05)], "boot"),
          ramp([(-0.42, {shin: 0.4, foot: 0.6}), (-0.38, {shin: 1}), (-0.06, {shin: 1}), (0.0, {thigh: 0.3, shin: 0.7})]))
        P("boot_cuff_" + sn, shin, "boot", lambda m: loft(m, [(-0.04, 0.064, 0.068), (0.005, 0.068, 0.072)], "boot"),
          ramp([(-0.04, {shin: 1}), (0.005, {thigh: 0.35, shin: 0.65})]))
        P("greave_" + sn, shin, "kael_leather", lambda m: loft(m, [(-0.06, 0.064, 0.068), (-0.2, 0.06, 0.064, 0, 0.003), (-0.33, 0.052, 0.056)], "kael_leather",
                                                              a0=-math.pi * 0.95, a1=-math.pi * 0.05, seg=10))
        for k, y in enumerate((-0.1, -0.27)):
            P("greave_strap_%s%d" % (sn, k), shin, "leather", lambda m, y=y: loft(m, [(y, 0.0605, 0.0645), (y + 0.014, 0.0605, 0.0645)], "leather"))
        P("knee_" + sn, shin, "kael_leather", lambda m: loft(m, [(0.0, 0.054, 0.056), (0.027, 0.047, 0.049), (0.05, 0.027, 0.029), (0.06, 0.004, 0.004)], "kael_leather",
                                                            xf=at(0, 0.0, -0.03) @ rot("X", -90)))
        P("foot_" + sn, foot, "boot", lambda m: loft(m, [(0.047, 0.03, 0.035, 0, 0.04), (0.02, 0.043, 0.051, 0, 0.03), (-0.04, 0.046, 0.044, 0, 0.045),
                                                        (-0.11, 0.044, 0.033, 0, 0.055), (-0.154, 0.035, 0.023, 0, 0.06), (-0.17, 0.011, 0.009, 0, 0.065)],
                                                    "boot", xf=rot("X", 90), cap0=True, cap1=True))


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


def textures():
    r = np.random.default_rng(11)
    n = 64
    yy, xx = np.mgrid[0:n, 0:n]
    noise = lambda s: K.wrapnoise(r, n, s)  # noqa: E731
    img = lambda v, cols: K.ramp_img(v, cols, n)  # noqa: E731
    out = {}
    # fair skin, a touch of colour
    v = 0.55 + (noise(5) - 0.5) * 0.3 + (noise(1.2) - 0.5) * 0.12
    out["kael_skin"] = img(v, [(176, 118, 90), (204, 144, 112), (226, 172, 138), (242, 196, 164)])
    # copper hair: combed strands, darker roots between
    v = 0.5 + np.sin(xx * 1.9 + noise(4) * 8) * 0.32 + (noise(1) - 0.5) * 0.3
    out["kael_hair"] = img(v, [(62, 22, 10), (98, 38, 16), (134, 56, 22), (168, 80, 32), (196, 108, 50)])
    # the beard and brows: the same copper, shorter and coarser, a shade darker
    v = 0.45 + (noise(0.7) - 0.5) * 0.7 + (noise(3) - 0.5) * 0.3
    out["kael_beard"] = img(v, [(54, 20, 10), (86, 34, 14), (120, 50, 20), (150, 72, 30), (176, 96, 44)])
    # the whites of the eyes, a little warm so they don't glow
    out["kael_eye"] = img(0.5 + (noise(2) - 0.5) * 0.3, [(176, 168, 152), (200, 192, 176), (216, 210, 196)])
    # the cuirass: oiled red-brown leather with tooled borders and stitching
    v = 0.5 + (noise(5) - 0.5) * 0.45 + (noise(0.8) - 0.5) * 0.3
    v[(yy == 2) | (yy == 3)] += 0.15
    v[(yy == 4)] -= 0.18
    v[(yy == 60) & (xx % 4 < 2)] = 0.9
    out["kael_leather"] = img(v, [(46, 22, 14), (74, 36, 20), (102, 52, 28), (128, 70, 38), (156, 94, 54)])
    # linen: undyed, a fine weave
    weave = ((xx % 2) ^ (yy % 2)) * 0.08
    v = 0.6 + weave + (noise(6) - 0.5) * 0.35 + ((yy % 7) == 0) * -0.1
    out["kael_linen"] = img(v, [(120, 108, 86), (152, 140, 114), (180, 168, 140), (204, 194, 166), (222, 214, 190)])
    # trousers: dark moss wool
    v = 0.5 + (noise(6) - 0.5) * 0.5 + ((yy % 3) == 0) * 0.08
    out["kael_trousers"] = img(v, [(30, 32, 24), (44, 48, 34), (60, 64, 46), (78, 82, 60)])
    for k, im in out.items():
        K.save_png(k, im)


def main():
    textures()
    K.clear()
    rig = K.Rig(K.HUMAN_BONES, "kael")
    build_kael(rig)
    rig.build()
    K.export(os.path.join(K.OUT, "kael_hd.glb"))
    print("kael_hd.glb: skinned, %d triangles" % rig.tris)
    K.clear()
    r = build_sword()
    K.export(os.path.join(K.OUT, "short_sword_hd.glb"))
    print("short_sword_hd.glb: %d triangles" % r.tris)


if __name__ == "__main__":
    main()
