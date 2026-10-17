"""Fail-closed identity and evidence checks; not Android runtime evidence."""

import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "devicefarm_collector",
    Path(__file__).parents[1] / "apps/runtime-spike/devicefarm/tests/test_runtime.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_local_or_emulator_context_rejected():
    with pytest.raises(ValueError):
        MODULE.assigned_device({})
    env = {
        "DEVICEFARM_RUN_ARN": "arn:aws:devicefarm:us-west-2:123456789012:run:fixture/run",
        "DEVICEFARM_DEVICE_ARN": "arn:aws:devicefarm:us-west-2::device:fixture",
        "DEVICEFARM_DEVICE_PLATFORM_NAME": "ANDROID",
        "DEVICEFARM_DEVICE_UDID": "emulator-5554",
    }
    with pytest.raises(ValueError):
        MODULE.assigned_device(env)
    env["DEVICEFARM_DEVICE_UDID"] = "synthetic-aws-device"
    assert MODULE.assigned_device(env) == "synthetic-aws-device"


@pytest.mark.parametrize("mutation", ["stale", "build", "uid", "abi", "manifest", "duplicate"])
def test_invalid_evidence_rejected(mutation):
    expected = {"build": {"targetSdk": 36}, "runtimeManifestSha256": "fixture-hash"}
    report = {
        "schema": 1,
        "build": {"targetSdk": 36},
        "package": "dev.phoneuse.spike.modern",
        "targetSdk": 36,
        "startedAt": 2,
        "uid": 10123,
        "abis": ["arm64-v8a"],
        "checks": [{"name": "fixture", "status": "passed"}],
        "state": "finished",
        "runtimeManifestSha256": "fixture-hash",
    }
    MODULE.validate_report(report, expected, 1, "dev.phoneuse.spike.modern")
    if mutation == "stale":
        report["startedAt"] = 1
    elif mutation == "build":
        report["build"] = {"targetSdk": 28}
    elif mutation == "uid":
        report["uid"] = 0
    elif mutation == "abi":
        report["abis"] = ["x86_64"]
    elif mutation == "manifest":
        report["runtimeManifestSha256"] = "different"
    else:
        report["checks"] *= 2
    with pytest.raises(ValueError):
        MODULE.validate_report(report, expected, 1, "dev.phoneuse.spike.modern")
