"""Run the app on one explicitly selected task emulator, preserving JSON evidence."""

import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path
from zipfile import ZipFile

parser = argparse.ArgumentParser()
parser.add_argument("--adb", required=True)
parser.add_argument("--serial", required=True)
parser.add_argument("--artifacts", type=Path, required=True)
parser.add_argument("--reports", type=Path)
parser.add_argument("--runtime-pack", type=Path)
parser.add_argument("--boot-timeout", type=int, default=600)
parser.add_argument("--run-timeout", type=int, default=1200)
args = parser.parse_args()
if not args.serial.startswith("emulator-"):
    parser.error("This collector is limited to an explicitly selected emulator")
reports = args.reports or args.artifacts
reports.mkdir(parents=True, exist_ok=True)


def adb(*arguments, timeout=20):
    return subprocess.run(
        [args.adb, "-s", args.serial, *arguments],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


deadline = time.monotonic() + args.boot_timeout
ready_samples = 0
while time.monotonic() < deadline:
    try:
        ready = (
            adb("shell", "getprop", "sys.boot_completed").stdout.strip() == "1"
            and adb("shell", "service", "check", "package").stdout.strip()
            == "Service package: found"
            and adb("shell", "service", "check", "activity").stdout.strip()
            == "Service activity: found"
        )
        ready_samples = ready_samples + 1 if ready else 0
        if ready_samples >= 2:
            break
    except subprocess.TimeoutExpired:
        ready_samples = 0
    time.sleep(10)
else:
    raise SystemExit("BLOCKED: emulator services did not stabilize; no app checks claimed")
print("Emulator boot and package/activity services ready", flush=True)

for target, suffix in ((28, "legacy"), (36, "modern")):
    apk = args.artifacts / f"runtime-spike-x86_64-target{target}.apk"
    package = f"dev.phoneuse.spike.{suffix}"
    with apk.open("rb") as stream:
        apk_hash = hashlib.file_digest(stream, "sha256").hexdigest()
    with ZipFile(apk) as archive:
        expected_build = json.loads(archive.read("assets/build.json"))
    try:
        previous = adb("exec-out", "run-as", package, "cat", "files/report.json")
    except subprocess.TimeoutExpired:
        raise SystemExit(
            "BLOCKED: app report probe timed out; refusing to accept stale evidence"
        ) from None
    try:
        previous_run = json.loads(previous.stdout).get("startedAt")
    except ValueError:
        previous_run = None
    installed = adb("shell", "pm", "path", package).stdout.startswith("package:")
    result = adb("install", "--no-incremental", "-r", str(apk), timeout=240)
    install_output = result.stdout + result.stderr
    print(install_output, flush=True)
    if result.returncode:
        raise SystemExit("APK installation failed")
    adb("shell", "am", "force-stop", package)
    if expected_build.get("runtimeDelivery") == "staged":
        if not args.runtime_pack:
            raise SystemExit("This APK requires --runtime-pack")
        print(f"Staging hash-verified fixture for target{target}", flush=True)
        # Import bytes only. All executable tests still run in the Activity's app process.
        with args.runtime_pack.open("rb") as source:
            staged = subprocess.run(
                [
                    args.adb,
                    "-s",
                    args.serial,
                    "shell",
                    "-T",
                    f"run-as {package} sh -c 'mkdir -p files && cat > files/runtime.zip'",
                ],
                stdin=source,
                capture_output=True,
                timeout=600,
                check=False,
            )
        if staged.returncode:
            raise SystemExit("Runtime staging failed: " + staged.stderr.decode())
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
        try:
            result = adb("exec-out", "run-as", package, "cat", "files/report.json", timeout=30)
            candidate = json.loads(result.stdout)
        except (ValueError, subprocess.TimeoutExpired):
            continue
        if candidate.get("startedAt") == previous_run:
            continue
        if candidate.get("build") != expected_build:
            raise SystemExit("Report build does not match the installed APK")
        report = candidate
        report["apkSha256"] = apk_hash
        report["collector"] = {
            "serial": args.serial,
            "scope": "x86_64 Android emulator only",
            "installOutput": install_output,
            "installationMode": "update" if installed else "fresh",
        }
        path = reports / f"emulator-target{target}.json"
        path.write_text(json.dumps(report, indent=2) + "\n")
        for check in report["checks"][observed:]:
            print(f"target{target}: {check['name']}: {check['status']}", flush=True)
        observed = len(report["checks"])
        if report["state"] != "running":
            break
    if report is None:
        raise SystemExit("No app-written report was obtained")
    if report["state"] == "running":
        raise SystemExit("Run timed out; partial report preserved")
    print(str(path), flush=True)
