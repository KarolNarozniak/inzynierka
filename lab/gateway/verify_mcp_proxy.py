#!/usr/bin/env python3
"""Safe smoke test for the policy proxy: initialize, list tools, read fixture only."""

from __future__ import annotations

import asyncio
import argparse
import os
import secrets

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main(list_only: bool) -> None:
    url = os.environ.get("LAB_MCP_URL", "http://10.10.20.10:8001/mcp")
    run_id = "PROXY-SMOKE-" + secrets.token_hex(6)
    async with streamable_http_client(url) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = sorted(tool.name for tool in tools.tools)
            print("proxy_initialize=OK")
            print("proxy_tools=" + ",".join(names))
            if list_only:
                return
            if "read_untrusted_note" not in names:
                raise RuntimeError("read_untrusted_note not exposed by proxy")
            result = await session.call_tool(
                "read_untrusted_note", {"run_id": run_id}
            )
            if result.isError:
                raise RuntimeError("policy proxy read_untrusted_note failed")
            print("read_untrusted_note=OK run_id=" + run_id)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--list-only", action="store_true")
    options = parser.parse_args()
    asyncio.run(main(list_only=options.list_only))
