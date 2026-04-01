"""Plan which API calls to make based on parsed intent."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from .intent_parser import IntentCategory, ParsedIntent

logger = logging.getLogger(__name__)


@dataclass
class QueryPlan:
    """A plan of API calls and analysis steps to execute."""

    api_calls: list[dict[str, str]] = field(default_factory=list)
    analysis_steps: list[str] = field(default_factory=list)
    chart_type: str | None = None
    export_format: str | None = None
    notes: list[str] = field(default_factory=list)


def plan_query(intent: ParsedIntent, config_enterprise: str, config_org: str) -> QueryPlan:
    """Create a query execution plan from a parsed intent.

    This provides hints for the orchestrator but Claude ultimately
    decides which tools to call via its own reasoning.

    Args:
        intent: Parsed user intent.
        config_enterprise: Default enterprise slug from config.
        config_org: Default organization name from config.

    Returns:
        QueryPlan with suggested API calls and analysis steps.
    """
    plan = QueryPlan()

    if intent.export_format:
        plan.export_format = intent.export_format

    period = intent.time_range or "28-day"
    day = intent.entities.get("day")

    match intent.category:
        case IntentCategory.METRICS_QUERY:
            if config_enterprise:
                plan.api_calls.append({
                    "tool": "get_enterprise_metrics",
                    "period": period,
                    **({"day": day} if day else {}),
                })
            elif config_org:
                plan.api_calls.append({
                    "tool": "get_organization_metrics",
                    "org": config_org,
                    "period": period,
                    **({"day": day} if day else {}),
                })
            plan.analysis_steps.append("engagement_breakdown")

        case IntentCategory.USER_ANALYSIS:
            scope = "enterprise" if config_enterprise else "organization"
            plan.api_calls.append({
                "tool": "get_user_metrics",
                "scope": scope,
                **({"org": config_org} if config_org else {}),
                "period": period,
            })
            if "top" in " ".join(intent.keywords) or intent.category == IntentCategory.USER_ANALYSIS:
                plan.analysis_steps.append("top_users")

        case IntentCategory.TEAM_COMPARISON:
            plan.analysis_steps.append("team_comparison")
            plan.notes.append(
                "Team metrics require the legacy API and teams with 5+ licensed members"
            )

        case IntentCategory.TREND_ANALYSIS:
            if config_enterprise:
                plan.api_calls.append({
                    "tool": "get_enterprise_metrics",
                    "period": "28-day",
                })
            elif config_org:
                plan.api_calls.append({
                    "tool": "get_organization_metrics",
                    "org": config_org,
                    "period": "28-day",
                })
            plan.analysis_steps.append("adoption_trend")
            plan.chart_type = "line"

        case IntentCategory.SEAT_MANAGEMENT:
            if config_org:
                plan.api_calls.append({
                    "tool": "get_seat_info",
                    "org": config_org,
                })
            plan.analysis_steps.append("inactive_users")

        case IntentCategory.EXPORT_REPORT:
            # Need to fetch data first, then export
            if config_enterprise:
                plan.api_calls.append({
                    "tool": "get_enterprise_metrics",
                    "period": "28-day",
                })
            elif config_org:
                plan.api_calls.append({
                    "tool": "get_organization_metrics",
                    "org": config_org,
                    "period": "28-day",
                })
            plan.export_format = intent.export_format or "pdf"

        case IntentCategory.CHART_REQUEST:
            plan.chart_type = "bar"
            if config_enterprise:
                plan.api_calls.append({
                    "tool": "get_enterprise_metrics",
                    "period": period,
                })
            elif config_org:
                plan.api_calls.append({
                    "tool": "get_organization_metrics",
                    "org": config_org,
                    "period": period,
                })

        case _:
            plan.notes.append("General question — Claude will determine the best approach")

    return plan
