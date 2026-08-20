"""
JARVIS - ADB Controller
Thin wrapper around the `adb` command-line tool. Every phone-facing action
(open app, call, text, screenshot, volume, navigation) goes through here so
the rest of the codebase never shells out directly.
"""

import subprocess
import shlex
import time
import os
from datetime import datetime

import config


class AdbError(RuntimeError):
    """Raised when an adb command fails or no device is available."""


class AdbController:
    def __init__(self, adb_path=None, serial=None):
        self.adb_path = adb_path or config.ADB_PATH
        self.serial = serial or config.ADB_DEVICE_SERIAL
        self._verify_adb_available()

    # ------------------------------------------------------------------ #
    # Low-level helpers
    # ------------------------------------------------------------------ #
    def _base_cmd(self):
        cmd = [self.adb_path]
        if self.serial:
            cmd += ["-s", self.serial]
        return cmd

    def _verify_adb_available(self):
        try:
            subprocess.run(
                [self.adb_path, "version"],
                capture_output=True, text=True, timeout=5, check=True,
            )
        except FileNotFoundError:
            raise AdbError(
                f"'{self.adb_path}' not found. Install Android platform-tools "
                f"and make sure adb is on your PATH, or set config.ADB_PATH."
            )
        except subprocess.CalledProcessError as e:
            raise AdbError(f"adb exists but failed to run: {e.stderr}")

    def run(self, args, timeout=15):
        """Run `adb <args>` and return stdout (stripped). Raises AdbError on failure."""
        cmd = self._base_cmd() + args
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout
            )
        except subprocess.TimeoutExpired:
            raise AdbError(f"Command timed out: {' '.join(cmd)}")

        if result.returncode != 0:
            raise AdbError(
                f"adb command failed: {' '.join(cmd)}\n{result.stderr.strip()}"
            )
        return result.stdout.strip()

    def shell(self, shell_cmd, timeout=15):
        """Run `adb shell <shell_cmd>`."""
        return self.run(["shell"] + shlex.split(shell_cmd), timeout=timeout)

    # ------------------------------------------------------------------ #
    # Device discovery / connection state
    # ------------------------------------------------------------------ #
    def list_devices(self):
        out = self.run(["devices"])
        devices = []
        for line in out.splitlines()[1:]:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device":
                devices.append(parts[0])
        return devices

    def ensure_device_connected(self):
        devices = self.list_devices()
        if not devices:
            raise AdbError(
                "No devices found. Check USB cable, enable USB debugging, "
                "and accept the RSA prompt on the phone screen."
            )
        if self.serial and self.serial not in devices:
            raise AdbError(f"Device '{self.serial}' not found. Available: {devices}")
        return devices

    # ------------------------------------------------------------------ #
    # App control
    # ------------------------------------------------------------------ #
    def open_app(self, package_name):
        """Launch an app by package name using monkey (works without knowing the activity)."""
        self.shell(f"monkey -p {package_name} -c android.intent.category.LAUNCHER 1")

    def close_app(self, package_name):
        self.shell(f"am force-stop {package_name}")

    # ------------------------------------------------------------------ #
    # Calls & messaging
    # ------------------------------------------------------------------ #
    def make_call(self, phone_number):
        digits = "".join(ch for ch in phone_number if ch.isdigit() or ch == "+")
        self.shell(f'am start -a android.intent.action.CALL -d tel:{digits}')

    def end_call(self):
        # Requires the "call" permission group; works on most stock dialers via keyevent.
        self.shell("input keyevent KEYCODE_ENDCALL")

    def send_sms(self, phone_number, message):
        digits = "".join(ch for ch in phone_number if ch.isdigit() or ch == "+")
        # Open the SMS compose intent pre-filled; user still taps send unless
        # accessibility/auto-send is configured (kept manual for safety).
        safe_msg = message.replace('"', "'")
        self.shell(
            f'am start -a android.intent.action.SENDTO -d sms:{digits} '
            f'--es sms_body "{safe_msg}" --ez exit_on_sent true'
        )

    # ------------------------------------------------------------------ #
    # Navigation / input
    # ------------------------------------------------------------------ #
    def press_home(self):
        self.shell("input keyevent KEYCODE_HOME")

    def press_back(self):
        self.shell("input keyevent KEYCODE_BACK")

    def press_recent_apps(self):
        self.shell("input keyevent KEYCODE_APP_SWITCH")

    def lock_screen(self):
        self.shell("input keyevent KEYCODE_POWER")

    def wake_screen(self):
        self.shell("input keyevent KEYCODE_WAKEUP")

    def type_text(self, text):
        # adb shell input text can't handle spaces directly; encode them.
        escaped = text.replace(" ", "%s").replace("'", "\\'")
        self.shell(f"input text '{escaped}'")

    def swipe(self, x1, y1, x2, y2, duration_ms=300):
        self.shell(f"input swipe {x1} {y1} {x2} {y2} {duration_ms}")

    def tap(self, x, y):
        self.shell(f"input tap {x} {y}")

    # ------------------------------------------------------------------ #
    # Volume / media
    # ------------------------------------------------------------------ #
    def volume_up(self, steps=1):
        for _ in range(steps):
            self.shell("input keyevent KEYCODE_VOLUME_UP")

    def volume_down(self, steps=1):
        for _ in range(steps):
            self.shell("input keyevent KEYCODE_VOLUME_DOWN")

    def mute(self):
        self.shell("input keyevent KEYCODE_VOLUME_MUTE")

    def play_pause(self):
        self.shell("input keyevent KEYCODE_MEDIA_PLAY_PAUSE")

    def next_track(self):
        self.shell("input keyevent KEYCODE_MEDIA_NEXT")

    def prev_track(self):
        self.shell("input keyevent KEYCODE_MEDIA_PREVIOUS")

    # ------------------------------------------------------------------ #
    # Screenshot / screen record
    # ------------------------------------------------------------------ #
    def take_screenshot(self, save_dir="screenshots"):
        os.makedirs(save_dir, exist_ok=True)
        remote_path = "/sdcard/jarvis_screenshot.png"
        self.shell(f"screencap -p {remote_path}")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        local_path = os.path.join(save_dir, f"screenshot_{timestamp}.png")
        self.run(["pull", remote_path, local_path])
        self.shell(f"rm {remote_path}")
        return local_path

    # ------------------------------------------------------------------ #
    # Web search / browser
    # ------------------------------------------------------------------ #
    def web_search(self, query):
        q = query.replace(" ", "+")
        self.shell(f'am start -a android.intent.action.VIEW -d "https://www.google.com/search?q={q}"')

    # ------------------------------------------------------------------ #
    # Battery / status info
    # ------------------------------------------------------------------ #
    def battery_level(self):
        out = self.shell("dumpsys battery")
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("level:"):
                return line.split(":")[1].strip()
        return None

    def storage_info(self):
        """
        Returns (used_human, total_human, percent_used) for /sdcard (internal storage),
        e.g. ("42G", "128G", 33). Returns None if it can't be parsed.
        """
        out = self.shell("df -h /sdcard")
        lines = [l for l in out.splitlines() if l.strip()]
        if len(lines) < 2:
            return None
        # Typical columns: Filesystem  Size  Used  Avail  Use%  Mounted on
        parts = lines[1].split()
        if len(parts) < 5:
            return None
        total, used, _avail, use_pct = parts[1], parts[2], parts[3], parts[4]
        try:
            percent = int(use_pct.strip("%"))
        except ValueError:
            percent = None
        return used, total, percent
