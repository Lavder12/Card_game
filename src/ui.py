import os
import sys
import math
import random
import pygame
from typing import Dict, Tuple, List, Optional, Set, Any
from collections import OrderedDict
from dataclasses import dataclass
import src.state as state
from src.config import (
    T, SUIT_SYMBOL, SUIT_COLOR, MENU_TILE_DIR, BACKGROUND_DIR, MENU_BG_PATH, TABLE_BG_PATH, HISTORY_MAP_PATH, USE_ART, ART_DEBUG,
    MAX_ART_CACHE_ENTRIES, CARDS_DIR, MUSIC_PATH, _BASE_CARD_W, _BASE_CARD_H, _BASE_W, _BASE_H,
    GM_NORMAL, GM_HOT_SEAT, GM_TIMED, GM_TOURNAMENT, PANEL, PANEL_BORD, PANEL_2, PANEL_GLOW, BG, CARD_FACE,
    CARD_SEL, CARD_HOVER, CARD_RED, CARD_BLACK, CARD_JOKER, TEXT, TEXT_DIM, BTN, BTN_H, BTN_TXT, ACCENT, RED,
    YELLOW, BLACK, OUT_OK, OUT_BAD, TOOLTIP_BG, UNDO_CLR, RES_ACTIVE, RES_ACT_H, CAPS_CLR, TIMER_OK, TIMER_WARN,
    TIMER_CRIT, ACH_BG, ACH_BORD, format_time_ms
)
from src.models import (
    Card, NumEntry, Caravan, PlayerState, BotPersonality, PERSONALITIES, DEFAULT_PERSONALITY, BENNY,
    standard_card_list, can_play_number_on_caravan, can_play_picture_on_target, get_bot_delay_ms
)
from src.achievements import unlock_achievement, tick_achievement_popup

_FONT_CANDIDATES = [
    "consolas", "couriernew", "dejavusansmono", "liberationmono",
    "ubuntumono", "freemono", "droidsansmono", "arial", "",
]

def _make_sysfont(size, bold=False):
    for name in _FONT_CANDIDATES:
        try:
            f = pygame.font.SysFont(name, size, bold=bold)
            if f.size("Тест")[0] > 0: return f
        except: pass
    return pygame.font.Font(None, max(8, size))

_menu_background_cache: Dict[Tuple[int, int], pygame.Surface] = {}
_table_background_cache: Dict[Tuple[int, int], pygame.Surface] = {}
_history_map_cache: Dict[Tuple[int, int], pygame.Surface] = {}
_menu_tile_surfaces: Dict[str, pygame.Surface] = {}
_menu_tile_scaled_cache: Dict[Tuple[str, int, int], pygame.Surface] = {}

def load_menu_tile_image(key: str) -> Optional[pygame.Surface]:
    if key in _menu_tile_surfaces:
        return _menu_tile_surfaces[key]
    fp = os.path.join(MENU_TILE_DIR, f"{key}.png")
    try:
        if os.path.exists(fp):
            surf = pygame.image.load(fp).convert_alpha()
            _menu_tile_surfaces[key] = surf
            return surf
    except: pass
    return None

def _scaled_menu_tile(key: str, src: pygame.Surface, max_w: int, max_h: int) -> pygame.Surface:
    cache_key = (key, max_w, max_h)
    cached = _menu_tile_scaled_cache.get(cache_key)
    if cached is not None:
        return cached
    sw, sh = src.get_size()
    scale = min(max_w / sw, max_h / sh)
    nw, nh = max(1, int(sw * scale)), max(1, int(sh * scale))
    
    # High-quality downscaling (mipmapping) to avoid pixelation
    surf = src
    while sw > nw * 2 and sh > nh * 2:
        sw //= 2
        sh //= 2
        surf = pygame.transform.smoothscale(surf, (sw, sh))
    
    scaled = pygame.transform.smoothscale(surf, (nw, nh))
    _menu_tile_scaled_cache[cache_key] = scaled
    return scaled

def draw_menu_tile_art(key: str, rect: pygame.Rect, hovered: bool):
    screen = state.screen
    src = load_menu_tile_image(key)
    if src is None: return False

    pad = max(2, int(min(rect.w, rect.h) * (0.01 if hovered else 0.025)))
    max_w = rect.w - pad * 2
    max_h = rect.h - pad * 2
    img = _scaled_menu_tile(key, src, max_w, max_h)
    x = rect.centerx - img.get_width() // 2
    y = rect.centery - img.get_height() // 2

    shadow = pygame.Surface((img.get_width() + 18, img.get_height() + 18), pygame.SRCALPHA)
    pygame.draw.rect(shadow, (0, 0, 0, 86 if hovered else 62), pygame.Rect(9, 10, img.get_width(), img.get_height()), border_radius=18)
    screen.blit(shadow, (x - 9, y - 9))
    screen.blit(img, (x, y))

    if hovered:
        glow = pygame.Surface((img.get_width() + 20, img.get_height() + 20), pygame.SRCALPHA)
        pygame.draw.rect(glow, (222, 174, 88, 58), pygame.Rect(2, 2, img.get_width() + 16, img.get_height() + 16), border_radius=22)
        screen.blit(glow, (x - 10, y - 10))
        screen.blit(img, (x, y))
    return True

def load_menu_background() -> Optional[pygame.Surface]:
    if state.menu_background_surface is not None:
        return state.menu_background_surface

    candidates = [MENU_BG_PATH]
    try:
        if os.path.isdir(BACKGROUND_DIR):
            for fn in os.listdir(BACKGROUND_DIR):
                if fn.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                    fp = os.path.join(BACKGROUND_DIR, fn)
                    if fp not in candidates: candidates.append(fp)
    except: pass

    for fp in candidates:
        try:
            if os.path.exists(fp):
                state.menu_background_surface = pygame.image.load(fp).convert()
                return state.menu_background_surface
        except: continue
    return None

