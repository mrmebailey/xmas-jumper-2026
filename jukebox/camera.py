import shutil
import signal
import subprocess
import tempfile
import time
from datetime import datetime

from . import config

# These take a photo on SIGUSR1 when run with --signal; raspistill's flags differ.
_SIGNAL_CMDS = {"rpicam-still", "libcamera-still"}


class CameraManager:
    """Takes photos with the camera CLI tool.

    Starting the tool (loading libcamera, opening the sensor, settling exposure)
    is most of the wait on a Pi Zero, so warm_up() starts it in signal mode
    during the countdown and capture() just tells it to take the picture.
    Without a warm-up, or if that fails, capture() falls back to a one-shot run.
    """

    def __init__(self):
        config.PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
        self.cmd = next((c for c in config.CAMERA_CMDS if shutil.which(c)), None)
        self._proc = None
        self._path = None
        self._log = None

    @staticmethod
    def _new_path():
        return config.PHOTOS_DIR / datetime.now().strftime("photo_%Y%m%d_%H%M%S.jpg")

    def warm_up(self):
        self.cancel()
        if self.cmd not in _SIGNAL_CMDS:
            return
        self._path = self._new_path()
        self._log = tempfile.TemporaryFile()
        self._proc = subprocess.Popen(
            [self.cmd, "-n", "-t", "0", "--signal", "-o", str(self._path), *config.CAMERA_ARGS],
            stdout=subprocess.DEVNULL,
            stderr=self._log,
        )

    def cancel(self):
        if self._proc is not None and self._proc.poll() is None:
            self._proc.terminate()
            self._proc.wait()
        self._proc = None
        if self._log is not None:
            self._log.close()
            self._log = None

    def capture(self):
        """Take a photo, returning (path, None) or (None, error message)."""
        if self.cmd is None:
            return None, "No camera tool found (install libcamera-apps/rpicam-apps)"
        if self._proc is None or self._proc.poll() is not None:
            # Never warmed up, or the warm camera died (e.g. an option it doesn't know).
            self.cancel()
            return self._one_shot()

        path = self._path
        self._proc.send_signal(signal.SIGUSR1)
        # In signal mode the tool keeps running for the next photo, so wait for the
        # file to finish writing (size stops changing), then stop it.
        deadline = time.monotonic() + 10
        last_size = -1
        while time.monotonic() < deadline:
            time.sleep(0.15)
            size = path.stat().st_size if path.exists() else 0
            if size > 0 and size == last_size:
                break
            if self._proc.poll() is not None:
                if size > 0:
                    break
                # Died without a photo (e.g. signalled before it was ready).
                self.cancel()
                return self._one_shot()
            last_size = size
        else:
            self.cancel()
            return None, "Camera took too long - try again"
        self.cancel()
        return path, None

    def _one_shot(self):
        path = self._new_path()
        try:
            subprocess.run(
                [self.cmd, "-n", "-t", str(config.CAMERA_SETTLE_MS), "-o", str(path), *config.CAMERA_ARGS],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
        except subprocess.CalledProcessError as e:
            return None, f"Camera failed: {e.stderr.decode(errors='replace').strip()[:80]}"
        return path, None
