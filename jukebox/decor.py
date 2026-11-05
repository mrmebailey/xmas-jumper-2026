import random

import pygame

from . import config


class Snow:
    """Flakes falling over the background, moved by elapsed time so the
    speed stays the same however slow the frame rate gets on the Pi."""

    def __init__(self, count=config.SNOWFLAKES):
        self.flakes = [self._new_flake(random.uniform(0, config.SCREEN_H)) for _ in range(count)]
        self._last_ticks = pygame.time.get_ticks()

    @staticmethod
    def _new_flake(y):
        return [random.uniform(0, config.SCREEN_W), y, random.uniform(25, 60), random.randint(1, 3)]

    def update(self):
        now = pygame.time.get_ticks()
        dt = (now - self._last_ticks) / 1000
        self._last_ticks = now
        for i, flake in enumerate(self.flakes):
            flake[1] += flake[2] * dt
            if flake[1] > config.SCREEN_H:
                self.flakes[i] = self._new_flake(-5)

    def draw(self, surface):
        for x, y, _, radius in self.flakes:
            pygame.draw.circle(surface, config.SNOW_COLOR, (int(x), int(y)), radius)


def draw_lights(surface):
    """A string of fairy lights along the top edge that twinkle once a second."""
    phase = pygame.time.get_ticks() // 1000
    spacing = 40
    pygame.draw.line(surface, config.LIGHTS_WIRE_COLOR, (0, 10), (config.SCREEN_W, 10), 2)
    for i, x in enumerate(range(spacing // 2, config.SCREEN_W, spacing)):
        color = config.LIGHT_COLORS[(i + phase) % len(config.LIGHT_COLORS)]
        pygame.draw.circle(surface, color, (x, 16), 7)
