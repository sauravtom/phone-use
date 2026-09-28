import shlex
import subprocess
import sys

import pytest
from conftest import XML, calls
from pydantic import ValidationError

from phone_use.adb import Adb, PhoneError
from phone_use.core import parse_tree


def shell_calls(log):
    return [shlex.split(args[3]) for args in calls(log) if len(args) > 3 and args[2] == "shell"]


def test_observe_redacts_and_taps_current_element(fake):
    phone, _, log = fake
    result = phone.observe()
    assert result["serial"] == "test-phone"
    assert len(result["elements"]) == 3
    assert result["elements"][1]["text"] == "[redacted]"
    assert result["elements"][1]["description"] == "[redacted]"
    assert phone.tap_element("0", result["snapshot"])["sent"]
    assert ["input", "tap", "110", "130"] in shell_calls(log)
    # Every generated hierarchy file is removed, including before the action.
    commands = shell_calls(log)
    assert len([c for c in commands if c[:2] == ["rm", "-f"]]) == 2


def test_stale_snapshot_does_not_tap(fake):
    phone, xml, log = fake
    result = phone.observe()
    xml.write_text(XML.replace("Settings", "Another screen"))
    with pytest.raises(PhoneError, match="UI changed"):
        phone.tap_element("0", result["snapshot"])
    assert not any(c[0] == "input" for c in shell_calls(log))


@pytest.mark.parametrize("element", ["2", "missing"])
def test_disabled_and_missing_element(fake, element):
    phone, _, log = fake
    result = phone.observe()
    with pytest.raises(PhoneError, match="missing or disabled"):
        phone.tap_element(element, result["snapshot"])
    assert not any(c[0] == "input" for c in shell_calls(log))


@pytest.mark.parametrize(
    "devices",
    ["", "test-phone device\nsecond device", "test-phone unauthorized", "test-phone offline"],
)
def test_no_implicit_wrong_device(fake, monkeypatch, devices):
    phone, _, log = fake
    monkeypatch.setenv("FAKE_DEVICES", devices)
    with pytest.raises(PhoneError):
        phone.press_key("HOME")
    assert not shell_calls(log)


def test_explicit_and_environment_serial(fake, monkeypatch):
    phone, _, _ = fake
    monkeypatch.setenv("FAKE_DEVICES", "test-phone device\nsecond device")
    assert phone.press_key("HOME", "test-phone")["sent"]
    monkeypatch.setenv("PHONE_USE_SERIAL", "test-phone")
    assert phone.press_key("HOME")["sent"]
    with pytest.raises(PhoneError, match="not connected"):
        phone.press_key("HOME", "unknown")


@pytest.mark.parametrize(
    "text", ["hello world", "it's $(touch /tmp/never); & | `id` \" hi", "100% fine"]
)
def test_text_is_one_remote_shell_argument(fake, text):
    phone, _, log = fake
    phone.type_text(text)
    assert shell_calls(log)[-1] == ["input", "text", text.replace(" ", "%s")]
    raw = calls(log)[-1]
    assert len(raw) == 4


@pytest.mark.parametrize("text", ["हिन्दी", "hello\nworld", "literal%s", "\0", "🙂"])
def test_unsupported_text_rejected_without_adb(fake, text):
    phone, _, log = fake
    with pytest.raises(PhoneError):
        phone.type_text(text)
    assert not calls(log)


@pytest.mark.parametrize(
    "kwargs", [{"x": -1, "y": 10}, {"x": True, "y": 1}, {"x": "10", "y": 10}, {"x": 1.5, "y": 10}]
)
def test_coordinate_types_are_strict(fake, kwargs):
    phone, _, log = fake
    with pytest.raises(ValidationError):
        phone.tap(**kwargs)
    assert not calls(log)


