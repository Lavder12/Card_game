import os
import sys
import json
import pygame
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any
import src.state as state
from src.security import secure_save, secure_load

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
TIMED_TURN_MS       = 30_000

BOT_DELAY_MS: Dict[str, int] = {
    "easy": 900, "medium": 800, "hard": 700, "impossible": 600,
}

MAX_ART_CACHE_ENTRIES = 512

_BASE_CARD_W = 76
_BASE_CARD_H = 110

# Colors (Desert Night Palette)
BG          = (17,  14,  12)     # #110E0C Deep coffee/charcoal
PANEL       = (42,  34,  29)     # #2A221D Warm dark gray-brown
PANEL_2     = (34,  26,  22)
PANEL_BORD  = (140, 92,  61)     # #8C5C3D Copper / rust
PANEL_GLOW  = (217, 155, 66)     # #D99B42 Amber glow
CARD_FACE   = (244, 238, 218)
CARD_BACK_C = (42,  34,  29)
CARD_SEL    = (217, 155, 66)
CARD_HOVER  = (242, 192, 87)
CARD_RED    = (190, 45,  40)
CARD_BLACK  = (26,  22,  20)
CARD_JOKER  = (130, 60,  160)
TEXT        = (232, 220, 200)    # #E8DCC8 Sand
TEXT_DIM    = (184, 164, 139)    # #B8A48B Dusty tan
BTN         = (94,  60,  40)     # #5E3C28 Mahogany
BTN_H       = (140, 92,  61)     # #8C5C3D Rust
BTN_TXT     = (240, 230, 210)
ACCENT      = (242, 192, 87)     # #F2C057 Vibrant gold
RED         = (200, 60,  60)
YELLOW      = (220, 180, 60)
BLACK       = (0,   0,   0)
OUT_OK      = (120, 190, 100)
OUT_BAD     = (200, 70,  70)
TOOLTIP_BG  = (26,  21,  18)
UNDO_CLR    = (110, 150, 200)
RES_ACTIVE  = (100, 140, 200)
RES_ACT_H   = (130, 175, 230)
CAPS_CLR    = (230, 185, 65)
TIMER_OK    = (100, 190, 100)
TIMER_WARN  = (220, 170, 50)
TIMER_CRIT  = (230, 70,  70)
ACH_BG      = (34,  26,  22)
ACH_BORD    = (140, 92,  61)

SUIT_SYMBOL: Dict[str, str]   = {"S":"♠","H":"♥","D":"♦","C":"♣"}
SUIT_COLOR:  Dict[str, Tuple] = {"S":CARD_BLACK,"C":CARD_BLACK,"H":CARD_RED,"D":CARD_RED}

# Paths
if getattr(sys, "frozen", False):
    BASE_DIR = sys._MEIPASS
    EXE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    EXE_DIR = BASE_DIR

def rpath(*p): return os.path.join(BASE_DIR, *p)
def wpath(*p):
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata: d = os.path.join(appdata, "Dustway")
        else: d = os.path.join(EXE_DIR, "data")
    else:
        d = os.path.join(os.path.expanduser("~"), ".config", "Dustway")
        
    os.makedirs(d, exist_ok=True)
    
    # Migrate old data if present
    old_d = os.path.join(EXE_DIR, "data")
    if old_d != d and os.path.exists(old_d):
        old_file = os.path.join(old_d, *p)
        new_file = os.path.join(d, *p)
        if os.path.exists(old_file) and not os.path.exists(new_file):
            try:
                import shutil
                shutil.copy2(old_file, new_file)
            except: pass

    return os.path.join(d, *p)

SETTINGS_FILE = wpath("settings.json")
DECK_FILE     = wpath("deck.json")
STATS_FILE    = wpath("stats.json")
HISTORY_FILE  = wpath("history.json")
ACH_FILE      = wpath("achievements.json")
CAMPAIGN_FILE = wpath("campaign.json")
MUSIC_PATH    = rpath("music", "music.mp3")
CARDS_DIR     = rpath("assets", "cards")
BACKGROUND_DIR = rpath("assets", "background")
MENU_BG_PATH   = rpath("assets", "background", "main_menu.png")
TABLE_BG_PATH  = rpath("assets", "background", "game_table.png")
HISTORY_MAP_PATH = rpath("assets", "background", "history_map.jpeg")
MENU_TILE_DIR  = rpath("assets", "menu_tiles")
AVATARS_DIR    = rpath("assets", "avatars")
PROFILE_BG_DIR = rpath("assets", "profile_backgrounds")

