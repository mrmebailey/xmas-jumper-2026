import pygame

from .. import config
from ..widgets import Button, draw_text
from .base import State


class CameraState(State):
    def on_enter(self):
        app = self.app
        self.status = "Tap the button to take a photo"
        self.preview = None
        self.preview_until = 0
        self.countdown_until = None
        self.capturing = False
        self.buttons = [
            Button((170, 380, 300, 60), "Take Photo", self._take_photo, app.font_medium),
            Button((500, 380, 100, 60), "Back", lambda: app.change_state("menu"), app.font_medium),
        ]

    def _take_photo(self):
        self.countdown_until = pygame.time.get_ticks() + config.PHOTO_COUNTDOWN_SECONDS * 1000

    def _capture(self):
        # Capturing blocks the main loop, so put the message on screen first.
        self.capturing = True
        self.draw(self.app.screen)
        pygame.display.flip()
        self.capturing = False

        path, error = self.app.camera.take_photo()
        if error:
            self.status = error
            return
        self.status = f"Saved {path.name}"
        image = pygame.image.load(str(path))
        w, h = image.get_size()
        # Scale to cover the screen (the overflow is cropped when centred) using the
        # turned-round size, but scale before rotating: turning the full-resolution
        # photo is much slower on the Pi Zero.
        fit_w, fit_h = (h, w) if config.PHOTO_ROTATION % 180 else (w, h)
        scale = max(config.SCREEN_W / fit_w, config.SCREEN_H / fit_h)
        image = pygame.transform.scale(image, (int(w * scale), int(h * scale)))
        self.preview = pygame.transform.rotate(image, config.PHOTO_ROTATION)
        self.preview_until = pygame.time.get_ticks() + config.PHOTO_PREVIEW_MS

    def handle_event(self, event):
        if self.preview is not None or self.countdown_until is not None:
            return
        for button in self.buttons:
            button.handle_event(event)

    def update(self):
        if self.countdown_until is not None and pygame.time.get_ticks() >= self.countdown_until:
            self.countdown_until = None
            self._capture()
        if self.preview is not None and pygame.time.get_ticks() >= self.preview_until:
            self.preview = None

    def draw(self, surface):
        if self.preview is not None:
            self.draw_background(surface)
            surface.blit(self.preview, self.preview.get_rect(center=(config.SCREEN_W // 2, config.SCREEN_H // 2)))
            return
        if self.capturing:
            self._draw_big(surface, "Smile!", self.app.font_title)
            return
        if self.countdown_until is not None:
            seconds_left = -(-(self.countdown_until - pygame.time.get_ticks()) // 1000)
            self._draw_big(surface, str(max(1, seconds_left)), self.app.font_countdown)
            return
        self.draw_background(surface, "Santa's Spy Cam")
        draw_text(surface, self.status, self.app.font_medium, config.SCREEN_W // 2, 180, config.SCREEN_W - 60)
        for button in self.buttons:
            button.draw(surface)

    def _draw_big(self, surface, text, font):
        self.draw_background(surface)
        rendered = font.render(text, True, config.TITLE_COLOR)
        surface.blit(rendered, rendered.get_rect(center=(config.SCREEN_W // 2, config.SCREEN_H // 2)))
