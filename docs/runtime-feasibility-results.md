# Phase 0 runtime feasibility results

Date: 2026-10-17. Four AWS Device Farm runs completed with real ARM64 app-UID
evidence, without the user's phone. **Core runtime feasibility is demonstrated;
the complete runtime/agent exit gate remains open.** On Android 16 / SDK 36,
Codex's credential-free `command/exec` launched Ubuntu bash → Python → Git under
the Android app sandbox. Files, shebangs/symlinks, local and HTTPS Git operations,
DNS/TLS, timeout cleanup and short lifecycle recovery checks passed.

**Do not claim a dependable agent beta:** Codex's separate read-only sandbox failed
with `cannot establish app-server socket mount isolation`. One initialization-only
PRoot session returned a valid response but exited 128. Provisioning fault injection,
synthetic secret/grant checks, authenticated model turns and long-duration lifecycle
tests remain unverified. Keep the next work focused on these runtime issues.

The [AWS validation plan](aws-android-validation-plan.md) remains useful for the
existing T3a host's KVM limitation. Device Farm removed the execution blocker
without resizing it, provisioning EC2 or using the user's phone.

This spike adds a separate diagnostic APK under `apps/runtime-spike/`. The existing
Python MCP/CLI still has no model dependency or required API key. No full workspace
app, subscription service or cloud desktop was built.

## Scope and environment

- Build/test host: existing `saurav-agents-aws`, Linux x86_64, JDK 17, Android SDK
  platform/build-tools 36, NDK 29.0.14206865. No local Android SDK/emulator installed.
- Host capacity: 8 CPUs, 31 GiB RAM; approximately 17 GiB available during the failed
  emulator runs. No `/dev/kvm` or usable VMX/SVM acceleration was available.
- Initial four debug APKs: ARM64 and x86_64, each targeting SDK 28 and 36, minimum SDK 26.
  These are research artifacts, not store releases.
- Bundled APK implementation commit: `d9d59ae1943fb0ed7d30b3682721c7970794d83f`.
  Small staged APK commit: `3ed971dea319ac802f5ac641bdd1400c03fea18e`.
- Ubuntu Noble userspace fixture assembled from signed APT package indexes. No
  package maintainer scripts or foreign-architecture programs were run during assembly.
- Unmodified Codex 0.163.0 Linux musl binaries; PRoot 5.1.107.96; libtalloc 2.5.0;
  libandroid-shmem 0.7. Package/release hashes are retained with the AWS artifacts.
- User approved up to $20 for AWS Device Farm. AWS-owned physical ARM64 devices
  were used; no personal phone was accessed.
- No provider credentials were copied, requested or used. No model inference performed.
- The existing `emulator-5554` reviewer emulator and bridge were preserved. Its
  32-bit x86 guest is unsuitable for the 64-bit engine fixtures in this spike.

## Linux host checks

| Check | Result | What it proves |
| --- | --- | --- |
| `uv run ruff check .` | Passed | Final executable-source checkpoint `f21cf2c` |
| `uv run pytest -q` | 58 passed in 17.81s | Existing tests, archive boundaries and Device Farm report validation |
| NDK compilation | Passed for both ABIs | Android executable builds; not execution on ARM64 |
| Eight APK signatures/manifests | Passed | Four ABI/target combinations in bundled and staged delivery modes |
| Supervisor timeout | Passed, exit 124 | Linux host fixture descendants did not write their delayed marker |
| Supervisor cancellation | Passed, exit 130 | Linux host fixture descendants did not write their delayed marker |
| Codex `--version` | `codex-cli 0.163.0` | The downloaded x86_64 engine starts on Linux |
| Codex app-server initialization | Passed, real response and exit 0 | Ordered credential-free protocol handshake on Linux |

The Codex host baseline runs in an empty temporary workspace with an explicitly
constructed environment. It reports warnings about temporary-directory helper aliases
and system bubblewrap availability. No sandbox command was executed; the handshake
must not be treated as proof that agent tools or sandboxing work.

