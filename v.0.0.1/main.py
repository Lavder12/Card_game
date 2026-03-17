import pygame
import random
import sys
import json
import os
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any

# ============================================================
# CARAVAN (Fallout: New Vegas) — комфорт + оптимизация (целиком)
# + Поддержка PNG-артов карт (assets/cards)
# - Конструктор колоды (мин 30, без дублей; стандарт 54)
# - Караваны СКЛАДЫВАЮТСЯ ГОРИЗОНТАЛЬНО (внутри слота)
# - “Злой” бот
# - Открывающая фаза (старт 3 караванов, только A-10)
# - Спецкарты J/Q/K/Joker + лимит 3 “картинки” на числовую
# - Кэш текста (меньше font.render)
# - Рука: адаптивный шаг + скролл колесом если не помещается
# - Исправлен UX “карта пропала”: ход бота выполняется с задержкой + лог хода бота
#
# Управление:
# - ЛКМ по карте в руке: выбрать/снять выбор
# - ЛКМ с выбранной картой:
#     * Числовая (A-10): клик по своему слоту каравана
#     * J/Q/K/🃏: клик по конкретной ЧИСЛОВОЙ карте (у себя или у бота)
# - ПКМ по карте в руке: сбросить (в MAIN-фазе)
# - ПКМ по своему слоту каравана: расформировать караван (в MAIN-фазе)
# - Колесо: скролл руки (если не помещается)
# - ESC: снять выбор
# ============================================================

# === Экран / UI ===
WIDTH, HEIGHT = 1280, 720
FPS = 60

MARGIN = 22
GAP = 14
TOP_BAR_H = 82
SECTION_H = 208
HAND_H_MIN = 190

CARD_W, CARD_H = 70, 98
SELECT_RAISE = 14
PIC_BADGE_W, PIC_BADGE_H = 20, 20

GRID_CARD_W, GRID_CARD_H = 74, 52  # в конструкторе колоды

MAX_VISIBLE_STACK = 9  # сколько карт показывать в караване

# Горизонтальная укладка каравана
STACK_OVERLAP_X = 26
STACK_OVERLAP_X_TIGHT = 18
STACK_PAD_X = 14

# === Цвета (темный Fallout-лайк) ===
BG = (28, 28, 28)
PANEL = (20, 20, 20)
PANEL_2 = (26, 26, 26)

CARD = (72, 72, 72)
CARD_SEL = (86, 150, 86)
TEXT = (210, 210, 190)

BTN = (55, 95, 55)
BTN_H = (85, 155, 85)
BTN_TXT = (230, 230, 200)

RED = (240, 95, 95)
YELLOW = (220, 200, 100)
BLACK = (0, 0, 0)

OUT_OK = (120, 180, 120)
OUT_BAD = (200, 90, 90)

# --- ВАЖНО: пути от папки со скриптом (чтобы assets находились всегда) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def rpath(*parts: str) -> str:
    return os.path.join(BASE_DIR, *parts)


SETTINGS_FILE = rpath("settings.json")
DECK_FILE = rpath("deck.json")
MUSIC_PATH = rpath("music", "music.mp3")

# --- Арты карт ---
CARDS_DIR = rpath("assets", "cards")
USE_ART = True                 # быстро включить/выключить арты
SHOW_LABEL_OVER_ART = False    # если True — поверх арта будет ещё и текст "6♥"
ART_DEBUG = True               # печатает в консоль, сколько карт найдено

SUIT_SYMBOL = {"S": "♠", "H": "♥", "D": "♦", "C": "♣"}
SUIT_COLOR = {"S": TEXT, "C": TEXT, "H": RED, "D": RED}

# Задержка хода бота (чтобы не выглядело как “карта пропала”)
BOT_DELAY_MS = 320


# ============================================================
# Настройки / утилиты
# ============================================================

def clamp(x, lo=0, hi=255):
    return max(lo, min(hi, x))


def lighten(color, amt=18):
    return (clamp(color[0] + amt), clamp(color[1] + amt), clamp(color[2] + amt))


