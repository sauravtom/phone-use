"""Device Farm entry point. Runs only on the AWS-assigned device, never local ADB."""

import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from zipfile import ZipFile


def assigned_device(env):
    """Fail closed before invoking ADB outside the intended Device Farm job."""
    for key, kind in (("DEVICEFARM_RUN_ARN", "run"), ("DEVICEFARM_DEVICE_ARN", "device")):
        if not re.fullmatch(
            rf"arn:aws:devicefarm:us-west-2:[0-9]*:{kind}:[A-Za-z0-9/._-]+",
            env.get(key, ""),
        ):
            raise ValueError(f"Missing or invalid {key}")
    serial = env.get("DEVICEFARM_DEVICE_UDID", "")
    if not re.fullmatch(r"[A-Za-z0-9._:-]+", serial) or serial.startswith("emulator-"):
        raise ValueError("An AWS-assigned physical-device UDID is required")
    if env.get("DEVICEFARM_DEVICE_PLATFORM_NAME", "").upper() != "ANDROID":
        raise ValueError("Android Device Farm job required")
    return serial


def validate_report(report, expected, previous, package):
    if not isinstance(report, dict) or report.get("schema") != 1:
        raise ValueError("Unknown report schema")
    if report.get("build") != expected["build"]:
        raise ValueError("Report build differs from submitted fixture")
    if (
        report.get("package") != package
        or report.get("targetSdk") != expected["build"]["targetSdk"]
    ):
        raise ValueError("Installed package/target mismatch")
    started = report.get("startedAt")
    if not isinstance(started, int) or started <= 0 or started == previous:
        raise ValueError("Stale or invalid report generation")
    if not isinstance(report.get("uid"), int) or report["uid"] % 100000 < 10000:
        raise ValueError("Diagnostic process is not an ordinary Android app UID")
    if not report.get("abis") or report["abis"][0] != "arm64-v8a":
        raise ValueError("An actual ARM64 device is required")
    checks = report.get("checks")
    if not isinstance(checks, list):
        raise ValueError("Missing checks")
    names = [c.get("name") for c in checks]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate checks")
    if any(c.get("status") not in {"passed", "failed", "cancelled", "not_run"} for c in checks):
        raise ValueError("Unknown check status")
    if report.get("state") not in {"running", "finished", "cancelled", "interrupted"}:
        raise ValueError("Unknown run state")
    manifest = report.get("runtimeManifestSha256")
    if manifest is not None and manifest != expected["runtimeManifestSha256"]:
        raise ValueError("Runtime manifest mismatch")