## Android emulator checks

**No app-written runtime report was obtained from these software emulators.** None
of their attempts establishes a passing Android shell, Python, Git, networking,
PRoot, Codex or cancellation check. Later physical-device evidence is reported below.
The failures below concern test infrastructure and installation; they do not establish
that these runtimes are incompatible with a real Android phone.

| Attempt | Observed result | Classification |
| --- | --- | --- |
| Android 11, first startup | Did not become usable; restarted with kernel logging | Infrastructure |
| Android 11, second startup | Early install could not find package service; later 600-second boot collector expired | Infrastructure; app not tested |
| Android 10, bundled APK | Boot-completed flag observed; streamed install lost package service with broken pipe | Installation/infrastructure failure; cause not isolated |
| Android 10, initial staged APK attempt | Existing-report probe timed out after 20 seconds before installation | Infrastructure; staged APK not tested |
| Android 10, clean restart with staged APK | Package/activity services did not stabilize within the 300-second readiness window (plus in-flight ADB timeouts) | Infrastructure; staged APK not tested |

The preinstalled Android 11 x86_64 image was started in a separate task-owned AVD,
with software emulation because this AWS host has no usable KVM. The first startup
did not become usable. A second start used one virtual CPU and kernel logging.
An early installation attempt failed with `Can't find service: package`. Android's
`iorapd` also aborted while waiting for the package manager; later the package service
became available. These are emulator bootstrap events, not app-runtime failures.

An Android 10 default x86_64 fallback image was downloaded on AWS during diagnosis
and booted in a separate task-owned AVD at 480x800. Its boot-completed gate passed.
The first full-bundle installation then failed with
`Failure calling service package: Broken pipe (32)`; a later package-service lookup
reported that the service was absent. This is not proof of an engine incompatibility,
and the large bundle's contribution to the failure has not been established.

To isolate package installation from runtime provisioning, a second build mode
produces approximately 449 KiB ARM64 / 457 KiB x86_64 APKs. These embed the trusted
runtime manifest and native helpers, with the large ZIP staged separately into
app-private storage. The app verifies its contents before activation. The extra
APK-installed Codex copy is omitted; that particular modern-target experiment remains
available only in the larger bundled build.

No emulator performance measurement is representative of a physical phone.

Both task-owned emulator processes were stopped after the attempts. The pre-existing
reviewer emulator was left running. AVD data, SDK images and task logs were retained
on AWS for diagnosis; no new paid infrastructure was provisioned.

## Physical ARM64 checks (AWS Device Farm)

Fresh installs of bundled ARM64 APKs from `d9d59ae` were tested on a Google Pixel 8,
Android 14 / API 34, 4 KiB pages. Target SDK 28 used UID 10273 / `untrusted_app_27`;
SDK 36 used UID 10272 / `untrusted_app`. Both required SELinux enforcing. All
executable probes came from the Activity, not privileged ADB shell. The collector
used `run-as` only to read synthetic app evidence.

| Initial probe | Target 28 | Target 36 |
| --- | --- | --- |
| APK-installed native supervisor and Android shell | Pass | Pass |
| Runtime extraction and per-file hash validation | Pass, 16.18s | Pass, 17.48s |
| Execute copied native helper in writable app data | Pass | Permission denied, exit 126 |
| Direct Ubuntu loader version | Pass | Permission denied, exit 126 |
| Direct Ubuntu bash/Python/Git/curl | Exit 159 | Loader execution denied, exit 126 |
| PRoot bash → Python → Git child chain | Pass, 310ms | Pass, 362ms |
| Native Android HTTPS | HTTP 200 | HTTP 200 |
| APK-packaged Codex version and initialize/EOF | Pass | Pass |
| Codex directly from writable runtime payload | Pass | Permission denied, exit 126 |
| Supervisor timeout | Expected exit 124 | Expected exit 124 |

