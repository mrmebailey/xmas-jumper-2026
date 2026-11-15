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
        self._closing = None  # a finished camera still shutting down

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
            [self.cmd, "-n", "-t", "0", "--signal", "-o", str(self._path),
             *config.CAMERA_ARGS, *config.CAMERA_WARM_ARGS],
            stdout=subprocess.DEVNULL,
            stderr=self._log,
        )

    def cancel(self):
        self._stop(wait=True)
        if self._closing is not None:
            # The camera can only be opened once, so the last one must be gone.
            self._closing.wait()
            self._closing = None

    def _stop(self, wait):
        if self._proc is not None and self._proc.poll() is None:
            self._proc.terminate()
            if wait:
                self._proc.wait()
            else:
                self._closing = self._proc
        self._proc = None
        if self._log is not None:
            self._log.close()
            self._log = None

    @staticmethod
    def _jpeg_done(path):
        """True once the file ends with the JPEG end-of-image marker."""
        try:
            with open(path, "rb") as f:
                f.seek(-2, 2)
                return f.read(2) == b"\xff\xd9"
        except OSError:  # missing, or not 2 bytes yet
            return False

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
        # JPEG to finish writing, then stop it.
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            time.sleep(0.03)
            if self._jpeg_done(path):
                break
            if self._proc.poll() is not None:
                if self._jpeg_done(path):
                    break
                # Died without a photo (e.g. signalled before it was ready).
                self.cancel()
                return self._one_shot()
        else:
            self.cancel()
            return None, "Camera took too long - try again"
        # Don't hold up showing the photo while the camera shuts down.
        self._stop(wait=False)
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
