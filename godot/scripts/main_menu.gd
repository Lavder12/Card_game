extends Control
# Main Menu Script for Dustway: Desert Trader (Godot 4)

@onready var title_label: Label = $MarginContainer/VBoxContainer/Header/TitleLabel
@onready var caps_label: Label = $MarginContainer/VBoxContainer/Header/CapsLabel
@onready var tiles_box: HBoxContainer = $MarginContainer/VBoxContainer/TilesBox

func _ready() -> void:
	print("Main Menu scene ready.")
	Network.global_caps_updated.connect(_on_global_caps_updated)
	Network.fetch_global_caps()

func _on_global_caps_updated(caps_val: int) -> void:
	if caps_label:
		caps_label.text = "Фонд Пустоши: %d крышек" % caps_val
