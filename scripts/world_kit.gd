class_name WorldKit
extends RefCounted
## Builds the demo's scenery in code with Miasma's textures: rolling ground, dead trees and new
## saplings (the land is healing), rocks, old palisade stakes, a campfire, lingering Miasma mist and
## the sky. Shared by the field and the battle arena so both look the same.

const TEX := "res://assets/textures/%s.png"


# --- Ground ---------------------------------------------------------------------------------------

## A height field from (x0, z0) to (x1, z1) on `cell` squares. height(x, z) -> metres;
## kind(x, z) -> "grass" or "dirt"; heal(x, z) -> 0 (miasma-scarred, grey) .. 1 (healthy green).
## Returns [MeshInstance3D, StaticBody3D].
static func ground(x0: float, z0: float, x1: float, z1: float, cell: float, height: Callable, kind: Callable, heal: Callable) -> Array:
	var tools := {}
	var nx := int(ceil((x1 - x0) / cell))
	var nz := int(ceil((z1 - z0) / cell))
	var faces := PackedVector3Array()
	for iz in nz:
		for ix in nx:
			var xa := x0 + ix * cell
			var za := z0 + iz * cell
			var xb := xa + cell
			var zb := za + cell
			var k: String = kind.call(xa + cell * 0.5, za + cell * 0.5)
			if not tools.has(k):
				var st := SurfaceTool.new()
				st.begin(Mesh.PRIMITIVE_TRIANGLES)
				tools[k] = st
			var st: SurfaceTool = tools[k]
			var p := [Vector3(xa, height.call(xa, za), za), Vector3(xb, height.call(xb, za), za),
				Vector3(xb, height.call(xb, zb), zb), Vector3(xa, height.call(xa, zb), zb)]
			var uv := [Vector2(xa, za) / 6.0, Vector2(xb, za) / 6.0, Vector2(xb, zb) / 6.0, Vector2(xa, zb) / 6.0]
			# split along the shorter diagonal's direction alternately, like hand-made PS1 terrain
			var tris := [[0, 1, 2], [0, 2, 3]] if (ix + iz) % 2 == 0 else [[0, 1, 3], [1, 2, 3]]
			for t in tris:
				var a: Vector3 = p[t[0]]
				var b: Vector3 = p[t[1]]
				var c: Vector3 = p[t[2]]
				var n := (c - a).cross(b - a).normalized()
				if n.y < 0:
					n = -n
				for i in [t[0], t[1], t[2]]:
					var v: Vector3 = p[i]
					st.set_normal(n)
					st.set_uv(uv[i])
					st.set_color(_tint(k, float(heal.call(v.x, v.z)), v))
					st.add_vertex(v)
				faces.append_array([a, b, c])
	var mesh := ArrayMesh.new()
	for k in tools:
		var st: SurfaceTool = tools[k]
		st.commit(mesh)
		var tex: String = "forest_grass" if k == "grass" else ("dirt" if k == "dirt" else String(k))
		mesh.surface_set_material(mesh.get_surface_count() - 1, Ps1.material(TEX % tex, {"vertex_color": true}))
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	mi.name = "Ground"
	var body := StaticBody3D.new()
	body.name = "GroundBody"
	var shape := CollisionShape3D.new()
	var con := ConcavePolygonShape3D.new()
	con.set_faces(faces)
	con.backface_collision = true
	shape.shape = con
	body.add_child(shape)
	return [mi, body]


static func _tint(k: String, heal: float, v: Vector3) -> Color:
	var noise := 0.92 + 0.08 * sin(v.x * 1.7 + v.z * 0.9) * cos(v.z * 1.3 - v.x * 0.4)
	if k == "grass":
		var sick := Color(0.62, 0.56, 0.6)     # grey-violet, where the miasma sat longest
		var well := Color(1.05, 1.08, 0.82)    # green coming back
		return sick.lerp(well, clampf(heal, 0.0, 1.0)) * noise
	var d := Color(0.85, 0.8, 0.78).lerp(Color(1, 0.96, 0.9), clampf(heal, 0.0, 1.0))
	return d * noise


