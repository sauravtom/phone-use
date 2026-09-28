"""Subprocess test double, not an Android emulator. Only used by automated tests."""

import json
import os
import shlex
import struct
import sys
import time
import zlib
from pathlib import Path


def png() -> bytes:
    def chunk(kind, value):
        return (
            struct.pack(">I", len(value))
            + kind
            + value
            + struct.pack(">I", zlib.crc32(kind + value) & 0xFFFFFFFF)
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 320, 640, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress((b"\0" + b"\xff\xff\xff" * 320) * 640))
        + chunk(b"IEND", b"")
    )


def main():
    args = sys.argv[1:]
    if os.environ.get("FAKE_ADB_MODE") == "read_stdin":
        if sys.stdin.read():
            return 1
    with open(os.environ["FAKE_ADB_LOG"], "a") as log:
        log.write(json.dumps(args) + "\n")
    if os.environ.get("FAKE_ADB_MODE") == "timeout":
        time.sleep(10)
    if os.environ.get("FAKE_ADB_MODE") == "error":
        print("device error", file=sys.stderr)
        return 1
    if args == ["devices", "-l"]:
        print(
            "List of devices attached\n"
            + os.environ.get("FAKE_DEVICES", "test-phone device model:Test")
        )
        return 0
    if args[:2] != ["-s", "test-phone"]:
        return 1
    if args[2:] == ["exec-out", "screencap", "-p"]:
        sys.stdout.buffer.write(png())
        return 0
    if args[2] != "shell":
        return 1
    command = shlex.split(args[3])
    if command[:2] == ["uiautomator", "dump"]:
        print("UI hierarchy dumped to: " + command[-1])
    elif command[0] == "cat":
        print(Path(os.environ["FAKE_XML"]).read_text())
    elif command[:2] == ["rm", "-f"]:
        pass
    elif command == ["getprop", "ro.build.version.release"]:
        print("11")
    elif command[:3] == ["pm", "list", "packages"]:
        print("package:com.android.settings\npackage:com.example.test")
    elif command[:3] == ["cmd", "package", "resolve-activity"]:
        if command[-1] == "com.android.settings":
            print("com.android.settings/.Settings")
        else:
            print("No activity found")
    elif command[:2] == ["am", "start"]:
        print("Status: ok")
    elif command[0] == "input":
        pass
    else:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
