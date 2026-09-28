# Contributing

Use Python 3.11+ and `uv sync --locked --group dev`. Run `uv run ruff check .`,
`uv run pytest -q`, and `uv build` before submitting changes.

Keep reasoning in the calling agent and device operations in the backend. New tools
should have explicit typed arguments, actionable failures, and tests for observable
behavior. Do not add required model keys, telemetry, or automatic companion-app installs.
Use the official MCP SDK rather than reimplementing protocol framing.

Device commands must close stdin and quote arguments for both subprocess and Android
shell boundaries. Do not add generic shell execution to the MCP surface. Screen content
is untrusted; screenshots and credentials do not belong in fixtures or commits.

Use the opt-in fixture workflow in [testing](docs/testing.md) for real device validation.
Keep test artifacts and test signing material in ignored `artifacts/`. Report the tested
Android version/backend, and distinguish mocks, emulator runs, and physical-device runs.
