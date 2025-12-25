import pygame
import random
import sys
import json
import os

# === Настройки ===
WIDTH, HEIGHT = 1280, 720
CARD_WIDTH, CARD_HEIGHT = 60, 90

# Цвета (темная палитра в стиле Fallout)
BG_COLOR = (30, 30, 30)
PANEL_COLOR = (22, 22, 22)
PANEL_COLOR_2 = (28, 28, 28)

CARD_COLOR = (60, 60, 60)
CARD_SELECTED_COLOR = (80, 140, 80)
TEXT_COLOR = (200, 200, 180)

BUTTON_COLOR = (50, 90, 50)
BUTTON_HOVER_COLOR = (80, 150, 80)
BUTTON_TEXT_COLOR = (220, 220, 180)

RED = (255, 100, 100)
BLACK = (0, 0, 0)

SETTINGS_FILE = "settings.json"

# === UI Layout ===
MARGIN = 30
TOP_Y = 10
GAP = 15

TOP_BAR_H = 70
SECTION_H = 170
HAND_MIN_H = 190

CARAVAN_CARD_OVERLAP = 18
HAND_CARD_GAP = 10
SELECT_RAISE_PX = 12

# Для подсветки
HOVER_OUTLINE = (120, 180, 120)
HOVER_BAD_OUTLINE = (200, 80, 80)

def clamp(x, lo=0, hi=255):
    return max(lo, min(hi, x))

def lighten(color, amt=15):
    return (clamp(color[0] + amt), clamp(color[1] + amt), clamp(color[2] + amt))

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"volume": 0.9, "muted": False}

def save_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


pygame.init()
pygame.mixer.init()
settings = load_settings()

# Шрифты
FONT = pygame.font.SysFont("consolas", 28)
SMALL_FONT = pygame.font.SysFont("consolas", 22)
TITLE_FONT = pygame.font.SysFont("consolas", 60, bold=True)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Караван (Fallout)")

# Загрузка музыки (нужно иметь файл music/music.mp3)
try:
    pygame.mixer.music.load("music/music.mp3")
    volume = 0 if settings.get("muted", False) else settings.get("volume", 0.9)
    pygame.mixer.music.set_volume(volume)
    pygame.mixer.music.play(-1)
except Exception:
    print("Не удалось загрузить музыку. Убедитесь, что файл music/music.mp3 в папке с игрой.")


def draw_text(text, x, y, color=TEXT_COLOR, font=FONT):
    img = font.render(text, True, color)
    screen.blit(img, (x, y))
    return img.get_width(), img.get_height()

def draw_text_center(text, rect, color=TEXT_COLOR, font=FONT):
    img = font.render(text, True, color)
    x = rect.x + (rect.width - img.get_width()) // 2
    y = rect.y + (rect.height - img.get_height()) // 2
    screen.blit(img, (x, y))

def draw_panel(rect, fill=PANEL_COLOR, border=BLACK):
    pygame.draw.rect(screen, fill, rect, border_radius=14)
    pygame.draw.rect(screen, border, rect, 3, border_radius=14)

def draw_button(text, x, y, width, height, color, hover_color, pos, font=FONT):
    mx, my = pos
    rect = pygame.Rect(x, y, width, height)
    is_hovered = rect.collidepoint(mx, my)
    pygame.draw.rect(screen, hover_color if is_hovered else color, rect, border_radius=10)
    pygame.draw.rect(screen, BLACK, rect, 3, border_radius=10)
    draw_text_center(text, rect, BUTTON_TEXT_COLOR, font=font)
    return is_hovered, rect

def draw_icon_button(text, rect, pos):
    mx, my = pos
    hovered = rect.collidepoint(mx, my)
    color = lighten(BUTTON_COLOR, 20) if hovered else BUTTON_COLOR
    pygame.draw.rect(screen, color, rect, border_radius=10)
    pygame.draw.rect(screen, BLACK, rect, 3, border_radius=10)
    draw_text_center(text, rect, BUTTON_TEXT_COLOR, font=SMALL_FONT)
    return hovered, rect

def draw_locked_overlay(rect):
    overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 120))
    screen.blit(overlay, (rect.x, rect.y))
    draw_text_center("LOCKED", rect, RED, font=SMALL_FONT)

