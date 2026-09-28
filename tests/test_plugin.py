"""Check the shipped skill bundle, rather than just its source manifest."""

import importlib.util
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_script(path):
    spec = importlib.util.spec_from_file_location("plugin_script", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_plugin_archive_is_portable_and_reproducible(tmp_path):
    builder = load_script(ROOT / "scripts/build-plugin.py")
    archive = builder.build_archive(tmp_path)
    first = archive.read_bytes()
    assert builder.build_archive(tmp_path).read_bytes() == first
    with zipfile.ZipFile(archive) as bundle:
        names = bundle.namelist()
        assert len(names) == len(set(names))
        assert not any(
            part in {".git", ".venv", "artifacts", "__pycache__"}
            for name in names
            for part in Path(name).parts
        )
        assert not any(name.endswith((".keystore", ".env", ".apk")) for name in names)
        assert ".mcp.json" in names
        manifest = json.loads(bundle.read(".codex-plugin/plugin.json"))
        assert manifest["mcpServers"] == "./.mcp.json"
        assert "apps" not in manifest
        interface = manifest["interface"]
        assert len(interface["shortDescription"]) <= 30
        assert len(interface["displayName"]) <= 30
        assert len(interface["defaultPrompt"]) <= 3
        assert all(len(prompt) <= 128 for prompt in interface["defaultPrompt"])
        for key in ("logo", "composerIcon"):
            assert interface[key].removeprefix("./") in names
        for path in (ROOT / "src/phone_use").glob("*.py"):
            name = "skills/phone-use/runtime/" + path.relative_to(ROOT).as_posix()
            assert bundle.read(name) == path.read_bytes()
        assert bundle.read("skills/phone-use/runtime/uv.lock") == (ROOT / "uv.lock").read_bytes()
        extracted = tmp_path / "path with spaces" / "phone-use"
        bundle.extractall(extracted)
    launcher = load_script(extracted / "skills/phone-use/scripts/phone_use.py")
    assert launcher.runtime_root() == extracted / "skills/phone-use/runtime"


def test_source_launcher_uses_checkout():
    launcher = load_script(ROOT / "skills/phone-use/scripts/phone_use.py")
    assert launcher.runtime_root() == ROOT


def test_full_plugin_declares_hosted_mcp(tmp_path):
    builder = load_script(ROOT / "scripts/build-plugin.py")
    with zipfile.ZipFile(builder.build_archive(tmp_path)) as bundle:
        manifest = json.loads(bundle.read(".codex-plugin/plugin.json"))
        assert manifest["mcpServers"] == "./.mcp.json"
        servers = json.loads(bundle.read(".mcp.json"))["mcpServers"]
        assert servers["phone-use"]["url"] == "https://phone-use.xagi.in/mcp"


def test_portal_upload_contains_one_skill_root(tmp_path):
    builder = load_script(ROOT / "scripts/build-plugin.py")
    archive = builder.build_archive(tmp_path, skills_only=True)
    original = archive.read_bytes()
    assert builder.build_archive(tmp_path, skills_only=True).read_bytes() == original
    with zipfile.ZipFile(archive) as bundle:
        names = bundle.namelist()
        assert "SKILL.md" in names
        assert [n for n in names if n.endswith("SKILL.md")] == ["SKILL.md"]
        assert ".codex-plugin/plugin.json" not in names
        assert ".mcp.json" not in names
        assert not any(n.startswith(("skills/", "assets/")) for n in names)
        assert "scripts/phone_use.py" in names
        assert bundle.read("runtime/uv.lock") == (ROOT / "uv.lock").read_bytes()
        for source in (ROOT / "src/phone_use").glob("*.py"):
            assert (
                bundle.read("runtime/" + source.relative_to(ROOT).as_posix()) == source.read_bytes()
            )
        target = tmp_path / "skill with spaces"
        bundle.extractall(target)
    launcher = load_script(target / "scripts/phone_use.py")
    assert launcher.runtime_root() == target / "runtime"
