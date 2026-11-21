#!/usr/bin/env python3
"""Record every joke in jokes.txt in Father Christmas's voice, ready for the
jukebox to play.

Run this on a laptop or desktop, not the Pi: the Pi Zero is far too slow for
a natural-sounding voice, but playing finished recordings costs it nothing.
Re-run it whenever jokes.txt changes (only new or edited jokes are
recorded), then commit jokes_audio/.

    python3 -m venv ~/.cache/jukebox/voice-venv
    ~/.cache/jukebox/voice-venv/bin/pip install -r tools/requirements-voice.txt
    ~/.cache/jukebox/voice-venv/bin/python tools/make_santa_voice.py

The words are spoken by Piper (an offline neural text-to-speech engine) and
then made into Santa with audio effects: pitched down, slowed, warmed up and
given a little room echo. Besides the jokes it records:
  - Santa's own lines before and after a joke (SANTA_INTROS / SANTA_OUTROS in
    jukebox/config.py), with sleigh bells under the opening line
  - his laugh (SANTA_LAUGHS), said as one phrase so it flows naturally
  - a sparkly twinkle at the end of every punch line
  - the Naughty or Nice scanner's messages (NAUGHTY_SCAN_MESSAGES) and every
    verdict it can give (jukebox/naughty_words.py)
The bells and twinkle are made here from scratch, so there are no sound files
to find or licence. Jokes without a recording fall back to espeak-ng on the Pi.

Options:
    --samples DIR   record a few jokes in each of SAMPLE_VOICES into DIR, to
                    pick the voice by ear (doesn't touch jokes_audio/)
    --voice NAME    use another Piper voice (see SAMPLE_VOICES)
    --force         record everything again (after changing the voice or effects)
"""

import argparse
import random
import re
import sys
from pathlib import Path

import numpy as np
from pedalboard import (Compressor, Gain, HighpassFilter, Limiter, LowpassFilter, LowShelfFilter, Pedalboard,
                        PeakFilter, PitchShift, Resample, Reverb)
from pedalboard.io import AudioFile
from piper import PiperVoice, SynthesisConfig
from piper.download_voices import download_voice

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
from jukebox import config  # noqa: E402
from jukebox.jokes_loader import parse_jokes, recorded_speech, split_joke  # noqa: E402
from jukebox import naughty_words  # noqa: E402

# A traditional Santa: an older, naturally deep and expressive American
# voice, so it only needs a gentle push down (big pitch shifts sound rough).
VOICE = "en_US-norman-medium"
SAMPLE_VOICES = [
    "en_US-norman-medium",
    "en_US-joe-medium",
    "en_US-kusal-medium",
    "en_US-john-medium",
]
VOICE_DIR = Path.home() / ".cache" / "jukebox" / "piper-voices"
SAMPLE_RATE = 22050  # plenty for speech, and keeps the files small
OGG_QUALITY = "96 kbps"

# How each kind of line is delivered. length_scale > 1 speaks more slowly;
# pitch is in semitones (negative = deeper). The question is warm and
# unhurried, the punch line slower, deeper and louder; Santa's own lines are
# chatty and a touch brighter.
STYLES = {
    "q": dict(length_scale=1.2, pitch=-2.5, gain_db=0, reverb=0.08),
    "p": dict(length_scale=1.3, pitch=-3, gain_db=2, reverb=0.10),
    "intro": dict(length_scale=1.15, pitch=-2.5, gain_db=0, reverb=0.10),
    "outro": dict(length_scale=1.15, pitch=-2.5, gain_db=1, reverb=0.10),
    "scan": dict(length_scale=1.1, pitch=-2.5, gain_db=0, reverb=0.10),  # Naughty or Nice scanner
    # The Naughty or Nice verdict: which list announced slow and big,
    # then the score and his comment in his chatty voice.
    "vword": dict(length_scale=1.25, pitch=-3, gain_db=2, reverb=0.12),
    "vpct": dict(length_scale=1.1, pitch=-2.5, gain_db=0, reverb=0.10),
    "vline": dict(length_scale=1.15, pitch=-2.5, gain_db=1, reverb=0.10),
    "vtop": dict(length_scale=1.2, pitch=-3, gain_db=2, reverb=0.10),
}