def draw_card(rect, value, selected=False, hovered=False):
    color = CARD_SELECTED_COLOR if selected else CARD_COLOR
    if hovered and not selected:
        color = lighten(color, 15)

    pygame.draw.rect(screen, color, rect, border_radius=8)
    pygame.draw.rect(screen, BLACK, rect, 3, border_radius=8)
    draw_text_center(str(value), rect, TEXT_COLOR, font=FONT)


def create_deck():
    numeric = [str(i) for i in range(2, 11)]
    faces = ["J", "Q", "K", "A"]
    deck = (numeric + faces) * 4 * 2
    random.shuffle(deck)
    return deck

def draw_cards(hand, deck, count=8):
    while len(hand) < count and deck:
        hand.append(deck.pop())

def card_value(card):
    if card.isdigit():
        return int(card)
    if card == "A":
        return 1
    if card in ["J", "Q", "K"]:
        return 0
    return 0

def caravan_score(caravan):
    return sum(card_value(c) for c in caravan["cards"])

def delivered_caravans(caravans):
    return sum(1 for caravan in caravans if 21 <= caravan_score(caravan) <= 26)

def is_valid_move(caravan, card):
    # Если караван завершён, то в него нельзя класть карты
    if caravan["locked"]:
        return False

    cards = caravan["cards"]
    if card in ["J", "Q", "K"]:
        return len(cards) > 0

    if not cards:
        return card not in ["J", "Q", "K"]

    if len(cards) == 1:
        return card not in ["J", "Q", "K"]

    # Определяем направление по первым двум картам
    ascending = card_value(cards[1]) > card_value(cards[0])
    if ascending and card_value(card) > card_value(cards[-1]):
        return True
    if not ascending and card_value(card) < card_value(cards[-1]):
        return True
    return False

def play_card(hand, caravans, hand_idx, caravan_idx):
    card = hand[hand_idx]
    target = caravans[caravan_idx]

    # Если караван завершён, ход недопустим
    if target["locked"]:
        return False

    # Обычные карты кладём только в свой караван
    if card not in ["J", "Q", "K"]:
        if is_valid_move(target, card):
            target["cards"].append(card)
            del hand[hand_idx]
            return True
        return False

    # Спецкарты — могут применяться и к чужим караванам
    if card == "J":
        if target["cards"]:
            target["cards"].pop()
            del hand[hand_idx]
            return True
    elif card == "Q":
        if len(target["cards"]) >= 2:
            target["cards"][0], target["cards"][1] = target["cards"][1], target["cards"][0]
            del hand[hand_idx]
            return True
    elif card == "K":
        if target["cards"]:
            last = target["cards"][-1]
            if last.isdigit():
                target["cards"][-1] = str(int(last) * 2)
            del hand[hand_idx]
            return True
    return False


