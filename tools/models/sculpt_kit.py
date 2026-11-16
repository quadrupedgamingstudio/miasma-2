"""Second-pass model kit (Cody 2026-11-15: "proper" Blender models that keep Miasma's vibe).

A model is still written as shapes in bone frames (rig_kit.py's loft / ellipsoid / box and the shapes below),
but they are no longer what ships. The pipeline (`Sculpt.finish()`):

1. **Forms** (closed shapes, rig `F`) and **shells** (open plates, rig `S`, thickened) are fused into one
   continuous sculpt with a voxel remesh: no seams, no shapes poking through each other.
2. **Retopology:** collapse decimation down to ~target_tris, relaxed, then shrink-wrapped back onto the sculpt.
3. **Skin weights** are carried over from the forms (each form keeps the `ramp` weights it was made with):
   nearest form points facing the same way, blended, smoothed over the mesh, at most 4 bones a vertex.
4. **UVs:** one atlas; the head gets more texels than the body (`density`), then everything is packed.
5. **Bakes** (Cycles): which material shows where (the forms plus **decals**, rig `D`: straps, laces, eyes,
   brows, snapped onto the sculpt), ambient occlusion, the sculpt's cavities, normals and positions.
6. **Pixel painting** (numpy): each texel takes its material's colour ramp, shaded by AO / cavity / light from
   above, with a per-material pattern (leather blotches, hair strands, cloth folds), Bayer-dithered to the ramp,
   then a dark contact line where one layer covers another and stitching where leather meets cloth.

Writes `assets/models/hd/<name>_hd.glb` (one skinned mesh `<name>_body__<name>_atlas`, the rig with
player.glb's bone names, every rest rotation the identity) and `assets/models/hd/<name>_atlas.png`; saves
`tools/models/blend/<name>.blend` (the sculpt, the sources and the result, for edits in Blender) and
`tools/models/maps/<name>.npz` (the baked maps, so the colours can be re-painted without re-baking).
"""
import math
import os

import bpy  # noqa: I001
import bmesh
import numpy as np
from mathutils import Vector, kdtree

import rig_kit as K

BLEND_DIR = os.path.join(K.ROOT, "tools", "models", "blend")
MAP_DIR = os.path.join(K.ROOT, "tools", "models", "maps")
BAYER8 = (np.array([[0, 32, 8, 40, 2, 34, 10, 42], [48, 16, 56, 24, 50, 18, 58, 26],
                    [12, 44, 4, 36, 14, 46, 6, 38], [60, 28, 52, 20, 62, 30, 54, 22],
                    [3, 35, 11, 43, 1, 33, 9, 41], [51, 19, 59, 27, 49, 17, 57, 25],
                    [15, 47, 7, 39, 13, 45, 5, 37], [63, 31, 55, 23, 61, 29, 53, 21]]) + 0.5) / 64.0 - 0.5


# --- extra shapes ---------------------------------------------------------------------------------------

def strand(m, pts, nrms, widths, thicks, seg=8):
    """A closed, flattened tube along pts (a hair clump, a strap with body): width across, thickness along nrms."""
    pts = [Vector(p) for p in pts]
    nrms = [Vector(n).normalized() for n in nrms]
    rings = []
    for i, p in enumerate(pts):
        d = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        b = d.cross(nrms[i]).normalized()
        n = b.cross(d).normalized()
        rings.append([p + b * math.cos(2 * math.pi * j / seg) * widths[i] + n * math.sin(2 * math.pi * j / seg) * thicks[i]
                      for j in range(seg)])
    for i in range(len(rings) - 1):
        for j in range(seg):
            j2 = (j + 1) % seg
            m.face([tuple(rings[i][j]), tuple(rings[i][j2]), tuple(rings[i + 1][j2]), tuple(rings[i + 1][j])],
                   [(0, 0), (1, 0), (1, 1), (0, 1)])
    for k, flip in ((0, True), (len(rings) - 1, False)):
        c = pts[k]
        for j in range(seg):
            a, b = rings[k][j], rings[k][(j + 1) % seg]
            tri = [c, b, a] if not flip else [c, a, b]
            m.face([tuple(q) for q in tri], [(0, 0), (1, 0), (1, 1)], smooth=False)


# --- helpers --------------------------------------------------------------------------------------------

def _link(ob):
    bpy.context.scene.collection.objects.link(ob)
    return ob


