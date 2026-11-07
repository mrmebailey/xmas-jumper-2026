import pygame

from .. import config
from ..photos import load_for_screen
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
        # Start the camera now so its startup happens during the countdown.
        self.app.camera.warm_up()

    def _capture(self):
        # Capturing blocks the main loop, so put the message on screen first.
        self.capturing = True
        self.draw(self.app.screen)
        pygame.display.flip()
        self.capturing = False

        path, error = self.app.camera.capture()
        if error:
            self.status = error
            return
        self.status = f"Saved {path.name}"
        self.preview = load_for_screen(path)
        self.preview_until = pygame.time.get_ticks() + config.PHOTO_PREVIEW_MS

    def on_exit(self):
        self.app.camera.cancel()

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
