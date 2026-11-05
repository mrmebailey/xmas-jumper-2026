from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

JOKES_FILE = REPO_ROOT / "jokes.txt"
MUSIC_DIR = REPO_ROOT / "music"
PHOTOS_DIR = REPO_ROOT / "photos"

SCREEN_W, SCREEN_H = 640, 480
FPS = 30

BG_COLOR = (8, 48, 28)
BUTTON_COLOR = (180, 30, 30)
BUTTON_ACTIVE_COLOR = (220, 50, 50)
BUTTON_BORDER_COLOR = (230, 190, 60)
TEXT_COLOR = (255, 255, 255)
TITLE_COLOR = (240, 200, 70)
ACCENT_COLOR = (0, 150, 70)

SNOW_COLOR = (235, 240, 255)
SNOWFLAKES = 40
LIGHTS_WIRE_COLOR = (20, 90, 40)
LIGHT_COLORS = [(230, 40, 40), (240, 200, 70), (60, 200, 90), (70, 140, 240)]

FONT_SIZE_COUNTDOWN = 400
FONT_SIZE_TITLE = 64
FONT_SIZE_LARGE = 52
FONT_SIZE_MEDIUM = 42
FONT_SIZE_SMALL = 34

ESPEAK_CMD = "espeak-ng"
ALSA_CARD = None  # set to a card index/name if "amixer sset Master" needs -c <card>

# Tried in order; whichever is found on PATH first is used to capture a photo.
CAMERA_CMDS = ["rpicam-still", "libcamera-still", "raspistill"]
# 1296x972 is the ov5647's binned mode: the full field of view (larger sizes
# like 1920x1080 crop in) with a quarter of the pixels, so it captures, encodes
# and loads much faster on the Pi Zero. 500ms is enough for exposure to settle;
# no EXIF thumbnail and fast colour denoise skip the slowest software steps.
# Note --denoise is rpicam/libcamera-still only; drop it if using raspistill.
CAMERA_ARGS = ["--width", "1296", "--height", "972", "-t", "500", "-q", "85",
               "--thumb", "none", "--denoise", "cdn_fast"]
PHOTO_COUNTDOWN_SECONDS = 3
PHOTO_PREVIEW_MS = 3000
# True crops the photo to fill the screen; False shows the whole photo.
PHOTO_PREVIEW_FILL = False  # how long a new photo is shown before returning to the camera screen
# Degrees anticlockwise to turn the photo for display (add 180 if it comes out upside down).
PHOTO_ROTATION = -90
