import pygame
from typing import Optional, Dict, List

# Shared dynamic globals
screen: Optional[pygame.Surface] = None
FONT: Optional[pygame.font.Font] = None
SMALL: Optional[pygame.font.Font] = None
TINY: Optional[pygame.font.Font] = None
TITLE: Optional[pygame.font.Font] = None

AUDIO_OK = True

# Dynamic Layout Dimensions
WIDTH = 1280
HEIGHT = 720
MARGIN = 22
GAP = 12
TOP_BAR_H = 100
CARD_W = 70
CARD_H = 98
SELECT_RAISE = 14
PIC_BADGE_W = 22
PIC_BADGE_H = 22
GRID_CARD_W = 82
GRID_CARD_H = 58
STACK_OVERLAP_X = 28
STACK_OVERLAP_X_TIGHT = 18
STACK_PAD_X = 14


# Audio and Particles
sounds = None
particles = None

# Settings & Stats
app_settings = None
app_stats = None

# Localization
language = "en"

# Caches
text_cache: Dict = {}
card_label_cache: Dict = {}
table_felt_surface: Optional[pygame.Surface] = None
menu_background_surface: Optional[pygame.Surface] = None
table_background_surface: Optional[pygame.Surface] = None

# Gameplay animations & effects
bot_tell_msg = ""
bot_tell_until = 0
bot_tell_color = (210, 185, 72)


_shake_end = 0
_shake_mag = 0

_deal_anims = []


# Achievements State
ach_unlocked = {}
ach_popup_queue = []
ach_popup_until = 0
deferred_bursts = []


