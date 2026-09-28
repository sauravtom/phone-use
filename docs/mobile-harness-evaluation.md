# mobile-harness evaluation

Inspected on 2026-09-28 at revision
`e0e73108aa4aae43dd682b5f713877976b822e1b` from
https://github.com/droidrun/mobile-harness.
Runtime evaluated separately: `mobilerun-core==1.7.0`,
`mobilerun-core-local==0.6.0`, `mobilerun-sdk==5.5.0`.

## Conclusion

This is the closest reference for phone-use. It is a portable Markdown skill/harness
that tells the existing coding agent how to use a device-control library. The model
loop stays in the calling agent. The original mobile-use and mobilerun repositories
also include agent orchestration and model integrations.

**Local Android ADB control in mobile-harness already works without model or cloud API
keys.** Its Python facade lazily initializes cloud credentials; `Mobilerun()` can be
constructed without them. Cloud devices require a Mobilerun API key. Portal HTTP-only
Android access requires a device bearer token, which is distinct from an LLM key.
“No API keys” by itself is therefore not a unique reason to build phone-use.

## Comparison

| Dimension | mobile-harness | phone-use v0.1 |
| --- | --- | --- |
| Agent interface | Markdown skill + Python Mobilerun facade | MCP tools + JSON CLI + compact skill |
| Reasoning | Existing agent | Existing agent |
| Local Android | ADB with optional Portal; Portal HTTP-only | Built-in platform-tools ADB commands |
| iOS | iOS Portal HTTP | Not supported |
| Hosted devices | Mobilerun cloud with API key | No vendor cloud integration |
| Runtime | mobilerun-core, local driver, cloud SDK and dependencies | MCP SDK, Pydantic, defusedxml, system ADB |
| Agent ergonomics | find_nodes, tap_text, bounded scroll_until, app cards | Find elements, snapshot-checked taps, directional scroll |
| Rich input | Capability-dependent; richer Portal path | Printable ASCII only; explicit failure otherwise |
| App knowledge | Platform guides and scoped per-app cards | Minimal general workflow; no copied app cards |
| Update model | Guidance requests session-start updates | Locked dependencies; explicit updates |

This is a scope comparison, not a performance or reliability ranking. The installed
package counts alone do not establish simplicity: MCP itself brings dependencies.
phone-use is narrower and younger, and has substantially less device coverage.

## What to adopt

- Treat a skill as operating guidance, with the coding agent supplying the intelligence.
- Inspect capabilities rather than assuming every backend supports every action.
- Search accessibility labels before guessing coordinates; account for hidden targets.
- Give scrolling content-relative semantics and verify movement.
- Observe after acting and distinguish dispatched input from completed app behavior.
- Keep future app-specific hints scoped to the current app and maintain them only when useful.

phone-use now implements capability/status reporting, fresh label search, hidden-node
rejection, directional scroll, JSON argument discovery and a concise agent workflow.
It keeps deterministic explicit MCP tools as the primary integration surface.

## Build versus reuse

If broad Android/iOS/cloud coverage is the primary need, reusing mobile-harness is a
credible choice and avoids rebuilding its driver ecosystem. If a small, inspectable,
ADB-only MCP/CLI with no Mobilerun runtime dependency is the intended open-source project,
phone-use has a clear narrower purpose. An optional backend adapter can be considered
later; it should not silently add cloud credentials or auto-install a Portal app.

No reference source was copied. Both implementations remain in separate repositories.

## AWS runtime evidence

The local Python API was exercised with an empty environment apart from PATH against
an Android 9 software emulator, without Portal or cloud credentials. With
`backend="local-android-adb"`, `device.ui()` returned 10 nodes and `device.screenshot()`
returned a valid PNG. This verifies the local keyless read path on that test device;
it does not establish iOS, cloud, or physical-phone compatibility.

Early runs encountered a boot crash (Android 11 image), a System UI ANR (Android 9),
and unavailable accessibility roots. Comparing against mobile-harness helped find a
phone-use compatibility problem: its compressed UI dump returned a null root on the
fixture, while the standard dump succeeded. phone-use now uses standard dumps and
filters the resulting XML itself. Standard dumps could also fail transiently; the
read path now retries a missing root once without retrying input actions. Regression
tests cover unsupported compressed trees and bounded recovery from missing roots. Single-run timings on software emulation are not a benchmark.
