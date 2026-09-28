#!/usr/bin/env python3
"""Keep a dedicated, account-free Android emulator available to directory reviewers.

Operator-only: REVIEW_ADMIN_KEY is read from the service environment, never logged.
Normal phone bridges retain their existing one-time pairing and expiration rules.
"""

import argparse
import asyncio
import os
import re
import signal
import sys
from pathlib import Path

import httpx

from phone_use.adb import Adb


async def run(origin: str, serial: str) -> None:
    if not origin.startswith("https://"):
        raise ValueError("The reviewer bridge requires HTTPS")
    adb = Adb()
    if not serial.startswith("emulator-") or adb.shell(serial, "getprop", "ro.kernel.qemu") != "1":
        raise ValueError("Reviewer access is restricted to an Android emulator")
    key = os.environ["REVIEW_ADMIN_KEY"]
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    while not stop.is_set():
        process = await asyncio.create_subprocess_exec(
            str(Path(sys.executable).with_name("phone-use")),
            "connect",
            "--server",
            origin,
            "--serial",
            serial,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            env={k: v for k, v in os.environ.items() if not k.startswith("REVIEW_")},
        )
        waiters = []
        try:
            pairing = None
            for _ in range(6):
                line = (await asyncio.wait_for(process.stdout.readline(), 90)).decode().strip()
                if re.fullmatch(r"[a-f0-9-]{36}\.[a-f0-9]{64}", line):
                    pairing = line
                    break
            if not pairing:
                raise RuntimeError("Emulator bridge did not become ready")
            async with httpx.AsyncClient(timeout=30, follow_redirects=False) as client:
                response = await client.post(
                    origin + "/api/review-session",
                    headers={"Authorization": "Bearer " + key},
                    json={"pairing_code": pairing},
                )
                if response.status_code != 200:
                    raise RuntimeError("Reviewer bridge registration was rejected")
            print("Dedicated reviewer emulator connected; renewal scheduled.", flush=True)
            waiters = [asyncio.create_task(process.wait()), asyncio.create_task(stop.wait())]
            await asyncio.wait(waiters, timeout=7 * 3600, return_when=asyncio.FIRST_COMPLETED)
        finally:
            for waiter in waiters:
                waiter.cancel()
            await asyncio.gather(*waiters, return_exceptions=True)
            if process.returncode is None:
                process.send_signal(signal.SIGINT)
                try:
                    await asyncio.wait_for(process.wait(), 20)
                except TimeoutError:
                    process.kill()
                    await process.wait()
        if not stop.is_set():
            # Reconnect the transport only. Never replay a phone input after disconnection.
            try:
                await asyncio.wait_for(stop.wait(), 15)
            except TimeoutError:
                pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="https://phone-use.xagi.in")
    parser.add_argument("--serial", required=True)
    args = parser.parse_args()
    asyncio.run(run(args.url.rstrip("/"), args.serial))
