extends RefCounted
class_name AIBot
# AI Caravan Opponent (Minimax & Heuristic evaluation)

var difficulty: String = "Мусорщик" # "Мусорщик" (Easy), "Охранник" (Medium), "Торговец" (Hard)
var hand: Array = [] # Array of Models.Card
var deck: Array = [] # Array of Models.Card

func _init(diff: String = "Мусорщик") -> void:
	difficulty = diff
	hand = []
	deck = Models.create_standard_deck()
	# Deal initial 8 cards to bot hand
	for i in range(8):
		if not deck.is_empty():
			hand.append(deck.pop_back())

func choose_action(bot_columns: Array, player_columns: Array) -> Dictionary:
	# Returns Dictionary with keys: "action" ("PLACE", "DISCARD", "PASS"), "card_index", "target_owner" ("OPPONENT" or "PLAYER"), "column_index", "card_target_index"
	if hand.is_empty():
		return {"action": "PASS"}
	
	# Difficulty-based randomness / error rate
	var error_chance = 0.35 if difficulty == "Мусорщик" else (0.15 if difficulty == "Охранник" else 0.0)
	if randf() < error_chance:
		# Make a random valid move or discard
		var rand_idx = randi() % hand.size()
		var rand_card = hand[rand_idx]
		for col_idx in range(3):
			if bot_columns[col_idx].can_place_card(rand_card):
				return {"action": "PLACE", "card_index": rand_idx, "target_owner": "OPPONENT", "column_index": col_idx, "card_target_index": -1}
		# Or discard random card
		return {"action": "DISCARD", "card_index": rand_idx}
	
	# Evaluate all possible moves with heuristic scoring
	var best_score = -999999
	var best_move = {"action": "DISCARD", "card_index": 0} # Default fallback: discard lowest or first
	
	for card_idx in range(hand.size()):
		var card = hand[card_idx]
		
		# 1. Check placing on Bot's own columns
		for col_idx in range(3):
			var col: Models.CaravanColumn = bot_columns[col_idx]
			if not card.is_face:
				if col.can_place_card(card):
					var current_val = col.get_total_value()
					var new_val = current_val + card.get_num_value()
					var score = _evaluate_column_change(current_val, new_val, true)
					if score > best_score:
						best_score = score
						best_move = {"action": "PLACE", "card_index": card_idx, "target_owner": "OPPONENT", "column_index": col_idx, "card_target_index": -1}
			else:
				# Face cards (K, Q, J) on bot's own cards
				for c_idx in range(col.cards.size()):
					if col.can_place_card(card, c_idx):
						# Simulate effect
						var current_val = col.get_total_value()
						var target_c: Models.Card = col.cards[c_idx]
						var score = 0
						if card.value == "K":
							# Double this card's effective value
							var added_val = target_c.get_effective_value()
							var new_val = current_val + added_val
							score = _evaluate_column_change(current_val, new_val, true)
						elif card.value == "J":
							# Removing own card only good if we busted
							var sub_val = target_c.get_effective_value()
							var new_val = current_val - sub_val
							if current_val > 26 and new_val <= 26:
								score = 150
							else:
								score = -50
						elif card.value == "Q":
							score = 20 # Direction change helper
						
						if score > best_score:
							best_score = score
							best_move = {"action": "PLACE", "card_index": card_idx, "target_owner": "OPPONENT", "column_index": col_idx, "card_target_index": c_idx}
		
		# 2. Check offensive placement on Player's columns (with Jack or King)
		if card.is_face:
			for col_idx in range(3):
				var p_col: Models.CaravanColumn = player_columns[col_idx]
				var p_val = p_col.get_total_value()
				if p_val >= 21 and p_val <= 26:
					# Player has a sold/winning column! Attack it!
					for c_idx in range(p_col.cards.size()):
						if p_col.can_place_card(card, c_idx):
							var target_c: Models.Card = p_col.cards[c_idx]
							var score = 0
							if card.value == "J":
								# Jack removes player's card from a winning column! Massive +250 score!
								score = 250
							elif card.value == "K":
								# King doubles player's card to force them to bust (> 26)!
								var added_val = target_c.get_effective_value()
								if (p_val + added_val) > 26:
									score = 220
							if score > best_score:
								best_score = score
								best_move = {"action": "PLACE", "card_index": card_idx, "target_owner": "PLAYER", "column_index": col_idx, "card_target_index": c_idx}
	
	# If no good placement moves found (best_score < 0), pick worst card to discard
	if best_score <= 0 and hand.size() > 0:
		return {"action": "DISCARD", "card_index": randi() % hand.size()}
	
	return best_move

func _evaluate_column_change(old_val: int, new_val: int, is_own: bool) -> int:
	if not is_own: return 0
	
	# Busted change
	if new_val > 26:
		return -100
	
	# Entering the golden winning zone (21..26)
	if new_val >= 21 and new_val <= 26:
		if old_val < 21:
			return 200 + (new_val - 21) * 10 # 26 is better than 21
		else:
			return 100 + (new_val - old_val) * 15 # Improving existing sold column toward 26
	
	# Below 21: reward getting closer to 26
	if new_val < 21:
		return new_val * 4
	
	return 0

func draw_card() -> void:
	if not deck.is_empty():
		hand.append(deck.pop_back())
