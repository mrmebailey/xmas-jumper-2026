import random

import pygame

from .. import config
from ..widgets import Button, draw_text
from .base import State


def split_joke(joke):
    """("Why did...?", "Because...") at the first question mark; the whole
    joke and no punch line if there isn't one."""
    question, mark, answer = joke.partition("?")
    if not mark or not answer.strip():
        return joke, ""
    return question + "?", answer.strip()


class JokesState(State):
    """Father Christmas reads the question, pauses, then delivers the punch
    line (louder and deeper), which pops up on screen as he says it."""

    def on_enter(self):
        app = self.app
        self.buttons = [
            Button((40, 400, 260, 60), "Another", self._another, app.font_medium),
            Button((340, 400, 260, 60), "Back", lambda: app.change_state("menu"), app.font_medium),
        ]
        self._show_new_joke()

    def _show_new_joke(self):
        self.setup, self.punch_line = split_joke(random.choice(self.app.jokes))
        self.revealed = not self.punch_line
        self.shown_at = pygame.time.get_ticks()
        parts = [(self.setup, config.SANTA_VOICE, 0)]
        if self.punch_line:
            parts.append((self.punch_line, config.PUNCH_LINE_VOICE, config.JOKE_PAUSE_MS))
            if config.JOKE_LAUGH:
                parts.append((config.JOKE_LAUGH, config.SANTA_VOICE, 400))
        self.app.audio.speak_parts(parts)

    def _another(self):
        self._show_new_joke()

    def handle_event(self, event):
        for button in self.buttons:
            button.handle_event(event)

    def update(self):
        if self.revealed:
            return
        audio = self.app.audio
        if audio.part_started(1):
            self.revealed = True
        elif not audio.speaking and pygame.time.get_ticks() - self.shown_at > config.JOKE_PAUSE_MS + 2000:
            # No speech (espeak missing or failed): still give the punch line its moment.
            self.revealed = True

    def draw(self, surface):
        self.draw_background(surface, "Cracker Jokes")
        y = draw_text(surface, self.setup, self.app.font_medium, config.SCREEN_W // 2, 100, config.SCREEN_W - 60)
        if self.revealed and self.punch_line:
            draw_text(surface, self.punch_line, self.app.font_large, config.SCREEN_W // 2, y + 30,
                      config.SCREEN_W - 50, config.TITLE_COLOR)
        for button in self.buttons:
            button.draw(surface)
