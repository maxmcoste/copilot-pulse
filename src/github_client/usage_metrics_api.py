"""Copilot Usage Metrics API (new, GA) — primary data source.

These endpoints use X-GitHub-Api-Version: 2026-03-10 and return NDJSON download links.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from .base_client import GitHubBaseClient
from .models import (
    CopilotDayMetrics,
    ReportDownloadResponse,
    UserUsageRecord,
)

logger = logging.getLogger(__name__)


def _parse_org_day_record(record: dict[str, Any]) -> CopilotDayMetrics:
    """Parse a single NDJSON record into CopilotDayMetrics."""
    from .models import (
        CliMetrics,
        CodeGenerationMetrics,
        DotcomChatMetrics,
        IdeChatMetrics,
        IdeCompletionMetrics,
        PullRequestMetrics,
    )

    day = record.get("date") or record.get("day", "")
    metrics = CopilotDayMetrics(
        date=day,
        total_active_users=record.get("total_active_users", 0),
        total_engaged_users=record.get("total_engaged_users", 0),
        raw=record,
    )

    if "copilot_ide_code_completions" in record:
        metrics.copilot_ide_code_completions = IdeCompletionMetrics(
            **record["copilot_ide_code_completions"]
        )
    if "copilot_ide_chat" in record:
        metrics.copilot_ide_chat = IdeChatMetrics(**record["copilot_ide_chat"])
    if "copilot_dotcom_chat" in record:
        metrics.copilot_dotcom_chat = DotcomChatMetrics(**record["copilot_dotcom_chat"])
    if "copilot_dotcom_pull_requests" in record:
        metrics.copilot_dotcom_pull_requests = PullRequestMetrics(
            **record["copilot_dotcom_pull_requests"]
        )
    if "copilot_cli" in record or "totals_by_cli" in record:
        cli_data = record.get("copilot_cli") or record.get("totals_by_cli", {})
        metrics.copilot_cli = CliMetrics(**cli_data)
    if "code_generation" in record:
        metrics.code_generation = CodeGenerationMetrics(**record["code_generation"])

    return metrics


def _parse_user_record(record: dict[str, Any]) -> UserUsageRecord:
    """Parse a single NDJSON user record into UserUsageRecord."""
    return UserUsageRecord(
        github_login=record.get("github_login", record.get("login", "")),
        team_slug=record.get("team_slug"),
        date=record.get("date") or record.get("day"),
        completions_suggestions=record.get("completions_suggestions", 0),
        completions_acceptances=record.get("completions_acceptances", 0),
        completions_lines_suggested=record.get("completions_lines_suggested", 0),
        completions_lines_accepted=record.get("completions_lines_accepted", 0),
        chat_turns=record.get("chat_turns", 0),
        chat_insertion_events=record.get("chat_insertion_events", 0),
        chat_copy_events=record.get("chat_copy_events", 0),
        agent_turns=record.get("agent_turns", 0),
        cli_turns=record.get("cli_turns", 0),
        editors=record.get("editors", []),
        languages=record.get("languages", []),
        models_used=record.get("models_used", []),
        raw=record,
    )


class UsageMetricsAPI:
    """Client for the new Copilot Usage Metrics API (GA).

    Args:
        client: Configured GitHubBaseClient instance.
    """

    def __init__(self, client: GitHubBaseClient) -> None:
        self._client = client

    # ------------------------------------------------------------------
    # Enterprise-level
    # ------------------------------------------------------------------

    async def get_enterprise_metrics(
        self, enterprise: str, *, day: str | None = None, period: str = "28-day"
    ) -> list[CopilotDayMetrics]:
        """Fetch enterprise-level aggregated metrics.

        Args:
            enterprise: Enterprise slug.
            day: Specific date (YYYY-MM-DD) for 1-day reports.
            period: '1-day' or '28-day'.

        Returns:
            List of CopilotDayMetrics.
        """
        if period == "1-day" and day:
            path = f"/enterprises/{enterprise}/copilot/metrics/reports/enterprise-1-day"
            params = {"day": day}
        else:
            path = f"/enterprises/{enterprise}/copilot/metrics/reports/enterprise-28-day/latest"
            params = None

        return await self._fetch_report(path, params, _parse_org_day_record)

    async def get_enterprise_user_metrics(
        self, enterprise: str, *, day: str | None = None, period: str = "28-day"
    ) -> list[UserUsageRecord]:
        """Fetch enterprise-level per-user metrics.

        Args:
            enterprise: Enterprise slug.
            day: Specific date (YYYY-MM-DD) for 1-day reports.
            period: '1-day' or '28-day'.

        Returns:
            List of UserUsageRecord.
        """
        if period == "1-day" and day:
            path = f"/enterprises/{enterprise}/copilot/metrics/reports/users-1-day"
            params = {"day": day}
        else:
            path = f"/enterprises/{enterprise}/copilot/metrics/reports/users-28-day/latest"
            params = None

        return await self._fetch_report(path, params, _parse_user_record)

    # ------------------------------------------------------------------
    # Organization-level
    # ------------------------------------------------------------------

    async def get_org_metrics(
        self, org: str, *, day: str | None = None, period: str = "28-day"
    ) -> list[CopilotDayMetrics]:
        """Fetch organization-level aggregated metrics.

        Args:
            org: Organization name.
            day: Specific date (YYYY-MM-DD) for 1-day reports.
            period: '1-day' or '28-day'.

        Returns:
            List of CopilotDayMetrics.
        """
        if period == "1-day" and day:
            path = f"/orgs/{org}/copilot/metrics/reports/organization-1-day"
            params = {"day": day}
        else:
            path = f"/orgs/{org}/copilot/metrics/reports/organization-28-day/latest"
            params = None

        return await self._fetch_report(path, params, _parse_org_day_record)

    async def get_org_user_metrics(
        self, org: str, *, day: str | None = None, period: str = "28-day"
    ) -> list[UserUsageRecord]:
        """Fetch organization-level per-user metrics.

        Args:
            org: Organization name.
            day: Specific date (YYYY-MM-DD) for 1-day reports.
            period: '1-day' or '28-day'.

        Returns:
            List of UserUsageRecord.
        """
        if period == "1-day" and day:
            path = f"/orgs/{org}/copilot/metrics/reports/users-1-day"
            params = {"day": day}
        else:
            path = f"/orgs/{org}/copilot/metrics/reports/users-28-day/latest"
            params = None

        return await self._fetch_report(path, params, _parse_user_record)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _fetch_report(self, path: str, params: dict | None, parser) -> list:
        """Fetch a report endpoint, download NDJSON, and parse records.

        Args:
            path: API path.
            params: Query params.
            parser: Callable to parse each NDJSON record.

        Returns:
            List of parsed model instances.
        """
        resp = await self._client.get(path, params=params)
        download_resp = ReportDownloadResponse(**resp.json())

        all_records: list = []
        for url in download_resp.download_links:
            raw_records = await self._client.download_ndjson(url)
            for record in raw_records:
                all_records.append(parser(record))

        logger.info(
            "Fetched %d records from %s (%d download links)",
            len(all_records),
            path,
            len(download_resp.download_links),
        )
        return all_records
