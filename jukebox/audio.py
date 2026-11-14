import shutil
import subprocess

import pygame

from . import config


class AudioManager:
    def __init__(self, playlist):
        self.playlist = playlist
        self.track_index = 0
        self.playing = False
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
        if self._pending_volume is None:
            return
        if self._volume_proc is not None and self._volume_proc.poll() is None:
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
