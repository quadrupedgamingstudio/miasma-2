class_name UiKit
extends RefCounted
## Window and text styles for the demo's menus: dark blue gradient boxes with a light border, like
## the PS1 JRPGs.

static func panel_style() -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color = Color(0.06, 0.08, 0.28, 0.92)
	s.border_color = Color(0.85, 0.85, 0.95)
	s.set_border_width_all(1)
	s.set_corner_radius_all(2)
	s.content_margin_left = 6
	s.content_margin_right = 6
	s.content_margin_top = 4
	s.content_margin_bottom = 4
	s.shadow_color = Color(0, 0, 0, 0.5)
	s.shadow_size = 2
	return s


static func panel(rect: Rect2) -> PanelContainer:
	var p := PanelContainer.new()
	p.add_theme_stylebox_override("panel", panel_style())
	p.position = rect.position
	p.size = rect.size
	p.custom_minimum_size = rect.size
	return p


static func label(text: String, size := 9, color := Color(0.95, 0.95, 1.0)) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_override("font", Game.font if size >= 9 else Game.font_small)
	l.add_theme_font_size_override("font_size", 12 if size >= 9 else 8)
	l.add_theme_color_override("font_color", color)
	l.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.8))
	l.add_theme_constant_override("shadow_offset_x", 1)
	l.add_theme_constant_override("shadow_offset_y", 1)
	return l