# Santa's laugh is said as one whole phrase: Piper flows naturally through a
# phrase, whereas "Ho"s recorded one at a time and joined sounded choppy.
# A little more natural wobble (noise) than the jokes, so it's lively.
LAUGH_STYLE = dict(length_scale=1.5, pitch=-2.5, gain_db=1, reverb=0.14, noise_scale=0.667, noise_w_scale=0.8)

BELLS_LEVEL = 0.22  # sleigh bells under the opening line, relative to the voice
TWINKLE_LEVEL = 0.18


def load_voice(name):
    VOICE_DIR.mkdir(parents=True, exist_ok=True)
    model = VOICE_DIR / f"{name}.onnx"
    if not model.exists():
        print(f"Downloading the {name} voice...")
        download_voice(name, VOICE_DIR)
    return PiperVoice.load(str(model))


# --- Delivery ---------------------------------------------------------------

# Commas make Piper take a breath (it ignores "..."), so add them where a
# storyteller would pause before the reveal: "What do you call, a snowman
# with a six-pack?"
_PAUSES = [
    (re.compile(r"^(What do you call)\s+", re.I), r"\1, "),
    (re.compile(r"^(What do you get)\s+", re.I), r"\1, "),
    (re.compile(r"^(What(?:'s|’s| is) [\w'’]+ favou?rite(?: (?:type|kind) of)?)\s+", re.I), r"\1, "),
    (re.compile(r"^(What did (?:the|one) .+? say)\s+(to\b)", re.I), r"\1, \2"),
    (re.compile(r"(\w)\s+(if|when) ", re.I), r"\1, \2 "),
]


def storyteller(question):
    """The question with one pause added (the first rule that fits)."""
    for pattern, replacement in _PAUSES:
        paused = pattern.sub(replacement, question, count=1)
        if paused != question:
            return paused
    return question


# --- Voice ------------------------------------------------------------------

def _trim(audio, rate, pad_ms=30):
    """Cut the silence Piper leaves at each end."""
    loud = np.where(np.abs(audio) > 0.01)[0]
    if not len(loud):
        return audio
    pad = rate * pad_ms // 1000
    return audio[max(0, loud[0] - pad):loud[-1] + pad]


def _speak(voice, text, length_scale, pitch, noise_scale=0.5, noise_w_scale=0.6):
    """Piper's voice, pitched down; (audio, rate)."""
    # Lower noise scales give a steadier, smoother delivery.
    syn = SynthesisConfig(length_scale=length_scale, noise_scale=noise_scale, noise_w_scale=noise_w_scale)
    chunks = list(voice.synthesize(text, syn_config=syn))
    rate = chunks[0].sample_rate
    audio = np.concatenate([c.audio_float_array for c in chunks]).astype(np.float32)
    return PitchShift(semitones=pitch)(audio, rate), rate


def _santa_tone(audio, rate, reverb, gain_db):
    """Warm, round, smooth, in a small room; resampled to SAMPLE_RATE."""
    effects = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=60),
        LowShelfFilter(cutoff_frequency_hz=250, gain_db=4),  # a fuller, rounder chest voice
        PeakFilter(cutoff_frequency_hz=3500, gain_db=-3, q=0.8),  # less nasal edge
        LowpassFilter(cutoff_frequency_hz=7000),  # smooth off the hiss and fizz
        Compressor(threshold_db=-20, ratio=3, attack_ms=5, release_ms=120),
        Reverb(room_size=0.3, damping=0.6, wet_level=reverb, dry_level=0.9, width=0),
        Gain(gain_db=gain_db),
    ])
    audio = effects(audio, rate)
    if rate != SAMPLE_RATE:
        audio = Resample(target_sample_rate=SAMPLE_RATE)(audio, rate)
    return audio.astype(np.float32)


def santa(voice, text, kind):
    style = STYLES[kind]
    audio, rate = _speak(voice, text, style["length_scale"], style["pitch"])
    return _santa_tone(audio, rate, style["reverb"], style["gain_db"])


def laugh(voice, text):
    style = LAUGH_STYLE
    audio, rate = _speak(voice, text, style["length_scale"], style["pitch"], style["noise_scale"],
                         style["noise_w_scale"])
    return _santa_tone(_trim(audio, rate), rate, style["reverb"], style["gain_db"])


