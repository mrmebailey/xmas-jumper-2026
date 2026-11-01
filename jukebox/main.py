import sys

import pygame

from . import config
from .audio import AudioManager
from .camera import CameraManager
from .jokes_loader import parse_jokes
from .music_loader import load_playlist
from .states.camera import CameraState
from .states.jokes import JokesState
from .states.menu import MenuState
from .states.music import MusicState


class App:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((config.SCREEN_W, config.SCREEN_H), pygame.FULLSCREEN)
        pygame.display.set_caption("Christmas Jukebox")
        pygame.mouse.set_visible(False)
        self.clock = pygame.time.Clock()

        self.font_large = pygame.font.Font(None, config.FONT_SIZE_LARGE)
        self.font_medium = pygame.font.Font(None, config.FONT_SIZE_MEDIUM)
        self.font_small = pygame.font.Font(None, config.FONT_SIZE_SMALL)

        self.jokes = parse_jokes(config.JOKES_FILE)
        playlist = load_playlist(config.MUSIC_DIR)
        self.audio = AudioManager(playlist)
        self.audio_volume = 70
        self.audio.set_volume(self.audio_volume)
        self.camera = CameraManager()

        self.states = {
            "menu": MenuState(self),
            "jokes": JokesState(self),
            "music": MusicState(self),
            "camera": CameraState(self),
        }
        self.current_state = None
        self.change_state("menu")
        self.running = True

    def change_state(self, name):
        if self.current_state is not None:
            self.current_state.on_exit()
        self.current_state = self.states[name]
        self.current_state.on_enter()

    def run(self):
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.running = False
                else:
                    self.current_state.handle_event(event)
            self.current_state.update()
            self.current_state.draw(self.screen)
            pygame.display.flip()
            self.clock.tick(config.FPS)
        pygame.quit()


def main():
    App().run()


if __name__ == "__main__":
    sys.exit(main())
