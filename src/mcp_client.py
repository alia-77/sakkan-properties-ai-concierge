import json
import os
import sys
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


ROOT = Path(__file__).resolve().parents[1]
MCP_SERVER_PATH = ROOT / "mcp" / "mcp_tool_server.py"


async def call_mcp_tool(
    tool_name: str,
    arguments: dict[str, Any],
) -> dict:
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(MCP_SERVER_PATH)],
        env=os.environ.copy(),
    )

    async with stdio_client(
        server_params
    ) as (read, write):
        async with ClientSession(
            read,
            write,
        ) as session:
            await session.initialize()

            result = await session.call_tool(
                tool_name,
                arguments=arguments,
            )

            if getattr(result, "isError", False):
                details = [
                    getattr(item, "text", str(item))
                    for item in result.content
                ]
                raise RuntimeError(
                    f"MCP tool '{tool_name}' failed: "
                    + " ".join(details)
                )

            structured = getattr(
                result,
                "structured_content",
                None,
            )

            if isinstance(
                structured,
                dict,
            ):
                return structured

            for item in result.content:
                text = getattr(
                    item,
                    "text",
                    None,
                )

                if not text:
                    continue

                try:
                    parsed = json.loads(text)
                except json.JSONDecodeError:
                    continue

                if isinstance(parsed, dict):
                    return parsed

            raise RuntimeError(
                f"MCP tool '{tool_name}' returned no structured result"
            )
