import sys
import os
import random
import copy
import json
import math
import pygame
from typing import List, Tuple, Optional, Dict, Any
import src.state as state
from src.security import secure_save, secure_load

class _FontProxy:
    def __init__(self, name):
        self._name = name
    def __getattr__(self, attr):
        return getattr(getattr(state, self._name), attr)
    def render(self, *args, **kwargs):
        return getattr(state, self._name).render(*args, **kwargs)
    def get_height(self, *args, **kwargs):
        return getattr(state, self._name).get_height(*args, **kwargs)
    def size(self, *args, **kwargs):
        return getattr(state, self._name).size(*args, **kwargs)

FONT = _FontProxy("FONT")
SMALL = _FontProxy("SMALL")
TINY = _FontProxy("TINY")
TITLE = _FontProxy("TITLE")
from src.config import (
    T, WIDTH, HEIGHT, FPS, GM_NORMAL, GM_HOT_SEAT, GM_TIMED, GM_TOURNAMENT, RESOLUTIONS, SETTINGS_FILE,
    DECK_FILE, STATS_FILE, HISTORY_FILE, ACH_FILE, CAMPAIGN_FILE, MUSIC_PATH, CARDS_DIR, BACKGROUND_DIR,
    MENU_BG_PATH, TABLE_BG_PATH, MENU_TILE_DIR, USE_ART, ART_DEBUG, ACCENT, TEXT, TEXT_DIM, YELLOW, RED,
    OUT_OK, OUT_BAD, BTN, BTN_H, PANEL_BORD, CAPS_CLR, TIMER_OK, TIMER_WARN, TIMER_CRIT, UNDO_CLR,
    CARD_FACE, CARD_BLACK, CARD_RED, CARD_JOKER,
    RES_ACTIVE, RES_ACT_H, ACH_BG, ACH_BORD, _BASE_CARD_W, _BASE_CARD_H, _BASE_W, _BASE_H,
    STALEMATE_THRESHOLD, TIMED_TURN_MS, HAND_OPENING_SIZE, HAND_TARGET_SIZE, UNDO_LEVELS,
    load_history, add_history, rpath, wpath, clamp, format_time_ms
)
from src.models import (
    Card, NumEntry, Caravan, PlayerState, BotPersonality, PERSONALITIES, DEFAULT_PERSONALITY,
    standard_card_list, load_deck_selection, save_deck_selection, build_deck_from_selection,
    ensure_min30_selection, draw_to_hand, discard_hand_card, disband_caravan, play_number,
    play_picture, check_game_end, slot_outcome, take_snapshot, restore_snapshot, bot_opening_play,
    get_bot_delay_ms
)
from src.achievements import (
    ACH_IDS, load_achievements, save_achievements, unlock_achievement,
    check_post_match_achievements, tick_achievement_popup
)
from src.bot import bot_take_turn
from src.ui import (
    apply_resolution, draw_ui_background, draw_main_menu_background, draw_panel, draw_panel_title_bar, draw_text_center,
    draw_button, draw_minimal_chip, draw_text, draw_board, ui_rects, caravan_slots,
    build_entry_hitboxes, get_idx_at, trigger_shake, wrap_text, lighten,
    draw_history_map, draw_map_node, draw_map_tooltip
)

clock = pygame.time.Clock()

