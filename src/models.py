import os
import json
import random
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any, Optional
import src.state as state
from src.config import T, DECK_FILE, SUIT_SYMBOL, SUIT_COLOR
from src.achievements import unlock_achievement
from src.security import secure_save, secure_load

# ============================================================
# BOT PERSONALITIES
# ============================================================
@dataclass
class BotPersonality:
    key:         str
    display_key: str        # T() key for localised name
    noise:       Dict[str, int]  # override noise per difficulty
    attack_bias: int        # extra score when sabotaging player
    defense_bias: int        # extra score when playing for self
    commentary:  List[str]  # random lines shown as bot messages
    delay_mult:  float      # multiplier on BOT_DELAY_MS

BENNY = BotPersonality(
    key="benny", display_key="bot_benny",
    noise={"easy": 200, "medium": 80, "hard": 15, "impossible": 5},
    attack_bias=180, defense_bias=0,
    commentary=[
        "You've got a lot of nerve...",
        "This desert ain't big enough.",
        "Let's see you recover from that.",
        "Lucky? We'll see about that.",
        "Nobody outsmarts Silas.",
    ],
    delay_mult=1.0,
)
YES_MAN = BotPersonality(
    key="yes_man", display_key="bot_yesman",
    noise={"easy": 300, "medium": 150, "hard": 60, "impossible": 20},
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
    noise={"easy": 120, "medium": 40, "hard": 8, "impossible": 2},
    attack_bias=60, defense_bias=60,
    commentary=[
        "Probability favors the Baron.",
        "Calculated.",
        "The odds are... not in your favour.",
        "Efficient.",
        "The Baron always wins.",
    ],
    delay_mult=0.8,
)

PERSONALITIES = {"benny": BENNY, "yes_man": YES_MAN, "house": HOUSE}
DEFAULT_PERSONALITY = "benny"

def get_bot_delay_ms(diff: str, personality_key: str = DEFAULT_PERSONALITY) -> int:
    """Small readable delay before an AI move, with personality pacing."""
    from src.config import BOT_DELAY_MS
    base = BOT_DELAY_MS.get(diff, BOT_DELAY_MS.get("medium", 800))
    pers = PERSONALITIES.get(personality_key, BENNY)
    return max(500, int(base * getattr(pers, "delay_mult", 1.0)))


# ============================================================
# CARD DATACLASSES
# ============================================================
@dataclass(frozen=True)
class Card:
    rank: str
    suit: Optional[str] = None

    def is_number(self): return self.rank == "A" or self.rank.isdigit()
    def is_picture(self): return self.rank in ("J", "Q", "K", "JKR")

    def value(self):
        if self.rank == "A": return 1
        if self.rank.isdigit(): return int(self.rank)
        return 0

    def label(self):
        if self.rank == "JKR":
            return "Joker" if state.language == "en" else "Джокер"
        if state.language == "ru":
            su = {"S": "П", "H": "Ч", "D": "Б", "C": "К"}
        else:
            su = {"S": "S", "H": "H", "D": "D", "C": "C"}
        return f"{self.rank}{su.get(self.suit, '')}"

    def key(self):
        return "JKR" if self.rank == "JKR" else f"{self.rank}-{self.suit}"

    def display_name(self):
        sn = {"S": "Spades", "H": "Hearts", "D": "Diamonds", "C": "Clubs"}
        rn = {"A": "Ace", "J": "Jack", "Q": "Queen", "K": "King", "JKR": "Joker"}
        r = rn.get(self.rank, self.rank)
        s = sn.get(self.suit or "", "")
        return f"{r} of {s}" if s else r


@dataclass
class NumEntry:
    card: Card
    pics: List[Card] = field(default_factory=list)

    def kings_count(self): return sum(1 for p in self.pics if p.rank == "K")
    def effective_value(self): return self.card.value() * (2 ** self.kings_count())

    def tooltip_lines(self):
        lines = [self.card.display_name(), T("base_value", self.card.value())]
        if self.pics:
            lines.append(T("attached", ", ".join("★" if p.rank == "JKR" else p.rank for p in self.pics)))
        kc = self.kings_count()
        if kc: lines.append(T("effective", self.effective_value(), 2 ** kc))
        return lines


