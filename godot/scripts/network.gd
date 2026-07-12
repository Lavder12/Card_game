extends Node
# Autoload: Network
# Firebase Realtime Database client using Godot HTTPRequest nodes

const FIREBASE_URL: String = "https://dustway-default-rtdb.europe-west1.firebasedatabase.app"

signal global_caps_updated(value: int)
signal friend_lookup_completed(friend_data: Dictionary)

var http_client: HTTPRequest

func _ready() -> void:
	http_client = HTTPRequest.new()
	add_child(http_client)
	http_client.request_completed.connect(_on_request_completed)
	print("Dustway Network initialized. Target: ", FIREBASE_URL)

func fetch_global_caps() -> void:
	var url = FIREBASE_URL + "/server_state/global_caps.json"
	http_client.request(url)

func _on_request_completed(result: int, response_code: int, headers: PackedStringArray, body: PackedByteArray) -> void:
	if response_code == 200:
		var json = JSON.parse_string(body.get_string_from_utf8())
		if json != null and typeof(json) in [TYPE_INT, TYPE_FLOAT]:
			global_caps_updated.emit(int(json))