def _activate(ob):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)


def _evaluated_mesh(ob, name):
    dg = bpy.context.evaluated_depsgraph_get()
    return bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)


def _meshes_of(arm):
    return [o for o in bpy.data.objects if o.parent == arm and o.type == "MESH"]


def _drop_rig(arm):
    """Keeps a rig's meshes as plain objects in world space (their verts already are) and deletes the rig."""
    obs = _meshes_of(arm)
    for o in obs:
        o.parent = None
        for md in list(o.modifiers):
            o.modifiers.remove(md)
    bpy.data.objects.remove(arm)
    return obs


def _key_of(ob):
    return ob.name.split("__")[-1]


# --- 3D value noise (patterns painted from baked positions) ------------------------------------------

ROT_A = np.array([[0.36, 0.48, -0.8], [-0.8, 0.6, 0.0], [0.48, 0.64, 0.6]])
ROT_B = np.array([[0.6, -0.8, 0.0], [0.64, 0.48, -0.6], [0.48, 0.36, 0.8]])


def noise3(p, cell, seed=0):
    """Smooth noise in [0, 1] at points p (N x 3), features about `cell` metres: two value-noise layers on
    turned axes, so no lattice shows."""
    return (_vnoise(p @ ROT_A, cell, seed) + _vnoise(p @ ROT_B, cell * 0.97, seed + 101)) * 0.5


def _vnoise(p, cell, seed):
    q = p / cell
    i = np.floor(q).astype(np.int64)
    f = q - i
    f = f * f * (3 - 2 * f)

    def h(dx, dy, dz):
        x = (i[:, 0] + dx) * 73856093 ^ (i[:, 1] + dy) * 19349663 ^ (i[:, 2] + dz) * 83492791 ^ seed * 2654435761
        x = (x ^ (x >> 13)) * 1274126177
        return ((x ^ (x >> 16)) & 0xFFFF) / 65535.0
    out = 0.0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (f[:, 0] if dx else 1 - f[:, 0]) * (f[:, 1] if dy else 1 - f[:, 1]) * (f[:, 2] if dz else 1 - f[:, 2])
                out = out + w * h(dx, dy, dz)
    return out


# --- the pipeline -----------------------------------------------------------------------------------------

