import pygame
import random
import sys

# === Настройки ===
settings = {
    "resolution": (1000, 600),
    "fullscreen": True,
    "music_volume": 0.3,
    "effects_volume": 0.5,
}

CARD_WIDTH, CARD_HEIGHT = 60, 90

BG_COLOR = (30, 30, 30)
CARD_COLOR = (60, 60, 60)
CARD_SELECTED_COLOR = (80, 140, 80)
TEXT_COLOR = (200, 200, 180)
BUTTON_COLOR = (50, 90, 50)
BUTTON_HOVER_COLOR = (80, 150, 80)
BUTTON_TEXT_COLOR = (220, 220, 180)
RED = (255, 100, 100)
BLACK = (0, 0, 0)

pygame.init()
pygame.mixer.init()

FONT = pygame.font.SysFont("consolas", 36)
TITLE_FONT = pygame.font.SysFont("consolas", 60, bold=True)

def apply_settings():
    global screen, card_y_player, card_y_bot, caravan_y_player, caravan_y_bot, hand_start_x, caravan_start_x, menu_button_rect, hand_y
    flags = pygame.FULLSCREEN if settings["fullscreen"] else 0
    screen = pygame.display.set_mode(settings["resolution"], flags)
    pygame.mixer.music.set_volume(settings["music_volume"])

    # Пересчёт координат элементов в зависимости от размера экрана
    w, h = settings["resolution"]
    hand_start_x = 50
    hand_y = h - CARD_HEIGHT - 60  # ниже по экрану — рука игрока
    caravan_y_player = h // 2 + 50
    caravan_y_bot = 100
    card_y_player = hand_y
    card_y_bot = caravan_y_bot + CARD_HEIGHT + 20

    # Кнопка меню — справа сверху
    menu_button_rect = pygame.Rect(w - 60, 10, 50, 50)

apply_settings()

pygame.display.set_caption("Караван (Fallout)")

# ... (тут функции draw_text, draw_button, draw_card и т.п. будут использовать новые переменные для позиций) ...

def draw_text(text, x, y, color=TEXT_COLOR, font=FONT):
    img = font.render(text, True, color)
    screen.blit(img, (x, y))