# --- Meshes made from boxes and prisms -------------------------------------------------------------------

## A tapered n-sided prism from radius r0 at y0 to r1 at y1 (a trunk, a stake, a branch).
static func prism(st: SurfaceTool, base: Transform3D, r0: float, r1: float, h: float, sides := 6, uv_h := 1.0) -> void:
	for i in sides:
		var a0 := TAU * i / sides
		var a1 := TAU * (i + 1) / sides
		var p00 := base * Vector3(cos(a0) * r0, 0, sin(a0) * r0)
		var p10 := base * Vector3(cos(a1) * r0, 0, sin(a1) * r0)
		var p01 := base * Vector3(cos(a0) * r1, h, sin(a0) * r1)
		var p11 := base * Vector3(cos(a1) * r1, h, sin(a1) * r1)
		var n := (base.basis * Vector3(cos((a0 + a1) * 0.5), 0.2, sin((a0 + a1) * 0.5))).normalized()
		var u0 := float(i) / sides
		var u1 := float(i + 1) / sides
		_quad(st, [p00, p01, p11, p10], [Vector2(u0, uv_h), Vector2(u0, 0), Vector2(u1, 0), Vector2(u1, uv_h)], n)
	if r1 > 0.001:
		var top := base * Vector3(0, h, 0)
		for i in sides:
			var a0 := TAU * i / sides
			var a1 := TAU * (i + 1) / sides
			st.set_normal(base.basis.y.normalized())
			st.set_uv(Vector2(0.5, 0.5))
			st.add_vertex(top)
			st.set_uv(Vector2(0.5 + cos(a1) * 0.5, 0.5 + sin(a1) * 0.5))
			st.add_vertex(base * Vector3(cos(a1) * r1, h, sin(a1) * r1))
			st.set_uv(Vector2(0.5 + cos(a0) * 0.5, 0.5 + sin(a0) * 0.5))
			st.add_vertex(base * Vector3(cos(a0) * r1, h, sin(a0) * r1))


static func box(st: SurfaceTool, xf: Transform3D, size: Vector3, uv_scale := 1.0) -> void:
	var h := size * 0.5
	var c := [Vector3(-h.x, -h.y, -h.z), Vector3(h.x, -h.y, -h.z), Vector3(h.x, h.y, -h.z), Vector3(-h.x, h.y, -h.z),
		Vector3(-h.x, -h.y, h.z), Vector3(h.x, -h.y, h.z), Vector3(h.x, h.y, h.z), Vector3(-h.x, h.y, h.z)]
	var faces := [[4, 5, 6, 7, Vector3(0, 0, 1), size.x, size.y], [1, 0, 3, 2, Vector3(0, 0, -1), size.x, size.y],
		[0, 4, 7, 3, Vector3(-1, 0, 0), size.z, size.y], [5, 1, 2, 6, Vector3(1, 0, 0), size.z, size.y],
		[7, 6, 2, 3, Vector3(0, 1, 0), size.x, size.z], [0, 1, 5, 4, Vector3(0, -1, 0), size.x, size.z]]
	for f in faces:
		var w: float = f[5] * uv_scale
		var hh: float = f[6] * uv_scale
		_quad(st, [xf * c[f[0]], xf * c[f[3]], xf * c[f[2]], xf * c[f[1]]],
			[Vector2(0, hh), Vector2(0, 0), Vector2(w, 0), Vector2(w, hh)], (xf.basis * f[4]).normalized())


static func _quad(st: SurfaceTool, p: Array, uv: Array, n: Vector3) -> void:
	for i in [0, 1, 2, 0, 2, 3]:
		st.set_normal(n)
		st.set_uv(uv[i])
		st.add_vertex(p[i])


static func _commit(st: SurfaceTool, tex: String, opts := {}) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	mi.mesh = st.commit()
	mi.material_override = Ps1.material(TEX % tex, opts)
	return mi


