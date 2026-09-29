"""Record supervised screenshot-based MCP actions on the sample browser page."""

import asyncio
import base64
import json
import os
import subprocess
import time
from datetime import timedelta

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def run(serial, output, url, token):
    if os.environ.get("PHONE_USE_RECORDING_AUTHORIZED") != "1":
        raise RuntimeError("Explicit recording authorization is required")
    report = {
        "passed": False,
        "transport": "production HTTPS MCP",
        "verification": "pending visual review",
        "steps": [],
    }
    (output / "report.json").write_text(json.dumps(report, indent=2))
    adb = os.environ.get("PHONE_USE_ADB", "adb")
    base = [adb, "-s", serial]
    remote = "/sdcard/phone-use-demo-recording.mp4"
    command_file = output / "visual-next.json"
    if command_file.exists():
        raise RuntimeError("Remove the previous command file before a new recording")
    if subprocess.run(
        [*base, "shell", "pidof", "screenrecord"], capture_output=True, text=True
    ).stdout.strip():
        raise RuntimeError("A screen recording is already active")
    async with httpx.AsyncClient(headers={"Authorization": "Bearer " + token}, timeout=120) as http:
        async with streamable_http_client(url, http_client=http) as (read, write, _):
            async with ClientSession(
                read, write, read_timeout_seconds=timedelta(seconds=120)
            ) as client:
                await client.initialize()
                epoch = time.monotonic()

                async def call(name, **kwargs):
                    response = await client.call_tool("phone_" + name, {"serial": serial, **kwargs})
                    if response.isError:
                        raise RuntimeError(name + " failed; do not replay input")
                    report["steps"].append(
                        {"tool": "phone_" + name, "at_seconds": round(time.monotonic() - epoch, 2)}
                    )
                    print(json.dumps(report["steps"][-1]), flush=True)
                    return response

                async def screenshot(filename):
                    result = await call("screenshot")
                    png = next(c for c in result.content if c.type == "image")
                    (output / filename).write_bytes(base64.b64decode(png.data))

                status = (await call("status")).structuredContent
                report["android_version"] = status["android_version"]
                report["screen"] = status["screen"]
                await screenshot("before-screen.png")
                print("PREVIEW_READY", flush=True)
                # Coordinates must come from the latest inspected screenshot.
                while not command_file.exists():
                    await asyncio.sleep(0.25)
                start = json.loads(command_file.read_text())
                command_file.unlink()
                if start.get("action") != "start":
                    raise RuntimeError("Expected a reviewed start command")
                recording = subprocess.Popen(
                    [
                        *base,
                        "shell",
                        "screenrecord",
                        "--time-limit",
                        "180",
                        "--size",
                        "540x1200",
                        "--bit-rate",
                        "2000000",
                        remote,
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                epoch = time.monotonic()
                report["steps"] = []
                try:
                    await asyncio.sleep(2)
                    await call("screenshot")
                    await call("tap", x=start["x"], y=start["y"])
                    await call("type_text", text="hello world")
                    await call("press_key", key="BACK")
                    await screenshot("typed-screen.png")
                    print("TYPED_READY", flush=True)
                    while not command_file.exists():
                        if time.monotonic() - epoch > 130:
                            raise RuntimeError("Visual review deadline exceeded")
                        await asyncio.sleep(0.25)
                    apply = json.loads(command_file.read_text())
                    command_file.unlink()
                    if apply.get("action") != "apply":
                        raise RuntimeError("Expected a reviewed Apply command")
                    await call("tap", x=apply["x"], y=apply["y"])
                    await asyncio.sleep(2)
                    await screenshot("verified-screen.png")
                    await asyncio.sleep(3)
                    report["workflow_completed"] = True
                    report["recorded_seconds"] = round(time.monotonic() - epoch, 2)
                    assert report["recorded_seconds"] < 175
                    print("VISUAL_REVIEW_REQUIRED", flush=True)
                finally:
                    pids = subprocess.run(
                        [*base, "shell", "pidof", "screenrecord"], capture_output=True, text=True
                    ).stdout.split()
                    if pids and all(p.isdigit() for p in pids):
                        subprocess.run([*base, "shell", "kill", "-2", *pids], check=False)
                    try:
                        recording.wait(timeout=20)
                    except subprocess.TimeoutExpired:
                        recording.terminate()
                    pull = subprocess.run(
                        [*base, "pull", remote, str(output / "android-raw.mp4")],
                        capture_output=True,
                    )
                    report["video_pulled"] = pull.returncode == 0
                    (output / "report.json").write_text(json.dumps(report, indent=2))
                    assert report["video_pulled"], "Recording was not retrieved"
