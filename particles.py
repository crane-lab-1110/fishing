import pygame
import random
import math


class Confetti:
    COLORS = [
        (255, 80, 80), (255, 200, 0), (80, 200, 80),
        (80, 150, 255), (255, 120, 200), (200, 80, 255),
        (255, 160, 0), (0, 220, 200),
    ]

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = random.uniform(-180, 180)
        self.vy = random.uniform(-320, -80)
        self.gravity = 350
        self.color = random.choice(self.COLORS)
        self.width = random.randint(8, 18)
        self.height = random.randint(5, 11)
        self.angle = random.uniform(0, 360)
        self.angular_vel = random.uniform(-200, 200)
        self.lifetime = random.uniform(2.0, 3.5)
        self.age = 0
        self.alive = True

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += self.gravity * dt
        self.angle += self.angular_vel * dt
        self.age += dt
        if self.age >= self.lifetime or self.y > 820:
            self.alive = False

    def draw(self, surface):
        alpha = max(0, int(255 * (1 - self.age / self.lifetime)))
        surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        surf.fill((*self.color, alpha))
        rotated = pygame.transform.rotate(surf, self.angle)
        rect = rotated.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(rotated, rect)


def _draw_star_shape(surface, cx, cy, size, color, alpha):
    points = []
    for i in range(10):
        angle = math.radians(i * 36 - 90)
        r = size if i % 2 == 0 else size * 0.42
        points.append((cx + math.cos(angle) * r, cy + math.sin(angle) * r))
    span = int(size * 2 + 4)
    surf = pygame.Surface((span, span), pygame.SRCALPHA)
    local = [(p[0] - cx + span // 2, p[1] - cy + span // 2) for p in points]
    pygame.draw.polygon(surf, (*color, int(alpha)), [(int(x), int(y)) for x, y in local])
    surface.blit(surf, (cx - span // 2, cy - span // 2))


class StarParticle:
    COLORS = [
        (255, 220, 0), (255, 180, 0), (255, 255, 120),
        (255, 140, 0), (255, 255, 200), (255, 100, 200),
    ]

    def __init__(self, x, y, big=False):
        self.x = x
        self.y = y
        speed = random.uniform(150, 350) if not big else random.uniform(250, 550)
        angle = random.uniform(0, 2 * math.pi)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed - (100 if big else 50)
        self.gravity = 200
        self.size = random.randint(16, 28) if not big else random.randint(28, 52)
        self.color = random.choice(self.COLORS)
        self.lifetime = random.uniform(0.8, 1.6)
        self.age = 0
        self.angle = random.uniform(0, 360)
        self.angular_vel = random.uniform(-200, 200)
        self.alive = True

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += self.gravity * dt
        self.angle += self.angular_vel * dt
        self.age += dt
        if self.age >= self.lifetime:
            self.alive = False

    def draw(self, surface):
        alpha = max(0, 255 * (1 - self.age / self.lifetime))
        _draw_star_shape(surface, int(self.x), int(self.y), self.size, self.color, alpha)


class ParticleSystem:
    def __init__(self):
        self.particles = []

    def add_confetti_burst(self, x=640, y=0, count=80):
        for _ in range(count):
            cx = random.uniform(x - 220, x + 220)
            cy = random.uniform(y, y + 40)
            self.particles.append(Confetti(cx, cy))

    def add_star_burst(self, x, y, count=20, big=False):
        for _ in range(count):
            self.particles.append(StarParticle(x, y, big=big))

    def update(self, dt):
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.alive]

    def draw(self, surface):
        for p in self.particles:
            p.draw(surface)

    def clear(self):
        self.particles.clear()
