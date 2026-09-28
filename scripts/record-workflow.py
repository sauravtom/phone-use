"""Record only the permission-free fixture app, with real MCP assertions."""

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
        raise RuntimeError(
            "Explicitly authorize recording this test device with PHONE_USE_RECORDING_AUTHORIZED=1"
        )
    output.mkdir(parents=True, exist_ok=True)
    report = {"passed": False, "transport": "production HTTPS MCP", "steps": []}
    (output / "report.json").write_text(json.dumps(report, indent=2))
    recording = None
    adb = os.environ.get("PHONE_USE_ADB", "adb")
    remote = "/sdcard/phone-use-demo-recording.mp4"
    epoch = time.monotonic()
    async with httpx.AsyncClient(headers={"Authorization": "Bearer " + token}, timeout=120) as http:
        async with streamable_http_client(url, http_client=http) as (read, write, _):
            async with ClientSession(
                read, write, read_timeout_seconds=timedelta(seconds=120)
            ) as client:
                await client.initialize()

                async def call(name, **kwargs):
                    response = await client.call_tool("phone_" + name, {"serial": serial, **kwargs})
                    if response.isError:
                        raise RuntimeError(f"{name} failed; no success claim or input retry")
                    report["steps"].append(
                        {"tool": "phone_" + name, "at_seconds": round(time.monotonic() - epoch, 2)}
                    )
                    print(json.dumps(report["steps"][-1]), flush=True)
                    return response

                async def find(predicate):
                    for attempt in range(3):
                        try:
                            state = (await call("observe")).structuredContent
                        except RuntimeError:
                            report.setdefault("read_failures", 0)
                            report["read_failures"] += 1
                            if attempt == 2:
                                raise
                            await asyncio.sleep(3)
                            continue
                        matches = [n for n in state["elements"] if predicate(n)]
                        if matches:
                            return state, matches[0]
                        await asyncio.sleep(1)
                    raise RuntimeError("Expected fixture state was not observed")

                status = (await call("status")).structuredContent
                report["android_version"] = status["android_version"]
                report["screen"] = status["screen"]
                package = (
                    "com.android.chrome"
                    if os.environ.get("PHONE_USE_RECORDING_MODE") == "browser"
                    else "org.phoneuse.fixture"
                )
                await call("launch_app", package=package)
                state, reset = await find(lambda n: n["text"].casefold() == "reset demo")
                await call("tap_element", element_id=reset["id"], snapshot=state["snapshot"])
                state, node = await find(lambda n: n["description"] == "Test input")
                assert node["package"] == package
                if subprocess.run(
                    [adb, "-s", serial, "shell", "pidof", "screenrecord"],
                    capture_output=True,
                    text=True,
                ).stdout.strip():
                    raise RuntimeError("A screen recording is already active")
                size = "480x800" if status["screen"]["height"] <= 800 else "540x1200"
                recording = subprocess.Popen(
                    [
                        adb,
                        "-s",
                        serial,
                        "shell",
                        "screenrecord",
                        "--time-limit",
                        "180",
                        "--size",
                        size,
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
                    state, node = await find(lambda n: n["description"] == "Test input")
                    await call("tap_element", element_id=node["id"], snapshot=state["snapshot"])
                    await find(lambda n: n["description"] == "Test input" and n["focused"])
                    await call("type_text", text="hello world")
                    await find(lambda n: n["text"] == "hello world")
                    await call("press_key", key="BACK")
                    state, button = await find(lambda n: n["text"].casefold() == "apply text")
                    await call("tap_element", element_id=button["id"], snapshot=state["snapshot"])
                    await find(lambda n: n["text"] == "Verified: hello world")
                    shot = await call("screenshot")
                    png = next(c for c in shot.content if c.type == "image")
                    (output / "verified-screen.png").write_bytes(base64.b64decode(png.data))
                    await asyncio.sleep(3)
                    assert time.monotonic() - epoch < 175, "Recording window exceeded"
                    report["passed"] = True
                    report["verified_text"] = "Verified: hello world"
                finally:
                    pids = (
                        subprocess.run(
                            [adb, "-s", serial, "shell", "pidof", "screenrecord"],
                            capture_output=True,
                            text=True,
                        )
                        .stdout.strip()
                        .split()
                    )
                    if pids and all(p.isdigit() for p in pids):
                        subprocess.run(
                            [adb, "-s", serial, "shell", "kill", "-2", *pids], check=False
                        )
                    try:
                        recording.wait(timeout=20)
                    except subprocess.TimeoutExpired:
                        recording.terminate()
                    pulled = subprocess.run(
                        [adb, "-s", serial, "pull", remote, str(output / "android-raw.mp4")],
                        capture_output=True,
                    )
                    report["video_pulled"] = pulled.returncode == 0
                    (output / "report.json").write_text(json.dumps(report, indent=2))
                    assert report["video_pulled"], "Recording was not retrieved"
