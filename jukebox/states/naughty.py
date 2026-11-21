import random

import pygame

from .. import config
from ..games import sprites
from .. import naughty_list
from ..jokes_loader import recorded_speech
from ..naughty_theme import theme_photo
from ..naughty_words import (NAUGHTINESS, TOP_OF_LIST, VERDICT_LINES, spoken_naughtiness,
                             spoken_verdict)
from ..photos import load_for_screen
from ..widgets import Button, draw_text, render_text
from .base import State

SCAN_MS = 3000  # how long the scan takes when its messages aren't recorded
SCAN_GAP_MS = 350  # between the spoken scan messages
PHOTO_BOX = (270, 330)
SCAN_MESSAGES = config.NAUGHTY_SCAN_MESSAGES
VERDICT_COLORS = {"NICE!": (90, 220, 120), "VERY NICE!": sprites.GOLD, "NAUGHTY!": (255, 90, 90)}
# (verdict, colour, weight, things to say)
VERDICTS = [(word, VERDICT_COLORS[word], weight, lines) for word, (weight, lines) in VERDICT_LINES.items()]


class NaughtyState(State):
    """Naughty or Nice scanner: a pretend scan with the spy cam, then a photo
    of you with Santa's verdict, read out loud. The photo is saved with the
    others, so it shows up in Photos."""

    def on_enter(self):
        app = self.app
        self.list_button = Button((20, 385, 150, 75), "Naughty\nList", lambda: app.change_state("naughty_list"),
                                  app.font_small)
        self.scan_button = Button((185, 385, 300, 75), "Scan me!", self._scan, app.font_medium)
        self.again_button = Button((185, 385, 300, 75), "Again", self._reset, app.font_medium)
        self.back_button = Button((500, 385, 120, 75), "Back", lambda: app.change_state("menu"), app.font_medium)
        self._reset()

    def _reset(self):
        self.phase = "ready"  # ready -> scanning -> result
        self.scan_until = None
        self.photo = None
        self.verdict = None
        self.naughtiness = None
        self.rank = None
        self.error = None

    @property
    def full_speed(self):
        return self.phase == "scanning"

    def _scan(self):
        self.phase = "scanning"
        self.scan_started = pygame.time.get_ticks()
        self.scan_until = self.scan_started + SCAN_MS
        # Santa reads each message out as it comes up, if they've been
        # recorded (tools/make_santa_voice.py); the scan then lasts as long
        # as he takes. espeak isn't used here: it would lag behind the screen.
        recordings = [recorded_speech(config.JOKE_AUDIO_DIR, text, "scan") for text in SCAN_MESSAGES]
        self.spoken = all(path.exists() for path in recordings)
        if self.spoken:
            self.app.audio.speak_parts([(text, config.SANTA_VOICE, SCAN_GAP_MS if i else 0, path)
                                        for i, (text, path) in enumerate(zip(SCAN_MESSAGES, recordings))])

    def _buttons(self):
        if self.phase == "scanning":
            return []
        main = self.scan_button if self.phase == "ready" else self.again_button
        return [self.list_button, main, self.back_button]

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
        if self.phase == "scanning" and self._scan_done():
            self._take_photo()

    def _scan_done(self):
        now = pygame.time.get_ticks()
        if self.spoken:
            # Until Santa has finished (and at least the usual scan time, in
            # case the sound fails), with a safety limit in case it never ends.
            finished = not self.app.audio.speaking and now >= self.scan_until
            return finished or now >= self.scan_started + 20000
        return now >= self.scan_until

    def _scan_progress(self):
        """(how far through the scan 0-1, which message to show)."""
        now = pygame.time.get_ticks()
        audio = self.app.audio
        if self.spoken and audio.part_starts and audio.speech_ends_at:
            start, end = audio.part_starts[0], audio.speech_ends_at
            done = (now - start) / max(1, end - start)
            shown = sum(1 for i in range(len(SCAN_MESSAGES)) if audio.part_started(i))
            return max(0.0, min(1.0, done)), max(0, shown - 1)
        done = 1 - max(0, self.scan_until - now) / SCAN_MS
        return done, min(len(SCAN_MESSAGES) - 1, int(done * len(SCAN_MESSAGES)))

    def _take_photo(self):
        # Taking the photo holds up the screen briefly, so say so first.
        self.draw(self.app.screen, checking=True)
        pygame.display.flip()
        path, error = self.app.camera.capture()
        word, color, _, lines = random.choices(VERDICTS, weights=[v[2] for v in VERDICTS])[0]
        self.verdict = (word, color, random.choice(lines))
        self.naughtiness = random.randint(*NAUGHTINESS[word])
        top = False
        if error:
            self.error = error
        else:
            # Saved over the plain photo, so Photos shows the themed one.
            theme_photo(path, word, self.verdict[2], self.naughtiness)
            self.photo = load_for_screen(path, PHOTO_BOX)
            if word == "NAUGHTY!":
                naughty_list.add(path, self.naughtiness)
                self.rank = naughty_list.rank_of(path)
                top = self.rank == 1
        self.phase = "result"
        self._say_verdict(word, self.naughtiness, self.verdict[2], top)

    def _say_verdict(self, word, naughtiness, line, top):
        """Santa reads the verdict, in his recorded voice if every bit of it
        has been recorded (tools/make_santa_voice.py), otherwise by espeak."""
        bits = [(spoken_verdict(word), "vword", 0), (spoken_naughtiness(naughtiness), "vpct", 250),
                (line, "vline", 350)]
        if top:
            bits.append((TOP_OF_LIST, "vtop", 350))
        parts = [(text, config.SANTA_VOICE, gap, recorded_speech(config.JOKE_AUDIO_DIR, text, kind))
                 for text, kind, gap in bits]
        if all(part[3].exists() for part in parts):
            self.app.audio.speak_parts(parts)
        else:
            self.app.audio.speak(" ".join(text for text, _, _ in bits))

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
        done, shown = self._scan_progress()
        frame = pygame.Rect(170, 80, 300, 230)
        pygame.draw.rect(surface, (90, 220, 120), frame, width=3, border_radius=10)
        # A scan line sweeping up and down the frame.
        sweep = (now % 1000) / 1000
        sweep = sweep * 2 if sweep < 0.5 else 2 - sweep * 2
        y = frame.y + 6 + int((frame.height - 12) * sweep)
        pygame.draw.line(surface, (90, 220, 120), (frame.x + 6, y), (frame.right - 6, y), 4)
        message = SCAN_MESSAGES[-1] if checking else SCAN_MESSAGES[shown]
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
        y = draw_text(surface, word, self.app.font_title, text_x, 60, 320, color)
        y = draw_text(surface, f"{self.naughtiness}% naughty", self.app.font_small, text_x, y + 4, 320)
        if self.rank is not None:
            rank_text = "Top of the Naughty List!" if self.rank == 1 else f"Number {self.rank} on the Naughty List"
            y = draw_text(surface, rank_text, self.app.font_small, text_x, y + 4, 320, color)
        draw_text(surface, line, self.app.font_medium, text_x, y + 16, 320)