DEFAULT_AVATARS     = ["trader", "scavenger", "guard", "nomad", "wanderer"]
DEFAULT_PROFILE_BGS = ["tent", "caravan", "shack", "bunker"]

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
FIREBASE_URL = "https://dustway-default-rtdb.europe-west1.firebasedatabase.app"

GM_NORMAL      = "normal"
GM_HOT_SEAT    = "hot_seat"
GM_TIMED       = "timed"
GM_TOURNAMENT  = "tournament"
GM_NETWORK     = "network"
NET_PORT       = 27015

# ============================================================
# LOCALISATION
# ============================================================
STRINGS: Dict[str, Dict[str, str]] = {
"en": {
    "title":"Dustway","subtitle":"(Desert Trader)",
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
    "streak_line":"Best streak:   {}","caps_line":"Coins:         {}",
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
    "bot_benny":"Silas","bot_yesman":"Rusty","bot_house":"The Baron",
    "betting_title":"Place Your Bet","caps_balance":"Your coins: {}",
    "bet_amount":"Bet: {} coins","bet_confirm":"Confirm Bet",
    "phase_lbl":"Phase: {}","diff_lbl":"Diff: {}","time_lbl":"Time: {}",
    "sound_lbl":"Sound: {}%","sound_off_lbl":"Sound: OFF",
    "stats_bar":"W:{} L:{} D:{}","bot_thinking":"Bot thinking",
    "player_deck_lbl":"Deck: {}  Discard: {}","bot_deck_lbl":"Bot: {}  Discard: {}",
    "undo_hint":"[U] Undo ({})","stalemate_warn":"⚠ Stalemate {}/{}",
    "hint_opening":"Opening: place A-10 on 3 empty routes",
    "hint_main":"LMB: play  |  RMB: discard/disband  |  1/2/3: route  |  D: discard  |  U: undo  |  ESC: pause",
    "bot_caravans":"Bot routes","your_caravans":"Your routes",
    "your_hand":"Your hand","score_fmt":"Score: {}","score_sold":"Score: {} ★",
    "p1_caravans":"P1 routes","p2_caravans":"P2 routes","p1_hand":"P1 hand","p2_hand":"P2 hand",
    "player_wins":"Player wins!","bot_wins":"Bot wins!",
    "draw_stalemate":"Draw — stalemate!",
    "player_wins_deck":"Player wins! (bot deck empty)",
    "bot_wins_deck":"Bot wins! (your deck empty)",
    "p1_wins":"Player 1 wins!","p2_wins":"Player 2 wins!",
    "match_time":"Match time: {}","stats_end":"W:{}  L:{}  D:{}  avg: {}",
    "play_again":"New Match","main_menu_btn":"Main Menu",
    "opening_nums_only":"Opening: numbers only (A-10)",
    "caravan_started":"Route already started",
    "nothing_disband":"Nothing to disband",
    "face_needs_target":"Face card needs a target number card",
    "undone":"Undone!","bot_deck_empty_win":"Bot deck empty — player wins!",
    "base_value":"Base value: {}","attached":"Attached: {}","effective":"Effective: {}  (×{})",
    "timer_lbl":"Turn: {}s","timer_expired":"Time's up — auto discard!",
    "pass_screen_title":"Pass to {}","pass_screen_hint":"Click or press SPACE to continue",
    "tourn_title":"Tournament","tourn_round":"Round {}","tourn_win":"WIN","tourn_loss":"LOSS",
    "tourn_champion":"Tournament Champion!","tourn_eliminated":"Eliminated in round {}",
    "caps_won":"+{} coins!","caps_lost":"-{} coins","no_caps":"Not enough coins to bet!",
    "ach_title":"Achievements",
    "FIRST_WIN":"First Win","STREAK_3":"Hot Streak","STREAK_5":"On Fire",
    "STREAK_10":"Unstoppable","FAST_WIN":"Speed Dealer","SPEED_DEMON":"Speed Demon",
    "PERFECT_26":"Perfect Score","JOKER_BOMB":"Nuclear Option",
    "JACK_ATTACK":"Jack the Ripper","IMPOSSIBLE_WIN":"Against All Odds",
    "TOURN_CHAMP":"Tournament Champion","CAPS_RICH":"Coin Collector",
    "COMEBACK":"Against All Odds II","HOT_SEAT_WIN":"Face to Face",
    "ALL_CARAVANS":"Trifecta",
    "FIRST_WIN_d":"Win your first match",
    "STREAK_3_d":"Win 3 matches in a row",
    "STREAK_5_d":"Win 5 matches in a row",
    "STREAK_10_d":"Win 10 matches in a row",
    "FAST_WIN_d":"Win in under 3 minutes",
    "SPEED_DEMON_d":"Win in under 2 minutes",
    "PERFECT_26_d":"Close a route at exactly 26",
    "JOKER_BOMB_d":"Clear 3+ cards with one Joker",
    "JACK_ATTACK_d":"Remove a card worth 10 with a Jack",
    "IMPOSSIBLE_WIN_d":"Beat Impossible difficulty",
    "TOURN_CHAMP_d":"Win a full tournament",
    "CAPS_RICH_d":"Accumulate 5 000 coins",
    "COMEBACK_d":"Win after your first route is beaten",
    "HOT_SEAT_WIN_d":"Win a hot-seat match",
    "ALL_CARAVANS_d":"Win all 3 routes simultaneously",
    "menu_vs_bot":"vs Bot","menu_vs_player":"vs Player","menu_tutorial":"Tutorial","menu_campaign":"Story",
    "menu_vs_bot_desc":"Play against AI opponent","menu_vs_player_desc":"Play over LAN / Hamachi",
    "menu_tutorial_desc":"Learn the game step by step","menu_campaign_desc":"Dusty Tract campaign",
    "tutorial_title":"Tutorial","tutorial_level":"Level {}","tutorial_completed":"Completed!",
    "tutorial_goal":"Goal: {}","tutorial_hint":"Hint: {}","tutorial_next":"Next Level",
    "tutorial_retry":"Retry","tutorial_back_to_list":"Back to Levels",
    "tutorial_progress":"Progress: {}/{}","tutorial_locked":"Locked",
    "tut1_t":"Meet the Cards","tut1_d":"Learn about the deck: suits, ranks, and card types.",
    "tut2_t":"Starting a Route","tut2_d":"Place your first number card on an empty route.",
    "tut3_t":"Direction Matters","tut3_d":"Cards must follow ascending or descending order.",
    "tut4_t":"Suit Rules","tut4_d":"Play a card of a different suit to break direction.",
    "tut5_t":"The Goal: 21-26","tut5_d":"A route is \"sold\" when its score is between 21 and 26.",
    "tut6_t":"Winning the Round","tut6_d":"Win 2 out of 3 routes to win the match.",
    "tut7_t":"The Jack (J)","tut7_d":"Use a Jack to remove an opponent's card.",
    "tut8_t":"The Queen (Q)","tut8_d":"A Queen reverses the route direction and changes its suit.",
    "tut9_t":"The King (K)","tut9_d":"A King doubles the value of the card it's attached to.",
    "tut10_t":"The Joker","tut10_d":"A Joker removes all cards of the same rank from the board.",
    "tut11_t":"Discarding","tut11_d":"Sometimes discarding a bad card is the best move.",
    "tut12_t":"Disbanding","tut12_d":"Disband your own route to start fresh.",
    "tut13_t":"Combo Attacks","tut13_d":"Chain face cards for devastating combos.",
    "tut14_t":"Defense Strategy","tut14_d":"Protect your routes from Jacks and Jokers.",
    "tut15_t":"Final Exam","tut15_d":"Play a full match against an easy bot with hints.",
},
"ru": {
    "title":"Дастуэй","subtitle":"(Торговый путь)",
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
    "streak_line":"Лучшая серия: {}","caps_line":"Монеты:       {}",
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
    "bot_benny":"Силас","bot_yesman":"Расти","bot_house":"Барон",
    "betting_title":"Ставка","caps_balance":"Ваши монеты: {}",
    "bet_amount":"Ставка: {} монет","bet_confirm":"Подтвердить",
    "phase_lbl":"Фаза: {}","diff_lbl":"Сложн.: {}","time_lbl":"Время: {}",
    "sound_lbl":"Звук: {}%","sound_off_lbl":"Звук: ВЫКЛ",
    "stats_bar":"П:{} П:{} Н:{}","bot_thinking":"Бот думает",
    "player_deck_lbl":"Колода: {}  Сброс: {}","bot_deck_lbl":"Бот: {}  Сброс: {}",
    "undo_hint":"[U] Отмена ({})","stalemate_warn":"⚠ Пат {}/{}",
    "hint_opening":"Начало: выложите A-10 на 3 пустых маршрута",
    "hint_main":"ЛКМ: ход  |  ПКМ: сброс  |  1/2/3: маршрут  |  D: сброс  |  U: отмена  |  ESC: пауза",
    "bot_caravans":"Маршруты бота","your_caravans":"Ваши маршруты",
    "your_hand":"Ваша рука","score_fmt":"Счёт: {}","score_sold":"Счёт: {} ★",
    "p1_caravans":"Маршруты игр. 1","p2_caravans":"Маршруты игр. 2",
    "p1_hand":"Рука игрока 1","p2_hand":"Рука игрока 2",
    "player_wins":"Игрок победил!","bot_wins":"Бот победил!",
    "draw_stalemate":"Ничья — пат!",
    "player_wins_deck":"Игрок победил! (колода бота пуста)",
    "bot_wins_deck":"Бот победил! (ваша колода пуста)",
    "p1_wins":"Игрок 1 победил!","p2_wins":"Игрок 2 победил!",
    "match_time":"Время матча: {}","stats_end":"П:{}  П:{}  Н:{}  ср: {}",
    "play_again":"Новый бой","main_menu_btn":"Главное меню",
    "opening_nums_only":"Начало: только числа (A-10)",
    "caravan_started":"Маршрут уже начат",
    "nothing_disband":"Нечего распускать",
    "face_needs_target":"Фигура должна бить числовую карту",
    "undone":"Отменено!","bot_deck_empty_win":"Колода бота пуста — победа!",
    "base_value":"Базовое: {}","attached":"Прикреплено: {}","effective":"Итого: {}  (×{})",
    "timer_lbl":"Ход: {}с","timer_expired":"Время вышло — авто-сброс!",
    "pass_screen_title":"Ход передаётся {}","pass_screen_hint":"Нажмите пробел или щёлкните",
    "tourn_title":"Турнир","tourn_round":"Раунд {}","tourn_win":"ПОБЕДА","tourn_loss":"ПОРАЖЕНИЕ",
    "tourn_champion":"Чемпион турнира!","tourn_eliminated":"Выбыл в раунде {}",
    "caps_won":"+{} монет!","caps_lost":"-{} монет","no_caps":"Недостаточно монет!",
    "ach_title":"Достижения",
    "FIRST_WIN":"Первая победа","STREAK_3":"Горячая серия","STREAK_5":"В огне",
    "STREAK_10":"Неудержимый","FAST_WIN":"Быстрый дилер","SPEED_DEMON":"Демон скорости",
    "PERFECT_26":"Идеальный счёт","JOKER_BOMB":"Ядерный вариант",
    "JACK_ATTACK":"Валет-потрошитель","IMPOSSIBLE_WIN":"Вопреки всему",
    "TOURN_CHAMP":"Чемпион турнира","CAPS_RICH":"Коллекционер монет",
    "COMEBACK":"Камбэк","HOT_SEAT_WIN":"Лицом к лицу","ALL_CARAVANS":"Три пути",
    "FIRST_WIN_d":"Одержите первую победу",
    "STREAK_3_d":"Победите 3 раза подряд",
    "STREAK_5_d":"Победите 5 раз подряд",
    "STREAK_10_d":"Победите 10 раз подряд",
    "FAST_WIN_d":"Победите менее чем за 3 минуты",
    "SPEED_DEMON_d":"Победите менее чем за 2 минуты",
    "PERFECT_26_d":"Закройте маршрут с точно 26 очками",
    "JOKER_BOMB_d":"Уберите 3+ карты одним Джокером",
    "JACK_ATTACK_d":"Уберите карту стоимостью 10 Валетом",
    "IMPOSSIBLE_WIN_d":"Победите на невозможной сложности",
    "TOURN_CHAMP_d":"Выиграйте полный турнир",
    "CAPS_RICH_d":"Накопите 5 000 монет",
    "COMEBACK_d":"Победите, проиграв первый маршрут",
    "HOT_SEAT_WIN_d":"Победите в режиме вдвоём",
    "ALL_CARAVANS_d":"Выиграйте все 3 маршрута одновременно",
    "menu_vs_bot":"Против Бота","menu_vs_player":"Против Игрока","menu_tutorial":"Обучение","menu_campaign":"Сюжет",
    "menu_vs_bot_desc":"Играть против ИИ","menu_vs_player_desc":"Игра по сети LAN / Hamachi",
    "menu_tutorial_desc":"Изучите игру шаг за шагом","menu_campaign_desc":"Кампания Пыльный тракт",
    "tutorial_title":"Обучение","tutorial_level":"Уровень {}","tutorial_completed":"Пройдено!",
    "tutorial_goal":"Цель: {}","tutorial_hint":"Подсказка: {}","tutorial_next":"Следующий уровень",
    "tutorial_retry":"Повторить","tutorial_back_to_list":"К списку уровней",
    "tutorial_progress":"Прогресс: {}/{}","tutorial_locked":"Закрыто",
    "tut1_t":"Знакомство с картами","tut1_d":"Узнайте о колоде: масти, номиналы и типы карт.",
    "tut2_t":"Начало маршрута","tut2_d":"Разместите первую числовую карту на пустой маршрут.",
    "tut3_t":"Направление","tut3_d":"Карты должны идти по возрастанию или убыванию.",
    "tut4_t":"Правила мастей","tut4_d":"Сыграйте карту другой масти, чтобы сменить направление.",
    "tut5_t":"Цель: 21-26","tut5_d":"Маршрут \"продан\", когда его счёт от 21 до 26.",
    "tut6_t":"Победа в раунде","tut6_d":"Выиграйте 2 из 3 маршрутов для победы.",
    "tut7_t":"Валет (J)","tut7_d":"Используйте Валета, чтобы убрать карту противника.",
    "tut8_t":"Дама (Q)","tut8_d":"Дама меняет направление маршрута и его масть.",
    "tut9_t":"Король (K)","tut9_d":"Король удваивает значение карты, к которой прикреплён.",
    "tut10_t":"Джокер","tut10_d":"Джокер удаляет все карты того же номинала с поля.",
    "tut11_t":"Сброс карты","tut11_d":"Иногда лучший ход — сбросить плохую карту.",
    "tut12_t":"Расформирование","tut12_d":"Распустите свой маршрут, чтобы начать заново.",
    "tut13_t":"Комбо-атака","tut13_d":"Комбинируйте фигуры для мощных комбо.",
    "tut14_t":"Стратегия защиты","tut14_d":"Защитите маршруты от Валетов и Джокеров.",
    "tut15_t":"Финальный экзамен","tut15_d":"Полная партия против слабого бота с подсказками.",
},
}