Exit 159 is the supervisor's encoding for signal 31; the collected bounded logcat
excerpt did not establish the offending syscall. Do not present a specific seccomp
cause as confirmed. The direct-loader route is rejected by the observed results.
PRoot changes the child filesystem/exec path successfully in these probes; it does
not weaken Android SELinux or create a security boundary between the app and agent.

Codex 0.163.0 returned a real app-server initialize response and exited in order.
It warned that system bubblewrap was missing and that it would use its bundled
fallback. These initial runs did not execute sandbox commands or model-authenticated tasks.
The final Android 16 run below adds explicit credential-free command/sandbox probes.

Both AWS runs are `FAILED` because the collector fails on any failed probe. Their
`collection` fields are `complete`; these are valid negative runtime findings,
not missing reports or broken installation infrastructure.

### Expanded SDK 36 route on Android 14

APK source `ec20071`, collector source `795c049`. Fresh AWS Pixel 8 API 34 allocation;
its patch-level fingerprint differs from the initial two runs. Source and runtime
hashes are pinned; this is not an identical physical-device performance comparison.

- Passed: Python JSON file write/read with spaces; PRoot DNS using Android's active
  network servers; certificate-validated HTTPS; public Git HTTPS clone, verified HEAD;
  real Codex app-server initialization inside Ubuntu.
- Passed: timed process group returned 124 after a confirmed child started; its delayed
  file marker remained absent after 3.5 seconds.
- Passed: three-second HOME/foreground transition preserved the same generation;
  completed report survived app stop/restart; a newly interrupted run was recovered
  as `interrupted` without starting a duplicate run.
- Partial Git fixture: init, add, commit and diff succeeded. Local clone failed with
  a missing shell helper. Build-host inspection confirmed `/bin` → `usr/bin` existed
  but `/usr/bin/sh` was absent. Package extraction intentionally skips maintainer
  scripts; the corrected fixture explicitly links `sh` → `bash`. A shebang/symlink
  execution assertion was added for the next device run.

Codex inside PRoot identified Ubuntu 24.4.0, but warned about helper aliases beneath
`/tmp` and missing system bubblewrap. Production integration needs a dedicated
persistent home and verified sandbox/helper behavior; these warnings are not waived.

### Final SDK 36 route on Android 16

Source/collector `f21cf2c`; APK SHA-256
`a9ddcf35bcfec2ba39673628672f6d093dfb91942a569b770c4fd7b4821ce55a`.
Google Pixel 10 Pro, actual API 36, ARM64, UID 10307, SELinux enforcing, **4 KiB pages**.
This does not establish 16 KiB-page compatibility. Runtime manifest `c0603334…e84ca`
includes the explicit shell link. Codex now uses persistent `/home/spike` within the
app-private rootfs instead of `/tmp`.

| Candidate-route check | Actual result |
| --- | --- |
| PRoot bash → Python → Git | Passed |
| JSON file with spaces, read-back assertion | Passed |
| Executable shebang script through symlink with spaces | Passed |
| Git init/add/commit/diff/local clone + content assertion | Passed; shell-link repair verified |
| Active-network DNS + certificate-validated HTTPS | Passed, HTTP 200 |
| Public Git HTTPS clone + verified HEAD | Passed |
| Timed child group and delayed descendant marker | Passed |
| HOME/foreground, completed-report restart, interrupted-report recovery | All passed |
| APK-packaged Codex version/initialize/EOF | Passed |
| PRoot Codex initialize-only/EOF | Valid initialize response, but exit 128 after 11.65s; **failed** |
| Codex `command/exec`, explicit Android/external sandbox boundary | Passed: id-2 result exit 0, `CODEX_CHILD_OK` and `git version 2.43.0` |
| Codex `command/exec`, separate `readOnly` policy | Failed: command result exit 1, socket-mount isolation error |

The command probes were constructed from the pinned vendor binary's generated
`CommandExecParams` and `CommandExecResponse` schema. They do not create a model
thread/turn or use authentication. The `externalSandbox` probe intentionally relies
only on Android's existing app UID for a fixed synthetic command. It is **not**
per-workspace isolation or proof that agent secrets are protected. The read-only
probe was independent; it did not trigger a fallback. Even a successful read-only
launch would still need write-denial verification.

