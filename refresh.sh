#!/bin/sh
# Pull the latest code and restart the jukebox on the touchscreen without a reboot.
# Safe to run over SSH: the new copy is detached, so it keeps running after you log out.
cd "$(dirname "$0")"
LOG=/tmp/jukebox.log
git pull
pkill -f jukebox.main
# Wait (up to 5s) for the old copy to exit so it releases the screen and sound card.
i=0
while pgrep -f jukebox.main >/dev/null && [ "$i" -lt 50 ]; do
  sleep 0.1
  i=$((i + 1))
done
setsid nohup ./run.sh >"$LOG" 2>&1 </dev/null &
sleep 3
if pgrep -f jukebox.main >/dev/null; then
  echo "Jukebox restarted (output in $LOG)."
else
  echo "Jukebox failed to start:"
  cat "$LOG"
fi
