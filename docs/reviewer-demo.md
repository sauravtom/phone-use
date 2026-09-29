# Dedicated reviewer demo

The reviewer account controls an account-free Android emulator on AWS, using the
same MCP tools, OAuth consent, relay and pinned-device bridge as normal phone use.
It does not expose the operator's personal USB phone. All app data is disposable.
This is an Android demo; it makes no iOS or Unicode-entry claim.

## Operator setup

Keep these secrets outside the repository:

- `REVIEW_ACCESS_CODE`: `review:` followed by 32 random bytes encoded as hex.
- `REVIEW_ADMIN_KEY`: an independent 32-byte random hex secret, only on the AWS host.
- Worker secrets `REVIEW_ACCESS_HASH` and `REVIEW_ADMIN_HASH`: SHA-256 hex digests of
  the corresponding full values. Never put raw credentials in Wrangler vars or Git.

Provision an emulator with `org.phoneuse.fixture` installed from the test APK.
Run `scripts/review-bridge.py --serial emulator-5554` under a process supervisor,
with the operator key in its private environment and the AWS Android platform-tools
on PATH. The supervisor refuses physical-device serials and checks Android's
emulator property before registering the bridge. The credential is never printed.

The operator endpoint consumes a fresh bridge pairing code before publishing its
session. Reviewers cannot register or switch devices. The supervisor renews the
bridge before its eight-hour deadline and never replays phone inputs. OAuth grants
for the review account follow this dedicated bridge across renewal. Ordinary OAuth
connections keep their originally paired session and cannot follow reviewer resets.

Changing or removing `REVIEW_ACCESS_HASH` disables existing review grants; changing
the access code requires sharing the new code privately with the review team.
Stopping the supervisor revokes the active bridge. Keep the emulator available for
ongoing review, and supply only sample data. Never add a personal account to it.

## Reviewer sign-in

1. Connect the submitted MCP server, `https://phone-use.xagi.in/mcp`, with OAuth.
2. On the phone-use consent page, paste the supplied `review:` access code into
   **Pairing code or reviewer access code** and choose **Allow phone control**.
3. The dedicated emulator is ready without running ADB or installing anything.

The access code belongs only in the private test-credentials submission field.
Do not put it in a public video, source file, screenshot, release or issue.

## Evidence and recording

A passing fake-ADB relay test validates authentication and isolation only. Before
claiming the demo is ready, run every positive review case against the real emulator
through the public MCP URL, capture actual app state, and verify the recording.
Show observation, app launch, a focused text input, the exact displayed result,
a screenshot and navigation. Label any editing or speed changes. Do not fabricate
phone screens or present a scripted MCP client as an LLM conversation.

## Recording commands

The public sample page at https://phone-use.xagi.in/demo works without an APK. It
echoes sample text without persistence. Open it in Android Chrome before recording.
The optional permission-free native fixture is built by `scripts/build-test-apk.sh`.
For repeatable runs it includes a Reset demo button and disables keyboard suggestions.

On the AWS host, with an explicitly authorized test device selected:

```sh
PHONE_USE_RECORDING_AUTHORIZED=1 PHONE_USE_RECORDING_MODE=browser \
  uv run python scripts/record-demo.py --serial YOUR_TEST_SERIAL
uv run python scripts/render-demo.py
```

Omit `PHONE_USE_RECORDING_MODE=browser` to record the native fixture. The recorder
checks for the sample controls before capture, verifies focus before typing, checks
the exact displayed result, and saves an actual MCP screenshot and Android MP4.
It never navigates to personal apps or Home during capture. Review the whole capture
for notifications or other private content before publishing. The shareable version
clearly labels its continuous capture as 2x speed and its client as screenshot-guided MCP.
The renderer refuses a failed test report.

`uv run python scripts/review-device-smoke.py` checks real reviewer OAuth and status
after loading the private environment. Add `--serial emulator-5554` for the complete
native fixture workflow. Do not treat the status-only check as a full demo pass.

### Screenshot-guided browser capture

Some Chrome versions omit webpage nodes from Android's accessibility tree.
Use the screenshot-and-coordinate fallback only after inspecting the sample page:

```sh
PHONE_USE_RECORDING_AUTHORIZED=1 PHONE_USE_RECORDING_MODE=visual-browser \
  uv run python scripts/record-demo.py --serial YOUR_TEST_SERIAL
```

The recorder writes `artifacts/recorded-demo/before-screen.png` and prints
`PREVIEW_READY`. Inspect that image, then write `visual-next.json` in the same
directory with `{"action":"start","x":X,"y":Y}`, where X/Y are the input coordinates
in the original screenshot resolution. Capture begins and MCP enters sample text.
At `TYPED_READY`, inspect `typed-screen.png`, confirm the exact text, and write
`{"action":"apply","x":X,"y":Y}` using the newly observed Apply coordinates.
Do not reuse coordinates from a different phone or an earlier UI state.

The script leaves `report.json` with `passed: false` even when tool calls complete.
Inspect `verified-screen.png` and the video before changing the report to passed;
record the visual verification method, the exact result, and
`automatic_text_assertion: false`. This is supervised visual verification, not an
automated text assertion. The renderer still requires a passed report and a retrieved
video. `--crop-top N` can remove the Android status bar; document the crop.

The September 29 physical Android 13 capture passed this visual workflow using
`phone_screenshot`, `phone_tap`, `phone_type_text`, and `phone_press_key`.
Its 56.82-second raw recording is published at 2x speed, with the top 40 pixels of
the 540x1200 capture removed. No account data or notification content was visible in
the reviewed frames. Rendering and tests ran on AWS.

The OpenAI submission form explicitly requests a **Developer Mode** recording.
This technical MCP demo does not replace that recording or the dedicated review
device's full interaction tests. Directory publication remains pending.
