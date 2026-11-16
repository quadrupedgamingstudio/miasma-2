// Full-screen colour dither (scripts/look.gd): cuts the picture to a few levels per channel with
// a 4x4 ordered (Bayer) dither, for the hard dithered gradients of the old 3D era. Drawn on a
// CanvasLayer under the HUD, so menus and text stay clean. Levels: Tuning.LOOK_DITHER_LEVELS.
shader_type canvas_item;

uniform sampler2D screen : hint_screen_texture, filter_nearest;
uniform float levels = 40.0;
uniform float pixel = 1.0;   // dither cell size in screen pixels (2 = chunkier)

const float BAYER[16] = float[](
	0.0 / 16.0,  8.0 / 16.0,  2.0 / 16.0, 10.0 / 16.0,
	12.0 / 16.0, 4.0 / 16.0, 14.0 / 16.0,  6.0 / 16.0,
	3.0 / 16.0, 11.0 / 16.0,  1.0 / 16.0,  9.0 / 16.0,
	15.0 / 16.0, 7.0 / 16.0, 13.0 / 16.0,  5.0 / 16.0
);

void fragment() {
	vec3 c = texture(screen, SCREEN_UV).rgb;
	ivec2 p = ivec2(FRAGCOORD.xy / max(pixel, 1.0)) % 4;
	float t = BAYER[p.y * 4 + p.x] - 0.5;
	c = floor(c * levels + 0.5 + t) / levels;
	COLOR = vec4(c, 1.0);
}
