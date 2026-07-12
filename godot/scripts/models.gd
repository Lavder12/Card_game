extends Node
# Autoload: Models
# Complete Caravan Rules Engine (Dustway: Desert Trader)

class Card:
	var value: String # "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"
	var suit: String  # "H", "D", "C", "S"
	var is_face: bool = false
	var attached_cards: Array = [] # Array of Card objects attached to this card (K, Q, J)

	func _init(v: String, s: String) -> void:
		value = v
		suit = s
		is_face = (v in ["J", "Q", "K"])
		attached_cards = []

	func get_num_value() -> int:
		if value == "A": return 1
		if value.is_valid_int(): return value.to_int()
		return 0

	func get_effective_value() -> int:
		if is_face: return 0
		var base_val = get_num_value()
		var multiplier = 1
		for att in attached_cards:
			if att.value == "K":
				multiplier *= 2
		return base_val * multiplier

	func get_effective_suit() -> String:
		# Queen reverses suit to the Queen's suit
		var current_s = suit
		for att in attached_cards:
			if att.value == "Q":
				current_s = att.suit
		return current_s

	func get_display_name() -> String:
		var suits_map = {"H": "♥", "D": "♦", "C": "♣", "S": "♠"}
		return value + suits_map.get(suit, suit)

	func get_texture_path() -> String:
		return "res://assets/cards/hand/%s_%s.png" % [value, suit]

class CaravanColumn:
	var cards: Array = [] # Array of main numeric/ace Card objects in column order
	var owner_name: String = "Player" # "Player" or "Opponent"

	func _init(owner: String = "Player") -> void:
		owner_name = owner
		cards = []

	func get_total_value() -> int:
		var total = 0
		for c in cards:
			total += c.get_effective_value()
		return total

	func get_status() -> String:
		var total = get_total_value()
		if total < 21: return "LOW"
		elif total <= 26: return "SOLD" # 21-26 is target winning range
		else: return "OVER" # >26 busted

	func get_direction() -> int:
		# Returns: 1 (Ascending), -1 (Descending), or 0 (Neutral/Only 1 card)
		if cards.size() < 2: return 0
		
		# Trace from start to determine active direction taking Queens into account
		var dir = 0
		for i in range(1, cards.size()):
			var prev_val = cards[i - 1].get_num_value()
			var curr_val = cards[i].get_num_value()
			if curr_val > prev_val:
				dir = 1
			elif curr_val < prev_val:
				dir = -1
			
			# Check if prev card or current card has Queen attached which reverses direction
			for att in cards[i - 1].attached_cards + cards[i].attached_cards:
				if att.value == "Q":
					dir = -dir
		return dir

	func can_place_card(card: Card, target_card_index: int = -1) -> bool:
		if cards.is_empty():
			# First card must be numeric or Ace (not J, Q, K)
			return not card.is_face
		
		if card.is_face:
			# Face card (K, Q, J) must be attached to an existing numeric card
			if target_card_index >= 0 and target_card_index < cards.size():
				# Cannot attach numeric card to another face card
				return true
			return cards.size() > 0 # Default attach to top if no specific index
		
		# Placing numeric card on top of the column
		var top_card = cards.back()
		var top_val = top_card.get_num_value()
		var card_val = card.get_num_value()
		
		if card_val == top_val:
			return false # Cannot play equal numeric value
		
		# If suit matches effective suit of top card, always allowed regardless of direction
		if card.suit == top_card.get_effective_suit():
			return true
		
		# Otherwise must follow active direction
		var dir = get_direction()
		if dir == 0:
			return true # Any direction allowed for second card
		elif dir == 1 and card_val > top_val:
			return true
		elif dir == -1 and card_val < top_val:
			return true
		
		return false

	func place_card(card: Card, target_card_index: int = -1) -> bool:
		if not can_place_card(card, target_card_index):
			return false
		
		if card.is_face:
			var idx = target_card_index if (target_card_index >= 0 and target_card_index < cards.size()) else (cards.size() - 1)
			if card.value == "J":
				# Jack removes the target card and all its attached cards from the column!
				cards.remove_at(idx)
			else:
				# King or Queen attaches to the card
				cards[idx].attached_cards.append(card)
		else:
			cards.append(card)
		return true

	func clear_column() -> void:
		cards.clear()

func create_standard_deck() -> Array:
	var deck = []
	var suits = ["H", "D", "C", "S"]
	var values = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
	for s in suits:
		for v in values:
			deck.append(Card.new(v, s))
	deck.shuffle()
	return deck

func check_match_winner(player_cols: Array, opponent_cols: Array) -> String:
	# Returns: "PLAYER", "OPPONENT", "TIE", or "NONE" (in progress)
	if player_cols.size() < 3 or opponent_cols.size() < 3: return "NONE"
	
	var sold_count = 0
	var player_wins = 0
	var opponent_wins = 0
	
	for i in range(3):
		var p_stat = player_cols[i].get_status()
		var o_stat = opponent_cols[i].get_status()
		var p_val = player_cols[i].get_total_value()
		var o_val = opponent_cols[i].get_total_value()
		
		if p_stat == "SOLD" or o_stat == "SOLD":
			# If both are SOLD, compare scores. If one is SOLD and other is not, the SOLD one wins.
			if p_stat == "SOLD" and o_stat != "SOLD":
				player_wins += 1
				sold_count += 1
			elif o_stat == "SOLD" and p_stat != "SOLD":
				opponent_wins += 1
				sold_count += 1
			elif p_stat == "SOLD" and o_stat == "SOLD":
				if p_val > o_val:
					player_wins += 1
					sold_count += 1
				elif o_val > p_val:
					opponent_wins += 1
					sold_count += 1
				else:
					# Tie on this column, column is contested
					sold_count += 1
	
	if sold_count == 3 or player_wins >= 2 or opponent_wins >= 2:
		if player_wins > opponent_wins: return "PLAYER"
		elif opponent_wins > player_wins: return "OPPONENT"
		elif sold_count == 3 and player_wins == opponent_wins: return "TIE"
	
	return "NONE"

func _ready() -> void:
	print("Dustway Models (Caravan Rules Engine) loaded.")