def pause_menu(allow_undo=False) -> str:
    screen = state.screen
    WIDTH = state.WIDTH
    HEIGHT = state.HEIGHT
    backdrop = screen.copy()
    dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    dim.fill((0, 0, 0, 150))
    pygame.event.clear()
    while True:
        clock.tick(FPS)
        pw, ph = min(440, WIDTH - 40), min(480, HEIGHT - 80)
        panel = pygame.Rect(WIDTH // 2 - pw // 2, HEIGHT // 2 - ph // 2, pw, ph)
        screen.blit(backdrop, (0, 0))
        screen.blit(dim, (0, 0))
        draw_panel(panel, glow=True)
        draw_panel_title_bar(panel, "PAUSE" if state.language == "en" else "ПАУЗА")
        draw_text_center("PAUSE" if state.language == "en" else "ПАУЗА",
                         pygame.Rect(panel.x, panel.y + 8, pw, 52), ACCENT, state.TITLE)
        pygame.draw.line(screen, PANEL_BORD, (panel.x + 30, panel.y + 64), (panel.right - 30, panel.y + 64), 1)
        pos = pygame.mouse.get_pos()
        bw, bh = max(200, int(pw * 0.60)), 54
        bx = panel.x + (pw - bw) // 2
        r_lbl = "▶  Resume" if state.language == "en" else "▶  Продолжить"
        s_lbl = "⚙  Settings" if state.language == "en" else "⚙  Настройки"
        q_lbl = "✕  Leave match" if state.language == "en" else "✕  Выйти из матча"
        row1 = panel.y + int(ph * 0.30)
        row2 = panel.y + int(ph * 0.47)
        row3 = panel.y + int(ph * 0.64)
        r_rect = pygame.Rect(bx, row1, bw, bh)
        s_rect = pygame.Rect(bx, row2, bw, bh)
        q_rect = pygame.Rect(bx, row3, bw, bh)
        draw_button(r_lbl, r_rect, pos, BTN, BTN_H)
        draw_button(s_lbl, s_rect, pos, BTN, BTN_H)
        draw_button(q_lbl, q_rect, pos, (100, 28, 28), lighten((100, 28, 28), 30))
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                if state.app_settings: state.app_settings.save()
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                return "resume"
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if r_rect.collidepoint(e.pos): return "resume"
                if s_rect.collidepoint(e.pos):
                    settings_menu()
                    return "resume"
                if q_rect.collidepoint(e.pos): return "quit_match"


def settings_menu():
    screen = state.screen
    WIDTH = state.WIDTH
    HEIGHT = state.HEIGHT
    app_settings = state.app_settings

    volume = app_settings.volume
    sfx_vol = app_settings.sfx_volume
    muted = app_settings.muted
    bot_use = app_settings.bot_uses_player_deck
    drag_music = False
    drag_sfx = False
    pygame.event.clear()

    def _ru():
        return state.language == "ru"

    def _draw_section(title, rect):
        surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        pygame.draw.rect(surf, (12, 24, 18, 130), pygame.Rect(0, 0, rect.w, rect.h), border_radius=12)
        pygame.draw.rect(surf, (120, 98, 58, 140), pygame.Rect(0, 0, rect.w, rect.h), 1, border_radius=12)
        screen.blit(surf, rect.topleft)
        label = pygame.Rect(rect.x + 16, rect.y - 14, min(220, rect.w - 32), 28)
        ls = pygame.Surface((label.w, label.h), pygame.SRCALPHA)
        pygame.draw.rect(ls, (58, 48, 24, 220), pygame.Rect(0, 0, label.w, label.h), border_radius=8)
        pygame.draw.rect(ls, (168, 134, 68, 160), pygame.Rect(0, 0, label.w, label.h), 1, border_radius=8)
        screen.blit(ls, label.topleft)
        draw_text_center(title, label, ACCENT, TINY)

    def _draw_slider(label, val, rect, dragging=False):
        draw_text(label, rect.x, rect.y - 26, TEXT, SMALL)
        draw_text(f"{int(val*100)}%", rect.right - 52, rect.y - 26, ACCENT, SMALL)
        bar = pygame.Rect(rect.x + 6, rect.y + 10, rect.w - 12, 12)
        pygame.draw.rect(screen, (14, 18, 12), bar, border_radius=8)
        pygame.draw.rect(screen, (64, 104, 62), pygame.Rect(bar.x, bar.y, max(3, int(bar.w * val)), bar.h), border_radius=8)
        pygame.draw.rect(screen, (174, 135, 72), bar, 1, border_radius=8)
        hx = bar.x + int(bar.w * val)
        hy = bar.centery
        pygame.draw.circle(screen, (10, 8, 6), (hx + 1, hy + 2), 13)
        pygame.draw.circle(screen, (94, 145, 84) if dragging else (76, 119, 69), (hx, hy), 11)
        return bar

    def _fit_font(label, width):
        return SMALL if SMALL.render(label, True, TEXT).get_width() <= width - 20 else TINY

    def _draw_wide_button(label, rect, pos, active=False):
        hov = draw_button(label, rect, pos, BTN if not active else (86, 97, 57), BTN_H if not active else (110, 122, 74), font=_fit_font(label, rect.w))
        return hov

    while True:
        clock.tick(FPS)
        screen = state.screen
        WIDTH = state.WIDTH
        HEIGHT = state.HEIGHT
        draw_ui_background()
        pos = pygame.mouse.get_pos()

        pw, ph = min(980, WIDTH - 44), min(650, HEIGHT - 34)
        panel = pygame.Rect(WIDTH // 2 - pw // 2, HEIGHT // 2 - ph // 2, pw, ph)
        draw_panel(panel, glow=True)
        draw_panel_title_bar(panel, T("settings_title"))
        draw_text_center(T("settings_title"), pygame.Rect(panel.x, panel.y + 8, pw, 52), ACCENT, TITLE)

        left = pygame.Rect(panel.x + 26, panel.y + 94, (pw - 78) // 2, ph - 170)
        right = pygame.Rect(left.right + 26, panel.y + 94, (pw - 78) // 2, ph - 170)

        sound_rect = pygame.Rect(left.x, left.y, left.w, 162)
        screen_rect = pygame.Rect(left.x, sound_rect.bottom + 44, left.w, 132)
        game_rect = pygame.Rect(right.x, right.y, right.w, 226)
        profile_rect = pygame.Rect(right.x, game_rect.bottom + 44, right.w, 140)

        _draw_section("ЗВУК" if _ru() else "SOUND", sound_rect)
        _draw_section("ЭКРАН" if _ru() else "SCREEN", screen_rect)
        _draw_section("ИГРА" if _ru() else "GAME", game_rect)
        _draw_section("ПРОФИЛЬ" if _ru() else "PROFILE", profile_rect)

        music_slider = _draw_slider("Музыка" if _ru() else "Music", volume, pygame.Rect(sound_rect.x + 22, sound_rect.y + 56, sound_rect.w - 44, 32), drag_music)
        sfx_slider   = _draw_slider("Эффекты" if _ru() else "SFX", sfx_vol, pygame.Rect(sound_rect.x + 22, sound_rect.y + 118, sound_rect.w - 44, 32), drag_sfx)

        rb_gap = 12
        rbw = (screen_rect.w - 56 - rb_gap) // 2
        rbh = 40
        res_rects = []
        rx = screen_rect.x + 22
        ry = screen_rect.y + 44
        for i, (rw2, rh2, rlabel) in enumerate(RESOLUTIONS):
            row = i // 2
            col = i % 2
            rr = pygame.Rect(rx + col * (rbw + rb_gap), ry + row * (rbh + 10), rbw, rbh)
            is_active = (app_settings.resolution == f"{rw2}x{rh2}")
            _draw_wide_button(rlabel, rr, pos, is_active)
            res_rects.append((rr, rw2, rh2))

        gx = game_rect.x + 22
        gw = game_rect.w - 44
        btn_h = 42
        gap = 10
        sound_label = ("Звук: ВЫКЛ" if muted else "Звук: ВКЛ") if _ru() else ("Sound: OFF" if muted else "Sound: ON")
        bot_label = ("Бот использует вашу колоду: ДА" if bot_use else "Бот использует вашу колоду: НЕТ") if _ru() else ("Bot uses your deck: YES" if bot_use else "Bot uses your deck: NO")
        lang_label = ("Язык: Русский" if _ru() else "Language: English")
        fs_label = ("Полный экран: ВКЛ" if app_settings.fullscreen else "Полный экран: ВЫКЛ") if _ru() else ("Fullscreen: ON" if app_settings.fullscreen else "Fullscreen: OFF")
        mut_r = pygame.Rect(gx, game_rect.y + 40, gw, btn_h)
        bot_r = pygame.Rect(gx, mut_r.bottom + gap, gw, btn_h)
        lng_r = pygame.Rect(gx, bot_r.bottom + gap, gw, btn_h)
        fsr   = pygame.Rect(gx, lng_r.bottom + gap, gw, btn_h)
        _draw_wide_button(sound_label, mut_r, pos, not muted)
        _draw_wide_button(bot_label, bot_r, pos, bot_use)
        _draw_wide_button(lang_label, lng_r, pos, True)
        _draw_wide_button(fs_label, fsr, pos, app_settings.fullscreen)

        name_label = (f"Имя игрока: {app_settings.player_name}" if _ru() else f"Player name: {app_settings.player_name}")
        name_r = pygame.Rect(profile_rect.x + 22, profile_rect.y + 28, profile_rect.w - 44, 42)
        _draw_wide_button(name_label, name_r, pos, False)

        restore_label = ("Восстановить профиль (Облако)" if _ru() else "Restore Profile (Cloud)")
        restore_r = pygame.Rect(profile_rect.x + 22, name_r.bottom + 10, profile_rect.w - 44, 42)
        _draw_wide_button(restore_label, restore_r, pos, False)

        back_r = pygame.Rect(panel.centerx - 110, panel.bottom - 54, 220, 42)
        draw_button(T("back"), back_r, pos, font=SMALL)
        stat_text = f"W:{state.app_stats.wins}  L:{state.app_stats.losses}  D:{state.app_stats.draws}  streak:{state.app_stats.win_streak}"
        draw_text_center(stat_text, pygame.Rect(panel.x + 20, panel.bottom - 28, panel.w - 40, 20), TEXT_DIM, TINY)
        pygame.display.flip()

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                app_settings.save()
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                app_settings.volume = volume
                app_settings.sfx_volume = sfx_vol
                app_settings.muted = muted
                app_settings.bot_uses_player_deck = bot_use
                app_settings.save()
                return
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if music_slider.inflate(24, 24).collidepoint(e.pos):
                    drag_music = True
                    volume = max(0.0, min(1.0, (e.pos[0] - music_slider.x) / music_slider.w))
                    app_settings.volume = volume
                    if state.AUDIO_OK and not muted: pygame.mixer.music.set_volume(volume)
                elif sfx_slider.inflate(24, 24).collidepoint(e.pos):
                    drag_sfx = True
                    sfx_vol = max(0.0, min(1.0, (e.pos[0] - sfx_slider.x) / sfx_slider.w))
                    app_settings.sfx_volume = sfx_vol
                elif mut_r.collidepoint(e.pos):
                    muted = not muted
                    app_settings.muted = muted
                    app_settings.apply_audio()
                    app_settings.save()
                elif bot_r.collidepoint(e.pos):
                    bot_use = not bot_use
                    app_settings.bot_uses_player_deck = bot_use
                    app_settings.save()
                elif lng_r.collidepoint(e.pos):
                    app_settings.language = "ru" if app_settings.language == "en" else "en"
                    app_settings.apply_language()
                    app_settings.save()
                elif fsr.collidepoint(e.pos):
                    app_settings.fullscreen = not app_settings.fullscreen
                    app_settings.save()
                    apply_resolution(*map(int, app_settings.resolution.split("x")), fullscreen=app_settings.fullscreen)
                elif name_r.collidepoint(e.pos):
                    app_settings.player_name = name_input_screen(app_settings.player_name)
                    app_settings.save()
                elif restore_r.collidepoint(e.pos):
                    restore_profile_input_screen()
                    volume = app_settings.volume
                    sfx_vol = app_settings.sfx_volume
                    muted = app_settings.muted
                    bot_use = app_settings.bot_uses_player_deck
                elif back_r.collidepoint(e.pos):
                    app_settings.volume = volume
                    app_settings.sfx_volume = sfx_vol
                    app_settings.muted = muted
                    app_settings.bot_uses_player_deck = bot_use
                    app_settings.save()
                    return
                else:
                    for rr, rw2, rh2 in res_rects:
                        if rr.collidepoint(e.pos):
                            new_key = f"{rw2}x{rh2}"
                            if app_settings.resolution != new_key:
                                app_settings.resolution = new_key
                                app_settings.save()
                                apply_resolution(rw2, rh2, fullscreen=app_settings.fullscreen)
                            break
            if e.type == pygame.MOUSEBUTTONUP:
                drag_music = False
                drag_sfx = False
                app_settings.volume = volume
                app_settings.sfx_volume = sfx_vol
                app_settings.save()
            if e.type == pygame.MOUSEMOTION:
                if drag_music:
                    volume = max(0.0, min(1.0, (e.pos[0] - music_slider.x) / music_slider.w))
                    app_settings.volume = volume
                    if state.AUDIO_OK and not muted: pygame.mixer.music.set_volume(volume)
                if drag_sfx:
                    sfx_vol = max(0.0, min(1.0, (e.pos[0] - sfx_slider.x) / sfx_slider.w))
                    app_settings.sfx_volume = sfx_vol


def mode_select_menu() -> Optional[str]:
    WIDTH = state.WIDTH
    HEIGHT = state.HEIGHT
    pygame.event.clear()
    while True:
        clock.tick(FPS)
        pw, ph = min(560, WIDTH - 40), min(520, HEIGHT - 80)
        panel = pygame.Rect(WIDTH // 2 - pw // 2, HEIGHT // 2 - ph // 2, pw, ph)
        draw_ui_background()
        draw_panel(panel)
        draw_panel_title_bar(panel, T("mode_title"))
        draw_text_center(T("mode_title"), pygame.Rect(panel.x, panel.y + 8, pw, 52), ACCENT, state.TITLE)
        pos = pygame.mouse.get_pos()
        bw, bh = max(240, int(pw * 0.60)), 56
        bx = panel.x + (pw - bw) // 2
        modes = [
            (GM_NORMAL, T("mode_normal"), BTN, BTN_H),
            (GM_HOT_SEAT, T("mode_hotSeat"), BTN, BTN_H),
            (GM_TIMED, T("mode_timed"), BTN, BTN_H),
            (GM_TOURNAMENT, T("mode_tournament"), (70, 50, 20), (110, 80, 30)),
            ("campaign", "🗺 Dusty Tract" if state.language == "en" else "🗺 Пыльный тракт", (92, 68, 44), (126, 92, 58)),
            ("spectator", "👁 AI vs AI" if state.language == "en" else "👁 Бот vs Бот", (50, 40, 70), (80, 60, 110)),
            ("network", "🌐 Network (LAN/Hamachi)" if state.language == "en" else "🌐 Сеть (LAN/Hamachi)", (30, 60, 90), (50, 90, 130))
        ]
        mode_rects = []
        for ii, (key, lbl, col, hcol) in enumerate(modes):
            r = pygame.Rect(bx, panel.y + int(ph * (0.22 + ii * 0.117)), bw, bh)
            mode_rects.append((r, key))
            draw_button(lbl, r, pos, col, hcol)
        back_r = pygame.Rect(bx, panel.bottom - 58, bw, 44)
        draw_button(T("back"), back_r, pos, font=SMALL)
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                if state.app_settings: state.app_settings.save()
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE: return None
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                for r, key in mode_rects:
                    if r.collidepoint(e.pos): return key
                if back_r.collidepoint(e.pos): return None


def personality_select_menu() -> str:
    WIDTH = state.WIDTH
    HEIGHT = state.HEIGHT
    keys = list(PERSONALITIES.keys())
    pygame.event.clear()
    while True:
        clock.tick(FPS)
        pw, ph = min(560, WIDTH - 40), min(460, HEIGHT - 80)
        panel = pygame.Rect(WIDTH // 2 - pw // 2, HEIGHT // 2 - ph // 2, pw, ph)
        draw_ui_background()
        draw_panel(panel)
        draw_panel_title_bar(panel, T("choose_bot"))
        draw_text_center(T("choose_bot"), pygame.Rect(panel.x, panel.y + 8, pw, 52), ACCENT, state.TITLE)
        pos = pygame.mouse.get_pos()
        bw, bh = max(240, int(pw * 0.60)), 56
        bx = panel.x + (pw - bw) // 2
        pers_rects = []
        for ii, pk in enumerate(keys):
            pers = PERSONALITIES[pk]
            r = pygame.Rect(bx, panel.y + int(ph * (0.28 + ii * 0.19)), bw, bh)
            pers_rects.append((r, pk))
            draw_button(T(pers.display_key), r, pos)
        back_r = pygame.Rect(bx, panel.bottom - 58, bw, 44)
        draw_button(T("back"), back_r, pos, font=SMALL)
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                if state.app_settings: state.app_settings.save()
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE: return None
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                for r, pk in pers_rects:
                    if r.collidepoint(e.pos): return pk
                if back_r.collidepoint(e.pos): return None


def difficulty_menu() -> Optional[str]:
    WIDTH = state.WIDTH
    HEIGHT = state.HEIGHT
    pygame.event.clear()
    while True:
        clock.tick(FPS)
        pw, ph = min(560, WIDTH - 40), min(520, HEIGHT - 80)
        panel = pygame.Rect(WIDTH // 2 - pw // 2, HEIGHT // 2 - ph // 2, pw, ph)
        draw_ui_background()
        draw_panel(panel)
        draw_panel_title_bar(panel, T("diff_title"))
        draw_text_center(T("diff_title"), pygame.Rect(panel.x, panel.y + 8, pw, 52), ACCENT, state.TITLE)
        pos = pygame.mouse.get_pos()
        bw, bh = max(220, int(pw * 0.52)), 56
        bx = panel.x + (pw - bw) // 2
        diffs = [
            ("easy", BTN, BTN_H), ("medium", BTN, BTN_H),
            ("hard", (100, 28, 28), lighten((100, 28, 28), 30))
        ]
        diff_rects = []
        for ii, (key, col, hcol) in enumerate(diffs):
            r = pygame.Rect(bx, panel.y + int(ph * (0.30 + ii * 0.18)), bw, bh)
            diff_rects.append((r, "impossible" if key == "hard" else key))
            draw_button(T(key), r, pos, col, hcol)
        back_r = pygame.Rect(bx, panel.bottom - 58, bw, 44)
        draw_button(T("back"), back_r, pos, font=SMALL)
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                if state.app_settings: state.app_settings.save()
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE: return None
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                for r, key in diff_rects:
                    if r.collidepoint(e.pos): return key
                if back_r.collidepoint(e.pos): return None


def betting_menu(diff: str) -> int:
    screen = state.screen
    WIDTH = state.WIDTH
    HEIGHT = state.HEIGHT
    MIN_BET = 50
    MAX_BET = min(state.app_settings.caps, 500)
    STEP = 50
    if MAX_BET < MIN_BET: return 0
    bet = MIN_BET
    pygame.event.clear()
    while True:
        clock.tick(FPS)
        pw, ph = min(560, WIDTH - 40), min(420, HEIGHT - 80)
        panel = pygame.Rect(WIDTH // 2 - pw // 2, HEIGHT // 2 - ph // 2, pw, ph)
        draw_ui_background()
        draw_panel(panel)
        draw_panel_title_bar(panel, T("betting_title"))
        
        # Title
        draw_text_center(T("betting_title"), pygame.Rect(panel.x, panel.y + 12, pw, 46), ACCENT, state.TITLE)
        
        # Fancy separator
        sep_y = panel.y + 68
        pygame.draw.line(screen, ACCENT, (panel.x + 40, sep_y), (panel.right - 40, sep_y), 2)
        pygame.draw.line(screen, PANEL_BORD, (panel.x + 20, sep_y + 3), (panel.right - 20, sep_y + 3), 1)

        content_y = sep_y + 20
        draw_text_center(T("caps_balance", state.app_settings.caps), pygame.Rect(panel.x, content_y, pw, 30), CAPS_CLR, state.FONT)
        
        content_y += 45
        draw_text_center(T("bet_amount", bet), pygame.Rect(panel.x, content_y, pw, 40), TEXT, state.TITLE)
        
        mults = {"easy": 1.0, "medium": 1.2, "hard": 1.5, "impossible": 2.0}
        m = mults.get(diff, 1.0)
        win_amt = int(bet * m)
        info = f"+{win_amt} caps on win  |  -{bet} on loss"
        
        content_y += 45
        draw_text_center(info, pygame.Rect(panel.x, content_y, pw, 26), TEXT_DIM, state.SMALL)
        
        pos = pygame.mouse.get_pos()
        
        # Layout buttons: [ - ] [ Confirm ] [ + ]
        btn_w = 220
        btn_h = 56
        bw = 64
        bh = 50
        
        mid_y = content_y + 50
        
        cf_r = pygame.Rect(panel.x + (pw - btn_w) // 2, mid_y, btn_w, btn_h)
        dn_r = pygame.Rect(cf_r.left - bw - 20, mid_y + (btn_h - bh) // 2, bw, bh)
        up_r = pygame.Rect(cf_r.right + 20, mid_y + (btn_h - bh) // 2, bw, bh)
        
        sk_r = pygame.Rect(panel.x + (pw - 180) // 2, panel.bottom - 74, 180, 50)
        
        draw_button("−", dn_r, pos, font=state.TITLE)
        draw_button("+", up_r, pos, font=state.TITLE)
        draw_button(T("bet_confirm"), cf_r, pos, BTN, BTN_H)
        draw_button(T("back"), sk_r, pos, (70, 70, 70), lighten((70, 70, 70), 20), state.SMALL)
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                if state.app_settings: state.app_settings.save()
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE: return None
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if dn_r.collidepoint(e.pos): bet = max(MIN_BET, bet - STEP)
                elif up_r.collidepoint(e.pos): bet = min(MAX_BET, bet + STEP)
                elif cf_r.collidepoint(e.pos): return bet
                elif sk_r.collidepoint(e.pos): return None


def stats_screen():
    WIDTH = state.WIDTH
    HEIGHT = state.HEIGHT
    pygame.event.clear()
    screen = state.screen
    while True:
        clock.tick(FPS)
        pw, ph = min(620, WIDTH - 40), min(480, HEIGHT - 80)
        panel = pygame.Rect(WIDTH // 2 - pw // 2, HEIGHT // 2 - ph // 2, pw, ph)
        draw_ui_background()
        draw_panel(panel)
        draw_panel_title_bar(panel, T("stats_title"))
        draw_text_center(T("stats_title"), pygame.Rect(panel.x, panel.y + 8, pw, 52), ACCENT, state.TITLE)
        pos = pygame.mouse.get_pos()
        lines = [
            T("games_played", state.app_stats.games_played),
            T("wins_line", state.app_stats.wins),
            T("losses_line", state.app_stats.losses),
            T("draws_line", state.app_stats.draws),
            T("avg_time_line", state.app_stats.avg_time_str()),
            T("streak_line", state.app_stats.best_streak),
            T("caps_line", state.app_settings.caps)
        ]
        row_h = max(32, int(38 * HEIGHT / 720))
        for ii, l in enumerate(lines):
            if ii % 2 == 0:
                rr = pygame.Rect(panel.x + 12, panel.y + 106 + ii * row_h, pw - 24, row_h - 4)
                rs = pygame.Surface((rr.w, rr.h), pygame.SRCALPHA)
                rs.fill((40, 65, 42, 80))
                screen.blit(rs, rr.topleft)
            draw_text(l, panel.x + 50, panel.y + 112 + ii * row_h, TEXT, state.FONT)
        bw = max(140, int(pw * 0.32))
        reset_r = pygame.Rect(panel.x + int(pw * 0.10), panel.bottom - 66, bw, 50)
        back_r = pygame.Rect(panel.x + int(pw * 0.58), panel.bottom - 66, bw, 50)
        draw_button(T("reset_stats"), reset_r, pos, (100, 28, 28), lighten((100, 28, 28), 30), SMALL)
        draw_button(T("back"), back_r, pos, font=SMALL)
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                if state.app_settings: state.app_settings.save()
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE: return
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if reset_r.collidepoint(e.pos):
                    state.app_stats.__init__()
                    state.app_stats.save()
                if back_r.collidepoint(e.pos): return


def achievements_screen():
    WIDTH = state.WIDTH
    HEIGHT = state.HEIGHT
    pygame.event.clear()
    screen = state.screen
    while True:
        clock.tick(FPS)
        pw, ph = min(680, WIDTH - 40), min(HEIGHT - 40, 760)
        panel = pygame.Rect(WIDTH // 2 - pw // 2, max(10, HEIGHT // 2 - ph // 2), pw, ph)
        draw_ui_background()
        draw_panel(panel)
        draw_panel_title_bar(panel, T("ach_title"))
        unlocked_count = sum(1 for v in state.ach_unlocked.values() if v)
        draw_text_center(T("ach_title"), pygame.Rect(panel.x, panel.y + 8, pw, 52), ACCENT, state.TITLE)
        draw_text_center(T("ach_unlocked", unlocked_count, len(ACH_IDS)), pygame.Rect(panel.x, panel.y + 58, pw, 28), TEXT_DIM, SMALL)
        pygame.draw.line(screen, PANEL_BORD, (panel.x + 20, panel.y + 88), (panel.right - 20, panel.y + 88), 1)
        pos = pygame.mouse.get_pos()
        row_h = max(44, int(50 * HEIGHT / 720))
        start_y = panel.y + 96
        for ii, aid in enumerate(ACH_IDS):
            ry = start_y + ii * row_h
            if ry + row_h > panel.bottom - 70: break
            unlocked = state.ach_unlocked.get(aid, False)
            row_r = pygame.Rect(panel.x + 12, ry, pw - 24, row_h - 4)
            rs = pygame.Surface((row_r.w, row_r.h), pygame.SRCALPHA)
            rs.fill((50, 80, 52, 90) if unlocked else (20, 30, 22, 60))
            screen.blit(rs, row_r.topleft)
            if unlocked: pygame.draw.rect(screen, (80, 130, 60, 120), row_r, 1, border_radius=4)
            star_col = ACCENT if unlocked else TEXT_DIM
            draw_text("★" if unlocked else "○", panel.x + 20, ry + (row_h - 4 - state.FONT.get_height()) // 2, star_col, state.FONT)
            draw_text(T(aid), panel.x + 52, ry + 4, ACCENT if unlocked else TEXT, SMALL)
            draw_text(T(aid + "_d"), panel.x + 52, ry + 4 + SMALL.get_height() + 2, TEXT_DIM, state.TINY)
        back_r = pygame.Rect(panel.x + (pw - 200) // 2, panel.bottom - 60, 200, 50)
        draw_button(T("back"), back_r, pos, font=SMALL)
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                if state.app_settings: state.app_settings.save()
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE: return
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if back_r.collidepoint(e.pos): return


def history_screen():
    WIDTH = state.WIDTH
    HEIGHT = state.HEIGHT
    h = load_history()
    pygame.event.clear()
    screen = state.screen
    while True:
        clock.tick(FPS)
        pw, ph = min(860, WIDTH - 40), min(620, HEIGHT - 40)
        panel = pygame.Rect(WIDTH // 2 - pw // 2, max(10, HEIGHT // 2 - ph // 2), pw, ph)
        draw_ui_background()
        draw_panel(panel, glow=True)
        draw_panel_title_bar(panel, T("history"))
        draw_text_center(T("history"), pygame.Rect(panel.x, panel.y + 8, pw, 52), ACCENT, state.TITLE)
        sub = "Last battles across the Dustway" if state.language == "en" else "Последние матчи на Пыльном тракте"
        draw_text_center(sub, pygame.Rect(panel.x, panel.y + 58, pw, 22), TEXT_DIM, SMALL)

        table = pygame.Rect(panel.x + 22, panel.y + 92, pw - 44, ph - 168)
        tint = pygame.Surface((table.w, table.h), pygame.SRCALPHA)
        tint.fill((10, 24, 18, 110))
        screen.blit(tint, table.topleft)
        pygame.draw.rect(screen, PANEL_BORD, table, 1, border_radius=12)

        headers = [
            (0.03, "Date" if state.language == "en" else "Дата"),
            (0.23, "Result" if state.language == "en" else "Итог"),
            (0.40, "Diff" if state.language == "en" else "Сложн."),
            (0.56, "Mode" if state.language == "en" else "Режим"),
            (0.73, "Time" if state.language == "en" else "Время"),
            (0.86, "Caps" if state.language == "en" else "Крышки"),
        ]
        hdr_y = table.y + 16
        for frac, label in headers:
            draw_text(label, table.x + int(table.w * frac), hdr_y, TEXT_DIM, SMALL)
        pygame.draw.line(screen, PANEL_BORD, (table.x + 18, table.y + 48), (table.right - 18, table.y + 48), 1)

        row_h = max(42, int(48 * HEIGHT / 720))
        visible = max(1, min(9, (table.h - 88) // row_h))
        recent = list(reversed(h[-visible:]))
        for ii, r in enumerate(recent):
            ry = table.y + 58 + ii * row_h
            rr = pygame.Rect(table.x + 12, ry, table.w - 24, row_h - 6)
            rsurf = pygame.Surface((rr.w, rr.h), pygame.SRCALPHA)
            rsurf.fill((38, 58, 40, 78) if ii % 2 == 0 else (20, 32, 24, 58))
            screen.blit(rsurf, rr.topleft)
            pygame.draw.rect(screen, (74, 98, 70), rr, 1, border_radius=8)
            rc = OUT_OK if r.result == "win" else RED if r.result == "loss" else YELLOW
            mode_txt = (r.mode.replace("_", " ")[:10])
            diff_txt = r.difficulty[:8]
            caps_txt = f"{'+' if r.caps_delta>=0 else ''}{r.caps_delta}"
            draw_text(r.date, table.x + int(table.w * 0.03), ry + 8, TEXT_DIM, SMALL)
            draw_text(r.result.upper(), table.x + int(table.w * 0.23), ry + 8, rc, state.FONT)
            draw_text(diff_txt, table.x + int(table.w * 0.40), ry + 8, TEXT, SMALL)
            draw_text(mode_txt, table.x + int(table.w * 0.56), ry + 8, TEXT, SMALL)
            draw_text(format_time_ms(r.duration_s * 1000), table.x + int(table.w * 0.73), ry + 8, TEXT_DIM, SMALL)
            draw_text(caps_txt, table.x + int(table.w * 0.86), ry + 8, CAPS_CLR if r.caps_delta >= 0 else RED, state.FONT)

        if not h:
            draw_text_center("No matches yet" if state.language == "en" else "История матчей пока пуста",
                             pygame.Rect(table.x, table.centery - 20, table.w, 40), TEXT_DIM, state.FONT)
        back_r = pygame.Rect(panel.x + (pw - 220) // 2, panel.bottom - 56, 220, 42)
        draw_button(T("back"), back_r, pygame.mouse.get_pos(), font=SMALL)
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                if state.app_settings: state.app_settings.save()
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE: return
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if back_r.collidepoint(e.pos): return


def local_leaderboard_screen():
    WIDTH = state.WIDTH
    HEIGHT = state.HEIGHT
    h = load_history()
    wins = [r for r in h if r.result == "win"]
    wins.sort(key=lambda r: r.duration_s)
    pygame.event.clear()
    screen = state.screen
    while True:
        clock.tick(FPS)
        pw, ph = min(640, WIDTH - 40), min(520, HEIGHT - 40)
        panel = pygame.Rect(WIDTH // 2 - pw // 2, max(10, HEIGHT // 2 - ph // 2), pw, ph)
        draw_ui_background()
        draw_panel(panel)
        draw_panel_title_bar(panel, T("leaderboard"))
        draw_text_center(T("leaderboard"), pygame.Rect(panel.x, panel.y + 8, pw, 52), ACCENT, state.TITLE)
        draw_text_center("Fastest wins", pygame.Rect(panel.x, panel.y + 58, pw, 26), TEXT_DIM, SMALL)
        pygame.draw.line(screen, PANEL_BORD, (panel.x + 20, panel.y + 88), (panel.right - 20, panel.y + 88), 1)
        pos = pygame.mouse.get_pos()
        rank_y = panel.y + 100
        row_h = max(36, int(42 * HEIGHT / 720))
        medals = ["🥇", "🥈", "🥉"]
        for ii, r in enumerate(wins[:10]):
            ry = rank_y + ii * row_h
            if ry + row_h > panel.bottom - 70: break
            rs = pygame.Surface((pw - 24, row_h - 4), pygame.SRCALPHA)
            rs.fill((50, 80, 52, 80) if ii < 3 else (30, 45, 32, 50))
            screen.blit(rs, (panel.x + 12, ry))
            medal = medals[ii] if ii < 3 else f"#{ii+1}"
            draw_text(medal, panel.x + 20, ry + 4, ACCENT if ii < 3 else TEXT_DIM, SMALL)
            draw_text(format_time_ms(r.duration_s * 1000), panel.x + 80, ry + 4, TEXT, SMALL)
            draw_text(r.difficulty, panel.x + 220, ry + 4, TEXT_DIM, SMALL)
            draw_text(r.date, panel.x + 360, ry + 4, TEXT_DIM, state.TINY)
        if not wins:
            draw_text_center("No wins yet!", pygame.Rect(panel.x, panel.y + 200, pw, 40), TEXT_DIM, state.FONT)
        back_r = pygame.Rect(panel.x + (pw - 200) // 2, panel.bottom - 60, 200, 50)
        draw_button(T("back"), back_r, pos, font=SMALL)
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                if state.app_settings: state.app_settings.save()
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE: return
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if back_r.collidepoint(e.pos): return


def global_leaderboard_screen():
    WIDTH = state.WIDTH
    HEIGHT = state.HEIGHT
    screen = state.screen
    FONT = state.FONT
    SMALL = state.SMALL
    TINY = state.TINY
    
    from src.network import FirebaseFriends
    import threading
    
    data_cache = {"users": None, "error": False}
    def _fetch():
        users = FirebaseFriends.get_all_users()
        if not users:
            data_cache["error"] = True
            return
        
        # Format and sort
        lst = []
        for code, info in users.items():
            if isinstance(info, dict):
                c = info.get("caps", 0)
                w = info.get("wins", 0)
                name = info.get("name", "Unknown")
                lst.append((c, w, name, code))
        
        lst.sort(key=lambda x: x[0], reverse=True)
        data_cache["users"] = lst[:10]
        
    threading.Thread(target=_fetch, daemon=True).start()
    
    pygame.event.clear()
    anim_t = 0.0
    while True:
        clock.tick(FPS)
        anim_t += 1.0 / FPS
        
        pw, ph = min(640, WIDTH - 40), min(520, HEIGHT - 40)
        panel = pygame.Rect(WIDTH // 2 - pw // 2, max(10, HEIGHT // 2 - ph // 2), pw, ph)
        
        draw_ui_background()
        draw_panel(panel)
        draw_panel_title_bar(panel, "GLOBAL LEADERBOARD" if state.language == "en" else "ТОП ТОРГОВЦЕВ")
        
        title_r = pygame.Rect(panel.x, panel.y + 8, pw, 52)
        draw_text_center("TOP TRADERS" if state.language == "en" else "САМЫЕ БОГАТЫЕ", title_r, (240, 210, 100), state.TITLE)
        
        sub_r = pygame.Rect(panel.x, panel.y + 58, pw, 26)
        draw_text_center("By Caps / По крышкам", sub_r, (160, 140, 110), SMALL)
        
        pygame.draw.line(screen, PANEL_BORD, (panel.x + 20, panel.y + 88), (panel.right - 20, panel.y + 88), 1)
        
        pos = pygame.mouse.get_pos()
        rank_y = panel.y + 100
        row_h = max(36, int(42 * HEIGHT / 720))
        
        if data_cache["users"] is None and not data_cache["error"]:
            load_txt = "Connecting to Satellite..." if state.language == "en" else "Соединение со спутником..."
            load_r = pygame.Rect(panel.x, panel.y + 200, pw, 40)
            if int(anim_t * 3) % 2 == 0:
                draw_text_center(load_txt, load_r, (180, 170, 140), FONT)
        elif data_cache["error"] or not data_cache["users"]:
            err_txt = "Failed to load" if state.language == "en" else "Ошибка загрузки"
            draw_text_center(err_txt, pygame.Rect(panel.x, panel.y + 200, pw, 40), (200, 80, 80), FONT)
        else:
            medals = ["🥇", "🥈", "🥉"]
            for ii, (caps, wins, name, code) in enumerate(data_cache["users"]):
                ry = rank_y + ii * row_h
                if ry + row_h > panel.bottom - 70: break
                rs = pygame.Surface((pw - 24, row_h - 4), pygame.SRCALPHA)
                rs.fill((80, 70, 50, 80) if ii < 3 else (50, 45, 40, 50))
                screen.blit(rs, (panel.x + 12, ry))
                
                medal = medals[ii] if ii < 3 else f"#{ii+1}"
                draw_text(medal, panel.x + 20, ry + 4, (240, 210, 100) if ii < 3 else (160, 140, 110), SMALL)
                
                draw_text(name[:15], panel.x + 80, ry + 4, (240, 230, 210), SMALL)
                draw_text(f"W: {wins}", panel.x + 280, ry + 4, (140, 180, 140), SMALL)
                draw_text(f"Caps: {caps}", panel.x + 400, ry + 4, (220, 190, 100), SMALL)

        back_r = pygame.Rect(panel.x + (pw - 200) // 2, panel.bottom - 60, 200, 50)
        draw_button(T("back"), back_r, pos, font=SMALL)
        
        pygame.display.flip()
        
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                return
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if back_r.collidepoint(e.pos): return


def _card_text_color(card):
    if card.rank == "JKR": return CARD_JOKER
    if card.suit in ("H", "D"): return CARD_RED
    return CARD_BLACK



def draw_wooden_board(rect):
    import pygame
    import src.state as state
    screen = state.screen
    # Wood backboard
    pygame.draw.rect(screen, (85, 65, 50), rect, border_radius=8)
    pygame.draw.rect(screen, (50, 35, 25), rect, 4, border_radius=8)
    # Metal corner brackets
    cs = 30
    for cx, cy in [(rect.left, rect.top), (rect.right-cs, rect.top), 
                   (rect.left, rect.bottom-cs), (rect.right-cs, rect.bottom-cs)]:
        pr = pygame.Rect(cx, cy, cs, cs)
        pygame.draw.rect(screen, (130, 140, 145), pr, border_radius=4)
        pygame.draw.rect(screen, (80, 90, 95), pr, 2, border_radius=4)
        pygame.draw.circle(screen, (60, 70, 75), (cx + cs//2, cy + cs//2), 4)

def draw_parchment(rect):
    import pygame
    import src.state as state
    screen = state.screen
    pygame.draw.rect(screen, (235, 225, 205), rect, border_radius=4)
    pygame.draw.rect(screen, (180, 160, 130), rect, 2, border_radius=4)
    inner = rect.inflate(-12, -12)
    pygame.draw.rect(screen, (190, 175, 145), inner, 1)

_AVATAR_CACHE = {}

def load_avatar(icon_key, size):
    cache_key = (icon_key, size)
    if cache_key in _AVATAR_CACHE:
        return _AVATAR_CACHE[cache_key]
    from src.config import AVATARS_DIR
    fp = os.path.join(AVATARS_DIR, f"{icon_key}.png")
    try:
        if os.path.exists(fp):
            img = pygame.image.load(fp).convert_alpha()
            scaled = pygame.transform.smoothscale(img, (size, size))
            _AVATAR_CACHE[cache_key] = scaled
            return scaled
    except:
        pass
    return None

def draw_leather_banner(rect):
    import pygame
    import src.state as state
    screen = state.screen
    points = [
        (rect.left, rect.top),
        (rect.right, rect.top),
        (rect.right, rect.bottom - 40),
        (rect.centerx, rect.bottom),
        (rect.left, rect.bottom - 40)
    ]
    pygame.draw.polygon(screen, (165, 105, 65), points)
    pygame.draw.polygon(screen, (100, 55, 35), points, 4)
    stitch_pts = [
        (rect.left + 6, rect.top + 6),
        (rect.right - 6, rect.top + 6),
        (rect.right - 6, rect.bottom - 43),
        (rect.centerx, rect.bottom - 6),
        (rect.left + 6, rect.bottom - 43)
    ]
    pygame.draw.polygon(screen, (190, 130, 90), stitch_pts, 2)
    pygame.draw.polygon(screen, (135, 80, 45), [
        (rect.centerx - 30, rect.bottom - 70),
        (rect.centerx + 30, rect.bottom - 70),
        (rect.centerx, rect.bottom - 30)
    ])

def draw_widget(rect, title, bg_color=(170, 185, 175), border_color=(110, 125, 115), hovered=False):
    import pygame
    import src.state as state
    from src.ui import lighten, draw_text_center
    screen = state.screen
    if hovered:
        bg_color = lighten(bg_color, 20)
    pygame.draw.rect(screen, bg_color, rect, border_radius=8)
    pygame.draw.rect(screen, border_color, rect, 2, border_radius=8)
    for rx, ry in [(rect.x+6, rect.y+6), (rect.right-6, rect.y+6), 
                   (rect.x+6, rect.bottom-6), (rect.right-6, rect.bottom-6)]:
        pygame.draw.circle(screen, (100, 110, 100), (rx, ry), 2)
    pygame.draw.rect(screen, (235, 225, 205), (rect.centerx - 80, rect.y + 6, 160, 24), border_radius=4)
    draw_text_center(title, pygame.Rect(rect.centerx - 80, rect.y + 6, 160, 24), (50, 50, 50), state.TINY)

def draw_stat_box(x, y, w, h, title, value, title_bg=(210, 200, 180), val_bg=(245, 235, 215)):
    import pygame
    import src.state as state
    from src.ui import draw_text_center
    screen = state.screen
    rect = pygame.Rect(x, y, w, h)
    pygame.draw.rect(screen, val_bg, rect, border_radius=6)
    pygame.draw.rect(screen, (150, 140, 120), rect, 2, border_radius=6)
    tr = pygame.Rect(x, y, w, 22)
    pygame.draw.rect(screen, title_bg, tr, border_top_left_radius=6, border_top_right_radius=6)
    pygame.draw.line(screen, (150, 140, 120), (x, y + 22), (x + w, y + 22), 2)
    draw_text_center(title, tr, (40, 40, 40), state.TINY)
    vr = pygame.Rect(x, y + 22, w, h - 22)
    draw_text_center(str(value), vr, (20, 20, 20), state.FONT)

def friend_profile_screen(friend_data: dict):
    from src.config import PROFILE_BG_DIR
    pygame.event.clear()
    
    while True:
        clock.tick(FPS)
        screen = state.screen
        WIDTH, HEIGHT = state.WIDTH, state.HEIGHT

        draw_ui_background()
        pos = pygame.mouse.get_pos()

        pw = min(1100, WIDTH - 40)
        ph = min(680, HEIGHT - 40)
        outer_rect = pygame.Rect(WIDTH // 2 - pw // 2, HEIGHT // 2 - ph // 2, pw, ph)
        
        title_r = pygame.Rect(outer_rect.x, outer_rect.y - 50, pw, 40)
        draw_text_center(f"{friend_data.get('name', 'Friend')}'s Profile", title_r, (240, 230, 210), state.TITLE)
        
        back_w = 140
        back_r = pygame.Rect(outer_rect.x, outer_rect.y - 50, back_w, 40)
        back_hovered = back_r.collidepoint(pos)
        pygame.draw.rect(screen, (235, 225, 205) if not back_hovered else (255, 245, 225), back_r, border_radius=20)
        pygame.draw.rect(screen, (140, 130, 110), back_r, 3, border_radius=20)
        for cx, cy in [(back_r.left+8, back_r.centery-4), (back_r.left+8, back_r.centery+4),
                       (back_r.right-8, back_r.centery-4), (back_r.right-8, back_r.centery+4)]:
            pygame.draw.circle(screen, (180, 170, 150), (cx, cy), 4)
        draw_text_center("← BACK" if state.language == "en" else "← НАЗАД", back_r, (50, 40, 30), state.SMALL)

        draw_wooden_board(outer_rect)
        parch_rect = outer_rect.inflate(-24, -24)
        draw_parchment(parch_rect)

        col_margin, gap = 30, 25
        col1_x = parch_rect.x + col_margin
        col1_w = int((parch_rect.w - col_margin * 2 - gap * 2) * 0.28)
        col2_x = col1_x + col1_w + gap
        col2_w = int((parch_rect.w - col_margin * 2 - gap * 2) * 0.38)
        col3_x = col2_x + col2_w + gap
        col3_w = parch_rect.right - col3_x - col_margin

        l_rect = pygame.Rect(col1_x, parch_rect.y - 10, col1_w, parch_rect.h - 40)
        draw_leather_banner(l_rect)
        
        av_w = col1_w - 40
        av_r = pygame.Rect(l_rect.x + 20, l_rect.y + 40, av_w, av_w)
        pygame.draw.rect(screen, (150, 155, 160), av_r, border_radius=16)
        pygame.draw.rect(screen, (90, 95, 100), av_r, 4, border_radius=16)
        inner_av_w = av_w - 24
        inner_av_r = pygame.Rect(av_r.x + 12, av_r.y + 12, inner_av_w, inner_av_w)
        pygame.draw.rect(screen, (40, 35, 30), inner_av_r, border_radius=8)
        
        av_surf = load_avatar(friend_data.get("icon", "trader"), inner_av_w)
        if av_surf: screen.blit(av_surf, inner_av_r.topleft)

        np_y = av_r.bottom + 30
        np_r = pygame.Rect(l_rect.x + 20, np_y, av_w, 40)
        pygame.draw.rect(screen, (240, 230, 210), np_r, border_radius=4)
        pygame.draw.rect(screen, (140, 120, 90), np_r, 2, border_radius=4)
        draw_text_center(friend_data.get("name", "Unknown"), np_r, (50, 40, 30), state.FONT)

        rp_y = np_r.bottom + 15
        rp_r = pygame.Rect(l_rect.x + 20, rp_y, av_w, 40)
        pygame.draw.rect(screen, (220, 205, 180), rp_r, border_radius=4)
        pygame.draw.rect(screen, (140, 120, 90), rp_r, 2, border_radius=4)
        caps_lbl = f"Caps: {friend_data.get('caps', 0)}" if state.language == "en" else f"Крышки: {friend_data.get('caps', 0)}"
        draw_text_center(caps_lbl, rp_r, (60, 50, 40), state.FONT)

        m_y = parch_rect.y + 40
        stat_w = (col2_w - 20) // 2
        draw_stat_box(col2_x, m_y, stat_w, 70, "LEVEL" if state.language == "en" else "УРОВЕНЬ", "1", title_bg=(220, 210, 190))
        draw_stat_box(col2_x + stat_w + 20, m_y, stat_w, 70, "REPUTATION" if state.language == "en" else "РЕПУТАЦИЯ", "0/0", title_bg=(220, 210, 190))
        
        m_y += 90
        draw_stat_box(col2_x, m_y, stat_w, 70, "WINS" if state.language == "en" else "ПОБЕДЫ", friend_data.get('wins', 0), title_bg=(150, 180, 160))
        draw_stat_box(col2_x + stat_w + 20, m_y, stat_w, 70, "LOSSES" if state.language == "en" else "ПОРАЖЕНИЯ", friend_data.get('losses', 0), title_bg=(220, 120, 100))
        
        m_y += 90
        draws_lbl = f"DRAWS: {friend_data.get('draws', 0)}" if state.language == "en" else f"НИЧЬИ: {friend_data.get('draws', 0)}"
        draw_text(draws_lbl, col2_x + 10, m_y, (50, 40, 30), state.FONT)
        pygame.draw.line(screen, (180, 160, 130), (col2_x, m_y + 35), (col2_x + col2_w, m_y + 35), 2)
        
        m_y += 80
        ra_lbl = "THEIR FRIENDS" if state.language == "en" else "ИХ ДРУЗЬЯ"
        draw_text(ra_lbl, col2_x, m_y, (50, 40, 30), state.SMALL)
        
        fr_y = m_y + 30
        fr_sz = 44
        fr_gap = 10
        their_friends = friend_data.get("friends", [])
        if not their_friends:
            draw_text("No friends yet." if state.language == "en" else "Пока нет друзей.", col2_x, fr_y + 10, (140, 130, 110), state.TINY)
        else:
            for i, fcode in enumerate(their_friends[:5]):
                fx = col2_x + i * (fr_sz + fr_gap)
                fr_r = pygame.Rect(fx, fr_y, fr_sz, fr_sz)
                pygame.draw.rect(screen, (225, 215, 195), fr_r, border_radius=6)
                pygame.draw.rect(screen, (190, 175, 150), fr_r, 2, border_radius=6)
                pygame.draw.circle(screen, (160, 150, 130), (fr_r.centerx, fr_r.centery), 12)

        pygame.display.flip()

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                return
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if back_r.collidepoint(e.pos):
                return

def cloud_restore_screen():
    WIDTH = state.WIDTH
    HEIGHT = state.HEIGHT
    screen = state.screen
    FONT = state.FONT
    SMALL = state.SMALL
    TINY = state.TINY
    
    from src.network import FirebaseFriends
    import threading
    
    input_code = ""
    status_msg = ""
    status_color = (200, 180, 140)
    is_loading = False
    
    def _do_restore(code: str):
        nonlocal status_msg, status_color, is_loading
        d = FirebaseFriends.lookup_friend(code)
        if not d:
            status_msg = "Profile not found!" if state.language == "en" else "Профиль не найден!"
            status_color = (200, 80, 80)
            is_loading = False
            return
            
        # We found it! Apply data
        state.app_settings.friend_code = code
        if "name" in d: state.app_settings.player_name = d["name"]
        if "icon" in d: state.app_settings.player_icon = d["icon"]
        if "caps" in d: state.app_settings.caps = d["caps"]
        if "friends" in d and isinstance(d["friends"], list):
            state.app_settings.friends = d["friends"]
            
        if "wins" in d: state.app_stats.wins = d["wins"]
        if "losses" in d: state.app_stats.losses = d["losses"]
        if "draws" in d: state.app_stats.draws = d["draws"]
        
        state.app_settings.save()
        state.app_stats.save()
        
        status_msg = "Profile Restored!" if state.language == "en" else "Профиль восстановлен!"
        status_color = (100, 200, 110)
        is_loading = False

    pygame.event.clear()
    anim_t = 0.0
    while True:
        clock.tick(FPS)
        anim_t += 1.0 / FPS
        
        pw, ph = min(500, WIDTH - 40), min(340, HEIGHT - 40)
        panel = pygame.Rect(WIDTH // 2 - pw // 2, HEIGHT // 2 - ph // 2, pw, ph)
        
        draw_ui_background()
        draw_panel(panel)
        draw_panel_title_bar(panel, "CLOUD RESTORE" if state.language == "en" else "ВОССТАНОВЛЕНИЕ ПРОФИЛЯ", color=(90, 140, 190))
        
        title_r = pygame.Rect(panel.x, panel.y + 10, pw, 52)
        draw_text_center("RESTORE FROM CLOUD" if state.language == "en" else "ВОССТАНОВИТЬ ПРОФИЛЬ", title_r, (220, 240, 255), state.TITLE)
        
        sub_r = pygame.Rect(panel.x + 20, panel.y + 60, pw - 40, 60)
        sub_txt = "Enter your old 6-character Friend Code:" if state.language == "en" else "Введите старый 6-значный Код Друга:"
        draw_text_center(sub_txt, sub_r, (180, 170, 150), SMALL)
        
        # Input Box
        box_w = 200
        box_r = pygame.Rect(panel.x + pw // 2 - box_w // 2, panel.y + 130, box_w, 50)
        pygame.draw.rect(screen, (30, 25, 20), box_r, border_radius=8)
        pygame.draw.rect(screen, (90, 140, 190), box_r, 2, border_radius=8)
        
        disp = input_code + ("_" if (pygame.time.get_ticks() // 500) % 2 == 0 and not is_loading else " ")
        draw_text_center(disp, box_r, (250, 250, 250), FONT)
        
        # Status Message
        stat_r = pygame.Rect(panel.x, panel.y + 190, pw, 30)
        draw_text_center("Fetching from Satellite..." if is_loading else status_msg, stat_r, status_color, SMALL)
        
        pos = pygame.mouse.get_pos()
        
        # Buttons
        btn_w = 140
        btn_gap = 20
        back_r = pygame.Rect(panel.x + pw // 2 - btn_w - btn_gap // 2, panel.bottom - 60, btn_w, 45)
        rest_r = pygame.Rect(panel.x + pw // 2 + btn_gap // 2, panel.bottom - 60, btn_w, 45)
        
        draw_button(T("back"), back_r, pos, font=SMALL)
        if not is_loading:
            draw_button("Restore" if state.language == "en" else "Загрузить", rest_r, pos, (50, 100, 140), (80, 130, 180), SMALL)
        else:
            draw_button("Wait..." if state.language == "en" else "Ждите...", rest_r, pos, (80, 80, 80), (80, 80, 80), SMALL)

        pygame.display.flip()
        
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    return
                if not is_loading:
                    if e.key == pygame.K_BACKSPACE:
                        input_code = input_code[:-1]
                        status_msg = ""
                    elif e.unicode.isalnum() and len(input_code) < 6:
                        input_code += e.unicode.upper()
                        status_msg = ""
                    elif e.key == pygame.K_RETURN and len(input_code) == 6:
                        is_loading = True
                        status_color = (200, 180, 140)
                        threading.Thread(target=lambda: _do_restore(input_code), daemon=True).start()

            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if back_r.collidepoint(e.pos):
                    return
                if rest_r.collidepoint(e.pos) and not is_loading and len(input_code) == 6:
                    is_loading = True
                    status_color = (200, 180, 140)
                    threading.Thread(target=lambda: _do_restore(input_code), daemon=True).start()

def profile_screen():
    """Profile hub: Avatar, Name, Deck, Stats, Achievements, History. Redesigned to mockup style."""
    from src.config import AVATARS_DIR, DEFAULT_AVATARS, PROFILE_BG_DIR
    _bg_cache = {}

    add_friend_mode = False
    add_friend_input = ""
    friend_status = ""
    friends_data = []
    pending_requests = {}
    
    import threading
    from src.network import FirebaseFriends

    def _sync_new_friends():
        # Check for accepted friend requests
        new_friends = FirebaseFriends.pop_new_friends(state.app_settings.friend_code)
        if new_friends:
            added = False
            for f in new_friends:
                if f not in state.app_settings.friends:
                    state.app_settings.friends.append(f)
                    added = True
            if added:
                state.app_settings.save()
                _fetch_friends()

    def _fetch_friends():
        nonlocal friends_data, pending_requests
        fetched = []
        for code in state.app_settings.friends:
            d = FirebaseFriends.lookup_friend(code)
            if d:
                d["code"] = code
                fetched.append(d)
            else:
                fetched.append({"code": code, "name": "Unknown", "icon": "trader"})
        friends_data = fetched
        pending_requests = FirebaseFriends.get_pending_requests(state.app_settings.friend_code)

    threading.Thread(target=_sync_new_friends, daemon=True).start()
    threading.Thread(target=_fetch_friends, daemon=True).start()

    def _load_profile_bg(bg_key, w, h):
        cache_key = (bg_key, w, h)
        if cache_key in _bg_cache:
            return _bg_cache[cache_key]
        fp = os.path.join(PROFILE_BG_DIR, f"{bg_key}.png")
        try:
            if os.path.exists(fp):
                img = pygame.image.load(fp).convert()
                sw, sh = img.get_size()
                scale = max(w / sw, h / sh)
                nw, nh = int(sw * scale), int(sh * scale)
                scaled = pygame.transform.smoothscale(img, (nw, nh))
                result = pygame.Surface((w, h))
                result.blit(scaled, ((w - nw) // 2, (h - nh) // 2))
                _bg_cache[cache_key] = result
                return result
        except:
            pass
        return None

    pygame.event.clear()
    while True:
        clock.tick(FPS)
        screen = state.screen
        WIDTH = state.WIDTH
        HEIGHT = state.HEIGHT

        bg_surf = _load_profile_bg(state.app_settings.profile_bg, WIDTH, HEIGHT)
        if bg_surf:
            screen.blit(bg_surf, (0, 0))
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 140))
            screen.blit(overlay, (0, 0))
            vignette = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            edge_h = max(60, HEIGHT // 5)
            for y in range(edge_h):
                alpha = int(80 * (1 - y / edge_h))
                pygame.draw.line(vignette, (0, 0, 0, alpha), (0, y), (WIDTH, y))
                pygame.draw.line(vignette, (0, 0, 0, alpha), (0, HEIGHT - 1 - y), (WIDTH, HEIGHT - 1 - y))
            screen.blit(vignette, (0, 0))
        else:
            draw_ui_background()

        pos = pygame.mouse.get_pos()

        # Layout metrics - made much wider and taller
        pw = min(1100, WIDTH - 40)
        ph = min(680, HEIGHT - 40)
        outer_rect = pygame.Rect(WIDTH // 2 - pw // 2, HEIGHT // 2 - ph // 2, pw, ph)
        
        # TITLE ABOVE PANEL
        title_lbl = "PROFILE" if state.language == "en" else "ПРОФИЛЬ"
        title_r = pygame.Rect(outer_rect.x, outer_rect.y - 50, pw, 40)
        draw_text_center(title_lbl, title_r, (240, 230, 210), state.TITLE)
        
        # Top-left BACK button
        back_w = 140
        back_r = pygame.Rect(outer_rect.x, outer_rect.y - 50, back_w, 40)
        back_hovered = back_r.collidepoint(pos)
        pygame.draw.rect(screen, (235, 225, 205) if not back_hovered else (255, 245, 225), back_r, border_radius=20)
        pygame.draw.rect(screen, (140, 130, 110), back_r, 3, border_radius=20)
        # bone decorations
        pygame.draw.circle(screen, (180, 170, 150), (back_r.left + 8, back_r.centery - 4), 4)
        pygame.draw.circle(screen, (180, 170, 150), (back_r.left + 8, back_r.centery + 4), 4)
        pygame.draw.circle(screen, (180, 170, 150), (back_r.right - 8, back_r.centery - 4), 4)
        pygame.draw.circle(screen, (180, 170, 150), (back_r.right - 8, back_r.centery + 4), 4)
        
        draw_text_center("← BACK" if state.language == "en" else "← НАЗАД", back_r, (50, 40, 30), state.SMALL)

        # Draw outer wooden board then parchment
        draw_wooden_board(outer_rect)
        
        parch_rect = outer_rect.inflate(-24, -24)
        draw_parchment(parch_rect)

        # COLUMNS setup
        col_margin = 30
        gap = 25
        
        col1_x = parch_rect.x + col_margin
        col1_w = int((parch_rect.w - col_margin * 2 - gap * 2) * 0.28)
        
        col2_x = col1_x + col1_w + gap
        col2_w = int((parch_rect.w - col_margin * 2 - gap * 2) * 0.38)
        
        col3_x = col2_x + col2_w + gap
        col3_w = parch_rect.right - col3_x - col_margin

        # --- LEFT COLUMN (Banner) ---
        l_rect = pygame.Rect(col1_x, parch_rect.y - 10, col1_w, parch_rect.h - 40)
        draw_leather_banner(l_rect)
        
        # Avatar frame (metallic)
        av_w = col1_w - 40
        av_r = pygame.Rect(l_rect.x + 20, l_rect.y + 40, av_w, av_w)
        av_hit = av_r.copy()
        av_hovered = av_hit.collidepoint(pos)
        
        # Outer metal base
        pygame.draw.rect(screen, (150, 155, 160) if not av_hovered else (170, 175, 180), av_r, border_radius=16)
        pygame.draw.rect(screen, (90, 95, 100), av_r, 4, border_radius=16)
        # Inner dark cutout
        inner_av_w = av_w - 24
        inner_av_r = pygame.Rect(av_r.x + 12, av_r.y + 12, inner_av_w, inner_av_w)
        pygame.draw.rect(screen, (40, 35, 30), inner_av_r, border_radius=8)
        
        av_surf = load_avatar(state.app_settings.player_icon, inner_av_w)
        if av_surf:
            screen.blit(av_surf, inner_av_r.topleft)

        # Name Plate
        np_y = av_r.bottom + 30
        np_r = pygame.Rect(l_rect.x + 20, np_y, av_w, 40)
        np_hovered = np_r.collidepoint(pos)
        pygame.draw.rect(screen, (240, 230, 210) if not np_hovered else (255, 245, 225), np_r, border_radius=4)
        pygame.draw.rect(screen, (140, 120, 90), np_r, 2, border_radius=4)
        # Stitch lines
        pygame.draw.line(screen, (180, 160, 130), (np_r.x + 5, np_r.y + 5), (np_r.right - 5, np_r.y + 5), 1)
        pygame.draw.line(screen, (180, 160, 130), (np_r.x + 5, np_r.bottom - 5), (np_r.right - 5, np_r.bottom - 5), 1)
        draw_text_center(state.app_settings.player_name, np_r, (50, 40, 30), state.FONT)

        # Reputation/Caps Plate
        rp_y = np_r.bottom + 15
        rp_r = pygame.Rect(l_rect.x + 20, rp_y, av_w, 40)
        pygame.draw.rect(screen, (220, 205, 180), rp_r, border_radius=4)
        pygame.draw.rect(screen, (140, 120, 90), rp_r, 2, border_radius=4)
        caps_lbl = f"Caps: {state.app_settings.caps}" if state.language == "en" else f"Крышки: {state.app_settings.caps}"
        draw_text_center(caps_lbl, rp_r, (60, 50, 40), state.FONT)

        # Backgrounds button at the bottom
        bg_btn_r = pygame.Rect(l_rect.x + 40, rp_r.bottom + 40, av_w - 40, 36)
        bg_hovered = bg_btn_r.collidepoint(pos)
        pygame.draw.rect(screen, (130, 140, 135) if not bg_hovered else (150, 160, 155), bg_btn_r, border_radius=6)
        pygame.draw.rect(screen, (80, 90, 85), bg_btn_r, 2, border_radius=6)
        bg_lbl = "Background" if state.language == "en" else "Фон"
        draw_text_center(bg_lbl, bg_btn_r, (240, 240, 240), state.SMALL)
        
        # Cloud Restore button
        restore_r = pygame.Rect(l_rect.x + 40, bg_btn_r.bottom + 15, av_w - 40, 36)
        restore_hovered = restore_r.collidepoint(pos)
        pygame.draw.rect(screen, (90, 140, 190) if not restore_hovered else (110, 160, 210), restore_r, border_radius=6)
        pygame.draw.rect(screen, (60, 100, 140), restore_r, 2, border_radius=6)
        restore_lbl = "☁ Restore" if state.language == "en" else "☁ Облако"
        draw_text_center(restore_lbl, restore_r, (250, 250, 250), state.SMALL)

        # --- MIDDLE COLUMN ---
        m_y = parch_rect.y + 40
        
        # Level / Rep stats
        stat_w = (col2_w - 20) // 2
        draw_stat_box(col2_x, m_y, stat_w, 70, "LEVEL" if state.language == "en" else "УРОВЕНЬ", "1", title_bg=(220, 210, 190))
        draw_stat_box(col2_x + stat_w + 20, m_y, stat_w, 70, "REPUTATION" if state.language == "en" else "РЕПУТАЦИЯ", "0/0", title_bg=(220, 210, 190))
        
        m_y += 90
        
        # Wins / Losses (Non-clickable)
        draw_stat_box(col2_x, m_y, stat_w, 70, "WINS" if state.language == "en" else "ПОБЕДЫ", state.app_stats.wins, title_bg=(150, 180, 160))
        draw_stat_box(col2_x + stat_w + 20, m_y, stat_w, 70, "LOSSES" if state.language == "en" else "ПОРАЖЕНИЯ", state.app_stats.losses, title_bg=(220, 120, 100))
        
        m_y += 90
        
        # Draws
        draws_lbl = f"DRAWS: {state.app_stats.draws}" if state.language == "en" else f"НИЧЬИ: {state.app_stats.draws}"
        draw_text(draws_lbl, col2_x + 10, m_y, (50, 40, 30), state.FONT)
        pygame.draw.line(screen, (180, 160, 130), (col2_x, m_y + 35), (col2_x + col2_w, m_y + 35), 2)
        
        m_y += 50
        
        # Story Progress Placeholder
        sp_lbl = "STORY PROGRESS" if state.language == "en" else "ПРОГРЕСС СЮЖЕТА"
        draw_text(sp_lbl, col2_x, m_y, (50, 40, 30), state.SMALL)
        pb_r = pygame.Rect(col2_x, m_y + 25, col2_w, 18)
        pygame.draw.rect(screen, (180, 160, 130), pb_r, border_radius=9)
        pygame.draw.rect(screen, (110, 90, 70), pygame.Rect(pb_r.x, pb_r.y, int(pb_r.w * 0.15), pb_r.h), border_radius=9)
        draw_text("(Coming Soon)" if state.language == "en" else "(Скоро)", col2_x, m_y + 50, (140, 120, 100), state.SMALL)
        
        pygame.draw.line(screen, (180, 160, 130), (col2_x, m_y + 80), (col2_x + col2_w, m_y + 80), 2)
        m_y += 100
        
        # FRIENDS WIDGET
        fc_lbl = f"Your Code: {state.app_settings.friend_code}" if state.language == "en" else f"Ваш Код: {state.app_settings.friend_code}"
        
        fc_rect = pygame.Rect(col2_x, m_y, col2_w, 36)
        pygame.draw.rect(screen, (220, 205, 180), fc_rect, border_radius=6)
        pygame.draw.rect(screen, (140, 120, 90), fc_rect, 2, border_radius=6)
        draw_text_center(fc_lbl, fc_rect, (40, 30, 20), state.SMALL)
        
        m_y += 45
        ra_lbl = "FRIENDS" if state.language == "en" else "ДРУЗЬЯ"
        draw_text(ra_lbl, col2_x, m_y, (50, 40, 30), state.SMALL)
        
        # Add Friend Button
        add_btn_r = pygame.Rect(col2_x + col2_w - 100, m_y, 100, 24)
        ab_hovered = add_btn_r.collidepoint(pos)
        pygame.draw.rect(screen, (100, 140, 110) if not ab_hovered else (120, 160, 130), add_btn_r, border_radius=4)
        draw_text_center("+ ADD" if state.language == "en" else "+ ДОБАВИТЬ", add_btn_r, (240, 240, 240), state.TINY)
        
        fr_y = m_y + 30
        friend_hitboxes = []
        if add_friend_mode:
            disp = add_friend_input + ("_" if (pygame.time.get_ticks() // 500) % 2 == 0 else " ")
            draw_text(f"Code: {disp}", col2_x, fr_y, (50, 40, 30), state.SMALL)
            if friend_status:
                draw_text(friend_status, col2_x, fr_y + 25, RED if "Error" in friend_status or "не" in friend_status.lower() else (40, 120, 50), state.TINY)
        else:
            fr_sz = 44
            fr_gap = 10
            for i, fd in enumerate(friends_data[:5]):
                fx = col2_x + i * (fr_sz + fr_gap)
                fr_r = pygame.Rect(fx, fr_y, fr_sz, fr_sz)
                pygame.draw.rect(screen, (225, 215, 195), fr_r, border_radius=6)
                pygame.draw.rect(screen, (190, 175, 150), fr_r, 2, border_radius=6)
                f_av = load_avatar(fd["icon"], fr_sz - 4)
                if f_av:
                    screen.blit(f_av, (fx + 2, fr_y + 2))
                friend_hitboxes.append((fr_r, fd))
                if fr_r.collidepoint(pos):
                    tt_r = pygame.Rect(fx, fr_y - 25, 100, 20)
                    pygame.draw.rect(screen, (30, 30, 30), tt_r)
                    draw_text_center(fd["name"], tt_r, (240, 240, 240), state.TINY)
            if not friends_data:
                draw_text("No friends yet." if state.language == "en" else "Пока нет друзей.", col2_x, fr_y + 10, (140, 130, 110), state.TINY)

        # Pending Requests below friends
        req_y = fr_y + 60
        accept_hitboxes = []
        decline_hitboxes = []
        if pending_requests:
            req_lbl = "PENDING REQUESTS" if state.language == "en" else "ВХОДЯЩИЕ ЗАПРОСЫ"
            draw_text(req_lbl, col2_x, req_y, (180, 70, 70), state.SMALL)
            req_y += 25
            for req_code, req_name in list(pending_requests.items())[:3]:
                req_rect = pygame.Rect(col2_x, req_y, col2_w, 30)
                pygame.draw.rect(screen, (230, 220, 200), req_rect, border_radius=4)
                draw_text(f"{req_name} ({req_code})", col2_x + 10, req_y + 6, (50, 40, 30), state.TINY)
                
                acc_r = pygame.Rect(req_rect.right - 80, req_y + 3, 35, 24)
                dec_r = pygame.Rect(req_rect.right - 40, req_y + 3, 35, 24)
                
                pygame.draw.rect(screen, (100, 160, 110) if not acc_r.collidepoint(pos) else (120, 180, 130), acc_r, border_radius=4)
                draw_text_center("✓", acc_r, (255, 255, 255), state.SMALL)
                
                pygame.draw.rect(screen, (180, 100, 100) if not dec_r.collidepoint(pos) else (200, 120, 120), dec_r, border_radius=4)
                draw_text_center("✗", dec_r, (255, 255, 255), state.SMALL)
                
                accept_hitboxes.append((acc_r, req_code))
                decline_hitboxes.append((dec_r, req_code))
                req_y += 35

        # --- RIGHT COLUMN ---
        r_y = parch_rect.y + 40
        
        # DECK WIDGET
        deck_h = 160
        deck_r = pygame.Rect(col3_x, r_y, col3_w, deck_h)
        draw_widget(deck_r, "DECK" if state.language == "en" else "КОЛОДА", bg_color=(170, 185, 175), hovered=False)
        # draw fake cards inside overlapping
        c_w, c_h = 50, 75
        c_y = deck_r.y + 45
        for i in range(3):
            cx = deck_r.x + deck_r.w // 2 - c_w // 2 + (i - 1) * 45
            c_rect = pygame.Rect(cx, c_y + abs(i - 1) * 8, c_w, c_h)
            pygame.draw.rect(screen, (200, 180, 140), c_rect, border_radius=6)
            pygame.draw.rect(screen, (140, 120, 90), c_rect, 2, border_radius=6)
            pygame.draw.circle(screen, (160, 140, 100), (cx + c_w//2, c_rect.y + c_h//2), 16)
        
        r_y += deck_h + 30
        
        # HISTORY / RECORD WIDGET
        hist_h = 160
        hist_r = pygame.Rect(col3_x, r_y, col3_w, hist_h)
        hh_hovered = hist_r.collidepoint(pos)
        draw_widget(hist_r, "CARAVAN RECORD" if state.language == "en" else "ЖУРНАЛ КАРАВАНА", bg_color=(220, 210, 180), hovered=hh_hovered)
        # notebook binding holes on left
        for i in range(8):
            hx = hist_r.x + 12
            hy = hist_r.y + 40 + i * 14
            pygame.draw.circle(screen, (80, 70, 60), (hx, hy), 4)
            pygame.draw.line(screen, (180, 170, 140), (hx + 4, hy), (hx + 12, hy), 2)
        
        # map line
        my = hist_r.y + 90
        mx1, mx2 = hist_r.x + 50, hist_r.right - 50
        pygame.draw.line(screen, (180, 160, 130), (mx1, my), (mx2, my), 3)
        pygame.draw.circle(screen, (200, 70, 70), (mx1, my), 8)
        pygame.draw.circle(screen, (160, 140, 110), (mx2, my), 8)
        
        # Add tiny "duels" swords icon mockup
        pygame.draw.line(screen, (100, 90, 80), (mx2 - 10, my - 20), (mx2 + 10, my - 40), 3)
        pygame.draw.line(screen, (100, 90, 80), (mx2 + 10, my - 20), (mx2 - 10, my - 40), 3)
        
        r_y += hist_h + 30
        
        # ACHIEVEMENTS WIDGET
        ach_h = 120
        ach_r = pygame.Rect(col3_x, r_y, col3_w, ach_h)
        ah_hovered = ach_r.collidepoint(pos)
        draw_widget(ach_r, "ACHIEVEMENTS" if state.language == "en" else "ДОСТИЖЕНИЯ", bg_color=(200, 190, 200), hovered=ah_hovered)
        # simple medal icon
        pygame.draw.circle(screen, (240, 210, 100), (ach_r.centerx, ach_r.centery + 15), 20)
        pygame.draw.circle(screen, (200, 160, 80), (ach_r.centerx, ach_r.centery + 15), 20, 3)

        pygame.display.flip()

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                if state.app_settings: state.app_settings.save()
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                return
            if e.type == pygame.KEYDOWN and add_friend_mode:
                if e.key == pygame.K_ESCAPE:
                    add_friend_mode = False
                    add_friend_input = ""
                    friend_status = ""
                elif e.key == pygame.K_BACKSPACE:
                    add_friend_input = add_friend_input[:-1]
                elif e.unicode.isalnum() and len(add_friend_input) < 6:
                    add_friend_input += e.unicode.upper()
                elif e.key == pygame.K_RETURN and len(add_friend_input) == 6:
                    if add_friend_input == state.app_settings.friend_code:
                        friend_status = "Cannot add yourself" if state.language == "en" else "Нельзя добавить себя"
                    elif add_friend_input in state.app_settings.friends:
                        friend_status = "Already a friend" if state.language == "en" else "Уже в друзьях"
                    else:
                        d = FirebaseFriends.lookup_friend(add_friend_input)
                        if d:
                            FirebaseFriends.send_friend_request(state.app_settings.friend_code, add_friend_input, state.app_settings.player_name)
                            friend_status = "Request Sent!" if state.language == "en" else "Запрос отправлен!"
                            # Keep open to show status, user can press ESC
                        else:
                            friend_status = "Player not found" if state.language == "en" else "Игрок не найден"
                continue

            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                # Friend clicks
                for fr_r, fd in friend_hitboxes:
                    if fr_r.collidepoint(e.pos):
                        friend_profile_screen(fd)
                        break

                for acc_r, req_code in accept_hitboxes:
                    if acc_r.collidepoint(e.pos):
                        if req_code not in state.app_settings.friends:
                            state.app_settings.friends.append(req_code)
                            state.app_settings.save()
                        FirebaseFriends.add_mutual_friend(state.app_settings.friend_code, req_code)
                        FirebaseFriends.remove_friend_request(state.app_settings.friend_code, req_code)
                        del pending_requests[req_code]
                        threading.Thread(target=_fetch_friends, daemon=True).start()
                        break
                
                for dec_r, req_code in decline_hitboxes:
                    if dec_r.collidepoint(e.pos):
                        FirebaseFriends.remove_friend_request(state.app_settings.friend_code, req_code)
                        del pending_requests[req_code]
                        break

                if add_btn_r.collidepoint(e.pos):
                    add_friend_mode = not add_friend_mode
                    friend_status = ""
                    continue
                if back_r.collidepoint(e.pos):
                    return
                if av_hit.collidepoint(e.pos):
                    avatar_select_screen()
                    continue
                if np_r.collidepoint(e.pos):
                    state.app_settings.player_name = name_input_screen(state.app_settings.player_name)
                    state.app_settings.save()
                    continue
                if bg_btn_r.collidepoint(e.pos):
                    profile_bg_select_screen()
                    continue
                if restore_r.collidepoint(e.pos):
                    cloud_restore_screen()
                    _fetch_friends()
                    continue
                if hist_r.collidepoint(e.pos):
                    global_leaderboard_screen()
                elif ach_r.collidepoint(e.pos):
                    achievements_screen()

def profile_bg_select_screen():
    """Let the player pick a profile background."""
    from src.config import PROFILE_BG_DIR, DEFAULT_PROFILE_BGS
    _thumb_cache = {}
    _preview_cache = {}

    def _load_thumb(bg_key, w, h):
        cache_key = (bg_key, w, h)
        if cache_key in _thumb_cache:
            return _thumb_cache[cache_key]
        fp = os.path.join(PROFILE_BG_DIR, f"{bg_key}.png")
        try:
            if os.path.exists(fp):
                img = pygame.image.load(fp).convert()
                sw, sh = img.get_size()
                scale = max(w / sw, h / sh)
                nw, nh = int(sw * scale), int(sh * scale)
                scaled = pygame.transform.smoothscale(img, (nw, nh))
                result = pygame.Surface((w, h))
                result.blit(scaled, ((w - nw) // 2, (h - nh) // 2))
                _thumb_cache[cache_key] = result
                return result
        except:
            pass
        return None

    def _load_preview(bg_key, w, h):
        cache_key = (bg_key, w, h)
        if cache_key in _preview_cache:
            return _preview_cache[cache_key]
        fp = os.path.join(PROFILE_BG_DIR, f"{bg_key}.png")
        try:
            if os.path.exists(fp):
                img = pygame.image.load(fp).convert()
                sw, sh = img.get_size()
                scale = max(w / sw, h / sh)
                nw, nh = int(sw * scale), int(sh * scale)
                scaled = pygame.transform.smoothscale(img, (nw, nh))
                result = pygame.Surface((w, h))
                result.blit(scaled, ((w - nw) // 2, (h - nh) // 2))
                _preview_cache[cache_key] = result
                return result
        except:
            pass
        return None

    # Discover available backgrounds
    available = []
    if os.path.isdir(PROFILE_BG_DIR):
        for fn in sorted(os.listdir(PROFILE_BG_DIR)):
            if fn.lower().endswith(".png"):
                key = fn[:-4]
                available.append(key)
    if not available:
        available = DEFAULT_PROFILE_BGS

    selected = state.app_settings.profile_bg
    pygame.event.clear()

    while True:
        clock.tick(FPS)
        screen = state.screen
        WIDTH = state.WIDTH
        HEIGHT = state.HEIGHT

        # Draw preview of the currently selected background
        preview = _load_preview(selected, WIDTH, HEIGHT)
        if preview:
            screen.blit(preview, (0, 0))
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 80))
            screen.blit(overlay, (0, 0))
        else:
            draw_ui_background()

        pos = pygame.mouse.get_pos()

        pw = min(1100, WIDTH - 40)
        ph = min(500, HEIGHT - 40)
        outer_rect = pygame.Rect(WIDTH // 2 - pw // 2, HEIGHT // 2 - ph // 2, pw, ph)
        
        draw_wooden_board(outer_rect)
        parch_rect = outer_rect.inflate(-24, -24)
        draw_parchment(parch_rect)

        title_lbl = "Choose Background" if state.language == "en" else "Выберите фон"
        draw_text_center(title_lbl, pygame.Rect(parch_rect.x, parch_rect.y + 15, parch_rect.w, 40), (50, 40, 30), state.TITLE)
        pygame.draw.line(screen, (180, 160, 130), (parch_rect.x + 40, parch_rect.y + 60), (parch_rect.right - 40, parch_rect.y + 60), 2)

        # Thumbnail row calculation
        thumb_gap = 20
        num_avail = len(available)
        max_thumb_w = (parch_rect.w - (num_avail + 1) * thumb_gap) // num_avail
        
        # calculate w/h keeping 16:9 aspect ratio
        thumb_w = min(max_thumb_w, 280) 
        thumb_h = int(thumb_w * 9 / 16)
        
        total_thumbs_w = num_avail * thumb_w + (num_avail - 1) * thumb_gap
        thumb_x0 = parch_rect.x + (parch_rect.w - total_thumbs_w) // 2
        thumb_y = parch_rect.y + 100

        bg_rects = []
        for i, bkey in enumerate(available):
            tx = thumb_x0 + i * (thumb_w + thumb_gap)
            tr = pygame.Rect(tx, thumb_y, thumb_w, thumb_h)
            bg_rects.append((tr, bkey))

            hovered = tr.collidepoint(pos)
            is_selected = (bkey == selected)

            # Shadow
            sh_surf = pygame.Surface((thumb_w + 4, thumb_h + 4), pygame.SRCALPHA)
            sh_surf.fill((0, 0, 0, 60))
            screen.blit(sh_surf, (tx + 2, thumb_y + 3))

            # Thumbnail image
            thumb_img = _load_thumb(bkey, thumb_w, thumb_h)
            if thumb_img:
                screen.blit(thumb_img, tr.topleft)

            # Border - Polaroid style
            if is_selected:
                pygame.draw.rect(screen, (50, 40, 30), tr, 4, border_radius=8)
                # Checkmark badge (Leather style)
                badge_r = 16
                badge_cx = tr.right - badge_r + 4
                badge_cy = tr.y + badge_r - 4
                pygame.draw.circle(screen, (100, 140, 110), (badge_cx, badge_cy), badge_r)
                pygame.draw.circle(screen, (50, 40, 30), (badge_cx, badge_cy), badge_r, 2)
                draw_text_center("✓", pygame.Rect(badge_cx - badge_r, badge_cy - badge_r,
                                                   badge_r * 2, badge_r * 2),
                                 (240, 240, 240), state.SMALL)
            elif hovered:
                pygame.draw.rect(screen, (160, 130, 90), tr, 4, border_radius=8)
            else:
                pygame.draw.rect(screen, (140, 120, 90), tr, 2, border_radius=8)

            # Name label
            name_map = {
                "tent": "Tent" if state.language == "en" else "Палатка",
                "caravan": "Caravan" if state.language == "en" else "Караван",
                "shack": "Shack" if state.language == "en" else "Хижина",
                "bunker": "Bunker" if state.language == "en" else "Бункер",
            }
            bname = name_map.get(bkey, bkey.capitalize())
            draw_text_center(bname, pygame.Rect(tx - 4, thumb_y + thumb_h + 4, thumb_w + 8, 22),
                             (50, 40, 30) if is_selected else (140, 120, 100), state.SMALL)

        # Confirm & Back
        btn_w2 = max(160, int(parch_rect.w * 0.25))
        btn_gap2 = 25
        btns_total = btn_w2 * 2 + btn_gap2
        bx = parch_rect.x + (parch_rect.w - btns_total) // 2
        by = parch_rect.bottom - 60

        confirm_lbl = "Confirm" if state.language == "en" else "Подтвердить"
        confirm_r = pygame.Rect(bx, by, btn_w2, 45)
        
        # Custom parchment button style for Confirm
        ch_hovered = confirm_r.collidepoint(pos)
        pygame.draw.rect(screen, (130, 150, 120) if not ch_hovered else (150, 170, 140), confirm_r, border_radius=8)
        pygame.draw.rect(screen, (80, 100, 70), confirm_r, 2, border_radius=8)
        draw_text_center(confirm_lbl, confirm_r, (240, 240, 240), state.SMALL)

        back_r = pygame.Rect(bx + btn_w2 + btn_gap2, by, btn_w2, 45)
        bh_hovered = back_r.collidepoint(pos)
        pygame.draw.rect(screen, (180, 130, 110) if not bh_hovered else (200, 150, 130), back_r, border_radius=8)
        pygame.draw.rect(screen, (130, 80, 60), back_r, 2, border_radius=8)
        draw_text_center(T("back"), back_r, (240, 240, 240), state.SMALL)

        pygame.display.flip()

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                if state.app_settings: state.app_settings.save()
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                return
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                for tr, bkey in bg_rects:
                    if tr.collidepoint(e.pos):
                        selected = bkey
                        break
                if confirm_r.collidepoint(e.pos):
                    state.app_settings.profile_bg = selected
                    state.app_settings.save()
                    return
                if back_r.collidepoint(e.pos):
                    return


def avatar_select_screen():
    """Let the player pick an avatar from available options."""
    from src.config import AVATARS_DIR, DEFAULT_AVATARS
    _avatar_cache = {}

    def _load_avatar(icon_key, size):
        cache_key = (icon_key, size)
        if cache_key in _avatar_cache:
            return _avatar_cache[cache_key]
        fp = os.path.join(AVATARS_DIR, f"{icon_key}.png")
        try:
            if os.path.exists(fp):
                img = pygame.image.load(fp).convert_alpha()
                scaled = pygame.transform.smoothscale(img, (size, size))
                _avatar_cache[cache_key] = scaled
                return scaled
        except:
            pass
        return None

    # Discover available avatars
    available = []
    if os.path.isdir(AVATARS_DIR):
        for fn in sorted(os.listdir(AVATARS_DIR)):
            if fn.lower().endswith(".png"):
                key = fn[:-4]
                available.append(key)
    if not available:
        available = DEFAULT_AVATARS

    selected = state.app_settings.player_icon
    pygame.event.clear()

    while True:
        clock.tick(FPS)
        screen = state.screen
        WIDTH = state.WIDTH
        HEIGHT = state.HEIGHT

        draw_ui_background()
        pos = pygame.mouse.get_pos()

        pw = min(720, WIDTH - 60)
        ph = min(520, HEIGHT - 60)
        panel = pygame.Rect(WIDTH // 2 - pw // 2, HEIGHT // 2 - ph // 2, pw, ph)
        draw_panel(panel, glow=True)

        title_lbl = "Choose Avatar" if state.language == "en" else "Выберите аватар"
        draw_panel_title_bar(panel, title_lbl)
        draw_text_center(title_lbl, pygame.Rect(panel.x, panel.y + 8, pw, 52), ACCENT, state.TITLE)
        pygame.draw.line(screen, (80, 75, 60), (panel.x + 30, panel.y + 64), (panel.right - 30, panel.y + 64), 1)

        # Avatar grid
        thumb_size = min(120, max(80, int((pw - 100) / min(len(available), 5) - 20)))
        cols = max(1, min(len(available), (pw - 60) // (thumb_size + 24)))
        rows = (len(available) + cols - 1) // cols
        grid_w = cols * (thumb_size + 24) - 24
        grid_h = rows * (thumb_size + 24) - 24
        grid_x = panel.x + (pw - grid_w) // 2
        grid_y = panel.y + 80 + (ph - 160 - grid_h) // 2

        avatar_rects = []
        for i, akey in enumerate(available):
            col = i % cols
            row = i // cols
            ax = grid_x + col * (thumb_size + 24)
            ay = grid_y + row * (thumb_size + 24)
            ar = pygame.Rect(ax, ay, thumb_size, thumb_size)
            avatar_rects.append((ar, akey))

            hovered = ar.collidepoint(pos)
            is_selected = (akey == selected)

            # Background
            bg_surf = pygame.Surface((thumb_size, thumb_size), pygame.SRCALPHA)
            bg_alpha = 180 if hovered else 140 if is_selected else 100
            bg_surf.fill((20, 16, 12, bg_alpha))
            screen.blit(bg_surf, ar.topleft)

            # Avatar image
            avatar_img = _load_avatar(akey, thumb_size - 12)
            if avatar_img:
                # Circular clip
                mask_s = thumb_size - 12
                mask_surf = pygame.Surface((mask_s, mask_s), pygame.SRCALPHA)
                pygame.draw.circle(mask_surf, (255, 255, 255, 255), (mask_s // 2, mask_s // 2), mask_s // 2)
                clipped = avatar_img.copy()
                clipped.blit(mask_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
                screen.blit(clipped, (ax + 6, ay + 6))

            # Border
            if is_selected:
                pygame.draw.rect(screen, (210, 175, 72), ar, 3, border_radius=12)
                # Small checkmark badge
                badge_r = 12
                badge_cx = ar.right - badge_r - 2
                badge_cy = ar.bottom - badge_r - 2
                pygame.draw.circle(screen, (40, 100, 50), (badge_cx, badge_cy), badge_r)
                pygame.draw.circle(screen, (80, 180, 90), (badge_cx, badge_cy), badge_r, 2)
                draw_text_center("✓", pygame.Rect(badge_cx - badge_r, badge_cy - badge_r,
                                                   badge_r * 2, badge_r * 2),
                                 (220, 255, 220), state.SMALL)
            elif hovered:
                pygame.draw.rect(screen, (180, 155, 80), ar, 2, border_radius=12)
            else:
                pygame.draw.rect(screen, (80, 70, 50), ar, 1, border_radius=12)

            # Name label under avatar
            name_map = {
                "trader": "Trader" if state.language == "en" else "Торговец",
                "scavenger": "Scavenger" if state.language == "en" else "Скиталица",
                "guard": "Guard" if state.language == "en" else "Охранник",
                "nomad": "Nomad" if state.language == "en" else "Кочевник",
                "wanderer": "Wanderer" if state.language == "en" else "Странник",
            }
            aname = name_map.get(akey, akey.capitalize())
            draw_text_center(aname, pygame.Rect(ax - 8, ay + thumb_size + 2, thumb_size + 16, 18),
                             (50, 40, 30) if is_selected else (140, 120, 100), state.TINY)

        # Confirm & Back buttons
        btn_w2 = max(140, int(pw * 0.24))
        btn_gap2 = 16
        btns_total = btn_w2 * 2 + btn_gap2
        bx = panel.x + (pw - btns_total) // 2

        confirm_lbl = "Confirm" if state.language == "en" else "Подтвердить"
        confirm_r = pygame.Rect(bx, panel.bottom - 58, btn_w2, 42)
        draw_button(confirm_lbl, confirm_r, pos, BTN, BTN_H, state.SMALL)

        back_r = pygame.Rect(bx + btn_w2 + btn_gap2, panel.bottom - 58, btn_w2, 42)
        draw_button(T("back"), back_r, pos, (80, 75, 68), lighten((80, 75, 68), 22), state.SMALL)

        pygame.display.flip()

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                if state.app_settings: state.app_settings.save()
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                return
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                for ar, akey in avatar_rects:
                    if ar.collidepoint(e.pos):
                        selected = akey
                        break
                if confirm_r.collidepoint(e.pos):
                    state.app_settings.player_icon = selected
                    state.app_settings.save()
                    return
                if back_r.collidepoint(e.pos):
                    return


def main_menu() -> str:
    app_settings = state.app_settings
    app_stats = state.app_stats

    MENU_TITLE_CLR = (186, 147, 72)
    MENU_SUB_CLR   = (154, 139, 104)
    MENU_INFO_CLR  = (198, 170, 94)
    MENU_BOT_COLORS = ((62, 86, 60), (86, 112, 81), (151, 178, 114))
    MENU_NET_COLORS = ((56, 72, 90), (77, 95, 116), (137, 171, 194))
    MENU_TUT_COLORS = ((96, 77, 52), (124, 98, 68), (201, 167, 104))
    MENU_CAMPAIGN_COLORS = ((92, 68, 44), (126, 92, 58), (216, 158, 86))
    MENU_SMALL_BTN = (79, 93, 65)
    MENU_SMALL_BTN_H = (103, 120, 83)
    MENU_QUIT_BTN = (118, 63, 51)
    MENU_QUIT_BTN_H = (148, 81, 66)
    _menu_anim_t = 0.0
    
    from src.network import FirebaseFriends
    import threading
    global_caps_cache = {"value": 0, "loaded": False}
    def _load_caps():
        global_caps_cache["value"] = FirebaseFriends.get_global_event()
        global_caps_cache["loaded"] = True
    threading.Thread(target=_load_caps, daemon=True).start()

    pygame.event.clear()
    while True:
        clock.tick(FPS)
        screen = state.screen
        WIDTH = state.WIDTH
        HEIGHT = state.HEIGHT
        FONT = state.FONT
        SMALL = state.SMALL
        TINY = state.TINY
        TITLE = state.TITLE
        
        _menu_anim_t += 1.0 / FPS
        draw_main_menu_background()
        pos = pygame.mouse.get_pos()

        # ── Stylized game title (non-translatable) ──
        title_y = int(HEIGHT * 0.04)
        title_text = "DUSTWAY"
        subtitle_text = "Desert Trader"

        # Build a larger title font for the main title
        title_font_size = max(28, int(72 * (WIDTH / 1280)))
        sub_font_size = max(14, int(22 * (WIDTH / 1280)))
        try:
            _title_fnt = pygame.font.SysFont("consolas", title_font_size, bold=True)
            _sub_fnt = pygame.font.SysFont("consolas", sub_font_size)
        except:
            _title_fnt = pygame.font.Font(None, title_font_size)
            _sub_fnt = pygame.font.Font(None, sub_font_size)

        # Render shadow layers for depth
        shadow_col = (40, 30, 10)
        shadow_surf = _title_fnt.render(title_text, True, shadow_col)
        sw_t = shadow_surf.get_width()
        sh_t = shadow_surf.get_height()
        sx = WIDTH // 2 - sw_t // 2
        screen.blit(shadow_surf, (sx + 3, title_y + 3))

        # Warm golden glow behind the title
        import math as _m
        glow_alpha = int(40 + 18 * _m.sin(_menu_anim_t * 1.8))
        glow_col = (220, 180, 80)
        glow_surf = pygame.Surface((sw_t + 30, sh_t + 20), pygame.SRCALPHA)
        pygame.draw.rect(glow_surf, (*glow_col, glow_alpha),
                         pygame.Rect(0, 0, sw_t + 30, sh_t + 20), border_radius=18)
        screen.blit(glow_surf, (sx - 15, title_y - 10))

        # Main golden title
        title_col = (222, 186, 92)
        main_surf = _title_fnt.render(title_text, True, title_col)
        screen.blit(main_surf, (sx, title_y))

        # Bright highlight pass (slightly offset) for emboss
        hi_col = (255, 235, 170)
        hi_surf = _title_fnt.render(title_text, True, hi_col)
        hi_mask = pygame.Surface((sw_t, sh_t), pygame.SRCALPHA)
        hi_mask.blit(hi_surf, (0, 0))
        hi_mask.fill((255, 255, 255, 45), special_flags=pygame.BLEND_RGBA_MULT)
        screen.blit(hi_mask, (sx, title_y - 1))

        # Decorative line under title
        line_w = min(sw_t + 40, int(WIDTH * 0.35))
        line_y2 = title_y + sh_t + 4
        line_x = WIDTH // 2 - line_w // 2
        for lx in range(line_w):
            frac = lx / line_w
            a = int(90 * (1.0 - abs(frac - 0.5) * 2.0))
            pygame.draw.line(screen, (186, 147, 72, a),
                             (line_x + lx, line_y2), (line_x + lx, line_y2))

        # Subtitle below the line
        sub_col = (168, 148, 108)
        sub_surf = _sub_fnt.render(subtitle_text, True, sub_col)
        screen.blit(sub_surf, (WIDTH // 2 - sub_surf.get_width() // 2, line_y2 + 6))

        tile_defs = [
            ("bot",    T("menu_vs_bot"),    T("menu_vs_bot_desc"),    "🤖", *MENU_BOT_COLORS),
            ("campaign", T("menu_campaign"), T("menu_campaign_desc"), "🗺", *MENU_CAMPAIGN_COLORS),
            ("network", T("menu_vs_player"), T("menu_vs_player_desc"), "🌐", *MENU_NET_COLORS),
            ("tutorial", T("menu_tutorial"), T("menu_tutorial_desc"),  "📖", *MENU_TUT_COLORS),
        ]
        tile_w = max(150, int(WIDTH * 0.170))
        tile_h = max(260, int(HEIGHT * 0.480))
        tile_gap = max(14, int(WIDTH * 0.018))
        total_w = len(tile_defs) * tile_w + (len(tile_defs) - 1) * tile_gap
        tile_x0 = (WIDTH - total_w) // 2
        tile_y = int(HEIGHT * 0.245)

        tile_rects = []
        for ti, (key, label, desc, icon, bg_c, bg_h, accent_c) in enumerate(tile_defs):
            tx = tile_x0 + ti * (tile_w + tile_gap)
            tr = pygame.Rect(tx, tile_y, tile_w, tile_h)
            tile_rects.append((tr, key))

            hovered = tr.collidepoint(pos)

            from src.ui import draw_menu_tile_art
            if draw_menu_tile_art(key, tr, hovered): continue

            fill = bg_h if hovered else bg_c

            ts = pygame.Surface((tile_w, tile_h), pygame.SRCALPHA)
            for gy2 in range(tile_h):
                frac = gy2 / tile_h
                r2 = int(fill[0] * (1 - frac * 0.4))
                g2 = int(fill[1] * (1 - frac * 0.4))
                b2 = int(fill[2] * (1 - frac * 0.4))
                pygame.draw.line(ts, (r2, g2, b2, 210 if hovered else 182), (0, gy2), (tile_w, gy2))
            mask = pygame.Surface((tile_w, tile_h), pygame.SRCALPHA)
            pygame.draw.rect(mask, (255, 255, 255, 255), pygame.Rect(0, 0, tile_w, tile_h), border_radius=16)
            ts.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            screen.blit(ts, tr.topleft)

            border_c = accent_c if hovered else lighten(bg_c, 30)
            pygame.draw.rect(screen, border_c, tr, 3 if hovered else 2, border_radius=16)

            if hovered:
                glow = pygame.Surface((tile_w + 8, tile_h + 8), pygame.SRCALPHA)
                pygame.draw.rect(glow, (*accent_c, 40), pygame.Rect(0, 0, tile_w + 8, tile_h + 8), border_radius=20)
                screen.blit(glow, (tr.x - 4, tr.y - 4))

            icon_font_size = max(32, int(tile_h * 0.25))
            try:
                icon_font = pygame.font.SysFont("Segoe UI Emoji", icon_font_size)
                icon_surf = icon_font.render(icon, True, accent_c)
            except:
                icon_surf = TITLE.render(icon, True, accent_c)
            ix = tr.x + (tile_w - icon_surf.get_width()) // 2
            iy = tr.y + int(tile_h * 0.12)
            screen.blit(icon_surf, (ix, iy))

            label_y2 = tr.y + int(tile_h * 0.52)
            draw_text_center(label, pygame.Rect(tr.x, label_y2, tile_w, int(tile_h * 0.14)), (240, 235, 210), FONT)

            desc_y2 = tr.y + int(tile_h * 0.68)
            draw_text_center(desc, pygame.Rect(tr.x + 8, desc_y2, tile_w - 16, int(tile_h * 0.20)), (191, 178, 146), TINY)

        # ── Bottom: two compact buttons ──
        bar_y = int(HEIGHT * 0.88)
        bar_h = max(48, int(HEIGHT * 0.065))
        btn_w2 = max(160, int(WIDTH * 0.15))
        btn_gap2 = max(16, int(WIDTH * 0.02))
        total_w2 = btn_w2 * 2 + btn_gap2
        bx_start = (WIDTH - total_w2) // 2

        settings_lbl = T("settings")
        profile_lbl = "Profile" if state.language == "en" else "Профиль"

        settings_r = pygame.Rect(bx_start, bar_y, btn_w2, bar_h)
        profile_r = pygame.Rect(bx_start + btn_w2 + btn_gap2, bar_y, btn_w2, bar_h)

        draw_button(settings_lbl, settings_r, pos, MENU_SMALL_BTN, MENU_SMALL_BTN_H, FONT)
        draw_button(profile_lbl, profile_r, pos, MENU_SMALL_BTN, MENU_SMALL_BTN_H, FONT)

        # Quit button in bottom-right corner
        quit_lbl = "EXIT" if state.language == "en" else "ВЫХОД"
        quit_w = max(100, int(WIDTH * 0.08))
        quit_h = max(40, int(HEIGHT * 0.055))
        quit_r = pygame.Rect(WIDTH - quit_w - 20, HEIGHT - quit_h - 20, quit_w, quit_h)
        draw_button(quit_lbl, quit_r, pos, MENU_QUIT_BTN, MENU_QUIT_BTN_H, SMALL)

        # Wasteland Fund (Community Event)
        fund_w = max(420, int(WIDTH * 0.45))
        fund_h = 22
        fund_x = WIDTH // 2 - fund_w // 2
        fund_y = int(HEIGHT * 0.80)
        
        # Draw dark backdrop for contrast
        bg_rect = pygame.Rect(fund_x - 30, fund_y - 35, fund_w + 60, fund_h + 50)
        backdrop = pygame.Surface((bg_rect.w, bg_rect.h), pygame.SRCALPHA)
        pygame.draw.rect(backdrop, (20, 15, 10, 150), backdrop.get_rect(), border_radius=16)
        screen.blit(backdrop, bg_rect.topleft)

        pygame.draw.rect(screen, (50, 40, 30), (fund_x, fund_y, fund_w, fund_h), border_radius=12)
        
        target = 100000
        current = global_caps_cache["value"]
        frac = min(1.0, current / target)
        
        if frac > 0:
            fill_r = pygame.Rect(fund_x, fund_y, int(fund_w * frac), fund_h)
            pygame.draw.rect(screen, (220, 170, 50), fill_r, border_radius=12)
            pygame.draw.rect(screen, (255, 210, 100), (fund_x, fund_y, int(fund_w * frac), fund_h//2), border_radius=12)
        
        fund_lbl = f"Wasteland Fund: {current} / {target} Caps" if state.language == "en" else f"Фонд Пустоши: {current} / {target} Крышек"
        
        draw_text_center(fund_lbl, pygame.Rect(fund_x + 2, fund_y - 30 + 2, fund_w, 20), (10, 10, 10), FONT)
        draw_text_center(fund_lbl, pygame.Rect(fund_x, fund_y - 30, fund_w, 20), (255, 230, 150), FONT)
        
        pygame.draw.rect(screen, (190, 160, 100), (fund_x, fund_y, fund_w, fund_h), 2, border_radius=12)

        draw_text_center("v4.0  Ultimate Edition", pygame.Rect(0, int(HEIGHT * 0.95), WIDTH, int(HEIGHT * 0.04)), MENU_SUB_CLR, TINY)
        pygame.display.flip()

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                app_settings.save()
                pygame.quit()
                sys.exit()
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                for tr2, key in tile_rects:
                    if tr2.collidepoint(e.pos): return key
                if settings_r.collidepoint(e.pos):
                    settings_menu()
                elif profile_r.collidepoint(e.pos):
                    profile_screen()
                elif quit_r.collidepoint(e.pos):
                    app_settings.save()
                    pygame.quit()
                    sys.exit()


def end_screen(text, elapsed_ms, caps_delta=0, result_context: str = "match"):
    screen = state.screen
    WIDTH = state.WIDTH
    HEIGHT = state.HEIGHT
    app_settings = state.app_settings
    app_stats = state.app_stats
    sounds = state.sounds
    particles = state.particles
    is_win = ("player" in text.lower() or "игрок" in text.lower() or
              "p1" in text.lower() or "игр. 1" in text.lower() or "bot a" in text.lower())
    is_draw = ("draw" in text.lower() or "ничья" in text.lower())
    
    # Use harmonious colors
    hdr_col = ACCENT if is_win else (TEXT_DIM if is_draw else RED)
    
    if sounds: sounds.play("win" if is_win else "lose")
    if is_win and particles: particles.confetti(80)
    
    if caps_delta > 0 and result_context == "match":
        from src.network import FirebaseFriends
        FirebaseFriends.add_to_global_event(caps_delta // 10)
        
    pygame.event.clear()

    while True:
        clock.tick(FPS)
        # Adjust panel size to be more compact and elegant
        pw, ph = min(560, WIDTH - 40), min(400, HEIGHT - 60)
        panel = pygame.Rect(WIDTH // 2 - pw // 2, HEIGHT // 2 - ph // 2, pw, ph)
        
        draw_ui_background()
        if particles: particles.tick_draw(screen)
        
        draw_panel(panel, glow=is_win)
        draw_panel_title_bar(panel, text, color=hdr_col)
        
        # Title
        draw_text_center(text, pygame.Rect(panel.x, panel.y + 12, pw, 46), hdr_col, state.TITLE)
        
        # Fancy separator
        sep_y = panel.y + 68
        pygame.draw.line(screen, hdr_col, (panel.x + 40, sep_y), (panel.right - 40, sep_y), 2)
        pygame.draw.line(screen, PANEL_BORD, (panel.x + 20, sep_y + 3), (panel.right - 20, sep_y + 3), 1)
        
        # Stats layout
        content_y = sep_y + 20
        draw_text_center(T("match_time", format_time_ms(elapsed_ms)), pygame.Rect(panel.x, content_y, pw, 30), TEXT, state.FONT)
        
        content_y += 35
        draw_text_center(T("stats_end", app_stats.wins, app_stats.losses, app_stats.draws, app_stats.avg_time_str()), pygame.Rect(panel.x, content_y, pw, 24), TEXT_DIM, state.SMALL)
        
        content_y += 45
        if caps_delta != 0:
            cc = ACCENT if caps_delta > 0 else RED
            cdelta_txt = T("caps_won", caps_delta) if caps_delta > 0 else T("caps_lost", abs(caps_delta))
            sign = "+" if caps_delta > 0 else "-"
            # Make the reward stand out
            draw_text_center(f"{sign} {abs(caps_delta)} CAPS", pygame.Rect(panel.x, content_y, pw, 40), cc, state.TITLE)
            content_y += 40
            
        draw_text_center(f"Total: {app_settings.caps} caps", pygame.Rect(panel.x, content_y, pw, 26), CAPS_CLR, state.FONT)
        
        # Buttons
        pos = pygame.mouse.get_pos()
        bw2 = max(180, int(pw * 0.38))
        gap2 = (pw - (bw2 * 2)) // 3
        
        btn_y = panel.bottom - 80
        left_r = pygame.Rect(panel.x + gap2, btn_y, bw2, 54)
        menu_r = pygame.Rect(panel.x + gap2 * 2 + bw2, btn_y, bw2, 54)

        if result_context == "campaign":
            left_label = "Continue" if state.language == "en" else "Продолжить"
            left_return = "continue"
        else:
            left_label = T("play_again")
            left_return = "restart"

        draw_button(left_label, left_r, pos)
        draw_button(T("main_menu_btn"), menu_r, pos, (100, 28, 28), lighten((100, 28, 28), 30))
        
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                app_settings.save()
                pygame.quit()
                sys.exit()
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if left_r.collidepoint(e.pos): return left_return
                if menu_r.collidepoint(e.pos): return "menu"


def hot_seat_pass_screen(player_name: str):
    pygame.event.clear()
    screen = state.screen
    WIDTH = state.WIDTH
    HEIGHT = state.HEIGHT
    while True:
        clock.tick(FPS)
        draw_ui_background()
        pw, ph = min(500, WIDTH - 40), min(250, HEIGHT - 80)
        panel = pygame.Rect(WIDTH // 2 - pw // 2, HEIGHT // 2 - ph // 2, pw, ph)
        draw_panel(panel, glow=True)
        
        title = T("pass_screen_title", player_name)
        draw_text_center(title, pygame.Rect(panel.x, panel.y + 20, pw, 40), ACCENT, state.FONT)
        
        hint = T("pass_screen_hint")
        draw_text_center(hint, pygame.Rect(panel.x, panel.y + 80, pw, 30), TEXT_DIM, SMALL)
        
        pos = pygame.mouse.get_pos()
        btn_r = pygame.Rect(panel.centerx - 80, panel.bottom - 60, 160, 40)
        draw_button("OK", btn_r, pos)
        
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                if state.app_settings: state.app_settings.save()
                pygame.quit()
                sys.exit()
            if e.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
                if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    if btn_r.collidepoint(e.pos): return
                elif e.type == pygame.KEYDOWN:
                    if e.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE): return


def tournament_results_screen(results: List[Tuple[int, str, str]]):
    pygame.event.clear()
    screen = state.screen
    WIDTH = state.WIDTH
    HEIGHT = state.HEIGHT
    while True:
        clock.tick(FPS)
        draw_ui_background()
        pw, ph = min(600, WIDTH - 40), min(450, HEIGHT - 80)
        panel = pygame.Rect(WIDTH // 2 - pw // 2, HEIGHT // 2 - ph // 2, pw, ph)
        draw_panel(panel, glow=True)
        draw_panel_title_bar(panel, T("tourn_title"))
        
        draw_text_center(T("tourn_title"), pygame.Rect(panel.x, panel.y + 10, pw, 46), ACCENT, state.TITLE)
        
        won_all = all(r[1] == "win" for r in results) and len(results) == 3
        if won_all:
            msg = T("tourn_champion")
            color = OUT_OK
        else:
            msg = T("tourn_eliminated", results[-1][0]) if results else "Tournament Over"
            color = RED
            
        draw_text_center(msg, pygame.Rect(panel.x, panel.y + 66, pw, 36), color, state.FONT)
        
        box = pygame.Rect(panel.x + 30, panel.y + 110, pw - 60, ph - 180)
        pygame.draw.rect(screen, PANEL_BORD, box, 1, border_radius=10)
        
        for i, (rnd, outcome, diff) in enumerate(results):
            ry = box.y + 16 + i * 44
            outcome_lbl = T("tourn_win") if outcome == "win" else T("tourn_loss")
            outcome_col = OUT_OK if outcome == "win" else RED
            draw_text(T("tourn_round", rnd), box.x + 20, ry, TEXT, SMALL)
            draw_text(diff.upper(), box.x + 180, ry, TEXT_DIM, SMALL)
            draw_text(outcome_lbl, box.right - 120, ry, outcome_col, SMALL)
            
        pos = pygame.mouse.get_pos()
        btn_r = pygame.Rect(panel.centerx - 100, panel.bottom - 54, 200, 42)
        draw_button(T("back"), btn_r, pos)
        
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                if state.app_settings: state.app_settings.save()
                pygame.quit()
                sys.exit()
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if btn_r.collidepoint(e.pos): return
            if e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE): return


def run_match(diff: str, game_mode: str = GM_NORMAL,
              personality_key: str = DEFAULT_PERSONALITY,
              bet: int = 0,
              result_context: str = "match") -> Tuple[str, int, int]:
    WIDTH = state.WIDTH
    HEIGHT = state.HEIGHT
    app_settings = state.app_settings
    app_stats = state.app_stats
    sounds = state.sounds
    particles = state.particles

    sel_keys = load_deck_selection()
    if sel_keys: sel_keys = ensure_min30_selection(sel_keys)
    p_deck = build_deck_from_selection(sel_keys)
    b_deck = build_deck_from_selection(sel_keys if app_settings.bot_uses_player_deck else None)

    p_name = "Player 1" if game_mode == GM_HOT_SEAT else app_settings.player_name
    b_name = "Player 2" if game_mode == GM_HOT_SEAT else "Bot"

    player = PlayerState(p_name, [Caravan() for _ in range(3)], p_deck, [], [])
    bot = PlayerState(b_name, [Caravan() for _ in range(3)], b_deck, [], [])
    draw_to_hand(player, HAND_OPENING_SIZE)
    draw_to_hand(bot, HAND_OPENING_SIZE)

    phase = "OPENING"
    opening_halfturn = 0
    match_start_ms = pygame.time.get_ticks()
    selected = -1
    drag_card_idx = -1
    drag_pos = (0, 0)
    drag_offset = (0, 0)
    drag_moved = False
    drag_was_selected = False
    msg = ""
    msg_until = 0
    hand_scroll = 0
    player_to_move = True
    pending_bot = False
    pending_at = 0
    undo_stack: List[Tuple] = []
    consecutive_discards = 0
    hitboxes_dirty = True
    cached_hit: Optional[Dict] = None
    winner_choice = None
    running = True
    turn_start_ms = match_start_ms
    player_lost_first = False

    while running:
        clock.tick(FPS)
        now = pygame.time.get_ticks()

        if game_mode == GM_TIMED and phase == "MAIN" and player_to_move and not pending_bot:
            if now - turn_start_ms >= TIMED_TURN_MS:
                if player.hand:
                    if sounds: sounds.play("discard")
                    if undo_stack and len(undo_stack) >= UNDO_LEVELS: undo_stack.pop(0)
                    undo_stack.append(take_snapshot(player, bot))
                    discard_hand_card(player, 0)
                    draw_to_hand(player, HAND_TARGET_SIZE)
                    consecutive_discards += 1
                    hitboxes_dirty = True
                    if game_mode != GM_HOT_SEAT:
                        pending_bot = True
                        pending_at = now + get_bot_delay_ms(diff, personality_key)
                    player_to_move = False
                    selected = -1
                    turn_start_ms = now
                    msg = T("timer_expired")
                    msg_until = now + 1200

        if hitboxes_dirty:
            _, ba_, pa_, _ = ui_rects()
            cached_hit = {
                "bot":    build_entry_hitboxes("bot",   caravan_slots(ba_), bot.caravans),
                "player": build_entry_hitboxes("player", caravan_slots(pa_), player.caravans),
            }
            hitboxes_dirty = False

        ui = draw_board(
            player=player, bot=bot, selected_idx=selected, msg=msg, msg_until=msg_until,
            start_ms=match_start_ms, phase=phase, bot_diff=diff, hand_scroll=hand_scroll,
            pending_bot=pending_bot, undo_count=len(undo_stack),
            consecutive_discards=consecutive_discards, cached_hitboxes=cached_hit,
            game_mode=game_mode, turn_start_ms=turn_start_ms, personality_key=personality_key,
            p2_label=b_name, drag_card_idx=drag_card_idx, drag_pos=drag_pos
        )
        hand_scroll = ui.hand_scroll

        if game_mode != GM_HOT_SEAT and phase == "MAIN" and pending_bot and now >= pending_at:
            ok2, rmsg, was_play = bot_take_turn(bot, player, diff, personality_key)
            pending_bot = False
            player_to_move = True
            selected = -1
            hitboxes_dirty = True
            turn_start_ms = now
            consecutive_discards = (0 if was_play else consecutive_discards + 1)
            if not ok2:
                elapsed = now - match_start_ms
                app_stats.record("win", elapsed)
                app_stats.save()
                if sounds: sounds.play("win")
                caps_delta = int(bet * {"easy": 1.0, "medium": 1.2, "hard": 1.5, "impossible": 2.0}.get(diff, 1.0)) if bet > 0 else 0
                app_settings.caps += caps_delta
                app_settings.save()
                check_post_match_achievements("win", diff, game_mode, elapsed, player_lost_first=player_lost_first, all_three=False)
                add_history("win", diff, game_mode, elapsed, caps_delta)
                wc = end_screen(T("player_wins_deck"), elapsed, caps_delta, result_context)
                return wc, elapsed, caps_delta
            elif rmsg:
                msg = rmsg
                msg_until = now + 1600

        if msg and now >= msg_until: msg = ""

        if phase == "MAIN" and running:
            if not player_lost_first:
                player_has_won = any(
                    slot_outcome(player.caravans[_i].score(), player.caravans[_i].for_sale(),
                                 bot.caravans[_i].score(),    bot.caravans[_i].for_sale())[1] == "player"
                    for _i in range(3)
                )
                if not player_has_won:
                    for _i in range(3):
                        _st, _w = slot_outcome(
                            player.caravans[_i].score(), player.caravans[_i].for_sale(),
                            bot.caravans[_i].score(),    bot.caravans[_i].for_sale()
                        )
                        if _st == "ready" and _w == "bot":
                            player_lost_first = True
                            break

            ended, win, _ = check_game_end(player, bot)
            if ended:
                elapsed = now - match_start_ms
                wp = sum(1 for i in range(3) if slot_outcome(
                    player.caravans[i].score(), player.caravans[i].for_sale(),
                    bot.caravans[i].score(), bot.caravans[i].for_sale())[1] == "player")
                all_three = (wp == 3) if win == "player" else False

                result = "win" if win == "player" else "loss"
                app_stats.record(result, elapsed)
                app_stats.save()
                if sounds: sounds.play("win" if result == "win" else "lose")
                mults = {"easy": 1.0, "medium": 1.2, "hard": 1.5, "impossible": 2.0}
                if result == "win":
                    caps_delta = int(bet * mults.get(diff, 1.0)) if bet > 0 else 0
                    app_settings.caps += caps_delta
                else:
                    caps_delta = -bet if bet > 0 else 0
                    app_settings.caps = max(0, app_settings.caps + caps_delta)
                app_settings.save()
                check_post_match_achievements(result, diff, game_mode, elapsed, player_lost_first=player_lost_first, all_three=all_three)
                add_history(result, diff, game_mode, elapsed, caps_delta)
                if game_mode == GM_TOURNAMENT:
                    return ("tournament_win" if result == "win" else "tournament_loss"), elapsed, caps_delta
                if game_mode == GM_HOT_SEAT:
                    winner_name = player.name if win == "player" else bot.name
                    wtxt = T("p1_wins") if winner_name == p_name else T("p2_wins")
                else:
                    wtxt = T("player_wins") if win == "player" else T("bot_wins")
                wc = end_screen(wtxt, elapsed, caps_delta, result_context)
                return wc, elapsed, caps_delta
            if consecutive_discards >= STALEMATE_THRESHOLD:
                elapsed = now - match_start_ms
                app_stats.record("draw", elapsed)
                app_stats.save()
                caps_delta = -bet // 2 if bet > 0 else 0
                app_settings.caps = max(0, app_settings.caps + caps_delta)
                app_settings.save()
                add_history("draw", diff, game_mode, elapsed, caps_delta)
                if game_mode == GM_TOURNAMENT:
                    return "tournament_loss", elapsed, caps_delta
                wc = end_screen(T("draw_stalemate"), elapsed, caps_delta, result_context)
                return wc, elapsed, caps_delta

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                app_settings.save()
                pygame.quit()
                sys.exit()

            if e.type == pygame.MOUSEMOTION:
                if drag_card_idx != -1:
                    drag_moved = True
                    drag_pos = (e.pos[0] + drag_offset[0], e.pos[1] + drag_offset[1])

            if e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                if drag_card_idx != -1:
                    hi = get_idx_at(e.pos, ui.hand_rects)
                    if hi == -1:
                        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': e.pos, 'button': 1, 'injected': True}))
                    else:
                        if not drag_moved and drag_was_selected and hi == drag_card_idx:
                            selected = -1
                    drag_card_idx = -1

            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    result = pause_menu(allow_undo=len(undo_stack) > 0)
                    if result == "quit_match":
                        elapsed = now - match_start_ms
                        app_stats.record("loss", elapsed)
                        app_stats.save()
                        if bet > 0:
                            app_settings.caps = max(0, app_settings.caps - bet)
                            app_settings.save()
                        add_history("loss", diff, game_mode, elapsed, -bet)
                        return "menu", elapsed, -bet
                    hitboxes_dirty = True
                    continue
                n = len(player.hand)
                if e.key == pygame.K_RIGHT and n > 0: selected = (max(selected, 0) + 1) % n
                elif e.key == pygame.K_LEFT and n > 0: selected = (max(selected, 0) - 1) % n

                if phase == "MAIN" and player_to_move:
                    if e.key == pygame.K_u and undo_stack:
                        player, bot = restore_snapshot(undo_stack.pop())
                        selected = -1
                        consecutive_discards = 0
                        hitboxes_dirty = True
                        turn_start_ms = now
                        msg = T("undone")
                        msg_until = now + 800
                        continue
                    if e.key == pygame.K_d and 0 <= selected < len(player.hand):
                        if len(undo_stack) >= UNDO_LEVELS: undo_stack.pop(0)
                        undo_stack.append(take_snapshot(player, bot))
                        if sounds: sounds.play("discard")
                        if discard_hand_card(player, selected):
                            if not draw_to_hand(player, HAND_TARGET_SIZE):
                                elapsed = now - match_start_ms
                                app_stats.record("loss", elapsed)
                                app_stats.save()
                                caps_delta = -bet if bet > 0 else 0
                                app_settings.caps = max(0, app_settings.caps + caps_delta)
                                app_settings.save()
                                add_history("loss", diff, game_mode, elapsed, caps_delta)
                                wc = end_screen(T("bot_wins_deck"), elapsed, caps_delta, result_context)
                                return wc, elapsed, caps_delta
                            consecutive_discards += 1
                            hitboxes_dirty = True
                            if game_mode == GM_HOT_SEAT:
                                player_to_move = False
                                selected = -1
                                turn_start_ms = now
                                hot_seat_pass_screen(b_name)
                                player, bot = bot, player
                                hitboxes_dirty = True
                                player_to_move = True
                            else:
                                pending_bot = True
                                pending_at = now + get_bot_delay_ms(diff, personality_key)
                                player_to_move = False
                                selected = -1
                                turn_start_ms = now
                        else:
                            undo_stack.pop()
                    cav_keys = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2}
                    if e.key in cav_keys and 0 <= selected < len(player.hand):
                        ci = cav_keys[e.key]
                        c = player.hand[selected]
                        if c.is_number():
                            if len(undo_stack) >= UNDO_LEVELS: undo_stack.pop(0)
                            undo_stack.append(take_snapshot(player, bot))
                            ok, emsg = play_number(player, selected, ci)
                            if not ok:
                                msg = emsg
                                msg_until = now + 1400
                                undo_stack.pop()
                            else:
                                if sounds: sounds.play("play_card")
                                selected = -1
                                hitboxes_dirty = True
                                consecutive_discards = 0
                                if not draw_to_hand(player, HAND_TARGET_SIZE):
                                    elapsed = now - match_start_ms
                                    app_stats.record("loss", elapsed)
                                    app_stats.save()
                                    caps_delta = -bet if bet > 0 else 0
                                    app_settings.caps = max(0, app_settings.caps + caps_delta)
                                    app_settings.save()
                                    add_history("loss", diff, game_mode, elapsed, caps_delta)
                                    wc = end_screen(T("bot_wins_deck"), elapsed, caps_delta, result_context)
                                    return wc, elapsed, caps_delta
                                if game_mode == GM_HOT_SEAT:
                                    player_to_move = False
                                    turn_start_ms = now
                                    hot_seat_pass_screen(b_name)
                                    player, bot = bot, player
                                    hitboxes_dirty = True
                                    player_to_move = True
                                else:
                                    pending_bot = True
                                    pending_at = now + get_bot_delay_ms(diff, personality_key)
                                    player_to_move = False
                                    turn_start_ms = now

            if e.type == pygame.MOUSEWHEEL and ui.hand_scroll_on:
                hand_scroll = max(0, min(ui.hand_max_scroll, hand_scroll - e.y * 50))

            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if ui.pause_btn.collidepoint(*e.pos):
                    result = pause_menu(allow_undo=len(undo_stack) > 0)
                    if result == "quit_match":
                        elapsed = now - match_start_ms
                        app_stats.record("loss", elapsed)
                        app_stats.save()
                        caps_delta = -bet if bet > 0 else 0
                        app_settings.caps = max(0, app_settings.caps + caps_delta)
                        app_settings.save()
                        add_history("loss", diff, game_mode, elapsed, caps_delta)
                        return "menu", elapsed, caps_delta
                    hitboxes_dirty = True
                    continue

            if phase == "OPENING" and player_to_move:
                if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    mpos = e.pos
                    hi = get_idx_at(mpos, ui.hand_rects)
                    if hi != -1:
                        drag_was_selected = (selected == hi)
                        selected = hi
                        drag_card_idx = hi
                        drag_moved = False
                        drag_offset = (ui.hand_rects[hi].x - mpos[0], ui.hand_rects[hi].y - mpos[1])
                        drag_pos = (mpos[0] + drag_offset[0], mpos[1] + drag_offset[1])
                        continue
                    if 0 <= selected < len(player.hand):
                        c = player.hand[selected]
                        if not c.is_number():
                            msg = T("opening_nums_only")
                            msg_until = now + 1200
                            selected = -1
                            continue
                        for ci, r in enumerate(ui.ply_slots):
                            if r.collidepoint(*mpos):
                                if not player.caravans[ci].empty():
                                    msg = T("caravan_started")
                                    msg_until = now + 1200
                                    selected = -1
                                    break
                                if sounds: sounds.play("deal")
                                card = player.hand.pop(selected)
                                player.caravans[ci].nums.append(NumEntry(card=card))
                                selected = -1
                                hitboxes_dirty = True
                                opening_halfturn += 1
                                player_to_move = False
                                if game_mode == GM_HOT_SEAT:
                                    hot_seat_pass_screen(b_name)
                                    player, bot = bot, player
                                    hitboxes_dirty = True
                                    player_to_move = True
                                    opening_halfturn += 1
                                else:
                                    bot_opening_play(bot)
                                    opening_halfturn += 1
                                    player_to_move = True
                                    hitboxes_dirty = True
                                if opening_halfturn >= 6:
                                    phase = "MAIN"
                                    player.hand = player.hand[:HAND_TARGET_SIZE]
                                    bot.hand = bot.hand[:HAND_TARGET_SIZE]
                                    if not draw_to_hand(player, HAND_TARGET_SIZE):
                                        elapsed = now - match_start_ms
                                        app_stats.record("loss", elapsed)
                                        app_stats.save()
                                        wc = end_screen(T("bot_wins_deck"), elapsed, 0, result_context)
                                        return wc, elapsed, 0
                                    if not draw_to_hand(bot, HAND_TARGET_SIZE):
                                        elapsed = now - match_start_ms
                                        app_stats.record("win", elapsed)
                                        app_stats.save()
                                        wc = end_screen(T("player_wins_deck"), elapsed, 0, result_context)
                                        return wc, elapsed, 0
                                    turn_start_ms = now
                                break
                continue

            if phase == "MAIN" and player_to_move:
                if e.type == pygame.MOUSEBUTTONDOWN:
                    mpos = e.pos
                    if e.button == 3:
                        hi = get_idx_at(mpos, ui.hand_rects)
                        if hi != -1:
                            if len(undo_stack) >= UNDO_LEVELS: undo_stack.pop(0)
                            undo_stack.append(take_snapshot(player, bot))
                            if sounds: sounds.play("discard")
                            if discard_hand_card(player, hi):
                                if not draw_to_hand(player, HAND_TARGET_SIZE):
                                    elapsed = now - match_start_ms
                                    app_stats.record("loss", elapsed)
                                    app_stats.save()
                                    caps_delta = -bet if bet > 0 else 0
                                    app_settings.caps = max(0, app_settings.caps + caps_delta)
                                    app_settings.save()
                                    add_history("loss", diff, game_mode, elapsed, caps_delta)
                                    wc = end_screen(T("bot_wins_deck"), elapsed, caps_delta, result_context)
                                    return wc, elapsed, caps_delta
                                consecutive_discards += 1
                                hitboxes_dirty = True
                                if game_mode == GM_HOT_SEAT:
                                    player_to_move = False
                                    turn_start_ms = now
                                    hot_seat_pass_screen(b_name)
                                    player, bot = bot, player
                                    hitboxes_dirty = True
                                    player_to_move = True
                                else:
                                    pending_bot = True
                                    pending_at = now + get_bot_delay_ms(diff, personality_key)
                                    player_to_move = False
                                    selected = -1
                                    turn_start_ms = now
                            else:
                                undo_stack.pop()
                            continue
                        for ci, r in enumerate(ui.ply_slots):
                            if r.collidepoint(*mpos):
                                if len(undo_stack) >= UNDO_LEVELS: undo_stack.pop(0)
                                undo_stack.append(take_snapshot(player, bot))
                                if disband_caravan(player, ci):
                                    if not draw_to_hand(player, HAND_TARGET_SIZE):
                                        elapsed = now - match_start_ms
                                        app_stats.record("loss", elapsed)
                                        app_stats.save()
                                        caps_delta = -bet if bet > 0 else 0
                                        app_settings.caps = max(0, app_settings.caps + caps_delta)
                                        app_settings.save()
                                        add_history("loss", diff, game_mode, elapsed, caps_delta)
                                        wc = end_screen(T("bot_wins_deck"), elapsed, caps_delta, result_context)
                                        return wc, elapsed, caps_delta
                                    consecutive_discards += 1
                                    hitboxes_dirty = True
                                    if game_mode == GM_HOT_SEAT:
                                        player_to_move = False
                                        turn_start_ms = now
                                        hot_seat_pass_screen(b_name)
                                        player, bot = bot, player
                                        hitboxes_dirty = True
                                        player_to_move = True
                                    else:
                                        pending_bot = True
                                        pending_at = now + get_bot_delay_ms(diff, personality_key)
                                        player_to_move = False
                                        selected = -1
                                        turn_start_ms = now
                                else:
                                    undo_stack.pop()
                                    msg = T("nothing_disband")
                                    msg_until = now + 1000
                                    selected = -1
                                break
                        continue
                    if e.button == 1:
                        hi = get_idx_at(mpos, ui.hand_rects)
                        if hi != -1:
                            drag_was_selected = (selected == hi)
                            selected = hi
                            drag_card_idx = hi
                            drag_moved = False
                            drag_offset = (ui.hand_rects[hi].x - mpos[0], ui.hand_rects[hi].y - mpos[1])
                            drag_pos = (mpos[0] + drag_offset[0], mpos[1] + drag_offset[1])
                            continue
                        if selected < 0 or selected >= len(player.hand): continue
                        c = player.hand[selected]
                        if c.is_number():
                            for ci, r in enumerate(ui.ply_slots):
                                if r.collidepoint(*mpos):
                                    if len(undo_stack) >= UNDO_LEVELS: undo_stack.pop(0)
                                    undo_stack.append(take_snapshot(player, bot))
                                    ok, emsg = play_number(player, selected, ci)
                                    selected = -1
                                    if not ok:
                                        msg = emsg
                                        msg_until = now + 1400
                                        undo_stack.pop()
                                        break
                                    if sounds: sounds.play("play_card")
                                    consecutive_discards = 0
                                    hitboxes_dirty = True
                                    if not draw_to_hand(player, HAND_TARGET_SIZE):
                                        elapsed = now - match_start_ms
                                        app_stats.record("loss", elapsed)
                                        app_stats.save()
                                        caps_delta = -bet if bet > 0 else 0
                                        app_settings.caps = max(0, app_settings.caps + caps_delta)
                                        app_settings.save()
                                        add_history("loss", diff, game_mode, elapsed, caps_delta)
                                        wc = end_screen(T("bot_wins_deck"), elapsed, caps_delta, result_context)
                                        return wc, elapsed, caps_delta
                                    if game_mode == GM_HOT_SEAT:
                                        player_to_move = False
                                        turn_start_ms = now
                                        hot_seat_pass_screen(b_name)
                                        player, bot = bot, player
                                        hitboxes_dirty = True
                                        player_to_move = True
                                    else:
                                        pending_bot = True
                                        pending_at = now + get_bot_delay_ms(diff, personality_key)
                                        player_to_move = False
                                        turn_start_ms = now
                                    break
                            continue
                        if c.is_picture():
                            hit = None
                            for r, own, ci, ei in reversed(ui.ply_boxes + ui.bot_boxes):
                                if r.collidepoint(*mpos):
                                    hit = (own, ci, ei)
                                    break
                            if not hit:
                                msg = T("face_needs_target")
                                msg_until = now + 1200
                                selected = -1
                                continue
                            own, ci, ei = hit
                            tgt = player if own == "player" else bot
                            if len(undo_stack) >= UNDO_LEVELS: undo_stack.pop(0)
                            undo_stack.append(take_snapshot(player, bot))
                            ok, emsg = play_picture(player, bot, selected, tgt, ci, ei)
                            selected = -1
                            if not ok:
                                msg = emsg
                                msg_until = now + 1500
                                undo_stack.pop()
                                continue
                            pic_played = player.discard[-1] if player.discard else None
                            if pic_played and sounds:
                                if pic_played.rank == "J": sounds.play("jack")
                                elif pic_played.rank == "JKR":
                                    sounds.play("joker")
                                    trigger_shake(10, 400)
                                elif pic_played.rank == "K": sounds.play("king")
                                else: sounds.play("play_card")
                            consecutive_discards = 0
                            hitboxes_dirty = True
                            if not draw_to_hand(player, HAND_TARGET_SIZE):
                                elapsed = now - match_start_ms
                                app_stats.record("loss", elapsed)
                                app_stats.save()
                                caps_delta = -bet if bet > 0 else 0
                                app_settings.caps = max(0, app_settings.caps + caps_delta)
                                app_settings.save()
                                add_history("loss", diff, game_mode, elapsed, caps_delta)
                                wc = end_screen(T("bot_wins_deck"), elapsed, caps_delta, result_context)
                                return wc, elapsed, caps_delta
                            if game_mode == GM_HOT_SEAT:
                                player_to_move = False
                                turn_start_ms = now
                                hot_seat_pass_screen(b_name)
                                player, bot = bot, player
                                hitboxes_dirty = True
                                player_to_move = True
                            else:
                                pending_bot = True
                                pending_at = now + get_bot_delay_ms(diff, personality_key)
                                player_to_move = False
                                turn_start_ms = now

    return "menu", 0, 0


def run_tournament(personality_key: str):
    diffs = ["easy", "medium", "hard"]
    results = []
    for rnd, diff in enumerate(diffs, 1):
        bet = betting_menu(diff)
        if bet is None: return "menu"
        wc, elapsed, caps_delta = run_match(diff, GM_TOURNAMENT, personality_key, bet)
        if wc == "tournament_win":
            results.append((rnd, "win", diff))
        else:
            results.append((rnd, "loss", diff))
            tournament_results_screen(results)
            return "menu"
    if all(r[1] == "win" for r in results):
        unlock_achievement("TOURN_CHAMP")
    tournament_results_screen(results)
    return "menu"


def name_input_screen(current: str = "Player") -> str:
    screen = state.screen
    WIDTH = state.WIDTH
    HEIGHT = state.HEIGHT
    name = list(current[:16])
    pygame.event.clear()
    while True:
        clock.tick(FPS)
        pw, ph = min(460, WIDTH - 40), min(220, HEIGHT - 80)
        panel = pygame.Rect(WIDTH // 2 - pw // 2, HEIGHT // 2 - ph // 2, pw, ph)
        draw_ui_background()
        draw_panel(panel)
        title = "Enter your name:" if state.language == "en" else "Введите имя:"
        draw_text_center(title, pygame.Rect(panel.x, panel.y + 12, pw, 36), ACCENT, state.FONT)
        tb = pygame.Rect(panel.x + 30, panel.y + 60, pw - 60, 48)
        pygame.draw.rect(screen, (20, 35, 22), tb, border_radius=8)
        pygame.draw.rect(screen, ACCENT, tb, 2, border_radius=8)
        disp = "".join(name) + ("_" if (pygame.time.get_ticks() // 500) % 2 == 0 else " ")
        draw_text_center(disp, tb, TEXT, state.FONT)
        pos = pygame.mouse.get_pos()
        ok_r = pygame.Rect(panel.x + pw // 2 - 80, panel.y + ph - 62, 160, 46)
        draw_button("OK", ok_r, pos)
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                if state.app_settings: state.app_settings.save()
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_RETURN or e.key == pygame.K_KP_ENTER:
                    return "".join(name).strip() or current
                elif e.key == pygame.K_ESCAPE:
                    return current
                elif e.key == pygame.K_BACKSPACE:
                    if name: name.pop()
                else:
                    ch = e.unicode
                    if ch and ch.isprintable() and len(name) < 16:
                        name.append(ch)
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if ok_r.collidepoint(e.pos):
                    return "".join(name).strip() or current

def restore_profile_input_screen():
    from src.network import FirebaseFriends
    import threading
    screen = state.screen
    WIDTH = state.WIDTH
    HEIGHT = state.HEIGHT
    code = []
    pygame.event.clear()
    
    status_msg = ""
    status_color = TEXT
    
    is_loading = False
    
    def _do_restore(friend_code):
        nonlocal status_msg, status_color, is_loading
        d = FirebaseFriends.lookup_friend(friend_code)
        if d:
            state.app_settings.friend_code = friend_code
            state.app_settings.player_name = d.get("name", "Player")
            state.app_settings.caps = d.get("caps", 500)
            state.app_settings.player_icon = d.get("icon", "trader")
            state.app_settings.friends = d.get("friends", [])
            
            if not state.app_stats:
                from src.config import Stats
                state.app_stats = Stats()
            state.app_stats.wins = d.get("wins", 0)
            state.app_stats.losses = d.get("losses", 0)
            state.app_stats.draws = d.get("draws", 0)
            
            state.app_settings.save()
            state.app_stats.save()
            
            status_msg = "Profile restored!" if state.language == "en" else "Профиль восстановлен!"
            status_color = OUT_OK
        else:
            status_msg = "Profile not found" if state.language == "en" else "Профиль не найден"
            status_color = RED
        is_loading = False
    
    while True:
        clock.tick(FPS)
        pw, ph = min(460, WIDTH - 40), min(260, HEIGHT - 80)
        panel = pygame.Rect(WIDTH // 2 - pw // 2, HEIGHT // 2 - ph // 2, pw, ph)
        draw_ui_background()
        draw_panel(panel)
        title = "Enter Friend Code:" if state.language == "en" else "Введите код друга:"
        draw_text_center(title, pygame.Rect(panel.x, panel.y + 12, pw, 36), ACCENT, state.FONT)
        tb = pygame.Rect(panel.x + 30, panel.y + 60, pw - 60, 48)
        pygame.draw.rect(screen, (20, 35, 22), tb, border_radius=8)
        pygame.draw.rect(screen, ACCENT, tb, 2, border_radius=8)
        disp = "".join(code) + ("_" if (pygame.time.get_ticks() // 500) % 2 == 0 else " ")
        draw_text_center(disp, tb, TEXT, state.FONT)
        
        if status_msg:
            draw_text_center(status_msg, pygame.Rect(panel.x, tb.bottom + 10, pw, 30), status_color, state.SMALL)
            
        pos = pygame.mouse.get_pos()
        ok_r = pygame.Rect(panel.x + pw // 2 - 160, panel.y + ph - 62, 140, 46)
        cancel_r = pygame.Rect(panel.x + pw // 2 + 20, panel.y + ph - 62, 140, 46)
        
        if not is_loading:
            draw_button("OK", ok_r, pos)
            draw_button("Cancel" if state.language == "en" else "Отмена", cancel_r, pos, (100, 28, 28), lighten((100, 28, 28), 30))
        
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                if state.app_settings: state.app_settings.save()
                pygame.quit()
                sys.exit()
            if not is_loading:
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_ESCAPE:
                        return
                    elif e.key == pygame.K_BACKSPACE:
                        if code: code.pop()
                        status_msg = ""
                    elif e.key == pygame.K_RETURN or e.key == pygame.K_KP_ENTER:
                        if len(code) > 0:
                            is_loading = True
                            status_msg = "Connecting..." if state.language == "en" else "Подключение..."
                            status_color = YELLOW
                            threading.Thread(target=_do_restore, args=("".join(code).strip(),), daemon=True).start()
                    else:
                        ch = e.unicode
                        if ch and ch.isalnum() and len(code) < 6:
                            code.append(ch.upper())
                            status_msg = ""
                if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    if ok_r.collidepoint(e.pos) and len(code) > 0:
                        is_loading = True
                        status_msg = "Connecting..." if state.language == "en" else "Подключение..."
                        status_color = YELLOW
                        threading.Thread(target=_do_restore, args=("".join(code).strip(),), daemon=True).start()
                    elif cancel_r.collidepoint(e.pos):
                        return


# ============================================================
# DUSTWAY CAMPAIGN
# ============================================================
FALLBACK_CAMPAIGN_STAGES = [
    {
        "id": "juk", "name": "Жук", "location": "Сухая Балка", "diff": "easy",
        "personality": "benny", "reward_caps": 120, "win_flag": "win_juk",
        "on_win_flags": ["win_juk"],
        "lore": "A loud small-time reseller tests the new caravan hand. Win to open the market rumor.",
        "lore_ru": "Жук принимает вас за лёгкую добычу и предлагает партию.\nПобеда открывает рынок, первый слух о медицинском караване\nи доступ к информатору Мире.",
        "loss_ru": "Жук забирает ставку и смеётся. Сюжет не двигается: нужен реванш.",
        "loss": "Juk laughs and keeps the rumor locked. Replay the stage.",
    },
    {
        "id": "mira", "name": "Мира", "location": "Сухая Балка — старая прачечная", "diff": "medium",
        "personality": "house", "reward_caps": 180, "win_flag": "win_mira",
        "on_win_flags": ["win_mira"],
        "lore": "Mira sells truth only to people who can hold pressure at the table.",
        "lore_ru": "Мира не верит обещаниям — только столу.\nВыиграйте партию, чтобы узнать: маршрут каравана\nбыл не сорван случайно, его продали.",
        "loss_ru": "Мира закрывает разговор: вы видите карты, но пока не человека за ними.",
        "loss": "Mira closes the conversation until you win a rematch.",
    },
    {
        "id": "torm", "name": "Торм", "location": "Ржавый Узел", "diff": "medium",
        "personality": "yes_man", "reward_caps": 220, "win_flag": "win_torm",
        "on_win_flags": ["win_torm"],
        "lore": "A straight, honest mechanic checks whether your routes can carry weight.",
        "lore_ru": "Торм играет просто и честно, почти без трюков.\nПобеда доказывает, что вы понимаете базовую дисциплину\nмаршрута и открывает партию с Никой.",
        "loss_ru": "Торм не злится, но дальше не пропускает. Нужна честная победа.",
        "loss": "Torm blocks the tournament path until you win.",
    },
    {
        "id": "nika", "name": "Ника", "location": "Ржавый Узел — склад деталей", "diff": "medium",
        "personality": "yes_man", "reward_caps": 260, "win_flag": "win_nika",
        "on_win_flags": ["win_nika"],
        "lore": "Nika plays through suits and exceptions. Numbers alone will not save you.",
        "lore_ru": "Ника играет через масти и обходные решения.\nПобеда открывает право сыграть со старшим мастером Вельтом\nи учит искать выходы из плохих ситуаций.",
        "loss_ru": "Ника советует собрать больше карт одной масти и вернуться сильнее.",
        "loss": "Nika tells you to rebuild your options and try again.",
    },
    {
        "id": "velt", "name": "Вельт", "location": "Ржавый Узел — старшая мастерская", "diff": "hard",
        "personality": "house", "reward_caps": 340, "win_flag": "win_velt",
        "on_win_flags": ["win_velt"],
        "lore": "Velt breaks weak plans. Win to get the repair record of the missing wagon.",
        "lore_ru": "Вельт ломает слишком очевидные планы.\nПобеда открывает ведомость ремонта: телегу медицинского\nкаравана заранее готовили к каменному обходному тракту.",
        "loss_ru": "Вельт отказывается говорить о заказах мастерской. Нужно переиграть.",
        "loss": "Velt keeps the repair record closed until you win.",
    },
    {
        "id": "orren", "name": "Оррен", "location": "Лагерь Длинной Дороги", "diff": "hard",
        "personality": "house", "reward_caps": 420, "win_flag": "win_orren",
        "on_win_flags": ["win_orren"],
        "lore": "Captain Orren will not open the route journal to a careless accuser.",
        "lore_ru": "Оррен не отдаст журнал маршрутов человеку, который\nне выдерживает давления. Победа открывает архив\nи доказывает, что приказ был подделан.",
        "loss_ru": "Оррен считает подозрение пустым. Для реванша нужна подготовка.",
        "loss": "Orren refuses access to the archive until a rematch is earned.",
    },
    {
        "id": "roven", "name": "Ровен", "location": "Совет Сухих Колодцев", "diff": "hard",
        "personality": "house", "reward_caps": 500, "win_flag": "win_roven",
        "on_win_flags": ["win_roven"],
        "lore": "Roven hides truth behind procedure. Win the public table to ask one official question.",
        "lore_ru": "Ровен прячет правду за процедурой и формальностями.\nПобеда даёт право на официальный вопрос:\nкто заверил изменение маршрута каравана?",
        "loss_ru": "Совет отклоняет обвинение. Без победы имени Грина не будет.",
        "loss": "The council rejects the accusation until you win publicly.",
    },
    {
        "id": "grin", "name": "Грин", "location": "Заброшенная станция", "diff": "hard",
        "personality": "benny", "reward_caps": 620, "win_flag": "win_grin",
        "on_win_flags": ["win_grin"],
        "lore": "Your mentor waits with the first deck he gave you. Win to make him confess.",
        "lore_ru": "Грин ждёт на заброшенной станции с колодой,\nс которой всё началось. Победа открывает признание:\nон продал маршрут ради дочери Эли.",
        "loss_ru": "Грин говорит, что вы пока не выдержите правду. Признание закрыто.",
        "loss": "Grin refuses the confession until you can beat him.",
    },
    {
        "id": "klyk", "name": "Клык", "location": "Логово Пепельных Псов", "diff": "impossible",
        "personality": "benny", "reward_caps": 900, "win_flag": "win_klyk",
        "on_win_flags": ["win_klyk", "elie_saved", "truth_full"],
        "lore": "The bandit leader stakes Eli and the final truth on the last table.",
        "lore_ru": "Клык ставит на кон жизнь Эли и финальную правду.\nЭто проверка всех уроков: не жадничать, держать линию,\nчитать соперника и иметь запасной план.",
        "loss_ru": "Клык оставляет Эли у себя. Финал закрыт: нужен побег и реванш.",
        "loss": "Klyk keeps Eli and the final truth locked behind a rematch.",
    },
]

def load_campaign_stages() -> List[dict]:
    path = rpath("story", "stages.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        stages = data.get("stages", data) if isinstance(data, dict) else data
        if isinstance(stages, list) and stages:
            return stages
    except Exception as exc:
        print(f"[campaign] Cannot load {path}: {exc}")
    return FALLBACK_CAMPAIGN_STAGES

CAMPAIGN_STAGES = load_campaign_stages()

def _load_campaign_data() -> dict:
    data = secure_load(CAMPAIGN_FILE)
    if data and isinstance(data, dict):
        return data
    return {"stage": 0, "flags": {}}

def load_campaign_progress() -> int:
    d = _load_campaign_data()
    return max(0, min(int(d.get("stage", 0)), len(CAMPAIGN_STAGES)))

def load_campaign_flags() -> dict:
    d = _load_campaign_data()
    flags = d.get("flags", {})
    return flags if isinstance(flags, dict) else {}

def save_campaign_progress(stage: int, flags: Optional[dict] = None):
    cur = _load_campaign_data()
    if flags is None:
        flags = cur.get("flags", {}) if isinstance(cur.get("flags", {}), dict) else {}
    secure_save(CAMPAIGN_FILE, {"stage": int(stage), "flags": flags})

def add_campaign_flags(flag_names: List[str]):
    flags = load_campaign_flags()
    for name in flag_names:
        if name:
            flags[name] = True
    save_campaign_progress(load_campaign_progress(), flags)

def reset_campaign_progress():
    save_campaign_progress(0, {})

def _stage_lore(stage: dict) -> str:
    return stage.get("lore_ru") if state.language == "ru" and stage.get("lore_ru") else stage.get("lore", "")

def _stage_loss_text(stage: dict) -> str:
    return stage.get("loss_ru") if state.language == "ru" and stage.get("loss_ru") else stage.get("loss", "")

def campaign_lore_screen(stage: dict) -> bool:
    screen = state.screen
    WIDTH = state.WIDTH
    HEIGHT = state.HEIGHT
    pygame.event.clear()
    while True:
        clock.tick(FPS)
        pw, ph = min(660, WIDTH - 40), min(420, HEIGHT - 80)
        panel = pygame.Rect(WIDTH // 2 - pw // 2, HEIGHT // 2 - ph // 2, pw, ph)
        draw_ui_background()
        draw_panel(panel, glow=True)
        draw_panel_title_bar(panel, f"📍 {stage.get('location', '')}", color=(164, 120, 72))
        draw_text_center(f"vs  {stage.get('name', '?')}", pygame.Rect(panel.x, panel.y + 8, pw, 52), ACCENT, TITLE)
        pygame.draw.line(screen, PANEL_BORD, (panel.x + 20, panel.y + 66), (panel.right - 20, panel.y + 66), 1)
        lore_lines = []
        for part in _stage_lore(stage).split("\n"):
            lore_lines.extend(wrap_text(part, SMALL, pw - 56))
        for li, ll in enumerate(lore_lines[:6]):
            draw_text_center(ll, pygame.Rect(panel.x + 18, panel.y + 84 + li * 30, pw - 36, 28), TEXT, SMALL)
        rew = int(stage.get("reward_caps", 0))
        rline = f"Reward: +{rew} caps" if state.language == "en" else f"Награда: +{rew} крышек"
        draw_text_center(rline, pygame.Rect(panel.x, panel.bottom - 102, pw, 28), CAPS_CLR, state.FONT)
        pos = pygame.mouse.get_pos()
        bw2 = max(160, int(pw * 0.36))
        play_r = pygame.Rect(panel.x + int(pw * 0.1), panel.bottom - 62, bw2, 50)
        back_r = pygame.Rect(panel.right - int(pw * 0.1) - bw2, panel.bottom - 62, bw2, 50)
        lbl_play = "Play" if state.language == "en" else "Играть"
        draw_button(lbl_play, play_r, pos, BTN, BTN_H)
        draw_button(T("back"), back_r, pos, (100, 28, 28), lighten((100, 28, 28), 30), SMALL)
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                state.app_settings.save()
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE: return False
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if play_r.collidepoint(e.pos): return True
                if back_r.collidepoint(e.pos): return False


def campaign_map_screen(current_stage: int) -> Optional[int]:
    screen = state.screen
    WIDTH = state.WIDTH
    HEIGHT = state.HEIGHT
    
    STAGE_COORDS = [
        (0.22, 0.73), # 0 
        (0.45, 0.75), # 1 
        (0.42, 0.41), # 2 
        (0.23, 0.21), # 3 
        (0.15, 0.45), # 4 
        (0.74, 0.26), # 5 
        (0.68, 0.42), # 6 
        (0.85, 0.48), # 7 
        (0.78, 0.65), # 8 
    ]
    
    pygame.event.clear()
    while True:
        clock.tick(FPS)
        draw_history_map()
        
        actual_coords = [(int(STAGE_COORDS[si][0]*WIDTH), int(STAGE_COORDS[si][1]*HEIGHT)) 
                         for si in range(min(len(CAMPAIGN_STAGES), len(STAGE_COORDS)))]
        from src.ui import draw_map_path
        draw_map_path(actual_coords, current_stage)
        
        pos = pygame.mouse.get_pos()
        hovered_stage = None
        
        node_rects = []
        for si, stg in enumerate(CAMPAIGN_STAGES):
            if si >= len(STAGE_COORDS): break
            px, py = STAGE_COORDS[si]
            cx, cy = int(px * WIDTH), int(py * HEIGHT)
            
            done = si < current_stage
            active = si == current_stage
            locked = si > current_stage
            
            dist = math.hypot(pos[0] - cx, pos[1] - cy)
            hovered = dist < 25 and not locked
            if hovered:
                hovered_stage = (cx, cy, stg, done)
            
            if not locked:
                draw_map_node(cx, cy, active, done, hovered)
                node_rects.append((cx, cy, si, active))
        
        if hovered_stage:
            draw_map_tooltip(*hovered_stage)
            
        if current_stage >= len(CAMPAIGN_STAGES):
            comp_txt = "Campaign Complete!" if state.language == "en" else "Кампания завершена!"
            tw, th = FONT.size(comp_txt)
            tr = pygame.Rect(WIDTH // 2 - tw // 2 - 20, 20, tw + 40, th + 20)
            draw_panel(tr, fill=(20, 24, 20, 220), border=ACCENT, glow=True)
            draw_text_center(comp_txt, tr, ACCENT, FONT)
            
        bw = max(180, int(220 * WIDTH / _BASE_W))
        bh = max(42, int(46 * HEIGHT / _BASE_H))
        back_r = pygame.Rect(WIDTH - bw - 20, HEIGHT - bh - 20, bw, bh)
        draw_button(T("back"), back_r, pos, font=SMALL)
        rst_r = pygame.Rect(20, HEIGHT - bh - 20, bw, bh)
        draw_button("Reset" if state.language == "en" else "Сброс", rst_r, pos, (80, 28, 28), lighten((80, 28, 28), 25), SMALL)
        
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                state.app_settings.save()
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE: return None
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if back_r.collidepoint(e.pos): return None
                if rst_r.collidepoint(e.pos):
                    reset_campaign_progress()
                    current_stage = 0
                    continue
                for cx, cy, si, active in node_rects:
                    if math.hypot(e.pos[0] - cx, e.pos[1] - cy) < 25 and active:
                        return si


def run_campaign():
    auto_stage: Optional[int] = None
    while True:
        progress = load_campaign_progress()
        if auto_stage is not None and auto_stage <= progress and auto_stage < len(CAMPAIGN_STAGES):
            idx = auto_stage
            auto_stage = None
        else:
            idx = campaign_map_screen(progress)
        if idx is None: return

        stg = CAMPAIGN_STAGES[idx]
        go = campaign_lore_screen(stg)
        if not go: continue

        while True:
            wc, elapsed, caps_delta = run_match(
                stg.get("diff", "easy"), GM_NORMAL, stg.get("personality", DEFAULT_PERSONALITY),
                bet=0, result_context="campaign"
            )
            if wc in ("menu", "quit_match"): return

            hist = load_history()
            last_result = hist[-1].result if hist else "loss"

            if last_result == "win":
                new_progress = max(progress + 1, idx + 1)
                flags = load_campaign_flags()
                for flag in stg.get("on_win_flags", [stg.get("win_flag", "")]):
                    if flag: flags[flag] = True
                save_campaign_progress(new_progress, flags)
                state.app_settings.caps += int(stg.get("reward_caps", 0))
                state.app_settings.save()
                reward_action = _campaign_reward_screen(stg, new_progress)
                if new_progress >= len(CAMPAIGN_STAGES):
                    unlock_achievement("TOURN_CHAMP")
                if reward_action == "next" and new_progress < len(CAMPAIGN_STAGES):
                    auto_stage = new_progress
                break

            fail_action = _campaign_failure_screen(stg)
            if fail_action == "retry": continue
            if fail_action == "menu": return
            break


def _campaign_reward_screen(stg: dict, new_progress: int) -> str:
    pygame.event.clear()
    particles = state.particles
    if particles: particles.confetti(60)
    screen = state.screen
    WIDTH = state.WIDTH
    HEIGHT = state.HEIGHT
    while True:
        clock.tick(FPS)
        pw, ph = min(620, WIDTH - 40), min(340, HEIGHT - 80)
        panel = pygame.Rect(WIDTH // 2 - pw // 2, HEIGHT // 2 - ph // 2, pw, ph)
        draw_ui_background()
        if particles: particles.tick_draw(screen)
        draw_panel(panel, glow=True)
        if new_progress >= len(CAMPAIGN_STAGES):
            hdr = "🏆 CAMPAIGN COMPLETE!" if state.language == "en" else "🏆 КАМПАНИЯ ЗАВЕРШЕНА!"
        else:
            hdr = "✓ Stage Clear!" if state.language == "en" else "✓ Этап пройден!"
        draw_text_center(hdr, pygame.Rect(panel.x, panel.y + 16, pw, 52), ACCENT, TITLE)
        draw_text_center(f"+{int(stg.get('reward_caps', 0))} caps!", pygame.Rect(panel.x, panel.y + 80, pw, 40), CAPS_CLR, state.FONT)
        if new_progress < len(CAMPAIGN_STAGES):
            nxt = CAMPAIGN_STAGES[new_progress].get("name", "?")
            nxt_txt = f"Next: {nxt}" if state.language == "en" else f"Следующий: {nxt}"
            draw_text_center(nxt_txt, pygame.Rect(panel.x, panel.y + 128, pw, 30), TEXT_DIM, SMALL)
        else:
            txt = "Eli is saved. Full truth unlocked." if state.language == "en" else "Эли спасена. Полная правда открыта."
            draw_text_center(txt, pygame.Rect(panel.x, panel.y + 128, pw, 30), TEXT_DIM, SMALL)

        pos = pygame.mouse.get_pos()
        if new_progress < len(CAMPAIGN_STAGES):
            bw, gap = 210, 18
            map_r = pygame.Rect(panel.centerx - bw - gap // 2, panel.bottom - 68, bw, 50)
            next_r = pygame.Rect(panel.centerx + gap // 2, panel.bottom - 68, bw, 50)
            draw_button("Map" if state.language == "en" else "К карте", map_r, pos, font=SMALL)
            draw_button("Next stage" if state.language == "en" else "Следующий этап", next_r, pos, BTN, BTN_H, SMALL)
        else:
            map_r = pygame.Rect(panel.x + (pw - 210) // 2, panel.bottom - 68, 210, 50)
            next_r = None
            draw_button("Map" if state.language == "en" else "К карте", map_r, pos, font=SMALL)
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                state.app_settings.save()
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN, pygame.K_SPACE):
                if particles: particles.clear()
                return "next" if new_progress < len(CAMPAIGN_STAGES) else "map"
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if map_r.collidepoint(e.pos):
                    if particles: particles.clear()
                    return "map"
                if next_r is not None and next_r.collidepoint(e.pos):
                    if particles: particles.clear()
                    return "next"


def _campaign_failure_screen(stg: dict) -> str:
    pygame.event.clear()
    WIDTH = state.WIDTH
    HEIGHT = state.HEIGHT
    while True:
        clock.tick(FPS)
        pw, ph = min(620, WIDTH - 40), min(300, HEIGHT - 80)
        panel = pygame.Rect(WIDTH // 2 - pw // 2, HEIGHT // 2 - ph // 2, pw, ph)
        draw_ui_background()
        draw_panel(panel)
        hdr = "Truth remains locked" if state.language == "en" else "Правда остаётся закрытой"
        draw_text_center(hdr, pygame.Rect(panel.x, panel.y + 16, pw, 46), RED, state.FONT)
        lines = []
        for part in _stage_loss_text(stg).split("\n"):
            lines.extend(wrap_text(part, SMALL, pw - 56))
        for i, line in enumerate(lines[:3]):
            draw_text_center(line, pygame.Rect(panel.x + 18, panel.y + 78 + i * 28, pw - 36, 26), TEXT, SMALL)
        pos = pygame.mouse.get_pos()
        bw, gap = 210, 18
        retry_r = pygame.Rect(panel.centerx - bw - gap // 2, panel.bottom - 64, bw, 50)
        map_r = pygame.Rect(panel.centerx + gap // 2, panel.bottom - 64, bw, 50)
        draw_button("Rematch" if state.language == "en" else "Реванш", retry_r, pos, BTN, BTN_H, SMALL)
        draw_button("Map" if state.language == "en" else "К карте", map_r, pos, font=SMALL)
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                state.app_settings.save()
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE: return "map"
                if e.key in (pygame.K_RETURN, pygame.K_SPACE): return "retry"
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if retry_r.collidepoint(e.pos): return "retry"
                if map_r.collidepoint(e.pos): return "map"


# ============================================================
# SPECTATOR MODE
# ============================================================
def run_spectator():
    spec_config = _spectator_config_screen()
    if spec_config is None: return
    diff_a, diff_b, pers_a, pers_b, speed = spec_config

    sel_keys = load_deck_selection()
    if sel_keys: sel_keys = ensure_min30_selection(sel_keys)
    bot_a = PlayerState("Bot A", [Caravan() for _ in range(3)], build_deck_from_selection(sel_keys), [], [])
    bot_b = PlayerState("Bot B", [Caravan() for _ in range(3)], build_deck_from_selection(sel_keys), [], [])
    draw_to_hand(bot_a, HAND_OPENING_SIZE)
    draw_to_hand(bot_b, HAND_OPENING_SIZE)

    phase = "OPENING"
    opening_halfturn = 0
    start_ms = pygame.time.get_ticks()
    turn_ms = start_ms
    delay_ms = {1: 1200, 2: 700, 3: 350, 4: 150, 5: 50}[speed]
    a_to_move = True
    msg = ""
    msg_until = 0
    consecutive_discards = 0
    hitboxes_dirty = True
    cached_hit = None
    game_over = False
    result_txt = ""

    WIDTH = state.WIDTH
    HEIGHT = state.HEIGHT
    particles = state.particles
    sounds = state.sounds

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

        _draw_spectator_overlay(speed, result_txt if game_over else "", now, start_ms)
        pygame.display.flip()

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                state.app_settings.save()
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE: return
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                new_spd = _check_speed_click(e.pos, speed)
                if new_spd is not None:
                    speed = new_spd
                    delay_ms = {1: 1200, 2: 700, 3: 350, 4: 150, 5: 50}[speed]
                    continue
                stop_r = pygame.Rect(WIDTH - 130, 10, 120, 40)
                if stop_r.collidepoint(e.pos): return

        if game_over:
            if now - start_ms > 3000:
                pygame.time.wait(1000)
                return
            continue

        if now - turn_ms < delay_ms: continue

        mover = bot_a if a_to_move else bot_b
        opponent = bot_b if a_to_move else bot_a
        diff = diff_a if a_to_move else diff_b
        pk = pers_a if a_to_move else pers_b

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
            consecutive_discards = (0 if was_play else consecutive_discards + 1)
            if rmsg: msg = rmsg; msg_until = now + 1200
            if not ok2:
                result_txt = f"{'Bot A' if a_to_move else 'Bot B'} deck empty!"
                game_over = True
            else:
                ended, win, wtxt = check_game_end(bot_a, bot_b)
                if ended or consecutive_discards >= STALEMATE_THRESHOLD:
                    result_txt = wtxt if ended else "Draw — stalemate!"
                    if ended and sounds: sounds.play("win")
                    game_over = True
                    if ended and particles: particles.confetti(50)
            hitboxes_dirty = True

        a_to_move = not a_to_move
        turn_ms = now

_spec_speed_rects: list = []

def _draw_spectator_overlay(speed: int, result_txt: str, now: int, start_ms: int):
    global _spec_speed_rects
    WIDTH = state.WIDTH
    HEIGHT = state.HEIGHT
    screen = state.screen
    stop_r = pygame.Rect(WIDTH - 130, 10, 120, 40)
    pos = pygame.mouse.get_pos()
    draw_button("■ Stop" if state.language == "en" else "■ Стоп", stop_r, pos, (100, 28, 28), lighten((100, 28, 28), 30), SMALL)
    speeds = ["1x", "2x", "3x", "4x", "5x"]
    bw3 = 44
    bh3 = 30
    sx0 = WIDTH - 130 - len(speeds) * (bw3 + 6) - 8
    _spec_speed_rects.clear()
    for si, sl in enumerate(speeds):
        sr = pygame.Rect(sx0 + si * (bw3 + 6), 14, bw3, bh3)
        _spec_speed_rects.append(sr)
        is_sel = (si + 1 == speed)
        draw_button(sl, sr, pos, RES_ACTIVE if is_sel else BTN, RES_ACT_H if is_sel else BTN_H, state.TINY)
    badge = "👁 AI vs AI Spectator" if state.language == "en" else "👁 Бот vs Бот"
    draw_text(badge, 8, 8, (140, 140, 200), SMALL)
    draw_text(format_time_ms(now - start_ms), 8, 8 + SMALL.get_height() + 4, TEXT_DIM, state.TINY)
    if result_txt:
        rr = pygame.Rect(WIDTH // 2 - 200, HEIGHT // 2 - 30, 400, 60)
        rs2 = pygame.Surface((400, 60), pygame.SRCALPHA)
        rs2.fill((12, 20, 14, 220))
        pygame.draw.rect(rs2, ACCENT, pygame.Rect(0, 0, 400, 60), 3, border_radius=14)
        screen.blit(rs2, rr.topleft)
        draw_text_center(result_txt, rr, ACCENT, state.FONT)

def _check_speed_click(pos: tuple, current_speed: int) -> Optional[int]:
    for si, sr in enumerate(_spec_speed_rects):
        if sr.collidepoint(pos): return si + 1
    return None

def _spectator_config_screen() -> Optional[tuple]:
    diff_a = "medium"
    diff_b = "medium"
    pers_a = "benny"
    pers_b = "house"
    speed = 2
    diffs = ["easy", "medium", "hard", "impossible"]
    perss = list(PERSONALITIES.keys())
    pygame.event.clear()
    WIDTH = state.WIDTH
    HEIGHT = state.HEIGHT
    screen = state.screen
    while True:
        clock.tick(FPS)
        pw, ph = min(640, WIDTH - 40), min(480, HEIGHT - 80)
        panel = pygame.Rect(WIDTH // 2 - pw // 2, HEIGHT // 2 - ph // 2, pw, ph)
        draw_ui_background()
        draw_panel(panel)
        hdr = "👁 Spectator Setup" if state.language == "en" else "👁 Настройка наблюдения"
        draw_panel_title_bar(panel, hdr, color=(140, 120, 220))
        draw_text_center(hdr, pygame.Rect(panel.x, panel.y + 8, pw, 52), (180, 160, 255), state.TITLE)
        pos = pygame.mouse.get_pos()
        col_w = pw // 2 - 20
        draw_text("Bot A", panel.x + 30, panel.y + 72, (100, 200, 255), state.FONT)
        da_rects = []
        for di, d in enumerate(diffs):
            r = pygame.Rect(panel.x + 20, panel.y + 104 + di * 46, col_w - 10, 40)
            da_rects.append(r)
            is_sel = (d == diff_a)
            dc = {"easy": OUT_OK, "medium": YELLOW, "hard": (230, 130, 50), "impossible": RED}.get(d, TEXT)
            draw_button(d.upper(), r, pos, (30, 50, 30) if is_sel else BTN, lighten((30, 50, 30), 40) if is_sel else BTN_H, SMALL)
            if is_sel: pygame.draw.rect(screen, dc, r, 3, border_radius=10)
        pa_rects = []
        for pi, pk in enumerate(perss):
            r = pygame.Rect(panel.x + 20, panel.y + 104 + len(diffs) * 46 + 10 + pi * 46, col_w - 10, 40)
            pa_rects.append(r)
            is_sel = (pk == pers_a)
            draw_button(T(PERSONALITIES[pk].display_key), r, pos, (30, 50, 60) if is_sel else BTN, lighten((30, 50, 60), 40) if is_sel else BTN_H, SMALL)
            if is_sel: pygame.draw.rect(screen, (100, 200, 255), r, 2, border_radius=10)
        draw_text("Bot B", panel.x + pw // 2 + 10, panel.y + 72, (255, 180, 100), state.FONT)
        db_rects = []
        for di, d in enumerate(diffs):
            r = pygame.Rect(panel.x + pw // 2 + 10, panel.y + 104 + di * 46, col_w - 10, 40)
            db_rects.append(r)
            is_sel = (d == diff_b)
            dc = {"easy": OUT_OK, "medium": YELLOW, "hard": (230, 130, 50), "impossible": RED}.get(d, TEXT)
            draw_button(d.upper(), r, pos, (50, 30, 20) if is_sel else BTN, lighten((50, 30, 20), 40) if is_sel else BTN_H, SMALL)
            if is_sel: pygame.draw.rect(screen, dc, r, 3, border_radius=10)
        pb_rects = []
        for pi, pk in enumerate(perss):
            r = pygame.Rect(panel.x + pw // 2 + 10, panel.y + 104 + len(diffs) * 46 + 10 + pi * 46, col_w - 10, 40)
            pb_rects.append(r)
            is_sel = (pk == pers_b)
            draw_button(T(PERSONALITIES[pk].display_key), r, pos, (60, 40, 20) if is_sel else BTN, lighten((60, 40, 20), 40) if is_sel else BTN_H, SMALL)
            if is_sel: pygame.draw.rect(screen, (255, 180, 100), r, 2, border_radius=10)
        spd_y = panel.bottom - 80
        draw_text("Speed:" if state.language == "en" else "Скорость:", panel.x + 20, spd_y, TEXT_DIM, SMALL)
        spd_rects = []
        for si in range(1, 6):
            sr = pygame.Rect(panel.x + 110 + (si - 1) * 52, spd_y - 4, 46, 34)
            spd_rects.append(sr)
            is_sel = (si == speed)
            draw_button(f"{si}x", sr, pos, RES_ACTIVE if is_sel else BTN, RES_ACT_H if is_sel else BTN_H, SMALL)
        start_r = pygame.Rect(panel.x + (pw - 200) // 2, panel.bottom - 38, 200, 32)
        draw_button("▶ Watch!" if state.language == "en" else "▶ Смотреть!", start_r, pos, BTN, BTN_H, SMALL)
        back_r2 = pygame.Rect(panel.x + 10, panel.bottom - 38, 120, 32)
        draw_button(T("back"), back_r2, pos, (80, 28, 28), lighten((80, 28, 28), 25), SMALL)
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                state.app_settings.save()
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE: return None
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if back_r2.collidepoint(e.pos): return None
                if start_r.collidepoint(e.pos): return (diff_a, diff_b, pers_a, pers_b, speed)
                for di, r in enumerate(da_rects):
                    if r.collidepoint(e.pos): diff_a = diffs[di]; break
                for di, r in enumerate(db_rects):
                    if r.collidepoint(e.pos): diff_b = diffs[di]; break
                for pi, r in enumerate(pa_rects):
                    if r.collidepoint(e.pos): pers_a = perss[pi]; break
                for pi, r in enumerate(pb_rects):
                    if r.collidepoint(e.pos): pers_b = perss[pi]; break
                for si, sr in enumerate(spd_rects):
                    if sr.collidepoint(e.pos): speed = si + 1; break


# ============================================================
# TUTORIAL SCREEN AND PROGRESS
# ============================================================
TUTORIAL_FILE = wpath("tutorial.json")

TUTORIAL_LEVELS = [
    {"id": 1,  "title_key": "tut1_t",  "desc_key": "tut1_d", "goal_en": "Read the card info and click 'Next' to continue.", "goal_ru": "Прочитайте информацию о картах и нажмите 'Далее'.", "type": "info"},
    {"id": 2,  "title_key": "tut2_t",  "desc_key": "tut2_d", "goal_en": "Place a number card (A-10) on any empty caravan.", "goal_ru": "Положите числовую карту (A-10) на любой пустой караван.", "type": "play", "check": "placed_one"},
    {"id": 3,  "title_key": "tut3_t",  "desc_key": "tut3_d", "goal_en": "Place 2 cards on the same caravan (ascending or descending).", "goal_ru": "Положите 2 карты на один караван (по возрастанию или убыванию).", "type": "play", "check": "direction_set"},
    {"id": 4,  "title_key": "tut4_t",  "desc_key": "tut4_d", "goal_en": "Play a card of a different suit to change direction.", "goal_ru": "Сыграйте карту другой масти, чтобы сменить направление.", "type": "play", "check": "suit_change"},
    {"id": 5,  "title_key": "tut5_t",  "desc_key": "tut5_d", "goal_en": "Build a caravan with a score between 21 and 26.", "goal_ru": "Соберите караван со счётом от 21 до 26.", "type": "play", "check": "sold_caravan"},
    {"id": 6,  "title_key": "tut6_t",  "desc_key": "tut6_d", "goal_en": "Win 2 out of 3 caravans to win the match!", "goal_ru": "Выиграйте 2 из 3 караванов для победы!", "type": "play", "check": "win_match"},
    {"id": 7,  "title_key": "tut7_t",  "desc_key": "tut7_d", "goal_en": "Use a Jack to remove an opponent's card.", "goal_ru": "Используйте Валета, чтобы удалить карту противника.", "type": "play", "check": "used_jack"},
    {"id": 8,  "title_key": "tut8_t",  "desc_key": "tut8_d", "goal_en": "Attach a Queen to the last card on a caravan.", "goal_ru": "Прикрепите Даму к верхней карте каравана.", "type": "play", "check": "used_queen"},
    {"id": 9,  "title_key": "tut9_t",  "desc_key": "tut9_d", "goal_en": "Attach a King to double a card's value.", "goal_ru": "Прикрепите Короля, чтобы удвоить значение карты.", "type": "play", "check": "used_king"},
    {"id": 10, "title_key": "tut10_t", "desc_key": "tut10_d", "goal_en": "Play a Joker to clear matching cards from the board.", "goal_ru": "Сыграйте Джокера, чтобы очистить совпадающие карты.", "type": "play", "check": "used_joker"},
    {"id": 11, "title_key": "tut11_t", "desc_key": "tut11_d", "goal_en": "Discard a card from your hand (press D or right-click).", "goal_ru": "Сбросьте карту из руки (нажмите D или ПКМ).", "type": "play", "check": "discarded"},
    {"id": 12, "title_key": "tut12_t", "desc_key": "tut12_d", "goal_en": "Disband one of your caravans (right-click a caravan slot).", "goal_ru": "Расформируйте один из ваших караванов (ПКМ по слоту).", "type": "play", "check": "disbanded"},
    {"id": 13, "title_key": "tut13_t", "desc_key": "tut13_d", "goal_en": "Play 2 face cards in a single match.", "goal_ru": "Сыграйте 2 фигурных карты за одну партию.", "type": "play", "check": "two_faces"},
    {"id": 14, "title_key": "tut14_t", "desc_key": "tut14_d", "goal_en": "Sell a caravan before the bot does.", "goal_ru": "Продайте караван раньше бота.", "type": "play", "check": "sold_first"},
    {"id": 15, "title_key": "tut15_t", "desc_key": "tut15_d", "goal_en": "Win a full match against an easy bot!", "goal_ru": "Выиграйте полную партию против лёгкого бота!", "type": "full_match"},
]

def load_tutorial_progress() -> list:
    data = secure_load(TUTORIAL_FILE)
    if data and isinstance(data, dict):
        return data.get("completed", [])
    return []

def save_tutorial_progress(completed: list):
    secure_save(TUTORIAL_FILE, {"completed": sorted(set(completed))})

def tutorial_level_select() -> Optional[int]:
    completed = load_tutorial_progress()
    pygame.event.clear()
    WIDTH = state.WIDTH
    HEIGHT = state.HEIGHT
    screen = state.screen
    while True:
        clock.tick(FPS)
        draw_ui_background()

        pw, ph = min(940, WIDTH - 40), min(700, HEIGHT - 34)
        panel = pygame.Rect(WIDTH // 2 - pw // 2, HEIGHT // 2 - ph // 2, pw, ph)
        draw_panel(panel, glow=True)
        draw_panel_title_bar(panel, T("tutorial_title"))
        draw_text_center(T("tutorial_title"), pygame.Rect(panel.x, panel.y + 8, pw, 52), ACCENT, state.TITLE)

        n_done = len([c for c in completed if 1 <= c <= 15])
        prog_txt = T("tutorial_progress", n_done, 15)
        draw_text_center(prog_txt, pygame.Rect(panel.x, panel.y + 58, pw, 26), TEXT_DIM, SMALL)

        grid_box = pygame.Rect(panel.x + 24, panel.y + 94, pw - 48, ph - 166)
        gs = pygame.Surface((grid_box.w, grid_box.h), pygame.SRCALPHA)
        gs.fill((12, 24, 18, 110))
        screen.blit(gs, grid_box.topleft)
        pygame.draw.rect(screen, PANEL_BORD, grid_box, 1, border_radius=12)

        pos = pygame.mouse.get_pos()
        cols = 3
        rows = 5
        cell_w = (grid_box.w - 40) // cols
        cell_h = (grid_box.h - 50) // rows
        grid_x0 = grid_box.x + 10
        grid_y0 = grid_box.y + 10

        level_rects = []
        for li, lvl in enumerate(TUTORIAL_LEVELS):
            row, col = li // cols, li % cols
            cr = pygame.Rect(grid_x0 + col * cell_w + 6, grid_y0 + row * cell_h + 6, cell_w - 12, cell_h - 12)
            level_rects.append((cr, lvl["id"]))

            is_done = lvl["id"] in completed
            is_unlocked = lvl["id"] == 1 or (lvl["id"] - 1) in completed
            hovered = cr.collidepoint(pos) and is_unlocked

            fill = (30, 70, 35) if is_done else (42, 55, 68) if is_unlocked else (24, 26, 28)
            border = (80, 180, 90) if is_done else (110, 150, 210) if is_unlocked else (54, 56, 58)
            cs2 = pygame.Surface((cr.w, cr.h), pygame.SRCALPHA)
            cs2.fill((*fill, 178 if hovered else 148))
            screen.blit(cs2, cr.topleft)
            pygame.draw.rect(screen, border, cr, 2 if not hovered else 3, border_radius=12)

            num_col = (80, 180, 90) if is_done else ((216, 220, 235) if is_unlocked else (80, 82, 85))
            draw_text_center(str(lvl["id"]), pygame.Rect(cr.x, cr.y + 6, cr.w, 24), num_col, state.FONT)
            title_lines = wrap_text(T(lvl["title_key"]), state.TINY, cr.w - 16)
            for i, line in enumerate(title_lines[:2]):
                draw_text_center(line, pygame.Rect(cr.x + 8, cr.y + 34 + i * 18, cr.w - 16, 18), TEXT if is_unlocked else (80, 82, 85), state.TINY)
            status = ""
            scol = TEXT_DIM
            if is_done:
                status = "Completed" if state.language == "en" else "Пройдено"
                scol = OUT_OK
            elif not is_unlocked:
                status = "Locked" if state.language == "en" else "Закрыто"
                scol = (92, 92, 92)
            else:
                status = "Open" if state.language == "en" else "Доступно"
                scol = ACCENT
            draw_text_center(status, pygame.Rect(cr.x, cr.bottom - 24, cr.w, 18), scol, state.TINY)

        back_r = pygame.Rect(panel.centerx - 110, panel.bottom - 56, 220, 42)
        draw_button(T("back"), back_r, pos, font=SMALL)
        pygame.display.flip()

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                state.app_settings.save()
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE: return None
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if back_r.collidepoint(e.pos): return None
                for cr2, lid in level_rects:
                    if cr2.collidepoint(e.pos):
                        is_unlocked = lid == 1 or (lid - 1) in completed
                        if is_unlocked: return lid


def _tutorial_info_screen(level_data: dict) -> str:
    pygame.event.clear()
    WIDTH = state.WIDTH
    HEIGHT = state.HEIGHT
    screen = state.screen
    while True:
        clock.tick(FPS)
        draw_ui_background()

        pw, ph = min(820, WIDTH - 40), min(600, HEIGHT - 50)
        panel = pygame.Rect(WIDTH // 2 - pw // 2, HEIGHT // 2 - ph // 2, pw, ph)
        draw_panel(panel, glow=True)
        draw_panel_title_bar(panel, T("tutorial_title"))

        draw_text_center(T("tutorial_level", level_data["id"]), pygame.Rect(panel.x, panel.y + 10, pw, 38), ACCENT, state.TITLE)
        draw_text_center(T(level_data["title_key"]), pygame.Rect(panel.x + 20, panel.y + 52, pw - 40, 28), TEXT, state.FONT)
        pygame.draw.line(screen, ACCENT, (panel.x + 28, panel.y + 92), (panel.right - 28, panel.y + 92), 1)

        body = pygame.Rect(panel.x + 28, panel.y + 108, pw - 56, ph - 190)
        bs = pygame.Surface((body.w, body.h), pygame.SRCALPHA)
        bs.fill((12, 24, 18, 110))
        screen.blit(bs, body.topleft)
        pygame.draw.rect(screen, PANEL_BORD, body, 1, border_radius=12)

        y = body.y + 18
        for line in wrap_text(T(level_data["desc_key"]), SMALL, body.w - 36):
            draw_text(line, body.x + 18, y, TEXT_DIM, SMALL)
            y += 22
        y += 10
        goal = level_data.get("goal_ru" if state.language == "ru" else "goal_en", "")
        goal_lines = wrap_text(("Goal: " if state.language == "en" else "Цель: ") + goal, SMALL, body.w - 36)
        for line in goal_lines:
            draw_text(line, body.x + 18, y, YELLOW, SMALL)
            y += 22

        if level_data["id"] == 1:
            y += 8
            info_lines = [
                "♠ ♥ ♦ ♣  —  4 suits (Spades, Hearts, Diamonds, Clubs)" if state.language == "en" else "♠ ♥ ♦ ♣  —  4 масти (Пики, Червы, Бубны, Трефы)",
                "A, 2-10  —  Number cards build caravans." if state.language == "en" else "A, 2-10  —  Числовые карты строят караваны.",
                "J, Q, K  —  Face cards add special effects." if state.language == "en" else "J, Q, K  —  Фигурные карты дают особые эффекты.",
                "Joker  —  A wildcard that disrupts the table." if state.language == "en" else "Джокер  —  Особая карта, меняющая ситуацию на столе.",
            ]
            for line in info_lines:
                for part in wrap_text(line, state.TINY, body.w - 36):
                    draw_text(part, body.x + 18, y, TEXT, state.TINY)
                    y += 18
                y += 3

        pos = pygame.mouse.get_pos()
        next_r = pygame.Rect(panel.centerx - 110, panel.bottom - 56, 220, 42)
        draw_button(T("tutorial_next"), next_r, pos, (30, 75, 35), (45, 110, 50), SMALL)
        back_r = pygame.Rect(panel.x + 24, panel.bottom - 56, 140, 42)
        draw_button(T("back"), back_r, pos, font=SMALL)

        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                state.app_settings.save()
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE: return "back"
                if e.key in (pygame.K_RETURN, pygame.K_SPACE): return "next"
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if next_r.collidepoint(e.pos): return "next"
                if back_r.collidepoint(e.pos): return "back"


def _tutorial_result_screen(level_data: dict, success: bool) -> str:
    pygame.event.clear()
    WIDTH = state.WIDTH
    HEIGHT = state.HEIGHT
    screen = state.screen
    particles = state.particles
    while True:
        clock.tick(FPS)
        draw_ui_background()

        pw, ph = min(620, WIDTH - 40), min(380, HEIGHT - 60)
        panel = pygame.Rect(WIDTH // 2 - pw // 2, HEIGHT // 2 - ph // 2, pw, ph)
        draw_panel(panel, glow=success)
        draw_panel_title_bar(panel, T("tutorial_title"))

        if success:
            draw_text_center("✅ " + T("tutorial_completed"), pygame.Rect(panel.x, panel.y + 28, pw, 44), OUT_OK, state.TITLE)
            if particles: particles.confetti(40)
        else:
            draw_text_center("❌ " + T("tutorial_retry") + "?", pygame.Rect(panel.x, panel.y + 28, pw, 44), RED, state.TITLE)
        draw_text_center(T("tutorial_level", level_data["id"]) + " — " + T(level_data["title_key"]), pygame.Rect(panel.x + 20, panel.y + 86, pw - 40, 28), TEXT_DIM, SMALL)
        draw_text_center(("Take the next lesson or try again." if state.language == "en" else "Перейдите к следующему уроку или попробуйте ещё раз."), pygame.Rect(panel.x + 26, panel.y + 122, pw - 52, 24), TEXT, state.TINY)

        pos = pygame.mouse.get_pos()
        bw2 = 220
        y0 = panel.y + 182
        if success and level_data["id"] < 15:
            next_r = pygame.Rect(panel.centerx - bw2 // 2, y0, bw2, 42)
            draw_button(T("tutorial_next"), next_r, pos, (30, 75, 35), (45, 110, 50), SMALL)
            y0 += 52
        else:
            next_r = None
        retry_r = pygame.Rect(panel.centerx - bw2 // 2, y0, bw2, 42)
        draw_button(T("tutorial_retry"), retry_r, pos, BTN, BTN_H, SMALL)
        back_r = pygame.Rect(panel.centerx - bw2 // 2, y0 + 52, bw2, 42)
        draw_button(T("tutorial_back_to_list"), back_r, pos, font=state.TINY)

        if particles: particles.tick_draw(screen)
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                state.app_settings.save()
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE: return "back"
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if next_r and next_r.collidepoint(e.pos): return "next"
                if retry_r.collidepoint(e.pos): return "retry"
                if back_r.collidepoint(e.pos): return "back"


def run_tutorial():
    while True:
        level_id = tutorial_level_select()
        if level_id is None: return

        while level_id is not None and 1 <= level_id <= 15:
            level_data = TUTORIAL_LEVELS[level_id - 1]
            completed = load_tutorial_progress()

            if level_data["type"] == "info":
                result = _tutorial_info_screen(level_data)
                if result == "back": break
                if level_id not in completed:
                    completed.append(level_id)
                    save_tutorial_progress(completed)
                if level_id < 15:
                    level_id += 1
                    continue
                else:
                    break

            elif level_data["type"] == "full_match":
                wc, elapsed, caps_delta = run_match("easy", GM_NORMAL, DEFAULT_PERSONALITY, 0)
                success = wc == "restart" or "win" in str(wc).lower()
                if wc not in ("menu", "quit_match"):
                    success = True
                else:
                    success = False
                if success and level_id not in completed:
                    completed.append(level_id)
                    save_tutorial_progress(completed)
                res = _tutorial_result_screen(level_data, success)
                if res == "next" and level_id < 15:
                    level_id += 1
                elif res == "retry":
                    continue
                else:
                    break

            else:
                wc, elapsed, caps_delta = run_match("easy", GM_NORMAL, DEFAULT_PERSONALITY, 0)
                success = wc not in ("menu", "quit_match")
                if success and level_id not in completed:
                    completed.append(level_id)
                    save_tutorial_progress(completed)
                res = _tutorial_result_screen(level_data, success)
                if res == "next" and level_id < 15:
                    level_id += 1
                elif res == "retry":
                    continue
                else:
                    break
