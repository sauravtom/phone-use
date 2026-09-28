"""Real-device test through the public relay and actual CLI bridge. Explicit test device only."""

import argparse
import asyncio
import base64
import hashlib
import importlib.util
import os
import re
import secrets
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

ROOT = Path(__file__).resolve().parents[1]


async def run(origin, serial):
    output = ROOT / "artifacts/review-device-smoke"
    output.mkdir(parents=True, exist_ok=True)
    if not os.environ.get("REVIEW_ACCESS_CODE", "").startswith("review:"):
        raise RuntimeError("Load the private reviewer environment before testing")
    pairing = os.environ["REVIEW_ACCESS_CODE"]
    async with httpx.AsyncClient(base_url=origin, follow_redirects=False, timeout=60) as client:
        register = await client.post(
            "/oauth/register",
            json={
                "client_name": "phone-use dedicated reviewer test",
                "redirect_uris": ["http://localhost:32123/callback"],
                "token_endpoint_auth_method": "none",
                "grant_types": ["authorization_code", "refresh_token"],
                "response_types": ["code"],
            },
        )
        assert register.status_code == 201
        client_id = register.json()["client_id"]
        verifier = secrets.token_urlsafe(48)
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
            .decode()
            .rstrip("=")
        )
        params = {
            "client_id": client_id,
            "redirect_uri": "http://localhost:32123/callback",
            "response_type": "code",
            "scope": "phone:control",
            "state": "device-test",
            "resource": origin + "/mcp",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        consent = await client.get("/authorize?" + urlencode(params))
        handle = re.search('name="handle" value="([^"]+)"', consent.text).group(1)
        approved = await client.post(
            "/authorize",
            data={"handle": handle, "pairing_code": pairing, "decision": "approve"},
            headers={"Origin": origin},
        )
        assert approved.status_code == 302
        code = parse_qs(urlparse(approved.headers["location"]).query)["code"][0]
        response = await client.post(
            "/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": client_id,
                "redirect_uri": params["redirect_uri"],
                "code": code,
                "code_verifier": verifier,
                "resource": origin + "/mcp",
            },
        )
        assert response.status_code == 200
        token = response.json()["access_token"]
        spec = importlib.util.spec_from_file_location(
            "device_smoke", ROOT / "scripts/device-smoke.py"
        )
        test = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(test)
        if serial == "status-only":
            import json

            from mcp import ClientSession
            from mcp.client.streamable_http import streamable_http_client

            async with httpx.AsyncClient(
                headers={"Authorization": "Bearer " + token}, timeout=120
            ) as http:
                async with streamable_http_client(origin + "/mcp", http_client=http) as (
                    read,
                    write,
                    _,
                ):
                    async with ClientSession(read, write) as mcp:
                        await mcp.initialize()
                        result = await mcp.call_tool("phone_status", {})
                        assert not result.isError
                        data = result.structuredContent
                        assert data["serial"].startswith("emulator-")
                        print(
                            json.dumps(
                                {"reviewer_oauth": "passed", "paired_emulator_status": data},
                                indent=2,
                            )
                        )
        else:
            await test.run(serial, output, url=origin + "/mcp", token=token)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="https://phone-use.xagi.in")
    parser.add_argument("--serial", default="status-only")
    args = parser.parse_args()
    asyncio.run(run(args.url, args.serial))
