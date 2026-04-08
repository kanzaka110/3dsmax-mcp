"""Deep SDK learning tools — reference graphs, class relationships, scene patterns, live events."""

import json
from ..server import mcp, client


# ── Private helpers ─────────────────────────────────────────────────


def _walk_references(name: str, max_depth: int = 3) -> str:
    """Walk the reference dependency graph of a scene object."""
    payload = json.dumps({"name": name, "max_depth": max_depth})
    response = client.send_command(payload, cmd_type="native:walk_references")
    return response.get("result", "{}")


def _map_class_relationships(
    pattern: str = "",
    superclass: str = "",
    limit: int = 100,
) -> str:
    """Map which classes accept which reference types via ParamBlock2 params."""
    payload = {}
    if pattern:
        payload["pattern"] = pattern
    if superclass:
        payload["superclass"] = superclass
    if limit != 100:
        payload["limit"] = limit
    response = client.send_command(
        json.dumps(payload) if payload else "",
        cmd_type="native:map_class_relationships",
    )
    return response.get("result", "{}")


def _learn_scene_patterns() -> str:
    """Analyze current scene for class usage patterns, modifier stacks, and material associations."""
    response = client.send_command("", cmd_type="native:learn_scene_patterns")
    return response.get("result", "{}")


def _watch_scene(
    watch_action: str = "status",
    since: int = 0,
    limit: int = 100,
) -> str:
    """Live scene event watcher."""
    payload = {"action": watch_action}
    if watch_action == "get":
        payload["since"] = since
        payload["limit"] = limit
    response = client.send_command(json.dumps(payload), cmd_type="native:watch_scene")
    return response.get("result", "{}")


# ── Unified tool ────────────────────────────────────────────────────


@mcp.tool()
def manage_learning(
    action: str,
    name: str = "",
    max_depth: int = 3,
    pattern: str = "",
    superclass: str = "",
    limit: int = 100,
    watch_action: str = "status",
    since: int = 0,
) -> str:
    """SDK learning and introspection. Actions: walk_references, map_relationships, learn_patterns, watch.

    Args:
        action: "walk_references" | "map_relationships" | "learn_patterns" | "watch".
        name: Object name (for walk_references).
        max_depth: Max recursion depth (for walk_references, default 3, max 8).
        pattern: Wildcard class filter (for map_relationships).
        superclass: Superclass filter (for map_relationships).
        limit: Max results (for map_relationships/watch, default 100).
        watch_action: status|start|stop|get|clear (for watch).
        since: Timestamp filter for watch get events.
    """
    if action == "walk_references":
        return _walk_references(name, max_depth)
    if action == "map_relationships":
        return _map_class_relationships(pattern, superclass, limit)
    if action == "learn_patterns":
        return _learn_scene_patterns()
    if action == "watch":
        return _watch_scene(watch_action, since, limit)
    return f"Unknown action: {action}. Use: walk_references, map_relationships, learn_patterns, watch"
