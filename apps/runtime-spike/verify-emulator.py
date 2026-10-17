"""Run the app on one explicitly selected task emulator, preserving JSON evidence."""

import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--adb", required=True)
parser.add_argument("--serial", required=True)
parser.add_argument("--artifacts", type=Path, required=True)
parser.add_argument("--boot-timeout", type=int, default=600)
parser.add_argument("--run-timeout", type=int, default=1200)
args = parser.parse_args()
if not args.serial.startswith("emulator-"):
    parser.error("This collector is limited to an explicitly selected emulator")


def adb(*arguments, timeout=20):
    return subprocess.run(
        [args.adb, "-s", args.serial, *arguments],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


deadline = time.monotonic() + args.boot_timeout
while time.monotonic() < deadline:
    try:
        if adb("shell", "getprop", "sys.boot_completed").stdout.strip() == "1":
            break
    except subprocess.TimeoutExpired:
        pass
    time.sleep(10)
else:
    raise SystemExit("BLOCKED: emulator did not complete boot; no app checks claimed")
print("Emulator boot complete", flush=True)

for target, suffix in ((28, "legacy"), (36, "modern")):
    apk = args.artifacts / f"runtime-spike-x86_64-target{target}.apk"
    package = f"dev.phoneuse.spike.{suffix}"
    result = adb("install", "--no-incremental", "-r", str(apk), timeout=240)
    print(result.stdout + result.stderr, flush=True)
    if result.returncode:
        raise SystemExit("APK installation failed")
    adb("shell", "am", "force-stop", package)
    launch = adb(
        "shell",
        "am",
        "start",
        "-n",
        package + "/dev.phoneuse.spike.MainActivity",
        "--ez",
        "runDiagnostics",
        "true",
        timeout=60,
    )
    if launch.returncode or "Error" in launch.stdout:
        raise SystemExit("Activity launch failed: " + launch.stdout + launch.stderr)
    deadline = time.monotonic() + args.run_timeout
    observed = 0
    report = None
    while time.monotonic() < deadline:
        time.sleep(5)
        result = adb("exec-out", "run-as", package, "cat", "files/report.json", timeout=30)
        try:
            candidate = json.loads(result.stdout)
        except (json.JSONDecodeError, ValueError):
            continue
        report = candidate
        for check in report["checks"][observed:]:
            print(f"target{target}: {check['name']}: {check['status']}", flush=True)
        observed = len(report["checks"])
        if report["state"] != "running":
            break
    if report is None:
        raise SystemExit("No app-written report was obtained")
    with apk.open("rb") as stream:
        report["apkSha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
    report["collector"] = {
        "serial": args.serial,
        "scope": "x86_64 Android emulator only",
        "installOutput": result.stdout if report is None else "see console log",
    }
    path = args.artifacts / f"emulator-target{target}.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    if report["state"] == "running":
        raise SystemExit("Run timed out; partial report preserved")
    print(str(path), flush=True)
