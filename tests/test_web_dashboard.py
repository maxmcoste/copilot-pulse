"""Tests for web dashboard productivity helpers."""

from __future__ import annotations

import pytest

from src.reports.web_dashboard import (
    _agent_edit_weekly_color,
    _compute_productivity_metrics,
    _resolve_active_user_count,
    _sum_agent_edits,
)


def test_sum_agent_edits_counts_only_agent_edit_feature() -> None:
    records = [
        {
            "totals_by_feature": [
                {"feature": "agent_edit", "code_generation_activity_count": 40},
                {"feature": "chat", "code_generation_activity_count": 99},
            ]
        },
        {
            "totals_by_feature": [
                {"feature": "agent_edit", "code_generation_activity_count": 2},
            ]
        },
    ]

    assert _sum_agent_edits(records) == 42


def test_resolve_active_user_count_prefers_28_day_org_denominator() -> None:
    records = [
        {"day": "2026-03-25", "monthly_active_users": 1400, "total_active_users": 220},
        {"day": "2026-04-01", "monthly_active_users": 1573, "total_active_users": 245},
    ]

    assert _resolve_active_user_count(records, is_filtered=False) == 1573


def test_resolve_active_user_count_uses_unique_logins_for_filtered_views() -> None:
    records = [
        {"user_login": "alice"},
        {"user_login": "alice"},
        {"user_login": "bob"},
    ]

    assert _resolve_active_user_count(records, is_filtered=True) == 2


def test_compute_productivity_metrics_assigns_advanced_badge_above_50() -> None:
    metrics = _compute_productivity_metrics(
        agent_edits=80_766,
        active_users=1_573,
        total_licenses=6_700,
    )

    assert metrics["agent_efficacy"] == pytest.approx(80_766 / 1_573)
    assert metrics["real_adoption"] == pytest.approx(80_766 / 6_700)
    assert metrics["efficacy_badge"] == "Advanced"


def test_compute_productivity_metrics_handles_missing_denominators() -> None:
    metrics = _compute_productivity_metrics(
        agent_edits=125,
        active_users=0,
        total_licenses=0,
    )

    assert metrics["agent_efficacy"] is None
    assert metrics["real_adoption"] is None
    assert metrics["efficacy_badge"] is None


@pytest.mark.parametrize(
    ("ratio", "color"),
    [
        (0, "#f85149"),
        (2.5, "#d29922"),
        (12.5, "#d29922"),
        (20, "#3fb950"),
        (25.1, "#58a6ff"),
    ],
)
def test_agent_edit_weekly_color_uses_expected_thresholds(ratio: float, color: str) -> None:
    assert _agent_edit_weekly_color(ratio) == color
