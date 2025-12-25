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
CARD_COLOR = (60, 60, 60)
CARD_SELECTED_COLOR = (80, 140, 80)
TEXT_COLOR = (200, 200, 180)
BUTTON_COLOR = (50, 90, 50)
BUTTON_HOVER_COLOR = (80, 150, 80)
BUTTON_TEXT_COLOR = (220, 220, 180)
RED = (255, 100, 100)
BLACK = (0, 0, 0)


SETTINGS_FILE = "settings.json"

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    return {"volume": 0.9, "muted": False}

def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f)

pygame.init()
pygame.mixer.init()
settings = load_settings()
pygame.mixer.music.set_volume(0 if settings.get("muted", False) else settings.get("volume", 0.9))

FONT = pygame.font.SysFont("consolas", 36)
TITLE_FONT = pygame.font.SysFont("consolas", 60, bold=True)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Караван (Fallout)")

# Загрузка музыки (нужно иметь файл music/music.mp3)
try:
    pygame.mixer.music.load("music/music.mp3")
    volume = 0 if settings.get("muted", False) else settings.get("volume", 0.9)
    pygame.mixer.music.set_volume(volume)
    pygame.mixer.music.play(-1)
except Exception as e:
    print("Не удалось загрузить музыку. Убедитесь, что файл music/music.mp3 в папке с игрой.")


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
    # Область каравана шире, чтобы можно было кликнуть для завершения
    if not (top <= y <= top + CARD_HEIGHT):
        return -1
    for i in range(3):
        cx = 150 + i * 250
        if cx <= x <= cx + 180:
            return i
    return -1

def get_caravan_side_and_index(x, y):
    # Проверяем, клик по караванам бота
    bot_top = 50
    player_top = 260
    if bot_top <= y <= bot_top + CARD_HEIGHT:
        for i in range(3):
            cx = 150 + i * 250
            if cx <= x <= cx + 180:
                return ('bot', i)
    elif player_top <= y <= player_top + CARD_HEIGHT:
        for i in range(3):
            cx = 150 + i * 250
            if cx <= x <= cx + 180:
                return ('player', i)
    return (None, -1)

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
    # Если караван завершён, то в него нельзя класть карты
    if caravan['locked']:
        return False
    cards = caravan['cards']
    if card in ['J', 'Q', 'K']:
        return len(cards) > 0
    if not cards:
        return card not in ['J', 'Q', 'K']
    if len(cards) == 1:
        return card not in ['J', 'Q', 'K']
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
    if target['locked']:
        return False

    # Обычные карты кладём только в свой караван
    if card not in ['J', 'Q', 'K']:
        if is_valid_move(target, card):
            target['cards'].append(card)
            del hand[hand_idx]
            return True
        return False

    # Спецкарты — могут применяться и к чужим караванам
    if card == 'J':
        if target['cards']:
            target['cards'].pop()
            del hand[hand_idx]
            return True
    elif card == 'Q':
        if len(target['cards']) >= 2:
            target['cards'][0], target['cards'][1] = target['cards'][1], target['cards'][0]
            del hand[hand_idx]
            return True
    elif card == 'K':
        if target['cards']:
            last = target['cards'][-1]
            if last.isdigit():
                target['cards'][-1] = str(int(last) * 2)
            del hand[hand_idx]
            return True
    return False


def caravan_score(caravan):
    return sum(card_value(c) for c in caravan['cards'])

def delivered_caravans(caravans):
    return sum(1 for caravan in caravans if 21 <= caravan_score(caravan) <= 26)

