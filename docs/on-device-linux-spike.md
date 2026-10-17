# ARM64 Android runtime feasibility spike

Status: the diagnostic harness and AWS APK builds are implemented, and AWS Device
Farm has produced real ARM64 app-UID execution reports. The
[execution report](runtime-feasibility-results.md) distinguishes verified capabilities
from remaining runtime and beta gates. The matrix below remains the required
verification scope. Read the
[architecture decision](on-device-linux-plan.md) first. The spike should answer one
question: can an ordinary, unrooted Android app reliably host the required local
agent/tool subprocess chain under an explicitly chosen distribution model?

## Environment and authorization

Build APKs, cross-compile native components and prepare runtime packs on
`saurav-agents-aws`. Recheck reachability, free memory/disk and active workloads.
Inspect local and remote Git state; use a task branch and a separate remote build
directory or managed worktree. Preserve the running reviewer emulator/bridge.

The host inspected on 2026-10-17 is x86_64 Linux with Android SDK/NDKs and no KVM.
It can build ARM64 artifacts, but native-host tests are not Android validation and
its existing x86 emulator cannot prove the ARM64 loader/JIT route. Do not install
anything on the Mac to compensate. Use an explicitly authorized ARM64 physical
device, or an already-authorized suitable remote device. If none is available,
report the device gate as blocked while completing builds and host-side checks.

Do not borrow the development host's model credentials, operate personal app data,
disable device security controls or purchase a new device service without authorization.
The user subsequently authorized up to $20 for AWS Device Farm, without their phone;
this permits the bounded hosted-device runs described in the execution report.

## Smallest test application

One Android activity with **Run diagnostics**, **Cancel**, and **Export report**.
Show actual step results and elapsed time, not a simulated terminal. Use separate
application IDs for a legacy-target research variant and modern-target experiment
so their behavior can be compared without overwriting an installed app.

Use minimal versioned fixture assets and explicit runtime-pack input. Avoid a full
desktop, cloud relay, payments or polished chat interface. No model call is required
for the initial executable/protocol tests.

## Candidate launchers

1. PRoot-backed userspace for the engine plus its subprocesses.
2. Direct glibc-loader route with an explicitly designed child-exec/path strategy.
3. Modern-target packaged native execution experiment, if neither prior route meets
   the intended distribution requirements.

Test the selected engine binary itself; do not assume an old npm launcher or
Node-based implementation matches today's distribution. Preserve unmodified vendor
binaries where required. Record exact rootfs, tool, engine and launcher versions.

## Required evidence

| Test | Passing evidence | Failure meaning |
| --- | --- | --- |
| Installation | Installs normally; app identity, API/ABI and target recorded | Distribution/device constraint |
| Executable launch | Real child process reports version and exits correctly | Permissions, ABI or loader problem |
| Child chain | Agent/runner → shell → Python/native child produces fixture output | Top-level exec worked but the environment is incomplete |
| Filesystem semantics | Absolute paths, symlinks, spaces, executable bits and shebangs work for declared tools | Direct loader/path strategy requires more work |
| Network | DNS and HTTPS with certificate validation succeed; offline errors are visible | Android/runtime resolver or trust-store problem |
| Git | Clone public fixture, modify a file, show diff and create local commit | Tool/dependency or permission failure |
| Codex protocol | Real app-server initialize and generated-schema match | Engine launch/protocol compatibility failure |
| Codex tools | Authenticated turn runs a fixture command under declared permissions | Protocol-only success is insufficient |
| Claude runtime | Real native engine starts; tool subprocess executes; permission denial works | JIT/loader/adapter incompatibility |
| Cancellation | Cancel ends owned task work, reports interrupted, leaves other processes intact | Process ownership/lifecycle failure |
| Lifecycle | Background/foreground and process restart reconcile persisted state | Resume/duplicate-execution risk |
| Storage | Low-space install rejected; corrupt/traversal pack rejected; interrupted update rolls back | Unsafe provisioning |
| Privacy | No tokens in logs, exports, intents or backups; denied file grant respected | App cannot enter beta |

An unauthenticated app-server handshake is valuable, but it is not an agent task.
An agent writing a file is not enough either: verify contents and run the fixture's
assertions, then reopen after app restart.

## Threat and isolation checks

- Determine the actual UID, SELinux and filesystem boundaries of every process.
  Do not count a PRoot path view as a security boundary.
- Explicitly test what a shell can read outside the chosen project, including runtime
  session/config locations. Use synthetic credentials only.
- Determine whether agent sandbox primitives function on this kernel. Unsupported
  sandboxing must produce a clear capability failure, not an automatic bypass.
- Verify unknown approval requests, disconnected UI and stale generation events
  fail closed without falsely marking the run complete.
- Test a process identity mismatch using controlled fixtures; never kill a live
  unrelated process as a test.

## Report format

Store a sanitized report with: source commit, APK SHA-256, runtime manifest hash,
Android version/vendor, ABI and page size, engine versions, target SDK, chosen
launcher, each attempted check, actual result, duration, human intervention and
failure category. Keep raw logs, APKs, screenshots and runtime packs outside Git;
retain only small redacted summaries and reproducible source in the backup branch.

Publish results under three headings: host-only checks, emulator checks, physical
ARM64 checks. Missing tests remain **not run**, never **passed**. Record fresh-install
and update-from-existing-install outcomes separately.

## Exit decision

Proceed to the workspace UI only when at least one intended distribution route
passes the real ARM64 subprocess, files, networking and lifecycle checks. Proceed
to an agent beta only after a real provider-authenticated workflow and its permission
denial/cancellation path pass. If no route passes, retain evidence, identify the exact
blocker and revise the runtime choice before adding features.
