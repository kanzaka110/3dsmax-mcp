"""Connection lifecycle state machine for MaxClient.

Tracks transport state through well-defined phases with timestamps and
event history, inspired by claw-code's MCP lifecycle management pattern.

States:
    DISCONNECTED ─► CONNECTING ─► HANDSHAKE ─► READY
         ▲              │             │           │
         └──────────────┴─────────────┴───► ERROR
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Well-defined connection lifecycle phases."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    HANDSHAKE = "handshake"
    READY = "ready"
    ERROR = "error"


# Valid state transitions
_TRANSITIONS: dict[ConnectionState, frozenset[ConnectionState]] = {
    ConnectionState.DISCONNECTED: frozenset({
        ConnectionState.CONNECTING,
    }),
    ConnectionState.CONNECTING: frozenset({
        ConnectionState.HANDSHAKE,
        ConnectionState.ERROR,
        ConnectionState.DISCONNECTED,
    }),
    ConnectionState.HANDSHAKE: frozenset({
        ConnectionState.READY,
        ConnectionState.ERROR,
        ConnectionState.DISCONNECTED,
    }),
    ConnectionState.READY: frozenset({
        ConnectionState.ERROR,
        ConnectionState.DISCONNECTED,
    }),
    ConnectionState.ERROR: frozenset({
        ConnectionState.CONNECTING,
        ConnectionState.DISCONNECTED,
    }),
}


@dataclass(frozen=True)
class StateEvent:
    """Immutable record of a state transition."""

    from_state: ConnectionState
    to_state: ConnectionState
    timestamp: float
    transport: str
    detail: str = ""


StateCallback = Callable[[StateEvent], None]


class LifecycleManager:
    """Tracks connection state with transition validation and event history.

    Usage:
        lm = LifecycleManager()
        lm.on_state_change(my_callback)

        lm.transition_to(ConnectionState.CONNECTING, "pipe", "opening pipe handle")
        lm.transition_to(ConnectionState.HANDSHAKE, "pipe", "first command sent")
        lm.transition_to(ConnectionState.READY, "pipe", "handshake ok")
    """

    _MAX_HISTORY = 50

    def __init__(self) -> None:
        self._state = ConnectionState.DISCONNECTED
        self._transport = ""
        self._history: list[StateEvent] = []
        self._callbacks: list[StateCallback] = []
        self._state_since = time.perf_counter()
        self._ready_count = 0
        self._error_count = 0

    # ── Properties ───────────────────────────────────────────────

    @property
    def state(self) -> ConnectionState:
        return self._state

    @property
    def transport(self) -> str:
        return self._transport

    @property
    def is_ready(self) -> bool:
        return self._state == ConnectionState.READY

    @property
    def state_duration_ms(self) -> float:
        """Milliseconds spent in the current state."""
        return (time.perf_counter() - self._state_since) * 1000.0

    @property
    def history(self) -> list[StateEvent]:
        return list(self._history)

    @property
    def ready_count(self) -> int:
        """Number of times the connection reached READY state."""
        return self._ready_count

    @property
    def error_count(self) -> int:
        """Number of times the connection entered ERROR state."""
        return self._error_count

    # ── Callbacks ────────────────────────────────────────────────

    def on_state_change(self, callback: StateCallback) -> None:
        """Register a callback invoked on every state transition."""
        self._callbacks.append(callback)

    # ── State transitions ────────────────────────────────────────

    def transition_to(
        self,
        new_state: ConnectionState,
        transport: str = "",
        detail: str = "",
    ) -> StateEvent:
        """Transition to a new state. Raises ValueError on invalid transition."""
        old_state = self._state
        allowed = _TRANSITIONS.get(old_state, frozenset())

        if new_state not in allowed:
            raise ValueError(
                f"Invalid transition: {old_state.value} -> {new_state.value}. "
                f"Allowed: {', '.join(s.value for s in allowed)}"
            )

        event = StateEvent(
            from_state=old_state,
            to_state=new_state,
            timestamp=time.perf_counter(),
            transport=transport or self._transport,
            detail=detail,
        )

        self._state = new_state
        self._transport = transport or self._transport
        self._state_since = event.timestamp

        if new_state == ConnectionState.READY:
            self._ready_count += 1
        elif new_state == ConnectionState.ERROR:
            self._error_count += 1

        self._history.append(event)
        if len(self._history) > self._MAX_HISTORY:
            self._history = self._history[-self._MAX_HISTORY:]

        logger.debug(
            "lifecycle: %s -> %s [%s] %s",
            old_state.value,
            new_state.value,
            event.transport,
            detail,
        )

        for cb in self._callbacks:
            try:
                cb(event)
            except Exception:
                logger.warning("lifecycle callback error", exc_info=True)

        return event

    def reset(self) -> None:
        """Force back to DISCONNECTED (e.g. on cleanup). Skips transition validation."""
        if self._state != ConnectionState.DISCONNECTED:
            event = StateEvent(
                from_state=self._state,
                to_state=ConnectionState.DISCONNECTED,
                timestamp=time.perf_counter(),
                transport=self._transport,
                detail="forced reset",
            )
            self._state = ConnectionState.DISCONNECTED
            self._state_since = event.timestamp
            self._history.append(event)

    def to_dict(self) -> dict[str, object]:
        """Snapshot of lifecycle state for diagnostics (e.g. bridge status)."""
        last_error: Optional[str] = None
        for event in reversed(self._history):
            if event.to_state == ConnectionState.ERROR:
                last_error = event.detail
                break

        return {
            "state": self._state.value,
            "transport": self._transport,
            "stateDurationMs": round(self.state_duration_ms, 1),
            "readyCount": self._ready_count,
            "errorCount": self._error_count,
            "lastError": last_error,
        }
