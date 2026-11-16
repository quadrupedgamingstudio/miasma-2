"""The Hollow Wolf at look B's detail: a skinned quadruped rig, the model and its animations, all made in
Blender. Run with Blender's Python module (pip install bpy), from the project root:

    python3 tools/models/hollow_wolf_hd.py

Writes assets/models/hd/hollow_wolf_hd.glb (mesh, rig and animations) and its textures (wolf_*.png).

Cody's picks (2026-11-15): more miasma-touched than Miasma's wolf: patchy ash-grey fur, exposed ribs, a faint
glow in the eyes and mouth; the animations re-made in Blender rather than converted.

- Rig: WOLF_BONES below (bones point up, no roll: see rig_kit.py). The body is one skinned mesh per material;
  the trunk bends through hips / spine / chest, the neck into the head, the tail along three bones.
- Animations (the names the battle and field use): idle, walk, run, alert, windup, strike, stagger, recover,
  death. Keyed in ANIMS below as poses over time, the same way scripts/actor.gd keys the party's battle moves.
- Materials: wolf_hide (patchy fur), wolf_hollow (the dark flesh behind the ribs), wolf_bone (ribs, teeth,
  claws), wolf_glow (eyes, mouth: self-lit), wolf_fur (alpha tufts), dark (nose, lips).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rig_kit as K  # noqa: E402
from rig_kit import ellipsoid, loft, ramp, rot, at, tube, along  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

K.TILE.update({"wolf_hide": 0.22, "wolf_hollow": 0.15, "wolf_bone": 0.12, "wolf_glow": 0.1, "wolf_fur": 1.0})

WOLF_BONES = [
    ("root", None, (0, 0, 0)),
    ("hips", "root", (0, 0.64, 0.32)),
    ("spine", "hips", (0, 0.02, -0.30)),
    ("chest", "spine", (0, 0.02, -0.28)),
    ("neck", "chest", (0, 0.05, -0.16)),
    ("head", "neck", (0, 0.11, -0.14)),
    ("jaw", "head", (0, -0.035, -0.04)),
    ("ear_r", "head", (0.05, 0.07, 0.02)),
    ("ear_l", "head", (-0.05, 0.07, 0.02)),
    ("fleg_r", "chest", (0.11, -0.08, -0.06)),
    ("fore_r", "fleg_r", (0.01, -0.25, 0.06)),
    ("fpaw_r", "fore_r", (0.0, -0.25, -0.01)),
    ("fleg_l", "chest", (-0.11, -0.08, -0.06)),
    ("fore_l", "fleg_l", (-0.01, -0.25, 0.06)),
    ("fpaw_l", "fore_l", (0.0, -0.25, -0.01)),
    ("thigh_r", "hips", (0.11, -0.04, 0.06)),
    ("shin_r", "thigh_r", (0.02, -0.23, -0.11)),
    ("hock_r", "shin_r", (0.0, -0.21, 0.15)),
    ("rpaw_r", "hock_r", (0.0, -0.12, -0.04)),
    ("thigh_l", "hips", (-0.11, -0.04, 0.06)),
    ("shin_l", "thigh_l", (-0.02, -0.23, -0.11)),
    ("hock_l", "shin_l", (0.0, -0.21, 0.15)),
    ("rpaw_l", "hock_l", (0.0, -0.12, -0.04)),
    ("tail1", "hips", (0, 0.03, 0.25)),
    ("tail2", "tail1", (0, -0.07, 0.18)),
    ("tail3", "tail2", (0, -0.09, 0.15)),
]
POS = K.world_positions(WOLF_BONES)

# the trunk: sections along the body (y = metres forward of the spine bone, rx, rz (up), cx, cz)
BODY = [(-0.56, 0.05, 0.055, 0, 0.03), (-0.48, 0.095, 0.11, 0, 0.0), (-0.36, 0.122, 0.14, 0, -0.01), (-0.2, 0.112, 0.125, 0, 0.0),
        (-0.06, 0.104, 0.112, 0, 0.018), (0.08, 0.124, 0.162, 0, -0.034), (0.22, 0.142, 0.195, 0, -0.06), (0.34, 0.14, 0.19, 0, -0.045),
        (0.44, 0.115, 0.15, 0, 0.0)]
BODY_XF = at(0, 0.66, 0.02) @ rot("X", -90)   # loft +Y = forward (-Z), loft +Z = up


def sec_at(y):
    for a, b in zip(BODY, BODY[1:]):
        if a[0] <= y <= b[0]:
            t = (y - a[0]) / (b[0] - a[0])
            return [a[i] * (1 - t) + b[i] * t for i in range(5)]
    return list(BODY[-1])


def body_point(y, ang, scale=1.0):
    """A point on the trunk's surface (world, Godot frame) at a station and angle (0 = right, pi/2 = up)."""
    _, rx, rz, cx, cz = sec_at(y)
    x, z = K.superellipse(ang, rx * scale, rz * scale, 2.0)
    return BODY_XF @ Vector((cx + x, y, cz + z))


