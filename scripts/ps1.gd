class_name Ps1
extends RefCounted
## Builds materials that use the PS1 shader (shaders/ps1*.gdshader), so everything shares one look.
## Same idea as Miasma's scripts/ps1.gd, trimmed down.

const SHADER := preload("res://shaders/ps1.gdshader")
const SHADER_DOUBLE := preload("res://shaders/ps1_double.gdshader")

static var _cache := {}


## A PS1 material for a texture. Shared unless `unique` (needed when a script changes it, e.g. a hit flash).
## options: tint (Color), uv_scale (Vector2), self_lit (float), alpha_cut, billboard, double_sided,
## vertex_color (bool), fade (float).
static func material(texture_path: String, options := {}, unique := false) -> ShaderMaterial:
	var key := texture_path + str(options)
	if not unique and _cache.has(key):
		return _cache[key]
	var mat := ShaderMaterial.new()
	mat.shader = SHADER_DOUBLE if options.get("double_sided", false) else SHADER
	mat.set_shader_parameter("albedo_texture", load(texture_path))
	mat.set_shader_parameter("uv_scale", options.get("uv_scale", Vector2.ONE))
	mat.set_shader_parameter("albedo_tint", options.get("tint", Color.WHITE))
	mat.set_shader_parameter("self_lit", options.get("self_lit", 0.0))
	mat.set_shader_parameter("alpha_cut", options.get("alpha_cut", false))
	mat.set_shader_parameter("billboard", options.get("billboard", false))
	mat.set_shader_parameter("use_vertex_color", options.get("vertex_color", false))
	mat.set_shader_parameter("fade", options.get("fade", 1.0))
	if not unique:
		_cache[key] = mat
	return mat


## Sets the scene's light and fog (outdoors: ambient + sun).
static func apply_look() -> void:
	var rs := RenderingServer
	var a := Tuning.AMBIENT
	rs.global_shader_parameter_set("ps1_ambient", Vector4(a.r, a.g, a.b, 1.0))
	var d := Tuning.SUN_DIRECTION.normalized()
	rs.global_shader_parameter_set("ps1_sun", Vector4(d.x, d.y, d.z, Tuning.SUN_STRENGTH))
	var s := Tuning.SUN_COLOR
	rs.global_shader_parameter_set("ps1_sun_color", Vector4(s.r, s.g, s.b, 1.0))
	var f := Tuning.FOG_COLOR
	rs.global_shader_parameter_set("ps1_fog_color", Vector4(f.r, f.g, f.b, 1.0))
	rs.global_shader_parameter_set("ps1_fog_range", Vector2(Tuning.FOG_START, Tuning.FOG_END))
	for i in 4:
		set_light(i, Vector3.ZERO, 0.0, Color.WHITE, 1.0)


## One of the four point-light slots (strength 0 = off).
static func set_light(slot: int, pos: Vector3, strength: float, color: Color, radius: float) -> void:
	RenderingServer.global_shader_parameter_set("ps1_light%d" % slot, Vector4(pos.x, pos.y, pos.z, strength))
	RenderingServer.global_shader_parameter_set("ps1_light_color%d" % slot, Vector4(color.r, color.g, color.b, radius))
