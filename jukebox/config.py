from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

JOKES_FILE = REPO_ROOT / "jokes.txt"
MUSIC_DIR = REPO_ROOT / "music"
PHOTOS_DIR = REPO_ROOT / "photos"

SCREEN_W, SCREEN_H = 640, 480
FPS = 30

BG_COLOR = (10, 30, 20)
BUTTON_COLOR = (180, 30, 30)
BUTTON_ACTIVE_COLOR = (220, 50, 50)
TEXT_COLOR = (255, 255, 255)
ACCENT_COLOR = (0, 150, 70)

FONT_SIZE_LARGE = 40
FONT_SIZE_MEDIUM = 28
FONT_SIZE_SMALL = 22

ESPEAK_CMD = "espeak-ng"
ALSA_CARD = None  # set to a card index/name if "amixer sset Master" needs -c <card>

# Tried in order; whichever is found on PATH first is used to capture a photo.
CAMERA_CMDS = ["rpicam-still", "libcamera-still", "raspistill"]
PHOTO_PREVIEW_MS = 3000  # how long a new photo is shown before returning to the camera screen
