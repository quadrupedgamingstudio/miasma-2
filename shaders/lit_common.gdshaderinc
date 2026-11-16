// The game's surface shader (scripts/look.gd, scripts/materials.gd): Godot's real lighting (sun and
// lamps with shadows, fog, ambient occlusion) on point-filtered textures, so they stay crisp pixel art.
//
// Included by lit.gdshader (one-sided), lit_double.gdshader (two-sided) and lit_alpha.gdshader
// (see-through: mist sheets). The see-through one defines LIT_ALPHA before including this.

uniform sampler2D albedo_texture : source_color, filter_nearest_mipmap, repeat_enable;
uniform vec4 albedo_tint : source_color = vec4(1.0);
uniform vec2 uv_scale = vec2(1.0);
uniform float self_lit = 0.0;              // 1 = ignores lighting (flames); glows instead
uniform vec4 flash_color : source_color = vec4(1.0, 1.0, 1.0, 0.0); // a = amount (hit flash)
uniform bool alpha_cut = false;            // discard transparent texels
uniform bool billboard = false;            // quad always turns to face the camera (Y axis)
uniform bool use_vertex_color = false;     // multiply by the mesh's vertex colour (ground tints)
uniform float fade = 1.0;                  // < 1 = see-through
uniform bool use_blend = false;            // ground: blend_texture painted in where COLOR.a is high
uniform sampler2D blend_texture : source_color, filter_nearest_mipmap, repeat_enable;
uniform vec4 blend_tint : source_color = vec4(1.0);
uniform float roughness_value = 0.85;      // Tuning.LIT_ROUGHNESS
uniform float specular_value = 0.25;       // Tuning.LIT_SPECULAR
uniform float glow_strength = 1.6;         // Tuning.LIT_SELF_LIT_GLOW: how bright self-lit things shine

varying vec4 v_color;

void vertex() {
	if (billboard) {
		// Turn round the model's Y axis to face the camera (StandardMaterial3D's Y-billboard).
		MODELVIEW_MATRIX = VIEW_MATRIX * mat4(
			vec4(normalize(cross(MODEL_MATRIX[1].xyz, INV_VIEW_MATRIX[2].xyz)) * length(MODEL_MATRIX[0].xyz), 0.0),
			MODEL_MATRIX[1],
			vec4(normalize(cross(INV_VIEW_MATRIX[0].xyz, MODEL_MATRIX[1].xyz)) * length(MODEL_MATRIX[2].xyz), 0.0),
			MODEL_MATRIX[3]);
		MODELVIEW_NORMAL_MATRIX = mat3(MODELVIEW_MATRIX);
	}
	v_color = use_vertex_color ? COLOR : vec4(1.0);
	UV = UV * uv_scale;
}

void fragment() {
	vec4 tex;
	if (use_blend) {
		// a ragged, pixel-crisp edge: each texel of the tile gets its own threshold
		vec2 texel = floor(UV * vec2(textureSize(albedo_texture, 0)));
		float n = fract(sin(dot(texel, vec2(12.9898, 78.233))) * 43758.5453);
		float w = step(n * 0.7 + 0.15, v_color.a);
		vec4 a = texture(albedo_texture, UV) * albedo_tint * vec4(v_color.rgb, 1.0);
		vec4 b = texture(blend_texture, UV) * blend_tint;
		tex = mix(a, b, w);
	} else {
		tex = texture(albedo_texture, UV) * albedo_tint * v_color;
	}
	if (alpha_cut && tex.a < 0.5) {
		discard;
	}
#ifdef LIT_SAME_BOTH_SIDES
	// both sides take the light of the front (grass, leaves, mist): Godot flips back faces otherwise
	if (!FRONT_FACING) {
		NORMAL = -NORMAL;
	}
#endif
	vec3 col = tex.rgb;
	col = mix(col, flash_color.rgb, flash_color.a);
	ALBEDO = col * (1.0 - self_lit);
	EMISSION = col * self_lit * glow_strength + flash_color.rgb * flash_color.a * 0.6;
	ROUGHNESS = roughness_value;
	SPECULAR = specular_value;
#ifdef LIT_ALPHA
	ALPHA = tex.a * fade;
#endif
}
