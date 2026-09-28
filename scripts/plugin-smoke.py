#!/usr/bin/env python3
"""Exercise the actual directory ZIP without API keys, using a fake ADB process."""

import asyncio
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]


async def check_mcp(launcher, env):
    params = StdioServerParameters(command=sys.executable, args=[str(launcher), "serve"], env=env)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as client:
            await client.initialize()
            assert len((await client.list_tools()).tools) == 13
            result = await client.call_tool("phone_observe", {})
            assert not result.isError
            assert result.structuredContent["elements"][0]["text"] == "Settings"


def main():
    uv = shutil.which("uv")
    if not uv:
        raise SystemExit("uv is required")
    subprocess.run([sys.executable, str(ROOT / "scripts/build-plugin.py")], check=True)
    version = json.loads((ROOT / ".codex-plugin/plugin.json").read_text())["version"]
    archive = ROOT / "dist" / f"phone-use-plugin-{version}.zip"
    evidence = ROOT / "artifacts/plugin-smoke"
    evidence.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="plugin with spaces ", dir=evidence) as temp:
        work = Path(temp).resolve()
        plugin = work / "phone-use"
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(plugin)
        launcher = plugin / "skills/phone-use/scripts/phone_use.py"
        adb = work / "fake-adb"
        adb.write_text(f"#!{sys.executable}\n" + (ROOT / "tests/fake_adb.py").read_text())
        adb.chmod(0o700)
        xml = work / "screen.xml"
        xml.write_text(
            '<hierarchy><node text="Settings" bounds="[10,100][210,160]" '
            'enabled="true" clickable="true"/></hierarchy>'
        )
        log = work / "calls.jsonl"
        env = {
            "PATH": os.pathsep.join([str(Path(uv).parent), "/usr/bin", "/bin"]),
            "PHONE_USE_PLUGIN_CACHE": str(work / "runtime-cache"),
            "PHONE_USE_ADB": str(adb),
            "FAKE_XML": str(xml),
            "FAKE_ADB_LOG": str(log),
        }

        def call(*args, data=None, success=True):
            result = subprocess.run(
                [sys.executable, str(launcher), *args],
                input=data,
                text=True,
                capture_output=True,
                env=env,
                timeout=120,
                cwd=work,
            )
            assert (result.returncode == 0) == success, result.stderr
            return json.loads(result.stdout if success else result.stderr)

        assert len(call("tools")) == 13
        assert call("call", "devices")
        state = call("call", "observe")
        assert state["elements"][0]["text"] == "Settings"
        call("call", "tap_element", json.dumps({"element_id": "0", "snapshot": state["snapshot"]}))
        value = "plugin 100% 'quote' & $HOME"
        call("call", "type_text", "-", data=json.dumps({"text": value}))
        inputs = [
            shlex.split(args[3])
            for args in map(json.loads, log.read_text().splitlines())
            if len(args) > 3 and args[3].startswith("input text")
        ]
        assert inputs[-1] == ["input", "text", value.replace(" ", "%s")]
        call("call", "screenshot", "--output", str(work / "screen.png"))
        assert (work / "screen.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
        assert "error" in call(
            "call", "tap_element", '{"element_id":"0","snapshot":"old"}', success=False
        )
        assert "error" in call("call", "type_text", '{"text":"हिन्दी"}', success=False)
        asyncio.run(check_mcp(launcher, env))
        assert not list(plugin.rglob(".venv")), "Plugin content must not contain its environment"
        assert (work / "runtime-cache").is_dir()
    report = {
        "passed": True,
        "api_keys": False,
        "backend": "fake-adb",
        "tools": 13,
        "checks": [
            "ZIP extraction with spaces",
            "isolated dependency bootstrap",
            "CLI schemas",
            "observe",
            "snapshot tap",
            "stdin text and shell quoting",
            "PNG",
            "stale snapshot rejection",
            "Unicode rejection",
            "MCP through launcher",
            "environment outside plugin",
        ],
    }
    (evidence / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