static func _new_st() -> SurfaceTool:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	return st


static func _collider(node: Node3D, shape: Shape3D, offset := Vector3.ZERO) -> void:
	var body := StaticBody3D.new()
	var cs := CollisionShape3D.new()
	cs.shape = shape
	cs.position = offset
	body.add_child(cs)
	node.add_child(body)


# --- Props ---------------------------------------------------------------------------------------------

## A dead tree killed by the miasma: a bare grey trunk with crooked branches.
static func dead_tree(rng: RandomNumberGenerator, height := 5.0) -> Node3D:
	var root := Node3D.new()
	var st := _new_st()
	var r := 0.22 + rng.randf() * 0.12
	prism(st, Transform3D.IDENTITY, r, r * 0.45, height, 6, 3.0)
	for i in 3 + rng.randi() % 3:
		var y := height * rng.randf_range(0.4, 0.9)
		var yaw := rng.randf() * TAU
		var tilt := rng.randf_range(0.6, 1.1)
		var b := Basis(Vector3.UP, yaw) * Basis(Vector3.RIGHT, tilt)
		prism(st, Transform3D(b, Vector3(0, y, 0)), r * 0.35, 0.02, height * rng.randf_range(0.25, 0.45), 4, 1.0)
	root.add_child(_commit(st, "hollow_wood", {"tint": Color(0.78, 0.74, 0.76)}))
	var cyl := CylinderShape3D.new()
	cyl.radius = r
	cyl.height = height
	_collider(root, cyl, Vector3(0, height * 0.5, 0))
	return root


## A young tree, green: the land coming back.
static func sapling(rng: RandomNumberGenerator, height := 3.0) -> Node3D:
	var root := Node3D.new()
	var st := _new_st()
	prism(st, Transform3D.IDENTITY, 0.09, 0.05, height * 0.55, 5, 2.0)
	root.add_child(_commit(st, "hollow_wood", {"tint": Color(0.9, 0.82, 0.7)}))
	var leaves := _new_st()
	var tiers := 2 + rng.randi() % 2
	for i in tiers:
		var y := height * (0.35 + 0.22 * i)
		var rr := height * (0.42 - 0.1 * i)
		prism(leaves, Transform3D(Basis(Vector3.UP, rng.randf() * TAU), Vector3(0, y, 0)), rr, 0.0, height * 0.45, 7, 1.0)
	root.add_child(_commit(leaves, "forest_moss", {"tint": Color(0.75, 1.0, 0.6)}))
	var cyl := CylinderShape3D.new()
	cyl.radius = 0.15
	cyl.height = height
	_collider(root, cyl, Vector3(0, height * 0.5, 0))
	return root


## A lumpy boulder.
static func rock(rng: RandomNumberGenerator, size := 1.0) -> Node3D:
	var root := Node3D.new()
	var st := _new_st()
	var mesh := SphereMesh.new()
	mesh.radial_segments = 7
	mesh.rings = 4
	mesh.radius = size
	mesh.height = size * 1.4
	var arr := mesh.get_mesh_arrays()
	var verts: PackedVector3Array = arr[Mesh.ARRAY_VERTEX]
	var seed := rng.randf() * 100.0
	for i in verts.size():
		var v := verts[i]
		var k := 0.8 + 0.35 * absf(sin(v.x * 3.1 + seed) * cos(v.z * 2.7 + seed * 0.3))
		verts[i] = Vector3(v.x * k, maxf(v.y, -0.2 * size) * k, v.z * k)
	arr[Mesh.ARRAY_VERTEX] = verts
	var am := ArrayMesh.new()
	am.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
	st.create_from(am, 0)
	st.generate_normals()
	var mi := _commit(st, "forest_rock", {"uv_scale": Vector2(2, 2)})
	root.add_child(mi)
	var sph := SphereShape3D.new()
	sph.radius = size * 0.85
	_collider(root, sph, Vector3(0, size * 0.2, 0))
	return root