@dataclass
class Caravan:
    nums: List[NumEntry] = field(default_factory=list)

    def empty(self): return len(self.nums) == 0
    def top(self): return self.nums[-1] if self.nums else None

    def base_direction(self):
        if len(self.nums) < 2: return None
        a, b = self.nums[-2].card.value(), self.nums[-1].card.value()
        return "up" if b > a else "down" if b < a else None

    def effective_direction(self):
        base = self.base_direction()
        if base is None: return None
        top = self.top()
        if not top: return base
        q = sum(1 for p in top.pics if p.rank == "Q")
        return ("down" if base == "up" else "up") if q % 2 == 1 else base

    def effective_suit(self):
        top = self.top()
        if not top: return None
        queens = [p for p in top.pics if p.rank == "Q" and p.suit in SUIT_SYMBOL]
        return queens[-1].suit if queens else top.card.suit

    def score(self): return sum(ne.effective_value() for ne in self.nums)
    def for_sale(self): return 21 <= self.score() <= 26

    def trend(self):
        s = self.score()
        if len(self.nums) < 1 or s <= 22: return 0
        d = self.effective_direction()
        if d == "up": return self.nums[-1].card.value()
        if d == "down" and s > 26: return -self.nums[-1].card.value()
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
    ranks = ["A"] + [str(i) for i in range(2, 11)] + ["J", "Q", "K"]
    suits = ["S", "H", "D", "C"]
    deck = [Card(r, s) for s in suits for r in ranks]
    if include_jokers: deck += [Card("JKR"), Card("JKR")]
    return deck

def load_deck_selection():
    data = secure_load(DECK_FILE)
    if data and isinstance(data, dict) and isinstance(data.get("selected_keys"), list):
        valid = {c.key() for c in standard_card_list(True)}
        keys = [str(k) for k in data["selected_keys"] if str(k) in valid]
        seen, uniq = set(), []
        for k in keys:
            if k not in seen: uniq.append(k); seen.add(k)
        return uniq
    return None

def save_deck_selection(keys):
    secure_save(DECK_FILE, {"selected_keys": keys})

def build_deck_from_selection(keys):
    all_cards = standard_card_list(True)
    if not keys:
        deck = list(all_cards); random.shuffle(deck); return deck
    by_key = {c.key(): c for c in all_cards}
    deck = [by_key[k] for k in keys if k in by_key]
    random.shuffle(deck); return deck

def ensure_min30_selection(keys):
    valid = [c.key() for c in standard_card_list(True)]
    s = set(keys)
    pool = [k for k in valid if k not in s]
    random.shuffle(pool)
    while len(keys) < 30 and pool: keys.append(pool.pop())
    return keys

def draw_to_hand(p, target):
    while len(p.hand) < target:
        if not p.deck: return False
        p.hand.append(p.deck.pop())
    return True

def move_card_to_discard(p, c): p.discard.append(c)

def move_entry_to_discard(p, entry):
    move_card_to_discard(p, entry.card)
    for pc in entry.pics: move_card_to_discard(p, pc)


# ============================================================
# GAME RULES
# ============================================================
def can_attach_picture(entry): return len(entry.pics) < 3

def can_play_number_on_caravan(card, caravan):
    if not card.is_number(): return False
    v = card.value()
    if caravan.empty(): return True
    top = caravan.top()
    last_v = top.card.value()
    if v == last_v: return False
    if len(caravan.nums) == 1: return True
    direction = caravan.effective_direction()
    suit_needed = caravan.effective_suit()
    by_dir = (v > last_v if direction == "up" else v < last_v if direction == "down" else False)
    by_suit = (card.suit == suit_needed)
    return by_dir or by_suit

def can_play_picture_on_target(pic, entry, is_last):
    if not pic.is_picture(): return False
    if not can_attach_picture(entry): return False
    if pic.rank == "Q": return is_last
    return True

def apply_jack(actor, caravan, idx):
    entry = caravan.nums.pop(idx)
    move_entry_to_discard(actor, entry)

def apply_king(entry, king): entry.pics.append(king)
def apply_queen(entry, queen): entry.pics.append(queen)

def apply_joker(actor, p1, p2, target_entry, joker_card):
    target_entry.pics.append(joker_card)
    tgt_rank = target_entry.card.rank
    tgt_suit = target_entry.card.suit
    def should_remove(ne):
        if ne is target_entry: return False
        return ne.card.suit == tgt_suit if tgt_rank == "A" else ne.card.rank == tgt_rank
    removed = 0
    for owner in (p1, p2):
        for cav in owner.caravans:
            keep, rem = [], []
            for ne in cav.nums:
                (rem if should_remove(ne) else keep).append(ne)
            for ne in rem:
                move_entry_to_discard(actor, ne)
                removed += 1
            cav.nums = keep
    if removed >= 3: unlock_achievement("JOKER_BOMB")