class Sculpt:
    """name: the model id ("kael"). After building into self.F, self.S and self.D (rig_kit.Rig objects on
    the same bones: forms, shells, decals), call finish()."""

    def __init__(self, name, bones, voxel=0.005, target_tris=7000, atlas=256):
        self.name = name
        self.bones = bones
        self.voxel = voxel
        self.target_tris = target_tris
        self.atlas = atlas
        self.F = K.Rig(bones, name + "F")
        self.S = K.Rig(bones, name + "S")
        self.D = K.Rig(bones, name + "D")
        self.palettes = {}    # key -> [(r, g, b), ...] dark to light
        self.layer = {}       # key -> how high it sits (a higher layer covering a lower one gets a contact line)
        self.style = {}       # key -> dict(base, ao, cav, up, noise, pattern, cell)
        self.density = []     # [(fn(vertex weights dict, position) -> bool, texel scale)] first match wins
        self.decal_lift = {}  # key -> metres a decal sits off the sculpt (higher = drawn over lower)
        self.stitch = []      # [(key_on, key_next_to)] dashed light stitches on key_on along key_next_to
        self.detail = None    # fn(Blender position) -> 0..1: where decimation keeps more triangles (the face)
        self.detail_boost = 3.5   # how much denser the detailed part stays
        self.smooth_region = None  # fn(Blender position) -> 0..1: smoothed on the sculpt before retopology

    # 1. forms + shells -> one continuous sculpt
    def _fuse(self, form_obs, shell_obs):
        for o in shell_obs:
            sm = o.modifiers.new("Solid", "SOLIDIFY")
            sm.thickness = 0.008
            sm.offset = 0.0
            sm.use_even_offset = True
        dg = bpy.context.evaluated_depsgraph_get()
        bm = bmesh.new()
        for o in form_obs + shell_obs:
            bm.from_object(o, dg)
        me = bpy.data.meshes.new(self.name + "_sculpt_src")
        bm.to_mesh(me)
        bm.free()
        src = _link(bpy.data.objects.new(self.name + "_sculpt_src", me))
        rm = src.modifiers.new("Remesh", "REMESH")
        rm.mode = "VOXEL"
        rm.voxel_size = self.voxel
        rm.adaptivity = 0.0
        hme = _evaluated_mesh(src, self.name + "_sculpt")
        bpy.data.objects.remove(src)
        bpy.data.meshes.remove(me)
        # drop voxel bubbles and crumbs (Quadriflow refuses a mesh with them)
        bm = bmesh.new()
        bm.from_mesh(hme)
        seen, comps = set(), []
        for f in bm.faces:
            if f in seen:
                continue
            st, comp = [f], []
            seen.add(f)
            while st:
                g = st.pop()
                comp.append(g)
                for e in g.edges:
                    for h in e.link_faces:
                        if h not in seen:
                            seen.add(h)
                            st.append(h)
            comps.append(comp)
        big = max(len(c) for c in comps)
        drop = [f for c in comps if len(c) < big * 0.01 for f in c]
        bmesh.ops.delete(bm, geom=drop, context="FACES")
        bm.to_mesh(hme)
        bm.free()
        high = _link(bpy.data.objects.new(self.name + "_sculpt", hme))
        for p in hme.polygons:
            p.use_smooth = True
        if self.smooth_region:
            vg = high.vertex_groups.new(name="smooth")
            for v in hme.vertices:
                w = self.smooth_region(v.co)
                if w > 0:
                    vg.add([v.index], w, "REPLACE")
            sm = high.modifiers.new("Smooth", "LAPLACIANSMOOTH")
            sm.vertex_group = "smooth"
            sm.iterations = 6
            sm.lambda_factor = 1.0
            sm.use_volume_preserve = True
            _activate(high)
            bpy.ops.object.modifier_apply(modifier="Smooth")
            high.vertex_groups.remove(high.vertex_groups["smooth"])
        for o in shell_obs:
            o.modifiers.remove(o.modifiers["Solid"])
        print("  sculpt: %d faces" % len(hme.polygons))
        return high

    # 2. retopology
    def _retopo(self, high):
        me = high.data.copy()
        nm = self.name + "_body__" + self.name + "_atlas"
        me.name = nm
        low = _link(bpy.data.objects.new(nm, me))
        _activate(low)
        # Quadriflow would give cleaner quads, but Blender 5.3's refuses every voxel-remeshed mesh ("needs to be
        # manifold", even a remeshed sphere), so: collapse decimation, which keeps the forms well at this count
        # with `detail`: decimate everything to detail_boost x the target first, then again with the detailed
        # part held, so it keeps that density (Blender's weighted collapse is all-or-nothing, so two passes)
        tris = lambda: sum(len(p.vertices) - 2 for p in low.data.polygons)  # noqa: E731
        passes = [(self.target_tris * self.detail_boost, False), (self.target_tris, True)] if self.detail else [(self.target_tris, False)]
        for goal, hold in passes:
            dm = low.modifiers.new("Dec", "DECIMATE")
            dm.decimate_type = "COLLAPSE"
            dm.use_collapse_triangulate = True
            if hold:
                vg = low.vertex_groups.new(name="detail")
                for v in low.data.vertices:
                    if self.detail(v.co) > 0:
                        vg.add([v.index], 1.0, "REPLACE")
                dm.vertex_group = "detail"
                dm.invert_vertex_group = True
            dm.ratio = goal / max(1, tris())
            bpy.ops.object.modifier_apply(modifier="Dec")
        if self.detail:
            low.vertex_groups.remove(low.vertex_groups["detail"])
            n = sum(1 for p in low.data.polygons if self.detail(p.center) > 0)
            print("  face triangles: %d" % n)
        sm = low.modifiers.new("Relax", "SMOOTH")
        sm.factor = 0.35
        sm.iterations = 2
        bpy.ops.object.modifier_apply(modifier="Relax")
        sw = low.modifiers.new("Wrap", "SHRINKWRAP")
        sw.target = high
        sw.wrap_method = "NEAREST_SURFACEPOINT"
        bpy.ops.object.modifier_apply(modifier="Wrap")
        for p in low.data.polygons:
            p.use_smooth = True
        print("  low: %d faces, %d tris" % (len(low.data.polygons), sum(len(p.vertices) - 2 for p in low.data.polygons)))
        return low

    # 3. weights from the forms: each vertex takes the weights of the form surface it lies on (the nearest
    # point on every form, the closest ones within a few mm blended), read off that face's corners
    def _weights(self, low, sources):
        from mathutils.bvhtree import BVHTree
        names = [b[0] for b in self.bones]
        dg = bpy.context.evaluated_depsgraph_get()
        srcs = []
        for o in sources:
            me = o.data
            gi = {g.index: g.name for g in o.vertex_groups}
            vw = [{gi[g.group]: g.weight for g in v.groups if g.weight > 1e-4} for v in me.vertices]
            tree = BVHTree.FromPolygons([v.co for v in me.vertices], [list(p.vertices) for p in me.polygons])
            srcs.append((tree, me, vw))
        me = low.data
        out = []
        for v in me.vertices:
            hits = []
            for tree, sme, vw in srcs:
                loc, nr, fi, d = tree.find_nearest(v.co)
                if loc is not None:
                    hits.append((d, loc, fi, sme, vw))
            dmin = min(h[0] for h in hits)
            acc = {}
            for d, loc, fi, sme, vw in hits:
                if d > dmin + 0.004:
                    continue
                poly = sme.polygons[fi]
                ks = []
                for vi in poly.vertices:
                    k = 1.0 / ((sme.vertices[vi].co - loc).length + 1e-4)
                    ks.append((k, vi))
                tk = sum(k for k, _ in ks)
                for k, vi in ks:
                    for bn, x in vw[vi].items():
                        acc[bn] = acc.get(bn, 0.0) + x * k / tk
            out.append(acc)
        # smooth over the mesh's edges
        nb = [[] for _ in me.vertices]
        for e in me.edges:
            a, b = e.vertices
            nb[a].append(b)
            nb[b].append(a)
        for _ in range(2):
            nxt = []
            for i, w in enumerate(out):
                t = sum(w.values()) or 1.0
                acc = {b: x / t * 0.5 for b, x in w.items()}
                for j in nb[i]:
                    tj = sum(out[j].values()) or 1.0
                    for b, x in out[j].items():
                        acc[b] = acc.get(b, 0.0) + x / tj * 0.5 / max(1, len(nb[i]))
                nxt.append(acc)
            out = nxt
        for b in names:
            low.vertex_groups.new(name=b)
        for i, w in enumerate(out):
            top = sorted(w.items(), key=lambda kv: -kv[1])[:4]
            t = sum(x for _, x in top) or 1.0
            for b, x in top:
                if x / t > 0.01:
                    low.vertex_groups[b].add([i], x / t, "REPLACE")

    # 4. UVs: one chart per body part (seams where parts meet), each tube cut open down its back or inside

    def _regions(self):
        """Region of each bone and how its chart is cut open: (from bone, to bone, cut side in Godot axes)."""
        reg, cut = {}, {}
        for name, parent, _ in self.bones:
            reg[name] = name
        for b in ("neck", "chest", "spine"):
            reg[b] = "torso"
        reg["root"] = "hips"
        cut["torso"] = ("hips", "neck", (0, 0, 1))
        cut["hips"] = ("hips", "spine", (0, 0, 1))
        cut["head"] = ("neck", "head", (0, 0, 1))
        kids = {}
        for name, parent, _ in self.bones:
            if parent:
                kids.setdefault(parent, name)
        for name, parent, off in self.bones:
            if name.startswith(("arm_", "forearm_", "thigh_", "shin_")) and name in kids:
                side = 1 if name.endswith("_r") else -1
                cut[name] = (name, kids[name], (-side, 0, 0))   # the inner side
        return reg, cut

    def _unwrap(self, low):
        me = low.data
        reg_of, cuts = self._regions()
        gi = {g.index: g.name for g in low.vertex_groups}
        pos = {b: K.G(*self.F.pos[b]) for b in self.F.names}
        region, side, scale_of = [], [], []
        for p in me.polygons:
            w = {}
            for vi in p.vertices:
                for g in me.vertices[vi].groups:
                    w[gi[g.group]] = w.get(gi[g.group], 0.0) + g.weight
            bone = max(w, key=w.get) if w else "hips"
            r = reg_of.get(bone, bone)
            region.append(r)
            sd = 0
            if r in cuts:
                b0, b1, cd = cuts[r]
                o, ax = pos[b0], (pos[b1] - pos[b0]).normalized()
                cdir = K.G(*cd)
                cdir = (cdir - ax * cdir.dot(ax)).normalized()
                bdir = ax.cross(cdir)
                v = p.center - o
                th = math.atan2(v.dot(bdir), v.dot(cdir))
                if abs(th) < math.pi / 2:
                    sd = 1 if th > 0 else -1
            side.append(sd)
            sc = 1.0
            for fn, s in self.density:
                if fn(w, p.center):
                    sc = s
                    break
            scale_of.append(sc)
        for e in me.edges:
            e.use_seam = False
        fe = {}
        for p in me.polygons:
            for ek in p.edge_keys:
                fe.setdefault(ek, []).append(p.index)
        ekey = {e.key: e for e in me.edges}
        for ek, fs in fe.items():
            if len(fs) != 2:
                continue
            a, b = fs
            if region[a] != region[b] or (side[a] * side[b] < 0):
                ekey[ek].use_seam = True
        _activate(low)
        if not me.uv_layers:
            me.uv_layers.new(name="UVMap")
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.unwrap(method="ANGLE_BASED", fill_holes=True, correct_aspect=True, margin=0.0)
        bpy.ops.object.mode_set(mode="OBJECT")
        # the same texel density everywhere, times the part's density scale (the face gets more)
        uv = me.uv_layers.active.data
        groups = {}
        for p in me.polygons:
            groups.setdefault((region[p.index], scale_of[p.index]), []).append(p.index)
        for gk, (key, faces) in enumerate(groups.items()):
            a3 = auv = 0.0
            for i in faces:
                p = me.polygons[i]
                a3 += p.area
                co = [uv[k].uv for k in p.loop_indices]
                for j in range(1, len(co) - 1):
                    auv += abs((co[j] - co[0]).cross(co[j + 1] - co[0])) * 0.5
            k = math.sqrt(a3 / max(auv, 1e-12)) * key[1]
            for i in faces:
                for li in me.polygons[i].loop_indices:
                    uv[li].uv = uv[li].uv * k + Vector((gk * 3.0, 0))
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.select_all(action="SELECT")
        bpy.ops.uv.pack_islands(rotate=True, scale=True, margin_method="FRACTION", margin=3.0 / self.atlas)
        bpy.ops.object.mode_set(mode="OBJECT")
        print("  uv: %d charts" % len(groups))

    # 5. bakes
    def _emit_mat(self, name, color=None, geo=None):
        mt = bpy.data.materials.new(name)
        mt.use_nodes = True
        nt = mt.node_tree
        nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        em = nt.nodes.new("ShaderNodeEmission")
        nt.links.new(em.outputs[0], out.inputs[0])
        if color is not None:
            em.inputs[0].default_value = (*color, 1.0)
        if geo:
            g = nt.nodes.new("ShaderNodeNewGeometry")
            if geo == "pointiness":
                nt.links.new(g.outputs["Pointiness"], em.inputs[0])
            elif geo == "position":
                nt.links.new(g.outputs["Position"], em.inputs[0])
        return mt

    def _target(self, low, img):
        mt = low.data.materials[0] if low.data.materials else None
        if mt is None:
            mt = bpy.data.materials.new(self.name + "_bake")
            mt.use_nodes = True
            low.data.materials.append(mt)
        nt = mt.node_tree
        node = nt.nodes.get("Target") or nt.nodes.new("ShaderNodeTexImage")
        node.name = "Target"
        node.image = img
        nt.nodes.active = node
        return mt

    def _bake(self, low, kind, sources=None, own=None, margin=4):
        img = bpy.data.images.new("%s_%s" % (self.name, kind), self.atlas, self.atlas, float_buffer=True, alpha=False)
        mt = self._target(low, img)
        nt = mt.node_tree
        for n in list(nt.nodes):
            if n.name != "Target":
                nt.nodes.remove(n)
        if own is not None:   # the low mesh bakes its own emission ("position" or "white")
            out = nt.nodes.new("ShaderNodeOutputMaterial")
            em = nt.nodes.new("ShaderNodeEmission")
            nt.links.new(em.outputs[0], out.inputs[0])
            g = nt.nodes.new("ShaderNodeNewGeometry")
            if own == "position":
                nt.links.new(g.outputs["Position"], em.inputs[0])
            elif own == "white":
                em.inputs[0].default_value = (1, 1, 1, 1)
        else:
            out = nt.nodes.new("ShaderNodeOutputMaterial")
            bs = nt.nodes.new("ShaderNodeBsdfDiffuse")
            nt.links.new(bs.outputs[0], out.inputs[0])
        nt.nodes.active = nt.nodes["Target"]
        sc = bpy.context.scene
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
            o.hide_render = True
        low.hide_render = False
        if sources:
            for o in sources:
                o.hide_render = False
                o.select_set(True)
        low.select_set(True)
        bpy.context.view_layer.objects.active = low
        bk = sc.render.bake
        bk.margin = margin
        bk.margin_type = "EXTEND"
        kw = dict(margin=margin, use_clear=True)
        if kind in ("id", "cavity"):
            kw.update(type="EMIT", use_selected_to_active=True, cage_extrusion=0.008, max_ray_distance=0.03)
            sc.cycles.samples = 1
        elif kind == "ao":
            kw.update(type="AO", use_selected_to_active=False)
            sc.cycles.samples = 96
        elif kind == "normal":
            kw.update(type="NORMAL", normal_space="OBJECT", use_selected_to_active=False)
            sc.cycles.samples = 1
        else:
            kw.update(type="EMIT", use_selected_to_active=False)
            sc.cycles.samples = 1
        bpy.ops.object.bake(**kw)
        a = np.array(img.pixels[:], dtype=np.float32).reshape(self.atlas, self.atlas, 4)[:, :, :3]
        return a

    # 6. pixel painting
    def paint(self, maps, seed=5):
        keys = maps["keys"]
        idm, mask, ao, cav, nrm, pos = maps["id"], maps["mask"], maps["ao"], maps["cav"], maps["nrm"], maps["pos"]
        n = self.atlas
        rng = np.random.default_rng(seed)
        yy, xx = np.mgrid[0:n, 0:n]
        bay = BAYER8[yy % 8, xx % 8]
        flat = pos.reshape(-1, 3)
        cav_n = np.clip((cav - np.median(cav[mask])) * 6.0, -1, 1)
        img = np.zeros((n, n, 3), np.uint8)
        idx_map = np.zeros((n, n), np.int32)
        for ki, key in enumerate(keys):
            sel = idm == ki
            if not sel.any():
                continue
            st = dict(base=0.55, ao=1.1, cav=0.35, up=0.18, noise=0.08, pattern=None, cell=0.03, dither=0.55)
            st.update(self.style.get(key, {}))
            v = (st["base"] + st["ao"] * (ao - 0.82) + st["cav"] * cav_n + st["up"] * nrm[:, :, 2])
            pn = noise3(flat, st["cell"], seed + ki).reshape(n, n)
            v = v + (pn - 0.5) * 2 * st["noise"]
            pat = st["pattern"]
            if pat is not None:
                v = v + pat(pos, nrm, rng).reshape(n, n)
            cols = self.palettes[key]
            t = np.clip(v, 0, 1) * (len(cols) - 1)
            ix = np.clip(np.floor(t + 0.5 + bay * st["dither"]), 0, len(cols) - 1).astype(np.int32)
            idx_map[sel] = ix[sel]
        # layers: a texel of a lower layer right next to a higher one takes a contact shadow (two steps down);
        # the higher layer's own edge texel a step down too (a crisp ink line)
        lay = np.array([self.layer.get(k, 0) for k in keys])[idm]
        shade = np.zeros((n, n), np.int32)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            l2 = np.roll(np.roll(lay, dy, 0), dx, 1)
            m2 = np.roll(np.roll(mask, dy, 0), dx, 1)
            ok = mask & m2
            shade = np.where(ok & (l2 > lay) & (l2 - lay < 50), np.minimum(shade, -2), shade)
        idx_map = idx_map + shade
        # stitches
        for on, nxt in self.stitch:
            if on not in keys or nxt not in keys:
                continue
            a, b = keys.index(on), keys.index(nxt)
            near = np.zeros((n, n), bool)
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    if abs(dy) + abs(dx) == 2:
                        near |= np.roll(np.roll((idm == b) & mask, dy, 0), dx, 1)
            edge1 = np.zeros((n, n), bool)
            for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                edge1 |= np.roll(np.roll((idm == b) & mask, dy, 0), dx, 1)
            st = (idm == a) & near & ~edge1 & mask & (((xx + yy) % 4) == 0)
            idx_map = np.where(st, idx_map + 1, idx_map)
        for ki, key in enumerate(keys):
            sel = idm == ki
            cols = np.array(self.palettes[key], np.uint8)
            img[sel] = cols[np.clip(idx_map[sel], 0, len(cols) - 1)]
        return img

    def _decals_onto(self, decals, high):
        """Snaps every decal vertex onto the sculpt, lifted by its key's decal_lift."""
        from mathutils.bvhtree import BVHTree
        dg = bpy.context.evaluated_depsgraph_get()
        tree = BVHTree.FromObject(high, dg)
        for o in decals:
            lift = self.decal_lift.get(_key_of(o), 0.002)
            for v in o.data.vertices:
                hit = tree.find_nearest(v.co)
                if hit[0] is not None:
                    v.co = hit[0] + hit[1] * lift

    def finish(self):
        name = self.name
        bpy.context.scene.render.engine = "CYCLES"
        bpy.context.scene.cycles.device = "CPU"
        if bpy.context.scene.world is None:
            bpy.context.scene.world = bpy.data.worlds.new("World")
        bpy.context.scene.world.light_settings.distance = 0.12
        arm = self.F.build()
        arm.name = name + "_rig"
        arm.data.name = name + "_rig"
        forms = _meshes_of(arm)
        shells = _drop_rig(self.S.build())
        decals = _drop_rig(self.D.build())
        for o in forms:
            o.modifiers.clear()
        print("%s: fusing %d forms + %d shells" % (name, len(forms), len(shells)))
        high = self._fuse(forms, shells)
        low = self._retopo(high)
        self._weights(low, forms + shells)
        self._unwrap(low)
        self._decals_onto(decals, high)
        # material ids
        keys = sorted({_key_of(o) for o in forms + shells + decals})
        rng = np.random.default_rng(1)
        idcol = {}
        for k in keys:
            idcol[k] = tuple(float(x) for x in rng.random(3) * 0.9 + 0.05)
        for o in forms + shells + decals:
            o.data.materials.clear()
            o.data.materials.append(self._emit_mat("id_" + o.name, idcol[_key_of(o)]))
        print("  baking")
        a_id = self._bake(low, "id", sources=forms + shells + decals)
        cols = np.array([idcol[k] for k in keys])
        d = ((a_id[:, :, None, :] - cols[None, None, :, :]) ** 2).sum(-1)
        idm = d.argmin(-1)
        mask = self._bake(low, "mask", own="white", margin=0)[:, :, 0] > 0.5
        high.data.materials.clear()
        high.data.materials.append(self._emit_mat("cav", geo="pointiness"))
        cav = self._bake(low, "cavity", sources=[high])[:, :, 0]
        ao = self._bake(low, "ao")[:, :, 0]
        nrm = self._bake(low, "normal") * 2 - 1        # object space: Blender X right(-), Y back, Z up
        pos = self._bake(low, "position", own="position")
        maps = dict(keys=keys, id=idm, mask=mask, ao=ao, cav=cav, nrm=nrm, pos=pos)
        os.makedirs(MAP_DIR, exist_ok=True)
        np.savez_compressed(os.path.join(MAP_DIR, name + ".npz"), keys=np.array(keys), id=idm.astype(np.uint8),
                            mask=mask, ao=ao.astype(np.float16), cav=cav.astype(np.float16),
                            nrm=nrm.astype(np.float16), pos=pos.astype(np.float16))
        img = self.paint(maps)
        from PIL import Image
        Image.fromarray(img[::-1]).save(os.path.join(K.OUT, name + "_atlas.png"))
        # the result: the low mesh on the rig
        low.data.materials.clear()
        low.parent = arm
        mod = low.modifiers.new("Armature", "ARMATURE")
        mod.object = arm
        coll = bpy.data.collections.new("sources")
        bpy.context.scene.collection.children.link(coll)
        for o in forms + shells + decals + [high]:
            for c in o.users_collection:
                c.objects.unlink(o)
            coll.objects.link(o)
            o.parent = None
        coll.hide_render = True
        coll.hide_viewport = True
        os.makedirs(BLEND_DIR, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(BLEND_DIR, name + ".blend"), compress=True)
        for o in list(coll.objects):
            bpy.data.objects.remove(o)
        K.export(os.path.join(K.OUT, name + "_hd.glb"))
        tris = sum(len(p.vertices) - 2 for p in low.data.polygons)
        print("%s_hd.glb: one skinned mesh, %d triangles, %d px atlas" % (name, tris, self.atlas))
        return maps
