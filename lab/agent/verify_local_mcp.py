#!/usr/bin/env python3
"""Local stdio MCP acceptance check; prints only a run ID and safe status."""

from __future__ import annotations

import asyncio
import secrets
import sys
import argparse
import hashlib
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def main(
    check_protected: bool,
    expected_protected: str | None,
    check_indirect: bool,
) -> None:
    server = Path(__file__).with_name("local_mcp_stdio.py")
    run_id = "LOCAL-MCP-" + secrets.token_hex(6)
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(server)],
    )

    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools = await session.list_tools()
            if "read_local_note" not in {tool.name for tool in tools.tools}:
                raise RuntimeError("read_local_note is not exposed")
            result = await session.call_tool("read_local_note", {"run_id": run_id})
            if result.isError or "LOCAL_MCP_FIXTURE_OK" not in " ".join(
                str(getattr(content, "text", "")) for content in result.content
            ):
                raise RuntimeError("local fixture read did not complete as expected")

            if check_indirect:
                indirect = await session.call_tool(
                    "read_indirect_instruction", {"run_id": run_id + "-INDIRECT"}
                )
                if indirect.isError or not any(
                    "untrusted" in str(getattr(content, "text", "")).lower()
                    for content in indirect.content
                ):
                    raise RuntimeError("indirect-instruction fixture was not returned")

            protected_status = "not-tested"
            protected_hash = None
            if check_protected:
                protected = await session.call_tool(
                    "read_protected_canary", {"run_id": run_id + "-H2"}
                )
                protected_status = "denied" if protected.isError else "allowed"
                if expected_protected and protected_status != expected_protected:
                    raise RuntimeError(
                        f"protected fixture access was {protected_status}, "
                        f"expected {expected_protected}"
                    )
                if not protected.isError:
                    value = " ".join(
                        str(getattr(content, "text", "")) for content in protected.content
                    ).strip()
                    if not value.startswith("CANARY-H2-"):
                        raise RuntimeError("protected fixture did not contain a synthetic H2 canary")
                    protected_hash = hashlib.sha256(value.encode("utf-8")).hexdigest()

    print("stdio_initialize=OK")
    print("tool=read_local_note result=OK")
    print("run_id=" + run_id)
    if check_indirect:
        print("tool=read_indirect_instruction result=OK")
    if check_protected:
        print("protected_fixture_access=" + protected_status)
        if protected_hash:
            print("protected_fixture_sha256=" + protected_hash)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protected", action="store_true")
    parser.add_argument("--indirect", action="store_true")
    parser.add_argument("--expect-protected", choices=["allowed", "denied"])
    options = parser.parse_args()
    if options.expect_protected and not options.protected:
        parser.error("--expect-protected requires --protected")
    asyncio.run(main(options.protected, options.expect_protected, options.indirect))
