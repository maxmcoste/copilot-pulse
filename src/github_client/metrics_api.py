"""Copilot Metrics API (legacy) — fallback data source.

DEPRECATED: These endpoints will be retired on 2026-04-02.
Use UsageMetricsAPI as the primary source.
"""

from __future__ import annotations

import logging
import warnings
from typing import Any

from .base_client import GitHubBaseClient
from .models import (
    CliMetrics,
    CodeGenerationMetrics,
    CopilotDayMetrics,
    DotcomChatMetrics,
    IdeChatMetrics,
    IdeCompletionMetrics,
    PullRequestMetrics,
)

logger = logging.getLogger(__name__)

_DEPRECATION_MSG = (
    "The legacy Copilot Metrics API will be retired on 2026-04-02. "
    "Migrate to UsageMetricsAPI (Copilot Usage Metrics API)."
)


def _parse_legacy_record(record: dict[str, Any]) -> CopilotDayMetrics:
    """Parse a single legacy API JSON record."""
    metrics = CopilotDayMetrics(
        date=record["date"],
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
    if "copilot_cli" in record:
        metrics.copilot_cli = CliMetrics(**record["copilot_cli"])
    if "code_generation" in record:
        metrics.code_generation = CodeGenerationMetrics(**record["code_generation"])

    return metrics


class LegacyMetricsAPI:
    """Client for the legacy Copilot Metrics API.

    .. deprecated::
        Will be retired 2026-04-02. Use UsageMetricsAPI instead.

    Args:
        client: Configured GitHubBaseClient instance.
    """

    def __init__(self, client: GitHubBaseClient) -> None:
        warnings.warn(_DEPRECATION_MSG, DeprecationWarning, stacklevel=2)
        self._client = client

    async def get_enterprise_metrics(
        self, enterprise: str, *, since: str | None = None, until: str | None = None
    ) -> list[CopilotDayMetrics]:
        """Fetch enterprise-level metrics (legacy).

        Args:
            enterprise: Enterprise slug.
            since: Start date YYYY-MM-DD.
            until: End date YYYY-MM-DD.

        Returns:
            List of CopilotDayMetrics.
        """
        params: dict[str, str] = {}
        if since:
            params["since"] = since
        if until:
            params["until"] = until

        resp = await self._client.get(
            f"/enterprises/{enterprise}/copilot/metrics", params=params
        )
        return [_parse_legacy_record(r) for r in resp.json()]

    async def get_org_metrics(
        self, org: str, *, since: str | None = None, until: str | None = None
    ) -> list[CopilotDayMetrics]:
        """Fetch organization-level metrics (legacy).

        Args:
            org: Organization name.
            since: Start date YYYY-MM-DD.
            until: End date YYYY-MM-DD.

        Returns:
            List of CopilotDayMetrics.
        """
        params: dict[str, str] = {}
        if since:
            params["since"] = since
        if until:
            params["until"] = until

        resp = await self._client.get(f"/orgs/{org}/copilot/metrics", params=params)
        return [_parse_legacy_record(r) for r in resp.json()]

    async def get_team_metrics(
        self,
        org: str,
        team_slug: str,
        *,
        since: str | None = None,
        until: str | None = None,
    ) -> list[CopilotDayMetrics]:
        """Fetch team-level metrics (legacy).

        Args:
            org: Organization name.
            team_slug: Team slug identifier.
            since: Start date YYYY-MM-DD.
            until: End date YYYY-MM-DD.

        Returns:
            List of CopilotDayMetrics.
        """
        params: dict[str, str] = {}
        if since:
            params["since"] = since
        if until:
            params["until"] = until

        resp = await self._client.get(
            f"/orgs/{org}/team/{team_slug}/copilot/metrics", params=params
        )
        return [_parse_legacy_record(r) for r in resp.json()]
