#!/bin/sh
# Pull the latest code and restart the jukebox on the touchscreen without a reboot.
# Safe to run over SSH: the new copy is detached, so it keeps running after you log out.
cd "$(dirname "$0")"
git pull
pkill -f jukebox.main
setsid nohup ./run.sh >/dev/null 2>&1 &
echo "Jukebox restarted."
