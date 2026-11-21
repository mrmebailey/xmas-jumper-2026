import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

JOKES_FILE = REPO_ROOT / "jokes.txt"
MUSIC_DIR = REPO_ROOT / "music"
PHOTOS_DIR = REPO_ROOT / "photos"

SCREEN_W, SCREEN_H = 640, 480
# The Pi Zero has one slow core shared with audio (Bluetooth encoding, speech),
# so redraw sparingly. While music or a joke is playing and nobody is touching
# the screen, the snow stops and the screen redraws only every LOW_POWER_FRAME_MS
# (a tap still wakes it instantly), leaving the CPU to the audio.
FPS = 12
LOW_POWER_FRAME_MS = 500
LOW_POWER_AFTER_INPUT_MS = 1500  # stay at full speed this long after a touch
# Every frame is pushed whole to the screen, which is what keeps Xorg and the
# kernel busy, so when nobody has touched the screen for IDLE_AFTER_INPUT_MS
# (long enough to cover the photo countdown) redraw at IDLE_FPS instead. The
# snow keeps falling at the same speed, just in bigger steps.
IDLE_FPS = 5
IDLE_AFTER_INPUT_MS = 5000
# Samples per audio chunk: bigger means fewer wake-ups (less CPU) for a little
# more delay, which doesn't matter for music.
AUDIO_BUFFER = 4096

BG_COLOR = (8, 48, 28)
BUTTON_COLOR = (180, 30, 30)
BUTTON_ACTIVE_COLOR = (220, 50, 50)
BUTTON_BORDER_COLOR = (230, 190, 60)
TEXT_COLOR = (255, 255, 255)
TITLE_COLOR = (240, 200, 70)
ACCENT_COLOR = (0, 150, 70)

# Button feel: squashed to this size while held, then a springy bounce back.
BUTTON_SQUASH = 0.88
BUTTON_BOUNCE_MS = 350
BUTTON_FIRE_DELAY_MS = 150  # lets the bounce show before the screen changes

SNOW_COLOR = (235, 240, 255)
SNOWFLAKES = 25
LIGHTS_WIRE_COLOR = (20, 90, 40)
LIGHT_COLORS = [(230, 40, 40), (240, 200, 70), (60, 200, 90), (70, 140, 240)]

FONT_SIZE_COUNTDOWN = 400
FONT_SIZE_TITLE = 64
FONT_SIZE_LARGE = 52
FONT_SIZE_MEDIUM = 42
FONT_SIZE_SMALL = 34
FONT_SIZE_TINY = 28

# Play songs in a random order (the Shuffle button on the music screen toggles it).
SHUFFLE = True
# Album art is taken from each MP3 and kept here, already shrunk, so the Pi
# only has to decode each cover once.
ART_CACHE_DIR = Path.home() / ".cache" / "jukebox" / "art"

# Naughty or Nice scans that came out naughty, for the Naughty List.
NAUGHTY_LIST_FILE = Path.home() / ".local" / "share" / "jukebox" / "naughty_list.json"
# Best game scores, kept between restarts.
SCORES_FILE = Path.home() / ".local" / "share" / "jukebox" / "scores.json"

ESPEAK_CMD = "espeak-ng"
# Father Christmas's voice (espeak-ng options): a deep male voice (-v ...+m3),
# low pitch (-p, 0-99, normally 50), slow and steady (-s, words a minute,
# normally 175) and loud (-a, 0-200, normally 100).
SANTA_VOICE = ["-v", "en-gb+m3", "-p", "30", "-s", "140", "-a", "160"]
# The punch line: deeper, slower and as loud as espeak goes.
PUNCH_LINE_VOICE = ["-v", "en-gb+m3", "-p", "24", "-s", "125", "-a", "200"]
# Silence between a joke's question and its punch line.
JOKE_PAUSE_MS = 2500
# Said after the punch line ("" for nothing).
JOKE_LAUGH = "Ho ho ho!"
# Jokes recorded in a natural Santa voice by tools/make_santa_voice.py (run on
# a laptop; the Pi is too slow to do it). Jokes without a recording here are
# spoken by espeak-ng instead, in the voices above.
JOKE_AUDIO_DIR = REPO_ROOT / "jokes_audio"
# Santa's own words around each recorded joke, picked at random (recorded
# by the same script, which also mixes sleigh bells under the opening line).
SANTA_INTROS = [
    "Ho ho! Here's one for you.",
    "Now then, listen closely.",
    "One of my elves told me this one.",
    "Gather round, here's a good one.",
    "Mrs Claus loves this one.",
    "Here's Rudolph's favourite joke!",
    "Ho ho, are you sitting comfortably?",
    "Right then, my dear. Here we go.",
]
SANTA_OUTROS = [
    "Oh ho ho, that's a good one!",
    "Don't tell Mrs Claus I told you that one!",
    "The elves never get that one!",
    "Oh, I do love a cracker joke!",
    "Ho ho! Have you been good this year?",
]
OUTRO_CHANCE = 0.5  # how often Santa adds one of those after his laugh
# Santa's laugh after the punch line (one picked at random if there are more).
SANTA_LAUGHS = ["Ho ho ho! Merry Christmas!"]
SPEECH_WAV = Path(tempfile.gettempdir()) / "jukebox-joke.wav"  # speech is rendered to jukebox-joke-0.wav, -1, ... then played
# When a speaker connects, wait this long (for PipeWire to finish setting it
# up with its own saved volume) and then set it to the slider's volume.
VOLUME_REAPPLY_MS = 2500
ALSA_CARD = None  # set to a card index/name if "amixer sset Master" needs -c <card>

