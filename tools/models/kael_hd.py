"""Kael (the placeholder city-faction hero) at look B's detail, skinned on the people's rig, plus his short
sword. Run with Blender's Python module (pip install bpy), from the project root:

    python3 tools/models/kael_hd.py

Writes assets/models/hd/kael_hd.glb, short_sword_hd.glb and Kael's own textures (kael_*.png); shares the
Guard's iron / steel / boot / dark / brass / grip / leather tiles (made by guard_hd.py).

His outfit is Actor.DRESS["kael"] (Cody 2026-11-15: same as before, at the Guard's detail, for now; it will
likely become the fighter class's default outfit): a leather cuirass with tassets and shoulder guards over a
linen shirt, leather greaves over his boots, cloth trousers, a satchel on a strap, the short sword. Young,
clean-shaven, copper hair. Same rig and weights scheme as guard_hd.py (see rig_kit.py).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rig_kit as K  # noqa: E402
from rig_kit import box, ellipsoid, loft, ramp, rot, at  # noqa: E402
import numpy as np  # noqa: E402

K.TILE.update({"kael_skin": 0.2, "kael_hair": 0.1, "kael_leather": 0.26, "kael_linen": 0.2, "kael_trousers": 0.25})


def build_kael(rig):
    P = rig.piece
    trunk = ramp([(-0.25, {"hips": 0.55, "spine": 0.45}), (-0.17, {"spine": 1}), (-0.06, {"spine": 0.3, "chest": 0.7}),
                  (0.0, {"chest": 1}), (0.24, {"chest": 1}), (0.29, {"chest": 0.6, "neck": 0.4})])

    # torso: the linen shirt shows at the neck and arms; the leather cuirass over it, laced up the sides
    shirt = [(-0.22, 0.158, 0.104), (-0.1, 0.155, 0.1), (0.05, 0.165, 0.108, 0, -0.004), (0.17, 0.182, 0.11),
             (0.23, 0.166, 0.094), (0.265, 0.11, 0.074), (0.285, 0.055, 0.05)]
    P("shirt", "chest", "kael_linen", lambda m: loft(m, shirt, "kael_linen", e=2.3, cap1=True), trunk)
    cuir = [(-0.235, 0.168, 0.114), (-0.12, 0.164, 0.11), (0.0, 0.174, 0.119, 0, -0.006), (0.1, 0.184, 0.124, 0, -0.01),
            (0.19, 0.188, 0.116, 0, -0.005), (0.235, 0.16, 0.098)]
    P("cuirass", "chest", "kael_leather", lambda m: loft(m, cuir, "kael_leather", e=2.5), trunk)
    # a raised chest plate and the side lacing
    P("plate", "chest", "kael_leather", lambda m: loft(m, [(-0.05, 0.12, 0.02, 0, -0.118), (0.08, 0.14, 0.024, 0, -0.13), (0.17, 0.13, 0.02, 0, -0.118)],
                                                     "kael_leather", a0=-math.pi, a1=0.0, seg=10, e=2.6), trunk)
    for s in (1, -1):
        for k in range(4):
            y = -0.14 + k * 0.07
            P("lace_%d_%d" % (s, k), "chest", "dark", lambda m, s=s, y=y: box(m, (s * 0.172, y, 0.0), (0.012, 0.008, 0.05), "dark", xf=rot("Z", s * 8)), trunk)
    # the satchel's strap: over the right shoulder, across the chest and back to the left hip
    def strap(m, front):
        z0 = -1 if front else 1
        pts = [(0.15, 0.25, 0.0), (0.08, 0.17, z0 * 0.115), (-0.02, 0.05, z0 * 0.122), (-0.11, -0.08, z0 * 0.12), (-0.165, -0.2, z0 * 0.1)]
        for a, b in zip(pts, pts[1:]):
            d = (np.array(b) - np.array(a))
            n = np.array([-d[1], d[0], 0.0])
            n = n / np.linalg.norm(n) * 0.022
            z = 0.006 * z0
            q = [(a[0] - n[0], a[1] - n[1], a[2] + z), (a[0] + n[0], a[1] + n[1], a[2] + z), (b[0] + n[0], b[1] + n[1], b[2] + z), (b[0] - n[0], b[1] - n[1], b[2] + z)]
            if not front:
                q = q[::-1]
            m.face(q, [(0, 0), (0.2, 0), (0.2, 1), (0, 1)], smooth=False)
    P("strap_front", "chest", "leather", lambda m: strap(m, True), trunk)
    P("strap_back", "chest", "leather", lambda m: strap(m, False), trunk)

    # hips: belt and buckle, tassets in two halves (they ride the thighs), the satchel on the left hip
    P("waist", "hips", "kael_linen", lambda m: loft(m, [(-0.06, 0.162, 0.11), (0.0, 0.166, 0.112), (0.07, 0.164, 0.112)], "kael_linen", e=2.3),
      ramp([(0.03, {"hips": 1}), (0.08, {"hips": 0.6, "spine": 0.4})]))
    P("belt", "hips", "leather", lambda m: loft(m, [(-0.005, 0.176, 0.12), (0.045, 0.176, 0.12)], "leather", e=2.3))
    P("buckle", "hips", "brass", lambda m: box(m, (0.0, 0.02, -0.123), (0.044, 0.04, 0.01), "brass"))
    P("satchel", "hips", "kael_leather", lambda m: box(m, (-0.2, -0.07, 0.0), (0.06, 0.14, 0.17), "kael_leather", xf=rot("Z", 6), smooth=False))
    P("satchel_flap", "hips", "leather", lambda m: box(m, (-0.234, -0.035, 0.0), (0.012, 0.085, 0.175), "leather", xf=rot("Z", 6)))
    P("satchel_buckle", "hips", "brass", lambda m: box(m, (-0.242, -0.07, 0.0), (0.006, 0.02, 0.026), "brass"))
    for side, sn in ((1, "r"), (-1, "l")):
        thigh = "thigh_" + sn
        P("tasset_" + sn, thigh, "kael_leather", lambda m, s=side: loft(m, [(0.09, 0.092, 0.114, -s * 0.012), (0.0, 0.097, 0.119, -s * 0.01), (-0.12, 0.101, 0.121, -s * 0.004)],
                                                                         "kael_leather", a0=-math.pi * 1.1, a1=math.pi * 0.1, seg=12),
          ramp([(-0.1, {thigh: 1}), (0.0, {"hips": 0.4, thigh: 0.6}), (0.09, {"hips": 0.75, thigh: 0.25})]))

    # neck and head: young, clean-shaven, copper hair swept back, ears
    P("neck", "neck", "kael_skin", lambda m: loft(m, [(-0.04, 0.044, 0.042), (0.09, 0.042, 0.04)], "kael_skin"),
      ramp([(-0.03, {"chest": 0.5, "neck": 0.5}), (0.01, {"neck": 1}), (0.05, {"neck": 0.6, "head": 0.4}), (0.09, {"head": 1})]))
    P("collar", "chest", "kael_linen", lambda m: loft(m, [(0.25, 0.062, 0.058), (0.295, 0.052, 0.05)], "kael_linen"), trunk)
    P("head", "head", "kael_skin", lambda m: ellipsoid(m, (0, 0.094, -0.002), (0.068, 0.102, 0.086), "kael_skin", seg=18, rings=12))
    P("jaw", "head", "kael_skin", lambda m: ellipsoid(m, (0, 0.045, -0.03), (0.055, 0.04, 0.055), "kael_skin", seg=14, rings=8))
    P("nose", "head", "kael_skin", lambda m: box(m, (0, 0.082, -0.09), (0.02, 0.036, 0.022), "kael_skin", xf=rot("X", -10)))
    P("mouth", "head", "dark", lambda m: box(m, (0, 0.05, -0.083), (0.026, 0.005, 0.006), "dark"))
    for side in (1, -1):
        P("ear_%s" % side, "head", "kael_skin", lambda m, s=side: ellipsoid(m, (s * 0.068, 0.09, 0.005), (0.012, 0.024, 0.016), "kael_skin", seg=8, rings=5))
        P("eye_%s" % side, "head", "dark", lambda m, s=side: ellipsoid(m, (s * 0.026, 0.102, -0.08), (0.012, 0.008, 0.006), "dark", seg=8, rings=4))
        P("brow_%s" % side, "head", "kael_hair", lambda m, s=side: box(m, (s * 0.028, 0.117, -0.083), (0.03, 0.008, 0.01), "kael_hair", xf=rot("Z", s * -6)))
    # hair: a cap over the crown and back, a swept fringe, short at the sides
    P("hair", "head", "kael_hair", lambda m: ellipsoid(m, (0, 0.11, 0.006), (0.075, 0.1, 0.094), "kael_hair", seg=20, rings=14,
                                                       keep=lambda x, y, z: y > 0.135 or (z > -0.03 and y > 0.05) or (abs(x) > 0.062 and y > 0.09 and z > -0.05)))
    for side in (1, -1):
        P("sideburn_%s" % side, "head", "kael_hair", lambda m, s=side: box(m, (s * 0.066, 0.1, -0.012), (0.01, 0.04, 0.022), "kael_hair"))

    # arms: linen sleeves, leather shoulder guards, bracers, gloves
    for side, sn in ((1, "r"), (-1, "l")):
        arm, fore, hand = "arm_" + sn, "forearm_" + sn, "hand_" + sn
        P("sleeve_" + sn, arm, "kael_linen", lambda m, s=side: loft(m, [(0.03, 0.06, 0.058, s * 0.006), (-0.1, 0.056, 0.053, s * 0.008),
                                                                       (-0.22, 0.053, 0.05, s * 0.01), (-0.3, 0.055, 0.052, s * 0.012), (-0.33, 0.058, 0.055, s * 0.013)], "kael_linen"),
          ramp([(-0.33, {arm: 0.35, fore: 0.65}), (-0.27, {arm: 1}), (-0.06, {arm: 1}), (0.04, {"chest": 0.5, arm: 0.5})]))
        P("shoulder_" + sn, arm, "kael_leather", lambda m, s=side: loft(m, [(-0.08, 0.066, 0.072), (-0.02, 0.072, 0.078), (0.02, 0.06, 0.066), (0.045, 0.034, 0.04), (0.055, 0.006, 0.008)],
                                                                        "kael_leather", xf=at(s * 0.024, 0.0, 0.0) @ rot("Z", s * -30)))
        P("shoulder_rim_" + sn, arm, "leather", lambda m, s=side: loft(m, [(-0.088, 0.069, 0.075), (-0.072, 0.07, 0.076)], "leather",
                                                                      xf=at(s * 0.024, 0.0, 0.0) @ rot("Z", s * -30)))
        P("forearm_" + sn, fore, "kael_linen", lambda m: loft(m, [(0.03, 0.047, 0.045), (-0.06, 0.045, 0.043)], "kael_linen"),
          ramp([(-0.03, {fore: 1}), (0.03, {arm: 0.55, fore: 0.45})]))
        P("bracer_" + sn, fore, "kael_leather", lambda m: loft(m, [(-0.05, 0.048, 0.046), (-0.15, 0.044, 0.042), (-0.235, 0.042, 0.04), (-0.25, 0.046, 0.044)], "kael_leather"),
          ramp([(-0.25, {fore: 0.5, hand: 0.5}), (-0.2, {fore: 1})]))
        for k, y in enumerate((-0.09, -0.18)):
            P("bracer_strap_%s%d" % (sn, k), fore, "leather", lambda m, y=y: loft(m, [(y, 0.0465, 0.0445), (y + 0.012, 0.0465, 0.0445)], "leather"))
        P("cuff_" + sn, hand, "boot", lambda m: loft(m, [(0.02, 0.04, 0.043), (-0.03, 0.035, 0.043)], "boot"),
          ramp([(-0.02, {hand: 1}), (0.02, {fore: 0.5, hand: 0.5})]))
        if side > 0:
            P("palm_r", "hand_r", "boot", lambda m: loft(m, [(-0.01, 0.025, 0.042), (-0.055, 0.027, 0.046), (-0.074, 0.025, 0.042)], "boot", cap1=True, e=2.6))
            P("fingers_r", "hand_r", "kael_skin", lambda m: ellipsoid(m, (-0.006, -0.082, 0.0), (0.03, 0.028, 0.047), "kael_skin", seg=12, rings=8))
            P("thumb_r", "hand_r", "kael_skin", lambda m: loft(m, [(0, 0.012, 0.011), (0.043, 0.01, 0.009)], "kael_skin", seg=8, cap1=True,
                                                                xf=at(-0.02, -0.04, -0.04) @ rot("Z", 60) @ rot("X", -30)))
        else:
            P("palm_l", "hand_l", "boot", lambda m: loft(m, [(-0.01, 0.021, 0.04), (-0.068, 0.021, 0.042)], "boot", cap1=True, e=2.6))
            P("fingers_l", "hand_l", "kael_skin", lambda m: loft(m, [(-0.063, 0.018, 0.038), (-0.098, 0.015, 0.034), (-0.115, 0.009, 0.024)], "kael_skin", cap1=True, e=2.4,
                                                                  xf=at(0.004, 0, 0) @ rot("Z", -6)))
            P("thumb_l", "hand_l", "kael_skin", lambda m: loft(m, [(0, 0.011, 0.01), (0.043, 0.009, 0.008)], "kael_skin", seg=8, cap1=True,
                                                                xf=at(0.012, -0.03, -0.035) @ rot("Z", -150) @ rot("X", 20)))

    # legs: cloth trousers, boots, leather greaves strapped over them
    for side, sn in ((1, "r"), (-1, "l")):
        thigh, shin, foot = "thigh_" + sn, "shin_" + sn, "foot_" + sn
        P("trousers_" + sn, thigh, "kael_trousers", lambda m: loft(m, [(0.06, 0.08, 0.08), (-0.1, 0.074, 0.072), (-0.25, 0.061, 0.06), (-0.41, 0.052, 0.055)], "kael_trousers"),
          ramp([(-0.415, {thigh: 0.45, shin: 0.55}), (-0.36, {thigh: 1}), (-0.04, {thigh: 1}), (0.06, {"hips": 0.6, thigh: 0.4})]))
        P("boot_" + sn, shin, "boot", lambda m: loft(m, [(-0.01, 0.056, 0.06), (-0.06, 0.053, 0.057), (-0.18, 0.049, 0.054, 0, 0.004), (-0.33, 0.042, 0.046), (-0.42, 0.045, 0.049)], "boot"),
          ramp([(-0.42, {shin: 0.4, foot: 0.6}), (-0.38, {shin: 1}), (-0.06, {shin: 1}), (0.0, {thigh: 0.3, shin: 0.7})]))
        P("boot_cuff_" + sn, shin, "boot", lambda m: loft(m, [(-0.04, 0.062, 0.066), (0.005, 0.066, 0.07)], "boot"),
          ramp([(-0.04, {shin: 1}), (0.005, {thigh: 0.35, shin: 0.65})]))
        P("greave_" + sn, shin, "kael_leather", lambda m: loft(m, [(-0.06, 0.062, 0.066), (-0.2, 0.058, 0.062, 0, 0.003), (-0.33, 0.051, 0.055)], "kael_leather",
                                                              a0=-math.pi * 0.95, a1=-math.pi * 0.05, seg=10))
        for k, y in enumerate((-0.1, -0.27)):
            P("greave_strap_%s%d" % (sn, k), shin, "leather", lambda m, y=y: loft(m, [(y, 0.0585, 0.0625), (y + 0.014, 0.0585, 0.0625)], "leather"))
        P("knee_" + sn, shin, "kael_leather", lambda m: loft(m, [(0.0, 0.052, 0.054), (0.026, 0.045, 0.047), (0.048, 0.026, 0.028), (0.058, 0.004, 0.004)], "kael_leather",
                                                            xf=at(0, 0.0, -0.03) @ rot("X", -90)))
        P("foot_" + sn, foot, "boot", lambda m: loft(m, [(0.046, 0.029, 0.034, 0, 0.04), (0.02, 0.042, 0.05, 0, 0.03), (-0.04, 0.045, 0.043, 0, 0.045),
                                                        (-0.11, 0.043, 0.032, 0, 0.055), (-0.152, 0.034, 0.022, 0, 0.06), (-0.168, 0.011, 0.009, 0, 0.065)],
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
    v = 0.55 + (noise(5) - 0.5) * 0.3
    out["kael_skin"] = img(v, [(190, 132, 102), (214, 156, 122), (232, 180, 146), (244, 202, 170)])
    # copper hair, combed strands
    v = 0.5 + np.sin(xx * 1.9 + noise(4) * 8) * 0.3 + (noise(1) - 0.5) * 0.3
    out["kael_hair"] = img(v, [(70, 26, 12), (104, 40, 18), (138, 58, 24), (170, 82, 34), (196, 108, 50)])
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
