"""Look B: the Guard (Miasma 1's hero, now Emberwick's town guard) rebuilt in Blender at higher detail,
plus his broadsword. Run with Blender's Python module (pip install bpy), from the project root:

    python3 tools/models/guard_hd.py

Writes assets/models/hd/guard_hd.glb, broadsword_hd.glb and their textures (*.png, made here too).

How the model fits the game:
- Same skeleton as Miasma's player model (assets/models/player/player.glb): the same parts
  (hips, spine, chest, neck, head, arm_r, forearm_r, hand_r, thigh_r, shin_r, foot_r and the left
  ones) at the same pivots, so the walk / run / idle from player.glb and every battle animation
  made in scripts/actor.gd play on it unchanged (Actor borrows player.glb's AnimationPlayer).
- Like the PS1 model it is made of rigid pieces that ride their bone (no skinning); joints are
  hidden by overlapping pieces (sleeve flares, knee cops, the mail skirt halves ride the thighs).
  A skinned Blender rig is the next step if look B is picked.
- Each mesh is named "<piece>__<material>"; Actor gives it assets/models/hd/<material>.png.
- Texture UVs are in real-world units (a tile = TILE[material] metres), so every piece shares one
  texel density and the textures (64 px tiles) stay crisp pixel art up close.

Coordinates: written in Godot's frame (Y up, the model faces -Z, +X is its right hand), turned into
Blender's (Z up) by G(); the glTF exporter turns it back.
"""
import math
import os

import bpy  # noqa: I001  (bpy first: it makes bmesh and mathutils importable)
import bmesh
import numpy as np
from mathutils import Matrix, Vector
from PIL import Image

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT = os.path.join(ROOT, "assets", "models", "hd")

SEG = 16  # sides on round pieces

# metres per texture tile, per material
TILE = {"mail": 0.11, "iron": 0.3, "leather": 0.22, "boot": 0.22, "cloth": 0.3, "padding": 0.18,
        "trousers": 0.25, "skin": 0.2, "hair": 0.12, "brass": 0.1, "emblem": 1.0, "dark": 0.2,
        "steel": 0.3, "grip": 0.08}

# the skeleton: bone -> (parent, local offset), copied from player.glb
BONES = [
    ("root", None, (0, 0, 0)),
    ("hips", "root", (0, 0.961, 0)),
    ("spine", "hips", (0, 0.081, 0.01)),
    ("chest", "spine", (0, 0.172, 0)),
    ("neck", "chest", (0, 0.243, 0)),
    ("head", "neck", (0, 0.061, -0.01)),
    ("arm_r", "chest", (0.19, 0.207, 0.002)),
    ("forearm_r", "arm_r", (0.03, -0.309, 0.018)),
    ("hand_r", "forearm_r", (0.015, -0.258, -0.03)),
    ("arm_l", "chest", (-0.19, 0.207, 0.002)),
    ("forearm_l", "arm_l", (-0.03, -0.309, 0.018)),
    ("hand_l", "forearm_l", (-0.015, -0.258, -0.03)),
    ("thigh_r", "hips", (0.092, -0.051, 0)),
    ("shin_r", "thigh_r", (0.005, -0.415, -0.01)),
    ("foot_r", "shin_r", (0.003, -0.415, 0.02)),
    ("thigh_l", "hips", (-0.092, -0.051, 0)),
    ("shin_l", "thigh_l", (-0.005, -0.415, -0.01)),
    ("foot_l", "shin_l", (-0.003, -0.415, 0.02)),
]


def G(x, y, z):
    """Godot (Y up, -Z forward) -> Blender (Z up)."""
    return Vector((x, -z, y))


# --- mesh building ----------------------------------------------------------------------------------

class Mesh:
    """Collects quads/triangles with UVs, then becomes a Blender object on a bone."""

    def __init__(self):
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("UVMap")

    def face(self, pts, uvs, smooth=True):
        vs = [self.bm.verts.new(G(*p)) for p in pts]
        try:
            f = self.bm.faces.new(vs)
        except ValueError:
            return None
        f.smooth = smooth
        for loop, uv in zip(f.loops, uvs):
            loop[self.uv].uv = uv
        return f

    def finish(self, name, bone, objs):
        bmesh.ops.remove_doubles(self.bm, verts=self.bm.verts, dist=1e-5)
        me = bpy.data.meshes.new(name)
        self.bm.to_mesh(me)
        self.bm.free()
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        ob.parent = objs[bone]
        ob.matrix_parent_inverse = Matrix.Identity(4)
        return ob