def _scale_menu_background_to_screen(src: pygame.Surface) -> pygame.Surface:
    WIDTH = state.WIDTH
    HEIGHT = state.HEIGHT
    key = (WIDTH, HEIGHT)
    cached = _menu_background_cache.get(key)
    if cached is not None: return cached

    sw, sh = src.get_size()
    scale = max(WIDTH / sw, HEIGHT / sh)
    nw, nh = int(sw * scale), int(sh * scale)
    scaled = pygame.transform.smoothscale(src, (nw, nh))

    result = pygame.Surface((WIDTH, HEIGHT)).convert()
    result.blit(scaled, ((WIDTH - nw) // 2, (HEIGHT - nh) // 2))
    _menu_background_cache.clear()
    _menu_background_cache[key] = result
    return result

def draw_main_menu_background():
    screen = state.screen
    WIDTH = state.WIDTH
    HEIGHT = state.HEIGHT
    src = load_menu_background()
    if src is None:
        draw_table_background()
        return

    screen.blit(_scale_menu_background_to_screen(src), (0, 0))
    shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 72))
    screen.blit(shade, (0, 0))

    vignette = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    edge_h = max(80, HEIGHT // 4)
    for y in range(edge_h):
        alpha = int(78 * (1 - y / edge_h))
        pygame.draw.line(vignette, (0, 0, 0, alpha), (0, y), (WIDTH, y))
        pygame.draw.line(vignette, (0, 0, 0, alpha), (0, HEIGHT - 1 - y), (WIDTH, HEIGHT - 1 - y))
    screen.blit(vignette, (0, 0))

def draw_ui_background():
    draw_main_menu_background()

def load_table_background_image() -> Optional[pygame.Surface]:
    if state.table_background_surface is not None:
        return state.table_background_surface
    try:
        if os.path.exists(TABLE_BG_PATH):
            state.table_background_surface = pygame.image.load(TABLE_BG_PATH).convert()
            return state.table_background_surface
    except:
        state.table_background_surface = None
    return None

def _scale_table_background_to_screen(src: pygame.Surface) -> pygame.Surface:
    WIDTH = state.WIDTH
    HEIGHT = state.HEIGHT
    key = (WIDTH, HEIGHT)
    cached = _table_background_cache.get(key)
    if cached is not None: return cached
    sw, sh = src.get_size()
    scale = max(WIDTH / sw, HEIGHT / sh)
    nw, nh = int(sw * scale), int(sh * scale)
    scaled = pygame.transform.smoothscale(src, (nw, nh))
    result = pygame.Surface((WIDTH, HEIGHT)).convert()
    result.blit(scaled, ((WIDTH - nw) // 2, (HEIGHT - nh) // 2))
    _table_background_cache.clear()
    _table_background_cache[key] = result
    return result

_history_map_source = None
def load_history_map() -> Optional[pygame.Surface]:
    global _history_map_source
    if _history_map_source is not None:
        return _history_map_source
    try:
        if os.path.exists(HISTORY_MAP_PATH):
            _history_map_source = pygame.image.load(HISTORY_MAP_PATH).convert()
            return _history_map_source
    except: pass
    return None

def _scale_history_map_to_screen(src: pygame.Surface) -> pygame.Surface:
    WIDTH = state.WIDTH
    HEIGHT = state.HEIGHT
    key = (WIDTH, HEIGHT)
    cached = _history_map_cache.get(key)
    if cached is not None: return cached
    sw, sh = src.get_size()
    scale = max(WIDTH / sw, HEIGHT / sh)
    nw, nh = int(sw * scale), int(sh * scale)
    scaled = pygame.transform.smoothscale(src, (nw, nh))
    result = pygame.Surface((WIDTH, HEIGHT)).convert()
    result.blit(scaled, ((WIDTH - nw) // 2, (HEIGHT - nh) // 2))
    _history_map_cache.clear()
    _history_map_cache[key] = result
    return result

def draw_history_map():
    screen = state.screen
    WIDTH = state.WIDTH
    HEIGHT = state.HEIGHT
    src = load_history_map()
    if src is not None:
        screen.blit(_scale_history_map_to_screen(src), (0, 0))
    else:
        draw_main_menu_background()

def _draw_dashed_line(surface, color, start_pos, end_pos, width=1, dash_length=10):
    x1, y1 = start_pos
    x2, y2 = end_pos
    dl = math.hypot(x2 - x1, y2 - y1)
    if dl == 0: return
    dashes = int(dl / dash_length)
    if dashes == 0:
        pygame.draw.line(surface, color, (x1, y1), (x2, y2), width)
        return
    for i in range(dashes):
        if i % 2 == 0:
            sx = x1 + (x2 - x1) * (i / dashes)
            sy = y1 + (y2 - y1) * (i / dashes)
            ex = x1 + (x2 - x1) * ((i + 1) / dashes)
            ey = y1 + (y2 - y1) * ((i + 1) / dashes)
            pygame.draw.line(surface, color, (sx, sy), (ex, ey), width)

def draw_map_path(coords, current_stage):
    screen = state.screen
    # Draw dashed lines between completed and current stages
    for i in range(min(len(coords) - 1, current_stage)):
        p1 = coords[i]
        p2 = coords[i+1]
        _draw_dashed_line(screen, (100, 40, 20), p1, p2, width=3, dash_length=15)

def draw_map_node(x, y, active, done, hovered):
    screen = state.screen
    if active:
        # Pulsing shadow for the pin
        now = pygame.time.get_ticks()
        pulse = 6 + int(math.sin(now * 0.005) * 3)
        s_surf = pygame.Surface((30, 30), pygame.SRCALPHA)
        pygame.draw.circle(s_surf, (0, 0, 0, 100), (15, 15), pulse)
        screen.blit(s_surf, (x - 15, y - 5))
        
        # Red pushpin
        pygame.draw.line(screen, (100, 100, 100), (x, y - 8), (x - 4, y + 4), 2) # Pin needle
        pygame.draw.circle(screen, (200, 40, 40), (x + 2, y - 10), 8)
        pygame.draw.circle(screen, (255, 100, 100), (x, y - 12), 3) # Highlight
        
    elif done:
        # Drawn "X" mark
        color = (150, 40, 40) if hovered else (100, 30, 30)
        w = 4 if hovered else 3
        pygame.draw.line(screen, color, (x - 8, y - 8), (x + 8, y + 8), w)
        pygame.draw.line(screen, color, (x - 8, y + 8), (x + 8, y - 8), w)
        
    else:
        # Penciled circle
        color = (60, 50, 40)
        pygame.draw.circle(screen, color, (x, y), 8, 2)
        pygame.draw.circle(screen, color, (x, y), 2)
        if hovered:
            pygame.draw.circle(screen, (200, 180, 120), (x, y), 12, 2)

def draw_map_tooltip(x, y, stage, done):
    screen = state.screen
    FONT = state.FONT
    
    name = stage.get("name", "?")
    loc = stage.get("location", "")
    diff = stage.get("diff", "easy").upper()
    rew = f"+{int(stage.get('reward_caps', 0))} caps" if state.language == "en" else f"+{int(stage.get('reward_caps', 0))} крышек"
    
    tw1, th1 = FONT.size(name)
    tw2, th2 = state.SMALL.size(loc)
    tw3, th3 = state.SMALL.size(f"{diff} | {rew}")
    
    tw = max(tw1, tw2, tw3) + 30
    th = th1 + th2 + th3 + 25
    
    tx = x + 25
    ty = y - th - 10
    if tx + tw > state.WIDTH: tx = x - tw - 25
    if ty < 0: ty = y + 25
    
    rect = pygame.Rect(tx, ty, tw, th)
    shadow_rect = pygame.Rect(tx + 6, ty + 6, tw, th)
    
    # Shadow
    s_surf = pygame.Surface((tw, th), pygame.SRCALPHA)
    s_surf.fill((0, 0, 0, 120))
    screen.blit(s_surf, shadow_rect.topleft)
    
    # Parchment background
    pygame.draw.rect(screen, (235, 220, 185), rect)
    pygame.draw.rect(screen, (110, 80, 50), rect, 2)
    
    ink_color = (50, 30, 20)
    draw_text_center(name, pygame.Rect(tx, ty + 5, tw, th1), ink_color, FONT)
    draw_text_center(loc, pygame.Rect(tx, ty + 5 + th1, tw, th2), (90, 60, 40), state.SMALL)
    draw_text_center(f"{diff} | {rew}", pygame.Rect(tx, ty + 10 + th1 + th2, tw, th3), ink_color, state.SMALL)
    
    # (Removed old tooltip)

# ── Card Animation Engine ────────────────────────────────────
class CardAnimation:
    def __init__(self, card, start_pos, end_pos, duration_ms=300, delay_ms=0):
        self.card = card
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.start_ticks = pygame.time.get_ticks() + delay_ms
        self.duration_ms = duration_ms
        self.completed = False
        
    def get_current_pos(self, now):
        if now < self.start_ticks:
            return self.start_pos
        elapsed = now - self.start_ticks
        if elapsed >= self.duration_ms:
            self.completed = True
            return self.end_pos
        t = elapsed / self.duration_ms
        ease_t = t * (2.0 - t)
        x = self.start_pos[0] + (self.end_pos[0] - self.start_pos[0]) * ease_t
        y = self.start_pos[1] + (self.end_pos[1] - self.start_pos[1]) * ease_t
        return (x, y)

active_card_animations: List[CardAnimation] = []
animating_card_keys: Set[str] = set()
_prev_player_hand_keys: List[str] = []
_prev_caravan_sizes: List[int] = [0, 0, 0, 0, 0, 0]
current_match_modifiers: Dict[str, Any] = {"banned_suits": [], "starting_hand_modifier": 0}

def build_table_felt(w: int, h: int):
    surf = pygame.Surface((w, h))
    theme = getattr(state.app_settings, "table_theme", 0)
    if theme == 1:   # Amber Dunes
        c_start = (85, 62, 28)
        c_end = (24, 15, 8)
        bord_c = (115, 85, 38)
    elif theme == 2: # Royal Crimson
        c_start = (76, 16, 22)
        c_end = (20, 6, 8)
        bord_c = (110, 24, 30)
    elif theme == 3: # Midnight Oasis
        c_start = (14, 38, 64)
        c_end = (4, 10, 20)
        bord_c = (24, 60, 95)
    else:            # Default Deep Forest Green
        c_start = (22, 48, 28)
        c_end = (7, 13, 9)
        bord_c = (38, 76, 46)

    cx, cy = w // 2, h // 2
    max_dist = math.hypot(cx, cy)
    steps = 100
    for i in range(steps):
        frac = i / steps
        r = max_dist * (1.0 - frac)
        color = (
            int(c_start[0] * (1.0 - frac) + c_end[0] * frac),
            int(c_start[1] * (1.0 - frac) + c_end[1] * frac),
            int(c_start[2] * (1.0 - frac) + c_end[2] * frac)
        )
        pygame.draw.circle(surf, color, (cx, cy), int(r))

    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    for i in range(0, w + h, 6):
        pygame.draw.line(overlay, (255, 255, 255, 3), (i, 0), (i - h, h), 1)
        pygame.draw.line(overlay, (0, 0, 0, 5), (i + 3, 0), (i + 3 - h, h), 1)
        pygame.draw.line(overlay, (255, 255, 255, 3), (0, i), (w, i - w), 1)
        pygame.draw.line(overlay, (0, 0, 0, 5), (0, i + 3), (w, i + 3 - w), 1)
    surf.blit(overlay, (0, 0))

    pygame.draw.rect(surf, bord_c, pygame.Rect(10, 10, w - 20, h - 20), 2, border_radius=14)
    for x in range(16, w - 16, 12):
        pygame.draw.line(surf, (150, 125, 45), (x, 15), (x + 6, 15), 1)
        pygame.draw.line(surf, (150, 125, 45), (x, h - 16), (x + 6, h - 16), 1)
    for y in range(16, h - 16, 12):
        pygame.draw.line(surf, (150, 125, 45), (15, y), (15, y + 6), 1)
        pygame.draw.line(surf, (150, 125, 45), (w - 16, y), (w - 16, y + 6), 1)
    state.table_felt_surface = surf

def draw_table_background():
    screen = state.screen
    WIDTH = state.WIDTH
    HEIGHT = state.HEIGHT
    src = load_table_background_image()
    if src is not None:
        screen.blit(_scale_table_background_to_screen(src), (0, 0))
        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 10))
        screen.blit(shade, (0, 0))
        return
    if state.table_felt_surface:
        screen.blit(state.table_felt_surface, (0, 0))
    else:
        screen.fill(BG)

def apply_resolution(w, h, fullscreen=False):
    global _menu_background_cache, _table_background_cache

    if fullscreen:
        try:
            state.screen = pygame.display.set_mode((w, h), pygame.FULLSCREEN | pygame.SCALED)
        except:
            try:
                state.screen = pygame.display.set_mode((w, h), pygame.FULLSCREEN)
            except:
                info = pygame.display.Info()
                w, h = info.current_w, info.current_h
                state.screen = pygame.display.set_mode((w, h), pygame.FULLSCREEN)
    else:
        state.screen = pygame.display.set_mode((w, h))

    state.WIDTH = w
    state.HEIGHT = h
    pygame.display.set_caption("Dustway: Desert Trader")
    build_table_felt(w, h)
    _menu_background_cache.clear()
    _table_background_cache.clear()

    s = state.WIDTH / _BASE_W
    state.FONT  = _make_sysfont(max(10, int(26 * s)))
    state.SMALL = _make_sysfont(max(8,  int(20 * s)))
    state.TINY  = _make_sysfont(max(6,  int(16 * s)))
    state.TITLE = _make_sysfont(max(16, int(56 * s)), bold=True)

    state.MARGIN        = max(10, int(20 * s))
    state.GAP           = max(6,  int(12 * s))
    state.TOP_BAR_H     = max(70, int(100 * s))
    state.CARD_W        = max(50, int(_BASE_CARD_W * s))
    state.CARD_H        = max(70, int(_BASE_CARD_H * s))
    state.SELECT_RAISE  = max(8,  int(16 * s))
    state.PIC_BADGE_W   = max(18, int(26 * s))
    state.PIC_BADGE_H   = max(18, int(26 * s))
    state.GRID_CARD_W   = max(52, int(84 * s))
    state.GRID_CARD_H   = max(38, int(60 * s))
    state.STACK_OVERLAP_X       = max(18, int(30 * s))
    state.STACK_OVERLAP_X_TIGHT = max(14, int(20 * s))
    state.STACK_PAD_X           = max(10, int(16 * s))

    state.text_cache.clear()
    state.card_label_cache.clear()

_back_cache: Dict = {}

def get_card_back_surf(design: int, w: int, h: int) -> pygame.Surface:
    key = (design, w, h)
    if key in _back_cache: return _back_cache[key]
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    s.fill((0, 0, 0, 0))

    if design == 0:   # Green felt — diamond grid
        pygame.draw.rect(s, (35, 80, 45), (0, 0, w, h), border_radius=10)
        pygame.draw.rect(s, (55, 110, 65), (4, 4, w - 8, h - 8), border_radius=7)
        for gx in range(0, w, max(8, w // 10)):
            for gy in range(0, h, max(8, h // 8)):
                pts = [(gx, gy - 4), (gx + 4, gy), (gx, gy + 4), (gx - 4, gy)]
                pygame.draw.polygon(s, (70, 140, 80), pts, 1)
        pygame.draw.rect(s, (90, 160, 100), (0, 0, w, h), 2, border_radius=10)

    elif design == 1:  # Red wasteland
        pygame.draw.rect(s, (130, 25, 25), (0, 0, w, h), border_radius=10)
        pygame.draw.rect(s, (160, 40, 40), (4, 4, w - 8, h - 8), border_radius=7)
        for i in range(0, w + h, max(6, w // 14)):
            x = i if i < w else w - 1
            y = 0 if i < w else i - w
            pygame.draw.circle(s, (180, 60, 60), (x, y), 2)
            pygame.draw.circle(s, (180, 60, 60), (w - x, h - y), 2)
        cx, cy = w // 2, h // 2
        pygame.draw.circle(s, (180, 60, 60), (cx, cy), min(w, h) // 4, 1)
        pygame.draw.rect(s, (200, 80, 80), (0, 0, w, h), 2, border_radius=10)

    elif design == 2:  # Casino blue
        pygame.draw.rect(s, (25, 40, 130), (0, 0, w, h), border_radius=10)
        pygame.draw.rect(s, (40, 60, 160), (4, 4, w - 8, h - 8), border_radius=7)
        for sx in range(w // 4, w, w // 4):
            for sy in range(h // 4, h, h // 4):
                pygame.draw.circle(s, (60, 90, 190), (sx, sy), 3, 1)
                for ang in range(0, 360, 45):
                    r = 8
                    ex = sx + int(r * math.cos(math.radians(ang)))
                    ey = sy + int(r * math.sin(math.radians(ang)))
                    pygame.draw.line(s, (60, 90, 190), (sx, sy), (ex, ey), 1)
        pygame.draw.rect(s, (80, 120, 220), (0, 0, w, h), 2, border_radius=10)

    elif design == 3:  # Baron — black gold
        pygame.draw.rect(s, (12, 12, 16), (0, 0, w, h), border_radius=10)
        pygame.draw.rect(s, (22, 22, 30), (4, 4, w - 8, h - 8), border_radius=7)
        for cx2, cy2 in [(12, 12), (w - 12, 12), (12, h - 12), (w - 12, h - 12)]:
            pygame.draw.circle(s, (160, 130, 50), (cx2, cy2), 8, 1)
            pygame.draw.circle(s, (160, 130, 50), (cx2, cy2), 4, 1)
        fnt = pygame.font.Font(None, max(20, h // 3))
        ht = fnt.render("D", True, (160, 130, 50))
        s.blit(ht, (w // 2 - ht.get_width() // 2, h // 2 - ht.get_height() // 2))
        pygame.draw.rect(s, (160, 130, 50), (0, 0, w, h), 2, border_radius=10)

    _back_cache[key] = s
    return s

BACK_NAMES = ["Green Felt", "Wasteland", "Casino Blue", "Midnight Gold"]

class CardArt:
    def __init__(self, base_dir, debug=False):
        self.base_dir = base_dir
        self.debug = debug
        self._files: Dict = {}
        self._scaled: OrderedDict = OrderedDict()
        self._missing: set = set()

    def _candidates(self, card):
        r = "JKR" if card.rank == "JKR" else card.rank
        s = card.suit or ""
        sl = s.lower()
        sym = SUIT_SYMBOL.get(card.suit or "", "")
        if r == "JKR":
            return ["JKR.png", "JOKER.png", "Joker.png", "joker.png", "JKR_1.png", "JKR-1.png", "JKR1.png"]
        return [
            f"{r}_{s}.png", f"{r}-{s}.png", f"{r}{s}.png", f"{s}_{r}.png", f"{s}-{r}.png", f"{s}{r}.png",
            f"{r}_{sl}.png", f"{r}-{sl}.png", f"{r}{sl}.png", f"{sl}_{r}.png", f"{sl}-{r}.png", f"{sl}{r}.png",
            f"{r}{sym}.png", f"{r}_{sym}.png", f"{r}-{sym}.png"
        ]

    def _find_file(self, card, variant):
        if not USE_ART: return None
        for sub in (["stack", "hand", ""] if variant == "stack" else ["thumb", "hand", ""] if variant == "thumb" else ["hand", ""]):
            folder = os.path.join(self.base_dir, sub) if sub else self.base_dir
            for name in self._candidates(card):
                fp = os.path.join(folder, name)
                if os.path.exists(fp): return fp
        if self.debug: self._missing.add(f"{variant}:{card.key()}")
        return None

    def get_scaled(self, card, size, variant="hand"):
        fp = self._find_file(card, variant)
        if fp is None: return None
        w, h = int(size[0]), int(size[1])
        key = (fp, w, h)
        if key in self._scaled:
            self._scaled.move_to_end(key)
            return self._scaled[key]
        try:
            if fp not in self._files:
                self._files[fp] = pygame.image.load(fp).convert_alpha()
            base = self._files[fp]
            surf = base if base.get_width() == w and base.get_height() == h else pygame.transform.smoothscale(base, (w, h))
            self._scaled[key] = surf
            if len(self._scaled) > MAX_ART_CACHE_ENTRIES:
                self._scaled.popitem(last=False)
            return surf
        except: return None

CARD_ART = CardArt(CARDS_DIR, debug=ART_DEBUG)

def _fk(font): return font.size("A")

def render_cached(text, font, color):
    key = (_fk(font), text, color)
    if key not in state.text_cache:
        state.text_cache[key] = font.render(text, True, color)
    return state.text_cache[key]

def draw_text(text, x, y, color=TEXT, font=None):
    screen = state.screen
    if font is None: font = state.FONT
    img = render_cached(str(text), font, color)
    screen.blit(img, (x, y))
    return img.get_width(), img.get_height()

def draw_text_fitted(text, rect, color=TEXT, font=None, center=True):
    screen = state.screen
    if font is None: font = state.FONT
    img = render_cached(str(text), font, color)
    iw, ih = img.get_width(), img.get_height()
    if iw <= rect.width and ih <= rect.height:
        x = rect.x + (rect.width - iw) // 2 if center else rect.x
        y = rect.y + (rect.height - ih) // 2 if center else rect.y
        screen.blit(img, (x, y))
    else:
        scale = min(rect.width / max(1, iw), rect.height / max(1, ih))
        scaled_img = pygame.transform.smoothscale(img, (int(iw * scale), int(ih * scale)))
        x = rect.x + (rect.width - scaled_img.get_width()) // 2 if center else rect.x
        y = rect.y + (rect.height - scaled_img.get_height()) // 2 if center else rect.y
        screen.blit(scaled_img, (x, y))

def draw_text_center(text, rect, color=TEXT, font=None):
    draw_text_fitted(text, rect, color, font)

def draw_text_center_outlined(text, rect, color=TEXT, outline=(0, 0, 0), font=None, offset=1):
    screen = state.screen
    if font is None: font = state.FONT
    txt = str(text)
    img = render_cached(txt, font, color)
    oi = render_cached(txt, font, outline)
    iw, ih = img.get_width(), img.get_height()
    x = rect.x + (rect.width - iw) // 2
    y = rect.y + (rect.height - ih) // 2
    for ox, oy in ((-offset, 0), (offset, 0), (0, -offset), (0, offset), (-offset, -offset), (-offset, offset), (offset, -offset), (offset, offset)):
        screen.blit(oi, (x + ox, y + oy))
    screen.blit(img, (x, y))

def wrap_text(text, font, max_width):
    words = str(text).split(' ')
    lines = []
    current_line = []
    for word in words:
        test_line = ' '.join(current_line + [word])
        if font.size(test_line)[0] <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
                current_line = [word]
            else:
                lines.append(word)
    if current_line:
        lines.append(' '.join(current_line))
    return lines

def draw_shadow_rect(rect, radius=12, alpha=90, offset=(4, 5)):
    screen = state.screen
    sh = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.rect(sh, (0, 0, 0, alpha), pygame.Rect(0, 0, rect.w, rect.h), border_radius=radius)
    screen.blit(sh, (rect.x + offset[0], rect.y + offset[1]))

def draw_panel(rect, fill=PANEL, border=PANEL_BORD, glow=False):
    screen = state.screen
    WIDTH = state.WIDTH
    # Deep shadow
    sh = pygame.Surface((rect.w + 8, rect.h + 8), pygame.SRCALPHA)
    pygame.draw.rect(sh, (0, 0, 0, 160), pygame.Rect(4, 5, rect.w, rect.h), border_radius=16)
    screen.blit(sh, rect.topleft)
    
    pygame.draw.rect(screen, fill, rect, border_radius=14)
    # Bright top edge
    pygame.draw.rect(screen, lighten(fill, 25), pygame.Rect(rect.x + 2, rect.y + 2, rect.w - 4, 3), border_radius=4)
    # Dark bottom edge
    dc = (max(0, fill[0]-20), max(0, fill[1]-20), max(0, fill[2]-20))
    pygame.draw.rect(screen, dc, pygame.Rect(rect.x + 2, rect.bottom - 5, rect.w - 4, 3), border_radius=4)
    
    # Outer border
    b_color = PANEL_GLOW if glow else border
    pygame.draw.rect(screen, b_color, rect, 2, border_radius=14)
    if glow:
        g_surf = pygame.Surface((rect.w + 4, rect.h + 4), pygame.SRCALPHA)
        pygame.draw.rect(g_surf, (*b_color[:3], 80), pygame.Rect(0, 0, rect.w + 4, rect.h + 4), 2, border_radius=16)
        screen.blit(g_surf, (rect.x - 2, rect.y - 2))

def lighten(c, a=18):
    from src.config import clamp
    return (int(clamp(c[0] + a)), int(clamp(c[1] + a)), int(clamp(c[2] + a)))

def draw_panel_title_bar(rect, text="", color=ACCENT):
    screen = state.screen
    WIDTH = state.WIDTH
    bar = pygame.Rect(rect.x + 2, rect.y + 2, rect.w - 4, max(36, int(44 * WIDTH / _BASE_W)))
    s = pygame.Surface((bar.w, bar.h), pygame.SRCALPHA)
    # Simple vertical gradient
    for y in range(bar.h):
        alpha = int(90 * (1 - y/bar.h))
        pygame.draw.line(s, (*color[:3], alpha), (0, y), (bar.w, y))
    screen.blit(s, bar.topleft)
    pygame.draw.line(screen, color, (bar.x, bar.bottom), (bar.right, bar.bottom), 2)

def draw_button(text, rect, pos, color=BTN, hover=BTN_H, font=None):
    screen = state.screen
    if font is None: font = state.FONT
    hov = rect.collidepoint(*pos)
    c = hover if hov else color
    
    # Strong shadow
    sh = pygame.Surface((rect.w + 6, rect.h + 6), pygame.SRCALPHA)
    pygame.draw.rect(sh, (0, 0, 0, 140), pygame.Rect(3, 4, rect.w, rect.h), border_radius=10)
    screen.blit(sh, rect.topleft)
    
    # Base fill
    pygame.draw.rect(screen, c, rect, border_radius=10)
    
    # Inner bright top line (Highlight)
    pygame.draw.rect(screen, lighten(c, 40), pygame.Rect(rect.x + 3, rect.y + 2, rect.w - 6, 2), border_radius=2)
    # Inner dark bottom line (Shading)
    dc = (max(0, c[0]-30), max(0, c[1]-30), max(0, c[2]-30))
    pygame.draw.rect(screen, dc, pygame.Rect(rect.x + 3, rect.bottom - 4, rect.w - 6, 2), border_radius=2)
    
    # Border
    pygame.draw.rect(screen, lighten(c, 60) if hov else lighten(c, 20), rect, 2, border_radius=10)
    
    draw_text_center(text, rect, BTN_TXT, font=font)
    return hov

def card_color_for(card):
    if card.rank == "JKR": return CARD_JOKER
    return SUIT_COLOR.get(card.suit or "", TEXT)

def get_card_label_surf(card, font):
    color = card_color_for(card)
    key = (card.key(), _fk(font), color)
    if key not in state.card_label_cache:
        state.card_label_cache[key] = font.render(card.label(), True, color)
    return state.card_label_cache[key]

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

def ui_rects():
    WIDTH = state.WIDTH
    HEIGHT = state.HEIGHT
    CARD_H = state.CARD_H
    side_pad = max(96, int(WIDTH * 0.075))
    top_h = max(46, int(HEIGHT * 0.065))
    bottom_margin = max(12, int(HEIGHT * 0.018))
    hand_h = max(CARD_H + 38, int(HEIGHT * 0.20))
    gap = max(22, int(HEIGHT * 0.028))
    route_w = WIDTH - side_pad * 2
    available_h = HEIGHT - top_h - hand_h - bottom_margin - gap * 2
    route_h = max(CARD_H + 30, available_h // 2)

    top = pygame.Rect(0, 0, WIDTH, top_h)
    bot_area = pygame.Rect(side_pad, top_h + gap // 2, route_w, route_h)
    ply_area = pygame.Rect(side_pad, bot_area.bottom + gap, route_w, route_h)
    hand = pygame.Rect(side_pad, HEIGHT - bottom_margin - hand_h, route_w, hand_h)
    return top, bot_area, ply_area, hand

def caravan_slots(area):
    WIDTH = state.WIDTH
    HEIGHT = state.HEIGHT
    w = area.width // 3
    pad_x = max(10, int(WIDTH * 0.010))
    pad_y = max(8, int(HEIGHT * 0.010))
    return [
        pygame.Rect(area.x + i * w + pad_x, area.y + pad_y, w - 2 * pad_x, area.height - 2 * pad_y)
        for i in range(3)
    ]

def get_idx_at(pos, rects):
    for i in range(len(rects) - 1, -1, -1):
        if rects[i].collidepoint(pos): return i
    return -1

def _card_text_color(card):
    if card.rank == "JKR": return CARD_JOKER
    if card.suit in ("H", "D"): return CARD_RED
    return CARD_BLACK

def _draw_value_badge(rect, value):
    screen = state.screen
    WIDTH = state.WIDTH
    SMALL = state.SMALL
    bw, bh = max(36, int(50 * WIDTH / _BASE_W)), max(22, int(30 * WIDTH / _BASE_W))
    pad = pygame.Rect(rect.x + 4, rect.y + rect.h - bh - 4, bw, bh)
    draw_shadow_rect(pad, radius=6, alpha=85, offset=(1, 2))
    bs = pygame.Surface((bw, bh), pygame.SRCALPHA)
    pygame.draw.rect(bs, (22, 20, 18, 228), pygame.Rect(0, 0, bw, bh), border_radius=6)
    pygame.draw.rect(bs, (196, 166, 88, 235), pygame.Rect(0, 0, bw, bh), 2, border_radius=6)
    screen.blit(bs, pad.topleft)
    draw_text_center_outlined(str(value), pad, (248, 236, 205), (15, 10, 6), SMALL, offset=1)

def draw_vector_suit_symbol(surface, suit, rect, color, alpha=255):
    if not suit: return
    s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    w, h = rect.w, rect.h
    cx, cy = w / 2.0, h / 2.0
    
    if suit == "D":
        points = [(cx, 0), (w, cy), (cx, h), (0, cy)]
        pygame.draw.polygon(s, color, points)
    elif suit == "H":
        r = w / 4.0
        pygame.draw.circle(s, color, (int(cx - r), int(r + 1)), int(r))
        pygame.draw.circle(s, color, (int(cx + r), int(r + 1)), int(r))
        points = [(int(cx - 2.0 * r), int(r + 2.0)), (int(cx + 2.0 * r), int(r + 2.0)), (int(cx), h)]
        pygame.draw.polygon(s, color, points)
    elif suit == "S":
        r = w / 4.0
        by = h - r - 2.0
        pygame.draw.circle(s, color, (int(cx - r), int(by)), int(r))
        pygame.draw.circle(s, color, (int(cx + r), int(by)), int(r))
        points = [(int(cx - 2.0 * r), int(by - 2.0)), (int(cx + 2.0 * r), int(by - 2.0)), (int(cx), 0)]
        pygame.draw.polygon(s, color, points)
        base_w = w / 4.0
        pygame.draw.polygon(s, color, [(int(cx), int(cy)), (int(cx - base_w), h), (int(cx + base_w), h)])
    elif suit == "C":
        r = w / 4.5
        pygame.draw.circle(s, color, (int(cx), int(r + 1)), int(r))
        pygame.draw.circle(s, color, (int(cx - r), int(h - r - 2)), int(r))
        pygame.draw.circle(s, color, (int(cx + r), int(h - r - 2)), int(r))
        base_w = w / 4.0
        pygame.draw.polygon(s, color, [(int(cx), int(cy)), (int(cx - base_w), h), (int(cx + base_w), h)])
    elif suit == "JKR":
        points = []
        size = min(w, h)
        for i in range(10):
            angle = i * math.pi / 5.0 - math.pi / 2.0
            cr = (size / 2.0) if i % 2 == 0 else (size / 4.0)
            points.append((int(cx + cr * math.cos(angle)), int(cy + cr * math.sin(angle))))
        pygame.draw.polygon(s, color, points)

    s.set_alpha(alpha)
    surface.blit(s, rect.topleft)

def _draw_card_face(rect, card, selected=False, hovered=False, value_override=None):
    screen = state.screen
    WIDTH = state.WIDTH
    SMALL = state.SMALL
    art_img = CARD_ART.get_scaled(card, (rect.w, rect.h), "hand") if USE_ART else None
    
    tx, ty = 0.0, 0.0
    sh_x, sh_y = 4.0, 5.0
    if hovered:
        mx, my = pygame.mouse.get_pos()
        cx, cy = rect.x + rect.w / 2.0, rect.y + rect.h / 2.0
        dx, dy = mx - cx, my - cy
        dist = math.hypot(rect.w / 2.0, rect.h / 2.0) or 1.0
        tx = max(-5.0, min(5.0, (dx / dist) * 5.0))
        ty = max(-7.0, min(7.0, (dy / dist) * 7.0))
        sh_x = 4.0 - tx * 0.8
        sh_y = 5.0 - ty * 0.8
        
    draw_r = pygame.Rect(rect.x + tx, rect.y + ty, rect.w, rect.h)

    if art_img:
        draw_shadow_rect(draw_r, 12, 80, offset=(sh_x, sh_y))
        screen.blit(art_img, draw_r)
        if selected:
            pygame.draw.rect(screen, CARD_SEL, draw_r, 4, border_radius=12)
            pygame.draw.rect(screen, ACCENT, draw_r, 2, border_radius=12)
        elif hovered:
            pygame.draw.rect(screen, CARD_HOVER, draw_r, 3, border_radius=12)
        if value_override is not None: _draw_value_badge(draw_r, value_override)
        return

    draw_shadow_rect(draw_r, 12, 85, offset=(sh_x, sh_y))
    face_col = CARD_FACE if not selected else (255, 255, 230)
    pygame.draw.rect(screen, face_col, draw_r, border_radius=12)
    inner = pygame.Rect(draw_r.x + 4, draw_r.y + 4, draw_r.w - 8, draw_r.h - 8)
    bord_col = CARD_RED if card.suit in ("H", "D") else (100, 100, 120)
    pygame.draw.rect(screen, bord_col, inner, 1, border_radius=8)
    tc = _card_text_color(card)
    rank_str = card.rank if card.rank != "JKR" else "★"
    pad = max(4, int(5 * WIDTH / _BASE_W))
    r_surf = SMALL.render(rank_str, True, tc)
    
    screen.blit(r_surf, (draw_r.x + pad, draw_r.y + pad))
    tiny_w = max(10, int(14 * WIDTH / _BASE_W))
    tiny_h = max(10, int(14 * WIDTH / _BASE_W))
    if card.suit:
        ts_rect = pygame.Rect(draw_r.x + pad, draw_r.y + pad + r_surf.get_height(), tiny_w, tiny_h)
        draw_vector_suit_symbol(screen, card.suit, ts_rect, tc)
        
    bx = draw_r.right - pad - r_surf.get_width()
    by = draw_r.bottom - pad - r_surf.get_height() - tiny_h
    screen.blit(r_surf, (bx, by + tiny_h))
    if card.suit:
        bs_rect = pygame.Rect(bx, by, tiny_w, tiny_h)
        draw_vector_suit_symbol(screen, card.suit, bs_rect, tc)
        
    big_w = max(24, int(draw_r.w * 0.45))
    big_h = max(32, int(draw_r.h * 0.45))
    big_rect = pygame.Rect(draw_r.x + (draw_r.w - big_w) // 2 + tx * 0.4, draw_r.y + (draw_r.h - big_h) // 2 + ty * 0.4, big_w, big_h)
    draw_vector_suit_symbol(screen, "JKR" if card.rank == "JKR" else card.suit, big_rect, tc, alpha=210)
    
    if selected:
        pygame.draw.rect(screen, ACCENT, draw_r, 3, border_radius=12)
        pygame.draw.rect(screen, CARD_SEL, draw_r, 1, border_radius=12)
    elif hovered:
        pygame.draw.rect(screen, CARD_HOVER, draw_r, 3, border_radius=12)
    else:
        pygame.draw.rect(screen, (180, 170, 148), draw_r, 2, border_radius=12)
    if value_override is not None: _draw_value_badge(draw_r, value_override)

def draw_hand_card(rect, card, selected=False, hovered=False):
    _draw_card_face(rect, card, selected=selected, hovered=hovered)

def draw_num_entry(rect, ne):
    screen = state.screen
    if ne.card.key() in animating_card_keys: return
    art = CARD_ART.get_scaled(ne.card, (rect.w, rect.h), "stack") if USE_ART else None
    if art:
        draw_shadow_rect(rect, 10, 75)
        screen.blit(art, rect)
        pygame.draw.rect(screen, BLACK, rect, 2, border_radius=10)
        _draw_value_badge(rect, ne.effective_value())
    else:
        _draw_card_face(rect, ne.card, value_override=ne.effective_value())
    bx, by = rect.right - 4 - state.PIC_BADGE_W, rect.y + 5
    for p in ne.pics[-3:]:
        badge = pygame.Rect(bx, by, state.PIC_BADGE_W, state.PIC_BADGE_H)
        bs = pygame.Surface((state.PIC_BADGE_W, state.PIC_BADGE_H), pygame.SRCALPHA)
        bs.fill((8, 12, 8, 210))
        screen.blit(bs, badge.topleft)
        bc = CARD_RED if p.suit in ("H", "D") and p.rank not in ("JKR",) else ACCENT
        pygame.draw.rect(screen, bc, badge, 1, border_radius=5)
        draw_text_center("★" if p.rank == "JKR" else p.rank, badge, bc, state.TINY)
        by += state.PIC_BADGE_H + 4

def build_entry_hitboxes(owner_name, slots, caravans):
    WIDTH = state.WIDTH
    CARD_H = state.CARD_H
    CARD_W = state.CARD_W
    overlap_x = state.STACK_OVERLAP_X
    overlap_tight = state.STACK_OVERLAP_X_TIGHT
    pad_x = state.STACK_PAD_X
    boxes = []
    for ci in range(3):
        cav = caravans[ci]
        base = slots[ci]
        overlap = overlap_tight if len(cav.nums) > 9 else overlap_x
        start = max(0, len(cav.nums) - 9)
        y = base.y + (base.height - CARD_H) // 2
        x0 = base.x + pad_x
        for ei in range(start, len(cav.nums)):
            r = pygame.Rect(x0 + (ei - start) * overlap, y, CARD_W, CARD_H)
            boxes.append((r, owner_name, ci, ei))
    return boxes

def draw_caravan_stack(slot, cav):
    screen = state.screen
    WIDTH = state.WIDTH
    CARD_H = state.CARD_H
    CARD_W = state.CARD_W
    overlap_x = state.STACK_OVERLAP_X
    overlap_tight = state.STACK_OVERLAP_X_TIGHT
    pad_x = state.STACK_PAD_X

    overlap = overlap_tight if len(cav.nums) > 9 else overlap_x
    start = max(0, len(cav.nums) - 9)
    y = slot.y + (slot.height - CARD_H) // 2
    x0 = slot.x + pad_x
    for ei in range(start, len(cav.nums)):
        r = pygame.Rect(x0 + (ei - start) * overlap, y, CARD_W, CARD_H)
        draw_num_entry(r, cav.nums[ei])
    if start > 0:
        badge = pygame.Rect(slot.x + 6, slot.y + 6, max(36, int(46 * WIDTH / _BASE_W)), 22)
        bs = pygame.Surface((badge.w, badge.h), pygame.SRCALPHA)
        bs.fill((8, 12, 8, 210))
        screen.blit(bs, badge.topleft)
        pygame.draw.rect(screen, ACCENT, badge, 1, border_radius=5)
        draw_text_center(f"+{start}", badge, ACCENT, state.TINY)

def hand_layout(area, n, sel, scroll):
    WIDTH = state.WIDTH
    CARD_H = state.CARD_H
    CARD_W = state.CARD_W
    sel_raise = state.SELECT_RAISE
    if n <= 0: return [], 0, 0, False
    left_pad = max(16, int(WIDTH * 0.014))
    top_pad = max(8, (area.height - CARD_H) // 2)
    avail = area.width - 2 * left_pad
    base_step = CARD_W + 10
    total = (n - 1) * base_step + CARD_W
    def make_rects(step, x0):
        return [pygame.Rect(x0 + i * step, area.y + top_pad - (sel_raise if i == sel else 0), CARD_W, CARD_H) for i in range(n)]
    if total <= avail:
        x0 = area.x + left_pad + (avail - total) // 2
        return make_rects(base_step, x0), 0, 0, False
    min_step = CARD_W + 2
    step = max(min_step, int((avail - CARD_W) / max(1, n - 1)))
    total2 = (n - 1) * step + CARD_W
    if total2 > avail:
        step = base_step
        total2 = (n - 1) * step + CARD_W
        max_sc = max(0, total2 - avail)
        scroll = max(0, min(max_sc, scroll))
        return make_rects(step, area.x + left_pad - scroll), scroll, max_sc, True
    return make_rects(step, area.x + left_pad), 0, 0, False

def draw_soft_route_slot(rect, active=False, invalid=False, sold=False):
    screen = state.screen
    WIDTH = state.WIDTH
    surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    if invalid:
        fill = (105, 45, 38, 24)
        border = (210, 95, 76, 155)
    elif sold:
        fill = (118, 105, 54, 24)
        border = (215, 182, 92, 155)
    elif active:
        fill = (110, 96, 58, 22)
        border = (220, 190, 112, 150)
    else:
        fill = (128, 104, 70, 14)
        border = (185, 150, 88, 86)
    pygame.draw.rect(surf, fill, pygame.Rect(0, 0, rect.w, rect.h), border_radius=14)
    dash = max(10, int(WIDTH * 0.007))
    gap = max(8, int(WIDTH * 0.005))
    width = 2 if active or invalid or sold else 1
    for x in range(10, rect.w - 10, dash + gap):
        pygame.draw.line(surf, border, (x, 2), (min(x + dash, rect.w - 10), 2), width)
        pygame.draw.line(surf, border, (x, rect.h - 3), (min(x + dash, rect.w - 10), rect.h - 3), width)
    for y in range(10, rect.h - 10, dash + gap):
        pygame.draw.line(surf, border, (2, y), (2, min(y + dash, rect.h - 10)), width)
        pygame.draw.line(surf, border, (rect.w - 3, y), (rect.w - 3, min(y + dash, rect.h - 10)), width)
    screen.blit(surf, rect.topleft)

def draw_route_score_badge(rect, score, sold=False, side="left", owner=""):
    screen = state.screen
    WIDTH = state.WIDTH
    HEIGHT = state.HEIGHT
    bw = max(68, int(84 * WIDTH / _BASE_W))
    bh = max(34, int(40 * HEIGHT / 720))
    gap = max(8, int(HEIGHT * 0.010))

    if owner == "player":
        x = rect.centerx - bw // 2
        y = rect.bottom - bh - gap
    elif owner == "bot":
        x = rect.centerx - bw // 2
        y = rect.y + gap
    else:
        x = rect.x - bw - max(10, int(WIDTH * 0.007)) if side == "left" else rect.right + max(10, int(WIDTH * 0.007))
        y = rect.centery - bh // 2

    badge = pygame.Rect(x, y, bw, bh)
    draw_shadow_rect(badge, radius=10, alpha=95, offset=(2, 2))
    surf = pygame.Surface((badge.w, badge.h), pygame.SRCALPHA)
    fill = (66, 54, 28, 220) if sold else (26, 20, 14, 210)
    bord = (228, 194, 102, 245) if sold else (198, 158, 92, 235)
    pygame.draw.rect(surf, fill, pygame.Rect(0, 0, badge.w, badge.h), border_radius=10)
    pygame.draw.rect(surf, bord, pygame.Rect(0, 0, badge.w, badge.h), 2, border_radius=10)
    screen.blit(surf, badge.topleft)
    txt = f"{score}★" if sold else str(score)
    fg = (252, 242, 214) if sold else (242, 230, 201)
    draw_text_center_outlined(txt, badge, fg, (20, 12, 8), state.FONT, offset=1)

def draw_minimal_chip(text, rect, color=(226, 212, 177), fill=(28, 22, 16, 188), border=(176, 138, 78, 170), font=None):
    screen = state.screen
    if font is None: font = state.TINY
    surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.rect(surf, fill, pygame.Rect(0, 0, rect.w, rect.h), border_radius=8)
    pygame.draw.rect(surf, border, pygame.Rect(0, 0, rect.w, rect.h), 1, border_radius=8)
    screen.blit(surf, rect.topleft)
    draw_text_center_outlined(text, rect, color, (10, 8, 6), font, offset=1)

def draw_tooltip(lines, pos):
    screen = state.screen
    WIDTH = state.WIDTH
    HEIGHT = state.HEIGHT
    SMALL = state.SMALL
    if not lines: return
    pad, lh = 10, max(18, int(22 * WIDTH / _BASE_W))
    max_w = min(WIDTH - 40, int(WIDTH * 0.45))
    wrapped_lines = []
    for l in lines:
        wrapped_lines.extend(wrap_text(l, SMALL, max_w))
    lines = wrapped_lines
    w = max(SMALL.size(l)[0] for l in lines) + 2 * pad + 4
    h = len(lines) * lh + 2 * pad
    x = min(pos[0] + 18, WIDTH - w - 4)
    y = max(4, min(pos[1] - h // 2, HEIGHT - h - 4))
    r = pygame.Rect(x, y, w, h)
    draw_shadow_rect(r, 8, 100, (3, 4))
    bg = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(bg, (15, 26, 17, 230), pygame.Rect(0, 0, w, h), border_radius=8)
    screen.blit(bg, r.topleft)
    pygame.draw.rect(screen, PANEL_BORD, r, 1, border_radius=8)
    for i, l in enumerate(lines):
        draw_text(l, r.x + pad, r.y + pad + i * lh, ACCENT if i == 0 else TEXT, SMALL)

def draw_achievement_popup(aid: str, until_ms: int, now: int):
    screen = state.screen
    WIDTH = state.WIDTH
    HEIGHT = state.HEIGHT
    SMALL = state.SMALL
    TINY = state.TINY
    FONT = state.FONT
    frac = min(1.0, (until_ms - now) / 3500)
    alpha = int(min(255, frac * 6 * 255))
    if alpha <= 0: return
    pw, ph = max(340, int(420 * WIDTH / _BASE_W)), max(60, int(72 * HEIGHT / 720))
    px = (WIDTH - pw) // 2
    py = max(8, int(20 * HEIGHT / 720))
    surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
    pygame.draw.rect(surf, (*ACH_BG, min(220, alpha)), pygame.Rect(0, 0, pw, ph), border_radius=12)
    pygame.draw.rect(surf, (*ACH_BORD, alpha), pygame.Rect(0, 0, pw, ph), 2, border_radius=12)
    screen.blit(surf, (px, py))
    star_r = pygame.Rect(px + 10, py + (ph - 36) // 2, 36, 36)
    draw_text_center("★", star_r, ACCENT, FONT)
    tit = T(aid) if T(aid) != aid else aid
    desc = T(aid + "_d") if T(aid + "_d") != aid + "_d" else ""
    draw_text(tit, px + 52, py + 6, ACCENT, SMALL)
    if desc:
        max_desc_w = pw - 60
        wrapped_desc = wrap_text(desc, TINY, max_desc_w)
        cy = py + 6 + SMALL.get_height() + 2
        for line in wrapped_desc:
            draw_text(line, px + 52, cy, TEXT_DIM, TINY)
            cy += TINY.get_height() + 2


# Speech bubble details
set_bot_tell_msg = ""
set_bot_tell_until = 0
set_bot_tell_color = (210, 185, 72)

def set_bot_tell(msg: str, color=(210, 185, 72), duration_ms=2200):
    state.bot_tell_msg = msg
    state.bot_tell_until = pygame.time.get_ticks() + duration_ms
    state.bot_tell_color = color

_TELLS = {
    "benny": {
        "jack":  ["Tough break, pal.", "Oops—gone!", "That's just business.", "Say goodbye to that card."],
        "joker": ["BOOM, baby!", "Nuclear option!", "The whole table's mine!", "Heh. Heh. Heh."],
        "king":  ["Stack 'em up!", "Double or nothing!", "Now we're cooking."],
        "26":    ["Twenty-six! Beautiful.", "Perfect game, baby.", "Read 'em and weep."],
        "win":   ["The dealer always wins, and I AM the dealer.", "Better luck next time, sweetheart."],
    },
    "yes_man": {
        "jack":  ["Oh! Sorry about that!", "Had to do it, no hard feelings!", "Oops, was that yours?"],
        "joker": ["Wow, that really worked out great!", "For me, I mean!", "Oh my goodness!"],
        "king":  ["Doubling up, yes! Great idea!", "More is definitely better!"],
        "26":    ["Twenty-six! Did I do that right?", "Oh wow, it worked!"],
        "win":   ["Oh wow, I won! That's… actually great!", "No offense intended!"],
    },
    "house": {
        "jack":  ["Calculated.", "Inefficiency removed.", "Expected outcome."],
        "joker": ["Probability: 94.7% favoring me.", "As predicted.", "Optimal."],
        "king":  ["Optimal play.", "Doubling as intended."],
        "26":    ["Precise. As intended.", "Twenty-six. Naturally."],
        "win":   ["The Baron always wins.", "Exactly as simulated.", "Inevitable."],
    },
}

def get_bot_tell(pk: str, event: str) -> str:
    opts = _TELLS.get(pk, {}).get(event, [])
    return random.choice(opts) if opts else ""

def trigger_shake(duration_ms=300, force=8):
    state._shake_end = pygame.time.get_ticks() + duration_ms
    state._shake_mag = force

def get_shake_offset(now) -> Tuple[int, int]:
    if now >= state._shake_end: return 0, 0
    t = (state._shake_end - now) / 300
    f = int(state._shake_mag * t)
    if f < 1: return 0, 0
    return random.randint(-f, f), random.randint(-f, f)

def add_deal_anim(card, start, end, delay=0):
    state._deal_anims.append({
        "card": card, "start": start, "end": end,
        "start_ticks": pygame.time.get_ticks() + delay,
        "duration": 250, "pos": start, "done": False
    })

def tick_deal_anims(now):
    for a in state._deal_anims:
        if now < a["start_ticks"]: continue
        elapsed = now - a["start_ticks"]
        if elapsed >= a["duration"]:
            a["pos"] = a["end"]
            a["done"] = True
        else:
            t = elapsed / a["duration"]
            ease = t * (2.0 - t)
            dx = a["end"][0] - a["start"][0]
            dy = a["end"][1] - a["start"][1]
            a["pos"] = (a["start"][0] + dx * ease, a["start"][1] + dy * ease)
    state._deal_anims[:] = [a for a in state._deal_anims if not a["done"]]

def get_card_draw_rect(card) -> Optional[pygame.Rect]:
    for a in state._deal_anims:
        if a["card"] == card and not a["done"] and pygame.time.get_ticks() >= a["start_ticks"]:
            return pygame.Rect(a["pos"][0], a["pos"][1], state.CARD_W, state.CARD_H)
    return None

_current_ach_popup: Optional[str] = None

def draw_board(player, bot, selected_idx, msg, msg_until,
               start_ms, phase, bot_diff, hand_scroll,
               pending_bot, undo_count, consecutive_discards,
               cached_hitboxes, game_mode=GM_NORMAL,
               turn_start_ms=0, personality_key=DEFAULT_PERSONALITY,
               p2_label="Player 2", drag_card_idx=-1, drag_pos=(0,0)) -> UILayout:
    global _current_ach_popup
    global _prev_player_hand_keys, _prev_caravan_sizes

    # Bind globals from state locally
    screen = state.screen
    WIDTH = state.WIDTH
    HEIGHT = state.HEIGHT
    FONT = state.FONT
    SMALL = state.SMALL
    TINY = state.TINY
    TITLE = state.TITLE
    CARD_W = state.CARD_W
    CARD_H = state.CARD_H
    SELECT_RAISE = state.SELECT_RAISE
    PIC_BADGE_W = state.PIC_BADGE_W
    PIC_BADGE_H = state.PIC_BADGE_H
    GRID_CARD_W = state.GRID_CARD_W
    GRID_CARD_H = state.GRID_CARD_H
    STACK_OVERLAP_X = state.STACK_OVERLAP_X
    STACK_OVERLAP_X_TIGHT = state.STACK_OVERLAP_X_TIGHT
    STACK_PAD_X = state.STACK_PAD_X

    now = pygame.time.get_ticks()
    ox, oy = get_shake_offset(now)
    top, bot_area, ply_area, hand_area = ui_rects()

    # ── Auto-triggering deal animations ──────────────────────
    global active_card_animations, animating_card_keys
    
    current_hand_keys = [c.key() for c in player.hand]
    new_hand_cards = [c for c in player.hand if c.key() not in _prev_player_hand_keys]
    
    if new_hand_cards:
        deck_x = hand_area.x + 24
        deck_y = hand_area.y + max(8, (hand_area.h - CARD_H) // 2)
        ha_temp = pygame.Rect(hand_area.x, hand_area.y, hand_area.w, hand_area.h)
        rects_temp, _, _, _ = hand_layout(ha_temp, len(player.hand), selected_idx, hand_scroll)
        
        for i, c in enumerate(player.hand):
            if c in new_hand_cards and i < len(rects_temp):
                dest_rect = rects_temp[i]
                delay = len(active_card_animations) * 80
                anim = CardAnimation(c, (deck_x, deck_y), (dest_rect.x + ox, dest_rect.y + oy), duration_ms=350, delay_ms=delay)
                active_card_animations.append(anim)
                animating_card_keys.add(c.key())
                
    _prev_player_hand_keys = current_hand_keys
    
    current_sizes = []
    for c in player.caravans: current_sizes.append(len(c.nums))
    for c in bot.caravans: current_sizes.append(len(c.nums))
    
    bot_slots_temp = [pygame.Rect(r.x + ox, r.y + oy, r.w, r.h) for r in caravan_slots(bot_area)]
    ply_slots_temp = [pygame.Rect(r.x + ox, r.y + oy, r.w, r.h) for r in caravan_slots(ply_area)]
    
    for ci in range(3):
        prev_sz = _prev_caravan_sizes[ci]
        curr_sz = current_sizes[ci]
        if curr_sz > prev_sz:
            new_ne = player.caravans[ci].nums[-1]
            start_x = hand_area.x + 24
            start_y = hand_area.y + max(8, (hand_area.h - CARD_H) // 2)
            overlap_temp = STACK_OVERLAP_X_TIGHT if curr_sz > 9 else STACK_OVERLAP_X
            start_idx = max(0, curr_sz - 9)
            dest_idx = curr_sz - 1 - start_idx
            dest_x = ply_slots_temp[ci].x + STACK_PAD_X + dest_idx * overlap_temp
            dest_y = ply_slots_temp[ci].y + (ply_slots_temp[ci].height - CARD_H) // 2
            
            anim = CardAnimation(new_ne.card, (start_x, start_y), (dest_x, dest_y), duration_ms=250)
            active_card_animations.append(anim)
            animating_card_keys.add(new_ne.card.key())
            
        prev_sz_b = _prev_caravan_sizes[ci + 3]
        curr_sz_b = current_sizes[ci + 3]
        if curr_sz_b > prev_sz_b:
            new_ne = bot.caravans[ci].nums[-1]
            b_deck_x = (WIDTH * 0.35)
            b_deck_y = (state.TOP_BAR_H // 2)
            overlap_temp = STACK_OVERLAP_X_TIGHT if curr_sz_b > 9 else STACK_OVERLAP_X
            start_idx = max(0, curr_sz_b - 9)
            dest_idx = curr_sz_b - 1 - start_idx
            dest_x = bot_slots_temp[ci].x + STACK_PAD_X + dest_idx * overlap_temp
            dest_y = bot_slots_temp[ci].y + (bot_slots_temp[ci].height - CARD_H) // 2
            
            anim = CardAnimation(new_ne.card, (b_deck_x, b_deck_y), (dest_x, dest_y), duration_ms=250)
            active_card_animations.append(anim)
            animating_card_keys.add(new_ne.card.key())
            
    _prev_caravan_sizes = current_sizes

    draw_table_background()

    def sr(r): return pygame.Rect(r.x + ox, r.y + oy, r.w, r.h)

    pos = pygame.mouse.get_pos()
    elapsed = now - start_ms

    chip_y = max(8, int(HEIGHT * 0.010)) + oy
    chip_h = max(28, int(34 * HEIGHT / 720))
    phase_txt = f"{phase}  ·  {bot_diff.upper()}"
    draw_minimal_chip(phase_txt, pygame.Rect(max(10, int(WIDTH * 0.012)) + ox, chip_y, max(170, int(WIDTH * 0.16)), chip_h),
                      color=(218, 198, 130), font=TINY)
    draw_minimal_chip(format_time_ms(elapsed), pygame.Rect(WIDTH // 2 - max(52, int(WIDTH * 0.045)) + ox, chip_y, max(104, int(WIDTH * 0.09)), chip_h),
                      color=(214, 205, 176), font=TINY)

    if pending_bot and phase == "MAIN" and game_mode != GM_HOT_SEAT:
        dots = "." * (1 + (now // 400) % 3)
        pers = PERSONALITIES.get(personality_key, BENNY)
        draw_minimal_chip(T(pers.display_key) + dots, pygame.Rect(max(10, int(WIDTH * 0.012)) + ox, chip_y + chip_h + 6, max(180, int(WIDTH * 0.19)), chip_h),
                          color=(222, 188, 95), fill=(54, 36, 20, 132), border=(182, 130, 70, 135), font=TINY)
    elif undo_count > 0:
        draw_minimal_chip(T("undo_hint", undo_count), pygame.Rect(max(10, int(WIDTH * 0.012)) + ox, chip_y + chip_h + 6, max(180, int(WIDTH * 0.19)), chip_h),
                          color=UNDO_CLR, font=TINY)

    if consecutive_discards >= 15:
        clr = RED if consecutive_discards >= 18 else YELLOW
        draw_minimal_chip(T("stalemate_warn", consecutive_discards, 20),
                          pygame.Rect(WIDTH // 2 - max(180, int(WIDTH * 0.16)) + ox, chip_y + chip_h + 6, max(360, int(WIDTH * 0.32)), chip_h),
                          color=clr, fill=(60, 28, 18, 150), border=(170, 80, 60, 150), font=TINY)

    if game_mode == GM_TIMED and phase == "MAIN" and not pending_bot:
        elapsed_turn = now - turn_start_ms
        frac = max(0.0, 1.0 - (elapsed_turn / 30000))
        bar_w = max(110, int(170 * WIDTH / _BASE_W))
        bar_h = 6
        bx = WIDTH // 2 - bar_w // 2 + ox
        by = chip_y + chip_h + 5
        pygame.draw.rect(screen, (55, 42, 28, 120), (bx, by, bar_w, bar_h), border_radius=4)
        fill_w = int(bar_w * frac)
        col = (TIMER_OK if frac > 0.5 else TIMER_WARN if frac > 0.25 else TIMER_CRIT)
        pygame.draw.rect(screen, col, (bx, by, fill_w, bar_h), border_radius=4)
        if frac <= 0.25 and elapsed_turn % 1000 < 100:
            if state.sounds: state.sounds.play("timer_warn")

    pb_w = max(76, int(92 * WIDTH / _BASE_W))
    pb_h = chip_h
    pb_lbl = "⏸ PAUSE" if state.language == "en" else "⏸ ПАУЗА"
    pause_btn = pygame.Rect(WIDTH - pb_w - max(10, int(WIDTH * 0.012)) + ox, chip_y, pb_w, pb_h)
    draw_button(pb_lbl, pause_btn, pos, (74, 61, 40), (102, 82, 51), TINY)

    bot_slots = [pygame.Rect(r.x + ox, r.y + oy, r.w, r.h) for r in caravan_slots(bot_area)]
    ply_slots = [pygame.Rect(r.x + ox, r.y + oy, r.w, r.h) for r in caravan_slots(ply_area)]

    sel_card = player.hand[selected_idx] if 0 <= selected_idx < len(player.hand) else None

    for i, r in enumerate(ply_slots):
        active = bool(sel_card and sel_card.is_number() and can_play_number_on_caravan(sel_card, player.caravans[i]))
        invalid = bool(sel_card and sel_card.is_number() and not can_play_number_on_caravan(sel_card, player.caravans[i]))
        draw_soft_route_slot(r, active=active, invalid=invalid, sold=player.caravans[i].for_sale())

    for i, r in enumerate(bot_slots):
        draw_soft_route_slot(r, sold=bot.caravans[i].for_sale())

    for i in range(3):
        draw_caravan_stack(bot_slots[i], bot.caravans[i])
        draw_caravan_stack(ply_slots[i], player.caravans[i])
        bs, bsold = bot.caravans[i].score(), bot.caravans[i].for_sale()
        ps, pssold = player.caravans[i].score(), player.caravans[i].for_sale()
        draw_route_score_badge(bot_slots[i], bs, bsold, side="left", owner="bot")
        draw_route_score_badge(ply_slots[i], ps, pssold, side="right", owner="player")

    raw_bot_slots = caravan_slots(bot_area)
    raw_ply_slots = caravan_slots(ply_area)
    if cached_hitboxes:
        bot_boxes = [(pygame.Rect(r.x + ox, r.y + oy, r.w, r.h), own, ci, ei) for r, own, ci, ei in cached_hitboxes["bot"]]
        ply_boxes = [(pygame.Rect(r.x + ox, r.y + oy, r.w, r.h), own, ci, ei) for r, own, ci, ei in cached_hitboxes["player"]]
    else:
        bot_boxes = [(pygame.Rect(r.x + ox, r.y + oy, r.w, r.h), own, ci, ei) for r, own, ci, ei in build_entry_hitboxes("bot", raw_bot_slots, bot.caravans)]
        ply_boxes = [(pygame.Rect(r.x + ox, r.y + oy, r.w, r.h), own, ci, ei) for r, own, ci, ei in build_entry_hitboxes("player", raw_ply_slots, player.caravans)]

    tooltip_lines = []
    if sel_card and sel_card.is_picture():
        for r, own, ci, ei in reversed(ply_boxes + bot_boxes):
            tgt = player if own == "player" else bot
            ne = tgt.caravans[ci].nums[ei]
            ok = can_play_picture_on_target(sel_card, ne, ei == len(tgt.caravans[ci].nums) - 1)
            pygame.draw.rect(screen, OUT_OK if ok else OUT_BAD, r, 2, border_radius=10)
            if r.collidepoint(pos):
                pygame.draw.rect(screen, OUT_OK if ok else OUT_BAD, r, 4, border_radius=10)
                tooltip_lines = ne.tooltip_lines()
    else:
        for r, own, ci, ei in reversed(ply_boxes + bot_boxes):
            if r.collidepoint(pos):
                tgt = player if own == "player" else bot
                tooltip_lines = tgt.caravans[ci].nums[ei].tooltip_lines()
                break

    ha = pygame.Rect(hand_area.x + ox, hand_area.y + oy, hand_area.w, hand_area.h)
    rects, hand_scroll, max_scroll, scroll_on = hand_layout(ha, len(player.hand), selected_idx, hand_scroll)
    hover_idx = get_idx_at(pos, rects)
    for i, c in enumerate(player.hand):
        if rects[i].right < ha.x + 10 or rects[i].x > ha.right - 10: continue
        if c.key() in animating_card_keys: continue
        if i == drag_card_idx: continue
        draw_hand_card(rects[i], c, selected=(i == selected_idx), hovered=(i == hover_idx and drag_card_idx == -1))

    if scroll_on and max_scroll > 0:
        bar_w2 = min(320, ha.width - 80)
        bar = pygame.Rect(ha.x + (ha.width - bar_w2) // 2, ha.y + 40, bar_w2, 8)
        pygame.draw.rect(screen, (80, 80, 80), bar, border_radius=6)
        vw = bar_w2 + max_scroll
        kw = max(20, int(bar_w2 * bar_w2 / vw))
        t = hand_scroll / max_scroll if max_scroll > 0 else 0
        kx = int(bar.x + t * (bar_w2 - kw))
        pygame.draw.rect(screen, BTN_H, pygame.Rect(kx, bar.y, kw, bar.height), border_radius=6)
        pygame.draw.rect(screen, BLACK, bar, 2, border_radius=6)

    if msg and now < msg_until:
        mr = pygame.Rect(ha.x + 20, ha.bottom - 52, ha.width - 40, 40)
        ms = pygame.Surface((mr.w, mr.h), pygame.SRCALPHA)
        ms.fill((35, 10, 10, 200))
        screen.blit(ms, mr.topleft)
        pygame.draw.rect(screen, RED, mr, 1, border_radius=10)
        draw_text_center(msg, mr, TEXT, SMALL)

    if tooltip_lines: draw_tooltip(tooltip_lines, pos)

    # ── Particle system ──────────────────────────────────────
    for b in list(state.deferred_bursts):
        btype, ci2, aname = b[0], b[1], b[2]
        if btype == "cav26":
            slot_list = ply_slots if aname != "Bot" and aname != "Bot A" else bot_slots
            if 0 <= ci2 < 3:
                sr2 = slot_list[ci2]
                cx2 = sr2.x + sr2.w // 2
                cy2 = sr2.y + sr2.h // 2
                if state.particles:
                    state.particles.burst(cx2, cy2, (195, 162, 52), 30, 5)
                    state.particles.burst(cx2, cy2, (100, 220, 120), 15, 3)
    state.deferred_bursts.clear()
    if state.particles: state.particles.tick_draw(screen)

    # ── Hover card preview (enlarged above hand) ─────────────
    if hover_idx != -1 and 0 <= hover_idx < len(player.hand) and hover_idx != selected_idx:
        hc = player.hand[hover_idx]
        hr = rects[hover_idx] if hover_idx < len(rects) else None
        if hr:
            pw2 = int(CARD_W * 1.65)
            ph2 = int(CARD_H * 1.65)
            px2 = hr.centerx - pw2 // 2
            py2 = hr.y - ph2 - 18
            px2 = max(4, min(px2, WIDTH - pw2 - 4))
            py2 = max(4, py2)
            preview_r = pygame.Rect(px2, py2, pw2, ph2)
            draw_shadow_rect(preview_r, 14, 120, (6, 8))
            _draw_card_face(preview_r, hc)
            if hc.is_number():
                vr = pygame.Rect(px2, py2 + ph2 + 4, pw2, 24)
                vs = pygame.Surface((pw2, 24), pygame.SRCALPHA)
                vs.fill((12, 20, 14, 200))
                screen.blit(vs, vr.topleft)
                pygame.draw.rect(screen, PANEL_BORD, vr, 1, border_radius=5)
                draw_text_center(f"Value: {hc.value()}", vr, ACCENT, TINY)

    # ── Bot tell bubble ──────────────────────────────────────
    if state.bot_tell_msg and now < state.bot_tell_until:
        frac = min(1.0, (state.bot_tell_until - now) / 400)
        alpha = int(min(255, frac * 8 * 255))
        tell_surf = SMALL.render(state.bot_tell_msg, True, state.bot_tell_color)
        tw, th = tell_surf.get_width() + 24, tell_surf.get_height() + 14
        tx = bot_area.x + ox + bot_area.width // 2 - tw // 2
        ty = bot_area.y + oy - th - 8
        ty = max(4, ty)
        bg2 = pygame.Surface((tw, th), pygame.SRCALPHA)
        bg2.fill((12, 20, 14, min(220, alpha)))
        pygame.draw.rect(bg2, (*state.bot_tell_color[:3], alpha), pygame.Rect(0, 0, tw, th), 2, border_radius=10)
        screen.blit(bg2, (tx, ty))
        ts2 = SMALL.render(state.bot_tell_msg, True, (*state.bot_tell_color[:3],))
        ts2.set_alpha(alpha)
        screen.blit(ts2, (tx + 12, ty + 7))
        tail = [(tx + tw // 2 - 6, ty + th), (tx + tw // 2 + 6, ty + th), (tx + tw // 2, ty + th + 10)]
        pygame.draw.polygon(screen, (*state.bot_tell_color[:3], alpha // 2), tail)

    # Achievement popup
    _current_ach_popup = tick_achievement_popup(now)
    if _current_ach_popup:
        draw_achievement_popup(_current_ach_popup, state.ach_popup_until, now)

    # Update and draw active card animations
    for anim in list(active_card_animations):
        pos_anim = anim.get_current_pos(now)
        if anim.completed:
            active_card_animations.remove(anim)
            animating_card_keys.discard(anim.card.key())
        else:
            if now >= anim.start_ticks:
                card_rect = pygame.Rect(pos_anim[0], pos_anim[1], CARD_W, CARD_H)
                _draw_card_face(card_rect, anim.card)

    # ── Draw dragged card ──────────────────────────────────────
    if drag_card_idx != -1 and 0 <= drag_card_idx < len(player.hand):
        dc = player.hand[drag_card_idx]
        dr = pygame.Rect(drag_pos[0], drag_pos[1], CARD_W, CARD_H)
        _draw_card_face(dr, dc, selected=True)

    pygame.display.flip()

    return UILayout(
        bot_slots=raw_bot_slots,
        ply_slots=raw_ply_slots,
        hand_rects=rects,
        bot_boxes=[(r, o, c, e) for r, o, c, e in build_entry_hitboxes("bot", raw_bot_slots, bot.caravans)],
        ply_boxes=[(r, o, c, e) for r, o, c, e in build_entry_hitboxes("player", raw_ply_slots, player.caravans)],
        hand_scroll=hand_scroll,
        hand_max_scroll=max_scroll,
        hand_scroll_on=scroll_on,
        pause_btn=pause_btn,
    )
