import random

import pygame

from .. import config
from . import sprites
from .base import GameState

COLS, ROWS = 4, 3
CARD = 100
GAP_X, GAP_Y = 20, 16
LEFT = (config.SCREEN_W - (COLS * CARD + (COLS - 1) * GAP_X)) // 2
TOP = 76
PICTURES = ["tree", "star", "snowman", "bauble", "candy_cane", "present", "bell"]
SHOW_MS = 900  # how long a wrong pair stays face up


class MemoryState(GameState):
    """Memory Match: turn over two cards at a time to find the matching
    Christmas pictures. Fewest moves wins."""

    name = "memory"
    score_label = "Moves"
    lower_is_better = True
    full_speed = False  # nothing moves by itself, so let the screen rest

    def reset(self):
        pictures = random.sample(PICTURES, COLS * ROWS // 2) * 2
        random.shuffle(pictures)
        self.cards = [{"picture": p, "up": False, "matched": False} for p in pictures]
        self.picked = []
        self.hide_at = None

    def _card_rect(self, i):
        col, row = i % COLS, i // COLS
        return pygame.Rect(LEFT + col * (CARD + GAP_X), TOP + row * (CARD + GAP_Y), CARD, CARD)

    def _hide_wrong_pair(self):
        for card in self.picked:
            card["up"] = False
        self.picked = []
        self.hide_at = None

    def handle_game_event(self, event):
        if event.type != pygame.MOUSEBUTTONDOWN:
            return
        for i, card in enumerate(self.cards):
            if not self._card_rect(i).collidepoint(event.pos):
                continue
            if card["up"] or card["matched"]:
                return
            if self.hide_at is not None:
                self._hide_wrong_pair()  # don't make them wait to carry on
            card["up"] = True
            self.picked.append(card)
            if len(self.picked) == 2:
                self.score += 1
                first, second = self.picked
                if first["picture"] == second["picture"]:
                    first["matched"] = second["matched"] = True
                    self.picked = []
                    if all(c["matched"] for c in self.cards):
                        self.end_game("You did it!")
                else:
                    self.hide_at = pygame.time.get_ticks() + SHOW_MS
            return

    def step(self, dt):
        if self.hide_at is not None and pygame.time.get_ticks() >= self.hide_at:
            self._hide_wrong_pair()

    def draw_game(self, surface):
        self.draw_background(surface)
        for i, card in enumerate(self.cards):
            rect = self._card_rect(i)
            if card["up"] or card["matched"]:
                face = (255, 250, 235) if not card["matched"] else (220, 245, 220)
                pygame.draw.rect(surface, face, rect, border_radius=12)
                pygame.draw.rect(surface, config.TITLE_COLOR, rect, width=3, border_radius=12)
                picture = sprites.get(card["picture"], CARD - 20)
                surface.blit(picture, picture.get_rect(center=rect.center))
            else:
                surface.blit(sprites.get("card_back", CARD), rect)
