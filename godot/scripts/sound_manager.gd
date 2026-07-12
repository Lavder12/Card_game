extends Node
# Autoload: SoundManager
# Handles background music and sound effects across the Godot project

var music_player: AudioStreamPlayer
var sfx_player: AudioStreamPlayer

var is_music_enabled: bool = true
var is_sfx_enabled: bool = true

func _ready() -> void:
	music_player = AudioStreamPlayer.new()
	music_player.name = "MusicPlayer"
	music_player.bus = "Master"
	add_child(music_player)
	
	sfx_player = AudioStreamPlayer.new()
	sfx_player.name = "SFXPlayer"
	sfx_player.bus = "Master"
	add_child(sfx_player)
	
	print("SoundManager initialized.")
	play_background_music("res://music/music.mp3")

func play_background_music(path: String) -> void:
	if not is_music_enabled: return
	if ResourceLoader.exists(path):
		var stream = load(path)
		if stream and stream is AudioStream:
			music_player.stream = stream
			music_player.volume_db = -12.0 # Comfortable ambient level
			music_player.play()
			print("Playing background music: ", path)

func stop_music() -> void:
	if music_player and music_player.playing:
		music_player.stop()

func play_sfx(sound_type: String) -> void:
	if not is_sfx_enabled: return
	# We can play pitch-shifted clicks or card swoosh effects using built-in pitch variations
	if sound_type == "click":
		_play_tone(800.0, 0.04, -18.0)
	elif sound_type == "card_drop":
		_play_tone(400.0, 0.08, -14.0)
	elif sound_type == "win":
		_play_tone(1000.0, 0.25, -10.0)
	elif sound_type == "lose":
		_play_tone(250.0, 0.35, -12.0)

func _play_tone(freq: float, duration: float, vol_db: float) -> void:
	# Generate a quick soft audio click/beep using AudioStreamGenerator if no wav file is loaded
	var generator = AudioStreamGenerator.new()
	generator.mix_rate = 44100
	generator.buffer_length = duration + 0.05
	
	var player = AudioStreamPlayer.new()
	player.stream = generator
	player.volume_db = vol_db
	add_child(player)
	player.play()
	
	var playback: AudioStreamGeneratorPlayback = player.get_stream_playback()
	if playback:
		var sample_rate = generator.mix_rate
		var total_samples = int(sample_rate * duration)
		for i in range(total_samples):
			var t = float(i) / sample_rate
			var envelope = 1.0 - (float(i) / total_samples) # Linear fade out
			var val = sin(t * freq * TAU) * envelope * 0.4
			playback.push_frame(Vector2(val, val))
	
	# Cleanup player after finishing
	get_tree().create_timer(duration + 0.2).timeout.connect(player.queue_free)
