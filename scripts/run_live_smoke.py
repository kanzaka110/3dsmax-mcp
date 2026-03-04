"""Small live smoke test for the 3ds Max MCP bridge."""

from __future__ import annotations

import json
import sys

from src.tools.bridge import get_bridge_status
from src.tools.capabilities import get_plugin_capabilities
from src.tools.session_context import get_session_context
from src.tools.snapshots import get_scene_delta, get_scene_snapshot, get_selection_snapshot


def main() -> int:
    checks = [
        ("get_bridge_status", lambda: json.loads(get_bridge_status())),
        ("get_plugin_capabilities", lambda: json.loads(get_plugin_capabilities())),
        ("get_scene_snapshot", lambda: json.loads(get_scene_snapshot())),
        ("get_selection_snapshot", lambda: json.loads(get_selection_snapshot())),
        ("get_scene_delta_capture", lambda: json.loads(get_scene_delta(capture=True))),
        ("get_session_context", lambda: json.loads(get_session_context())),
    ]

    failed = False
    for name, fn in checks:
        try:
            result = fn()
            print(f"[ok] {name}")
            print(json.dumps(result, indent=2))
        except Exception as exc:  # pragma: no cover - live smoke path
            failed = True
            print(f"[fail] {name}: {exc}", file=sys.stderr)

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