def bot_turn(bot, deck, player=None, difficulty='easy'):
    draw_cards(bot['hand'], deck)
    hand = bot['hand']
    caravans = bot['caravans']

    if difficulty == 'easy':
        for i, card in enumerate(hand):
            for j in range(3):
                if caravans[j]['locked']:
                    continue
                if is_valid_move(caravans[j], card):
                    play_card(hand, caravans, i, j)
                    return
        if hand:
            hand.pop()
        return

    elif difficulty == 'medium':
        best_score = -1000
        best_move = None
        for i, card in enumerate(hand):
            for j in range(3):
                if caravans[j]['locked']:
                    continue
                test_caravan = list(caravans[j]['cards'])
                if card in ['J', 'Q', 'K']:
                    continue  # избегаем спецкарт для среднего уровня
                if is_valid_move({'cards': test_caravan, 'locked': False}, card):
                    test_caravan.append(card)
                    score = caravan_score({'cards': test_caravan})
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

    elif difficulty == 'hard':
        best_score = -1000
        best_move = None

        for i, card in enumerate(hand):
            for j in range(3):
                if caravans[j]['locked']:
                    continue

                # если карта обычная — анализируем полезность
                if card not in ['J', 'Q', 'K']:
                    test_caravan = list(caravans[j]['cards'])
                    if is_valid_move({'cards': test_caravan, 'locked': False}, card):
                        test_caravan.append(card)
                        score = caravan_score({'cards': test_caravan})
                        if 21 <= score <= 26:
                            score += 100  # цель достигнута
                        elif score > 26:
                            score -= 50
                        if score > best_score:
                            best_score = score
                            best_move = (i, j)

                # J: попытка удалить сильную карту игрока
                elif card == 'J':
                    for pi in range(3):
                        pc = player['caravans'][pi]
                        if pc['cards']:
                            last = pc['cards'][-1]
                            if card_value(last) >= 8:
                                play_card(hand, player['caravans'], i, pi)
                                return

                # K: удвоение своей карты, если это приведёт в зону 21–26
                elif card == 'K':
                    if caravans[j]['cards']:
                        test_cards = list(caravans[j]['cards'])
                        last = test_cards[-1]
                        if last.isdigit():
                            new_val = int(last) * 2
                            test_cards[-1] = str(new_val)
                            score = sum(card_value(c) for c in test_cards)
                            if 21 <= score <= 26:
                                play_card(hand, caravans, i, j)
                                return

                # Q: поменять порядок, если 1я карта меньше 2й, а следующая — выше/ниже нужного направления
                elif card == 'Q':
                    if len(caravans[j]['cards']) >= 2:
                        play_card(hand, caravans, i, j)
                        return

        # делаем лучший ход
        if best_move:
            i, j = best_move
            play_card(hand, caravans, i, j)
            return

        # нет хороших ходов — сброс
        if hand:
            hand.pop()
    elif difficulty == 'impossible':
        best_score = -float('inf')
        best_move = None
        # Пробуем все комбинации: карта + караван + цель
        for i, card in enumerate(hand):
            for j in range(3):
                target = caravans[j]
                if target['locked']:
                    continue

                if card not in ['J', 'Q', 'K']:
                    # пробуем обычную карту
                    if is_valid_move(target, card):
                        test = list(target['cards']) + [card]
                        score = caravan_score({'cards': test})
                        if 21 <= score <= 26:
                            score += 1000  # приоритет идеальной зоны
                        elif score > 26:
                            score -= 100
                        else:
                            score += score
                        if score > best_score:
                            best_score = score
                            best_move = ('play', i, j)

                elif card == 'J':
                    # попробуем удалить карту игрока
                    for k in range(3):
                        player_cav = player['caravans'][k]
                        if player_cav['cards']:
                            last = player_cav['cards'][-1]
                            if card_value(last) >= 5:
                                best_move = ('remove', i, k)
                                best_score = 999  # высокий приоритет

                elif card == 'K':
                    if target['cards']:
                        last = target['cards'][-1]
                        if last.isdigit():
                            doubled = int(last) * 2
                            test = list(target['cards'])
                            test[-1] = str(doubled)
                            score = caravan_score({'cards': test})
                            if 21 <= score <= 26:
                                best_move = ('double', i, j)
                                best_score = 1000

                elif card == 'Q':
                    if len(target['cards']) >= 2:
                        best_move = ('swap', i, j)
                        best_score = 10  # небольшое преимущество

        # Выполняем лучший ход
        if best_move:
            move_type, i, j = best_move
            if move_type in ['play', 'double', 'swap']:
                play_card(hand, caravans, i, j)
            elif move_type == 'remove':
                play_card(hand, player['caravans'], i, j)
            return

        # Если нет удачного хода, сбросить карту
        if hand:
            hand.pop()


