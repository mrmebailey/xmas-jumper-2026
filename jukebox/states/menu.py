from .. import config
from ..widgets import Button, draw_text
from .base import State


class MenuState(State):
    def on_enter(self):
        app = self.app
        self.buttons = [
            Button((20, 160, 190, 160), "Jokes", lambda: app.change_state("jokes"), app.font_large),
            Button((225, 160, 190, 160), "Music", lambda: app.change_state("music"), app.font_large),
            Button((430, 160, 190, 160), "Camera", lambda: app.change_state("camera"), app.font_large),
        ]

    def handle_event(self, event):
        for button in self.buttons:
            button.handle_event(event)

    def draw(self, surface):
        self.draw_background(surface, "Christmas Jukebox")
        for button in self.buttons:
            button.draw(surface)
        draw_text(surface, "Merry Christmas!", self.app.font_medium, config.SCREEN_W // 2, 360,
                  config.SCREEN_W - 40, config.TITLE_COLOR)
