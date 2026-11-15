import shutil
import signal
import subprocess
import tempfile
import time
from datetime import datetime

from . import config

# These take a photo on SIGUSR1 when run with --signal; raspistill's flags differ.
_SIGNAL_CMDS = {"rpicam-still", "libcamera-still"}
# After the warm camera quits by itself, wait this long before starting it again.
_RETRY_AFTER_S = 10
# Ask again this often until the camera starts writing the photo.
_RESIGNAL_S = 0.3


def _log(msg):
    """Add a line to the camera log; never let logging break taking a photo."""
    try:
        with open(config.CAMERA_LOG, "a") as f:
            f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}\n")
    except OSError:
        pass


def _ignore_photo_signal():
    # Runs in the camera process before it starts. The tool only sets up its
    # SIGUSR1 handler once the camera is running, and until then the signal
    # would kill it; ignored, an early signal is just dropped (and resent).
    signal.signal(signal.SIGUSR1, signal.SIG_IGN)


class CameraManager:
    """Takes photos with the camera CLI tool.

    Starting the tool (loading libcamera, opening the sensor, settling exposure)
    takes about 5s on a Pi Zero, longer than the countdown, so keep_warm() starts
    it in signal mode as soon as the Camera screen opens and capture() just
    tells it to take the picture. If there's no warm camera, or it fails,
    capture() falls back to a one-shot run.
    """

    def __init__(self):
        config.PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
        self.cmd = next((c for c in config.CAMERA_CMDS if shutil.which(c)), None)
        # The warm camera writes here; the photo is renamed when it's taken.
        # Not photo_*.jpg, so the photo viewer never lists it.
        self._warm_path = config.PHOTOS_DIR / ".warm.jpg"
        self._proc = None
        self._log = None
        self._closing = None  # a finished camera still shutting down
        self._started_at = 0
        self._retry_at = 0

    @staticmethod
    def _new_path():
        return config.PHOTOS_DIR / datetime.now().strftime("photo_%Y%m%d_%H%M%S.jpg")

    def keep_warm(self):
        """Have a camera running and ready for the next photo. Called every frame
        while the Camera screen is waiting; does nothing when one already is."""
        if self.cmd not in _SIGNAL_CMDS:
            return
        if self._closing is not None:
            if self._closing.poll() is None:
                return  # the last camera still has the sensor open
            self._closing = None
        if self._proc is not None:
            if self._proc.poll() is None:
                return
            _log(f"warm camera quit (exit {self._proc.returncode}): {self._warm_errors()}")
            self._stop(wait=True)
            self._retry_at = time.monotonic() + _RETRY_AFTER_S
        if time.monotonic() < self._retry_at:
            return
        self._warm_path.unlink(missing_ok=True)
        self._log = tempfile.TemporaryFile()
        self._started_at = time.monotonic()
        self._proc = subprocess.Popen(
            [self.cmd, "-n", "-t", "0", "--signal", "-o", str(self._warm_path),
             *config.CAMERA_ARGS, *config.CAMERA_WARM_ARGS],
            stdout=subprocess.DEVNULL,
            stderr=self._log,
            preexec_fn=_ignore_photo_signal,
        )

    def cancel(self):
        self._stop(wait=True)
        if self._closing is not None:
            # The camera can only be opened once, so the last one must be gone.
            self._closing.wait()
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
        if self._proc is None or self._proc.poll() is not None:
            if self._proc is not None:
                _log(f"warm camera had quit (exit {self._proc.returncode}): {self._warm_errors()}")
            else:
                _log("no warm camera, taking a one-shot photo")
            self.cancel()
            return self._one_shot()

        warm_for = time.monotonic() - self._started_at
        started = time.monotonic()
        # In signal mode the tool keeps running for the next photo, so wait for the
        # JPEG to finish writing, then stop it. If the camera is still starting
        # up it ignores the signal, so keep asking until the photo appears.
        signalled_at = 0
        deadline = started + 10
        while time.monotonic() < deadline:
            if not self._warm_path.exists() and time.monotonic() - signalled_at >= _RESIGNAL_S:
                self._proc.send_signal(signal.SIGUSR1)
                signalled_at = time.monotonic()
            time.sleep(0.03)
            if self._jpeg_done(self._warm_path):
                break
            if self._proc.poll() is not None:
                if self._jpeg_done(self._warm_path):
                    break
                _log(f"warm camera quit without a photo: {self._warm_errors()}")
                self.cancel()
                return self._one_shot()
        else:
            _log(f"warm camera gave no photo in 10s: {self._warm_errors()}")
            self.cancel()
            return self._one_shot()
        _log(f"warm photo in {(time.monotonic() - started) * 1000:.0f}ms "
             f"(camera started {warm_for:.1f}s before)")
        # Don't hold up showing the photo while the camera shuts down.
        self._stop(wait=False)
        path = self._new_path()
        self._warm_path.rename(path)
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