# --- Bells ------------------------------------------------------------------

def _bell(freq, decay_s, rng, length_s):
    """One small metal bell: a few out-of-tune partials dying away."""
    t = np.arange(int(SAMPLE_RATE * length_s)) / SAMPLE_RATE
    out = np.zeros_like(t)
    for ratio, amp in [(1.0, 1.0), (2.32, 0.6), (3.86, 0.35), (5.4, 0.2)]:
        f = freq * ratio * rng.uniform(0.99, 1.01)
        if f < SAMPLE_RATE / 2 - 500:
            out += amp * np.sin(2 * np.pi * f * t + rng.uniform(0, 6.28)) * np.exp(-t / (decay_s / ratio ** 0.5))
    return out


def sleigh_bells(seconds, seed):
    """A bunch of jingle bells shaken in time, like a sleigh going by."""
    rng = random.Random(seed)
    out = np.zeros(int(SAMPLE_RATE * (seconds + 0.5)))
    shake = 0.0
    while shake < seconds:
        for _ in range(rng.randint(8, 14)):  # every bell in the bunch rattles
            start = int(SAMPLE_RATE * (shake + rng.uniform(0, 0.05)))
            bell = _bell(rng.uniform(2300, 3400), rng.uniform(0.05, 0.12), rng, 0.4) * rng.uniform(0.3, 1)
            out[start:start + len(bell)] += bell[:len(out) - start]
        shake += 0.22 + rng.uniform(-0.02, 0.02)
    fade = np.linspace(1, 0, int(SAMPLE_RATE * 0.5)) ** 2
    out[-len(fade):] *= fade
    out = HighpassFilter(cutoff_frequency_hz=1500)(out.astype(np.float32), SAMPLE_RATE)
    return Reverb(room_size=0.4, wet_level=0.2, dry_level=0.9)(out, SAMPLE_RATE)


def twinkle():
    """A quick sparkly run up a C major chord, like a glockenspiel."""
    rng = random.Random(7)
    out = np.zeros(int(SAMPLE_RATE * 1.0))
    for i, freq in enumerate([1047, 1319, 1568, 2093]):
        start = int(SAMPLE_RATE * 0.07 * i)
        t = np.arange(len(out) - start) / SAMPLE_RATE
        note = (np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(2 * np.pi * freq * 2.76 * t + rng.uniform(0, 6))) \
            * np.exp(-t / 0.3) * (1 + 0.1 * i)
        out[start:] += note
    return Reverb(room_size=0.5, wet_level=0.25, dry_level=0.9)(out.astype(np.float32), SAMPLE_RATE)


def _mix(base, extra, at, level):
    """extra laid over base from sample `at`, scaled to `level` of base's peak."""
    extra = extra * (level * np.max(np.abs(base)) / (np.max(np.abs(extra)) or 1))
    out = np.zeros(max(len(base), at + len(extra)), np.float32)
    out[:len(base)] += base
    out[at:at + len(extra)] += extra
    return out


def with_bells(speech, seed):
    """Sleigh bells start, Santa speaks over them, they jingle away."""
    lead = int(SAMPLE_RATE * 0.5)
    bells = sleigh_bells(len(speech) / SAMPLE_RATE + 0.3, seed)
    return _mix(np.concatenate([np.zeros(lead, np.float32), speech]), bells, 0, BELLS_LEVEL)


def with_twinkle(speech):
    """The twinkle sparkles in just as the punch line finishes."""
    speech = _trim(speech, SAMPLE_RATE, pad_ms=60)
    return _mix(speech, twinkle(), max(0, len(speech) - int(SAMPLE_RATE * 0.15)), TWINKLE_LEVEL)


# --- Files ------------------------------------------------------------------

def save(audio, path):
    # Same loudness for every file, with headroom: Ogg encoding overshoots the
    # peaks a little, and they'd crackle if they went past 1.
    audio = Limiter(threshold_db=-6, release_ms=100)(audio.astype(np.float32), SAMPLE_RATE)
    audio = audio * (0.5 / (float(np.max(np.abs(audio))) or 1.0))
    path.parent.mkdir(parents=True, exist_ok=True)
    with AudioFile(str(path), "w", SAMPLE_RATE, 1, quality=OGG_QUALITY) as f:
        f.write(audio.reshape(1, -1).astype(np.float32))


