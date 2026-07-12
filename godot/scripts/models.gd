extends Node
# Autoload: Models
# Core card structures and Caravan rules engine

class Card:
	var value: String # "2", "3", ... "10", "J", "Q", "K", "A"
	var suit: String  # "H", "D", "C", "S"
	var is_face: bool = false

	func _init(v: String, s: String) -> void:
		value = v
		suit = s
		is_face = (v in ["J", "Q", "K"])

	func get_num_value() -> int:
		if value == "A": return 1
		if value.is_valid_int(): return value.to_int()
		return 0

func _ready() -> void:
	print("Dustway Models logic loaded.")
