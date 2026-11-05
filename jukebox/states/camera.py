import pygame

from .. import config
from ..widgets import Button
from .base import State


class CameraState(State):
    def on_enter(self):
        app = self.app
        self.status = "Tap the button to take a photo"
        self.preview = None
        self.preview_until = 0
        self.buttons = [
            Button((170, 380, 300, 60), "Take Photo", self._take_photo, app.font_medium),
            Button((500, 380, 100, 60), "Back", lambda: app.change_state("menu"), app.font_medium),
        ]

    def _take_photo(self):
        # Capturing blocks the main loop, so put the message on screen first.
        self.status = "Say cheese!"
        self.draw(self.app.screen)
        pygame.display.flip()

        path, error = self.app.camera.take_photo()
        if error:
            self.status = error
            return
        self.status = f"Saved {path.name}"
        image = pygame.image.load(str(path))
        scale = min(config.SCREEN_W / image.get_width(), config.SCREEN_H / image.get_height())
        size = (int(image.get_width() * scale), int(image.get_height() * scale))
        self.preview = pygame.transform.scale(image, size)
        self.preview_until = pygame.time.get_ticks() + config.PHOTO_PREVIEW_MS

    def handle_event(self, event):
        if self.preview is not None:
            return
        for button in self.buttons:
            button.handle_event(event)

    def update(self):
        if self.preview is not None and pygame.time.get_ticks() >= self.preview_until:
            self.preview = None

    def draw(self, surface):
        surface.fill(config.BG_COLOR)
        if self.preview is not None:
            surface.blit(self.preview, self.preview.get_rect(center=(config.SCREEN_W // 2, config.SCREEN_H // 2)))
            return
        title = self.app.font_large.render("Spy Cam", True, config.TEXT_COLOR)
        surface.blit(title, title.get_rect(center=(config.SCREEN_W // 2, 100)))
        status = self.app.font_small.render(self.status, True, config.TEXT_COLOR)
        surface.blit(status, status.get_rect(center=(config.SCREEN_W // 2, 200)))
        for button in self.buttons:
            button.draw(surface)
