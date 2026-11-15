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
DEV_PATH="/org/bluez/hci0/dev_$(echo "$MAC" | tr ':' '_')"

# Starting bluetoothctl takes a burst of CPU that the Pi Zero can't spare
# while it's playing music (it made the audio break up every 10s), so ask
# BlueZ directly over D-Bus, which costs almost nothing.
connected() {
  if command -v busctl >/dev/null 2>&1; then
    busctl --system get-property org.bluez "$DEV_PATH" org.bluez.Device1 Connected 2>/dev/null | grep -q true
  else
    bluetoothctl info "$MAC" 2>/dev/null | grep -q "Connected: yes"
  fi
}

while true; do
  if ! connected; then
    bluetoothctl connect "$MAC" >/dev/null 2>&1
  fi
  sleep 10
done
