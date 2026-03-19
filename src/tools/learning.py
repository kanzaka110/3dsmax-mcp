"""Deep SDK learning tools — reference graphs, class relationships, scene patterns, live events."""

import json
from ..server import mcp, client


@mcp.tool()
def walk_references(
    name: str,
    max_depth: int = 4,
) -> str:
    """Walk the full reference dependency graph of a scene object.

    Shows exactly how materials, modifiers, controllers, textures, and nodes
    connect to each other through Max's reference system. Use this to understand
    why changing one object affects another, or to map a complex shader network.

    Args:
        name: Object name to walk from.
        max_depth: Max recursion depth (default 4, max 8). Deeper = more detail
                   but larger output.

    Returns:
        JSON tree showing the full reference graph with class names and superclasses.
    """
    payload = json.dumps({"name": name, "max_depth": max_depth})
    response = client.send_command(payload, cmd_type="native:walk_references")
    return response.get("result", "{}")


@mcp.tool()
def map_class_relationships(
    pattern: str = "",
    superclass: str = "",
    limit: int = 100,
) -> str:
    """Map which classes can reference which types via their ParamBlock2 params.

    Scans the DLL class directory and finds every parameter that accepts a node,
    material, texturemap, or reference target. Builds a relationship graph showing
    "TurboSmooth accepts nothing", "Forest_Pro accepts nodes + texturemaps", etc.

    Use this to learn which classes plug into which slots without reading docs.

    Args:
        pattern: Wildcard filter for class names (e.g. "*Vray*", "Forest*").
        superclass: Filter by superclass: geometry, modifier, material, texturemap, etc.
        limit: Max classes to return (default 100).

    Returns:
        JSON array of classes with their accepted reference types and param names.
    """
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


@mcp.tool()
def learn_scene_patterns() -> str:
    """Analyze the current scene to learn real-world class usage patterns.

    Scans every object and collects frequency data on:
    - Which geometry/material/modifier/texmap classes are used and how often
    - Common modifier stacks (e.g. "TurboSmooth | Symmetry" appears 12 times)
    - Material-to-geometry associations (e.g. "PhysicalMaterial -> Editable Poly")
    - Texture-to-material connections (e.g. "Bitmap -> PhysicalMaterial")

    Use this to understand a scene's structure before making changes,
    or to learn production conventions from real files.

    Returns:
        JSON with frequency-sorted pattern data across all categories.
    """
    response = client.send_command("", cmd_type="native:learn_scene_patterns")
    return response.get("result", "{}")


@mcp.tool()
def watch_scene(
    action: str = "status",
    since: int = 0,
    limit: int = 100,
) -> str:
    """Live scene event watcher — track what happens in 3ds Max in real-time.

    Registers native SDK notification callbacks to capture scene events:
    node created/deleted, selection changes, modifier added, material assigned,
    file open, undo/redo, render start/end.

    Events are buffered (up to 500) and can be polled via action="get".

    Actions:
        status: Check if watcher is active and how many events are buffered.
        start: Start watching scene events.
        stop: Stop watching (callbacks stay registered but events aren't captured).
        get: Retrieve buffered events. Use since=<timestamp> for incremental polling.
        clear: Clear the event buffer.

    Args:
        action: One of: status, start, stop, get, clear.
        since: For action="get" — only return events after this timestamp.
        limit: For action="get" — max events to return (default 100).

    Returns:
        JSON with watcher status and/or event list.
    """
    payload = {"action": action}
    if action == "get":
        payload["since"] = since
        payload["limit"] = limit
    response = client.send_command(json.dumps(payload), cmd_type="native:watch_scene")
    return response.get("result", "{}")
