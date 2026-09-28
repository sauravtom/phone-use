#!/usr/bin/env python3
"""Build a Codex plugin ZIP or skill upload from an explicit source allowlist."""

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build_archive(output: Path, *, skills_only: bool = False) -> Path:
    manifest = json.loads((ROOT / ".codex-plugin/plugin.json").read_text())
    files = {}
    for name in ("LICENSE",):
        files[name] = ROOT / name
    for folder in ("assets", "skills/phone-use"):
        for path in (ROOT / folder).rglob("*"):
            if path.is_file() and path.suffix in {".md", ".py", ".yaml", ".svg", ".png"}:
                if "runtime" in path.relative_to(ROOT).parts:
                    raise ValueError("Runtime is generated during packaging; do not vendor it.")
                files[path.relative_to(ROOT).as_posix()] = path
    if not skills_only:
        files[".mcp.json"] = ROOT / ".mcp.json"
    runtime = "skills/phone-use/runtime/"
    for name in ("pyproject.toml", "uv.lock", "README.md", "LICENSE"):
        files[runtime + name] = ROOT / name
    for path in (ROOT / "src/phone_use").glob("*.py"):
        files[runtime + path.relative_to(ROOT).as_posix()] = path
    if skills_only:
        prefix = "skills/phone-use/"
        files = {
            name.removeprefix(prefix): path
            for name, path in files.items()
            if name.startswith(prefix) or name == "LICENSE"
        }
    output.mkdir(parents=True, exist_ok=True)
    kind = "skills" if skills_only else "plugin"
    archive = output / f"phone-use-{kind}-{manifest['version']}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        if not skills_only:
            manifest_entry = zipfile.ZipInfo(".codex-plugin/plugin.json", (1980, 1, 1, 0, 0, 0))
            manifest_entry.compress_type = zipfile.ZIP_DEFLATED
            manifest_entry.create_system = 3
            manifest_entry.external_attr = 0o100644 << 16
            bundle.writestr(manifest_entry, json.dumps(manifest, indent=2) + "\n")
        for name, path in sorted(files.items()):
            if path.is_symlink():
                raise ValueError(f"Refusing symlink in plugin: {name}")
            entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            bundle.writestr(entry, path.read_bytes())
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix(".zip.sha256").write_text(f"{checksum}  {archive.name}\n")
    return archive


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument(
        "--skills-only", action="store_true", help="Skill upload for an MCP-backed portal draft"
    )
    args = parser.parse_args()
    print(build_archive(args.output, skills_only=args.skills_only).resolve())


if __name__ == "__main__":
    main()
