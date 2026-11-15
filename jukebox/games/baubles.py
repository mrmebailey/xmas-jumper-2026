import math
import random

import pygame

from .. import config
from ..widgets import draw_text
from . import sprites
from .base import PLAY_TOP, GameState

BAUBLE = 64
HIT_RADIUS = 40  # a little bigger than the bauble, for fingers
TREE = 400
LIVES = 3
MAX_AT_ONCE = 4
COLORS = [sprites.RED, sprites.BLUE, sprites.PURPLE, sprites.GOLD, (230, 90, 160)]
POP_MS = 300


class BaublesState(GameState):
    """Bauble Pop: baubles appear on the tree; tap them before they vanish.
    They come quicker and last less time as you go. Each one missed costs a life."""

    name = "baubles"

    def reset(self):
        self.baubles = []  # dicts: x, y, color, born, life
        self.pops = []  # (x, y, color, started)
        self.lives = LIVES
        self.played = 0
        self.next_spawn = 600

    def _spawn(self):
        now = pygame.time.get_ticks()
        seconds = self.played / 1000
        for _ in range(20):  # find a spot clear of the others
            x = random.uniform(60, config.SCREEN_W - 60)
            y = random.uniform(PLAY_TOP + 40, config.SCREEN_H - 45)
            if all(math.hypot(x - b["x"], y - b["y"]) > BAUBLE * 1.3 for b in self.baubles):
                break
        else:
            return
        self.baubles.append({
            "x": x, "y": y, "color": random.choice(COLORS), "born": now,
            "life": max(900, 2300 - seconds * 25),
        })

    def handle_game_event(self, event):
        if event.type != pygame.MOUSEBUTTONDOWN:
            return
        hits = [b for b in self.baubles if math.hypot(event.pos[0] - b["x"], event.pos[1] - b["y"]) <= HIT_RADIUS]
        if hits:
            bauble = min(hits, key=lambda b: math.hypot(event.pos[0] - b["x"], event.pos[1] - b["y"]))
            self.baubles.remove(bauble)
            self.pops.append((bauble["x"], bauble["y"], bauble["color"], pygame.time.get_ticks()))
            self.score += 1

    def step(self, dt):
        self.played += dt
        now = pygame.time.get_ticks()
        self.next_spawn -= dt
        if self.next_spawn <= 0:
            if len(self.baubles) < MAX_AT_ONCE:
                self._spawn()
            self.next_spawn = max(420, 1100 - self.played / 50)
        for bauble in list(self.baubles):
            if now - bauble["born"] > bauble["life"]:
                self.baubles.remove(bauble)
                self.lives -= 1
                if self.lives <= 0:
                    self.end_game()
                    break
        self.pops = [p for p in self.pops if now - p[3] < POP_MS]

    def draw_game(self, surface):
        self.draw_background(surface)
        tree = sprites.get("tree", TREE)
        surface.blit(tree, tree.get_rect(midbottom=(config.SCREEN_W // 2, config.SCREEN_H + 10)))
        now = pygame.time.get_ticks()
        for b in self.baubles:
            age = (now - b["born"]) / b["life"]
            # Blink when it's about to go.
            if age > 0.7 and (now // 150) % 2:
                continue
            picture = sprites.get("bauble", BAUBLE, b["color"])
            surface.blit(picture, picture.get_rect(center=(b["x"], b["y"])))
        for x, y, color, started in self.pops:
            t = (now - started) / POP_MS
            pygame.draw.circle(surface, color, (x, y), int(BAUBLE * (0.4 + 0.5 * t)), 4)
            for i in range(6):
                a = i * math.pi / 3
                r = BAUBLE * (0.3 + 0.6 * t)
                pygame.draw.circle(surface, config.TITLE_COLOR, (x + r * math.cos(a), y + r * math.sin(a)), 4)
        for i in range(self.lives):
            surface.blit(sprites.get("heart", 28), (440 - i * 32, 30))
        if self.played < 2500:
            draw_text(surface, "Tap the baubles before they vanish!", self.app.font_small, config.SCREEN_W // 2,
                      200, config.SCREEN_W - 60, config.TITLE_COLOR)