# the exposed ribs: the left flank has a big hole, the right a small one (station range, angle range)
HOLES = [((0.08, 0.34), (math.pi * 0.74, math.pi * 1.16)), ((0.08, 0.22), (-math.pi * 0.08, math.pi * 0.12))]


def in_hole(y, a):
    a = a % (2 * math.pi)
    for (y0, y1), (a0, a1) in HOLES:
        if y0 <= y <= y1:
            if a0 <= a <= a1 or a0 <= a - 2 * math.pi <= a1:
                return True
    return False


def build_wolf(rig):
    def P(name, bone, mat, fn, wfn=None):
        """fn(m, X) draws in world coordinates through X; wfn(world point) -> weights."""
        off = rig.pos[bone]
        X = at(*(-off))
        rig.piece(name, bone, mat, lambda m: fn(m, X), (lambda p: wfn(p + off)) if wfn else None)

    trunk_w = ramp([(-0.4, {"chest": 0.6, "neck": 0.4}), (-0.26, {"chest": 1}), (-0.12, {"spine": 0.5, "chest": 0.5}), (0.02, {"spine": 1}),
                    (0.2, {"hips": 0.5, "spine": 0.5}), (0.38, {"hips": 1}), (0.58, {"hips": 0.6, "tail1": 0.4})], axis=2)

    # --- the trunk, with holes where the ribs show
    ys = [s[0] for s in BODY]

    def trunk(m, X):
        loft(m, BODY, "wolf_hide", xf=X @ BODY_XF, seg=24, cap0=True,
             keep=lambda k, a: not in_hole((ys[k] + ys[k + 1]) / 2, a))
    P("trunk", "spine", "wolf_hide", trunk, trunk_w)

    # behind each hole: sunken dark flesh, and the ribs bridging it
    for i, ((y0, y1), (a0, a1)) in enumerate(HOLES):
        secs = [[y] + sec_at(y)[1:] for y in np.linspace(y0 - 0.01, y1 + 0.01, 5)]
        secs = [(s[0], s[1] * 0.82, s[2] * 0.86, s[3], s[4]) for s in secs]
        P("hollow_%d" % i, "chest", "wolf_hollow", lambda m, X, secs=secs, a0=a0, a1=a1: loft(m, secs, "wolf_hollow", xf=X @ BODY_XF, a0=a0 - 0.08, a1=a1 + 0.08, seg=8), trunk_w)
        n = 5 if i == 0 else 2
        for j in range(n):
            y = y0 + (y1 - y0) * (j + 0.5) / n
            pts = [body_point(y + 0.012 * math.sin(t * math.pi), a0 - 0.05 + (a1 - a0 + 0.1) * t, 0.975) for t in np.linspace(0, 1, 7)]
            P("rib_%d_%d" % (i, j), "chest", "wolf_bone", lambda m, X, pts=pts: tube(m, [X @ p for p in pts], [0.005, 0.0075, 0.0085, 0.0085, 0.0085, 0.0075, 0.005], "wolf_bone", seg=6), trunk_w)
    # a ridge of bony spine along the back, where the fur has gone
    knobs = [body_point(y, math.pi / 2, 1.0) for y in np.linspace(-0.2, 0.3, 7)]
    for j, p in enumerate(knobs):
        P("vertebra_%d" % j, "spine", "wolf_bone", lambda m, X, p=p: ellipsoid(m, tuple(X @ p), (0.016, 0.014, 0.022), "wolf_bone", seg=8, rings=5), trunk_w)

    # --- neck and head
    neck_w = ramp([(-0.36, {"chest": 0.6, "neck": 0.4}), (-0.46, {"neck": 1}), (-0.53, {"neck": 0.5, "head": 0.5}), (-0.6, {"head": 1})], axis=2)
    nx, nl = along((0, 0.69, -0.33), (0, 0.85, -0.6))
    P("neck", "neck", "wolf_hide", lambda m, X: loft(m, [(-0.02, 0.115, 0.15), (0.1, 0.1, 0.125), (0.2, 0.08, 0.095), (nl, 0.07, 0.08)], "wolf_hide",
                                                    xf=X @ nx, seg=18), neck_w)
    h = POS["head"]
    hp = lambda x, y, z: (h.x + x, h.y + y, h.z + z)  # noqa: E731
    P("skull", "head", "wolf_hide", lambda m, X: ellipsoid(m, hp(0, 0.025, -0.01), (0.082, 0.072, 0.098), "wolf_hide", seg=16, rings=10, xf=X))
    P("brows", "head", "wolf_hide", lambda m, X: ellipsoid(m, hp(0, 0.04, -0.07), (0.07, 0.03, 0.045), "wolf_hide", seg=12, rings=6, xf=X))
    P("muzzle", "head", "wolf_hide", lambda m, X: ellipsoid(m, hp(0, -0.012, -0.15), (0.048, 0.038, 0.12), "wolf_hide", seg=14, rings=8, xf=X,
                                                           keep=lambda x, y, z: y > h.y - 0.03))
    P("nose", "head", "dark", lambda m, X: ellipsoid(m, hp(0, -0.008, -0.262), (0.022, 0.018, 0.016), "dark", seg=10, rings=6, xf=X))
    P("lip_upper", "head", "dark", lambda m, X: loft(m, [(-0.24, 0.032, 0.008), (-0.12, 0.046, 0.009), (-0.04, 0.05, 0.008)], "dark",
                                                    xf=X @ at(h.x, h.y - 0.036, h.z) @ rot("X", 90), seg=12, a0=0, a1=math.pi))
    P("palate", "head", "wolf_glow", lambda m, X: ellipsoid(m, hp(0, -0.04, -0.13), (0.032, 0.006, 0.1), "wolf_glow", seg=10, rings=4, xf=X))
    for s in (1, -1):
        P("socket_%d" % s, "head", "dark", lambda m, X, s=s: ellipsoid(m, hp(s * 0.043, 0.032, -0.072), (0.02, 0.014, 0.014), "dark", seg=10, rings=5, xf=X))
        P("eye_%d" % s, "head", "wolf_glow", lambda m, X, s=s: ellipsoid(m, hp(s * 0.047, 0.032, -0.08), (0.016, 0.01, 0.009), "wolf_glow", seg=10, rings=5, xf=X))
        P("cheek_%d" % s, "head", "wolf_hide", lambda m, X, s=s: ellipsoid(m, hp(s * 0.05, -0.012, -0.04), (0.04, 0.045, 0.06), "wolf_hide", seg=12, rings=6, xf=X))
        # upper fangs and a row of teeth
        P("fang_u_%d" % s, "head", "wolf_bone", lambda m, X, s=s: tube(m, [X @ Vector(hp(s * 0.028, -0.032, -0.215)), X @ Vector(hp(s * 0.027, -0.066, -0.212))],
                                                                       [0.008, 0.0], "wolf_bone", seg=6, cap=False))
        for k in range(4):
            z = -0.19 + k * 0.035
            P("tooth_u_%d_%d" % (s, k), "head", "wolf_bone", lambda m, X, s=s, z=z: tube(m, [X @ Vector(hp(s * 0.036, -0.034, z)), X @ Vector(hp(s * 0.036, -0.05, z))],
                                                                                       [0.006, 0.0], "wolf_bone", seg=5, cap=False))
    # the lower jaw, its fangs, and the glow in the throat that shows when it opens
    j = POS["jaw"]
    jp = lambda x, y, z: (j.x + x, j.y + y, j.z + z)  # noqa: E731
    P("jaw", "jaw", "wolf_hide", lambda m, X: ellipsoid(m, jp(0, -0.012, -0.09), (0.042, 0.024, 0.115), "wolf_hide", seg=12, rings=8, xf=X,
                                                       keep=lambda x, y, z: y < j.y - 0.004))
    P("lip_lower", "jaw", "dark", lambda m, X: loft(m, [(-0.2, 0.028, 0.007), (-0.1, 0.04, 0.008), (0.0, 0.044, 0.007)], "dark",
                                                   xf=X @ at(j.x, j.y - 0.004, j.z) @ rot("X", 90), seg=12, a0=math.pi, a1=2 * math.pi))
    P("tongue", "jaw", "wolf_glow", lambda m, X: ellipsoid(m, jp(0, -0.002, -0.085), (0.028, 0.008, 0.095), "wolf_glow", seg=10, rings=4, xf=X))
    for s in (1, -1):
        P("fang_l_%d" % s, "jaw", "wolf_bone", lambda m, X, s=s: tube(m, [X @ Vector(jp(s * 0.024, -0.004, -0.17)), X @ Vector(jp(s * 0.024, 0.028, -0.165))],
                                                                      [0.007, 0.0], "wolf_bone", seg=6, cap=False))
        for k in range(3):
            z = -0.14 + k * 0.035
            P("tooth_l_%d_%d" % (s, k), "jaw", "wolf_bone", lambda m, X, s=s, z=z: tube(m, [X @ Vector(jp(s * 0.03, -0.004, z)), X @ Vector(jp(s * 0.03, 0.012, z))],
                                                                                       [0.005, 0.0], "wolf_bone", seg=5, cap=False))
    # ears: pointed, the left one torn short
    for s, sn in ((1, "r"), (-1, "l")):
        e = POS["ear_" + sn]
        tip = (e.x + s * 0.02, e.y + (0.1 if s > 0 else 0.065), e.z + 0.03)
        ex, el = along(tuple(e), tip)
        P("ear_" + sn, "ear_" + sn, "wolf_hide", lambda m, X, ex=ex, el=el: loft(m, [(0.0, 0.03, 0.013), (el * 0.55, 0.02, 0.009), (el, 0.002, 0.002)],
                                                                             "wolf_hide", xf=X @ ex, seg=8, cap0=True))

    # --- legs
    def limb(name, b0, b1, mat, secs, wfn, end=None):
        p0, p1 = POS[b0], end if end is not None else POS[b1]
        lx, ll = along(tuple(p0), tuple(p1))
        sc = [(s[0] * ll, s[1], s[2]) for s in secs]
        P(name, b0, mat, lambda m, X: loft(m, sc, mat, xf=X @ lx, seg=12), wfn)

    for s, sn in ((1, "r"), (-1, "l")):
        fl, fo, fp = "fleg_" + sn, "fore_" + sn, "fpaw_" + sn
        th, sh, hk, rp = "thigh_" + sn, "shin_" + sn, "hock_" + sn, "rpaw_" + sn
        y = lambda b: POS[b].y  # noqa: E731
        # front: a muscled shoulder, a lean forearm, a paw with claws
        limb("upperarm_" + sn, fl, fo, "wolf_hide", [(-0.2, 0.062, 0.08), (0.25, 0.058, 0.07), (0.7, 0.04, 0.045), (1.05, 0.031, 0.035)],
             ramp([(y(fl) + 0.05, {"chest": 0.5, fl: 0.5}), (y(fl) - 0.04, {fl: 1}), (y(fo) + 0.05, {fl: 1}), (y(fo) - 0.01, {fl: 0.5, fo: 0.5})]))
        limb("forearm_" + sn, fo, fp, "wolf_hide", [(-0.08, 0.032, 0.036), (0.5, 0.025, 0.028), (1.04, 0.022, 0.024)],
             ramp([(y(fo) + 0.03, {fl: 0.5, fo: 0.5}), (y(fo) - 0.03, {fo: 1}), (y(fp) + 0.04, {fo: 1}), (y(fp) - 0.005, {fo: 0.5, fp: 0.5})]))
        pp = POS[fp]
        P("fpaw_" + sn, fp, "wolf_hide", lambda m, X, pp=pp: ellipsoid(m, (pp.x, pp.y - 0.06, pp.z - 0.03), (0.032, 0.034, 0.05), "wolf_hide", seg=12, rings=7, xf=X))
        for k in range(4):
            dx = (k - 1.5) * 0.017
            P("fclaw_%s%d" % (sn, k), fp, "wolf_bone", lambda m, X, pp=pp, dx=dx: tube(m, [X @ Vector((pp.x + dx, pp.y - 0.075, pp.z - 0.07)),
                                                                                           X @ Vector((pp.x + dx * 1.1, pp.y - 0.098, pp.z - 0.094))], [0.006, 0.0], "wolf_bone", seg=5, cap=False))
        # hind: a heavy thigh, the shin, the hock down to a paw
        limb("thigh_" + sn, th, sh, "wolf_hide", [(-0.25, 0.075, 0.095), (0.3, 0.068, 0.088), (0.72, 0.046, 0.056), (1.04, 0.035, 0.04)],
             ramp([(y(th) + 0.06, {"hips": 0.6, th: 0.4}), (y(th) - 0.04, {th: 1}), (y(sh) + 0.05, {th: 1}), (y(sh) - 0.01, {th: 0.5, sh: 0.5})]))
        limb("shin_" + sn, sh, hk, "wolf_hide", [(-0.08, 0.035, 0.04), (0.5, 0.027, 0.03), (1.04, 0.022, 0.024)],
             ramp([(y(sh) + 0.03, {th: 0.5, sh: 0.5}), (y(sh) - 0.03, {sh: 1}), (y(hk) + 0.03, {sh: 1}), (y(hk) - 0.01, {sh: 0.5, hk: 0.5})]))
        limb("hock_" + sn, hk, rp, "wolf_hide", [(-0.1, 0.023, 0.027), (0.6, 0.02, 0.022), (1.05, 0.02, 0.022)],
             ramp([(y(hk) + 0.02, {sh: 0.5, hk: 0.5}), (y(hk) - 0.03, {hk: 1}), (y(rp) + 0.03, {hk: 1}), (y(rp) - 0.005, {hk: 0.5, rp: 0.5})]))
        rpp = POS[rp]
        P("rpaw_" + sn, rp, "wolf_hide", lambda m, X, pp=rpp: ellipsoid(m, (pp.x, pp.y - 0.004, pp.z - 0.035), (0.03, 0.03, 0.05), "wolf_hide", seg=12, rings=7, xf=X))
        for k in range(4):
            dx = (k - 1.5) * 0.016
            P("rclaw_%s%d" % (sn, k), rp, "wolf_bone", lambda m, X, pp=rpp, dx=dx: tube(m, [X @ Vector((pp.x + dx, pp.y - 0.018, pp.z - 0.075)),
                                                                                            X @ Vector((pp.x + dx * 1.1, pp.y - 0.038, pp.z - 0.098))], [0.006, 0.0], "wolf_bone", seg=5, cap=False))

    # --- the tail: thin and ragged
    tail_pts = [(0, 0.672, 0.55), (0, 0.65, 0.66), POS["tail2"], (0, 0.55, 0.83), POS["tail3"], (0, 0.46, 1.0)]
    tail_w = ramp([(0.57, {"hips": 0.5, "tail1": 0.5}), (0.62, {"tail1": 1}), (0.7, {"tail1": 0.5, "tail2": 0.5}), (0.78, {"tail2": 1}),
                   (0.86, {"tail2": 0.5, "tail3": 0.5}), (0.92, {"tail3": 1})], axis=2)
    P("tail", "tail1", "wolf_hide", lambda m, X: tube(m, [X @ Vector(p) for p in tail_pts], [0.045, 0.042, 0.036, 0.03, 0.022, 0.004], "wolf_hide", seg=10), tail_w)

    # --- fur tufts (alpha cards): a ragged mane down the neck and back, ruff, haunches, tail
    rng = np.random.default_rng(3)
    cards = []
    for k in range(26):   # the mane: from the head down the back, leaning back
        t = k / 25.0
        if t < 0.35:
            base = nx @ Vector((0, nl * (1 - t / 0.35), 0.075 + 0.04 * (t / 0.35)))
        else:
            base = body_point(0.44 - (t - 0.35) / 0.65 * 0.62, math.pi / 2, 0.96)
        if 0.18 < (0.44 - (t - 0.35) / 0.65 * 0.62) < 0.32 and t >= 0.35:
            continue   # bald over the worst of the ribs
        cards.append((base, Vector((rng.uniform(-0.04, 0.04), 0.03 + rng.uniform(0, 0.03), 0.09 + rng.uniform(0, 0.03))), 0.08 + rng.uniform(0, 0.03)))
    for k in range(14):   # the neck ruff, round the throat and sides, hanging down and back
        a = math.pi * (0.85 + 1.3 * k / 13.0)   # left side, under the throat, right side (local +Z is up)
        p = nx @ Vector((math.cos(a) * 0.105, 0.04 + rng.uniform(0, 0.06), math.sin(a) * 0.13))
        out = (p - nx @ Vector((0, p.y, 0))).normalized()
        cards.append((p, Vector((out.x * 0.05, -0.08 - rng.uniform(0, 0.04), 0.05)), 0.08 + rng.uniform(0, 0.03)))
    for s in (1, -1):   # tufts on the haunches and shoulders
        for k in range(4):
            p = body_point(-0.42 + k * 0.05, math.pi * (0.5 - s * 0.3), 1.0)
            cards.append((p, Vector((s * 0.04, -0.07, 0.05)), 0.045))
            p = body_point(0.36 + k * 0.02, math.pi * (0.5 - s * 0.35), 1.0)
            cards.append((p, Vector((s * 0.04, -0.07, 0.04)), 0.045))
    for k in range(6):   # tail tufts
        t = 0.2 + k * 0.14
        i = min(int(t * (len(tail_pts) - 1)), len(tail_pts) - 2)
        f = t * (len(tail_pts) - 1) - i
        p = Vector(tail_pts[i]).lerp(Vector(tail_pts[i + 1]), f)
        cards.append((p + Vector((0, 0.02, 0)), Vector((rng.uniform(-0.04, 0.04), -0.03, 0.09)), 0.05))

    def fur(m, X):
        # each tuft is two crossed cards, so it has body from every side
        for base, d, wid in cards:
            sa = Vector((wid * 0.5, 0, 0))
            sb = d.cross(Vector((1, 0, 0))).normalized() * wid * 0.5
            u0 = rng.integers(0, 2) * 0.5
            for side in (sa, sb):
                p0, p1, p2, p3 = base - side, base + side, base + side + d, base - side + d
                K.card(m, [X @ p0, X @ p1, X @ p2, X @ p3], "wolf_fur", uv=((u0, 1), (u0 + 0.5, 1), (u0 + 0.5, 0), (u0, 0)))
    allw = lambda p: (tail_w(p) if p.z > 0.56 else (neck_w(p) if p.z < -0.38 else trunk_w(p)))  # noqa: E731
    P("fur", "spine", "wolf_fur", fur, allw)


