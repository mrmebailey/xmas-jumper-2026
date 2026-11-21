#!/usr/bin/env python3
"""Make the 80s home-computer style music that loops while a game is played.

Everything is synthesised here from scratch, the way the old sound chips did
it: a square-wave lead, a thinner square wave rattling through the chords
(those fast arpeggios), a triangle-wave bass and noise drums. The tunes are
public-domain carols plus one original, so there's nothing to licence.

Run on a laptop (it only needs numpy), then commit game_music/:

    ~/.cache/jukebox/voice-venv/bin/python tools/make_game_music.py

Each track is a seamless loop, saved as a small mono WAV: the Pi plays WAVs
without having to decode them, which leaves its CPU for the game.
"""

import sys
import wave
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
from jukebox import config  # noqa: E402

SR = 22050
_NOTE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_CHORDS = {"": [0, 4, 7], "m": [0, 3, 7], "7": [0, 4, 7, 10]}


def midi(name):
    """"C4" -> 60, "F#4" -> 66."""
    pitch = _NOTE[name[0]]
    rest = name[1:]
    if rest.startswith("#"):
        pitch, rest = pitch + 1, rest[1:]
    elif rest.startswith("b"):
        pitch, rest = pitch - 1, rest[1:]
    return 12 * (int(rest) + 1) + pitch


def hz(note):
    return 440.0 * 2 ** ((note - 69) / 12)


def chord_notes(chord):
    """"G7" -> its notes from the root in octave 3, e.g. [55, 59, 62, 65]."""
    root = chord[0] + ("#" if chord[1:2] == "#" else "")
    kind = chord[len(root):]
    base = midi(root + "3")
    return [base + i for i in _CHORDS[kind]]


def parse(melody):
    """"G4:1.5 F4:.5 R:1" -> [(note or None, beats)]."""
    out = []
    for token in melody.split():
        name, _, beats = token.partition(":")
        out.append((None if name == "R" else midi(name), float(beats or 1)))
    return out


# --- Sound chip voices -----------------------------------------------------

def _phase(freq, n, vibrato=False):
    f = np.full(n, freq)
    if vibrato and n > SR * 0.3:
        t = np.arange(n) / SR
        depth = np.clip((t - 0.2) / 0.2, 0, 1) * 0.008  # fades in on long notes
        f = f * (1 + depth * np.sin(2 * np.pi * 6 * t))
    return np.cumsum(f / SR) % 1.0


def pulse(freq, n, duty=0.5, vibrato=False):
    return np.where(_phase(freq, n, vibrato) < duty, 1.0, -1.0)


def triangle(freq, n):
    return 2 * np.abs(2 * _phase(freq, n) - 1) - 1


def envelope(n, attack=0.004, decay=0.1, sustain=0.65, release=0.025):
    env = np.full(n, float(sustain))
    a, d, r = int(SR * attack), int(SR * decay), int(SR * release)
    a = min(a, n)
    env[:a] = np.linspace(0, 1, a)
    end = min(n, a + d)
    env[a:end] = np.linspace(1, sustain, end - a)
    r = min(r, n)
    env[n - r:] *= np.linspace(1, 0, r)
    return env


def kick(n):
    t = np.arange(min(n, int(SR * 0.15))) / SR
    freq = 50 + 110 * np.exp(-t * 35)
    out = np.zeros(n)
    out[:len(t)] = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t * 18)
    return out


def snare(n, rng):
    t = np.arange(min(n, int(SR * 0.14))) / SR
    out = np.zeros(n)
    out[:len(t)] = (rng.uniform(-1, 1, len(t)) * 0.8 + 0.4 * np.sin(2 * np.pi * 190 * t)) * np.exp(-t * 28)
    return out


def hat(n, rng):
    t = np.arange(min(n, int(SR * 0.04))) / SR
    noise = rng.uniform(-1, 1, len(t) + 1)
    out = np.zeros(n)
    out[:len(t)] = np.diff(noise) * 0.5 * np.exp(-t * 90)  # differenced noise = just the fizz
    return out


# --- Arranging --------------------------------------------------------------

