extends Control
# Full Caravan Game Table Controller (Dustway: Desert Trader - Godot 4)

# Node paths matching game_table.tscn structure
@onready var status_label: Label = $MarginContainer/VBoxContainer/Header/StatusLabel
@onready var back_button: Button = $MarginContainer/VBoxContainer/Header/BackButton
@onready var opponent_box: HBoxContainer = $MarginContainer/VBoxContainer/TableArea/OpponentBox
@onready var player_box: HBoxContainer = $MarginContainer/VBoxContainer/TableArea/PlayerBox
@onready var hand_box: HBoxContainer = $MarginContainer/VBoxContainer/HandArea/HandBox

@onready var pass_btn: Button = $MarginContainer/VBoxContainer/Header/ControlsBox/PassButton
@onready var discard_btn: Button = $MarginContainer/VBoxContainer/Header/ControlsBox/DiscardButton

@onready var end_modal: ColorRect = $EndMatchModal
@onready var end_title: Label = $EndMatchModal/Panel/VBoxContainer/TitleLabel
@onready var end_desc: Label = $EndMatchModal/Panel/VBoxContainer/DescLabel
@onready var end_replay_btn: Button = $EndMatchModal/Panel/VBoxContainer/HBoxContainer/ReplayButton
@onready var end_menu_btn: Button = $EndMatchModal/Panel/VBoxContainer/HBoxContainer/MenuButton

var opponent_cols: Array = []
var player_cols: Array = []
var opponent_slots: Array = []
var player_slots: Array = []

var player_deck: Array = []
var player_hand: Array = [] # Array of Models.Card
var bot: AIBot
var is_player_turn: bool = true
var is_game_over: bool = false
var selected_card_ui: CardUI = null

func _ready() -> void:
	print("=== Initializing Caravan Game Table ===")
	if back_button: back_button.pressed.connect(_on_back_pressed)
	if pass_btn: pass_btn.pressed.connect(_on_pass_pressed)
	if discard_btn: discard_btn.pressed.connect(_on_discard_pressed)
	if end_replay_btn: end_replay_btn.pressed.connect(_on_replay_pressed)
	if end_menu_btn: end_menu_btn.pressed.connect(_on_back_pressed)
	
	_start_new_match()

func _start_new_match() -> void:
	is_game_over = false
	is_player_turn = true
	selected_card_ui = null
	if end_modal: end_modal.visible = false
	
	# Determine difficulty
	var diff = Globals.selected_bot_difficulty if Globals.selected_bot_difficulty else "Мусорщик"
	bot = AIBot.new(diff)
	
	# Setup Models
	opponent_cols.clear()
	player_cols.clear()
	for i in range(3):
		opponent_cols.append(Models.CaravanColumn.new("Opponent"))
		player_cols.append(Models.CaravanColumn.new("Player"))
	
	# Setup Deck & Hand
	player_deck = Models.create_standard_deck()
	player_hand.clear()
	for i in range(8):
		if not player_deck.is_empty():
			player_hand.append(player_deck.pop_back())
	
	# Setup UI Slots
	_rebuild_table_slots()
	_rebuild_hand_ui()
	_update_status("Ваш ход! Кликните на карту в руке, затем на колонку.")
	print("Match started vs %s. Player hand: %d cards." % [diff, player_hand.size()])

func _rebuild_table_slots() -> void:
	# Remove old dynamic slots (keep only static children like AvatarBox/Spacer)
	for slot in opponent_slots:
		if is_instance_valid(slot): slot.queue_free()
	for slot in player_slots:
		if is_instance_valid(slot): slot.queue_free()
	opponent_slots.clear()
	player_slots.clear()
	
	# Wait a frame for queue_free to process
	await get_tree().process_frame
	
	var slot_scene = preload("res://scenes/caravan_slot.tscn")
	
	for i in range(3):
		# Opponent slot
		var o_slot = slot_scene.instantiate() as CaravanSlot
		o_slot.owner_type = "OPPONENT"
		o_slot.column_index = i
		if opponent_box: opponent_box.add_child(o_slot)
		o_slot.set_column_model(opponent_cols[i])
		o_slot.column_clicked.connect(_on_slot_clicked)
		o_slot.card_dropped_on_slot.connect(_on_card_dropped_on_slot)
		opponent_slots.append(o_slot)
		print("Created opponent slot %d" % (i + 1))
		
		# Player slot
		var p_slot = slot_scene.instantiate() as CaravanSlot
		p_slot.owner_type = "PLAYER"
		p_slot.column_index = i
		if player_box: player_box.add_child(p_slot)
		p_slot.set_column_model(player_cols[i])
		p_slot.column_clicked.connect(_on_slot_clicked)
		p_slot.card_dropped_on_slot.connect(_on_card_dropped_on_slot)
		player_slots.append(p_slot)
		print("Created player slot %d" % (i + 1))

