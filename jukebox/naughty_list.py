"""Santa's Naughty List: every scan that came out naughty, with its photo and
how naughty it was, saved so the list survives a restart. A photo deleted
in the Photos screen drops off the list."""
import json
import os
import time

from . import config

_entries = None


def _load():
    global _entries
    if _entries is None:
        try:
            _entries = json.loads(config.NAUGHTY_LIST_FILE.read_text())
        except (OSError, ValueError):
            _entries = []
    return _entries


def add(photo_path, score):
    entries = _load()
    entries.append({"photo": photo_path.name, "score": score, "time": time.time()})
    try:
        config.NAUGHTY_LIST_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = config.NAUGHTY_LIST_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(entries))
        os.replace(tmp, config.NAUGHTY_LIST_FILE)
    except OSError:
        pass


def ranked():
    """Naughtiest first (the earlier scan first on a tie), only those whose
    photo is still there."""
    entries = [e for e in _load() if (config.PHOTOS_DIR / e["photo"]).exists()]
    return sorted(entries, key=lambda e: (-e["score"], e["time"]))


def rank_of(photo_path):
    """Where this photo sits on the list (1 = naughtiest), or None."""
    for i, entry in enumerate(ranked(), 1):
        if entry["photo"] == photo_path.name:
            return i
    return None
