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
        self._parts = []
        self._rendered = []
        self._rendering_to = None
        self._plain_retry = False
        self.part_starts = None  # when each bit of the current speech starts (ticks)
        self.speech_ends_at = None  # when the current speech will finish (ticks)
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
        """Say something in Father Christmas's voice."""
        self.speak_parts([(text, config.SANTA_VOICE, 0)])

    def speak_parts(self, parts):
        """Say several bits one after another, each as (text, espeak options,
        ms of silence before it[, recording]), e.g. a joke's setup, then its
        punch line in a bigger voice after a pause. part_started(i) says when
        bit i is heard. A bit with a recording (a file that exists) plays
        that instead of being spoken by espeak.

        espeak-ng renders each bit to a WAV first and pygame plays them joined
        into one sound: synthesising live on the Pi Zero's busy CPU made the
        speech stutter, whereas playing finished audio is as smooth as the music."""
        if not self.speaking:
            self._music_was_playing_before_speak = self.playing
            if self.playing:
                pygame.mixer.music.pause()
        self._stop_speech()
        self._parts = [part for part in parts if part[0].strip()]
        self._rendered = []
        self._plain_retry = False
        self.part_starts = None
        self.speech_ends_at = None
        self._next_part()

    def _next_part(self):
        """Take recorded bits as they are, then render the next one with
        espeak, or play the lot once every bit is ready."""
        while len(self._rendered) < len(self._parts):
            part = self._parts[len(self._rendered)]
            recording = part[3] if len(part) > 3 else None
            if recording is None or not recording.exists():
                self._render_next()
                return
            self._rendered.append(recording)
        if self._parts:
            try:
                self._join_and_play()
            except pygame.error:
                self._speech_channel = None

    def _render_next(self):
        text, options = self._parts[len(self._rendered)][:2]
        if self._plain_retry and "-v" in options:
            # This espeak didn't know the voice: use its default one, still
            # with Santa's pitch, speed and loudness.
            i = options.index("-v")
            options = options[:i] + options[i + 2:]
        path = config.SPEECH_WAV.with_name(f"{config.SPEECH_WAV.stem}-{len(self._rendered)}.wav")
        self._rendering_to = path
        self._speak_proc = subprocess.Popen(
            [config.ESPEAK_CMD, *options, "-w", str(path), text],
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

    def part_started(self, index):
        """True once bit `index` of the speech has started being heard."""
        return (self.part_starts is not None and index < len(self.part_starts)
                and pygame.time.get_ticks() >= self.part_starts[index])

    def _join_and_play(self):
        """Join the rendered bits, with their pauses, into one sound and play it."""
        frequency, size, channels = pygame.mixer.get_init()
        frame_bytes = abs(size) // 8 * channels
        chunks, starts, offset = [], [], 0
        for part, path in zip(self._parts, self._rendered):
            gap_ms = part[2]
            gap = bytes(int(frequency * gap_ms / 1000) * frame_bytes)
            chunks.append(gap)
            offset += len(gap)
            starts.append(offset)
            raw = pygame.mixer.Sound(str(path)).get_raw()
            chunks.append(raw)
            offset += len(raw)
        self._speech_sound = pygame.mixer.Sound(buffer=b"".join(chunks))
        self._speech_channel = self._speech_sound.play()
        now = pygame.time.get_ticks()
        self.part_starts = [now + start * 1000 // (frequency * frame_bytes) for start in starts]
        self.speech_ends_at = now + offset * 1000 // (frequency * frame_bytes)

    def poll_speak(self):
        if self._speak_proc is not None and self._speak_proc.poll() is not None:
            ok = self._speak_proc.returncode == 0 and self._rendering_to.exists()
            self._speak_proc = None
            if ok:
                self._rendered.append(self._rendering_to)
                self._next_part()
            elif not self._plain_retry:
                self._plain_retry = True
                self._render_next()
        if self._speech_channel is not None and not self._speech_channel.get_busy():
            self._speech_channel = None
            self._speech_sound = None
        if not self.speaking and self._music_was_playing_before_speak:
            self._music_was_playing_before_speak = False
            pygame.mixer.music.unpause()
