# Christmas Jukebox

A touchscreen jukebox for a Raspberry Pi Zero W: pick **Jokes** (shown on screen and spoken aloud), **Music** (plays through `music/`), or **Camera** (snaps a photo with the spy cam) on a 2.8" capacitive touchscreen, through a USB speaker.

## Hardware assumed

- Raspberry Pi Zero W, Raspberry Pi OS **Desktop** (not Lite) — the app runs as a fullscreen window on top of the desktop session, autologin to the desktop is expected to already be configured
- 2.8" capacitive IPS touchscreen, 480x640 native panel, run in landscape (640x480)
- USB speaker
- Camera module ("spy cam"), used by the Camera menu option

## TOUCHSCREEN DRIVER — vendor specific

This was written against a generic "2.8\" capacitive IPS touchscreen" with no specific vendor/driver known, but you'll need its driver/overlay installed and working (vendor `apt` package, or a `git clone`d driver repo's install script, or a `dtoverlay=` line in `/boot/config.txt`) so the panel shows the desktop and the display's framebuffer is `/dev/fb0` or `/dev/fb1`. Once the desktop itself renders correctly on the panel (confirmed by seeing the normal Pi desktop there), the app just runs as an ordinary fullscreen X11 window — no raw framebuffer/evdev code needed on our side, X handles the touch input directly.

## CAMERA — TODO, module specific

The exact "spy cam" module/sensor is unknown too. The app shells out to whichever of `rpicam-still` / `libcamera-still` / `raspistill` is on `PATH` (covers current and older Raspberry Pi OS). If it's an official Pi Camera Module this should just work once enabled; a third-party sensor may need a `dtoverlay=` line in `/boot/config.txt` for that specific sensor first. Photos are saved to `photos/` in the repo, timestamped.

## Install on the Pi

```sh
git clone <this repo> ~/xmas-jumper-2026
cd ~/xmas-jumper-2026
./setup.sh
sudo reboot
```

`setup.sh` installs `python3-pygame`, `espeak-ng`, `alsa-utils`, a camera CLI tool (`rpicam-apps`/`libcamera-apps`), adds your user to the `video`/`audio` groups (camera/sound access), and writes `~/.config/autostart/jukebox.desktop` so the desktop session launches `run.sh` on login. It figures out the repo path itself (no hardcoded paths to edit).

To launch it immediately without logging out/in: `./run.sh`. Press `Esc` to quit back to the desktop.

### Running under xinit (no desktop)

The Pi in use boots to a console and starts X with `xinit`, which runs `~/.xinitrc`. Link it to the repo's `xinitrc` once:

```sh
ln -sf ~/xmas-jumper-2026/xinitrc ~/.xinitrc
```

It keeps the jukebox in a restart loop (xinit would otherwise shut X down as soon as the jukebox exits), so `Esc` restarts the app rather than quitting it.

To pick up new code without a reboot: `./refresh.sh` (pulls, then stops the running jukebox so the `xinitrc` loop starts the new code; safe to run over SSH).

## Running / testing on a dev machine

```sh
pip install pygame
python3 -m jukebox.main
```

This opens fullscreen on whatever display you're on — click with a mouse to simulate touch, `Esc` to quit. You'll need `espeak-ng` installed locally too if you want to hear jokes spoken.

## Layout

- `jukebox/main.py` — app entry point, state machine, main loop
- `jukebox/states/` — Menu, Jokes, Music, Camera screens
- `jukebox/audio.py` — music playback + text-to-speech + volume
- `jukebox/camera.py` — shells out to the camera CLI tool, saves to `photos/`
- `jukebox/jokes_loader.py`, `jukebox/music_loader.py` — parse `jokes.txt` / scan `music/`
- `refresh.sh` — `git pull` and restart the running jukebox without a reboot
- `xinitrc` — X session for xinit: disables blanking, starts openbox, runs the jukebox in a restart loop
- `run.sh` — launched by `xinitrc` (or the desktop autostart entry `setup.sh` creates); `cd`s to the repo and runs the app

Games are a planned future addition — not implemented yet.
