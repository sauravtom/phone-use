#!/usr/bin/env python3
"""Integration-check OAuth + Cloudflare relay + device dispatch; never prints tokens."""

import argparse
import asyncio
import base64
import hashlib
import json
import os
import secrets
import sys
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

from phone_use.bridge import NoRedirectConnect, dispatch
from phone_use.core import Phone

ROOT = Path(__file__).resolve().parents[1]


async def run(origin):
    results = []
    with tempfile.TemporaryDirectory(prefix="phone-relay-") as temp:
        work = Path(temp)
        adb = work / "adb"
        adb.write_text(f"#!{sys.executable}\n" + (ROOT / "tests/fake_adb.py").read_text())
        adb.chmod(0o700)
        xml = work / "ui.xml"
        xml.write_text(
            '<hierarchy><node text="Settings" bounds="[10,100][210,160]" '
            'enabled="true" clickable="true"/></hierarchy>'
        )
        os.environ.update(
            PHONE_USE_ADB=str(adb), FAKE_XML=str(xml), FAKE_ADB_LOG=str(work / "adb.jsonl")
        )
        phone = Phone()
        async with httpx.AsyncClient(base_url=origin, follow_redirects=False, timeout=80) as client:
            unauth = await client.post("/mcp", json={})
            assert unauth.status_code == 401, unauth.text
            assert "resource_metadata" in unauth.headers.get("www-authenticate", "")
            results.append("unauthenticated MCP rejected")
            metadata = (await client.get("/.well-known/oauth-authorization-server")).json()
            assert metadata["code_challenge_methods_supported"] == ["S256"]
            registration = await client.post(
                "/oauth/register",
                json={
                    "client_name": "phone-use integration test",
                    "redirect_uris": ["http://localhost:32123/callback"],
                    "token_endpoint_auth_method": "none",
                    "grant_types": ["authorization_code", "refresh_token"],
                    "response_types": ["code"],
                },
            )
            assert registration.status_code == 201, registration.text
            client_id = registration.json()["client_id"]
            creation = await client.post("/api/bridges")
            assert creation.status_code == 201, creation.text
            bridge = creation.json()
            ws_url = (
                origin.replace("https:", "wss:").replace("http:", "ws:")
                + "/api/bridges/"
                + bridge["id"]
            )
            headers = {"Authorization": "Bearer " + bridge["token"]}
            async with NoRedirectConnect(ws_url, additional_headers=headers, proxy=None) as ws:

                async def respond():
                    async for raw in ws:
                        request = json.loads(raw)
                        try:
                            result = await asyncio.to_thread(
                                dispatch, phone, "test-phone", request["tool"], request["arguments"]
                            )
                            reply = {"id": request["id"], "result": result}
                        except Exception:
                            reply = {"id": request["id"], "error": "Rejected phone operation"}
                        await ws.send(json.dumps(reply))

                task = asyncio.create_task(respond())
                verifier = secrets.token_urlsafe(48)
                challenge = (
                    base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
                    .decode()
                    .rstrip("=")
                )
                query = urlencode(
                    {
                        "client_id": client_id,
                        "redirect_uri": "http://localhost:32123/callback",
                        "response_type": "code",
                        "scope": "phone:control",
                        "state": "test-state",
                        "resource": origin + "/mcp",
                        "code_challenge": challenge,
                        "code_challenge_method": "S256",
                    }
                )
                consent = await client.get("/authorize?" + query)
                assert consent.status_code == 200, consent.text
                assert consent.headers["referrer-policy"] == "strict-origin"
                for bad_origin in ("null", "https://untrusted.example"):
                    blocked = await client.post(
                        "/authorize",
                        data={"decision": "approve"},
                        headers={"Origin": bad_origin},
                    )
                    assert blocked.status_code == 403
                results.append(
                    "browser-compatible referrer policy; null and foreign origins blocked"
                )
                import re

                handle = re.search('name="handle" value="([^"]+)"', consent.text).group(1)
                cookie = consent.headers["set-cookie"].split(";")[0]
                # The local test uses HTTP; explicitly transport the secure consent cookie.
                approved = await client.post(
                    "/authorize",
                    data={
                        "handle": handle,
                        "pairing_code": bridge["pairing_code"],
                        "decision": "approve",
                    },
                    headers={"Origin": origin, "Cookie": cookie},
                )
                assert approved.status_code == 302, approved.text
                params = parse_qs(urlparse(approved.headers["location"]).query)
                assert params["state"] == ["test-state"]
                code = params["code"][0]
                token_form = {
                    "grant_type": "authorization_code",
                    "client_id": client_id,
                    "code": code,
                    "redirect_uri": "http://localhost:32123/callback",
                    "code_verifier": verifier,
                    "resource": origin + "/mcp",
                }
                bad = await client.post(
                    "/oauth/token", data={**token_form, "code_verifier": "wrong"}
                )
                assert bad.status_code == 400, bad.text
                token_response = await client.post("/oauth/token", data=token_form)
                assert token_response.status_code == 200, token_response.text
                token = token_response.json()["access_token"]
                results.append("OAuth consent, S256 PKCE and token exchange")
                auth_headers = {
                    "Authorization": "Bearer " + token,
                    "Accept": "application/json, text/event-stream",
                    "MCP-Protocol-Version": "2025-11-25",
                }

                async def rpc(method, params=None):
                    r = await client.post(
                        "/mcp",
                        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}},
                        headers=auth_headers,
                    )
                    assert r.status_code == 200, r.text
                    return r.json()

                await rpc(
                    "initialize",
                    {
                        "protocolVersion": "2025-11-25",
                        "capabilities": {},
                        "clientInfo": {"name": "relay-smoke", "version": "1"},
                    },
                )
                listing = await rpc("tools/list")
                assert len(listing["result"]["tools"]) == 13
                observed = await rpc("tools/call", {"name": "phone_observe", "arguments": {}})
                assert (
                    observed["result"]["structuredContent"]["elements"][0]["text"] == "Settings"
                ), observed
                denied = await rpc(
                    "tools/call",
                    {
                        "name": "phone_tap",
                        "arguments": {"serial": "other-device", "x": 10, "y": 20},
                    },
                )
                assert denied["result"]["isError"]
                shot = await rpc("tools/call", {"name": "phone_screenshot", "arguments": {}})
                assert shot["result"]["content"][0]["type"] == "image"
                assert base64.b64decode(shot["result"]["content"][0]["data"]).startswith(b"\x89PNG")
                results.append("authenticated tool list, observation and PNG relay")
                results.append("cross-device override rejected")
                csrf = await client.post(
                    "/authorize",
                    data={
                        "handle": handle,
                        "pairing_code": bridge["pairing_code"],
                        "decision": "approve",
                    },
                    headers={"Origin": "https://attacker.invalid"},
                )
                assert csrf.status_code == 403
                results.extend(
                    ["authorization code cannot be reused", "cross-origin consent blocked"]
                )
                revoke = await client.delete("/api/bridges/" + bridge["id"], headers=headers)
                assert revoke.status_code == 200
                offline = await rpc("tools/call", {"name": "phone_observe", "arguments": {}})
                assert offline["result"]["isError"]
                results.append("bridge revocation stops tool access")
                used_code = await client.post("/oauth/token", data=token_form)
                assert used_code.status_code == 400
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
    report = {"passed": True, "origin": origin, "backend": "fake-adb", "checks": results}
    output = ROOT / "artifacts/relay-smoke/report.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8787")
    asyncio.run(run(parser.parse_args().url.rstrip("/")))