def draw_button(text, x, y, width, height, color, hover_color, pos):
    mx, my = pos
    rect = pygame.Rect(x, y, width, height)
    is_hovered = rect.collidepoint(mx, my)
    pygame.draw.rect(screen, hover_color if is_hovered else color, rect, border_radius=8)
    pygame.draw.rect(screen, BLACK, rect, 3, border_radius=8)
    draw_text(text, x + (width - FONT.size(text)[0]) // 2, y + (height - FONT.get_height()) // 2, BUTTON_TEXT_COLOR)
    return is_hovered, rect

def draw_card(x, y, value, selected=False):
    rect = pygame.Rect(x, y, CARD_WIDTH, CARD_HEIGHT)
    color = CARD_SELECTED_COLOR if selected else CARD_COLOR
    pygame.draw.rect(screen, color, rect, border_radius=6)
    pygame.draw.rect(screen, BLACK, rect, 3, border_radius=6)
    draw_text(str(value), x + 15, y + 30)

def get_card_at(x, y):
    if y < hand_y or y > hand_y + CARD_HEIGHT:
        return -1
    for i in range(8):
        cx = hand_start_x + i * (CARD_WIDTH + 10)
        if cx <= x <= cx + CARD_WIDTH:
            return i
    return -1

def get_caravan_at(x, y, top):
    if not (top <= y <= top + CARD_HEIGHT):
        return -1
    for i in range(3):
        cx = 150 + i * 250
        if cx <= x <= cx + 180:
            return i
    return -1

def create_deck():
    numeric = [str(i) for i in range(2, 11)]
    faces = ['J', 'Q', 'K', 'A']
    deck = (numeric + faces) * 4 * 2
    random.shuffle(deck)
    return deck

def draw_cards(hand, deck, count=8):
    while len(hand) < count and deck:
        hand.append(deck.pop())

def card_value(card):
    if card.isdigit():
        return int(card)
    if card == 'A':
        return 1
    if card in ['J', 'Q', 'K']:
        return 0
    return 0

def is_valid_move(caravan, card):
    if card in ['J', 'Q', 'K']:
        return len(caravan) > 0
    if not caravan:
        return card not in ['J', 'Q', 'K']
    if len(caravan) == 1:
        return card not in ['J', 'Q', 'K']
    ascending = card_value(caravan[1]) > card_value(caravan[0])
    if ascending and card_value(card) > card_value(caravan[-1]):
        return True
    if not ascending and card_value(card) < card_value(caravan[-1]):
        return True
    return False

def play_card(hand, caravans, hand_idx, caravan_idx):
    card = hand[hand_idx]
    target = caravans[caravan_idx]

    if card not in ['J', 'Q', 'K']:
        if is_valid_move(target, card):
            target.append(card)
            del hand[hand_idx]
            return True
        return False

    if card == 'J':
        if target:
            target.pop()
            del hand[hand_idx]
            return True
    elif card == 'Q':
        if len(target) >= 2:
            target[0], target[1] = target[1], target[0]
            del hand[hand_idx]
            return True
    elif card == 'K':
        if target:
            last = target[-1]
            if last.isdigit():
                target[-1] = str(int(last) * 2)
            del hand[hand_idx]
            return True
    return False

def caravan_score(caravan):
    return sum(card_value(c) for c in caravan)

def delivered_caravans(caravans):
    return sum(1 for c in caravans if 21 <= caravan_score(c) <= 26)

def bot_turn(bot, deck):
    draw_cards(bot['hand'], deck)
    hand = bot['hand']

    for i, card in enumerate(hand):
        for j in range(3):
            if is_valid_move(bot['caravans'][j], card):
                play_card(hand, bot['caravans'], i, j)
                return
    if hand:
        hand.pop()

def draw_game(player, bot):
    screen.fill(BG_COLOR)

    draw_text("Караваны бота", 50, 20)
    for i, caravan in enumerate(bot['caravans']):
        x = 150 + i * 250
        for j, card in enumerate(caravan):
            draw_card(x + j * 15, caravan_y_bot, card)
        draw_text(f"Сумма: {caravan_score(caravan)}", x, caravan_y_bot + CARD_HEIGHT + 10)

    draw_text("Ваши караваны", 50, caravan_y_player - 50)
    for i, caravan in enumerate(player['caravans']):
        x = 150 + i * 250
        for j, card in enumerate(caravan):
            draw_card(x + j * 15, caravan_y_player, card)
        draw_text(f"Сумма: {caravan_score(caravan)}", x, caravan_y_player + CARD_HEIGHT + 10)

    draw_text("Ваша рука", hand_start_x, hand_y - 40)
    for i, card in enumerate(player['hand']):
        draw_card(hand_start_x + i * (CARD_WIDTH + 10), hand_y, card, i == selected_card)

    pygame.draw.rect(screen, BUTTON_COLOR, menu_button_rect, border_radius=10)
    pygame.draw.rect(screen, BLACK, menu_button_rect, 3, border_radius=10)
    draw_text("🏠", menu_button_rect.x + 10, menu_button_rect.y + 5, BUTTON_TEXT_COLOR, font=TITLE_FONT)

    pygame.display.flip()
    return menu_button_rect

def main_menu():
    while True:
        screen.fill(BG_COLOR)
        w, h = settings["resolution"]
        draw_text("КАРАВАН", w//2 - 120, 100, TEXT_COLOR, font=TITLE_FONT)

        pos = pygame.mouse.get_pos()
        play_hover, _ = draw_button(" Играть", w//2 - 100, 220, 200, 60, BUTTON_COLOR, BUTTON_HOVER_COLOR, pos)
        settings_hover, _ = draw_button("Настройки", w//2 - 100, 300, 200, 60, BUTTON_COLOR, BUTTON_HOVER_COLOR, pos)
        quit_hover, _ = draw_button(" Выход", w//2 - 100, 380, 200, 60, (120, 40, 40), (180, 60, 60), pos)

        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if play_hover:
                    return 'play'
                if settings_hover:
                    settings_menu()
                if quit_hover:
                    pygame.quit()
                    sys.exit()

def settings_menu():
    resolutions = [(800, 600), (1000, 600), (1280, 720), (1920, 1080)]
    fullscreen = settings["fullscreen"]
    res_idx = resolutions.index(settings["resolution"])
    music_vol = settings["music_volume"]

    running = True
    while running:
        screen.fill(BG_COLOR)
        w, h = settings["resolution"]
        draw_text("Настройки", w//2 - 100, 50, TEXT_COLOR, font=TITLE_FONT)

        pos = pygame.mouse.get_pos()

        draw_text("Разрешение экрана:", 300, 150)
        for i, res in enumerate(resolutions):
            color = BUTTON_HOVER_COLOR if i == res_idx else BUTTON_COLOR
            rect = pygame.Rect(300 + i * 150, 180, 140, 50)
            pygame.draw.rect(screen, color, rect, border_radius=8)
            pygame.draw.rect(screen, BLACK, rect, 3, border_radius=8)
            draw_text(f"{res[0]}x{res[1]}", rect.x + 15, rect.y + 10, BUTTON_TEXT_COLOR)

        fs_text = "Полноэкранный режим: " + ("Вкл" if fullscreen else "Выкл")
        fs_rect = pygame.Rect(300, 260, 250, 50)
        pygame.draw.rect(screen, BUTTON_COLOR, fs_rect, border_radius=8)
        pygame.draw.rect(screen, BLACK, fs_rect, 3, border_radius=8)
        draw_text(fs_text, fs_rect.x + 15, fs_rect.y + 10, BUTTON_TEXT_COLOR)

        draw_text(f"Громкость музыки: {int(music_vol * 100)}%", 300, 340)
        music_dec = pygame.Rect(550, 340, 40, 40)
        music_inc = pygame.Rect(600, 340, 40, 40)
        pygame.draw.rect(screen, BUTTON_COLOR, music_dec, border_radius=8)
        pygame.draw.rect(screen, BUTTON_COLOR, music_inc, border_radius=8)
        pygame.draw.rect(screen, BLACK, music_dec, 3, border_radius=8)
        pygame.draw.rect(screen, BLACK, music_inc, 3, border_radius=8)
        draw_text("-", music_dec.x + 15, music_dec.y + 5, BUTTON_TEXT_COLOR)
        draw_text("+", music_inc.x + 15, music_inc.y + 5, BUTTON_TEXT_COLOR)

        exit_hover, exit_rect = draw_button("Назад", w//2 - 100, 480, 200, 60, BUTTON_COLOR, BUTTON_HOVER_COLOR, pos)

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos

                for i, res in enumerate(resolutions):
                    rect = pygame.Rect(300 + i * 150, 180, 140, 50)
                    if rect.collidepoint(mx, my):
                        res_idx = i
                        settings["resolution"] = resolutions[res_idx]
                        apply_settings()
                        selected_card = -1  # сброс выделения карт
                        break

                if fs_rect.collidepoint(mx, my):
                    fullscreen = not fullscreen
                    settings["fullscreen"] = fullscreen
                    apply_settings()
                    selected_card = -1

                if music_dec.collidepoint(mx, my):
                    music_vol = max(0.0, music_vol - 0.1)
                    settings["music_volume"] = music_vol
                    pygame.mixer.music.set_volume(music_vol)

                if music_inc.collidepoint(mx, my):
                    music_vol = min(1.0, music_vol + 0.1)
                    settings["music_volume"] = music_vol
                    pygame.mixer.music.set_volume(music_vol)

                if exit_rect.collidepoint(mx, my):
                    running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

def game_loop():
    global selected_card

    deck = create_deck()
    player = {"hand": [], "caravans": [[] for _ in range(3)]}
    bot = {"hand": [], "caravans": [[] for _ in range(3)]}
    selected_card = -1

    draw_cards(player["hand"], deck)
    draw_cards(bot["hand"], deck)

    clock = pygame.time.Clock()
    player_turn = True

    while True:
        clock.tick(30)
        menu_rect = draw_game(player, bot)

        pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos

                if menu_rect.collidepoint(mx, my):
                    return

                if player_turn:
                    hand_idx = get_card_at(mx, my)
                    if hand_idx != -1 and hand_idx < len(player["hand"]):
                        selected_card = hand_idx
                    else:
                        caravan_idx = get_caravan_at(mx, my, caravan_y_player)
                        if selected_card != -1 and caravan_idx != -1:
                            if play_card(player["hand"], player["caravans"], selected_card, caravan_idx):
                                selected_card = -1
                                player_turn = False

        if not player_turn:
            bot_turn(bot, deck)
            player_turn = True

        # Пополнение руки игрока и бота после каждого хода
        draw_cards(player["hand"], deck)
        draw_cards(bot["hand"], deck)

        # Проверка победы
        if delivered_caravans(player["caravans"]) >= 3:
            show_message("Вы выиграли!")
            return
        if delivered_caravans(bot["caravans"]) >= 3:
            show_message("Вы проиграли!")
            return

def show_message(message):
    running = True
    while running:
        screen.fill(BG_COLOR)
        w, h = settings["resolution"]
        draw_text(message, w//2 - FONT.size(message)[0]//2, h//2 - 30, RED, font=TITLE_FONT)
        draw_text("Нажмите ESC для выхода в меню", w//2 - 180, h//2 + 40, TEXT_COLOR)
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

selected_card = -1

while True:
    action = main_menu()
    if action == 'play':
        game_loop()