class Song:
    def __init__(self, bpm, beats_per_bar, bars, melody, pickup=0.0, swing_bass=False):
        self.beat = 60 / bpm
        self.bpb = beats_per_bar
        self.bars = bars  # chord per bar
        self.melody = parse(melody)
        self.pickup = pickup  # melody beats before bar 1 (wrapped onto the end of the loop)
        self.length = int(round(len(bars) * beats_per_bar * self.beat * SR))

    def _at(self, beats):
        return int(round(beats * self.beat * SR))

    def _add(self, track, start, sound):
        start %= len(track)
        end = min(len(track), start + len(sound))
        track[start:end] += sound[:end - start]
        if end - start < len(sound):  # wrap round, so the loop is seamless
            rest = sound[end - start:]
            track[:len(rest)] += rest

    def lead(self, octave_up=False):
        track = np.zeros(self.length)
        pos = -self.pickup
        for note, beats in self.melody:
            if note is not None:
                n = self._at(beats * 0.92)  # a hair of a gap between notes, so repeats are heard
                freq = hz(note + (12 if octave_up else 0))
                sound = pulse(freq, n, 0.25, vibrato=True) * envelope(n)
                self._add(track, self._at(pos), sound)
            pos += beats
        return track

    def arpeggio(self, step_s=0.055):
        """The chord's notes in turn, very fast: the sound chip's way of playing a chord."""
        track = np.zeros(self.length)
        step = int(SR * step_s)
        for i, chord in enumerate(self.bars):
            notes = [n + 12 for n in chord_notes(chord)]
            start, end = self._at(i * self.bpb), self._at((i + 1) * self.bpb)
            for j, s in enumerate(range(start, end, step)):
                n = min(step, end - s)
                track[s:s + n] += pulse(hz(notes[j % len(notes)]), n, 0.125)
        return track

    def bass(self):
        """Driving eighth notes, jumping between the root and its octave."""
        track = np.zeros(self.length)
        for i, chord in enumerate(self.bars):
            root = chord_notes(chord)[0] - 12
            for k in range(self.bpb * 2):
                note = root + (12 if k % 2 else 0)
                n = self._at(0.5 * 0.85)
                self._add(track, self._at(i * self.bpb + k * 0.5),
                          triangle(hz(note), n) * envelope(n, decay=0.05, sustain=0.8))
        return track

    def drums(self, seed=1):
        rng = np.random.default_rng(seed)
        track = np.zeros(self.length)
        hit = self._at(1)
        for i in range(len(self.bars)):
            for b in range(self.bpb):
                at = self._at(i * self.bpb + b)
                if b == 0 or (self.bpb == 4 and b == 2):
                    self._add(track, at, kick(hit))
                elif self.bpb == 4 or b == 2:
                    self._add(track, at, snare(hit, rng))
                self._add(track, at, hat(hit, rng) * 0.6)
                self._add(track, at + self._at(0.5), hat(hit, rng) * 0.4)
            if i % 8 == 7:  # a little fill every 8 bars
                for k in range(4):
                    self._add(track, self._at(i * self.bpb + self.bpb - 1 + k * 0.25), snare(hit // 4, rng) * 0.7)
        return track

    def render(self, passes=2):
        """The tune played `passes` times, the lead an octave up on the last time round."""
        beats = sum(b for _, b in self.melody)
        if abs(beats - len(self.bars) * self.bpb) > 1e-6:
            raise ValueError(f"melody is {beats} beats but the chords are {len(self.bars) * self.bpb}")
        parts = []
        for p in range(passes):
            last = p == passes - 1 and passes > 1
            mix = (0.30 * self.lead(octave_up=last) + (0.12 if last else 0.08) * self.arpeggio()
                   + 0.30 * self.bass() + 0.25 * self.drums(seed=p))
            parts.append(mix)
        audio = np.concatenate(parts)
        # Take the edge off the square waves, like a TV speaker would.
        out = np.empty_like(audio)
        acc = 0.0
        a = 0.55
        for i in range(0, len(audio), 4096):  # one-pole low-pass, in blocks for speed
            block = audio[i:i + 4096]
            res = np.empty_like(block)
            for j, x in enumerate(block):
                acc += a * (x - acc)
                res[j] = acc
            out[i:i + 4096] = res
        return out / (np.max(np.abs(out)) or 1) * 0.8


# --- The tunes ---------------------------------------------------------------

JINGLE_BELLS = Song(150, 4, [
    "C", "C", "C", "F", "F", "G", "G", "C",
    "C", "C", "C", "F", "F", "G", "G7", "C",
    "C", "C", "C", "C", "F", "C", "D7", "G",
    "C", "C", "C", "C", "F", "C", "G7", "C",
], """
    G3 E4 D4 C4  G3:3 G3:.5 G3:.5  G3 E4 D4 C4  A3:4
    A3 F4 E4 D4  B3:4  G4 G4 F4 D4  E4:4
    G3 E4 D4 C4  G3:4  G3 E4 D4 C4  A3:3 A3
    A3 F4 E4 D4  G4 G4 G4 G4  A4 G4 F4 D4  C4:2 G4:2
    E4 E4 E4:2  E4 E4 E4:2  E4 G4 C4:1.5 D4:.5  E4:4
    F4 F4 F4:1.5 F4:.5  F4 E4 E4 E4:.5 E4:.5  E4 D4 D4 E4  D4:2 G4:2
    E4 E4 E4:2  E4 E4 E4:2  E4 G4 C4:1.5 D4:.5  E4:4
    F4 F4 F4:1.5 F4:.5  F4 E4 E4 E4:.5 E4:.5  G4 G4 F4 D4  C4:4
""")

WE_WISH_YOU = Song(170, 3, ["G", "C", "A7", "D", "B7", "Em", "D7", "G"], """
    D4
    G4 G4:.5 A4:.5 G4:.5 F#4:.5  E4 E4 E4
    A4 A4:.5 B4:.5 A4:.5 G4:.5  F#4 D4 D4
    B4 B4:.5 C5:.5 B4:.5 A4:.5  G4 E4 D4:.5 D4:.5
    E4 A4 F#4  G4:2
""", pickup=1)

DECK_THE_HALLS = Song(132, 4, [
    "C", "C", "G", "C", "C", "C", "G", "C",
    "G", "C", "D", "G", "C", "C", "F", "C",
], """
    G4:1.5 F4:.5 E4 D4  C4 D4 E4 C4  D4:.5 E4:.5 F4:.5 D4:.5 E4:1.5 D4:.5  C4 B3 C4:2
    G4:1.5 F4:.5 E4 D4  C4 D4 E4 C4  D4:.5 E4:.5 F4:.5 D4:.5 E4:1.5 D4:.5  C4 B3 C4:2
    D4:1.5 E4:.5 F4 D4  E4:1.5 F4:.5 G4 D4  E4:.5 F#4:.5 G4 A4:.5 B4:.5 C5  B4 A4 G4:2
    G4:1.5 F4:.5 E4 D4  C4 D4 E4 C4  A4:.5 A4:.5 A4:.5 A4:.5 G4:1.5 F4:.5  E4 D4 C4:2
""")

# An original tune in the same style, for Bauble Pop.
BAUBLE_BOP = Song(140, 4, [
    "Am", "F", "C", "G", "Am", "F", "G", "Am",
    "F", "G", "Em", "Am", "F", "G", "E", "Am",
], """
    E5:.5 A5:.5 E5:.5 C5:.5 A4 C5:.5 E5:.5   F5 E5:.5 D5:.5 C5 A4
    G4:.5 C5:.5 E5:.5 G5:.5 E5 C5            D5:1.5 B4:.5 G4:2
    E5:.5 A5:.5 E5:.5 C5:.5 A4 B4:.5 C5:.5   D5 C5:.5 D5:.5 F5 E5
    D5:.5 E5:.5 D5:.5 B4:.5 G4 B4            A4:3 R
    A5 G5:.5 F5:.5 E5 C5                     D5 B4:.5 D5:.5 G5:2
    B5 G5:.5 E5:.5 G5 E5                     A5:1.5 E5:.5 C5:2
    F5:.5 A5:.5 F5:.5 C5:.5 A4 C5            B4:.5 D5:.5 G5:.5 D5:.5 B4 D5
    E5 D5:.5 B4:.5 G#4 B4                    A4:2 R:2
""")

TRACKS = {
    "jingle-bells.wav": (JINGLE_BELLS, 1),
    "we-wish-you.wav": (WE_WISH_YOU, 3),
    "deck-the-halls.wav": (DECK_THE_HALLS, 2),
    "bauble-bop.wav": (BAUBLE_BOP, 2),
}


def save_wav(audio, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes((np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes())


def main():
    for name, (song, passes) in TRACKS.items():
        audio = song.render(passes)
        path = config.GAME_MUSIC_DIR / name
        save_wav(audio, path)
        print(f"{path.relative_to(REPO_ROOT)}: {len(audio) / SR:.0f}s, {path.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
