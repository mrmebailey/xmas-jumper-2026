import shutil
import signal
import subprocess
import tempfile
import time
from datetime import datetime

from . import config

# These take a photo on SIGUSR1 when run with --signal; raspistill's flags differ.
_SIGNAL_CMDS = {"rpicam-still", "libcamera-still"}


def _log(msg):
    """Add a line to the camera log; never let logging break taking a photo."""
    try:
        with open(config.CAMERA_LOG, "a") as f:
            f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}\n")
    except OSError:
        pass


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
        self._started_at = 0

    @staticmethod
    def _new_path():
        return config.PHOTOS_DIR / datetime.now().strftime("photo_%Y%m%d_%H%M%S.jpg")

    def warm_up(self):
        self.cancel()
        if self.cmd not in _SIGNAL_CMDS:
            return
        self._path = self._new_path()
        self._log = tempfile.TemporaryFile()
        self._started_at = time.monotonic()
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

    def reap(self):
        """Clear away the last camera once it has shut down. Called every frame."""
        if self._closing is not None and self._closing.poll() is not None:
            self._closing = None

    def _warm_errors(self):
        """The last few lines the warmed-up camera wrote to stderr."""
        if self._log is None:
            return ""
        self._log.seek(0)
        lines = self._log.read().decode(errors="replace").strip().splitlines()
        return " | ".join(lines[-3:])

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
        if self._proc is None:
            _log("not warmed up, taking a one-shot photo")
            return self._one_shot()
        if self._proc.poll() is not None:
            # The warm camera died, e.g. on an option it doesn't know.
            _log(f"warm camera had quit (exit {self._proc.returncode}): {self._warm_errors()}")
            self.cancel()
            return self._one_shot()

        path = self._path
        warm_for = time.monotonic() - self._started_at
        started = time.monotonic()
        self._proc.send_signal(signal.SIGUSR1)
        # In signal mode the tool keeps running for the next photo, so wait for the
        # JPEG to finish writing, then stop it.
        deadline = started + 10
        while time.monotonic() < deadline:
            time.sleep(0.03)
            if self._jpeg_done(path):
                break
            if self._proc.poll() is not None:
                if self._jpeg_done(path):
                    break
                # Died without a photo (e.g. signalled before it was ready).
                _log(f"warm camera quit without a photo: {self._warm_errors()}")
                self.cancel()
                return self._one_shot()
        else:
            _log(f"warm camera took over 10s: {self._warm_errors()}")
            self.cancel()
            return None, "Camera took too long - try again"
        _log(f"warm photo in {(time.monotonic() - started) * 1000:.0f}ms "
             f"(camera started {warm_for:.1f}s before)")
        # Don't hold up showing the photo while the camera shuts down.
        self._stop(wait=False)
        return path, None

    def _one_shot(self):
        path = self._new_path()
        started = time.monotonic()
        try:
            subprocess.run(
                [self.cmd, "-n", "-t", str(config.CAMERA_SETTLE_MS), "-o", str(path), *config.CAMERA_ARGS],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
        except subprocess.CalledProcessError as e:
            error = e.stderr.decode(errors="replace").strip()
            _log(f"one-shot failed: {error[-300:]}")
            return None, f"Camera failed: {error[:80]}"
        _log(f"one-shot photo in {(time.monotonic() - started) * 1000:.0f}ms")
        return path, None
