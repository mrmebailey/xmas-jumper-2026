"""Dress up a Naughty or Nice photo with its verdict and save it over the
original, so the Photos screen shows the themed version.

The camera's photo is stored on its side (the Photos screen turns it by
PHOTO_ROTATION), so it's turned upright to draw on and turned back to save.
"""
import math
import random

import pygame

from . import config
from .games import sprites
from .widgets import draw_text

BORDER = 26
THEMES = {
    "NICE!": {
        "frame": (25, 120, 55), "edge": sprites.GOLD, "banner": (200, 30, 30), "text": sprites.WHITE,
        "lights": [sprites.RED, sprites.GOLD, sprites.BLUE, (90, 220, 120)],
        "corners": [("present", sprites.RED), ("tree",), ("present", sprites.BLUE), ("star",)],
    },
    "VERY NICE!": {
        "frame": (190, 150, 40), "edge": sprites.WHITE, "banner": (150, 20, 20), "text": sprites.GOLD,
        "lights": [sprites.WHITE, sprites.RED, sprites.WHITE, (90, 220, 120)],
        "corners": [("star",), ("star",), ("bell",), ("present", sprites.PURPLE)],
    },
    "NAUGHTY!": {
        "frame": (35, 35, 40), "edge": (200, 40, 40), "banner": (25, 25, 28), "text": (255, 90, 90),
        "lights": [(80, 80, 85), (200, 40, 40)],
        "corners": [("coal",), ("coal",), ("coal",), ("coal",)],
    },
}


def theme_photo(path, verdict, line, naughtiness=None):
    """Draw the verdict's theme onto the photo at path and save it in place.
    Returns False (leaving the plain photo) if anything goes wrong."""
    try:
        raw = pygame.image.load(str(path))
    except pygame.error:
        return False
    photo = pygame.transform.rotate(raw, config.PHOTO_ROTATION).convert() \
        if pygame.display.get_surface() else pygame.transform.rotate(raw, config.PHOTO_ROTATION)
    _decorate(photo, THEMES.get(verdict, THEMES["NICE!"]), verdict, line, naughtiness)
    try:
        pygame.image.save(pygame.transform.rotate(photo, -config.PHOTO_ROTATION), str(path))
    except pygame.error:
        return False
    return True


def _decorate(surface, theme, verdict, line, naughtiness=None):
    w, h = surface.get_size()
    if verdict == "NAUGHTY!":
        # A grubby grey cast for the naughty list.
        shade = pygame.Surface((w, h), pygame.SRCALPHA)
        shade.fill((40, 40, 50, 70))
        surface.blit(shade, (0, 0))

    # Frame with a string of lights running round it.
    pygame.draw.rect(surface, theme["frame"], (0, 0, w, h), width=BORDER)
    pygame.draw.rect(surface, theme["edge"], (BORDER - 4, BORDER - 4, w - 2 * BORDER + 8, h - 2 * BORDER + 8),
                     width=4)
    spacing = 34
    perimeter = [(x, BORDER // 2) for x in range(spacing // 2, w, spacing)]
    perimeter += [(w - BORDER // 2, y) for y in range(spacing // 2, h, spacing)]
    perimeter += [(x, h - BORDER // 2) for x in range(w - spacing // 2, 0, -spacing)]
    perimeter += [(BORDER // 2, y) for y in range(h - spacing // 2, 0, -spacing)]
    for i, (x, y) in enumerate(perimeter):
        pygame.draw.circle(surface, theme["lights"][i % len(theme["lights"])], (x, y), 7)

    # The verdict on a banner across the top.
    title_font = pygame.font.Font(None, max(48, w // 6))
    banner = pygame.Rect(BORDER + 10, BORDER + 12, w - 2 * BORDER - 20, title_font.get_linesize() + 14)
    pygame.draw.rect(surface, theme["banner"], banner, border_radius=14)
    pygame.draw.rect(surface, theme["edge"], banner, width=4, border_radius=14)
    draw_text(surface, verdict, title_font, w // 2, banner.y + 9, banner.width - 20, theme["text"])
    if verdict != "NAUGHTY!":
        for x in (banner.x + 6, banner.right - 34):
            pygame.draw.polygon(surface, sprites.GOLD, _star(x + 14, banner.centery, 14, 6))

    top = banner.bottom
    if naughtiness is not None:
        top = _draw_meter(surface, banner, naughtiness)

    # Santa's comment along the bottom.
    line_font = pygame.font.Font(None, max(28, w // 15))
    lines_h = line_font.get_linesize() * 3
    strip = pygame.Surface((w - 2 * BORDER, lines_h + 16), pygame.SRCALPHA)
    strip.fill((0, 0, 0, 150))
    strip_y = h - BORDER - strip.get_height()
    surface.blit(strip, (BORDER, strip_y))
    draw_text(surface, line, line_font, w // 2, strip_y + 8, w - 2 * BORDER - 70, sprites.WHITE)

    # Pictures in the corners, just inside the frame.
    size = max(48, w // 8)
    spots = [(BORDER + 6, top + 8), (w - BORDER - 6 - size, top + 8),
             (BORDER + 6, strip_y - size - 6), (w - BORDER - 6 - size, strip_y - size - 6)]
    for (x, y), picture in zip(spots, theme["corners"]):
        surface.blit(sprites.get(picture[0], size, *picture[1:]), (x, y))

    if verdict == "NAUGHTY!":
        # A little cloud of coal dust drifting about.
        rng = random.Random(line)
        for _ in range(40):
            x, y = rng.uniform(BORDER, w - BORDER), rng.uniform(top, strip_y)
            pygame.draw.circle(surface, (30, 30, 30), (x, y), rng.choice((2, 3, 4)))


def _draw_meter(surface, banner, naughtiness):
    """A "Naughty-o-meter" bar under the banner, green (nice) to red (naughty)."""
    font = pygame.font.Font(None, max(26, banner.width // 16))
    label = font.render(f"Naughty-o-meter: {naughtiness}%", True, sprites.WHITE)
    bar = pygame.Rect(banner.x + 30, banner.bottom + 10, banner.width - 60, label.get_height() + 12)
    pygame.draw.rect(surface, (20, 20, 20), bar, border_radius=10)
    fill = bar.inflate(-6, -6)
    fill.width = max(fill.height, int(fill.width * naughtiness / 100))
    red = min(255, 60 + naughtiness * 2)
    green = max(40, 220 - naughtiness * 2)
    pygame.draw.rect(surface, (red, green, 50), fill, border_radius=8)
    pygame.draw.rect(surface, sprites.WHITE, bar, width=2, border_radius=10)
    surface.blit(label, label.get_rect(center=bar.center))
    return bar.bottom


def _star(cx, cy, outer, inner):
    pts = []
    for i in range(10):
        r = outer if i % 2 == 0 else inner
        a = -math.pi / 2 + i * math.pi / 5
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts
