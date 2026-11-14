#!/bin/sh
# Keep the paired Bluetooth speaker connected: whenever it's disconnected
# (switched off, out of range), retry every 10s so it's picked up again as
# soon as it comes back. Started in the background by xinitrc.
# The speaker's address goes in ~/.jukebox-speaker, e.g. AA:BB:CC:DD:EE:FF
MAC=$(cat "$HOME/.jukebox-speaker" 2>/dev/null | tr -d '[:space:]')
if [ -z "$MAC" ]; then
  echo "No speaker set in ~/.jukebox-speaker - not managing Bluetooth."
  exit 0
fi

while true; do
  if ! bluetoothctl info "$MAC" 2>/dev/null | grep -q "Connected: yes"; then
    bluetoothctl connect "$MAC" >/dev/null 2>&1
  fi
  sleep 10
done
