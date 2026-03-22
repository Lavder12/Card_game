#!/usr/bin/env python3
"""
Caravan (Fallout: New Vegas) — v4 ULTIMATE EDITION
====================================================
  Achievements (15), Bot personalities (Benny / Yes Man / House),
  Bot commentary + tell-animations, Caps betting, Card-back chooser (4),
  Tournament mode, Hot-seat 2-player, Timed mode (30s/turn),
  Match history, Streak / Leaderboard, Screen-shake + deal flash,
  Sound effects (procedural), Undo 5 levels, SFX volume slider,
  EN / RU localisation, Fullscreen, Resolution selector,

  NEW v4:
  ─ Mojave Campaign (5 sequential stages with lore + rewards)
  ─ AI vs AI Spectator mode (watch two bots fight, adjustable speed)
  ─ Deck Archetypes (The Blitz / The Wrecker / Balanced + custom)
  ─ Particle system (burst at 26, confetti on win)
  ─ Card hover-preview (enlarged card above hand on hover)
  ─ Bot tell bubbles (personality reacts to Jack / Joker / King)
  ─ Custom player name (set in Settings)
  ─ Streak fire on main menu grows with streak
"""

import pygame
import random
import sys
import json
import os
import copy
import math
import time as _time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any

# ============================================================
# BASE CONSTANTS
# ============================================================
_BASE_W, _BASE_H = 1280, 720
FPS = 60

WIDTH, HEIGHT = _BASE_W, _BASE_H

MARGIN    = 22
GAP       = 12
TOP_BAR_H = 100

CARD_W, CARD_H     = 70, 98
SELECT_RAISE       = 14
PIC_BADGE_W        = 22
PIC_BADGE_H        = 22
GRID_CARD_W        = 82
GRID_CARD_H        = 58

MAX_VISIBLE_STACK      = 9
STACK_OVERLAP_X        = 28
STACK_OVERLAP_X_TIGHT  = 18
STACK_PAD_X            = 14

HAND_TARGET_SIZE    = 5
HAND_OPENING_SIZE   = 8
STALEMATE_THRESHOLD = 20
UNDO_LEVELS         = 5
TIMED_TURN_MS       = 30_000   # 30 seconds per turn in timed mode

BOT_DELAY_MS: Dict[str, int] = {
    "easy": 600, "medium": 420, "hard": 260, "impossible": 140,
}

MAX_ART_CACHE_ENTRIES = 512

_BASE_CARD_W = 102
_BASE_CARD_H = 144

# ── Colours ──────────────────────────────────────────────────
BG          = (10,  16,  12)
PANEL       = (18,  28,  20)
PANEL_2     = (14,  22,  16)
PANEL_BORD  = (80,  110, 60)
PANEL_GLOW  = (50,  90,  40)
CARD_FACE   = (244, 238, 218)
CARD_BACK_C = (32,  80,  40)
CARD_SEL    = (200, 170, 50)
CARD_HOVER  = (240, 200, 60)
CARD_RED    = (175, 25,  30)
CARD_BLACK  = (22,  22,  30)
CARD_JOKER  = (110, 35,  150)
TEXT        = (220, 212, 175)
TEXT_DIM    = (140, 132, 100)
BTN         = (38,  72,  42)
BTN_H       = (58,  118, 65)
BTN_TXT     = (230, 225, 190)
ACCENT      = (195, 162, 52)
RED         = (230, 80,  80)
YELLOW      = (210, 185, 72)
BLACK       = (0,   0,   0)
OUT_OK      = (100, 200, 110)
OUT_BAD     = (200, 70,  70)
TOOLTIP_BG  = (18,  28,  20)
UNDO_CLR    = (90,  140, 190)
RES_ACTIVE  = (70,  130, 195)
RES_ACT_H   = (100, 165, 230)
CAPS_CLR    = (210, 175, 55)
TIMER_OK    = (80,  180, 90)
TIMER_WARN  = (210, 160, 40)
TIMER_CRIT  = (220, 60,  60)
ACH_BG      = (22,  40,  24)
ACH_BORD    = (160, 130, 50)

SUIT_SYMBOL: Dict[str, str]   = {"S":"♠","H":"♥","D":"♦","C":"♣"}
SUIT_COLOR:  Dict[str, Tuple] = {"S":CARD_BLACK,"C":CARD_BLACK,"H":CARD_RED,"D":CARD_RED}

# ── Paths ─────────────────────────────────────────────────────
BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))

def rpath(*p): return os.path.join(BASE_DIR, *p)

SETTINGS_FILE = rpath("settings.json")
DECK_FILE     = rpath("deck.json")
STATS_FILE    = rpath("stats.json")
HISTORY_FILE  = rpath("history.json")
ACH_FILE      = rpath("achievements.json")
CAMPAIGN_FILE = rpath("campaign.json")
MUSIC_PATH    = rpath("music", "music.mp3")
CARDS_DIR     = rpath("assets", "cards")

USE_ART             = True
SHOW_LABEL_OVER_ART = False
ART_DEBUG           = False

RESOLUTIONS: List[Tuple[int,int,str]] = [
    (1024, 576,  "1024×576"),
    (1280, 720,  "1280×720"),
    (1600, 900,  "1600×900"),
    (1920, 1080, "1920×1080"),
]

# Game modes
GM_NORMAL      = "normal"
GM_HOT_SEAT    = "hot_seat"
GM_TIMED       = "timed"
GM_TOURNAMENT  = "tournament"

# ============================================================
# LOCALISATION
# ============================================================
STRINGS: Dict[str, Dict[str, str]] = {
"en": {
    "title":"Caravan","subtitle":"(Fallout: New Vegas)",
    "play":"Play","deck":"Deck","settings":"Settings",
    "stats":"Stats","quit":"Quit","back":"Back","save":"Save","clear":"Clear",
    "settings_title":"Settings","volume_pct":"Volume: {}%",
    "sound_on":"Sound: ON","sound_off":"Sound: OFF",
    "sfx_pct":"SFX: {}%",
    "bot_deck_yes":"Bot uses your deck: YES","bot_deck_no":"Bot uses your deck: NO",
    "lang_btn":"Language: EN","resolution":"Resolution",
    "card_back":"Card Back: {}",
    "diff_title":"Select Difficulty","easy":"Easy","medium":"Medium",
    "hard":"Hard","impossible":"Impossible",
    "stats_title":"Statistics","games_played":"Games played:  {}",
    "wins_line":"Wins:          {}","losses_line":"Losses:        {}",
    "draws_line":"Draws:         {}","avg_time_line":"Avg time:      {}",
    "streak_line":"Best streak:   {}","caps_line":"Caps:          {}",
    "reset_stats":"Reset Stats",
    "deck_builder":"Deck Builder","standard_54":"Standard 54","auto_30":"Auto 30",
    "selected_cnt":"Selected: {} (min 30)","deck_saved":"Deck saved!",
    "need_30":"Need at least 30 cards!",
    "achievements":"Achievements","ach_unlocked":"Unlocked: {}/{}",
    "history":"Match History","leaderboard":"Leaderboard",
    "mode_title":"Game Mode",
    "mode_normal":"vs Bot","mode_hotSeat":"Hot Seat (2P)",
    "mode_timed":"Timed Mode","mode_tournament":"Tournament",
    "choose_bot":"Choose Opponent",
    "bot_benny":"Benny","bot_yesman":"Yes Man","bot_house":"Mr House",
    "betting_title":"Place Your Bet","caps_balance":"Your caps: {}",
    "bet_amount":"Bet: {} caps","bet_confirm":"Confirm Bet",
    "phase_lbl":"Phase: {}","diff_lbl":"Diff: {}","time_lbl":"Time: {}",
    "sound_lbl":"Sound: {}%","sound_off_lbl":"Sound: OFF",
    "stats_bar":"W:{} L:{} D:{}","bot_thinking":"Bot thinking",
    "player_deck_lbl":"Deck: {}  Discard: {}","bot_deck_lbl":"Bot: {}  Discard: {}",
    "undo_hint":"[U] Undo ({})","stalemate_warn":"⚠ Stalemate {}/{}",
    "hint_opening":"Opening: place A-10 on 3 empty caravans",
    "hint_main":"LMB: play  |  RMB: discard/disband  |  1/2/3: caravan  |  D: discard  |  U: undo  |  ESC: pause",
    "bot_caravans":"Bot caravans","your_caravans":"Your caravans",
    "your_hand":"Your hand","score_fmt":"Score: {}","score_sold":"Score: {} ★",
    "p1_caravans":"P1 caravans","p2_caravans":"P2 caravans","p1_hand":"P1 hand","p2_hand":"P2 hand",
    "player_wins":"Player wins!","bot_wins":"Bot wins!",
    "draw_stalemate":"Draw — stalemate!",
    "player_wins_deck":"Player wins! (bot deck empty)",
    "bot_wins_deck":"Bot wins! (your deck empty)",
    "p1_wins":"Player 1 wins!","p2_wins":"Player 2 wins!",
    "match_time":"Match time: {}","stats_end":"W:{}  L:{}  D:{}  avg: {}",
    "play_again":"Play Again","main_menu_btn":"Main Menu",
    "opening_nums_only":"Opening: numbers only (A-10)",
    "caravan_started":"Caravan already started",
    "nothing_disband":"Nothing to disband",
    "face_needs_target":"Face card needs a target number card",
    "undone":"Undone!","bot_deck_empty_win":"Bot deck empty — player wins!",
    "base_value":"Base value: {}","attached":"Attached: {}","effective":"Effective: {}  (×{})",
    "timer_lbl":"Turn: {}s","timer_expired":"Time's up — auto discard!",
    "pass_screen_title":"Pass to {}","pass_screen_hint":"Click or press SPACE to continue",
    "tourn_title":"Tournament","tourn_round":"Round {}","tourn_win":"WIN","tourn_loss":"LOSS",
    "tourn_champion":"Tournament Champion!","tourn_eliminated":"Eliminated in round {}",
    "caps_won":"+{} caps!","caps_lost":"-{} caps","no_caps":"Not enough caps to bet!",
    "ach_title":"Achievements",
    "FIRST_WIN":"First Win","STREAK_3":"Hot Streak","STREAK_5":"On Fire",
    "STREAK_10":"Unstoppable","FAST_WIN":"Speed Dealer","SPEED_DEMON":"Speed Demon",
    "PERFECT_26":"Perfect Score","JOKER_BOMB":"Nuclear Option",
    "JACK_ATTACK":"Jack the Ripper","IMPOSSIBLE_WIN":"Against All Odds",
    "TOURN_CHAMP":"Tournament Champion","CAPS_RICH":"Caps Collector",
    "COMEBACK":"Against All Odds II","HOT_SEAT_WIN":"Face to Face",
    "ALL_CARAVANS":"Trifecta",
    "FIRST_WIN_d":"Win your first match",
    "STREAK_3_d":"Win 3 matches in a row",
    "STREAK_5_d":"Win 5 matches in a row",
    "STREAK_10_d":"Win 10 matches in a row",
    "FAST_WIN_d":"Win in under 3 minutes",
    "SPEED_DEMON_d":"Win in under 2 minutes",
    "PERFECT_26_d":"Close a caravan at exactly 26",
    "JOKER_BOMB_d":"Clear 3+ cards with one Joker",
    "JACK_ATTACK_d":"Remove a card worth 10 with a Jack",
    "IMPOSSIBLE_WIN_d":"Beat Impossible difficulty",
    "TOURN_CHAMP_d":"Win a full tournament",
    "CAPS_RICH_d":"Accumulate 5 000 caps",
    "COMEBACK_d":"Win after your first caravan is beaten",
    "HOT_SEAT_WIN_d":"Win a hot-seat match",
    "ALL_CARAVANS_d":"Win all 3 caravans simultaneously",
},
"ru": {
    "title":"Каравáн","subtitle":"(Fallout: New Vegas)",
    "play":"Играть","deck":"Колода","settings":"Настройки",
    "stats":"Статистика","quit":"Выход","back":"Назад","save":"Сохранить","clear":"Очистить",
    "settings_title":"Настройки","volume_pct":"Громкость: {}%",
    "sound_on":"Звук: ВКЛ","sound_off":"Звук: ВЫКЛ","sfx_pct":"SFX: {}%",
    "bot_deck_yes":"Бот из вашей колоды: ДА","bot_deck_no":"Бот из вашей колоды: НЕТ",
    "lang_btn":"Язык: RU","resolution":"Разрешение","card_back":"Рубашка: {}",
    "diff_title":"Сложность","easy":"Лёгкий","medium":"Средний",
    "hard":"Сложный","impossible":"Невозможный",
    "stats_title":"Статистика","games_played":"Игр сыграно:  {}",
    "wins_line":"Побед:        {}","losses_line":"Поражений:    {}",
    "draws_line":"Ничьих:       {}","avg_time_line":"Ср. время:    {}",
    "streak_line":"Лучшая серия: {}","caps_line":"Крышки:       {}",
    "reset_stats":"Сбросить",
    "deck_builder":"Редактор колоды","standard_54":"Стандарт 54","auto_30":"Авто 30",
    "selected_cnt":"Выбрано: {} (мин. 30)","deck_saved":"Колода сохранена!",
    "need_30":"Нужно минимум 30 карт!",
    "achievements":"Достижения","ach_unlocked":"Получено: {}/{}",
    "history":"История матчей","leaderboard":"Таблица лидеров",
    "mode_title":"Режим игры",
    "mode_normal":"vs Бот","mode_hotSeat":"Вдвоём (2 игрока)",
    "mode_timed":"На время","mode_tournament":"Турнир",
    "choose_bot":"Выбор противника",
    "bot_benny":"Бенни","bot_yesman":"Да-человек","bot_house":"Мистер Хаус",
    "betting_title":"Ставка","caps_balance":"Ваши крышки: {}",
    "bet_amount":"Ставка: {} крышек","bet_confirm":"Подтвердить",
    "phase_lbl":"Фаза: {}","diff_lbl":"Сложн.: {}","time_lbl":"Время: {}",
    "sound_lbl":"Звук: {}%","sound_off_lbl":"Звук: ВЫКЛ",
    "stats_bar":"П:{} П:{} Н:{}","bot_thinking":"Бот думает",
    "player_deck_lbl":"Колода: {}  Сброс: {}","bot_deck_lbl":"Бот: {}  Сброс: {}",
    "undo_hint":"[U] Отмена ({})","stalemate_warn":"⚠ Пат {}/{}",
    "hint_opening":"Начало: выложите A-10 на 3 пустых каравана",
    "hint_main":"ЛКМ: ход  |  ПКМ: сброс  |  1/2/3: каравин  |  D: сброс  |  U: отмена  |  ESC: пауза",
    "bot_caravans":"Каравины бота","your_caravans":"Ваши каравины",
    "your_hand":"Ваша рука","score_fmt":"Счёт: {}","score_sold":"Счёт: {} ★",
    "p1_caravans":"Каравины игр. 1","p2_caravans":"Каравины игр. 2",
    "p1_hand":"Рука игрока 1","p2_hand":"Рука игрока 2",
    "player_wins":"Игрок победил!","bot_wins":"Бот победил!",
    "draw_stalemate":"Ничья — пат!",
    "player_wins_deck":"Игрок победил! (колода бота пуста)",
    "bot_wins_deck":"Бот победил! (ваша колода пуста)",
    "p1_wins":"Игрок 1 победил!","p2_wins":"Игрок 2 победил!",
    "match_time":"Время матча: {}","stats_end":"П:{}  П:{}  Н:{}  ср: {}",
    "play_again":"Играть снова","main_menu_btn":"Главное меню",
    "opening_nums_only":"Начало: только числа (A-10)",
    "caravan_started":"Каравин уже начат",
    "nothing_disband":"Нечего распускать",
    "face_needs_target":"Фигура должна бить числовую карту",
    "undone":"Отменено!","bot_deck_empty_win":"Колода бота пуста — победа!",
    "base_value":"Базовое: {}","attached":"Прикреплено: {}","effective":"Итого: {}  (×{})",
    "timer_lbl":"Ход: {}с","timer_expired":"Время вышло — авто-сброс!",
    "pass_screen_title":"Ход передаётся {}","pass_screen_hint":"Нажмите пробел или щёлкните",
    "tourn_title":"Турнир","tourn_round":"Раунд {}","tourn_win":"ПОБЕДА","tourn_loss":"ПОРАЖЕНИЕ",
    "tourn_champion":"Чемпион турнира!","tourn_eliminated":"Выбыл в раунде {}",
    "caps_won":"+{} крышек!","caps_lost":"-{} крышек","no_caps":"Недостаточно крышек!",
    "ach_title":"Достижения",
    "FIRST_WIN":"Первая победа","STREAK_3":"Горячая серия","STREAK_5":"В огне",
    "STREAK_10":"Неудержимый","FAST_WIN":"Быстрый дилер","SPEED_DEMON":"Демон скорости",
    "PERFECT_26":"Идеальный счёт","JOKER_BOMB":"Ядерный вариант",
    "JACK_ATTACK":"Валет-потрошитель","IMPOSSIBLE_WIN":"Против всех шансов",
    "TOURN_CHAMP":"Чемпион турнира","CAPS_RICH":"Коллекционер крышек",
    "COMEBACK":"Камбэк","HOT_SEAT_WIN":"Лицом к лицу","ALL_CARAVANS":"Трифекта",
    "FIRST_WIN_d":"Одержите первую победу",
    "STREAK_3_d":"Победите 3 раза подряд",
    "STREAK_5_d":"Победите 5 раз подряд",
    "STREAK_10_d":"Победите 10 раз подряд",
    "FAST_WIN_d":"Победите менее чем за 3 минуты",
    "SPEED_DEMON_d":"Победите менее чем за 2 минуты",
    "PERFECT_26_d":"Закройте каравин с точно 26 очками",
    "JOKER_BOMB_d":"Уберите 3+ карты одним Джокером",
    "JACK_ATTACK_d":"Уберите карту стоимостью 10 Валетом",
    "IMPOSSIBLE_WIN_d":"Победите на невозможной сложности",
    "TOURN_CHAMP_d":"Выиграйте полный турнир",
    "CAPS_RICH_d":"Накопите 5 000 крышек",
    "COMEBACK_d":"Победите, проиграв первый каравин",
    "HOT_SEAT_WIN_d":"Победите в режиме вдвоём",
    "ALL_CARAVANS_d":"Выиграйте все 3 каравина одновременно",
},
}

_LANG = "en"
def T(key: str, *args) -> str:
    s = STRINGS.get(_LANG, STRINGS["en"]).get(key, STRINGS["en"].get(key, key))
    return s.format(*args) if args else s


# ============================================================
# UTILITY
# ============================================================
def clamp(x, lo=0.0, hi=255.0): return max(lo, min(hi, x))
def lighten(c, a=18): return (int(clamp(c[0]+a)),int(clamp(c[1]+a)),int(clamp(c[2]+a)))
def format_time_ms(ms):
    t = max(0, ms // 1000); return f"{t//60:02d}:{t%60:02d}"
def lerp(a, b, t): return a + (b-a)*t


# ============================================================
# SETTINGS
# ============================================================
@dataclass
class Settings:
    volume:               float = 0.85
    sfx_volume:           float = 0.70
    muted:                bool  = False
    bot_uses_player_deck: bool  = True
    language:             str   = "en"
    resolution:           str   = "1280x720"
    fullscreen:           bool  = True
    card_back:            int   = 0       # 0-3
    caps:                 int   = 500     # starting caps
    player_name:          str   = "Player"

    def apply_audio(self):
        if AUDIO_OK:
            pygame.mixer.music.set_volume(0.0 if self.muted else self.volume)

    def apply_language(self):
        global _LANG; _LANG = self.language

    def save(self):
        try:
            with open(SETTINGS_FILE,"w",encoding="utf-8") as f:
                json.dump(self.__dict__, f, indent=2)
        except: pass

    @classmethod
    def load(cls):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE,"r",encoding="utf-8") as f:
                    d = json.load(f)
                s = cls()
                for k,v in d.items():
                    if hasattr(s,k): setattr(s,k,v)
                return s
            except: pass
        return cls()


# ============================================================
# STATS + MATCH HISTORY
# ============================================================
@dataclass
class MatchRecord:
    date:       str
    result:     str
    difficulty: str
    mode:       str
    duration_s: int
    caps_delta: int

@dataclass
class Stats:
    wins:          int = 0
    losses:        int = 0
    draws:         int = 0
    total_time_ms: int = 0
    games_played:  int = 0
    win_streak:    int = 0
    best_streak:   int = 0

    def record(self, result, elapsed_ms):
        self.games_played  += 1
        self.total_time_ms += elapsed_ms
        if result == "win":
            self.wins += 1
            self.win_streak += 1
            self.best_streak = max(self.best_streak, self.win_streak)
        elif result == "loss":
            self.losses += 1; self.win_streak = 0
        else:
            self.draws += 1; self.win_streak = 0

    def avg_time_str(self):
        if self.games_played == 0: return "00:00"
        return format_time_ms(self.total_time_ms // self.games_played)

    def save(self):
        try:
            with open(STATS_FILE,"w",encoding="utf-8") as f:
                json.dump(self.__dict__, f, indent=2)
        except: pass

    @classmethod
    def load(cls):
        if os.path.exists(STATS_FILE):
            try:
                with open(STATS_FILE,"r",encoding="utf-8") as f:
                    d = json.load(f)
                s = cls()
                for k,v in d.items():
                    if hasattr(s,k): setattr(s,k,v)
                return s
            except: pass
        return cls()

def load_history() -> List[MatchRecord]:
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE,"r",encoding="utf-8") as f:
                return [MatchRecord(**r) for r in json.load(f)]
        except: pass
    return []

def save_history(h: List[MatchRecord]):
    try:
        with open(HISTORY_FILE,"w",encoding="utf-8") as f:
            json.dump([r.__dict__ for r in h[-10:]], f, indent=2)
    except: pass

def add_history(result, diff, mode, elapsed_ms, caps_delta):
    h = load_history()
    import datetime
    h.append(MatchRecord(
        date=datetime.datetime.now().strftime("%d.%m %H:%M"),
        result=result, difficulty=diff, mode=mode,
        duration_s=elapsed_ms//1000, caps_delta=caps_delta
    ))
    save_history(h)


# ============================================================
# ACHIEVEMENTS
# ============================================================
ACH_IDS = [
    "FIRST_WIN","STREAK_3","STREAK_5","STREAK_10",
    "FAST_WIN","SPEED_DEMON","PERFECT_26","JOKER_BOMB",
    "JACK_ATTACK","IMPOSSIBLE_WIN","TOURN_CHAMP",
    "CAPS_RICH","COMEBACK","HOT_SEAT_WIN","ALL_CARAVANS",
]

_ach_unlocked: Dict[str,bool] = {}
_ach_popup_queue: List[str]   = []   # ids waiting to show
_ach_popup_until: int         = 0    # ms timestamp

def load_achievements():
    global _ach_unlocked
    if os.path.exists(ACH_FILE):
        try:
            with open(ACH_FILE,"r",encoding="utf-8") as f:
                _ach_unlocked = json.load(f)
            return
        except: pass
    _ach_unlocked = {aid: False for aid in ACH_IDS}

def save_achievements():
    try:
        with open(ACH_FILE,"w",encoding="utf-8") as f:
            json.dump(_ach_unlocked, f, indent=2)
    except: pass

def unlock_achievement(aid: str):
    if _ach_unlocked.get(aid): return
    _ach_unlocked[aid] = True
    _ach_popup_queue.append(aid)
    save_achievements()

def check_post_match_achievements(result, diff, mode, elapsed_ms,
                                   player_lost_first=False, all_three=False):
    if result == "win":
        unlock_achievement("FIRST_WIN")
        if app_stats.win_streak >= 3:  unlock_achievement("STREAK_3")
        if app_stats.win_streak >= 5:  unlock_achievement("STREAK_5")
        if app_stats.win_streak >= 10: unlock_achievement("STREAK_10")
        if elapsed_ms < 180_000: unlock_achievement("FAST_WIN")
        if elapsed_ms < 120_000: unlock_achievement("SPEED_DEMON")
        if diff == "impossible":  unlock_achievement("IMPOSSIBLE_WIN")
        if mode == GM_HOT_SEAT:   unlock_achievement("HOT_SEAT_WIN")
        if mode == GM_TOURNAMENT: unlock_achievement("TOURN_CHAMP")
        if player_lost_first:     unlock_achievement("COMEBACK")
        if all_three:             unlock_achievement("ALL_CARAVANS")
    if app_settings.caps >= 5000: unlock_achievement("CAPS_RICH")

def tick_achievement_popup(now: int) -> Optional[str]:
    """Returns current popup achievement id if active, else None."""
    global _ach_popup_until
    if _ach_popup_queue and now > _ach_popup_until:
        aid = _ach_popup_queue.pop(0)
        _ach_popup_until = now + 3500
        tick_achievement_popup._current = aid
        return aid
    if now < _ach_popup_until:
        return getattr(tick_achievement_popup, "_current", None)
    tick_achievement_popup._current = None
    return None
# store current popup id
tick_achievement_popup._current = None


# ============================================================
# BOT PERSONALITIES
# ============================================================
@dataclass
class BotPersonality:
    key:         str
    display_key: str        # T() key for localised name
    noise:       Dict[str,int]          # override noise per difficulty
    attack_bias: int        # extra score when sabotaging player
    defense_bias:int        # extra score when playing for self
    commentary:  List[str]  # random lines shown as bot messages
    delay_mult:  float      # multiplier on BOT_DELAY_MS

BENNY = BotPersonality(
    key="benny", display_key="bot_benny",
    noise={"easy":200,"medium":80,"hard":15,"impossible":5},
    attack_bias=180, defense_bias=0,
    commentary=[
        "You've got a lot of nerve...",
        "This town ain't big enough.",
        "Let's see you recover from that.",
        "Lucky? We'll see about that.",
        "Nobody outsmarts the Benny.",
    ],
    delay_mult=1.0,
)
YES_MAN = BotPersonality(
    key="yes_man", display_key="bot_yesman",
    noise={"easy":300,"medium":150,"hard":60,"impossible":20},
    attack_bias=-80, defense_bias=50,
    commentary=[
        "Oh sure, whatever you say!",
        "I can definitely work with that!",
        "Great idea! For you, I mean.",
        "No complaints here!",
        "I'm totally fine with this situation.",
    ],
    delay_mult=1.2,
)
HOUSE = BotPersonality(
    key="house", display_key="bot_house",
    noise={"easy":120,"medium":40,"hard":8,"impossible":2},
    attack_bias=60, defense_bias=60,
    commentary=[
        "Probability favors the House.",
        "Calculated.",
        "The odds are... not in your favour.",
        "Efficient.",
        "The House always wins.",
    ],
    delay_mult=0.8,
)

PERSONALITIES = {"benny": BENNY, "yes_man": YES_MAN, "house": HOUSE}
DEFAULT_PERSONALITY = "benny"


# ============================================================
# CARD DATACLASSES
# ============================================================
@dataclass(frozen=True)
class Card:
    rank: str
    suit: Optional[str] = None

    def is_number(self): return self.rank=="A" or self.rank.isdigit()
    def is_picture(self): return self.rank in ("J","Q","K","JKR")

    def value(self):
        if self.rank=="A": return 1
        if self.rank.isdigit(): return int(self.rank)
        return 0

    def label(self):
        if self.rank=="JKR": return "🃏"
        return f"{self.rank}{SUIT_SYMBOL.get(self.suit,'')}"

    def key(self):
        return "JKR" if self.rank=="JKR" else f"{self.rank}-{self.suit}"

    def display_name(self):
        sn={"S":"Spades","H":"Hearts","D":"Diamonds","C":"Clubs"}
        rn={"A":"Ace","J":"Jack","Q":"Queen","K":"King","JKR":"Joker"}
        r=rn.get(self.rank,self.rank); s=sn.get(self.suit or "","")
        return f"{r} of {s}" if s else r


