# Working on phone-use

phone-use is a small Android MCP/JSON CLI and agent skill. The host coding agent owns
planning; the package must not require a model API key or call an LLM.

- `src/phone_use/adb.py`: transport, subprocess deadlines, device selection, shell quoting.
- `src/phone_use/core.py`: typed, transport-independent tool operations.
- `src/phone_use/server.py`: official MCP stdio server and tool metadata.
- `src/phone_use/cli.py`: JSON CLI using the same operations.
- `skills/phone-use/SKILL.md`: instructions for an agent using the tools.
- `docs/mobile-harness-evaluation.md`: closest reference and intended scope.

Validate changes with `uv run ruff check .` and `uv run pytest -q`.
Use `docs/testing.md` for optional device checks; never substitute mock success for a
verified device workflow. Do not touch a personal device without task authorization.
Keep Android SDKs, build outputs, screenshots, and signing keys outside tracked source.
