import random
import shutil
import subprocess

import pygame

from . import config


class AudioManager:
    def __init__(self, playlist):
        self.playlist = playlist
        self.track_index = 0
        self.playing = False
        self._paused = False  # a track is loaded and paused (get_busy() is False then)
        self.shuffle = config.SHUFFLE
        self._order = []  # playlist indexes in play order
        self._position = 0  # where track_index is in _order
        if self.shuffle and self.playlist:
            self.track_index = random.randrange(len(self.playlist))  # start somewhere new
        self._set_order()
        self._speak_proc = None
        self._speech_sound = None
        self._speech_channel = None
        self._music_was_playing_before_speak = False
        # PipeWire's default output covers everything (music, spoken jokes, a
        # Bluetooth speaker); amixer only reaches a local ALSA card.
        self._use_wpctl = shutil.which("wpctl") is not None
        self._volume_proc = None
        self._pending_volume = None
        pygame.mixer.init()

    @property
    def current_track(self):
        return self.playlist[self.track_index] if self.playlist else None

    def _set_order(self):
        """Play order from the current track on: shuffled, or album order."""
        order = list(range(len(self.playlist)))
        if self.shuffle:
            random.shuffle(order)
            if self.playlist:
                # Start from the current track so the song playing carries on.
                order.remove(self.track_index)
                order.insert(0, self.track_index)
        self._order = order
        self._position = order.index(self.track_index) if self.playlist else 0

    def toggle_shuffle(self):
        self.shuffle = not self.shuffle
        self._set_order()

    def _play(self, index):
        self.track_index = index
        pygame.mixer.music.load(self.playlist[index].path)
        pygame.mixer.music.play()
        self.playing = True
        self._paused = False

    def play_track(self, index):
        """Play a song picked from the list; the play order carries on from it."""
        if not self.playlist:
            return
        self._play(index)
        if self.shuffle:
            self._set_order()
        else:
            self._position = index

    def play_pause(self):
        if not self.playlist:
            return
        if self.playing:
            pygame.mixer.music.pause()
            self.playing = False
            self._paused = True
        elif self._paused:
            pygame.mixer.music.unpause()
            self.playing = True
            self._paused = False
        else:
            self._play(self.track_index)

    def _step(self, delta):
        if not self.playlist:
            return
        self._position += delta
        if self.shuffle and self._position >= len(self._order):
            # Been through every song: shuffle again, without repeating the last one first.
            last = self._order[-1]
            random.shuffle(self._order)
            if len(self._order) > 1 and self._order[0] == last:
                self._order.append(self._order.pop(0))
            self._position = 0
        self._position %= len(self._order)
        self._play(self._order[self._position])

    def next_track(self):
        self._step(1)

    def prev_track(self):
        self._step(-1)

    def stop(self):
        pygame.mixer.music.stop()
        self.playing = False
        self._paused = False

    def poll_music(self):
        """Move on to the next song when one finishes. Called every frame."""
        if (self.playing and not self.speaking and not self._music_was_playing_before_speak
                and not pygame.mixer.music.get_busy()):
            self.next_track()

    def set_volume(self, percent):
        percent = max(0, min(100, int(percent)))
        if self._use_wpctl:
            # The system volume already scales the music, so don't scale it twice.
            pygame.mixer.music.set_volume(1.0)
        else:
            pygame.mixer.music.set_volume(percent / 100)
        self._pending_volume = percent
        self.poll_volume()

    def poll_volume(self):
        """Apply the latest requested volume without blocking. Dragging the slider
        asks many times a second; only one volume command runs at a time and the
        newest value wins. Called every frame."""
        if self._volume_proc is not None:
            if self._volume_proc.poll() is None:
                return
            self._volume_proc = None  # finished; don't leave it as a zombie
        if self._pending_volume is None:
            return
        percent, self._pending_volume = self._pending_volume, None
        if self._use_wpctl:
            cmd = ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{percent / 100:.2f}"]
        else:
            target = ["-c", str(config.ALSA_CARD)] if config.ALSA_CARD is not None else []
            cmd = ["amixer", *target, "sset", "Master", f"{percent}%"]
        self._volume_proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def speak(self, text):
        """Speak a joke. espeak-ng renders it to a WAV first and pygame plays that:
        synthesising live on the Pi Zero's busy CPU made the speech stutter,
        whereas playing a finished file is as smooth as the music."""
        if not self.speaking:
            self._music_was_playing_before_speak = self.playing
            if self.playing:
                pygame.mixer.music.pause()
        self._stop_speech()
        self._speak_proc = subprocess.Popen(
            [config.ESPEAK_CMD, "-w", str(config.SPEECH_WAV), text],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def _stop_speech(self):
        if self._speak_proc is not None and self._speak_proc.poll() is None:
            self._speak_proc.kill()
            self._speak_proc.wait()
        self._speak_proc = None
        if self._speech_channel is not None:
            self._speech_channel.stop()
        self._speech_channel = None
        self._speech_sound = None

    @property
    def music_active(self):
        # get_busy() is False once a track ends or while paused.
        return self.playing and pygame.mixer.music.get_busy()

    @property
    def speaking(self):
        return self._speak_proc is not None or self._speech_channel is not None

    def poll_speak(self):
        if self._speak_proc is not None and self._speak_proc.poll() is not None:
            ok = self._speak_proc.returncode == 0
            self._speak_proc = None
            if ok:
                self._speech_sound = pygame.mixer.Sound(str(config.SPEECH_WAV))
                self._speech_channel = self._speech_sound.play()
        if self._speech_channel is not None and not self._speech_channel.get_busy():
            self._speech_channel = None
            self._speech_sound = None
        if not self.speaking and self._music_was_playing_before_speak:
            self._music_was_playing_before_speak = False
            pygame.mixer.music.unpause()
