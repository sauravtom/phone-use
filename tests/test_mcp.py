import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_real_stdio_protocol(fake):
    # Spawn the installed entrypoint, exercising FastMCP and an actual subprocess ADB boundary.
    params = StdioServerParameters(
        command=str(Path(sys.executable).with_name("phone-use")),
        args=["serve"],
        env=dict(os.environ),
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as client:
            info = await client.initialize()
            assert info.serverInfo.name == "phone-use"
            tools = (await client.list_tools()).tools
            assert len(tools) == 13
            names = {t.name: t for t in tools}
            assert names["phone_observe"].annotations.readOnlyHint
            assert not names["phone_tap"].annotations.readOnlyHint
            result = await client.call_tool("phone_observe", {})
            assert not result.isError
            data = result.structuredContent
            assert data["elements"][0]["text"] == "Settings"
            result = await client.call_tool(
                "phone_tap_element",
                {"element_id": "0", "snapshot": data["snapshot"], "serial": "test-phone"},
            )
            assert not result.isError
            result = await client.call_tool("phone_screenshot", {})
            assert not result.isError
            assert result.content[0].type == "image"
            assert result.content[0].mimeType == "image/png"
            result = await client.call_tool("phone_tap", {"x": -1, "y": 20})
            assert result.isError
            result = await client.call_tool("phone_type_text", {"text": "हिन्दी"})
            assert result.isError
            result = await client.call_tool(
                "phone_tap_element", {"element_id": "0", "snapshot": "old"}
            )
            assert result.isError
