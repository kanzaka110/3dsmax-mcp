"""Safety gate for dangerous MCP tools.

Classifies tools by risk level and injects warning metadata into responses
for destructive operations, giving the AI agent context to confirm with users.

Risk levels:
    SAFE      — read-only, no scene mutation
    CAUTION   — scene mutation, reversible (create, move, hide)
    DANGEROUS — irreversible or high-impact (delete, reset, raw MAXScript)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    SAFE = "safe"
    CAUTION = "caution"
    DANGEROUS = "dangerous"


@dataclass(frozen=True)
class ToolRisk:
    """Risk classification for a single tool or tool+args combo."""

    level: RiskLevel
    reason: str
    suggestion: str = ""


# ── Static tool risk registry ────────────────────────────────────

_TOOL_RISKS: dict[str, ToolRisk] = {
    "delete_objects": ToolRisk(
        level=RiskLevel.DANGEROUS,
        reason="Permanently removes objects from the scene",
        suggestion="Use manage_scene(action='hold') first to create a restore point",
    ),
    "execute_maxscript": ToolRisk(
        level=RiskLevel.DANGEROUS,
        reason="Executes arbitrary MAXScript code — can modify or destroy scene data",
        suggestion="Prefer dedicated tools over raw MAXScript when available",
    ),
}

# Conditional risks: tool name -> (condition_fn, risk_if_true, risk_if_false)
# condition_fn receives the tool's kwargs
_CONDITIONAL_RISKS: dict[str, tuple[
    type[object],  # placeholder for callable type
    ToolRisk,
    ToolRisk,
]] = {}


def _manage_scene_risk(**kwargs: object) -> ToolRisk:
    """manage_scene is dangerous only for 'reset'; 'hold'/'info' are safe."""
    action = str(kwargs.get("action", "")).lower().strip()
    if action == "reset":
        return ToolRisk(
            level=RiskLevel.DANGEROUS,
            reason="Resets the entire scene — all unsaved work will be lost",
            suggestion="Use manage_scene(action='hold') first, or confirm with user",
        )
    if action in ("save",):
        return ToolRisk(
            level=RiskLevel.CAUTION,
            reason="Overwrites the saved file on disk",
        )
    return ToolRisk(level=RiskLevel.SAFE, reason="Read-only or reversible operation")


# ── Public API ───────────────────────────────────────────────────

def classify_risk(tool_name: str, **kwargs: object) -> ToolRisk:
    """Classify the risk level of a tool invocation.

    Args:
        tool_name: MCP tool function name (e.g. "delete_objects").
        **kwargs: Tool arguments for conditional risk evaluation.

    Returns:
        ToolRisk with level, reason, and optional suggestion.
    """
    # Check conditional risks first (tool behavior depends on args)
    if tool_name == "manage_scene":
        return _manage_scene_risk(**kwargs)

    # Static registry lookup
    if tool_name in _TOOL_RISKS:
        return _TOOL_RISKS[tool_name]

    return ToolRisk(level=RiskLevel.SAFE, reason="")


def format_safety_warning(risk: ToolRisk) -> str:
    """Format a risk assessment as a human-readable warning prefix."""
    if risk.level == RiskLevel.SAFE:
        return ""

    parts = [f"[{risk.level.value.upper()}] {risk.reason}"]
    if risk.suggestion:
        parts.append(f"Suggestion: {risk.suggestion}")
    return " | ".join(parts)


def wrap_with_safety(
    tool_name: str,
    result: str,
    **kwargs: object,
) -> str:
    """Wrap a tool result with safety metadata if the tool is risky.

    For DANGEROUS tools, prepends a warning to the result string.
    For SAFE/CAUTION tools, returns the result unchanged.

    This is designed to work within MCP's string return constraint —
    no protocol changes needed.
    """
    risk = classify_risk(tool_name, **kwargs)

    if risk.level == RiskLevel.SAFE:
        return result

    warning = format_safety_warning(risk)

    if risk.level == RiskLevel.DANGEROUS:
        logger.info("safety gate: %s -> %s", tool_name, risk.level.value)
        return f"WARNING: {warning}\n---\n{result}"

    # CAUTION: just log, don't modify output
    logger.debug("safety note: %s -> %s", tool_name, risk.level.value)
    return result
