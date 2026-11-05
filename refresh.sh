#!/bin/sh
# Pull the latest code and restart the jukebox on the touchscreen without a reboot.
# Safe to run over SSH: the new copy is detached, so it keeps running after you log out.
cd "$(dirname "$0")"
LOG=/tmp/jukebox.log
git pull

# The autostart copy runs inside the desktop session, which has the display
# settings an SSH login lacks (X11 vs Wayland, auth, session bus). Borrow them
# from a desktop process so the new copy starts exactly as it would at login.
session_pid=$(pgrep -n -u "$(id -u)" -x 'labwc|wayfire|openbox|lxsession|pcmanfm|lxpanel|wf-panel-pi')
if [ -n "$session_pid" ]; then
  echo "Using desktop session from $(cat /proc/"$session_pid"/comm) (pid $session_pid)"
  for var in DISPLAY WAYLAND_DISPLAY XAUTHORITY XDG_RUNTIME_DIR XDG_SESSION_TYPE DBUS_SESSION_BUS_ADDRESS; do
    value=$(tr '\0' '\n' <"/proc/$session_pid/environ" | sed -n "s/^$var=//p")
    if [ -n "$value" ]; then
      export "$var=$value"
      echo "  $var=$value"
    fi
  done
else
  echo "No desktop session found - falling back to run.sh defaults."
fi

pkill -f jukebox.main
# Wait (up to 5s) for the old copy to exit so it releases the screen and sound card.
i=0
while pgrep -f jukebox.main >/dev/null && [ "$i" -lt 50 ]; do
  sleep 0.1
  i=$((i + 1))
done
# Unbuffered so the log fills in as it happens rather than when Python exits.
PYTHONUNBUFFERED=1 setsid nohup ./run.sh >"$LOG" 2>&1 </dev/null &
sleep 3
if pgrep -f jukebox.main >/dev/null; then
  echo "Jukebox restarted (output in $LOG)."
else
  echo "Jukebox failed to start:"
  cat "$LOG"
fi