def discard_hand_card(actor, idx):
    if not (0 <= idx < len(actor.hand)): return False
    move_card_to_discard(actor, actor.hand.pop(idx))
    return True

def disband_caravan(actor, cav_i):
    if cav_i not in (0, 1, 2): return False
    cav = actor.caravans[cav_i]
    if cav.empty(): return False
    for ne in cav.nums: move_entry_to_discard(actor, ne)
    cav.nums = []
    return True

def play_number(actor, card_idx, cav_i):
    if not (0 <= card_idx < len(actor.hand)): return False, "No such card."
    if cav_i not in (0, 1, 2): return False, "Invalid caravan."
    card = actor.hand[card_idx]
    if not card.is_number(): return False, "Not a number card."
    if not can_play_number_on_caravan(card, actor.caravans[cav_i]):
        return False, "Invalid play."
    actor.caravans[cav_i].nums.append(NumEntry(card=card))
    actor.hand.pop(card_idx)
    sc = actor.caravans[cav_i].score()
    if sc == 26:
        unlock_achievement("PERFECT_26")
        state.deferred_bursts.append(("cav26", cav_i, actor.name))
    return True, ""

def play_picture(actor, opponent, card_idx, target_owner, cav_i, entry_i):
    if not (0 <= card_idx < len(actor.hand)): return False, "No such card."
    pic = actor.hand[card_idx]
    if not pic.is_picture(): return False, "Not a face card."
    if cav_i not in (0, 1, 2): return False, "Invalid caravan."
    cav = target_owner.caravans[cav_i]
    if not (0 <= entry_i < len(cav.nums)): return False, "Invalid target."
    entry = cav.nums[entry_i]
    is_last = (entry_i == len(cav.nums) - 1)
    if not can_play_picture_on_target(pic, entry, is_last):
        return False, "Invalid (Q=last card only / limit 3)."
    if pic.rank == "J":
        if entry.effective_value() == 10: unlock_achievement("JACK_ATTACK")
        apply_jack(actor, cav, entry_i)
    elif pic.rank == "K": apply_king(entry, pic)
    elif pic.rank == "Q": apply_queen(entry, pic)
    elif pic.rank == "JKR": apply_joker(actor, actor, opponent, entry, pic)
    actor.hand.pop(card_idx)
    return True, ""


# ============================================================
# WIN CONDITIONS
# ============================================================
def slot_outcome(pv, ps, bv, bs):
    if not ps and not bs: return "not_ready", None
    if ps and not bs: return "ready", "player"
    if bs and not ps: return "ready", "bot"
    if pv == bv: return "tie", None
    return "ready", "player" if pv > bv else "bot"

def check_game_end(player, bot):
    wp = wb = 0
    for i in range(3):
        st, w = slot_outcome(player.caravans[i].score(), player.caravans[i].for_sale(),
                             bot.caravans[i].score(), bot.caravans[i].for_sale())
        if st == "ready":
            if w == "player": wp += 1
            else: wb += 1
    if wp >= 2: return True, "player", T("player_wins")
    if wb >= 2: return True, "bot", T("bot_wins")
    return False, None, ""

def _clone(p):
    return PlayerState(
        name=p.name,
        caravans=[Caravan([NumEntry(ne.card, list(ne.pics)) for ne in c.nums])
                  for c in p.caravans],
        deck=[], discard=[], hand=list(p.hand),
    )

def _clone_full(p):
    return PlayerState(
        name=p.name,
        caravans=[Caravan([NumEntry(ne.card, list(ne.pics)) for ne in c.nums])
                  for c in p.caravans],
        deck=list(p.deck),
        discard=list(p.discard),
        hand=list(p.hand),
    )

def take_snapshot(player, bot):
    return _clone_full(player), _clone_full(bot)

def restore_snapshot(snapshot):
    return snapshot[0], snapshot[1]

def bot_opening_play(bot):
    # Find an empty caravan slot
    empty_idx = -1
    for i in range(3):
        if bot.caravans[i].empty():
            empty_idx = i
            break
    if empty_idx == -1:
        return
    # Find a number card in hand
    card_idx = -1
    for idx, c in enumerate(bot.hand):
        if c.is_number():
            card_idx = idx
            break
    if card_idx == -1:
        # If no number cards, bot must discard a card
        if bot.hand:
            discard_hand_card(bot, 0)
        return
    # Play the card on the empty caravan
    if state.sounds:
        state.sounds.play("deal")
    card = bot.hand.pop(card_idx)
    bot.caravans[empty_idx].nums.append(NumEntry(card=card))