def test_runtime():
    serial = assigned_device(os.environ)
    logs = Path(os.environ["DEVICEFARM_LOG_DIR"])
    logs.mkdir(parents=True, exist_ok=True)
    adb_path = shutil.which("adb")
    assert adb_path, "Device Farm Android host has no adb"
    expected_records = json.loads((Path(__file__).parent / "expected.json").read_text())
    apk = Path(os.environ["DEVICEFARM_APP_PATH"])
    with ZipFile(apk) as archive:
        build = json.loads(archive.read("assets/build.json"))
        manifest_hash = hashlib.sha256(archive.read("assets/runtime-manifest.json")).hexdigest()
    target = build["targetSdk"]
    assert target in (28, 36) and build["abi"] == "arm64-v8a"
    expected = expected_records[str(target)]
    assert build == expected["build"] and manifest_hash == expected["runtimeManifestSha256"]
    assert build.get("runtimeDelivery", "bundled") == "bundled", "Bundled APK required"
    package = "dev.phoneuse.spike." + ("legacy" if target == 28 else "modern")

    def adb(*arguments, timeout=20, required=True):
        result = subprocess.run(
            [adb_path, "-s", serial, *arguments],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        if required and result.returncode:
            raise RuntimeError(f"ADB {arguments[:3]} failed: {result.stderr[-2000:]}")
        return result

    with apk.open("rb") as stream:
        service_hash = hashlib.file_digest(stream, "sha256").hexdigest()
    metadata = {
        "runArn": os.environ["DEVICEFARM_RUN_ARN"],
        "deviceArn": os.environ["DEVICEFARM_DEVICE_ARN"],
        "submittedApkSha256": expected["apkSha256"],
        "serviceApkSha256": service_hash,
        "targetSdk": target,
        "collection": "started",
        "scope": "AWS-hosted ARM64 Android; Activity executes all runtime diagnostics",
        "runtimeGate": "not_evaluated",
        "backgroundForeground": "not_run",
        "completedReportRestart": "not_run",
        "interruptedReportRestart": "not_run",
    }
    report_path = logs / "app-report.json"
    metadata_path = logs / "collection.json"

    def save_metadata():
        metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")

    save_metadata()
    try:
        assert adb("get-state").stdout.strip() == "device"
        for prop in ("ro.product.cpu.abilist", "ro.build.version.sdk", "ro.build.fingerprint"):
            metadata[prop] = adb("shell", "getprop", prop).stdout.strip()
        assert metadata["ro.product.cpu.abilist"].split(",")[0] == "arm64-v8a"
        metadata["selinux"] = adb("shell", "getenforce").stdout.strip()
        assert metadata["selinux"] == "Enforcing", "Do not weaken Android security for the spike"
        if not adb("shell", "pm", "path", package, required=False).stdout.startswith("package:"):
            installed = adb("install", "--no-incremental", "-r", str(apk), timeout=240)
            assert "Success" in installed.stdout, installed.stdout
        (logs / "installed-package.txt").write_text(
            adb("shell", "dumpsys", "package", package).stdout
        )
        # This package contains synthetic fixtures only; clear it for a real fresh run.
        adb("shell", "am", "force-stop", package)
        assert "Success" in adb("shell", "pm", "clear", package).stdout
        assert adb("shell", "run-as", package, "id").stdout.startswith("uid="), "run-as unavailable"
        launched = adb(
            "shell",
            "am",
            "start",
            "-W",
            "-n",
            package + "/dev.phoneuse.spike.MainActivity",
            "--ez",
            "runDiagnostics",
            "true",
            timeout=60,
        )
        assert "Error" not in launched.stdout + launched.stderr, launched.stdout
        deadline = time.monotonic() + 900
        seen = 0
        background_generation = None
        report = None
        while time.monotonic() < deadline:
            time.sleep(3)
            try:
                result = adb(
                    "exec-out", "run-as", package, "cat", "files/report.json", required=False
                )
                candidate = json.loads(result.stdout)
            except (ValueError, subprocess.TimeoutExpired):
                continue
            validate_report(candidate, expected, None, package)
            report = candidate
            if background_generation is not None:
                assert report["startedAt"] == background_generation, (
                    "Background resume duplicated run"
                )
            if background_generation is None and report["state"] == "running":
                background_generation = report["startedAt"]
                adb("shell", "input", "keyevent", "KEYCODE_HOME")
                time.sleep(3)
                adb(
                    "shell", "am", "start", "-W", "-n",
                    package + "/dev.phoneuse.spike.MainActivity",
                )
                metadata["backgroundForeground"] = "attempted"
            report_path.write_text(json.dumps(report, indent=2) + "\n")
            for check in report["checks"][seen:]:
                print(f"{check['name']}: {check['status']}", flush=True)
            seen = len(report["checks"])
            if report["state"] != "running":
                break
        assert report is not None, "No app-written report obtained"
        assert report["state"] == "finished", "Partial or interrupted report; see artifacts"
        assert report.get("runtimeManifestSha256") == expected["runtimeManifestSha256"]
        assert report["checks"], "Empty diagnostic report"
        if background_generation is not None:
            metadata["backgroundForeground"] = "passed"
        metadata["collection"] = "complete"
        metadata["failedChecks"] = [c["name"] for c in report["checks"] if c["status"] == "failed"]
        metadata["notRunChecks"] = [c["name"] for c in report["checks"] if c["status"] == "not_run"]
        save_metadata()
        # Recover the completed app-written report after process death; do not rerun probes.
        adb("shell", "am", "force-stop", package)
        adb("shell", "am", "start", "-W", "-n", package + "/dev.phoneuse.spike.MainActivity")
        recovered = json.loads(
            adb("exec-out", "run-as", package, "cat", "files/report.json").stdout
        )
        assert recovered == report, "Completed report changed or disappeared after restart"
        metadata["completedReportRestart"] = "passed"
        save_metadata()
        # Kill only this synthetic app during another run, then require interrupted recovery.
        adb("shell", "am", "force-stop", package)
        adb(
            "shell", "am", "start", "-W", "-n", package + "/dev.phoneuse.spike.MainActivity",
            "--ez", "runDiagnostics", "true",
        )
        deadline = time.monotonic() + 15
        interrupted_generation = None
        while time.monotonic() < deadline:
            current = json.loads(
                adb("exec-out", "run-as", package, "cat", "files/report.json").stdout
            )
            if current["startedAt"] != report["startedAt"] and current["state"] == "running":
                interrupted_generation = current["startedAt"]
                break
            time.sleep(0.2)
        assert interrupted_generation is not None, "No fresh running generation to interrupt"
        adb("shell", "am", "force-stop", package)
        adb("shell", "am", "start", "-W", "-n", package + "/dev.phoneuse.spike.MainActivity")
        recovered = json.loads(
            adb("exec-out", "run-as", package, "cat", "files/report.json").stdout
        )
        (logs / "interrupted-report.json").write_text(json.dumps(recovered, indent=2) + "\n")
        assert recovered["startedAt"] == interrupted_generation
        assert recovered["state"] == "interrupted"
        metadata["interruptedReportRestart"] = "passed"
        save_metadata()
        # A provider PASSED status must never hide a failed runtime probe.
        assert not metadata["failedChecks"], "Runtime probes failed; inspect app-report.json"
    except Exception as error:
        metadata["error"] = str(error)[:4000]
        if metadata["collection"] != "complete":
            metadata["collection"] = "failed"
        save_metadata()
        raise
    finally:
        for name, command in (
            ("logcat.txt", ("logcat", "-d", "-t", "1500")),
            ("activity.txt", ("shell", "dumpsys", "activity", "activities")),
        ):
            try:
                (logs / name).write_text(adb(*command, required=False).stdout[-500000:])
            except (OSError, subprocess.TimeoutExpired):
                pass
        try:
            adb("shell", "am", "force-stop", package, required=False)
        except (OSError, subprocess.TimeoutExpired):
            pass
