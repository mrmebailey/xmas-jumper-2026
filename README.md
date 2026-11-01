# Christmas Jukebox

A touchscreen jukebox for a Raspberry Pi Zero W: pick **Jokes** (shown on screen and spoken aloud), **Music** (plays through `music/`), or **Camera** (snaps a photo with the spy cam) on a 2.8" capacitive touchscreen, through a USB speaker.

## Hardware assumed

- Raspberry Pi Zero W, Raspberry Pi OS Lite (no desktop needed)
- 2.8" capacitive IPS touchscreen, 480x640 native panel, run in landscape (640x480)
- USB speaker
- Camera module ("spy cam"), used by the Camera menu option

## TOUCHSCREEN DRIVER — TODO, vendor specific

This was written against a generic "2.8\" capacitive IPS touchscreen" with no specific vendor/driver known. Before this will work on real hardware you'll likely need to:

1. Identify the exact panel (check the product listing / any included driver CD or link).
2. Install whatever driver/overlay it needs (common patterns: a vendor `apt` package, or `git clone`-ing a driver repo and running its install script, or adding a `dtoverlay=` line to `/boot/config.txt`).
3. Confirm it shows up as a framebuffer (`/dev/fb0` or similar) and a touch input device (`/dev/input/eventX`, check with `evtest`).

This app assumes standard SDL/Linux input — once the panel enumerates as a normal framebuffer + HID touch device, no app-side driver code should be needed.

## CAMERA — TODO, module specific

The exact "spy cam" module/sensor is unknown too. The app shells out to whichever of `rpicam-still` / `libcamera-still` / `raspistill` is on `PATH` (covers current and older Raspberry Pi OS). If it's an official Pi Camera Module this should just work once enabled; a third-party sensor may need a `dtoverlay=` line in `/boot/config.txt` for that specific sensor first. Photos are saved to `photos/` in the repo, timestamped.

## Install on the Pi

```sh
git clone <this repo> ~/xmas-jumper-2026
cd ~/xmas-jumper-2026
./setup.sh
sudo reboot
```

`setup.sh` installs `python3-pygame`, `espeak-ng`, `alsa-utils`, a camera CLI tool (`rpicam-apps`/`libcamera-apps`), adds your user to the `video`/`input`/`audio` groups (needed for framebuffer/touch/camera/sound access without a desktop session), and installs+enables the `jukebox` systemd service so it starts on boot.

If your Pi login isn't `mark`, edit `User=`/`WorkingDirectory=` in `systemd/jukebox.service` before running `setup.sh` (or after, then `sudo systemctl daemon-reload`).

## Running / testing on a dev machine

```sh
pip install pygame
python3 -m jukebox.main
```

This runs in an ordinary window (no `SDL_VIDEODRIVER` override, that's only set in the systemd unit), so you can click with a mouse to simulate touch. You'll need `espeak-ng` installed locally too if you want to hear jokes spoken.

## Layout

- `jukebox/main.py` — app entry point, state machine, main loop
- `jukebox/states/` — Menu, Jokes, Music, Camera screens
- `jukebox/audio.py` — music playback + text-to-speech + volume
- `jukebox/camera.py` — shells out to the camera CLI tool, saves to `photos/`
- `jukebox/jokes_loader.py`, `jukebox/music_loader.py` — parse `jokes.txt` / scan `music/`
- `systemd/jukebox.service` — boots straight into the app, no desktop login

Games are a planned future addition — not implemented yet.
