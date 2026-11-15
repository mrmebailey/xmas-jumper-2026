import math

import pygame

from . import config


# Rendering text is one of the slowest things drawn each frame on the Pi Zero,
# and the same few strings are drawn every frame, so keep the results.
_TEXT_CACHE_LIMIT = 200
_rendered = {}
_wrapped = {}
_fitted = {}


def render_text(font, text, color=config.TEXT_COLOR):
    """font.render(text, True, color), remembered between frames."""
    key = (font, text, color)
    surface = _rendered.get(key)
    if surface is None:
        if len(_rendered) >= _TEXT_CACHE_LIMIT:
            _rendered.clear()
        surface = _rendered[key] = font.render(text, True, color)
    return surface


def fit_text(font, text, max_width, color=config.TEXT_COLOR):
    """Render one line, cut short with "..." if it's wider than max_width."""
    key = (font, text, max_width)
    fitted = _fitted.get(key)
    if fitted is None:
        fitted = text
        if font.size(text)[0] > max_width:
            while fitted and font.size(fitted + "...")[0] > max_width:
                fitted = fitted[:-1]
            fitted = fitted.rstrip() + "..."
        if len(_fitted) >= _TEXT_CACHE_LIMIT:
            _fitted.clear()
        _fitted[key] = fitted
    return render_text(font, fitted, color)


def wrap_lines(text, font, max_width):
    """Split text into lines that each render no wider than max_width."""
    key = (font, text, max_width)
    lines = _wrapped.get(key)
    if lines is None:
        if len(_wrapped) >= _TEXT_CACHE_LIMIT:
            _wrapped.clear()
        lines = _wrapped[key] = _wrap_lines(text, font, max_width)
    return lines


def _wrap_lines(text, font, max_width):
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
        rendered = render_text(font, line, color)
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


def has_pending_callbacks():
    return bool(_pending)


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
        # A label can be split over lines with "\n".
        lines = self.label.split("\n")
        line_h = self.font.get_linesize()
        top = rect.centery - line_h * len(lines) // 2
        for i, line in enumerate(lines):
            text = render_text(self.font, line)
            surface.blit(text, text.get_rect(center=(rect.centerx, top + line_h * i + line_h // 2)))


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