def bot_turn(bot, deck, player=None, difficulty="easy"):
    draw_cards(bot["hand"], deck)
    hand = bot["hand"]
    caravans = bot["caravans"]

    if difficulty == "easy":
        for i, card in enumerate(hand):
            for j in range(3):
                if caravans[j]["locked"]:
                    continue
                if is_valid_move(caravans[j], card):
                    play_card(hand, caravans, i, j)
                    return
        if hand:
            hand.pop()
        return

    elif difficulty == "medium":
        best_score = -1000
        best_move = None
        for i, card in enumerate(hand):
            for j in range(3):
                if caravans[j]["locked"]:
                    continue
                test_caravan = list(caravans[j]["cards"])
                if card in ["J", "Q", "K"]:
                    continue  # избегаем спецкарт для среднего уровня
                if is_valid_move({"cards": test_caravan, "locked": False}, card):
                    test_caravan.append(card)
                    score = caravan_score({"cards": test_caravan})
                    if 21 <= score <= 26:
                        score += 50  # приоритет «золотой зоны»
                    if score > best_score:
                        best_score = score
                        best_move = (i, j)
        if best_move:
            i, j = best_move
            play_card(hand, caravans, i, j)
            return
        if hand:
            hand.pop()
        return

    elif difficulty == "hard":
        best_score = -1000
        best_move = None

        for i, card in enumerate(hand):
            for j in range(3):
                if caravans[j]["locked"]:
                    continue

                # если карта обычная — анализируем полезность
                if card not in ["J", "Q", "K"]:
                    test_caravan = list(caravans[j]["cards"])
                    if is_valid_move({"cards": test_caravan, "locked": False}, card):
                        test_caravan.append(card)
                        score = caravan_score({"cards": test_caravan})
                        if 21 <= score <= 26:
                            score += 100
                        elif score > 26:
                            score -= 50
                        if score > best_score:
                            best_score = score
                            best_move = (i, j)

                elif card == "J" and player:
                    for pi in range(3):
                        pc = player["caravans"][pi]
                        if pc["cards"]:
                            last = pc["cards"][-1]
                            if card_value(last) >= 8:
                                play_card(hand, player["caravans"], i, pi)
                                return

                elif card == "K":
                    if caravans[j]["cards"]:
                        test_cards = list(caravans[j]["cards"])
                        last = test_cards[-1]
                        if last.isdigit():
                            new_val = int(last) * 2
                            test_cards[-1] = str(new_val)
                            score = sum(card_value(c) for c in test_cards)
                            if 21 <= score <= 26:
                                play_card(hand, caravans, i, j)
                                return

                elif card == "Q":
                    if len(caravans[j]["cards"]) >= 2:
                        play_card(hand, caravans, i, j)
                        return

        if best_move:
            i, j = best_move
            play_card(hand, caravans, i, j)
            return

        if hand:
            hand.pop()
        return

    elif difficulty == "impossible":
        best_score = -float("inf")
        best_move = None

        for i, card in enumerate(hand):
            for j in range(3):
                target = caravans[j]
                if target["locked"]:
                    continue

                if card not in ["J", "Q", "K"]:
                    if is_valid_move(target, card):
                        test = list(target["cards"]) + [card]
                        score = caravan_score({"cards": test})
                        if 21 <= score <= 26:
                            score += 1000
                        elif score > 26:
                            score -= 100
                        else:
                            score += score
                        if score > best_score:
                            best_score = score
                            best_move = ("play", i, j)

                elif card == "J" and player:
                    for k in range(3):
                        player_cav = player["caravans"][k]
                        if player_cav["cards"]:
                            last = player_cav["cards"][-1]
                            if card_value(last) >= 5:
                                best_move = ("remove", i, k)
                                best_score = 999

                elif card == "K":
                    if target["cards"]:
                        last = target["cards"][-1]
                        if last.isdigit():
                            doubled = int(last) * 2
                            test = list(target["cards"])
                            test[-1] = str(doubled)
                            score = caravan_score({"cards": test})
                            if 21 <= score <= 26:
                                best_move = ("double", i, j)
                                best_score = 1000

                elif card == "Q":
                    if len(target["cards"]) >= 2:
                        best_move = ("swap", i, j)
                        best_score = 10

        if best_move:
            move_type, i, j = best_move
            if move_type in ["play", "double", "swap"]:
                play_card(hand, caravans, i, j)
            elif move_type == "remove" and player:
                play_card(hand, player["caravans"], i, j)
            return

        if hand:
            hand.pop()
        return


def ui_rects():
    top_bar = pygame.Rect(MARGIN, TOP_Y, WIDTH - 2 * MARGIN, TOP_BAR_H)

    bot_area_y = top_bar.bottom + GAP
    bot_area = pygame.Rect(MARGIN, bot_area_y, WIDTH - 2 * MARGIN, SECTION_H)

    player_area_y = bot_area.bottom + GAP
    player_area = pygame.Rect(MARGIN, player_area_y, WIDTH - 2 * MARGIN, SECTION_H)

    hand_area_y = player_area.bottom + GAP
    hand_h = max(HAND_MIN_H, HEIGHT - hand_area_y - 20)
    hand_area = pygame.Rect(MARGIN, hand_area_y, WIDTH - 2 * MARGIN, hand_h)

    return top_bar, bot_area, player_area, hand_area

