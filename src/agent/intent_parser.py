"""Parse user intent from natural language queries."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class IntentCategory(Enum):
    """High-level categories of user intent."""

    METRICS_QUERY = "metrics_query"
    USER_ANALYSIS = "user_analysis"
    TEAM_COMPARISON = "team_comparison"
    TREND_ANALYSIS = "trend_analysis"
    SEAT_MANAGEMENT = "seat_management"
    EXPORT_REPORT = "export_report"
    CHART_REQUEST = "chart_request"
    GENERAL_QUESTION = "general_question"


@dataclass
class ParsedIntent:
    """Result of parsing a user's natural language query."""

    category: IntentCategory
    entities: dict[str, str] = field(default_factory=dict)
    time_range: str | None = None
    export_format: str | None = None
    keywords: list[str] = field(default_factory=list)


# Patterns for local pre-processing (supplements Claude's understanding)
_DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")
_PERIOD_PATTERNS = {
    "oggi": "1-day",
    "today": "1-day",
    "ieri": "1-day",
    "yesterday": "1-day",
    "settimana": "28-day",
    "week": "28-day",
    "mese": "28-day",
    "month": "28-day",
    "28 giorni": "28-day",
    "28 days": "28-day",
    "ultimo mese": "28-day",
    "last month": "28-day",
}

_EXPORT_PATTERNS = {
    "csv": "csv",
    "excel": "excel",
    "xlsx": "excel",
    "pdf": "pdf",
}


def parse_intent(query: str) -> ParsedIntent:
    """Pre-parse a user query to extract structured hints.

    This is a lightweight local parser that extracts obvious entities
    before sending to Claude. Claude does the heavy lifting for intent
    classification via tool selection.

    Args:
        query: Raw user input string.

    Returns:
        ParsedIntent with extracted entities and hints.
    """
    query_lower = query.lower()
    entities: dict[str, str] = {}
    keywords: list[str] = []

    # Extract explicit dates
    date_match = _DATE_PATTERN.search(query)
    if date_match:
        entities["day"] = date_match.group()

    # Detect time period
    time_range = None
    for pattern, period in _PERIOD_PATTERNS.items():
        if pattern in query_lower:
            time_range = period
            break

    # Detect export format
    export_format = None
    for pattern, fmt in _EXPORT_PATTERNS.items():
        if pattern in query_lower:
            export_format = fmt
            break

    # Detect category hints
    category = IntentCategory.GENERAL_QUESTION

    if any(w in query_lower for w in ["seat", "licenz", "billing", "assegnat"]):
        category = IntentCategory.SEAT_MANAGEMENT
    elif any(w in query_lower for w in ["export", "esport", "report", "scarica"]):
        category = IntentCategory.EXPORT_REPORT
    elif any(w in query_lower for w in ["grafico", "chart", "mostra", "visualizza", "trend"]):
        category = IntentCategory.CHART_REQUEST
        if "trend" in query_lower:
            category = IntentCategory.TREND_ANALYSIS
    elif any(w in query_lower for w in ["team", "confronta", "compare"]):
        category = IntentCategory.TEAM_COMPARISON
    elif any(
        w in query_lower
        for w in [
            "metrich", "metric", "acceptance", "utilizzo", "usage",
            "attiv", "active", "engaged", "quant",
        ]
    ):
        category = IntentCategory.METRICS_QUERY
    elif any(w in query_lower for w in ["utent", "user", "top", "inattiv", "inactive"]):
        category = IntentCategory.USER_ANALYSIS

    # Extract keyword hints
    for word in ["completion", "chat", "cli", "pr", "pull request", "agent"]:
        if word in query_lower:
            keywords.append(word)

    return ParsedIntent(
        category=category,
        entities=entities,
        time_range=time_range,
        export_format=export_format,
        keywords=keywords,
    )