def test_bounds_and_duration(fake):
    phone, _, log = fake
    with pytest.raises(PhoneError, match="outside"):
        phone.tap(320, 640)
    with pytest.raises(ValidationError):
        phone.swipe(1, 2, 3, 4, 10001)
    assert not any(c[0] == "input" for c in shell_calls(log))
    assert phone.swipe(30, 400, 30, 100, 500)["sent"]
    assert shell_calls(log)[-1] == ["input", "swipe", "30", "400", "30", "100", "500"]


def test_launch_and_apps(fake):
    phone, _, log = fake
    assert "com.android.settings" in phone.list_apps()["packages"]
    assert phone.launch_app("com.android.settings")["sent"]
    assert shell_calls(log)[-1] == ["am", "start", "-W", "-n", "com.android.settings/.Settings"]
    with pytest.raises(PhoneError, match="No launchable"):
        phone.launch_app("com.example.missing")
    with pytest.raises(ValidationError):
        phone.launch_app("com.android.settings;id")


def test_malformed_and_entity_xml_rejected(fake):
    phone, xml, log = fake
    xml.write_text("<broken")
    with pytest.raises(PhoneError, match="invalid UI"):
        phone.observe()
    assert shell_calls(log)[-1][:2] == ["rm", "-f"]
    with pytest.raises(PhoneError):
        parse_tree(
            '<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><hierarchy>&xxe;</hierarchy>'
        )


def test_transport_failure_and_timeout(fake, monkeypatch):
    phone, _, _ = fake
    monkeypatch.setenv("FAKE_ADB_MODE", "error")
    with pytest.raises(PhoneError, match="failed"):
        phone.devices()
    monkeypatch.setenv("FAKE_ADB_MODE", "timeout")
    phone.adb.timeout = 0.05
    with pytest.raises(PhoneError, match="timed out"):
        phone.devices()
    with pytest.raises(PhoneError, match="not found"):
        Adb("/nonexistent/adb").devices()


def test_cli_errors_are_machine_readable_without_tracebacks(fake):
    exe = str(__import__("pathlib").Path(sys.executable).with_name("phone-use"))
    result = subprocess.run([exe, "call", "tap", '{"x":-1,"y":10}'], capture_output=True, text=True)
    assert result.returncode == 1
    assert '"error"' in result.stderr
    assert "Traceback" not in result.stderr
    result = subprocess.run(
        [exe, "call", "type_text", "-"],
        input='{"text":"hello world"}',
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert '"sent": true' in result.stdout


def test_status_capabilities_and_find_preserve_snapshot(fake):
    phone, _, _ = fake
    status = phone.status()
    assert status["screen"] == {"width": 320, "height": 640}
    assert status["android_version"] == "11"
    assert status["capabilities"]["unicode_text"] is False
    result = phone.find_elements("SETTINGS")
    assert len(result["elements"]) == 1
    assert phone.tap_element(result["elements"][0]["id"], result["snapshot"])["sent"]
    assert phone.find_elements("private-password")["elements"] == []
    assert phone.find_elements("absent")["elements"] == []


def test_scroll_direction_is_content_relative(fake):
    phone, _, log = fake
    assert phone.scroll("down")["sent"]
    assert shell_calls(log)[-1] == ["input", "swipe", "160", "480", "160", "160", "500"]


def test_hidden_element_is_not_tapped(fake):
    phone, xml, log = fake
    xml.write_text(XML.replace('text="Settings"', 'text="Settings" visible-to-user="false"'))
    result = phone.observe()
    assert result["elements"][0]["hidden"]
    with pytest.raises(PhoneError, match="hidden"):
        phone.tap_element("0", result["snapshot"])
    assert not any(c[0] == "input" for c in shell_calls(log))


def test_adb_cannot_consume_agent_stdin(fake, monkeypatch):
    monkeypatch.setenv("FAKE_ADB_MODE", "read_stdin")
    exe = str(__import__("pathlib").Path(sys.executable).with_name("phone-use"))
    result = subprocess.run(
        [exe, "call", "devices"],
        input="agent protocol data",
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    assert "test-phone" in result.stdout