## A short run of Emberwick's old palisade stakes, some leaning, some broken.
static func stakes(rng: RandomNumberGenerator, count: int, spacing := 0.55) -> Node3D:
	var root := Node3D.new()
	var st := _new_st()
	for i in count:
		var h := rng.randf_range(1.4, 2.4) if rng.randf() > 0.2 else rng.randf_range(0.5, 0.9)
		var lean := Basis(Vector3.FORWARD, rng.randf_range(-0.12, 0.12)) * Basis(Vector3.RIGHT, rng.randf_range(-0.1, 0.1))
		prism(st, Transform3D(lean, Vector3(i * spacing, -0.2, 0)), 0.16, 0.13, h, 6, 1.5)
		prism(st, Transform3D(lean, Vector3(i * spacing, h - 0.2, 0) + lean * Vector3.ZERO), 0.13, 0.0, 0.3, 6, 0.3)
	var rail := Transform3D(Basis(Vector3.FORWARD, PI * 0.5), Vector3(-0.2, 0.9, 0.18))
	prism(st, rail, 0.06, 0.06, count * spacing + 0.2, 5, 4.0)
	root.add_child(_commit(st, "logs"))
	var b := BoxShape3D.new()
	b.size = Vector3(count * spacing, 2.0, 0.4)
	_collider(root, b, Vector3(count * spacing * 0.5 - spacing * 0.5, 1.0, 0))
	return root


## A wooden signpost with two boards.
static func signpost() -> Node3D:
	var root := Node3D.new()
	var st := _new_st()
	box(st, Transform3D(Basis(), Vector3(0, 0.9, 0)), Vector3(0.14, 1.8, 0.14))
	box(st, Transform3D(Basis(Vector3.UP, 0.15), Vector3(0.35, 1.55, 0)), Vector3(0.9, 0.24, 0.05))
	box(st, Transform3D(Basis(Vector3.UP, -0.4), Vector3(-0.3, 1.2, 0)), Vector3(0.8, 0.22, 0.05))
	root.add_child(_commit(st, "planks"))
	var b := BoxShape3D.new()
	b.size = Vector3(0.3, 1.8, 0.3)
	_collider(root, b, Vector3(0, 0.9, 0))
	return root


## An abandoned cart with a broken wheel.
static func cart() -> Node3D:
	var root := Node3D.new()
	var st := _new_st()
	box(st, Transform3D(Basis(), Vector3(0, 0.75, 0)), Vector3(1.4, 0.12, 2.2))
	box(st, Transform3D(Basis(), Vector3(-0.7, 1.0, 0)), Vector3(0.08, 0.45, 2.2))
	box(st, Transform3D(Basis(), Vector3(0.7, 1.0, 0)), Vector3(0.08, 0.45, 2.2))
	box(st, Transform3D(Basis(), Vector3(0, 1.0, 1.1)), Vector3(1.4, 0.45, 0.08))
	box(st, Transform3D(Basis(Vector3.RIGHT, -0.25), Vector3(0, 0.55, -1.8)), Vector3(0.1, 0.1, 1.6))
	root.add_child(_commit(st, "planks"))
	var wheels := _new_st()
	prism(wheels, Transform3D(Basis(Vector3.FORWARD, PI * 0.5), Vector3(0.85, 0.45, 0.4)), 0.45, 0.45, 0.1, 8, 0.2)
	prism(wheels, Transform3D(Basis(Vector3.FORWARD, PI * 0.5) * Basis(Vector3.RIGHT, 0.3), Vector3(-0.75, 0.2, -0.4)), 0.45, 0.45, 0.1, 8, 0.2)
	root.add_child(_commit(wheels, "logs"))
	root.rotation.z = 0.12
	var b := BoxShape3D.new()
	b.size = Vector3(1.6, 1.2, 2.4)
	_collider(root, b, Vector3(0, 0.6, 0))
	return root


