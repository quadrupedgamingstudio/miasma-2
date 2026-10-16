// PS1-style surface shader for the JRPG demo. A trimmed copy of Miasma's shaders/ps1_common.gdshaderinc
// (same look: vertex snapping, affine textures, Gouraud vertex lighting, per-vertex fog, 15-bit colour
// with an ordered dither), minus Miasma's baked lamp shadows and real-shadow passes, plus one
// directional sun for outdoor scenes.
//
// The look is driven by global shader parameters (Project Settings > Shader Globals), which
// scripts/ps1.gd sets from scripts/data/tuning.gd.

global uniform vec4 ps1_ambient;        // rgb = ambient light
global uniform vec4 ps1_sun;            // xyz = direction towards the sun, w = strength
global uniform vec4 ps1_sun_color;      // rgb
global uniform vec4 ps1_fog_color;      // rgb = fog colour
global uniform vec2 ps1_fog_range;      // x = fog start, y = fog end (metres)
global uniform vec2 ps1_snap;           // pixel grid to snap vertices to; 0 = off
global uniform float ps1_affine;        // 1 = affine (warped) textures, 0 = correct
global uniform float ps1_dither;        // 1 = 15-bit colour with dither, 0 = off

// Four point lights (campfire, glows). light = xyz position + w strength, color = rgb + a radius.
global uniform vec4 ps1_light0; global uniform vec4 ps1_light_color0;
global uniform vec4 ps1_light1; global uniform vec4 ps1_light_color1;
global uniform vec4 ps1_light2; global uniform vec4 ps1_light_color2;
global uniform vec4 ps1_light3; global uniform vec4 ps1_light_color3;

uniform sampler2D albedo_texture : source_color, filter_nearest, repeat_enable;
uniform vec4 albedo_tint : source_color = vec4(1.0);
uniform vec2 uv_scale = vec2(1.0);
uniform float self_lit = 0.0;              // 1 = ignores lighting (flames)
uniform vec4 flash_color : source_color = vec4(1.0, 1.0, 1.0, 0.0); // a = amount (hit flash)
uniform bool alpha_cut = false;            // discard transparent texels
uniform bool billboard = false;            // quad always turns to face the camera (Y axis)
uniform bool use_vertex_color = false;     // multiply by the mesh's vertex colour (ground tints)
uniform float fade = 1.0;                  // < 1 = dithered see-through (screen-door, like the PS1)

varying vec3 v_light;
varying float v_fog;
varying vec3 v_affine;   // xy = uv * w, z = w  (lets the fragment rebuild an affine uv)
varying vec4 v_color;

vec3 point_light(vec3 p, vec3 n, vec4 l, vec4 c) {
	if (l.w <= 0.0) {
		return vec3(0.0);
	}
	vec3 d = l.xyz - p;
	float dist = length(d);
	float x = clamp(dist / max(c.a, 0.01), 0.0, 1.0);
	float att = mix((1.0 - x) * (1.0 - x), 1.0 - x * x, 0.5);
	float ndl = clamp(dot(n, d / max(dist, 0.001)) * 0.7 + 0.3, 0.0, 1.0);
	return c.rgb * l.w * att * ndl;
}

void vertex() {
	vec3 wpos;
	vec3 wnormal;
	if (billboard) {
		vec3 cam_right = normalize(vec3(INV_VIEW_MATRIX[0].x, 0.0, INV_VIEW_MATRIX[0].z));
		float s = length(MODEL_MATRIX[0].xyz);
		wpos = MODEL_MATRIX[3].xyz + cam_right * VERTEX.x * s + vec3(0.0, 1.0, 0.0) * VERTEX.y * s;
		wnormal = normalize(cross(cam_right, vec3(0.0, 1.0, 0.0)));
	} else {
		wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
		wnormal = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
	}
	vec3 light = ps1_ambient.rgb;
	light += ps1_sun_color.rgb * ps1_sun.w * clamp(dot(wnormal, normalize(ps1_sun.xyz)) * 0.75 + 0.25, 0.0, 1.0);
	light += point_light(wpos, wnormal, ps1_light0, ps1_light_color0);
	light += point_light(wpos, wnormal, ps1_light1, ps1_light_color1);
	light += point_light(wpos, wnormal, ps1_light2, ps1_light_color2);
	light += point_light(wpos, wnormal, ps1_light3, ps1_light_color3);
	v_light = light;
	v_color = use_vertex_color ? COLOR : vec4(1.0);

	vec4 vpos = VIEW_MATRIX * vec4(wpos, 1.0);
	float dist = length(vpos.xyz);
	v_fog = clamp((dist - ps1_fog_range.x) / max(ps1_fog_range.y - ps1_fog_range.x, 0.01), 0.0, 1.0);

	vec4 clip = PROJECTION_MATRIX * vpos;
	if (ps1_snap.x > 0.0 && clip.w > 0.0) {
		vec2 grid = ps1_snap * 0.5;
		clip.xy = round(clip.xy / clip.w * grid) / grid * clip.w;
	}
	POSITION = clip;

	vec2 uv = UV * uv_scale;
	UV = uv;
	v_affine = vec3(uv * clip.w, clip.w);
}

const float BAYER[16] = float[](
	0.0 / 16.0,  8.0 / 16.0,  2.0 / 16.0, 10.0 / 16.0,
	12.0 / 16.0, 4.0 / 16.0, 14.0 / 16.0,  6.0 / 16.0,
	3.0 / 16.0, 11.0 / 16.0,  1.0 / 16.0,  9.0 / 16.0,
	15.0 / 16.0, 7.0 / 16.0, 13.0 / 16.0,  5.0 / 16.0
);

vec3 to_srgb(vec3 c) {
	return mix(c * 12.92, 1.055 * pow(c, vec3(1.0 / 2.4)) - 0.055, step(vec3(0.0031308), c));
}

vec3 to_linear(vec3 c) {
	return mix(c / 12.92, pow((c + 0.055) / 1.055, vec3(2.4)), step(vec3(0.04045), c));
}

void fragment() {
	vec2 uv = mix(UV, v_affine.xy / v_affine.z, ps1_affine);
	vec4 tex = texture(albedo_texture, uv) * albedo_tint * v_color;
	if (alpha_cut && tex.a < 0.5) {
		discard;
	}
	ivec2 p = ivec2(FRAGCOORD.xy) % 4;
	float threshold = BAYER[p.y * 4 + p.x];
	if (fade < 1.0 && fade <= threshold) {
		discard;
	}
	vec3 col = tex.rgb * mix(v_light, vec3(1.0), self_lit);
	col = mix(col, flash_color.rgb, flash_color.a);
	col = mix(col, ps1_fog_color.rgb, v_fog * (1.0 - 0.7 * self_lit));
	if (ps1_dither > 0.5) {
		vec3 s = to_srgb(clamp(col, 0.0, 1.0));
		s = floor(s * 31.0 + threshold) / 31.0;
		col = to_linear(s);
	}
	ALBEDO = col;
}
