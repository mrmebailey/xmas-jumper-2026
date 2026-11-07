from datetime import datetime

from .. import config
from ..widgets import Button, draw_text
from .base import State


def christmas_countdown(now):
    """Time left until Christmas Day as (headline, subtitle); on the day itself,
    a greeting. Uses the Pi's local clock, so it needs the right time zone."""
    if now.month == 12 and now.day == 25:
        return "Merry Christmas!", "It's Christmas Day!"
    year = now.year if now < datetime(now.year, 12, 25) else now.year + 1
    minutes = int((datetime(year, 12, 25) - now).total_seconds() // 60)
    days, minutes = divmod(minutes, 24 * 60)
    hours, minutes = divmod(minutes, 60)
    parts = [(days, "day"), (hours, "hr"), (minutes, "min")]
    return " ".join(f"{n} {unit}{'' if n == 1 else 's'}" for n, unit in parts), "until Christmas Day"


class MenuState(State):
    def on_enter(self):
        app = self.app
        self.buttons = [
            Button((30, 100, 280, 120), "Jokes", lambda: app.change_state("jokes"), app.font_large),
            Button((330, 100, 280, 120), "Music", lambda: app.change_state("music"), app.font_large),
            Button((30, 235, 280, 120), "Camera", lambda: app.change_state("camera"), app.font_large),
            Button((330, 235, 280, 120), "Photos", lambda: app.change_state("photos"), app.font_large),
        ]

    def handle_event(self, event):
        for button in self.buttons:
            button.handle_event(event)

    def draw(self, surface):
        self.draw_background(surface, "Christmas Jukebox")
        for button in self.buttons:
            button.draw(surface)
        headline, subtitle = christmas_countdown(datetime.now())
        y = draw_text(surface, headline, self.app.font_medium, config.SCREEN_W // 2, 370,
                      config.SCREEN_W - 40, config.TITLE_COLOR)
        draw_text(surface, subtitle, self.app.font_small, config.SCREEN_W // 2, y + 2, config.SCREEN_W - 40)
