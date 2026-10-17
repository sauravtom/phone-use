# Android runtime feasibility APK

This is a standalone research harness. It does not change phone-use's Python MCP
tools or require a model key. Build only on the existing AWS Linux host. No Gradle,
local Android SDK, desktop UI, relay, model inference, or personal files are involved.

The APK intentionally uses the Android platform UI and a small NDK supervisor.
Each command runs as the app UID, with a time limit and task-owned process group.
The supervisor is not a security sandbox; descendants that deliberately escape
their process group are outside this first prototype's cancellation guarantee.

## Build on AWS

Use an isolated checkout and output directory outside Git. Prerequisites are the
existing Docker, Python 3.11+, JDK 17, SDK platform/build-tools 36 and NDK 29.0.14206865.
The package preparation script downloads Ubuntu Noble packages through APT's signed
repository verification, extracts them without running maintainer scripts and records
package versions/hashes. It is a curated userspace fixture, not a bootable Ubuntu OS.

```sh
bash apps/runtime-spike/prepare-runtime.sh /home/saurav/builds/phone-use-phase0/runtime
python3 apps/runtime-spike/fetch-engines.py /home/saurav/builds/phone-use-phase0/runtime
python3 apps/runtime-spike/pack.py /home/saurav/builds/phone-use-phase0/runtime/amd64/root /home/saurav/builds/phone-use-phase0/runtime/amd64/pack
python3 apps/runtime-spike/build.py --sdk /home/saurav/Android/Sdk --runtime /home/saurav/builds/phone-use-phase0/runtime/amd64/pack --native-extra /home/saurav/builds/phone-use-phase0/runtime/amd64/native-extra --out /home/saurav/builds/phone-use-phase0/artifacts --abi x86_64 --target 28
```

Repeat the pack/build for `arm64` / `arm64-v8a` and both targets 28 and 36.
For the preferred small test APK, use `--staged-runtime` and a fresh output directory
such as `/home/saurav/builds/phone-use-phase0/artifacts/staged`. This keeps the
manifest and small native helpers inside the APK, while the ZIP is imported into
app-private storage separately. Every imported file must still match the manifest
signed into the APK. The extra APK-installed Codex copy is omitted in this mode;
Codex from the runtime payload can still be tested.

Builds are debug-signed with a task-local throwaway key outside source. Do not ship
these as a production app. The build embeds its source commit and runtime manifest;
APK hashes are recorded in the external test report. APT versions are recorded but
not yet pinned to a snapshot; retain packages.txt and the downloaded packages.

The optional engine fetcher pins Codex 0.163.0 and checks GitHub's release asset
digest. PRoot and its two dependencies are checked against hashes in Termux's
HTTPS package index, with exact versions recorded in `engines.json`. That index
check is not independent signature verification. Vendor binaries are unmodified.
Before distributing an app publicly, complete the third-party license/source-offer
review and package all required notices; these APKs are internal feasibility builds.

## Test on the dedicated AWS emulator

Always use an explicit serial. Never operate the existing reviewer emulator.

```sh
adb -s emulator-5580 install /home/saurav/builds/phone-use-phase0/artifacts/runtime-spike-x86_64-target28.apk
adb -s emulator-5580 shell am start -n dev.phoneuse.spike.legacy/dev.phoneuse.spike.MainActivity --ez runDiagnostics true
adb -s emulator-5580 exec-out run-as dev.phoneuse.spike.legacy cat files/report.json
```

`run-as` reads the diagnostic report only. Executable tests are launched by the
Activity, never by ADB shell. The app also has Run, Cancel and Export buttons.
It persists each result atomically and labels a previously running report interrupted
on restart. Leaving/destroying the Activity cancels work; persistent background
execution is deliberately outside this initial probe.

For bounded collection of both variants after the emulator boots:

```sh
python3 apps/runtime-spike/verify-emulator.py --adb /home/saurav/Android/Sdk/platform-tools/adb --serial emulator-5580 --artifacts /home/saurav/builds/phone-use-phase0/artifacts
```

For staged APKs, also pass `--runtime-pack /home/saurav/builds/phone-use-phase0/runtime/amd64/pack/runtime.zip`
and point `--artifacts` to the staged output directory. `--reports` can select a
separate evidence directory for each emulator. The debug importer copies bytes
with `run-as`; it never runs a runtime test through ADB. The Activity performs all
executable checks under its normal app UID. No credentials are imported.

For the separate Linux host supervisor check (never count this as Android evidence):

```sh
cc -O2 -Wall -Wextra -Werror apps/runtime-spike/native/runner.c -o /home/saurav/builds/phone-use-phase0/host-runner
python3 apps/runtime-spike/test-supervisor.py /home/saurav/builds/phone-use-phase0/host-runner
```

Checks explicitly distinguish `passed`, `failed`, `cancelled`, and `not_run`.
An expected timeout is passing only when the supervisor returns 124. Codex protocol
success requires an actual initialize response, not just exit code zero.

## Boundaries

- Runtime files are bounded, hashed and extracted to private staging before activation.
  Update rollback, corrupt-pack tests, low-space tests and hostile symlink chains still
  need a dedicated fault-injection suite before use with downloaded/user-supplied packs.
- Only fixture contents matching the APK-signed manifest are accepted. A staged ZIP
  is untrusted until its file hashes, paths and sizes are verified by the app.
- No credentials are loaded; cloud/authenticated agent tasks remain not run.
- x86_64 emulator findings cannot establish ARM64/JIT or current Android compatibility.
- Android 11 can compare target-dependent W^X behavior, but cannot validate Android 16
  lifecycle, kernel or distribution behavior merely by setting targetSdk 36.
- Native execution is scoped by the Android app sandbox. PRoot, if tested, only changes
  filesystem views and is not additional isolation between agents and app credentials.

## AWS-hosted ARM64 evidence

The [Device Farm adapter](devicefarm/README.md) exercises bundled builds on
AWS-owned devices, without a personal phone or local emulator. The expanded APK
adds PRoot file round trips, Git init/add/commit/diff/local clone, active Android DNS
configuration, DNS/TLS/public Git clone, a timed descendant marker and Codex
initialization inside PRoot. Native Android DNS configuration requires only the
normal `ACCESS_NETWORK_STATE` permission; no broad storage permission is requested.

Keep the original failing direct-loader probes in the report as comparison data.
Use the [execution report](../../docs/runtime-feasibility-results.md) for verified
results rather than assuming an implemented probe passed. The expanded collector
checks short background/foreground, completed report restart and interrupted
report recovery separately from runtime probes.

The final Codex probes use the pinned 0.163.0 binary's generated JSON schema
(`app-server generate-json-schema --out ...`) for `command/exec`. They initialize,
send `initialized`, then request a bounded bash → Python → Git command and require
an actual id-2 response, zero exit code and fixture output. Two independent policies
are tested: `externalSandbox`, meaning only the existing Android app-UID boundary
for this synthetic fixture, and Codex `readOnly`. Neither is an automatic fallback.
The former does not establish per-workspace isolation; even a successful read-only
launch would still need a separate write-denial test. No model turn or credentials
are involved. PRoot's Codex home is `/home/spike`, inside this app's private rootfs.