# --- animations ----------------------------------------------------------------------------------------
# Angles in degrees on Godot's axes: +X swings a leg forward (and raises the head / lifts the tail's tip
# down), +Y turns left, +Z rolls. "bone@" = an offset in metres.

BASE = {"neck": (-8, 0, 0), "head": (6, 0, 0), "tail1": (8, 0, 0), "tail2": (6, 0, 0), "tail3": (4, 0, 0), "jaw": (4, 0, 0)}


def pose(**kw):
    d = dict(BASE)
    for k, v in kw.items():
        d[k.replace("__", "@")] = v
    return d


def gait(period, phases, swing_frac, amp_f, amp_h, bob, spine_flex, samples=12, lift=1.0):
    """Leg swing for walk/run. phases: leg -> phase (0..1). Stance = the leg sweeps back on the ground;
    swing = it folds and comes forward."""
    keys = []
    for i in range(samples + 1):
        t = period * i / samples
        p = dict(BASE)
        for leg, ph in phases.items():
            u = (i / samples + ph) % 1.0
            st = 1.0 - swing_frac
            if u < st:     # stance: forward -> back
                k = u / st
                sw = math.cos(k * math.pi)       # +1 -> -1
                fold = 0.0
            else:          # swing: back -> forward, folded
                k = (u - st) / swing_frac
                sw = -math.cos(k * math.pi)      # -1 -> +1
                fold = math.sin(k * math.pi) * lift
            sn = leg[-1]
            if leg.startswith("f"):
                p["fleg_" + sn] = (amp_f * sw, 0, 0)
                p["fore_" + sn] = (-28 * fold + 4 * sw, 0, 0)
                p["fpaw_" + sn] = (-70 * fold, 0, 0)
            else:
                p["thigh_" + sn] = (amp_h * sw - 6, 0, 0)
                p["shin_" + sn] = (-30 * fold + 6, 0, 0)
                p["hock_" + sn] = (40 * fold - 4, 0, 0)
                p["rpaw_" + sn] = (-30 * fold + 6, 0, 0)
        ph2 = (i / samples) * 2 * math.pi
        p["root@"] = (0, bob * math.cos(ph2 * 2), 0)
        p["spine"] = (spine_flex * math.sin(ph2), 0, 0)
        p["chest"] = (-spine_flex * 0.6 * math.sin(ph2), 0, 0)
        p["neck"] = (BASE["neck"][0] + 3 * math.cos(ph2 * 2), 0, 0)
        p["tail1"] = (BASE["tail1"][0], 8 * math.sin(ph2), 0)
        p["tail2"] = (BASE["tail2"][0], 10 * math.sin(ph2 - 0.6), 0)
        keys.append((t, p))
    return keys


