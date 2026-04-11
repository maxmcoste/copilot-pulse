"""Tests for the org data layer (loader, registry, models)."""

from __future__ import annotations

from datetime import date

import pytest

from src.orgdata.models import Employee
from src.orgdata.registry import UserRegistry
from src.github_client.models import UserUsageRecord


# ---------------------------------------------------------------------------
# Employee model tests
# ---------------------------------------------------------------------------

class TestEmployeeModel:

    def test_full_name(self) -> None:
        emp = Employee(name="MARIO", surname="ROSSI")
        assert emp.full_name == "MARIO ROSSI"

    def test_age_range_buckets(self) -> None:
        assert Employee(age=22).age_range == "<25"
        assert Employee(age=25).age_range == "25-29"
        assert Employee(age=30).age_range == "30-34"
        assert Employee(age=35).age_range == "35-39"
        assert Employee(age=40).age_range == "40-44"
        assert Employee(age=45).age_range == "45-49"
        assert Employee(age=50).age_range == "50-54"
        assert Employee(age=55).age_range == "55-59"
        assert Employee(age=62).age_range == "60+"
        assert Employee(age=None).age_range == "Unknown"

    def test_get_sup_org_level(self) -> None:
        emp = Employee(
            sup_org_level_5="ENG MODERNIZE",
            sup_org_level_6="BUSINESS SOLUTION",
        )
        assert emp.get_sup_org_level(5) == "ENG MODERNIZE"
        assert emp.get_sup_org_level(6) == "BUSINESS SOLUTION"
        assert emp.get_sup_org_level(10) == ""

    def test_org_path(self) -> None:
        emp = Employee(
            top_level_sup_org="GROUP",
            sup_org_level_2="ITALY",
            sup_org_level_3="SENIOR TEAM",
            sup_org_level_4="ENG DIGITAL",
            sup_org_level_5="",
        )
        assert emp.org_path() == ["GROUP", "ITALY", "SENIOR TEAM", "ENG DIGITAL"]

    def test_org_path_empty(self) -> None:
        emp = Employee()
        assert emp.org_path() == []


# ---------------------------------------------------------------------------
# UserRegistry tests
# ---------------------------------------------------------------------------

def _make_employees() -> list[Employee]:
    """Create a small test dataset of employees."""
    return [
        Employee(
            employee_id="E001", name="ALICE", surname="SMITH",
            github_id="alice-gh", age=28, gender="Female",
            job_family="Technical/ Development", location="Roma",
            sup_org_level_5="ENG MODERNIZE", sup_org_level_6="BUSINESS SOLUTION",
            email_work="alice@company.com",
        ),
        Employee(
            employee_id="E002", name="BOB", surname="JONES",
            github_id="bob-gh", age=42, gender="Male",
            job_family="Technical/ Development", location="Milano",
            sup_org_level_5="ENG MODERNIZE", sup_org_level_6="SOLUTION DELIVERY",
            email_work="bob@company.com",
        ),
        Employee(
            employee_id="E003", name="CHARLIE", surname="BROWN",
            github_id="charlie-gh", age=55, gender="Male",
            job_family="Consulting", location="Roma",
            sup_org_level_5="ENG MODERNIZE", sup_org_level_6="BUSINESS SOLUTION",
            email_work="charlie@company.com",
        ),
        Employee(
            employee_id="E004", name="DIANA", surname="ROSS",
            github_id=None, age=35, gender="Female",
            job_family="Operations", location="Napoli",
            sup_org_level_5="ENG MODERNIZE", sup_org_level_6="BUSINESS SOLUTION",
        ),
        Employee(
            employee_id="E005", name="EVE", surname="TAYLOR",
            github_id="eve-gh", age=31, gender="Female",
            job_family="Technical/ Development", location="Roma",
            sup_org_level_5="ENG MODERNIZE", sup_org_level_6="BUSINESS SOLUTION",
            email_work="eve@company.com",
        ),
    ]


def _make_usage_records() -> list[UserUsageRecord]:
    """Create test GitHub usage records matching some employees."""
    return [
        UserUsageRecord(
            github_login="alice-gh",
            completions_suggestions=200, completions_acceptances=80,
            completions_lines_suggested=300, completions_lines_accepted=120,
            chat_turns=15, agent_turns=2, cli_turns=3,
        ),
        UserUsageRecord(
            github_login="bob-gh",
            completions_suggestions=100, completions_acceptances=30,
            completions_lines_suggested=150, completions_lines_accepted=45,
            chat_turns=5, agent_turns=0, cli_turns=0,
        ),
        UserUsageRecord(
            github_login="charlie-gh",
            completions_suggestions=0, completions_acceptances=0,
            completions_lines_suggested=0, completions_lines_accepted=0,
            chat_turns=0, agent_turns=0, cli_turns=0,
        ),
        UserUsageRecord(
            github_login="unknown-user",
            completions_suggestions=50, completions_acceptances=20,
            completions_lines_suggested=75, completions_lines_accepted=30,
            chat_turns=8, agent_turns=1, cli_turns=0,
        ),
    ]


