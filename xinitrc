#!/bin/sh
# X session for the jukebox, started by xinit on the Pi's console.
# Install with: ln -sf ~/xmas-jumper-2026/xinitrc ~/.xinitrc
REPO_DIR="$(dirname "$(readlink -f "$0")")"

# Disable screen blanking and power management
xset s off
xset -dpms
xset s noblank

# Start minimal window manager in background
openbox &

# xinit shuts X down when this script ends, so keep the jukebox in a loop:
# when it exits (crash, Esc, or refresh.sh stopping it) it starts again
# with the latest code while X stays up.
while true; do
  /bin/sh "$REPO_DIR/run.sh"
  sleep 1
done
