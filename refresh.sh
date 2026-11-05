#!/bin/sh
# Pull the latest code and restart the jukebox on the touchscreen without a reboot.
# Relies on the restart loop in xinitrc: stopping the running copy makes the
# loop start the new code inside the same X session.
cd "$(dirname "$0")"
git pull

old_pid=$(pgrep -of jukebox.main)
if [ -z "$old_pid" ]; then
  echo "Jukebox isn't running - reboot the Pi to start it."
  exit 1
fi
pkill -f jukebox.main

# Wait (up to 10s) for the loop to start a new copy.
i=0
while [ "$i" -lt 100 ]; do
  new_pid=$(pgrep -nf jukebox.main)
  if [ -n "$new_pid" ] && [ "$new_pid" != "$old_pid" ]; then
    echo "Jukebox restarted."
    exit 0
  fi
  sleep 0.1
  i=$((i + 1))
done
echo "Jukebox didn't come back. Is ~/.xinitrc linked to this repo's xinitrc? Reboot to recover."
exit 1