def caravan_rects(area_rect, y_offset=55):
    # 3 каравана равномерно по ширине панели
    slot_w = area_rect.width // 3
    cav_w = slot_w - 40
    cav_h = CARD_HEIGHT
    y = area_rect.y + y_offset
    rects = []
    for i in range(3):
        x = area_rect.x + 20 + i * slot_w
        rects.append(pygame.Rect(x, y, cav_w, cav_h))
    return rects

def hand_card_rects(hand_area, hand, selected_card):
    rects = []
    base_x = hand_area.x + 20
    base_y = hand_area.y + 70
    for i, _ in enumerate(hand):
        x = base_x + i * (CARD_WIDTH + HAND_CARD_GAP)
        y = base_y - (SELECT_RAISE_PX if i == selected_card else 0)
        rects.append(pygame.Rect(x, y, CARD_WIDTH, CARD_HEIGHT))
    return rects

def get_hand_index_at(pos, rects):
    for i, r in enumerate(rects):
        if r.collidepoint(pos):
            return i
    return -1

def get_caravan_side_and_index(pos, bot_cav_rects, player_cav_rects):
    x, y = pos
    for i, r in enumerate(bot_cav_rects):
        if r.collidepoint(x, y):
            return ("bot", i)
    for i, r in enumerate(player_cav_rects):
        if r.collidepoint(x, y):
            return ("player", i)
    return (None, -1)