func _rebuild_hand_ui() -> void:
	if hand_box == null:
		print("ERROR: hand_box is null!")
		return
	for child in hand_box.get_children():
		child.queue_free()
	
	await get_tree().process_frame
	
	var card_scene = preload("res://scenes/card.tscn")
	for i in range(player_hand.size()):
		var c_model = player_hand[i]
		var c_ui = card_scene.instantiate() as CardUI
		hand_box.add_child(c_ui)
		c_ui.set_card_model(c_model, false)
		c_ui.card_clicked.connect(_on_hand_card_clicked)
	print("Hand rebuilt: %d cards displayed." % player_hand.size())

func _on_hand_card_clicked(c_ui: CardUI) -> void:
	if not is_player_turn or is_game_over: return
	
	print("Hand card clicked: %s" % c_ui.card_model.get_display_name())
	
	if selected_card_ui == c_ui:
		# Deselect
		c_ui.set_selected(false)
		selected_card_ui = null
		_update_status("Карта снята с выбора. Выберите карту.")
	else:
		# Deselect previous, select new
		if selected_card_ui:
			selected_card_ui.set_selected(false)
		selected_card_ui = c_ui
		c_ui.set_selected(true)
		_update_status("Выбрана: %s — кликните на колонку!" % c_ui.card_model.get_display_name())

func _on_slot_clicked(slot: CaravanSlot) -> void:
	if not is_player_turn or is_game_over:
		print("Slot clicked but not player's turn.")
		return
	if selected_card_ui == null:
		_update_status("⚠ Сначала выберите карту в руке!")
		return
	print("Slot clicked: %s column %d" % [slot.owner_type, slot.column_index + 1])
	_try_place_player_card(selected_card_ui, slot)

func _on_card_dropped_on_slot(slot: CaravanSlot, c_ui: CardUI) -> void:
	if not is_player_turn or is_game_over: return
	_try_place_player_card(c_ui, slot)

func _try_place_player_card(c_ui: CardUI, slot: CaravanSlot) -> void:
	var c_model = c_ui.card_model
	var target_col = slot.caravan_model
	var target_owner = slot.owner_type
	
	# Validate move
	if target_owner == "PLAYER":
		if not target_col.can_place_card(c_model):
			_update_status("❌ Недопустимый ход! Проверьте масть или направление.")
			SoundManager.play_sfx("lose")
			return
		target_col.place_card(c_model)
	else:
		# Offensive card on opponent column
		if not c_model.is_face or (c_model.value not in ["J", "K"]):
			_update_status("❌ На колонку противника можно класть только J или K!")
			SoundManager.play_sfx("lose")
			return
		if not target_col.can_place_card(c_model, target_col.cards.size() - 1):
			_update_status("❌ Невозможно прикрепить карту противнику!")
			return
		target_col.place_card(c_model, target_col.cards.size() - 1)
	
	SoundManager.play_sfx("card_drop")
	player_hand.erase(c_model)
	if selected_card_ui == c_ui:
		selected_card_ui = null
	
	# Draw new card
	if not player_deck.is_empty() and player_hand.size() < 8:
		player_hand.append(player_deck.pop_back())
	
	_rebuild_hand_ui()
	_update_all_slots()
	
	if _check_winner_condition(): return
	_start_bot_turn()

func _on_pass_pressed() -> void:
	if not is_player_turn or is_game_over: return
	SoundManager.play_sfx("click")
	_update_status("Вы пропустили ход.")
	_start_bot_turn()