def superellipse(a, rx, rz, e):
    c, s = math.cos(a), math.sin(a)
    x = rx * math.copysign(abs(c) ** (2.0 / e), c)
    z = rz * math.copysign(abs(s) ** (2.0 / e), s)
    return x, z


def loft(m, sections, mat, xf=None, a0=0.0, a1=2 * math.pi, cap0=False, cap1=False, seg=SEG, e=2.0):
    """A tube through cross-sections [(y, rx, rz, cx, cz), ...] (cx, cz optional) in a frame where
    the tube runs along +Y; xf (Matrix, Godot space) places it. a0..a1 = the part of the circle to
    build (a partial tube = a plate). Angle 0 = +X, pi/2 = +Z (the back), -pi/2 = -Z (the front)."""
    xf = xf or Matrix.Identity(4)
    tile = TILE[mat]
    full = abs((a1 - a0) - 2 * math.pi) < 1e-6
    rings = []
    for sec in sections:
        y, rx, rz = sec[0], sec[1], sec[2]
        cx = sec[3] if len(sec) > 3 else 0.0
        cz = sec[4] if len(sec) > 4 else 0.0
        ring = []
        for i in range(seg + 1):
            a = a0 + (a1 - a0) * i / seg
            x, z = superellipse(a, rx, rz, e)
            ring.append(xf @ Vector((cx + x, y, cz + z)))
        rings.append(ring)
    # u along the circumference (metres / tile), v along the length
    vs = [0.0]
    for k in range(1, len(rings)):
        d = sum((rings[k][i] - rings[k - 1][i]).length for i in range(seg + 1)) / (seg + 1)
        vs.append(vs[-1] + d)
    for k in range(len(rings) - 1):
        us0 = [0.0]
        for i in range(1, seg + 1):
            us0.append(us0[-1] + (rings[k][i] - rings[k][i - 1]).length)
        for i in range(seg):
            p = [rings[k][i], rings[k][i + 1], rings[k + 1][i + 1], rings[k + 1][i]]
            uv = [(us0[i] / tile, vs[k] / tile), (us0[i + 1] / tile, vs[k] / tile),
                  (us0[i + 1] / tile, vs[k + 1] / tile), (us0[i] / tile, vs[k + 1] / tile)]
            m.face([tuple(q) for q in p], uv)
    for capk, flip in ((0, True), (len(rings) - 1, False)):
        if not ((cap0 and capk == 0) or (cap1 and capk != 0)):
            continue
        ring = rings[capk][: seg if full else seg + 1]
        c = sum(ring, Vector()) / len(ring)
        for i in range(len(ring) - (0 if full else 1)):
            a, b = ring[i], ring[(i + 1) % len(ring)]
            tri = [c, b, a] if flip else [c, a, b]
            m.face([tuple(q) for q in tri], [((q.x) / tile, (q.z) / tile) for q in tri], smooth=False)


def rib(m, sections, angle, width, mat):
    """A thin strip laid over a lofted dome's surface at one angle (the helm's riveted ribs)."""
    tile = TILE[mat]
    pts = []
    for y, rx, rz in sections:
        c, s_ = math.cos(angle), math.sin(angle)
        p = Vector((rx * c * 1.04, y, rz * s_ * 1.04))
        t = Vector((-s_, 0, c)) * width
        pts.append((p - t, p + t))
    for k in range(len(pts) - 1):
        a, b = pts[k], pts[k + 1]
        m.face([tuple(a[0]), tuple(a[1]), tuple(b[1]), tuple(b[0])],
               [(0, k * 0.3), (0.2, k * 0.3), (0.2, (k + 1) * 0.3), (0, (k + 1) * 0.3)], smooth=False)


