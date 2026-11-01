#!/bin/sh
# Run this on the Raspberry Pi (not on a dev machine) after cloning the repo.
set -e

sudo apt-get update
sudo apt-get install -y python3-pygame espeak-ng alsa-utils
# Camera CLI tool: package name varies by OS version, try the newer name first.
sudo apt-get install -y rpicam-apps || sudo apt-get install -y libcamera-apps || \
  echo "Could not install a camera CLI tool automatically - install libcamera-apps/rpicam-apps manually."

sudo usermod -aG video,input,audio "$USER"

sudo cp systemd/jukebox.service /etc/systemd/system/jukebox.service
sudo systemctl daemon-reload
sudo systemctl enable jukebox.service

echo "Installed. Reboot (or 'sudo systemctl start jukebox') to launch the jukebox."
echo "If this user isn't 'pi', edit User=/WorkingDirectory in /etc/systemd/system/jukebox.service first."
