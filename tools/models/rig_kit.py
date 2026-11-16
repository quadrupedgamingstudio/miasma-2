"""Shared kit for Miasma: Rebirth's Blender-built models (run with Blender's Python module: pip install bpy).

Used by guard_hd.py, kael_hd.py, hollow_wolf_hd.py and skeleton_hd.py. Two ways to build a model:

- **Skinned** (people, the Hollow Wolf): `Rig(bones)`. Each piece is modelled in its bone's frame (like the
  old rigid pieces), then moved to the bone's place and merged into one skinned mesh per material. A piece's
  `weights` (see `ramp`) let it bend with the next bone near a joint, so elbows, knees, shoulders, hips and
  the neck deform smoothly instead of hinging. Pieces with no `weights` ride one bone rigidly (the "extras":
  helm, spaulders, emblem...). `Rig.export()` writes an Armature + meshes to .glb.
- **Rigid** (the Skeleton, whose bones must fly apart on death): `Rigid(bones)`. Each piece is its own mesh
  object on an empty named like the bone, so the old node animations still play and Actor.scatter() works.

The armature's bones all point straight up with no roll, so in Godot every bone's rest rotation is the
identity: the animations made as plain node rotations (player.glb's walk/run/idle, the battle animations
built in scripts/actor.gd) play on the Skeleton3D unchanged. Keep it that way for new rigs.

Coordinates are written in Godot's frame (Y up, the model faces -Z, +X is its right hand), turned into
Blender's (Z up) by G(); the glTF exporter turns them back. Each mesh is named "<prefix>_<material>__<material>";
Actor gives it assets/models/hd/<material>.png. Texture UVs are in real-world units (a tile = TILE[material]
metres) so every piece shares one texel density and the pixel art stays crisp up close.
"""
import math
import os

import bpy  # noqa: I001  (bpy first: it makes bmesh and mathutils importable)
import bmesh
import numpy as np
from mathutils import Matrix, Vector

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT = os.path.join(ROOT, "assets", "models", "hd")

SEG = 16  # sides on round pieces

# metres per texture tile, per material (each model script adds its own)
TILE = {"mail": 0.11, "iron": 0.3, "leather": 0.22, "boot": 0.22, "cloth": 0.3, "padding": 0.18,
        "trousers": 0.25, "skin": 0.2, "hair": 0.12, "brass": 0.1, "emblem": 1.0, "dark": 0.2,
        "steel": 0.3, "grip": 0.08}

