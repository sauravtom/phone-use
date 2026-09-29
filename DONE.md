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
  Browser OAuth completed successfully and the portal scanned all 13 tools.
  Imported annotation justifications are populated. A durable reviewer demo and
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

### Physical-phone connection smoke test

A user-connected Samsung SM-G985F running Android 13 was reachable from the AWS
checkout through a temporary SSH tunnel to the Mac's USB ADB server. MCP stdio
and the production HTTPS relay both passed device/status checks; the hosted
connection exposed only its paired device and reported a 1080x2400 display.
The real bridge was revoked after testing. No app inputs were sent, and no
personal screen image was saved or published. This validates the physical-phone
connection path only, not the complete interaction workflow or reviewer demo.

### Reviewer demo infrastructure and recording preparation

- Deployed a stateless sample page at https://phone-use.xagi.in/demo. It supports
  observing a labelled input, typing sample text, pressing Apply and verifying the
  echoed result. No APK or account is required. HTML escaping and cross-origin POST
  rejection were checked before deployment.
- Added private reusable reviewer credentials, separate operator registration of a
  dedicated emulator bridge, credential-rotation revocation and supervised renewal.
  Normal phone pairing remains one-time and pinned to its original device.
- Local reviewer-auth integration tests passed using fake ADB, including bad
  credentials, repeated OAuth sign-in, operator-only bridge registration, device
  override rejection and bridge revocation. Normal relay tests passed locally and
  against production. Cloudflare version: 02244143-d412-4f34-b78a-69d55d33a9bb.
- Real reusable reviewer OAuth and status passed against the AWS Android 9 emulator.
  Its complete interaction workflow still fails intermittently: System UI ANRs and
  UI hierarchy timeouts remain. This is NOT a review-ready full-workflow claim.
- Added a fixture-only/browser-sample recorder and a renderer that requires a passing
  MCP workflow and real Android video. Rendering labels the scripted client and 2x
  playback speed. No successful recording has been produced or published yet.
- The connected Samsung rejected the optional native test APK install. The browser
  alternative is prepared, but the last phone observation was a screensaver; user
  unlock is pending. No personal phone is assigned to the reviewer account.

Reviewer credentials and service environment are private AWS files outside Git.
The OpenAI draft remains unsubmitted. Do not fill a demo video URL or claim the five
review cases passed until those results have actually been obtained.

### Physical-phone demo recorded and published (September 29)

- Completed a real Android 13 workflow through the production HTTPS MCP relay:
  inspect sample-page screenshot, tap input, enter "hello world", hide keyboard,
  inspect the new screenshot, tap Apply, and visually confirm "Verified: hello world".
- Chrome did not expose webpage nodes in its Android hierarchy. Used supported MCP
  screenshot/coordinate tools with agent visual review; no automated text assertion
  or successful element-tree workflow is claimed.
- Captured 56.82 seconds of actual Android video; rendered a continuous 28.43-second
  1080p demo at 2x speed on AWS. Cropped only the 40-pixel status bar from the raw
  540x1200 capture. Reviewed one-second contact sheets, key MCP screenshots and the
  rendered final frame; decoded the complete MP4 without ffmpeg errors.
- Published and verified HTTP 200 for:
  https://github.com/sauravtom/phone-use/releases/download/plugin-v0.1.0/phone-use-demo.mp4
- Restored the phone's original stay-awake setting, stopped/revoked the scoped bridge
  and closed the loopback-only SSH ADB tunnel.
- The directory form explicitly asks for a Developer Mode video. This technical
  screenshot-guided MCP recording was not entered as a substitute. The directory
  draft remains unsubmitted; dedicated emulator full-workflow reliability and a
  Developer Mode recording are still outstanding.
