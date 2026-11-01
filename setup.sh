#!/bin/sh
# Run this on the Raspberry Pi (not on a dev machine) after cloning the repo.
# Assumes Raspberry Pi OS Desktop with autologin to the desktop already configured
# (raspi-config > System Options > Boot / Auto Login) - this script makes the
# jukebox launch on top of that desktop session, it doesn't set up autologin itself.
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

sudo apt-get update
sudo apt-get install -y python3-pygame espeak-ng alsa-utils
# Camera CLI tool: package name varies by OS version, try the newer name first.
sudo apt-get install -y rpicam-apps || sudo apt-get install -y libcamera-apps || \
  echo "Could not install a camera CLI tool automatically - install libcamera-apps/rpicam-apps manually."

sudo usermod -aG audio,video "$USER"

mkdir -p "$HOME/.config/autostart"
cat > "$HOME/.config/autostart/jukebox.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Christmas Jukebox
Exec=$REPO_DIR/run.sh
X-GNOME-Autostart-enabled=true
EOF

echo "Installed. Log out/in or reboot to launch the jukebox automatically."
echo "To test right now without rebooting: $REPO_DIR/run.sh"
