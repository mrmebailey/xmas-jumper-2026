from .. import config
from ..games import sprites
from ..widgets import Button
from .base import State

ICON = 56


class GamesState(State):
    """Pick a game."""

    def on_enter(self):
        app = self.app
        self.buttons = [
            Button((30, 75, 280, 135), "Reindeer\nSnake", lambda: app.change_state("snake"), app.font_large),
            Button((330, 75, 280, 135), "Present\nCatch", lambda: app.change_state("catch"), app.font_large),
            Button((30, 225, 280, 135), "Bauble\nPop", lambda: app.change_state("baubles"), app.font_large),
            Button((330, 225, 280, 135), "Memory\nMatch", lambda: app.change_state("memory"), app.font_large),
            Button((500, 385, 120, 75), "Back", lambda: app.change_state("menu"), app.font_medium),
        ]

    def handle_event(self, event):
        for button in self.buttons:
            button.handle_event(event)

    def draw(self, surface):
        self.draw_background(surface, "Christmas Games")
        for button in self.buttons:
            button.draw(surface)
        for i, icon in enumerate(["reindeer", "present", "bauble", "tree", "snowman"]):
            surface.blit(sprites.get(icon, ICON), (30 + i * 90, 397))
