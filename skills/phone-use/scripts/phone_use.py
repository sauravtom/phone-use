#!/usr/bin/env python3
"""Run the bundled phone-use CLI with locked dependencies outside the plugin cache."""

import hashlib
import json
import os
import shutil
import sys
from pathlib import Path


def runtime_root() -> Path:
    skill = Path(__file__).resolve().parents[1]
    bundled = skill / "runtime"
    root = bundled if bundled.is_dir() else skill.parents[1]
    if not (root / "src/phone_use/cli.py").is_file() or not (root / "uv.lock").is_file():
        raise RuntimeError("Incomplete phone-use plugin. Reinstall the release ZIP.")
    return root


def main() -> None:
    try:
        if sys.version_info < (3, 11):  # noqa: UP036 - runs before installing the package
            raise RuntimeError("phone-use requires Python 3.11 or newer.")
        uv = shutil.which("uv")
        if uv is None:
            raise RuntimeError("uv is required. Install it from https://docs.astral.sh/uv/.")
        root = runtime_root()
        cache_base = Path(
            os.environ.get("PHONE_USE_PLUGIN_CACHE", "~/.cache/phone-use")
        ).expanduser()
        key = hashlib.sha256(str(root).encode()).hexdigest()[:16]
        environment = os.environ.copy()
        environment["UV_PROJECT_ENVIRONMENT"] = str((cache_base / key / "venv").resolve())
        os.execvpe(
            uv,
            [uv, "run", "--locked", "--no-dev", "--project", str(root), "phone-use", *sys.argv[1:]],
            environment,
        )
    except (OSError, RuntimeError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
