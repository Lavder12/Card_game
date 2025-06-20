import pygame
import random
import sys

# === Настройки ===
WIDTH, HEIGHT = 1000, 600
CARD_WIDTH, CARD_HEIGHT = 60, 90

# Цвета (темная палитра в стиле Fallout)
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

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Караван (Fallout)")

# Загрузка музыки (нужно иметь файл fallout_theme.mp3 в папке с игрой)
try:
    pygame.mixer.music.load("fallout_theme.mp3")
    pygame.mixer.music.set_volume(0.3)
    pygame.mixer.music.play(-1)
except Exception as e:
    print("Не удалось загрузить музыку. Убедитесь, что файл fallout_theme.mp3 в папке с игрой.")

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

def get_card_at(x, y, cards_y):
    if y < cards_y or y > cards_y + CARD_HEIGHT:
        return -1
    for i in range(8):
        cx = 50 + i * (CARD_WIDTH + 10)
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
            draw_card(x + j * 15, 50, card)
        draw_text(f"Сумма: {caravan_score(caravan)}", x, 150)

    draw_text("Ваши караваны", 50, 200)
    for i, caravan in enumerate(player['caravans']):
        x = 150 + i * 250
        for j, card in enumerate(caravan):
            draw_card(x + j * 15, 230, card)
        draw_text(f"Сумма: {caravan_score(caravan)}", x, 330)

    draw_text("Ваша рука", 50, 400)
    for i, card in enumerate(player['hand']):
        draw_card(50 + i * (CARD_WIDTH + 10), 430, card, i == selected_card)

    # Кнопка меню
    menu_rect = pygame.Rect(WIDTH - 60, 10, 50, 50)
    pygame.draw.rect(screen, BUTTON_COLOR, menu_rect, border_radius=10)
    pygame.draw.rect(screen, BLACK, menu_rect, 3, border_radius=10)
    draw_text("🏠", WIDTH - 48, 15, BUTTON_TEXT_COLOR, font=TITLE_FONT)

    pygame.display.flip()
    return menu_rect

def main_menu():
    while True:
        screen.fill(BG_COLOR)
        draw_text("КАРАВАН", 380, 100, TEXT_COLOR, font=TITLE_FONT)

        pos = pygame.mouse.get_pos()
        play_hover, _ = draw_button("▶ Играть", 400, 220, 200, 60, BUTTON_COLOR, BUTTON_HOVER_COLOR, pos)
        settings_hover, _ = draw_button("⚙ Настройки", 400, 300, 200, 60, BUTTON_COLOR, BUTTON_HOVER_COLOR, pos)
        quit_hover, _ = draw_button("❌ Выход", 400, 380, 200, 60, (120, 40, 40), (180, 60, 60), pos)

        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if play_hover: return 'play'
                if settings_hover: settings_menu()
                if quit_hover:
                    pygame.quit()
                    sys.exit()

def settings_menu():
    while True:
        screen.fill(BG_COLOR)
        draw_text("⚙ Настройки (заглушка)", 320, 250, TEXT_COLOR)
        draw_text("Нажмите любую клавишу или клик для возврата", 220, 320, TEXT_COLOR)
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                return

def difficulty_menu():
    while True:
        screen.fill(BG_COLOR)
        draw_text("Выберите уровень бота:", 320, 150, TEXT_COLOR)
        pos = pygame.mouse.get_pos()

        easy_hover, _ = draw_button("Лёгкий", 350, 220, 200, 60, BUTTON_COLOR, BUTTON_HOVER_COLOR, pos)
        med_hover, _ = draw_button("Средний", 350, 300, 200, 60, BUTTON_COLOR, BUTTON_HOVER_COLOR, pos)
        hard_hover, _ = draw_button("Сложный", 350, 380, 200, 60, BUTTON_COLOR, BUTTON_HOVER_COLOR, pos)

        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if easy_hover: return 'easy'
                if med_hover: return 'medium'
                if hard_hover: return 'hard'

# === Главный цикл игры ===
while True:
    action = main_menu()
    if action != 'play':
        continue

    bot_difficulty = difficulty_menu()

    deck = create_deck()
    player = {'caravans': [[] for _ in range(3)], 'hand': []}
    bot = {'caravans': [[] for _ in range(3)], 'hand': []}
    draw_cards(player['hand'], deck)
    draw_cards(bot['hand'], deck)
    selected_card = -1

    running = True
    while running:
        menu_icon = draw_game(player, bot)

        if delivered_caravans(player['caravans']) >= 2:
            draw_text("🎉 Победа игрока!", 400, 550, RED)
            pygame.display.flip()
            pygame.time.wait(2000)
            break
        if delivered_caravans(bot['caravans']) >= 2:
            draw_text("🤖 Победа бота!", 400, 550, RED)
            pygame.display.flip()
            pygame.time.wait(2000)
            break

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                x, y = pygame.mouse.get_pos()
                if menu_icon.collidepoint(x, y):
                    running = False
                    break
                if selected_card == -1:
                    idx = get_card_at(x, y, 430)
                    if 0 <= idx < len(player['hand']):
                        selected_card = idx
                else:
                    cav = get_caravan_at(x, y, 230)
                    if cav != -1:
                        if play_card(player['hand'], player['caravans'], selected_card, cav):
                            draw_cards(player['hand'], deck)
                            bot_turn(bot, deck)
                        selected_card = -1
