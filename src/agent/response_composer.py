"""Compose rich terminal responses from agent outputs."""

from __future__ import annotations

import logging
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

logger = logging.getLogger(__name__)


class ResponseComposer:
    """Composes Rich-formatted terminal output from agent results.

    Args:
        console: Rich Console instance for output.
    """

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()

    def display_text(self, text: str) -> None:
        """Display a text response with markdown-like formatting."""
        self.console.print()
        self.console.print(Panel(text, border_style="cyan", padding=(1, 2)))
        self.console.print()

    def display_table(self, title: str, headers: list[str], rows: list[list[Any]]) -> None:
        """Display data as a Rich table.

        Args:
            title: Table title.
            headers: Column header names.
            rows: List of row data.
        """
        table = Table(title=title, show_lines=True)
        for header in headers:
            table.add_column(header, style="cyan")

        for row in rows:
            table.add_row(*[str(v) for v in row])

        self.console.print(table)

    def display_analysis(self, result: dict[str, Any]) -> None:
        """Display analysis results with appropriate formatting.

        Args:
            result: Analysis result dict from DataAnalyzer.
        """
        analysis_type = result.get("type", "unknown")

        match analysis_type:
            case "adoption_trend":
                self._display_adoption_trend(result)
            case "top_users":
                self._display_top_users(result)
            case "engagement_breakdown":
                self._display_engagement_breakdown(result)
            case "inactive_users":
                self._display_inactive_users(result)
            case "acceptance_rate_by_language":
                self._display_acceptance_by_language(result)
            case "feature_usage_distribution":
                self._display_feature_distribution(result)
            case "loc_impact":
                self._display_loc_impact(result)
            case "org_summary":
                self._display_org_summary(result)
            case "org_copilot_analysis":
                self._display_org_copilot_analysis(result)
            case _:
                # Generic JSON display
                import json
                self.console.print_json(json.dumps(result, default=str))

    def _display_adoption_trend(self, result: dict[str, Any]) -> None:
        summary = result.get("summary", {})
        dates = result.get("dates", [])
        active = result.get("active_users", [])

        panel_text = (
            f"📈 Avg Daily Active: [bold green]{summary.get('avg_daily_active', 0)}[/]\n"
            f"👥 Avg Daily Engaged: [bold blue]{summary.get('avg_daily_engaged', 0)}[/]\n"
            f"🏔  Peak Active: [bold yellow]{summary.get('peak_active', 0)}[/]\n"
            f"📅 Period: {summary.get('period_days', 0)} days\n"
            f"📊 Trend: {'↑ Up' if summary.get('trend_direction') == 'up' else '↓ Down'}"
        )
        self.console.print(Panel(panel_text, title="Adoption Trend", border_style="green"))

        # Simple ASCII sparkline
        if active:
            max_val = max(active) or 1
            bar_width = 40
            self.console.print("\n[bold]Daily Active Users:[/]")
            for i, (d, v) in enumerate(zip(dates, active)):
                bar_len = int(v / max_val * bar_width)
                bar = "█" * bar_len
                label = d[-5:]  # MM-DD
                color = "green" if i == len(active) - 1 else "cyan"
                self.console.print(f"  {label} [{color}]{bar}[/] {v}")

    def _display_top_users(self, result: dict[str, Any]) -> None:
        users = result.get("users", [])
        table = Table(title=f"Top {len(users)} Users", show_lines=True)
        table.add_column("#", style="dim", width=4)
        table.add_column("User", style="cyan")
        table.add_column("Completions", justify="right", style="green")
        table.add_column("Chat Turns", justify="right", style="blue")
        table.add_column("Lines Accepted", justify="right", style="yellow")
        table.add_column("Total Activity", justify="right", style="bold")

        for i, user in enumerate(users, 1):
            table.add_row(
                str(i),
                user["login"],
                str(user["completions"]),
                str(user["chat_turns"]),
                str(user["lines_accepted"]),
                str(user["total_activity"]),
            )

        self.console.print(table)
        self.console.print(
            f"\n[dim]Analyzed {result.get('total_users_analyzed', 0)} total users[/]"
        )

    def _display_engagement_breakdown(self, result: dict[str, Any]) -> None:
        features = result.get("features", {})
        table = Table(title="Feature Engagement (avg daily users)", show_lines=True)
        table.add_column("Feature", style="cyan")
        table.add_column("Avg Daily Users", justify="right", style="green")

        for feature, avg in sorted(features.items(), key=lambda x: x[1], reverse=True):
            table.add_row(feature, str(avg))

        self.console.print(table)

    def _display_inactive_users(self, result: dict[str, Any]) -> None:
        panel_text = (
            f"📋 Total Seats: [bold]{result.get('total_seats', 0)}[/]\n"
            f"😴 Inactive (never used): [bold red]{result.get('inactive_count', 0)}[/]\n"
            f"✅ Utilization Rate: [bold green]{result.get('utilization_rate', 0)}%[/]"
        )
        self.console.print(Panel(panel_text, title="Seat Utilization", border_style="yellow"))

    def _display_acceptance_by_language(self, result: dict[str, Any]) -> None:
        languages = result.get("languages", {})
        table = Table(title="Acceptance Rate by Language", show_lines=True)
        table.add_column("Language", style="cyan")
        table.add_column("Rate", justify="right")
        table.add_column("Suggestions", justify="right", style="dim")
        table.add_column("Accepted", justify="right", style="dim")

        for lang, stats in list(languages.items())[:20]:
            rate = stats["acceptance_rate"]
            rate_style = "green" if rate >= 30 else "yellow" if rate >= 20 else "red"
            table.add_row(
                lang,
                f"[{rate_style}]{rate}%[/]",
                str(stats["total_suggestions"]),
                str(stats["total_acceptances"]),
            )

        self.console.print(table)

    def _display_feature_distribution(self, result: dict[str, Any]) -> None:
        percentages = result.get("percentages", {})
        distribution = result.get("distribution", {})
        self.console.print(
            Panel(
                f"[dim]Date: {result.get('date', 'N/A')}[/]",
                title="Feature Usage Distribution",
                border_style="blue",
            )
        )

        max_val = max(distribution.values()) if distribution else 1
        bar_width = 30
        for feature, count in sorted(distribution.items(), key=lambda x: x[1], reverse=True):
            bar_len = int(count / max_val * bar_width)
            bar = "█" * bar_len
            pct = percentages.get(feature, 0)
            self.console.print(f"  {feature:<20} [cyan]{bar}[/] {count} ({pct}%)")

    def _display_loc_impact(self, result: dict[str, Any]) -> None:
        panel_text = (
            f"📝 Lines Suggested: [bold]{result.get('total_lines_suggested', 0):,}[/]\n"
            f"✅ Lines Accepted: [bold green]{result.get('total_lines_accepted', 0):,}[/]\n"
            f"📊 Line Acceptance Rate: [bold cyan]{result.get('line_acceptance_rate', 0)}%[/]\n"
            f"📅 Period: {result.get('period_days', 0)} days"
        )
        self.console.print(Panel(panel_text, title="Lines of Code Impact", border_style="green"))

    def _display_org_summary(self, result: dict[str, Any]) -> None:
        panel_text = (
            f"Total employees: [bold]{result.get('total_employees', 0)}[/]\n"
            f"With GitHub ID: [bold green]{result.get('with_github_id', 0)}[/]"
        )
        self.console.print(Panel(panel_text, title="Org Structure Summary", border_style="blue"))

        # Age ranges
        age_ranges = result.get("age_ranges", {})
        if age_ranges:
            table = Table(title="Employees by Age Range", show_lines=True)
            table.add_column("Age Range", style="cyan")
            table.add_column("Count", justify="right", style="green")
            for age_range, count in age_ranges.items():
                table.add_row(age_range, str(count))
            self.console.print(table)

        # Top job families
        job_families = result.get("job_families", {})
        if job_families:
            table = Table(title="Top Job Families", show_lines=True)
            table.add_column("Job Family", style="cyan")
            table.add_column("Count", justify="right", style="green")
            for jf, count in list(job_families.items())[:10]:
                table.add_row(jf, str(count))
            self.console.print(table)

        # Sup Org Level 6
        sup_org = result.get("sup_org_level_6", {})
        if sup_org:
            table = Table(title="Sup Org Level 6", show_lines=True)
            table.add_column("Organization", style="cyan")
            table.add_column("Count", justify="right", style="green")
            for org, count in list(sup_org.items())[:15]:
                table.add_row(org, str(count))
            self.console.print(table)

    def _display_org_copilot_analysis(self, result: dict[str, Any]) -> None:
        group_by = result.get("group_by", "")
        metric = result.get("metric", "active_users")
        groups = result.get("groups", {})
        filter_info = result.get("filter", "")

        title = f"Copilot {metric.replace('_', ' ').title()} by {group_by.replace('_', ' ').title()}"
        if filter_info:
            title += f" (filtered: {filter_info})"

        table = Table(title=title, show_lines=True)
        table.add_column(group_by.replace("_", " ").title(), style="cyan")
        table.add_column(metric.replace("_", " ").title(), justify="right", style="green")

        for group_name, value in groups.items():
            display_val = f"{value}%" if metric == "acceptance_rate" else str(value)
            table.add_row(group_name, display_val)

        self.console.print(table)
        self.console.print(
            f"\n[dim]Matched: {result.get('matched_users', 0)} / "
            f"{result.get('total_enriched_users', 0)} users with org data[/]"
        )

        # Also render as bar chart
        if groups:
            max_val = max(groups.values()) if groups.values() else 1
            bar_width = 35
            self.console.print()
            for name, value in groups.items():
                bar_len = int(value / max_val * bar_width) if max_val else 0
                bar = "█" * bar_len
                self.console.print(f"  {name:<35} [cyan]{bar}[/] {value}")

    def display_error(self, message: str) -> None:
        """Display an error message."""
        self.console.print(Panel(f"[bold red]Error:[/] {message}", border_style="red"))

    def display_status(self, message: str) -> None:
        """Display a status/info message."""
        self.console.print(f"[dim]{message}[/]")
