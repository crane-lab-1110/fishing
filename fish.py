import pygame
import math
import os
import random

SCREEN_W = 1280
SCREEN_H = 720
FISH_ZONE_TOP = 130
FISH_ZONE_BOTTOM = 700

FISH_DEFS = [
    {
        'name': 'クマノミ',
        'key': 'kumanomi',
        'size': (80, 52),
        'speed': 125.0,
        'gauge': 1,
        'weight': 35,
        'color': (255, 110, 20),
        'accent': (255, 255, 255),
        'boss': False,
        'kind': 'clown',
    },
    {
        'name': 'カクレクマノミ',
        'key': 'kakure_kumanomi',
        'size': (68, 44),
        'speed': 145.0,
        'gauge': 1,
        'weight': 30,
        'color': (255, 155, 0),
        'accent': (255, 255, 255),
        'boss': False,
        'kind': 'clown',
    },
    {
        'name': 'ヒラメ',
        'key': 'hirame',
        'size': (110, 70),
        'speed': 80.0,
        'gauge': 2,
        'weight': 20,
        'color': (160, 200, 105),
        'accent': (110, 150, 70),
        'boss': False,
        'kind': 'flat',
    },
    {
        'name': 'マンタ',
        'key': 'manta',
        'size': (170, 95),
        'speed': 55.0,
        'gauge': 3,
        'weight': 15,
        'color': (55, 70, 170),
        'accent': (200, 220, 255),
        'boss': False,
        'kind': 'manta',
    },
    {
        'name': 'サメ',
        'key': 'same',
        'size': (230, 125),
        'speed': 65.0,
        'gauge': 5,
        'weight': 0,
        'color': (95, 110, 130),
        'accent': (200, 215, 230),
        'boss': True,
        'kind': 'shark',
    },
]


