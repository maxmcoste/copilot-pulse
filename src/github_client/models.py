"""Pydantic v2 models for GitHub Copilot API response payloads."""

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared / building-block models
# ---------------------------------------------------------------------------

class ModelStats(BaseModel):
    """Stats broken down by AI model."""
    name: str = ""
    is_custom_model: bool = False
    custom_model_training_date: Optional[str] = None
    total_engaged_users: int = 0
    # Completions-specific
    total_code_suggestions: int = 0
    total_code_acceptances: int = 0
    total_code_lines_suggested: int = 0
    total_code_lines_accepted: int = 0
    # Chat-specific
    total_chats: int = 0
    total_chat_insertion_events: int = 0
    total_chat_copy_events: int = 0


class EditorBreakdown(BaseModel):
    """Breakdown of metrics per IDE/editor."""
    name: str = ""
    total_engaged_users: int = 0
    models: list[ModelStats] = Field(default_factory=list)


class LanguageBreakdown(BaseModel):
    """Breakdown of metrics per programming language."""
    name: str = ""
    total_engaged_users: int = 0
    total_code_suggestions: int = 0
    total_code_acceptances: int = 0
    total_code_lines_suggested: int = 0
    total_code_lines_accepted: int = 0


# ---------------------------------------------------------------------------
# IDE Code Completions
# ---------------------------------------------------------------------------

class IdeCompletionMetrics(BaseModel):
    """Metrics for Copilot IDE code completions."""
    total_engaged_users: int = 0
    total_code_suggestions: int = 0
    total_code_acceptances: int = 0
    total_code_lines_suggested: int = 0
    total_code_lines_accepted: int = 0
    editors: list[EditorBreakdown] = Field(default_factory=list)
    languages: list[LanguageBreakdown] = Field(default_factory=list)

    @property
    def acceptance_rate(self) -> float:
        """Calculate suggestion acceptance rate as a percentage."""
        if self.total_code_suggestions == 0:
            return 0.0
        return round(self.total_code_acceptances / self.total_code_suggestions * 100, 1)


# ---------------------------------------------------------------------------
# IDE Chat
# ---------------------------------------------------------------------------

class IdeChatMetrics(BaseModel):
    """Metrics for Copilot IDE chat."""
    total_engaged_users: int = 0
    total_chats: int = 0
    total_chat_insertion_events: int = 0
    total_chat_copy_events: int = 0
    editors: list[EditorBreakdown] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# GitHub.com Chat
# ---------------------------------------------------------------------------

class DotcomChatMetrics(BaseModel):
    """Metrics for Copilot chat on GitHub.com."""
    total_engaged_users: int = 0
    total_chats: int = 0
    models: list[ModelStats] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# CLI Metrics
# ---------------------------------------------------------------------------

class CliMetrics(BaseModel):
    """Metrics for Copilot CLI usage."""
    total_engaged_users: int = 0
    total_chats: int = 0
    models: list[ModelStats] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Pull Request Metrics
# ---------------------------------------------------------------------------

class PullRequestMetrics(BaseModel):
    """Metrics for Copilot pull request features."""
    total_engaged_users: int = 0
    total_pr_summaries_created: int = 0
    repositories: list[dict[str, Any]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Code Generation (LoC) Metrics
# ---------------------------------------------------------------------------

class CodeGenerationMetrics(BaseModel):
    """Lines of code metrics attributed to Copilot."""
    total_code_lines_suggested: int = 0
    total_code_lines_accepted: int = 0
    total_code_lines_added: int = 0
    total_code_lines_deleted: int = 0


# ---------------------------------------------------------------------------
# Aggregated Day Metrics (Legacy API format + new API flattened)
# ---------------------------------------------------------------------------

class CopilotDayMetrics(BaseModel):
    """Aggregated Copilot metrics for a single day."""
    date: date
    total_active_users: int = 0
    total_engaged_users: int = 0
    copilot_ide_code_completions: Optional[IdeCompletionMetrics] = None
    copilot_ide_chat: Optional[IdeChatMetrics] = None
    copilot_dotcom_chat: Optional[DotcomChatMetrics] = None
    copilot_dotcom_pull_requests: Optional[PullRequestMetrics] = None
    copilot_cli: Optional[CliMetrics] = None
    code_generation: Optional[CodeGenerationMetrics] = None

    # Raw data preserved for custom analysis
    raw: dict[str, Any] = Field(default_factory=dict, exclude=True)


# ---------------------------------------------------------------------------
# User-level Usage Record (new Usage Metrics API)
# ---------------------------------------------------------------------------

class UserUsageRecord(BaseModel):
    """Per-user Copilot usage record from the Usage Metrics API."""
    github_login: str = ""
    team_slug: Optional[str] = None
    date: Optional[date] = None

    # Completions
    completions_suggestions: int = 0
    completions_acceptances: int = 0
    completions_lines_suggested: int = 0
    completions_lines_accepted: int = 0

    # Chat
    chat_turns: int = 0
    chat_insertion_events: int = 0
    chat_copy_events: int = 0

    # Agent / CLI
    agent_turns: int = 0
    cli_turns: int = 0

    # Editors & languages used
    editors: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    models_used: list[str] = Field(default_factory=list)

    # Raw NDJSON record
    raw: dict[str, Any] = Field(default_factory=dict, exclude=True)


# ---------------------------------------------------------------------------
# Seat / Billing
# ---------------------------------------------------------------------------

class SeatAssignment(BaseModel):
    """Individual seat assignment within an organization."""
    login: str = ""
    assigned_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None
    last_activity_editor: Optional[str] = None
    plan_type: str = ""
    pending_cancellation_date: Optional[str] = None


class SeatInfo(BaseModel):
    """Copilot billing / seat information for an organization."""
    seat_breakdown: dict[str, int] = Field(default_factory=dict)
    total_seats: int = 0
    seats: list[SeatAssignment] = Field(default_factory=list)

    @property
    def active_seats(self) -> int:
        return self.seat_breakdown.get("active_this_cycle", 0)

    @property
    def inactive_seats(self) -> int:
        return self.seat_breakdown.get("inactive_this_cycle", 0)

    @property
    def added_this_cycle(self) -> int:
        return self.seat_breakdown.get("added_this_cycle", 0)


# ---------------------------------------------------------------------------
# Download link wrapper (new API)
# ---------------------------------------------------------------------------

class ReportDownloadResponse(BaseModel):
    """Response from the new Usage Metrics API report endpoints."""
    download_links: list[str] = Field(default_factory=list)
    report_day: str = ""
