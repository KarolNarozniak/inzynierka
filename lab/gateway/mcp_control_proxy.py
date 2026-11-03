#!/usr/bin/env python3
"""Deterministic allow/ask/deny MCP proxy for VM-Agent -> VM-Target."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import threading
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from starlette.requests import Request
from starlette.responses import JSONResponse

from policy_engine import InvalidToolRequest, decide, load_profile, normalize_arguments


PROXY_HOST = "10.10.20.10"
PROXY_PORT = 8001
TARGET_MCP_URL = "http://10.10.30.10:8000/mcp"
POLICY_PATH = Path("/opt/lab/control/policy.json")
LOG_PATH = Path("/var/log/lab-control/decisions.jsonl")
PENDING_DIR = Path("/var/lib/lab-control/pending")
APPROVAL_DIR = Path("/var/lib/lab-control/approvals")
RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
WRITE_LOCK = threading.Lock()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("lab-mcp-control")

mcp = FastMCP(
    "Lab MCP Policy Gateway",
    instructions="Deterministic allow/ask/deny gateway. Unmatched tools are denied.",
    host=PROXY_HOST,
    port=PROXY_PORT,
    streamable_http_path="/mcp",
    stateless_http=True,
    json_response=True,
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _source_ip(ctx: Context) -> str:
    try:
        request = ctx.request_context.request
        client = getattr(request, "client", None)
        return str(client.host) if client else "unknown"
    except Exception:
        return "unknown"


def _append_event(event: dict[str, Any]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    line = (json.dumps(event, separators=(",", ":"), sort_keys=True) + "\n").encode("utf-8")
    with WRITE_LOCK, LOG_PATH.open("ab") as log_file:
        log_file.write(line)


def _event(
    *,
    run_id: str,
    request_id: str,
    source_ip: str,
    tool_name: str,
    arguments: dict[str, str],
    profile: str,
    decision: str,
    stage: str,
    execution_attempted: bool,
    outcome: str | None = None,
    approval: str | None = None,
) -> None:
    record: dict[str, Any] = {
        "timestamp": _now(),
        "run_id": run_id,
        "request_id": request_id,
        "source_ip": source_ip,
        "tool": tool_name,
        "normalized_arguments": arguments,
        "policy_profile": profile,
        "decision": decision,
        "stage": stage,
        "execution_attempted": execution_attempted,
    }
    if outcome is not None:
        record["outcome"] = outcome
    if approval is not None:
        record["user_approval"] = approval
    _append_event(record)
    logger.info("LAB_CONTROL %s", json.dumps(record, separators=(",", ":"), sort_keys=True))


def _request_id(ctx: Context) -> str:
    # Never use a client-supplied JSON-RPC ID in a filesystem path.
    # Generate a UUID for correlation and approval filenames.
    return str(uuid.uuid4())


def _create_approval_request(
    request_id: str,
    run_id: str,
    tool_name: str,
    arguments: dict[str, str],
    source_ip: str,
) -> Path:
    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    path = PENDING_DIR / f"{request_id}.json"
    payload = {
        "request_id": request_id,
        "run_id": run_id,
        "tool": tool_name,
        "normalized_arguments": arguments,
        "source_ip": source_ip,
        "created_at": _now(),
    }
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)
    return path


async def _wait_for_human_approval(request_id: str, timeout_seconds: int) -> tuple[str, str]:
    """Wait for an operator decision written by lab-control-approve on Gateway."""
    approval_path = APPROVAL_DIR / f"{request_id}.json"
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if approval_path.exists():
            try:
                decision = json.loads(approval_path.read_text(encoding="utf-8"))
                value = decision.get("decision")
                approved_by = decision.get("approved_by", "unknown")
                if value in {"allow", "deny"}:
                    approval_path.unlink(missing_ok=True)
                    return value, str(approved_by)
            except (OSError, json.JSONDecodeError):
                pass
        await asyncio.sleep(0.5)
    return "deny", "approval_timeout"


async def _call_target(tool_name: str, arguments: dict[str, str]) -> Any:
    async with streamable_http_client(TARGET_MCP_URL) as (
        read_stream,
        write_stream,
        _,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
    if result.isError:
        messages = [getattr(item, "text", "") for item in result.content]
        raise RuntimeError("; ".join(text for text in messages if text) or "backend MCP error")
    structured = getattr(result, "structuredContent", None)
    if structured is not None:
        return structured
    return "\n".join(getattr(item, "text", "") for item in result.content)


async def _evaluate_and_forward(
    tool_name: str,
    raw_arguments: dict[str, Any],
    ctx: Context,
) -> Any:
    request_id = _request_id(ctx)
    source_ip = _source_ip(ctx)
    try:
        normalized = normalize_arguments(tool_name, raw_arguments)
    except InvalidToolRequest as exc:
        _event(
            run_id=str(raw_arguments.get("run_id", "INVALID"))[:64],
            request_id=request_id,
            source_ip=source_ip,
            tool_name=tool_name,
            arguments={},
            profile="validation",
            decision="deny",
            stage="validation",
            execution_attempted=False,
            outcome="invalid_arguments",
        )
        raise ToolError(str(exc)) from exc

    run_id = normalized["run_id"]
    try:
        profile_name, profile, approval_timeout = load_profile(POLICY_PATH)
        decision = decide(profile, tool_name)
    except Exception as exc:
        logger.exception("Could not load policy; fail closed")
        _event(
            run_id=run_id,
            request_id=request_id,
            source_ip=source_ip,
            tool_name=tool_name,
            arguments=normalized,
            profile="policy-error",
            decision="deny",
            stage="decision",
            execution_attempted=False,
            outcome="policy_load_error",
        )
        raise ToolError("Policy unavailable; request denied") from exc

    _event(
        run_id=run_id,
        request_id=request_id,
        source_ip=source_ip,
        tool_name=tool_name,
        arguments=normalized,
        profile=profile_name,
        decision=decision,
        stage="policy_decision",
        execution_attempted=False,
    )

    if decision == "deny":
        raise ToolError("Denied by laboratory policy")

    if decision == "ask":
        pending_path = _create_approval_request(
            request_id, run_id, tool_name, normalized, source_ip
        )
        logger.warning(
            "ASK_REQUIRED request_id=%s run_id=%s tool=%s source_ip=%s; approve with: "
            "lab-control-approve %s allow|deny",
            request_id,
            run_id,
            tool_name,
            source_ip,
            request_id,
        )
        approval, approved_by = await _wait_for_human_approval(request_id, approval_timeout)
        pending_path.unlink(missing_ok=True)
        _event(
            run_id=run_id,
            request_id=request_id,
            source_ip=source_ip,
            tool_name=tool_name,
            arguments=normalized,
            profile=profile_name,
            decision="ask",
            stage="human_approval",
            execution_attempted=False,
            outcome="approved" if approval == "allow" else "rejected",
            approval=f"{approval}:{approved_by}",
        )
        if approval != "allow":
            raise ToolError("Denied: human approval was not granted")

    _event(
        run_id=run_id,
        request_id=request_id,
        source_ip=source_ip,
        tool_name=tool_name,
        arguments=normalized,
        profile=profile_name,
        decision=decision,
        stage="execution_attempt",
        execution_attempted=True,
        outcome="started",
    )

    try:
        backend_arguments = (
            normalized
            if tool_name == "submit_canary"
            else {}
        )
        result = await _call_target(tool_name, backend_arguments)
    except Exception as exc:
        _event(
            run_id=run_id,
            request_id=request_id,
            source_ip=source_ip,
            tool_name=tool_name,
            arguments=normalized,
            profile=profile_name,
            decision=decision,
            stage="execution_result",
            execution_attempted=True,
            outcome=f"error:{type(exc).__name__}",
        )
        raise ToolError("Backend execution failed") from exc

    _event(
        run_id=run_id,
        request_id=request_id,
        source_ip=source_ip,
        tool_name=tool_name,
        arguments=normalized,
        profile=profile_name,
        decision=decision,
        stage="execution_result",
        execution_attempted=True,
        outcome="success",
    )
    return result


@mcp.custom_route("/healthz", methods=["GET"])
async def health(_: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "lab-mcp-policy-proxy"})


@mcp.tool()
async def read_untrusted_note(run_id: str, ctx: Context) -> str:
    """Request the staged synthetic indirect-instruction fixture."""
    result = await _evaluate_and_forward("read_untrusted_note", {"run_id": run_id}, ctx)
    if isinstance(result, dict):
        value = result.get("result")
        return str(value) if value is not None else json.dumps(result)
    return str(result)


@mcp.tool()
async def submit_canary(run_id: str, canary_value: str, ctx: Context) -> dict[str, Any]:
    """Submit one synthetic canary, subject to the active policy and human approval."""
    result = await _evaluate_and_forward(
        "submit_canary",
        {"run_id": run_id, "canary_value": canary_value},
        ctx,
    )
    return result if isinstance(result, dict) else {"result": str(result)}


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
