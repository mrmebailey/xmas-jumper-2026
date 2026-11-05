import random

from .. import config
from ..widgets import Button, draw_text
from .base import State


class JokesState(State):
    def on_enter(self):
        app = self.app
        self.buttons = [
            Button((40, 400, 260, 60), "Another", self._another, app.font_medium),
            Button((340, 400, 260, 60), "Back", lambda: app.change_state("menu"), app.font_medium),
        ]
        self._show_new_joke()

    def _show_new_joke(self):
        self.joke = random.choice(self.app.jokes)
        self.app.audio.speak(self.joke)

    def _another(self):
        self._show_new_joke()

    def handle_event(self, event):
        for button in self.buttons:
            button.handle_event(event)

    def update(self):
        self.app.audio.poll_speak()

    def draw(self, surface):
        self.draw_background(surface, "Cracker Jokes")
        draw_text(surface, self.joke, self.app.font_medium, config.SCREEN_W // 2, 110, config.SCREEN_W - 60)
        for button in self.buttons:
            button.draw(surface)