def recordings():
    """[(path, description, make(voice) -> audio)] for everything Santa says."""
    out = []
    rec = lambda text, kind: recorded_speech(config.JOKE_AUDIO_DIR, text, kind)  # noqa: E731
    for joke in parse_jokes(config.JOKES_FILE):
        question, punch_line = split_joke(joke)
        out.append((rec(question, "q"), question,
                    lambda v, q=question: santa(v, storyteller(q), "q")))
        if punch_line:
            out.append((rec(punch_line, "p"), punch_line,
                        lambda v, p=punch_line: with_twinkle(santa(v, p, "p"))))
    for i, text in enumerate(config.SANTA_INTROS):
        out.append((rec(text, "intro"), text, lambda v, t=text, i=i: with_bells(santa(v, t, "intro"), i)))
    for text in config.SANTA_OUTROS:
        out.append((rec(text, "outro"), text, lambda v, t=text: santa(v, t, "outro")))
    for text in config.NAUGHTY_SCAN_MESSAGES:
        out.append((rec(text, "scan"), text, lambda v, t=text: santa(v, t, "scan")))
    verdict_lines = [(naughty_words.spoken_verdict(word), "vword") for word in naughty_words.VERDICT_LINES]
    verdict_lines += [(text, "vpct") for text in naughty_words.all_naughtiness_lines()]
    verdict_lines += [(line, "vline") for _, lines in naughty_words.VERDICT_LINES.values() for line in lines]
    verdict_lines.append((naughty_words.TOP_OF_LIST, "vtop"))
    for text, kind in verdict_lines:
        out.append((rec(text, kind), text, lambda v, t=text, k=kind: santa(v, t, k)))
    for text in config.SANTA_LAUGHS:
        out.append((rec(text, "laugh"), text, lambda v, t=text: laugh(v, t)))
    return out


def record_samples(out_dir, count=3):
    """A few whole jokes, as the jukebox would play them, in each voice."""
    jokes = parse_jokes(config.JOKES_FILE)[:count]
    silence = lambda s: np.zeros(int(SAMPLE_RATE * s), np.float32)  # noqa: E731
    for name in SAMPLE_VOICES:
        voice = load_voice(name)
        parts = []
        for n, joke in enumerate(jokes):
            question, punch_line = split_joke(joke)
            parts += [with_bells(santa(voice, config.SANTA_INTROS[n], "intro"), n), silence(0.3),
                      santa(voice, storyteller(question), "q")]
            if punch_line:
                parts += [silence(config.JOKE_PAUSE_MS / 1000), with_twinkle(santa(voice, punch_line, "p"))]
            parts += [silence(0.4), laugh(voice, config.SANTA_LAUGHS[n % len(config.SANTA_LAUGHS)])]
            if n % 2 == 0:
                parts += [silence(0.3), santa(voice, config.SANTA_OUTROS[n], "outro")]
            parts.append(silence(1.5))
        path = Path(out_dir) / f"santa-{name}.ogg"
        save(np.concatenate(parts), path)
        print(f"Wrote {path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--voice", default=VOICE)
    parser.add_argument("--samples", metavar="DIR")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.samples:
        record_samples(args.samples)
        return

    wanted = recordings()
    todo = [r for r in wanted if args.force or not r[0].exists()]
    voice = load_voice(args.voice) if todo else None
    for i, (path, description, make) in enumerate(todo, 1):
        print(f"[{i}/{len(todo)}] {description}")
        save(make(voice), path)

    # Recordings of jokes or lines that have since been edited or removed.
    keep = {path for path, _, _ in wanted}
    stale = [p for p in config.JOKE_AUDIO_DIR.glob("*.ogg") if p not in keep]
    for path in stale:
        path.unlink()
    size = sum(p.stat().st_size for p in config.JOKE_AUDIO_DIR.glob("*.ogg"))
    print(f"Recorded {len(todo)}, removed {len(stale)} old; {len(keep)} files, {size / 1e6:.1f} MB "
          f"in {config.JOKE_AUDIO_DIR.relative_to(REPO_ROOT)}/")


if __name__ == "__main__":
    main()