func _on_discard_pressed() -> void:
	if not is_player_turn or is_game_over or selected_card_ui == null:
		_update_status("⚠ Сначала кликните на карту, которую хотите сбросить!")
		return
	SoundManager.play_sfx("card_drop")
	player_hand.erase(selected_card_ui.card_model)
	selected_card_ui = null
	if not player_deck.is_empty():
		player_hand.append(player_deck.pop_back())
	_rebuild_hand_ui()
	_update_status("Карта сброшена. Взята новая из колоды.")
	_start_bot_turn()

func _start_bot_turn() -> void:
	is_player_turn = false
	_update_status("🤔 %s думает..." % bot.difficulty)
	get_tree().create_timer(1.0).timeout.connect(_execute_bot_move)

func _execute_bot_move() -> void:
	if is_game_over: return
	
	var move = bot.choose_action(opponent_cols, player_cols)
	var action = move.get("action", "PASS")
	
	if action == "PLACE":
		var card_idx = move.get("card_index", 0)
		if card_idx >= bot.hand.size():
			_update_status("🤖 %s пропустил ход." % bot.difficulty)
			is_player_turn = true
			return
		var c_model: Models.Card = bot.hand[card_idx]
		bot.hand.remove_at(card_idx)
		bot.draw_card()
		
		var target_owner = move.get("target_owner", "OPPONENT")
		var col_idx = move.get("column_index", 0)
		var target_idx = move.get("card_target_index", -1)
		
		if target_owner == "OPPONENT":
			opponent_cols[col_idx].place_card(c_model, target_idx)
			_update_status("🤖 %s → %s в свой Караван %d" % [bot.difficulty, c_model.get_display_name(), col_idx + 1])
		else:
			player_cols[col_idx].place_card(c_model, target_idx)
			_update_status("💥 %s атакует ваш Караван %d! (%s)" % [bot.difficulty, col_idx + 1, c_model.get_display_name()])
		SoundManager.play_sfx("card_drop")
	elif action == "DISCARD":
		var card_idx = move.get("card_index", 0)
		if card_idx < bot.hand.size():
			bot.hand.remove_at(card_idx)
		bot.draw_card()
		_update_status("🤖 %s сбросил карту." % bot.difficulty)
	else:
		_update_status("🤖 %s пропустил ход." % bot.difficulty)
	
	_update_all_slots()
	if _check_winner_condition(): return
	
	is_player_turn = true
	_update_status("Ваш ход! Выберите карту или перетащите на колонку.")

func _update_all_slots() -> void:
	for slot in opponent_slots:
		if is_instance_valid(slot): slot._update_ui()
	for slot in player_slots:
		if is_instance_valid(slot): slot._update_ui()

func _check_winner_condition() -> bool:
	var winner = Models.check_match_winner(player_cols, opponent_cols)
	if winner != "NONE":
		is_game_over = true
		is_player_turn = false
		_show_end_modal(winner)
		return true
	return false

func _show_end_modal(winner: String) -> void:
	if end_modal == null: return
	end_modal.visible = true
	if winner == "PLAYER":
		SoundManager.play_sfx("win")
		if end_title: end_title.text = "🏆 ПОБЕДА!"
		if end_desc: end_desc.text = "Вы обыграли %s!\n+%d монет!" % [bot.difficulty, Globals.selected_bot_bet]
		Globals.caps += Globals.selected_bot_bet
		if Network: Network.award_caps(Globals.selected_bot_bet)
	elif winner == "OPPONENT":
		SoundManager.play_sfx("lose")
		if end_title: end_title.text = "💀 ПОРАЖЕНИЕ"
		if end_desc: end_desc.text = "%s оказался хитрее.\n-%d монет." % [bot.difficulty, Globals.selected_bot_bet]
		Globals.caps = max(0, Globals.caps - Globals.selected_bot_bet)
	else:
		if end_title: end_title.text = "🤝 НИЧЬЯ"
		if end_desc: end_desc.text = "Караваны разошлись миром."

func _update_status(msg: String) -> void:
	if status_label: status_label.text = msg

func _on_replay_pressed() -> void:
	SoundManager.play_sfx("click")
	_start_new_match()

func _on_back_pressed() -> void:
	SoundManager.play_sfx("click")
	get_tree().change_scene_to_file("res://scenes/main_menu.tscn")
