extends Control
# Main Menu Script for Dustway: Desert Trader (Godot 4)

@onready var title_label: Label = $MarginContainer/VBoxContainer/Header/TitleLabel
@onready var caps_label: Label = $MarginContainer/VBoxContainer/Header/CapsLabel
@onready var tiles_box: HBoxContainer = $MarginContainer/VBoxContainer/TilesBox

@onready var btn_campaign: TextureButton = $MarginContainer/VBoxContainer/TilesBox/TileCampaign/BtnCampaign
@onready var btn_bot: TextureButton = $MarginContainer/VBoxContainer/TilesBox/TileBot/BtnBot
@onready var btn_network: TextureButton = $MarginContainer/VBoxContainer/TilesBox/TileNetwork/BtnNetwork
@onready var btn_tutorial: TextureButton = $MarginContainer/VBoxContainer/TilesBox/TileTutorial/BtnTutorial

@onready var popup_overlay: ColorRect = $PopupOverlay
@onready var popup_label: Label = $PopupOverlay/PanelContainer/VBoxContainer/MessageLabel
@onready var popup_close_btn: Button = $PopupOverlay/PanelContainer/VBoxContainer/CloseButton

func _ready() -> void:
	print("Main Menu scene ready. Connecting tiles...")
	Network.global_caps_updated.connect(_on_global_caps_updated)
	Network.fetch_global_caps()
	
	_setup_tile_hover(btn_campaign)
	_setup_tile_hover(btn_bot)
	_setup_tile_hover(btn_network)
	_setup_tile_hover(btn_tutorial)
	
	if btn_campaign: btn_campaign.pressed.connect(_on_campaign_pressed)
	if btn_bot: btn_bot.pressed.connect(_on_bot_pressed)
	if btn_network: btn_network.pressed.connect(_on_network_pressed)
	if btn_tutorial: btn_tutorial.pressed.connect(_on_tutorial_pressed)
	if popup_close_btn: popup_close_btn.pressed.connect(_close_popup)

func _setup_tile_hover(btn: TextureButton) -> void:
	if btn == null: return
	btn.pivot_offset = btn.custom_minimum_size / 2.0
	btn.mouse_entered.connect(func():
		var tween = create_tween().set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
		tween.tween_property(btn, "scale", Vector2(1.06, 1.06), 0.15)
		btn.modulate = Color(1.15, 1.15, 1.15)
	)
	btn.mouse_exited.connect(func():
		var tween = create_tween().set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
		tween.tween_property(btn, "scale", Vector2(1.0, 1.0), 0.15)
		btn.modulate = Color(1.0, 1.0, 1.0)
	)

func _on_global_caps_updated(caps_val: int) -> void:
	if caps_label:
		caps_label.text = "Фонд Пустоши: %d крышек" % caps_val

func _on_campaign_pressed() -> void:
	_show_popup("СЮЖЕТНАЯ КАМПАНИЯ\n\nПуть через Пустошь: 12 опасных этапов и боссы караванов.\n(Этапы загружаются из stages.json)")

func _on_bot_pressed() -> void:
	print("Starting Single Player vs Bot...")
	get_tree().change_scene_to_file("res://scenes/game_table.tscn")

func _on_network_pressed() -> void:
	_show_popup("СЕТЕВАЯ ИГРА (ONLINE)\n\nСвязь с базой Firebase активна!\nЗдесь откроется лобби для поиска и приглашения друзей.")

func _on_tutorial_pressed() -> void:
	_show_popup("ПРАВИЛА КАРАВАНА\n\n• Цель: Собрать в 3 колонках сумму от 21 до 26.\n• Числовые карты (2-10) задают направление и вес.\n• Картинки (Валет, Дама, Король, Туз) модифицируют карты.\n• Побеждает тот, кто выиграл минимум 2 каравана из 3!")

func _show_popup(msg: String) -> void:
	if popup_label: popup_label.text = msg
	if popup_overlay: popup_overlay.visible = true

func _close_popup() -> void:
	if popup_overlay: popup_overlay.visible = false
