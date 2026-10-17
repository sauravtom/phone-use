"""Establish a credential-free host baseline, not Android compatibility."""

import argparse
import json
import os
import selectors
import signal
import subprocess
import tempfile
import time
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("binary", type=Path)
args = parser.parse_args()
binary = str(args.binary.resolve())
with tempfile.TemporaryDirectory(prefix="codex-runtime-spike-") as workspace:
    env = {"HOME": workspace, "PATH": "/usr/bin:/bin", "SHELL": "/bin/sh", "TMPDIR": workspace}
    version = subprocess.run(
        [binary, "--version"],
        env=env,
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=20,
        check=True,
    )
    proc = subprocess.Popen(
        [binary, "app-server", "--listen", "stdio://"],
        env=env,
        cwd=workspace,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    response = None
    try:
        proc.stdin.write(
            json.dumps(
                {
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "clientInfo": {
                            "name": "runtime-spike",
                            "title": "Runtime Spike",
                            "version": "0.1",
                        }
                    },
                }
            )
            + "\n"
        )
        proc.stdin.flush()
        with selectors.DefaultSelector() as selector:
            selector.register(proc.stdout, selectors.EVENT_READ)
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                if not selector.select(timeout=1):
                    continue
                line = proc.stdout.readline()
                if not line:
                    break
                message = json.loads(line)
                if message.get("id") == 1:
                    response = message
                    break
        proc.stdin.write('{"method":"initialized"}\n')
        proc.stdin.close()
        proc.wait(timeout=10)
        stderr = proc.stderr.read(10000)
    finally:
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait(timeout=5)
    passed = response is not None and "result" in response and proc.returncode == 0
    print(
        json.dumps(
            {
                "scope": "Linux x86_64 host only",
                "version": version.stdout.strip(),
                "initialize": response,
                "exitCode": proc.returncode,
                "stderr": stderr,
                "passed": passed,
            },
            indent=2,
        )
    )
    raise SystemExit(0 if passed else 1)
