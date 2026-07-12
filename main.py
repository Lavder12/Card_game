#!/usr/bin/env python3
"""
Dustway: Desert Trader — Ultimate Edition
====================================================
Entry point of the modular refactored code.
"""

import sys
import os
import pygame

# DPI Scaling fix for Windows
try:
    import ctypes
    ctypes.windll.user32.SetProcessDPIAware()
except:
    pass

# Initialize pygame
pygame.init()

# Initialize audio/mixer
AUDIO_OK = True
try:
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
except:
    AUDIO_OK = False

# Import shared state and configuration
import src.state as state
state.AUDIO_OK = AUDIO_OK

from src.config import Settings, Stats, GM_NORMAL
from src.models import DEFAULT_PERSONALITY
from src.audio import SoundManager
from src.particles import ParticleSystem
from src.achievements import load_achievements
from src.ui import apply_resolution
from src.network import network_lobby_screen, run_network_match
from src.screens import (
    main_menu, run_tutorial, run_campaign, difficulty_menu,
    personality_select_menu, betting_menu, run_match
)

# Load settings and stats
state.app_settings = Settings.load()
state.app_stats = Stats.load()
state.app_settings.apply_language()
state.app_settings.apply_audio()

# Sync profile to Firebase for Friends feature
try:
    from src.network import FirebaseFriends
    FirebaseFriends.sync_profile(
        state.app_settings.friend_code, 
        state.app_settings.player_name, 
        state.app_settings.player_icon
    )
except Exception as e:
    print(f"Failed to sync profile: {e}")

# Initialize procedural audio, particles, and achievements
state.sounds = SoundManager()
state.particles = ParticleSystem()
load_achievements()

# Apply window resolution
apply_resolution(
    *map(int, state.app_settings.resolution.split("x")),
    fullscreen=state.app_settings.fullscreen
)

# Setup custom cursor
from src.config import rpath
cursor_path = rpath("assets", "cursor.png")
if os.path.exists(cursor_path):
    try:
        # Load and scale the custom cursor image
        # Using 55x55 to make the cursor slightly larger as requested
        cursor_img = pygame.image.load(cursor_path).convert_alpha()
        cursor_img = pygame.transform.smoothscale(cursor_img, (55, 55))
        
        # Create a Pygame Cursor object with hotspot at the top-left tip (0, 0)
        custom_cursor = pygame.cursors.Cursor((0, 0), cursor_img)
        pygame.mouse.set_cursor(custom_cursor)
    except Exception as e:
        print(f"Failed to load custom cursor: {e}")



# Play intro video
from src.intro import play_intro
play_intro(state.screen, rpath("assets", "intro", "intro.mp4"))

# Start background music
if state.AUDIO_OK:
    from src.config import MUSIC_PATH
    import os
    if os.path.exists(MUSIC_PATH):
        try:
            pygame.mixer.music.load(MUSIC_PATH)
            pygame.mixer.music.play(-1)
            pygame.mixer.music.set_volume(0.0 if state.app_settings.muted else state.app_settings.volume)
        except Exception as e:
            print(f"Failed to load/play music: {e}")

# Top-level game loop
while True:
    choice = main_menu()

    # ── Tutorial ──────────────────────────────────────────────
    if choice == "tutorial":
        run_tutorial()
        continue

    # ── Story Campaign ────────────────────────────────────────
    if choice == "campaign":
        run_campaign()
        continue

    # ── Network (vs Player) ───────────────────────────────────
    if choice == "network":
        nm = network_lobby_screen()
        if nm is None:
            continue
        run_network_match(nm)
        continue

    # ── vs Bot ────────────────────────────────────────────────
    if choice == "bot":
        diff = difficulty_menu()
        if diff is None:
            continue
            
        # Automatically assign personality based on difficulty to streamline the menu
        # easy -> benny, medium -> yesman, hard/impossible -> house
        pers_map = {"easy": "benny", "medium": "yesman", "hard": "house", "impossible": "house"}
        personality_key = pers_map.get(diff, DEFAULT_PERSONALITY)
        
        bet = betting_menu(diff)
        if bet is None:
            continue

        while True:
            wc, elapsed, caps_delta = run_match(diff, GM_NORMAL, personality_key, bet)
            if wc in ("menu", "quit_match"):
                break
            # "restart" → loop again with same settings
            bet = betting_menu(diff)
            if bet is None:
                break