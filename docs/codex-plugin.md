# phone-use for Codex

The phone-use plugin packages the Android-control skill, a CLI launcher, the Python
source, and its dependency lockfile. It needs no phone-use account or API keys.
The plugin declares the hosted MCP endpoint at https://phone-use.xagi.in/mcp.
The existing local stdio server remains available through the main README.

## Download

Get `phone-use-plugin-0.1.0.zip` and its SHA-256 checksum from the
[plugin release](https://github.com/sauravtom/phone-use/releases/tag/plugin-v0.1.0).
The ZIP contains `.codex-plugin/plugin.json` at its root and a complete skill under
`skills/phone-use/`. Import it using a client that supports local plugin ZIPs, or
extract it into a `phone-use` folder and pass its `skills/phone-use/SKILL.md` to a
coding agent. The file can also be copied with its entire skill folder into the
agent's supported skills directory.

Installing a plugin does not connect a phone. The execution host needs Python 3.11+,
[uv](https://docs.astral.sh/uv/), and Android platform-tools. ADB must see an authorized
Android phone or emulator. The first launcher invocation downloads the locked Python
dependencies. Later invocations reuse the environment in `~/.cache/phone-use/`;
`PHONE_USE_PLUGIN_CACHE` can select a different writable location. Installing dependencies
requires network access, but phone-use makes no model API calls. The source and lockfile
are bundled in the skill; it does not fetch an unpinned Git branch or depend on a PyPI
release of phone-use.

For a manually extracted ZIP, use its absolute path:

```sh
python3 /absolute/path/to/phone-use/skills/phone-use/scripts/phone_use.py tools
python3 /absolute/path/to/phone-use/skills/phone-use/scripts/phone_use.py call devices
python3 /absolute/path/to/phone-use/skills/phone-use/scripts/phone_use.py call observe
```

Use the same launcher with `serve` to start the existing MCP stdio server. The full plugin ZIP declares the remote MCP connection; a separate skills ZIP is
available for uploading the same skill alongside that server in the portal. Screen
inspection, actions, and verification all use the same phone-use implementation.

For remote coding sessions, the phone must be reachable from the execution host.
For a web-only chat, run `phone-use connect --serial SERIAL` on the computer attached
to the phone and pair through the hosted OAuth flow. See [remote device setup](remote-devices.md). Missing prerequisites should produce a setup
explanation, never a claim of successful device control.

## Build and validate

Run on the development host:

```sh
uv sync --locked --group dev
uv run --locked ruff check .
uv run --locked pytest -q
python3 scripts/build-plugin.py
uv run --locked python scripts/plugin-smoke.py
```

The packager uses an explicit source allowlist, produces a deterministic ZIP and checksum,
and keeps virtual environments, device screenshots, APKs, signing keys, and other test
artifacts out of the release. Source files under `src/phone_use/` are the single source
of truth; the build copies them into the skill's `runtime/` directory. Do not edit or
commit generated runtime copies.

The plugin smoke test extracts the release ZIP into a path with spaces, bootstraps a
fresh dependency environment without API keys, and exercises CLI and MCP against a
fake ADB process. It verifies stdin text transport, shell quoting, screenshot output,
stale snapshot rejection, and unsupported Unicode rejection. This packaging test does
not establish physical-device compatibility. The separate Android emulator evidence
and limitations are in [DONE.md](../DONE.md).

## Public directory submission

This GitHub release is a downloadable plugin, not proof of public directory listing.
The official [submission process](https://developers.openai.com/plugins/deploy/submission)
requires a verified publisher, review, approval, and a subsequent publish action.
Use **With MCP** with `https://phone-use.xagi.in/mcp` and OAuth. The server runs on
Cloudflare Workers; each user runs `phone-use connect --serial SERIAL` on their own
ADB host, then enters its one-time code in the OAuth consent page. This uses an
outbound WebSocket and never exposes the ADB port. The bridge limits commands to
one explicit device. Pairing codes expire in 10 minutes and work once; sessions
last at most eight hours. Stop the bridge to revoke the device connection.

Build `phone-use-skills-0.1.0.zip` with `python3 scripts/build-plugin.py --skills-only`
for the portal's Skills tab. The upload has `SKILL.md` at the ZIP root, with `scripts/`, `agents/`, and
`runtime/` beside it. It omits the plugin manifest, icons, and `.mcp.json`; the portal
registers the HTTPS endpoint and listing assets separately. The full downloadable
plugin retains its manifest, icons, and `.mcp.json`.

Review materials are in [plugin-review.json](plugin-review.json), with the generated
portal import at [chatgpt-app-submission.json](chatgpt-app-submission.json). The publisher
identity and actual country availability must be confirmed in the portal.

The MCP submission draft was created on 2026-09-28. A draft, deployed endpoint, or
GitHub release does not establish submission, approval, or public directory listing.
See the repository's validation record for verified results and submission status.
