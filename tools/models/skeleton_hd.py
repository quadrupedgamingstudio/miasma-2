"""The Skeleton at look B's detail: rigid bone pieces (so they still fly apart on death, Actor.scatter) with
rusted armor scraps. Run with Blender's Python module (pip install bpy), from the project root:

    python3 tools/models/skeleton_hd.py

Writes assets/models/hd/skeleton_hd.glb and its textures (skel_*.png).

- Same node names and pivots as Miasma's skeleton.glb (SKEL_BONES below), so its animations (idle, walk,
  alert, windup, strike, stagger, recover) still play: Actor borrows that model's AnimationPlayer.
- Every bone, rib, vertebra and armor scrap is its own mesh, so more pieces scatter on death.
- Cody's pick (2026-11-15): armor scraps: a rusted half-helm, a pauldron, a tattered cloth.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rig_kit as K  # noqa: E402
from rig_kit import box, ellipsoid, loft, rot, at, tube  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

K.TILE.update({"skel_bone": 0.12, "skel_rust": 0.22, "skel_rag": 1.0, "skel_leather": 0.2})

SKEL_BONES = [
    ("skeleton", None, (0.0, 0.0, 0.0)),
    ("hips", "skeleton", (0.0, 0.97, 0.03)),
    ("spine", "hips", (0.0, 0.06, 0.02)),
    ("chest", "spine", (0.0, 0.18, 0.01)),
    ("neck", "chest", (0.0, 0.29, -0.015)),
    ("head", "neck", (0.0, 0.1, -0.02)),
    ("jaw", "head", (0.0, 0.055, 0.005)),
    ("arm_r", "chest", (0.185, 0.255, -0.05)),
    ("forearm_r", "arm_r", (0.02, -0.3, 0.015)),
    ("hand_r2", "forearm_r", (0.01, -0.26, -0.025)),
    ("arm_l", "chest", (-0.185, 0.255, -0.05)),
    ("forearm_l", "arm_l", (-0.02, -0.3, 0.015)),
    ("hand_l2", "forearm_l", (-0.01, -0.26, -0.025)),
    ("thigh_r", "hips", (0.085, -0.03, -0.03)),
    ("shin_r", "thigh_r", (0.015, -0.43, -0.005)),
    ("foot_r2", "shin_r", (0.0, -0.425, 0.015)),
    ("thigh_l", "hips", (-0.085, -0.03, -0.03)),
    ("shin_l", "thigh_l", (-0.015, -0.43, -0.005)),
    ("foot_l2", "shin_l", (0.0, -0.425, 0.015)),
]


def long_bone(m, top, bottom, r_shaft, r_top, r_bot, mat="skel_bone"):
    """A limb bone: a shaft with knobbly ends."""
    tube(m, [top, [(a + b) / 2 for a, b in zip(top, bottom)], bottom], [r_shaft * 1.15, r_shaft, r_shaft * 1.2], mat, seg=8, cap=False)
    ellipsoid(m, tuple(top), (r_top, r_top * 0.85, r_top * 0.9), mat, seg=10, rings=6)
    ellipsoid(m, tuple(bottom), (r_bot * 1.2, r_bot * 0.8, r_bot), mat, seg=10, rings=6)


def build(r):
    P = r.piece
    # --- skull: cranium, brow, cheekbones, deep sockets, the nasal hole, upper teeth
    P("cranium", "head", "skel_bone", lambda m: ellipsoid(m, (0, 0.125, 0.0), (0.072, 0.082, 0.092), "skel_bone", seg=18, rings=12))
    P("face", "head", "skel_bone", lambda m: ellipsoid(m, (0, 0.075, -0.05), (0.058, 0.055, 0.05), "skel_bone", seg=14, rings=8))
    P("brow", "head", "skel_bone", lambda m: ellipsoid(m, (0, 0.122, -0.074), (0.062, 0.018, 0.022), "skel_bone", seg=12, rings=6))
    for s in (1, -1):
        P("cheek_%d" % s, "head", "skel_bone", lambda m, s=s: ellipsoid(m, (s * 0.048, 0.08, -0.058), (0.022, 0.016, 0.028), "skel_bone", seg=8, rings=5))
        P("socket_%d" % s, "head", "dark", lambda m, s=s: ellipsoid(m, (s * 0.027, 0.103, -0.083), (0.021, 0.019, 0.012), "dark", seg=10, rings=6))
    P("nasal", "head", "dark", lambda m: ellipsoid(m, (0, 0.077, -0.096), (0.01, 0.017, 0.008), "dark", seg=8, rings=5))

    def teeth(m, y, z0, rx, n, h):
        for i in range(n):
            a = math.pi * (0.2 + 0.6 * i / (n - 1))
            x, z = -math.cos(a) * rx, z0 - math.sin(a) * rx * 0.9
            box(m, (x, y, z), (0.009, h, 0.008), "skel_bone")
    P("teeth_upper", "head", "skel_bone", lambda m: teeth(m, 0.047, -0.03, 0.04, 10, 0.016))
    # --- the jaw: a U of bone hinged under the ears, its teeth
    P("mandible", "jaw", "skel_bone", lambda m: tube(m, [(-0.052, 0.0, 0.0), (-0.05, -0.03, -0.035), (-0.035, -0.042, -0.07), (0, -0.046, -0.088),
                                                         (0.035, -0.042, -0.07), (0.05, -0.03, -0.035), (0.052, 0.0, 0.0)], 0.011, "skel_bone", seg=8))
    P("teeth_lower", "jaw", "skel_bone", lambda m: teeth(m, -0.03, -0.035, 0.036, 8, 0.014))

    # --- neck: four vertebrae
    for i in range(4):
        y = 0.012 + i * 0.026
        P("cervical_%d" % i, "neck", "skel_bone", lambda m, y=y: (ellipsoid(m, (0, y, -0.004 * y / 0.03), (0.018, 0.011, 0.02), "skel_bone", seg=10, rings=5),
                                                                 box(m, (0, y, 0.022), (0.008, 0.008, 0.02), "skel_bone")))

    # --- chest: the thoracic spine, seven pairs of ribs, sternum, collarbones, shoulder blades
    for i in range(8):
        y = 0.01 + i * 0.034
        P("thoracic_%d" % i, "chest", "skel_bone", lambda m, y=y: (ellipsoid(m, (0, y, 0.01), (0.019, 0.014, 0.02), "skel_bone", seg=10, rings=5),
                                                                  box(m, (0, y - 0.006, 0.034), (0.008, 0.01, 0.024), "skel_bone", xf=rot("X", 0))))
    for i in range(7):
        y = 0.235 - i * 0.034
        rx = 0.075 + 0.06 * math.sin(math.pi * (i + 1.5) / 9)
        rz = 0.07 + 0.045 * math.sin(math.pi * (i + 1.5) / 9)
        reach = 60 if i < 5 else 20 + (6 - i) * 15   # the lower ribs stop short of the breastbone
        for s in (1, -1):
            pts = []
            for k in range(9):
                th = math.radians(90 - (90 + reach) * k / 8)
                pts.append((s * (0.018 + rx * math.cos(th)), y - 0.05 * (k / 8) ** 1.5, -0.035 + rz * math.sin(th) * (1.0 if th > 0 else 1.12)))
            P("rib_%d_%d" % (s, i), "chest", "skel_bone", lambda m, pts=pts: tube(m, pts, 0.0085, "skel_bone", seg=6))
    P("sternum", "chest", "skel_bone", lambda m: box(m, (0, 0.13, -0.148), (0.028, 0.15, 0.014), "skel_bone", xf=rot("X", -8)))
    for s in (1, -1):
        P("clavicle_%d" % s, "chest", "skel_bone", lambda m, s=s: tube(m, [(s * 0.012, 0.236, -0.13), (s * 0.08, 0.252, -0.12), (s * 0.165, 0.258, -0.06)], 0.009, "skel_bone", seg=6))
        P("scapula_%d" % s, "chest", "skel_bone", lambda m, s=s: box(m, (s * 0.1, 0.17, 0.045), (0.095, 0.15, 0.012), "skel_bone", xf=rot("Y", s * -18)))

    # --- lumbar spine
    for i in range(5):
        y = 0.008 + i * 0.036
        P("lumbar_%d" % i, "spine", "skel_bone", lambda m, y=y: (ellipsoid(m, (0, y, 0.004), (0.026, 0.014, 0.026), "skel_bone", seg=10, rings=5),
                                                                box(m, (0, y, 0.032), (0.01, 0.012, 0.026), "skel_bone")))

    # --- pelvis, the rotted belt, the loincloth rags
    for s in (1, -1):
        P("ilium_%d" % s, "hips", "skel_bone", lambda m, s=s: ellipsoid(m, (s * 0.09, 0.02, 0.0), (0.06, 0.075, 0.03), "skel_bone", seg=12, rings=6, xf=rot("Y", s * -25)))
    P("sacrum", "hips", "skel_bone", lambda m: box(m, (0, -0.0, 0.05), (0.06, 0.12, 0.022), "skel_bone", xf=rot("X", 12)))
    P("pubis", "hips", "skel_bone", lambda m: tube(m, [(0.09, -0.04, -0.02), (0.05, -0.07, -0.07), (0, -0.075, -0.08), (-0.05, -0.07, -0.07), (-0.09, -0.04, -0.02)], 0.012, "skel_bone", seg=6))
    P("belt", "hips", "skel_leather", lambda m: loft(m, [(0.03, 0.15, 0.1), (0.058, 0.152, 0.102)], "skel_leather", seg=16, e=2.2))
    P("buckle", "hips", "skel_rust", lambda m: box(m, (0.02, 0.044, -0.104), (0.036, 0.03, 0.008), "skel_rust"))
    rag = K.card
    P("rag_front", "hips", "skel_rag", lambda m: rag(m, [(-0.085, 0.035, -0.108), (0.085, 0.035, -0.108), (0.075, -0.27, -0.13), (-0.08, -0.25, -0.12)], "skel_rag",
                                                     uv=((0, 0), (0.5, 0), (0.5, 1), (0, 1))))
    P("rag_back", "hips", "skel_rag", lambda m: rag(m, [(0.09, 0.035, 0.1), (-0.09, 0.035, 0.1), (-0.085, -0.22, 0.12), (0.08, -0.24, 0.125)], "skel_rag",
                                                    uv=((0.5, 0), (1, 0), (1, 1), (0.5, 1))))

    # --- arms
    for s, sn in ((1, "r"), (-1, "l")):
        P("humerus_" + sn, "arm_" + sn, "skel_bone", lambda m, s=s: long_bone(m, (0.0, -0.01, 0.0), (s * 0.018, -0.29, 0.012), 0.014, 0.026, 0.02))
        P("ulna_" + sn, "forearm_" + sn, "skel_bone", lambda m, s=s: long_bone(m, (s * 0.004, -0.005, 0.012), (s * 0.006, -0.245, -0.002), 0.008, 0.014, 0.01))
        P("radius_" + sn, "forearm_" + sn, "skel_bone", lambda m, s=s: long_bone(m, (s * -0.002, -0.01, -0.02), (s * 0.012, -0.245, -0.035), 0.008, 0.011, 0.013))
        hb = "hand_%s2" % sn
        P("carpals_" + sn, hb, "skel_bone", lambda m: ellipsoid(m, (0, -0.02, 0.0), (0.024, 0.018, 0.03), "skel_bone", seg=10, rings=6))
        if s > 0:
            # curled round the sword's grip
            for k in range(4):
                z = -0.022 + k * 0.015
                P("finger_r%d" % k, hb, "skel_bone", lambda m, z=z: tube(m, [(-0.012, -0.035, z), (-0.02, -0.07, z), (0.004, -0.09, z), (0.018, -0.076, z)], 0.0055, "skel_bone", seg=5))
            P("thumb_r", hb, "skel_bone", lambda m: tube(m, [(0.012, -0.03, -0.03), (0.02, -0.06, -0.045), (0.012, -0.078, -0.05)], 0.006, "skel_bone", seg=5))
        else:
            for k in range(4):
                z = -0.022 + k * 0.015
                P("finger_l%d" % k, hb, "skel_bone", lambda m, z=z: tube(m, [(0.0, -0.035, z), (0.004, -0.075, z - 0.004), (0.01, -0.105, z - 0.01)], 0.0055, "skel_bone", seg=5))
            P("thumb_l", hb, "skel_bone", lambda m: tube(m, [(-0.012, -0.03, -0.03), (-0.022, -0.06, -0.045), (-0.024, -0.082, -0.052)], 0.006, "skel_bone", seg=5))

    # the rusted sword, held point-forward like Miasma's (blade along -Z from the fist)
    sw = at(0.004, -0.078, -0.012)
    P("sword_blade", "hand_r2", "skel_rust", lambda m: loft(m, [(0.06, 0.032, 0.009), (0.3, 0.03, 0.009), (0.55, 0.027, 0.008), (0.72, 0.016, 0.006), (0.79, 0.001, 0.001)],
                                                          "skel_rust", seg=4, e=1.0, cap0=True, xf=sw @ rot("X", -90) @ rot("Y", 90)))
    P("sword_guard", "hand_r2", "skel_rust", lambda m: box(m, (0, 0, -0.05), (0.16, 0.018, 0.016), "skel_rust", xf=sw @ rot("Z", 90)))
    P("sword_grip", "hand_r2", "skel_leather", lambda m: tube(m, [sw @ Vector((0, 0, -0.04)), sw @ Vector((0, 0, 0.05))], 0.015, "skel_leather", seg=8, cap=False))
    P("sword_pommel", "hand_r2", "skel_rust", lambda m: ellipsoid(m, tuple(sw @ Vector((0, 0, 0.068))), (0.02, 0.02, 0.02), "skel_rust", seg=8, rings=5))

    # --- legs
    for s, sn in ((1, "r"), (-1, "l")):
        P("femur_" + sn, "thigh_" + sn, "skel_bone", lambda m, s=s: long_bone(m, (s * -0.012, 0.0, 0.0), (s * 0.012, -0.415, 0.0), 0.016, 0.028, 0.026))
        P("patella_" + sn, "thigh_" + sn, "skel_bone", lambda m, s=s: ellipsoid(m, (s * 0.014, -0.43, -0.036), (0.017, 0.022, 0.01), "skel_bone", seg=8, rings=5))
        P("tibia_" + sn, "shin_" + sn, "skel_bone", lambda m: long_bone(m, (0.0, -0.01, 0.0), (0.0, -0.405, 0.008), 0.014, 0.03, 0.02))
        P("fibula_" + sn, "shin_" + sn, "skel_bone", lambda m, s=s: long_bone(m, (s * 0.03, -0.03, 0.016), (s * 0.026, -0.39, 0.018), 0.006, 0.01, 0.012))
        fb = "foot_%s2" % sn
        P("tarsals_" + sn, fb, "skel_bone", lambda m: ellipsoid(m, (0, -0.045, 0.0), (0.026, 0.024, 0.04), "skel_bone", seg=10, rings=6))
        for k in range(4):
            x = (k - 1.5) * 0.017
            P("toe_%s%d" % (sn, k), fb, "skel_bone", lambda m, x=x: tube(m, [(x * 0.6, -0.055, -0.02), (x, -0.07, -0.09), (x * 1.1, -0.075, -0.135)], 0.0065, "skel_bone", seg=5))

    # --- armor scraps: a rusted half-helm (dented, its brim torn), a layered pauldron, a tattered cloth
    dome = [(0.105, 0.081, 0.097), (0.145, 0.08, 0.096), (0.18, 0.068, 0.082), (0.205, 0.046, 0.058), (0.215, 0.012, 0.015)]
    P("half_helm", "head", "skel_rust", lambda m: loft(m, dome, "skel_rust", seg=20, a0=-math.pi * 0.35, a1=math.pi * 1.35, xf=at(0, 0, 0.004) @ rot("Z", -6)))
    P("helm_rim", "head", "skel_rust", lambda m: loft(m, [(0.098, 0.084, 0.1), (0.112, 0.084, 0.1)], "skel_rust", seg=20, a0=-math.pi * 0.2, a1=math.pi * 1.2,
                                                       xf=at(0, 0, 0.004) @ rot("Z", -6)))
    P("helm_crest", "head", "skel_rust", lambda m: box(m, (0, 0.17, 0.0), (0.012, 0.03, 0.18), "skel_rust", xf=rot("Z", -6)))
    for k in range(3):
        P("pauldron_%d" % k, "arm_l", "skel_rust", lambda m, k=k: loft(m, [(-0.07 + k * 0.035, 0.075 - k * 0.006, 0.08 - k * 0.006), (-0.035 + k * 0.035, 0.077 - k * 0.006, 0.082 - k * 0.006),
                                                                          (-0.005 + k * 0.03, 0.06 - k * 0.012, 0.066 - k * 0.012)],
                                                                    "skel_rust", seg=12, a0=-math.pi * 0.95, a1=math.pi * 0.95, xf=at(-0.02, 0.0, 0.0) @ rot("Z", 30)))
    P("pauldron_strap", "chest", "skel_leather", lambda m: tube(m, [(-0.17, 0.27, -0.06), (-0.06, 0.2, -0.13), (0.06, 0.08, -0.12), (0.13, -0.02, -0.08)], 0.008, "skel_leather", seg=5))
    P("cloak", "chest", "skel_rag", lambda m: (rag(m, [(-0.16, 0.27, 0.05), (0.15, 0.27, 0.05), (0.18, -0.12, 0.12), (-0.14, -0.18, 0.1)], "skel_rag",
                                                  uv=((0, 0), (1, 0), (1, 1), (0, 1)))))


def textures():
    r = np.random.default_rng(31)
    n = 64
    yy, xx = np.mgrid[0:n, 0:n]
    noise = lambda s: K.wrapnoise(r, n, s)  # noqa: E731
    img = lambda v, cols: K.ramp_img(v, cols, n)  # noqa: E731
    # bone: old, yellowed, stained and cracked
    v = 0.6 + (noise(5) - 0.5) * 0.4 + (noise(1) - 0.5) * 0.2
    v[noise(1.3) > 0.84] -= 0.45
    K.save_png("skel_bone", img(v, [(70, 62, 48), (112, 102, 80), (150, 140, 114), (184, 176, 150), (210, 204, 182)]))
    # rust: pitted orange-brown iron with dark scale
    v = 0.5 + (noise(4) - 0.5) * 0.6 + (noise(1) - 0.5) * 0.35
    K.save_png("skel_rust", img(v, [(36, 24, 18), (68, 38, 22), (104, 56, 28), (138, 78, 38), (164, 104, 56), (120, 112, 104)]))
    # leather: dried, cracked, near black
    v = 0.45 + (noise(3) - 0.5) * 0.5
    v[(noise(0.8) > 0.8)] -= 0.4
    K.save_png("skel_leather", img(v, [(22, 16, 12), (38, 28, 20), (56, 42, 30), (74, 58, 42)]))
    # rag: a faded, mouldering cloth with torn holes and a ragged hem (alpha)
    weave = ((xx % 2) ^ (yy % 2)) * 0.1
    v = 0.5 + weave + (noise(5) - 0.5) * 0.5
    rgb = img(v, [(52, 48, 38), (76, 70, 52), (100, 92, 68), (124, 116, 88)])
    hem = 52 + (noise(2) * 14).astype(int)
    holes = noise(4) > 0.78
    alpha = np.where((yy < hem) & ~holes, 255, 0).astype(np.uint8)
    rgba = np.dstack([rgb, alpha])
    K.save_png("skel_rag", rgba)


def main():
    textures()
    K.clear()
    r = K.Rigid(SKEL_BONES)
    build(r)
    K.export(os.path.join(K.OUT, "skeleton_hd.glb"))
    print("skeleton_hd.glb: %d pieces, %d triangles" % (r.count, r.tris))


if __name__ == "__main__":
    main()
