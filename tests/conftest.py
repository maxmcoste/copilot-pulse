"""Shared test fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def metrics_response() -> list[dict]:
    """Load the metrics API mock response."""
    return json.loads((FIXTURES_DIR / "metrics_response.json").read_text())


@pytest.fixture
def usage_metrics_response() -> dict:
    """Load the usage metrics API download-link response."""
    return json.loads((FIXTURES_DIR / "usage_metrics_response.json").read_text())


@pytest.fixture
def user_metrics_ndjson() -> str:
    """Load raw NDJSON user metrics content."""
    return (FIXTURES_DIR / "user_metrics_ndjson.txt").read_text()


@pytest.fixture
def seats_response() -> dict:
    """Load the seats API mock response."""
    return json.loads((FIXTURES_DIR / "seats_response.json").read_text())
