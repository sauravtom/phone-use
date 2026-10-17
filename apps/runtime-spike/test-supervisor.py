"""Linux host check of timeout/cancel cleanup; this is not Android evidence."""

import argparse
import json
import subprocess
import tempfile
import time
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("runner", type=Path)
args = parser.parse_args()
runner = str(args.runner.resolve())
results = []
with tempfile.TemporaryDirectory(prefix="runtime-supervisor-") as directory:
    root = Path(directory)
    for action in ("timeout", "cancel"):
        marker = root / action
        # Synthetic fixture path is supplied as a positional shell argument.
        proc = subprocess.Popen(
            [
                runner,
                "1" if action == "timeout" else "10",
                "/bin/sh",
                "-c",
                '(sleep 2; printf leak > "$1") & wait',
                "fixture",
                str(marker),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if action == "cancel":
            time.sleep(0.25)
            proc.terminate()
        output, _ = proc.communicate(timeout=5)
        time.sleep(2.2)
        expected = 124 if action == "timeout" else 130
        passed = proc.returncode == expected and not marker.exists()
        results.append(
            {
                "check": action,
                "passed": passed,
                "exitCode": proc.returncode,
                "descendantMarkerExists": marker.exists(),
                "output": output.decode(),
            }
        )
print(json.dumps({"scope": "Linux host only", "checks": results}, indent=2))
raise SystemExit(0 if all(item["passed"] for item in results) else 1)
