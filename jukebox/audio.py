import subprocess

import pygame

from . import config


class AudioManager:
    def __init__(self, playlist):
        self.playlist = playlist
        self.track_index = 0
        self.playing = False
        self._speak_proc = None
        self._music_was_playing_before_speak = False
        pygame.mixer.init()

    @property
    def current_track_name(self):
        if not self.playlist:
            return "No music found"
        return self.playlist[self.track_index][0]

    def _load_current(self):
        if not self.playlist:
            return
        pygame.mixer.music.load(self.playlist[self.track_index][1])

    def play_pause(self):
        if not self.playlist:
            return
        if self.playing:
            pygame.mixer.music.pause()
            self.playing = False
        elif pygame.mixer.music.get_busy():
            pygame.mixer.music.unpause()
            self.playing = True
        else:
            self._load_current()
            pygame.mixer.music.play()
            self.playing = True

    def next_track(self):
        if not self.playlist:
            return
        self.track_index = (self.track_index + 1) % len(self.playlist)
        self._load_current()
        pygame.mixer.music.play()
        self.playing = True

    def prev_track(self):
        if not self.playlist:
            return
        self.track_index = (self.track_index - 1) % len(self.playlist)
        self._load_current()
        pygame.mixer.music.play()
        self.playing = True

    def stop(self):
        pygame.mixer.music.stop()
        self.playing = False

    def set_volume(self, percent):
        percent = max(0, min(100, int(percent)))
        pygame.mixer.music.set_volume(percent / 100)
        target = f"-c{config.ALSA_CARD} " if config.ALSA_CARD is not None else ""
        subprocess.run(
            f"amixer {target}sset Master {percent}%".split(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def speak(self, text):
        self._music_was_playing_before_speak = self.playing
        if self.playing:
            pygame.mixer.music.pause()
        self._speak_proc = subprocess.Popen([config.ESPEAK_CMD, text])

    def poll_speak(self):
        if self._speak_proc is not None and self._speak_proc.poll() is not None:
            self._speak_proc = None
            if self._music_was_playing_before_speak:
                pygame.mixer.music.unpause()