def draw_game(player, bot, deck, selected_card, bot_difficulty, invalid_message, invalid_until_ms):
    screen.fill(BG_COLOR)

    top_bar, bot_area, player_area, hand_area = ui_rects()

    # Панели
    draw_panel(top_bar, fill=PANEL_COLOR)
    draw_panel(bot_area, fill=PANEL_COLOR_2)
    draw_panel(player_area, fill=PANEL_COLOR_2)
    draw_panel(hand_area, fill=PANEL_COLOR)

    mx, my = pygame.mouse.get_pos()
    pos = (mx, my)

    # === Топ-бар (статус) ===
    vol = settings.get("volume", 0.9)
    muted = settings.get("muted", False)
    sound_label = "Звук: ВЫКЛ" if muted else f"Звук: {int(vol * 100)}%"

    draw_text(f"Колода: {len(deck)}", top_bar.x + 18, top_bar.y + 20, font=SMALL_FONT)
    draw_text(f"Бот: {bot_difficulty.upper()}", top_bar.x + 220, top_bar.y + 20, font=SMALL_FONT)
    draw_text(sound_label, top_bar.x + 420, top_bar.y + 20, font=SMALL_FONT, color=(170, 170, 150))
    draw_text("ЛКМ: ход/выбор   ПКМ: LOCK", top_bar.x + 650, top_bar.y + 20, font=SMALL_FONT, color=(160, 160, 140))

    menu_rect = pygame.Rect(top_bar.right - 100, top_bar.y + 15, 85, 40)
    menu_hover, menu_rect = draw_icon_button("МЕНЮ", menu_rect, pos)

    # === Караваны ===
    bot_cav_rects = caravan_rects(bot_area)
    player_cav_rects = caravan_rects(player_area)

    # Заголовки секций
    draw_text("Караваны бота", bot_area.x + 18, bot_area.y + 14, font=SMALL_FONT)
    draw_text("Ваши караваны", player_area.x + 18, player_area.y + 14, font=SMALL_FONT)
    draw_text("Ваша рука", hand_area.x + 18, hand_area.y + 14, font=SMALL_FONT)

    # Подсветка каравана под мышкой + подсказка валидности (если выбрана карта)
    hovered_side, hovered_idx = get_caravan_side_and_index(pos, bot_cav_rects, player_cav_rects)

    # Рисуем караваны бота
    for i, cav in enumerate(bot["caravans"]):
        cav_rect = bot_cav_rects[i]

        # Контур каравана
        outline_color = BLACK
        if hovered_side == "bot" and hovered_idx == i:
            outline_color = HOVER_OUTLINE

        pygame.draw.rect(screen, (0, 0, 0, 0), cav_rect, border_radius=10)
        pygame.draw.rect(screen, outline_color, cav_rect, 3, border_radius=10)

        # Карты в караване
        for j, card in enumerate(cav["cards"]):
            r = pygame.Rect(cav_rect.x + j * CARAVAN_CARD_OVERLAP, cav_rect.y, CARD_WIDTH, CARD_HEIGHT)
            draw_card(r, card)

        score = caravan_score(cav)
        draw_text(f"Сумма: {score}", cav_rect.x, cav_rect.bottom + 8, font=SMALL_FONT)

        if cav["locked"]:
            draw_locked_overlay(cav_rect)

        # Направление
        if len(cav["cards"]) >= 2 and not cav["locked"]:
            ascending = card_value(cav["cards"][1]) > card_value(cav["cards"][0])
            arrow = "↑" if ascending else "↓"
            draw_text(arrow, cav_rect.right - 26, cav_rect.y - 8, RED, font=TITLE_FONT)

    # Рисуем караваны игрока
    for i, cav in enumerate(player["caravans"]):
        cav_rect = player_cav_rects[i]

        outline_color = BLACK
        if hovered_side == "player" and hovered_idx == i:
            outline_color = HOVER_OUTLINE

        pygame.draw.rect(screen, outline_color, cav_rect, 3, border_radius=10)

        for j, card in enumerate(cav["cards"]):
            r = pygame.Rect(cav_rect.x + j * CARAVAN_CARD_OVERLAP, cav_rect.y, CARD_WIDTH, CARD_HEIGHT)
            draw_card(r, card)

        score = caravan_score(cav)
        draw_text(f"Сумма: {score}", cav_rect.x, cav_rect.bottom + 8, font=SMALL_FONT)

        if cav["locked"]:
            draw_locked_overlay(cav_rect)

        if len(cav["cards"]) >= 2 and not cav["locked"]:
            ascending = card_value(cav["cards"][1]) > card_value(cav["cards"][0])
            arrow = "↑" if ascending else "↓"
            draw_text(arrow, cav_rect.right - 26, cav_rect.y - 8, RED, font=TITLE_FONT)

    # === Рука игрока ===
    hand_rects = hand_card_rects(hand_area, player["hand"], selected_card)
    hovered_hand_idx = get_hand_index_at(pos, hand_rects)

    for i, card in enumerate(player["hand"]):
        draw_card(
            hand_rects[i],
            card,
            selected=(i == selected_card),
            hovered=(i == hovered_hand_idx),
        )

    # === Сообщение об ошибке/подсказка (без стоп-кадра) ===
    now = pygame.time.get_ticks()
    if invalid_message and now < invalid_until_ms:
        # Плашка
        msg_rect = pygame.Rect(hand_area.x + 20, hand_area.bottom - 55, hand_area.width - 40, 40)
        pygame.draw.rect(screen, (35, 20, 20), msg_rect, border_radius=10)
        pygame.draw.rect(screen, BLACK, msg_rect, 3, border_radius=10)
        draw_text_center(invalid_message, msg_rect, RED, font=SMALL_FONT)

    pygame.display.flip()

    return {
        "menu_rect": menu_rect,
        "menu_hover": menu_hover,
        "bot_cav_rects": bot_cav_rects,
        "player_cav_rects": player_cav_rects,
        "hand_rects": hand_rects,
    }


