"""Copilot Usage Metrics API (new, GA) — primary data source.

These endpoints use X-GitHub-Api-Version: 2026-03-10 and return NDJSON download links.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from .base_client import GitHubBaseClient
from .models import (
    CopilotDayMetrics,
    ReportDownloadResponse,
    UserUsageRecord,
)

logger = logging.getLogger(__name__)


def _default_day() -> str:
    """Return the most recent day likely to have metrics (today − 2 business days).

    GitHub Copilot metrics have a ~2 business-day delay, so requesting
    "today" would return no data.
    """
    return (date.today() - timedelta(days=2)).isoformat()


def _parse_org_day_record(record: dict[str, Any]) -> CopilotDayMetrics:
    """Parse a single NDJSON day record into CopilotDayMetrics.

    Handles both the legacy API format and the new GA Usage Metrics API
    format (fields like ``daily_active_users``, ``totals_by_ide``,
    ``totals_by_feature``, etc.).
    """
    from .models import (
        CliMetrics,
        CodeGenerationMetrics,
        DotcomChatMetrics,
        IdeChatMetrics,
        IdeCompletionMetrics,
        PullRequestMetrics,
    )

    day = record.get("date") or record.get("day", "")

    # -- active / engaged users -------------------------------------------
    total_active = (
        record.get("total_active_users")
        or record.get("daily_active_users", 0)
    )
    total_engaged = (
        record.get("total_engaged_users")
        or record.get("monthly_active_users", 0)
    )

    metrics = CopilotDayMetrics(
        date=day,
        total_active_users=total_active,
        total_engaged_users=total_engaged,
        raw=record,
    )

    # -- IDE completions --------------------------------------------------
    if "copilot_ide_code_completions" in record:
        metrics.copilot_ide_code_completions = IdeCompletionMetrics(
            **record["copilot_ide_code_completions"]
        )
    elif "totals_by_feature" in record:
        # Build from the GA totals_by_feature array.
        completions = [
            f for f in record["totals_by_feature"]
            if f.get("feature") == "code_completion"
        ]
        if completions:
            c = completions[0]
            # Build editor and language breakdowns from totals_by_ide
            editors = [
                {"name": e.get("ide", ""), "total_engaged_users": 0}
                for e in record.get("totals_by_ide", [])
            ]
            langs = [
                {
                    "name": lf.get("language", ""),
                    "total_code_suggestions": lf.get("code_generation_activity_count", 0),
                    "total_code_acceptances": lf.get("code_acceptance_activity_count", 0),
                }
                for lf in record.get("totals_by_language_feature", [])
            ]
            metrics.copilot_ide_code_completions = IdeCompletionMetrics(
                total_code_suggestions=c.get("code_generation_activity_count", 0),
                total_code_acceptances=c.get("code_acceptance_activity_count", 0),
                total_code_lines_suggested=c.get("loc_suggested_to_add_sum", 0),
                total_code_lines_accepted=c.get("loc_added_sum", 0),
                editors=editors,
                languages=langs,
            )

    # -- IDE chat ---------------------------------------------------------
    if "copilot_ide_chat" in record:
        metrics.copilot_ide_chat = IdeChatMetrics(**record["copilot_ide_chat"])
    elif "totals_by_feature" in record:
        chats = [
            f for f in record["totals_by_feature"]
            if f.get("feature") in ("chat", "ide_chat")
        ]
        if chats:
            c = chats[0]
            metrics.copilot_ide_chat = IdeChatMetrics(
                total_engaged_users=record.get("monthly_active_chat_users", 0),
                total_chats=c.get("user_initiated_interaction_count", 0),
            )

    # -- Dotcom chat (same for GA) ----------------------------------------
    if "copilot_dotcom_chat" in record:
        metrics.copilot_dotcom_chat = DotcomChatMetrics(**record["copilot_dotcom_chat"])

    # -- Pull requests ----------------------------------------------------
    if "copilot_dotcom_pull_requests" in record:
        metrics.copilot_dotcom_pull_requests = PullRequestMetrics(
            **record["copilot_dotcom_pull_requests"]
        )
    elif "pull_requests" in record:
        pr = record["pull_requests"]
        metrics.copilot_dotcom_pull_requests = PullRequestMetrics(
            total_pr_summaries_created=pr.get("total_created", 0),
        )

    # -- CLI --------------------------------------------------------------
    if "copilot_cli" in record:
        metrics.copilot_cli = CliMetrics(**record["copilot_cli"])
    elif "totals_by_cli" in record:
        cli = record["totals_by_cli"]
        metrics.copilot_cli = CliMetrics(
            total_engaged_users=record.get("daily_active_cli_users", 0),
        )

    # -- Code generation (LoC) --------------------------------------------
    if "code_generation" in record:
        metrics.code_generation = CodeGenerationMetrics(**record["code_generation"])
    elif "loc_added_sum" in record:
        metrics.code_generation = CodeGenerationMetrics(
            total_code_lines_suggested=record.get("loc_suggested_to_add_sum", 0),
            total_code_lines_accepted=record.get("loc_added_sum", 0) - record.get("loc_deleted_sum", 0),
            total_code_lines_added=record.get("loc_added_sum", 0),
            total_code_lines_deleted=record.get("loc_deleted_sum", 0),
        )

    return metrics


def _unwrap_day_totals(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Unwrap 28-day wrapper records that contain a ``day_totals`` array.

    The GA 28-day endpoints return a single NDJSON record per entity with
    the daily data nested in ``day_totals``. This helper flattens that into
    one record per day so the parser can process them uniformly.

    Parent-level fields (e.g. ``user_login``, ``team_slug``) are propagated
    into each child record so they are not lost during unwrapping.
    """
    # Fields to carry from the parent wrapper into each day record
    _PROPAGATE = {"user_login", "github_login", "login", "team_slug"}

    unwrapped: list[dict[str, Any]] = []
    for rec in records:
        if "day_totals" in rec and isinstance(rec["day_totals"], list):
            parent_fields = {k: v for k, v in rec.items() if k in _PROPAGATE and v}
            for day_rec in rec["day_totals"]:
                merged = {**parent_fields, **day_rec}
                unwrapped.append(merged)
        else:
            unwrapped.append(rec)
    return unwrapped


