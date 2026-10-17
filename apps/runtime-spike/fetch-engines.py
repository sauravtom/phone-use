"""Fetch unmodified research binaries on AWS; verify upstream asset hashes."""

import argparse
import gzip
import hashlib
import json
import shutil
import subprocess
import tarfile
import urllib.request
from pathlib import Path


def fetch(url: str, target: Path):
    target.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=90) as response, target.open("wb") as out:
        shutil.copyfileobj(response, out)


def digest(path: Path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("runtime", type=Path)
    parser.add_argument("--codex-version", default="rust-v0.163.0")
    args = parser.parse_args()
    base = args.runtime.resolve()
    release = base / "codex-release.json"
    fetch(f"https://api.github.com/repos/openai/codex/releases/tags/{args.codex_version}", release)
    metadata = json.loads(release.read_text())
    provenance = []
    for ubuntu_arch, termux_arch, codex_arch in (
        ("amd64", "x86_64", "x86_64"),
        ("arm64", "aarch64", "aarch64"),
    ):
        target = base / ubuntu_arch
        native = target / "native-extra"
        native.mkdir(parents=True, exist_ok=True)
        name = f"codex-{codex_arch}-unknown-linux-musl.tar.gz"
        asset = next(a for a in metadata["assets"] if a["name"] == name)
        archive = target / name
        fetch(asset["browser_download_url"], archive)
        if asset.get("digest") != "sha256:" + digest(archive):
            raise ValueError("Missing or mismatched GitHub release digest")
        with tarfile.open(archive) as tar:
            binary = next(m for m in tar.getmembers() if m.isfile() and m.name.startswith("codex"))
            destination = target / "root/opt/codex"
            destination.parent.mkdir(parents=True, exist_ok=True)
            with tar.extractfile(binary) as source, destination.open("wb") as out:
                shutil.copyfileobj(source, out)
            destination.chmod(0o755)
        # Also test the same unmodified static executable from APK-installed storage.
        shutil.copyfile(destination, native / "libcodex.so")
        provenance.append(
            {
                "name": name,
                "url": asset["browser_download_url"],
                "sha256": digest(archive),
                "version": args.codex_version,
            }
        )
        index = target / "termux-Packages.gz"
        mirror = "https://packages.termux.dev/apt/termux-main/"
        fetch(mirror + f"dists/stable/main/binary-{termux_arch}/Packages.gz", index)
        packages = {}
        for block in gzip.decompress(index.read_bytes()).decode().split("\n\n"):
            fields = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line)
            if "Package" in fields:
                packages[fields["Package"]] = fields
        extracted = target / "termux"
        for name in ("proot", "libtalloc", "libandroid-shmem"):
            record = packages[name]
            deb = target / Path(record["Filename"]).name
            fetch(mirror + record["Filename"], deb)
            if digest(deb) != record["SHA256"]:
                raise ValueError("Termux package hash mismatch")
            subprocess.run(["dpkg-deb", "-x", str(deb), str(extracted)], check=True)
            provenance.append(
                {
                    "name": name,
                    "architecture": termux_arch,
                    "version": record["Version"],
                    "sha256": digest(deb),
                    "url": mirror + record["Filename"],
                }
            )
        prefix = extracted / "data/data/com.termux/files/usr"
        shutil.copyfile(prefix / "bin/proot", native / "libproot.so")
        shutil.copyfile(prefix / "libexec/proot/loader", native / "libproot_loader.so")
        for library in (prefix / "lib").glob("*.so*"):
            if library.is_file() and ".so" in library.name:
                # Android's native library extraction only includes names ending in .so.
                shutil.copyfile(library, native / (library.name.split(".so")[0] + ".so"))
    (base / "engines.json").write_text(json.dumps(provenance, indent=2) + "\n")


if __name__ == "__main__":
    main()
