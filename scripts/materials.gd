class_name Materials
extends RefCounted
## Every surface material in the game comes from here, so everything shares one look: Godot-lit
## surfaces (shaders/lit*.gdshader) with point-filtered pixel-art textures (see scripts/look.gd).
## Also runs the lamps (the campfire's OmniLight3D).

const LIT := preload("res://shaders/lit.gdshader")
const LIT_DOUBLE := preload("res://shaders/lit_double.gdshader")
const LIT_ALPHA := preload("res://shaders/lit_alpha.gdshader")

static var _cache := {}
static var _lamps := {}    # light slot -> OmniLight3D


## A material for a texture. Shared unless `unique` (needed when a script changes it, e.g. a hit flash).
## The texture is swapped for its higher-detail version in assets/textures_hd/ when there is one.
## options: tint (Color), uv_scale (Vector2), self_lit (float), alpha_cut, billboard, double_sided,
## vertex_color (bool), fade (float, < 1 = see-through), blend_texture (path), blend_tint (Color).
static func material(texture_path: String, options := {}, unique := false) -> ShaderMaterial:
	var key := texture_path + str(options)
	if not unique and _cache.has(key):
		return _cache[key]
	var mat := ShaderMaterial.new()
	if options.get("fade", 1.0) < 1.0:
		mat.shader = LIT_ALPHA
	else:
		mat.shader = LIT_DOUBLE if options.get("double_sided", false) else LIT
	mat.set_shader_parameter("roughness_value", Tuning.LIT_ROUGHNESS)
	mat.set_shader_parameter("specular_value", Tuning.LIT_SPECULAR)
	mat.set_shader_parameter("glow_strength", Tuning.LIT_SELF_LIT_GLOW)
	mat.set_shader_parameter("albedo_texture", load(Look.texture(texture_path)))
	mat.set_shader_parameter("uv_scale", options.get("uv_scale", Vector2.ONE))
	mat.set_shader_parameter("albedo_tint", options.get("tint", Color.WHITE))
	mat.set_shader_parameter("self_lit", options.get("self_lit", 0.0))
	mat.set_shader_parameter("alpha_cut", options.get("alpha_cut", false))
	mat.set_shader_parameter("billboard", options.get("billboard", false))
	mat.set_shader_parameter("use_vertex_color", options.get("vertex_color", false))
	mat.set_shader_parameter("fade", options.get("fade", 1.0))
	if options.has("blend_texture"):
		# the ground: a second texture painted in by the vertex colour's alpha (the road)
		mat.set_shader_parameter("use_blend", true)
		mat.set_shader_parameter("blend_texture", load(Look.texture(options.blend_texture)))
		mat.set_shader_parameter("blend_tint", options.get("blend_tint", Color.WHITE))
	if not unique:
		_cache[key] = mat
	return mat


## A lamp slot (strength 0 = off): moves a real OmniLight3D in the current scene (slot 0 casts
## shadows). The campfire calls this every frame for its flicker.
static func set_light(slot: int, pos: Vector3, strength: float, color: Color, radius: float) -> void:
	var held: Variant = _lamps.get(slot)
	var lamp: OmniLight3D = held if is_instance_valid(held) else null
	var scene := (Engine.get_main_loop() as SceneTree).current_scene
	if strength > 0.0 and scene and (lamp == null or not lamp.is_inside_tree()):
		lamp = OmniLight3D.new()
		lamp.name = "Lamp%d" % slot
		lamp.shadow_enabled = slot == 0
		lamp.omni_attenuation = 1.2
		lamp.light_volumetric_fog_energy = 2.0
		scene.add_child(lamp)
		_lamps[slot] = lamp
	if lamp:
		lamp.visible = strength > 0.0
		lamp.global_position = pos
		lamp.light_color = color
		lamp.light_energy = strength * Tuning.LIT_LAMP_ENERGY
		lamp.omni_range = radius * Tuning.LIT_LAMP_RANGE
