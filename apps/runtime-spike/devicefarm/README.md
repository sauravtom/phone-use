# AWS Device Farm runtime probe

This collector is separate from the emulator collector and refuses to start
without Device Farm run/device ARNs, an assigned physical-device UDID, and an
Android job. It only addresses that serial. All executable runtime probes run
inside the APK Activity as the app UID; the host reads evidence with `run-as`.

The user approved up to $20 for Device Farm on 2026-10-17. Do not provision EC2,
buy device slots or run model inference under that approval. Start with one device
and one target at a time, inspect results and metered device minutes, and schedule
another job only when enough budget remains for its timeout plus setup/cleanup.

## Prepare on the existing AWS build VM

```sh
python3 apps/runtime-spike/devicefarm/package.py \
  --apks /home/saurav/builds/phone-use-phase0/artifacts/final \
  --out /home/saurav/builds/phone-use-phase0/artifacts/devicefarm/tests.zip
```

The ZIP contains `tests/test_runtime.py`, requirements and an `expected.json`
generated from both actual bundled ARM64 APKs. It pins each submitted APK SHA-256,
embedded build metadata and runtime-manifest hash. No APK, runtime or credential
is included in the test ZIP. Early bundled APK metadata predates `runtimeDelivery`;
absence of that field means bundled delivery for these pinned fixtures.

## Submit after authentication

Use the dedicated `phone-use-phase0` AWS CLI profile. Confirm the account matches
the existing build VM, then inspect Device Farm account settings and device list
in `us-west-2`. Select a currently available public ARM64 Android model; a catalog
entry alone does not prove runtime ABI, OS or page size. The collector checks the
actual ABI and captures the device properties and app-native page-size probe.

Use an isolated project named for the phone-use phase-0 spike. Upload:

- One bundled `runtime-spike-arm64-v8a-target28.apk` or `target36.apk` as `ANDROID_APP`.
- `tests.zip` as `APPIUM_PYTHON_TEST_PACKAGE`.
- `testspec.yml` as `APPIUM_PYTHON_TEST_SPEC`.

Wait for all three uploads to become `SUCCEEDED`. Schedule a custom
`APPIUM_PYTHON` run with exactly one device, `jobTimeoutMinutes: 20` and metered
billing. The custom test uses the host's ADB directly; no Appium server or driver
session is needed. Provider validation and execution of this configuration must
be verified on the first submission; local pytest success does not establish that.

Do not log presigned upload/download URLs or credentials. If uploading the APK
directly from the build VM, pass only the short-lived upload URL to that operation;
do not transfer the user's CLI credential cache or signing keys.

## Read the evidence

- `app-report.json`: incrementally preserved, app-written checks.
- `collection.json`: Device Farm identity, original/service APK hashes, collected
  device properties, report completeness and failed/not-run check names.
- `installed-package.txt`: installed target/version/package information.
- `logcat.txt`, `activity.txt`, `junit.xml`: bounded supporting diagnostics.

Public Device Farm re-signs APKs, so submitted and service hashes may differ.
Embedded build and runtime-manifest identity must still match. The collector
clears only the spike's synthetic fixture package before running, requires
SELinux enforcing and an ordinary app UID, and stops that package afterward.

A Device Farm `FAILED` result can represent a successfully collected negative
runtime finding. Inspect `collection.json` to distinguish complete evidence from
installation/collection failure. A `PASSED` result only means the implemented
probes passed; `runtimeGate: not_evaluated` prevents treating it as the full phase-0
exit decision. Lifecycle/fault-injection, sandbox behavior and authenticated agent
work remain separately required as described in the main spike plan.

After every completed job, read `deviceMinutes.metered`, accumulate the cost at
the current published rate, retrieve artifacts and check for pending jobs. Do not
spend the remaining allowance on an automatic retry loop. Keep the original APKs
and runtime packs on AWS; copy back only small reports needed for review.
