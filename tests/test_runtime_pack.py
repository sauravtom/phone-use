"""Check the archive trust boundary before feeding a fixture to the Android spike."""

import hashlib
import importlib.util
import json
from pathlib import Path
from zipfile import ZipFile

import pytest

SPEC = importlib.util.spec_from_file_location(
    "runtime_pack", Path(__file__).parents[1] / "apps/runtime-spike/pack.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_pack_records_contents_modes_and_root_relative_links(tmp_path):
    root = tmp_path / "root"
    (root / "usr/bin").mkdir(parents=True)
    binary = root / "usr/bin/tool"
    binary.write_bytes(b"synthetic fixture")
    binary.chmod(0o755)
    (root / "bin").symlink_to("/usr/bin")
    output = tmp_path / "pack"
    MODULE.pack(root, output)
    manifest = json.loads((output / "runtime-manifest.json").read_text())
    records = {f["path"]: f for f in manifest["files"]}
    assert records["bin"] == {"path": "bin", "link": "usr/bin"}
    assert records["usr/bin/tool"]["sha256"] == hashlib.sha256(binary.read_bytes()).hexdigest()
    assert records["usr/bin/tool"]["executable"] is True
    assert manifest["uncompressedBytes"] == binary.stat().st_size
    with ZipFile(output / "runtime.zip") as archive:
        assert archive.namelist() == ["usr/bin/tool"]
        assert archive.read("usr/bin/tool") == binary.read_bytes()


def test_pack_rejects_link_outside_root(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "escape").symlink_to("../outside")
    with pytest.raises(ValueError, match="Escaping symlink"):
        MODULE.pack(root, tmp_path / "pack")


def test_pack_does_not_follow_directory_link(tmp_path):
    root = tmp_path / "root"
    (root / "usr/share").mkdir(parents=True)
    (root / "usr/share/file").write_text("fixture")
    (root / "alias").symlink_to("usr/share")
    MODULE.pack(root, tmp_path / "pack")
    with ZipFile(tmp_path / "pack/runtime.zip") as archive:
        assert archive.namelist() == ["usr/share/file"]
