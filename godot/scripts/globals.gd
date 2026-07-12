extends Node
# Autoload: Globals
# Global state, settings, and constants for Dustway: Desert Trader

const VERSION: String = "2.0.0-Godot"
var language: String = "RU" # "RU" or "EN"

var player_name: String = "Путешественник"
var friend_code: String = ""
var caps: int = 100

func _ready() -> void:
	print("Dustway Globals initialized. Version: ", VERSION)
