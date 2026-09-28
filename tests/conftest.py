import json
import sys
from pathlib import Path

import pytest

from phone_use.adb import Adb
from phone_use.core import Phone

XML = """<?xml version="1.0"?><hierarchy rotation="0">
<node text="Settings" resource-id="android:id/title" class="android.widget.TextView"
content-desc="" bounds="[10,100][210,160]" enabled="true" clickable="true"/>
<node text="private-password" content-desc="also-private" password="true" enabled="true"
bounds="[10,200][210,250]"/>
<node text="disabled" bounds="[10,300][210,350]" enabled="false"/>
<node text="invisible" bounds="[0,0][0,0]"/>
</hierarchy>"""


@pytest.fixture
def fake(tmp_path, monkeypatch):
    executable = tmp_path / "adb"
    source = Path(__file__).with_name("fake_adb.py").read_text()
    executable.write_text(f"#!{sys.executable}\n" + source)
    executable.chmod(0o755)
    xml = tmp_path / "screen.xml"
    xml.write_text(XML)
    log = tmp_path / "commands.jsonl"
    monkeypatch.setenv("PHONE_USE_ADB", str(executable))
    monkeypatch.delenv("PHONE_USE_SERIAL", raising=False)
    monkeypatch.setenv("FAKE_XML", str(xml))
    monkeypatch.setenv("FAKE_ADB_LOG", str(log))
    return Phone(Adb(str(executable))), xml, log


def calls(log):
    return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
