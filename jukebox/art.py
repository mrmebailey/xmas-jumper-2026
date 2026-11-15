"""Album art from the cover picture embedded in each MP3's ID3 tag.

The covers are big (600x600 PNGs, ~512KB) and the same for every song on an
album. Decoding one takes a noticeable moment on the Pi Zero, so each cover
is decoded once, shrunk, and saved under ART_CACHE_DIR named after a hash of
the picture; after that it loads instantly, even after a restart.
"""
import hashlib
import io
import json
import os
import struct

import pygame

from . import config

_MAX_TAG = 4 * 1024 * 1024  # don't read silly-sized tags
_INDEX = "index.json"

_surfaces = {}  # (picture hash, size) -> Surface
_hashes = None  # "path|mtime|size" -> picture hash, or "" for no picture


def _syncsafe(b):
    return (b[0] << 21) | (b[1] << 14) | (b[2] << 7) | b[3]


def _read_picture(path):
    """The bytes of the first embedded picture, or None."""
    with open(path, "rb") as f:
        header = f.read(10)
        if len(header) < 10 or header[:3] != b"ID3" or header[3] not in (3, 4):
            return None
        version = header[3]
        tag = f.read(min(_syncsafe(header[6:10]), _MAX_TAG))
    pos = 0
    while pos + 10 <= len(tag):
        frame_id = tag[pos:pos + 4]
        if not frame_id.strip(b"\0"):
            break  # padding
        size_bytes = tag[pos + 4:pos + 8]
        size = _syncsafe(size_bytes) if version == 4 else struct.unpack(">I", size_bytes)[0]
        if frame_id == b"APIC":
            return _picture_data(tag[pos + 10:pos + 10 + size])
        pos += 10 + size
    return None


def _picture_data(body):
    # APIC: encoding, MIME type\0, picture type, description\0, picture data.
    if len(body) < 4:
        return None
    encoding = body[0]
    mime_end = body.find(b"\0", 1)
    if mime_end < 0:
        return None
    rest = body[mime_end + 2:]
    if encoding in (1, 2):  # UTF-16 description ends with \0\0 on a 2-byte boundary
        i = 0
        while i + 1 < len(rest) and rest[i:i + 2] != b"\0\0":
            i += 2
        return rest[i + 2:] or None
    end = rest.find(b"\0")
    return rest[end + 1:] if end >= 0 else None


def _load_index():
    global _hashes
    if _hashes is None:
        try:
            _hashes = json.loads((config.ART_CACHE_DIR / _INDEX).read_text())
        except (OSError, ValueError):
            _hashes = {}
    return _hashes


def _save_index():
    try:
        config.ART_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        tmp = config.ART_CACHE_DIR / (_INDEX + ".tmp")
        tmp.write_text(json.dumps(_hashes))
        os.replace(tmp, config.ART_CACHE_DIR / _INDEX)
    except OSError:
        pass


def cover(path, size):
    """The song's cover as a size x size Surface, or None if it has none."""
    try:
        stat = os.stat(path)
    except OSError:
        return None
    index = _load_index()
    key = f"{path}|{stat.st_mtime_ns}|{stat.st_size}"
    picture_hash = index.get(key)
    picture = None
    if picture_hash is None:
        try:
            picture = _read_picture(path)
        except OSError:
            picture = None
        picture_hash = hashlib.sha1(picture).hexdigest() if picture else ""
        index[key] = picture_hash
        _save_index()
    if not picture_hash:
        return None

    surface = _surfaces.get((picture_hash, size))
    if surface is not None:
        return surface
    cached = config.ART_CACHE_DIR / f"{picture_hash}_{size}.png"
    try:
        surface = pygame.image.load(str(cached))
    except (OSError, pygame.error):
        if picture is None:
            try:
                picture = _read_picture(path)
            except OSError:
                picture = None
        if not picture:
            return None
        try:
            hint = "cover.png" if picture.startswith(b"\x89PNG") else "cover.jpg"
            full = pygame.image.load(io.BytesIO(picture), hint)
        except pygame.error:
            return None
        surface = pygame.transform.smoothscale(full, (size, size))
        try:
            config.ART_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            pygame.image.save(surface, str(cached))
        except (OSError, pygame.error):
            pass
    if pygame.display.get_surface() is not None:
        surface = surface.convert()
    _surfaces[(picture_hash, size)] = surface
    return surface
