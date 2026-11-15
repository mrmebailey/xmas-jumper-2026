"""Christmas pictures for the games, drawn with shapes (no image files).

Each is drawn once per size and kept, so games only blit them each frame,
which is all the Pi Zero has time for.
"""
import math

import pygame

RED = (210, 35, 35)
DARK_RED = (140, 20, 20)
GOLD = (240, 200, 70)
GREEN = (30, 140, 60)
DARK_GREEN = (15, 95, 40)
WHITE = (245, 245, 250)
BROWN = (130, 80, 40)
LIGHT_BROWN = (185, 130, 75)
BLACK = (20, 20, 20)
ORANGE = (240, 130, 30)
BLUE = (60, 120, 230)
PURPLE = (150, 70, 200)
COAL = (45, 45, 50)

_cache = {}


def get(name, size, *args):
    """The named picture, size x size pixels, with a transparent background."""
    key = (name, size, args)
    surface = _cache.get(key)
    if surface is None:
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        _DRAW[name](surface, size, *args)
        _cache[key] = surface
    return surface


def _star_points(cx, cy, outer, inner, points=5, turn=-math.pi / 2):
    pts = []
    for i in range(points * 2):
        r = outer if i % 2 == 0 else inner
        a = turn + i * math.pi / points
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def _present(s, n, color=RED):
    m = n // 8
    box = pygame.Rect(m, n // 4, n - 2 * m, n - n // 4 - m)
    pygame.draw.rect(s, color, box, border_radius=max(1, n // 16))
    rib = max(2, n // 8)
    pygame.draw.rect(s, GOLD, (box.centerx - rib // 2, box.y, rib, box.height))
    pygame.draw.rect(s, GOLD, (box.x, box.centery - rib // 2, box.width, rib))
    bow = max(2, n // 7)
    pygame.draw.circle(s, GOLD, (box.centerx - bow, box.y - bow // 3), bow, max(1, n // 20))
    pygame.draw.circle(s, GOLD, (box.centerx + bow, box.y - bow // 3), bow, max(1, n // 20))


def _star(s, n, color=GOLD):
    pygame.draw.polygon(s, color, _star_points(n / 2, n / 2 + n * 0.04, n * 0.48, n * 0.2))


def _tree(s, n):
    trunk_w = n // 6
    pygame.draw.rect(s, BROWN, (n // 2 - trunk_w // 2, n * 0.8, trunk_w, n * 0.2))
    for i, (top, bottom, half) in enumerate(((0.12, 0.45, 0.25), (0.28, 0.65, 0.35), (0.45, 0.85, 0.45))):
        pygame.draw.polygon(s, GREEN if i % 2 == 0 else DARK_GREEN,
                            [(n / 2, n * top), (n / 2 - n * half, n * bottom), (n / 2 + n * half, n * bottom)])
    for x, y, c in ((0.42, 0.42, RED), (0.6, 0.58, GOLD), (0.38, 0.72, BLUE), (0.66, 0.78, RED)):
        pygame.draw.circle(s, c, (n * x, n * y), max(2, n // 18))
    pygame.draw.polygon(s, GOLD, _star_points(n / 2, n * 0.11, n * 0.11, n * 0.045))


def _snowman(s, n):
    pygame.draw.circle(s, WHITE, (n / 2, n * 0.68), n * 0.28)
    pygame.draw.circle(s, WHITE, (n / 2, n * 0.33), n * 0.19)
    pygame.draw.rect(s, BLACK, (n * 0.33, n * 0.1, n * 0.34, n * 0.05))
    pygame.draw.rect(s, BLACK, (n * 0.39, n * 0.0, n * 0.22, n * 0.12))
    for x in (0.43, 0.57):
        pygame.draw.circle(s, BLACK, (n * x, n * 0.3), max(1, n // 28))
    pygame.draw.polygon(s, ORANGE, [(n * 0.5, n * 0.34), (n * 0.66, n * 0.37), (n * 0.5, n * 0.4)])
    pygame.draw.rect(s, RED, (n * 0.32, n * 0.47, n * 0.36, n * 0.06))
    for y in (0.62, 0.72, 0.82):
        pygame.draw.circle(s, BLACK, (n / 2, n * y), max(1, n // 30))


def _bauble(s, n, color=RED):
    r = n * 0.4
    c = (n / 2, n * 0.56)
    pygame.draw.rect(s, GOLD, (n * 0.42, n * 0.06, n * 0.16, n * 0.14))
    pygame.draw.circle(s, color, c, r)
    shade = tuple(max(0, v - 60) for v in color)
    pygame.draw.circle(s, shade, c, r, max(1, n // 20))
    pygame.draw.circle(s, WHITE, (c[0] - r * 0.4, c[1] - r * 0.4), max(2, n // 10))
    pygame.draw.line(s, GOLD, (n * 0.18, c[1]), (n * 0.82, c[1]), max(1, n // 18))


def _candy_cane(s, n):
    w = max(3, n // 7)
    # Walk along the cane (up the stick, then round the hook) dropping dots
    # that alternate red and white in bands, which makes the stripes.
    path = []
    x0, bottom, top = n * 0.38, n * 0.94, n * 0.32
    hook_r = n * 0.2
    steps = 40
    for i in range(steps):
        path.append((x0, bottom - (bottom - top) * i / steps))
    for i in range(steps + 1):
        a = math.pi + math.pi * i / steps
        path.append((x0 + hook_r + hook_r * math.cos(a), top + hook_r * math.sin(a)))
    for i in range(10):
        path.append((x0 + 2 * hook_r, top + n * 0.012 * i))
    for i, (x, y) in enumerate(path):
        pygame.draw.circle(s, RED if (i // 6) % 2 else WHITE, (x, y), w / 2)


def _bell(s, n):
    pygame.draw.polygon(s, GOLD, [(n * 0.5, n * 0.12), (n * 0.72, n * 0.3), (n * 0.82, n * 0.75),
                                  (n * 0.18, n * 0.75), (n * 0.28, n * 0.3)])
    pygame.draw.circle(s, GOLD, (n * 0.5, n * 0.2), n * 0.13)
    pygame.draw.rect(s, (200, 160, 40), (n * 0.14, n * 0.72, n * 0.72, n * 0.08), border_radius=3)
    pygame.draw.circle(s, (200, 160, 40), (n * 0.5, n * 0.86), n * 0.08)
    pygame.draw.circle(s, RED, (n * 0.5, n * 0.1), n * 0.07)


def _coal(s, n):
    pts = [(0.2, 0.45), (0.38, 0.22), (0.66, 0.2), (0.85, 0.42), (0.8, 0.75), (0.52, 0.86), (0.22, 0.72)]
    pygame.draw.polygon(s, COAL, [(n * x, n * y) for x, y in pts])
    pygame.draw.circle(s, (85, 85, 90), (n * 0.42, n * 0.38), max(1, n // 12))


def _heart(s, n, color=RED):
    r = n * 0.25
    pygame.draw.circle(s, color, (n * 0.3, n * 0.36), r)
    pygame.draw.circle(s, color, (n * 0.7, n * 0.36), r)
    pygame.draw.polygon(s, color, [(n * 0.07, n * 0.45), (n * 0.93, n * 0.45), (n * 0.5, n * 0.92)])


def _reindeer(s, n):
    """Rudolph's head, facing right (games turn it to face the way he's going)."""
    pygame.draw.line(s, LIGHT_BROWN, (n * 0.32, n * 0.3), (n * 0.18, n * 0.04), max(2, n // 12))
    pygame.draw.line(s, LIGHT_BROWN, (n * 0.24, n * 0.16), (n * 0.06, n * 0.14), max(2, n // 14))
    pygame.draw.line(s, LIGHT_BROWN, (n * 0.32, n * 0.7), (n * 0.18, n * 0.96), max(2, n // 12))
    pygame.draw.line(s, LIGHT_BROWN, (n * 0.24, n * 0.84), (n * 0.06, n * 0.86), max(2, n // 14))
    pygame.draw.ellipse(s, BROWN, (n * 0.12, n * 0.18, n * 0.7, n * 0.64))
    pygame.draw.circle(s, WHITE, (n * 0.55, n * 0.35), max(2, n // 9))
    pygame.draw.circle(s, WHITE, (n * 0.55, n * 0.65), max(2, n // 9))
    pygame.draw.circle(s, BLACK, (n * 0.58, n * 0.35), max(1, n // 18))
    pygame.draw.circle(s, BLACK, (n * 0.58, n * 0.65), max(1, n // 18))
    pygame.draw.circle(s, RED, (n * 0.84, n * 0.5), n * 0.14)
    pygame.draw.circle(s, (255, 150, 150), (n * 0.8, n * 0.45), max(1, n // 20))


def _reindeer_body(s, n, shade=0):
    color = BROWN if shade == 0 else (115, 70, 35)
    pygame.draw.rect(s, color, (n * 0.08, n * 0.08, n * 0.84, n * 0.84), border_radius=n // 4)
    pygame.draw.rect(s, RED, (n * 0.08, n * 0.42, n * 0.84, n * 0.16))
    pygame.draw.circle(s, GOLD, (n * 0.5, n * 0.5), max(2, n // 9))


def _sack(s, n):
    pygame.draw.ellipse(s, DARK_RED, (n * 0.05, n * 0.3, n * 0.9, n * 0.68))
    pygame.draw.ellipse(s, RED, (n * 0.1, n * 0.33, n * 0.8, n * 0.6))
    pygame.draw.polygon(s, DARK_RED, [(n * 0.3, n * 0.36), (n * 0.7, n * 0.36), (n * 0.62, n * 0.16),
                                      (n * 0.38, n * 0.16)])
    pygame.draw.rect(s, GOLD, (n * 0.33, n * 0.3, n * 0.34, n * 0.07), border_radius=3)
    pygame.draw.ellipse(s, WHITE, (n * 0.2, n * 0.08, n * 0.6, n * 0.14))


def _card_back(s, n):
    pygame.draw.rect(s, RED, (0, 0, n, n), border_radius=n // 8)
    pygame.draw.rect(s, GOLD, (0, 0, n, n), width=max(2, n // 20), border_radius=n // 8)
    pygame.draw.polygon(s, GOLD, _star_points(n / 2, n / 2, n * 0.2, n * 0.08))


_DRAW = {
    "present": _present,
    "star": _star,
    "tree": _tree,
    "snowman": _snowman,
    "bauble": _bauble,
    "candy_cane": _candy_cane,
    "bell": _bell,
    "coal": _coal,
    "heart": _heart,
    "reindeer": _reindeer,
    "reindeer_body": _reindeer_body,
    "sack": _sack,
    "card_back": _card_back,
}
