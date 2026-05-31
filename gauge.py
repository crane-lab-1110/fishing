import pygame
import math


def _draw_mini_star(surface, cx, cy, size, color):
    points = []
    for i in range(10):
        angle = math.radians(i * 36 - 90)
        r = size if i % 2 == 0 else size * 0.42
        points.append((int(cx + math.cos(angle) * r), int(cy + math.sin(angle) * r)))
    pygame.draw.polygon(surface, color, points)


class Gauge:
    MAX_VALUE = 100

    def __init__(self):
        self.value = 0

    @property
    def is_full(self):
        return self.value >= self.MAX_VALUE

    def add(self, amount):
        self.value = min(self.MAX_VALUE, self.value + amount)

    def reset(self):
        self.value = 0

    def draw(self, surface, rect, font_small):
        x, y, w, h = rect
        r = h // 2

        # Track background
        pygame.draw.rect(surface, (180, 210, 255), (x, y, w, h), border_radius=r)
        pygame.draw.rect(surface, (80, 130, 200), (x, y, w, h), 3, border_radius=r)

        # Fill bar
        fill_w = max(0, int(w * self.value / self.MAX_VALUE))
        if fill_w > 2:
            fill_col = (255, 80, 50) if self.is_full else (255, 200, 30)
            pygame.draw.rect(surface, fill_col, (x, y, fill_w, h), border_radius=r)

        # Star markers
        n_stars = 10
        for i in range(n_stars):
            sx = x + int(w * (i + 0.5) / n_stars)
            sy = y + h // 2
            threshold = (i + 0.5) / n_stars * self.MAX_VALUE
            filled = self.value >= threshold
            col = (255, 230, 0) if filled else (160, 180, 220)
            _draw_mini_star(surface, sx, sy, 7, col)

        # Label
        label = font_small.render(f"はなまる  {int(self.value)}/{self.MAX_VALUE}", True, (240, 240, 255))
        surface.blit(label, (x + w + 12, y + h // 2 - label.get_height() // 2))