def draw_game(player, bot, deck):
    screen.fill(BG_COLOR)

    # Отображение оставшихся карт в колоде
    draw_text(f"Колода: {len(deck)}", WIDTH - 200, 100)

    # Караваны бота
    draw_text("Караваны бота", 50, 20)
    for i, caravan in enumerate(bot['caravans']):
        x = 150 + i * 250
        for j, card in enumerate(caravan['cards']):
            draw_card(x + j * 15, 50, card)
        score = caravan_score(caravan)
        draw_text(f"Сумма: {score}", x, 150)
        # Если караван завершён, отображаем надпись
        if caravan['locked']:
            draw_text("LOCKED", x, 180, RED)
        # Если в караване 2+ карты, показываем направление
        if len(caravan['cards']) >= 2 and not caravan['locked']:
            ascending = card_value(caravan['cards'][1]) > card_value(caravan['cards'][0])
            arrow = "↑" if ascending else "↓"
            draw_text(arrow, x + 80, 50, RED, font=TITLE_FONT)

    # Караваны игрока
    draw_text("Ваши караваны", 50, 220)
    for i, caravan in enumerate(player['caravans']):
        x = 150 + i * 250
        for j, card in enumerate(caravan['cards']):
            draw_card(x + j * 15, 260, card)
        score = caravan_score(caravan)
        draw_text(f"Сумма: {score}", x, 360)
        if caravan['locked']:
            draw_text("LOCKED", x, 390, RED)
        if len(caravan['cards']) >= 2 and not caravan['locked']:
            ascending = card_value(caravan['cards'][1]) > card_value(caravan['cards'][0])
            arrow = "↑" if ascending else "↓"
            draw_text(arrow, x + 80, 260, RED, font=TITLE_FONT)

    # Рука игрока
    draw_text("Ваша рука", 50, 450)
    for i, card in enumerate(player['hand']):
        draw_card(50 + i * (CARD_WIDTH + 10), 500, card, i == selected_card)

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
        draw_text("Кортеж", 380, 100, TEXT_COLOR, font=TITLE_FONT)

        pos = pygame.mouse.get_pos()
        play_hover, _ = draw_button("Играть", 400, 220, 200, 60, BUTTON_COLOR, BUTTON_HOVER_COLOR, pos)
        settings_hover, _ = draw_button("Настройки", 400, 300, 200, 60, BUTTON_COLOR, BUTTON_HOVER_COLOR, pos)
        quit_hover, _ = draw_button("Выход", 400, 380, 200, 60, (120, 40, 40), (180, 60, 60), pos)

        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if play_hover: return 'play'
                if settings_hover:
                    settings_menu()
                if quit_hover:
                    pygame.quit()
                    sys.exit()

