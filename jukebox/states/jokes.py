import random

import pygame

from .. import config
from ..jokes_loader import recorded_speech, split_joke
from ..widgets import Button, draw_text
from .base import State


class JokesState(State):
    """Father Christmas reads the question, pauses, then delivers the punch
    line (louder and deeper), which pops up on screen as he says it. With the
    recordings from tools/make_santa_voice.py he also opens with a line of his
    own over sleigh bells, laughs "Ho ho ho! Merry Christmas!", and sometimes adds
    a word afterwards."""

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
        # Each bit plays its recording from tools/make_santa_voice.py if
        # there is one, or is spoken by espeak in these voices if not.
        rec = lambda text, kind: recorded_speech(config.JOKE_AUDIO_DIR, text, kind)  # noqa: E731
        question = rec(self.setup, "q")
        # Santa's own lines only come recorded: espeak's voice saying them
        # would just be a longer wait for the joke.
        recorded = question.exists()
        parts = []
        if recorded:
            intro = self._pick_recorded(config.SANTA_INTROS, "intro")
            if intro:
                parts.append((intro[0], config.SANTA_VOICE, 0, intro[1]))
        parts.append((self.setup, config.SANTA_VOICE, 300 if parts else 0, question))
        self._punch_part = len(parts)
        if self.punch_line:
            parts.append((self.punch_line, config.PUNCH_LINE_VOICE, config.JOKE_PAUSE_MS,
                          rec(self.punch_line, "p")))
            laugh = self._pick_recorded(config.SANTA_LAUGHS, "laugh")
            if laugh:
                parts.append((config.JOKE_LAUGH or "Ho ho ho!", config.SANTA_VOICE, 400, laugh[1]))
            elif config.JOKE_LAUGH:
                parts.append((config.JOKE_LAUGH, config.SANTA_VOICE, 400))
            if recorded and random.random() < config.OUTRO_CHANCE:
                outro = self._pick_recorded(config.SANTA_OUTROS, "outro")
                if outro:
                    parts.append((outro[0], config.SANTA_VOICE, 300, outro[1]))
        self.app.audio.speak_parts(parts)

    @staticmethod
    def _pick_recorded(texts, kind):
        """A random (text, recording) among those that have been recorded, or None."""
        found = [(text, recorded_speech(config.JOKE_AUDIO_DIR, text, kind)) for text in texts]
        found = [item for item in found if item[1].exists()]
        return random.choice(found) if found else None

    def _another(self):
        self._show_new_joke()

    def handle_event(self, event):
        for button in self.buttons:
            button.handle_event(event)

    def update(self):
        if self.revealed:
            return
        audio = self.app.audio
        if audio.part_started(self._punch_part):
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
