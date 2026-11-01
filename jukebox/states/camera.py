from .. import config
from ..widgets import Button
from .base import State


class CameraState(State):
    def on_enter(self):
        app = self.app
        self.status = "Tap the button to take a photo"
        self.buttons = [
            Button((170, 380, 300, 60), "Take Photo", self._take_photo, app.font_medium),
            Button((500, 380, 100, 60), "Back", lambda: app.change_state("menu"), app.font_medium),
        ]

    def _take_photo(self):
        path, error = self.app.camera.take_photo()
        self.status = error if error else f"Saved {path.name}"

    def handle_event(self, event):
        for button in self.buttons:
            button.handle_event(event)

    def draw(self, surface):
        surface.fill(config.BG_COLOR)
        title = self.app.font_large.render("Spy Cam", True, config.TEXT_COLOR)
        surface.blit(title, title.get_rect(center=(config.SCREEN_W // 2, 100)))
        status = self.app.font_small.render(self.status, True, config.TEXT_COLOR)
        surface.blit(status, status.get_rect(center=(config.SCREEN_W // 2, 200)))
        for button in self.buttons:
            button.draw(surface)
