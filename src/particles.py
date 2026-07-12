import random
import math
import pygame
from src.config import WIDTH

class ParticleSystem:
    def __init__(self):
        self._p: list = []

    def burst(self, x, y, color=(195, 162, 52), count=22, speed=4.0):
        for _ in range(count):
            ang = random.uniform(0, 2 * math.pi)
            spd = random.uniform(0.8, speed)
            self._p.append({
                'x': x, 'y': y,
                'vx': math.cos(ang) * spd,
                'vy': math.sin(ang) * spd - random.uniform(0, 2),
                'life': 1.0, 'decay': random.uniform(0.018, 0.045),
                'color': color, 'size': random.randint(3, 8),
            })

    def confetti(self, count=70):
        cols = [(195, 162, 52), (100, 200, 110), (210, 185, 72), (180, 100, 220), (100, 200, 255), (230, 80, 80)]
        for _ in range(count):
            self._p.append({
                'x': random.randint(0, WIDTH), 'y': random.randint(-30, 0),
                'vx': random.uniform(-2, 2), 'vy': random.uniform(1.5, 5),
                'life': 1.0, 'decay': random.uniform(0.006, 0.018),
                'color': random.choice(cols), 'size': random.randint(4, 11),
            })

    def tick_draw(self, surface):
        keep = []
        for p in self._p:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['vy'] += 0.13
            p['life'] -= p['decay']
            if p['life'] <= 0:
                continue
            sz = max(1, int(p['size'] * p['life']))
            alpha = int(p['life'] * 230)
            s = pygame.Surface((sz * 2, sz * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*p['color'][:3], alpha), (sz, sz), sz)
            surface.blit(s, (int(p['x']) - sz, int(p['y']) - sz))
            keep.append(p)
        self._p[:] = keep

    def clear(self):
        self._p.clear()

    def active(self):
        return len(self._p) > 0
