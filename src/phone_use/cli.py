"""JSON CLI for agents without MCP support."""

import argparse
import asyncio
import base64
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from . import __version__
from .adb import PhoneError
from .core import Phone

COMMANDS = (
    "devices",
    "status",
    "find_elements",
    "scroll",
    "observe",
    "screenshot",
    "tap",
    "tap_element",
    "swipe",
    "press_key",
    "type_text",
    "list_apps",
    "launch_app",
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Keyless Android control for coding agents")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("serve", help="Run the MCP server over stdio")
    sub.add_parser("tools", help="Print available tool names and descriptions")
    call = sub.add_parser("call", help="Call a tool with JSON arguments")
    call.add_argument("tool", choices=COMMANDS)
    call.add_argument("arguments", nargs="?", default="{}", help="JSON object; use - for stdin")
    call.add_argument("--output", type=Path, help="Save screenshot PNG to this file")
    args = parser.parse_args()
    if args.command == "serve":
        from .server import serve

        serve()
        return
    phone = Phone()
    if args.command == "tools":
        from .server import create_server

        tools = asyncio.run(create_server(phone).list_tools())
        print(
            json.dumps(
                {
                    tool.name.removeprefix("phone_"): {
                        "description": tool.description,
                        "inputSchema": tool.inputSchema,
                    }
                    for tool in tools
                },
                indent=2,
            )
        )
        return
    if args.output and args.tool != "screenshot":
        parser.error("--output is supported only for screenshot")
    try:
        payload = json.loads(sys.stdin.read() if args.arguments == "-" else args.arguments)
        if not isinstance(payload, dict):
            raise ValueError("Arguments must be a JSON object.")
        result = getattr(phone, args.tool)(**payload)
        if isinstance(result, bytes):
            if args.output:
                args.output.write_bytes(result)
                result = {"mimeType": "image/png", "path": str(args.output.resolve())}
            else:
                result = {"mimeType": "image/png", "data": base64.b64encode(result).decode()}
        print(json.dumps(result, ensure_ascii=False))
    except ValidationError:
        print(
            json.dumps(
                {"error": "Invalid arguments. Check tool types, ranges and required fields."}
            ),
            file=sys.stderr,
        )
        raise SystemExit(1) from None
    except (PhoneError, ValueError, TypeError, OSError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        raise SystemExit(1) from None