@dataclass
class NumEntry:
    card: Card
    pics: List[Card] = field(default_factory=list)

    def kings_count(self): return sum(1 for p in self.pics if p.rank=="K")
    def effective_value(self): return self.card.value()*(2**self.kings_count())

    def tooltip_lines(self):
        lines=[self.card.display_name(), T("base_value",self.card.value())]
        if self.pics:
            lines.append(T("attached", ", ".join("★" if p.rank=="JKR" else p.rank for p in self.pics)))
        kc=self.kings_count()
        if kc: lines.append(T("effective",self.effective_value(),2**kc))
        return lines


@dataclass
class Caravan:
    nums: List[NumEntry] = field(default_factory=list)

    def empty(self): return len(self.nums)==0
    def top(self): return self.nums[-1] if self.nums else None

    def base_direction(self):
        if len(self.nums)<2: return None
        a,b=self.nums[-2].card.value(),self.nums[-1].card.value()
        return "up" if b>a else "down" if b<a else None

    def effective_direction(self):
        base=self.base_direction()
        if base is None: return None
        top=self.top()
        if not top: return base
        q=sum(1 for p in top.pics if p.rank=="Q")
        return ("down" if base=="up" else "up") if q%2==1 else base

    def effective_suit(self):
        top=self.top()
        if not top: return None
        queens=[p for p in top.pics if p.rank=="Q" and p.suit in SUIT_SYMBOL]
        return queens[-1].suit if queens else top.card.suit

    def score(self): return sum(ne.effective_value() for ne in self.nums)
    def for_sale(self): return 21<=self.score()<=26

    def trend(self):
        s=self.score()
        if len(self.nums)<1 or s<=22: return 0
        d=self.effective_direction()
        if d=="up": return self.nums[-1].card.value()
        if d=="down" and s>26: return -self.nums[-1].card.value()
        return 0


@dataclass
class PlayerState:
    name:     str
    caravans: List[Caravan]
    deck:     List[Card]
    discard:  List[Card]
    hand:     List[Card]


# ============================================================
# DECK MANAGEMENT
# ============================================================
def standard_card_list(include_jokers=True):
    ranks=["A"]+[str(i) for i in range(2,11)]+["J","Q","K"]
    suits=["S","H","D","C"]
    deck=[Card(r,s) for s in suits for r in ranks]
    if include_jokers: deck+=[Card("JKR"),Card("JKR")]
    return deck

def load_deck_selection():
    if not os.path.exists(DECK_FILE): return None
    try:
        with open(DECK_FILE,"r",encoding="utf-8") as f: data=json.load(f)
        if isinstance(data,dict) and isinstance(data.get("selected_keys"),list):
            valid={c.key() for c in standard_card_list(True)}
            keys=[str(k) for k in data["selected_keys"] if str(k) in valid]
            seen,uniq=set(),[]
            for k in keys:
                if k not in seen: uniq.append(k); seen.add(k)
            return uniq
    except: pass
    return None

def save_deck_selection(keys):
    try:
        with open(DECK_FILE,"w",encoding="utf-8") as f:
            json.dump({"selected_keys":keys}, f, ensure_ascii=False, indent=2)
    except: pass

def build_deck_from_selection(keys):
    all_cards=standard_card_list(True)
    if not keys:
        deck=list(all_cards); random.shuffle(deck); return deck
    by_key={c.key():c for c in all_cards}
    deck=[by_key[k] for k in keys if k in by_key]
    random.shuffle(deck); return deck

def ensure_min30_selection(keys):
    valid=[c.key() for c in standard_card_list(True)]
    s=set(keys); pool=[k for k in valid if k not in s]
    random.shuffle(pool)
    while len(keys)<30 and pool: keys.append(pool.pop())
    return keys

def draw_to_hand(p,target):
    while len(p.hand)<target:
        if not p.deck: return False
        p.hand.append(p.deck.pop())
    return True

def move_card_to_discard(p,c): p.discard.append(c)

def move_entry_to_discard(p,entry):
    move_card_to_discard(p,entry.card)
    for pc in entry.pics: move_card_to_discard(p,pc)


# ============================================================
# GAME RULES
# ============================================================
def can_attach_picture(entry): return len(entry.pics)<3

def can_play_number_on_caravan(card,caravan):
    if not card.is_number(): return False
    v=card.value()
    if caravan.empty(): return True
    top=caravan.top(); last_v=top.card.value()
    if v==last_v: return False
    if len(caravan.nums)==1: return True
    direction=caravan.effective_direction()
    suit_needed=caravan.effective_suit()
    by_dir=(v>last_v if direction=="up" else v<last_v if direction=="down" else False)
    by_suit=(card.suit==suit_needed)
    return by_dir or by_suit

def can_play_picture_on_target(pic,entry,is_last):
    if not pic.is_picture(): return False
    if not can_attach_picture(entry): return False
    if pic.rank=="Q": return is_last
    return True

def apply_jack(actor,caravan,idx):
    entry=caravan.nums.pop(idx); move_entry_to_discard(actor,entry)

def apply_king(entry,king): entry.pics.append(king)
def apply_queen(entry,queen): entry.pics.append(queen)

def apply_joker(actor,p1,p2,target_entry,joker_card):
    target_entry.pics.append(joker_card)
    tgt_rank=target_entry.card.rank; tgt_suit=target_entry.card.suit
    def should_remove(ne):
        if ne is target_entry: return False
        return ne.card.suit==tgt_suit if tgt_rank=="A" else ne.card.rank==tgt_rank
    removed=0
    for owner in (p1,p2):
        for cav in owner.caravans:
            keep,rem=[],[]
            for ne in cav.nums:
                (rem if should_remove(ne) else keep).append(ne)
            for ne in rem:
                move_entry_to_discard(actor,ne); removed+=1
            cav.nums=keep
    if removed>=3: unlock_achievement("JOKER_BOMB")

def discard_hand_card(actor,idx):
    if not (0<=idx<len(actor.hand)): return False
    move_card_to_discard(actor,actor.hand.pop(idx)); return True

def disband_caravan(actor,cav_i):
    if cav_i not in (0,1,2): return False
    cav=actor.caravans[cav_i]
    if cav.empty(): return False
    for ne in cav.nums: move_entry_to_discard(actor,ne)
    cav.nums=[]; return True

# Deferred particle bursts - populated by game logic, consumed by draw_board
_deferred_bursts: list = []

def play_number(actor,card_idx,cav_i):
    if not (0<=card_idx<len(actor.hand)): return False,"No such card."
    if cav_i not in (0,1,2): return False,"Invalid caravan."
    card=actor.hand[card_idx]
    if not card.is_number(): return False,"Not a number card."
    if not can_play_number_on_caravan(card,actor.caravans[cav_i]):
        return False,"Invalid play."
    actor.caravans[cav_i].nums.append(NumEntry(card=card))
    actor.hand.pop(card_idx)
    # Check perfect 26 — burst particles at caravan centre
    sc = actor.caravans[cav_i].score()
    if sc == 26:
        unlock_achievement("PERFECT_26")
        # We don't have screen coords here, so we store a deferred burst
        _deferred_bursts.append(("cav26", cav_i, actor.name))
    return True,""

def play_picture(actor,opponent,card_idx,target_owner,cav_i,entry_i):
    if not (0<=card_idx<len(actor.hand)): return False,"No such card."
    pic=actor.hand[card_idx]
    if not pic.is_picture(): return False,"Not a face card."
    if cav_i not in (0,1,2): return False,"Invalid caravan."
    cav=target_owner.caravans[cav_i]
    if not (0<=entry_i<len(cav.nums)): return False,"Invalid target."
    entry=cav.nums[entry_i]; is_last=(entry_i==len(cav.nums)-1)
    if not can_play_picture_on_target(pic,entry,is_last):
        return False,"Invalid (Q=last card only / limit 3)."
    if pic.rank=="J":
        if entry.effective_value()==10: unlock_achievement("JACK_ATTACK")
        apply_jack(actor,cav,entry_i)
    elif pic.rank=="K": apply_king(entry,pic)
    elif pic.rank=="Q": apply_queen(entry,pic)
    elif pic.rank=="JKR": apply_joker(actor,actor,opponent,entry,pic)
    actor.hand.pop(card_idx)
    return True,""


# ============================================================
# WIN CONDITIONS
# ============================================================
def slot_outcome(pv,ps,bv,bs):
    if not ps and not bs: return "not_ready",None
    if ps and not bs: return "ready","player"
    if bs and not ps: return "ready","bot"
    if pv==bv: return "tie",None
    return "ready","player" if pv>bv else "bot"

# FIX #3 + #5: check_game_end now correctly allows 2-1 wins.
# Previously it returned False early if any slot was not_ready/tie,
# preventing a player from winning 2-0 while the third slot was undecided.
# Also fixed the fallthrough bug where reaching the end of the loop
# automatically declared the bot a winner even with 0 or 1 wins.
def check_game_end(player,bot):
    wp=wb=0
    for i in range(3):
        st,w=slot_outcome(player.caravans[i].score(),player.caravans[i].for_sale(),
                           bot.caravans[i].score(),bot.caravans[i].for_sale())
        if st=="ready":
            if w=="player": wp+=1
            else: wb+=1
    if wp>=2: return True,"player",T("player_wins")
    if wb>=2: return True,"bot",T("bot_wins")
    return False,None,""


# ============================================================
# BOT AI (with personalities)
# ============================================================
def _clone(p):
    return PlayerState(
        name=p.name,
        caravans=[Caravan([NumEntry(ne.card,list(ne.pics)) for ne in c.nums])
                  for c in p.caravans],
        deck=[], discard=[], hand=list(p.hand),
    )

def heuristic(player,bot):
    score=0
    for i in range(3):
        bv,bs=bot.caravans[i].score(),bot.caravans[i].for_sale()
        pv,ps=player.caravans[i].score(),player.caravans[i].for_sale()
        st,w=slot_outcome(pv,ps,bv,bs)
        if st=="ready":   score+=600 if w=="bot" else -600
        elif st=="tie":   score-=120
        else:
            score+=bv*4 if bv<=26 else -(bv-26)*60
            score-=pv*4 if pv<=26 else -(pv-26)*30
        if bs: score+=250+(bv-21)*20
        if ps: score-=320+(pv-21)*24
        if 18<=pv<=20: score-=120
        if 27<=pv<=29: score-=90
        bt=bot.caravans[i].trend()
        if bv>22 and bt>0: score-=bt*8
        pt=player.caravans[i].trend()
        if pv>22 and pt>0: score+=pt*6
    return score

def _bot_candidates(bot,player):
    cands=[]
    for i,c in enumerate(bot.hand):
        if c.is_number():
            for ci in range(3):
                if can_play_number_on_caravan(c,bot.caravans[ci]):
                    cands.append(("play_number",{"card_idx":i,"cav":ci}))
    for i,c in enumerate(bot.hand):
        if not c.is_picture(): continue
        for own_name,own in (("bot",bot),("player",player)):
            for ci in range(3):
                cav=own.caravans[ci]
                for ei in range(len(cav.nums)):
                    if can_play_picture_on_target(c,cav.nums[ei],ei==len(cav.nums)-1):
                        cands.append(("play_pic",{"card_idx":i,"owner":own_name,"cav":ci,"entry":ei}))
    for i in range(len(bot.hand)): cands.append(("discard",{"card_idx":i}))
    for ci in range(3):
        if not bot.caravans[ci].empty(): cands.append(("disband",{"cav":ci}))
    return cands

def _sim_move(mtype,payload,sp,sb):
    if mtype=="play_number":
        i,ci=payload["card_idx"],payload["cav"]
        if i>=len(sb.hand): return False
        c=sb.hand[i]
        if not c.is_number() or not can_play_number_on_caravan(c,sb.caravans[ci]): return False
        sb.caravans[ci].nums.append(NumEntry(card=c)); sb.hand.pop(i)
    elif mtype=="play_pic":
        i,own,ci,ei=payload["card_idx"],payload["owner"],payload["cav"],payload["entry"]
        if i>=len(sb.hand): return False
        pic=sb.hand[i]; tgt=sb if own=="bot" else sp
        if ci not in (0,1,2) or ei>=len(tgt.caravans[ci].nums): return False
        ne=tgt.caravans[ci].nums[ei]; is_last=(ei==len(tgt.caravans[ci].nums)-1)
        if not can_play_picture_on_target(pic,ne,is_last): return False
        if pic.rank=="J": apply_jack(sb,tgt.caravans[ci],ei)
        elif pic.rank=="K": apply_king(ne,pic)
        elif pic.rank=="Q": apply_queen(ne,pic)
        elif pic.rank=="JKR": apply_joker(sb,sp,sb,ne,pic)
        sb.hand.pop(i)
    elif mtype=="discard":
        i=payload["card_idx"]
        if i>=len(sb.hand): return False
        discard_hand_card(sb,i)
    elif mtype=="disband":
        if not disband_caravan(sb,payload["cav"]): return False
    return True

def bot_choose_move(bot,player,difficulty,personality_key=DEFAULT_PERSONALITY):
    pers=PERSONALITIES.get(personality_key, BENNY)
    cands=_bot_candidates(bot,player)
    if not cands: return "discard",{"card_idx":0}
    scored=[]
    for mtype,payload in cands:
        sp,sb=_clone(player),_clone(bot)
        if not _sim_move(mtype,payload,sp,sb): continue
        h=heuristic(sp,sb)
        # Personality biases
        if mtype=="play_pic" and payload["owner"]=="player":
            pi=payload["card_idx"]
            if pi<len(bot.hand):
                pic=bot.hand[pi]; pv=player.caravans[payload["cav"]].score()
                if pic.rank=="J" and 18<=pv<=26:   h+=220+pers.attack_bias
                if pic.rank=="JKR" and 18<=pv<=26: h+=140+pers.attack_bias
        if mtype in ("play_number","disband"): h+=pers.defense_bias
        noise=pers.noise.get(difficulty,80)
        h+=random.randint(-noise,noise)
        if difficulty=="easy" and mtype=="discard": h+=30
        scored.append((h,mtype,payload))
    if not scored: return "discard",{"card_idx":0}
    scored.sort(key=lambda x:x[0],reverse=True)
    if difficulty=="easy" and len(scored)>=4:
        k=random.randint(0,3); return scored[k][1],scored[k][2]
    if difficulty=="medium" and len(scored)>=2:
        k=0 if random.random()<0.80 else 1; return scored[k][1],scored[k][2]
    return scored[0][1],scored[0][2]

def bot_take_turn(bot,player,difficulty,personality_key=DEFAULT_PERSONALITY):
    pers=PERSONALITIES.get(personality_key,BENNY)
    mtype,payload=bot_choose_move(bot,player,difficulty,personality_key)
    msg=""; was_play=False
    commentary=""
    if random.random()<0.25 and pers.commentary:
        commentary=random.choice(pers.commentary)

    if mtype=="play_number":
        i,ci=payload["card_idx"],payload["cav"]
        card=bot.hand[i] if 0<=i<len(bot.hand) else None
        ok,_=play_number(bot,i,ci)
        if ok and card:
            msg=f"Bot played {card.label()} on caravan #{ci+1}"; was_play=True
            # Tell on 26
            if bot.caravans[ci].score()==26:
                tell=get_bot_tell(personality_key,"26")
                if tell: set_bot_tell(tell,(195,162,52))
        else: discard_hand_card(bot,0); msg="Bot: failed → discard"
    elif mtype=="play_pic":
        i,own,ci,ei=payload["card_idx"],payload["owner"],payload["cav"],payload["entry"]
        pic=bot.hand[i] if 0<=i<len(bot.hand) else None
        tgt=bot if own=="bot" else player
        tlbl=(tgt.caravans[ci].nums[ei].card.label()
              if 0<=ci<3 and 0<=ei<len(tgt.caravans[ci].nums) else "?")
        ok,_=play_picture(bot,player,i,tgt,ci,ei)
        if ok and pic:
            side="self" if own=="bot" else "you"
            if pic.rank=="J":
                msg=f"Bot played J on {side}: removed {tlbl}"
                tell=get_bot_tell(personality_key,"jack")
                if tell: set_bot_tell(tell,(230,80,80))
            elif pic.rank=="JKR":
                msg=f"Bot played 🃏 on {side}: {tlbl}"
                tell=get_bot_tell(personality_key,"joker")
                if tell: set_bot_tell(tell,(110,35,150))
            elif pic.rank=="K":
                tell=get_bot_tell(personality_key,"king")
                if tell: set_bot_tell(tell,(210,185,72))
                msg=f"Bot played {pic.label()} on {side}: {tlbl}"
            else: msg=f"Bot played {pic.label()} on {side}: {tlbl}"
            was_play=True
        else: discard_hand_card(bot,0); msg="Bot: failed → discard"
    elif mtype=="discard":
        i=payload["card_idx"]
        card=bot.hand[i] if 0<=i<len(bot.hand) else None
        discard_hand_card(bot,i); msg=f"Bot discarded {card.label() if card else '?'}"
    elif mtype=="disband":
        ci=payload["cav"]
        if disband_caravan(bot,ci): msg=f"Bot disbanded caravan #{ci+1}"
        else: discard_hand_card(bot,0); msg="Bot: failed disband → discard"

    if commentary: msg=f'"{commentary}"'
    if not draw_to_hand(bot,HAND_TARGET_SIZE):
        return False,T("bot_deck_empty_win"),False
    return True,msg,was_play

# ============================================================
# SOUND SYSTEM (procedural — no external files needed)
# ============================================================
class SoundManager:
    def __init__(self):
        self._sounds: Dict[str,Any] = {}
        self._ok = AUDIO_OK
        if self._ok:
            try: pygame.mixer.set_num_channels(8)
            except: pass
        self._gen_all()

    def _gen_tone(self, freqs, dur_ms, vol=0.35, shape="sine"):
        if not self._ok: return None
        try:
            import numpy as np
            sr=44100; n=int(sr*dur_ms/1000)
            t=np.linspace(0,dur_ms/1000,n,False)
            wave=np.zeros(n)
            for freq in freqs:
                if shape=="sine":   wave+=np.sin(2*np.pi*freq*t)
                elif shape=="saw":  wave+=2*(t*freq-np.floor(t*freq+0.5))
                elif shape=="sq":   wave+=np.sign(np.sin(2*np.pi*freq*t))
            wave/=len(freqs)
            fade=np.linspace(1,0,n)**0.6
            wave=(wave*fade*vol*32767).astype(np.int16)
            stereo=np.column_stack([wave,wave])
            return pygame.sndarray.make_sound(stereo)
        except: return None

    def _gen_all(self):
        self._sounds["play_card"] = self._gen_tone([600,800],80,0.25)
        self._sounds["discard"]   = self._gen_tone([220,180],120,0.20,"saw")
        self._sounds["jack"]      = self._gen_tone([400,300,200],180,0.30,"sq")
        self._sounds["joker"]     = self._gen_tone([150,100,80],350,0.40,"sq")
        self._sounds["king"]      = self._gen_tone([700,900],100,0.25)
        self._sounds["win"]       = self._gen_tone([523,659,784,1047],500,0.40)
        self._sounds["lose"]      = self._gen_tone([400,320,260,220],600,0.35)
        self._sounds["deal"]      = self._gen_tone([900],40,0.15)
        self._sounds["tick"]      = self._gen_tone([880],30,0.10)
        self._sounds["timer_warn"]= self._gen_tone([440],60,0.20)

    def play(self, name: str):
        if not self._ok or app_settings.muted: return
        snd=self._sounds.get(name)
        if snd:
            try:
                snd.set_volume(app_settings.sfx_volume)
                snd.play()
            except: pass


# ============================================================
# PARTICLE SYSTEM
# ============================================================
class ParticleSystem:
    def __init__(self):
        self._p: list = []

    def burst(self, x, y, color=(195,162,52), count=22, speed=4.0):
        for _ in range(count):
            ang = random.uniform(0, 2*math.pi)
            spd = random.uniform(0.8, speed)
            self._p.append({
                'x':x,'y':y,
                'vx':math.cos(ang)*spd,
                'vy':math.sin(ang)*spd - random.uniform(0,2),
                'life':1.0,'decay':random.uniform(0.018,0.045),
                'color':color,'size':random.randint(3,8),
            })

    def confetti(self, count=70):
        cols=[(195,162,52),(100,200,110),(210,185,72),(180,100,220),(100,200,255),(230,80,80)]
        for _ in range(count):
            self._p.append({
                'x':random.randint(0,WIDTH),'y':random.randint(-30,0),
                'vx':random.uniform(-2,2),'vy':random.uniform(1.5,5),
                'life':1.0,'decay':random.uniform(0.006,0.018),
                'color':random.choice(cols),'size':random.randint(4,11),
            })

    def tick_draw(self, surface):
        keep=[]
        for p in self._p:
            p['x']+=p['vx']; p['y']+=p['vy']; p['vy']+=0.13
            p['life']-=p['decay']
            if p['life']<=0: continue
            sz=max(1,int(p['size']*p['life']))
            alpha=int(p['life']*230)
            s=pygame.Surface((sz*2,sz*2),pygame.SRCALPHA)
            pygame.draw.circle(s,(*p['color'][:3],alpha),(sz,sz),sz)
            surface.blit(s,(int(p['x'])-sz,int(p['y'])-sz))
            keep.append(p)
        self._p[:]=keep

    def clear(self): self._p.clear()
    def active(self): return len(self._p)>0















# ============================================================
# NETWORK MULTIPLAYER (LAN / Hamachi)
# ============================================================
import socket   as _socket
import threading as _threading
import queue    as _queue_mod

NET_PORT   = 27015
GM_NETWORK = "network"


class NetworkManager:
    def __init__(self):
        self.role:      str                      = ""
        self._srv:      _socket.socket           = None  # host listen socket
        self._sock:     _socket.socket           = None  # active peer socket
        self.connected: bool                     = False
        self.error:     str                      = ""
        self._q:        _queue_mod.Queue         = _queue_mod.Queue()

    # ── Host ────────────────────────────────────────────────
    def start_host(self, port: int = NET_PORT) -> bool:
        self.role = "host"
        try:
            self._srv = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
            self._srv.setsockopt(_socket.SOL_SOCKET, _socket.SO_REUSEADDR, 1)
            self._srv.bind(("0.0.0.0", port))
            self._srv.listen(1)
            self._srv.settimeout(0.05)
            return True
        except Exception as exc:
            self.error = str(exc); return False

    def poll_accept(self) -> bool:
        """Call every frame while waiting; returns True once client connects."""
        if self.connected: return True
        if not self._srv:  return False
        try:
            conn, _ = self._srv.accept()
            conn.settimeout(None)
            self._sock = conn
            self.connected = True
            _threading.Thread(target=self._recv_loop, daemon=True).start()
            return True
        except _socket.timeout:
            return False
        except Exception as exc:
            self.error = str(exc); return False

    # ── Client ──────────────────────────────────────────────
    def connect(self, ip: str, port: int = NET_PORT) -> bool:
        self.role = "client"
        try:
            s = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
            s.settimeout(8)
            s.connect((ip, port))
            s.settimeout(None)
            self._sock = s
            self.connected = True
            _threading.Thread(target=self._recv_loop, daemon=True).start()
            return True
        except Exception as exc:
            self.error = str(exc); return False

    # ── Shared ──────────────────────────────────────────────
    def _recv_loop(self):
        buf = b""
        while self.connected:
            try:
                data = self._sock.recv(131072)
                if not data: self.connected = False; break
                buf += data
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    try: self._q.put(json.loads(line.decode()))
                    except: pass
            except OSError:
                self.connected = False; break

    def send(self, msg: dict):
        if self._sock and self.connected:
            try: self._sock.sendall(json.dumps(msg).encode() + b"\n")
            except: self.connected = False

    def poll(self) -> Optional[dict]:
        try: return self._q.get_nowait()
        except _queue_mod.Empty: return None

    def close(self):
        self.connected = False
        for s in (self._sock, self._srv):
            if s:
                try: s.close()
                except: pass

    @staticmethod
    def local_ip() -> str:
        try:
            s = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]; s.close(); return ip
        except: return "127.0.0.1"


# ── Serialisation helpers ────────────────────────────────────
def _sc(c: Card)      -> dict: return {"r": c.rank, "s": c.suit}
def _dc(d: dict)      -> Card: return Card(d["r"], d.get("s"))
def _sne(ne: NumEntry)-> dict: return {"c":_sc(ne.card),"p":[_sc(x) for x in ne.pics]}
def _dne(d: dict)-> NumEntry:  return NumEntry(card=_dc(d["c"]),pics=[_dc(x) for x in d["p"]])
def _scav(cv: Caravan)-> dict: return {"n":[_sne(ne) for ne in cv.nums]}
def _dcav(d: dict)-> Caravan:  return Caravan(nums=[_dne(n) for n in d["n"]])

def _sp(p: PlayerState) -> dict:
    return {"name":p.name,
            "cavs":[_scav(c) for c in p.caravans],
            "deck":[_sc(c)   for c in p.deck],
            "disc":[_sc(c)   for c in p.discard],
            "hand":[_sc(c)   for c in p.hand]}

def _dp(d: dict) -> PlayerState:
    return PlayerState(name=d["name"],
        caravans=[_dcav(c) for c in d["cavs"]],
        deck    =[_dc(c)   for c in d["deck"]],
        discard =[_dc(c)   for c in d["disc"]],
        hand    =[_dc(c)   for c in d["hand"]])

def net_encode(p1: PlayerState, p2: PlayerState,
               phase: str, p1_to_move: bool, oht: int) -> dict:
    return {"t":"s","p1":_sp(p1),"p2":_sp(p2),"ph":phase,"pm":p1_to_move,"oht":oht}

def net_decode(d: dict):
    return _dp(d["p1"]), _dp(d["p2"]), d["ph"], d["pm"], d.get("oht", 0)


