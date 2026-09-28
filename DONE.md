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


## Codex plugin and Cloudflare relay (2026-09-28)

- Created deterministic full-plugin and skills-only ZIPs with the source, locked
  runtime, launcher, manifest, and original icon. Plugin validation passed.
- Hosted HTTPS MCP at https://phone-use.xagi.in/mcp with OAuth S256 PKCE, browser-bound
  consent, per-device pairing, outbound WebSocket transport, bounded requests, and
  expiring sessions. Domain ownership was verified in the OpenAI portal.
- 44 Python tests passed, including hosted/local schema parity and device isolation.
  Ruff, TypeScript checks, Python builds, and
  isolated plugin installation smoke tests passed. No model API keys were used.
- Local and production relay smoke tests passed using fake ADB: OAuth and token flow,
  13 tools, observations/screenshots, device isolation, authorization-code replay
  rejection, cross-origin consent rejection, and bridge revocation.
- A production relay test reached status, app listing and app launch on the real
  Android 9 emulator. Its full UI workflow did NOT pass: System UI stopped responding,
  and a second attempt encountered a device-operation failure. The earlier complete
  19-call test above used local stdio; it does not establish remote end-to-end success.
- An OpenAI directory draft exists with metadata, prompts, release notes and five
  positive/three negative review cases. It has NOT been submitted, approved or listed.
  The skill ZIP passed the portal scan; both icons and review JSON were uploaded.
  Browser OAuth verification remains in progress. A durable reviewer demo and
  Developer Mode demo recording remain outstanding. The current short-lived pairing
  code must not be represented as a permanent reviewer login. Final terms and policy
  attestations have not been accepted.

Relay evidence is under ignored `artifacts/relay-smoke`; plugin evidence is under
`artifacts/plugin-smoke`. These fixtures are synthetic and contain no personal phone
accounts. The hosted relay is experimental; keep this distinction in release notes.


### Directory skill archive correction

The portal rejected the original skills ZIP because it included plugin-level files.
The corrected skills-only builder emits one skill root: `SKILL.md`, `scripts/`,
`agents/`, and `runtime/` at the ZIP top level. The full plugin archive is unchanged.
Ruff and all 45 Python tests pass, including a regression check of the portal layout.
This packaging check does not imply that the directory has accepted or approved it.

### Browser consent origin correction

Browser form submission exposed an Origin mismatch: the consent page's no-referrer
policy caused a null Origin. The page now uses strict-origin, preserving the origin
without sharing OAuth query parameters. The server still rejects null and foreign
origins. Ruff, all 45 Python tests, npm ci/check, and local and production relay
smoke tests passed. Cloudflare version: 17fa9583-83f8-450d-95a6-a1a572ade93c.
These relay checks use fake ADB and do not replace real-device workflow validation.
