"""Compact session context tool for natural AI + 3ds Max interaction."""

from __future__ import annotations

import json

from ..server import mcp


@mcp.tool()
def get_session_context(
    max_roots: int = 20,
    max_selection: int = 20,
) -> str:
    """Get compact live context for the current 3ds Max session.

    This is the fastest "where am I?" tool for an AI client. It combines:
    - bridge status
    - host/plugin capabilities
    - compact scene snapshot
    - compact current selection snapshot

    Args:
        max_roots: Max top-level root names to include from the scene snapshot.
        max_selection: Max selected objects to include from the selection snapshot.
    """
    from .bridge import get_bridge_status
    from .capabilities import get_plugin_capabilities
    from .snapshots import get_scene_snapshot, get_selection_snapshot

    return json.dumps({
        "bridge": json.loads(get_bridge_status()),
        "capabilities": json.loads(get_plugin_capabilities()),
        "scene": json.loads(get_scene_snapshot(max_roots=max_roots)),
        "selection": json.loads(get_selection_snapshot(max_items=max_selection)),
    })
