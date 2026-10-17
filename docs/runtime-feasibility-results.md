# Phase 0 runtime feasibility results

Date: 2026-10-17. Status: APK builds and host checks complete; Android execution
verification blocked by unstable software emulation. Phase 0 has not passed its
runtime exit gate. Do not start the full workspace app on the strength of these results.

This spike adds a separate diagnostic APK under `apps/runtime-spike/`. The existing
Python MCP/CLI still has no model dependency or required API key. No full workspace
app, subscription service or cloud desktop was built.

## Scope and environment

- Build/test host: existing `saurav-agents-aws`, Linux x86_64, JDK 17, Android SDK
  platform/build-tools 36, NDK 29.0.14206865. No local Android SDK/emulator installed.
- Host capacity: 8 CPUs, 31 GiB RAM; approximately 17 GiB available during the failed
  emulator runs. No `/dev/kvm` or usable VMX/SVM acceleration was available.
- Four debug APKs: ARM64 and x86_64, each targeting SDK 28 and 36, minimum SDK 26.
  These are research artifacts, not store releases.
- Bundled APK implementation commit: `d9d59ae1943fb0ed7d30b3682721c7970794d83f`.
  Small staged APK commit: `3ed971dea319ac802f5ac641bdd1400c03fea18e`.
- Ubuntu Noble userspace fixture assembled from signed APT package indexes. No
  package maintainer scripts or foreign-architecture programs were run during assembly.
- Unmodified Codex 0.163.0 Linux musl binaries; PRoot 5.1.107.96; libtalloc 2.5.0;
  libandroid-shmem 0.7. Package/release hashes are retained with the AWS artifacts.
- User authorized AWS/emulator testing only. No physical Android phone was accessed.
- No provider credentials were copied, requested or used. No model inference performed.
- The existing `emulator-5554` reviewer emulator and bridge were preserved. Its
  32-bit x86 guest is unsuitable for the 64-bit engine fixtures in this spike.

## Linux host checks

| Check | Result | What it proves |
| --- | --- | --- |
| `uv run ruff check .` | Passed | Final executable-source checkpoint `662395d` |
| `uv run pytest -q` | 51 passed in 19.01s | Existing 48 tests plus archive hash/path/link boundary tests |
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

**No app-written Android runtime report was obtained.** No Ubuntu shell, Python,
Git, networking, PRoot, Codex or cancellation check is counted as passing on Android.
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

## Physical ARM64 checks

**Not run**, by the user's AWS/emulator-only choice. An ARM64 APK building and having
64 KiB-aligned Codex ELF load segments does not establish ARM64 execution, 16 KiB-page
device compatibility, Bun/JIT behavior, battery usage or Android 16 compatibility.

## Remaining gates

**Decision: hold the full workspace UI and agent beta.** The existing AWS VM is
usable for builds but did not provide a reliable Android execution environment in
these trials. The next verification run needs an authorized physical ARM64 phone or
an available, reliably accelerated Android host. Neither was used or provisioned.

Still required: real ARM64 shell/tool subprocesses; DNS/TLS and Git; Android
cancellation/restart/background behavior; hostile/corrupt/low-space/interrupted
runtime-pack installation; workspace isolation and secret-handling checks; working
agent sandbox primitives; an authenticated provider task and permission-denial path.

Claude was not bundled or tested in this first Codex-focused probe. No Linux desktop,
systemd, distribution compatibility, Play eligibility or offline model inference is
claimed. PRoot is a filesystem compatibility layer, not a security sandbox.

## Artifacts and reproduction

See [the harness README](../apps/runtime-spike/README.md) for preparation, build and
collection commands. AWS task root: `/home/saurav/builds/phone-use-phase0/`.

- `artifacts/final/`: larger bundled APKs from the first installer experiment.
- `artifacts/staged/`: preferred small diagnostic APKs; requires the matching runtime ZIP.
- `artifacts/api29*`: collector output directories; no app-written reports were produced.
- `artifacts/host-supervisor.json`, `artifacts/host-codex.json`: host-only evidence.
- `runtime/*/packages.txt`, `runtime/engines.json`: exact fixture provenance.
- `runtime/*/pack/`: ZIPs and per-file hashed manifests. The manifests are embedded
  in both APK modes; the ZIP is bundled or imported separately according to the mode.
- Emulator, installation and collector logs stay outside Git.

Runtime manifest SHA-256 values:

- amd64: `036a4270b0963fc3f536d216c50aeed7941767741b29533293ff2d32539aaf06`
- arm64: `253fb46f7fc6430e15d4c3eee6937e6f36ee62938ac41e94f7ce9cfa7c230e1e`

The four small APKs and selected diagnostic logs were copied to local
`artifacts/runtime-spike/`; their APK hashes were checked against AWS. A partial
download of a larger APK was cancelled and removed; its complete AWS original remains.
Source, build/collection scripts and this report are backed up on the existing GitHub
repository's `sodex/runtime-feasibility-spike` branch. Large APKs/runtime packs and raw
logs remain outside GitHub; there is no separately verified remote artifact backup.
The unrelated untracked `docs/yc-readiness.md` was not changed or included in the backup.

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
