"""Data analysis engine for Copilot metrics."""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from ..github_client.models import CopilotDayMetrics, SeatInfo, UserUsageRecord

logger = logging.getLogger(__name__)


class DataAnalyzer:
    """Performs analysis and computes derived metrics from raw Copilot data."""

    def __init__(self) -> None:
        self._metrics_cache: list[CopilotDayMetrics] = []
        self._user_cache: list[UserUsageRecord] = []
        self._seat_cache: SeatInfo | None = None

    def load_metrics(self, metrics: list[CopilotDayMetrics]) -> None:
        """Load aggregated metrics for analysis."""
        self._metrics_cache = sorted(metrics, key=lambda m: m.date)

    def load_users(self, users: list[UserUsageRecord]) -> None:
        """Load user-level records for analysis."""
        self._user_cache = users

    def load_seats(self, seats: SeatInfo) -> None:
        """Load seat info for analysis."""
        self._seat_cache = seats

    def analyze(self, analysis_type: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Run an analysis and return structured results.

        Args:
            analysis_type: One of the supported analysis types.
            params: Optional parameters for the analysis.

        Returns:
            Dict with analysis results suitable for display or charting.
        """
        params = params or {}
        analyzers = {
            "adoption_trend": self._adoption_trend,
            "engagement_breakdown": self._engagement_breakdown,
            "acceptance_rate_by_language": self._acceptance_rate_by_language,
            "acceptance_rate_by_editor": self._acceptance_rate_by_editor,
            "top_users": self._top_users,
            "inactive_users": self._inactive_users,
            "team_comparison": self._team_comparison,
            "feature_usage_distribution": self._feature_usage_distribution,
            "loc_impact": self._loc_impact,
            "pr_lifecycle_impact": self._pr_lifecycle_impact,
            "cli_vs_ide_usage": self._cli_vs_ide_usage,
            "custom": self._custom_analysis,
        }

        analyzer = analyzers.get(analysis_type)
        if not analyzer:
            return {"error": f"Unknown analysis type: {analysis_type}"}

        return analyzer(params)

    def _adoption_trend(self, params: dict[str, Any]) -> dict[str, Any]:
        """Compute daily active/engaged user trend."""
        if not self._metrics_cache:
            return {"error": "No metrics data loaded. Fetch metrics first."}

        dates = [str(m.date) for m in self._metrics_cache]
        active = [m.total_active_users for m in self._metrics_cache]
        engaged = [m.total_engaged_users for m in self._metrics_cache]

        avg_active = round(sum(active) / len(active), 1) if active else 0
        avg_engaged = round(sum(engaged) / len(engaged), 1) if engaged else 0
        trend_direction = "up" if len(active) > 1 and active[-1] > active[0] else "down"

        return {
            "type": "adoption_trend",
            "dates": dates,
            "active_users": active,
            "engaged_users": engaged,
            "summary": {
                "avg_daily_active": avg_active,
                "avg_daily_engaged": avg_engaged,
                "peak_active": max(active) if active else 0,
                "trend_direction": trend_direction,
                "period_days": len(dates),
            },
        }

    def _engagement_breakdown(self, params: dict[str, Any]) -> dict[str, Any]:
        """Break down engagement across Copilot features."""
        if not self._metrics_cache:
            return {"error": "No metrics data loaded."}

        totals: dict[str, int] = defaultdict(int)
        for m in self._metrics_cache:
            if m.copilot_ide_code_completions:
                totals["IDE Completions"] += m.copilot_ide_code_completions.total_engaged_users
            if m.copilot_ide_chat:
                totals["IDE Chat"] += m.copilot_ide_chat.total_engaged_users
            if m.copilot_dotcom_chat:
                totals["GitHub.com Chat"] += m.copilot_dotcom_chat.total_engaged_users
            if m.copilot_cli:
                totals["CLI"] += m.copilot_cli.total_engaged_users
            if m.copilot_dotcom_pull_requests:
                totals["Pull Requests"] += m.copilot_dotcom_pull_requests.total_engaged_users

        days = len(self._metrics_cache)
        avg_totals = {k: round(v / days, 1) for k, v in totals.items()}

        return {
            "type": "engagement_breakdown",
            "features": avg_totals,
            "period_days": days,
        }

    def _acceptance_rate_by_language(self, params: dict[str, Any]) -> dict[str, Any]:
        """Compute acceptance rate per programming language."""
        lang_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"suggested": 0, "accepted": 0})

        for m in self._metrics_cache:
            if m.copilot_ide_code_completions:
                for lang in m.copilot_ide_code_completions.languages:
                    lang_stats[lang.name]["suggested"] += lang.total_code_suggestions
                    lang_stats[lang.name]["accepted"] += lang.total_code_acceptances

        results = {}
        for lang, stats in sorted(lang_stats.items(), key=lambda x: x[1]["suggested"], reverse=True):
            rate = round(stats["accepted"] / stats["suggested"] * 100, 1) if stats["suggested"] else 0
            results[lang] = {
                "acceptance_rate": rate,
                "total_suggestions": stats["suggested"],
                "total_acceptances": stats["accepted"],
            }

        return {"type": "acceptance_rate_by_language", "languages": results}

    def _acceptance_rate_by_editor(self, params: dict[str, Any]) -> dict[str, Any]:
        """Compute acceptance rate per IDE/editor."""
        editor_stats: dict[str, dict[str, int]] = defaultdict(
            lambda: {"users": 0, "suggestions": 0, "acceptances": 0}
        )

        for m in self._metrics_cache:
            if m.copilot_ide_code_completions:
                for editor in m.copilot_ide_code_completions.editors:
                    editor_stats[editor.name]["users"] += editor.total_engaged_users

        return {"type": "acceptance_rate_by_editor", "editors": dict(editor_stats)}

    def _top_users(self, params: dict[str, Any]) -> dict[str, Any]:
        """Identify top users by activity."""
        if not self._user_cache:
            return {"error": "No user data loaded. Fetch user metrics first."}

        top_n = params.get("top_n", 10)

        user_scores: dict[str, dict[str, Any]] = {}
        for u in self._user_cache:
            login = u.github_login
            if login not in user_scores:
                user_scores[login] = {
                    "completions": 0,
                    "chat_turns": 0,
                    "lines_accepted": 0,
                    "total_activity": 0,
                }
            user_scores[login]["completions"] += u.completions_acceptances
            user_scores[login]["chat_turns"] += u.chat_turns
            user_scores[login]["lines_accepted"] += u.completions_lines_accepted
            user_scores[login]["total_activity"] += (
                u.completions_acceptances + u.chat_turns + u.cli_turns + u.agent_turns
            )

        sorted_users = sorted(
            user_scores.items(), key=lambda x: x[1]["total_activity"], reverse=True
        )[:top_n]

        return {
            "type": "top_users",
            "users": [{"login": login, **stats} for login, stats in sorted_users],
            "total_users_analyzed": len(user_scores),
        }

    def _inactive_users(self, params: dict[str, Any]) -> dict[str, Any]:
        """Identify users with seats but no/low activity."""
        if not self._seat_cache:
            return {"error": "No seat data loaded. Fetch seat info first."}

        inactive = []
        for seat in self._seat_cache.seats:
            if seat.last_activity_at is None:
                inactive.append({
                    "login": seat.login,
                    "assigned_at": str(seat.assigned_at) if seat.assigned_at else None,
                    "last_activity": None,
                })

        return {
            "type": "inactive_users",
            "inactive_count": len(inactive),
            "total_seats": self._seat_cache.total_seats,
            "utilization_rate": round(
                (1 - len(inactive) / max(self._seat_cache.total_seats, 1)) * 100, 1
            ),
            "users": inactive[:50],  # Limit to 50 for display
        }

    def _team_comparison(self, params: dict[str, Any]) -> dict[str, Any]:
        """Compare metrics across teams (requires user data with team_slug)."""
        if not self._user_cache:
            return {"error": "No user data loaded."}

        team_stats: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"users": set(), "completions": 0, "chat_turns": 0, "lines_accepted": 0}
        )

        for u in self._user_cache:
            team = u.team_slug or "unassigned"
            team_stats[team]["users"].add(u.github_login)
            team_stats[team]["completions"] += u.completions_acceptances
            team_stats[team]["chat_turns"] += u.chat_turns
            team_stats[team]["lines_accepted"] += u.completions_lines_accepted

        results = {}
        for team, stats in team_stats.items():
            n_users = len(stats["users"])
            results[team] = {
                "active_users": n_users,
                "total_completions": stats["completions"],
                "avg_completions_per_user": round(stats["completions"] / max(n_users, 1), 1),
                "total_chat_turns": stats["chat_turns"],
                "total_lines_accepted": stats["lines_accepted"],
            }

        return {"type": "team_comparison", "teams": results}

    def _feature_usage_distribution(self, params: dict[str, Any]) -> dict[str, Any]:
        """Show distribution of usage across Copilot features."""
        if not self._metrics_cache:
            return {"error": "No metrics data loaded."}

        latest = self._metrics_cache[-1]
        distribution: dict[str, int] = {}

        if latest.copilot_ide_code_completions:
            distribution["Completions"] = latest.copilot_ide_code_completions.total_engaged_users
        if latest.copilot_ide_chat:
            distribution["IDE Chat"] = latest.copilot_ide_chat.total_engaged_users
        if latest.copilot_dotcom_chat:
            distribution["GitHub.com Chat"] = latest.copilot_dotcom_chat.total_engaged_users
        if latest.copilot_cli:
            distribution["CLI"] = latest.copilot_cli.total_engaged_users
        if latest.copilot_dotcom_pull_requests:
            distribution["PR Features"] = latest.copilot_dotcom_pull_requests.total_engaged_users

        total = sum(distribution.values())
        percentages = {
            k: round(v / max(total, 1) * 100, 1) for k, v in distribution.items()
        }

        return {
            "type": "feature_usage_distribution",
            "distribution": distribution,
            "percentages": percentages,
            "date": str(latest.date),
        }

    def _loc_impact(self, params: dict[str, Any]) -> dict[str, Any]:
        """Analyze lines-of-code impact from Copilot."""
        total_suggested = 0
        total_accepted = 0

        for m in self._metrics_cache:
            if m.copilot_ide_code_completions:
                total_suggested += m.copilot_ide_code_completions.total_code_lines_suggested
                total_accepted += m.copilot_ide_code_completions.total_code_lines_accepted

        acceptance_rate = round(total_accepted / max(total_suggested, 1) * 100, 1)

        return {
            "type": "loc_impact",
            "total_lines_suggested": total_suggested,
            "total_lines_accepted": total_accepted,
            "line_acceptance_rate": acceptance_rate,
            "period_days": len(self._metrics_cache),
        }

    def _pr_lifecycle_impact(self, params: dict[str, Any]) -> dict[str, Any]:
        """Analyze Copilot's impact on PR lifecycle."""
        total_pr_summaries = 0
        pr_users = 0

        for m in self._metrics_cache:
            if m.copilot_dotcom_pull_requests:
                total_pr_summaries += m.copilot_dotcom_pull_requests.total_pr_summaries_created
                pr_users += m.copilot_dotcom_pull_requests.total_engaged_users

        return {
            "type": "pr_lifecycle_impact",
            "total_pr_summaries_created": total_pr_summaries,
            "avg_daily_pr_users": round(pr_users / max(len(self._metrics_cache), 1), 1),
            "period_days": len(self._metrics_cache),
        }

    def _cli_vs_ide_usage(self, params: dict[str, Any]) -> dict[str, Any]:
        """Compare CLI vs IDE usage patterns."""
        cli_users = 0
        ide_users = 0
        cli_chats = 0
        ide_chats = 0

        for m in self._metrics_cache:
            if m.copilot_cli:
                cli_users += m.copilot_cli.total_engaged_users
                cli_chats += m.copilot_cli.total_chats
            if m.copilot_ide_chat:
                ide_users += m.copilot_ide_chat.total_engaged_users
                ide_chats += m.copilot_ide_chat.total_chats

        days = max(len(self._metrics_cache), 1)
        return {
            "type": "cli_vs_ide_usage",
            "cli": {
                "avg_daily_users": round(cli_users / days, 1),
                "total_chats": cli_chats,
            },
            "ide": {
                "avg_daily_users": round(ide_users / days, 1),
                "total_chats": ide_chats,
            },
            "period_days": len(self._metrics_cache),
        }

    def _custom_analysis(self, params: dict[str, Any]) -> dict[str, Any]:
        """Run a custom analysis based on provided params."""
        return {
            "type": "custom",
            "metrics_count": len(self._metrics_cache),
            "users_count": len(self._user_cache),
            "has_seat_data": self._seat_cache is not None,
            "note": "Custom analysis — review raw data for specific queries",
        }
