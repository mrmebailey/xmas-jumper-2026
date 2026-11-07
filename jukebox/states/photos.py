import pygame

from .. import config
from ..photos import list_photos, load_for_screen
from ..widgets import Button, draw_text
from .base import State

SWIPE_PX = 80


class PhotosState(State):
    """Browse saved photos newest first: Prev/Next or swipe, and delete with a
    second "Sure?" tap. The photo sits in the middle with the buttons in the
    bands either side of it."""

    def on_enter(self):
        app = self.app
        self.photos = list_photos()
        self.index = 0
        self.image = None
        self.confirm_until = None
        self._swipe_start = None
        self.delete_button = Button((510, 390, 120, 70), "Delete", self._delete, app.font_small)
        self.buttons = [
            Button((10, 170, 120, 140), "Prev", lambda: self._step(-1), app.font_medium),
            Button((510, 170, 120, 140), "Next", lambda: self._step(1), app.font_medium),
            Button((10, 390, 120, 70), "Back", lambda: app.change_state("menu"), app.font_small),
            self.delete_button,
        ]
        self._load()

    def _load(self):
        self.image = load_for_screen(self.photos[self.index]) if self.photos else None

    def _step(self, delta):
        if len(self.photos) > 1:
            self.index = (self.index + delta) % len(self.photos)
            self._reset_confirm()
            self._load()

    def _delete(self):
        if not self.photos:
            return
        if self.confirm_until is None:
            self.confirm_until = pygame.time.get_ticks() + config.DELETE_CONFIRM_MS
            self.delete_button.label = "Sure?"
            return
        self.photos.pop(self.index).unlink(missing_ok=True)
        self.index = min(self.index, len(self.photos) - 1) if self.photos else 0
        self._reset_confirm()
        self._load()

    def _reset_confirm(self):
        self.confirm_until = None
        self.delete_button.label = "Delete"

    def handle_event(self, event):
        for button in self.buttons:
            button.handle_event(event)
        # Swipe left/right across the photo (not starting on a button) to change photo.
        if event.type == pygame.MOUSEBUTTONDOWN:
            on_button = any(b.rect.collidepoint(event.pos) for b in self.buttons)
            self._swipe_start = None if on_button else event.pos[0]
        elif event.type == pygame.MOUSEBUTTONUP and self._swipe_start is not None:
            dx = event.pos[0] - self._swipe_start
            self._swipe_start = None
            if abs(dx) >= SWIPE_PX:
                self._step(-1 if dx > 0 else 1)

    def update(self):
        if self.confirm_until is not None and pygame.time.get_ticks() >= self.confirm_until:
            self._reset_confirm()

    def draw(self, surface):
        if self.image is None:
            self.draw_background(surface, "Photo Album")
            y = draw_text(surface, "No photos yet!", self.app.font_medium, config.SCREEN_W // 2, 170,
                          config.SCREEN_W - 60)
            draw_text(surface, "Take some with the Spy Cam.", self.app.font_small, config.SCREEN_W // 2, y + 10,
                      config.SCREEN_W - 60)
            self.buttons[2].draw(surface)
            return
        self.draw_background(surface)
        surface.blit(self.image, self.image.get_rect(center=(config.SCREEN_W // 2, config.SCREEN_H // 2)))
        counter = self.app.font_small.render(f"{self.index + 1}/{len(self.photos)}", True, config.TEXT_COLOR)
        surface.blit(counter, counter.get_rect(center=(70, 80)))
        for button in self.buttons:
            button.draw(surface)
        if self.confirm_until is not None:
            # Make the armed delete stand out from the other buttons.
            pygame.draw.rect(surface, config.TITLE_COLOR, self.delete_button.rect.inflate(8, 8), width=5,
                             border_radius=14)
