"""Tests for the agent layer (intent parsing, data analysis)."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from src.agent.data_analyzer import DataAnalyzer
from src.agent.intent_parser import IntentCategory, parse_intent
from src.github_client.models import (
    CopilotDayMetrics,
    IdeCompletionMetrics,
    IdeChatMetrics,
    CliMetrics,
    DotcomChatMetrics,
    PullRequestMetrics,
    SeatAssignment,
    SeatInfo,
    UserUsageRecord,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestIntentParser:
    """Test the local intent parser."""

    def test_metrics_query(self) -> None:
        intent = parse_intent("Quanti utenti attivi abbiamo oggi?")
        assert intent.category == IntentCategory.METRICS_QUERY
        assert intent.time_range == "1-day"

    def test_trend_analysis(self) -> None:
        intent = parse_intent("Mostrami il trend degli ultimi 28 giorni")
        assert intent.category == IntentCategory.TREND_ANALYSIS
        assert intent.time_range == "28-day"

    def test_user_analysis(self) -> None:
        intent = parse_intent("Chi sono i top 10 utenti?")
        assert intent.category == IntentCategory.USER_ANALYSIS

    def test_team_comparison(self) -> None:
        intent = parse_intent("Confronta il team backend con il team frontend")
        assert intent.category == IntentCategory.TEAM_COMPARISON

    def test_seat_management(self) -> None:
        intent = parse_intent("Quanti seat abbiamo assegnati ma mai utilizzati?")
        assert intent.category == IntentCategory.SEAT_MANAGEMENT

    def test_export_pdf(self) -> None:
        intent = parse_intent("Generami un report PDF per il management")
        assert intent.category == IntentCategory.EXPORT_REPORT
        assert intent.export_format == "pdf"

    def test_export_excel(self) -> None:
        intent = parse_intent("Esporta le metriche in Excel")
        assert intent.export_format == "excel"

    def test_date_extraction(self) -> None:
        intent = parse_intent("Metriche del 2026-03-15")
        assert intent.entities.get("day") == "2026-03-15"

    def test_english_query(self) -> None:
        intent = parse_intent("Show me the acceptance rate by language")
        assert intent.category == IntentCategory.METRICS_QUERY

    def test_keyword_extraction(self) -> None:
        intent = parse_intent("Come va il chat usage nella CLI?")
        assert "chat" in intent.keywords
        assert "cli" in intent.keywords


class TestDataAnalyzer:
    """Test the data analysis engine."""

    @pytest.fixture
    def analyzer_with_metrics(self, metrics_response: list[dict]) -> DataAnalyzer:
        analyzer = DataAnalyzer()
        metrics = []
        for record in metrics_response:
            m = CopilotDayMetrics(
                date=record["date"],
                total_active_users=record["total_active_users"],
                total_engaged_users=record["total_engaged_users"],
            )
            if "copilot_ide_code_completions" in record:
                m.copilot_ide_code_completions = IdeCompletionMetrics(
                    **record["copilot_ide_code_completions"]
                )
            if "copilot_ide_chat" in record:
                m.copilot_ide_chat = IdeChatMetrics(**record["copilot_ide_chat"])
            if "copilot_dotcom_chat" in record:
                m.copilot_dotcom_chat = DotcomChatMetrics(**record["copilot_dotcom_chat"])
            if "copilot_dotcom_pull_requests" in record:
                m.copilot_dotcom_pull_requests = PullRequestMetrics(
                    **record["copilot_dotcom_pull_requests"]
                )
            if "copilot_cli" in record:
                m.copilot_cli = CliMetrics(**record["copilot_cli"])
            metrics.append(m)
        analyzer.load_metrics(metrics)
        return analyzer

    @pytest.fixture
    def analyzer_with_users(self, user_metrics_ndjson: str) -> DataAnalyzer:
        analyzer = DataAnalyzer()
        users = []
        for line in user_metrics_ndjson.strip().splitlines():
            record = json.loads(line)
            users.append(UserUsageRecord(
                github_login=record["github_login"],
                completions_suggestions=record.get("completions_suggestions", 0),
                completions_acceptances=record.get("completions_acceptances", 0),
                completions_lines_accepted=record.get("completions_lines_accepted", 0),
                chat_turns=record.get("chat_turns", 0),
                cli_turns=record.get("cli_turns", 0),
                agent_turns=record.get("agent_turns", 0),
            ))
        analyzer.load_users(users)
        return analyzer

    def test_adoption_trend(self, analyzer_with_metrics: DataAnalyzer) -> None:
        result = analyzer_with_metrics.analyze("adoption_trend")
        assert result["type"] == "adoption_trend"
        assert len(result["dates"]) == 2
        assert result["summary"]["avg_daily_active"] == 145.0
        assert result["summary"]["peak_active"] == 148

    def test_engagement_breakdown(self, analyzer_with_metrics: DataAnalyzer) -> None:
        result = analyzer_with_metrics.analyze("engagement_breakdown")
        assert result["type"] == "engagement_breakdown"
        assert "IDE Completions" in result["features"]
        assert "IDE Chat" in result["features"]
        assert result["period_days"] == 2

    def test_acceptance_rate_by_language(self, analyzer_with_metrics: DataAnalyzer) -> None:
        result = analyzer_with_metrics.analyze("acceptance_rate_by_language")
        assert result["type"] == "acceptance_rate_by_language"
        assert "python" in result["languages"]
        python_rate = result["languages"]["python"]["acceptance_rate"]
        assert 30 <= python_rate <= 40  # ~35% based on fixture data

    def test_top_users(self, analyzer_with_users: DataAnalyzer) -> None:
        result = analyzer_with_users.analyze("top_users", {"top_n": 3})
        assert result["type"] == "top_users"
        assert len(result["users"]) == 3
        # charlie should be #1 (highest total activity)
        assert result["users"][0]["login"] == "charlie"
        assert result["total_users_analyzed"] == 5

    def test_top_users_no_data(self) -> None:
        analyzer = DataAnalyzer()
        result = analyzer.analyze("top_users")
        assert "error" in result

    def test_feature_usage_distribution(self, analyzer_with_metrics: DataAnalyzer) -> None:
        result = analyzer_with_metrics.analyze("feature_usage_distribution")
        assert result["type"] == "feature_usage_distribution"
        assert "Completions" in result["distribution"]
        assert sum(result["percentages"].values()) == pytest.approx(100.0, abs=1.0)

    def test_loc_impact(self, analyzer_with_metrics: DataAnalyzer) -> None:
        result = analyzer_with_metrics.analyze("loc_impact")
        assert result["type"] == "loc_impact"
        assert result["total_lines_suggested"] > 0
        assert result["total_lines_accepted"] > 0
        assert 0 < result["line_acceptance_rate"] < 100

    def test_cli_vs_ide_usage(self, analyzer_with_metrics: DataAnalyzer) -> None:
        result = analyzer_with_metrics.analyze("cli_vs_ide_usage")
        assert result["type"] == "cli_vs_ide_usage"
        assert result["cli"]["total_chats"] > 0
        assert result["ide"]["total_chats"] > 0

    def test_inactive_users_with_seats(self, seats_response: dict) -> None:
        analyzer = DataAnalyzer()
        seats = []
        for seat in seats_response["seats"]:
            assignee = seat.get("assignee", {})
            seats.append(SeatAssignment(
                login=assignee.get("login", ""),
                last_activity_at=seat.get("last_activity_at"),
            ))
        info = SeatInfo(total_seats=seats_response["total_seats"], seats=seats)
        analyzer.load_seats(info)

        result = analyzer.analyze("inactive_users")
        assert result["type"] == "inactive_users"
        assert result["inactive_count"] == 2  # eve and frank
        assert result["total_seats"] == 200
        assert result["utilization_rate"] == 99.0  # (200-2)/200 * 100

    def test_unknown_analysis_type(self) -> None:
        analyzer = DataAnalyzer()
        result = analyzer.analyze("nonexistent_type")
        assert "error" in result


class TestToolsSchema:
    """Test that tool schemas are well-formed."""

    def test_tools_list(self) -> None:
        from src.agent.tools_schema import TOOLS

        assert len(TOOLS) == 10
        names = [t["name"] for t in TOOLS]
        assert "get_enterprise_metrics" in names
        assert "get_organization_metrics" in names
        assert "get_team_metrics" in names
        assert "get_user_metrics" in names
        assert "get_seat_info" in names
        assert "analyze_data" in names
        assert "generate_chart" in names
        assert "export_report" in names

    def test_all_tools_have_input_schema(self) -> None:
        from src.agent.tools_schema import TOOLS

        for tool in TOOLS:
            assert "name" in tool
            assert "description" in tool
            assert "input_schema" in tool
            assert tool["input_schema"]["type"] == "object"
