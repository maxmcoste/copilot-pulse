"""Tests for the SQLite org database layer."""

from __future__ import annotations

import pytest

from src.orgdata.database import OrgDatabase


@pytest.fixture
def db(tmp_path):
    """Create an in-memory-like temp database."""
    db_path = tmp_path / "test_org.db"
    database = OrgDatabase(db_path)
    yield database
    database.close()


def _sample_employees() -> list[dict]:
    """Create sample employee dicts for import."""
    return [
        {
            "employee_id": "E001", "name": "ALICE", "surname": "SMITH",
            "github_id": "alice-gh", "age": 28, "gender": "Female",
            "job_family": "Technical/ Development", "location": "Roma",
            "email_work": "alice.smith@company.com",
            "sup_org_level_5": "ENG MODERNIZE", "sup_org_level_6": "BUSINESS SOLUTION",
        },
        {
            "employee_id": "E002", "name": "BOB", "surname": "JONES",
            "github_id": "bob-gh", "age": 42, "gender": "Male",
            "job_family": "Technical/ Development", "location": "Milano",
            "email_work": "bob.jones@company.com",
            "sup_org_level_5": "ENG MODERNIZE", "sup_org_level_6": "SOLUTION DELIVERY",
        },
        {
            "employee_id": "E003", "name": "CHARLIE", "surname": "BROWN",
            "github_id": None, "age": 55, "gender": "Male",
            "job_family": "Consulting", "location": "Roma",
            "email_work": "charlie.brown@company.com",
            "sup_org_level_5": "ENG MODERNIZE", "sup_org_level_6": "BUSINESS SOLUTION",
        },
        {
            "employee_id": "E004", "name": "DIANA", "surname": "ROSS",
            "github_id": None, "age": 35, "gender": "Female",
            "job_family": "Operations", "location": "Napoli",
            "email_work": None,
            "sup_org_level_5": "ENG MODERNIZE", "sup_org_level_6": "BUSINESS SOLUTION",
        },
        {
            "employee_id": "E005", "name": "EVE", "surname": "TAYLOR",
            "github_id": "eve-gh", "age": 31, "gender": "Female",
            "job_family": "Technical/ Development", "location": "Roma",
            "email_work": "eve.taylor@company.com",
            "sup_org_level_5": "ENG MODERNIZE", "sup_org_level_6": "BUSINESS SOLUTION",
        },
    ]


def _sample_usage() -> list[dict]:
    """Create sample Copilot usage records."""
    return [
        {
            "github_login": "alice-gh",
            "completions_suggestions": 200, "completions_acceptances": 80,
            "completions_lines_suggested": 300, "completions_lines_accepted": 120,
            "chat_turns": 15, "agent_turns": 2, "cli_turns": 3,
        },
        {
            "github_login": "bob-gh",
            "completions_suggestions": 100, "completions_acceptances": 30,
            "completions_lines_suggested": 150, "completions_lines_accepted": 45,
            "chat_turns": 5, "agent_turns": 0, "cli_turns": 0,
        },
        {
            "github_login": "eve-gh",
            "completions_suggestions": 50, "completions_acceptances": 20,
            "completions_lines_suggested": 75, "completions_lines_accepted": 30,
            "chat_turns": 8, "agent_turns": 1, "cli_turns": 0,
        },
        {
            "github_login": "unknown-user",
            "completions_suggestions": 10, "completions_acceptances": 5,
            "completions_lines_suggested": 15, "completions_lines_accepted": 8,
            "chat_turns": 2, "agent_turns": 0, "cli_turns": 0,
        },
    ]


class TestImportEmployees:

    def test_import_count(self, db: OrgDatabase) -> None:
        count = db.import_employees(_sample_employees())
        assert count == 5
        assert db.employee_count() == 5

    def test_mapped_count(self, db: OrgDatabase) -> None:
        db.import_employees(_sample_employees())
        assert db.mapped_count() == 3  # alice, bob, eve

    def test_replace_mode(self, db: OrgDatabase) -> None:
        db.import_employees(_sample_employees())
        db.import_employees(_sample_employees()[:2], replace=True)
        assert db.employee_count() == 2


