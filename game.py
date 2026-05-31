import os
import pygame
import math
import random
import sys

from fish import Fish, FISH_DEFS, FISH_ZONE_TOP, SCREEN_W, SCREEN_H
from gauge import Gauge
from particles import ParticleSystem

# Game states
FISHING = 'fishing'
BOSS_INTRO = 'boss_intro'
BOSS_ACTIVE = 'boss_active'
BOSS_SUCCESS = 'boss_success'

_CATCHABLE = {FISHING, BOSS_ACTIVE}

GOAL_Y = 115         # drag above this y to catch
GOAL_HALF_W = 155    # ±x from center for goal zone
HOOK_REST_X = SCREEN_W // 2
HOOK_REST_Y = 88

_FONT_CANDIDATES = [
    os.path.join(os.path.dirname(__file__), 'assets', 'fonts', 'ipagp.ttf'),
    '/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf',
    '/usr/share/fonts/truetype/fonts-japanese-gothic.ttf',
]
FONT_PATH = next((p for p in _FONT_CANDIDATES if os.path.exists(p)), None)


def _try_font(path, size):
    if path:
        try:
            return pygame.font.Font(path, size)
        except Exception:
            pass
    return pygame.font.SysFont(None, size + 10)


class ScorePopup:
    def __init__(self, text, x, y):
        self.text = text
        self.x = float(x)
        self.y = float(y)
        self.age = 0.0
        self.lifetime = 1.3

    def update(self, dt):
        self.age += dt
        self.y -= 65 * dt

    @property
    def alive(self):
        return self.age < self.lifetime


