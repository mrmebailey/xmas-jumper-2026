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
from .widgets import clear_pending_callbacks, has_pending_callbacks, run_pending_callbacks
from .states.camera import CameraState
from .states.photos import PhotosState
from .states.jokes import JokesState
from .states.menu import MenuState
from .states.music import MusicState
from .states.songs import SongsState


# Set JUKEBOX_PROFILE=1 to log input arrival and slow frames to stderr.
PROFILE = os.environ.get("JUKEBOX_PROFILE") == "1"
SLOW_FRAME_MS = 100
_TOUCH_EVENTS = {pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.FINGERDOWN, pygame.FINGERUP}
_INPUT_EVENTS = _TOUCH_EVENTS | {pygame.MOUSEMOTION, pygame.KEYDOWN}


def _log(msg):
    print(f"[{time.monotonic():10.3f}] {msg}", file=sys.stderr, flush=True)


class App:
    def __init__(self):
        # SDL's accelerated window framebuffer stalls ~5s per flip on the Pi Zero
        # touchscreen; the plain X11 framebuffer flips in ~100ms.
        os.environ.setdefault("SDL_FRAMEBUFFER_ACCELERATION", "0")
        # Talk to PipeWire directly rather than through its PulseAudio layer
        # (pipewire-pulse), which was costing ~20% CPU; fall back if unavailable.
        os.environ.setdefault("SDL_AUDIODRIVER", "pipewire,pulseaudio,alsa")
        # Must come before pygame.init(), which otherwise starts the mixer with defaults.
        pygame.mixer.pre_init(buffer=config.AUDIO_BUFFER)
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
        self.font_tiny = pygame.font.Font(None, config.FONT_SIZE_TINY)

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
            "songs": SongsState(self),
            "camera": CameraState(self),
            "photos": PhotosState(self),
        }
        self.current_state = None
        self.change_state("menu")
        self.running = True
        self.low_power = False
        self._last_input = 0
        self._last_frame = None  # what's on screen, while in low power
        if PROFILE:
            _log(f"display info: {pygame.display.Info()}")

    def _low_power(self):
        """True while audio is playing and the screen is left alone."""
        if not (self.audio.music_active or self.audio.speaking):
            return False
        if has_pending_callbacks():
            return False
        return pygame.time.get_ticks() - self._last_input > config.LOW_POWER_AFTER_INPUT_MS

    def _frame_ms(self, low_power):
        """How long to wait for the next frame when slowed down, or None for full speed."""
        if low_power:
            return config.LOW_POWER_FRAME_MS
        if has_pending_callbacks():
            return None
        if pygame.time.get_ticks() - self._last_input > config.IDLE_AFTER_INPUT_MS:
            return 1000 // config.IDLE_FPS
        return None

    def change_state(self, name):
        # Drop taps still waiting to fire on the screen being left.
        clear_pending_callbacks()
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
                if event.type in _INPUT_EVENTS:
                    self._last_input = pygame.time.get_ticks()
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.running = False
                else:
                    self.current_state.handle_event(event)
            run_pending_callbacks()
            self.audio.poll_volume()
            self.audio.poll_speak()
            self.audio.poll_music()
            t2 = time.monotonic()
            low_power = self.low_power = self._low_power()
            self.snow.update(moving=not low_power)
            self.current_state.update()
            self.current_state.draw(self.screen)
            t3 = time.monotonic()
            if low_power:
                # Putting a frame on screen costs Xorg and the display driver
                # ~100ms of CPU that the music needs, and while music plays the
                # screen is usually still (snow and lights stop), so only send
                # frames that changed.
                frame = self.screen.get_buffer().raw
                if frame != self._last_frame:
                    pygame.display.flip()
                self._last_frame = frame
            else:
                self._last_frame = None
                pygame.display.flip()
            t4 = time.monotonic()
            if PROFILE and (t4 - t0) * 1000 > SLOW_FRAME_MS:
                _log(
                    f"slow frame {(t4 - t0) * 1000:.0f}ms: get={(t1 - t0) * 1000:.0f} "
                    f"handle={(t2 - t1) * 1000:.0f} ({len(events)} events) "
                    f"draw={(t3 - t2) * 1000:.0f} flip={(t4 - t3) * 1000:.0f}"
                )
            frame_ms = self._frame_ms(low_power)
            if frame_ms:
                # Sleep until the next slow frame, but wake at once for a touch:
                # put it back for the next pygame.event.get() to handle.
                event = pygame.event.wait(max(1, frame_ms - int((time.monotonic() - t0) * 1000)))
                if event.type != pygame.NOEVENT:
                    pygame.event.post(event)
                self.clock.tick()
            else:
                self.clock.tick(config.FPS)
        pygame.quit()


def main():
    App().run()


if __name__ == "__main__":
    sys.exit(main())