def format_time_ms(ms: int) -> str:
    total_sec = max(0, ms // 1000)
    mm = total_sec // 60
    ss = total_sec % 60
    return f"{mm:02d}:{ss:02d}"


def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                data.setdefault("volume", 0.85)
                data.setdefault("muted", False)
                data.setdefault("bot_uses_player_deck", True)
                return data
        except Exception:
            pass
    return {"volume": 0.85, "muted": False, "bot_uses_player_deck": True}


def save_settings(settings):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ============================================================
# Карты / структуры
# ============================================================

@dataclass(frozen=True)
class Card:
    rank: str  # "A","2".. "10","J","Q","K","JKR"
    suit: Optional[str] = None  # "S","H","D","C" or None for Joker

    def is_number(self) -> bool:
        return self.rank == "A" or self.rank.isdigit()

    def is_picture(self) -> bool:
        return self.rank in ("J", "Q", "K", "JKR")

    def value(self) -> int:
        if self.rank == "A":
            return 1
        if self.rank.isdigit():
            return int(self.rank)
        return 0

    def label(self) -> str:
        if self.rank == "JKR":
            return "🃏"
        s = SUIT_SYMBOL.get(self.suit, "")
        return f"{self.rank}{s}"

    def key(self) -> str:
        if self.rank == "JKR":
            return "JKR"
        return f"{self.rank}-{self.suit}"


@dataclass
class NumEntry:
    card: Card
    pics: List[Card] = field(default_factory=list)

    def kings_count(self) -> int:
        return sum(1 for p in self.pics if p.rank == "K")


@dataclass
class Caravan:
    nums: List[NumEntry] = field(default_factory=list)

    def empty(self) -> bool:
        return len(self.nums) == 0

    def top(self) -> Optional[NumEntry]:
        return self.nums[-1] if self.nums else None

    def base_direction(self) -> Optional[str]:
        if len(self.nums) < 2:
            return None
        a = self.nums[-2].card.value()
        b = self.nums[-1].card.value()
        if b > a:
            return "up"
        if b < a:
            return "down"
        return None

    def effective_direction(self) -> Optional[str]:
        base = self.base_direction()
        if base is None:
            return None
        top = self.top()
        if not top:
            return base
        q_count = sum(1 for p in top.pics if p.rank == "Q")
        if q_count % 2 == 1:
            return "down" if base == "up" else "up"
        return base

    def effective_suit(self) -> Optional[str]:
        top = self.top()
        if not top:
            return None
        queens = [p for p in top.pics if p.rank == "Q" and p.suit in ("S", "H", "D", "C")]
        if queens:
            return queens[-1].suit
        return top.card.suit

    def score(self) -> int:
        total = 0
        for ne in self.nums:
            v = ne.card.value()
            total += v * (2 ** ne.kings_count())
        return total

    def for_sale(self) -> bool:
        s = self.score()
        return 21 <= s <= 26


@dataclass
class PlayerState:
    name: str
    caravans: List[Caravan]
    deck: List[Card]
    discard: List[Card]
    hand: List[Card]


# ============================================================
# Колода: стандарт 52 + 2 Joker; конструктор — подмножество без дублей
# ============================================================

def standard_card_list(include_jokers=True) -> List[Card]:
    ranks = ["A"] + [str(i) for i in range(2, 11)] + ["J", "Q", "K"]
    suits = ["S", "H", "D", "C"]
    deck = [Card(r, s) for s in suits for r in ranks]
    if include_jokers:
        deck += [Card("JKR", None), Card("JKR", None)]
    return deck


def load_deck_selection() -> Optional[List[str]]:
    if not os.path.exists(DECK_FILE):
        return None
    try:
        with open(DECK_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("selected_keys"), list):
            keys = [str(k) for k in data["selected_keys"]]
            valid = {c.key() for c in standard_card_list(True)}
            keys = [k for k in keys if k in valid]
            uniq, seen = [], set()
            for k in keys:
                if k not in seen:
                    uniq.append(k)
                    seen.add(k)
            return uniq
    except Exception:
        return None
    return None


def save_deck_selection(keys: List[str]):
    try:
        with open(DECK_FILE, "w", encoding="utf-8") as f:
            json.dump({"selected_keys": keys}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def build_deck_from_selection(keys: Optional[List[str]]) -> List[Card]:
    all_cards = standard_card_list(True)
    if not keys:
        deck = list(all_cards)
        random.shuffle(deck)
        return deck
    by_key: Dict[str, Card] = {c.key(): c for c in all_cards}
    deck = [by_key[k] for k in keys if k in by_key]
    random.shuffle(deck)
    return deck


def ensure_min30_selection(keys: List[str]) -> List[str]:
    valid = [c.key() for c in standard_card_list(True)]
    s = set(keys)
    pool = [k for k in valid if k not in s]
    random.shuffle(pool)
    while len(keys) < 30 and pool:
        keys.append(pool.pop())
    return keys


# ============================================================
# Добор / discard
# ============================================================

def draw_to_hand(p: PlayerState, target_size: int) -> bool:
    while len(p.hand) < target_size:
        if not p.deck:
            return False
        p.hand.append(p.deck.pop())
    return True


def move_card_to_discard(p: PlayerState, c: Card):
    p.discard.append(c)


def move_entry_to_discard(p: PlayerState, entry: NumEntry):
    move_card_to_discard(p, entry.card)
    for pc in entry.pics:
        move_card_to_discard(p, pc)


# ============================================================
# Правила ходов
# ============================================================

def can_attach_picture(entry: NumEntry) -> bool:
    return len(entry.pics) < 3


def can_play_number_on_caravan(card: Card, caravan: Caravan) -> bool:
    if not card.is_number():
        return False

    v = card.value()
    if caravan.empty():
        return True

    top = caravan.top()
    assert top is not None
    last_v = top.card.value()

    if v == last_v:
        return False

    if len(caravan.nums) == 1:
        return True

    direction = caravan.effective_direction()
    suit_needed = caravan.effective_suit()

    by_dir = False
    if direction == "up":
        by_dir = v > last_v
    elif direction == "down":
        by_dir = v < last_v

    by_suit = (card.suit == suit_needed)
    return by_dir or by_suit


def can_play_picture_on_target(pic: Card, target_entry: NumEntry, is_target_last: bool) -> bool:
    if not pic.is_picture():
        return False
    if not target_entry.card.is_number():
        return False
    if not can_attach_picture(target_entry):
        return False
    if pic.rank == "Q":
        return is_target_last
    return True


def apply_jack(actor: PlayerState, caravan: Caravan, idx: int):
    entry = caravan.nums.pop(idx)
    move_entry_to_discard(actor, entry)


def apply_king(entry: NumEntry, king_card: Card):
    entry.pics.append(king_card)


def apply_queen(entry: NumEntry, queen_card: Card):
    entry.pics.append(queen_card)


def apply_joker(actor: PlayerState, p1: PlayerState, p2: PlayerState,
                target_entry: NumEntry, joker_card: Card):
    """
    Joker:
    - на A: удалить все прочие ЧИСЛОВЫЕ той же печатной масти (у обоих)
    - на 2-10: удалить все прочие ЧИСЛОВЫЕ того же значения (у обоих)
    Цель остается; Joker прикрепляется к цели (учитывается в лимите картинок).
    """
    target_entry.pics.append(joker_card)

    tgt_rank = target_entry.card.rank
    tgt_suit = target_entry.card.suit

    def should_remove(ne: NumEntry) -> bool:
        if ne is target_entry:
            return False
        if not ne.card.is_number():
            return False
        if tgt_rank == "A":
            return ne.card.suit == tgt_suit
        return ne.card.rank == tgt_rank

    def sweep(owner: PlayerState):
        for cav in owner.caravans:
            keep = []
            for ne in cav.nums:
                if should_remove(ne):
                    move_entry_to_discard(actor, ne)
                else:
                    keep.append(ne)
            cav.nums = keep

    sweep(p1)
    sweep(p2)


def discard_hand_card(actor: PlayerState, idx: int) -> bool:
    if idx < 0 or idx >= len(actor.hand):
        return False
    c = actor.hand.pop(idx)
    move_card_to_discard(actor, c)
    return True


def disband_caravan(actor: PlayerState, cav_i: int) -> bool:
    if cav_i not in (0, 1, 2):
        return False
    cav = actor.caravans[cav_i]
    if cav.empty():
        return False
    for ne in cav.nums:
        move_entry_to_discard(actor, ne)
    cav.nums = []
    return True


def play_number(actor: PlayerState, card_idx: int, cav_i: int) -> Tuple[bool, str]:
    if card_idx < 0 or card_idx >= len(actor.hand):
        return False, "Нет карты."
    if cav_i not in (0, 1, 2):
        return False, "Неверный караван."
    card = actor.hand[card_idx]
    if not card.is_number():
        return False, "Это не числовая."
    if not can_play_number_on_caravan(card, actor.caravans[cav_i]):
        return False, "Недопустимо (направление/масть/повтор)."
    actor.caravans[cav_i].nums.append(NumEntry(card=card))
    actor.hand.pop(card_idx)
    return True, ""


def play_picture(actor: PlayerState, opponent: PlayerState,
                 card_idx: int, target_owner: PlayerState,
                 cav_i: int, entry_i: int) -> Tuple[bool, str]:
    if card_idx < 0 or card_idx >= len(actor.hand):
        return False, "Нет карты."
    pic = actor.hand[card_idx]
    if not pic.is_picture():
        return False, "Это не картинка."
    if cav_i not in (0, 1, 2):
        return False, "Неверный караван."
    cav = target_owner.caravans[cav_i]
    if entry_i < 0 or entry_i >= len(cav.nums):
        return False, "Неверная цель."
    entry = cav.nums[entry_i]
    is_last = (entry_i == len(cav.nums) - 1)

    if not can_play_picture_on_target(pic, entry, is_last):
        return False, "Недопустимо (Q только на последнюю / лимит картинок)."

    if pic.rank == "J":
        apply_jack(actor, cav, entry_i)
    elif pic.rank == "K":
        apply_king(entry, pic)
    elif pic.rank == "Q":
        apply_queen(entry, pic)
    elif pic.rank == "JKR":
        apply_joker(actor, p1=actor, p2=opponent, target_entry=entry, joker_card=pic)
    else:
        return False, "Неизвестная картинка."

    actor.hand.pop(card_idx)
    return True, ""


# ============================================================
# Победа / конец игры
# ============================================================

def slot_outcome(pv: int, ps: bool, bv: int, bs: bool) -> Tuple[str, Optional[str]]:
    if not ps and not bs:
        return "not_ready", None
    if ps and not bs:
        return "ready", "player"
    if bs and not ps:
        return "ready", "bot"
    if pv == bv:
        return "tie", None
    return "ready", "player" if pv > bv else "bot"


def check_game_end(player: PlayerState, bot: PlayerState) -> Tuple[bool, Optional[str], str]:
    wins_p = 0
    wins_b = 0
    any_not_ready = False
    any_tie = False

    for i in range(3):
        pv = player.caravans[i].score()
        bv = bot.caravans[i].score()
        ps = player.caravans[i].for_sale()
        bs = bot.caravans[i].for_sale()
        st, w = slot_outcome(pv, ps, bv, bs)
        if st == "not_ready":
            any_not_ready = True
        elif st == "tie":
            any_tie = True
        elif st == "ready":
            if w == "player":
                wins_p += 1
            else:
                wins_b += 1

    if any_not_ready or any_tie:
        return False, None, ""

    if wins_p >= 2:
        return True, "player", "Игрок выиграл (2 из 3)!"
    return True, "bot", "Бот выиграл (2 из 3)!"


# ============================================================
# “Злой” бот: кандидаты + оценка + фокус на саботаже
# ============================================================

def clone_state(p: PlayerState) -> PlayerState:
    caravans = []
    for cav in p.caravans:
        nums = []
        for ne in cav.nums:
            nums.append(NumEntry(card=ne.card, pics=list(ne.pics)))
        caravans.append(Caravan(nums=nums))
    # оптимизация: deck/discard не нужны для эвристики
    return PlayerState(
        name=p.name,
        caravans=caravans,
        deck=[],
        discard=[],
        hand=list(p.hand),
    )


def heuristic(player: PlayerState, bot: PlayerState) -> int:
    score = 0
    for i in range(3):
        bv = bot.caravans[i].score()
        pv = player.caravans[i].score()
        bs = bot.caravans[i].for_sale()
        ps = player.caravans[i].for_sale()

        st, w = slot_outcome(pv, ps, bv, bs)
        if st == "ready":
            score += 600 if w == "bot" else -600
        elif st == "tie":
            score -= 120
        else:
            if bv <= 26:
                score += bv * 4
            else:
                score -= (bv - 26) * 60
            if pv <= 26:
                score -= pv * 4
            else:
                score += (pv - 26) * 30

        if bs:
            score += 250 + (bv - 21) * 20
        if ps:
            score -= 320 + (pv - 21) * 24

        if 18 <= pv <= 20:
            score -= 120
        if 27 <= pv <= 29:
            score -= 90

    return score


def bot_candidates(bot: PlayerState, player: PlayerState) -> List[Tuple[str, Dict[str, Any]]]:
    cand: List[Tuple[str, Dict[str, Any]]] = []

    for i, c in enumerate(bot.hand):
        if c.is_number():
            for cav_i in range(3):
                if can_play_number_on_caravan(c, bot.caravans[cav_i]):
                    cand.append(("play_number", {"card_idx": i, "cav": cav_i}))

    for i, c in enumerate(bot.hand):
        if not c.is_picture():
            continue
        for owner_name, owner in (("bot", bot), ("player", player)):
            for cav_i in range(3):
                cav = owner.caravans[cav_i]
                for ei in range(len(cav.nums)):
                    is_last = (ei == len(cav.nums) - 1)
                    if can_play_picture_on_target(c, cav.nums[ei], is_last):
                        cand.append(("play_pic", {"card_idx": i, "owner": owner_name, "cav": cav_i, "entry": ei}))

    for i in range(len(bot.hand)):
        cand.append(("discard", {"card_idx": i}))

    for cav_i in range(3):
        if not bot.caravans[cav_i].empty():
            cand.append(("disband", {"cav": cav_i}))

    return cand


def bot_choose_move(bot: PlayerState, player: PlayerState, difficulty: str) -> Tuple[str, Dict[str, Any]]:
    cand = bot_candidates(bot, player)
    if not cand:
        return "discard", {"card_idx": 0}

    scored: List[Tuple[int, str, Dict[str, Any]]] = []

    for mtype, payload in cand:
        sp = clone_state(player)
        sb = clone_state(bot)

        ok = True
        if mtype == "play_number":
            i = payload["card_idx"]
            cav_i = payload["cav"]
            if i >= len(sb.hand):
                ok = False
            else:
                c = sb.hand[i]
                if not c.is_number() or not can_play_number_on_caravan(c, sb.caravans[cav_i]):
                    ok = False
                else:
                    sb.caravans[cav_i].nums.append(NumEntry(card=c))
                    sb.hand.pop(i)

        elif mtype == "play_pic":
            i = payload["card_idx"]
            owner = payload["owner"]
            cav_i = payload["cav"]
            entry = payload["entry"]
            if i >= len(sb.hand):
                ok = False
            else:
                pic = sb.hand[i]
                target_owner = sb if owner == "bot" else sp
                if cav_i not in (0, 1, 2) or entry < 0 or entry >= len(target_owner.caravans[cav_i].nums):
                    ok = False
                else:
                    ne = target_owner.caravans[cav_i].nums[entry]
                    is_last = (entry == len(target_owner.caravans[cav_i].nums) - 1)
                    if not can_play_picture_on_target(pic, ne, is_last):
                        ok = False
                    else:
                        if pic.rank == "J":
                            apply_jack(sb, target_owner.caravans[cav_i], entry)
                        elif pic.rank == "K":
                            apply_king(ne, pic)
                        elif pic.rank == "Q":
                            apply_queen(ne, pic)
                        elif pic.rank == "JKR":
                            apply_joker(sb, p1=sp, p2=sb, target_entry=ne, joker_card=pic)
                        sb.hand.pop(i)

        elif mtype == "discard":
            i = payload["card_idx"]
            if i >= len(sb.hand):
                ok = False
            else:
                discard_hand_card(sb, i)

        elif mtype == "disband":
            cav_i = payload["cav"]
            if not disband_caravan(sb, cav_i):
                ok = False

        if not ok:
            continue

        h = heuristic(sp, sb)

        # бонус саботажа
        if mtype == "play_pic" and payload.get("owner") == "player":
            pic0 = bot.hand[payload["card_idx"]] if payload["card_idx"] < len(bot.hand) else None
            if pic0 and pic0.rank == "J":
                cav_i = payload["cav"]
                pv = player.caravans[cav_i].score()
                if 18 <= pv <= 26:
                    h += 220
            if pic0 and pic0.rank == "JKR":
                cav_i = payload["cav"]
                pv = player.caravans[cav_i].score()
                if 18 <= pv <= 26:
                    h += 140

        if difficulty == "easy":
            h += random.randint(-220, 220)
            if mtype == "discard":
                h += 30
        elif difficulty == "medium":
            h += random.randint(-80, 80)
        elif difficulty == "hard":
            h += random.randint(-20, 20)
        elif difficulty == "impossible":
            h += random.randint(-5, 5)

        scored.append((h, mtype, payload))

    if not scored:
        return "discard", {"card_idx": 0}

    scored.sort(key=lambda x: x[0], reverse=True)

    if difficulty == "easy" and len(scored) >= 4:
        pick = random.randint(0, 3)
        return scored[pick][1], scored[pick][2]
    if difficulty == "medium" and len(scored) >= 2:
        pick = 0 if random.random() < 0.8 else 1
        return scored[pick][1], scored[pick][2]

    return scored[0][1], scored[0][2]


def bot_take_turn(bot: PlayerState, player: PlayerState, difficulty: str) -> Tuple[bool, str]:
    mtype, payload = bot_choose_move(bot, player, difficulty)
    msg = ""

    if mtype == "play_number":
        idx = payload["card_idx"]
        cav_i = payload["cav"]
        card = bot.hand[idx] if 0 <= idx < len(bot.hand) else None
        ok, _ = play_number(bot, idx, cav_i)
        if not ok:
            discard_hand_card(bot, 0)
            msg = "Бот: ход сорвался → сброс"
        else:
            msg = f"Бот сыграл {card.label()} на свой караван #{cav_i+1}"

    elif mtype == "play_pic":
        idx = payload["card_idx"]
        owner = payload["owner"]  # "bot" / "player"
        cav_i = payload["cav"]
        entry_i = payload["entry"]

        pic = bot.hand[idx] if 0 <= idx < len(bot.hand) else None
        target_owner = bot if owner == "bot" else player

        target_label = ""
        if 0 <= cav_i < 3 and 0 <= entry_i < len(target_owner.caravans[cav_i].nums):
            target_label = target_owner.caravans[cav_i].nums[entry_i].card.label()

        ok, _ = play_picture(bot, player, idx, target_owner, cav_i, entry_i)
        if not ok:
            discard_hand_card(bot, 0)
            msg = "Бот: не смог сыграть → сброс"
        else:
            side = "себе" if owner == "bot" else "вам"
            if pic:
                if pic.rank == "J":
                    msg = f"Бот сыграл J на {side}: снял {target_label}"
                elif pic.rank == "JKR":
                    msg = f"Бот сыграл 🃏 на {side}: цель {target_label}"
                else:
                    msg = f"Бот сыграл {pic.label()} на {side}: {target_label}"

    elif mtype == "discard":
        idx = payload["card_idx"]
        card = bot.hand[idx] if 0 <= idx < len(bot.hand) else None
        discard_hand_card(bot, idx)
        msg = f"Бот сбросил {card.label() if card else 'карту'}"

    elif mtype == "disband":
        cav_i = payload["cav"]
        if not disband_caravan(bot, cav_i):
            discard_hand_card(bot, 0)
            msg = "Бот: не смог расформировать → сброс"
        else:
            msg = f"Бот расформировал свой караван #{cav_i+1}"

    if not draw_to_hand(bot, 5):
        return False, "У бота закончилась колода — игрок победил!"
    return True, msg


# ============================================================
# Pygame init + кэш текста
# ============================================================

pygame.init()

AUDIO_OK = True
try:
    pygame.mixer.init()
except Exception:
    AUDIO_OK = False
    print("Аудио недоступно, запуск без звука.")

settings = load_settings()

FONT = pygame.font.SysFont("consolas", 26)
SMALL = pygame.font.SysFont("consolas", 20)
TINY = pygame.font.SysFont("consolas", 16)
TITLE = pygame.font.SysFont("consolas", 56, bold=True)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Caravan (Fallout NV) — улучшенная версия")
clock = pygame.time.Clock()


# ============================================================
# CARD ART LOADER (PNG) — robust + debug
# ============================================================

class CardArt:
    """
    Ищет арты в:
    - assets/cards/hand/
    - assets/cards/stack/   (опционально)
    - assets/cards/thumb/   (опционально)
    - assets/cards/         (fallback, если нет подпапок)

    Имена поддерживаются:
    A_S.png / A-S.png / AS.png / S_A.png / A♠.png / ♠A.png
    Joker: JKR.png / JOKER.png / Joker.png / joker.png (+ JKR_1/2)
    """
    def __init__(self, base_dir: str, debug: bool = False):
        self.base_dir = base_dir
        self.debug = debug
        self._file_cache: Dict[str, pygame.Surface] = {}
        self._scaled_cache: Dict[Tuple[str, int, int], pygame.Surface] = {}
        self._missing: set[str] = set()

    def _rank_token(self, rank: str) -> str:
        return "JKR" if rank == "JKR" else rank

    def _suit_token(self, suit: Optional[str]) -> str:
        return "" if suit is None else suit

    def _suit_symbol(self, suit: Optional[str]) -> str:
        if suit is None:
            return ""
        return SUIT_SYMBOL.get(suit, "")

    def _name_candidates(self, card: Card) -> List[str]:
        r = self._rank_token(card.rank)
        s = self._suit_token(card.suit)          # S/H/D/C
        sym = self._suit_symbol(card.suit)       # ♠/♥/♦/♣

        if r == "JKR":
            return [
                "JKR.png", "JOKER.png", "Joker.png", "joker.png",
                "JKR_1.png", "JKR-1.png", "JKR1.png",
                "JKR_2.png", "JKR-2.png", "JKR2.png",
            ]

        return [
            f"{r}_{s}.png", f"{r}-{s}.png", f"{r}{s}.png",
            f"{s}_{r}.png", f"{s}-{r}.png", f"{s}{r}.png",

            f"{r}_{s.lower()}.png", f"{r}-{s.lower()}.png", f"{r}{s.lower()}.png",
            f"{s.lower()}_{r}.png", f"{s.lower()}-{r}.png", f"{s.lower()}{r}.png",

            f"{r}{sym}.png", f"{r}_{sym}.png", f"{r}-{sym}.png",
            f"{sym}{r}.png", f"{sym}_{r}.png", f"{sym}-{r}.png",
        ]

    def _variant_dirs(self, variant: str) -> List[str]:
        # последний элемент "" означает base_dir (assets/cards/) без подпапки
        if variant == "hand":
            return ["hand", ""]
        if variant == "stack":
            return ["stack", "hand", ""]
        if variant == "thumb":
            return ["thumb", "hand", ""]
        return ["hand", ""]

    def _find_file(self, card: Card, variant: str) -> Optional[str]:
        if not USE_ART:
            return None
        for sub in self._variant_dirs(variant):
            folder = os.path.join(self.base_dir, sub) if sub else self.base_dir
            for name in self._name_candidates(card):
                fp = os.path.join(folder, name)
                if os.path.exists(fp):
                    return fp
        return None

    def _load_file(self, fp: str) -> Optional[pygame.Surface]:
        surf = self._file_cache.get(fp)
        if surf is not None:
            return surf
        try:
            img = pygame.image.load(fp).convert_alpha()
            self._file_cache[fp] = img
            return img
        except Exception as e:
            if self.debug:
                print(f"[CardArt] FAIL load: {fp} -> {e}")
            return None

    def get_scaled(self, card: Card, size: Tuple[int, int], variant: str = "hand") -> Optional[pygame.Surface]:
        fp = self._find_file(card, variant)
        if fp is None:
            if self.debug:
                self._missing.add(f"{variant}:{card.key()}")
            return None

        w, h = int(size[0]), int(size[1])
        ck = (fp, w, h)
        cached = self._scaled_cache.get(ck)
        if cached is not None:
            return cached

        base = self._load_file(fp)
        if base is None:
            return None

        if base.get_width() == w and base.get_height() == h:
            self._scaled_cache[ck] = base
            return base

        scaled = pygame.transform.smoothscale(base, (w, h))
        self._scaled_cache[ck] = scaled
        return scaled

    def debug_report(self):
        if not self.debug:
            return
        all_cards = standard_card_list(True)
        found = 0
        for c in all_cards:
            if self._find_file(c, "hand") is not None:
                found += 1
        print(f"[CardArt] base_dir = {self.base_dir}")
        print(f"[CardArt] found(hand) = {found}/{len(all_cards)}")
        if self._missing:
            sample = list(sorted(self._missing))[:12]
            print("[CardArt] missing samples:")
            for s in sample:
                print("  -", s)


CARD_ART = CardArt(CARDS_DIR, debug=ART_DEBUG)
if ART_DEBUG:
    CARD_ART.debug_report()

if AUDIO_OK and os.path.exists(MUSIC_PATH):
    try:
        pygame.mixer.music.load(MUSIC_PATH)
        vol = 0 if settings.get("muted", False) else float(settings.get("volume", 0.85))
        pygame.mixer.music.set_volume(vol)
        pygame.mixer.music.play(-1)
    except Exception:
        pass

# --- Кэш рендера текста ---
_text_cache: Dict[Tuple[int, str, Tuple[int, int, int]], pygame.Surface] = {}
_card_label_cache: Dict[Tuple[str, int, Tuple[int, int, int]], pygame.Surface] = {}


def render_cached(text: str, font: pygame.font.Font, color: Tuple[int, int, int]) -> pygame.Surface:
    key = (id(font), text, color)
    surf = _text_cache.get(key)
    if surf is None:
        surf = font.render(text, True, color)
        _text_cache[key] = surf
    return surf


def draw_text(text, x, y, color=TEXT, font=FONT):
    img = render_cached(text, font, color)
    screen.blit(img, (x, y))
    return img.get_width(), img.get_height()


def draw_text_center(text, rect, color=TEXT, font=FONT):
    img = render_cached(text, font, color)
    x = rect.x + (rect.width - img.get_width()) // 2
    y = rect.y + (rect.height - img.get_height()) // 2
    screen.blit(img, (x, y))


def draw_panel(rect, fill=PANEL, border=BLACK):
    pygame.draw.rect(screen, fill, rect, border_radius=14)
    pygame.draw.rect(screen, border, rect, 3, border_radius=14)


def draw_button(text, rect, pos, color=BTN, hover=BTN_H, font=FONT):
    mx, my = pos
    hov = rect.collidepoint(mx, my)
    pygame.draw.rect(screen, hover if hov else color, rect, border_radius=10)
    pygame.draw.rect(screen, BLACK, rect, 3, border_radius=10)
    draw_text_center(text, rect, BTN_TXT, font=font)
    return hov


def ui_rects():
    top = pygame.Rect(MARGIN, 10, WIDTH - 2 * MARGIN, TOP_BAR_H)
    bot_area_y = top.bottom + GAP
    bot_area = pygame.Rect(MARGIN, bot_area_y, WIDTH - 2 * MARGIN, SECTION_H)
    ply_area_y = bot_area.bottom + GAP
    ply_area = pygame.Rect(MARGIN, ply_area_y, WIDTH - 2 * MARGIN, SECTION_H)
    hand_y = ply_area.bottom + GAP
    hand_h = max(HAND_H_MIN, HEIGHT - hand_y - 16)
    hand = pygame.Rect(MARGIN, hand_y, WIDTH - 2 * MARGIN, hand_h)
    return top, bot_area, ply_area, hand


def caravan_slots(area: pygame.Rect) -> List[pygame.Rect]:
    w = area.width // 3
    rects = []
    for i in range(3):
        rects.append(pygame.Rect(area.x + i * w + 20, area.y + 56, w - 40, CARD_H + 6))
    return rects


def get_idx_at(pos, rects) -> int:
    for i, r in enumerate(rects):
        if r.collidepoint(pos):
            return i
    return -1


def card_color_for(card: Card) -> Tuple[int, int, int]:
    if card.rank == "JKR":
        return YELLOW
    if card.suit in SUIT_COLOR:
        return SUIT_COLOR[card.suit]
    return TEXT


def get_card_label_surface(card: Card, font: pygame.font.Font) -> pygame.Surface:
    color = card_color_for(card)
    key = (card.key(), id(font), color)
    surf = _card_label_cache.get(key)
    if surf is None:
        surf = font.render(card.label(), True, color)
        _card_label_cache[key] = surf
    return surf


def draw_hand_card(rect, card: Card, selected=False, hovered=False):
    img = CARD_ART.get_scaled(card, (rect.w, rect.h), variant="hand") if USE_ART else None
    if img is not None:
        screen.blit(img, rect)

        if selected:
            pygame.draw.rect(screen, OUT_OK, rect, 4, border_radius=10)
        elif hovered:
            pygame.draw.rect(screen, YELLOW, rect, 3, border_radius=10)
        else:
            pygame.draw.rect(screen, BLACK, rect, 3, border_radius=10)

        if SHOW_LABEL_OVER_ART:
            t = get_card_label_surface(card, FONT)
            screen.blit(t, (rect.x + (rect.w - t.get_width()) // 2, rect.y + (rect.h - t.get_height()) // 2))
        return

    base = CARD_SEL if selected else CARD
    if hovered and not selected:
        base = lighten(base, 14)
    pygame.draw.rect(screen, base, rect, border_radius=10)
    pygame.draw.rect(screen, BLACK, rect, 3, border_radius=10)
    img2 = get_card_label_surface(card, FONT)
    x = rect.x + (rect.width - img2.get_width()) // 2
    y = rect.y + (rect.height - img2.get_height()) // 2
    screen.blit(img2, (x, y))


def draw_num_entry(rect, ne: NumEntry):
    img = CARD_ART.get_scaled(ne.card, (rect.w, rect.h), variant="stack") if USE_ART else None

    if img is not None:
        screen.blit(img, rect)
        pygame.draw.rect(screen, BLACK, rect, 3, border_radius=10)
        if SHOW_LABEL_OVER_ART:
            lab = get_card_label_surface(ne.card, SMALL)
            screen.blit(lab, (rect.x + 8, rect.y + 7))
    else:
        pygame.draw.rect(screen, CARD, rect, border_radius=10)
        pygame.draw.rect(screen, BLACK, rect, 3, border_radius=10)
        lab = get_card_label_surface(ne.card, SMALL)
        screen.blit(lab, (rect.x + 8, rect.y + 7))

    # Оверлей: значение с учётом K
    base = ne.card.value()
    k = ne.kings_count()
    shown = base * (2 ** k)

    pad = pygame.Rect(rect.x + 6, rect.y + rect.h - 34, 56, 28)
    overlay = pygame.Surface((pad.w, pad.h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 150))
    screen.blit(overlay, pad.topleft)
    pygame.draw.rect(screen, BLACK, pad, 2, border_radius=6)
    draw_text_center(str(shown), pad, color=TEXT, font=SMALL)

    # Бейджи картинок (K/Q/🃏)
    bx = rect.right - 6 - PIC_BADGE_W
    by = rect.y + 6
    for p in ne.pics[-3:]:
        badge = pygame.Rect(bx, by, PIC_BADGE_W, PIC_BADGE_H)
        pygame.draw.rect(screen, (95, 95, 95), badge, border_radius=4)
        pygame.draw.rect(screen, BLACK, badge, 2, border_radius=4)
        t = "🃏" if p.rank == "JKR" else p.rank
        cc = card_color_for(p) if p.rank == "Q" else TEXT
        draw_text_center(t, badge, color=cc, font=TINY)
        by += PIC_BADGE_H + 4


# --- ГОРИЗОНТАЛЬНЫЕ караваны: hitboxes + draw ---
def build_entry_hitboxes(owner_name: str, slots: List[pygame.Rect], caravans: List[Caravan]) -> List[Tuple[pygame.Rect, str, int, int]]:
    boxes = []
    for ci in range(3):
        cav = caravans[ci]
        base = slots[ci]

        overlap = STACK_OVERLAP_X
        if len(cav.nums) > MAX_VISIBLE_STACK:
            overlap = STACK_OVERLAP_X_TIGHT

        start = max(0, len(cav.nums) - MAX_VISIBLE_STACK)
        y = base.y + (base.height - CARD_H) // 2
        x0 = base.x + STACK_PAD_X

        for ei in range(start, len(cav.nums)):
            vis_i = ei - start
            r = pygame.Rect(x0 + vis_i * overlap, y, CARD_W, CARD_H)
            boxes.append((r, owner_name, ci, ei))
    return boxes


def draw_caravan_stack(slot_rect: pygame.Rect, cav: Caravan):
    pygame.draw.rect(screen, BLACK, slot_rect, 3, border_radius=10)

    overlap = STACK_OVERLAP_X
    if len(cav.nums) > MAX_VISIBLE_STACK:
        overlap = STACK_OVERLAP_X_TIGHT

    start = max(0, len(cav.nums) - MAX_VISIBLE_STACK)

    y = slot_rect.y + (slot_rect.height - CARD_H) // 2
    x0 = slot_rect.x + STACK_PAD_X

    for ei in range(start, len(cav.nums)):
        vis_i = ei - start
        r = pygame.Rect(x0 + vis_i * overlap, y, CARD_W, CARD_H)
        draw_num_entry(r, cav.nums[ei])

    hidden = start
    if hidden > 0:
        badge = pygame.Rect(slot_rect.x + 10, slot_rect.y + 8, 46, 22)
        pygame.draw.rect(screen, (90, 90, 90), badge, border_radius=6)
        pygame.draw.rect(screen, BLACK, badge, 2, border_radius=6)
        draw_text_center(f"+{hidden}", badge, color=TEXT, font=TINY)


# --- Рука: адаптивный шаг + скролл ---
def hand_layout(area: pygame.Rect, n: int, selected_idx: int, scroll_px: int) -> Tuple[List[pygame.Rect], int, int, bool]:
    left_pad = 20
    top_pad = 66
    avail = area.width - 2 * left_pad

    if n <= 0:
        return [], 0, 0, False

    base_step = CARD_W + 10
    total = (n - 1) * base_step + CARD_W

    if total <= avail:
        x0 = area.x + left_pad + (avail - total) // 2
        rects = []
        for i in range(n):
            x = x0 + i * base_step
            y = area.y + top_pad - (SELECT_RAISE if i == selected_idx else 0)
            rects.append(pygame.Rect(x, y, CARD_W, CARD_H))
        return rects, 0, 0, False

    min_step = CARD_W + 2
    step = max(min_step, int((avail - CARD_W) / max(1, (n - 1))))
    total2 = (n - 1) * step + CARD_W

    if total2 > avail:
        step = base_step
        total2 = (n - 1) * step + CARD_W
        max_scroll = max(0, total2 - avail)
        scroll_px = max(0, min(max_scroll, scroll_px))
        x0 = area.x + left_pad - scroll_px
        rects = []
        for i in range(n):
            x = x0 + i * step
            y = area.y + top_pad - (SELECT_RAISE if i == selected_idx else 0)
            rects.append(pygame.Rect(x, y, CARD_W, CARD_H))
        return rects, scroll_px, max_scroll, True

    x0 = area.x + left_pad
    rects = []
    for i in range(n):
        x = x0 + i * step
        y = area.y + top_pad - (SELECT_RAISE if i == selected_idx else 0)
        rects.append(pygame.Rect(x, y, CARD_W, CARD_H))
    return rects, 0, 0, False


def draw_board(player: PlayerState, bot: PlayerState,
               selected_idx: int, msg: str, msg_until: int,
               start_ms: int, phase: str, opening_halfturn: int, bot_diff: str,
               hand_scroll: int,
               pending_bot: bool) -> Dict[str, Any]:
    screen.fill(BG)

    top, bot_area, ply_area, hand_area = ui_rects()
    draw_panel(top, fill=PANEL)
    draw_panel(bot_area, fill=PANEL_2)
    draw_panel(ply_area, fill=PANEL_2)
    draw_panel(hand_area, fill=PANEL)

    mx, my = pygame.mouse.get_pos()
    pos = (mx, my)

    elapsed = pygame.time.get_ticks() - start_ms
    draw_text(f"Фаза: {phase}", top.x + 16, top.y + 10, font=SMALL, color=YELLOW)
    draw_text(f"Сложность: {bot_diff.upper()}", top.x + 160, top.y + 10, font=SMALL, color=TEXT)
    draw_text(f"Время: {format_time_ms(elapsed)}", top.x + 420, top.y + 10, font=SMALL, color=(170, 170, 150))

    vol = float(settings.get("volume", 0.85))
    muted = bool(settings.get("muted", False))
    draw_text(("Звук: ВЫКЛ" if muted else f"Звук: {int(vol*100)}%"),
              top.x + 620, top.y + 10, font=SMALL, color=(170, 170, 150))

    if pending_bot and phase == "MAIN":
        draw_text("Бот думает...", top.x + 820, top.y + 10, font=SMALL, color=YELLOW)

    draw_text(f"Колода игрока: {len(player.deck)}  Отбой: {len(player.discard)}",
              top.x + 16, top.y + 36, font=SMALL, color=(165, 165, 150))
    draw_text(f"Колода бота: {len(bot.deck)}  Отбой: {len(bot.discard)}",
              top.x + 360, top.y + 36, font=SMALL, color=(165, 165, 150))

    hint = "ЛКМ: выбрать/сыграть | ПКМ по карте: сброс | ПКМ по своему слоту: расформировать | ESC: снять выбор | Колесо: скролл руки"
    if phase == "OPENING":
        hint = "Открытие: положи A-10 на 3 пустых своих каравана (3 хода). Сброс/расформирование запрещены."
    draw_text(hint, top.x + 16, top.y + 60, font=SMALL, color=(150, 150, 135))

    draw_text("Караваны бота", bot_area.x + 16, bot_area.y + 14, font=SMALL)
    draw_text("Ваши караваны", ply_area.x + 16, ply_area.y + 14, font=SMALL)
    draw_text("Ваша рука", hand_area.x + 16, hand_area.y + 14, font=SMALL)

    bot_slots = caravan_slots(bot_area)
    ply_slots = caravan_slots(ply_area)

    selected_card = player.hand[selected_idx] if 0 <= selected_idx < len(player.hand) else None

    for i in range(3):
        r = ply_slots[i]
        outline = BLACK
        if selected_card and selected_card.is_number():
            outline = OUT_OK if can_play_number_on_caravan(selected_card, player.caravans[i]) else OUT_BAD
        pygame.draw.rect(screen, outline, r, 3, border_radius=10)

    for i in range(3):
        draw_caravan_stack(bot_slots[i], bot.caravans[i])
        draw_caravan_stack(ply_slots[i], player.caravans[i])

        bs = bot.caravans[i].score()
        ps = player.caravans[i].score()
        bs_sold = bot.caravans[i].for_sale()
        ps_sold = player.caravans[i].for_sale()

        draw_text(f"Сумма: {bs}" + (" (SOLD)" if bs_sold else ""),
                  bot_slots[i].x, bot_slots[i].bottom + 6, font=SMALL, color=YELLOW if bs_sold else TEXT)
        draw_text(f"Сумма: {ps}" + (" (SOLD)" if ps_sold else ""),
                  ply_slots[i].x, ply_slots[i].bottom + 6, font=SMALL, color=YELLOW if ps_sold else TEXT)

    bot_boxes = build_entry_hitboxes("bot", bot_slots, bot.caravans)
    ply_boxes = build_entry_hitboxes("player", ply_slots, player.caravans)

    # подсветка целей для картинок
    if selected_card and selected_card.is_picture():
        for r, owner, ci, ei in ply_boxes + bot_boxes:
            target_owner = player if owner == "player" else bot
            ne = target_owner.caravans[ci].nums[ei]
            is_last = (ei == len(target_owner.caravans[ci].nums) - 1)
            ok = can_play_picture_on_target(selected_card, ne, is_last)
            pygame.draw.rect(screen, OUT_OK if ok else OUT_BAD, r, 2, border_radius=10)

        for r, owner, ci, ei in ply_boxes + bot_boxes:
            if r.collidepoint(pos):
                target_owner = player if owner == "player" else bot
                ne = target_owner.caravans[ci].nums[ei]
                is_last = (ei == len(target_owner.caravans[ci].nums) - 1)
                ok = can_play_picture_on_target(selected_card, ne, is_last)
                pygame.draw.rect(screen, OUT_OK if ok else OUT_BAD, r, 4, border_radius=10)
                break

    rects, hand_scroll, max_scroll, scroll_on = hand_layout(hand_area, len(player.hand), selected_idx, hand_scroll)
    hover_idx = get_idx_at(pos, rects)
    for i, c in enumerate(player.hand):
        if rects[i].right < hand_area.x + 10 or rects[i].x > hand_area.right - 10:
            continue
        draw_hand_card(rects[i], c, selected=(i == selected_idx), hovered=(i == hover_idx))

    if scroll_on and max_scroll > 0:
        bar_w = min(320, hand_area.width - 80)
        bar = pygame.Rect(hand_area.x + (hand_area.width - bar_w)//2, hand_area.y + 40, bar_w, 8)
        pygame.draw.rect(screen, (80, 80, 80), bar, border_radius=6)
        knob_w = max(20, int(bar_w * (bar_w / (bar_w + max_scroll))))
        t = 0 if max_scroll == 0 else hand_scroll / max_scroll
        knob_x = int(bar.x + t * (bar_w - knob_w))
        knob = pygame.Rect(knob_x, bar.y, knob_w, bar.height)
        pygame.draw.rect(screen, BTN_H, knob, border_radius=6)
        pygame.draw.rect(screen, BLACK, bar, 2, border_radius=6)

    now = pygame.time.get_ticks()
    if msg and now < msg_until:
        mr = pygame.Rect(hand_area.x + 20, hand_area.bottom - 52, hand_area.width - 40, 40)
        pygame.draw.rect(screen, (35, 20, 20), mr, border_radius=10)
        pygame.draw.rect(screen, BLACK, mr, 3, border_radius=10)
        draw_text_center(msg, mr, RED, font=SMALL)

    pygame.display.flip()

    return {
        "bot_slots": bot_slots,
        "ply_slots": ply_slots,
        "hand_rects": rects,
        "bot_boxes": bot_boxes,
        "ply_boxes": ply_boxes,
        "hand_scroll": hand_scroll,
        "hand_max_scroll": max_scroll,
        "hand_scroll_on": scroll_on
    }


# ============================================================
# Меню / настройки / конструктор колоды
# ============================================================

def settings_menu():
    global settings
    volume = float(settings.get("volume", 0.85))
    muted = bool(settings.get("muted", False))
    bot_uses_player = bool(settings.get("bot_uses_player_deck", True))

    panel = pygame.Rect(WIDTH // 2 - 360, 120, 720, 500)
    slider_x = panel.x + 140
    slider_y = panel.y + 210
    slider_w = 440
    slider_h = 12
    dragging = False

    while True:
        clock.tick(FPS)
        screen.fill(BG)
        draw_panel(panel, fill=PANEL)

        draw_text_center("Настройки", pygame.Rect(panel.x, panel.y + 18, panel.width, 70), TEXT, TITLE)

        pos = pygame.mouse.get_pos()
        draw_text(f"Громкость: {int(volume*100)}%", panel.x + 140, panel.y + 165, TEXT, font=FONT)

        pygame.draw.rect(screen, (100, 100, 100), (slider_x, slider_y, slider_w, slider_h), border_radius=6)
        hx = slider_x + int(volume * slider_w)
        pygame.draw.circle(screen, BTN_H if dragging else BTN, (hx, slider_y + slider_h//2), 12)
        pygame.draw.circle(screen, BLACK, (hx, slider_y + slider_h//2), 12, 2)

        mute_rect = pygame.Rect(panel.x + 260, panel.y + 260, 200, 52)
        bot_rect  = pygame.Rect(panel.x + 190, panel.y + 322, 340, 52)
        back_rect = pygame.Rect(panel.x + 260, panel.y + 400, 200, 52)

        mhov = draw_button("Звук: ВЫКЛ" if muted else "Звук: ВКЛ", mute_rect, pos, font=SMALL)
        bhov = draw_button("Назад", back_rect, pos, font=SMALL)

        bot_label = "Бот использует вашу колоду: ДА" if bot_uses_player else "Бот использует вашу колоду: НЕТ"
        bot_hov = draw_button(bot_label, bot_rect, pos, font=SMALL)

        pygame.display.flip()

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                settings["volume"] = volume
                settings["muted"] = muted
                settings["bot_uses_player_deck"] = bot_uses_player
                save_settings(settings)
                pygame.quit()
                sys.exit()

            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                settings["volume"] = volume
                settings["muted"] = muted
                settings["bot_uses_player_deck"] = bot_uses_player
                save_settings(settings)
                return

            if e.type == pygame.MOUSEBUTTONDOWN:
                mx, my = e.pos
                if abs(mx - hx) <= 18 and abs(my - (slider_y + slider_h//2)) <= 18:
                    dragging = True
                elif mhov:
                    muted = not muted
                    settings["muted"] = muted
                    if AUDIO_OK:
                        pygame.mixer.music.set_volume(0 if muted else volume)
                    save_settings(settings)
                elif bot_hov:
                    bot_uses_player = not bot_uses_player
                    settings["bot_uses_player_deck"] = bot_uses_player
                    save_settings(settings)
                elif bhov:
                    settings["volume"] = volume
                    settings["muted"] = muted
                    settings["bot_uses_player_deck"] = bot_uses_player
                    save_settings(settings)
                    return

            if e.type == pygame.MOUSEBUTTONUP:
                dragging = False
                settings["volume"] = volume
                settings["muted"] = muted
                save_settings(settings)

            if e.type == pygame.MOUSEMOTION and dragging:
                mx, _ = e.pos
                mx = max(slider_x, min(slider_x + slider_w, mx))
                volume = (mx - slider_x) / slider_w
                settings["volume"] = volume
                if AUDIO_OK and not muted:
                    pygame.mixer.music.set_volume(volume)


def difficulty_menu():
    panel = pygame.Rect(WIDTH // 2 - 360, 140, 720, 460)
    while True:
        clock.tick(FPS)
        screen.fill(BG)
        draw_panel(panel, fill=PANEL)

        draw_text_center("Сложность бота", pygame.Rect(panel.x, panel.y + 18, panel.width, 70), TEXT, TITLE)

        pos = pygame.mouse.get_pos()
        r1 = pygame.Rect(panel.x + 260, panel.y + 140, 200, 56)
        r2 = pygame.Rect(panel.x + 260, panel.y + 210, 200, 56)
        r3 = pygame.Rect(panel.x + 260, panel.y + 280, 200, 56)
        r4 = pygame.Rect(panel.x + 260, panel.y + 350, 200, 56)
        back = pygame.Rect(panel.x + 260, panel.y + 410, 200, 44)

        h1 = draw_button("Easy", r1, pos)
        h2 = draw_button("Medium", r2, pos)
        h3 = draw_button("Hard", r3, pos)
        h4 = draw_button("Impossible", r4, pos, color=RED, hover=lighten(RED, 30))
        hb = draw_button("Назад", back, pos, font=SMALL)

        pygame.display.flip()

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                save_settings(settings)
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                return None
            if e.type == pygame.MOUSEBUTTONDOWN:
                if h1: return "easy"
                if h2: return "medium"
                if h3: return "hard"
                if h4: return "impossible"
                if hb: return None


def deck_builder_menu():
    all_cards = standard_card_list(True)

    keys = load_deck_selection()
    selected = set(keys) if keys else set(c.key() for c in all_cards)

    panel = pygame.Rect(40, 60, WIDTH - 80, HEIGHT - 120)
    grid_rect = pygame.Rect(panel.x + 20, panel.y + 70, panel.width - 40, panel.height - 170)

    def sort_key(c: Card):
        suit_order = {"S": 0, "H": 1, "D": 2, "C": 3, None: 4}
        rank_order = {"A": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, "10": 10,
                      "J": 11, "Q": 12, "K": 13, "JKR": 14}
        return (suit_order.get(c.suit, 9), rank_order.get(c.rank, 99), c.rank)

    all_cards_sorted = sorted(all_cards, key=sort_key)
    cols = max(1, grid_rect.width // (GRID_CARD_W + 10))

    def card_cell_rect(i: int) -> pygame.Rect:
        col = i % cols
        row = i // cols
        x = grid_rect.x + col * (GRID_CARD_W + 10)
        y = grid_rect.y + row * (GRID_CARD_H + 10)
        return pygame.Rect(x, y, GRID_CARD_W, GRID_CARD_H)

    msg = ""
    msg_until = 0

    while True:
        clock.tick(FPS)
        screen.fill(BG)
        draw_panel(panel, fill=PANEL)

        draw_text("Конструктор колоды", panel.x + 20, panel.y + 18, font=TITLE)
        cnt = len(selected)
        draw_text(f"Выбрано: {cnt} (минимум 30)", panel.x + 540, panel.y + 30, font=SMALL, color=YELLOW if cnt >= 30 else RED)

        pos = pygame.mouse.get_pos()

        btn_y = panel.bottom - 80
        b_std = pygame.Rect(panel.x + 20, btn_y, 200, 52)
        b_auto = pygame.Rect(panel.x + 235, btn_y, 200, 52)
        b_clear = pygame.Rect(panel.x + 450, btn_y, 200, 52)
        b_save = pygame.Rect(panel.x + 665, btn_y, 200, 52)
        b_back = pygame.Rect(panel.x + 880, btn_y, 200, 52)

        h_std = draw_button("Стандарт 54", b_std, pos, font=SMALL)
        h_auto = draw_button("Авто 30", b_auto, pos, font=SMALL)
        h_clear = draw_button("Сброс", b_clear, pos, font=SMALL, color=(90, 90, 90), hover=lighten((90, 90, 90), 25))
        h_save = draw_button("Сохранить", b_save, pos, font=SMALL)
        h_back = draw_button("Назад", b_back, pos, font=SMALL, color=(120, 40, 40), hover=(180, 60, 60))

        for i, c in enumerate(all_cards_sorted):
            r = card_cell_rect(i)
            if r.bottom > grid_rect.bottom:
                continue
            on = (c.key() in selected)
            bg = BTN_H if on else (70, 70, 70)
            pygame.draw.rect(screen, bg, r, border_radius=8)
            pygame.draw.rect(screen, BLACK, r, 2, border_radius=8)

            thumb = CARD_ART.get_scaled(c, (r.w, r.h), variant="thumb") if USE_ART else None
            if thumb is not None:
                screen.blit(thumb, r)
                pygame.draw.rect(screen, BLACK, r, 2, border_radius=8)
                if SHOW_LABEL_OVER_ART:
                    draw_text_center(c.label(), r, color=card_color_for(c), font=SMALL)
            else:
                draw_text_center(c.label(), r, color=card_color_for(c), font=SMALL)

            if r.collidepoint(pos):
                pygame.draw.rect(screen, YELLOW, r, 2, border_radius=8)

        now = pygame.time.get_ticks()
        if msg and now < msg_until:
            mr = pygame.Rect(panel.x + 20, panel.y + 60, panel.width - 40, 34)
            pygame.draw.rect(screen, (35, 20, 20), mr, border_radius=10)
            pygame.draw.rect(screen, BLACK, mr, 3, border_radius=10)
            draw_text_center(msg, mr, RED, font=SMALL)

        pygame.display.flip()

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                save_settings(settings)
                pygame.quit()
                sys.exit()

            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                return

            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                mx, my = e.pos

                if h_std:
                    selected = set(c.key() for c in all_cards)
                    continue
                if h_auto:
                    selected = set()
                    nums = [c for c in all_cards if c.is_number()]
                    pics = [c for c in all_cards if c.is_picture() and c.rank != "JKR"]
                    jok = [c for c in all_cards if c.rank == "JKR"]
                    random.shuffle(nums)
                    random.shuffle(pics)
                    random.shuffle(jok)
                    for c in nums[:22]:
                        selected.add(c.key())
                    for c in pics[:7]:
                        selected.add(c.key())
                    if jok:
                        selected.add(jok[0].key())
                    selected = set(ensure_min30_selection(list(selected)))
                    continue
                if h_clear:
                    selected = set()
                    continue
                if h_save:
                    if len(selected) < 30:
                        msg = "Нужно минимум 30 карт!"
                        msg_until = pygame.time.get_ticks() + 1400
                        continue
                    save_deck_selection(sorted(selected))
                    msg = "Колода сохранена!"
                    msg_until = pygame.time.get_ticks() + 1000
                    continue
                if h_back:
                    return

                for i2, c2 in enumerate(all_cards_sorted):
                    r2 = card_cell_rect(i2)
                    if r2.bottom > grid_rect.bottom:
                        continue
                    if r2.collidepoint(mx, my):
                        k2 = c2.key()
                        if k2 in selected:
                            selected.remove(k2)
                        else:
                            selected.add(k2)
                        break


def main_menu():
    panel = pygame.Rect(WIDTH // 2 - 300, 120, 600, 520)
    while True:
        clock.tick(FPS)
        screen.fill(BG)
        draw_panel(panel, fill=PANEL)

        draw_text_center("Caravan", pygame.Rect(panel.x, panel.y + 18, panel.width, 80), TEXT, TITLE)
        draw_text_center("(Fallout: New Vegas)", pygame.Rect(panel.x, panel.y + 86, panel.width, 40), (170, 170, 150), SMALL)

        pos = pygame.mouse.get_pos()
        play_r = pygame.Rect(panel.x + 200, panel.y + 170, 200, 58)
        deck_r = pygame.Rect(panel.x + 200, panel.y + 240, 200, 58)
        set_r  = pygame.Rect(panel.x + 200, panel.y + 310, 200, 58)
        quit_r = pygame.Rect(panel.x + 200, panel.y + 380, 200, 58)

        hp = draw_button("Играть", play_r, pos)
        hd = draw_button("Колода", deck_r, pos)
        hs = draw_button("Настройки", set_r, pos)
        hq = draw_button("Выход", quit_r, pos, color=(120, 40, 40), hover=(180, 60, 60))

        pygame.display.flip()

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                save_settings(settings)
                pygame.quit()
                sys.exit()
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if hp:
                    return "play"
                if hd:
                    deck_builder_menu()
                if hs:
                    settings_menu()
                if hq:
                    save_settings(settings)
                    pygame.quit()
                    sys.exit()


def end_screen(text: str, elapsed_ms: int):
    panel = pygame.Rect(WIDTH // 2 - 360, 170, 720, 380)
    while True:
        clock.tick(FPS)
        screen.fill(BG)
        draw_panel(panel, fill=PANEL)

        draw_text_center(text, pygame.Rect(panel.x, panel.y + 24, panel.width, 90), TEXT, TITLE)
        draw_text_center(f"Время матча: {format_time_ms(elapsed_ms)}",
                         pygame.Rect(panel.x, panel.y + 130, panel.width, 40),
                         (170, 170, 150), SMALL)

        pos = pygame.mouse.get_pos()
        again = pygame.Rect(panel.x + 240, panel.y + 200, 240, 60)
        menu  = pygame.Rect(panel.x + 240, panel.y + 275, 240, 60)

        ha = draw_button("Играть заново", again, pos)
        hm = draw_button("В меню", menu, pos, color=(120, 40, 40), hover=(180, 60, 60))

        pygame.display.flip()

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                save_settings(settings)
                pygame.quit()
                sys.exit()
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if ha:
                    return "restart"
                if hm:
                    return "menu"


# ============================================================
# Матч / фазы
# ============================================================

def start_match(bot_uses_player_deck: bool) -> Tuple[PlayerState, PlayerState, str, int, int]:
    sel = load_deck_selection()
    if sel:
        sel = ensure_min30_selection(sel)
    p_deck = build_deck_from_selection(sel)

    if bot_uses_player_deck:
        b_deck = build_deck_from_selection(sel)
    else:
        b_deck = build_deck_from_selection(None)

    player = PlayerState("Игрок", [Caravan() for _ in range(3)], p_deck, [], [])
    bot = PlayerState("Бот", [Caravan() for _ in range(3)], b_deck, [], [])

    draw_to_hand(player, 8)
    draw_to_hand(bot, 8)

    phase = "OPENING"
    opening_halfturn = 0
    start_ms = pygame.time.get_ticks()
    return player, bot, phase, opening_halfturn, start_ms


def opening_can_play(card: Card) -> bool:
    return card.is_number()


def opening_empty_slots(owner: PlayerState) -> List[int]:
    return [i for i in range(3) if owner.caravans[i].empty()]


def bot_opening_play(bot: PlayerState):
    empty = opening_empty_slots(bot)
    if not empty:
        return
    num_idxs = [i for i, c in enumerate(bot.hand) if c.is_number()]
    if not num_idxs:
        bot.deck.extend(bot.hand)
        bot.hand = []
        random.shuffle(bot.deck)
        draw_to_hand(bot, 8)
        num_idxs = [i for i, c in enumerate(bot.hand) if c.is_number()]
        if not num_idxs:
            return
    i = random.choice(num_idxs)
    cav_i = empty[0]
    card = bot.hand.pop(i)
    bot.caravans[cav_i].nums.append(NumEntry(card=card))


# ============================================================
# Главный цикл
# ============================================================

while True:
    act = main_menu()
    if act != "play":
        continue

    diff = difficulty_menu()
    if diff is None:
        continue

    while True:
        player, bot, phase, opening_halfturn, match_start_ms = start_match(
            bot_uses_player_deck=bool(settings.get("bot_uses_player_deck", True))
        )

        selected = -1
        msg = ""
        msg_until = 0
        hand_scroll = 0

        player_to_move = True

        # задержанный ход бота
        pending_bot = False
        pending_at = 0

        winner_choice = None
        running = True

        while running:
            clock.tick(FPS)

            ui = draw_board(
                player=player, bot=bot,
                selected_idx=selected,
                msg=msg, msg_until=msg_until,
                start_ms=match_start_ms,
                phase=phase,
                opening_halfturn=opening_halfturn,
                bot_diff=diff,
                hand_scroll=hand_scroll,
                pending_bot=pending_bot
            )
            hand_scroll = ui["hand_scroll"]

            # выполнить отложенный ход бота
            now = pygame.time.get_ticks()
            if phase == "MAIN" and pending_bot and now >= pending_at:
                ok2, rmsg = bot_take_turn(bot, player, diff)
                pending_bot = False
                player_to_move = True
                selected = -1
                if not ok2:
                    elapsed = pygame.time.get_ticks() - match_start_ms
                    winner_choice = end_screen("Игрок победил! (у бота кончилась колода)", elapsed)
                    running = False
                elif rmsg:
                    msg = rmsg
                    msg_until = pygame.time.get_ticks() + 1400

            if msg and pygame.time.get_ticks() >= msg_until:
                msg = ""

            if phase == "MAIN":
                ended, win, _ = check_game_end(player, bot)
                if ended:
                    elapsed = pygame.time.get_ticks() - match_start_ms
                    winner_choice = end_screen("Игрок победил!" if win == "player" else "Бот победил!", elapsed)
                    running = False
                    break

            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    save_settings(settings)
                    pygame.quit()
                    sys.exit()

                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_ESCAPE:
                        selected = -1

                # колесо мыши: скролл руки
                if e.type == pygame.MOUSEWHEEL:
                    if ui.get("hand_scroll_on", False):
                        hand_scroll = max(0, min(ui["hand_max_scroll"], hand_scroll - e.y * 50))

                # ===== OPENING =====
                if phase == "OPENING":
                    if not player_to_move:
                        continue

                    if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                        pos = e.pos
                        hi = get_idx_at(pos, ui["hand_rects"])
                        if hi != -1:
                            selected = -1 if selected == hi else hi
                            continue

                        if selected != -1 and selected < len(player.hand):
                            c = player.hand[selected]
                            if not opening_can_play(c):
                                msg = "Открытие: можно только A-10"
                                msg_until = pygame.time.get_ticks() + 1200
                                selected = -1
                                continue

                            did = False
                            for ci, r in enumerate(ui["ply_slots"]):
                                if r.collidepoint(*pos):
                                    if not player.caravans[ci].empty():
                                        msg = "Этот караван уже начат"
                                        msg_until = pygame.time.get_ticks() + 1200
                                        selected = -1
                                        did = True
                                        break
                                    card = player.hand.pop(selected)
                                    player.caravans[ci].nums.append(NumEntry(card=card))
                                    selected = -1
                                    did = True
                                    break

                            if did:
                                opening_halfturn += 1
                                player_to_move = False

                                bot_opening_play(bot)
                                opening_halfturn += 1
                                player_to_move = True

                                if opening_halfturn >= 6:
                                    phase = "MAIN"
                                    player.hand = player.hand[:5]
                                    bot.hand = bot.hand[:5]
                                    if not draw_to_hand(player, 5):
                                        elapsed = pygame.time.get_ticks() - match_start_ms
                                        winner_choice = end_screen("Бот победил! (у игрока кончилась колода)", elapsed)
                                        running = False
                                        break
                                    if not draw_to_hand(bot, 5):
                                        elapsed = pygame.time.get_ticks() - match_start_ms
                                        winner_choice = end_screen("Игрок победил! (у бота кончилась колода)", elapsed)
                                        running = False
                                        break
                    continue

                # ===== MAIN =====
                if phase == "MAIN":
                    # пока бот “думает” — блокируем действия игрока
                    if not player_to_move:
                        continue

                    if e.type == pygame.MOUSEBUTTONDOWN:
                        x, y = e.pos
                        pos = (x, y)

                        # ПКМ: сброс по карте / расформировать по слоту
                        if e.button == 3:
                            hi = get_idx_at(pos, ui["hand_rects"])
                            if hi != -1:
                                if discard_hand_card(player, hi):
                                    if not draw_to_hand(player, 5):
                                        elapsed = pygame.time.get_ticks() - match_start_ms
                                        winner_choice = end_screen("Бот победил! (у игрока кончилась колода)", elapsed)
                                        running = False
                                        break

                                    pending_bot = True
                                    pending_at = pygame.time.get_ticks() + BOT_DELAY_MS
                                    player_to_move = False
                                    selected = -1
                                    continue

                            for ci, r in enumerate(ui["ply_slots"]):
                                if r.collidepoint(x, y):
                                    if disband_caravan(player, ci):
                                        if not draw_to_hand(player, 5):
                                            elapsed = pygame.time.get_ticks() - match_start_ms
                                            winner_choice = end_screen("Бот победил! (у игрока кончилась колода)", elapsed)
                                            running = False
                                            break

                                        pending_bot = True
                                        pending_at = pygame.time.get_ticks() + BOT_DELAY_MS
                                        player_to_move = False
                                        selected = -1
                                        continue
                                    else:
                                        msg = "Нечего расформировывать"
                                        msg_until = pygame.time.get_ticks() + 1000
                                        selected = -1
                                        break
                            continue

                        # ЛКМ: выбор карты или игра
                        if e.button == 1:
                            hi = get_idx_at(pos, ui["hand_rects"])
                            if hi != -1:
                                selected = -1 if selected == hi else hi
                                continue

                            if selected == -1 or selected >= len(player.hand):
                                continue

                            c = player.hand[selected]

                            # 1) числовая -> клик по своему слоту
                            if c.is_number():
                                played = False
                                for ci, r in enumerate(ui["ply_slots"]):
                                    if r.collidepoint(x, y):
                                        ok, emsg = play_number(player, selected, ci)
                                        selected = -1
                                        played = True
                                        if not ok:
                                            msg = emsg
                                            msg_until = pygame.time.get_ticks() + 1400
                                            break

                                        if not draw_to_hand(player, 5):
                                            elapsed = pygame.time.get_ticks() - match_start_ms
                                            winner_choice = end_screen("Бот победил! (у игрока кончилась колода)", elapsed)
                                            running = False
                                            break

                                        pending_bot = True
                                        pending_at = pygame.time.get_ticks() + BOT_DELAY_MS
                                        player_to_move = False
                                        break

                                if not running:
                                    break
                                if played:
                                    continue

                                msg = "Числовые кладутся только на свой караван"
                                msg_until = pygame.time.get_ticks() + 1200
                                selected = -1
                                continue

                            # 2) картинка -> клик по конкретной числовой карте
                            if c.is_picture():
                                hit = None
                                for r, owner, ci, ei in ui["ply_boxes"] + ui["bot_boxes"]:
                                    if r.collidepoint(x, y):
                                        hit = (owner, ci, ei)
                                        break
                                if not hit:
                                    msg = "Картинки нужно класть на числовую карту"
                                    msg_until = pygame.time.get_ticks() + 1200
                                    selected = -1
                                    continue

                                owner, ci, ei = hit
                                target_owner = player if owner == "player" else bot
                                ok, emsg = play_picture(player, bot, selected, target_owner, ci, ei)
                                selected = -1
                                if not ok:
                                    msg = emsg
                                    msg_until = pygame.time.get_ticks() + 1500
                                    continue

                                if not draw_to_hand(player, 5):
                                    elapsed = pygame.time.get_ticks() - match_start_ms
                                    winner_choice = end_screen("Бот победил! (у игрока кончилась колода)", elapsed)
                                    running = False
                                    break

                                pending_bot = True
                                pending_at = pygame.time.get_ticks() + BOT_DELAY_MS
                                player_to_move = False
                                continue

        if winner_choice == "menu":
            break
        if winner_choice == "restart":
            continue
        break
