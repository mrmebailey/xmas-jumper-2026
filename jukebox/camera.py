import shutil
import subprocess
from datetime import datetime

from . import config


class CameraManager:
    def __init__(self):
        config.PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
        self.cmd = next((c for c in config.CAMERA_CMDS if shutil.which(c)), None)

    def take_photo(self):
        if self.cmd is None:
            return None, "No camera tool found (install libcamera-apps/rpicam-apps)"

        filename = datetime.now().strftime("photo_%Y%m%d_%H%M%S.jpg")
        path = config.PHOTOS_DIR / filename
        try:
            subprocess.run(
                [self.cmd, "-o", str(path), "-n", "-t", "1000"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
        except subprocess.CalledProcessError as e:
            return None, f"Camera failed: {e.stderr.decode(errors='replace').strip()[:80]}"
        return path, None
