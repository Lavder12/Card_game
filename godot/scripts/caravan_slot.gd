extends Control
class_name CaravanSlot
# UI Slot for a single Caravan Column (Player or Opponent)

signal column_clicked(slot: CaravanSlot)
signal card_dropped_on_slot(slot: CaravanSlot, card_ui: CardUI)

@export var owner_type: String = "PLAYER" # "PLAYER" or "OPPONENT"
@export var column_index: int = 0

var caravan_model: Models.CaravanColumn

@onready var header_label: Label = $HeaderLabel
@onready var status_badge: PanelContainer = $StatusBadge
@onready var status_label: Label = $StatusBadge/Label
@onready var cards_container: VBoxContainer = $CardsContainer
@onready var hover_highlight: ColorRect = $HoverHighlight
@onready var click_button: Button = $ClickButton

func _ready() -> void:
	custom_minimum_size = Vector2(160, 320)
	if click_button:
		click_button.pressed.connect(_on_click_button_pressed)
	if hover_highlight:
		hover_highlight.visible = false
	_update_ui()

func set_column_model(model: Models.CaravanColumn) -> void:
	caravan_model = model
	_update_ui()

func _update_ui() -> void:
	if not is_inside_tree() or caravan_model == null: return
	
	var total = caravan_model.get_total_value()
	var stat = caravan_model.get_status()
	var dir = caravan_model.get_direction()
	
	var dir_str = ""
	if dir == 1: dir_str = "▲ Возр."
	elif dir == -1: dir_str = "▼ Убыв."
	
	if header_label:
		header_label.text = "Караван %d\n%s" % [column_index + 1, dir_str]
	
	if status_label and status_badge:
		if stat == "SOLD":
			status_label.text = "Сумма: %d\nПРОДАН!" % total
			status_badge.modulate = Color(0.2, 1.0, 0.3) # Glowing green
		elif stat == "OVER":
			status_label.text = "Сумма: %d\nПЕРЕБОР" % total
			status_badge.modulate = Color(1.0, 0.3, 0.3) # Red alert
		else:
			status_label.text = "Сумма: %d" % total
			status_badge.modulate = Color(1.0, 0.85, 0.4) # Yellow/gold
	
	# Rebuild displayed cards
	if cards_container:
		for child in cards_container.get_children():
			child.queue_free()
		
		for card_model in caravan_model.cards:
			var card_ui = preload("res://scenes/card.tscn").instantiate() as CardUI
			cards_container.add_child(card_ui)
			card_ui.is_draggable = false
			card_ui.set_card_model(card_model, false)
			
			# Also show attached face cards slightly indented right next to / under the card
			for att_model in card_model.attached_cards:
				var att_ui = preload("res://scenes/card.tscn").instantiate() as CardUI
				cards_container.add_child(att_ui)
				att_ui.is_draggable = false
				att_ui.set_card_model(att_model, false)
				att_ui.modulate = Color(0.85, 0.95, 1.0)
				att_ui.custom_minimum_size = Vector2(90, 130)

func _on_click_button_pressed() -> void:
	column_clicked.emit(self)

# Drag & Drop handling for dropping cards right onto this column slot
func _can_drop_data(at_position: Vector2, data: Variant) -> bool:
	if typeof(data) != TYPE_DICTIONARY or not data.has("type") or data["type"] != "CARD":
		return false
	var dragged_card = data["card_model"] as Models.Card
	if caravan_model == null or dragged_card == null:
		return false
	
	# Check rules: can we place this card?
	if owner_type == "PLAYER":
		# Player placing on their own column
		if not dragged_card.is_face:
			return caravan_model.can_place_card(dragged_card)
		else:
			# Face cards on own column
			return caravan_model.can_place_card(dragged_card, caravan_model.cards.size() - 1)
	else:
		# Player placing offensive face card (J, K) on opponent's column!
		if dragged_card.is_face and (dragged_card.value in ["J", "K"]):
			return caravan_model.can_place_card(dragged_card, caravan_model.cards.size() - 1)
		return false

func _drop_data(at_position: Vector2, data: Variant) -> void:
	if typeof(data) == TYPE_DICTIONARY and data.has("card_node"):
		var card_ui = data["card_node"] as CardUI
		card_dropped_on_slot.emit(self, card_ui)
