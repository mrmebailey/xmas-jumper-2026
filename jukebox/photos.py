import pygame

from . import config


def list_photos():
    """Saved photos, newest first (the timestamped names sort by date)."""
    return sorted(config.PHOTOS_DIR.glob("photo_*.jpg"), reverse=True)


def load_for_screen(path):
    """Load a photo turned the right way up and sized for the screen."""
    image = pygame.image.load(str(path))
    w, h = image.get_size()
    # Scale to fit (or, with PHOTO_PREVIEW_FILL, to cover and crop) the screen
    # using the turned-round size, but scale before rotating: turning the
    # full-resolution photo is much slower on the Pi Zero.
    fit_w, fit_h = (h, w) if config.PHOTO_ROTATION % 180 else (w, h)
    pick = max if config.PHOTO_PREVIEW_FILL else min
    scale = pick(config.SCREEN_W / fit_w, config.SCREEN_H / fit_h)
    image = pygame.transform.scale(image, (int(w * scale), int(h * scale)))
    return pygame.transform.rotate(image, config.PHOTO_ROTATION)
