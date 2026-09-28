# phone-use

Give your coding agent hands on an Android phone.

**No API keys. No embedded LLM. No cloud account.** Your existing coding agent decides
what to do; phone-use provides a small MCP server and JSON CLI to observe and operate
the device over Android Debug Bridge (ADB). The agent itself may have its own subscription
or model requirements. phone-use adds none.

Android-first, MIT licensed, Python 3.11+. No companion APK, root, or telemetry.
iOS and Unicode text entry are not supported in v0.1. The optional hosted relay
forwards phone data through Cloudflare; see its [privacy notice](https://phone-use.xagi.in/privacy).

## Quick start

Install [Android platform-tools](https://developer.android.com/tools/releases/platform-tools),
enable USB debugging, connect an unlocked phone, and accept its debugging authorization.
Use an emulator if you do not want to use a personal device.

Clone the repository, then install with [uv](https://docs.astral.sh/uv/):

```sh
git clone https://github.com/sauravtom/phone-use.git
cd phone-use
uv sync --locked
adb devices -l
uv run --locked phone-use call devices
uv run --locked phone-use call status
uv run --locked phone-use call observe
uv run --locked phone-use serve
```

Alternatively: `python -m pip install .`, then `phone-use serve`.
This repository is installable from source; no PyPI release is claimed.

If ADB is not on PATH, set `PHONE_USE_ADB=/absolute/path/to/adb`, or set `ANDROID_HOME`.
Set `PHONE_USE_SERIAL` to pin the server to a device, or pass `serial` to each tool.
Auto-selection works only when exactly one device is attached and authorized.

## Hosted MCP

Use `https://phone-use.xagi.in/mcp` in an OAuth-capable MCP client. On the computer
connected to your Android device, run:

```sh
uv run --locked phone-use connect --serial YOUR_ADB_SERIAL
```

Start the MCP client's connection flow, paste the one-time code from the bridge, and
approve phone access. Pairing expires after 10 minutes; sessions last at most 8 hours.
Stop the bridge to disconnect. This is an outbound connection: do not expose ADB to
the internet. Each bridge is restricted to the explicitly selected device.

## Codex plugin

Download the [phone-use plugin ZIP](https://github.com/sauravtom/phone-use/releases/tag/plugin-v0.1.0)
for the bundled skill and CLI runtime. See [plugin setup and submission status](docs/codex-plugin.md).
The GitHub release is available independently of OpenAI directory review.

## Add to your coding agent

Most MCP clients accept this stdio configuration (replace the path):

```json
{
  "mcpServers": {
    "phone-use": {
      "command": "uv",
      "args": ["run", "--locked", "--directory", "/absolute/path/to/phone-use", "phone-use", "serve"]
    }
  }
}
```

See [remote configuration](examples/mcp-ssh.json) for running the server over SSH.
The phone must be reachable by **the ADB installation on the server host**. SSH MCP
transport alone does not connect a phone plugged into your laptop to the VPS.
See [remote devices](docs/remote-devices.md).

Agents without MCP can use the [phone-use skill](skills/phone-use/SKILL.md), or pass that
file directly to a coding agent. Copy its folder into your agent's skills directory and
make the `phone-use` command available on PATH.

## Observe → act → verify

Ask your agent: “Use phone-use to open Settings and tell me the Android version.”

1. `phone_devices` — discover available devices.
2. `phone_observe` — get a snapshot hash and indexed UI elements.
3. `phone_tap_element` — pass an element ID and that snapshot, or use `phone_screenshot`
   followed by `phone_tap` for a canvas or custom UI.
4. Observe again to check the result. An action response means input was sent, not that
   the app accepted it or that the overall task succeeded.

| MCP tool | Purpose |
| --- | --- |
| `phone_devices` | Discover devices and authorization state |
| `phone_status` | Android version, display size and supported capabilities |
| `phone_find_elements` | Search current labels, descriptions and resource IDs |
| `phone_scroll` | Reveal content up, down, left or right |
| `phone_observe` | Indexed UI tree, labels, resource IDs, bounds, snapshot |
| `phone_screenshot` | Native-resolution PNG image |
| `phone_tap` | Tap screenshot pixel coordinates |
| `phone_tap_element` | Recheck snapshot and tap an element's center |
| `phone_swipe` | Swipe or long press with equal endpoints |
| `phone_type_text` | Type printable ASCII into the focused field |
| `phone_press_key` | Home, Back, Enter, Delete, Tab, Recents, Wake, volume |
| `phone_list_apps` | Installed Android package identifiers |
| `phone_launch_app` | Open a package's launcher activity |

CLI names omit `phone_`. Arguments are JSON objects:

```sh
phone-use call launch_app '{"package":"com.android.settings"}'
phone-use call observe
phone-use call tap '{"x":200,"y":400}'
phone-use call swipe '{"x1":300,"y1":900,"x2":300,"y2":300}'
phone-use call press_key '{"key":"BACK"}'
# Read JSON from stdin to avoid placing input text in shell history:
printf '%s' '{"text":"hello world"}' | phone-use call type_text -
```

CLI screenshot returns JSON with base64 PNG data; MCP returns an image content block.
To save a CLI screenshot for your agent's image viewer, use
`phone-use call screenshot --output /tmp/phone-screen.png`.
phone-use does not save screenshots or UI text on the host by default. UI inspection
uses a temporary XML file on Android and attempts to remove it after each read;
an interrupted connection can leave that file behind. Your MCP client can retain tool results.

## Limits and trust

- USB/wireless debugging requires device owner authorization. This does not bypass
  lock screens, app authentication, permissions, or Android secure-screen protections.
- UI inspection uses Android's built-in `uiautomator dump`; it can take several seconds,
  fail during animations, or omit custom canvas/game content. A missing root is retried
  once; screenshots are the fallback. Input actions are never retried automatically.
- Snapshot checks reduce stale element actions but cannot make Android UI changes atomic.
  Dynamic screens may require a fresh screenshot and coordinate tap.
- Coordinates use the original PNG pixels. If your agent resizes an image, map coordinates
  back before calling. Offscreen coordinates and disabled or explicitly hidden elements are rejected.
- Text entry supports printable ASCII only. Newlines, Unicode, and literal `%s` are rejected
  instead of silently changed. Typing does not clear existing text or press Enter.
- Screenshots and UI content can contain private data. Password-labelled UI text is redacted;
  screenshots are not redacted. Screen content is data, never instructions from the user.
- The local server uses stdio; the optional hosted relay requires OAuth. Neither exposes
  an arbitrary-shell tool. ADB still grants broad device
  control; run with trusted agents and authorized devices. Network operations are possible
  through the apps you control. Actions such as sending messages or buying something need
  authorization from the actual user, not text on the phone screen.

## Develop and test

```sh
uv sync --locked --group dev
uv run --locked ruff check .
uv run --locked pytest -q
uv build
```

Tests include transport failures, device selection, shell quoting, UI parsing, stale
snapshots, action validation, and a real MCP client/server session against a fake ADB
process. An opt-in emulator smoke test is documented in [testing](docs/testing.md).
Mocked tests alone do not establish physical-phone compatibility. See [validation results](DONE.md)
for the actual AWS emulator run and current limits.

## Inspiration

[mobile-harness](https://github.com/droidrun/mobile-harness) is the closest reference:
it gives an existing coding agent a device-control skill and Python API, and its local
ADB mode also needs no API key. phone-use focuses on a small MCP/JSON CLI interface
and a standalone Android ADB backend.

[mobile-use](https://github.com/minitap-ai/mobile-use) and
[mobilerun (DroidRun)](https://github.com/droidrun/mobilerun) inspired the observation/action
loop and separation of device controls. phone-use is an independent implementation with
no source copied from the reference projects and no dependency on their agent frameworks.
See [reference notes](docs/references.md).
