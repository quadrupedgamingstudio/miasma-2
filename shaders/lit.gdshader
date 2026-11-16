// One-sided lit surface. See lit_common.gdshaderinc.
shader_type spatial;
render_mode cull_back, depth_draw_opaque, diffuse_burley, specular_schlick_ggx;

#include "res://shaders/lit_common.gdshaderinc"