The bounded logcat includes Android policy denials for `/proc/version`,
`overcommit_memory` and a shell-test directory. These alone do not identify the
cause of the initialization-only exit 128. Preserve this stability failure rather
than relabeling a response-plus-abnormal-exit as success. Two later independent
command sessions initialized and exited 0; the read-only session's **command**
result was still exit 1. These exit levels are distinct.

## Run and budget ledger

All four provider runs are `COMPLETED / FAILED`; all four collectors completed and
preserved genuine reports. Failed alternatives and the final sandbox/stability
failures intentionally keep the overall provider status red.

| Run ID | Device / target / build | Metered device minutes |
| --- | --- | ---: |
| `34bf6c74-3fa9-48f3-8f35-62530ac505c0` | Pixel 8 Android 14 / 28 / initial | 0.77 |
| `e30ca6f6-99cf-49cd-8c27-ffe522f21251` | Pixel 8 Android 14 / 36 / initial | 0.87 |
| `c1b45b2d-725b-4482-9320-714f1994ce47` | Pixel 8 Android 14 / 36 / expanded | 1.00 |
| `d47cfdaa-3e0d-4269-97ab-a8c1c821c58f` | Pixel 10 Pro Android 16 / 36 / final | 1.02 |
| **Total of rounded run values** | | **3.66** |

