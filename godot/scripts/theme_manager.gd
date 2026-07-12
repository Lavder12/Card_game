extends Node
# Autoload: ThemeManager
# Creates and applies the Desert Night visual theme matching the original Pygame version

var desert_theme: Theme

# Desert Night Palette (exact match from src/config.py)
const BG           = Color(0.067, 0.055, 0.047)     # #110E0C Deep coffee/charcoal
const PANEL        = Color(0.165, 0.133, 0.114)     # #2A221D Warm dark gray-brown
const PANEL_2      = Color(0.133, 0.102, 0.086)     # #221A16
const PANEL_BORD   = Color(0.549, 0.361, 0.239)     # #8C5C3D Copper / rust
const PANEL_GLOW   = Color(0.851, 0.608, 0.259)     # #D99B42 Amber glow
const CARD_FACE    = Color(0.957, 0.933, 0.855)     # #F4EEDA
const CARD_SEL     = Color(0.851, 0.608, 0.259)     # #D99B42
const CARD_HOVER   = Color(0.949, 0.753, 0.341)     # #F2C057
const TEXT_CLR     = Color(0.910, 0.863, 0.784)     # #E8DCC8 Sand
const TEXT_DIM     = Color(0.722, 0.643, 0.545)     # #B8A48B Dusty tan
const BTN_CLR      = Color(0.369, 0.235, 0.157)     # #5E3C28 Mahogany
const BTN_H        = Color(0.549, 0.361, 0.239)     # #8C5C3D Rust
const BTN_TXT      = Color(0.941, 0.902, 0.824)     # #F0E6D2
const ACCENT       = Color(0.949, 0.753, 0.341)     # #F2C057 Vibrant gold
const RED_CLR      = Color(0.784, 0.235, 0.235)     # #C83C3C
const OUT_OK       = Color(0.471, 0.745, 0.392)     # #78BE64
const OUT_BAD      = Color(0.784, 0.275, 0.275)     # #C84646
const CAPS_CLR     = Color(0.902, 0.725, 0.255)     # #E6B941

func _ready() -> void:
	desert_theme = Theme.new()
	_setup_default_font()
	_setup_label_styles()
	_setup_button_styles()
	_setup_panel_styles()
	_setup_color_rect_styles()
	_setup_scroll_styles()
	
	# Apply theme globally to root viewport
	get_tree().root.theme = desert_theme
	print("Desert Night Theme applied globally.")

func _setup_default_font() -> void:
	# Use the default Godot font but with adjusted sizes
	pass

func _setup_label_styles() -> void:
	desert_theme.set_color("font_color", "Label", TEXT_CLR)
	desert_theme.set_color("font_shadow_color", "Label", Color(0, 0, 0, 0.7))
	desert_theme.set_constant("shadow_offset_x", "Label", 1)
	desert_theme.set_constant("shadow_offset_y", "Label", 2)

func _setup_button_styles() -> void:
	# Normal state
	var normal_sb = StyleBoxFlat.new()
	normal_sb.bg_color = BTN_CLR
	normal_sb.border_color = PANEL_BORD
	normal_sb.set_border_width_all(2)
	normal_sb.set_corner_radius_all(10)
	normal_sb.set_content_margin_all(12)
	# Top highlight
	normal_sb.shadow_color = Color(1, 1, 1, 0.08)
	normal_sb.shadow_size = 0
	desert_theme.set_stylebox("normal", "Button", normal_sb)
	
	# Hover state
	var hover_sb = normal_sb.duplicate()
	hover_sb.bg_color = BTN_H
	hover_sb.border_color = PANEL_GLOW
	hover_sb.set_border_width_all(2)
	desert_theme.set_stylebox("hover", "Button", hover_sb)
	
	# Pressed state
	var pressed_sb = normal_sb.duplicate()
	pressed_sb.bg_color = Color(BTN_CLR.r * 0.8, BTN_CLR.g * 0.8, BTN_CLR.b * 0.8)
	pressed_sb.border_color = ACCENT
	pressed_sb.set_border_width_all(2)
	desert_theme.set_stylebox("pressed", "Button", pressed_sb)
	
	# Disabled state
	var disabled_sb = normal_sb.duplicate()
	disabled_sb.bg_color = Color(BTN_CLR.r * 0.5, BTN_CLR.g * 0.5, BTN_CLR.b * 0.5, 0.6)
	disabled_sb.border_color = Color(PANEL_BORD.r, PANEL_BORD.g, PANEL_BORD.b, 0.3)
	desert_theme.set_stylebox("disabled", "Button", disabled_sb)
	
	# Button text colors
	desert_theme.set_color("font_color", "Button", BTN_TXT)
	desert_theme.set_color("font_hover_color", "Button", ACCENT)
	desert_theme.set_color("font_pressed_color", "Button", Color(1, 1, 1))
	desert_theme.set_color("font_disabled_color", "Button", TEXT_DIM)

func _setup_panel_styles() -> void:
	var panel_sb = StyleBoxFlat.new()
	panel_sb.bg_color = PANEL
	panel_sb.border_color = PANEL_BORD
	panel_sb.set_border_width_all(2)
	panel_sb.set_corner_radius_all(14)
	panel_sb.set_content_margin_all(16)
	# Deep shadow
	panel_sb.shadow_color = Color(0, 0, 0, 0.6)
	panel_sb.shadow_size = 8
	panel_sb.shadow_offset = Vector2(2, 4)
	desert_theme.set_stylebox("panel", "PanelContainer", panel_sb)

func _setup_color_rect_styles() -> void:
	pass

func _setup_scroll_styles() -> void:
	# ScrollContainer grab/slider
	var grab_sb = StyleBoxFlat.new()
	grab_sb.bg_color = PANEL_BORD
	grab_sb.set_corner_radius_all(4)
	desert_theme.set_stylebox("grabber", "VScrollBar", grab_sb)
	desert_theme.set_stylebox("grabber", "HScrollBar", grab_sb)
	
	var bg_sb = StyleBoxFlat.new()
	bg_sb.bg_color = PANEL_2
	bg_sb.set_corner_radius_all(4)
	desert_theme.set_stylebox("scroll", "VScrollBar", bg_sb)
	desert_theme.set_stylebox("scroll", "HScrollBar", bg_sb)
