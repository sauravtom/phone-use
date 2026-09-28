# phone-use v0.1 implementation and validation

Completed 2026-09-28. All source clones, dependency installation, builds and tests
were performed on the AWS development host.

## Delivered

- MIT-licensed standalone Android ADB backend.
- 13 MCP stdio tools, matching JSON CLI and portable agent skill.
- Locked Python dependencies, CI workflow, setup documentation and reference evaluation.
- Separate clones of mobile-use, mobilerun and mobile-harness outside this repository.

## Verified

- 37 automated tests passed under Python 3.12, with an empty environment except PATH.
  Tests include a real MCP client/server connection against a fake ADB subprocess.
- Ruff passed; the skill validator passed; relative documentation links were checked.
- Wheel and source distribution built; the wheel was installed and its CLI exercised
  in an isolated environment. The source archive includes the agent skill and license.
- A real Android 9 x86 software emulator at 480x800 passed the opt-in MCP smoke test:
  19 tool calls, app launch, observed UI, snapshot-checked element taps, focus readiness,
  exact ASCII text including punctuation, button result, PNG screenshots, coordinate
  input, Home and return to the fixture app. Screenshot/UI assertions verified the result.
- mobile-harness / mobilerun-core 1.7.0 independently returned a 10-node UI tree and PNG
  through local Android ADB without API keys or Portal.

## Evidence and limits

The local developer evidence is intentionally gitignored:
`artifacts/device-smoke/report.json`, `verified-ui.json`, and `verified-screen.png`.
The fixture APK and test-only keystore are under `artifacts/android/`.

The first Android 11 image failed during system startup; the Android 9 image initially
showed a System UI ANR. These are not successful Android 11 validation. Testing found
that compressed UI dumps were less compatible in this setup, missing accessibility
roots needed a bounded read retry, and input focus must be verified before typing.
An early typing attempt lost characters while the keyboard was starting; the final
focused-input test verified the exact full value and the app's displayed result.

Swipe/scroll dispatch was exercised on a static fixture; content movement on real
scrollable apps needs separate testing. Physical devices, wireless debugging, Android
versions beyond this emulator, iOS and Unicode entry are not verified here. iOS and
Unicode are intentionally unsupported in v0.1. This is an initial open-source MVP,
not a production compatibility certification. The public source repository is
[github.com/sauravtom/phone-use](https://github.com/sauravtom/phone-use).
No PyPI release has been published.
