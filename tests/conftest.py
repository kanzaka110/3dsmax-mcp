"""Shared pytest fixtures for 3dsmax-mcp tests."""

from __future__ import annotations

import pytest

from tests.mock_client import MockMaxClient


@pytest.fixture()
def mock_client() -> MockMaxClient:
    """Fresh MockMaxClient with native_available=True and no pre-loaded rules."""
    return MockMaxClient(native_available=True)


@pytest.fixture()
def mock_client_tcp() -> MockMaxClient:
    """MockMaxClient with native_available=False (simulates TCP-only fallback)."""
    return MockMaxClient(native_available=False)
