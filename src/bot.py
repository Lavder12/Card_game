import random
import math
import pygame
import src.state as state
from src.config import T, HAND_TARGET_SIZE
from src.models import (
    BENNY, PERSONALITIES, DEFAULT_PERSONALITY, NumEntry, PlayerState, Caravan,
    can_play_number_on_caravan, can_play_picture_on_target,
    apply_jack, apply_king, apply_queen, apply_joker,
    discard_hand_card, disband_caravan, play_number, play_picture,
    slot_outcome, _clone, draw_to_hand
)

def heuristic(player, bot):
    score = 0
    for i in range(3):
        bv, bs = bot.caravans[i].score(), bot.caravans[i].for_sale()
        pv, ps = player.caravans[i].score(), player.caravans[i].for_sale()
        st, w = slot_outcome(pv, ps, bv, bs)
        if st == "ready":
            score += 600 if w == "bot" else -600
        elif st == "tie":
            score -= 120
        else:
            score += bv * 4 if bv <= 26 else -(bv - 26) * 60
            score -= pv * 4 if pv <= 26 else -(pv - 26) * 30
        if bs: score += 250 + (bv - 21) * 20
        if ps: score -= 320 + (pv - 21) * 24
        if 18 <= pv <= 20: score -= 120
        if 27 <= pv <= 29: score -= 90
        bt = bot.caravans[i].trend()
        if bv > 22 and bt > 0: score -= bt * 8
        pt = player.caravans[i].trend()
        if pv > 22 and pt > 0: score += pt * 6
    return score

def _bot_candidates(bot, player):
    cands = []
    for i, c in enumerate(bot.hand):
        if c.is_number():
            for ci in range(3):
                if can_play_number_on_caravan(c, bot.caravans[ci]):
                    cands.append(("play_number", {"card_idx": i, "cav": ci}))
    for i, c in enumerate(bot.hand):
        if not c.is_picture(): continue
        for own_name, own in (("bot", bot), ("player", player)):
            for ci in range(3):
                cav = own.caravans[ci]
                for ei in range(len(cav.nums)):
                    if can_play_picture_on_target(c, cav.nums[ei], ei == len(cav.nums) - 1):
                        cands.append(("play_pic", {"card_idx": i, "owner": own_name, "cav": ci, "entry": ei}))
    for i in range(len(bot.hand)):
        cands.append(("discard", {"card_idx": i}))
    for ci in range(3):
        if not bot.caravans[ci].empty():
            cands.append(("disband", {"cav": ci}))
    return cands

def _sim_move(mtype, payload, sp, sb):
    if mtype == "play_number":
        i, ci = payload["card_idx"], payload["cav"]
        if i >= len(sb.hand): return False
        c = sb.hand[i]
        if not c.is_number() or not can_play_number_on_caravan(c, sb.caravans[ci]): return False
        sb.caravans[ci].nums.append(NumEntry(card=c))
        sb.hand.pop(i)
    elif mtype == "play_pic":
        i, own, ci, ei = payload["card_idx"], payload["owner"], payload["cav"], payload["entry"]
        if i >= len(sb.hand): return False
        pic = sb.hand[i]
        tgt = sb if own == "bot" else sp
        if ci not in (0, 1, 2) or ei >= len(tgt.caravans[ci].nums): return False
        ne = tgt.caravans[ci].nums[ei]
        is_last = (ei == len(tgt.caravans[ci].nums) - 1)
        if not can_play_picture_on_target(pic, ne, is_last): return False
        if pic.rank == "J": apply_jack(sb, tgt.caravans[ci], ei)
        elif pic.rank == "K": apply_king(ne, pic)
        elif pic.rank == "Q": apply_queen(ne, pic)
        elif pic.rank == "JKR": apply_joker(sb, sp, sb, ne, pic)
        sb.hand.pop(i)
    elif mtype == "discard":
        i = payload["card_idx"]
        if i >= len(sb.hand): return False
        discard_hand_card(sb, i)
    elif mtype == "disband":
        if not disband_caravan(sb, payload["cav"]): return False
    return True

