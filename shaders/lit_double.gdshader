// Two-sided lit surface (leaves, grass tufts, cloth, flames). See lit_common.gdshaderinc.
shader_type spatial;
render_mode cull_disabled, depth_draw_opaque, diffuse_burley, specular_schlick_ggx;

#define LIT_SAME_BOTH_SIDES
#include "res://shaders/lit_common.gdshaderinc"