def ellipsoid(m, center, radii, mat, seg=SEG, rings=10, keep=None):
    """An ellipsoid; keep(x, y, z) -> bool drops faces whose centre fails it (cut shapes: beard)."""
    tile = TILE[mat]
    cx, cy, cz = center
    rx, ry, rz = radii
    pts = []
    for j in range(rings + 1):
        t = math.pi * j / rings
        row = []
        for i in range(seg + 1):
            a = 2 * math.pi * i / seg
            row.append((cx + rx * math.sin(t) * math.cos(a), cy + ry * math.cos(t), cz + rz * math.sin(t) * math.sin(a)))
        pts.append(row)
    for j in range(rings):
        for i in range(seg):
            q = [pts[j][i], pts[j][i + 1], pts[j + 1][i + 1], pts[j + 1][i]]
            if keep:
                c = [sum(v[k] for v in q) / 4 for k in range(3)]
                if not keep(*c):
                    continue
            uv = [(i / seg * 2 * math.pi * max(rx, rz) / tile, j / rings * math.pi * ry / tile),
                  ((i + 1) / seg * 2 * math.pi * max(rx, rz) / tile, j / rings * math.pi * ry / tile),
                  ((i + 1) / seg * 2 * math.pi * max(rx, rz) / tile, (j + 1) / rings * math.pi * ry / tile),
                  (i / seg * 2 * math.pi * max(rx, rz) / tile, (j + 1) / rings * math.pi * ry / tile)]
            m.face(q, uv)


