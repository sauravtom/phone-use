"""Small, bounded ADB subprocess adapter. Never invokes a host shell."""

import os
import shlex
import subprocess
from pathlib import Path


class PhoneError(RuntimeError):
    """Actionable device/transport failure safe to show to a caller."""


class Adb:
    def __init__(self, executable: str | None = None, timeout: float = 30):
        sdk = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
        candidate = Path(sdk, "platform-tools", "adb") if sdk else None
        self.executable = (
            executable
            or os.environ.get("PHONE_USE_ADB")
            or (str(candidate) if candidate and candidate.is_file() else "adb")
        )
        self.timeout = timeout

    def run(self, *args: str) -> bytes:
        try:
            result = subprocess.run(
                [self.executable, *args],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                timeout=self.timeout,
                check=False,
            )
        except FileNotFoundError as exc:
            raise PhoneError(
                "ADB not found. Install Android platform-tools or set PHONE_USE_ADB."
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise PhoneError(
                "ADB timed out. Check the device and connection before retrying."
            ) from exc
        except OSError as exc:
            raise PhoneError("Unable to execute ADB. Check its path and permissions.") from exc
        if result.returncode:
            # Do not echo commands, text input, or arbitrary device output into error logs.
            raise PhoneError(
                "ADB command failed. Check phone_devices for offline/unauthorized devices."
            )
        return result.stdout

    def shell(self, serial: str, *args: str) -> str:
        # adb shell joins arguments on the remote shell; host argv alone is NOT sufficient.
        command = shlex.join(args)
        return self.run("-s", serial, "shell", command).decode("utf-8", errors="replace").strip()

    def devices(self) -> list[dict]:
        rows = self.run("devices", "-l").decode("utf-8", errors="replace").splitlines()
        devices = []
        for row in rows:
            fields = row.split()
            if len(fields) < 2 or row.startswith(("List of devices", "*")):
                continue
            devices.append(
                {"serial": fields[0], "state": fields[1], "details": " ".join(fields[2:])}
            )
        return devices

    def resolve(self, serial: str | None) -> str:
        serial = serial or os.environ.get("PHONE_USE_SERIAL")
        devices = self.devices()
        if serial:
            match = next((d for d in devices if d["serial"] == serial), None)
            if not match:
                raise PhoneError("Selected device is not connected. Run phone_devices.")
            if match["state"] != "device":
                raise PhoneError(
                    f"Selected device is {match['state']}. Unlock and authorize debugging."
                )
            return serial
        if len(devices) != 1:
            raise PhoneError(
                "Connect one Android device, or pass serial explicitly when several exist."
            )
        return self.resolve(devices[0]["serial"])
