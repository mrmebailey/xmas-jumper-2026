import re
from collections import namedtuple
from pathlib import Path

_CAMEL_SPLIT = re.compile(r"(?<!^)(?=[A-Z])")

Track = namedtuple("Track", "title artist path")


def _spaced(camel_text):
    return _CAMEL_SPLIT.sub(" ", camel_text)


def _track(path):
    # Files are named like 07-ChrisRea-DrivingHomeForChristmas.mp3.
    parts = path.stem.split("-", 2)
    if len(parts) == 3:
        _, artist, title = parts
        return Track(_spaced(title), _spaced(artist), str(path))
    return Track(_spaced(path.stem), "", str(path))


def load_playlist(music_dir):
    playlist = []
    for album_dir in sorted(Path(music_dir).iterdir()):
        if not album_dir.is_dir():
            continue
        for track in sorted(album_dir.glob("*.mp3")):
            playlist.append(_track(track))
    return playlist
