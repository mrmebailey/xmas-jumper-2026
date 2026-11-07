import math

import pygame

from . import config


def wrap_lines(text, font, max_width):
    """Split text into lines that each render no wider than max_width."""
    lines, line = [], ""
    for word in text.split():
        candidate = f"{line} {word}".strip()
        if line and font.size(candidate)[0] > max_width:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    return lines


def draw_text(surface, text, font, center_x, top, max_width, color=config.TEXT_COLOR):
    """Draw text wrapped and centred, returning the y just below the last line."""
    y = top
    for line in wrap_lines(text, font, max_width):
        rendered = font.render(line, True, color)
        surface.blit(rendered, rendered.get_rect(midtop=(center_x, y)))
        y += font.get_linesize()
    return y


# Button callbacks waiting for their bounce to play; see run_pending_callbacks().
_pending = []


def run_pending_callbacks():
    """Fire button callbacks whose delay has passed. Called once per frame."""
    now = pygame.time.get_ticks()
    due = [cb for fire_at, cb in _pending if fire_at <= now]
    _pending[:] = [(fire_at, cb) for fire_at, cb in _pending if fire_at > now]
    for callback in due:
        callback()


def clear_pending_callbacks():
    _pending.clear()


class Button:
    """Squashes while held and springs back with a bounce when released. The
    callback is held back by BUTTON_FIRE_DELAY_MS so the bounce is seen
    before the screen changes."""

    def __init__(self, rect, label, callback, font):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.callback = callback
        self.font = font
        self._pressed = False
        self._released_at = None

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos):
            self._pressed = True
        elif event.type == pygame.MOUSEBUTTONUP:
            if self._pressed and self.rect.collidepoint(event.pos):
                self._released_at = pygame.time.get_ticks()
                _pending.append((self._released_at + config.BUTTON_FIRE_DELAY_MS, self.callback))
            self._pressed = False

    def _scale(self):
        if self._pressed:
            return config.BUTTON_SQUASH
        if self._released_at is None:
            return 1.0
        t = (pygame.time.get_ticks() - self._released_at) / config.BUTTON_BOUNCE_MS
        if t >= 1:
            self._released_at = None
            return 1.0
        # Damped spring from the squashed size: overshoots, dips, then settles at 1.
        return 1 - (1 - config.BUTTON_SQUASH) * math.cos(3 * math.pi * t) * (1 - t)

    def draw(self, surface):
        scale = self._scale()
        lit = self._pressed or self._released_at is not None
        rect = self.rect.inflate(int(self.rect.width * (scale - 1)), int(self.rect.height * (scale - 1)))
        color = config.BUTTON_ACTIVE_COLOR if lit else config.BUTTON_COLOR
        pygame.draw.rect(surface, color, rect, border_radius=12)
        pygame.draw.rect(surface, config.BUTTON_BORDER_COLOR, rect, width=3, border_radius=12)
        text = self.font.render(self.label, True, config.TEXT_COLOR)
        surface.blit(text, text.get_rect(center=rect.center))


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
