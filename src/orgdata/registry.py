"""User registry that joins GitHub users with org structure data."""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from .models import Employee
from ..github_client.models import UserUsageRecord

logger = logging.getLogger(__name__)


class UserRegistry:
    """Registry that joins GitHub Copilot user data with org employee records.

    The join is performed on github_id (Employee.github_id == UserUsageRecord.github_login).

    Args:
        employees: List of Employee records from org structure.
    """

    def __init__(self, employees: list[Employee]) -> None:
        self._employees = employees
        self._by_github_id: dict[str, Employee] = {}
        self._by_employee_id: dict[str, Employee] = {}
        self._by_email: dict[str, Employee] = {}

        for emp in employees:
            if emp.github_id:
                self._by_github_id[emp.github_id.lower()] = emp
            if emp.employee_id:
                self._by_employee_id[emp.employee_id] = emp
            if emp.email_work:
                self._by_email[emp.email_work.lower()] = emp
            if emp.email:
                self._by_email[emp.email.lower()] = emp

        logger.info(
            "UserRegistry: %d employees, %d with github_id",
            len(employees),
            len(self._by_github_id),
        )

    @property
    def total_employees(self) -> int:
        return len(self._employees)

    @property
    def employees_with_github(self) -> int:
        return len(self._by_github_id)

    def lookup_by_github(self, github_login: str) -> Employee | None:
        """Find employee by GitHub login/ID.

        Args:
            github_login: GitHub username.

        Returns:
            Employee or None if not found.
        """
        return self._by_github_id.get(github_login.lower())

    def lookup_by_email(self, email: str) -> Employee | None:
        """Find employee by email address.

        Args:
            email: Email address.

        Returns:
            Employee or None if not found.
        """
        return self._by_email.get(email.lower())

    def enrich_users(
        self, users: list[UserUsageRecord]
    ) -> list[dict[str, Any]]:
        """Join GitHub usage records with org data.

        Args:
            users: List of GitHub Copilot usage records.

        Returns:
            List of dicts combining usage + org fields. Unmatched users
            are still included with org fields set to None.
        """
        enriched = []
        matched = 0

        for user in users:
            emp = self.lookup_by_github(user.github_login)
            record: dict[str, Any] = {
                "github_login": user.github_login,
                "completions_suggestions": user.completions_suggestions,
                "completions_acceptances": user.completions_acceptances,
                "completions_lines_suggested": user.completions_lines_suggested,
                "completions_lines_accepted": user.completions_lines_accepted,
                "chat_turns": user.chat_turns,
                "agent_turns": user.agent_turns,
                "cli_turns": user.cli_turns,
                "total_activity": (
                    user.completions_acceptances + user.chat_turns
                    + user.cli_turns + user.agent_turns
                ),
            }

            if emp:
                matched += 1
                record.update({
                    "employee_id": emp.employee_id,
                    "full_name": emp.full_name,
                    "age": emp.age,
                    "age_range": emp.age_range,
                    "gender": emp.gender,
                    "location": emp.location,
                    "location_country": emp.location_country,
                    "job_family": emp.job_family,
                    "job_title": emp.job_title,
                    "job_level": emp.job_level,
                    "job_category": emp.job_category,
                    "management_level": emp.management_level,
                    "is_manager": emp.is_manager,
                    "sup_org_level_2": emp.sup_org_level_2,
                    "sup_org_level_3": emp.sup_org_level_3,
                    "sup_org_level_4": emp.sup_org_level_4,
                    "sup_org_level_5": emp.sup_org_level_5,
                    "sup_org_level_6": emp.sup_org_level_6,
                    "sup_org_level_7": emp.sup_org_level_7,
                    "sup_org_level_8": emp.sup_org_level_8,
                    "sup_org_level_9": emp.sup_org_level_9,
                    "sup_org_level_10": emp.sup_org_level_10,
                    "org_matched": True,
                })
            else:
                record.update({
                    "employee_id": None,
                    "full_name": None,
                    "age": None,
                    "age_range": None,
                    "gender": None,
                    "location": None,
                    "location_country": None,
                    "job_family": None,
                    "job_title": None,
                    "job_level": None,
                    "job_category": None,
                    "management_level": None,
                    "is_manager": None,
                    "sup_org_level_2": None,
                    "sup_org_level_3": None,
                    "sup_org_level_4": None,
                    "sup_org_level_5": None,
                    "sup_org_level_6": None,
                    "sup_org_level_7": None,
                    "sup_org_level_8": None,
                    "sup_org_level_9": None,
                    "sup_org_level_10": None,
                    "org_matched": False,
                })

            enriched.append(record)

        logger.info(
            "Enriched %d users: %d matched with org data, %d unmatched",
            len(users),
            matched,
            len(users) - matched,
        )
        return enriched

    def group_by(
        self, field: str, employees: list[Employee] | None = None
    ) -> dict[str, list[Employee]]:
        """Group employees by a given field.

        Args:
            field: Field name to group by (e.g., 'age_range', 'sup_org_level_6', 'job_family').
            employees: Optional subset; defaults to all employees.

        Returns:
            Dict mapping field values to lists of employees.
        """
        source = employees or self._employees
        groups: dict[str, list[Employee]] = defaultdict(list)

        for emp in source:
            if field == "age_range":
                key = emp.age_range
            else:
                key = getattr(emp, field, None)
                if not key:
                    key = "Unknown"
                key = str(key)
            groups[key].append(emp)

        return dict(groups)

    def org_summary(self) -> dict[str, Any]:
        """Get summary statistics of the org structure.

        Returns:
            Dict with counts by various dimensions.
        """
        age_ranges = defaultdict(int)
        job_families = defaultdict(int)
        locations = defaultdict(int)
        sup_org_6 = defaultdict(int)
        genders = defaultdict(int)

        for emp in self._employees:
            age_ranges[emp.age_range] += 1
            if emp.job_family:
                job_families[emp.job_family] += 1
            if emp.location:
                locations[emp.location] += 1
            if emp.sup_org_level_6:
                sup_org_6[emp.sup_org_level_6] += 1
            if emp.gender:
                genders[emp.gender] += 1

        return {
            "total_employees": len(self._employees),
            "with_github_id": len(self._by_github_id),
            "age_ranges": dict(sorted(age_ranges.items())),
            "job_families": dict(sorted(job_families.items(), key=lambda x: -x[1])),
            "locations_top10": dict(sorted(locations.items(), key=lambda x: -x[1])[:10]),
            "sup_org_level_6": dict(sorted(sup_org_6.items(), key=lambda x: -x[1])),
            "genders": dict(genders),
        }
