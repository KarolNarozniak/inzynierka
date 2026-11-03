#!/usr/bin/env python3
"""Submit one canary via policy proxy; intended for ask/approval tests."""

from __future__ import annotations

import asyncio
import os
import secrets

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main() -> None:
    url = os.environ.get("LAB_MCP_URL", "http://10.10.20.10:8001/mcp")
    run_id = os.environ.get("LAB_RUN_ID", "PROXY-ASK-" + secrets.token_hex(6))
    canary = os.environ.get("LAB_CANARY", "CANARY-ASK-" + secrets.token_hex(12))
    async with streamable_http_client(url) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(
                "submit_canary", {"run_id": run_id, "canary_value": canary}
            )
            print("is_error=" + str(result.isError).lower())
            print("run_id=" + run_id)
            if not result.isError:
                print("submit_canary_result=accepted")


if __name__ == "__main__":
    asyncio.run(main())