def T(key: str, *args) -> str:
    s = STRINGS.get(state.language, STRINGS["en"]).get(key, STRINGS["en"].get(key, key))
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
    player_icon:          str   = "trader"  # avatar filename (without .png)
    profile_bg:           str   = "tent"    # profile background (without .png)
    table_theme:          int   = 0       # 0-3
    unlocked_backs:       List[int] = field(default_factory=lambda: [0])
    unlocked_themes:      List[int] = field(default_factory=lambda: [0])
    friend_code:          str   = ""
    friends:              List[str] = field(default_factory=list)

    def apply_audio(self):
        if state.AUDIO_OK:
            pygame.mixer.music.set_volume(0.0 if self.muted else self.volume)

    def apply_language(self):
        state.language = self.language

    def save(self):
        secure_save(SETTINGS_FILE, self.__dict__)

    @classmethod
    def load(cls):
        import random, string
        d = secure_load(SETTINGS_FILE)
        if d is not None:
            s = cls()
            for k,v in d.items():
                if hasattr(s,k): setattr(s,k,v)
            if not s.friend_code:
                s.friend_code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
                s.save()
            return s
        s = cls()
        s.friend_code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        s.save()
        return s


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
        secure_save(STATS_FILE, self.__dict__)

    @classmethod
    def load(cls):
        d = secure_load(STATS_FILE)
        if d is not None:
            s = cls()
            for k,v in d.items():
                if hasattr(s,k): setattr(s,k,v)
            return s
        return cls()

def load_history() -> List[MatchRecord]:
    data = secure_load(HISTORY_FILE, [])
    return [MatchRecord(**r) for r in data]

def save_history(h: List[MatchRecord]):
    secure_save(HISTORY_FILE, [r.__dict__ for r in h[-10:]])

def add_history(result, diff, mode, elapsed_ms, caps_delta):
    h = load_history()
    import datetime
    h.append(MatchRecord(
        date=datetime.datetime.now().strftime("%d.%m %H:%M"),
        result=result, difficulty=diff, mode=mode,
        duration_s=elapsed_ms//1000, caps_delta=caps_delta
    ))
    save_history(h)