class Game:
    MAX_NORMAL_FISH = 6

    def __init__(self, screen):
        self.screen = screen
        self.state = FISHING
        self.score = 0
        self.gauge = Gauge()
        self.particles = ParticleSystem()
        self.fishes = []
        self.dragging_fish = None
        self.hook_x = float(HOOK_REST_X)
        self.hook_y = float(HOOK_REST_Y)
        self.is_dragging = False
        self.state_timer = 0.0
        self.score_popups = []
        self.last_caught_name = ''
        self._boss_spawned = False

        self._init_fonts()
        self._init_sounds()
        self._build_background()
        self._spawn_normal_fish(self.MAX_NORMAL_FISH)

    # ------------------------------------------------------------------ setup

    def _init_fonts(self):
        self.font_lg = _try_font(FONT_PATH, 60)
        self.font_md = _try_font(FONT_PATH, 38)
        self.font_sm = _try_font(FONT_PATH, 26)
        self.font_xs = _try_font(FONT_PATH, 20)

    def _init_sounds(self):
        self._snd = {}
        self._bgm = None
        try:
            import numpy as np
            sr = 44100

            def sine(freq, dur, vol=0.35, attack=0.015, release=0.12):
                n = int(sr * dur)
                t = np.linspace(0, dur, n, False)
                w = np.sin(2 * np.pi * freq * t)
                env = np.ones(n)
                a = int(sr * attack)
                r = int(sr * release)
                if a < n:
                    env[:a] = np.linspace(0, 1, a)
                if r < n:
                    env[n - r:] *= np.linspace(1, 0, r)
                data = (w * env * vol * 32767).astype(np.int16)
                return np.stack([data, data], axis=-1)

            def make_sound(*segs):
                gap = np.zeros((int(sr * 0.018), 2), dtype=np.int16)
                full = np.concatenate([np.concatenate([s, gap]) for s in segs])
                return pygame.sndarray.make_sound(full)

            # success jingle: C5 E5 G5 C6
            self._snd['success'] = make_sound(
                sine(523, 0.11), sine(659, 0.11), sine(784, 0.11), sine(1047, 0.18)
            )
            # fail sound: descending glide
            n_f = int(sr * 0.45)
            t_f = np.linspace(0, 0.45, n_f, False)
            freq_f = 380 - 180 * t_f / 0.45
            w_f = np.sin(2 * np.pi * np.cumsum(freq_f) / sr)
            env_f = np.linspace(1, 0, n_f)
            fail_data = (w_f * env_f * 0.3 * 32767).astype(np.int16)
            self._snd['fail'] = pygame.sndarray.make_sound(np.stack([fail_data, fail_data], axis=-1))

            # boss fanfare: dramatic low rumble
            self._snd['boss'] = make_sound(
                sine(110, 0.2, 0.5), sine(165, 0.2, 0.4), sine(220, 0.15, 0.35),
                sine(110, 0.1, 0.4), sine(165, 0.35, 0.45),
            )
            # flower丸 fanfare
            self._snd['hanmaru'] = make_sound(
                sine(523, 0.10), sine(659, 0.10), sine(784, 0.10),
                sine(1047, 0.13), sine(1319, 0.22),
            )

            # BGM: simple C-major arpeggio loop
            melody = [
                (523, 0.5), (659, 0.5), (784, 0.5), (1047, 0.5),
                (784, 0.5), (659, 0.5), (523, 0.5), (440, 0.5),
                (392, 0.5), (523, 0.5), (659, 0.5), (784, 0.5),
                (880, 0.5), (784, 0.5), (659, 0.5), (523, 1.0),
            ]
            bpm = 112
            beat = 60.0 / bpm
            segs = []
            for freq, beats in melody:
                dur = beats * beat
                n = int(sr * dur)
                t = np.linspace(0, dur, n, False)
                w = (0.55 * np.sin(2 * np.pi * freq * t)
                     + 0.3 * np.sin(2 * np.pi * freq * 2 * t)
                     + 0.1 * np.sin(2 * np.pi * freq * 3 * t)) / 0.95
                env = np.ones(n)
                a = int(sr * 0.018)
                r = int(sr * 0.08)
                if a < n:
                    env[:a] = np.linspace(0, 1, a)
                if r < n:
                    env[n - r:] *= np.linspace(1, 0.25, r)
                segs.append(w * env)
            bgm_wave = np.concatenate(segs)
            bgm_data = (bgm_wave * 0.14 * 32767).astype(np.int16)
            self._bgm = pygame.sndarray.make_sound(np.stack([bgm_data, bgm_data], axis=-1))
            self._bgm.play(-1)
        except Exception:
            pass

    def _play(self, name):
        s = self._snd.get(name)
        if s:
            s.play()

    def _build_background(self):
        bg = pygame.Surface((SCREEN_W, SCREEN_H))
        for y in range(SCREEN_H):
            r_ratio = y / SCREEN_H
            r = int(8 + 28 * r_ratio)
            g = int(55 + 75 * r_ratio)
            b = int(160 + 60 * (1 - r_ratio))
            pygame.draw.line(bg, (r, g, b), (0, y), (SCREEN_W, y))

        # Light rays from top
        for i in range(6):
            bx = 150 + i * 200
            pts = [(bx - 30, 0), (bx + 30, 0), (bx + 120, SCREEN_H), (bx - 120, SCREEN_H)]
            ray_surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            pygame.draw.polygon(ray_surf, (255, 255, 255, 10), pts)
            bg.blit(ray_surf, (0, 0))

        # Seaweed
        for sx in range(40, SCREEN_W, 110):
            hgt = random.randint(55, 130)
            col = random.choice([(45, 145, 75), (35, 125, 65), (65, 165, 85)])
            for i in range(hgt):
                t = i / hgt
                ox = int(math.sin(t * 4.5) * 14)
                pygame.draw.circle(bg, col, (sx + ox, SCREEN_H - i - 5), 3)

        # Sandy floor
        for fx in range(0, SCREEN_W, 1):
            variation = random.randint(-3, 3)
            pygame.draw.line(bg, (200, 175, 120), (fx, SCREEN_H - 12 + variation),
                             (fx, SCREEN_H), 1)

        # Static bubble decorations
        for _ in range(25):
            bx = random.randint(0, SCREEN_W)
            by = random.randint(150, SCREEN_H - 20)
            br = random.randint(3, 11)
            pygame.draw.circle(bg, (110, 185, 255), (bx, by), br, 2)

        self._bg = bg

    # --------------------------------------------------------------- spawning

    def _spawn_normal_fish(self, count):
        normal = [d for d in FISH_DEFS if not d['boss']]
        weights = [d['weight'] for d in normal]
        for _ in range(count):
            chosen = random.choices(normal, weights=weights, k=1)[0]
            self.fishes.append(Fish(chosen))

    def _spawn_boss(self):
        boss_def = next(d for d in FISH_DEFS if d['boss'])
        boss = Fish(boss_def, x=SCREEN_W + 160, y=SCREEN_H // 2)
        boss.vx = -boss.speed
        boss.facing_right = False
        self.fishes.append(boss)
        self._boss_spawned = True

    # ------------------------------------------------------------ event handling

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._on_click(event.pos)
        elif event.type == pygame.MOUSEMOTION and self.is_dragging:
            self._on_drag(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.is_dragging:
            self._on_release(event.pos)
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            pygame.quit()
            sys.exit()

    def _on_click(self, pos):
        if self.state not in _CATCHABLE:
            return
        mx, my = pos
        for fish in self.fishes:
            if fish.state == Fish.STATE_SWIMMING and fish.get_rect().collidepoint(mx, my):
                fish.state = Fish.STATE_CAUGHT
                fish.target_x = float(mx)
                fish.target_y = float(my)
                self.dragging_fish = fish
                self.hook_x = float(mx)
                self.hook_y = float(my)
                self.is_dragging = True
                break

    def _on_drag(self, pos):
        if self.dragging_fish:
            self.hook_x, self.hook_y = float(pos[0]), float(pos[1])
            self.dragging_fish.target_x = self.hook_x
            self.dragging_fish.target_y = self.hook_y

    def _on_release(self, pos):
        self.is_dragging = False
        fish = self.dragging_fish
        self.dragging_fish = None
        if fish is None:
            return

        mx, my = pos
        in_goal = (my <= GOAL_Y and abs(mx - SCREEN_W // 2) <= GOAL_HALF_W)
        if in_goal:
            self._catch_success(fish)
        else:
            self._catch_fail(fish)

    # --------------------------------------------------------------- catch logic

    def _catch_success(self, fish):
        pts = fish.gauge_value * 100
        self.score += pts
        self.gauge.add(fish.gauge_value * (20 if fish.boss else 10))
        self.last_caught_name = fish.name
        self.score_popups.append(ScorePopup(f'+{pts}', fish.x, fish.y))
        fish.state = Fish.STATE_DEAD
        self._play('success')
        self.particles.add_confetti_burst(count=55)

        if fish.boss:
            self._play('hanmaru')
            self.particles.add_star_burst(SCREEN_W // 2, SCREEN_H // 2, count=45, big=True)
            self.particles.add_confetti_burst(count=100)
            self.gauge.reset()
            self.state = BOSS_SUCCESS
            self.state_timer = 0.0
        elif self.gauge.is_full and self.state == FISHING:
            self.state = BOSS_INTRO
            self.state_timer = 0.0
            self._boss_spawned = False
            self._play('boss')

    def _catch_fail(self, fish):
        fish.start_escape()
        self._play('fail')

    # ------------------------------------------------------------------- update

    def update(self, dt):
        dt = min(dt, 0.05)

        for fish in self.fishes:
            fish.update(dt)
        self.fishes = [f for f in self.fishes if not f.is_dead]

        for p in self.score_popups:
            p.update(dt)
        self.score_popups = [p for p in self.score_popups if p.alive]

        self.particles.update(dt)

        if self.state == FISHING:
            normal = [f for f in self.fishes if not f.boss]
            deficit = self.MAX_NORMAL_FISH - len(normal)
            if deficit > 0:
                self._spawn_normal_fish(deficit)

        elif self.state == BOSS_INTRO:
            self.state_timer += dt
            if self.state_timer >= 2.8 and not self._boss_spawned:
                self._spawn_boss()
            if self.state_timer >= 3.2:
                self.state = BOSS_ACTIVE
                self.state_timer = 0.0
                # Remove normal fish to spotlight the boss
                self.fishes = [f for f in self.fishes if f.boss]

        elif self.state == BOSS_ACTIVE:
            self.state_timer += dt
            has_boss = any(f.boss and not f.is_dead for f in self.fishes)
            if not has_boss:
                # Boss escaped without being caught
                self.gauge.reset()
                self.state = FISHING
                self.state_timer = 0.0

        elif self.state == BOSS_SUCCESS:
            self.state_timer += dt
            if self.state_timer >= 3.5:
                self.state = FISHING
                self.state_timer = 0.0

    # -------------------------------------------------------------------- draw

    def draw(self):
        self.screen.blit(self._bg, (0, 0))
        self._draw_water_surface()
        self._draw_animated_bubbles()

        # Swimming fish
        for fish in self.fishes:
            if fish != self.dragging_fish:
                fish.draw(self.screen)

        # Fishing line and hook
        self._draw_line_and_hook()

        # Dragging fish on top
        if self.dragging_fish:
            self.dragging_fish.draw(self.screen)

        # UI panel
        self._draw_ui()

        # Particles
        self.particles.draw(self.screen)

        # Score popups
        self._draw_score_popups()

        # State overlays
        if self.state == BOSS_INTRO:
            self._draw_boss_banner()
        elif self.state == BOSS_SUCCESS:
            self._draw_hanmaru_effect()

    def _draw_water_surface(self):
        t = pygame.time.get_ticks() / 1000.0
        surf = pygame.Surface((SCREEN_W, 18), pygame.SRCALPHA)
        for x in range(0, SCREEN_W, 2):
            wave_y = int(8 + math.sin(x * 0.025 + t * 2.2) * 5 + math.sin(x * 0.04 + t * 1.5) * 3)
            pygame.draw.line(surf, (160, 220, 255, 110), (x, wave_y), (x, wave_y + 4), 2)
        self.screen.blit(surf, (0, FISH_ZONE_TOP - 15))

    def _draw_animated_bubbles(self):
        t = pygame.time.get_ticks() / 1000.0
        for i in range(7):
            bx = int((180 + i * 175 + math.sin(t * 0.6 + i * 1.1) * 22) % SCREEN_W)
            by = int(SCREEN_H - 30 - (t * 35 + i * 95) % (SCREEN_H - 180))
            r = 3 + i % 4
            pygame.draw.circle(self.screen, (170, 220, 255), (bx, by), r, 2)

    def _draw_line_and_hook(self):
        if self.is_dragging:
            hx, hy = int(self.hook_x), int(self.hook_y)
            pygame.draw.line(self.screen, (230, 230, 200), (HOOK_REST_X, 10), (hx, hy), 2)
            self._draw_hook_icon(hx, hy)
        else:
            t = pygame.time.get_ticks() / 1000.0
            sway = int(math.sin(t * 1.6) * 22)
            hx = HOOK_REST_X + sway
            hy = HOOK_REST_Y
            pygame.draw.line(self.screen, (230, 230, 200), (HOOK_REST_X, 10), (hx, hy), 2)
            self._draw_hook_icon(hx, hy)

    def _draw_hook_icon(self, x, y):
        pygame.draw.circle(self.screen, (240, 210, 80), (x, y), 9)
        pygame.draw.circle(self.screen, (180, 150, 40), (x, y), 9, 2)
        pygame.draw.arc(self.screen, (180, 150, 40),
                        (x - 8, y + 2, 16, 18), math.pi, 0, 3)
        pygame.draw.line(self.screen, (180, 150, 40), (x + 8, y + 10), (x + 8, y + 2), 3)

    def _draw_ui(self):
        # Top panel
        panel = pygame.Surface((SCREEN_W, 115), pygame.SRCALPHA)
        panel.fill((0, 15, 50, 170))
        self.screen.blit(panel, (0, 0))

        # Bucket
        self._draw_bucket()

        # Goal zone highlight when dragging
        if self.is_dragging:
            gz = pygame.Surface((GOAL_HALF_W * 2, GOAL_Y), pygame.SRCALPHA)
            gz.fill((255, 255, 80, 55))
            self.screen.blit(gz, (SCREEN_W // 2 - GOAL_HALF_W, 0))
            for gx in range(SCREEN_W // 2 - GOAL_HALF_W, SCREEN_W // 2 + GOAL_HALF_W, 22):
                pygame.draw.line(self.screen, (255, 255, 100, 200),
                                 (gx, GOAL_Y), (gx + 12, GOAL_Y), 3)

        # Gauge
        self.gauge.draw(self.screen, (240, 12, 460, 34), self.font_xs)

        # Score
        score_surf = self.font_md.render(f"スコア: {self.score}", True, (255, 240, 100))
        self.screen.blit(score_surf, (SCREEN_W - score_surf.get_width() - 20, 18))

        # Hint / catch feedback
        if self.is_dragging and self.dragging_fish:
            msg = self.font_sm.render(
                f"うえのバケツまで はこぼう！  【{self.dragging_fish.name}】",
                True, (255, 255, 255))
            self.screen.blit(msg, (20, 78))
        elif self.state == BOSS_ACTIVE:
            pulse = abs(math.sin(pygame.time.get_ticks() / 400.0))
            col = (int(255 * pulse), int(100 * pulse), 50)
            msg = self.font_sm.render("★ サメがあらわれた！ つりあげよう！ ★", True, col)
            self.screen.blit(msg, (SCREEN_W // 2 - msg.get_width() // 2, 78))
        else:
            hint = self.font_xs.render("さかなをクリックして バケツまで ひっぱろう！", True, (200, 230, 255))
            self.screen.blit(hint, (20, 84))

    def _draw_bucket(self):
        bx, by = SCREEN_W // 2, 8
        # Body trapezoid
        pts = [
            (bx - 38, by + 22), (bx + 38, by + 22),
            (bx + 28, by + 70), (bx - 28, by + 70),
        ]
        pygame.draw.polygon(self.screen, (210, 130, 55), pts)
        pygame.draw.polygon(self.screen, (150, 85, 25), pts, 3)
        # Top rim
        pygame.draw.line(self.screen, (150, 85, 25), (bx - 40, by + 21), (bx + 40, by + 21), 4)
        # Handle arc
        pygame.draw.arc(self.screen, (130, 75, 20),
                        (bx - 28, by - 12, 56, 38), 0, math.pi, 4)
        # Water reflection
        pygame.draw.ellipse(self.screen, (80, 160, 220),
                            (bx - 20, by + 30, 40, 20))
        # Label
        label = self.font_xs.render("バケツ", True, (255, 240, 200))
        self.screen.blit(label, (bx - label.get_width() // 2, by + 76))

    def _draw_score_popups(self):
        for popup in self.score_popups:
            alpha = int(255 * (1 - popup.age / popup.lifetime))
            surf = self.font_md.render(popup.text, True, (255, 240, 60))
            surf.set_alpha(alpha)
            self.screen.blit(surf, (int(popup.x) - surf.get_width() // 2, int(popup.y)))

    def _draw_boss_banner(self):
        progress = min(1.0, self.state_timer / 0.45)
        scale = _ease_out_bounce(progress)

        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 25, int(120 * min(1.0, progress * 2))))
        self.screen.blit(overlay, (0, 0))

        bw = int(SCREEN_W * 0.82 * scale)
        bh = int(130 * scale)
        if bw < 10 or bh < 10:
            return

        banner = pygame.Surface((bw, bh), pygame.SRCALPHA)
        # Gradient fill
        for row in range(bh):
            r_r = row / bh
            col = (int(200 + 55 * r_r), int(20 + 30 * r_r), int(20 + 30 * r_r), 235)
            pygame.draw.line(banner, col, (0, row), (bw, row))
        pygame.draw.rect(banner, (255, 210, 0), (0, 0, bw, bh), 6, border_radius=12)

        # Flashing stars on border
        t = pygame.time.get_ticks() / 1000.0
        for i in range(10):
            sx = int(bw * (i + 0.5) / 10)
            flash = abs(math.sin(t * 4 + i * 0.6))
            scol = (int(255 * flash), int(220 * flash), 0)
            _mini_star(banner, sx, 10, 8, scol)
            _mini_star(banner, sx, bh - 10, 8, scol)

        if scale > 0.55:
            txt = self.font_lg.render("すごい おおもの チャレンジ！", True, (255, 255, 255))
            banner.blit(txt, (bw // 2 - txt.get_width() // 2, bh // 2 - txt.get_height() // 2))

        bx = SCREEN_W // 2 - bw // 2
        by = SCREEN_H // 2 - bh // 2
        self.screen.blit(banner, (bx, by))

    def _draw_hanmaru_effect(self):
        t = self.state_timer
        scale = min(1.5, t * 3.2)
        alpha = int(255 * max(0.0, min(1.0, 3.5 - t * 1.2)))

        # Big "はなまる！" text
        txt = self.font_lg.render("はなまる！", True, (255, 230, 0))
        sw = int(txt.get_width() * scale)
        sh = int(txt.get_height() * scale)
        if sw > 0 and sh > 0:
            scaled = pygame.transform.scale(txt, (sw, sh))
            scaled.set_alpha(alpha)
            self.screen.blit(scaled, (SCREEN_W // 2 - sw // 2, SCREEN_H // 2 - sh // 2 - 60))

        if scale > 0.85:
            sub = self.font_md.render("サメをつった！ すごい！", True, (255, 255, 255))
            sub.set_alpha(alpha)
            self.screen.blit(sub, (SCREEN_W // 2 - sub.get_width() // 2, SCREEN_H // 2 + 70))


def _mini_star(surface, cx, cy, size, color):
    pts = []
    for i in range(10):
        angle = math.radians(i * 36 - 90)
        r = size if i % 2 == 0 else size * 0.42
        pts.append((int(cx + math.cos(angle) * r), int(cy + math.sin(angle) * r)))
    pygame.draw.polygon(surface, color, pts)


def _ease_out_bounce(t):
    if t < 1 / 2.75:
        return 7.5625 * t * t
    elif t < 2 / 2.75:
        t -= 1.5 / 2.75
        return 7.5625 * t * t + 0.75
    elif t < 2.5 / 2.75:
        t -= 2.25 / 2.75
        return 7.5625 * t * t + 0.9375
    else:
        t -= 2.625 / 2.75
        return 7.5625 * t * t + 0.984375
