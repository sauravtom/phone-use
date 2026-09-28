# Testing

## Automated suite

Run `uv sync --locked --group dev`, then `uv run --locked pytest -q` and
`uv run --locked ruff check .`. The fake ADB process exercises subprocess arguments
and actual MCP framing without claiming Android execution.

## Opt-in device smoke test

Use a disposable emulator or test phone. This test launches and types into a dedicated
fixture app and navigates Home; it does not access personal applications or accounts.
The fixture has no Android permissions and no network code.

With an Android SDK, JDK and zip installed:

```sh
export ANDROID_HOME=/path/to/android-sdk
bash scripts/build-test-apk.sh
adb -s YOUR_TEST_SERIAL install -r artifacts/android/phone-use-test.apk
uv run --locked python scripts/device-smoke.py --serial YOUR_TEST_SERIAL
```

The build defaults to platform android-35 and build-tools 35.0.0; override
`PHONE_USE_TEST_PLATFORM` and `PHONE_USE_TEST_BUILD_TOOLS` for an existing SDK.
It produces a test-only signing key under ignored `artifacts/`; never use it for a release.
For a repeat run, clear **only the disposable fixture** first:
`adb -s YOUR_TEST_SERIAL shell pm clear org.phoneuse.fixture`.

The smoke test creates a real MCP client/server connection with model/API credentials
removed from its child environment. It verifies launch, UI observation, snapshot-checked
element taps, input focus readiness, exact text entry (including shell punctuation), native PNG output,
coordinate actions, navigation and returning to the app. It saves a report, UI tree and
screenshot under ignored `artifacts/device-smoke/`. Swipe/scroll dispatch is tested on
the fixture; list scrolling success needs a scrollable app and separate observation.

No test establishes iOS support. Physical OEM devices and wireless connections require
separate validation; software emulator performance is not representative of a real phone.