def main_menu():
    while True:
        screen.fill(BG_COLOR)
        top_bar, bot_area, player_area, hand_area = ui_rects()

        # Одну большую панель для меню
        menu_panel = pygame.Rect(WIDTH // 2 - 260, 120, 520, 480)
        draw_panel(menu_panel, fill=PANEL_COLOR)

        draw_text_center("Караван", pygame.Rect(menu_panel.x, menu_panel.y + 20, menu_panel.width, 80), TEXT_COLOR, TITLE_FONT)

        pos = pygame.mouse.get_pos()
        play_hover, _ = draw_button("Играть", menu_panel.x + 160, menu_panel.y + 160, 200, 60, BUTTON_COLOR, BUTTON_HOVER_COLOR, pos)
        settings_hover, _ = draw_button("Настройки", menu_panel.x + 160, menu_panel.y + 240, 200, 60, BUTTON_COLOR, BUTTON_HOVER_COLOR, pos)
        quit_hover, _ = draw_button("Выход", menu_panel.x + 160, menu_panel.y + 320, 200, 60, (120, 40, 40), (180, 60, 60), pos)

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if play_hover:
                    return "play"
                if settings_hover:
                    settings_menu()
                if quit_hover:
                    pygame.quit()
                    sys.exit()

def settings_menu():
    global settings

    volume = float(settings.get("volume", 0.9))
    muted = bool(settings.get("muted", False))

    slider_x = WIDTH // 2 - 220
    slider_y = 330
    slider_width = 440
    slider_height = 10
    handle_radius = 12
    dragging = False

    panel = pygame.Rect(WIDTH // 2 - 320, 140, 640, 440)

    while True:
        screen.fill(BG_COLOR)
        draw_panel(panel, fill=PANEL_COLOR)

        draw_text_center("Настройки", pygame.Rect(panel.x, panel.y + 20, panel.width, 70), TEXT_COLOR, TITLE_FONT)

        pos = pygame.mouse.get_pos()

        # Полоса громкости
        draw_text(f"Громкость: {int(volume * 100)}%", panel.x + 80, slider_y - 45, TEXT_COLOR, font=FONT)
        pygame.draw.rect(screen, (100, 100, 100), (slider_x, slider_y, slider_width, slider_height), border_radius=5)

        handle_x = slider_x + int(volume * slider_width)
        pygame.draw.circle(screen, BUTTON_HOVER_COLOR if dragging else BUTTON_COLOR, (handle_x, slider_y + slider_height // 2), handle_radius)
        pygame.draw.circle(screen, BLACK, (handle_x, slider_y + slider_height // 2), handle_radius, 2)

        # Кнопка выключения звука
        mute_text = "Звук: ВКЛ" if not muted else "Звук: ВЫКЛ"
        mute_hover, _ = draw_button(mute_text, panel.x + 220, panel.y + 250, 200, 55, BUTTON_COLOR, BUTTON_HOVER_COLOR, pos, font=SMALL_FONT)

        # Кнопка "Назад"
        back_hover, _ = draw_button("Назад", panel.x + 220, panel.y + 320, 200, 55, BUTTON_COLOR, BUTTON_HOVER_COLOR, pos, font=SMALL_FONT)

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                settings["volume"] = volume
                settings["muted"] = muted
                save_settings(settings)
                pygame.quit()
                sys.exit()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                if abs(mx - handle_x) <= handle_radius + 4 and abs(my - (slider_y + slider_height // 2)) <= handle_radius + 4:
                    dragging = True
                elif mute_hover:
                    muted = not muted
                    pygame.mixer.music.set_volume(0 if muted else volume)
                    settings["muted"] = muted
                    save_settings(settings)
                elif back_hover:
                    settings["volume"] = volume
                    settings["muted"] = muted
                    save_settings(settings)
                    return

            elif event.type == pygame.MOUSEBUTTONUP:
                dragging = False

            elif event.type == pygame.MOUSEMOTION and dragging:
                mx, _ = event.pos
                mx = max(slider_x, min(slider_x + slider_width, mx))
                volume = (mx - slider_x) / slider_width
                settings["volume"] = volume
                if not muted:
                    pygame.mixer.music.set_volume(volume)
                save_settings(settings)


def difficulty_menu():
    panel = pygame.Rect(WIDTH // 2 - 320, 120, 640, 520)
    while True:
        screen.fill(BG_COLOR)
        draw_panel(panel, fill=PANEL_COLOR)

        draw_text_center("Выберите уровень бота:", pygame.Rect(panel.x, panel.y + 20, panel.width, 70), TEXT_COLOR, font=FONT)

        pos = pygame.mouse.get_pos()

        easy_hover, _ = draw_button("Лёгкий", panel.x + 220, panel.y + 120, 200, 60, BUTTON_COLOR, BUTTON_HOVER_COLOR, pos)
        med_hover, _ = draw_button("Средний", panel.x + 220, panel.y + 200, 200, 60, BUTTON_COLOR, BUTTON_HOVER_COLOR, pos)
        hard_hover, _ = draw_button("Сложный", panel.x + 220, panel.y + 280, 200, 60, BUTTON_COLOR, BUTTON_HOVER_COLOR, pos)
        impossible_hover, _ = draw_button("Невозможно", panel.x + 220, panel.y + 360, 200, 60, RED, (255, 80, 80), pos)

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if easy_hover:
                    return "easy"
                if med_hover:
                    return "medium"
                if hard_hover:
                    return "hard"
                if impossible_hover:
                    return "impossible"


# === Главный цикл игры ===
while True:
    action = main_menu()
    if action != "play":
        continue

    bot_difficulty = difficulty_menu()

    deck = create_deck()
    player = {"caravans": [{"cards": [], "locked": False} for _ in range(3)], "hand": []}
    bot = {"caravans": [{"cards": [], "locked": False} for _ in range(3)], "hand": []}

    draw_cards(player["hand"], deck)
    draw_cards(bot["hand"], deck)

    selected_card = -1
    invalid_move_message = ""
    invalid_until = 0  # ms

    running = True
    while running:
        ui = draw_game(
            player=player,
            bot=bot,
            deck=deck,
            selected_card=selected_card,
            bot_difficulty=bot_difficulty,
            invalid_message=invalid_move_message,
            invalid_until_ms=invalid_until,
        )

        # очистка сообщения после таймера
        if invalid_move_message and pygame.time.get_ticks() >= invalid_until:
            invalid_move_message = ""

        # Победа
        if delivered_caravans(player["caravans"]) >= 2:
            # короткое сообщение, без блокировки на секунды — просто пару кадров
            invalid_move_message = "Победа игрока!"
            invalid_until = pygame.time.get_ticks() + 1600
            draw_game(player, bot, deck, selected_card, bot_difficulty, invalid_move_message, invalid_until)
            pygame.time.wait(900)
            break

        if delivered_caravans(bot["caravans"]) >= 2:
            invalid_move_message = "Победа бота!"
            invalid_until = pygame.time.get_ticks() + 1600
            draw_game(player, bot, deck, selected_card, bot_difficulty, invalid_move_message, invalid_until)
            pygame.time.wait(900)
            break

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                save_settings(settings)
                pygame.quit()
                sys.exit()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                x, y = event.pos

                # Клик по меню
                if ui["menu_rect"].collidepoint(x, y):
                    running = False
                    break

                # Левый клик — выбор карты или попытка сыграть
                if event.button == 1:
                    # 1) выбор карты в руке
                    idx = get_hand_index_at((x, y), ui["hand_rects"])
                    if idx != -1 and idx < len(player["hand"]):
                        selected_card = -1 if selected_card == idx else idx
                        continue

                    # 2) попытка сыграть в караван
                    side, cav_idx = get_caravan_side_and_index((x, y), ui["bot_cav_rects"], ui["player_cav_rects"])
                    if cav_idx != -1 and selected_card != -1:
                        card = player["hand"][selected_card]

                        if card in ["J", "Q", "K"]:
                            # спецкарты: можно на любого
                            target_caravans = bot["caravans"] if side == "bot" else player["caravans"]
                            if play_card(player["hand"], target_caravans, selected_card, cav_idx):
                                selected_card = -1
                                draw_cards(player["hand"], deck)
                                bot_turn(bot, deck, player, difficulty=bot_difficulty)
                            else:
                                invalid_move_message = "Недопустимый ход!"
                                invalid_until = pygame.time.get_ticks() + 1000
                                selected_card = -1
                        else:
                            # обычные: только на свои
                            if side != "player":
                                invalid_move_message = "Нельзя класть обычные карты на караван противника"
                                invalid_until = pygame.time.get_ticks() + 1200
                                selected_card = -1
                            else:
                                if play_card(player["hand"], player["caravans"], selected_card, cav_idx):
                                    selected_card = -1
                                    draw_cards(player["hand"], deck)
                                    bot_turn(bot, deck, player, difficulty=bot_difficulty)
                                else:
                                    invalid_move_message = "Недопустимый ход!"
                                    invalid_until = pygame.time.get_ticks() + 1000
                                    selected_card = -1

                # Правый клик — завершить караван (LOCK) по области каравана игрока
                elif event.button == 3:
                    for i, r in enumerate(ui["player_cav_rects"]):
                        if r.collidepoint(x, y):
                            caravan = player["caravans"][i]
                            if caravan["cards"] and not caravan["locked"]:
                                caravan["locked"] = True
                            break
