"""Tests for the GitHub client layer."""

from __future__ import annotations

import json

import httpx
import pytest

from src.github_client.models import (
    CopilotDayMetrics,
    IdeCompletionMetrics,
    ReportDownloadResponse,
    SeatAssignment,
    SeatInfo,
    UserUsageRecord,
)


class TestModels:
    """Test Pydantic model parsing."""

    def test_copilot_day_metrics_from_dict(self, metrics_response: list[dict]) -> None:
        record = metrics_response[0]
        metrics = CopilotDayMetrics(
            date=record["date"],
            total_active_users=record["total_active_users"],
            total_engaged_users=record["total_engaged_users"],
        )
        assert metrics.total_active_users == 142
        assert metrics.total_engaged_users == 118
        assert str(metrics.date) == "2026-03-25"

    def test_ide_completion_metrics(self, metrics_response: list[dict]) -> None:
        data = metrics_response[0]["copilot_ide_code_completions"]
        m = IdeCompletionMetrics(**data)
        assert m.total_engaged_users == 105
        assert m.total_code_suggestions == 48520
        assert m.acceptance_rate == pytest.approx(32.2, abs=0.1)
        assert len(m.editors) == 2
        assert len(m.languages) == 5

    def test_ide_completion_zero_suggestions(self) -> None:
        m = IdeCompletionMetrics(total_code_suggestions=0, total_code_acceptances=0)
        assert m.acceptance_rate == 0.0

    def test_user_usage_record(self, user_metrics_ndjson: str) -> None:
        lines = user_metrics_ndjson.strip().splitlines()
        record = json.loads(lines[0])
        user = UserUsageRecord(
            github_login=record["github_login"],
            completions_suggestions=record["completions_suggestions"],
            completions_acceptances=record["completions_acceptances"],
            chat_turns=record["chat_turns"],
            editors=record["editors"],
            languages=record["languages"],
        )
        assert user.github_login == "alice"
        assert user.completions_suggestions == 320
        assert user.completions_acceptances == 112
        assert "python" in user.languages

    def test_seat_info(self, seats_response: dict) -> None:
        seats = []
        for seat in seats_response["seats"]:
            assignee = seat.get("assignee", {})
            seats.append(SeatAssignment(
                login=assignee.get("login", ""),
                last_activity_at=seat.get("last_activity_at"),
                plan_type=seat.get("plan_type", ""),
            ))

        info = SeatInfo(total_seats=seats_response["total_seats"], seats=seats)
        assert info.total_seats == 200
        assert len(info.seats) == 5
        assert info.seats[0].login == "alice"
        # eve and frank have no activity
        inactive = [s for s in info.seats if s.last_activity_at is None]
        assert len(inactive) == 2

    def test_report_download_response(self, usage_metrics_response: dict) -> None:
        resp = ReportDownloadResponse(**usage_metrics_response)
        assert len(resp.download_links) == 1
        assert resp.report_day == "2026-03-25"


class TestNDJSONParsing:
    """Test NDJSON parsing logic."""

    def test_parse_ndjson_lines(self, user_metrics_ndjson: str) -> None:
        records = []
        for line in user_metrics_ndjson.strip().splitlines():
            if line.strip():
                records.append(json.loads(line))

        assert len(records) == 5
        assert records[0]["github_login"] == "alice"
        assert records[2]["github_login"] == "charlie"
        assert records[4]["completions_suggestions"] == 0  # eve inactive


class TestBaseClientRetry:
    """Test the base client error handling without hitting real APIs."""

    def test_github_api_error(self) -> None:
        from src.github_client.base_client import GitHubAPIError

        err = GitHubAPIError(403, "Insufficient permissions")
        assert err.status_code == 403
        assert "Insufficient permissions" in str(err)

    def test_github_api_error_422(self) -> None:
        from src.github_client.base_client import GitHubAPIError

        err = GitHubAPIError(422, "Copilot metrics disabled")
        assert err.status_code == 422
        assert "disabled" in str(err)
