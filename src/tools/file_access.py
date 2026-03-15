"""External .max file access tools — inspect, merge, and batch scan."""

import json
import fnmatch
from pathlib import Path
from typing import Optional
from ..server import mcp, client


@mcp.tool()
def inspect_max_file(
    file_path: str,
    list_objects: bool = False,
) -> str:
    """Inspect an external .max file without opening it.

    Reads OLE metadata (file size, dates, author, title, comments) directly
    from the file's structured storage — no scene load required.
    Optionally lists all object names in the file using the merge-list API.

    Args:
        file_path: Full path to the .max file.
        list_objects: If True, also list all object names in the file
                      (slightly slower — uses Max's merge-list API).

    Returns:
        JSON with file metadata and optionally object names.
    """
    payload = json.dumps({
        "file_path": file_path,
        "list_objects": list_objects,
    })
    response = client.send_command(payload, cmd_type="native:inspect_max_file")
    return response.get("result", "")


@mcp.tool()
def merge_from_file(
    file_path: str,
    object_names: Optional[list[str]] = None,
    select_merged: bool = True,
    duplicate_action: str = "rename",
) -> str:
    """Merge objects from an external .max file into the current scene.

    Supports selective merging (specific objects by name) or full merge.
    Uses the SDK's MergeFromFile with configurable duplicate handling.

    Args:
        file_path: Full path to the .max file to merge from.
        object_names: Optional list of specific object names to merge.
                      If empty/None, merges all objects.
        select_merged: If True, select the merged objects after import.
        duplicate_action: How to handle duplicate names:
            - "rename": Auto-rename merged objects (default)
            - "skip": Don't merge objects with existing names
            - "merge": Keep both old and new
            - "delete_old": Replace existing objects

    Returns:
        JSON with list of merged object names and count.
    """
    payload = {
        "file_path": file_path,
        "select_merged": select_merged,
        "duplicate_action": duplicate_action,
    }
    if object_names:
        payload["object_names"] = object_names
    response = client.send_command(json.dumps(payload), cmd_type="native:merge_from_file")
    return response.get("result", "")


@mcp.tool()
def batch_file_info(
    file_paths: list[str],
    list_objects: bool = False,
) -> str:
    """Read metadata from multiple .max files in a single call.

    Metadata-only mode runs in parallel threads for maximum speed.
    With list_objects=True, object listing runs sequentially on the main thread.

    Args:
        file_paths: List of full paths to .max files.
        list_objects: If True, also list object names from each file.

    Returns:
        JSON array with metadata for each file.
    """
    payload = json.dumps({
        "file_paths": file_paths,
        "list_objects": list_objects,
    })
    response = client.send_command(payload, cmd_type="native:batch_file_info")
    return response.get("result", "")


@mcp.tool()
def search_max_files(
    folder: str,
    pattern: str = "*",
    recursive: bool = True,
) -> str:
    """Search .max files in a folder for objects matching a name pattern.

    Scans every .max file in the folder, lists all objects, and filters
    by the given wildcard pattern. Use this to find which files contain
    specific objects — e.g. "where is the fridge?", "find all files with
    lights", "which scene has the character mesh?".

    Args:
        folder: Folder path to scan for .max files.
        pattern: Wildcard pattern to match object names (e.g. "Fridge*",
                 "*Light*", "CC_Base_*"). Default "*" returns all objects.
        recursive: If True, scan subfolders too. Default True.

    Returns:
        JSON with matching objects grouped by file.
    """
    p = Path(folder)
    if not p.is_dir():
        return json.dumps({"error": f"Folder not found: {folder}"})

    glob_pattern = "**/*.max" if recursive else "*.max"
    max_files = [str(f) for f in p.glob(glob_pattern) if f.is_file()]

    if not max_files:
        return json.dumps({"error": f"No .max files found in: {folder}"})

    # Get object lists from all files via native batch handler
    payload = json.dumps({
        "file_paths": max_files,
        "list_objects": True,
    })
    response = client.send_command(payload, cmd_type="native:batch_file_info")
    raw = response.get("result", "")

    try:
        data = json.loads(raw)
    except Exception:
        return raw

    # Filter objects by pattern
    results = []
    total_matches = 0
    for file_info in data.get("files", []):
        objects = file_info.get("objects", [])
        matched = [name for name in objects if fnmatch.fnmatch(name.lower(), pattern.lower())]
        if matched:
            results.append({
                "file": file_info.get("filePath", ""),
                "matchCount": len(matched),
                "totalObjects": len(objects),
                "matches": matched,
            })
            total_matches += len(matched)

    return json.dumps({
        "pattern": pattern,
        "filesScanned": len(max_files),
        "filesWithMatches": len(results),
        "totalMatches": total_matches,
        "results": results,
    })