# the people's skeleton: bone -> (parent, local offset), copied from Miasma's player.glb
HUMAN_BONES = [
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


def world_positions(bones):
    pos = {}
    for name, parent, off in bones:
        pos[name] = (pos[parent] if parent else Vector((0, 0, 0))) + Vector(off)
    return pos


# --- weights ------------------------------------------------------------------------------------------

def _smooth(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def ramp(keys, axis=1):
    """Skin weights that change along one axis of the piece's bone frame (default Y, along a limb).
    keys: [(coordinate, {bone: weight}), ...]; between two keys the weights ease from one to the other,
    past the ends they hold. A bone missing from a key counts as 0 there."""
    keys = sorted(keys, key=lambda k: k[0])

    def fn(p):
        c = p[axis]
        if c <= keys[0][0]:
            return dict(keys[0][1])
        if c >= keys[-1][0]:
            return dict(keys[-1][1])
        for (c0, w0), (c1, w1) in zip(keys, keys[1:]):
            if c0 <= c <= c1:
                t = _smooth((c - c0) / max(c1 - c0, 1e-9))
                out = {}
                for b in set(w0) | set(w1):
                    out[b] = w0.get(b, 0.0) * (1 - t) + w1.get(b, 0.0) * t
                return out
        return dict(keys[-1][1])
    return fn


# --- mesh building ----------------------------------------------------------------------------------

class Mesh:
    """Collects quads/triangles with UVs, in one bone's frame (Godot coordinates)."""

    def __init__(self):
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("UVMap")

    def face(self, pts, uvs, smooth=True):
        vs = [self.bm.verts.new(Vector(p)) for p in pts]
        try:
            f = self.bm.faces.new(vs)
        except ValueError:
            return None
        f.smooth = smooth
        for loop, uv in zip(f.loops, uvs):
            loop[self.uv].uv = uv
        return f


def superellipse(a, rx, rz, e):
    c, s = math.cos(a), math.sin(a)
    x = rx * math.copysign(abs(c) ** (2.0 / e), c)
    z = rz * math.copysign(abs(s) ** (2.0 / e), s)
    return x, z


def loft(m, sections, mat, xf=None, a0=0.0, a1=2 * math.pi, cap0=False, cap1=False, seg=SEG, e=2.0, keep=None):
    """A tube through cross-sections [(y, rx, rz, cx, cz), ...] (cx, cz optional) in a frame where
    the tube runs along +Y; xf (Matrix, Godot space) places it. a0..a1 = the part of the circle to
    build (a partial tube = a plate). Angle 0 = +X, pi/2 = +Z (the back), -pi/2 = -Z (the front).
    keep(k, a) -> bool drops the quad between sections k and k+1 at angle a (a hole: the wolf's ribs)."""
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
    vs = [0.0]
    for k in range(1, len(rings)):
        d = sum((rings[k][i] - rings[k - 1][i]).length for i in range(seg + 1)) / (seg + 1)
        vs.append(vs[-1] + d)
    for k in range(len(rings) - 1):
        us0 = [0.0]
        for i in range(1, seg + 1):
            us0.append(us0[-1] + (rings[k][i] - rings[k][i - 1]).length)
        for i in range(seg):
            if keep and not keep(k, a0 + (a1 - a0) * (i + 0.5) / seg):
                continue
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


def ellipsoid(m, center, radii, mat, seg=SEG, rings=10, keep=None, xf=None):
    """An ellipsoid; keep(x, y, z) -> bool drops faces whose centre fails it (cut shapes: beard)."""
    xf = xf or Matrix.Identity(4)
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
            m.face([tuple(xf @ Vector(v)) for v in q], uv)


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


def card(m, corners, mat, uv=((0, 0), (1, 0), (1, 1), (0, 1))):
    """One flat quad (alpha cards: fur tufts, rags). Shown from both sides by the material."""
    m.face([tuple(c) for c in corners], list(uv), smooth=False)


def tube(m, pts, radius, mat, seg=6, cap=True):
    """A round tube along a polyline (ribs, claws, teeth, tail hairs); radius: a number or one per point."""
    tile = TILE[mat]
    pts = [Vector(p) for p in pts]
    rs = radius if isinstance(radius, (list, tuple)) else [radius] * len(pts)
    rings = []
    for i, p in enumerate(pts):
        d = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        up = Vector((0, 1, 0)) if abs(d.y) < 0.9 else Vector((1, 0, 0))
        u = d.cross(up).normalized()
        v = d.cross(u).normalized()
        rings.append([p + (u * math.cos(2 * math.pi * j / seg) + v * math.sin(2 * math.pi * j / seg)) * rs[i] for j in range(seg)])
    acc = 0.0
    for i in range(len(rings) - 1):
        l = (pts[i + 1] - pts[i]).length
        for j in range(seg):
            j2 = (j + 1) % seg
            m.face([tuple(rings[i][j]), tuple(rings[i][j2]), tuple(rings[i + 1][j2]), tuple(rings[i + 1][j])],
                   [(j / seg * 0.3, acc / tile), ((j + 1) / seg * 0.3, acc / tile), ((j + 1) / seg * 0.3, (acc + l) / tile), (j / seg * 0.3, (acc + l) / tile)])
        acc += l
    if cap and rs[-1] > 1e-4:
        c = pts[-1]
        for j in range(seg):
            m.face([tuple(c), tuple(rings[-1][j]), tuple(rings[-1][(j + 1) % seg])], [(0, 0), (0.1, 0), (0.1, 0.1)], smooth=False)


def along(p0, p1):
    """A frame at p0 whose +Y points at p1 (for lofts along a limb). Returns (Matrix, length)."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    q = Vector((0, 1, 0)).rotation_difference(d.normalized())
    return Matrix.Translation(p0) @ q.to_matrix().to_4x4(), d.length


def rot(axis, deg):
    return Matrix.Rotation(math.radians(deg), 4, axis)


def at(x, y, z):
    return Matrix.Translation((x, y, z))


# --- scene --------------------------------------------------------------------------------------------

def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def export(path, animations=False):
    kw = dict(filepath=path, export_format="GLB", export_yup=True, export_apply=False,
              export_materials="NONE", export_texcoords=True, export_normals=True, use_selection=False,
              export_animations=animations)
    if animations:
        kw.update(export_animation_mode="ACTIONS", export_force_sampling=True, export_frame_step=1,
                  export_optimize_animation_size=False, export_anim_single_armature=True)
    bpy.ops.export_scene.gltf(**kw)


class Rig:
    """A skinned model: an armature (bones pointing up, no roll) and one skinned mesh per material."""

    def __init__(self, bones, prefix):
        self.bones = bones
        self.names = [b[0] for b in bones]
        self.pos = world_positions(bones)
        self.prefix = prefix
        self.mats = {}   # material -> bmesh (world coords, Godot frame) with uv + deform layers
        self.tris = 0

    def _bm(self, mat):
        if mat not in self.mats:
            bm = bmesh.new()
            bm.loops.layers.uv.new("UVMap")
            bm.verts.layers.deform.verify()
            self.mats[mat] = bm
        return self.mats[mat]

    def piece(self, name, bone, mat, fn, weights=None):
        """Builds fn(m) in `bone`'s frame and merges it into the material's skinned mesh.
        weights: None (rigid on `bone`) or a function of the local point -> {bone: weight}."""
        m = Mesh()
        fn(m)
        bmesh.ops.remove_doubles(m.bm, verts=m.bm.verts, dist=1e-5)
        dst = self._bm(mat)
        uv_src = m.uv
        uv_dst = dst.loops.layers.uv["UVMap"]
        dl = dst.verts.layers.deform.active
        off = self.pos[bone]
        vmap = {}
        for v in m.bm.verts:
            p = v.co
            nv = dst.verts.new(G(*(p + off)))
            w = weights(p) if weights else {bone: 1.0}
            total = sum(x for x in w.values() if x > 1e-4) or 1.0
            for b, x in w.items():
                if x > 1e-4:
                    nv[dl][self.names.index(b)] = x / total
            vmap[v] = nv
        for f in m.bm.faces:
            try:
                nf = dst.faces.new([vmap[v] for v in f.verts])
            except ValueError:
                continue
            nf.smooth = f.smooth
            for ls, ld in zip(f.loops, nf.loops):
                ld[uv_dst].uv = ls[uv_src].uv
            self.tris += len(f.verts) - 2
        m.bm.free()

    def build(self):
        """Makes the armature and the meshes in the Blender scene. Returns the armature object."""
        arm = bpy.data.armatures.new(self.prefix + "_rig")
        ob = bpy.data.objects.new(self.prefix + "_rig", arm)
        bpy.context.scene.collection.objects.link(ob)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.mode_set(mode="EDIT")
        ebs = {}
        for name, parent, _ in self.bones:
            eb = arm.edit_bones.new(name)
            eb.head = G(*self.pos[name])
            eb.tail = G(*(self.pos[name] + Vector((0, 0.05, 0))))
            eb.roll = 0.0
            eb.use_deform = True
            if parent:
                eb.parent = ebs[parent]
            ebs[name] = eb
        bpy.ops.object.mode_set(mode="OBJECT")
        for mat, bm in self.mats.items():
            name = "%s_%s__%s" % (self.prefix, mat, mat)
            me = bpy.data.meshes.new(name)
            bm.to_mesh(me)
            bm.free()
            if mat.endswith("_fur"):
                # tufts are lit as if facing up, from both sides, so they read as fur and not dark slats
                me.normals_split_custom_set_from_vertices([(0.0, 0.0, 1.0)] * len(me.vertices))
            mo = bpy.data.objects.new(name, me)
            bpy.context.scene.collection.objects.link(mo)
            for b in self.names:
                mo.vertex_groups.new(name=b)
            mo.parent = ob
            mod = mo.modifiers.new("Armature", "ARMATURE")
            mod.object = ob
        self.mats = {}
        return ob


def quat_yxz(deg):
    """Godot's Basis.from_euler(e, EULER_ORDER_YXZ) as a quaternion (Z turn first, then X, then Y)."""
    from mathutils import Quaternion
    x, y, z = (math.radians(a) for a in deg)
    return Quaternion((0, 1, 0), y) @ Quaternion((1, 0, 0), x) @ Quaternion((0, 0, 1), z)


def add_action(arm_ob, name, keys, fps=30, loc_bones=("root",)):
    """One animation, keyed like scripts/actor.gd's pose animations but in Blender:
    keys = [(seconds, {bone: (x, y, z) euler degrees, "bone@": (x, y, z) offset in metres}), ...]. A bone
    left out of a key keeps its last value. The rig's bone frames are Godot's axes (bones point up, no
    roll), so the numbers mean the same as in Godot. Every bone is keyed (rest unless given), and the
    offsets of loc_bones, so one animation never leaves another's pose behind. Pushed to its own NLA track
    so the exporter takes it."""
    ad = arm_ob.animation_data or arm_ob.animation_data_create()
    act = bpy.data.actions.new(name)
    ad.action = act
    bpy.context.scene.render.fps = fps
    last = {pb.name: (0, 0, 0) for pb in arm_ob.pose.bones}
    last.update({b + "@": (0, 0, 0) for b in loc_bones})
    for t, pose in keys:
        f = 1 + round(t * fps)
        last.update({k.replace("__", "@"): v for k, v in pose.items()})
        for b, val in last.items():
            if b.endswith("@"):
                pb = arm_ob.pose.bones[b[:-1]]
                pb.location = Vector(val)
                pb.keyframe_insert("location", frame=f)
            else:
                pb = arm_ob.pose.bones[b]
                pb.rotation_mode = "QUATERNION"
                pb.rotation_quaternion = quat_yxz(val)
                pb.keyframe_insert("rotation_quaternion", frame=f)
    for pb in arm_ob.pose.bones:   # back to rest so the next action starts clean
        pb.location = Vector((0, 0, 0))
        pb.rotation_quaternion = (1, 0, 0, 0)
    tr = ad.nla_tracks.new()
    tr.name = name
    tr.strips.new(name, 1, act)
    ad.action = None
    return act


class Rigid:
    """A model of rigid pieces on empties named like the bones (the Skeleton: its bones fly apart)."""

    def __init__(self, bones):
        self.objs = {}
        self.tris = 0
        self.count = 0
        for name, parent, off in bones:
            e = bpy.data.objects.new(name, None)
            bpy.context.scene.collection.objects.link(e)
            if parent:
                e.parent = self.objs[parent]
            e.location = G(*off)
            self.objs[name] = e

    def piece(self, name, bone, mat, fn):
        m = Mesh()
        fn(m)
        bmesh.ops.remove_doubles(m.bm, verts=m.bm.verts, dist=1e-5)
        for v in m.bm.verts:
            v.co = G(*v.co)
        self.tris += sum(len(f.verts) - 2 for f in m.bm.faces)
        self.count += 1
        nm = "%s__%s" % (name, mat)
        me = bpy.data.meshes.new(nm)
        m.bm.to_mesh(me)
        m.bm.free()
        ob = bpy.data.objects.new(nm, me)
        bpy.context.scene.collection.objects.link(ob)
        ob.parent = self.objs[bone]
        ob.matrix_parent_inverse = Matrix.Identity(4)
        return ob


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


def save_png(name, img):
    from PIL import Image
    os.makedirs(OUT, exist_ok=True)
    Image.fromarray(img, "RGBA" if img.shape[2] == 4 else "RGB").save(os.path.join(OUT, name + ".png"))
