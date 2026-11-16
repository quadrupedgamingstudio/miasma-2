class_name Look
extends RefCounted
## The game's look (Cody 2026-11-15: "everything should be B"): Godot's real lighting (sun and campfire
## shadows, distance fog plus the miasma hanging in the air, ambient occlusion, glow, a screen dither)
## on point-filtered pixel-art textures at full resolution; higher-detail textures in
## assets/textures_hd/, smooth ground, rounded props, models rebuilt in Blender in assets/models/hd/.
## Every look number is in Tuning ("Look"). Scenes call Look.setup(self) once.

const HD_TEXTURES := "res://assets/textures_hd/%s"


## A texture path: the higher-detail version in assets/textures_hd/<same name> when there is one
## (textures not remade yet, like the flame and the mist, keep the original).
static func texture(path: String) -> String:
	var hd_path := HD_TEXTURES % path.get_file()
	if ResourceLoader.exists(hd_path):
		return hd_path
	return path


## Gives a scene its light, sky light, fog and the dither layer.
static func setup(scene: Node) -> void:
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Tuning.FOG_COLOR
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Tuning.LIT_AMBIENT_COLOR
	env.ambient_light_energy = Tuning.LIT_AMBIENT_ENERGY
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.tonemap_exposure = Tuning.LIT_EXPOSURE
	env.adjustment_enabled = true
	env.adjustment_contrast = Tuning.LIT_CONTRAST
	env.adjustment_saturation = Tuning.LIT_SATURATION
	# distance fog: the land fades into the grey-violet haze
	env.fog_enabled = true
	env.fog_mode = Environment.FOG_MODE_EXPONENTIAL
	env.fog_light_color = Tuning.FOG_COLOR
	env.fog_density = Tuning.LIT_FOG_DENSITY
	env.fog_sky_affect = 0.0
	env.fog_aerial_perspective = 0.0
	# the miasma that's left, hanging in the air: lit by the sun and the fire
	if Tuning.LIT_VOLUMETRIC_DENSITY > 0.0:
		env.volumetric_fog_enabled = true
		env.volumetric_fog_density = Tuning.LIT_VOLUMETRIC_DENSITY
		env.volumetric_fog_albedo = Tuning.LIT_VOLUMETRIC_ALBEDO
		env.volumetric_fog_emission = Tuning.LIT_VOLUMETRIC_EMISSION
		env.volumetric_fog_emission_energy = 1.0
		env.volumetric_fog_length = Tuning.LIT_VOLUMETRIC_LENGTH
		env.volumetric_fog_ambient_inject = 0.1
	env.ssao_enabled = Tuning.LIT_SSAO
	env.ssao_radius = 1.2
	env.ssao_intensity = 1.6
	env.glow_enabled = Tuning.LIT_GLOW > 0.0
	env.glow_intensity = Tuning.LIT_GLOW
	env.glow_bloom = 0.05
	env.glow_hdr_threshold = 1.0
	var we := WorldEnvironment.new()
	we.name = "LookEnvironment"
	we.environment = env
	scene.add_child(we)

	var sun := DirectionalLight3D.new()
	sun.name = "LookSun"
	sun.light_color = Tuning.SUN_COLOR
	sun.light_energy = Tuning.LIT_SUN_ENERGY
	sun.shadow_enabled = true
	sun.shadow_blur = 1.5
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_2_SPLITS
	sun.directional_shadow_max_distance = Tuning.LIT_SHADOW_DISTANCE
	sun.light_volumetric_fog_energy = 1.2
	scene.add_child(sun)
	var d := Tuning.SUN_DIRECTION.normalized()
	sun.look_at_from_position(Vector3.ZERO, -d, Vector3.UP if absf(d.y) < 0.99 else Vector3.FORWARD)

	if Tuning.LOOK_DITHER_LEVELS > 0.0:
		var layer := CanvasLayer.new()
		layer.name = "LookDither"
		layer.layer = -1
		var rect := ColorRect.new()
		rect.set_anchors_preset(Control.PRESET_FULL_RECT)
		rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
		var m := ShaderMaterial.new()
		m.shader = preload("res://shaders/dither_post.gdshader")
		m.set_shader_parameter("levels", Tuning.LOOK_DITHER_LEVELS)
		m.set_shader_parameter("pixel", Tuning.LOOK_DITHER_PIXEL)
		rect.material = m
		layer.add_child(rect)
		scene.add_child(layer)