def anims():
    A = {}
    # idle: breathing, a slow head turn, the tail swaying, an ear flick, jaw a little open
    A["idle"] = [(0.0, pose()),
                 (0.6, pose(spine=(1.5, 0, 0), chest=(-1, 0, 0), neck=(-6, 5, 0), head=(5, 4, 0), tail2=(6, 8, 0), tail3=(4, 10, 0), jaw=(7, 0, 0))),
                 (1.2, pose(neck=(-9, 0, 0), head=(7, -2, 0), tail2=(6, -6, 0), tail3=(4, -9, 0), ear_l=(0, 0, -25))),
                 (1.35, pose(neck=(-9, -1, 0), head=(7, -3, 0), ear_l=(0, 0, 0))),
                 (1.8, pose(spine=(1.5, 0, 0), chest=(-1, 0, 0), neck=(-7, -6, 0), head=(5, -4, 0), tail2=(6, 6, 0), tail3=(4, 8, 0), jaw=(8, 0, 0))),
                 (2.4, pose())]
    A["walk"] = gait(0.6, {"fr": 0.0, "hl": 0.25, "fl": 0.5, "hr": 0.75}, 0.4, 22, 20, 0.012, 2.0)
    A["run"] = gait(0.42, {"hr": 0.0, "hl": 0.08, "fr": 0.48, "fl": 0.58}, 0.45, 38, 34, 0.035, 9.0, lift=1.1)
    # alert: the head drops, the lips peel back, the hackles and tail go up, a growl's tremble
    snarl = pose(neck=(-24, 0, 0), head=(14, 0, 0), jaw=(20, 0, 0), tail1=(-18, 0, 0), tail2=(-4, 0, 0), tail3=(0, 0, 0),
                 fleg_r=(6, 0, 6), fleg_l=(6, 0, -6), thigh_r=(-12, 0, 0), thigh_l=(-12, 0, 0), shin_r=(14, 0, 0), shin_l=(14, 0, 0),
                 root__=(0, -0.03, 0), ear_r=(-20, 0, 0), ear_l=(-20, 0, 0))
    shake = dict(snarl, head=(16, 3, 0), jaw=(26, 0, 0))
    A["alert"] = [(0.0, pose()), (0.35, snarl), (0.5, shake), (0.65, snarl), (0.8, shake), (1.0, snarl), (1.4, pose(jaw=(8, 0, 0)))]
    # windup: gathers back on its haunches, head low and aimed, jaw opening
    crouch = pose(root__=(0, -0.05, 0.08), hips__=(0, -0.04, 0), spine=(-4, 0, 0), neck=(-20, 0, 0), head=(18, 0, 0), jaw=(24, 0, 0),
                  fleg_r=(-14, 0, 0), fleg_l=(-10, 0, 0), fore_r=(-12, 0, 0), fore_l=(-12, 0, 0), fpaw_r=(10, 0, 0), fpaw_l=(10, 0, 0),
                  thigh_r=(22, 0, 0), thigh_l=(22, 0, 0), shin_r=(-26, 0, 0), shin_l=(-26, 0, 0), hock_r=(22, 0, 0), hock_l=(22, 0, 0),
                  tail1=(18, 0, 0), ear_r=(-25, 0, 0), ear_l=(-25, 0, 0))
    A["windup"] = [(0.0, pose()), (0.3, crouch), (0.45, dict(crouch, jaw=(30, 0, 0)))]
    # strike: springs, forelegs reaching, jaw wide, then snaps shut
    reach = pose(root__=(0, 0.06, -0.12), spine=(6, 0, 0), chest=(4, 0, 0), neck=(-2, 0, 0), head=(-4, 0, 0), jaw=(38, 0, 0),
                 fleg_r=(42, 0, 0), fleg_l=(36, 0, 0), fore_r=(16, 0, 0), fore_l=(14, 0, 0), fpaw_r=(-20, 0, 0), fpaw_l=(-20, 0, 0),
                 thigh_r=(-34, 0, 0), thigh_l=(-30, 0, 0), shin_r=(14, 0, 0), shin_l=(12, 0, 0), hock_r=(-20, 0, 0), hock_l=(-20, 0, 0),
                 tail1=(-6, 0, 0), ear_r=(-30, 0, 0), ear_l=(-30, 0, 0))
    bite = dict(reach, jaw=(0, 0, 0), head=(-10, 0, 0), root__=(0, 0.02, -0.08))
    A["strike"] = [(0.0, crouch), (0.1, reach), (0.17, bite), (0.3, pose(jaw=(6, 0, 0)))]
    # stagger: thrown back, head whipped up and aside
    hit = pose(root__=(0, 0.02, 0.12), spine=(10, 0, 4), chest=(6, 0, 0), neck=(18, 14, 0), head=(-12, 10, 6), jaw=(18, 0, 0),
               fleg_r=(22, 0, 0), fleg_l=(16, 0, 0), fore_r=(-20, 0, 0), thigh_r=(8, 0, 0), thigh_l=(-6, 0, 0), tail1=(30, 0, 0), ear_r=(-35, 0, 0), ear_l=(-35, 0, 0))
    A["stagger"] = [(0.0, pose()), (0.08, hit), (0.3, dict(hit, neck=(6, 6, 0), head=(-2, 4, 0))), (0.55, pose(jaw=(10, 0, 0)))]
    # recover: shakes it off and settles
    A["recover"] = [(0.0, pose()), (0.12, pose(neck=(-12, 12, 0), head=(4, 14, 10))), (0.25, pose(neck=(-12, -12, 0), head=(4, -14, -10))),
                    (0.36, pose(neck=(-10, 6, 0), head=(5, 6, 4))), (0.5, pose())]
    # death: the forelegs buckle, it rolls onto its left side, the legs go slack, a last twitch
    buckle = pose(root__=(0, -0.06, 0), spine=(-8, 0, 0), neck=(-30, 0, 0), head=(10, 0, 0), jaw=(20, 0, 0),
                  fleg_r=(-24, 0, 0), fleg_l=(-24, 0, 0), fore_r=(40, 0, 0), fore_l=(40, 0, 0), fpaw_r=(-40, 0, 0), fpaw_l=(-40, 0, 0),
                  tail1=(30, 0, 0))
    fallen = pose(root=(0, 0, 84), root__=(0.0, 0.02, 0), spine=(-6, 0, -6), neck=(-14, 0, -10), head=(0, 0, -8), jaw=(26, 0, 0),
                  fleg_r=(26, 0, -8), fore_r=(-18, 0, 0), fleg_l=(14, 0, 0), fore_l=(-10, 0, 0), thigh_r=(24, 0, -10), shin_r=(-18, 0, 0),
                  thigh_l=(10, 0, 0), tail1=(10, -14, 0), tail2=(4, -10, 0), ear_r=(-30, 0, 0), ear_l=(-30, 0, 0))
    A["death"] = [(0.0, pose()), (0.3, buckle), (0.75, dict(fallen, root=(0, 0, 90))), (0.9, fallen), (1.05, dict(fallen, thigh_r=(30, 0, -10), jaw=(30, 0, 0))),
                  (1.3, dict(fallen, jaw=(22, 0, 0)))]
    return A


