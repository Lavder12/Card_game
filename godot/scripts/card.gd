extends Control
class_name CardUI
# Interactive 2D Card with Hover effect, Click-to-select, and Drag & Drop

signal card_clicked(card_node: CardUI)
signal card_drag_started(card_node: CardUI)

@export var value: String = "10"
@export var suit: String = "H"
@export var is_face_down: bool = false
@export var is_draggable: bool = true

var card_model: Models.Card
var original_position: Vector2
var is_hovered: bool = false
var is_selected: bool = false

@onready var texture_rect: TextureRect = $TextureRect
@onready var highlight_rect: ColorRect = $HighlightRect
@onready var fallback_label: Label = $FallbackLabel

func _ready() -> void:
	custom_minimum_size = Vector2(110, 160)
	pivot_offset = custom_minimum_size / 2.0
	mouse_filter = Control.MOUSE_FILTER_STOP
	
	mouse_entered.connect(_on_mouse_entered)
	mouse_exited.connect(_on_mouse_exited)
	
	if highlight_rect:
		highlight_rect.visible = false
	
	if card_model:
		_update_visuals()
	else:
		set_card_data(value, suit, is_face_down)

func set_card_data(v: String, s: String, face_down: bool = false) -> void:
	value = v
	suit = s
	is_face_down = face_down
	card_model = Models.Card.new(v, s)
	if is_inside_tree():
		_update_visuals()

func set_card_model(model: Models.Card, face_down: bool = false) -> void:
	card_model = model
	if model:
		value = model.value
		suit = model.suit
	is_face_down = face_down
	if is_inside_tree():
		_update_visuals()

func _update_visuals() -> void:
	if texture_rect == null: return
	
	if is_face_down:
		var back_tex = load("res://assets/cards/back-red 1.png")
		if back_tex:
			texture_rect.texture = back_tex
		if fallback_label: fallback_label.visible = false
		return
	
	var path = "res://assets/cards/hand/%s_%s.png" % [value, suit]
	if ResourceLoader.exists(path):
		texture_rect.texture = load(path)
		if fallback_label: fallback_label.visible = false
	else:
		texture_rect.texture = null
		if fallback_label:
			fallback_label.visible = true
			var suits_map = {"H": "♥", "D": "♦", "C": "♣", "S": "♠"}
			fallback_label.text = "%s\n%s" % [value, suits_map.get(suit, suit)]

func _on_mouse_entered() -> void:
	if not is_draggable or is_face_down: return
	is_hovered = true
	z_index = 10
	var tween = create_tween().set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	tween.tween_property(self, "scale", Vector2(1.12, 1.12), 0.1)
	modulate = Color(1.12, 1.12, 1.12)

func _on_mouse_exited() -> void:
	if not is_draggable or is_face_down: return
	is_hovered = false
	if not is_selected:
		z_index = 0
		var tween = create_tween().set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
		tween.tween_property(self, "scale", Vector2(1.0, 1.0), 0.1)
		modulate = Color(1.0, 1.0, 1.0)

func _gui_input(event: InputEvent) -> void:
	if not is_draggable or is_face_down: return
	
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT and event.pressed:
		print("Card clicked: %s%s" % [value, suit])
		_toggle_selection()
		card_clicked.emit(self)
		accept_event()

func _toggle_selection() -> void:
	is_selected = not is_selected
	if highlight_rect:
		highlight_rect.visible = is_selected
	if is_selected:
		z_index = 10
		scale = Vector2(1.12, 1.12)
		modulate = Color(1.15, 1.15, 1.0)
	else:
		z_index = 0
		scale = Vector2(1.0, 1.0)
		modulate = Color(1, 1, 1)

func set_selected(selected: bool) -> void:
	is_selected = selected
	if highlight_rect:
		highlight_rect.visible = is_selected
	if is_selected:
		z_index = 10
		scale = Vector2(1.12, 1.12)
		modulate = Color(1.15, 1.15, 1.0)
	else:
		z_index = 0
		scale = Vector2(1.0, 1.0)
		modulate = Color(1, 1, 1)

# Native Godot Drag & Drop
func _get_drag_data(at_position: Vector2) -> Variant:
	if not is_draggable or is_face_down or card_model == null:
		return null
	
	card_drag_started.emit(self)
	
	var preview = Control.new()
	var preview_tex = TextureRect.new()
	preview_tex.texture = texture_rect.texture
	preview_tex.custom_minimum_size = custom_minimum_size
	preview_tex.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	preview_tex.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	preview_tex.position = -custom_minimum_size / 2.0
	preview_tex.modulate = Color(1, 1, 1, 0.85)
	preview.add_child(preview_tex)
	set_drag_preview(preview)
	
	return {"type": "CARD", "card_node": self, "card_model": card_model}
