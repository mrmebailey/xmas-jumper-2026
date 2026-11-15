from .. import config
from ..decor import draw_lights
from ..widgets import draw_text


class State:
    # True while the screen is animating on its own (a game being played), so
    # the main loop keeps drawing at full speed even when nobody touches it.
    full_speed = False

    def __init__(self, app):
        self.app = app

    def on_enter(self):
        pass

    def on_exit(self):
        pass

    def handle_event(self, event):
        pass

    def update(self):
        pass

    def draw(self, surface):
        pass

    def draw_background(self, surface, title=None):
        """Festive backdrop shared by every screen: snow, fairy lights, gold title."""
        surface.fill(config.BG_COLOR)
        self.app.snow.draw(surface)
        draw_lights(surface, twinkle=not self.app.low_power)
        if title:
            draw_text(surface, title, self.app.font_title, config.SCREEN_W // 2, 34, config.SCREEN_W - 40,
                      config.TITLE_COLOR)