def box(m, center, size, mat, xf=None, smooth=False):
    xf = xf or Matrix.Identity(4)
    tile = TILE[mat]
    hx, hy, hz = size[0] / 2, size[1] / 2, size[2] / 2
    c = Vector(center)
    corners = [Vector((sx * hx, sy * hy, sz * hz)) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
    P = [xf @ (c + v) for v in corners]
    quads = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    for q in quads:
        pts = [P[i] for i in q]
        n = (pts[1] - pts[0]).cross(pts[2] - pts[0])
        ax = max(range(3), key=lambda k: abs(n[k]))
        uv = [((p[(ax + 1) % 3]) / tile, (p[(ax + 2) % 3]) / tile) for p in pts]
        m.face([tuple(p) for p in pts], uv, smooth=smooth)


def rot(axis, deg):
    return Matrix.Rotation(math.radians(deg), 4, axis)


def at(x, y, z):
    return Matrix.Translation((x, y, z))


# --- the Guard --------------------------------------------------------------------------------------

def build_guard(objs):
    parts = []

    def piece(name, bone, mat, fn):
        m = Mesh()
        fn(m)
        parts.append(m.finish("%s__%s" % (name, mat), bone, objs))

    # hips: the hauberk's waist under the belt, the belt and its buckle, a pouch
    piece("waist", "hips", "mail", lambda m: loft(m, [(-0.09, 0.172, 0.118), (0.0, 0.178, 0.12), (0.07, 0.176, 0.12)], "mail", e=2.3))
    piece("belt", "hips", "leather", lambda m: loft(m, [(0.0, 0.186, 0.127), (0.048, 0.186, 0.127)], "leather", e=2.3))
    piece("buckle", "hips", "brass", lambda m: box(m, (0.0, 0.024, -0.13), (0.05, 0.045, 0.012), "brass"))
    piece("pouch", "hips", "leather", lambda m: box(m, (-0.17, -0.03, -0.04), (0.04, 0.075, 0.06), "leather", xf=rot("Y", -12)))

    # chest: the hauberk, the ember-red tabard over it, Emberwick's flame on the front
    torso = [(-0.24, 0.172, 0.114), (-0.12, 0.168, 0.11), (0.0, 0.178, 0.118, 0, -0.004), (0.1, 0.19, 0.126, 0, -0.008),
             (0.18, 0.198, 0.12, 0, -0.004), (0.235, 0.18, 0.1), (0.27, 0.12, 0.08), (0.29, 0.06, 0.055)]
    piece("hauberk", "chest", "mail", lambda m: loft(m, torso, "mail", e=2.4, cap1=True))
    tab = [(-0.25, 0.184, 0.126), (-0.12, 0.18, 0.122), (0.0, 0.19, 0.13, 0, -0.004), (0.1, 0.2, 0.137, 0, -0.008), (0.17, 0.205, 0.132, 0, -0.004)]
    piece("tabard", "chest", "cloth", lambda m: loft(m, tab, "cloth", e=2.4))

    def emblem(m):
        z = -0.139
        s = 0.075
        y = 0.05
        m.face([(-s, y - s, z), (s, y - s, z), (s, y + s, z), (-s, y + s, z)],
               [(0, 0), (1, 0), (1, 1), (0, 1)], smooth=False)
    piece("emblem", "chest", "emblem", emblem)

    # neck and head
    piece("neck", "neck", "skin", lambda m: loft(m, [(-0.04, 0.046, 0.044), (0.09, 0.044, 0.042)], "skin"))
    piece("head", "head", "skin", lambda m: ellipsoid(m, (0, 0.092, -0.004), (0.071, 0.104, 0.09), "skin", seg=18, rings=12))
    piece("nose", "head", "skin", lambda m: box(m, (0, 0.078, -0.094), (0.022, 0.04, 0.026), "skin", xf=rot("X", -12)))
    for side in (1, -1):
        piece("eye_%s" % side, "head", "dark", lambda m, s=side: ellipsoid(m, (s * 0.027, 0.1, -0.083), (0.013, 0.008, 0.006), "dark", seg=8, rings=4))
        piece("brow_%s" % side, "head", "hair", lambda m, s=side: box(m, (s * 0.029, 0.114, -0.087), (0.032, 0.01, 0.012), "hair", xf=rot("Z", s * -10)))
    piece("beard", "head", "hair", lambda m: ellipsoid(m, (0, 0.024, -0.026), (0.075, 0.07, 0.075), "hair", seg=18, rings=10,
                                                       keep=lambda x, y, z: y < 0.05 and z < 0.02 and not (abs(x) < 0.02 and 0.034 < y)))
    piece("moustache", "head", "hair", lambda m: box(m, (0, 0.054, -0.094), (0.05, 0.014, 0.016), "hair"))
    # the iron helm: a pointed spangenhelm with a rim band, a nasal and the mail aventail
    dome = [(0.126, 0.087, 0.104), (0.168, 0.083, 0.099), (0.204, 0.071, 0.086), (0.232, 0.051, 0.063), (0.252, 0.026, 0.032), (0.264, 0.004, 0.005)]
    piece("helm", "head", "iron", lambda m: loft(m, dome, "iron", seg=20))
    piece("helm_band", "head", "iron", lambda m: loft(m, [(0.121, 0.093, 0.11), (0.149, 0.092, 0.109)], "iron", seg=20, cap0=False))
    piece("nasal", "head", "iron", lambda m: box(m, (0, 0.107, -0.105), (0.016, 0.074, 0.008), "iron", xf=rot("X", -4)))
    for k in range(4):
        piece("helm_rib_%d" % k, "head", "brass", lambda m, k=k: rib(m, dome[:-1], math.radians(45 + 90 * k), 0.006, "brass"))
    # the aventail hangs from the helm round the sides and back; the face stays open (65 degrees either side)
    gap = math.radians(65)
    piece("aventail", "head", "mail", lambda m: loft(m, [(0.126, 0.092, 0.108), (0.06, 0.097, 0.111), (-0.02, 0.118, 0.12), (-0.075, 0.15, 0.13)],
                                                     "mail", a0=-math.pi / 2 + gap, a1=math.pi * 1.5 - gap, seg=18))

    # arms: mail sleeves, iron spaulders, quilted gambeson forearms, leather bracers and gloves
    for side, sn in ((1, "r"), (-1, "l")):
        piece("sleeve_" + sn, "arm_" + sn, "mail", lambda m, s=side: loft(m, [(0.03, 0.064, 0.062, s * 0.008), (-0.1, 0.06, 0.057, s * 0.008),
                                                                             (-0.22, 0.057, 0.054, s * 0.01), (-0.3, 0.061, 0.058, s * 0.012), (-0.335, 0.068, 0.064, s * 0.014)], "mail"))
        piece("spaulder_" + sn, "arm_" + sn, "iron", lambda m, s=side: loft(m, [(-0.085, 0.072, 0.078), (-0.02, 0.078, 0.084), (0.025, 0.066, 0.072), (0.05, 0.04, 0.045), (0.062, 0.008, 0.01)],
                                                                            "iron", xf=at(s * 0.028, 0.0, 0.0) @ rot("Z", s * -34)))
        piece("forearm_" + sn, "forearm_" + sn, "padding", lambda m, s=side: loft(m, [(0.03, 0.05, 0.048), (-0.05, 0.048, 0.046), (-0.09, 0.045, 0.043)], "padding"))
        piece("bracer_" + sn, "forearm_" + sn, "leather", lambda m, s=side: loft(m, [(-0.07, 0.049, 0.047), (-0.16, 0.044, 0.042), (-0.24, 0.043, 0.04), (-0.255, 0.048, 0.045)], "leather"))
        for k, y in enumerate((-0.11, -0.2)):
            piece("bracer_strap_%s%d" % (sn, k), "forearm_" + sn, "dark", lambda m, y=y: loft(m, [(y, 0.0495, 0.0475), (y + 0.012, 0.0495, 0.0475)], "dark"))
        piece("cuff_" + sn, "hand_" + sn, "boot", lambda m: loft(m, [(0.02, 0.042, 0.045), (-0.03, 0.036, 0.045)], "boot"))
        if side > 0:
            # the sword hand: a fist round the grip
            piece("palm_r", "hand_r", "boot", lambda m: loft(m, [(-0.01, 0.026, 0.044), (-0.055, 0.028, 0.048), (-0.075, 0.026, 0.044)], "boot", cap1=True, e=2.6))
            piece("fingers_r", "hand_r", "boot", lambda m: ellipsoid(m, (-0.006, -0.083, 0.0), (0.032, 0.03, 0.05), "boot", seg=12, rings=8))
            piece("thumb_r", "hand_r", "boot", lambda m: loft(m, [(0, 0.013, 0.012), (0.045, 0.011, 0.01)], "boot", seg=8, cap1=True,
                                                               xf=at(-0.02, -0.04, -0.04) @ rot("Z", 60) @ rot("X", -30)))
        else:
            # the off hand: open, fingers together
            piece("palm_l", "hand_l", "boot", lambda m: loft(m, [(-0.01, 0.022, 0.042), (-0.07, 0.022, 0.044)], "boot", cap1=True, e=2.6))
            piece("fingers_l", "hand_l", "boot", lambda m: loft(m, [(-0.065, 0.019, 0.04), (-0.1, 0.016, 0.036), (-0.118, 0.01, 0.026)], "boot", cap1=True, e=2.4,
                                                                 xf=at(0.004, 0, 0) @ rot("Z", -6)))
            piece("thumb_l", "hand_l", "boot", lambda m: loft(m, [(0, 0.012, 0.011), (0.045, 0.01, 0.009)], "boot", seg=8, cap1=True,
                                                               xf=at(0.012, -0.03, -0.035) @ rot("Z", -150) @ rot("X", 20)))

    # legs: wool trousers, the mail skirt in two halves (they ride the thighs, so no clipping), knee-high
    # boots, iron greaves and knee cops, sabaton plates on the feet
    for side, sn in ((1, "r"), (-1, "l")):
        piece("trousers_" + sn, "thigh_" + sn, "trousers", lambda m, s=side: loft(m, [(0.06, 0.084, 0.084), (-0.1, 0.078, 0.075), (-0.25, 0.064, 0.062), (-0.41, 0.054, 0.057)], "trousers"))
        piece("skirt_" + sn, "thigh_" + sn, "mail", lambda m, s=side: loft(m, [(0.1, 0.1, 0.122, -s * 0.012), (0.0, 0.106, 0.128, -s * 0.01), (-0.12, 0.112, 0.132, -s * 0.004), (-0.215, 0.118, 0.136)], "mail"))
        piece("boot_" + sn, "shin_" + sn, "boot", lambda m: loft(m, [(-0.01, 0.06, 0.064), (-0.06, 0.056, 0.06), (-0.18, 0.051, 0.056, 0, 0.004), (-0.33, 0.043, 0.047), (-0.42, 0.046, 0.05)], "boot"))
        piece("boot_cuff_" + sn, "shin_" + sn, "leather", lambda m: loft(m, [(-0.05, 0.066, 0.07), (0.0, 0.07, 0.074)], "leather"))
        piece("greave_" + sn, "shin_" + sn, "iron", lambda m: loft(m, [(-0.07, 0.066, 0.07), (-0.2, 0.062, 0.066, 0, 0.003), (-0.34, 0.054, 0.058)], "iron",
                                                                  a0=-math.pi * 0.92, a1=-math.pi * 0.08, seg=10))
        piece("knee_" + sn, "shin_" + sn, "iron", lambda m: loft(m, [(0.0, 0.058, 0.06), (0.03, 0.05, 0.052), (0.055, 0.03, 0.032), (0.066, 0.004, 0.004)], "iron",
                                                                xf=at(0, 0.005, -0.03) @ rot("X", -90)))
        # feet: lofted heel to toe (the loft's Y runs along +Z here; a section's z is the foot's height, down)
        piece("foot_" + sn, "foot_" + sn, "boot", lambda m: loft(m, [(0.048, 0.03, 0.036, 0, 0.04), (0.02, 0.044, 0.052, 0, 0.03), (-0.04, 0.047, 0.045, 0, 0.045),
                                                                    (-0.11, 0.045, 0.034, 0, 0.055), (-0.155, 0.036, 0.024, 0, 0.06), (-0.172, 0.012, 0.01, 0, 0.065)],
                                                                "boot", xf=rot("X", 90), cap0=True, cap1=True))
        piece("sabaton_" + sn, "foot_" + sn, "iron", lambda m: loft(m, [(0.0, 0.05, 0.05, 0, 0.022), (-0.06, 0.05, 0.042, 0, 0.032), (-0.12, 0.046, 0.032, 0, 0.042)],
                                                                   "iron", xf=rot("X", 90), a0=-math.pi * 0.92, a1=-math.pi * 0.08, seg=8))
    return parts


def build_sword():
    """The broadsword, in the PS1 sword's frame: blade up +Y from the crossguard, grip at the origin."""
    obs = []
    root = bpy.data.objects.new("broadsword", None)
    bpy.context.scene.collection.objects.link(root)

    def piece(name, mat, fn):
        m = Mesh()
        fn(m)
        ob = m.finish("%s__%s" % (name, mat), "x", {"x": root})
        obs.append(ob)

    def blade(m):
        # diamond section with a fuller, tapering to a point
        secs = [(0.085, 0.038, 0.011), (0.3, 0.036, 0.011), (0.6, 0.033, 0.01), (0.8, 0.027, 0.009), (0.88, 0.014, 0.006), (0.905, 0.001, 0.001)]
        loft(m, secs, "steel", seg=4, e=1.0, cap0=True)
    piece("blade", "steel", blade)
    piece("fuller", "dark", lambda m: loft(m, [(0.1, 0.007, 0.0115), (0.7, 0.006, 0.0105)], "dark", seg=4, e=1.0))
    piece("crossguard", "iron", lambda m: loft(m, [(-0.122, 0.012, 0.014), (-0.1, 0.01, 0.012), (0.1, 0.01, 0.012), (0.122, 0.012, 0.014)], "iron", seg=8,
                                                xf=at(0, 0.066, 0) @ rot("Z", 90), cap0=True, cap1=True))
    piece("grip", "grip", lambda m: loft(m, [(-0.066, 0.016, 0.014), (0.0, 0.018, 0.016), (0.058, 0.016, 0.014)], "grip", seg=10))
    piece("pommel", "iron", lambda m: ellipsoid(m, (0, -0.09, 0), (0.028, 0.03, 0.02), "iron", seg=12, rings=8))
    return root, obs


# --- textures (64 px pixel art, numpy) ----------------------------------------------------------------

BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0


def wrapnoise(r, n, s):
    from scipy import ndimage
    a = ndimage.gaussian_filter(r.random((n, n)), s, mode="wrap")
    a -= a.min()
    return a / a.max()


def ramp_img(v, cols, n):
    cols = np.array(cols, dtype=float)
    t = np.clip(v, 0, 1) * (len(cols) - 1)
    th = np.tile(BAYER, (n // 4, n // 4)) - 0.5
    idx = np.clip(np.floor(t + 0.5 + th * 0.9), 0, len(cols) - 1).astype(int)
    return cols[idx].astype(np.uint8)


def textures():
    os.makedirs(OUT, exist_ok=True)
    r = np.random.default_rng(5)
    n = 64
    yy, xx = np.mgrid[0:n, 0:n]
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
    v += (wrapnoise(r, n, 6) - 0.5) * 0.2
    out["mail"] = ramp_img(v, [(22, 23, 28), (40, 42, 49), (60, 63, 71), (82, 86, 94), (108, 112, 120), (140, 144, 150)], n)

    # iron: dark hammered plate
    v = 0.45 + (wrapnoise(r, n, 8) - 0.5) * 0.4 + (wrapnoise(r, n, 1.5) - 0.5) * 0.25
    for _ in range(14):
        cy, cx = r.integers(0, n, 2)
        d = np.hypot((yy - cy + n // 2) % n - n // 2, (xx - cx + n // 2) % n - n // 2)
        v += np.exp(-(d / 3.5) ** 2) * 0.18 * np.sign(r.random() - 0.4)
    for _ in range(6):
        y0, x0 = r.integers(0, n, 2)
        for t in range(r.integers(5, 14)):
            v[(y0 + t // 3) % n, (x0 + t) % n] = 0.95
    out["iron"] = ramp_img(v, [(44, 46, 54), (64, 68, 76), (86, 90, 99), (110, 114, 122), (138, 142, 150), (172, 176, 182)], n)

    # steel: brighter, polished blade
    v = 0.6 + (wrapnoise(r, n, 10) - 0.5) * 0.4 + (xx % 16 == 0) * 0.2
    out["steel"] = ramp_img(v, [(70, 74, 82), (110, 114, 122), (150, 154, 162), (186, 190, 196), (220, 224, 228)], n)

    # leather: brown with grain and a stitched seam
    v = 0.5 + (wrapnoise(r, n, 5) - 0.5) * 0.5 + (wrapnoise(r, n, 0.8) - 0.5) * 0.35
    v[(yy % 32 == 30) & (xx % 4 < 2)] = 0.95
    v[(yy % 32 == 31)] -= 0.25
    out["leather"] = ramp_img(v, [(40, 26, 18), (62, 40, 26), (86, 56, 36), (108, 74, 48), (136, 98, 64)], n)
    out["boot"] = ramp_img(v * 0.9, [(24, 18, 14), (38, 28, 20), (56, 40, 28), (74, 54, 38), (96, 72, 50)], n)
    out["grip"] = ramp_img(((xx + yy) % 8 < 4) * 0.5 + v * 0.4, [(30, 20, 14), (56, 36, 24), (84, 56, 36), (110, 76, 50)], n)

    # dark: straps, eyes, the fuller's shadow
    out["dark"] = ramp_img(0.4 + (wrapnoise(r, n, 3) - 0.5) * 0.3, [(14, 12, 12), (26, 22, 20), (38, 32, 28)], n)

    # cloth: Emberwick's ember-red wool tabard, a soft weave
    weave = ((xx % 4 < 2) ^ (yy % 4 < 2)) * 0.12
    v = 0.5 + weave + (wrapnoise(r, n, 7) - 0.5) * 0.45 + (wrapnoise(r, n, 1) - 0.5) * 0.15
    out["cloth"] = ramp_img(v, [(52, 14, 12), (78, 22, 16), (106, 32, 20), (134, 44, 24), (164, 62, 32)], n)

    # padding: the quilted gambeson (diamond quilting)
    q = ((xx + yy) % 16 == 0) | ((xx - yy) % 16 == 0)
    v = 0.6 + (wrapnoise(r, n, 4) - 0.5) * 0.3 - q * 0.4
    out["padding"] = ramp_img(v, [(62, 54, 42), (96, 86, 66), (128, 116, 90), (156, 144, 114), (180, 170, 140)], n)

    # trousers: dark brown-grey wool
    v = 0.5 + (wrapnoise(r, n, 6) - 0.5) * 0.5 + ((yy % 3) == 0) * 0.08
    out["trousers"] = ramp_img(v, [(34, 30, 28), (50, 44, 40), (68, 60, 54), (88, 78, 70)], n)

    # skin and hair (the Guard's: skin 1, dark brown hair)
    v = 0.55 + (wrapnoise(r, n, 5) - 0.5) * 0.3
    out["skin"] = ramp_img(v, [(168, 114, 84), (194, 138, 104), (214, 160, 124), (232, 184, 148)], n)
    v = 0.5 + np.sin(xx * 1.7 + wrapnoise(r, n, 4) * 9) * 0.3 + (wrapnoise(r, n, 1) - 0.5) * 0.3
    out["hair"] = ramp_img(v, [(26, 18, 14), (44, 30, 22), (64, 44, 30), (88, 62, 42)], n)

    # brass: buckle, helm ribs
    v = 0.55 + (wrapnoise(r, n, 4) - 0.5) * 0.6
    out["brass"] = ramp_img(v, [(86, 60, 22), (130, 96, 38), (176, 136, 58), (214, 176, 90)], n)

    for k, img in out.items():
        Image.fromarray(img, "RGB").save(os.path.join(OUT, k + ".png"))

    # emblem: Emberwick's flame in a ring, gold on the red, with alpha
    s = 64
    yy, xx = np.mgrid[0:s, 0:s].astype(float)
    cx, cy = 31.5, 31.5
    d = np.hypot(xx - cx, yy - cy)
    rgba = np.zeros((s, s, 4), dtype=np.uint8)
    ring_m = (d > 25) & (d < 30)
    # a three-tongued flame (image y down: the flame points up)
    ny = (yy - 12) / 40.0
    flame = np.zeros((s, s), bool)
    for ox, w, top in ((0, 11, 0.0), (-9, 6, 0.35), (9, 6, 0.3)):
        prof = np.clip((ny - top) / (1 - top), 0, 1)
        half = w * np.sin(np.clip(prof, 0, 1) * math.pi * 0.85) ** 0.8
        flame |= (np.abs(xx - cx - ox * prof) < half) & (ny > top) & (ny < 1.0)
    inner = flame & ~(np.roll(flame, 2, 0) & np.roll(flame, -2, 0) & np.roll(flame, 2, 1) & np.roll(flame, -2, 1))
    gold = (226, 170, 60)
    dark = (40, 14, 10)
    rgba[ring_m] = (*gold, 255)
    rgba[flame] = (*gold, 255)
    rgba[flame & (ny > 0.62)] = (250, 214, 110, 255)
    rgba[inner] = (*dark, 255)
    outline = (d >= 30) & (d < 31.5)
    rgba[outline] = (*dark, 255)
    Image.fromarray(rgba, "RGBA").save(os.path.join(OUT, "emblem.png"))


# --- main ---------------------------------------------------------------------------------------------

def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def export(path):
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", export_yup=True, export_apply=True,
                              export_animations=False, export_materials="NONE", export_texcoords=True,
                              export_normals=True, use_selection=False)


def main():
    textures()

    clear()
    objs = {}
    for name, parent, off in BONES:
        e = bpy.data.objects.new(name, None)
        bpy.context.scene.collection.objects.link(e)
        if parent:
            e.parent = objs[parent]
        e.location = G(*off)
        objs[name] = e
    parts = build_guard(objs)
    tris = sum(sum(len(p.vertices) - 2 for p in ob.data.polygons) for ob in parts)
    export(os.path.join(OUT, "guard_hd.glb"))
    print("guard_hd.glb: %d pieces, %d triangles" % (len(parts), tris))

    clear()
    _, obs = build_sword()
    tris = sum(sum(len(p.vertices) - 2 for p in ob.data.polygons) for ob in obs)
    export(os.path.join(OUT, "broadsword_hd.glb"))
    print("broadsword_hd.glb: %d triangles" % tris)


if __name__ == "__main__":
    main()