# Tried in order; whichever is found on PATH first is used to capture a photo.
CAMERA_CMDS = ["rpicam-still", "libcamera-still", "raspistill"]
# Photos are a quick snapshot for the small screen, not a keepsake: the camera
# is sewn into a jumper and moves, so sharpness matters more than detail.
# 640x480 is the sensor's fastest full-view mode and still more than the
# screen shows (the photo is turned on its side, so it's shown 360x480).
# A short fixed shutter freezes movement ("sports mode"); the camera turns the
# gain up to make up the light, so indoor photos are a bit grainier.
# 10000us (1/100s) also lines up with UK mains lighting so there's no banding;
# try 5000 if it's still blurry, or 20000 if it's too dark.
CAMERA_SHUTTER_US = 10000
# No EXIF thumbnail and no colour denoise skip the slowest software steps.
# Note these are rpicam/libcamera-still options; raspistill's flags differ.
CAMERA_ARGS = ["--width", "640", "--height", "480", "-q", "75",
               "--shutter", str(CAMERA_SHUTTER_US),
               "--thumb", "none", "--denoise", "cdn_off"]
# Extra options for the camera kept running while the Camera screen is open. --zsl (zero
# shutter lag) runs the viewfinder at the photo size, so the shot is taken from
# a frame already captured instead of stopping and restarting the sensor in
# still mode. If the tool doesn't know an option the warm camera dies and the
# one-shot fallback (which doesn't use these) takes the photo instead.
# --framerate keeps the camera from using more CPU than it needs while it waits.
CAMERA_WARM_ARGS = ["--zsl", "--framerate", "15"]
# Exposure settling time when the camera wasn't warmed up during the countdown.
CAMERA_SETTLE_MS = 500
# Each photo adds a line here saying how it was taken and how long it took
# (and why, if the warmed-up camera failed), to see what's slow on the Pi.
CAMERA_LOG = Path(tempfile.gettempdir()) / "jukebox-camera.log"
PHOTO_COUNTDOWN_SECONDS = 3
PHOTO_PREVIEW_MS = 3000
# True crops the photo to fill the screen; False shows the whole photo.
PHOTO_PREVIEW_FILL = False
# The Off button on the main menu tries these in turn: the desktop user is
# normally allowed to power off; sudo is the fallback (never asks for a password).
SHUTDOWN_CMDS = [["systemctl", "poweroff"], ["sudo", "-n", "poweroff"]]
SHUTDOWN_LOG = Path(tempfile.gettempdir()) / "jukebox-shutdown.log"  # why, if it fails
DELETE_CONFIRM_MS = 3000  # how long the "Sure?" delete confirmation waits for a second tap  # how long a new photo is shown before returning to the camera screen
# Degrees anticlockwise to turn the photo for display (add 180 if it comes out upside down).
PHOTO_ROTATION = -90
# System Info screen (the "Info" button, bottom left of the main menu).
SPEAKER_FILE = Path.home() / ".jukebox-speaker"  # the speaker bt-speaker.sh keeps connected
QR_CODE_FILE = REPO_ROOT / "qr-code.png"  # shown on the right to be scanned
# The QR code is 148px with 4px squares, so 1.5x keeps every square a whole 6px.
QR_CODE_SIZE = 222
SYSINFO_REFRESH_MS = 3000
# Shown at the bottom of the System Info screen, highlighted in red.
FRONTIER_FINDINGS = "138 old libraries"
WARNING_COLOR = (255, 80, 80)
