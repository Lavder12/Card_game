import os
import json
from typing import Dict, List, Optional
import src.state as state
import src.config as cfg
from src.security import secure_save, secure_load

ACH_IDS = [
    "FIRST_WIN","STREAK_3","STREAK_5","STREAK_10",
    "FAST_WIN","SPEED_DEMON","PERFECT_26","JOKER_BOMB",
    "JACK_ATTACK","IMPOSSIBLE_WIN","TOURN_CHAMP",
    "CAPS_RICH","COMEBACK","HOT_SEAT_WIN","ALL_CARAVANS",
]

def load_achievements():
    data = secure_load(cfg.ACH_FILE)
    if data and isinstance(data, dict):
        state.ach_unlocked = data
        return
    state.ach_unlocked = {aid: False for aid in ACH_IDS}

def save_achievements():
    secure_save(cfg.ACH_FILE, state.ach_unlocked)

def unlock_achievement(aid: str):
    if state.ach_unlocked.get(aid): return
    state.ach_unlocked[aid] = True
    state.ach_popup_queue.append(aid)
    save_achievements()

def check_post_match_achievements(result, diff, mode, elapsed_ms,
                                   player_lost_first=False, all_three=False):
    if result == "win":
        unlock_achievement("FIRST_WIN")
        if state.app_stats.win_streak >= 3:  unlock_achievement("STREAK_3")
        if state.app_stats.win_streak >= 5:  unlock_achievement("STREAK_5")
        if state.app_stats.win_streak >= 10: unlock_achievement("STREAK_10")
        if elapsed_ms < 180_000: unlock_achievement("FAST_WIN")
        if elapsed_ms < 120_000: unlock_achievement("SPEED_DEMON")
        if diff == "impossible":  unlock_achievement("IMPOSSIBLE_WIN")
        if mode == cfg.GM_HOT_SEAT:   unlock_achievement("HOT_SEAT_WIN")
        if mode == cfg.GM_TOURNAMENT: unlock_achievement("TOURN_CHAMP")
        if player_lost_first:     unlock_achievement("COMEBACK")
        if all_three:             unlock_achievement("ALL_CARAVANS")
    if state.app_settings.caps >= 5000: unlock_achievement("CAPS_RICH")

def tick_achievement_popup(now: int) -> Optional[str]:
    """Returns current popup achievement id if active, else None."""
    if state.ach_popup_queue and now > state.ach_popup_until:
        aid = state.ach_popup_queue.pop(0)
        state.ach_popup_until = now + 3500
        tick_achievement_popup._current = aid
        return aid
    if now < state.ach_popup_until:
        return getattr(tick_achievement_popup, "_current", None)
    tick_achievement_popup._current = None
    return None

# store current popup id
tick_achievement_popup._current = None
