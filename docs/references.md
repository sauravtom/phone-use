# Reference study

All three repositories were cloned separately from phone-use on the development VPS.
mobile-harness runtime dependencies were installed in its own AWS virtual environment
for evaluation. The larger agent projects were inspected without installing their runtimes.

| Reference | Inspected revision | License | Useful idea |
| --- | --- | --- | --- |
| https://github.com/droidrun/mobile-harness | e0e73108aa4aae43dd682b5f713877976b822e1b | MIT | Skill-first device control, capability inspection, label search, content-relative scroll |
| https://github.com/minitap-ai/mobile-use | 62913c933e21b27da353a89316a09f60525af496 | Apache-2.0 | Element/coordinate controls and explicit action results |
| https://github.com/droidrun/mobilerun | 4f168cbbfa3134a7acca6ab7f96d8d059c249df5 | MIT | Device CLI and indexed screen observation |

mobile-use's project metadata includes LangGraph and several model integrations.
mobilerun's metadata includes LlamaIndex, model integrations, and its device backend.
phone-use deliberately leaves planning to the calling agent. Its runtime uses the
[official MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk),
Pydantic (via MCP), defusedxml, and the system ADB executable.

The implementation uses Android platform commands, not copied source or bundled code
from the reference repositories. Original code is MIT licensed.

See [mobile-harness evaluation](mobile-harness-evaluation.md) for the closest comparison.