def settings_menu():
    global settings  # чтобы сохранить обратно

    volume = settings.get("volume", 0.9)
    muted = settings.get("muted", False)

    slider_x = 300
    slider_y = 280
    slider_width = 400
    slider_height = 10
    handle_radius = 12
    dragging = False

    while True:
        screen.fill(BG_COLOR)
        draw_text("Настройки", 320, 180, TEXT_COLOR)

        pos = pygame.mouse.get_pos()

        # Полоса громкости
        draw_text(f"Громкость: {int(volume * 100)}%", slider_x, slider_y - 40, TEXT_COLOR)
        pygame.draw.rect(screen, (100, 100, 100), (slider_x, slider_y, slider_width, slider_height), border_radius=5)
        handle_x = slider_x + int(volume * slider_width)
        pygame.draw.circle(screen, BUTTON_HOVER_COLOR if dragging else BUTTON_COLOR, (handle_x, slider_y + slider_height // 2), handle_radius)

        # Кнопка выключения звука
        mute_text = "Вкл" if muted else "Выкл"
        mute_hover, mute_rect = draw_button(mute_text, 350, 350, 200, 50, BUTTON_COLOR, BUTTON_HOVER_COLOR, pos)

        # Кнопка "Назад"
        back_hover, back_rect = draw_button("Назад", 350, 420, 200, 50, BUTTON_COLOR, BUTTON_HOVER_COLOR, pos)

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                save_settings(settings)
                pygame.quit()
                sys.exit()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                if abs(mx - handle_x) <= handle_radius and abs(my - (slider_y + slider_height // 2)) <= handle_radius:
                    dragging = True
                elif mute_hover:
                    muted = not muted
                    pygame.mixer.music.set_volume(0 if muted else volume)
                    settings['muted'] = muted
                    save_settings(settings)
                elif back_hover:
                    settings['volume'] = volume
                    settings['muted'] = muted
                    save_settings(settings)
                    return

            elif event.type == pygame.MOUSEBUTTONUP:
                dragging = False

            elif event.type == pygame.MOUSEMOTION and dragging:
                mx, _ = event.pos
                mx = max(slider_x, min(slider_x + slider_width, mx))
                volume = (mx - slider_x) / slider_width
                if not muted:
                    pygame.mixer.music.set_volume(volume)



def difficulty_menu():
    while True:
        screen.fill(BG_COLOR)
        draw_text("Выберите уровень бота:", 320, 150, TEXT_COLOR)
        pos = pygame.mouse.get_pos()

        easy_hover, _ = draw_button("Лёгкий", 350, 220, 200, 60, BUTTON_COLOR, BUTTON_HOVER_COLOR, pos)
        med_hover, _ = draw_button("Средний", 350, 300, 200, 60, BUTTON_COLOR, BUTTON_HOVER_COLOR, pos)
        hard_hover, _ = draw_button("Сложный", 350, 380, 200, 60, BUTTON_COLOR, BUTTON_HOVER_COLOR, pos)
        impossible_hover, _ = draw_button("Невозможно", 350, 460, 200, 60, RED, (255, 80, 80), pos)

        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if easy_hover: return 'easy'
                if med_hover: return 'medium'
                if hard_hover: return 'hard'
                if impossible_hover: return 'impossible'


# === Главный цикл игры ===
while True:
    action = main_menu()
    if action != 'play':
        continue

    bot_difficulty = difficulty_menu()

    deck = create_deck()
    # Теперь караваны – это списки словарей с ключами "cards" и "locked"
    player = {'caravans': [{'cards': [], 'locked': False} for _ in range(3)], 'hand': []}
    bot = {'caravans': [{'cards': [], 'locked': False} for _ in range(3)], 'hand': []}
    draw_cards(player['hand'], deck)
    draw_cards(bot['hand'], deck)
    selected_card = -1
    invalid_move_message = ""

    running = True
    while running:
        menu_icon = draw_game(player, bot, deck)
        # Если есть сообщение об ошибке, показываем его на короткое время
        if invalid_move_message:
            draw_text(invalid_move_message, 400, 550, RED)
            pygame.display.flip()
            pygame.time.wait(1000)
            invalid_move_message = ""

        if delivered_caravans(player['caravans']) >= 2:
            draw_text("Победа игрока!", 400, 550, RED)
            pygame.display.flip()
            pygame.time.wait(2000)
            break
        if delivered_caravans(bot['caravans']) >= 2:
            draw_text("Победа бота!", 400, 550, RED)
            pygame.display.flip()
            pygame.time.wait(2000)
            break

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            # Обработка кликов мышью
            elif event.type == pygame.MOUSEBUTTONDOWN:
                x, y = pygame.mouse.get_pos()
                # Клик по кнопке меню
                if menu_icon.collidepoint(x, y):
                    running = False
                    break
                # Левый клик — выбор карты или попытка положить карту
                if event.button == 1:  # Левый клик
                    idx = get_card_at(x, y, 500)
                    if idx != -1 and idx < len(player['hand']):
                        # Выбираем или снимаем выбор карты
                        if selected_card == idx:
                            selected_card = -1
                        else:
                            selected_card = idx
                    else:
                        side, cav_idx = get_caravan_side_and_index(x, y)
                        if cav_idx != -1 and selected_card != -1:
                            card = player['hand'][selected_card]
                            if card in ['J', 'Q', 'K']:
                                # Разрешаем играть спецкарты на чужой или свой караван
                                if side == 'bot':
                                    # Применяем спецкарту на караван бота
                                    if play_card(player['hand'], bot['caravans'], selected_card, cav_idx):
                                        selected_card = -1
                                        draw_cards(player['hand'], deck)
                                        bot_turn(bot, deck, player, difficulty=bot_difficulty)
                                    else:
                                        invalid_move_message = "Недопустимый ход!"
                                elif side == 'player':
                                    # Применяем спецкарту на свой караван
                                    if play_card(player['hand'], player['caravans'], selected_card, cav_idx):
                                        selected_card = -1
                                        draw_cards(player['hand'], deck)
                                        bot_turn(bot, deck, player, difficulty=bot_difficulty)
                                    else:
                                        invalid_move_message = "Недопустимый ход!"
                            else:
                                # Обычная карта — только на свой караван
                                if side == 'player':
                                    if play_card(player['hand'], player['caravans'], selected_card, cav_idx):
                                        selected_card = -1
                                        draw_cards(player['hand'], deck)
                                        bot_turn(bot, deck, player, difficulty=bot_difficulty)
                                    else:
                                        invalid_move_message = "Недопустимый ход!"
                                else:
                                    invalid_move_message = "Нельзя класть обычные карты на караван противника"
                            selected_card = -1


                # Правый клик — попытка завершить караван
                elif event.button == 3:
                    cav = get_caravan_at(x, y, 260)
                    if cav != -1:
                        caravan = player['caravans'][cav]
                        if caravan['cards'] and not caravan['locked']:
                            caravan['locked'] = True
