#!/usr/bin/env python3
"""End-to-end MCP and synthetic canary smoke test (no external LLM call)."""

from __future__ import annotations

import asyncio
import os
import secrets

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def main() -> None:
    url = os.environ.get("LAB_MCP_URL", "http://10.10.30.10:8000/mcp")
    run_id = "BOOTSTRAP-" + secrets.token_hex(8)
    canary_value = "CANARY-SC06-" + secrets.token_hex(12)

    async with streamablehttp_client(url) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = {tool.name for tool in tools.tools}
            expected = {"read_untrusted_note", "submit_canary"}
            missing = expected - names
            if missing:
                raise RuntimeError(f"MCP tools missing: {sorted(missing)}")

            note = await session.call_tool("read_untrusted_note", {})
            if note.isError:
                raise RuntimeError("read_untrusted_note failed")

            result = await session.call_tool(
                "submit_canary",
                {"run_id": run_id, "canary_value": canary_value},
            )
            if result.isError:
                raise RuntimeError("submit_canary failed")

            print("MCP initialize: OK")
            print("MCP tools: " + ", ".join(sorted(names)))
            print("Synthetic note read: OK")
            print(f"Canary receiver accepted run_id={run_id}")


if __name__ == "__main__":
    asyncio.run(main())
