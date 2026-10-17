# Finish the runtime spike using AWS

Decision date: 2026-10-17. Research and read-only host inspection completed;
no infrastructure provisioned, instance restarted, or Device Farm run submitted.
Android runtime feasibility remains unverified. See the
[existing evidence](runtime-feasibility-results.md).

Execution preparation: the user subsequently approved up to $20 for Device Farm.
The [Device Farm collector](../apps/runtime-spike/devicefarm/README.md) is implemented
and its test ZIP built on AWS. Ruff and 58 host tests passed. AWS sign-in refresh
is pending; the browser authorization flow stalled and the normal Console sign-in
page was opened in Chrome. No Device Farm project, upload or run has been created
at this checkpoint, so no Device Farm spend has started. The prior spending
proposal below is now authorized within that $20 scope; do not ask for it again.

## Recommendation

Run the bundled ARM64 diagnostic APK on **AWS Device Farm first**. This directly
tests the architecture required by the product, without the user's phone or a new
EC2 server. Add a temporary KVM-enabled `m7i.xlarge` only if repeated debugging
would benefit from an interactive x86_64 emulator. Keep the shared build VM intact.

| Option | Practical result | Decision |
| --- | --- | --- |
| Load KVM modules on the current T3a | Missing guest CPU virtualization extensions remain missing | Cannot solve the blocker |
| Resize the existing VM to M7i/M8i and enable nesting | Reuses disk/toolchains, but requires stopping shared workloads; still x86_64 | Possible maintenance-window option, not the first step |
| Temporary M7i with nested KVM | Fast x86_64 emulator iteration; still needs ARM64 validation | Preferred debugging fallback |
| AWS Device Farm public Android devices | Real ARM64 Android app execution, without the user's phone | First validation route |
| EC2 bare metal | Hardware virtualization access, larger infrastructure commitment | Unnecessary for the first attempt |

Device Farm is an AWS-hosted physical-device service, not an emulator. It fits
the requirement to avoid the user's phone. If the constraint becomes strictly
emulators-only, the ARM64 physical-device exit gate must remain open.

## Verified existing-host facts

Read-only SSH, DMI, IMDSv2 identity metadata, process inspection and Android
`-accel-check` on 2026-10-17 found:

- EC2 `t3a.2xlarge`, `us-east-1`, x86_64, 8 vCPUs and 31 GiB RAM.
- Approximately 20 GiB available RAM and 354 GiB free disk at inspection time.
- No `/dev/kvm`; neither `vmx` nor `svm` exposed to the guest.
- Emulator acceleration check: `KVM requires a CPU that supports vmx or svm`.
- The existing `emulator-5554` and its reviewer bridge remain running.
- SSH works. The local AWS CLI's STS identity request fails with
  `InvalidClientTokenId`; the remote host has no AWS CLI on PATH.

The `Hypervisor vendor: KVM` field in `lscpu` describes the outer hypervisor; it
does not mean this guest can create accelerated virtual machines. Installing
packages, changing `/dev/kvm` permissions or setting a nested module parameter
cannot expose CPU extensions withheld by the EC2 instance type.

## What changed in AWS support

