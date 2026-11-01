import re
from pathlib import Path

_CAMEL_SPLIT = re.compile(r"(?<!^)(?=[A-Z])")


def _spaced(camel_text):
    return _CAMEL_SPLIT.sub(" ", camel_text)


def _display_name(path):
    stem = path.stem
    parts = stem.split("-", 2)
    if len(parts) == 3:
        _, artist, title = parts
        return f"{_spaced(artist)} — {_spaced(title)}"
    return _spaced(stem)


def load_playlist(music_dir):
    playlist = []
    for album_dir in sorted(Path(music_dir).iterdir()):
        if not album_dir.is_dir():
            continue
        for track in sorted(album_dir.glob("*.mp3")):
            playlist.append((_display_name(track), str(track)))
    return playlist
