import os
import sys
import time

import pygame

from . import config
from .audio import AudioManager
from .camera import CameraManager
from .decor import Snow
from .jokes_loader import parse_jokes
from .music_loader import load_playlist
from .states.camera import CameraState
from .states.jokes import JokesState
from .states.menu import MenuState
from .states.music import MusicState


# Set JUKEBOX_PROFILE=1 to log input arrival and slow frames to stderr.
PROFILE = os.environ.get("JUKEBOX_PROFILE") == "1"
SLOW_FRAME_MS = 100
_TOUCH_EVENTS = {pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.FINGERDOWN, pygame.FINGERUP}


def _log(msg):
    print(f"[{time.monotonic():10.3f}] {msg}", file=sys.stderr, flush=True)


class App:
    def __init__(self):
        # SDL's accelerated window framebuffer stalls ~5s per flip on the Pi Zero
        # touchscreen; the plain X11 framebuffer flips in ~100ms.
        os.environ.setdefault("SDL_FRAMEBUFFER_ACCELERATION", "0")
        pygame.init()
        if PROFILE and pygame.display.get_init():
            _log(f"SDL video driver: {pygame.display.get_driver()}")
        self.screen = pygame.display.set_mode((config.SCREEN_W, config.SCREEN_H), pygame.FULLSCREEN)
        pygame.display.set_caption("Christmas Jukebox")
        pygame.mouse.set_visible(False)
        self.clock = pygame.time.Clock()

        self.font_countdown = pygame.font.Font(None, config.FONT_SIZE_COUNTDOWN)
        self.font_title = pygame.font.Font(None, config.FONT_SIZE_TITLE)
        self.font_large = pygame.font.Font(None, config.FONT_SIZE_LARGE)
        self.font_medium = pygame.font.Font(None, config.FONT_SIZE_MEDIUM)
        self.font_small = pygame.font.Font(None, config.FONT_SIZE_SMALL)

        self.jokes = parse_jokes(config.JOKES_FILE)
        playlist = load_playlist(config.MUSIC_DIR)
        self.audio = AudioManager(playlist)
        self.audio_volume = 70
        self.audio.set_volume(self.audio_volume)
        self.camera = CameraManager()
        self.snow = Snow()

        self.states = {
            "menu": MenuState(self),
            "jokes": JokesState(self),
            "music": MusicState(self),
            "camera": CameraState(self),
        }
        self.current_state = None
        self.change_state("menu")
        self.running = True
        if PROFILE:
            _log(f"display info: {pygame.display.Info()}")

    def change_state(self, name):
        if self.current_state is not None:
            self.current_state.on_exit()
        self.current_state = self.states[name]
        self.current_state.on_enter()

    def run(self):
        while self.running:
            t0 = time.monotonic()
            events = pygame.event.get()
            t1 = time.monotonic()
            for event in events:
                if PROFILE and event.type in _TOUCH_EVENTS:
                    # SDL timestamps are ms since SDL init; compare against
                    # pygame.time.get_ticks() to see how long it sat in the queue.
                    queued = pygame.time.get_ticks() - getattr(event, "timestamp", pygame.time.get_ticks())
                    _log(f"{pygame.event.event_name(event.type)} {getattr(event, 'pos', '')} queued={queued}ms")
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.running = False
                else:
                    self.current_state.handle_event(event)
            t2 = time.monotonic()
            self.snow.update()
            self.current_state.update()
            self.current_state.draw(self.screen)
            t3 = time.monotonic()
            pygame.display.flip()
            t4 = time.monotonic()
            if PROFILE and (t4 - t0) * 1000 > SLOW_FRAME_MS:
                _log(
                    f"slow frame {(t4 - t0) * 1000:.0f}ms: get={(t1 - t0) * 1000:.0f} "
                    f"handle={(t2 - t1) * 1000:.0f} ({len(events)} events) "
                    f"draw={(t3 - t2) * 1000:.0f} flip={(t4 - t3) * 1000:.0f}"
                )
            self.clock.tick(config.FPS)
        pygame.quit()


def main():
    App().run()


if __name__ == "__main__":
    sys.exit(main())
