"""Small deterministic policy engine for the lab MCP proxy."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
CANARY_RE = re.compile(r"^CANARY-[A-Za-z0-9_-]{8,120}$")
VALID_DECISIONS = {"allow", "ask", "deny"}


class InvalidToolRequest(ValueError):
    pass


def normalize_arguments(tool_name: str, arguments: dict[str, Any]) -> dict[str, str]:
    """Validate and canonicalize exactly the arguments used by the lab tools."""
    if not isinstance(arguments, dict):
        raise InvalidToolRequest("tool arguments must be an object")

    if tool_name == "read_untrusted_note":
        if set(arguments) != {"run_id"}:
            raise InvalidToolRequest("read_untrusted_note requires only run_id")
        run_id = arguments["run_id"]
        if not isinstance(run_id, str):
            raise InvalidToolRequest("run_id must be a string")
        run_id = run_id.strip()
        if not RUN_ID_RE.fullmatch(run_id):
            raise InvalidToolRequest("run_id format is invalid")
        return {"run_id": run_id}

    if tool_name == "submit_canary":
        if set(arguments) != {"run_id", "canary_value"}:
            raise InvalidToolRequest("submit_canary requires run_id and canary_value only")
        run_id = arguments["run_id"]
        canary_value = arguments["canary_value"]
        if not isinstance(run_id, str) or not isinstance(canary_value, str):
            raise InvalidToolRequest("run_id and canary_value must be strings")
        run_id = run_id.strip()
        canary_value = canary_value.strip()
        if not RUN_ID_RE.fullmatch(run_id):
            raise InvalidToolRequest("run_id format is invalid")
        if not CANARY_RE.fullmatch(canary_value):
            raise InvalidToolRequest("canary_value must be synthetic and start with CANARY-")
        return {"run_id": run_id, "canary_value": canary_value}

    raise InvalidToolRequest(f"unknown tool: {tool_name}")


def load_profile(policy_path: str | Path) -> tuple[str, dict[str, Any], int]:
    """Load and validate the currently active immutable policy snapshot."""
    data = json.loads(Path(policy_path).read_text(encoding="utf-8"))
    profile_name = data.get("active_profile")
    profiles = data.get("profiles")
    if not isinstance(profile_name, str) or not isinstance(profiles, dict):
        raise ValueError("policy file lacks active_profile/profiles")
    profile = profiles.get(profile_name)
    if not isinstance(profile, dict):
        raise ValueError(f"active profile is not defined: {profile_name}")
    default = profile.get("default")
    tools = profile.get("tools")
    if default not in VALID_DECISIONS or not isinstance(tools, dict):
        raise ValueError(f"invalid policy profile: {profile_name}")
    if any(decision not in VALID_DECISIONS for decision in tools.values()):
        raise ValueError(f"invalid tool decision in profile: {profile_name}")
    timeout = int(data.get("approval_timeout_seconds", 180))
    return profile_name, profile, max(1, min(timeout, 600))


def decide(profile: dict[str, Any], tool_name: str) -> str:
    """Resolve one exact tool rule; unmatched calls use the profile default."""
    decision = profile["tools"].get(tool_name, profile["default"])
    if decision not in VALID_DECISIONS:
        return "deny"
    return decision
