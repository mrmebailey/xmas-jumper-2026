import random

import pygame

from .. import config
from ..widgets import draw_text, render_text
from . import sprites
from .base import PLAY_TOP, GameState

ITEM = 48
SACK = 96
SACK_Y = config.SCREEN_H - SACK + 6
SACK_SPEED = 650  # px/s
LIVES = 3
# What falls, and how often (out of 100).
_KINDS = [("present", 68), ("coal", 24), ("star", 8)]
_POINTS = {"present": 1, "star": 5}
PRESENT_COLORS = [sprites.RED, sprites.BLUE, sprites.PURPLE, sprites.GREEN]


class CatchState(GameState):
    """Present Catch: hold a finger on either side (or drag) to slide Santa's
    sack under the falling presents. Stars are worth 5. Catching coal or
    letting a present hit the ground costs a life."""

    name = "catch"

    def reset(self):
        self.sack_x = config.SCREEN_W / 2
        self.target_x = None  # where the finger is, while it's down
        self.items = []
        self.popups = []  # (text, x, y, until)
        self.lives = LIVES
        self.played = 0  # ms
        self.next_drop = 800

    def handle_game_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN or (event.type == pygame.MOUSEMOTION and self.target_x is not None):
            self.target_x = event.pos[0]
        elif event.type == pygame.MOUSEBUTTONUP:
            self.target_x = None
        elif event.type == pygame.KEYDOWN and event.key in (pygame.K_LEFT, pygame.K_RIGHT):
            self.target_x = 0 if event.key == pygame.K_LEFT else config.SCREEN_W
        elif event.type == pygame.KEYUP and event.key in (pygame.K_LEFT, pygame.K_RIGHT):
            self.target_x = None

    def _drop(self):
        kind = random.choices([k for k, _ in _KINDS], weights=[w for _, w in _KINDS])[0]
        seconds = self.played / 1000
        self.items.append({
            "kind": kind,
            "color": random.choice(PRESENT_COLORS),
            "x": random.uniform(ITEM / 2 + 10, config.SCREEN_W - ITEM / 2 - 10),
            "y": PLAY_TOP - ITEM,
            # Everything falls faster the longer you last.
            "speed": min(330, 120 + seconds * 3) * random.uniform(0.85, 1.15),
        })

    def _popup(self, text, x, color):
        self.popups.append((text, x, SACK_Y - 30, pygame.time.get_ticks() + 600, color))

    def step(self, dt):
        self.played += dt
        seconds = dt / 1000
        if self.target_x is not None:
            move = SACK_SPEED * seconds
            self.sack_x += max(-move, min(move, self.target_x - self.sack_x))
            self.sack_x = max(SACK / 2, min(config.SCREEN_W - SACK / 2, self.sack_x))

        self.next_drop -= dt
        if self.next_drop <= 0:
            self._drop()
            self.next_drop = max(450, 1100 - self.played / 60)

        for item in list(self.items):
            item["y"] += item["speed"] * seconds
            bottom = item["y"] + ITEM / 2
            if bottom >= SACK_Y + 30 and abs(item["x"] - self.sack_x) < SACK / 2 + 4:
                self.items.remove(item)
                if item["kind"] == "coal":
                    self._lose_life(item["x"], "Coal!")
                else:
                    self.score += _POINTS[item["kind"]]
                    self._popup(f"+{_POINTS[item['kind']]}", item["x"], config.TITLE_COLOR)
            elif item["y"] - ITEM / 2 > config.SCREEN_H:
                self.items.remove(item)
                if item["kind"] != "coal":
                    self._lose_life(item["x"], "Dropped!")
        now = pygame.time.get_ticks()
        self.popups = [p for p in self.popups if p[3] > now]

    def _lose_life(self, x, text):
        self.lives -= 1
        self._popup(text, x, (255, 120, 120))
        if self.lives <= 0:
            self.end_game()

    def draw_game(self, surface):
        self.draw_background(surface)
        for item in self.items:
            args = (item["color"],) if item["kind"] == "present" else ()
            picture = sprites.get(item["kind"], ITEM, *args)
            surface.blit(picture, picture.get_rect(center=(item["x"], item["y"])))
        sack = sprites.get("sack", SACK)
        surface.blit(sack, (self.sack_x - SACK / 2, SACK_Y))
        for i in range(self.lives):
            surface.blit(sprites.get("heart", 28), (440 - i * 32, 30))
        for text, x, y, _, color in self.popups:
            rendered = render_text(self.app.font_medium, text, color)
            surface.blit(rendered, rendered.get_rect(center=(x, y)))
        if self.played < 2500:
            draw_text(surface, "Hold left or right to move the sack", self.app.font_small, config.SCREEN_W // 2,
                      200, config.SCREEN_W - 60, config.TITLE_COLOR)