AWS now supports nested virtualization on selected virtual Intel instances,
including M7i and M8i, with no separate nesting surcharge. T3a is not supported.
The setting must be enabled explicitly. An existing instance must be stopped
before changing it. AWS specifically identifies Android emulators as a use case.
See [EC2 nested virtualization](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/amazon-ec2-nested-virtualization.html)
and the [June 2026 expansion](https://aws.amazon.com/about-aws/whats-new/2026/06/nested-virtualization-intel-us-gov-cloud/).

Google's emulator documentation still contains a general restriction against
running accelerated emulators inside VMs. Treat the AWS route as a feasibility
test, not a locally verified guarantee: require `emulator -accel-check` success,
then a stable boot and actual app report. Intel KVM cannot accelerate an ARM64
Android image; use x86_64 images for this route.
[Android acceleration requirements](https://developer.android.com/studio/run/emulator-acceleration)

## First Device Farm batch

1. Restore AWS account access through the normal sign-in flow. Read account
   settings, remaining trial minutes and available public Android devices in the
   Device Farm region. Confirm device availability before selecting models.
2. Prepare a custom test environment and a small collector on the existing build
   VM. The current `verify-emulator.py` intentionally rejects non-emulator serials;
   keep that guard and add a separate Device Farm adapter pinned to the service's
   `DEVICEFARM_DEVICE_UDID`. Do not broaden it to arbitrary attached devices.
3. Start with **one available ARM64 Android device, target 28 and target 36 in two
   separate jobs**, with a 20-minute execution timeout for each job. Use bundled
   APKs from `artifacts/final/`; they include the runtime pack and installed native
   Codex experiment. This avoids relying on app-private ZIP staging initially.
4. Gate collection on the actual ABI, API, page size, target SDK, UID, SELinux state,
   runtime manifest and fresh report generation. Launch the Activity to execute
   diagnostics. ADB may install/launch/read reports; it must not execute the Linux
   fixture in place of the app.
5. Export report JSON, logcat, package metadata and test-host logs to
   `DEVICEFARM_LOG_DIR`. Verify whether `run-as` works with the service-installed
   debuggable APK. If it does not, implement a bounded diagnostic export path;
   classify collection failure separately from runtime failure.
6. Inspect the first two jobs before spending on more devices. If useful, repeat
   both targets on a second available ARM64 model/OS, preferably a different OEM
   and current Android version. Do not claim Android 16 or 16 KiB-page coverage
   unless those actual configurations are observed.

The service supports a 4 GB app upload, comfortably above our approximately
258 MiB bundled ARM64 APK. Custom environments provide command phases and an
artifact directory. Use custom tests rather than the built-in random exerciser.
Confirm device-side permissions in the first job; documentation alone does not
establish that our PRoot, loader or Codex subprocesses work there.
[File limits](https://docs.aws.amazon.com/devicefarm/latest/developerguide/limits.html),
[test spec](https://docs.aws.amazon.com/devicefarm/latest/developerguide/custom-test-environment-test-spec.html),
[environment variables](https://docs.aws.amazon.com/devicefarm/latest/developerguide/custom-test-environment-variables.html)

Public Device Farm devices re-sign Android APKs. Record the submitted APK hash
and the installed package/certificate separately; a changed signature is not proof
of corrupted runtime data. Re-check installed target SDK and native extraction
behavior. The service has Internet access. Initial tests use only synthetic files
and no provider credentials.
[Device Farm FAQ](https://aws.amazon.com/device-farm/faqs/)

### Spending proposal, not authorization

- Metered rate: **$0.17 per device-minute**; a one-time 1,000-minute trial may
  apply, but this account's remaining allocation has not been checked.
- Two jobs at 20 minutes each: **$6.80** of timed execution; four jobs: **$13.60**.
- Request **up to $20 before tax for the initial batch**, including room for
  installation/cleanup time. This is an operating budget, not an AWS-enforced
  billing cap. Set job timeouts, inspect actual usage after each pair, and do not
  launch further jobs if the remaining allowance is insufficient.
- No monthly device subscription, private device fleet, new EC2 instance, NAT
  gateway or paid model usage is included in this proposal.

[Device Farm pricing](https://aws.amazon.com/device-farm/pricing/) and
[execution timeouts](https://docs.aws.amazon.com/devicefarm/latest/developerguide/how-to-set-default-timeout-for-test-runs.html)

## Optional accelerated emulator host

If iteration warrants it, propose a separate on-demand Ubuntu x86_64
`m7i.xlarge` (4 vCPU, 16 GiB), one AVD at a time, 60 GiB gp3, and an initial
four-hour lifetime. Obtain a live regional quote and separate spending approval
before launch; EC2 pricing and account capacity have not been verified here.
M7i avoids a burst-performance dependency. M8i is a supported alternative if
availability or pricing is better. A GPU is unnecessary for these command tests;
software graphics rendering can coexist with KVM CPU acceleration.
[M7i specifications](https://aws.amazon.com/ec2/instance-types/m7i/)

Before launch, query `describe-instance-types` for
`ProcessorInfo.SupportedFeatures` containing `nested-virtualization`, confirm
regional offerings/quota, and review a minimal security group. Launch with
`--cpu-options NestedVirtualization=enabled`; choosing M7i alone is insufficient.
Use only the committed spike source and selected APK/runtime/image artifacts,
not a clone of the shared VM containing unrelated projects or credentials.

On the new host, require exposed `vmx`, usable `/dev/kvm`, a successful
`emulator -accel-check`, and `-accel on` so failure cannot silently fall back to
software CPU emulation. Run an API 30 control and a current API 35/36 x86_64 image
sequentially. Require package/activity services to stabilize and collect fresh
app-written results. Preserve ordinary app UID and SELinux behavior; no `adb root`
or disabling security controls to make runtime checks pass.

Export evidence before terminating the task-owned instance and deleting only its
approved temporary volume. Configure bounded runtime and verify cleanup; stopping
an instance alone leaves EBS charges. Existing build-server data remains intact.
Do not launch bare metal automatically if nesting fails.

Resizing the existing T3a is a separate maintenance operation: capture workload
and restart plans, verify backup coverage, stop the instance, change to a supported
type with suitable RAM/CPU, enable nesting, start and verify all services. Review
addressing and storage compatibility first. It is not a live KVM toggle and was
not attempted during this investigation.

## What finishes phase 0

An accelerated boot only removes an infrastructure blocker. First obtain real
ARM64 evidence for shell/Python/native child chains, filesystem behavior, Git,
DNS/TLS, Codex startup/protocol and cancellation. Then extend the harness to cover
background/foreground/restart, interrupted/corrupt/low-space provisioning and
synthetic isolation/permission-denial cases. These are not all implemented today.

Apply the existing [spike exit decision](on-device-linux-spike.md#exit-decision):
at least one intended distribution route must pass the ARM64 subprocess, file,
network and lifecycle checks before the full workspace UI. An authenticated agent
workflow, permission denial and cancellation remain a separate gate before beta.
Use a dedicated test credential and explicit model-spend authorization for that
later step; never borrow the host's login. Claude/JIT, battery behavior and store
eligibility remain unverified until separately exercised or assessed.

A useful phase-0 outcome may also be a reproducible **no-go** on the proposed
runtime. Report real failures and choose the next launcher from that evidence;
do not weaken Android controls or turn missing reports into passes.