class TestUserRegistry:

    def test_init_counts(self) -> None:
        registry = UserRegistry(_make_employees())
        assert registry.total_employees == 5
        assert registry.employees_with_github == 4  # Diana has no github_id

    def test_lookup_by_github(self) -> None:
        registry = UserRegistry(_make_employees())
        emp = registry.lookup_by_github("alice-gh")
        assert emp is not None
        assert emp.name == "ALICE"

    def test_lookup_by_github_case_insensitive(self) -> None:
        registry = UserRegistry(_make_employees())
        emp = registry.lookup_by_github("ALICE-GH")
        assert emp is not None
        assert emp.name == "ALICE"

    def test_lookup_by_github_not_found(self) -> None:
        registry = UserRegistry(_make_employees())
        assert registry.lookup_by_github("nonexistent") is None

    def test_lookup_by_email(self) -> None:
        registry = UserRegistry(_make_employees())
        emp = registry.lookup_by_email("bob@company.com")
        assert emp is not None
        assert emp.name == "BOB"

    def test_enrich_users(self) -> None:
        registry = UserRegistry(_make_employees())
        users = _make_usage_records()
        enriched = registry.enrich_users(users)

        assert len(enriched) == 4

        # Alice should be matched
        alice = next(r for r in enriched if r["github_login"] == "alice-gh")
        assert alice["org_matched"] is True
        assert alice["full_name"] == "ALICE SMITH"
        assert alice["age"] == 28
        assert alice["age_range"] == "25-29"
        assert alice["sup_org_level_6"] == "BUSINESS SOLUTION"
        assert alice["total_activity"] == 100  # 80 + 15 + 2 + 3

        # Unknown user should be unmatched
        unknown = next(r for r in enriched if r["github_login"] == "unknown-user")
        assert unknown["org_matched"] is False
        assert unknown["full_name"] is None
        assert unknown["age_range"] is None

    def test_enrich_matched_count(self) -> None:
        registry = UserRegistry(_make_employees())
        users = _make_usage_records()
        enriched = registry.enrich_users(users)

        matched = sum(1 for r in enriched if r["org_matched"])
        unmatched = sum(1 for r in enriched if not r["org_matched"])
        assert matched == 3  # alice, bob, charlie
        assert unmatched == 1  # unknown-user

    def test_group_by_age_range(self) -> None:
        registry = UserRegistry(_make_employees())
        groups = registry.group_by("age_range")
        assert "25-29" in groups  # Alice (28)
        assert "40-44" in groups  # Bob (42)
        assert "55-59" in groups  # Charlie (55)
        assert len(groups["25-29"]) == 1

    def test_group_by_job_family(self) -> None:
        registry = UserRegistry(_make_employees())
        groups = registry.group_by("job_family")
        assert len(groups["Technical/ Development"]) == 3  # Alice, Bob, Eve
        assert len(groups["Consulting"]) == 1  # Charlie

    def test_group_by_sup_org_level_6(self) -> None:
        registry = UserRegistry(_make_employees())
        groups = registry.group_by("sup_org_level_6")
        assert "BUSINESS SOLUTION" in groups
        assert len(groups["BUSINESS SOLUTION"]) == 4  # Alice, Charlie, Diana, Eve
        assert len(groups["SOLUTION DELIVERY"]) == 1  # Bob

    def test_org_summary(self) -> None:
        registry = UserRegistry(_make_employees())
        summary = registry.org_summary()
        assert summary["total_employees"] == 5
        assert summary["with_github_id"] == 4
        assert "25-29" in summary["age_ranges"]
        assert "Technical/ Development" in summary["job_families"]
        assert "Male" in summary["genders"]
        assert summary["genders"]["Male"] == 2
        assert summary["genders"]["Female"] == 3


class TestOrgLoader:
    """Test loading from the real Excel file (integration test)."""

    def test_load_real_file(self) -> None:
        from pathlib import Path
        xlsx_path = Path(__file__).parent.parent / "Org structure.xlsx"
        if not xlsx_path.exists():
            pytest.skip("Org structure.xlsx not available")

        from src.orgdata.loader import OrgDataLoader
        loader = OrgDataLoader(xlsx_path)
        employees = loader.load()

        assert len(employees) > 100
        # Verify fields are populated
        assert all(e.employee_id for e in employees)
        assert all(e.name for e in employees)
        assert any(e.age is not None for e in employees)
        assert any(e.sup_org_level_6 for e in employees)

    def test_loader_file_not_found(self) -> None:
        from src.orgdata.loader import OrgDataLoader
        with pytest.raises(FileNotFoundError):
            OrgDataLoader("/nonexistent/path.xlsx")


class TestToolsSchema:
    """Verify new tools are in the schema."""

    def test_org_tools_present(self) -> None:
        from src.agent.tools_schema import TOOLS
        names = [t["name"] for t in TOOLS]
        assert "get_org_structure_summary" in names
        assert "analyze_org_copilot_usage" in names

    def test_analyze_org_tool_has_group_by_enum(self) -> None:
        from src.agent.tools_schema import TOOLS
        tool = next(t for t in TOOLS if t["name"] == "analyze_org_copilot_usage")
        group_by = tool["input_schema"]["properties"]["group_by"]
        assert "age_range" in group_by["enum"]
        assert "sup_org_level_6" in group_by["enum"]
        assert "job_family" in group_by["enum"]
