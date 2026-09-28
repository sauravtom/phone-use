import pytest

from phone_use.adb import PhoneError
from phone_use.bridge import dispatch, run_bridge


def test_bridge_does_not_expose_other_devices(fake, monkeypatch):
    phone, _, _ = fake
    monkeypatch.setenv("FAKE_DEVICES", "test-phone device\nprivate-other-phone device")
    devices = dispatch(phone, "test-phone", "phone_devices", {})["devices"]
    assert [d["serial"] for d in devices] == ["test-phone"]
    with pytest.raises(PhoneError, match="paired device"):
        dispatch(
            phone, "test-phone", "phone_tap", {"serial": "private-other-phone", "x": 1, "y": 2}
        )


def test_bridge_only_dispatches_allowed_tools(fake):
    phone, _, _ = fake
    for tool in ["_read_tree", "phone__read_tree", "shell", "phone_adb"]:
        with pytest.raises(PhoneError, match="Unknown"):
            dispatch(phone, "test-phone", tool, {})


async def test_bridge_refuses_insecure_remote_url():
    with pytest.raises(PhoneError, match="HTTPS"):
        await run_bridge("http://example.com", "test-phone")
    with pytest.raises(PhoneError, match="credentials"):
        await run_bridge("https://user:password@example.com", "test-phone")


async def test_hosted_schemas_match_local_mcp():
    import json
    from pathlib import Path

    from phone_use.server import create_server

    expected = [tool.model_dump(exclude_none=True) for tool in await create_server().list_tools()]
    actual = json.loads((Path(__file__).parents[1] / "cloudflare/src/tools.json").read_text())
    assert actual == expected
