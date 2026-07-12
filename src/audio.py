import pygame
from typing import Dict, Any
import src.state as state

class SoundManager:
    def __init__(self):
        self._sounds: Dict[str, Any] = {}
        self._ok = state.AUDIO_OK
        if self._ok:
            try: pygame.mixer.set_num_channels(8)
            except: pass
        self._gen_all()

    def _gen_tone(self, freqs, dur_ms, vol=0.35, shape="sine"):
        if not self._ok: return None
        try:
            import math
            import struct
            sr = 44100
            n = int(sr * dur_ms / 1000)
            samples = bytearray(n * 4)
            for i in range(n):
                t = i / sr
                v = 0.0
                for freq in freqs:
                    if shape == "sine":
                        v += math.sin(2 * math.pi * freq * t)
                    elif shape == "saw":
                        v += 2.0 * (t * freq - math.floor(t * freq + 0.5))
                    elif shape == "sq":
                        val = math.sin(2 * math.pi * freq * t)
                        v += 1.0 if val >= 0 else -1.0
                v /= len(freqs)
                fade = (1.0 - (i / n)) ** 0.6
                sample_val = int(v * fade * vol * 32767)
                sample_val = max(-32768, min(32767, sample_val))
                struct.pack_into("<hh", samples, i * 4, sample_val, sample_val)
            return pygame.mixer.Sound(buffer=samples)
        except:
            return None

    def _gen_all(self):
        self._sounds["play_card"] = self._gen_tone([600, 800], 80, 0.25)
        self._sounds["discard"]   = self._gen_tone([220, 180], 120, 0.20, "saw")
        self._sounds["jack"]      = self._gen_tone([400, 300, 200], 180, 0.30, "sq")
        self._sounds["joker"]     = self._gen_tone([150, 100, 80], 350, 0.40, "sq")
        self._sounds["king"]      = self._gen_tone([700, 900], 100, 0.25)
        self._sounds["win"]       = self._gen_tone([523, 659, 784, 1047], 500, 0.40)
        self._sounds["lose"]      = self._gen_tone([400, 320, 260, 220], 600, 0.35)
        self._sounds["deal"]      = self._gen_tone([900], 40, 0.15)
        self._sounds["tick"]      = self._gen_tone([880], 30, 0.10)
        self._sounds["timer_warn"] = self._gen_tone([440], 60, 0.20)

    def play(self, name: str):
        if not self._ok or not state.app_settings or state.app_settings.muted:
            return
        snd = self._sounds.get(name)
        if snd:
            try:
                snd.set_volume(state.app_settings.sfx_volume)
                snd.play()
            except:
                pass