The account began with 1,000 trial minutes and reports 996.35 remaining. Its 3.65
minute consumption differs by 0.01 from the sum of separately rounded run values. At the published
[$0.17/device-minute rate](https://aws.amazon.com/device-farm/pricing/), 3.66 minutes
is approximately **$0.62 before trial coverage**, comfortably within the approved
$20. The account's trial allowance covered the observed minute consumption; this
is a usage record, not a billing-invoice reconciliation. No device slots, new EC2,
model inference or personal-device access were used. No active runs remain.

## Remaining gates

Choose the **modern-target PRoot route with APK-installed native components** for
continued runtime engineering. The raw child/file/network/short-lifecycle experiment
passed, including an actual Codex-launched command. Hold the full workspace/agent
beta until the observed stability and sandbox issues have a verified solution.
This experiment does not establish arbitrary Linux packages, a bootable Ubuntu OS, systemd, Omarchy, a desktop, Play eligibility or
on-device model inference. No Claude runtime or JIT behavior was tested.

Still required before beta: provider-authenticated tool execution and permission
denial; working agent sandbox primitives or a reviewed isolation design; synthetic
secret/grant boundaries; hostile/corrupt/low-space/interrupted provisioning; and
long-running background, cancellation and device-resource behavior. No provider
credentials were copied or used. PRoot itself is not an agent security sandbox.

Next work: reproduce and resolve initialization-only shutdown under PRoot; design
and validate an Android-compatible command isolation boundary without silently
weakening requested permissions; add provisioning fault injection and synthetic
secret/file-grant denial cases. Then use a dedicated authorized provider test account
for a real agent turn. Long-duration background/Doze and UI cancellation still need
device checks; short HOME transitions and deadline cleanup are narrower evidence.

## Artifacts and reproduction

See [the harness README](../apps/runtime-spike/README.md) for preparation, build and
collection commands. AWS task root: `/home/saurav/builds/phone-use-phase0/`.

- `artifacts/final/`: larger bundled APKs from the first installer experiment.
- `artifacts/staged/`: small diagnostic APKs; requires the matching runtime ZIP.
- `artifacts/proot-expanded/`: SDK 28/36 expanded PRoot probes (`ec20071`).
- `artifacts/proot-sh/`: SDK 36 shell-link/shebang build (`777271c`); built, not submitted.
- `artifacts/codex-exec/`: SDK 36 shell-link and Codex command probes (`f21cf2c`).
- Local `artifacts/runtime-spike/devicefarm/`: collected app reports, lifecycle
  metadata, run metadata and bounded customer artifacts; ignored by Git.
- [Sanitized Device Farm summary](evidence/android-runtime-devicefarm-2026-10-17.json):
  committed probe statuses, timings, build identities and hashes of the local reports.
- `artifacts/api29*`: collector output directories; no app-written reports were produced.
- `artifacts/host-supervisor.json`, `artifacts/host-codex.json`: host-only evidence.
- `runtime/*/packages.txt`, `runtime/engines.json`: exact fixture provenance.
- `runtime/*/pack/`: ZIPs and per-file hashed manifests. The manifests are embedded
  in both APK modes; the ZIP is bundled or imported separately according to the mode.
- Emulator, installation and collector logs stay outside Git.

Runtime manifest SHA-256 values:

- amd64: `036a4270b0963fc3f536d216c50aeed7941767741b29533293ff2d32539aaf06`
- arm64 initial: `253fb46f7fc6430e15d4c3eee6937e6f36ee62938ac41e94f7ce9cfa7c230e1e`
- arm64 with explicit `sh` → `bash` fixture link:
  `c0603334576d9b4b2277b72c1bccd581d73e18039a547f974d50d7e28e7e84ca`

The four small APKs and selected diagnostic logs were copied to local
`artifacts/runtime-spike/`; their APK hashes were checked against AWS. A partial
download of a larger APK was cancelled and removed; its complete AWS original remains.
Source, build/collection scripts and this report are backed up on the existing GitHub
repository's `sodex/runtime-feasibility-spike` branch. Collected reports also reside
at AWS `artifacts/devicefarm-collected/`; app-report SHA-256 values were checked
against their local copies. Raw logs, APKs and runtime packs remain outside GitHub.
Submitted APKs also exist in Device Farm under its retention policy; runtime packs
and unsubmitted builds have no independently verified durable artifact backup beyond
the original build host. Retain those originals. The unrelated untracked
`docs/yc-readiness.md` was not changed or included in the backup.

Large binaries, runtime packs, signing material and SDK images are not committed.
The throwaway debug signing key stays only in the task's AWS artifact directories.
Complete license/notice/source-offer review before any public binary distribution.

| Bundled APK | SHA-256 |
| --- | --- |
| x86_64 target 28 | `16c9ee6426d789a0d6c275a96582ad0b88de3c1a8effb56a3f5933294e2321d5` |
| x86_64 target 36 | `9520bc270772ea462d8a3c35435d280ed8c0a535d98c624e0f692de0e139a053` |
| ARM64 target 28 | `bbdec2a743e767f1facd4aea32a52a7d86260359b7030d45ca3f12e71b310b0e` |
| ARM64 target 36 | `91d84ce7270dc69487c48f29680081172d3f8f9f03a5dcfab6e56b1e2f38a2a3` |

| Small staged APK | SHA-256 |
| --- | --- |
| x86_64 target 28 | `a3dac8121e2d55bac99676e7d48fc15add636b6e684721014351c729b3e80763` |
| x86_64 target 36 | `8ea1c9ba00d5e3359914c342e140cc5f0b963893573765238a7a03ba81a7528f` |
| ARM64 target 28 | `b87d86dabf5bd2da4a2f3e50de6bf7148c7ceb2f86ad9c6c3da28b57c7bab143` |
| ARM64 target 36 | `65126407d672456d5bce65d5b4537934c5b76c9faa68d0a8cb302f74bb8e45af` |

| Later ARM64 SDK 36 APK | Source | SHA-256 |
| --- | --- | --- |
| Expanded PRoot | `ec20071` | `eb1992269874fa97ad8e6d3c6440ccd0a8d7f839b18316444f0c47db4b3c93a7` |
| Shell-link fixture (built only) | `777271c` | `d56d83fc5429c6d3cce463cc476f2421447b5c6f6be8c3021a173846b3917800` |
| Codex command/sandbox probes | `f21cf2c` | `a9ddcf35bcfec2ba39673628672f6d093dfb91942a569b770c4fd7b4821ce55a` |