# --- textures ------------------------------------------------------------------------------------------

def textures():
    r = np.random.default_rng(23)
    n = 64
    yy, xx = np.mgrid[0:n, 0:n]
    noise = lambda s: K.wrapnoise(r, n, s)  # noqa: E731
    img = lambda v, cols: K.ramp_img(v, cols, n)  # noqa: E731
    # hide: ash-grey fur in streaks, sooty mottling, bald scarred patches showing grey skin
    streak = np.sin(xx * 0.9 + noise(3) * 10 + yy * 0.15) * 0.5 + 0.5
    v = 0.5 + (streak - 0.5) * 0.14 + (noise(6) - 0.5) * 0.4 + (noise(1) - 0.5) * 0.25
    fur = img(v, [(62, 60, 62), (90, 87, 86), (116, 112, 108), (142, 138, 132), (168, 164, 158), (192, 188, 182)])
    bald = noise(9) > 0.68
    skin = img(0.5 + (noise(2) - 0.5) * 0.5, [(72, 58, 62), (98, 80, 82), (122, 102, 102), (142, 122, 120)])
    hide = np.where(bald[..., None], skin, fur)
    soot = noise(7) < 0.2
    hide = np.where(soot[..., None], (hide * 0.68).astype(np.uint8), hide)
    K.save_png("wolf_hide", hide)
    # hollow: dark sinew behind the ribs
    v = 0.4 + np.sin(yy * 0.8 + noise(3) * 6) * 0.2 + (noise(2) - 0.5) * 0.4
    K.save_png("wolf_hollow", img(v, [(10, 6, 8), (26, 12, 14), (46, 20, 22), (70, 32, 32), (92, 46, 44)]))
    # bone: dirty, cracked
    v = 0.6 + (noise(4) - 0.5) * 0.5
    v[(noise(1.2) > 0.82)] -= 0.4
    K.save_png("wolf_bone", img(v, [(84, 76, 60), (124, 114, 92), (162, 152, 126), (192, 184, 160), (214, 208, 188)]))
    # glow: a faint sickly violet-white, a little uneven
    v = 0.5 + (noise(3) - 0.5) * 0.6
    K.save_png("wolf_glow", img(v, [(70, 52, 96), (100, 80, 132), (134, 114, 168), (170, 154, 200)]))
    # fur tufts: two tufts side by side (u 0-0.5, 0.5-1), strands rising from the bottom, ragged
    rgba = np.zeros((n, n, 4), np.uint8)
    for half in (0, 1):
        for k in range(14):
            x0 = half * 32 + 3 + r.integers(0, 26)
            top = r.integers(4, 30)
            lean = r.uniform(-0.25, 0.25)
            col = np.array([(96, 92, 90), (124, 120, 116), (150, 146, 140), (176, 172, 166)][r.integers(0, 4)])
            for y in range(top, n):
                t = (y - top) / (n - top)
                w = 0.6 + 2.2 * t
                x = x0 + lean * (n - y)
                for xi in range(int(x - w), int(x + w) + 1):
                    if half * 32 <= xi < half * 32 + 32:
                        rgba[y, xi, :3] = (col * (0.6 + 0.4 * t)).astype(np.uint8)
                        rgba[y, xi, 3] = 255
    K.save_png("wolf_fur", rgba)


def main():
    textures()
    K.clear()
    rig = K.Rig(WOLF_BONES, "wolf")
    build_wolf(rig)
    arm = rig.build()
    for name, keys in anims().items():
        K.add_action(arm, name, keys, loc_bones=("root", "hips"))
    K.export(os.path.join(K.OUT, "hollow_wolf_hd.glb"), animations=True)
    print("hollow_wolf_hd.glb: skinned, %d triangles, %d animations" % (rig.tris, len(anims())))


if __name__ == "__main__":
    main()
