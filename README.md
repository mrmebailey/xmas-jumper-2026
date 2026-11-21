# Christmas Jukebox

A touchscreen jukebox sewn into a Christmas jumper, run by a Raspberry Pi Zero W on a 2.8" capacitive touchscreen. From the main menu: **Jokes** (Father Christmas reads them aloud), **Music** (plays `music/` through a Bluetooth speaker), **Games**, **Camera** and **Photos** (snap and browse photos with the spy cam), **Naughty or Nice** (with a Naughty List), plus **Info** (system status and a QR code) and **Off** in the bottom corners.

## Hardware

| Part | Notes |
| --- | --- |
| [Raspberry Pi Zero W](https://thepihut.com/products/raspberry-pi-zero-w) | One slow core and 512MB RAM, so the app is tuned to leave CPU for the audio. A [Zero 2 W](https://thepihut.com/products/raspberry-pi-zero-2) is a faster drop-in. Needs a soldered GPIO header for the screen. |
| [2.8" Capacitive IPS LCD Touchscreen (480×640)](https://thepihut.com/products/2-8-capacitive-ips-lcd-touchscreen-for-raspberry-pi-480x640) | Waveshare, plugs onto the GPIO header (DPI display, I2C touch). Portrait natively; run in landscape (640x480). |
| [Zero Spy Camera for Raspberry Pi Zero](https://thepihut.com/products/zero-spy-camera-for-raspberry-pi-zero) | Tiny 5MP camera on the Zero's camera connector. Now discontinued; a [ZeroCam](https://thepihut.com/products/zerocam-camera-for-raspberry-pi-zero) fits the same connector. |
| Bluetooth speaker | Any; paired once (see below) and kept connected by `bt-speaker.sh`. |
| USB power bank | Powers the Pi through its micro USB power port. The Info screen warns if the voltage drops too low. |

## Software

The Pi runs **Raspberry Pi OS Lite** (no desktop): it boots to the console, logs in automatically and starts a bare X server with `xinit`. X runs just `openbox` and the jukebox, fullscreen. A full desktop is too much for the Pi Zero alongside Bluetooth audio.

### Touchscreen driver

Set up the screen with Waveshare's instructions for this panel (its `dtoverlay=` lines in `/boot/firmware/config.txt`) until the console shows on it, and rotate it to landscape. After that, X draws on it and handles touch itself; the app is an ordinary fullscreen X11 window with no screen-specific code.

### Camera

The app shells out to whichever of `rpicam-still` / `libcamera-still` / `raspistill` is on `PATH` (covers current and older Raspberry Pi OS). Photos are saved to `photos/` in the repo, timestamped. Camera settings (shutter speed, size, rotation) are in `jukebox/config.py`.

## Install on the Pi

```sh
sudo apt-get install -y git xserver-xorg xinit openbox
git clone <this repo> ~/xmas-jumper-2026
cd ~/xmas-jumper-2026
./setup.sh
```

`setup.sh` installs `python3-pygame`, `espeak-ng`, `alsa-utils`, a camera CLI tool (`rpicam-apps`/`libcamera-apps`), adds your user to the `video`/`audio` groups (camera/sound access) and turns off the serial login console on the GPIO pins (noise there kept its login prompt busy and made the music break up; Bluetooth is unaffected). It also writes a desktop autostart entry, which isn't used when running under `xinit`.

### Start the jukebox on boot

Link the repo's `xinitrc` as your X session:

```sh
ln -sf ~/xmas-jumper-2026/xinitrc ~/.xinitrc
```

Turn on console autologin (`sudo raspi-config nonint do_boot_behaviour B2`, or raspi-config > System Options > Boot / Auto Login > Console Autologin), then start X when that login happens on the screen by adding this to `~/.bash_profile`:

```sh
[ -z "$DISPLAY" ] && [ "$(tty)" = /dev/tty1 ] && exec startx
```

`sudo reboot` and the jukebox comes up on the touchscreen. `xinitrc` turns off screen blanking, starts `openbox` and `bt-speaker.sh`, and keeps the jukebox in a restart loop (xinit would otherwise shut X down as soon as the jukebox exits), so `Esc` or a crash restarts the app rather than leaving a blank screen. SSH logins aren't on tty1, so they get a normal shell.

To pick up new code without a reboot: `./refresh.sh` (pulls, then stops the running jukebox so the `xinitrc` loop starts the new code; safe to run over SSH).

### Bluetooth speaker

Pair once over SSH (speaker in pairing mode), then save its address so `bt-speaker.sh` keeps it connected:

```sh
sudo apt-get install -y libspa-0.2-bluetooth   # PipeWire's Bluetooth audio support
bluetoothctl                                   # then: power on, agent on, default-agent,
                                               # scan on, pair <MAC>, trust <MAC>, connect <MAC>, exit
echo <MAC> > ~/.jukebox-speaker
wpctl status                                   # find the speaker's number under Sinks
wpctl set-default <number>                     # remembered, and used again whenever it reconnects
```

The Info screen shows whether it's connected and, if the speaker reports it, its battery level.

### QR code

`qr-code.png` is shown on the Info screen to be scanned. Replace it with your own (keep it 148x148 with 4px squares, or change `QR_CODE_SIZE` in `jukebox/config.py`).

## Running / testing on a dev machine

```sh
pip install pygame
python3 -m jukebox.main
```

This opens fullscreen on whatever display you're on — click with a mouse to simulate touch, `Esc` to quit. You'll need `espeak-ng` installed locally too if you want to hear jokes spoken.

## Layout

- `jukebox/main.py` — app entry point, state machine, main loop
- `jukebox/states/` — Menu, System Info (CPU, memory, disk, speaker, Wi-Fi, SSH, power and the `qr-code.png` QR code; the Info button bottom left), Jokes, Music, Songs (pick a song), Camera, Photos, Games (picker), Naughty or Nice and the Naughty List (naughtiest scans ranked, saved in `~/.local/share/jukebox/naughty_list.json`) screens
- `jukebox/games/` — Reindeer Snake, Present Catch, Bauble Pop, Memory Match, their shared base and the shape-drawn Christmas sprites; best scores saved in `~/.local/share/jukebox/scores.json`
- `jukebox/audio.py` — music playback (shuffle, moves on when a song ends) + text-to-speech + volume
- `jukebox/art.py` — album covers from the MP3s' tags, shrunk once and cached in `~/.cache/jukebox/art`
- `jukebox/sysinfo.py` — reads the System Info screen's details (CPU, memory, disk, speaker, Wi-Fi, SSH, power)
- `jukebox/camera.py` — shells out to the camera CLI tool, saves to `photos/`
- `jukebox/jokes_loader.py`, `jukebox/music_loader.py` — parse `jokes.txt` / scan `music/`
- `refresh.sh` — `git pull` and restart the running jukebox without a reboot
- `bt-speaker.sh` — keeps the Bluetooth speaker in `~/.jukebox-speaker` connected (started by `xinitrc`)
- `xinitrc` — X session for xinit: disables blanking, starts openbox, runs the jukebox in a restart loop
- `run.sh` — launched by `xinitrc`; `cd`s to the repo and runs the app

