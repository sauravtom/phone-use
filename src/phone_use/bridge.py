"""Outbound, single-device bridge for the OAuth-protected hosted MCP relay."""

import asyncio
import base64
import json
import time
from urllib.parse import urlparse

import httpx
from pydantic import ValidationError
from websockets.asyncio.client import connect as WebSocketConnect
from websockets.exceptions import SecurityError

from .adb import PhoneError
from .core import Phone

TOOLS = frozenset(
    {
        "devices",
        "status",
        "observe",
        "screenshot",
        "find_elements",
        "tap",
        "tap_element",
        "swipe",
        "scroll",
        "press_key",
        "type_text",
        "list_apps",
        "launch_app",
    }
)


class NoRedirectConnect(WebSocketConnect):
    def process_redirect(self, exc):
        # Never forward the bridge credential to a redirect destination.
        return SecurityError("Bridge redirects are not allowed")


def dispatch(phone: Phone, serial: str, tool: str, arguments: dict):
    name = tool.removeprefix("phone_")
    if tool != "phone_" + name or name not in TOOLS:
        raise PhoneError("Unknown phone tool.")
    if not isinstance(arguments, dict):
        raise PhoneError("Arguments must be an object.")
    if name == "devices":
        if arguments:
            raise PhoneError("devices accepts no arguments.")
        return {"devices": [d for d in phone.adb.devices() if d["serial"] == serial]}
    if arguments.get("serial") not in (None, serial):
        raise PhoneError("This connection is authorized only for its paired device.")
    result = getattr(phone, name)(**{**arguments, "serial": serial})
    if isinstance(result, bytes):
        return {"mimeType": "image/png", "data": base64.b64encode(result).decode()}
    return result


async def run_bridge(server: str, serial: str, *, allow_local: bool = False):
    parsed = urlparse(server)
    local = (
        allow_local and parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost"}
    )
    if (parsed.scheme != "https" and not local) or parsed.username or parsed.password:
        raise PhoneError("Use an HTTPS relay URL without embedded credentials.")
    if not parsed.hostname or parsed.path not in ("", "/") or parsed.query or parsed.fragment:
        raise PhoneError("Relay URL must be an origin, without a path, query, or fragment.")
    server = server.rstrip("/")
    phone = Phone()
    serial = phone.adb.resolve(serial)
    async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
        response = await client.post(server + "/api/bridges")
        response.raise_for_status()
        session = response.json()
        endpoint = server + "/api/bridges/" + session["id"]
        headers = {"Authorization": "Bearer " + session["token"]}
        ws_url = endpoint.replace("https://", "wss://", 1).replace("http://", "ws://", 1)
        try:
            async with NoRedirectConnect(
                ws_url, additional_headers=headers, max_size=65536, open_timeout=15, proxy=None
            ) as socket:
                print(f"Connected device: {serial}", flush=True)
                print(f"MCP endpoint: {server}/mcp", flush=True)
                print(
                    "Start your MCP client's OAuth sign-in, then paste this one-time code:",
                    flush=True,
                )
                print(session["pairing_code"], flush=True)
                print(
                    "Code expires in 10 minutes. Session: 8 hours maximum. Ctrl-C disconnects.",
                    flush=True,
                )
                async for raw in socket:
                    message = json.loads(raw)
                    request_id = message.get("id")
                    try:
                        if (
                            not isinstance(message.get("deadline"), (float, int))
                            or message["deadline"] < time.time() * 1000
                        ):
                            raise PhoneError(
                                "Command expired before it reached the phone; no input sent."
                            )
                        result = await asyncio.to_thread(
                            dispatch, phone, serial, message["tool"], message.get("arguments", {})
                        )
                        reply = {"id": request_id, "result": result}
                    except ValidationError:
                        reply = {"id": request_id, "error": "Invalid arguments for phone tool."}
                    except (PhoneError, ValueError, TypeError, KeyError):
                        reply = {
                            "id": request_id,
                            "error": "Operation failed or rejected. Observe before retrying.",
                        }
                    await socket.send(json.dumps(reply))
        finally:
            try:
                await client.delete(endpoint, headers=headers)
            except httpx.HTTPError:
                pass  # Disconnection still stops commands; server expiry handles cleanup.