def _parse_user_record(record: dict[str, Any]) -> UserUsageRecord:
    """Parse a single NDJSON user record into UserUsageRecord.

    Supports both the legacy field names (``github_login``,
    ``completions_suggestions``, …) and the GA Usage Metrics API names
    (``user_login``, ``code_generation_activity_count``, ``totals_by_*``).
    """
    login = (
        record.get("github_login")
        or record.get("user_login")
        or record.get("login", "")
    )
    day = record.get("date") or record.get("day")

    # -- Completions / suggestions ----------------------------------------
    completions_suggestions = record.get("completions_suggestions", 0)
    completions_acceptances = record.get("completions_acceptances", 0)
    completions_lines_suggested = record.get("completions_lines_suggested", 0)
    completions_lines_accepted = record.get("completions_lines_accepted", 0)

    # GA format: aggregate from totals_by_feature
    if not completions_suggestions and "totals_by_feature" in record:
        for feat in record["totals_by_feature"]:
            if feat.get("feature") == "code_completion":
                completions_suggestions += feat.get("code_generation_activity_count", 0)
                completions_acceptances += feat.get("code_acceptance_activity_count", 0)
                completions_lines_suggested += feat.get("loc_suggested_to_add_sum", 0)
                completions_lines_accepted += feat.get("loc_added_sum", 0)
    # Fallback to top-level GA fields
    if not completions_suggestions:
        completions_suggestions = record.get("code_generation_activity_count", 0)
        completions_acceptances = record.get("code_acceptance_activity_count", 0)
        completions_lines_suggested = record.get("loc_suggested_to_add_sum", 0)
        completions_lines_accepted = record.get("loc_added_sum", 0)

    # -- Chat -------------------------------------------------------------
    chat_turns = record.get("chat_turns", 0)
    if not chat_turns and "totals_by_feature" in record:
        for feat in record["totals_by_feature"]:
            if "chat" in feat.get("feature", ""):
                chat_turns += feat.get("user_initiated_interaction_count", 0)
    if not chat_turns:
        chat_turns = record.get("user_initiated_interaction_count", 0)

    # -- Editors & languages from GA arrays -------------------------------
    editors = record.get("editors", [])
    languages = record.get("languages", [])
    models_used = record.get("models_used", [])

    if not editors and "totals_by_ide" in record:
        editors = list({e.get("ide", "") for e in record["totals_by_ide"] if e.get("ide")})
    if not languages and "totals_by_language_feature" in record:
        languages = list({
            lf.get("language", "")
            for lf in record["totals_by_language_feature"]
            if lf.get("language")
        })
    if not models_used and "totals_by_model_feature" in record:
        models_used = list({
            mf.get("model", "")
            for mf in record["totals_by_model_feature"]
            if mf.get("model")
        })

    return UserUsageRecord(
        github_login=login,
        team_slug=record.get("team_slug"),
        date=day,
        completions_suggestions=completions_suggestions,
        completions_acceptances=completions_acceptances,
        completions_lines_suggested=completions_lines_suggested,
        completions_lines_accepted=completions_lines_accepted,
        chat_turns=chat_turns,
        chat_insertion_events=record.get("chat_insertion_events", 0),
        chat_copy_events=record.get("chat_copy_events", 0),
        agent_turns=record.get("agent_turns", 0),
        cli_turns=record.get("cli_turns", 0),
        editors=editors,
        languages=languages,
        models_used=models_used,
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
            day: Specific date (YYYY-MM-DD) for 1-day reports. If *period*
                 is ``'1-day'`` and *day* is ``None`` the most recent
                 available day (today - 2) is used automatically.
            period: '1-day' or '28-day'.

        Returns:
            List of CopilotDayMetrics.
        """
        if period == "1-day":
            day = day or _default_day()
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
            day: Specific date (YYYY-MM-DD) for 1-day reports. If *period*
                 is ``'1-day'`` and *day* is ``None`` the most recent
                 available day (today - 2) is used automatically.
            period: '1-day' or '28-day'.

        Returns:
            List of UserUsageRecord.
        """
        if period == "1-day":
            day = day or _default_day()
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
            day: Specific date (YYYY-MM-DD) for 1-day reports. If *period*
                 is ``'1-day'`` and *day* is ``None`` the most recent
                 available day (today - 2) is used automatically.
            period: '1-day' or '28-day'.

        Returns:
            List of CopilotDayMetrics.
        """
        if period == "1-day":
            day = day or _default_day()
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
            day: Specific date (YYYY-MM-DD) for 1-day reports. If *period*
                 is ``'1-day'`` and *day* is ``None`` the most recent
                 available day (today - 2) is used automatically.
            period: '1-day' or '28-day'.

        Returns:
            List of UserUsageRecord.
        """
        if period == "1-day":
            day = day or _default_day()
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
            # 28-day reports wrap daily data inside a "day_totals" array;
            # unwrap so the parser receives one record per day.
            raw_records = _unwrap_day_totals(raw_records)
            for record in raw_records:
                all_records.append(parser(record))

        logger.info(
            "Fetched %d records from %s (%d download links)",
            len(all_records),
            path,
            len(download_resp.download_links),
        )
        return all_records
