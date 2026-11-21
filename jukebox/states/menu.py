import subprocess
from datetime import datetime

import pygame

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
        go = app.change_state
        cells = [("Jokes", "jokes"), ("Music", "music"), ("Games", "games"),
                 ("Camera", "camera"), ("Photos", "photos"), ("Naughty\nor Nice", "naughty")]
        self.buttons = []
        for i, (label, state) in enumerate(cells):
            x, y = 20 + (i % 3) * 205, 85 + (i // 3) * 140
            self.buttons.append(Button((x, y, 190, 125), label, lambda s=state: go(s), app.font_large))
        # Small to look at, but it takes touches right out to the screen's corner:
        # 50px is only ~6mm on this screen, and the panel's edges are the least accurate.
        self.off_button = Button((535, 405, 95, 60), "Off", self._off, app.font_small,
                                 touch_rect=(515, 395, config.SCREEN_W - 515, config.SCREEN_H - 395))
        self.buttons.append(self.off_button)
        # The same, mirrored into the bottom-left corner.
        self.buttons.append(Button((10, 405, 95, 60), "Info", lambda: go("sysinfo"), app.font_small,
                                   touch_rect=(0, 395, 125, config.SCREEN_H - 395)))
        self.confirm_until = None
        self.status = None

    def _off(self):
        # Needs a second tap, so a knock against the jumper can't switch it off.
        if self.confirm_until is None:
            self.confirm_until = pygame.time.get_ticks() + config.DELETE_CONFIRM_MS
            self.off_button.label = "Sure?"
            return
        self._reset_confirm()
        self.app.audio.stop()
        self._show_message("Shutting down...", "Wait for the green light to stop before unplugging.")
        errors = []
        for cmd in config.SHUTDOWN_CMDS:
            try:
                result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=15)
            except (OSError, subprocess.TimeoutExpired) as e:
                errors.append(f"{' '.join(cmd)}: {e}")
                continue
            if result.returncode == 0:
                return
            errors.append(f"{' '.join(cmd)}: exit {result.returncode}: "
                          f"{result.stderr.decode(errors='replace').strip()}")
        try:
            with open(config.SHUTDOWN_LOG, "a") as f:
                f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S}\n" + "\n".join(errors) + "\n")
        except OSError:
            pass
        self.status = f"Couldn't shut down: {errors[0][:120] if errors else 'no command'}"

    def _show_message(self, headline, detail):
        surface = self.app.screen
        self.draw_background(surface, "Goodnight!")
        y = draw_text(surface, headline, self.app.font_large, config.SCREEN_W // 2, 170, config.SCREEN_W - 60)
        draw_text(surface, detail, self.app.font_small, config.SCREEN_W // 2, y + 20, config.SCREEN_W - 80,
                  config.TITLE_COLOR)
        pygame.display.flip()

    def _reset_confirm(self):
        self.confirm_until = None
        self.off_button.label = "Off"

    def handle_event(self, event):
        for button in self.buttons:
            button.handle_event(event)

    def update(self):
        if self.confirm_until is not None and pygame.time.get_ticks() >= self.confirm_until:
            self._reset_confirm()

    def draw(self, surface):
        self.draw_background(surface, "Christmas Jukebox")
        for button in self.buttons:
            button.draw(surface)
        headline, subtitle = christmas_countdown(datetime.now())
        y = draw_text(surface, headline, self.app.font_medium, config.SCREEN_W // 2, 370,
                      config.SCREEN_W - 40, config.TITLE_COLOR)
        draw_text(surface, subtitle, self.app.font_small, config.SCREEN_W // 2, y + 2, config.SCREEN_W - 40)
        if self.confirm_until is not None:
            # Make the armed button stand out, like Delete in Photos.
            pygame.draw.rect(surface, config.TITLE_COLOR, self.off_button.rect.inflate(8, 8), width=4,
                             border_radius=14)
        if self.status:
            draw_text(surface, self.status, self.app.font_tiny, 320, 428, 400, (255, 120, 120))