class TestStoreUsage:

    def test_store_count(self, db: OrgDatabase) -> None:
        count = db.store_usage(_sample_usage())
        assert count == 4

    def test_upsert(self, db: OrgDatabase) -> None:
        db.store_usage(_sample_usage())
        db.store_usage(_sample_usage())  # same data again
        # Should still be 4 due to UNIQUE constraint with OR REPLACE
        rows = db._conn.execute("SELECT COUNT(*) FROM copilot_usage").fetchone()[0]
        assert rows == 4


class TestAutoMap:

    def test_auto_map_by_email(self, db: OrgDatabase) -> None:
        db.import_employees(_sample_employees())
        # charlie.brown should match employee E003 via email local part
        matches = db.auto_map_by_email(["charlie.brown"])
        assert len(matches) == 1
        assert matches[0]["employee_id"] == "E003"
        assert matches[0]["github_login"] == "charlie.brown"
        # Verify it was persisted
        assert db.mapped_count() == 4  # 3 original + 1 new

    def test_auto_map_name_surname(self, db: OrgDatabase) -> None:
        # Diana has no email_work, but name.surname should work
        emps = _sample_employees()
        # Give Diana an email so the email match doesn't trigger, but use a different login
        db.import_employees(emps)
        matches = db.auto_map_by_email(["diana-ross"])
        assert len(matches) == 1
        assert matches[0]["employee_id"] == "E004"

    def test_skip_already_mapped(self, db: OrgDatabase) -> None:
        db.import_employees(_sample_employees())
        # alice-gh is already mapped via github_id
        matches = db.auto_map_by_email(["alice-gh"])
        assert len(matches) == 0


class TestSetGithubId:

    def test_manual_mapping(self, db: OrgDatabase) -> None:
        db.import_employees(_sample_employees())
        db.set_github_id("E003", "charlie-dev", method="manual")
        assert db.mapped_count() == 4


class TestOrgSummary:

    def test_summary_structure(self, db: OrgDatabase) -> None:
        db.import_employees(_sample_employees())
        summary = db.org_summary()
        assert summary["total_employees"] == 5
        assert summary["with_github_id"] == 3
        assert "25-29" in summary["age_ranges"]
        assert "Technical/ Development" in summary["job_families"]
        assert summary["genders"]["Female"] == 3
        assert summary["genders"]["Male"] == 2


class TestAnalyzeCopilotBy:

    @pytest.fixture(autouse=True)
    def setup(self, db: OrgDatabase) -> None:
        db.import_employees(_sample_employees())
        db.store_usage(_sample_usage())

    def test_by_age_range(self, db: OrgDatabase) -> None:
        result = db.analyze_copilot_by("age_range", "active_users")
        assert result["type"] == "org_copilot_analysis"
        assert result["group_by"] == "age_range"
        # alice (28 -> 25-29), bob (42 -> 40-44), eve (31 -> 30-34)
        assert "25-29" in result["groups"]
        assert "40-44" in result["groups"]
        assert "30-34" in result["groups"]

    def test_by_sup_org_level_6(self, db: OrgDatabase) -> None:
        result = db.analyze_copilot_by("sup_org_level_6", "active_users")
        assert "BUSINESS SOLUTION" in result["groups"]
        assert "SOLUTION DELIVERY" in result["groups"]

    def test_acceptance_rate(self, db: OrgDatabase) -> None:
        result = db.analyze_copilot_by("job_family", "acceptance_rate")
        assert result["metric"] == "acceptance_rate"
        tech_rate = result["groups"].get("Technical/ Development")
        assert tech_rate is not None
        assert 30 <= tech_rate <= 45  # rough range

    def test_with_filter(self, db: OrgDatabase) -> None:
        result = db.analyze_copilot_by(
            "age_range", "active_users",
            filter_field="location", filter_value="Roma",
        )
        # Only alice and eve are in Roma with github IDs
        total = sum(result["groups"].values())
        assert total == 2

    def test_unsupported_group_by(self, db: OrgDatabase) -> None:
        result = db.analyze_copilot_by("invalid_field")
        assert "error" in result

    def test_unmatched_users(self, db: OrgDatabase) -> None:
        unmatched = db.unmatched_github_users()
        assert "unknown-user" in unmatched

    def test_mapping_stats(self, db: OrgDatabase) -> None:
        stats = db.mapping_stats()
        assert stats["total_employees"] == 5
        assert stats["total_copilot_users"] == 4
        assert stats["matched_copilot_users"] == 3  # alice, bob, eve
        assert stats["unmatched_copilot_users"] == 1  # unknown-user
