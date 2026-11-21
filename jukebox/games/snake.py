import random

import pygame

from .. import config
from ..widgets import draw_text
from . import sprites
from .base import PLAY_TOP, GameState

CELL = 32
COLS = config.SCREEN_W // CELL
ROWS = (config.SCREEN_H - PLAY_TOP) // CELL
SWIPE_PX = 30
START_STEP_MS = 230
FASTEST_STEP_MS = 120
PRESENT_COLORS = [sprites.RED, sprites.BLUE, sprites.PURPLE, sprites.GREEN]
# Which way the head picture is turned for each direction (it's drawn facing right).
_ANGLE = {(1, 0): 0, (0, -1): 90, (-1, 0): 180, (0, 1): -90}
_KEYS = {pygame.K_UP: (0, -1), pygame.K_DOWN: (0, 1), pygame.K_LEFT: (-1, 0), pygame.K_RIGHT: (1, 0)}


class SnakeState(GameState):
    """Reindeer Snake: swipe to steer Rudolph round the field collecting
    presents. Every present adds another reindeer to the team behind him;
    hitting the fence or the team ends the game."""

    name = "snake"
    score_label = "Presents"

    def reset(self):
        mid = ROWS // 2
        self.body = [(5, mid), (4, mid), (3, mid)]  # head first
        self.direction = (1, 0)
        self.turns = []  # swipes waiting for the next step
        self.grow = 0
        self.step_ms = START_STEP_MS
        self.elapsed = 0
        self.waiting = True  # until the first swipe
        self._swipe_from = None
        self._place_present()

    def _place_present(self):
        free = [(x, y) for x in range(COLS) for y in range(ROWS) if (x, y) not in self.body]
        self.present = random.choice(free)
        self.present_color = random.choice(PRESENT_COLORS)

    def _turn(self, direction):
        # Any swipe starts the game; one that can't turn him (right, the way
        # he's facing, or left, back into his team) just sets him off.
        self.waiting = False
        last = self.turns[-1] if self.turns else self.direction
        if direction == last or direction == (-last[0], -last[1]):
            return  # same way, or straight back into the team
        if len(self.turns) < 2:
            self.turns.append(direction)

    def handle_game_event(self, event):
        if event.type == pygame.KEYDOWN and event.key in _KEYS:
            self._turn(_KEYS[event.key])
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self._swipe_from = event.pos
        elif event.type == pygame.MOUSEMOTION and self._swipe_from is not None:
            # Turn as soon as the finger has moved far enough, so a turn
            # doesn't wait for it to lift; carry on from here for the next one.
            dx = event.pos[0] - self._swipe_from[0]
            dy = event.pos[1] - self._swipe_from[1]
            if max(abs(dx), abs(dy)) >= SWIPE_PX:
                self._turn((1 if dx > 0 else -1, 0) if abs(dx) > abs(dy) else (0, 1 if dy > 0 else -1))
                self._swipe_from = event.pos
        elif event.type == pygame.MOUSEBUTTONUP:
            self._swipe_from = None

    def step(self, dt):
        if self.waiting:
            return
        self.elapsed += dt
        while self.elapsed >= self.step_ms and not self.over:
            self.elapsed -= self.step_ms
            self._move()

    def _move(self):
        if self.turns:
            self.direction = self.turns.pop(0)
        hx, hy = self.body[0]
        head = (hx + self.direction[0], hy + self.direction[1])
        # The last reindeer moves out of the way this step unless the team is growing.
        team = self.body if self.grow else self.body[:-1]
        if not (0 <= head[0] < COLS and 0 <= head[1] < ROWS) or head in team:
            self.end_game("Crash!")
            return
        self.body.insert(0, head)
        if self.grow:
            self.grow -= 1
        else:
            self.body.pop()
        if head == self.present:
            self.score += 1
            self.grow += 1
            self.step_ms = max(FASTEST_STEP_MS, self.step_ms - 6)
            self._place_present()

    def _cell(self, x, y):
        return x * CELL, PLAY_TOP + y * CELL

    def draw_game(self, surface):
        self.draw_background(surface)
        field = pygame.Rect(0, PLAY_TOP, COLS * CELL, ROWS * CELL)
        pygame.draw.rect(surface, (14, 70, 40), field)
        pygame.draw.rect(surface, sprites.BROWN, field, width=3)
        surface.blit(sprites.get("present", CELL, self.present_color), self._cell(*self.present))
        for i, (x, y) in enumerate(self.body[1:]):
            surface.blit(sprites.get("reindeer_body", CELL, i % 2), self._cell(x, y))
        head = sprites.get("reindeer", CELL)
        surface.blit(pygame.transform.rotate(head, _ANGLE[self.direction]), self._cell(*self.body[0]))
        if self.waiting:
            draw_text(surface, "Swipe to start!", self.app.font_large, config.SCREEN_W // 2, 330,
                      config.SCREEN_W - 40, config.TITLE_COLOR)