## A campfire: a ring of stones, logs and a flickering flame. Returns the node; the flame's light is
## set by whoever owns it (Ps1.set_light).
static func campfire(rng: RandomNumberGenerator) -> Node3D:
	var root := Node3D.new()
	var st := _new_st()
	for i in 8:
		var a := TAU * i / 8.0
		box(st, Transform3D(Basis(Vector3.UP, a + rng.randf() * 0.3), Vector3(cos(a) * 0.55, 0.08, sin(a) * 0.55)), Vector3(0.25, 0.18, 0.2))
	root.add_child(_commit(st, "forest_rock"))
	var logs := _new_st()
	for i in 3:
		var a := TAU * i / 3.0
		prism(logs, Transform3D(Basis(Vector3.UP, a) * Basis(Vector3.RIGHT, 1.1), Vector3(cos(a) * 0.3, 0.02, sin(a) * 0.3)), 0.07, 0.06, 0.6, 5, 0.5)
	root.add_child(_commit(logs, "logs"))
	var flame := MeshInstance3D.new()
	var q := QuadMesh.new()
	q.size = Vector2(0.7, 0.9)
	q.center_offset = Vector3(0, 0.45, 0)
	flame.mesh = q
	flame.material_override = Ps1.material(TEX % "flame", {"self_lit": 1.0, "alpha_cut": true, "billboard": true, "double_sided": true})
	flame.name = "Flame"
	root.add_child(flame)
	var cyl := CylinderShape3D.new()
	cyl.radius = 0.6
	cyl.height = 0.6
	_collider(root, cyl, Vector3(0, 0.3, 0))
	return root


## A sheet of lingering miasma: a dithered, see-through violet wall.
static func mist(width: float, height: float) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var q := QuadMesh.new()
	q.size = Vector2(width, height)
	q.center_offset = Vector3(0, height * 0.5, 0)
	mi.mesh = q
	mi.material_override = Ps1.material(TEX % "forest_mist", {"double_sided": true, "self_lit": 0.6,
		"tint": Color(0.75, 0.6, 0.85), "fade": 0.3, "uv_scale": Vector2(width / 6.0, 1.0)})
	return mi


## A tuft of grass: two crossed quads.
static func grass_tuft(st: SurfaceTool, at: Vector3, size: float, yaw: float) -> void:
	for k in 2:
		var b := Basis(Vector3.UP, yaw + k * PI * 0.5)
		var r := b * Vector3(size * 0.5, 0, 0)
		var up := Vector3(0, size * 0.7, 0)
		_quad(st, [at - r, at - r + up, at + r + up, at + r], [Vector2(0, 1), Vector2(0, 0), Vector2(1, 0), Vector2(1, 1)], b * Vector3(0, 0, 1))


## A sky dome: a big inverted sphere with a gradient, drawn behind everything (no fog).
static func sky(top: Color, horizon: Color) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var s := SphereMesh.new()
	s.radius = 200.0
	s.height = 400.0
	s.radial_segments = 16
	s.rings = 8
	s.flip_faces = true
	mi.mesh = s
	var sh := Shader.new()
	sh.code = """
shader_type spatial;
render_mode unshaded, cull_disabled, depth_draw_never, fog_disabled;
uniform vec4 top : source_color;
uniform vec4 horizon : source_color;
varying float h;
void vertex() { h = normalize(VERTEX).y; }
void fragment() {
	float t = clamp(h * 2.2, 0.0, 1.0);
	vec3 c = mix(horizon.rgb, top.rgb, t);
	ivec2 p = ivec2(FRAGCOORD.xy) % 4;
	float d = float((p.x * 3 + p.y * 2) % 4) / 4.0;
	ALBEDO = floor(c * 31.0 + d) / 31.0;
}
"""
	var m := ShaderMaterial.new()
	m.shader = sh
	m.set_shader_parameter("top", top)
	m.set_shader_parameter("horizon", horizon)
	m.render_priority = -100
	mi.material_override = m
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	mi.extra_cull_margin = 1000.0
	return mi