# ── Lobby screen ─────────────────────────────────────────────
def network_lobby_screen() -> Optional["NetworkManager"]:
    nm   = None
    mode = ""          # "" | "host" | "join"
    ip_chars = []
    status   = ""
    pygame.event.clear()

    while True:
        clock.tick(FPS)
        now = pygame.time.get_ticks()
        pw, ph = min(580, WIDTH-40), min(400, HEIGHT-80)
        panel  = pygame.Rect(WIDTH//2-pw//2, HEIGHT//2-ph//2, pw, ph)
        screen.fill(BG)
        for gy in range(0, HEIGHT, max(4, int(6*WIDTH/_BASE_W))):
            pygame.draw.line(screen, lighten(BG,3), (0,gy), (WIDTH,gy), 1)
        draw_panel(panel, glow=True)
        draw_panel_title_bar(panel, "🌐 LAN / Hamachi")
        draw_text_center("🌐 Network Game",
                         pygame.Rect(panel.x, panel.y+8, pw, 52), ACCENT, TITLE)
        pos  = pygame.mouse.get_pos()
        bw   = max(180, int(pw*0.38)); bh = 52
        c1x  = panel.x + int(pw*0.10)
        c2x  = panel.x + int(pw*0.52)
        row1 = panel.y + int(ph*0.30)

        if mode == "":
            r_host = pygame.Rect(c1x, row1, bw, bh)
            r_join = pygame.Rect(c2x, row1, bw, bh)
            r_back = pygame.Rect(panel.x+(pw-200)//2, panel.bottom-60, 200, 50)
            draw_button("🖥  Host Game",  r_host, pos)
            draw_button("🔌  Join Game",  r_join, pos)
            draw_button(T("back"), r_back, pos, (100,28,28), lighten((100,28,28),30), SMALL)
            lip = NetworkManager.local_ip()
            draw_text_center(f"Your IP:  {lip}",
                             pygame.Rect(panel.x, row1+bh+14, pw, 26), TEXT_DIM, SMALL)
            draw_text_center("Share this IP with your friend to let them join.",
                             pygame.Rect(panel.x, row1+bh+40, pw, 24), TEXT_DIM, TINY)

        elif mode == "host":
            dots = "."*(1+(now//400)%3)
            draw_text_center("Waiting for opponent" + dots,
                             pygame.Rect(panel.x, panel.y+int(ph*0.32), pw, 34), YELLOW, FONT)
            draw_text_center(f"Your IP:  {NetworkManager.local_ip()}   Port: {NET_PORT}",
                             pygame.Rect(panel.x, panel.y+int(ph*0.48), pw, 28), ACCENT, SMALL)
            draw_text_center("(Hamachi: use your Hamachi IP above)",
                             pygame.Rect(panel.x, panel.y+int(ph*0.58), pw, 24), TEXT_DIM, TINY)
            r_cancel = pygame.Rect(panel.x+(pw-200)//2, panel.bottom-60, 200, 50)
            draw_button("Cancel", r_cancel, pos, (100,28,28), lighten((100,28,28),30), SMALL)
            if nm and nm.poll_accept():
                return nm

        elif mode == "join":
            draw_text_center("Enter host's IP address (Hamachi IP):",
                             pygame.Rect(panel.x, panel.y+int(ph*0.26), pw, 30), TEXT, FONT)
            tb = pygame.Rect(panel.x+60, panel.y+int(ph*0.40), pw-120, 48)
            pygame.draw.rect(screen, (20,35,22), tb, border_radius=8)
            pygame.draw.rect(screen, ACCENT,     tb, 2, border_radius=8)
            disp = "".join(ip_chars) + ("_" if (now//500)%2==0 else " ")
            draw_text_center(disp, tb, TEXT, FONT)
            r_conn   = pygame.Rect(panel.x+(pw-200)//2, panel.bottom-120, 200, 52)
            r_cancel = pygame.Rect(panel.x+(pw-200)//2, panel.bottom-60,  200, 50)
            draw_button("🔌  Connect", r_conn,   pos)
            draw_button("Cancel",      r_cancel, pos, (100,28,28), lighten((100,28,28),30), SMALL)

        if status:
            bad = any(w in status.lower() for w in ("fail","error","refused","timed"))
            draw_text_center(status,
                             pygame.Rect(panel.x, panel.bottom-10, pw, 12),
                             RED if bad else OUT_OK, TINY)
        pygame.display.flip()

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                if nm: nm.close(); app_settings.save(); pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    if nm: nm.close(); nm = None
                    if mode: mode = ""; status = ""; continue
                    return None
                if mode == "join":
                    if e.key == pygame.K_BACKSPACE:
                        if ip_chars: ip_chars.pop()
                    elif e.key == pygame.K_RETURN:
                        ip2 = "".join(ip_chars).strip()
                        nm2 = NetworkManager()
                        if nm2.connect(ip2):
                            return nm2
                        status = f"Failed: {nm2.error}"
                    else:
                        ch = e.unicode
                        if ch and (ch.isdigit() or ch == ".") and len(ip_chars) < 15:
                            ip_chars.append(ch)
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if mode == "":
                    r_h = pygame.Rect(c1x, row1, bw, bh)
                    r_j = pygame.Rect(c2x, row1, bw, bh)
                    r_b = pygame.Rect(panel.x+(pw-200)//2, panel.bottom-60, 200, 50)
                    if r_h.collidepoint(e.pos):
                        nm = NetworkManager()
                        if nm.start_host(): mode = "host"; status = f"Listening on port {NET_PORT}…"
                        else: status = f"Error: {nm.error}"; nm = None
                    elif r_j.collidepoint(e.pos):
                        mode = "join"
                        ip_chars = list(NetworkManager.local_ip())
                    elif r_b.collidepoint(e.pos):
                        return None
                elif mode == "host":
                    r_c = pygame.Rect(panel.x+(pw-200)//2, panel.bottom-60, 200, 50)
                    if r_c.collidepoint(e.pos):
                        if nm: nm.close(); nm = None
                        mode = ""; status = ""
                elif mode == "join":
                    r_cn = pygame.Rect(panel.x+(pw-200)//2, panel.bottom-120, 200, 52)
                    r_ca = pygame.Rect(panel.x+(pw-200)//2, panel.bottom-60,  200, 50)
                    if r_cn.collidepoint(e.pos):
                        ip2 = "".join(ip_chars).strip()
                        nm2 = NetworkManager()
                        if nm2.connect(ip2):
                            return nm2
                        status = f"Failed: {nm2.error}"
                    elif r_ca.collidepoint(e.pos):
                        mode = ""; status = ""


# ── Small HUD shown during a network match ───────────────────
def _draw_net_hud(is_host: bool, is_my_turn: bool):
    role_lbl = "🖥 HOST" if is_host else "🔌 CLIENT"
    turn_lbl = "▶ YOUR TURN" if is_my_turn else "⏳ Opponent's turn…"
    draw_text(role_lbl, 8, 8, (120,180,255), TINY)
    draw_text(turn_lbl, 8, 8+TINY.get_height()+4,
              ACCENT if is_my_turn else TEXT_DIM, SMALL)


# ── Network match loop ────────────────────────────────────────
def run_network_match(nm: "NetworkManager") -> str:
    is_host  = (nm.role == "host")
    sel_keys = load_deck_selection()
    if sel_keys: sel_keys = ensure_min30_selection(sel_keys)

    # Host builds the authoritative initial state for both sides
    if is_host:
        p1 = PlayerState(app_settings.player_name,
                         [Caravan() for _ in range(3)],
                         build_deck_from_selection(sel_keys), [], [])
        p2 = PlayerState("Opponent",
                         [Caravan() for _ in range(3)],
                         build_deck_from_selection(sel_keys), [], [])
        draw_to_hand(p1, HAND_OPENING_SIZE)
        draw_to_hand(p2, HAND_OPENING_SIZE)
        opening_ht = 0
        nm.send(net_encode(p1, p2, "OPENING", True, 0))
    else:
        # Client waits for the host's initial state message
        p1 = p2 = None
        while p1 is None:
            clock.tick(FPS)
            screen.fill(BG)
            draw_text_center("Waiting for host to start…",
                             pygame.Rect(0, HEIGHT//2-20, WIDTH, 40), YELLOW, FONT)
            pygame.display.flip()
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    nm.close(); app_settings.save(); pygame.quit(); sys.exit()
                if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                    nm.close(); return "menu"
            if not nm.connected: return "menu"
            msg = nm.poll()
            if msg and msg.get("t") == "s":
                p1, p2, phase0, pm0, oht0 = net_decode(msg)
                opening_ht = oht0
                break

    phase      = "OPENING"
    p1_to_move = True
    if not is_host:
        phase = phase0; p1_to_move = pm0; opening_ht = oht0

    # ── convenience closures ─────────────────────────────────
    def me()       -> PlayerState: return p1 if is_host else p2
    def opp()      -> PlayerState: return p2 if is_host else p1
    def my_turn()  -> bool:        return p1_to_move if is_host else (not p1_to_move)

    def sync():
        nm.send(net_encode(p1, p2, phase, p1_to_move, opening_ht))

    def apply_incoming(msg: dict):
        nonlocal p1, p2, phase, p1_to_move, opening_ht
        np1, np2, nph, npm, noht = net_decode(msg)
        # Full replacement — both sides stay in lock-step
        for attr in ("caravans","deck","discard","hand"):
            setattr(p1, attr, getattr(np1, attr))
            setattr(p2, attr, getattr(np2, attr))
        phase = nph; p1_to_move = npm; opening_ht = noht

    # ── game state ───────────────────────────────────────────
    start_ms   = pygame.time.get_ticks()
    selected   = -1
    msg_str    = ""; msg_until = 0
    hand_scroll = 0
    consecutive_discards = 0
    hitboxes_dirty = True
    cached_hit: Optional[dict] = None

    while True:
        clock.tick(FPS)
        now = pygame.time.get_ticks()

        if not nm.connected:
            sounds.play("lose")
            end_screen("Connection lost!", now - start_ms, 0)
            return "menu"

        # Drain incoming messages
        while True:
            net_msg = nm.poll()
            if net_msg is None: break
            if net_msg.get("t") == "s":
                apply_incoming(net_msg)
                hitboxes_dirty = True
            elif net_msg.get("t") == "chat":
                msg_str   = f"Opp: {net_msg.get('text','')}"
                msg_until = now + 2500

        if hitboxes_dirty:
            _, ba_, pa_, _ = ui_rects()
            cached_hit = {
                "bot":    build_entry_hitboxes("bot",    caravan_slots(ba_), opp().caravans),
                "player": build_entry_hitboxes("player", caravan_slots(pa_), me().caravans),
            }
            hitboxes_dirty = False

        ui = draw_board(
            player=me(), bot=opp(),
            selected_idx=selected, msg=msg_str, msg_until=msg_until,
            start_ms=start_ms, phase=phase, bot_diff="LAN",
            hand_scroll=hand_scroll, pending_bot=not my_turn(),
            undo_count=0, consecutive_discards=consecutive_discards,
            cached_hitboxes=cached_hit, game_mode=GM_NETWORK,
            turn_start_ms=start_ms, personality_key=DEFAULT_PERSONALITY,
        )
        hand_scroll = ui.hand_scroll
        _draw_net_hud(is_host, my_turn())
        pygame.display.flip()

        # Win / stalemate checks
        if phase == "MAIN":
            ended, win, _ = check_game_end(me(), opp())
            if ended:
                elapsed = now - start_ms
                result  = "win" if win == "player" else "loss"
                app_stats.record(result, elapsed); app_stats.save()
                sounds.play("win" if result == "win" else "lose")
                add_history(result, "LAN", GM_NETWORK, elapsed, 0)
                if result == "win": particles.confetti(70)
                end_screen(T("player_wins") if result == "win" else T("bot_wins"),
                           elapsed, 0)
                nm.close(); return "menu"
            if consecutive_discards >= STALEMATE_THRESHOLD:
                elapsed = now - start_ms
                app_stats.record("draw", elapsed); app_stats.save()
                add_history("draw","LAN", GM_NETWORK, elapsed, 0)
                end_screen(T("draw_stalemate"), elapsed, 0)
                nm.close(); return "menu"

        # ── Event loop ────────────────────────────────────────
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                nm.close(); app_settings.save(); pygame.quit(); sys.exit()

            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                r2 = pause_menu()
                if r2 == "quit_match":
                    nm.close(); return "menu"
                hitboxes_dirty = True; continue

            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if ui.pause_btn.collidepoint(*e.pos):
                    r2 = pause_menu()
                    if r2 == "quit_match":
                        nm.close(); return "menu"
                    hitboxes_dirty = True; continue

            if not my_turn():
                continue   # ← ignore input while opponent moves

            if e.type == pygame.MOUSEWHEEL and ui.hand_scroll_on:
                hand_scroll = max(0, min(ui.hand_max_scroll,
                                         hand_scroll - e.y * 50))

            # keyboard: arrow keys to select card
            if e.type == pygame.KEYDOWN:
                n = len(me().hand)
                if e.key == pygame.K_RIGHT and n > 0:
                    selected = (max(selected,0)+1) % n
                elif e.key == pygame.K_LEFT and n > 0:
                    selected = (max(selected,0)-1) % n

                # D = discard selected card
                if e.key == pygame.K_d and phase == "MAIN" \
                        and 0 <= selected < len(me().hand):
                    sounds.play("discard")
                    if discard_hand_card(me(), selected):
                        draw_to_hand(me(), HAND_TARGET_SIZE)
                        consecutive_discards += 1; hitboxes_dirty = True
                        p1_to_move = not p1_to_move; sync()
                        selected = -1

                # 1/2/3 = play selected number card on caravan
                cav_keys = {pygame.K_1:0, pygame.K_2:1, pygame.K_3:2}
                if e.key in cav_keys and phase == "MAIN" \
                        and 0 <= selected < len(me().hand):
                    ci = cav_keys[e.key]
                    c  = me().hand[selected]
                    if c.is_number():
                        ok, emsg = play_number(me(), selected, ci)
                        selected = -1
                        if not ok:
                            msg_str = emsg; msg_until = now+1400
                        else:
                            sounds.play("play_card")
                            consecutive_discards = 0; hitboxes_dirty = True
                            draw_to_hand(me(), HAND_TARGET_SIZE)
                            p1_to_move = not p1_to_move; sync()

            # ── OPENING phase mouse ───────────────────────────
            if phase == "OPENING" and e.type == pygame.MOUSEBUTTONDOWN \
                    and e.button == 1:
                mpos = e.pos
                hi = get_idx_at(mpos, ui.hand_rects)
                if hi != -1:
                    selected = -1 if selected == hi else hi; continue
                if 0 <= selected < len(me().hand):
                    c = me().hand[selected]
                    if not c.is_number():
                        msg_str = T("opening_nums_only")
                        msg_until = now+1200; selected = -1; continue
                    for ci, r in enumerate(ui.ply_slots):
                        if r.collidepoint(*mpos):
                            if not me().caravans[ci].empty():
                                msg_str = T("caravan_started")
                                msg_until = now+1200; selected = -1; break
                            sounds.play("deal")
                            card = me().hand.pop(selected)
                            me().caravans[ci].nums.append(NumEntry(card=card))
                            selected = -1; hitboxes_dirty = True
                            opening_ht += 1
                            p1_to_move = not p1_to_move
                            if opening_ht >= 6:
                                # Both sides trim and enter MAIN
                                me().hand  = me().hand[:HAND_TARGET_SIZE]
                                opp().hand = opp().hand[:HAND_TARGET_SIZE]
                                draw_to_hand(me(), HAND_TARGET_SIZE)
                                phase = "MAIN"; p1_to_move = True
                            sync()
                            break
                continue

            # ── MAIN phase mouse ──────────────────────────────
            if phase == "MAIN" and e.type == pygame.MOUSEBUTTONDOWN:
                mpos = e.pos

                # Right-click: discard card OR disband caravan
                if e.button == 3:
                    hi = get_idx_at(mpos, ui.hand_rects)
                    if hi != -1:
                        sounds.play("discard")
                        if discard_hand_card(me(), hi):
                            draw_to_hand(me(), HAND_TARGET_SIZE)
                            consecutive_discards += 1; hitboxes_dirty = True
                            p1_to_move = not p1_to_move; sync()
                        continue
                    for ci, r in enumerate(ui.ply_slots):
                        if r.collidepoint(*mpos):
                            if disband_caravan(me(), ci):
                                draw_to_hand(me(), HAND_TARGET_SIZE)
                                consecutive_discards += 1; hitboxes_dirty = True
                                p1_to_move = not p1_to_move; sync()
                            else:
                                msg_str = T("nothing_disband"); msg_until = now+1000
                            break
                    continue

                # Left-click: select / play
                if e.button == 1:
                    hi = get_idx_at(mpos, ui.hand_rects)
                    if hi != -1:
                        selected = -1 if selected == hi else hi; continue
                    if not (0 <= selected < len(me().hand)): continue
                    c = me().hand[selected]

                    if c.is_number():
                        for ci, r in enumerate(ui.ply_slots):
                            if r.collidepoint(*mpos):
                                ok, emsg = play_number(me(), selected, ci)
                                selected = -1
                                if not ok:
                                    msg_str = emsg; msg_until = now+1400; break
                                sounds.play("play_card")
                                consecutive_discards = 0; hitboxes_dirty = True
                                draw_to_hand(me(), HAND_TARGET_SIZE)
                                p1_to_move = not p1_to_move; sync()
                                break

                    elif c.is_picture():
                        hit = None
                        for r, own, ci, ei in ui.ply_boxes + ui.bot_boxes:
                            if r.collidepoint(*mpos): hit = (own,ci,ei); break
                        if not hit:
                            msg_str = T("face_needs_target")
                            msg_until = now+1200; selected = -1; continue
                        own, ci, ei = hit
                        tgt = me() if own == "player" else opp()
                        ok, emsg = play_picture(me(), opp(), selected, tgt, ci, ei)
                        selected = -1
                        if not ok:
                            msg_str = emsg; msg_until = now+1500; continue
                        pic = me().discard[-1] if me().discard else None
                        if pic:
                            if   pic.rank == "J":   sounds.play("jack")
                            elif pic.rank == "JKR":
                                sounds.play("joker"); trigger_shake(10, 400)
                            elif pic.rank == "K":   sounds.play("king")
                            else:                   sounds.play("play_card")
                        consecutive_discards = 0; hitboxes_dirty = True
                        draw_to_hand(me(), HAND_TARGET_SIZE)
                        p1_to_move = not p1_to_move; sync()

    nm.close(); return "menu"    


# ============================================================
# BOT TELL SYSTEM
# ============================================================
_bot_tell_msg   = ""
_bot_tell_until = 0
_bot_tell_color = (210,185,72)

def set_bot_tell(msg:str, color=(210,185,72), duration_ms=2200):
    global _bot_tell_msg,_bot_tell_until,_bot_tell_color
    _bot_tell_msg=msg; _bot_tell_until=pygame.time.get_ticks()+duration_ms
    _bot_tell_color=color

_TELLS={
    "benny":{
        "jack":  ["Tough break, pal.","Oops—gone!","That's just business.","Say goodbye to that card."],
        "joker": ["BOOM, baby!","Nuclear option!","The whole table's mine!","Heh. Heh. Heh."],
        "king":  ["Stack 'em up!","Double or nothing!","Now we're cooking."],
        "26":    ["Twenty-six! Beautiful.","Perfect game, baby.","Read 'em and weep."],
        "win":   ["The house always wins, and I AM the house.","Better luck next time, sweetheart."],
    },
    "yes_man":{
        "jack":  ["Oh! Sorry about that!","Had to do it, no hard feelings!","Oops, was that yours?"],
        "joker": ["Wow, that really worked out great!","For me, I mean!","Oh my goodness!"],
        "king":  ["Doubling up, yes! Great idea!","More is definitely better!"],
        "26":    ["Twenty-six! Did I do that right?","Oh wow, it worked!"],
        "win":   ["Oh wow, I won! That's… actually great!","No offense intended!"],
    },
    "house":{
        "jack":  ["Calculated.","Inefficiency removed.","Expected outcome."],
        "joker": ["Probability: 94.7% favoring me.","As predicted.","Optimal."],
        "king":  ["Optimal play.","Doubling as intended."],
        "26":    ["Precise. As intended.","Twenty-six. Naturally."],
        "win":   ["The House always wins.","Exactly as simulated.","Inevitable."],
    },
}

def get_bot_tell(pk:str, event:str) -> str:
    opts=_TELLS.get(pk,{}).get(event,[])
    return random.choice(opts) if opts else ""
_shake_end   = 0    # ms timestamp when shake ends
_shake_mag   = 0    # pixels

def trigger_shake(magnitude=8, duration_ms=300):
    global _shake_end, _shake_mag
    _shake_end = pygame.time.get_ticks() + duration_ms
    _shake_mag = magnitude

def get_shake_offset(now):
    if now >= _shake_end: return 0, 0
    t = (_shake_end - now) / 300
    mag = int(_shake_mag * t)
    return random.randint(-mag, mag), random.randint(-mag//2, mag//2)

# Deal flash: list of (card, start_ms, duration_ms, start_rect, end_rect)
_deal_anims: list = []

def add_deal_anim(start_rect, end_rect, delay_ms=0):
    now = pygame.time.get_ticks()
    _deal_anims.append({
        "start": now + delay_ms,
        "end":   now + delay_ms + 200,
        "sr":    start_rect,
        "er":    end_rect,
        "done":  False,
    })

def tick_deal_anims(now):
    for a in _deal_anims:
        a["done"] = (now >= a["end"])
    _deal_anims[:] = [a for a in _deal_anims if not a["done"]]

def get_card_draw_rect(base_rect, now):
    """Returns possibly animated rect for a card."""
    for a in _deal_anims:
        if a["done"]: continue
        if now < a["start"]: continue
        t = min(1.0, (now - a["start"]) / (a["end"] - a["start"]))
        t = t*t*(3-2*t)  # smoothstep
        sr, er = a["sr"], a["er"]
        x = int(lerp(sr.x, er.x, t))
        y = int(lerp(sr.y, er.y, t))
        if abs(x-base_rect.x)<4 and abs(y-base_rect.y)<4:
            break
        return pygame.Rect(x, y, base_rect.w, base_rect.h)
    return base_rect


# ============================================================
# PYGAME INIT
# ============================================================
pygame.init()

AUDIO_OK = True
try: pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
except: AUDIO_OK = False

app_settings = Settings.load()
app_stats    = Stats.load()
load_achievements()
app_settings.apply_language()

_FONT_CANDIDATES = [
    "consolas","couriernew","dejavusansmono","liberationmono",
    "ubuntumono","freemono","droidsansmono","arial","",
]

def _make_sysfont(size, bold=False):
    for name in _FONT_CANDIDATES:
        try:
            f=pygame.font.SysFont(name,size,bold=bold)
            if f.size("Тест")[0]>0: return f
        except: pass
    return pygame.font.Font(None,max(8,size))

screen: pygame.Surface = None
FONT=SMALL=TINY=TITLE=None
_text_cache:       Dict = {}
_card_label_cache: Dict = {}

def apply_resolution(w, h, fullscreen=False):
    global WIDTH,HEIGHT,screen,FONT,SMALL,TINY,TITLE
    global MARGIN,GAP,TOP_BAR_H
    global CARD_W,CARD_H,SELECT_RAISE,PIC_BADGE_W,PIC_BADGE_H
    global GRID_CARD_W,GRID_CARD_H
    global STACK_OVERLAP_X,STACK_OVERLAP_X_TIGHT,STACK_PAD_X
    global _text_cache,_card_label_cache

    if fullscreen:
        info=pygame.display.Info(); w,h=info.current_w,info.current_h
        screen=pygame.display.set_mode((w,h),pygame.FULLSCREEN)
    else:
        screen=pygame.display.set_mode((w,h))
    WIDTH,HEIGHT=w,h
    pygame.display.set_caption("Caravan — Fallout: New Vegas")

    s=WIDTH/_BASE_W
    FONT  = _make_sysfont(max(10,int(26*s)))
    SMALL = _make_sysfont(max(8, int(20*s)))
    TINY  = _make_sysfont(max(6, int(16*s)))
    TITLE = _make_sysfont(max(16,int(56*s)),bold=True)

    MARGIN        = max(10,int(20*s))
    GAP           = max(6, int(12*s))
    TOP_BAR_H     = max(70,int(100*s))
    CARD_W        = max(50,int(_BASE_CARD_W*s))
    CARD_H        = max(70,int(_BASE_CARD_H*s))
    SELECT_RAISE  = max(8, int(16*s))
    PIC_BADGE_W   = max(18,int(26*s))
    PIC_BADGE_H   = max(18,int(26*s))
    GRID_CARD_W   = max(52,int(84*s))
    GRID_CARD_H   = max(38,int(60*s))
    STACK_OVERLAP_X       = max(18,int(30*s))
    STACK_OVERLAP_X_TIGHT = max(14,int(20*s))
    STACK_PAD_X           = max(10,int(16*s))

    _text_cache.clear(); _card_label_cache.clear()

apply_resolution(*map(int,app_settings.resolution.split("x")),
                 fullscreen=app_settings.fullscreen)
clock = pygame.time.Clock()
sounds = SoundManager()
particles = ParticleSystem()


# ============================================================
# CARD BACK DESIGNS (4 procedural patterns)
# ============================================================
_back_cache: Dict = {}

def get_card_back_surf(design: int, w: int, h: int) -> pygame.Surface:
    key=(design,w,h)
    if key in _back_cache: return _back_cache[key]
    s=pygame.Surface((w,h), pygame.SRCALPHA)
    s.fill((0,0,0,0))

    if design==0:   # Green felt — diamond grid
        pygame.draw.rect(s,(35,80,45),(0,0,w,h),border_radius=10)
        pygame.draw.rect(s,(55,110,65),(4,4,w-8,h-8),border_radius=7)
        for gx in range(0,w,max(8,w//10)):
            for gy in range(0,h,max(8,h//8)):
                pts=[(gx,gy-4),(gx+4,gy),(gx,gy+4),(gx-4,gy)]
                pygame.draw.polygon(s,(70,140,80),pts,1)
        pygame.draw.rect(s,(90,160,100),(0,0,w,h),2,border_radius=10)

    elif design==1:  # Red wasteland
        pygame.draw.rect(s,(130,25,25),(0,0,w,h),border_radius=10)
        pygame.draw.rect(s,(160,40,40),(4,4,w-8,h-8),border_radius=7)
        # decorative rope border
        for i in range(0,w+h,max(6,w//14)):
            x=i if i<w else w-1; y=0 if i<w else i-w
            pygame.draw.circle(s,(180,60,60),(x,y),2)
            pygame.draw.circle(s,(180,60,60),(w-x,h-y),2)
        cx,cy=w//2,h//2
        pygame.draw.circle(s,(180,60,60),(cx,cy),min(w,h)//4,1)
        pygame.draw.rect(s,(200,80,80),(0,0,w,h),2,border_radius=10)

    elif design==2:  # Casino blue
        pygame.draw.rect(s,(25,40,130),(0,0,w,h),border_radius=10)
        pygame.draw.rect(s,(40,60,160),(4,4,w-8,h-8),border_radius=7)
        for sx in range(w//4,w,w//4):
            for sy in range(h//4,h,h//4):
                pygame.draw.circle(s,(60,90,190),(sx,sy),3,1)
                for ang in range(0,360,45):
                    r=8; ex=sx+int(r*math.cos(math.radians(ang))); ey=sy+int(r*math.sin(math.radians(ang)))
                    pygame.draw.line(s,(60,90,190),(sx,sy),(ex,ey),1)
        pygame.draw.rect(s,(80,120,220),(0,0,w,h),2,border_radius=10)

    elif design==3:  # House — black gold
        pygame.draw.rect(s,(12,12,16),(0,0,w,h),border_radius=10)
        pygame.draw.rect(s,(22,22,30),(4,4,w-8,h-8),border_radius=7)
        # Gold filigree corners
        for cx2,cy2 in [(12,12),(w-12,12),(12,h-12),(w-12,h-12)]:
            pygame.draw.circle(s,(160,130,50),(cx2,cy2),8,1)
            pygame.draw.circle(s,(160,130,50),(cx2,cy2),4,1)
        # Centre H  — FIX #1: render() requires 3 arguments (text, antialias, color)
        fnt=pygame.font.Font(None,max(20,h//3))
        ht=fnt.render("H", True, (160,130,50))
        s.blit(ht,(w//2-ht.get_width()//2,h//2-ht.get_height()//2))
        pygame.draw.rect(s,(160,130,50),(0,0,w,h),2,border_radius=10)

    _back_cache[key]=s; return s

BACK_NAMES = ["Green Felt","Wasteland","Casino Blue","House Black"]


# ============================================================
# CARD ART (LRU-evicting scaled cache)
# ============================================================
class CardArt:
    def __init__(self,base_dir,debug=False):
        self.base_dir=base_dir; self.debug=debug
        self._files:  Dict={};  self._scaled:OrderedDict=OrderedDict()
        self._missing:set=set()

    def _candidates(self,card):
        r="JKR" if card.rank=="JKR" else card.rank
        s=card.suit or ""; sl=s.lower(); sym=SUIT_SYMBOL.get(card.suit or "","")
        if r=="JKR":
            return ["JKR.png","JOKER.png","Joker.png","joker.png",
                    "JKR_1.png","JKR-1.png","JKR1.png"]
        return [f"{r}_{s}.png",f"{r}-{s}.png",f"{r}{s}.png",
                f"{s}_{r}.png",f"{s}-{r}.png",f"{s}{r}.png",
                f"{r}_{sl}.png",f"{r}-{sl}.png",f"{r}{sl}.png",
                f"{sl}_{r}.png",f"{sl}-{r}.png",f"{sl}{r}.png",
                f"{r}{sym}.png",f"{r}_{sym}.png",f"{r}-{sym}.png"]

    def _find_file(self,card,variant):
        if not USE_ART: return None
        for sub in (["stack","hand",""] if variant=="stack"
                    else ["thumb","hand",""] if variant=="thumb"
                    else ["hand",""]):
            folder=os.path.join(self.base_dir,sub) if sub else self.base_dir
            for name in self._candidates(card):
                fp=os.path.join(folder,name)
                if os.path.exists(fp): return fp
        if self.debug: self._missing.add(f"{variant}:{card.key()}")
        return None

    def get_scaled(self,card,size,variant="hand"):
        fp=self._find_file(card,variant)
        if fp is None: return None
        w,h=int(size[0]),int(size[1]); key=(fp,w,h)
        if key in self._scaled:
            self._scaled.move_to_end(key); return self._scaled[key]
        try:
            if fp not in self._files:
                self._files[fp]=pygame.image.load(fp).convert_alpha()
            base=self._files[fp]
            surf=(base if base.get_width()==w and base.get_height()==h
                  else pygame.transform.smoothscale(base,(w,h)))
            self._scaled[key]=surf
            if len(self._scaled)>MAX_ART_CACHE_ENTRIES:
                self._scaled.popitem(last=False)
            return surf
        except: return None

CARD_ART = CardArt(CARDS_DIR, debug=ART_DEBUG)

if AUDIO_OK and os.path.exists(MUSIC_PATH):
    try:
        pygame.mixer.music.load(MUSIC_PATH)
        app_settings.apply_audio()
        pygame.mixer.music.play(-1)
    except: pass


# ============================================================
# TEXT HELPERS
# ============================================================
def _fk(font): return font.size("A")

def render_cached(text,font,color):
    key=(_fk(font),text,color)
    if key not in _text_cache:
        _text_cache[key]=font.render(text,True,color)
    return _text_cache[key]

def draw_text(text,x,y,color=TEXT,font=None):
    if font is None: font=FONT
    img=render_cached(str(text),font,color)
    screen.blit(img,(x,y)); return img.get_width(),img.get_height()

def draw_text_center(text,rect,color=TEXT,font=None):
    if font is None: font=FONT
    img=render_cached(str(text),font,color)
    screen.blit(img,(rect.x+(rect.width-img.get_width())//2,
                     rect.y+(rect.height-img.get_height())//2))

def draw_shadow_rect(rect,radius=12,alpha=90,offset=(4,5)):
    sh=pygame.Surface((rect.w,rect.h),pygame.SRCALPHA)
    pygame.draw.rect(sh,(0,0,0,alpha),pygame.Rect(0,0,rect.w,rect.h),border_radius=radius)
    screen.blit(sh,(rect.x+offset[0],rect.y+offset[1]))

def draw_panel(rect,fill=PANEL,border=PANEL_BORD,glow=False):
    sh=pygame.Surface((rect.w,rect.h),pygame.SRCALPHA)
    pygame.draw.rect(sh,(0,0,0,80),pygame.Rect(0,0,rect.w,rect.h),border_radius=16)
    screen.blit(sh,(rect.x+4,rect.y+5))
    pygame.draw.rect(screen,fill,rect,border_radius=14)
    hi=pygame.Rect(rect.x+2,rect.y+2,rect.w-4,3)
    pygame.draw.rect(screen,lighten(fill,30),hi)
    pygame.draw.rect(screen,lighten(PANEL_GLOW,40) if glow else border,rect,2,border_radius=14)

def draw_panel_title_bar(rect,text="",color=ACCENT):
    bar=pygame.Rect(rect.x+2,rect.y+2,rect.w-4,max(36,int(44*WIDTH/_BASE_W)))
    s=pygame.Surface((bar.w,bar.h),pygame.SRCALPHA); s.fill((*color[:3],55))
    screen.blit(s,bar.topleft)
    pygame.draw.line(screen,color,(bar.x,bar.bottom),(bar.right,bar.bottom),1)

def draw_button(text,rect,pos,color=BTN,hover=BTN_H,font=None):
    if font is None: font=FONT
    hov=rect.collidepoint(*pos); c=hover if hov else color
    sh=pygame.Surface((rect.w,rect.h),pygame.SRCALPHA)
    pygame.draw.rect(sh,(0,0,0,60),pygame.Rect(3,3,rect.w,rect.h),border_radius=10)
    screen.blit(sh,rect.topleft)
    pygame.draw.rect(screen,c,rect,border_radius=10)
    pygame.draw.rect(screen,lighten(c,35),pygame.Rect(rect.x+3,rect.y+2,rect.w-6,3))
    pygame.draw.rect(screen,lighten(c,50) if hov else lighten(c,20),rect,2,border_radius=10)
    draw_text_center(text,rect,BTN_TXT,font=font)
    return hov

def card_color_for(card):
    if card.rank=="JKR": return CARD_JOKER
    return SUIT_COLOR.get(card.suit or "",TEXT)

def get_card_label_surf(card,font):
    color=card_color_for(card); key=(card.key(),_fk(font),color)
    if key not in _card_label_cache:
        _card_label_cache[key]=font.render(card.label(),True,color)
    return _card_label_cache[key]


# ============================================================
# UI LAYOUT
# ============================================================
@dataclass
class UILayout:
    bot_slots:       List[pygame.Rect]
    ply_slots:       List[pygame.Rect]
    hand_rects:      List[pygame.Rect]
    bot_boxes:       list
    ply_boxes:       list
    hand_scroll:     int
    hand_max_scroll: int
    hand_scroll_on:  bool
    pause_btn:       pygame.Rect


# ============================================================
# DRAWING HELPERS
# ============================================================
def ui_rects():
    top   = pygame.Rect(MARGIN,10,WIDTH-2*MARGIN,TOP_BAR_H)
    avail = HEIGHT-top.bottom-3*GAP-16
    sec_h = max(CARD_H+62, avail*36//100)
    hand_h= max(CARD_H+50, avail-2*sec_h)
    ba    = pygame.Rect(MARGIN,top.bottom+GAP,WIDTH-2*MARGIN,sec_h)
    pa    = pygame.Rect(MARGIN,ba.bottom+GAP,WIDTH-2*MARGIN,sec_h)
    hand  = pygame.Rect(MARGIN,pa.bottom+GAP,WIDTH-2*MARGIN,hand_h)
    return top,ba,pa,hand

def caravan_slots(area):
    w=area.width//3
    title_h=max(36,int(44*WIDTH/_BASE_W))
    score_h=max(20,int(28*WIDTH/_BASE_W))
    slot_h=area.height-title_h-score_h-8
    return [pygame.Rect(area.x+i*w+14,area.y+title_h+4,w-28,slot_h) for i in range(3)]

def get_idx_at(pos,rects):
    for i,r in enumerate(rects):
        if r.collidepoint(pos): return i
    return -1

def _card_text_color(card):
    if card.rank=="JKR": return CARD_JOKER
    if card.suit in ("H","D"): return CARD_RED
    return CARD_BLACK

def _draw_value_badge(rect,value):
    bw,bh=max(30,int(44*WIDTH/_BASE_W)),max(18,int(26*WIDTH/_BASE_W))
    pad=pygame.Rect(rect.x+4,rect.y+rect.h-bh-4,bw,bh)
    bs=pygame.Surface((bw,bh),pygame.SRCALPHA); bs.fill((8,12,8,195))
    pygame.draw.rect(bs,(80,120,60,200),pygame.Rect(0,0,bw,bh),1,border_radius=5)
    screen.blit(bs,pad.topleft); draw_text_center(str(value),pad,ACCENT,TINY)

def _draw_card_face(rect,card,selected=False,hovered=False,value_override=None):
    back=app_settings.card_back
    art_img=CARD_ART.get_scaled(card,(rect.w,rect.h),"hand") if USE_ART else None
    if art_img:
        draw_shadow_rect(rect,12,80)
        screen.blit(art_img,rect)
        if selected:
            pygame.draw.rect(screen,CARD_SEL,rect,4,border_radius=12)
            pygame.draw.rect(screen,ACCENT,rect,2,border_radius=12)
        elif hovered:
            pygame.draw.rect(screen,CARD_HOVER,rect,3,border_radius=12)
        if value_override is not None: _draw_value_badge(rect,value_override)
        return

    draw_shadow_rect(rect,12,85)
    face_col=CARD_FACE if not selected else (255,255,230)
    pygame.draw.rect(screen,face_col,rect,border_radius=12)
    inner=pygame.Rect(rect.x+4,rect.y+4,rect.w-8,rect.h-8)
    bord_col=CARD_RED if card.suit in ("H","D") else (100,100,120)
    pygame.draw.rect(screen,bord_col,inner,1,border_radius=8)
    tc=_card_text_color(card)
    rank_str=card.rank if card.rank!="JKR" else "★"
    suit_str=SUIT_SYMBOL.get(card.suit or "","")
    pad=max(4,int(5*WIDTH/_BASE_W))
    r_surf=SMALL.render(rank_str,True,tc); s_surf=TINY.render(suit_str,True,tc)
    screen.blit(r_surf,(rect.x+pad,rect.y+pad))
    screen.blit(s_surf,(rect.x+pad,rect.y+pad+r_surf.get_height()-2))
    bx=rect.right-pad-r_surf.get_width(); by=rect.bottom-pad-r_surf.get_height()-s_surf.get_height()+2
    screen.blit(r_surf,(bx,by+s_surf.get_height()))
    screen.blit(s_surf,(bx,by))
    big=FONT.render("🃏" if card.rank=="JKR" else suit_str,True,tc)
    cx=rect.x+(rect.w-big.get_width())//2; cy=rect.y+(rect.h-big.get_height())//2
    g=pygame.Surface((big.get_width(),big.get_height()),pygame.SRCALPHA); g.blit(big,(0,0)); g.set_alpha(40)
    screen.blit(g,(cx,cy)); screen.blit(big,(cx,cy))
    if selected:
        pygame.draw.rect(screen,ACCENT,rect,3,border_radius=12)
        pygame.draw.rect(screen,CARD_SEL,rect,1,border_radius=12)
    elif hovered:
        pygame.draw.rect(screen,CARD_HOVER,rect,3,border_radius=12)
    else:
        pygame.draw.rect(screen,(180,170,148),rect,2,border_radius=12)
    if value_override is not None: _draw_value_badge(rect,value_override)

def draw_hand_card(rect,card,selected=False,hovered=False):
    _draw_card_face(rect,card,selected=selected,hovered=hovered)

def draw_num_entry(rect,ne):
    art=CARD_ART.get_scaled(ne.card,(rect.w,rect.h),"stack") if USE_ART else None
    if art:
        draw_shadow_rect(rect,10,75)
        screen.blit(art,rect)
        pygame.draw.rect(screen,BLACK,rect,2,border_radius=10)
        _draw_value_badge(rect,ne.effective_value())
    else:
        _draw_card_face(rect,ne.card,value_override=ne.effective_value())
    bx,by=rect.right-4-PIC_BADGE_W,rect.y+5
    for p in ne.pics[-3:]:
        badge=pygame.Rect(bx,by,PIC_BADGE_W,PIC_BADGE_H)
        bs=pygame.Surface((PIC_BADGE_W,PIC_BADGE_H),pygame.SRCALPHA); bs.fill((8,12,8,210))
        screen.blit(bs,badge.topleft)
        bc=CARD_RED if p.suit in ("H","D") and p.rank not in ("JKR",) else ACCENT
        pygame.draw.rect(screen,bc,badge,1,border_radius=5)
        draw_text_center("★" if p.rank=="JKR" else p.rank,badge,bc,TINY)
        by+=PIC_BADGE_H+4

def build_entry_hitboxes(owner_name,slots,caravans):
    boxes=[]
    for ci in range(3):
        cav=caravans[ci]; base=slots[ci]
        overlap=STACK_OVERLAP_X_TIGHT if len(cav.nums)>MAX_VISIBLE_STACK else STACK_OVERLAP_X
        start=max(0,len(cav.nums)-MAX_VISIBLE_STACK)
        y=base.y+(base.height-CARD_H)//2; x0=base.x+STACK_PAD_X
        for ei in range(start,len(cav.nums)):
            r=pygame.Rect(x0+(ei-start)*overlap,y,CARD_W,CARD_H)
            boxes.append((r,owner_name,ci,ei))
    return boxes

def draw_caravan_stack(slot,cav):
    overlap=STACK_OVERLAP_X_TIGHT if len(cav.nums)>MAX_VISIBLE_STACK else STACK_OVERLAP_X
    start=max(0,len(cav.nums)-MAX_VISIBLE_STACK)
    y=slot.y+(slot.height-CARD_H)//2; x0=slot.x+STACK_PAD_X
    for ei in range(start,len(cav.nums)):
        r=pygame.Rect(x0+(ei-start)*overlap,y,CARD_W,CARD_H)
        draw_num_entry(r,cav.nums[ei])
    if start>0:
        badge=pygame.Rect(slot.x+6,slot.y+6,max(36,int(46*WIDTH/_BASE_W)),22)
        bs=pygame.Surface((badge.w,badge.h),pygame.SRCALPHA); bs.fill((8,12,8,210))
        screen.blit(bs,badge.topleft)
        pygame.draw.rect(screen,ACCENT,badge,1,border_radius=5)
        draw_text_center(f"+{start}",badge,ACCENT,TINY)

def hand_layout(area,n,sel,scroll):
    if n<=0: return [],0,0,False
    left_pad=20; title_h=max(36,int(44*WIDTH/_BASE_W)); top_pad=title_h+8
    avail=area.width-2*left_pad
    base_step=CARD_W+10; total=(n-1)*base_step+CARD_W
    def make_rects(step,x0):
        return [pygame.Rect(x0+i*step,
                            area.y+top_pad-(SELECT_RAISE if i==sel else 0),
                            CARD_W,CARD_H)
                for i in range(n)]
    if total<=avail:
        x0=area.x+left_pad+(avail-total)//2
        return make_rects(base_step,x0),0,0,False
    min_step=CARD_W+2
    step=max(min_step,int((avail-CARD_W)/max(1,n-1)))
    total2=(n-1)*step+CARD_W
    if total2>avail:
        step=base_step; total2=(n-1)*step+CARD_W
        max_sc=max(0,total2-avail); scroll=max(0,min(max_sc,scroll))
        return make_rects(step,area.x+left_pad-scroll),scroll,max_sc,True
    return make_rects(step,area.x+left_pad),0,0,False

def draw_tooltip(lines,pos):
    if not lines: return
    pad,lh=10,max(18,int(22*WIDTH/_BASE_W))
    w=max(SMALL.size(l)[0] for l in lines)+2*pad+4; h=len(lines)*lh+2*pad
    x=min(pos[0]+18,WIDTH-w-4); y=max(4,min(pos[1]-h//2,HEIGHT-h-4))
    r=pygame.Rect(x,y,w,h)
    draw_shadow_rect(r,8,100,(3,4))
    bg=pygame.Surface((w,h),pygame.SRCALPHA); bg.fill((15,26,17,230))
    pygame.draw.rect(bg,(15,26,17,230),pygame.Rect(0,0,w,h),border_radius=8)
    screen.blit(bg,r.topleft); pygame.draw.rect(screen,PANEL_BORD,r,1,border_radius=8)
    for i,l in enumerate(lines):
        draw_text(l,r.x+pad,r.y+pad+i*lh,ACCENT if i==0 else TEXT,SMALL)

def draw_achievement_popup(aid: str, until_ms: int, now: int):
    """Draw the achievement unlock popup at the top of the screen."""
    frac = min(1.0,(until_ms-now)/3500)
    alpha = int(min(255, frac*6*255))
    if alpha<=0: return
    pw,ph=max(340,int(420*WIDTH/_BASE_W)),max(60,int(72*HEIGHT/720))
    px=(WIDTH-pw)//2; py=max(8,int(20*HEIGHT/720))
    surf=pygame.Surface((pw,ph),pygame.SRCALPHA)
    pygame.draw.rect(surf,(*ACH_BG,min(220,alpha)),pygame.Rect(0,0,pw,ph),border_radius=12)
    pygame.draw.rect(surf,(*ACH_BORD,alpha),pygame.Rect(0,0,pw,ph),2,border_radius=12)
    screen.blit(surf,(px,py))
    star_r=pygame.Rect(px+10,py+(ph-36)//2,36,36)
    draw_text_center("★",star_r,ACCENT,FONT)
    tit=T(aid) if T(aid)!=aid else aid
    desc=T(aid+"_d") if T(aid+"_d")!=aid+"_d" else ""
    draw_text(tit,px+52,py+6,ACCENT,SMALL)
    if desc: draw_text(desc,px+52,py+6+SMALL.get_height()+2,TEXT_DIM,TINY)


# ============================================================
# DRAW BOARD
# ============================================================
_current_ach_popup: Optional[str] = None

def draw_board(player, bot, selected_idx, msg, msg_until,
               start_ms, phase, bot_diff, hand_scroll,
               pending_bot, undo_count, consecutive_discards,
               cached_hitboxes, game_mode=GM_NORMAL,
               turn_start_ms=0, personality_key=DEFAULT_PERSONALITY,
               p2_label="Player 2") -> UILayout:
    global _current_ach_popup

    now = pygame.time.get_ticks()
    ox, oy = get_shake_offset(now)

    # Felt background
    screen.fill(BG)
    for gy in range(0,HEIGHT,max(4,int(6*WIDTH/_BASE_W))):
        pygame.draw.line(screen,lighten(BG,3),(0,gy),(WIDTH,gy),1)

    top,bot_area,ply_area,hand_area=ui_rects()

    # Apply shake offset to all panels
    def sr(r): return pygame.Rect(r.x+ox,r.y+oy,r.w,r.h)

    draw_panel(sr(top))
    draw_panel(sr(bot_area),fill=PANEL_2)
    draw_panel(sr(ply_area),fill=PANEL_2)
    draw_panel(sr(hand_area))

    pos=pygame.mouse.get_pos()
    elapsed=now-start_ms

    # ── Top bar ───────────────────────────────────────────────
    col1=top.x+ox+16; col2=top.x+ox+220; col3=top.x+ox+440
    draw_text(T("phase_lbl",phase),    col1,top.y+oy+8,  YELLOW,SMALL)
    draw_text(T("diff_lbl",bot_diff.upper()),col2,top.y+oy+8,TEXT,SMALL)
    draw_text(T("time_lbl",format_time_ms(elapsed)),col3,top.y+oy+8,(170,170,150),SMALL)

    # Caps display
    caps_r=pygame.Rect(top.x+ox+660,top.y+oy+4,max(120,int(140*WIDTH/_BASE_W)),28)
    cs=pygame.Surface((caps_r.w,caps_r.h),pygame.SRCALPHA); cs.fill((30,25,10,160))
    pygame.draw.rect(cs,(140,110,40,200),pygame.Rect(0,0,caps_r.w,caps_r.h),1,border_radius=6)
    screen.blit(cs,caps_r.topleft)
    draw_text_center(f"⚙ {app_settings.caps}",caps_r,CAPS_CLR,SMALL)

    draw_text(T("stats_bar",app_stats.wins,app_stats.losses,app_stats.draws),
              top.x+ox+810,top.y+oy+8,(150,180,150),SMALL)

    if pending_bot and phase=="MAIN" and game_mode!=GM_HOT_SEAT:
        dots="."*(1+(now//400)%3)
        pers=PERSONALITIES.get(personality_key,BENNY)
        draw_text(T(pers.display_key)+dots,col1,top.y+oy+34,YELLOW,SMALL)
    else:
        draw_text(T("player_deck_lbl",len(player.deck),len(player.discard)),
                  col1,top.y+oy+34,(165,165,150),SMALL)
    draw_text(T("bot_deck_lbl",len(bot.deck),len(bot.discard)),
              col3,top.y+oy+34,(165,165,150),SMALL)
    if undo_count>0:
        draw_text(T("undo_hint",undo_count),top.x+ox+660,top.y+oy+34,UNDO_CLR,SMALL)
    if consecutive_discards>=STALEMATE_THRESHOLD-5:
        clr=RED if consecutive_discards>=STALEMATE_THRESHOLD-2 else YELLOW
        draw_text(T("stalemate_warn",consecutive_discards,STALEMATE_THRESHOLD),
                  top.x+ox+860,top.y+oy+34,clr,SMALL)

    hint=T("hint_opening") if phase=="OPENING" else T("hint_main")
    draw_text(hint,top.x+ox+16,top.y+oy+62,(130,130,118),TINY)

    # ── Timed mode: countdown bar ─────────────────────────────
    if game_mode==GM_TIMED and phase=="MAIN" and not pending_bot:
        elapsed_turn=now-turn_start_ms
        frac=max(0.0,1.0-(elapsed_turn/TIMED_TURN_MS))
        bar_w=max(100,int(200*WIDTH/_BASE_W)); bar_h=10
        bx=top.right+ox-bar_w-10; by=top.y+oy+(TOP_BAR_H-bar_h)//2
        pygame.draw.rect(screen,(30,40,30),(bx,by,bar_w,bar_h),border_radius=5)
        fill_w=int(bar_w*frac)
        col=(TIMER_OK if frac>0.5 else TIMER_WARN if frac>0.25 else TIMER_CRIT)
        pygame.draw.rect(screen,col,(bx,by,fill_w,bar_h),border_radius=5)
        pygame.draw.rect(screen,PANEL_BORD,(bx,by,bar_w,bar_h),1,border_radius=5)
        secs=max(0,int((TIMED_TURN_MS-elapsed_turn)//1000))
        draw_text(T("timer_lbl",secs),bx-60,by-2,col,TINY)
        if frac<=0.25 and elapsed_turn%1000<100:
            sounds.play("timer_warn")

    # ── Pause button ─────────────────────────────────────────
    pb_w=max(80,int(100*WIDTH/_BASE_W)); pb_h=max(32,int(40*WIDTH/_BASE_W))
    pb_lbl="⏸ PAUSE" if _LANG=="en" else "⏸ ПАУЗА"
    pause_btn=pygame.Rect(top.right-pb_w-8+ox,top.y+oy+(TOP_BAR_H-pb_h)//2,pb_w,pb_h)
    draw_button(pb_lbl,pause_btn,pos,(50,70,50),(80,130,80),SMALL)

    # ── Section labels ────────────────────────────────────────
    b_lbl=T("bot_caravans") if game_mode!=GM_HOT_SEAT else T("p2_caravans")
    p_lbl=T("your_caravans") if game_mode!=GM_HOT_SEAT else T("p1_caravans")
    h_lbl=T("your_hand") if game_mode!=GM_HOT_SEAT else T("p1_hand")
    draw_panel_title_bar(sr(bot_area), b_lbl)
    draw_panel_title_bar(sr(ply_area), p_lbl)
    draw_panel_title_bar(sr(hand_area), h_lbl)
    draw_text(b_lbl,bot_area.x+ox+16,bot_area.y+oy+10,ACCENT,SMALL)
    draw_text(p_lbl,ply_area.x+ox+16,ply_area.y+oy+10,ACCENT,SMALL)
    draw_text(h_lbl,hand_area.x+ox+16,hand_area.y+oy+10,ACCENT,SMALL)

    bot_slots=[pygame.Rect(r.x+ox,r.y+oy,r.w,r.h) for r in caravan_slots(bot_area)]
    ply_slots=[pygame.Rect(r.x+ox,r.y+oy,r.w,r.h) for r in caravan_slots(ply_area)]

    sel_card=player.hand[selected_idx] if 0<=selected_idx<len(player.hand) else None

    # Slot backgrounds
    for i,r in enumerate(ply_slots):
        outline=PANEL_BORD
        if sel_card and sel_card.is_number():
            outline=OUT_OK if can_play_number_on_caravan(sel_card,player.caravans[i]) else OUT_BAD
        sb=pygame.Surface((r.w,r.h),pygame.SRCALPHA); sb.fill((8,16,10,120))
        screen.blit(sb,r.topleft); pygame.draw.rect(screen,outline,r,2,border_radius=10)
    for r in bot_slots:
        sb=pygame.Surface((r.w,r.h),pygame.SRCALPHA); sb.fill((8,16,10,120))
        screen.blit(sb,r.topleft); pygame.draw.rect(screen,PANEL_BORD,r,2,border_radius=10)

    for i in range(3):
        draw_caravan_stack(bot_slots[i],bot.caravans[i])
        draw_caravan_stack(ply_slots[i],player.caravans[i])
        bs,bsold=bot.caravans[i].score(),bot.caravans[i].for_sale()
        ps,pssold=player.caravans[i].score(),player.caravans[i].for_sale()
        def score_badge(x,y,score,sold):
            bw2=max(80,int(100*WIDTH/_BASE_W)); bh2=max(20,int(26*WIDTH/_BASE_W))
            br=pygame.Rect(x,y+4,bw2,bh2)
            bs2=pygame.Surface((bw2,bh2),pygame.SRCALPHA)
            fill=(50,120,50,200) if sold else (20,35,22,180)
            pygame.draw.rect(bs2,fill,pygame.Rect(0,0,bw2,bh2),border_radius=6)
            pygame.draw.rect(bs2,ACCENT if sold else PANEL_BORD,pygame.Rect(0,0,bw2,bh2),1,border_radius=6)
            screen.blit(bs2,br.topleft)
            draw_text_center(T("score_sold",score) if sold else T("score_fmt",score),br,ACCENT if sold else TEXT,SMALL)
        score_badge(bot_slots[i].x,bot_slots[i].bottom,bs,bsold)
        score_badge(ply_slots[i].x,ply_slots[i].bottom,ps,pssold)

    # Hitboxes
    raw_bot_slots=caravan_slots(bot_area); raw_ply_slots=caravan_slots(ply_area)
    if cached_hitboxes:
        bot_boxes=[(pygame.Rect(r.x+ox,r.y+oy,r.w,r.h),own,ci,ei)
                   for r,own,ci,ei in cached_hitboxes["bot"]]
        ply_boxes=[(pygame.Rect(r.x+ox,r.y+oy,r.w,r.h),own,ci,ei)
                   for r,own,ci,ei in cached_hitboxes["player"]]
    else:
        bot_boxes=[(pygame.Rect(r.x+ox,r.y+oy,r.w,r.h),own,ci,ei)
                   for r,own,ci,ei in build_entry_hitboxes("bot",raw_bot_slots,bot.caravans)]
        ply_boxes=[(pygame.Rect(r.x+ox,r.y+oy,r.w,r.h),own,ci,ei)
                   for r,own,ci,ei in build_entry_hitboxes("player",raw_ply_slots,player.caravans)]

    tooltip_lines=[]
    if sel_card and sel_card.is_picture():
        for r,own,ci,ei in ply_boxes+bot_boxes:
            tgt=player if own=="player" else bot
            ne=tgt.caravans[ci].nums[ei]
            ok=can_play_picture_on_target(sel_card,ne,ei==len(tgt.caravans[ci].nums)-1)
            pygame.draw.rect(screen,OUT_OK if ok else OUT_BAD,r,2,border_radius=10)
            if r.collidepoint(pos):
                pygame.draw.rect(screen,OUT_OK if ok else OUT_BAD,r,4,border_radius=10)
                tooltip_lines=ne.tooltip_lines()
    else:
        for r,own,ci,ei in ply_boxes+bot_boxes:
            if r.collidepoint(pos):
                tgt=player if own=="player" else bot
                tooltip_lines=tgt.caravans[ci].nums[ei].tooltip_lines()
                break

    # Hand
    ha=pygame.Rect(hand_area.x+ox,hand_area.y+oy,hand_area.w,hand_area.h)
    rects,hand_scroll,max_scroll,scroll_on=hand_layout(ha,len(player.hand),selected_idx,hand_scroll)
    hover_idx=get_idx_at(pos,rects)
    for i,c in enumerate(player.hand):
        if rects[i].right<ha.x+10 or rects[i].x>ha.right-10: continue
        draw_hand_card(rects[i],c,selected=(i==selected_idx),hovered=(i==hover_idx))

    if scroll_on and max_scroll>0:
        bar_w2=min(320,ha.width-80)
        bar=pygame.Rect(ha.x+(ha.width-bar_w2)//2,ha.y+40,bar_w2,8)
        pygame.draw.rect(screen,(80,80,80),bar,border_radius=6)
        vw=bar_w2+max_scroll; kw=max(20,int(bar_w2*bar_w2/vw))
        t=hand_scroll/max_scroll if max_scroll>0 else 0
        kx=int(bar.x+t*(bar_w2-kw))
        pygame.draw.rect(screen,BTN_H,pygame.Rect(kx,bar.y,kw,bar.height),border_radius=6)
        pygame.draw.rect(screen,BLACK,bar,2,border_radius=6)

    if msg and now<msg_until:
        mr=pygame.Rect(ha.x+20,ha.bottom-52,ha.width-40,40)
        ms=pygame.Surface((mr.w,mr.h),pygame.SRCALPHA); ms.fill((35,10,10,200))
        screen.blit(ms,mr.topleft)
        pygame.draw.rect(screen,RED,mr,1,border_radius=10)
        draw_text_center(msg,mr,TEXT,SMALL)

    if tooltip_lines: draw_tooltip(tooltip_lines,pos)

    # ── Particle system ──────────────────────────────────────
    # Consume deferred bursts (from play_number hitting 26)
    for b in list(_deferred_bursts):
        btype,ci2,aname=b[0],b[1],b[2]
        if btype=="cav26":
            # Use player slot if player, bot slot if bot
            slot_list = ply_slots if aname!="Bot" and aname!="Bot A" else bot_slots
            if 0<=ci2<3:
                sr2=slot_list[ci2]
                cx2=sr2.x+sr2.w//2; cy2=sr2.y+sr2.h//2
                particles.burst(cx2,cy2,(195,162,52),30,5)
                particles.burst(cx2,cy2,(100,220,120),15,3)
    _deferred_bursts.clear()
    particles.tick_draw(screen)

    # ── Hover card preview (enlarged above hand) ─────────────
    if hover_idx!=-1 and 0<=hover_idx<len(player.hand) and hover_idx!=selected_idx:
        hc=player.hand[hover_idx]
        hr=rects[hover_idx] if hover_idx<len(rects) else None
        if hr:
            pw2=int(CARD_W*1.65); ph2=int(CARD_H*1.65)
            px2=hr.centerx-pw2//2
            py2=hr.y-ph2-18
            # Keep in screen bounds
            px2=max(4,min(px2,WIDTH-pw2-4))
            py2=max(4,py2)
            preview_r=pygame.Rect(px2,py2,pw2,ph2)
            draw_shadow_rect(preview_r,14,120,(6,8))
            _draw_card_face(preview_r,hc)
            # Value hint below preview
            if hc.is_number():
                vr=pygame.Rect(px2,py2+ph2+4,pw2,24)
                vs=pygame.Surface((pw2,24),pygame.SRCALPHA); vs.fill((12,20,14,200))
                screen.blit(vs,vr.topleft)
                pygame.draw.rect(screen,PANEL_BORD,vr,1,border_radius=5)
                draw_text_center(f"Value: {hc.value()}",vr,ACCENT,TINY)

    # ── Bot tell bubble ──────────────────────────────────────
    if _bot_tell_msg and now<_bot_tell_until:
        frac=min(1.0,(_bot_tell_until-now)/400)
        alpha=int(min(255,frac*8*255))
        tell_surf=SMALL.render(_bot_tell_msg,True,_bot_tell_color)
        tw,th=tell_surf.get_width()+24,tell_surf.get_height()+14
        tx=bot_area.x+ox+bot_area.width//2-tw//2
        ty=bot_area.y+oy-th-8
        ty=max(4,ty)
        bg2=pygame.Surface((tw,th),pygame.SRCALPHA)
        bg2.fill((12,20,14,min(220,alpha)))
        pygame.draw.rect(bg2,(*_bot_tell_color[:3],alpha),pygame.Rect(0,0,tw,th),2,border_radius=10)
        screen.blit(bg2,(tx,ty))
        ts2=SMALL.render(_bot_tell_msg,True,(*_bot_tell_color[:3],))
        ts2.set_alpha(alpha)
        screen.blit(ts2,(tx+12,ty+7))
        # Speech-bubble tail
        tail=[(tx+tw//2-6,ty+th),(tx+tw//2+6,ty+th),(tx+tw//2,ty+th+10)]
        tsurf=pygame.Surface((20,14),pygame.SRCALPHA)
        pygame.draw.polygon(screen,(*_bot_tell_color[:3],alpha//2),tail)

    # Achievement popup
    _current_ach_popup=tick_achievement_popup(now)
    if _current_ach_popup:
        draw_achievement_popup(_current_ach_popup,_ach_popup_until,now)

    pygame.display.flip()

    return UILayout(
        bot_slots=raw_bot_slots, ply_slots=raw_ply_slots,
        hand_rects=rects, bot_boxes=[(r,o,c,e) for r,o,c,e in
                                      build_entry_hitboxes("bot",raw_bot_slots,bot.caravans)],
        ply_boxes=[(r,o,c,e) for r,o,c,e in
                   build_entry_hitboxes("player",raw_ply_slots,player.caravans)],
        hand_scroll=hand_scroll, hand_max_scroll=max_scroll, hand_scroll_on=scroll_on,
        pause_btn=pause_btn,
    )


# ============================================================
# PAUSE MENU
# ============================================================
def pause_menu(allow_undo=False) -> str:
    backdrop=screen.copy()
    dim=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA); dim.fill((0,0,0,150))
    pygame.event.clear()
    while True:
        clock.tick(FPS)
        pw,ph=min(440,WIDTH-40),min(480,HEIGHT-80)
        panel=pygame.Rect(WIDTH//2-pw//2,HEIGHT//2-ph//2,pw,ph)
        screen.blit(backdrop,(0,0)); screen.blit(dim,(0,0))
        draw_panel(panel,glow=True)
        draw_panel_title_bar(panel,"PAUSE" if _LANG=="en" else "ПАУЗА")
        draw_text_center("PAUSE" if _LANG=="en" else "ПАУЗА",
                         pygame.Rect(panel.x,panel.y+8,pw,52),ACCENT,TITLE)
        pygame.draw.line(screen,PANEL_BORD,(panel.x+30,panel.y+64),(panel.right-30,panel.y+64),1)
        pos=pygame.mouse.get_pos()
        bw,bh=max(200,int(pw*0.60)),54
        bx=panel.x+(pw-bw)//2
        r_lbl="▶  Resume" if _LANG=="en" else "▶  Продолжить"
        s_lbl="⚙  Settings" if _LANG=="en" else "⚙  Настройки"
        q_lbl="✕  Leave match" if _LANG=="en" else "✕  Выйти из матча"
        row1=panel.y+int(ph*0.30); row2=panel.y+int(ph*0.47); row3=panel.y+int(ph*0.64)
        r_rect=pygame.Rect(bx,row1,bw,bh)
        s_rect=pygame.Rect(bx,row2,bw,bh)
        q_rect=pygame.Rect(bx,row3,bw,bh)
        draw_button(r_lbl,r_rect,pos,BTN,BTN_H)
        draw_button(s_lbl,s_rect,pos,BTN,BTN_H)
        draw_button(q_lbl,q_rect,pos,(100,28,28),lighten((100,28,28),30))
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type==pygame.QUIT: app_settings.save(); pygame.quit(); sys.exit()
            if e.type==pygame.KEYDOWN and e.key==pygame.K_ESCAPE: return "resume"
            if e.type==pygame.MOUSEBUTTONDOWN and e.button==1:
                if r_rect.collidepoint(e.pos): return "resume"
                if s_rect.collidepoint(e.pos): settings_menu(); return "resume"
                if q_rect.collidepoint(e.pos): return "quit_match"


# ============================================================
# SETTINGS MENU
# ============================================================
def settings_menu():
    volume=app_settings.volume; sfx_vol=app_settings.sfx_volume
    muted=app_settings.muted; bot_use=app_settings.bot_uses_player_deck
    drag_music=False; drag_sfx=False
    pygame.event.clear()
    while True:
        clock.tick(FPS)
        pw,ph=min(820,WIDTH-40),min(740,HEIGHT-40)
        panel=pygame.Rect(WIDTH//2-pw//2,max(10,HEIGHT//2-ph//2),pw,ph)
        sl_x=panel.x+int(0.18*pw); sl_w=int(0.64*pw); sl_h=14
        m_sl_y=panel.y+int(0.28*ph); s_sl_y=panel.y+int(0.40*ph)
        mhx=sl_x+int(volume*sl_w); shx=sl_x+int(sfx_vol*sl_w)

        screen.fill(BG)
        for gy in range(0,HEIGHT,max(4,int(6*WIDTH/_BASE_W))):
            pygame.draw.line(screen,lighten(BG,3),(0,gy),(WIDTH,gy),1)
        draw_panel(panel); draw_panel_title_bar(panel,T("settings_title"))
        draw_text_center(T("settings_title"),pygame.Rect(panel.x,panel.y+8,pw,52),ACCENT,TITLE)
        pos=pygame.mouse.get_pos()

        def draw_slider(lbl,val,sx,sy):
            draw_text(lbl,panel.x+int(0.18*pw),sy-26,TEXT,FONT)
            pygame.draw.rect(screen,(20,38,22),(sx,sy,sl_w,sl_h),border_radius=7)
            pygame.draw.rect(screen,BTN_H,(sx,sy,max(0,int(val*sl_w)),sl_h),border_radius=7)
            pygame.draw.rect(screen,PANEL_BORD,(sx,sy,sl_w,sl_h),1,border_radius=7)
            hx2=sx+int(val*sl_w)
            kc=ACCENT if (drag_music if lbl.startswith("Vol") or lbl.startswith("Гр") else drag_sfx) else BTN_H
            pygame.draw.circle(screen,(10,18,12),(hx2,sy+sl_h//2),14)
            pygame.draw.circle(screen,kc,(hx2,sy+sl_h//2),12)
            pygame.draw.circle(screen,lighten(kc,50),(hx2,sy+sl_h//2),6)
            return hx2

        draw_slider(T("volume_pct",int(volume*100)),volume,sl_x,m_sl_y)
        draw_slider(T("sfx_pct",int(sfx_vol*100)),sfx_vol,sl_x,s_sl_y)

        bw,bh=int(0.40*pw),50
        c1x=panel.x+int(0.06*pw); c2x=panel.x+int(0.54*pw)
        r1y=panel.y+int(0.52*ph); r2y=panel.y+int(0.62*ph)
        mut_r=pygame.Rect(c1x,r1y,bw,bh); bot_r=pygame.Rect(c2x,r1y,bw,bh)
        lng_r=pygame.Rect(c1x,r2y,bw,bh); fsr=pygame.Rect(c2x,r2y,bw,bh)

        draw_button(T("sound_off") if muted else T("sound_on"),mut_r,pos,font=SMALL)
        draw_button(T("bot_deck_yes") if bot_use else T("bot_deck_no"),bot_r,pos,font=SMALL)
        draw_button(T("lang_btn"),lng_r,pos,font=SMALL)
        fs_lbl=("Fullscreen: ON" if app_settings.fullscreen else "Fullscreen: OFF") if _LANG=="en" else \
               ("Полный экран: ВКЛ" if app_settings.fullscreen else "Полный экран: ВЫКЛ")
        draw_button(fs_lbl,fsr,pos,font=SMALL)

        # Player name
        name_lbl = f"Name: {app_settings.player_name}" if _LANG=="en" else f"Имя: {app_settings.player_name}"
        name_r = pygame.Rect(c1x, r2y+bh+12, bw, bh)
        draw_button(name_lbl, name_r, pos, font=SMALL)

        # Card back row
        cb_y=panel.y+int(0.74*ph)
        draw_text(T("card_back",BACK_NAMES[app_settings.card_back]),
                  panel.x+int(0.06*pw),cb_y-24,TEXT_DIM,SMALL)
        cb_rects=[]
        cbw=max(60,int(70*WIDTH/_BASE_W)); cbh=max(44,int(52*HEIGHT/720))
        for bi in range(4):
            r=pygame.Rect(panel.x+20+bi*(cbw+8),cb_y,cbw,cbh)
            s=get_card_back_surf(bi,cbw,cbh); screen.blit(s,r.topleft)
            if bi==app_settings.card_back:
                pygame.draw.rect(screen,ACCENT,r,3,border_radius=8)
            elif r.collidepoint(*pos):
                pygame.draw.rect(screen,PANEL_BORD,r,2,border_radius=8)
            cb_rects.append(r)

        # Resolution row
        res_y=panel.y+int(0.85*ph)
        draw_text(T("resolution")+":",panel.x+int(0.06*pw),res_y-22,TEXT_DIM,SMALL)
        rbw=max(76,(pw-40)//4-10); rbh=44; res_rects=[]
        for ri,(rw2,rh2,rlabel) in enumerate(RESOLUTIONS):
            rrect=pygame.Rect(panel.x+20+ri*(rbw+10),res_y,rbw,rbh)
            is_active=(app_settings.resolution==f"{rw2}x{rh2}")
            draw_button(rlabel,rrect,pos,RES_ACTIVE if is_active else BTN,
                        RES_ACT_H if is_active else BTN_H,SMALL)
            res_rects.append((rrect,rw2,rh2))   # FIX #5: store Rect, not draw_button() bool

        back_r=pygame.Rect(panel.x+(pw-200)//2,panel.bottom-62,200,50)
        draw_button(T("back"),back_r,pos,font=SMALL)
        draw_text(f"W:{app_stats.wins}  L:{app_stats.losses}  D:{app_stats.draws}  streak:{app_stats.win_streak}",
                  panel.x+24,panel.bottom-22,TEXT_DIM,TINY)
        pygame.display.flip()

        for e in pygame.event.get():
            if e.type==pygame.QUIT: app_settings.save(); pygame.quit(); sys.exit()
            if e.type==pygame.KEYDOWN and e.key==pygame.K_ESCAPE:
                app_settings.save(); return
            if e.type==pygame.MOUSEBUTTONDOWN:
                if abs(e.pos[0]-mhx)<=18 and abs(e.pos[1]-(m_sl_y+sl_h//2))<=18: drag_music=True
                elif abs(e.pos[0]-shx)<=18 and abs(e.pos[1]-(s_sl_y+sl_h//2))<=18: drag_sfx=True
                elif mut_r.collidepoint(e.pos):
                    muted=not muted; app_settings.muted=muted
                    app_settings.apply_audio(); app_settings.save()
                elif bot_r.collidepoint(e.pos):
                    bot_use=not bot_use; app_settings.bot_uses_player_deck=bot_use; app_settings.save()
                elif lng_r.collidepoint(e.pos):
                    app_settings.language="ru" if app_settings.language=="en" else "en"
                    app_settings.apply_language(); app_settings.save()
                elif fsr.collidepoint(e.pos):
                    app_settings.fullscreen=not app_settings.fullscreen; app_settings.save()
                    apply_resolution(*map(int,app_settings.resolution.split("x")),
                                     fullscreen=app_settings.fullscreen)
                elif name_r.collidepoint(e.pos):
                    new_name=name_input_screen(app_settings.player_name)
                    app_settings.player_name=new_name; app_settings.save()
                elif back_r.collidepoint(e.pos):
                    app_settings.volume=volume; app_settings.sfx_volume=sfx_vol
                    app_settings.muted=muted; app_settings.bot_uses_player_deck=bot_use
                    app_settings.save(); return
                else:
                    for bi,br in enumerate(cb_rects):
                        if br.collidepoint(*e.pos):
                            app_settings.card_back=bi; app_settings.save(); break
                    for rrect2,rw2,rh2 in res_rects:   # FIX #5: use collidepoint on stored Rect
                        if rrect2.collidepoint(*e.pos):
                            new_key=f"{rw2}x{rh2}"
                            if app_settings.resolution!=new_key:
                                app_settings.resolution=new_key; app_settings.save()
                                apply_resolution(rw2,rh2,fullscreen=app_settings.fullscreen)
                            break
            if e.type==pygame.MOUSEBUTTONUP:
                drag_music=False; drag_sfx=False
                app_settings.volume=volume; app_settings.sfx_volume=sfx_vol; app_settings.save()
            if e.type==pygame.MOUSEMOTION:
                if drag_music:
                    volume=max(0.0,min(1.0,(e.pos[0]-sl_x)/sl_w))
                    app_settings.volume=volume
                    if AUDIO_OK and not muted: pygame.mixer.music.set_volume(volume)
                if drag_sfx:
                    sfx_vol=max(0.0,min(1.0,(e.pos[0]-sl_x)/sl_w))
                    app_settings.sfx_volume=sfx_vol


# ============================================================
# MODE SELECT + PERSONALITY SELECT + BETTING
# ============================================================
def mode_select_menu() -> Optional[str]:
    pygame.event.clear()
    while True:
        clock.tick(FPS)
        pw,ph=min(560,WIDTH-40),min(520,HEIGHT-80)
        panel=pygame.Rect(WIDTH//2-pw//2,HEIGHT//2-ph//2,pw,ph)
        screen.fill(BG)
        for gy in range(0,HEIGHT,max(4,int(6*WIDTH/_BASE_W))):
            pygame.draw.line(screen,lighten(BG,3),(0,gy),(WIDTH,gy),1)
        draw_panel(panel); draw_panel_title_bar(panel,T("mode_title"))
        draw_text_center(T("mode_title"),pygame.Rect(panel.x,panel.y+8,pw,52),ACCENT,TITLE)
        pos=pygame.mouse.get_pos()
        bw,bh=max(240,int(pw*0.60)),56; bx=panel.x+(pw-bw)//2
        modes=[(GM_NORMAL,T("mode_normal"),BTN,BTN_H),
               (GM_HOT_SEAT,T("mode_hotSeat"),BTN,BTN_H),
               (GM_TIMED,T("mode_timed"),BTN,BTN_H),
               (GM_TOURNAMENT,T("mode_tournament"),(70,50,20),(110,80,30)),
               ("campaign","🗺 Mojave Campaign" if _LANG=="en" else "🗺 Кампания Мохаве",(40,60,80),(60,90,120)),
               ("spectator","👁 AI vs AI" if _LANG=="en" else "👁 Бот vs Бот",(50,40,70),(80,60,110)),
               ("network",  "🌐 Network (LAN/Hamachi)" if _LANG=="en" else "🌐 Сеть (LAN/Hamachi)",(30,60,90),(50,90,130))]
        mode_rects=[]
        for ii,(key,lbl,col,hcol) in enumerate(modes):
            r=pygame.Rect(bx,panel.y+int(ph*(0.22+ii*0.117)),bw,bh)
            mode_rects.append((r,key))
            draw_button(lbl,r,pos,col,hcol)
        back_r=pygame.Rect(bx,panel.bottom-58,bw,44)
        draw_button(T("back"),back_r,pos,font=SMALL)
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type==pygame.QUIT: app_settings.save(); pygame.quit(); sys.exit()
            if e.type==pygame.KEYDOWN and e.key==pygame.K_ESCAPE: return None
            if e.type==pygame.MOUSEBUTTONDOWN and e.button==1:
                for r,key in mode_rects:
                    if r.collidepoint(e.pos): return key
                if back_r.collidepoint(e.pos): return None

def personality_select_menu() -> str:
    keys=list(PERSONALITIES.keys())
    pygame.event.clear()
    while True:
        clock.tick(FPS)
        pw,ph=min(560,WIDTH-40),min(460,HEIGHT-80)
        panel=pygame.Rect(WIDTH//2-pw//2,HEIGHT//2-ph//2,pw,ph)
        screen.fill(BG)
        for gy in range(0,HEIGHT,max(4,int(6*WIDTH/_BASE_W))):
            pygame.draw.line(screen,lighten(BG,3),(0,gy),(WIDTH,gy),1)
        draw_panel(panel); draw_panel_title_bar(panel,T("choose_bot"))
        draw_text_center(T("choose_bot"),pygame.Rect(panel.x,panel.y+8,pw,52),ACCENT,TITLE)
        pos=pygame.mouse.get_pos()
        bw,bh=max(240,int(pw*0.60)),56; bx=panel.x+(pw-bw)//2
        pers_rects=[]
        for ii,pk in enumerate(keys):
            pers=PERSONALITIES[pk]
            r=pygame.Rect(bx,panel.y+int(ph*(0.28+ii*0.19)),bw,bh)
            pers_rects.append((r,pk))
            draw_button(T(pers.display_key),r,pos)
        back_r=pygame.Rect(bx,panel.bottom-58,bw,44)
        draw_button(T("back"),back_r,pos,font=SMALL)
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type==pygame.QUIT: app_settings.save(); pygame.quit(); sys.exit()
            if e.type==pygame.KEYDOWN and e.key==pygame.K_ESCAPE: return None
            if e.type==pygame.MOUSEBUTTONDOWN and e.button==1:
                for r,pk in pers_rects:
                    if r.collidepoint(e.pos): return pk
                if back_r.collidepoint(e.pos): return None

# FIX #2: difficulty_menu event loop used undefined 'mode_rects' — changed to 'diff_rects'
def difficulty_menu() -> Optional[str]:
    pygame.event.clear()
    while True:
        clock.tick(FPS)
        pw,ph=min(560,WIDTH-40),min(520,HEIGHT-80)
        panel=pygame.Rect(WIDTH//2-pw//2,HEIGHT//2-ph//2,pw,ph)
        screen.fill(BG)
        for gy in range(0,HEIGHT,max(4,int(6*WIDTH/_BASE_W))):
            pygame.draw.line(screen,lighten(BG,3),(0,gy),(WIDTH,gy),1)
        draw_panel(panel); draw_panel_title_bar(panel,T("diff_title"))
        draw_text_center(T("diff_title"),pygame.Rect(panel.x,panel.y+8,pw,52),ACCENT,TITLE)
        pos=pygame.mouse.get_pos()
        bw,bh=max(220,int(pw*0.52)),56; bx=panel.x+(pw-bw)//2
        diffs=[("easy",BTN,BTN_H),("medium",BTN,BTN_H),
               ("hard",BTN,BTN_H),("impossible",(100,28,28),lighten((100,28,28),30))]
        diff_rects=[]
        for ii,(key,col,hcol) in enumerate(diffs):
            r=pygame.Rect(bx,panel.y+int(ph*(0.28+ii*0.155)),bw,bh)
            diff_rects.append((r,key))
            draw_button(T(key),r,pos,col,hcol)
        back_r=pygame.Rect(bx,panel.bottom-58,bw,44)
        draw_button(T("back"),back_r,pos,font=SMALL)
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type==pygame.QUIT: app_settings.save(); pygame.quit(); sys.exit()
            if e.type==pygame.KEYDOWN and e.key==pygame.K_ESCAPE: return None
            if e.type==pygame.MOUSEBUTTONDOWN and e.button==1:
                for r,key in diff_rects:          # was mode_rects — fixed
                    if r.collidepoint(e.pos): return key
                if back_r.collidepoint(e.pos): return None

def betting_menu(diff: str) -> int:
    """Returns the bet amount (0 if skipped/not enough caps)."""
    MIN_BET=50; MAX_BET=min(app_settings.caps,500); STEP=50
    if MAX_BET<MIN_BET: return 0
    bet=MIN_BET
    pygame.event.clear()
    while True:
        clock.tick(FPS)
        pw,ph=min(500,WIDTH-40),min(380,HEIGHT-80)
        panel=pygame.Rect(WIDTH//2-pw//2,HEIGHT//2-ph//2,pw,ph)
        screen.fill(BG)
        for gy in range(0,HEIGHT,max(4,int(6*WIDTH/_BASE_W))):
            pygame.draw.line(screen,lighten(BG,3),(0,gy),(WIDTH,gy),1)
        draw_panel(panel); draw_panel_title_bar(panel,T("betting_title"))
        draw_text_center(T("betting_title"),pygame.Rect(panel.x,panel.y+8,pw,52),ACCENT,TITLE)
        draw_text_center(T("caps_balance",app_settings.caps),
                         pygame.Rect(panel.x,panel.y+60,pw,30),CAPS_CLR,FONT)
        draw_text_center(T("bet_amount",bet),
                         pygame.Rect(panel.x,panel.y+100,pw,40),TEXT,TITLE)
        # Multiplier info
        mults={"easy":1.0,"medium":1.2,"hard":1.5,"impossible":2.0}
        m=mults.get(diff,1.0)
        win_amt=int(bet*m)
        info=f"+{win_amt} caps on win  |  -{bet} on loss"
        draw_text_center(info,pygame.Rect(panel.x,panel.y+150,pw,26),TEXT_DIM,SMALL)
        pos=pygame.mouse.get_pos()
        bw=max(50,int(60*WIDTH/_BASE_W)); bh=44
        mid=panel.y+int(ph*0.56)
        dn_r=pygame.Rect(panel.x+int(pw*0.12),mid,bw,bh)
        up_r=pygame.Rect(panel.x+int(pw*0.72),mid,bw,bh)
        cf_r=pygame.Rect(panel.x+(pw-200)//2,mid+60,200,52)
        sk_r=pygame.Rect(panel.x+(pw-160)//2,panel.bottom-58,160,44)
        draw_button("−",dn_r,pos,font=TITLE)
        draw_button("+",up_r,pos,font=TITLE)
        draw_button(T("bet_confirm"),cf_r,pos,BTN,BTN_H)
        draw_button(T("back"),sk_r,pos,(70,70,70),lighten((70,70,70),20),SMALL)
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type==pygame.QUIT: app_settings.save(); pygame.quit(); sys.exit()
            if e.type==pygame.KEYDOWN and e.key==pygame.K_ESCAPE: return None
            if e.type==pygame.MOUSEBUTTONDOWN and e.button==1:
                if dn_r.collidepoint(e.pos): bet=max(MIN_BET,bet-STEP)
                elif up_r.collidepoint(e.pos): bet=min(MAX_BET,bet+STEP)
                elif cf_r.collidepoint(e.pos): return bet
                elif sk_r.collidepoint(e.pos): return None  # Back → go back


# ============================================================
# STATS / ACHIEVEMENTS / HISTORY / LEADERBOARD
# ============================================================
def stats_screen():
    pygame.event.clear()
    while True:
        clock.tick(FPS)
        pw,ph=min(620,WIDTH-40),min(480,HEIGHT-80)
        panel=pygame.Rect(WIDTH//2-pw//2,HEIGHT//2-ph//2,pw,ph)
        screen.fill(BG)
        for gy in range(0,HEIGHT,max(4,int(6*WIDTH/_BASE_W))):
            pygame.draw.line(screen,lighten(BG,3),(0,gy),(WIDTH,gy),1)
        draw_panel(panel); draw_panel_title_bar(panel,T("stats_title"))
        draw_text_center(T("stats_title"),pygame.Rect(panel.x,panel.y+8,pw,52),ACCENT,TITLE)
        pos=pygame.mouse.get_pos()
        lines=[T("games_played",app_stats.games_played),T("wins_line",app_stats.wins),
               T("losses_line",app_stats.losses),T("draws_line",app_stats.draws),
               T("avg_time_line",app_stats.avg_time_str()),
               T("streak_line",app_stats.best_streak),T("caps_line",app_settings.caps)]
        row_h=max(32,int(38*HEIGHT/720))
        for ii,l in enumerate(lines):
            if ii%2==0:
                rr=pygame.Rect(panel.x+12,panel.y+106+ii*row_h,pw-24,row_h-4)
                rs=pygame.Surface((rr.w,rr.h),pygame.SRCALPHA); rs.fill((40,65,42,80))
                screen.blit(rs,rr.topleft)
            draw_text(l,panel.x+50,panel.y+112+ii*row_h,TEXT,FONT)
        bw=max(140,int(pw*0.32))
        reset_r=pygame.Rect(panel.x+int(pw*0.10),panel.bottom-66,bw,50)
        back_r=pygame.Rect(panel.x+int(pw*0.58),panel.bottom-66,bw,50)
        draw_button(T("reset_stats"),reset_r,pos,(100,28,28),lighten((100,28,28),30),SMALL)
        draw_button(T("back"),back_r,pos,font=SMALL)
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type==pygame.QUIT: app_settings.save(); pygame.quit(); sys.exit()
            if e.type==pygame.KEYDOWN and e.key==pygame.K_ESCAPE: return
            if e.type==pygame.MOUSEBUTTONDOWN and e.button==1:
                if reset_r.collidepoint(e.pos): app_stats.__init__(); app_stats.save()
                if back_r.collidepoint(e.pos): return

def achievements_screen():
    pygame.event.clear()
    while True:
        clock.tick(FPS)
        pw,ph=min(680,WIDTH-40),min(HEIGHT-40,760)
        panel=pygame.Rect(WIDTH//2-pw//2,max(10,HEIGHT//2-ph//2),pw,ph)
        screen.fill(BG)
        for gy in range(0,HEIGHT,max(4,int(6*WIDTH/_BASE_W))):
            pygame.draw.line(screen,lighten(BG,3),(0,gy),(WIDTH,gy),1)
        draw_panel(panel); draw_panel_title_bar(panel,T("ach_title"))
        unlocked_count=sum(1 for v in _ach_unlocked.values() if v)
        draw_text_center(T("ach_title"),pygame.Rect(panel.x,panel.y+8,pw,52),ACCENT,TITLE)
        draw_text_center(T("ach_unlocked",unlocked_count,len(ACH_IDS)),
                         pygame.Rect(panel.x,panel.y+58,pw,28),TEXT_DIM,SMALL)
        pygame.draw.line(screen,PANEL_BORD,(panel.x+20,panel.y+88),(panel.right-20,panel.y+88),1)
        pos=pygame.mouse.get_pos()
        row_h=max(44,int(50*HEIGHT/720)); start_y=panel.y+96
        for ii,aid in enumerate(ACH_IDS):
            ry=start_y+ii*row_h
            if ry+row_h>panel.bottom-70: break
            unlocked=_ach_unlocked.get(aid,False)
            row_r=pygame.Rect(panel.x+12,ry,pw-24,row_h-4)
            rs=pygame.Surface((row_r.w,row_r.h),pygame.SRCALPHA)
            rs.fill((50,80,52,90) if unlocked else (20,30,22,60))
            screen.blit(rs,row_r.topleft)
            if unlocked: pygame.draw.rect(screen,(80,130,60,120),row_r,1,border_radius=4)
            star_col=ACCENT if unlocked else TEXT_DIM
            draw_text("★" if unlocked else "○",panel.x+20,ry+(row_h-4-FONT.get_height())//2,
                      star_col,FONT)
            draw_text(T(aid),panel.x+52,ry+4,ACCENT if unlocked else TEXT,SMALL)
            draw_text(T(aid+"_d"),panel.x+52,ry+4+SMALL.get_height()+2,TEXT_DIM,TINY)
        back_r=pygame.Rect(panel.x+(pw-200)//2,panel.bottom-60,200,50)
        draw_button(T("back"),back_r,pos,font=SMALL)
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type==pygame.QUIT: app_settings.save(); pygame.quit(); sys.exit()
            if e.type==pygame.KEYDOWN and e.key==pygame.K_ESCAPE: return
            if e.type==pygame.MOUSEBUTTONDOWN and e.button==1:
                if back_r.collidepoint(e.pos): return

def history_screen():
    h=load_history()
    pygame.event.clear()
    while True:
        clock.tick(FPS)
        pw,ph=min(700,WIDTH-40),min(580,HEIGHT-40)
        panel=pygame.Rect(WIDTH//2-pw//2,max(10,HEIGHT//2-ph//2),pw,ph)
        screen.fill(BG)
        for gy in range(0,HEIGHT,max(4,int(6*WIDTH/_BASE_W))):
            pygame.draw.line(screen,lighten(BG,3),(0,gy),(WIDTH,gy),1)
        draw_panel(panel); draw_panel_title_bar(panel,T("history"))
        draw_text_center(T("history"),pygame.Rect(panel.x,panel.y+8,pw,52),ACCENT,TITLE)
        pygame.draw.line(screen,PANEL_BORD,(panel.x+20,panel.y+64),(panel.right-20,panel.y+64),1)
        pos=pygame.mouse.get_pos()
        hd=panel.y+72
        for col,label in [(panel.x+20,"Date"),(panel.x+140,"Result"),
                          (panel.x+250,"Diff"),(panel.x+360,"Mode"),
                          (panel.x+470,"Time"),(panel.x+560,"Caps")]:
            draw_text(label,col,hd,TEXT_DIM,TINY)
        row_h=max(34,int(38*HEIGHT/720))
        for ii,r in enumerate(reversed(h[-10:])):
            ry=hd+row_h+ii*row_h
            if ry+row_h>panel.bottom-70: break
            rs_r=pygame.Rect(panel.x+12,ry,pw-24,row_h-4)
            rsurf=pygame.Surface((rs_r.w,rs_r.h),pygame.SRCALPHA)
            rsurf.fill((40,65,42,60) if ii%2==0 else (20,35,22,40))
            screen.blit(rsurf,rs_r.topleft)
            rc=OUT_OK if r.result=="win" else RED if r.result=="loss" else YELLOW
            draw_text(r.date,panel.x+20,ry+4,TEXT_DIM,TINY)
            draw_text(r.result.upper(),panel.x+140,ry+4,rc,SMALL)
            draw_text(r.difficulty[:4],panel.x+250,ry+4,TEXT,TINY)
            draw_text(r.mode[:6],panel.x+360,ry+4,TEXT,TINY)
            draw_text(format_time_ms(r.duration_s*1000),panel.x+470,ry+4,TEXT_DIM,TINY)
            cap_c=CAPS_CLR if r.caps_delta>=0 else RED
            draw_text(f"{'+' if r.caps_delta>=0 else ''}{r.caps_delta}",
                      panel.x+560,ry+4,cap_c,TINY)
        back_r=pygame.Rect(panel.x+(pw-200)//2,panel.bottom-60,200,50)
        draw_button(T("back"),back_r,pos,font=SMALL)
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type==pygame.QUIT: app_settings.save(); pygame.quit(); sys.exit()
            if e.type==pygame.KEYDOWN and e.key==pygame.K_ESCAPE: return
            if e.type==pygame.MOUSEBUTTONDOWN and e.button==1:
                if back_r.collidepoint(e.pos): return

def leaderboard_screen():
    h=load_history()
    wins=[r for r in h if r.result=="win"]
    wins.sort(key=lambda r:r.duration_s)
    pygame.event.clear()
    while True:
        clock.tick(FPS)
        pw,ph=min(640,WIDTH-40),min(520,HEIGHT-40)
        panel=pygame.Rect(WIDTH//2-pw//2,max(10,HEIGHT//2-ph//2),pw,ph)
        screen.fill(BG)
        for gy in range(0,HEIGHT,max(4,int(6*WIDTH/_BASE_W))):
            pygame.draw.line(screen,lighten(BG,3),(0,gy),(WIDTH,gy),1)
        draw_panel(panel); draw_panel_title_bar(panel,T("leaderboard"))
        draw_text_center(T("leaderboard"),pygame.Rect(panel.x,panel.y+8,pw,52),ACCENT,TITLE)
        draw_text_center("Fastest wins",pygame.Rect(panel.x,panel.y+58,pw,26),TEXT_DIM,SMALL)
        pygame.draw.line(screen,PANEL_BORD,(panel.x+20,panel.y+88),(panel.right-20,panel.y+88),1)
        pos=pygame.mouse.get_pos()
        rank_y=panel.y+100; row_h=max(36,int(42*HEIGHT/720))
        medals=["🥇","🥈","🥉"]
        for ii,r in enumerate(wins[:10]):
            ry=rank_y+ii*row_h
            if ry+row_h>panel.bottom-70: break
            rs=pygame.Surface((pw-24,row_h-4),pygame.SRCALPHA)
            rs.fill((50,80,52,80) if ii<3 else (30,45,32,50))
            screen.blit(rs,(panel.x+12,ry))
            medal=medals[ii] if ii<3 else f"#{ii+1}"
            draw_text(medal,panel.x+20,ry+4,ACCENT if ii<3 else TEXT_DIM,SMALL)
            draw_text(format_time_ms(r.duration_s*1000),panel.x+80,ry+4,TEXT,SMALL)
            draw_text(r.difficulty,panel.x+220,ry+4,TEXT_DIM,SMALL)
            draw_text(r.date,panel.x+360,ry+4,TEXT_DIM,TINY)
        if not wins:
            draw_text_center("No wins yet!",pygame.Rect(panel.x,panel.y+200,pw,40),TEXT_DIM,FONT)
        back_r=pygame.Rect(panel.x+(pw-200)//2,panel.bottom-60,200,50)
        draw_button(T("back"),back_r,pos,font=SMALL)
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type==pygame.QUIT: app_settings.save(); pygame.quit(); sys.exit()
            if e.type==pygame.KEYDOWN and e.key==pygame.K_ESCAPE: return
            if e.type==pygame.MOUSEBUTTONDOWN and e.button==1:
                if back_r.collidepoint(e.pos): return

def deck_builder_menu():
    all_cards=standard_card_list(True)
    keys=load_deck_selection()
    selected=set(keys) if keys else set(c.key() for c in all_cards)
    rank_order={"A":1,"2":2,"3":3,"4":4,"5":5,"6":6,"7":7,"8":8,"9":9,"10":10,"J":11,"Q":12,"K":13,"JKR":14}
    suit_order={"S":0,"H":1,"D":2,"C":3,None:4}
    all_sorted=sorted(all_cards,key=lambda c:(suit_order.get(c.suit,9),rank_order.get(c.rank,99)))
    notify,notify_until="",0
    pygame.event.clear()
    while True:
        clock.tick(FPS)
        panel=pygame.Rect(14,30,WIDTH-28,HEIGHT-60)
        grid=pygame.Rect(panel.x+16,panel.y+64,panel.width-32,panel.height-136)
        cols=max(1,grid.width//(GRID_CARD_W+10))
        def cell_rect(i): return pygame.Rect(grid.x+(i%cols)*(GRID_CARD_W+10),grid.y+(i//cols)*(GRID_CARD_H+10),GRID_CARD_W,GRID_CARD_H)
        screen.fill(BG)
        for gy in range(0,HEIGHT,max(4,int(6*WIDTH/_BASE_W))): pygame.draw.line(screen,lighten(BG,3),(0,gy),(WIDTH,gy),1)
        draw_panel(panel); draw_panel_title_bar(panel,T("deck_builder"))
        draw_text(T("deck_builder"),panel.x+18,panel.y+10,ACCENT,TITLE)
        cnt=len(selected)
        draw_text(T("selected_cnt",cnt),panel.x+int(panel.width*0.44),panel.y+18,OUT_OK if cnt>=30 else RED,SMALL)
        pos=pygame.mouse.get_pos()
        btn_y=panel.bottom-68; bw2=max(120,(panel.width-60)//5-8)
        b=[pygame.Rect(panel.x+18+k*(bw2+8),btn_y,bw2,50) for k in range(5)]
        draw_button(T("standard_54"),b[0],pos,font=SMALL)
        draw_button(T("auto_30"),b[1],pos,font=SMALL)
        draw_button(T("clear"),b[2],pos,(70,70,70),lighten((70,70,70),30),SMALL)
        draw_button(T("save"),b[3],pos,font=SMALL)
        draw_button(T("back"),b[4],pos,(100,28,28),lighten((100,28,28),30),SMALL)
        # Archetype row
        arch_y=btn_y-56
        arch_lbl="Archetypes:" if _LANG=="en" else "Архетипы:"
        draw_text(arch_lbl,panel.x+18,arch_y+8,TEXT_DIM,SMALL)
        aw=max(100,int((panel.width-140)//3-8))
        a_rects=[]
        arch_defs=[("⚔ The Blitz","Kings heavy"),("💣 The Wrecker","Jacks+Jokers"),("⚖ Balanced","Mixed")]
        for ai,(albl,_) in enumerate(arch_defs):
            ar=pygame.Rect(panel.x+120+ai*(aw+8),arch_y,aw,40)
            a_rects.append(ar)
            draw_button(albl,ar,pos,BTN,BTN_H,TINY)
        for i,c in enumerate(all_sorted):
            r=cell_rect(i)
            if r.bottom>grid.bottom: continue
            on=c.key() in selected
            thumb=CARD_ART.get_scaled(c,(r.w,r.h),"thumb") if USE_ART else None
            if thumb:
                screen.blit(thumb,r)
                pygame.draw.rect(screen,OUT_OK if on else (60,80,62),r,2,border_radius=8)
            else:
                pygame.draw.rect(screen,CARD_FACE if on else (50,65,52),r,border_radius=8)
                pygame.draw.rect(screen,OUT_OK if on else PANEL_BORD,r,1,border_radius=8)
                draw_text_center(c.label(),r,_card_text_color(c) if on else TEXT_DIM,SMALL)
            if r.collidepoint(pos): pygame.draw.rect(screen,ACCENT,r,2,border_radius=8)
        now=pygame.time.get_ticks()
        if notify and now<notify_until:
            mr=pygame.Rect(panel.x+16,panel.y+56,panel.width-32,28)
            ms=pygame.Surface((mr.w,mr.h),pygame.SRCALPHA); ms.fill((60,12,12,200))
            screen.blit(ms,mr.topleft); pygame.draw.rect(screen,RED,mr,1,border_radius=8)
            draw_text_center(notify,mr,RED,SMALL)
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type==pygame.QUIT: app_settings.save(); pygame.quit(); sys.exit()
            if e.type==pygame.KEYDOWN and e.key==pygame.K_ESCAPE: return
            if e.type==pygame.MOUSEBUTTONDOWN and e.button==1:
                if b[0].collidepoint(e.pos): selected=set(c.key() for c in all_cards); continue
                if b[1].collidepoint(e.pos):
                    selected=set()
                    nums=[c for c in all_cards if c.is_number()]; pics=[c for c in all_cards if c.is_picture() and c.rank!="JKR"]; joks=[c for c in all_cards if c.rank=="JKR"]
                    random.shuffle(nums); random.shuffle(pics); random.shuffle(joks)
                    for c in nums[:22]: selected.add(c.key())
                    for c in pics[:7]: selected.add(c.key())
                    if joks: selected.add(joks[0].key())
                    selected=set(ensure_min30_selection(list(selected))); continue
                if b[2].collidepoint(e.pos): selected=set(); continue
                if b[3].collidepoint(e.pos):
                    if cnt<30: notify=T("need_30"); notify_until=now+1400; continue
                    save_deck_selection(sorted(selected)); notify=T("deck_saved"); notify_until=now+1000; continue
                if b[4].collidepoint(e.pos): return
                # Archetype buttons
                if a_rects[0].collidepoint(*e.pos):
                    # The Blitz: heavy Kings, all numbers
                    selected=set()
                    nums2=[c for c in all_cards if c.is_number()]
                    kings2=[c for c in all_cards if c.rank=="K"]
                    others2=[c for c in all_cards if c.is_picture() and c.rank not in ("K","JKR")]
                    joks2=[c for c in all_cards if c.rank=="JKR"]
                    for c in nums2: selected.add(c.key())
                    for c in kings2: selected.add(c.key())
                    for c in others2[:2]: selected.add(c.key())
                    for c in joks2[:1]: selected.add(c.key())
                    selected=set(ensure_min30_selection(list(selected)))
                    notify="⚔ The Blitz loaded!"; notify_until=now+1000; continue
                if a_rects[1].collidepoint(*e.pos):
                    # The Wrecker: Jacks + Jokers + enough numbers
                    selected=set()
                    nums3=[c for c in all_cards if c.is_number()]
                    jacks3=[c for c in all_cards if c.rank=="J"]
                    joks3=[c for c in all_cards if c.rank=="JKR"]
                    queens3=[c for c in all_cards if c.rank=="Q"]
                    random.shuffle(nums3)
                    for c in nums3[:22]: selected.add(c.key())
                    for c in jacks3: selected.add(c.key())
                    for c in joks3: selected.add(c.key())
                    for c in queens3[:2]: selected.add(c.key())
                    selected=set(ensure_min30_selection(list(selected)))
                    notify="💣 The Wrecker loaded!"; notify_until=now+1000; continue
                if a_rects[2].collidepoint(*e.pos):
                    # Balanced: even spread
                    selected=set()
                    for suit in ["S","H","D","C"]:
                        for rank in ["A","2","4","6","8","10","J","Q","K"]:
                            c2=Card(rank,suit)
                            if c2 in all_cards: selected.add(c2.key())
                    joks4=[c for c in all_cards if c.rank=="JKR"]
                    for c in joks4: selected.add(c.key())
                    selected=set(ensure_min30_selection(list(selected)))
                    notify="⚖ Balanced loaded!"; notify_until=now+1000; continue
                for i2,c2 in enumerate(all_sorted):
                    r2=cell_rect(i2)
                    if r2.bottom>grid.bottom: continue
                    if r2.collidepoint(*e.pos):
                        k=c2.key(); selected.discard(k) if k in selected else selected.add(k); break


# ============================================================
# MAIN MENU + END SCREEN
# ============================================================
def main_menu() -> str:
    deco_cards=[(Card("A","S"),pygame.Rect(int(WIDTH*0.04),int(HEIGHT*0.10),int(CARD_W*1.6),int(CARD_H*1.6))),
                (Card("K","H"),pygame.Rect(int(WIDTH*0.88),int(HEIGHT*0.08),int(CARD_W*1.4),int(CARD_H*1.4))),
                (Card("Q","D"),pygame.Rect(int(WIDTH*0.06),int(HEIGHT*0.62),int(CARD_W*1.3),int(CARD_H*1.3))),
                (Card("J","C"),pygame.Rect(int(WIDTH*0.86),int(HEIGHT*0.60),int(CARD_W*1.5),int(CARD_H*1.5)))]
    pygame.event.clear()
    while True:
        clock.tick(FPS)
        pw,ph=min(520,WIDTH-40),min(700,HEIGHT-40)
        panel=pygame.Rect(WIDTH//2-pw//2,HEIGHT//2-ph//2,pw,ph)
        screen.fill(BG)
        for gy in range(0,HEIGHT,max(4,int(6*WIDTH/_BASE_W))): pygame.draw.line(screen,lighten(BG,3),(0,gy),(WIDTH,gy),1)
        for dc,dr in deco_cards:
            surf=pygame.Surface((dr.w,dr.h),pygame.SRCALPHA); surf.set_alpha(38)
            img=CARD_ART.get_scaled(dc,(dr.w,dr.h),"hand") if USE_ART else None
            if img: surf.blit(img,(0,0))
            else: pygame.draw.rect(surf,(*CARD_FACE,38),pygame.Rect(0,0,dr.w,dr.h),border_radius=10)
            screen.blit(surf,dr.topleft)
        draw_panel(panel,glow=True); draw_panel_title_bar(panel,T("title"))
        draw_text_center(T("title"),pygame.Rect(panel.x,panel.y+10,pw,62),ACCENT,TITLE)
        div_y=panel.y+74
        pygame.draw.line(screen,ACCENT,(panel.x+30,div_y),(panel.right-30,div_y),1)
        draw_text_center(T("subtitle"),pygame.Rect(panel.x,div_y+4,pw,30),TEXT_DIM,SMALL)
        draw_text_center(f"⚙ {app_settings.caps} caps",pygame.Rect(panel.x,panel.y+106,pw,24),CAPS_CLR,SMALL)
        streak=app_stats.win_streak
        if streak>0:
            fires="🔥"*min(streak,5)
            streak_col=(230,80,80) if streak>=5 else (230,160,40) if streak>=3 else YELLOW
            draw_text_center(f"{fires} Streak: {streak} {fires}",
                             pygame.Rect(panel.x,panel.y+130,pw,28),streak_col,FONT)
        pos=pygame.mouse.get_pos()
        bw,bh=max(200,int(pw*0.52)),54
        bx=panel.x+(pw-bw)//2
        btn_defs=[(T("play"),BTN,BTN_H,panel.y+int(ph*0.25)),
                  (T("deck"),BTN,BTN_H,panel.y+int(ph*0.36)),
                  (T("settings"),BTN,BTN_H,panel.y+int(ph*0.47)),
                  (T("stats"),BTN,BTN_H,panel.y+int(ph*0.57)),
                  (T("achievements"),BTN,BTN_H,panel.y+int(ph*0.67)),
                  (T("history"),BTN,BTN_H,panel.y+int(ph*0.77)),
                  (T("quit"),(100,28,28),lighten((100,28,28),30),panel.y+int(ph*0.88))]
        menu_rects=[]
        for label,col,hcol,ry in btn_defs:
            r=pygame.Rect(bx,ry,bw,bh)
            menu_rects.append(r)
            draw_button(label,r,pos,col,hcol)
        draw_text_center("v3.0  Full Edition",pygame.Rect(panel.x,panel.bottom-20,pw,18),TEXT_DIM,TINY)
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type==pygame.QUIT: app_settings.save(); pygame.quit(); sys.exit()
            if e.type==pygame.MOUSEBUTTONDOWN and e.button==1:
                if menu_rects[0].collidepoint(e.pos): return "play"
                if menu_rects[1].collidepoint(e.pos): deck_builder_menu()
                if menu_rects[2].collidepoint(e.pos): settings_menu()
                if menu_rects[3].collidepoint(e.pos): stats_screen()
                if menu_rects[4].collidepoint(e.pos): achievements_screen()
                if menu_rects[5].collidepoint(e.pos): history_screen(); leaderboard_screen()
                if menu_rects[6].collidepoint(e.pos): app_settings.save(); pygame.quit(); sys.exit()

def end_screen(text,elapsed_ms,caps_delta=0):
    is_win=("player" in text.lower() or "игрок" in text.lower() or
            "p1" in text.lower() or "игр. 1" in text.lower() or "bot a" in text.lower())
    is_draw=("draw" in text.lower() or "ничья" in text.lower())
    hdr_col=OUT_OK if is_win else (YELLOW if is_draw else RED)
    sounds.play("win" if is_win else "lose")
    if is_win: particles.confetti(80)
    pygame.event.clear()
    while True:
        clock.tick(FPS)
        pw,ph=min(700,WIDTH-40),min(460,HEIGHT-60)
        panel=pygame.Rect(WIDTH//2-pw//2,HEIGHT//2-ph//2,pw,ph)
        screen.fill(BG)
        for gy in range(0,HEIGHT,max(4,int(6*WIDTH/_BASE_W))): pygame.draw.line(screen,lighten(BG,3),(0,gy),(WIDTH,gy),1)
        particles.tick_draw(screen)
        draw_panel(panel,glow=is_win); draw_panel_title_bar(panel,text,color=hdr_col)
        draw_text_center(text,pygame.Rect(panel.x,panel.y+8,pw,58),hdr_col,TITLE)
        pygame.draw.line(screen,PANEL_BORD,(panel.x+30,panel.y+68),(panel.right-30,panel.y+68),1)
        draw_text_center(T("match_time",format_time_ms(elapsed_ms)),
                         pygame.Rect(panel.x,panel.y+80,pw,38),TEXT,FONT)
        draw_text_center(T("stats_end",app_stats.wins,app_stats.losses,app_stats.draws,app_stats.avg_time_str()),
                         pygame.Rect(panel.x,panel.y+122,pw,32),TEXT_DIM,SMALL)
        if caps_delta!=0:
            cc=CAPS_CLR if caps_delta>0 else RED
            cdelta_txt=T("caps_won",caps_delta) if caps_delta>0 else T("caps_lost",abs(caps_delta))
            draw_text_center(cdelta_txt,pygame.Rect(panel.x,panel.y+158,pw,30),cc,FONT)
        draw_text_center(f"⚙ {app_settings.caps} caps total",
                         pygame.Rect(panel.x,panel.y+192,pw,26),CAPS_CLR,SMALL)
        pos=pygame.mouse.get_pos()
        bw2=max(170,int(pw*0.36)); gap2=pw//7
        again_r=pygame.Rect(panel.x+gap2,panel.y+int(ph*0.60),bw2,58)
        menu_r=pygame.Rect(panel.x+pw-gap2-bw2,panel.y+int(ph*0.60),bw2,58)
        draw_button(T("play_again"),again_r,pos)
        draw_button(T("main_menu_btn"),menu_r,pos,(100,28,28),lighten((100,28,28),30))
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type==pygame.QUIT: app_settings.save(); pygame.quit(); sys.exit()
            if e.type==pygame.MOUSEBUTTONDOWN and e.button==1:
                if again_r.collidepoint(e.pos): return "restart"
                if menu_r.collidepoint(e.pos): return "menu"


# ============================================================
# PASS SCREEN (Hot Seat)
# ============================================================
def hot_seat_pass_screen(next_player_name: str):
    backdrop=screen.copy()
    dim=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA); dim.fill((0,0,0,200))
    pygame.event.clear()
    while True:
        clock.tick(FPS)
        screen.blit(backdrop,(0,0)); screen.blit(dim,(0,0))
        pw,ph=min(480,WIDTH-40),min(220,HEIGHT-80)
        panel=pygame.Rect(WIDTH//2-pw//2,HEIGHT//2-ph//2,pw,ph)
        draw_panel(panel,glow=True)
        draw_text_center(T("pass_screen_title",next_player_name),
                         pygame.Rect(panel.x,panel.y+20,pw,60),ACCENT,TITLE)
        draw_text_center(T("pass_screen_hint"),pygame.Rect(panel.x,panel.y+90,pw,30),TEXT_DIM,SMALL)
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type==pygame.QUIT: app_settings.save(); pygame.quit(); sys.exit()
            if e.type in (pygame.KEYDOWN,pygame.MOUSEBUTTONDOWN): return


# ============================================================
# TOURNAMENT SCREEN
# ============================================================
def tournament_results_screen(results: list):
    """Show tournament bracket. results = [(round, result, diff)]"""
    pygame.event.clear()
    while True:
        clock.tick(FPS)
        pw,ph=min(540,WIDTH-40),min(420,HEIGHT-80)
        panel=pygame.Rect(WIDTH//2-pw//2,HEIGHT//2-ph//2,pw,ph)
        screen.fill(BG)
        for gy in range(0,HEIGHT,max(4,int(6*WIDTH/_BASE_W))): pygame.draw.line(screen,lighten(BG,3),(0,gy),(WIDTH,gy),1)
        draw_panel(panel); draw_panel_title_bar(panel,T("tourn_title"))
        draw_text_center(T("tourn_title"),pygame.Rect(panel.x,panel.y+8,pw,52),ACCENT,TITLE)
        row_h=max(50,int(58*HEIGHT/720))
        for ii,(rnd,res,diff) in enumerate(results):
            ry=panel.y+76+ii*row_h
            rs=pygame.Surface((pw-24,row_h-8),pygame.SRCALPHA)
            rs.fill((50,80,52,80) if res=="win" else (80,20,20,80))
            screen.blit(rs,(panel.x+12,ry))
            draw_text(T("tourn_round",rnd),panel.x+24,ry+8,TEXT,SMALL)
            draw_text(diff.capitalize(),panel.x+200,ry+8,TEXT_DIM,SMALL)
            rc=OUT_OK if res=="win" else RED
            draw_text(T("tourn_win") if res=="win" else T("tourn_loss"),panel.x+340,ry+8,rc,FONT)
        all_win=all(r[1]=="win" for r in results)
        if len(results)==3:
            draw_text_center(T("tourn_champion") if all_win else T("tourn_eliminated",len(results)),
                             pygame.Rect(panel.x,panel.bottom-100,pw,36),
                             OUT_OK if all_win else RED,FONT)
        pos=pygame.mouse.get_pos()
        back_r=pygame.Rect(panel.x+(pw-200)//2,panel.bottom-60,200,50)
        draw_button(T("back"),back_r,pos,font=SMALL)
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type==pygame.QUIT: app_settings.save(); pygame.quit(); sys.exit()
            if e.type==pygame.KEYDOWN and e.key==pygame.K_ESCAPE: return
            if e.type==pygame.MOUSEBUTTONDOWN and e.button==1:
                if back_r.collidepoint(e.pos): return


# ============================================================
# OPENING PHASE HELPERS
# ============================================================
def bot_opening_play(bot):
    empty=[i for i in range(3) if bot.caravans[i].empty()]
    if not empty: return
    num_idxs=[i for i,c in enumerate(bot.hand) if c.is_number()]
    if not num_idxs:
        for c in bot.hand: bot.discard.append(c)
        bot.hand=[]; bot.deck.extend(bot.discard); bot.discard=[]; random.shuffle(bot.deck)
        draw_to_hand(bot,HAND_OPENING_SIZE)
        num_idxs=[i for i,c in enumerate(bot.hand) if c.is_number()]
        if not num_idxs: return
    i=random.choice(num_idxs); card=bot.hand.pop(i)
    bot.caravans[empty[0]].nums.append(NumEntry(card=card))

def take_snapshot(player,bot): return copy.deepcopy((player,bot))
def restore_snapshot(snap): return copy.deepcopy(snap)


# ============================================================
# SINGLE MATCH GAME LOOP
# ============================================================
def run_match(diff: str, game_mode: str = GM_NORMAL,
              personality_key: str = DEFAULT_PERSONALITY,
              bet: int = 0) -> Tuple[str,int,int]:
    """
    Run one match. Returns (winner_choice, elapsed_ms, caps_delta).
    winner_choice: "restart" | "menu" | "tournament_win" | "tournament_loss"
    """
    sel_keys=load_deck_selection()
    if sel_keys: sel_keys=ensure_min30_selection(sel_keys)
    p_deck=build_deck_from_selection(sel_keys)
    b_deck=build_deck_from_selection(sel_keys if app_settings.bot_uses_player_deck else None)

    p_name="Player 1" if game_mode==GM_HOT_SEAT else app_settings.player_name
    b_name="Player 2" if game_mode==GM_HOT_SEAT else "Bot"

    player=PlayerState(p_name,[Caravan() for _ in range(3)],p_deck,[],[])
    bot=PlayerState(b_name,[Caravan() for _ in range(3)],b_deck,[],[])
    draw_to_hand(player,HAND_OPENING_SIZE); draw_to_hand(bot,HAND_OPENING_SIZE)

    phase="OPENING"; opening_halfturn=0
    match_start_ms=pygame.time.get_ticks()
    selected=-1; msg=""; msg_until=0; hand_scroll=0
    player_to_move=True; pending_bot=False; pending_at=0
    undo_stack: List[Tuple] = []
    consecutive_discards=0; hitboxes_dirty=True
    cached_hit: Optional[Dict]=None
    winner_choice=None; running=True
    turn_start_ms=match_start_ms
    # FIX #4: player_lost_first is now updated during the game loop
    player_lost_first=False

    while running:
        clock.tick(FPS)
        now=pygame.time.get_ticks()

        # Timed mode: auto-discard if time's up
        if game_mode==GM_TIMED and phase=="MAIN" and player_to_move and not pending_bot:
            if now-turn_start_ms>=TIMED_TURN_MS:
                if player.hand:
                    sounds.play("discard")
                    if undo_stack and len(undo_stack)>=UNDO_LEVELS: undo_stack.pop(0)
                    undo_stack.append(take_snapshot(player,bot))
                    discard_hand_card(player,0)
                    draw_to_hand(player,HAND_TARGET_SIZE)
                    consecutive_discards+=1; hitboxes_dirty=True
                    if game_mode!=GM_HOT_SEAT:
                        pending_bot=True; pending_at=now+BOT_DELAY_MS[diff]
                    player_to_move=False; selected=-1; turn_start_ms=now
                    msg=T("timer_expired"); msg_until=now+1200

        if hitboxes_dirty:
            _,ba_,pa_,_=ui_rects()
            cached_hit={
                "bot":    build_entry_hitboxes("bot",   caravan_slots(ba_),bot.caravans),
                "player": build_entry_hitboxes("player",caravan_slots(pa_),player.caravans),
            }
            hitboxes_dirty=False

        ui=draw_board(
            player=player,bot=bot,selected_idx=selected,msg=msg,msg_until=msg_until,
            start_ms=match_start_ms,phase=phase,bot_diff=diff,hand_scroll=hand_scroll,
            pending_bot=pending_bot,undo_count=len(undo_stack),
            consecutive_discards=consecutive_discards,cached_hitboxes=cached_hit,
            game_mode=game_mode,turn_start_ms=turn_start_ms,personality_key=personality_key,
            p2_label=b_name,
        )
        hand_scroll=ui.hand_scroll

        # Bot turn (not hot seat)
        if game_mode!=GM_HOT_SEAT and phase=="MAIN" and pending_bot and now>=pending_at:
            ok2,rmsg,was_play=bot_take_turn(bot,player,diff,personality_key)
            pending_bot=False; player_to_move=True; selected=-1
            hitboxes_dirty=True; turn_start_ms=now
            consecutive_discards=(0 if was_play else consecutive_discards+1)
            if not ok2:
                elapsed=now-match_start_ms
                app_stats.record("win",elapsed); app_stats.save()
                sounds.play("win")
                caps_delta=int(bet*{"easy":1.0,"medium":1.2,"hard":1.5,"impossible":2.0}.get(diff,1.0)) if bet>0 else 0
                app_settings.caps+=caps_delta; app_settings.save()
                check_post_match_achievements("win",diff,game_mode,elapsed,
                    player_lost_first=player_lost_first, all_three=False)
                add_history("win",diff,game_mode,elapsed,caps_delta)
                wc=end_screen(T("player_wins_deck"),elapsed,caps_delta)
                return wc,elapsed,caps_delta
            elif rmsg: msg=rmsg; msg_until=now+1600

        if msg and now>=msg_until: msg=""

        if phase=="MAIN" and running:
            # FIX #4: Track whether bot won a caravan before player did (for COMEBACK achievement)
            if not player_lost_first:
                player_has_won = any(
                    slot_outcome(player.caravans[_i].score(), player.caravans[_i].for_sale(),
                                 bot.caravans[_i].score(),    bot.caravans[_i].for_sale())[1]=="player"
                    for _i in range(3)
                )
                if not player_has_won:
                    for _i in range(3):
                        _st, _w = slot_outcome(
                            player.caravans[_i].score(), player.caravans[_i].for_sale(),
                            bot.caravans[_i].score(),    bot.caravans[_i].for_sale()
                        )
                        if _st=="ready" and _w=="bot":
                            player_lost_first = True
                            break

            ended,win,_=check_game_end(player,bot)
            if ended:
                elapsed=now-match_start_ms
                # FIX #4: Removed dead bw2 loop; compute all_three cleanly
                wp=sum(1 for i in range(3) if slot_outcome(
                    player.caravans[i].score(),player.caravans[i].for_sale(),
                    bot.caravans[i].score(),bot.caravans[i].for_sale())[1]=="player")
                all_three=(wp==3) if win=="player" else False

                result="win" if win=="player" else "loss"
                app_stats.record(result,elapsed); app_stats.save()
                sounds.play("win" if result=="win" else "lose")
                mults={"easy":1.0,"medium":1.2,"hard":1.5,"impossible":2.0}
                if result=="win":
                    caps_delta=int(bet*mults.get(diff,1.0)) if bet>0 else 0
                    app_settings.caps+=caps_delta
                else:
                    caps_delta=-bet if bet>0 else 0
                    app_settings.caps=max(0,app_settings.caps+caps_delta)
                app_settings.save()
                check_post_match_achievements(result,diff,game_mode,elapsed,
                    player_lost_first=player_lost_first,all_three=all_three)
                add_history(result,diff,game_mode,elapsed,caps_delta)
                if game_mode==GM_TOURNAMENT:
                    return ("tournament_win" if result=="win" else "tournament_loss"),elapsed,caps_delta
                # FIX #6: In hot-seat the player/bot variables may be swapped; use .name to pick correct end text
                if game_mode==GM_HOT_SEAT:
                    # whichever name is in the winning slot tells us who actually won
                    winner_name = player.name if win=="player" else bot.name
                    wtxt = T("p1_wins") if winner_name == p_name else T("p2_wins")
                else:
                    wtxt=T("player_wins") if win=="player" else T("bot_wins")
                wc=end_screen(wtxt,elapsed,caps_delta)
                return wc,elapsed,caps_delta
            if consecutive_discards>=STALEMATE_THRESHOLD:
                elapsed=now-match_start_ms
                app_stats.record("draw",elapsed); app_stats.save()
                caps_delta=-bet//2 if bet>0 else 0
                app_settings.caps=max(0,app_settings.caps+caps_delta); app_settings.save()
                add_history("draw",diff,game_mode,elapsed,caps_delta)
                if game_mode==GM_TOURNAMENT:
                    return "tournament_loss",elapsed,caps_delta
                wc=end_screen(T("draw_stalemate"),elapsed,caps_delta)
                return wc,elapsed,caps_delta

        # ── Event loop ────────────────────────────────────────
        for e in pygame.event.get():
            if e.type==pygame.QUIT: app_settings.save(); pygame.quit(); sys.exit()

            if e.type==pygame.KEYDOWN:
                if e.key==pygame.K_ESCAPE:
                    result=pause_menu(allow_undo=len(undo_stack)>0)
                    if result=="quit_match":
                        elapsed=now-match_start_ms
                        app_stats.record("loss",elapsed); app_stats.save()
                        if bet>0:
                            app_settings.caps=max(0,app_settings.caps-bet); app_settings.save()
                        add_history("loss",diff,game_mode,elapsed,-bet)
                        return "menu",elapsed,-bet
                    hitboxes_dirty=True; continue
                n=len(player.hand)
                if e.key==pygame.K_RIGHT and n>0: selected=(max(selected,0)+1)%n
                elif e.key==pygame.K_LEFT and n>0: selected=(max(selected,0)-1)%n

                if phase=="MAIN" and player_to_move:
                    if e.key==pygame.K_u and undo_stack:
                        player,bot=restore_snapshot(undo_stack.pop())
                        selected=-1; consecutive_discards=0; hitboxes_dirty=True
                        turn_start_ms=now; msg=T("undone"); msg_until=now+800; continue
                    if e.key==pygame.K_d and 0<=selected<len(player.hand):
                        if len(undo_stack)>=UNDO_LEVELS: undo_stack.pop(0)
                        undo_stack.append(take_snapshot(player,bot))
                        sounds.play("discard")
                        if discard_hand_card(player,selected):
                            if not draw_to_hand(player,HAND_TARGET_SIZE):
                                elapsed=now-match_start_ms; app_stats.record("loss",elapsed); app_stats.save()
                                caps_delta=-bet if bet>0 else 0; app_settings.caps=max(0,app_settings.caps+caps_delta); app_settings.save()
                                add_history("loss",diff,game_mode,elapsed,caps_delta)
                                wc=end_screen(T("bot_wins_deck"),elapsed,caps_delta); return wc,elapsed,caps_delta
                            consecutive_discards+=1; hitboxes_dirty=True
                            if game_mode==GM_HOT_SEAT:
                                player_to_move=False; selected=-1; turn_start_ms=now
                                hot_seat_pass_screen(b_name); player,bot=bot,player; hitboxes_dirty=True; player_to_move=True
                            else:
                                pending_bot=True; pending_at=now+BOT_DELAY_MS[diff]
                                player_to_move=False; selected=-1; turn_start_ms=now
                        else: undo_stack.pop()
                    cav_keys={pygame.K_1:0,pygame.K_2:1,pygame.K_3:2}
                    if e.key in cav_keys and 0<=selected<len(player.hand):
                        ci=cav_keys[e.key]; c=player.hand[selected]
                        if c.is_number():
                            if len(undo_stack)>=UNDO_LEVELS: undo_stack.pop(0)
                            undo_stack.append(take_snapshot(player,bot))
                            ok,emsg=play_number(player,selected,ci)
                            if not ok: msg=emsg; msg_until=now+1400; undo_stack.pop()
                            else:
                                sounds.play("play_card"); selected=-1; hitboxes_dirty=True
                                consecutive_discards=0
                                if not draw_to_hand(player,HAND_TARGET_SIZE):
                                    elapsed=now-match_start_ms; app_stats.record("loss",elapsed); app_stats.save()
                                    caps_delta=-bet if bet>0 else 0; app_settings.caps=max(0,app_settings.caps+caps_delta); app_settings.save()
                                    add_history("loss",diff,game_mode,elapsed,caps_delta)
                                    wc=end_screen(T("bot_wins_deck"),elapsed,caps_delta); return wc,elapsed,caps_delta
                                if game_mode==GM_HOT_SEAT:
                                    player_to_move=False; turn_start_ms=now
                                    hot_seat_pass_screen(b_name); player,bot=bot,player; hitboxes_dirty=True; player_to_move=True
                                else:
                                    pending_bot=True; pending_at=now+BOT_DELAY_MS[diff]
                                    player_to_move=False; turn_start_ms=now

            if e.type==pygame.MOUSEWHEEL and ui.hand_scroll_on:
                hand_scroll=max(0,min(ui.hand_max_scroll,hand_scroll-e.y*50))

            # Pause button click
            if e.type==pygame.MOUSEBUTTONDOWN and e.button==1:
                if ui.pause_btn.collidepoint(*e.pos):
                    result=pause_menu(allow_undo=len(undo_stack)>0)
                    if result=="quit_match":
                        elapsed=now-match_start_ms; app_stats.record("loss",elapsed); app_stats.save()
                        caps_delta=-bet if bet>0 else 0; app_settings.caps=max(0,app_settings.caps+caps_delta); app_settings.save()
                        add_history("loss",diff,game_mode,elapsed,caps_delta)
                        return "menu",elapsed,caps_delta
                    hitboxes_dirty=True; continue

            # ── OPENING PHASE ─────────────────────────────────
            if phase=="OPENING" and player_to_move:
                if e.type==pygame.MOUSEBUTTONDOWN and e.button==1:
                    mpos=e.pos
                    hi=get_idx_at(mpos,ui.hand_rects)
                    if hi!=-1: selected=-1 if selected==hi else hi; continue
                    if 0<=selected<len(player.hand):
                        c=player.hand[selected]
                        if not c.is_number(): msg=T("opening_nums_only"); msg_until=now+1200; selected=-1; continue
                        for ci,r in enumerate(ui.ply_slots):
                            if r.collidepoint(*mpos):
                                if not player.caravans[ci].empty():
                                    msg=T("caravan_started"); msg_until=now+1200; selected=-1; break
                                sounds.play("deal")
                                card=player.hand.pop(selected)
                                player.caravans[ci].nums.append(NumEntry(card=card))
                                selected=-1; hitboxes_dirty=True
                                opening_halfturn+=1; player_to_move=False
                                if game_mode==GM_HOT_SEAT:
                                    hot_seat_pass_screen(b_name); player,bot=bot,player; hitboxes_dirty=True; player_to_move=True
                                    opening_halfturn+=1
                                else:
                                    bot_opening_play(bot); opening_halfturn+=1; player_to_move=True; hitboxes_dirty=True
                                if opening_halfturn>=6:
                                    phase="MAIN"; player.hand=player.hand[:HAND_TARGET_SIZE]; bot.hand=bot.hand[:HAND_TARGET_SIZE]
                                    if not draw_to_hand(player,HAND_TARGET_SIZE):
                                        elapsed=now-match_start_ms; app_stats.record("loss",elapsed); app_stats.save(); wc=end_screen(T("bot_wins_deck"),elapsed); return wc,elapsed,0
                                    if not draw_to_hand(bot,HAND_TARGET_SIZE):
                                        elapsed=now-match_start_ms; app_stats.record("win",elapsed); app_stats.save(); wc=end_screen(T("player_wins_deck"),elapsed); return wc,elapsed,0
                                    turn_start_ms=now
                                break
                continue

            # ── MAIN PHASE ────────────────────────────────────
            if phase=="MAIN" and player_to_move:
                if e.type==pygame.MOUSEBUTTONDOWN:
                    mpos=e.pos
                    if e.button==3:
                        hi=get_idx_at(mpos,ui.hand_rects)
                        if hi!=-1:
                            if len(undo_stack)>=UNDO_LEVELS: undo_stack.pop(0)
                            undo_stack.append(take_snapshot(player,bot))
                            sounds.play("discard")
                            if discard_hand_card(player,hi):
                                if not draw_to_hand(player,HAND_TARGET_SIZE):
                                    elapsed=now-match_start_ms; app_stats.record("loss",elapsed); app_stats.save()
                                    caps_delta=-bet if bet>0 else 0; app_settings.caps=max(0,app_settings.caps+caps_delta); app_settings.save()
                                    add_history("loss",diff,game_mode,elapsed,caps_delta); wc=end_screen(T("bot_wins_deck"),elapsed,caps_delta); return wc,elapsed,caps_delta
                                consecutive_discards+=1; hitboxes_dirty=True
                                if game_mode==GM_HOT_SEAT:
                                    player_to_move=False; turn_start_ms=now
                                    hot_seat_pass_screen(b_name); player,bot=bot,player; hitboxes_dirty=True; player_to_move=True
                                else:
                                    pending_bot=True; pending_at=now+BOT_DELAY_MS[diff]; player_to_move=False; selected=-1; turn_start_ms=now
                            else: undo_stack.pop()
                            continue
                        for ci,r in enumerate(ui.ply_slots):
                            if r.collidepoint(*mpos):
                                if len(undo_stack)>=UNDO_LEVELS: undo_stack.pop(0)
                                undo_stack.append(take_snapshot(player,bot))
                                if disband_caravan(player,ci):
                                    if not draw_to_hand(player,HAND_TARGET_SIZE):
                                        elapsed=now-match_start_ms; app_stats.record("loss",elapsed); app_stats.save()
                                        caps_delta=-bet if bet>0 else 0; app_settings.caps=max(0,app_settings.caps+caps_delta); app_settings.save()
                                        add_history("loss",diff,game_mode,elapsed,caps_delta); wc=end_screen(T("bot_wins_deck"),elapsed,caps_delta); return wc,elapsed,caps_delta
                                    consecutive_discards+=1; hitboxes_dirty=True
                                    if game_mode==GM_HOT_SEAT:
                                        player_to_move=False; turn_start_ms=now
                                        hot_seat_pass_screen(b_name); player,bot=bot,player; hitboxes_dirty=True; player_to_move=True
                                    else:
                                        pending_bot=True; pending_at=now+BOT_DELAY_MS[diff]; player_to_move=False; selected=-1; turn_start_ms=now
                                else:
                                    undo_stack.pop(); msg=T("nothing_disband"); msg_until=now+1000; selected=-1
                                break
                        continue
                    if e.button==1:
                        hi=get_idx_at(mpos,ui.hand_rects)
                        if hi!=-1: selected=-1 if selected==hi else hi; continue
                        if selected<0 or selected>=len(player.hand): continue
                        c=player.hand[selected]
                        if c.is_number():
                            for ci,r in enumerate(ui.ply_slots):
                                if r.collidepoint(*mpos):
                                    if len(undo_stack)>=UNDO_LEVELS: undo_stack.pop(0)
                                    undo_stack.append(take_snapshot(player,bot))
                                    ok,emsg=play_number(player,selected,ci)
                                    selected=-1
                                    if not ok: msg=emsg; msg_until=now+1400; undo_stack.pop(); break
                                    sounds.play("play_card"); consecutive_discards=0; hitboxes_dirty=True
                                    if not draw_to_hand(player,HAND_TARGET_SIZE):
                                        elapsed=now-match_start_ms; app_stats.record("loss",elapsed); app_stats.save()
                                        caps_delta=-bet if bet>0 else 0; app_settings.caps=max(0,app_settings.caps+caps_delta); app_settings.save()
                                        add_history("loss",diff,game_mode,elapsed,caps_delta); wc=end_screen(T("bot_wins_deck"),elapsed,caps_delta); return wc,elapsed,caps_delta
                                    if game_mode==GM_HOT_SEAT:
                                        player_to_move=False; turn_start_ms=now
                                        hot_seat_pass_screen(b_name); player,bot=bot,player; hitboxes_dirty=True; player_to_move=True
                                    else:
                                        pending_bot=True; pending_at=now+BOT_DELAY_MS[diff]; player_to_move=False; turn_start_ms=now
                                    break
                            continue
                        if c.is_picture():
                            hit=None
                            for r,own,ci,ei in ui.ply_boxes+ui.bot_boxes:
                                if r.collidepoint(*mpos): hit=(own,ci,ei); break
                            if not hit: msg=T("face_needs_target"); msg_until=now+1200; selected=-1; continue
                            own,ci,ei=hit; tgt=player if own=="player" else bot
                            if len(undo_stack)>=UNDO_LEVELS: undo_stack.pop(0)
                            undo_stack.append(take_snapshot(player,bot))
                            ok,emsg=play_picture(player,bot,selected,tgt,ci,ei)
                            selected=-1
                            if not ok: msg=emsg; msg_until=now+1500; undo_stack.pop(); continue
                            pic_played=player.discard[-1] if player.discard else None
                            if pic_played:
                                if pic_played.rank=="J": sounds.play("jack")
                                elif pic_played.rank=="JKR": sounds.play("joker"); trigger_shake(10,400)
                                elif pic_played.rank=="K": sounds.play("king")
                                else: sounds.play("play_card")
                            consecutive_discards=0; hitboxes_dirty=True
                            if not draw_to_hand(player,HAND_TARGET_SIZE):
                                elapsed=now-match_start_ms; app_stats.record("loss",elapsed); app_stats.save()
                                caps_delta=-bet if bet>0 else 0; app_settings.caps=max(0,app_settings.caps+caps_delta); app_settings.save()
                                add_history("loss",diff,game_mode,elapsed,caps_delta); wc=end_screen(T("bot_wins_deck"),elapsed,caps_delta); return wc,elapsed,caps_delta
                            if game_mode==GM_HOT_SEAT:
                                player_to_move=False; turn_start_ms=now
                                hot_seat_pass_screen(b_name); player,bot=bot,player; hitboxes_dirty=True; player_to_move=True
                            else:
                                pending_bot=True; pending_at=now+BOT_DELAY_MS[diff]; player_to_move=False; turn_start_ms=now

    return "menu",0,0


# ============================================================
# TOURNAMENT MODE
# ============================================================
def run_tournament(personality_key: str):
    diffs=["easy","medium","hard"]
    results=[]
    total_caps_delta=0
    for rnd,diff in enumerate(diffs,1):
        bet=betting_menu(diff)
        if bet is None: return "menu"  # Back clicked in betting menu
        wc,elapsed,caps_delta=run_match(diff,GM_TOURNAMENT,personality_key,bet)
        total_caps_delta+=caps_delta
        if wc=="tournament_win":
            results.append((rnd,"win",diff))
        else:
            results.append((rnd,"loss",diff))
            tournament_results_screen(results)
            return "menu"
    # All 3 won
    if all(r[1]=="win" for r in results):
        unlock_achievement("TOURN_CHAMP")
    tournament_results_screen(results)
    return "menu"


# ============================================================
# NAME INPUT SCREEN
# ============================================================
def name_input_screen(current: str = "Player") -> str:
    name = list(current[:16])
    pygame.event.clear()
    while True:
        clock.tick(FPS)
        pw, ph = min(460, WIDTH-40), min(220, HEIGHT-80)
        panel = pygame.Rect(WIDTH//2-pw//2, HEIGHT//2-ph//2, pw, ph)
        screen.fill(BG)
        for gy in range(0, HEIGHT, max(4, int(6*WIDTH/_BASE_W))):
            pygame.draw.line(screen, lighten(BG, 3), (0, gy), (WIDTH, gy), 1)
        draw_panel(panel)
        title = "Enter your name:" if _LANG=="en" else "Введите имя:"
        draw_text_center(title, pygame.Rect(panel.x, panel.y+12, pw, 36), ACCENT, FONT)
        # Text box
        tb = pygame.Rect(panel.x+30, panel.y+60, pw-60, 48)
        pygame.draw.rect(screen, (20,35,22), tb, border_radius=8)
        pygame.draw.rect(screen, ACCENT, tb, 2, border_radius=8)
        disp = "".join(name) + ("_" if (pygame.time.get_ticks()//500)%2==0 else " ")
        draw_text_center(disp, tb, TEXT, FONT)
        pos = pygame.mouse.get_pos()
        ok_r = pygame.Rect(panel.x+pw//2-80, panel.y+ph-62, 160, 46)
        draw_button("OK", ok_r, pos)
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT: app_settings.save(); pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_RETURN or e.key == pygame.K_KP_ENTER:
                    return "".join(name).strip() or current
                elif e.key == pygame.K_ESCAPE:
                    return current
                elif e.key == pygame.K_BACKSPACE:
                    if name: name.pop()
                else:
                    ch = e.unicode
                    if ch and ch.isprintable() and len(name)<16:
                        name.append(ch)
            if e.type == pygame.MOUSEBUTTONDOWN and e.button==1:
                if ok_r.collidepoint(e.pos):
                    return "".join(name).strip() or current


# ============================================================
# MOJAVE CAMPAIGN
# ============================================================
CAMPAIGN_STAGES = [
    {
        "id": "powder_ganger",
        "name": "Powder Ganger",
        "location": "NCRCF Outskirts",
        "diff": "easy",
        "personality": "yes_man",
        "reward_caps": 150,
        "lore": (
            "You stumble upon a battered Powder Ganger\n"
            "playing cards outside the NCRCF. He eyes your\n"
            "caps pouch greedily. Teach him a lesson."
        ),
        "lore_ru": (
            "Вы натыкаетесь на потрёпанного Пороховика,\n"
            "играющего в карты у стен NCRCF. Он жадно\n"
            "косится на ваши крышки. Проучите его."
        ),
    },
    {
        "id": "victor",
        "name": "Victor",
        "location": "Goodsprings",
        "diff": "easy",
        "personality": "yes_man",
        "reward_caps": 200,
        "lore": (
            "Victor the Securitron rolls up cheerfully.\n"
            "'Howdy, pardner! Care for a friendly game?\n"
            "Winner gets caps — loser gets memories.'"
        ),
        "lore_ru": (
            "Виктор-секьютрон радостно подкатывает к вам.\n"
            "'Привет, приятель! Сыграем по-дружески?\n"
            "Победитель получает крышки — проигравший — воспоминания.'"
        ),
    },
    {
        "id": "benny",
        "name": "Benny",
        "location": "The Tops Casino",
        "diff": "hard",
        "personality": "benny",
        "reward_caps": 400,
        "lore": (
            "Benny leans back in his chair, platinum chip\n"
            "glinting on the table. 'You got nerve, coming here.\n"
            "Let's see if your cards are as big as your mouth.'"
        ),
        "lore_ru": (
            "Бенни откидывается на спинку кресла, платиновый\n"
            "чип блестит на столе. 'Наглость — ваша сильная\n"
            "сторона. Посмотрим, так ли хороши ваши карты.'"
        ),
    },
    {
        "id": "yes_man",
        "name": "Yes Man",
        "location": "Lucky 38",
        "diff": "medium",
        "personality": "yes_man",
        "reward_caps": 350,
        "lore": (
            "Yes Man bounces excitedly. 'Oh! You want to play\n"
            "cards? That's GREAT! I've been studying strategy\n"
            "and I think I'm pretty good now. Probably.'"
        ),
        "lore_ru": (
            "Да-человек радостно подпрыгивает. 'О! Вы хотите\n"
            "сыграть в карты? Это ОТЛИЧНО! Я изучал стратегию\n"
            "и думаю, что теперь весьма неплох. Наверное.'"
        ),
    },
    {
        "id": "house",
        "name": "Mr. House",
        "location": "Lucky 38 Penthouse",
        "diff": "impossible",
        "personality": "house",
        "reward_caps": 800,
        "lore": (
            "The screen flickers on. Mr. House's face fills\n"
            "the monitor. 'I have calculated every possible\n"
            "outcome of this game. You will not enjoy them.'"
        ),
        "lore_ru": (
            "Экран мигает. Лицо Мистера Хауса заполняет монитор.\n"
            "'Я просчитал все возможные исходы этой игры.\n"
            "Вам они не понравятся.'"
        ),
    },
]

def load_campaign_progress() -> int:
    """Returns index of next stage to play (0-5, 5 = complete)."""
    if os.path.exists(CAMPAIGN_FILE):
        try:
            with open(CAMPAIGN_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
            return int(d.get("stage", 0))
        except: pass
    return 0

def save_campaign_progress(stage: int):
    try:
        with open(CAMPAIGN_FILE, "w", encoding="utf-8") as f:
            json.dump({"stage": stage}, f)
    except: pass

def reset_campaign_progress():
    save_campaign_progress(0)

def campaign_lore_screen(stage: dict) -> bool:
    """Show lore card for stage. Returns True to continue, False to abort."""
    lore = stage["lore_ru"] if _LANG=="ru" else stage["lore"]
    location = stage["location"]
    name = stage["name"]
    pygame.event.clear()
    t_start = pygame.time.get_ticks()
    while True:
        clock.tick(FPS)
        now = pygame.time.get_ticks()
        pw, ph = min(600, WIDTH-40), min(400, HEIGHT-80)
        panel = pygame.Rect(WIDTH//2-pw//2, HEIGHT//2-ph//2, pw, ph)
        screen.fill(BG)
        for gy in range(0, HEIGHT, max(4, int(6*WIDTH/_BASE_W))):
            pygame.draw.line(screen, lighten(BG, 3), (0, gy), (WIDTH, gy), 1)
        draw_panel(panel, glow=True)
        draw_panel_title_bar(panel, f"📍 {location}", color=(100, 180, 220))
        draw_text_center(f"vs  {name}", pygame.Rect(panel.x, panel.y+8, pw, 52), ACCENT, TITLE)
        pygame.draw.line(screen, PANEL_BORD, (panel.x+20, panel.y+66), (panel.right-20, panel.y+66), 1)
        # Lore text with word wrap
        lore_lines = lore.split("\n")
        for li, ll in enumerate(lore_lines):
            draw_text_center(ll, pygame.Rect(panel.x, panel.y+82+li*32, pw, 30), TEXT, SMALL)
        # Reward
        rew = stage["reward_caps"]
        rline = f"Reward: +{rew} caps" if _LANG=="en" else f"Награда: +{rew} крышек"
        draw_text_center(rline, pygame.Rect(panel.x, panel.bottom-100, pw, 28), CAPS_CLR, FONT)
        pos = pygame.mouse.get_pos()
        bw2 = max(160, int(pw*0.36))
        play_r = pygame.Rect(panel.x+int(pw*0.1), panel.bottom-62, bw2, 50)
        back_r = pygame.Rect(panel.right-int(pw*0.1)-bw2, panel.bottom-62, bw2, 50)
        lbl_play = "Fight!" if _LANG=="en" else "В бой!"
        draw_button(lbl_play, play_r, pos, BTN, BTN_H)
        draw_button(T("back"), back_r, pos, (100,28,28), lighten((100,28,28),30), SMALL)
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT: app_settings.save(); pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE: return False
            if e.type == pygame.MOUSEBUTTONDOWN and e.button==1:
                if play_r.collidepoint(e.pos): return True
                if back_r.collidepoint(e.pos): return False

def campaign_map_screen(current_stage: int) -> Optional[int]:
    """Show the Mojave map with stage progression. Returns stage index to play, or None."""
    pygame.event.clear()
    while True:
        clock.tick(FPS)
        pw, ph = min(800, WIDTH-40), min(560, HEIGHT-40)
        panel = pygame.Rect(WIDTH//2-pw//2, max(10, HEIGHT//2-ph//2), pw, ph)
        screen.fill(BG)
        for gy in range(0, HEIGHT, max(4, int(6*WIDTH/_BASE_W))):
            pygame.draw.line(screen, lighten(BG, 3), (0, gy), (WIDTH, gy), 1)
        draw_panel(panel)
        title = "🗺 Mojave Campaign" if _LANG=="en" else "🗺 Кампания Мохаве"
        draw_panel_title_bar(panel, title, color=(100,180,220))
        draw_text_center(title, pygame.Rect(panel.x, panel.y+8, pw, 52), (100,200,255), TITLE)
        prog_txt = f"Progress: {current_stage}/{len(CAMPAIGN_STAGES)}" if _LANG=="en" \
                   else f"Прогресс: {current_stage}/{len(CAMPAIGN_STAGES)}"
        draw_text_center(prog_txt, pygame.Rect(panel.x, panel.y+58, pw, 26), TEXT_DIM, SMALL)
        pygame.draw.line(screen, PANEL_BORD, (panel.x+20, panel.y+88), (panel.right-20, panel.y+88), 1)
        pos = pygame.mouse.get_pos()
        stage_rects = []
        row_h = max(64, int(72*HEIGHT/720))
        for si, stg in enumerate(CAMPAIGN_STAGES):
            ry = panel.y + 100 + si*row_h
            done = si < current_stage
            active = si == current_stage
            locked = si > current_stage
            row_r = pygame.Rect(panel.x+14, ry, pw-28, row_h-8)
            fill = (30,55,32,120) if done else (50,75,30,160) if active else (15,22,15,80)
            rs = pygame.Surface((row_r.w, row_r.h), pygame.SRCALPHA)
            rs.fill(fill)
            screen.blit(rs, row_r.topleft)
            bord_col = OUT_OK if done else ACCENT if active else TEXT_DIM
            pygame.draw.rect(screen, bord_col, row_r, 2 if active else 1, border_radius=8)
            icon = "✓" if done else ("▶" if active else "🔒")
            draw_text(icon, row_r.x+14, ry+(row_h-8-FONT.get_height())//2, bord_col, FONT)
            draw_text(stg["name"], row_r.x+52, ry+6, bord_col, FONT)
            draw_text(f"📍 {stg['location']}", row_r.x+52, ry+6+FONT.get_height()+2, TEXT_DIM, SMALL)
            diff_col = {"easy":OUT_OK,"medium":YELLOW,"hard":(230,130,50),"impossible":RED}.get(stg["diff"],TEXT)
            draw_text(stg["diff"].upper(), row_r.right-100, ry+8, diff_col, SMALL)
            rew_txt = f"+{stg['reward_caps']}⚙"
            draw_text(rew_txt, row_r.right-100, ry+8+SMALL.get_height()+4, CAPS_CLR, TINY)
            if active and row_r.collidepoint(*pos):
                pygame.draw.rect(screen, ACCENT, row_r, 3, border_radius=8)
            stage_rects.append((row_r, si, active))
        if current_stage >= len(CAMPAIGN_STAGES):
            draw_text_center("🏆 Campaign Complete! 🏆",
                             pygame.Rect(panel.x, panel.bottom-110, pw, 36), ACCENT, FONT)
        back_r = pygame.Rect(panel.x+(pw-200)//2, panel.bottom-60, 200, 50)
        draw_button(T("back"), back_r, pos, font=SMALL)
        rst_r = pygame.Rect(panel.x+16, panel.bottom-60, 160, 50)
        draw_button("Reset" if _LANG=="en" else "Сброс", rst_r, pos,
                    (80,28,28), lighten((80,28,28),25), SMALL)
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT: app_settings.save(); pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE: return None
            if e.type == pygame.MOUSEBUTTONDOWN and e.button==1:
                if back_r.collidepoint(e.pos): return None
                if rst_r.collidepoint(e.pos):
                    reset_campaign_progress(); current_stage=0; continue
                for row_r, si, active in stage_rects:
                    if row_r.collidepoint(e.pos) and active:
                        return si

def run_campaign():
    """Full campaign flow."""
    while True:
        progress = load_campaign_progress()
        idx = campaign_map_screen(progress)
        if idx is None: return
        stg = CAMPAIGN_STAGES[idx]
        go = campaign_lore_screen(stg)
        if not go: continue
        # Run the match
        wc, elapsed, caps_delta = run_match(
            stg["diff"], GM_NORMAL, stg["personality"], bet=0
        )
        if wc in ("menu", "quit_match"): return
        if wc == "restart":
            # Treat restart as replaying same stage
            continue
        # wc == "tournament_win"/"tournament_loss" shouldn't happen, but treat as win/loss
        # Determine result from end_screen choice — we need to track it differently
        # In GM_NORMAL, run_match returns end_screen result: "restart"|"menu"
        # We detect win by checking if caps increased (caps_delta > 0 means win)
        # Actually we can check: run_match for campaign always gives back "restart"/"menu"
        # Let's re-check: in run_match, non-tournament: result from end_screen("restart"/"menu")
        # So we can't directly tell win/loss from wc. 
        # Workaround: track via caps change. But bet=0 so caps_delta=0 always.
        # Better fix: pass a callback. For now, use stats: if last recorded result == "win"
        # We'll check app_stats.wins changed by comparing before/after
        # Actually simplest: always advance after any non-quit exit (restart or menu)
        # A quit_match was already handled above. "restart"/"menu" both mean match finished.
        # We can check history for last entry's result:
        hist = load_history()
        last_result = hist[-1].result if hist else "loss"
        if last_result == "win":
            new_progress = progress + 1
            save_campaign_progress(new_progress)
            # Reward caps
            app_settings.caps += stg["reward_caps"]
            app_settings.save()
            # Show reward screen
            _campaign_reward_screen(stg, new_progress)
            if new_progress >= len(CAMPAIGN_STAGES):
                unlock_achievement("TOURN_CHAMP")
        # Loop back to map

def _campaign_reward_screen(stg: dict, new_progress: int):
    pygame.event.clear()
    t0 = pygame.time.get_ticks()
    particles.confetti(60)
    while True:
        clock.tick(FPS)
        now = pygame.time.get_ticks()
        pw, ph = min(500, WIDTH-40), min(300, HEIGHT-80)
        panel = pygame.Rect(WIDTH//2-pw//2, HEIGHT//2-ph//2, pw, ph)
        screen.fill(BG)
        for gy in range(0, HEIGHT, max(4, int(6*WIDTH/_BASE_W))):
            pygame.draw.line(screen, lighten(BG, 3), (0, gy), (WIDTH, gy), 1)
        particles.tick_draw(screen)
        draw_panel(panel, glow=True)
        if new_progress >= len(CAMPAIGN_STAGES):
            hdr = "🏆 CAMPAIGN COMPLETE!" if _LANG=="en" else "🏆 КАМПАНИЯ ЗАВЕРШЕНА!"
        else:
            hdr = "✓ Stage Clear!" if _LANG=="en" else "✓ Этап пройден!"
        draw_text_center(hdr, pygame.Rect(panel.x, panel.y+16, pw, 52), ACCENT, TITLE)
        draw_text_center(f"+{stg['reward_caps']} caps!",
                         pygame.Rect(panel.x, panel.y+80, pw, 40), CAPS_CLR, FONT)
        if new_progress < len(CAMPAIGN_STAGES):
            nxt = CAMPAIGN_STAGES[new_progress]["name"]
            nxt_txt = f"Next: {nxt}" if _LANG=="en" else f"Следующий: {nxt}"
            draw_text_center(nxt_txt, pygame.Rect(panel.x, panel.y+128, pw, 30), TEXT_DIM, SMALL)
        pos = pygame.mouse.get_pos()
        ok_r = pygame.Rect(panel.x+(pw-200)//2, panel.bottom-62, 200, 50)
        draw_button("Continue" if _LANG=="en" else "Продолжить", ok_r, pos)
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT: app_settings.save(); pygame.quit(); sys.exit()
            if e.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                if e.type == pygame.MOUSEBUTTONDOWN and not ok_r.collidepoint(e.pos):
                    continue
                particles.clear(); return


# ============================================================
# AI vs AI SPECTATOR MODE
# ============================================================
def run_spectator():
    """Watch two bots play each other. ESC or clicking Stop returns to menu."""
    # Choose difficulty + personalities
    spec_config = _spectator_config_screen()
    if spec_config is None: return
    diff_a, diff_b, pers_a, pers_b, speed = spec_config

    sel_keys = load_deck_selection()
    if sel_keys: sel_keys = ensure_min30_selection(sel_keys)
    bot_a = PlayerState("Bot A", [Caravan() for _ in range(3)],
                        build_deck_from_selection(sel_keys), [], [])
    bot_b = PlayerState("Bot B", [Caravan() for _ in range(3)],
                        build_deck_from_selection(sel_keys), [], [])
    draw_to_hand(bot_a, HAND_OPENING_SIZE)
    draw_to_hand(bot_b, HAND_OPENING_SIZE)

    phase = "OPENING"
    opening_halfturn = 0
    start_ms = pygame.time.get_ticks()
    turn_ms = start_ms
    delay_ms = {1: 1200, 2: 700, 3: 350, 4: 150, 5: 50}[speed]
    a_to_move = True
    msg = ""; msg_until = 0
    consecutive_discards = 0
    hitboxes_dirty = True
    cached_hit = None
    game_over = False
    result_txt = ""

    while True:
        clock.tick(FPS)
        now = pygame.time.get_ticks()

        if hitboxes_dirty:
            _, ba_, pa_, _ = ui_rects()
            cached_hit = {
                "bot":    build_entry_hitboxes("bot",    caravan_slots(ba_), bot_b.caravans),
                "player": build_entry_hitboxes("player", caravan_slots(pa_), bot_a.caravans),
            }
            hitboxes_dirty = False

        # Draw using draw_board with bot_a as "player" and bot_b as "bot"
        ui = draw_board(
            player=bot_a, bot=bot_b,
            selected_idx=-1, msg=msg, msg_until=msg_until,
            start_ms=start_ms, phase=phase, bot_diff=diff_a,
            hand_scroll=0, pending_bot=(not a_to_move),
            undo_count=0, consecutive_discards=consecutive_discards,
            cached_hitboxes=cached_hit, game_mode=GM_NORMAL,
            turn_start_ms=turn_ms, personality_key=pers_a,
            p2_label="Bot B",
        )

        # Speed overlay
        _draw_spectator_overlay(speed, result_txt if game_over else "", now, start_ms)
        pygame.display.flip()

        # Events
        for e in pygame.event.get():
            if e.type == pygame.QUIT: app_settings.save(); pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE: return
            if e.type == pygame.MOUSEBUTTONDOWN and e.button==1:
                # Speed buttons drawn in overlay
                new_spd = _check_speed_click(e.pos, speed)
                if new_spd is not None:
                    speed = new_spd
                    delay_ms = {1:1200,2:700,3:350,4:150,5:50}[speed]
                    continue
                # Stop button
                stop_r = pygame.Rect(WIDTH-130, 10, 120, 40)
                if stop_r.collidepoint(e.pos): return

        if game_over:
            if now - start_ms > 3000:
                pygame.time.wait(1000)
                return
            continue

        if now - turn_ms < delay_ms:
            continue

        # Bot move
        mover   = bot_a if a_to_move else bot_b
        opponent= bot_b if a_to_move else bot_a
        diff    = diff_a if a_to_move else diff_b
        pk      = pers_a if a_to_move else pers_b

        if phase == "OPENING":
            bot_opening_play(mover)
            opening_halfturn += 1
            hitboxes_dirty = True
            if opening_halfturn >= 6:
                phase = "MAIN"
                bot_a.hand = bot_a.hand[:HAND_TARGET_SIZE]
                bot_b.hand = bot_b.hand[:HAND_TARGET_SIZE]
                draw_to_hand(bot_a, HAND_TARGET_SIZE)
                draw_to_hand(bot_b, HAND_TARGET_SIZE)
        else:
            ok2, rmsg, was_play = bot_take_turn(mover, opponent, diff, pk)
            consecutive_discards = (0 if was_play else consecutive_discards+1)
            if rmsg: msg=rmsg; msg_until=now+1200
            if not ok2:
                result_txt = f"{'Bot A' if a_to_move else 'Bot B'} deck empty!"
                game_over = True
            else:
                ended, win, wtxt = check_game_end(bot_a, bot_b)
                if ended or consecutive_discards >= STALEMATE_THRESHOLD:
                    result_txt = wtxt if ended else "Draw — stalemate!"
                    if ended: sounds.play("win")
                    game_over = True
                    if ended: particles.confetti(50)
            hitboxes_dirty = True

        a_to_move = not a_to_move
        turn_ms = now

_spec_speed_rects: list = []

def _draw_spectator_overlay(speed: int, result_txt: str, now: int, start_ms: int):
    global _spec_speed_rects
    # Stop button
    stop_r = pygame.Rect(WIDTH-130, 10, 120, 40)
    pos = pygame.mouse.get_pos()
    draw_button("■ Stop" if _LANG=="en" else "■ Стоп",
                stop_r, pos, (100,28,28), lighten((100,28,28),30), SMALL)
    # Speed bar
    speeds = ["1x","2x","3x","4x","5x"]
    bw3 = 44; bh3 = 30; sx0 = WIDTH-130-len(speeds)*(bw3+6)-8
    _spec_speed_rects.clear()
    for si, sl in enumerate(speeds):
        sr = pygame.Rect(sx0+si*(bw3+6), 14, bw3, bh3)
        _spec_speed_rects.append(sr)
        is_sel = (si+1 == speed)
        draw_button(sl, sr, pos, RES_ACTIVE if is_sel else BTN,
                    RES_ACT_H if is_sel else BTN_H, TINY)
    # "AI vs AI" badge
    badge = "👁 AI vs AI Spectator" if _LANG=="en" else "👁 Бот vs Бот"
    draw_text(badge, 8, 8, (140,140,200), SMALL)
    # Elapsed
    draw_text(format_time_ms(now-start_ms), 8, 8+SMALL.get_height()+4, TEXT_DIM, TINY)
    # Result
    if result_txt:
        rr = pygame.Rect(WIDTH//2-200, HEIGHT//2-30, 400, 60)
        rs2 = pygame.Surface((400,60), pygame.SRCALPHA); rs2.fill((12,20,14,220))
        pygame.draw.rect(rs2, ACCENT, pygame.Rect(0,0,400,60), 3, border_radius=14)
        screen.blit(rs2, rr.topleft)
        draw_text_center(result_txt, rr, ACCENT, FONT)

def _check_speed_click(pos: tuple, current_speed: int) -> Optional[int]:
    for si, sr in enumerate(_spec_speed_rects):
        if sr.collidepoint(pos): return si+1
    return None

def _spectator_config_screen() -> Optional[tuple]:
    """Returns (diff_a, diff_b, pers_a, pers_b, speed) or None."""
    diff_a = "medium"; diff_b = "medium"
    pers_a = "benny";  pers_b = "house"
    speed  = 2
    diffs  = ["easy","medium","hard","impossible"]
    perss  = list(PERSONALITIES.keys())
    pygame.event.clear()
    while True:
        clock.tick(FPS)
        pw, ph = min(640, WIDTH-40), min(480, HEIGHT-80)
        panel = pygame.Rect(WIDTH//2-pw//2, HEIGHT//2-ph//2, pw, ph)
        screen.fill(BG)
        for gy in range(0, HEIGHT, max(4, int(6*WIDTH/_BASE_W))):
            pygame.draw.line(screen, lighten(BG, 3), (0, gy), (WIDTH, gy), 1)
        draw_panel(panel)
        hdr = "👁 Spectator Setup" if _LANG=="en" else "👁 Настройка наблюдения"
        draw_panel_title_bar(panel, hdr, color=(140,120,220))
        draw_text_center(hdr, pygame.Rect(panel.x, panel.y+8, pw, 52), (180,160,255), TITLE)
        pos = pygame.mouse.get_pos()
        col_w = pw//2-20
        # Bot A column
        draw_text("Bot A", panel.x+30, panel.y+72, (100,200,255), FONT)
        da_rects = []
        for di, d in enumerate(diffs):
            r = pygame.Rect(panel.x+20, panel.y+104+di*46, col_w-10, 40)
            da_rects.append(r)
            is_sel = (d == diff_a)
            dc = {"easy":OUT_OK,"medium":YELLOW,"hard":(230,130,50),"impossible":RED}.get(d,TEXT)
            draw_button(d.upper(), r, pos, (30,50,30) if is_sel else BTN,
                        lighten((30,50,30),40) if is_sel else BTN_H, SMALL)
            if is_sel: pygame.draw.rect(screen, dc, r, 3, border_radius=10)
        pa_rects = []
        for pi, pk in enumerate(perss):
            r = pygame.Rect(panel.x+20, panel.y+104+len(diffs)*46+10+pi*46, col_w-10, 40)
            pa_rects.append(r)
            is_sel = (pk == pers_a)
            draw_button(T(PERSONALITIES[pk].display_key), r, pos,
                        (30,50,60) if is_sel else BTN,
                        lighten((30,50,60),40) if is_sel else BTN_H, SMALL)
            if is_sel: pygame.draw.rect(screen, (100,200,255), r, 2, border_radius=10)
        # Bot B column
        draw_text("Bot B", panel.x+pw//2+10, panel.y+72, (255,180,100), FONT)
        db_rects = []
        for di, d in enumerate(diffs):
            r = pygame.Rect(panel.x+pw//2+10, panel.y+104+di*46, col_w-10, 40)
            db_rects.append(r)
            is_sel = (d == diff_b)
            dc = {"easy":OUT_OK,"medium":YELLOW,"hard":(230,130,50),"impossible":RED}.get(d,TEXT)
            draw_button(d.upper(), r, pos, (50,30,20) if is_sel else BTN,
                        lighten((50,30,20),40) if is_sel else BTN_H, SMALL)
            if is_sel: pygame.draw.rect(screen, dc, r, 3, border_radius=10)
        pb_rects = []
        for pi, pk in enumerate(perss):
            r = pygame.Rect(panel.x+pw//2+10, panel.y+104+len(diffs)*46+10+pi*46, col_w-10, 40)
            pb_rects.append(r)
            is_sel = (pk == pers_b)
            draw_button(T(PERSONALITIES[pk].display_key), r, pos,
                        (60,40,20) if is_sel else BTN,
                        lighten((60,40,20),40) if is_sel else BTN_H, SMALL)
            if is_sel: pygame.draw.rect(screen, (255,180,100), r, 2, border_radius=10)
        # Speed row
        spd_y = panel.bottom-80
        draw_text("Speed:" if _LANG=="en" else "Скорость:", panel.x+20, spd_y, TEXT_DIM, SMALL)
        spd_rects = []
        for si in range(1,6):
            sr = pygame.Rect(panel.x+110+(si-1)*52, spd_y-4, 46, 34)
            spd_rects.append(sr)
            is_sel = (si == speed)
            draw_button(f"{si}x", sr, pos, RES_ACTIVE if is_sel else BTN,
                        RES_ACT_H if is_sel else BTN_H, SMALL)
        # Buttons
        start_r = pygame.Rect(panel.x+(pw-200)//2, panel.bottom-38, 200, 32)
        draw_button("▶ Watch!" if _LANG=="en" else "▶ Смотреть!", start_r, pos, BTN, BTN_H, SMALL)
        back_r2 = pygame.Rect(panel.x+10, panel.bottom-38, 120, 32)
        draw_button(T("back"), back_r2, pos, (80,28,28), lighten((80,28,28),25), SMALL)
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT: app_settings.save(); pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE: return None
            if e.type == pygame.MOUSEBUTTONDOWN and e.button==1:
                if back_r2.collidepoint(e.pos): return None
                if start_r.collidepoint(e.pos):
                    return (diff_a, diff_b, pers_a, pers_b, speed)
                for di, r in enumerate(da_rects):
                    if r.collidepoint(e.pos): diff_a = diffs[di]; break
                for di, r in enumerate(db_rects):
                    if r.collidepoint(e.pos): diff_b = diffs[di]; break
                for pi, r in enumerate(pa_rects):
                    if r.collidepoint(e.pos): pers_a = perss[pi]; break
                for pi, r in enumerate(pb_rects):
                    if r.collidepoint(e.pos): pers_b = perss[pi]; break
                for si, sr in enumerate(spd_rects):
                    if sr.collidepoint(e.pos): speed = si+1; break


# ============================================================
# TOP-LEVEL GAME LOOP
# ============================================================
while True:
    choice=main_menu()
    if choice!="play": continue

    game_mode=mode_select_menu()
    if game_mode is None: continue

    if game_mode=="campaign":
        run_campaign()
        continue

    if game_mode=="spectator":
        run_spectator()
        continue
    if game_mode == GM_NETWORK:
        nm = network_lobby_screen()
        if nm is None: continue
        run_network_match(nm)
        continue

    if game_mode==GM_TOURNAMENT:
        diff=difficulty_menu()
        if diff is None: continue
        personality_key=personality_select_menu()
        if personality_key is None: continue    # Back clicked in personality menu
        bet=betting_menu(diff)
        if bet is None: continue                # Back clicked in betting menu
    else:
        diff="medium"; personality_key=DEFAULT_PERSONALITY; bet=0

    while True:
        wc,elapsed,caps_delta=run_match(diff,game_mode,personality_key,bet)
        if wc in ("menu","quit_match"): break
        # "restart" → loop again with same settings
        bet=betting_menu(diff) if game_mode!=GM_HOT_SEAT else 0