def _create_fallback_fish(fish_def):
    w, h = fish_def['size']
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    c = fish_def['color']
    ac = fish_def['accent']
    kind = fish_def.get('kind', 'normal')

    if kind == 'clown':
        # Rounded body
        pygame.draw.ellipse(surf, c, (0, h // 4, int(w * 0.78), int(h * 0.55)))
        # Tail fin
        tail = [
            (int(w * 0.72), h // 2),
            (w - 2, h // 5),
            (w - 2, h * 4 // 5),
        ]
        pygame.draw.polygon(surf, c, tail)
        # Dorsal fin
        dorsal = [
            (int(w * 0.25), h // 4),
            (int(w * 0.5), 2),
            (int(w * 0.6), h // 4),
        ]
        pygame.draw.polygon(surf, c, dorsal)
        # White stripes
        for sx in [int(w * 0.28), int(w * 0.50)]:
            pygame.draw.line(surf, ac, (sx, h // 4 + 2), (sx, h * 3 // 4 - 2), 6)
        # Outline
        pygame.draw.ellipse(surf, (180, 60, 0), (0, h // 4, int(w * 0.78), int(h * 0.55)), 2)
        # Eye
        ex, ey = int(w * 0.13), h // 2 - 2
        pygame.draw.circle(surf, (255, 255, 255), (ex, ey), 7)
        pygame.draw.circle(surf, (20, 20, 20), (ex + 2, ey), 4)
        pygame.draw.circle(surf, (255, 255, 255), (ex + 3, ey - 2), 2)

    elif kind == 'flat':
        # Flat oval shape
        pygame.draw.ellipse(surf, c, (0, h // 5, int(w * 0.82), int(h * 0.62)))
        # Tail
        tail = [
            (int(w * 0.75), h // 2),
            (w - 2, h // 6),
            (w - 2, h * 5 // 6),
        ]
        pygame.draw.polygon(surf, c, tail)
        # Spots
        for sx, sy, sr in [(int(w * 0.3), int(h * 0.42), 7), (int(w * 0.5), int(h * 0.38), 5),
                           (int(w * 0.22), int(h * 0.55), 5)]:
            pygame.draw.circle(surf, ac, (sx, sy), sr)
        pygame.draw.ellipse(surf, (100, 150, 60), (0, h // 5, int(w * 0.82), int(h * 0.62)), 2)
        ex, ey = int(w * 0.1), h // 2 - 3
        pygame.draw.circle(surf, (255, 255, 255), (ex, ey), 6)
        pygame.draw.circle(surf, (20, 20, 20), (ex + 2, ey), 3)

    elif kind == 'manta':
        # Wide kite/diamond shape
        mid_y = h // 2
        body = [
            (int(w * 0.45), mid_y),        # nose
            (int(w * 0.15), mid_y - h // 3),  # left wing tip top
            (0, mid_y - 4),                 # left far tip
            (int(w * 0.15), mid_y + h // 3),  # left wing tip bot
            (int(w * 0.45), mid_y),        # back to nose
            (w - 2, mid_y - h // 5),        # right wing
            (w - 2, mid_y + h // 5),
        ]
        pygame.draw.polygon(surf, c, body)
        # Tail spike
        pygame.draw.line(surf, c, (w // 2, mid_y), (w - 10, mid_y + h // 3), 5)
        # Belly marking
        belly = [
            (int(w * 0.42), mid_y),
            (int(w * 0.2), mid_y - h // 5),
            (int(w * 0.2), mid_y + h // 5),
        ]
        pygame.draw.polygon(surf, ac, belly)
        ex, ey = int(w * 0.37), mid_y - 6
        pygame.draw.circle(surf, (30, 30, 30), (ex, ey), 4)
        pygame.draw.circle(surf, (255, 255, 255), (ex + 2, ey - 2), 2)

    elif kind == 'shark':
        mid_y = h // 2
        # Body
        body = [
            (0, mid_y),
            (int(w * 0.2), mid_y - h // 4),
            (int(w * 0.7), mid_y - h // 4),
            (w - 2, mid_y - 4),
            (w - 2, mid_y + 4),
            (int(w * 0.7), mid_y + h // 5),
            (int(w * 0.2), mid_y + h // 5),
        ]
        pygame.draw.polygon(surf, c, body)
        # Dorsal fin
        dorsal = [
            (int(w * 0.35), mid_y - h // 4),
            (int(w * 0.45), 2),
            (int(w * 0.58), mid_y - h // 4),
        ]
        pygame.draw.polygon(surf, c, dorsal)
        # Tail
        tail = [
            (w - 2, mid_y),
            (w - 2, mid_y - h // 4),
            (w - int(w * 0.15), mid_y),
            (w - 2, mid_y + h // 4),
        ]
        pygame.draw.polygon(surf, c, tail)
        # Belly
        pygame.draw.ellipse(surf, ac, (int(w * 0.15), mid_y, int(w * 0.55), h // 5))
        # Outline
        pygame.draw.polygon(surf, (60, 75, 95), body, 2)
        # Eye
        ex, ey = int(w * 0.08), mid_y - 4
        pygame.draw.circle(surf, (20, 20, 20), (ex, ey), 6)
        pygame.draw.circle(surf, (255, 255, 255), (ex + 2, ey - 2), 2)
        # Grin
        pygame.draw.arc(surf, (20, 20, 20),
                        (int(w * 0.03), mid_y - 8, 25, 18), math.pi, 2 * math.pi, 2)
        # Teeth
        for tx in range(int(w * 0.04), int(w * 0.14), 6):
            pygame.draw.polygon(surf, (255, 255, 255), [
                (tx, mid_y - 2), (tx + 3, mid_y + 6), (tx + 6, mid_y - 2)
            ])

    else:
        # Generic fish
        pygame.draw.ellipse(surf, c, (0, h // 4, int(w * 0.76), h // 2))
        tail = [(int(w * 0.72), h // 2), (w - 2, h // 4), (w - 2, h * 3 // 4)]
        pygame.draw.polygon(surf, c, tail)
        ex, ey = int(w * 0.12), h // 2
        pygame.draw.circle(surf, (255, 255, 255), (ex, ey), 6)
        pygame.draw.circle(surf, (20, 20, 20), (ex + 2, ey), 3)

    return surf


class Fish:
    STATE_SWIMMING = 'swimming'
    STATE_CAUGHT = 'caught'
    STATE_ESCAPING = 'escaping'
    STATE_DEAD = 'dead'

    _image_cache = {}

    def __init__(self, fish_def, x=None, y=None):
        self.fish_def = fish_def
        self.name = fish_def['name']
        self.w, self.h = fish_def['size']
        self.speed = fish_def['speed']
        self.gauge_value = fish_def['gauge']
        self.color = fish_def['color']
        self.boss = fish_def.get('boss', False)

        self.x = x if x is not None else random.uniform(self.w, SCREEN_W - self.w)
        self.y = y if y is not None else random.uniform(FISH_ZONE_TOP + 60, FISH_ZONE_BOTTOM - 60)

        self.vx = self.speed * random.choice([-1, 1])
        self.time_offset = random.uniform(0, 2 * math.pi)
        self.state = self.STATE_SWIMMING

        self.target_x = 0.0
        self.target_y = 0.0
        self.escape_timer = 0.0
        self.wobble_angle = 0.0
        self.facing_right = self.vx > 0

        self.image = self._load_image(fish_def)
        self.image_flipped = pygame.transform.flip(self.image, True, False)

    @classmethod
    def _load_image(cls, fish_def):
        key = fish_def['key']
        if key in cls._image_cache:
            return cls._image_cache[key]

        w, h = fish_def['size']
        path = os.path.join('assets', 'fish', key + '.png')
        if os.path.exists(path):
            try:
                img = pygame.image.load(path).convert_alpha()
                img = pygame.transform.scale(img, (w, h))
                cls._image_cache[key] = img
                return img
            except Exception:
                pass

        img = _create_fallback_fish(fish_def)
        cls._image_cache[key] = img
        return img

    def get_rect(self):
        return pygame.Rect(
            int(self.x - self.w // 2),
            int(self.y - self.h // 2),
            self.w, self.h,
        )

    def update(self, dt):
        if self.state == self.STATE_SWIMMING:
            self._swim(dt)
        elif self.state == self.STATE_CAUGHT:
            self._follow_hook(dt)
        elif self.state == self.STATE_ESCAPING:
            self._escape(dt)

    def _swim(self, dt):
        self.x += self.vx * dt
        self.time_offset += dt * 1.6
        self.y += math.sin(self.time_offset) * 28 * dt

        margin = self.w // 2
        if self.x < margin:
            self.x = margin
            self.vx = abs(self.vx)
        elif self.x > SCREEN_W - margin:
            self.x = SCREEN_W - margin
            self.vx = -abs(self.vx)

        y_margin = self.h // 2
        if self.y < FISH_ZONE_TOP + y_margin:
            self.y = FISH_ZONE_TOP + y_margin
        elif self.y > FISH_ZONE_BOTTOM - y_margin:
            self.y = FISH_ZONE_BOTTOM - y_margin

        self.facing_right = self.vx > 0

    def _follow_hook(self, dt):
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        t = min(1.0, 12 * dt)
        self.x += dx * t
        self.y += dy * t
        self.wobble_angle += 300 * dt

    def _escape(self, dt):
        self.escape_timer += dt
        self.x += self.vx * 2.8 * dt
        self.y += 55 * dt
        if self.escape_timer > 1.6 or self.y > SCREEN_H + 80:
            self.state = self.STATE_DEAD

    def start_escape(self):
        self.state = self.STATE_ESCAPING
        self.escape_timer = 0.0
        self.vx = self.speed * 2.5 * (1 if self.vx > 0 else -1)

    def draw(self, surface):
        if self.state == self.STATE_DEAD:
            return

        img = self.image_flipped if self.facing_right else self.image

        if self.state == self.STATE_CAUGHT:
            angle = math.sin(math.radians(self.wobble_angle)) * 22
            img = pygame.transform.rotate(img, angle)
        elif self.state == self.STATE_ESCAPING:
            alpha = max(0, int(255 * (1 - self.escape_timer / 1.6)))
            img = img.copy()
            img.set_alpha(alpha)

        rect = img.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(img, rect)

        if self.state == self.STATE_SWIMMING:
            self._draw_shadow(surface)

    def _draw_shadow(self, surface):
        shadow = pygame.Surface((self.w, 12), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 40), (0, 0, self.w, 12))
        surface.blit(shadow, (int(self.x - self.w // 2), int(self.y + self.h // 2 - 4)))

    @property
    def is_dead(self):
        return self.state == self.STATE_DEAD
