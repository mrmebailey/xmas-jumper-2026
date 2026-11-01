from .. import config
from ..widgets import Button
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
        surface.fill(config.BG_COLOR)
        title = self.app.font_large.render("Christmas Jukebox", True, config.TEXT_COLOR)
        surface.blit(title, title.get_rect(center=(config.SCREEN_W // 2, 70)))
        for button in self.buttons:
            button.draw(surface)
