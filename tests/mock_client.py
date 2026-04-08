"""Reusable mock client for testing MCP tools without a live 3ds Max connection.

Usage:
    mock = MockMaxClient()
    mock.add_response("native:ping", {"pong": True, "server": "3dsmax-mcp"})
    mock.add_response("maxscript", {"result": "Box01"}, pattern="Box")

    # In tests, patch the global client:
    with mock.patch_client("src.tools.objects"):
        result = create_object("Box", "TestBox")
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Optional
from uuid import uuid4


@dataclass
class CallRecord:
    """Immutable record of a single send_command() invocation."""

    command: str
    cmd_type: str
    timeout: Optional[float]
    timestamp: float
    response: dict[str, Any]


@dataclass
class _ResponseRule:
    """A rule that matches commands and returns a canned response."""

    cmd_type: str
    result: dict[str, Any]
    pattern: Optional[str] = None
    _compiled: Optional[re.Pattern[str]] = field(default=None, repr=False)

    def matches(self, command: str, cmd_type: str) -> bool:
        if self.cmd_type != cmd_type:
            return False
        if self.pattern is None:
            return True
        if self._compiled is None:
            self._compiled = re.compile(self.pattern, re.IGNORECASE)
        return bool(self._compiled.search(command))


class MockMaxClient:
    """Drop-in replacement for MaxClient that returns scripted responses.

    Supports:
    - Scenario-based response rules (cmd_type + optional pattern matching)
    - Call recording for assertion
    - native_available toggle
    - Default fallback response
    """

    def __init__(
        self,
        *,
        native_available: bool = True,
        default_result: str = "ok",
    ) -> None:
        self._native_available = native_available
        self._default_result = default_result
        self._rules: list[_ResponseRule] = []
        self._call_history: list[CallRecord] = []

        # Satisfy MaxClient interface attributes
        self.host = "127.0.0.1"
        self.port = 8765
        self.timeout = 120.0
        self.transport = "mock"
        self.pipe_name = r"\\.\pipe\3dsmax-mcp-mock"

    # ── Configuration ────────────────────────────────────────────

    @property
    def native_available(self) -> bool:
        return self._native_available

    @native_available.setter
    def native_available(self, value: bool) -> None:
        self._native_available = value

    def add_response(
        self,
        cmd_type: str,
        result: dict[str, Any] | str,
        *,
        pattern: Optional[str] = None,
    ) -> None:
        """Register a canned response for a given cmd_type + optional command pattern.

        Args:
            cmd_type: Command type to match (e.g. "maxscript", "native:create_object").
            result: Response payload dict, or a string shorthand for {"result": value}.
            pattern: Optional regex to match against the command string.
        """
        if isinstance(result, str):
            result = {"result": result}
        self._rules.append(_ResponseRule(cmd_type=cmd_type, result=result, pattern=pattern))

    def clear_responses(self) -> None:
        """Remove all registered response rules."""
        self._rules.clear()

    # ── Call history ─────────────────────────────────────────────

    @property
    def call_history(self) -> list[CallRecord]:
        return list(self._call_history)

    @property
    def call_count(self) -> int:
        return len(self._call_history)

    def last_call(self) -> CallRecord:
        """Return the most recent call record. Raises IndexError if none."""
        return self._call_history[-1]

    def calls_for(self, cmd_type: str) -> list[CallRecord]:
        """Filter call history by cmd_type."""
        return [c for c in self._call_history if c.cmd_type == cmd_type]

    def reset_history(self) -> None:
        """Clear call history (keeps response rules)."""
        self._call_history.clear()

    # ── Core interface (matches MaxClient.send_command) ──────────

    def send_command(
        self,
        command: str,
        cmd_type: str = "maxscript",
        timeout: Optional[float] = None,
    ) -> dict[str, Any]:
        """Simulate MaxClient.send_command() with canned responses."""
        response = self._find_response(command, cmd_type)

        record = CallRecord(
            command=command,
            cmd_type=cmd_type,
            timeout=timeout,
            timestamp=time.perf_counter(),
            response=response,
        )
        self._call_history.append(record)

        return response

    # ── Patching helper ──────────────────────────────────────────

    def patch_client(self, module: Any) -> Any:
        """Return a context manager that patches `client` in an already-imported module.

        Usage:
            from src.tools import objects
            with mock.patch_client(objects):
                result = objects.create_object("Box")
        """
        from unittest.mock import patch as _patch
        return _patch.object(module, "client", self)

    # ── Internal ─────────────────────────────────────────────────

    def _find_response(self, command: str, cmd_type: str) -> dict[str, Any]:
        # Check rules in reverse order (last added wins)
        for rule in reversed(self._rules):
            if rule.matches(command, cmd_type):
                return self._wrap_response(rule.result)
        return self._wrap_response({"result": self._default_result})

    def _wrap_response(self, result: dict[str, Any]) -> dict[str, Any]:
        """Ensure response has standard fields (success, requestId, meta)."""
        response = {"success": True, **result}
        response.setdefault("requestId", uuid4().hex)
        response.setdefault("meta", {"clientRoundTripMs": 0.1})
        return response
