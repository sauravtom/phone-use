"""Build a bounded, hashed rootfs fixture from extracted Ubuntu packages."""

import argparse
import hashlib
import json
import os
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def pack(root: Path, output: Path):
    entries = []
    output.mkdir(parents=True, exist_ok=True)
    with ZipFile(output / "runtime.zip", "w", ZIP_DEFLATED) as archive:
        for directory, dirs, files in os.walk(root, followlinks=False):
            for name in sorted(dirs + files):
                path = Path(directory) / name
                rel = path.relative_to(root).as_posix()
                if path.is_symlink():
                    target = os.readlink(path)
                    # Convert Linux absolute links to rootfs-relative links.
                    if target.startswith("/"):
                        target = os.path.relpath(root / target.lstrip("/"), path.parent)
                    resolved = os.path.normpath(os.path.join(os.path.dirname(rel), target))
                    if resolved == ".." or resolved.startswith("../"):
                        raise ValueError(f"Escaping symlink: {rel}")
                    entries.append({"path": rel, "link": target})
                elif path.is_file():
                    digest = hashlib.file_digest(path.open("rb"), "sha256").hexdigest()
                    entries.append(
                        {
                            "path": rel,
                            "sha256": digest,
                            "size": path.stat().st_size,
                            "executable": bool(path.stat().st_mode & 0o111),
                        }
                    )
                    archive.write(path, rel)
    manifest = {
        "format": 1,
        "files": entries,
        "uncompressedBytes": sum(x.get("size", 0) for x in entries),
    }
    (output / "runtime-manifest.json").write_text(json.dumps(manifest, separators=(",", ":")))
    print(
        json.dumps(
            {
                "files": len(entries),
                "bytes": manifest["uncompressedBytes"],
                "zip_sha256": hashlib.file_digest(
                    (output / "runtime.zip").open("rb"), "sha256"
                ).hexdigest(),
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    pack(args.root, args.output)
