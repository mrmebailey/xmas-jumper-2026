import random

import pygame

from .. import config
from ..games import sprites
from ..photos import load_for_screen
from ..widgets import Button, draw_text, render_text
from .base import State

SCAN_MS = 3000
PHOTO_BOX = (270, 330)
SCAN_MESSAGES = ["Checking Santa's list...", "Counting good deeds...", "Asking the elves...", "Checking it twice..."]
# (verdict, colour, weight, things to say)
VERDICTS = [
    ("NICE!", (90, 220, 120), 45, [
        "Santa's sleigh will definitely be stopping at yours.",
        "The elves give you a big thumbs up!",
        "Mince pies all round!",
        "Keep it up and there might be an extra present.",
    ]),
    ("VERY NICE!", sprites.GOLD, 25, [
        "Top of Santa's list this year!",
        "Rudolph wants your autograph!",
        "The elves are building something special for you.",
    ]),
    ("NAUGHTY!", (255, 90, 90), 30, [
        "Uh oh... it's looking like a lump of coal.",
        "The elves saw what you did...",
        "Better be extra good from now until Christmas!",
        "Santa is going to have a word with you.",
    ]),
]


class NaughtyState(State):
    """Naughty or Nice scanner: a pretend scan with the spy cam, then a photo
    of you with Santa's verdict, read out loud. The photo is saved with the
    others, so it shows up in Photos."""

    def on_enter(self):
        app = self.app
        self.scan_button = Button((170, 385, 300, 75), "Scan me!", self._scan, app.font_medium)
        self.again_button = Button((170, 385, 300, 75), "Again", self._reset, app.font_medium)
        self.back_button = Button((500, 385, 120, 75), "Back", lambda: app.change_state("menu"), app.font_medium)
        self._reset()

    def _reset(self):
        self.phase = "ready"  # ready -> scanning -> result
        self.scan_until = None
        self.photo = None
        self.verdict = None
        self.error = None

    @property
    def full_speed(self):
        return self.phase == "scanning"

    def _scan(self):
        self.phase = "scanning"
        self.scan_until = pygame.time.get_ticks() + SCAN_MS

    def _buttons(self):
        if self.phase == "scanning":
            return []
        main = self.scan_button if self.phase == "ready" else self.again_button
        return [main, self.back_button]

    def on_exit(self):
        self.app.camera.cancel()

    def handle_event(self, event):
        for button in self._buttons():
            button.handle_event(event)

    def update(self):
        if self.phase != "result":
            # Start the camera as soon as the screen opens; it takes longer to
            # start than the scan does.
            self.app.camera.keep_warm()
        if self.phase == "scanning" and pygame.time.get_ticks() >= self.scan_until:
            self._take_photo()

    def _take_photo(self):
        # Taking the photo holds up the screen briefly, so say so first.
        self.draw(self.app.screen, checking=True)
        pygame.display.flip()
        path, error = self.app.camera.capture()
        word, color, _, lines = random.choices(VERDICTS, weights=[v[2] for v in VERDICTS])[0]
        self.verdict = (word, color, random.choice(lines))
        if error:
            self.error = error
        else:
            self.photo = load_for_screen(path, PHOTO_BOX)
        self.phase = "result"
        self.app.audio.speak(f"{word.rstrip('!').lower()}. {self.verdict[2]}")

    def draw(self, surface, checking=False):
        if self.phase == "result":
            self._draw_result(surface)
        elif self.phase == "scanning":
            self._draw_scanning(surface, checking)
        else:
            self.draw_background(surface, "Naughty or Nice?")
            y = draw_text(surface, "Santa's scanner is ready.", self.app.font_medium, config.SCREEN_W // 2, 120,
                          config.SCREEN_W - 60)
            draw_text(surface, "Stand in front of the camera and press the button to find out which list "
                      "you're on!", self.app.font_small, config.SCREEN_W // 2, y + 20, config.SCREEN_W - 80)
            surface.blit(sprites.get("star", 70), (40, 300))
            surface.blit(sprites.get("coal", 70), (530, 300))
        for button in self._buttons():
            button.draw(surface)

    def _draw_scanning(self, surface, checking):
        self.draw_background(surface, "Scanning...")
        now = pygame.time.get_ticks()
        left = max(0, self.scan_until - now)
        done = 1 - left / SCAN_MS
        frame = pygame.Rect(170, 80, 300, 230)
        pygame.draw.rect(surface, (90, 220, 120), frame, width=3, border_radius=10)
        # A scan line sweeping up and down the frame.
        sweep = (now % 1000) / 1000
        sweep = sweep * 2 if sweep < 0.5 else 2 - sweep * 2
        y = frame.y + 6 + int((frame.height - 12) * sweep)
        pygame.draw.line(surface, (90, 220, 120), (frame.x + 6, y), (frame.right - 6, y), 4)
        message = "Checking it twice..." if checking else SCAN_MESSAGES[min(len(SCAN_MESSAGES) - 1,
                                                                            int(done * len(SCAN_MESSAGES)))]
        text = render_text(self.app.font_medium, message, config.TITLE_COLOR)
        surface.blit(text, text.get_rect(center=(config.SCREEN_W // 2, 345)))
        bar = pygame.Rect(120, 390, 400, 26)
        pygame.draw.rect(surface, config.BUTTON_COLOR, bar, border_radius=8)
        pygame.draw.rect(surface, (90, 220, 120), (bar.x, bar.y, int(bar.width * done), bar.height), border_radius=8)

    def _draw_result(self, surface):
        self.draw_background(surface)
        word, color, line = self.verdict
        box = pygame.Rect(25, 40, *PHOTO_BOX)
        if self.photo is not None:
            surface.blit(self.photo, self.photo.get_rect(center=box.center))
            pygame.draw.rect(surface, color, self.photo.get_rect(center=box.center), width=4)
        else:
            pygame.draw.rect(surface, config.BUTTON_COLOR, box, border_radius=10)
            draw_text(surface, self.error or "No photo", self.app.font_tiny, box.centerx, box.y + 120,
                      box.width - 20)
        text_x = (box.right + config.SCREEN_W) // 2
        y = draw_text(surface, word, self.app.font_title, text_x, 90, 320, color)
        draw_text(surface, line, self.app.font_medium, text_x, y + 20, 320)
