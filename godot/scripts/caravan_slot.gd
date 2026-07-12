extends Control
class_name CaravanSlot
# UI Slot for a single Caravan Column (Player or Opponent)

signal column_clicked(slot: CaravanSlot)
signal card_dropped_on_slot(slot: CaravanSlot, card_ui: CardUI)

@export var owner_type: String = "PLAYER" # "PLAYER" or "OPPONENT"
@export var column_index: int = 0

var caravan_model: Models.CaravanColumn

# Node paths MUST match the actual scene tree in caravan_slot.tscn
@onready var header_label: Label = $VBoxContainer/HeaderLabel
@onready var status_badge: PanelContainer = $VBoxContainer/StatusBadge
@onready var status_label: Label = $VBoxContainer/StatusBadge/Label
@onready var cards_container: VBoxContainer = $VBoxContainer/ScrollContainer/CardsContainer
@onready var hover_highlight: ColorRect = $HoverHighlight
@onready var click_button: Button = $ClickButton

func _ready() -> void:
	custom_minimum_size = Vector2(160, 280)
	if click_button:
		click_button.pressed.connect(_on_click_button_pressed)
	if hover_highlight:
		hover_highlight.visible = false
	_update_ui()

func set_column_model(model: Models.CaravanColumn) -> void:
	caravan_model = model
	if is_inside_tree():
		_update_ui()

func _update_ui() -> void:
	if not is_inside_tree(): return
	
	# Update header
	if header_label:
		var dir_str = ""
		if caravan_model and caravan_model.get_direction() == 1: dir_str = " ▲"
		elif caravan_model and caravan_model.get_direction() == -1: dir_str = " ▼"
		header_label.text = "Караван %d%s" % [column_index + 1, dir_str]
	
	# Update status badge
	if status_label and caravan_model:
		var total = caravan_model.get_total_value()
		var stat = caravan_model.get_status()
		
		if stat == "SOLD":
			status_label.text = "Счёт: %d ★" % total
			if status_badge: status_badge.modulate = Color(0.47, 0.75, 0.39) # Green
		elif stat == "OVER":
			status_label.text = "Счёт: %d ✕" % total
			if status_badge: status_badge.modulate = Color(0.78, 0.27, 0.27) # Red
		else:
			status_label.text = "Счёт: %d" % total
			if status_badge: status_badge.modulate = Color(0.95, 0.75, 0.34) # Gold
	elif status_label:
		status_label.text = "Счёт: 0"
	
	# Rebuild displayed cards
	if cards_container and caravan_model:
		for child in cards_container.get_children():
			child.queue_free()
		
		var card_scene = preload("res://scenes/card.tscn")
		for card_model in caravan_model.cards:
			var card_ui = card_scene.instantiate() as CardUI
			cards_container.add_child(card_ui)
			card_ui.is_draggable = false
			card_ui.custom_minimum_size = Vector2(80, 115)
			card_ui.set_card_model(card_model, false)

func _on_click_button_pressed() -> void:
	column_clicked.emit(self)

# Drag & Drop handling
func _can_drop_data(at_position: Vector2, data: Variant) -> bool:
	if typeof(data) != TYPE_DICTIONARY or not data.has("type") or data["type"] != "CARD":
		return false
	var dragged_card = data["card_model"] as Models.Card
	if caravan_model == null or dragged_card == null:
		return false
	
	if owner_type == "PLAYER":
		if not dragged_card.is_face:
			return caravan_model.can_place_card(dragged_card)
		else:
			return caravan_model.can_place_card(dragged_card, caravan_model.cards.size() - 1)
	else:
		if dragged_card.is_face and (dragged_card.value in ["J", "K"]):
			return caravan_model.can_place_card(dragged_card, caravan_model.cards.size() - 1)
		return false

func _drop_data(at_position: Vector2, data: Variant) -> void:
	if typeof(data) == TYPE_DICTIONARY and data.has("card_node"):
		var card_ui = data["card_node"] as CardUI
		card_dropped_on_slot.emit(self, card_ui)
