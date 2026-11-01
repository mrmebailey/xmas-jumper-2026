import pygame

from . import config


class Button:
    def __init__(self, rect, label, callback, font):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.callback = callback
        self.font = font
        self._pressed = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos):
            self._pressed = True
        elif event.type == pygame.MOUSEBUTTONUP:
            if self._pressed and self.rect.collidepoint(event.pos):
                self.callback()
            self._pressed = False

    def draw(self, surface):
        color = config.BUTTON_ACTIVE_COLOR if self._pressed else config.BUTTON_COLOR
        pygame.draw.rect(surface, color, self.rect, border_radius=12)
        text = self.font.render(self.label, True, config.TEXT_COLOR)
        surface.blit(text, text.get_rect(center=self.rect.center))


class Slider:
    def __init__(self, rect, value, on_change):
        self.rect = pygame.Rect(rect)
        self.value = value
        self.on_change = on_change
        self._dragging = False

    def _value_from_pos(self, x):
        pct = (x - self.rect.x) / self.rect.width * 100
        return max(0, min(100, pct))

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos):
            self._dragging = True
            self.value = self._value_from_pos(event.pos[0])
            self.on_change(self.value)
        elif event.type == pygame.MOUSEBUTTONUP:
            self._dragging = False
        elif event.type == pygame.MOUSEMOTION and self._dragging:
            self.value = self._value_from_pos(event.pos[0])
            self.on_change(self.value)

    def draw(self, surface):
        pygame.draw.rect(surface, config.BUTTON_COLOR, self.rect, border_radius=6)
        fill_w = int(self.rect.width * self.value / 100)
        fill_rect = pygame.Rect(self.rect.x, self.rect.y, fill_w, self.rect.height)
        pygame.draw.rect(surface, config.ACCENT_COLOR, fill_rect, border_radius=6)
        handle_x = self.rect.x + fill_w
        pygame.draw.circle(surface, config.TEXT_COLOR, (handle_x, self.rect.centery), self.rect.height)