def bot_choose_move(bot, player, difficulty, personality_key=DEFAULT_PERSONALITY):
    pers = PERSONALITIES.get(personality_key, BENNY)
    cands = _bot_candidates(bot, player)
    if not cands: return "discard", {"card_idx": 0}
    scored = []
    for mtype, payload in cands:
        sp, sb = _clone(player), _clone(bot)
        if not _sim_move(mtype, payload, sp, sb): continue
        h = heuristic(sp, sb)
        # Personality biases
        if mtype == "play_pic" and payload["owner"] == "player":
            pi = payload["card_idx"]
            if pi < len(bot.hand):
                pic = bot.hand[pi]
                pv = player.caravans[payload["cav"]].score()
                if pic.rank == "J" and 18 <= pv <= 26:   h += 220 + pers.attack_bias
                if pic.rank == "JKR" and 18 <= pv <= 26: h += 140 + pers.attack_bias
        if mtype in ("play_number", "disband"): h += pers.defense_bias
        noise = pers.noise.get(difficulty, 80)
        h += random.randint(-noise, noise)
        if difficulty == "easy" and mtype == "discard": h += 30
        scored.append((h, mtype, payload))
    if not scored: return "discard", {"card_idx": 0}
    scored.sort(key=lambda x: x[0], reverse=True)
    if difficulty == "easy" and len(scored) >= 4:
        k = random.randint(0, 3)
        return scored[k][1], scored[k][2]
    if difficulty == "medium" and len(scored) >= 2:
        k = 0 if random.random() < 0.80 else 1
        return scored[k][1], scored[k][2]
    return scored[0][1], scored[0][2]

def bot_take_turn(bot, player, difficulty, personality_key=DEFAULT_PERSONALITY):
    from src.ui import get_bot_tell, set_bot_tell
    from src.config import HAND_OPENING_SIZE, HAND_TARGET_SIZE
    pers = PERSONALITIES.get(personality_key, BENNY)
    mtype, payload = bot_choose_move(bot, player, difficulty, personality_key)
    msg = ""
    was_play = False
    commentary = ""
    if random.random() < 0.25 and pers.commentary:
        commentary = random.choice(pers.commentary)

    if mtype == "play_number":
        i, ci = payload["card_idx"], payload["cav"]
        card = bot.hand[i] if 0 <= i < len(bot.hand) else None
        ok, _ = play_number(bot, i, ci)
        if ok and card:
            msg = f"Bot played {card.label()} on caravan #{ci+1}"
            was_play = True
            # Tell on 26
            if bot.caravans[ci].score() == 26:
                tell = get_bot_tell(personality_key, "26")
                if tell: set_bot_tell(tell, (195, 162, 52))
        else:
            discard_hand_card(bot, 0)
            msg = "Bot: failed → discard"
    elif mtype == "play_pic":
        i, own, ci, ei = payload["card_idx"], payload["owner"], payload["cav"], payload["entry"]
        pic = bot.hand[i] if 0 <= i < len(bot.hand) else None
        tgt = bot if own == "bot" else player
        tlbl = (tgt.caravans[ci].nums[ei].card.label()
                if 0 <= ci < 3 and 0 <= ei < len(tgt.caravans[ci].nums) else "?")
        ok, _ = play_picture(bot, player, i, tgt, ci, ei)
        if ok and pic:
            side = "self" if own == "bot" else "you"
            if pic.rank == "J":
                msg = f"Bot played J on {side}: removed {tlbl}"
                tell = get_bot_tell(personality_key, "jack")
                if tell: set_bot_tell(tell, (230, 80, 80))
            elif pic.rank == "JKR":
                jkr_lbl = "Joker" if state.language == "en" else "Джокера"
                msg = f"Bot played {jkr_lbl} on {side}: {tlbl}"
                tell = get_bot_tell(personality_key, "joker")
                if tell: set_bot_tell(tell, (110, 35, 150))
            elif pic.rank == "K":
                tell = get_bot_tell(personality_key, "king")
                if tell: set_bot_tell(tell, (210, 185, 72))
                msg = f"Bot played {pic.label()} on {side}: {tlbl}"
            else:
                msg = f"Bot played {pic.label()} on {side}: {tlbl}"
            was_play = True
        else:
            discard_hand_card(bot, 0)
            msg = "Bot: failed → discard"
    elif mtype == "discard":
        i = payload["card_idx"]
        card = bot.hand[i] if 0 <= i < len(bot.hand) else None
        discard_hand_card(bot, i)
        msg = f"Bot discarded {card.label() if card else '?'}"
    elif mtype == "disband":
        ci = payload["cav"]
        if disband_caravan(bot, ci):
            msg = f"Bot disbanded caravan #{ci+1}"
        else:
            discard_hand_card(bot, 0)
            msg = "Bot: failed disband → discard"

    if commentary: msg = f'"{commentary}"'
    if not draw_to_hand(bot, HAND_TARGET_SIZE):
        return False, T("bot_deck_empty_win"), False
    return True, msg, was_play
