"""What the Pi is up to, for the System Info screen: CPU, memory, disk,
Bluetooth speaker, Wi-Fi, SSH and power. Everything is read from /proc and
/sys or from small, quick commands (busctl rather than bluetoothctl, which
costs the Pi Zero a burst of CPU), and any of it may be missing on another
machine, in which case it just shows "n/a"."""

import os
import shutil
import socket
import subprocess
from pathlib import Path

from . import config

NA = "n/a"


def _run(cmd, timeout=3):
    """A command's output (stripped), or None if it isn't there or fails."""
    if shutil.which(cmd[0]) is None:
        return None
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.decode(errors="replace").strip()


def _read(path):
    try:
        return Path(path).read_text().strip()
    except OSError:
        return None


def _cpu_times():
    line = _read("/proc/stat")
    if not line:
        return None
    fields = [int(n) for n in line.splitlines()[0].split()[1:]]
    idle = fields[3] + (fields[4] if len(fields) > 4 else 0)  # idle + iowait
    return sum(fields), idle


def _temperature():
    raw = _read("/sys/class/thermal/thermal_zone0/temp")
    try:
        return int(raw) / 1000
    except (TypeError, ValueError):
        return None


def _memory():
    info = {}
    for line in (_read("/proc/meminfo") or "").splitlines():
        key, _, rest = line.partition(":")
        try:
            info[key] = int(rest.split()[0])  # kB
        except (IndexError, ValueError):
            pass
    total, available = info.get("MemTotal"), info.get("MemAvailable")
    if not total or available is None:
        return NA
    used = total - available
    return f"{used // 1024} / {total // 1024} MB ({used * 100 // total}%)"


def _disk():
    try:
        st = os.statvfs(config.REPO_ROOT)
    except OSError:
        return NA
    total = st.f_blocks * st.f_frsize
    free = st.f_bavail * st.f_frsize
    if not total:
        return NA
    return f"{free / 1e9:.1f} GB free ({(total - free) * 100 // total}% used)"


def _busctl_value(dev_path, interface, prop):
    out = _run(["busctl", "--system", "get-property", "org.bluez", dev_path, interface, prop])
    if not out:
        return None
    # e.g. 'b true', 'y 80', 's "JBL Go 3"'
    _, _, value = out.partition(" ")
    return value.strip().strip('"')


def _speaker():
    """(status, battery) for the speaker saved in ~/.jukebox-speaker."""
    mac = (_read(config.SPEAKER_FILE) or "").replace(" ", "")
    if not mac:
        return "Not set up", NA
    if shutil.which("busctl") is None:
        out = _run(["bluetoothctl", "info", mac])
        if out is None:
            return NA, NA
        return ("Connected" if "Connected: yes" in out else "Not connected"), NA
    dev_path = "/org/bluez/hci0/dev_" + mac.upper().replace(":", "_")
    connected = _busctl_value(dev_path, "org.bluez.Device1", "Connected")
    if connected is None:
        return "Not paired", NA
    name = _busctl_value(dev_path, "org.bluez.Device1", "Alias") or mac
    if connected != "true":
        return f"Off ({name})", NA
    # Only speakers that report it (and BlueZ new enough to pass it on).
    battery = _busctl_value(dev_path, "org.bluez.Battery1", "Percentage")
    return f"Connected ({name})", f"{battery}%" if battery else "Not reported"


def _wifi():
    """(name, signal) of the Wi-Fi network, or ("Not connected", n/a)."""
    iface, quality = None, None
    lines = (_read("/proc/net/wireless") or "").splitlines()[2:]
    if lines:
        parts = lines[0].split()
        iface = parts[0].rstrip(":")
        try:
            quality = float(parts[2].rstrip("."))
        except (IndexError, ValueError):
            pass
    iface = iface or "wlan0"
    ssid = _run(["iwgetid", "-r", iface])
    if not ssid:
        ssid = _run(["nmcli", "-t", "-g", "GENERAL.CONNECTION", "device", "show", iface])
    if not ssid:
        for line in (_run(["wpa_cli", "-i", iface, "status"]) or "").splitlines():
            if line.startswith("ssid="):
                ssid = line[5:]
    if not ssid:
        return "Not connected", NA
    # Link quality is out of 70 on the Pi's Wi-Fi.
    signal = f"{min(100, int(quality * 100 / 70))}%" if quality is not None else NA
    return ssid, signal


def _ip_address():
    out = _run(["hostname", "-I"])
    return out.split()[0] if out else NA


def _ssh():
    state = _run(["systemctl", "is-active", "ssh"]) or _run(["systemctl", "is-active", "sshd"])
    if state is None:
        # Not running: "is-active" exits non-zero; or there's no systemd.
        return "Off"
    if state != "active":
        return state.capitalize()
    # Remote logins show their address in brackets.
    sessions = sum(1 for line in (_run(["who"]) or "").splitlines() if "(" in line)
    return f"On ({sessions} logged in)" if sessions else "On"


def _power():
    """Under-voltage warnings from the Pi's firmware (a flat battery pack)."""
    out = _run(["vcgencmd", "get_throttled"])
    if not out or "=" not in out:
        return NA
    try:
        flags = int(out.split("=")[1], 16)
    except ValueError:
        return NA
    if flags & 0x1:
        return "LOW VOLTAGE now!"
    if flags & 0x4:
        return "Slowed down (throttled)"
    if flags & 0x10000:
        return "OK (was low earlier)"
    return "OK"


def _uptime():
    raw = _read("/proc/uptime")
    try:
        minutes = int(float(raw.split()[0])) // 60
    except (AttributeError, IndexError, ValueError):
        return NA
    days, minutes = divmod(minutes, 24 * 60)
    hours, minutes = divmod(minutes, 60)
    return f"{days}d {hours}h {minutes}m" if days else f"{hours}h {minutes}m"


class SystemInfo:
    """Keeps the CPU reading from the last call, so CPU use is measured
    across the gap between calls."""

    def __init__(self):
        self._last_cpu = _cpu_times()

    def _cpu(self):
        now = _cpu_times()
        usage = None
        if now and self._last_cpu and now[0] > self._last_cpu[0]:
            total = now[0] - self._last_cpu[0]
            idle = now[1] - self._last_cpu[1]
            usage = 100 * (total - idle) // total
        self._last_cpu = now
        temp = _temperature()
        parts = [f"{usage}%" if usage is not None else NA]
        if temp is not None:
            parts.append(f"{temp:.0f}°C")
        return ", ".join(parts)

    def read(self):
        """[(label, value), ...] in the order they're shown."""
        speaker, battery = _speaker()
        wifi, signal = _wifi()
        return [
            ("CPU", self._cpu()),
            ("Memory", _memory()),
            ("Disk", _disk()),
            ("Speaker", speaker),
            ("Battery", battery),
            ("Wi-Fi", wifi),
            ("Signal", signal),
            ("Address", _ip_address()),
            ("Name", socket.gethostname()),
            ("SSH", _ssh()),
            ("Power", _power()),
            ("Uptime", _uptime()),
        ]
