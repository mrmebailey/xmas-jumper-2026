#!/bin/sh
cd "$(dirname "$0")"
# Only kicks in when unset (e.g. testing over SSH) - a real desktop
# autostart session already has these set correctly.
: "${DISPLAY:=:0}"
: "${XAUTHORITY:=$HOME/.Xauthority}"
export DISPLAY XAUTHORITY
exec python3 -m jukebox.main
