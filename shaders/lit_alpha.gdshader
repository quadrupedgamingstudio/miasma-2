// See-through, two-sided lit surface (the lingering miasma's mist sheets). See lit_common.gdshaderinc.
shader_type spatial;
render_mode blend_mix, cull_disabled, depth_draw_never, shadows_disabled, diffuse_burley, specular_disabled;

#define LIT_ALPHA
#define LIT_SAME_BOTH_SIDES
#include "res://shaders/lit_common.gdshaderinc"
