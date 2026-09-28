"""Opt-in live MCP test against the separately installed fixture app."""

import argparse
import asyncio
import base64
import json
import os
import sys
import time
from datetime import timedelta
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def run(serial: str, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    report = {"serial": serial, "steps": [], "transport": "MCP stdio", "passed": False}
    env = {
        k: v
        for k, v in os.environ.items()
        if not any(name in k for name in ("API_KEY", "TOKEN", "SECRET"))
    }
    params = StdioServerParameters(
        command=str(Path(sys.executable).with_name("phone-use")), args=["serve"], env=env
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(
            read, write, read_timeout_seconds=timedelta(seconds=120)
        ) as client:
            await client.initialize()

            async def call(name, **kwargs):
                started = time.monotonic()
                response = await client.call_tool("phone_" + name, {"serial": serial, **kwargs})
                if response.isError:
                    raise RuntimeError(f"{name}: {response.content}")
                report["steps"].append(
                    {"tool": name, "seconds": round(time.monotonic() - started, 2)}
                )
                print(json.dumps(report["steps"][-1]), flush=True)
                return response

            async def find(predicate):
                for _ in range(4):
                    response = await call("observe")
                    data = response.structuredContent
                    matches = [n for n in data["elements"] if predicate(n)]
                    if matches:
                        return data, matches[0]
                    await asyncio.sleep(2)
                raise AssertionError("Expected fixture element was not visible")

            status = (await call("status")).structuredContent
            report["device"] = status
            assert status["boot_completed"], "Android must finish booting before this test"
            apps = (await call("list_apps")).structuredContent["packages"]
            assert "org.phoneuse.fixture" in apps, "Install the fixture APK first"
            await call("launch_app", package="org.phoneuse.fixture")
            state, node = await find(lambda n: n["description"] == "Test input")
            await call("tap_element", element_id=node["id"], snapshot=state["snapshot"])
            await find(lambda n: n["description"] == "Test input" and n["focused"])
            payload = "phone-use 100% 'quote' & $HOME"
            await call("type_text", text=payload)
            await find(lambda n: n["text"] == payload)
            await call("press_key", key="BACK")
            state, node = await find(lambda n: n["text"].casefold() == "apply text")
            await call("tap_element", element_id=node["id"], snapshot=state["snapshot"])
            state, node = await find(lambda n: n["text"] == "Verified: " + payload)
            report["verified_text"] = node["text"]
            (output / "verified-ui.json").write_text(json.dumps(state, indent=2))
            response = await call("screenshot")
            image = next(c for c in response.content if c.type == "image")
            png = base64.b64decode(image.data)
            assert png.startswith(b"\x89PNG\r\n\x1a\n")
            (output / "verified-screen.png").write_bytes(png)
            await call("tap", x=node["center"][0], y=node["center"][1])
            width, height = status["screen"]["width"], status["screen"]["height"]
            await call("swipe", x1=width // 2, y1=height * 3 // 4, x2=width // 2, y2=height // 4)
            await call("scroll", direction="down")
            await call("press_key", key="HOME")
            await call("launch_app", package="org.phoneuse.fixture")
            await find(lambda n: n["text"] == "phone-use device test")
            report["passed"] = True
    (output / "report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial", required=True, help="Explicit disposable test device")
    parser.add_argument("--output", type=Path, default=Path("artifacts/device-smoke"))
    args = parser.parse_args()
    asyncio.run(run(args.serial, args.output))
