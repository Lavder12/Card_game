extends Control
# Game Table Script for Dustway: Desert Trader (Godot 4)

@onready var status_label: Label = $MarginContainer/VBoxContainer/Header/StatusLabel
@onready var back_button: Button = $MarginContainer/VBoxContainer/Header/BackButton
@onready var opponent_box: HBoxContainer = $MarginContainer/VBoxContainer/TableArea/OpponentBox
@onready var player_box: HBoxContainer = $MarginContainer/VBoxContainer/TableArea/PlayerBox
@onready var hand_box: HBoxContainer = $MarginContainer/VBoxContainer/HandArea/HandBox

func _ready() -> void:
	print("Game Table scene ready.")
	if back_button:
		back_button.pressed.connect(_on_back_pressed)
	
	_setup_mock_table()

func _setup_mock_table() -> void:
	if status_label:
		status_label.text = "Противник: Мусорщик (Ставка: 25 крышек) | Цель: 21-26 в караванах"

func _on_back_pressed() -> void:
	get_tree().change_scene_to_file("res://scenes/main_menu.tscn")
